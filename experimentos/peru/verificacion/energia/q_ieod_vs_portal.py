"""Compara demanda SEIN del IEOD (DEMANDA_AREAS) con el 'Ejecutado' del portal. Uso: q_ieod_vs_portal.py <anexo.xlsx> <sein_csv> <YYYY-MM-DD>"""
import sys, re, datetime as dt
import pandas as pd, openpyxl
anexo, csv, day = sys.argv[1], sys.argv[2], sys.argv[3]
wb = openpyxl.load_workbook(anexo, read_only=True, data_only=True)
ws = wb["DEMANDA_AREAS"]
rows = list(ws.iter_rows(values_only=True))
hdr_i = next(i for i, r in enumerate(rows) if r and any(isinstance(x, str) and x.strip() == "SEIN" for x in r))
hdr = [str(x).strip() if x is not None else None for x in rows[hdr_i]][1:]
data = []
for r in rows[hdr_i + 1:]:
    r = r[1:]
    if not r or r[0] is None: continue
    t = r[0]
    if isinstance(t, str):
        if not re.match(r"^\d{1,2}:\d{2}", t.strip()): continue
        hh, mm = map(int, t.split(":")[:2])
    elif isinstance(t, dt.time): hh, mm = t.hour, t.minute
    elif isinstance(t, dt.datetime): hh, mm = t.hour, t.minute
    else: continue
    ts = pd.Timestamp(day) + pd.Timedelta(hours=hh, minutes=mm)
    if hh == 0 and mm == 0: ts += pd.Timedelta(days=1)
    data.append([ts] + list(r[1:]))
cols = ["ts"] + [h if h else f"c{i}" for i, h in enumerate(hdr[1:], 1)]
n = min(len(cols), len(data[0])); data = [d[:n] for d in data]
ie = pd.DataFrame(data, columns=cols[:n]).set_index("ts")
print("columnas IEOD:", list(ie.columns)); print("filas IEOD:", len(ie), ie.index.min(), ie.index.max())
po = pd.read_csv(csv, index_col=0, parse_dates=True)
j = ie[["SEIN"]].join(po["EJECUTADO"], how="inner").astype(float)
j["dif"] = j["EJECUTADO"] - j["SEIN"]; j["dif_%"] = 100 * j["dif"] / j["SEIN"]
print(j.describe().round(2).to_string())
areas = [c for c in ["NORTE", "CENTRO", "SUR"] if c in ie.columns]
s = ie[areas].astype(float).sum(axis=1)
print("max |NORTE+CENTRO+SUR - SEIN| (MW):", float((s - ie["SEIN"].astype(float)).abs().max()))
print("energía día IEOD (MWh):", round(float(ie['SEIN'].astype(float).sum() * 0.5), 1), "| portal:", round(float(j['EJECUTADO'].sum() * 0.5), 1))
