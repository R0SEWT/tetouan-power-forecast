import sys
sys.path.insert(0, "/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad/scripts")
import numpy as np, pandas as pd
from load849 import load

df = load(sys.argv[1]).set_index("dt")
y = df["Z1"]
n = len(y)
H = 6

def metrics(yt, yp):
    m = yt.notna() & yp.notna()
    yt, yp = yt[m], yp[m]
    e = yt - yp
    return dict(n=int(m.sum()), MAE=round(e.abs().mean(), 1), RMSE=round(np.sqrt((e ** 2).mean()), 1),
                MAPE=round((e.abs() / yt).mean() * 100, 2),
                R2=round(1 - (e ** 2).sum() / ((yt - yt.mean()) ** 2).sum(), 4))

# target at t+6 aligned to origin t
target = y.shift(-H)
preds = {
    "persistence y(t)": y,
    "same time yesterday y(t+6-144)": y.shift(144 - H),
    "same time last week y(t+6-1008)": y.shift(1008 - H),
    "persist+daily delta y(t)+[y(t+6-144)-y(t-144)]": y + (y.shift(144 - H) - y.shift(144)),
    "persist+weekly delta y(t)+[y(t+6-1008)-y(t-1008)]": y + (y.shift(1008 - H) - y.shift(1008)),
}
# evaluate: full year, chronological 70/15/15 split, per month
i70, i85 = int(n * 0.70), int(n * 0.85)
print("split boundaries:", y.index[i70], y.index[i85])
res = []
for name, p in preds.items():
    for lbl, sl in [("full", slice(0, n)), ("train70", slice(0, i70)), ("val15", slice(i70, i85)), ("test15", slice(i85, n))]:
        r = metrics(target.iloc[sl], p.iloc[sl]); r.update(model=name, part=lbl); res.append(r)
R = pd.DataFrame(res)
print(R.pivot(index="model", columns="part", values="MAE")[["full", "train70", "val15", "test15"]].to_string())
print(R.pivot(index="model", columns="part", values="MAPE")[["full", "train70", "val15", "test15"]].to_string())
print(R.pivot(index="model", columns="part", values="R2")[["full", "train70", "val15", "test15"]].to_string())
# per month (month of the target time)
tm = target.index + pd.Timedelta(minutes=10 * H)
pm = []
for name, p in preds.items():
    for mth in range(1, 13):
        m = (tm.month == mth)
        r = metrics(target[m], p[m]); r.update(model=name, month=mth); pm.append(r)
PM = pd.DataFrame(pm)
print("\nPer-month MAE (kW, by month of target time):")
print(PM.pivot(index="month", columns="model", values="MAE").to_string())
print("\nPer-month MAPE %:")
print(PM.pivot(index="month", columns="model", values="MAPE").to_string())

# hourly-resolution persistence (1h mean, 1h ahead) for comparison with hourly literature
yh = y.resample("1h").mean()
print("\nHourly series persistence (1 step = 1h ahead):", metrics(yh.shift(-1), yh), " same hour yesterday:", metrics(yh.shift(-1), yh.shift(23)))

# ---------- month boundary steps (scaling artefact check) ----------
dif = y.diff()
mid = dif[(dif.index.hour == 0) & (dif.index.minute == 0)]
first = mid[mid.index.day == 1]
other = mid[mid.index.day != 1]
print("\n23:50->00:00 jumps Z1: other days median %.0f, IQR [%.0f, %.0f]" % (other.median(), other.quantile(.25), other.quantile(.75)))
for c in ["Z1", "Z2", "Z3"]:
    s = df[c]; d_ = s.diff(); m0 = d_[(d_.index.hour == 0) & (d_.index.minute == 0)]
    f = m0[m0.index.day == 1]; o = m0[m0.index.day != 1]
    z = (f - o.mean()) / o.std()
    # relative jump vs same-transition
    print(c, "1st-of-month midnight jumps z-scores:", {i.strftime("%m"): round(v, 1) for i, v in z.items()})

