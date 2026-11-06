"""Calidad de la demanda SEIN 30-min (COES ExportarDemanda). Uso: q_sein.py <dir_xlsx> <out_parquet_or_csv>"""
import sys, glob, os
import pandas as pd, numpy as np

d = sys.argv[1]; out = sys.argv[2]
frames = []
for f in sorted(glob.glob(os.path.join(d, "sein_*.xlsx"))):
    df = pd.read_excel(f, header=3)
    df.columns = [c.strip() for c in df.columns]
    df["archivo"] = os.path.basename(f)
    frames.append(df)
raw = pd.concat(frames, ignore_index=True)
print("filas crudas:", len(raw), "columnas:", list(raw.columns))
print("tipos:", raw.dtypes.to_dict())
raw = raw.dropna(subset=["FECHA"])
# Formato de fecha: 'dd/mm/yyyy HH:MM'; puede venir 24:00?
s = raw["FECHA"].astype(str)
print("ejemplos FECHA:", s.head(3).tolist(), "... horas únicas:", sorted(s.str[-5:].unique())[:3], sorted(s.str[-5:].unique())[-3:])
raw["ts"] = pd.to_datetime(s, format="%d/%m/%Y %H:%M", errors="coerce")
print("FECHA no parseadas:", raw["ts"].isna().sum())
for c in ["EJECUTADO", "PROG. DIARIA", "PROG. SEMANAL"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
dup = raw.duplicated("ts", keep=False)
print("timestamps duplicados (filas):", dup.sum())
if dup.sum():
    print(raw.loc[dup, ["ts", "EJECUTADO", "archivo"]].head(10))
df = raw.drop_duplicates("ts").set_index("ts").sort_index()
full = pd.date_range(df.index.min(), df.index.max(), freq="30min")
missing = full.difference(df.index)
print(f"rango: {df.index.min()} -> {df.index.max()}  esperados={len(full)} presentes={len(df)} faltantes={len(missing)}")
if len(missing):
    m = pd.Series(1, index=missing)
    print("faltantes por año:", m.groupby(m.index.year).sum().to_dict())
    print("primeros faltantes:", list(missing[:10]))
df = df.reindex(full)
y = df["EJECUTADO"]
print("NaN en EJECUTADO:", int(y.isna().sum()), "| ceros:", int((y == 0).sum()), "| negativos:", int((y < 0).sum()))
print("NaN por año:", y.isna().groupby(y.index.year).sum().astype(int).to_dict())
print("NaN PROG. DIARIA:", int(df["PROG. DIARIA"].isna().sum()), "| NaN PROG. SEMANAL:", int(df["PROG. SEMANAL"].isna().sum()))
# Resumen anual
ann = pd.DataFrame({
    "media_MW": y.groupby(y.index.year).mean(),
    "max_MW": y.groupby(y.index.year).max(),
    "min_MW": y.groupby(y.index.year).min(),
    "energia_GWh": y.groupby(y.index.year).sum() * 0.5 / 1000,
})
ann["ts_max"] = y.groupby(y.index.year).idxmax()
print("\nResumen anual:\n", ann.round(1).to_string())
# Atípicos: salto relativo entre periodos consecutivos y desvío vs misma hora semana pasada
r = y.pct_change(fill_method=None)
print("\n|salto 30min| > 5%:", int((r.abs() > 0.05).sum()), " >10%:", int((r.abs() > 0.10).sum()))
print("top 10 saltos:\n", r.abs().sort_values(ascending=False).head(10).round(3).to_string())
w = (y / y.shift(336) - 1)
print("|desvío vs semana pasada| > 20%:", int((w.abs() > 0.20).sum()))
# Atípicos robustos: residuo vs mediana móvil 1 día, MAD
med = y.rolling(48, center=True, min_periods=24).median()
res = y - med
mad = (res - res.rolling(48*7, center=True, min_periods=48).median()).abs().rolling(48*7, center=True, min_periods=48).median()
z = 0.6745 * (res) / mad
print("|z robusto| > 6:", int((z.abs() > 6).sum()))
print(" ejemplos:", z.abs().sort_values(ascending=False).head(8).round(1).to_dict())
# Pronóstico oficial COES vs ejecutado y referencias ingenuas
def mape(a, b):
    m = a.notna() & b.notna()
    return float((abs(a[m] - b[m]) / a[m]).mean() * 100)
print("\nMAPE % por año (ejecutado vs ...):")
rows = []
for yr, g in df.groupby(df.index.year):
    yy = g["EJECUTADO"]
    rows.append({"año": yr,
                 "prog_diaria": mape(yy, g["PROG. DIARIA"]),
                 "prog_semanal": mape(yy, g["PROG. SEMANAL"]),
                 "persist_1h": mape(yy, y.shift(2).loc[g.index]),
                 "ayer_mismo": mape(yy, y.shift(48).loc[g.index]),
                 "semana_pas": mape(yy, y.shift(336).loc[g.index])})
print(pd.DataFrame(rows).round(2).to_string(index=False))
# Eventos
for name, a, b in [("COVID cuarentena", "2020-03-01", "2020-04-30"), ("Niño Costero 2017", "2017-01-15", "2017-04-30"),
                   ("Niño Costero 2023 (Yaku)", "2023-02-15", "2023-05-31")]:
    g = y.loc[a:b].resample("W").mean()
    g0 = y.loc[str(int(a[:4]) - 1) + a[4:]: str(int(b[:4]) - 1) + b[4:]].resample("W").mean()
    print(f"\n{name}: media semanal (MW) y variación vs mismo periodo año anterior")
    print(pd.DataFrame({"MW": g.round(0).values, "vs_año_ant_%": ((g.values / g0.values[:len(g)] - 1) * 100).round(1) if len(g0) >= len(g) else None}, index=g.index.date).to_string())
df.index.name = "ts"
df[["EJECUTADO", "PROG. DIARIA", "PROG. SEMANAL"]].to_csv(out)
print("\nescrito", out)
