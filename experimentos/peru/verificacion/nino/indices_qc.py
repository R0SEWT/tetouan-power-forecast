"""QC de índices ENSO: ICEN (IGP/ENFEN), ONI y Niño 1+2 (NOAA CPC).
Uso: uv run --with pandas python -I indices_qc.py <dir_dl>
"""
import sys, re, glob, os
import pandas as pd
import numpy as np

D = sys.argv[1]
pd.set_option("display.width", 200)

def read_icen(path):
    rows = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if line.startswith("%") or not line.strip():
            continue
        p = line.split()
        if len(p) < 3:
            continue
        try:
            rows.append((int(p[0]), int(p[1]), float(p[2])))
        except ValueError:
            pass
    s = pd.Series({pd.Period(year=y, month=m, freq="M"): v for y, m, v in rows})
    return s.sort_index()

SEAS = ["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"]
def read_oni(path):
    rows = []
    for line in open(path):
        p = line.split()
        if len(p) == 4 and p[0] in SEAS:
            rows.append((int(p[1]), SEAS.index(p[0]) + 1, float(p[3])))
    return pd.Series({pd.Period(year=y, month=m, freq="M"): v for y, m, v in rows}).sort_index()

def read_cpc_monthly(path):
    df = pd.read_csv(path, sep=r"\s+")
    df.columns = ["YR","MON","N12","N12A","N3","N3A","N4","N4A","N34","N34A"]
    df.index = [pd.Period(year=int(y), month=int(m), freq="M") for y, m in zip(df.YR, df.MON)]
    return df

def read_weekly(path):
    rows = []
    for line in open(path):
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)", line)
        if not m:
            continue
        vals = [float(x) for x in re.findall(r"-?\d+\.\d", m.group(2))]
        if len(vals) == 8:
            rows.append([pd.to_datetime(m.group(1), format="%d%b%Y")] + vals)
    df = pd.DataFrame(rows, columns=["week","N12","N12A","N3","N3A","N34","N34A","N4","N4A"]).set_index("week")
    return df

icen = read_icen(f"{D}/icen/ICEN.txt")
icen9120 = read_icen(f"{D}/icen/ICEN_91_20.txt")
icen8110 = read_icen(f"{D}/icen/ICEN_81_10.txt")
oni = read_oni(f"{D}/noaa/oni.ascii.txt")
ers = read_cpc_monthly(f"{D}/noaa/ersst5.nino.mth.91-20.ascii")
ois = read_cpc_monthly(f"{D}/noaa/sstoi.indices")
wk = read_weekly(f"{D}/noaa/wksst9120.for")

print("=== 1. Cobertura y huecos ===")
for name, s in [("ICEN oficial", icen), ("ICEN trad 91-20", icen9120), ("ICEN trad 81-10", icen8110), ("ONI", oni)]:
    full = pd.period_range(s.index.min(), s.index.max(), freq="M")
    miss = full.difference(s.index)
    print(f"{name:16s} {s.index.min()}..{s.index.max()} n={len(s)} huecos={len(miss)} NaN={s.isna().sum()} dup={s.index.duplicated().sum()}")
for name, df in [("ERSSTv5 CPC", ers), ("OISST CPC", ois)]:
    full = pd.period_range(df.index.min(), df.index.max(), freq="M")
    print(f"{name:16s} {df.index.min()}..{df.index.max()} n={len(df)} huecos={len(full.difference(df.index))}")
wd = wk.index.to_series().diff().dt.days.value_counts()
print(f"OISST semanal     {wk.index.min().date()}..{wk.index.max().date()} n={len(wk)} pasos(días)={dict(wd)}")
# valores con más de 2 decimales (errores de tipeo) en ICEN.txt
raw = [l for l in open(f"{D}/icen/ICEN.txt", encoding="utf-8") if not l.startswith("%")]
odd = [l.strip() for l in raw if re.search(r"\.\d{3,}", l)]
print("ICEN.txt líneas con >2 decimales:", odd[:5])

# Tabla HTML (lista de eventos) vs ICEN.txt
t = open(f"{D}/icen/lista_eventos_ICEN.html", encoding="utf-8", errors="replace").read()
cells = re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", t)
html_vals = {}
year = None; buf = []
for c in cells:
    c = c.strip()
    if re.fullmatch(r"(19|20)\d{2}", c):
        year = int(c); buf = []; continue
    if year and re.fullmatch(r"-?\d+\.\d+", c):
        buf.append(float(c))
        if len(buf) <= 12:
            html_vals[pd.Period(year=year, month=len(buf), freq="M")] = float(c)