# ---------- DST: does LOAD shift relative to the fixed timestamp? cross-correlate mean weekday profiles ----------
def prof(a, b, col="Z1"):
    s = df.loc[a:b, col]
    s = s[s.index.dayofweek < 5]
    p = s.groupby(s.index.hour * 6 + s.index.minute // 10).mean()
    return (p - p.mean()) / p.std()
def best_lag(p1, p2, maxlag=12):
    best = None
    for L in range(-maxlag, maxlag + 1):
        c = np.corrcoef(p1.values, np.roll(p2.values, L))[0, 1]
        if best is None or c > best[1]:
            best = (L, c)
    return best
print("\nLoad-profile lag (10-min steps) after vs before transition (positive = after-profile occurs EARLIER in timestamp):")
for lbl, a1, b1, a2, b2 in [
    ("DST start 26 Mar", "2017-03-13", "2017-03-24", "2017-03-27", "2017-04-07"),
    ("Ramadan suspension 21 May", "2017-05-08", "2017-05-19", "2017-05-22", "2017-05-26"),
    ("DST resume 2 Jul", "2017-06-26", "2017-06-30", "2017-07-03", "2017-07-14"),
    ("DST end 29 Oct", "2017-10-16", "2017-10-27", "2017-10-30", "2017-11-10"),
    ("control: no change 10 Feb", "2017-01-30", "2017-02-09", "2017-02-13", "2017-02-24"),
    ("control: no change 15 Sep", "2017-09-04", "2017-09-15", "2017-09-18", "2017-09-29")]:
    for col in ["Z1", "Z2", "Z3"]:
        L, c = best_lag(prof(a1, b1, col), prof(a2, b2, col))
        print(f"  {lbl:28s} {col}: lag={L:+d} steps ({L*10:+d} min) corr={c:.3f}")
# morning ramp timing: time when weekday mean profile crosses its daily midpoint between 05:00 and 10:00
def ramp_time(a, b, col="Z1"):
    s = df.loc[a:b, col]; s = s[s.index.dayofweek < 5]
    p = s.groupby(s.index.hour * 60 + s.index.minute).mean()
    lo, hi = p.loc[240:420].min(), p.loc[480:720].max()
    thr = lo + 0.5 * (hi - lo)
    seg = p.loc[300:720]
    return int(seg[seg > thr].index[0])
for a, b in [("2017-03-13", "2017-03-24"), ("2017-03-27", "2017-04-07"), ("2017-05-08", "2017-05-19"),
             ("2017-07-03", "2017-07-14"), ("2017-10-16", "2017-10-27"), ("2017-10-30", "2017-11-10")]:
    t = ramp_time(a, b)
    print("  morning ramp 50% crossing Z1", a, b, f"{t//60:02d}:{t%60:02d}")

# ---------- contemporaneous R2 from calendar alone ----------
X = pd.DataFrame(index=df.index)
X["hod"] = df.index.hour * 6 + df.index.minute // 10  # 144 slots
X["hour"] = df.index.hour
X["dow"] = df.index.dayofweek
X["month"] = df.index.month
def r2(yt, yp):
    return 1 - ((yt - yp) ** 2).sum() / ((yt - yt.mean()) ** 2).sum()
def table_pred(keys, train_idx, test_idx):
    g = y.iloc[train_idx].groupby([X[k].iloc[train_idx] for k in keys]).mean()
    kk = pd.MultiIndex.from_frame(X[keys].iloc[test_idx]) if len(keys) > 1 else X[keys[0]].iloc[test_idx]
    p = g.reindex(kk).values
    return pd.Series(p, index=y.index[test_idx])
allidx = np.arange(n)
print("\nContemporaneous R2 from calendar lookup tables (no lags, no weather):")
for keys in [["hour"], ["hod"], ["hour", "dow"], ["hod", "dow"], ["hod", "month"], ["hod", "dow", "month"]]:
    p_in = table_pred(keys, allidx, allidx)
    rng = np.random.default_rng(0); perm = rng.permutation(n); tr, te = np.sort(perm[: int(.8 * n)]), np.sort(perm[int(.8 * n):])
    p_rs = table_pred(keys, tr, te)
    tr_c, te_c = allidx[:i70], allidx[i85:]
    p_ch = table_pred(keys, tr_c, te_c)
    print(f"  {'x'.join(keys):18s} in-sample R2={r2(y, p_in):.3f}  random80/20 test R2={r2(y.iloc[te], p_rs):.3f}  chrono(train70->test15) R2={r2(y.iloc[te_c], p_ch):.3f}")
# R2 of t+6 persistence on test, for comparison
print("  t+6 persistence R2 test15:", round(r2(target.iloc[i85:n - H], y.iloc[i85:n - H]), 4))

# ---------- the 'same-instant' recipe common in the literature: RF with calendar+weather, random split ----------
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
F = pd.DataFrame(index=df.index)
F["hour"] = df.index.hour; F["minute"] = df.index.minute; F["dow"] = df.index.dayofweek
F["month"] = df.index.month; F["day"] = df.index.day; F["doy"] = df.index.dayofyear
for c in ["T", "H", "W", "GDF", "DF"]:
    F[c] = df[c]
def fitpred(cols, tr, te, seed=0):
    m = RandomForestRegressor(n_estimators=200, min_samples_leaf=1, n_jobs=-1, random_state=seed)
    m.fit(F[cols].iloc[tr], y.iloc[tr]); p = m.predict(F[cols].iloc[te])
    yt = y.iloc[te]
    return r2(yt, p), (yt - p).abs().mean(), ((yt - p).abs() / yt).mean() * 100
rng = np.random.default_rng(42); perm = rng.permutation(n); tr, te = np.sort(perm[: int(.8 * n)]), np.sort(perm[int(.8 * n):])
tr_c, te_c = allidx[:i70], allidx[i85:]
print("\nSame-instant RandomForest (no lags of Z1):")
for lbl, cols in [("weather only", ["T", "H", "W", "GDF", "DF"]),
                  ("calendar only (incl. month/day/doy)", ["hour", "minute", "dow", "month", "day", "doy"]),
                  ("calendar + weather", ["hour", "minute", "dow", "month", "day", "doy", "T", "H", "W", "GDF", "DF"]),
                  ("calendar(hour,minute,dow) + weather, no date", ["hour", "minute", "dow", "T", "H", "W", "GDF", "DF"])]:
    a = fitpred(cols, tr, te); b = fitpred(cols, tr_c, te_c)
    print(f"  {lbl:45s} random80/20: R2={a[0]:.3f} MAE={a[1]:.0f} MAPE={a[2]:.2f}% | chrono 70->last15: R2={b[0]:.3f} MAE={b[1]:.0f} MAPE={b[2]:.2f}%")
