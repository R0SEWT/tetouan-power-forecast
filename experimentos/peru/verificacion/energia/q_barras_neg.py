"""Detalle de negativos y mínimos en export de barras. Uso: q_barras_neg.py <xlsx>"""
import sys
import pandas as pd
raw = pd.read_excel(sys.argv[1], header=None)
i = raw.index[raw[0].astype(str).str.startswith("PUNTO DE MEDIC")][0]
meta = raw.iloc[i:i + 5].set_index(0).T; meta.columns = ["punto", "empresa", "equipo", "kv", "subestacion"]
body = raw.iloc[i + 5:]; body = body[body[0].notna()]
v = body.iloc[:, 1:].apply(pd.to_numeric, errors="coerce"); v.index = pd.to_datetime(body[0].astype(str), format="%d/%m/%Y %H:%M")
v.columns = (meta.equipo.astype(str) + "@" + meta.subestacion.astype(str)).values
neg = (v < 0).sum().sort_values(ascending=False)
print("puntos con negativos:", int((neg > 0).sum())); print(neg[neg > 0].head(8).to_string())
for c in neg[neg > 0].head(3).index:
    print(c, "min", v[c].min(), "media", round(v[c].mean(), 2), "% neg", round(100 * (v[c] < 0).mean(), 1))
tot = v.sum(axis=1)
t = tot.idxmin(); print("\nmínimo agregado en", t, round(tot.min(), 1), "| ceros en ese instante:", int((v.loc[t] == 0).sum()), "de", v.shape[1])
print(tot.loc[t - pd.Timedelta(hours=2): t + pd.Timedelta(hours=2)].round(1).to_string())