hv = pd.Series(html_vals)
common = hv.index.intersection(icen.index)
diff = (hv[common] - icen[common]).round(3)
bad = diff[diff.abs() > 0.005]
print(f"Tabla HTML vs ICEN.txt: {len(common)} meses comparados, {len(bad)} discrepancias")
for p, v in bad.items():
    print(f"   {p}: html={hv[p]} txt={icen[p]}")

print("\n=== 2. Revisiones (Wayback) ===")
snaps = sorted(glob.glob(f"{D}/wayback/icen_*.txt"))
snapd = {os.path.basename(f)[5:13]: read_icen(f) for f in snaps}
for k, s in snapd.items():
    print(f"snapshot {k}: último mes={s.index.max()} valor={s.iloc[-1]:.2f} n={len(s)}")
# valores de 2017 enero-abril según cada snapshot
months = [pd.Period(f"2017-{m:02d}", "M") for m in (1, 2, 3, 4)]
tab = pd.DataFrame({k: s.reindex(months) for k, s in snapd.items()})
tab["oficial_2024"] = icen.reindex(months)
tab["trad_81_10_hoy"] = icen8110.reindex(months)
print("ICEN ene-abr 2017 según versión publicada:\n", tab.round(2).to_string())
months = pd.period_range("2023-02", "2023-07", freq="M")
tab = pd.DataFrame({k: s.reindex(months) for k, s in snapd.items() if k >= "2023"})
tab["oficial_2024"] = icen.reindex(months)
print("ICEN feb-jul 2023 según versión publicada:\n", tab.round(2).to_string())
# magnitud de las revisiones entre snapshots consecutivos (mismo método 2012)
keys = [k for k in snapd if k < "2025"]
for a, b in zip(keys[:-1], keys[1:]):
    c = snapd[a].index.intersection(snapd[b].index)
    d = (snapd[b][c] - snapd[a][c]).abs()
    rec = c[c >= snapd[a].index.max() - 11]
    dr = (snapd[b][rec] - snapd[a][rec]).abs()
    print(f"{a}->{b}: comunes={len(c)} max|Δ|={d.max():.2f} media|Δ|={d.mean():.3f} | últimos 12 meses max|Δ|={dr.max():.2f}")
# cambio de método: snapshot 2024-11 (2012) vs oficial 2024
old = snapd["20241112"]
c = old.index.intersection(icen.index)
d = icen[c] - old[c]
print(f"Método 2012 (snap 2024-11) vs oficial 2024: n={len(c)} sesgo medio={d.mean():.2f} max|Δ|={d.abs().max():.2f} r={np.corrcoef(old[c], icen[c])[0,1]:.3f}")
for per in [("1950", "1980"), ("1981", "2005"), ("2006", "2024")]:
    cc = c[(c >= pd.Period(per[0] + "-01", "M")) & (c <= pd.Period(per[1] + "-12", "M"))]
    print(f"   {per}: sesgo medio={d[cc].mean():+.2f} max|Δ|={d[cc].abs().max():.2f}")

# ONI revisiones
osn = {os.path.basename(f)[4:12]: read_oni(f) for f in sorted(glob.glob(f"{D}/wayback/oni_2*.txt")) if "dec" in f or "20260309194143" not in f}
for k, s in osn.items():
    c = s.index.intersection(oni.index)
    d = (oni[c] - s[c]).abs()
    rec = c[c >= s.index.max() - 11]
    print(f"ONI snapshot {k} (último {s.index.max()}) vs hoy: n={len(c)} max|Δ|={d.max():.2f} meses con |Δ|>0={int((d>0.005).sum())} | últimos 12: max|Δ|={(oni[rec]-s[rec]).abs().max():.2f}")

print("\n=== 3. Coherencia entre índices ===")
n12_ers3 = ers["N12A"].rolling(3, center=True).mean()
n12_ois3 = ois["N12A"].rolling(3, center=True).mean()
n34_ois3 = ois["N34A"].rolling(3, center=True).mean()
df = pd.DataFrame({"ICEN": icen, "ICEN_91_20": icen9120, "ONI": oni, "N12_ERSST_3m": n12_ers3,
                   "N12_OISST_3m": n12_ois3, "N34_OISST_3m": n34_ois3, "N12_OISST_mens": ois["N12A"]})
