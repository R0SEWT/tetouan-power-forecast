"""Resumen de eventos COES (ExportarEvento). Uso: q_eventos.py <xlsx>..."""
import sys, pandas as pd
for f in sys.argv[1:]:
    raw = pd.read_excel(f, header=None)
    i = raw.index[raw[1].astype(str).str.strip() == "Empresa"][0]
    df = raw.iloc[i + 1:, 1:8]; df.columns = ["empresa", "ubicacion", "familia", "equipo", "inicio", "final", "descripcion"]
    df = df.dropna(subset=["inicio"])
    df["inicio"] = pd.to_datetime(df.inicio, dayfirst=True, errors="coerce"); df["final"] = pd.to_datetime(df.final, dayfirst=True, errors="coerce")
    dur = (df.final - df.inicio).dt.total_seconds() / 60
    print(f"== {f.split('/')[-1]}: eventos {len(df)} | inicio NaT {int(df.inicio.isna().sum())} | final NaT {int(df.final.isna().sum())} | duración<0 {int((dur<0).sum())}")
    print("   duración min (mediana, p90):", round(dur.median(), 1), round(dur.quantile(.9), 1), "| duplicados:", int(df.duplicated(["empresa", "equipo", "inicio"]).sum()))
    print("   por mes:", df.groupby(df.inicio.dt.month).size().to_dict())
    print("   familias top:", df.familia.value_counts().head(5).to_dict())
    print("   con 'MW' en descripción (carga interrumpida):", int(df.descripcion.astype(str).str.contains(r"\bMW\b", regex=True).sum()))
