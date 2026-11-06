"""Calidad CMg nodales COES (ExportarMasivo). Uso: q_cmg.py <xlsx>"""
import sys, pandas as pd
df = pd.read_excel(sys.argv[1], header=4).iloc[:, 1:]
df.columns = ["fecha", "nodo", "barra", "energia", "congestion", "total"]
df = df.dropna(subset=["fecha"])
df["ts"] = pd.to_datetime(df.fecha.astype(str), format="%d/%m/%Y %H:%M", errors="coerce")
print("filas", len(df), "| ts no parseables", int(df.ts.isna().sum()), "| barras", df.nodo.nunique(), "| rango", df.ts.min(), "->", df.ts.max())
cnt = df.groupby("nodo").size(); print("periodos por barra: min", cnt.min(), "max", cnt.max(), "mediana", cnt.median())
print("duplicados (nodo, ts):", int(df.duplicated(["nodo", "ts"]).sum()))
for c in ["energia", "congestion", "total"]:
    s = pd.to_numeric(df[c], errors="coerce")
    print(f"{c}: NaN {int(s.isna().sum())} ceros {int((s==0).sum())} negativos {int((s<0).sum())} min {s.min():.2f} p50 {s.median():.2f} p99 {s.quantile(.99):.2f} max {s.max():.2f}")
print("periodos con congestión != 0:", int((pd.to_numeric(df.congestion) != 0).sum()), "en", df.loc[pd.to_numeric(df.congestion) != 0, "nodo"].nunique(), "barras")
p = df.pivot_table(index="ts", columns="nodo", values="total")
print("dispersión entre barras (CV mediano por instante):", round(float((p.std(axis=1) / p.mean(axis=1)).median()), 3))
ref = [c for c in p.columns if "SANTAROSA" in c.replace(" ", "").upper()][:1]
if ref:
    s = p[ref[0]]; print("barra ref", ref[0], "media", round(s.mean(), 2), "S/./MWh? min", round(s.min(), 2), "max", round(s.max(), 2))
    d = s.groupby(s.index.date).agg(["mean", "max", "min"]).round(1); print(d.to_string())