sub = df.loc[pd.Period("1982-02", "M"):pd.Period("2025-12", "M")]
print("Correlaciones (1982-2025, mensual):\n", sub.corr().round(2).to_string())
# Reproducir ICEN oficial con CPC ERSST 91-20 en 2006-2025
c = pd.period_range("2006-01", "2025-12", freq="M")
d = (df.loc[c, "ICEN"] - df.loc[c, "N12_ERSST_3m"]).dropna()
print(f"ICEN oficial - media3(N12 ERSST CPC 91-20), 2006-2025: sesgo={d.mean():+.3f} max|Δ|={d.abs().max():.2f} RMSE={np.sqrt((d**2).mean()):.3f}")
d2 = (df.loc[c, "ICEN"] - df.loc[c, "N12_OISST_3m"]).dropna()
print(f"ICEN oficial - media3(N12 OISST), 2006-2025: sesgo={d2.mean():+.3f} max|Δ|={d2.abs().max():.2f} RMSE={np.sqrt((d2**2).mean()):.3f}")
c26 = pd.period_range("2026-01", "2026-08", freq="M")
print("2026: ICEN oficial vs trad 91-20 vs media3 N12 ERSST/OISST:\n", df.loc[c26, ["ICEN","ICEN_91_20","N12_ERSST_3m","N12_OISST_3m","ONI"]].round(2).to_string())

# Acuerdo de fases: cálido ICEN>0.5 vs ONI>=0.5
ss = sub[["ICEN", "ONI"]].dropna()
wi = ss.ICEN > 0.5; wo = ss.ONI >= 0.5
ci = ss.ICEN < -0.7; co = ss.ONI <= -0.5
print(f"Meses cálidos: ICEN={wi.sum()} ONI={wo.sum()} ambos={(wi&wo).sum()} solo ICEN={(wi&~wo).sum()} solo ONI={(~wi&wo).sum()} (n={len(ss)})")
print(f"Meses fríos:  ICEN={ci.sum()} ONI={co.sum()} ambos={(ci&co).sum()} solo ICEN={(ci&~co).sum()} solo ONI={(~ci&co).sum()}")

print("\n=== 4. Eventos 2017 y 2023-24 ===")
ev = df[["ICEN", "ONI", "N12_OISST_mens", "N12_OISST_3m", "N34_OISST_3m"]]
print(ev.loc[pd.Period("2016-10", "M"):pd.Period("2017-07", "M")].round(2).to_string())
print(ev.loc[pd.Period("2023-01", "M"):pd.Period("2024-06", "M")].round(2).to_string())
for y0, y1 in [("2017-01-01", "2017-05-31"), ("2023-01-01", "2024-06-30"), ("2026-01-01", "2026-12-31")]:
    w = wk.loc[y0:y1]
    print(f"Semanal N12 anom máx {y0[:4]}: {w.N12A.max():.1f} °C el {w.N12A.idxmax().date()} | semanas >=1.0: {(w.N12A>=1).sum()} | N34 máx {w.N34A.max():.1f}")
icen_max = {"2017": icen["2017"].max(), "2023-24": icen[pd.Period("2023-01","M"):pd.Period("2024-06","M")].max(), "1997-98": icen[pd.Period("1997-01","M"):pd.Period("1998-12","M")].max(), "1982-83": icen[pd.Period("1982-01","M"):pd.Period("1983-12","M")].max(), "2026": icen["2026"].max()}
print("Máximo ICEN por evento:", {k: round(v, 2) for k, v in icen_max.items()})
oni_ev = {"2017(DJF-MAM)": oni[pd.Period("2017-01","M"):pd.Period("2017-04","M")].max(), "2023-24": oni[pd.Period("2023-01","M"):pd.Period("2024-06","M")].max(), "2026": oni["2026"].max()}
print("Máximo ONI:", {k: round(v, 2) for k, v in oni_ev.items()})

print("\n=== 5. Último dato y rezago (a la fecha de descarga) ===")
print("ICEN último:", icen.index.max(), "| ICEN trad:", icen9120.index.max(), "| ONI último centro:", oni.index.max(),
      "| ERSST CPC:", ers.index.max(), "| OISST mensual:", ois.index.max(), "| semanal:", wk.index.max().date())
