import sys, pandas as pd, numpy as np
df = pd.read_csv(sys.argv[1], parse_dates=["t"]).set_index("t").sort_index()
df.columns = ["y", "pdo", "pso"]
df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="30min"))
e = df.pdo - df.y
df["e"] = e
# day D of a period-end timestamp: period start date
df["dia"] = (df.index - pd.Timedelta(minutes=30)).normalize()
df["hh"] = ((df.index - pd.Timedelta(minutes=30)).hour * 2 + (df.index - pd.Timedelta(minutes=30)).minute // 30)
def stats(sl, name):
    d = df.loc[sl].dropna(subset=["e", "y"])
    a = d.e.abs()
    print(f"{name}: n={len(d)} MAE={a.mean():.1f} MAPE={100*(a/d.y).mean():.2f}% bias={d.e.mean():+.1f} "
          f"q90={a.quantile(.9):.0f} q95={a.quantile(.95):.0f} q97.5={a.quantile(.975):.0f} q99={a.quantile(.99):.0f} sd={d.e.std():.0f}")
for y in ["2017","2022","2023","2024","2025","2026"]:
    stats(y, "PDO "+y)
# debiased PDO: bias per half-hour slot estimated from the 28 complete days ending D-2
piv = df.pivot_table(index="dia", columns="hh", values="e")
bias = piv.shift(2).rolling(28, min_periods=20).mean()
corr = bias.stack().rename("b")
df2 = df.join(corr, on=["dia", "hh"])
df2["pdo_db"] = df2.pdo - df2.b
for y in ["2024","2025","2026"]:
    d = df2.loc[y].dropna(subset=["pdo_db","y"])
    a0 = (d.pdo-d.y).abs(); a1 = (d.pdo_db-d.y).abs()
    print(f"debiased {y}: MAE {a0.mean():.1f} -> {a1.mean():.1f}  MAPE {100*(a0/d.y).mean():.2f} -> {100*(a1/d.y).mean():.2f}")
# ramp errors (30-min and 2h ramps)
for y in ["2025"]:
    d = df.loc[y]
    for k in [1,4]:
        r_true = d.y.diff(k); r_pdo = d.pdo.diff(k)
        er = (r_pdo-r_true).abs().dropna()
        print(f"ramp {k*30}min {y}: MAE ramp err={er.mean():.1f} q95={er.quantile(.95):.0f}")
    # daily peak
    g = d.dropna(subset=["y","pdo"]).groupby("dia")
    pk = (g.pdo.max()-g.y.max())
    tm = (g.pdo.idxmax()-g.y.idxmax()).abs().dt.total_seconds()/3600
    print(f"daily peak {y}: MAE={pk.abs().mean():.1f} bias={pk.mean():+.1f} peak-time |err|<=1h share={(tm<=1).mean():.2f}")
# gamma tolerance episodes (>3 consecutive half-hours outside tolerance)
d = df.loc["2025"].dropna(subset=["y","pdo"])
g = (d.y - d.pdo)/d.pdo
for tau in [0.02,0.03,0.05]:
    out = (g.abs() > tau).astype(int)
    runs = out.groupby((out != out.shift()).cumsum()).agg(["first","size"])
    ep = runs[(runs["first"]==1) & (runs["size"]>3)]
    print(f"tau={tau:.0%}: half-hours out={out.mean():.3f}, episodes >3 consecutive={len(ep)}")
# El Nino costero months vs same months other years
def mape(sl):
    d = df.loc[sl].dropna(subset=["e","y"]); return 100*(d.e.abs()/d.y).mean()
print("ElNino 2017 Feb-Apr", round(mape(slice("2017-02-01","2017-04-30")),2), "| 2018 Feb-Apr", round(mape(slice("2018-02-01","2018-04-30")),2), "| 2019 Feb-Apr", round(mape(slice("2019-02-01","2019-04-30")),2))
print("ElNino 2023 Mar-Jul", round(mape(slice("2023-03-01","2023-07-31")),2), "| 2022 Mar-Jul", round(mape(slice("2022-03-01","2022-07-31")),2), "| 2024 Mar-Jul", round(mape(slice("2024-03-01","2024-07-31")),2))
print("2026 Mar-Oct", round(mape(slice("2026-03-01","2026-10-31")),2), "| 2025 Mar-Oct", round(mape(slice("2025-03-01","2025-10-31")),2))
