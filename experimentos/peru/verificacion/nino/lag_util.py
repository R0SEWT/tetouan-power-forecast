"""Utilidad predictiva con rezago de publicación: corr de anomalía mensual de Tmedia (ERA5) con
ICEN(t-2) [último definitivo disponible], N12 OISST mensual (t-1) y N12 semanal más reciente."""
import sys, io, pandas as pd
D = sys.argv[1]
def rd_om(p):
    t = open(p).read().split("\n\n", 1)[1]
    df = pd.read_csv(io.StringIO(t), parse_dates=["time"]).set_index("time")
    return df.iloc[:, 2]
icen = {}
for l in open(f"{D}/icen/ICEN.txt", encoding="utf-8"):
    if l.startswith("%"): continue
    p = l.split()
    if len(p) >= 3: icen[pd.Period(year=int(p[0]), month=int(p[1]), freq="M")] = float(p[2])
icen = pd.Series(icen)
ois = pd.read_csv(f"{D}/noaa/sstoi.indices", sep=r"\s+")
ois.index = [pd.Period(year=int(y), month=int(m), freq="M") for y, m in zip(ois.YR, ois.MON)]
n12 = ois.iloc[:, 3]
print("Autocorrelación ICEN (1982-2025): lag1=%.2f lag2=%.2f lag3=%.2f" % tuple(icen["1982":"2025"].autocorr(k) for k in (1, 2, 3)))
for city in ["lima", "piura", "tumbes", "chiclayo"]:
    s = rd_om(f"{D}/openmeteo/{city}_era5.csv").resample("ME").mean()
    s.index = s.index.to_period("M")
    a = s - s.groupby(s.index.month).transform("mean")
    j = pd.DataFrame({"a": a, "icen0": icen, "icen_m2": icen.shift(2), "n12_m1": n12.shift(1), "n12_0": n12}).dropna()
    print(f"{city:9s} r(ICEN t)={j.a.corr(j.icen0):+.2f}  r(ICEN t-2, disponible)={j.a.corr(j.icen_m2):+.2f}  r(N12 OISST t-1)={j.a.corr(j.n12_m1):+.2f}  r(N12 OISST t)={j.a.corr(j.n12_0):+.2f}  n={len(j)}")
    # solo verano DEFM
    v = j[j.index.month.isin([12, 1, 2, 3])]
    print(f"{'':9s} verano (DEFM): r(ICEN t-2)={v.a.corr(v.icen_m2):+.2f} r(N12 t-1)={v.a.corr(v.n12_m1):+.2f} n={len(v)}")
