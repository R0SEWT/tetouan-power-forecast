"""Calidad de demanda por barras COES (export Excel mensual). Uso: q_barras.py <xlsx> [<xlsx> ...]"""
import sys
import pandas as pd, numpy as np

def load(p):
    raw = pd.read_excel(p, header=None)
    i = raw.index[raw[0].astype(str).str.startswith("PUNTO DE MEDIC")][0]
    meta = raw.iloc[i:i + 5].set_index(0).T
    meta.columns = ["punto", "empresa", "equipo", "kv", "subestacion"]
    body = raw.iloc[i + 5:].copy()
    body = body[body[0].notna()]
    ts = pd.to_datetime(body[0].astype(str), format="%d/%m/%Y %H:%M", errors="coerce")
    vals = body.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
    vals.columns = meta["punto"].astype(str).values
    vals.index = ts
    return meta.reset_index(drop=True), vals, int(ts.isna().sum())

for p in sys.argv[1:]:
    meta, v, bad_ts = load(p)
    print(f"\n===== {p.split('/')[-1]}")
    n_days = v.index.normalize().nunique()
    print(f"puntos={v.shape[1]} subestaciones={meta.subestacion.nunique()} filas={len(v)} (esperado {48*(n_days-1)}..) ts no parseables={bad_ts}")
    print("rango:", v.index.min(), "->", v.index.max(), "| duplicados ts:", int(v.index.duplicated().sum()))
    full = pd.date_range(v.index.min(), v.index.max(), freq="30min")
    print("faltantes en la grilla:", len(full.difference(v.index)))
    tot = v.size
    print(f"celdas NaN: {int(v.isna().sum().sum())} ({100*v.isna().sum().sum()/tot:.2f}%) | ceros: {int((v==0).sum().sum())} ({100*(v==0).sum().sum()/tot:.2f}%) | negativos: {int((v<0).sum().sum())}")
    allzero = (v.fillna(0) == 0).all()
    print("puntos 100% cero o vacíos:", int(allzero.sum()), "->", list(meta.loc[allzero.values, "equipo"].astype(str) + "@" + meta.loc[allzero.values, "subestacion"].astype(str))[:8])
    # tramos planos (mismo valor >= 4 periodos = 2h) en puntos no nulos
    nz = v.loc[:, ~allzero.values]
    flat = 0
    for c in nz:
        s = nz[c]
        g = (s != s.shift()).cumsum()
        run = s.groupby(g).transform("size")
        flat += int(((run >= 4) & (s != 0)).sum())
    print(f"celdas en tramos planos >=2h (no cero): {flat} ({100*flat/nz.size:.2f}%)")
    # saltos: cambio > 50% entre periodos en puntos con media > 5 MW
    big = nz.loc[:, nz.mean() > 5]
    r = (big.pct_change(fill_method=None).abs() > 0.5)
    print(f"puntos con media>5MW: {big.shape[1]} | saltos >50% en 30 min: {int(r.sum().sum())} (en {int((r.sum()>0).sum())} puntos)")
    tot_lds = v.sum(axis=1)
    print("demanda agregada empresa (MW): media %.1f, max %.1f, min %.1f" % (tot_lds.mean(), tot_lds.max(), tot_lds.min()))
    sub = v.T.groupby(meta.subestacion.str.strip().str.upper().values).sum().T
    print("subestaciones con media > 20 MW:", int((sub.mean() > 20).sum()), "| top5:", sub.mean().sort_values(ascending=False).head(5).round(1).to_dict())
    print("tensiones (kV):", meta.kv.value_counts().to_dict())
