"""Calidad SAIDI/SAIFI Osinergmin. Uso: q_saidi.py <csv>"""
import sys, pandas as pd, numpy as np
df = pd.read_csv(sys.argv[1], encoding="utf-8-sig")
print("filas", len(df), "| cols", list(df.columns))
print("AÑO:", df["AÑO"].min(), "->", df["AÑO"].max(), "| meses distintos:", df.MES.nunique(), "| rango MES:", df.MES.min(), df.MES.max())
print("empresas:", df.CODIGO_EMPRESA.nunique(), "| sistemas eléctricos:", df.COD_SIST_ELEC.nunique())
print("FECHA_CORTE únicas:", df.FECHA_CORTE.nunique(), df.FECHA_CORTE.unique()[:5])
dup = df.duplicated(["MES", "COD_SIST_ELEC"], keep=False)
print("duplicados (MES, sistema):", int(dup.sum()))
if dup.sum():
    print(df[dup].sort_values(["COD_SIST_ELEC", "MES"]).head(6).to_string())
cnt = df.groupby("MES").COD_SIST_ELEC.nunique()
print("sistemas por mes: min", cnt.min(), "max", cnt.max()); print(cnt.groupby(cnt.index // 100).agg(["min", "max", "count"]).to_string())
for c in ["SAIDI", "SAIFI"]:
    s = df[c]; print(f"{c}: NaN {int(s.isna().sum())} ceros {100*(s==0).mean():.1f}% negativos {int((s<0).sum())} p50 {s.median():.3f} p99 {s.quantile(.99):.2f} max {s.max():.1f}")
# ¿Mensual o acumulado? comparar diciembre vs suma de meses para un sistema grande
comp = (df.SAIDI - df.SAIDI_GEN - df.SAIDI_TRA - df.SAIDI_DIS).abs()
print("SAIDI != GEN+TRA+DIS (>0.01):", int((comp > 0.01).sum()))
g = df[df.NOMBRE_EMPRESA.str.contains("LUZ DEL SUR", na=False)]
print("Luz del Sur sistemas:", g.NOM_SIST_ELEC.unique()[:5])
s1 = g.groupby("MES").SAIDI.sum().tail(15); print(s1.round(3).to_string())
# serie mensual nacional (mediana por sistema)
m = df.groupby("MES").SAIDI.median()
print("mediana SAIDI por mes, por año (media de medianas):", m.groupby(m.index // 100).mean().round(3).to_dict())
