import sys, math
import numpy as np
import pandas as pd

path = sys.argv[1]
df = pd.read_csv(path)
df.columns = [c.strip() for c in df.columns]
ren = {"DateTime": "dt", "Temperature": "T", "Humidity": "H", "Wind Speed": "W",
       "general diffuse flows": "GDF", "diffuse flows": "DF",
       "Zone 1 Power Consumption": "Z1", "Zone 2  Power Consumption": "Z2",
       "Zone 3  Power Consumption": "Z3"}
df = df.rename(columns=ren)
df["dt"] = pd.to_datetime(df["dt"], format="%m/%d/%Y %H:%M")
print("rows", len(df), "start", df.dt.min(), "end", df.dt.max())
d = df.dt.diff().dropna()
print("step counts:", d.value_counts().to_dict())
print("duplicated timestamps:", df.dt.duplicated().sum())
full = pd.date_range(df.dt.min(), df.dt.max(), freq="10min")
print("missing timestamps within range:", len(full.difference(df.dt)))
print("days:", df.dt.dt.normalize().nunique(), "rows/day set:", set(df.groupby(df.dt.dt.date).size()))
print(df.describe().T.to_string())

# ---------- DST transition windows -----------
for day in ["2017-03-26", "2017-05-21", "2017-07-02", "2017-10-29"]:
    sub = df[(df.dt >= pd.Timestamp(day) + pd.Timedelta("1h")) & (df.dt <= pd.Timestamp(day) + pd.Timedelta("4h"))]
    print("DST window", day, "n=", len(sub), "Z1 first/last:", round(sub.Z1.iloc[0]), round(sub.Z1.iloc[-1]))

# ---------- Solar timing: GDF centroid (clock time) vs astronomical solar noon (UTC) ----------
lat, lon = 35.5785, -5.3684
def solar_noon_utc(date):
    n = date.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eot = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    return 720 - 4 * lon - eot  # minutes UTC
df["date"] = df.dt.dt.date
df["mod"] = df.dt.dt.hour * 60 + df.dt.dt.minute + 5  # interval midpoint
rows = []
for dte, g in df.groupby("date"):
    w = g.GDF.clip(lower=0)
    if w.sum() <= 0:
        continue
    cen = (w * g["mod"]).sum() / w.sum()
    # first time GDF>20 (sunrise proxy)
    above = g[g.GDF > 20]
    first = above["mod"].iloc[0] if len(above) else np.nan
    rows.append((pd.Timestamp(dte), cen, solar_noon_utc(pd.Timestamp(dte)), first, g.GDF.max(), g.DF.max()))
sol = pd.DataFrame(rows, columns=["date", "gdf_centroid_min", "solar_noon_utc_min", "first_gdf20_min", "gdf_max", "df_max"])
sol["offset_min"] = sol.gdf_centroid_min - sol.solar_noon_utc_min
sol["month"] = sol.date.dt.month
print("\nGDF centroid minus astronomical solar noon (UTC), minutes; median by month:")
print(sol.groupby("month").offset_min.median().round(1).to_string())
def per(a, b):
    m = (sol.date >= pd.Timestamp(a)) & (sol.date < pd.Timestamp(b))
    return round(sol.loc[m, "offset_min"].median(), 1), int(m.sum())
for lbl, a, b in [("pre-DST Jan1-Mar25", "2017-01-01", "2017-03-26"),
                  ("DST Mar26-May20", "2017-03-26", "2017-05-21"),
                  ("Ramadan suspension May21-Jul1", "2017-05-21", "2017-07-02"),
                  ("DST Jul2-Oct28", "2017-07-02", "2017-10-29"),
                  ("post-DST Oct29-Dec30", "2017-10-29", "2017-12-31")]:
    print(" ", lbl, per(a, b))
for a, b in [("2017-03-19", "2017-04-02"), ("2017-05-14", "2017-05-28"), ("2017-06-25", "2017-07-09"), ("2017-10-22", "2017-11-05")]:
    m = (sol.date >= pd.Timestamp(a)) & (sol.date < pd.Timestamp(b))
    print(" daily offsets", a, b, sol.loc[m, ["date", "offset_min"]].assign(date=lambda x: x.date.dt.strftime("%m-%d")).set_index("date").offset_min.round(0).to_dict())
print("GDF max overall", df.GDF.max(), "DF max", df.DF.max(), "GDF night (00-04h) median", df[df.dt.dt.hour < 4].GDF.median())
print("Monthly max GDF / DF:")
print(df.groupby(df.dt.dt.month)[["GDF", "DF"]].max().to_string())
print("share rows DF>GDF:", (df.DF > df.GDF).mean().round(3), "share DF>GDF when GDF>100:", (df[df.GDF > 100].DF > df[df.GDF > 100].GDF).mean().round(3))

# Load-profile timing check: clock hour of daily max Z1 (evening peak) around DST changes
df["hourf"] = df["mod"] / 60
pk = df.groupby("date").apply(lambda g: g.loc[g.Z1.idxmax(), "hourf"])
pk.index = pd.to_datetime(pk.index)
for lbl, a, b in [("pre-DST", "2017-03-12", "2017-03-26"), ("DST", "2017-03-26", "2017-04-09"),
                  ("DST bef. Ram.", "2017-05-07", "2017-05-21"), ("Ram. susp.", "2017-05-21", "2017-06-04"),
                  ("susp. end", "2017-06-18", "2017-07-02"), ("DST after", "2017-07-02", "2017-07-16"),
                  ("DST Oct", "2017-10-15", "2017-10-29"), ("post Oct", "2017-10-29", "2017-11-12")]:
    m = (pk.index >= a) & (pk.index < b)
    print(" Z1 daily-peak clock hour median", lbl, round(pk[m].median(), 2))

# ---------- weather plausibility ----------
def runs(s, minlen):
    same = s.ne(s.shift()).cumsum()
    r = s.groupby(same).agg(["first", "size"])
    r = r[r["size"] >= minlen]
    return r
for c in ["T", "H", "W", "GDF", "DF", "Z1", "Z2", "Z3"]:
    r = runs(df[c], 6)
    print(f"{c}: runs of identical value >=6 steps (1h): {len(r)}, longest {r['size'].max() if len(r) else 0}, unique values {df[c].nunique()}")
# linear interpolation detection: second difference == 0 over long stretches
for c in ["T", "H", "W"]:
    d2 = df[c].diff().diff().abs()
    print(c, "share of exact-zero 2nd diff:", round((d2 < 1e-9).mean(), 4))
print("Wind speed value distribution (quantiles):", df.W.quantile([.01, .1, .25, .5, .75, .9, .99]).round(3).to_dict())
print("Wind share <0.2:", round((df.W < 0.2).mean(), 3), " share >4:", round((df.W > 4).mean(), 3), " share 0.2-4:", round(((df.W >= 0.2) & (df.W <= 4)).mean(), 3))
wm = df.groupby(df.dt.dt.month).W.agg(lambda s: round((s > 4).mean(), 3))
print("Wind share >4 by month:", wm.to_dict())
# wind regime switches
hi = (df.W > 2).astype(int)
sw = hi.diff().abs().sum()
print("wind high/low regime switches:", int(sw))
seg = hi.ne(hi.shift()).cumsum()
segs = df.groupby(seg).agg(start=("dt", "first"), end=("dt", "last"), n=("W", "size"), mean=("W", "mean"))
print("longest wind segments:\n", segs.sort_values("n", ascending=False).head(12).to_string())
print("Temperature range", df["T"].min(), df["T"].max(), "Humidity range", df.H.min(), df.H.max())
print("Temperature monthly mean:", df.groupby(df.dt.dt.month)["T"].mean().round(1).to_dict())

# ---------- denominators / scaling artefact ----------
def best_den(v, maxd=2000):
    for d_ in range(1, maxd):
        x = v * d_
        if abs(x - round(x)) < 0.02 * d_ / 1000 + 1e-3 * d_ / 10:
            pass
    return None
def den_of(vals, maxd=3000):
    # smallest d such that all vals*d are (near) integers multiple
    for d_ in range(1, maxd):
        x = vals * d_
        if np.all(np.abs(x - np.round(x)) < 0.05):
            return d_
    return None
print("\nDenominator test (smallest d s.t. value*d is integer) on daily samples:")
out = []
for dte, g in df.groupby("date"):
    out.append((dte, den_of(g.Z1.values[:20]), den_of(g.Z2.values[:20]), den_of(g.Z3.values[:20])))
den = pd.DataFrame(out, columns=["date", "d1", "d2", "d3"])
den["date"] = pd.to_datetime(den.date)
for c in ["d1", "d2", "d3"]:
    ch = den[den[c].ne(den[c].shift())]
    print(c, "number of distinct denominators:", den[c].nunique(), "; change points (first 40):", [(r.date.strftime("%m-%d"), r[c]) for r in ch.itertuples()][:40])
# numerators: value*d -> integer ; check granularity of numerator
for c, dc in [("Z1", "d1"), ("Z2", "d2"), ("Z3", "d3")]:
    m = df.merge(den[["date", dc]].assign(date=lambda x: x.date.dt.date), on="date")
    num = np.round(m[c] * m[dc]).astype(np.int64)
    g = np.gcd.reduce(num.values[:5000])
    print(c, "gcd of numerators (first 5000 rows):", g, "example numerators:", num.values[:5].tolist())

# ---------- level shifts ----------
dm = df.set_index("dt")[["Z1", "Z2", "Z3"]].resample("D").mean()
print("\nMonthly means:")
print(df.groupby(df.dt.dt.month)[["Z1", "Z2", "Z3"]].mean().round(0).to_string())
for c in ["Z1", "Z2", "Z3"]:
    jump = dm[c].diff()
    big = jump.abs().sort_values(ascending=False).head(6)
    print(c, "largest day-to-day jumps in daily mean:", [(i.strftime("%m-%d"), round(jump[i]), round(dm[c][i])) for i in big.index])
# ratio of daily mean to 7-day rolling median of previous days
for c in ["Z1", "Z2", "Z3"]:
    r = dm[c] / dm[c].shift(1).rolling(7).median()
    print(c, "days with ratio >1.15 or <0.85:", [(i.strftime("%m-%d"), round(v, 2)) for i, v in r[(r > 1.15) | (r < 0.85)].items()])

df.to_pickle(sys.argv[2])
sol.to_csv(sys.argv[3], index=False)
den.to_csv(sys.argv[4], index=False)
