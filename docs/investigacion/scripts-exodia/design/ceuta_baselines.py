"""Naive baselines (incl. persistence + daily/weekly delta) for Ceuta Jul-Aug 2022-2026, t+6 at 10 min."""
import json, re, sys
from pathlib import Path
import numpy as np, pandas as pd
carpeta = Path(sys.argv[1])
DOC = {  # docs/historico.md table: best naive, V4 sin_verano, V4 1 año, V4 3 años
 2022: (4.58, 2.71, 2.40, 2.31), 2023: (4.84, 2.10, 1.85, 1.74), 2024: (4.47, 2.72, 2.00, 1.91),
 2025: (4.60, 1.92, 1.67, 1.49), 2026: (4.64, 2.12, 1.70, 1.62)}
filas = []
for anio in range(2022, 2027):
    partes = []
    for l in (carpeta / f"{anio}.jsonl").read_text().splitlines():
        txt = json.loads(l)["respuesta"]
        m = re.search(r"\((\{.*\})\)", txt, re.DOTALL)
        v = json.loads(m.group(1)).get("valoresHorariosGeneracion") or []
        partes.append(pd.DataFrame(v)[["ts", "dem"]])
    d = pd.concat(partes)
    loc = pd.to_datetime(d["ts"], format="%Y-%m-%d %H:%M")
    d["DateTime"] = loc.dt.tz_localize("Europe/Madrid").dt.tz_convert("UTC").dt.tz_localize(None)
    s = d.drop_duplicates("DateTime").set_index("DateTime")["dem"].sort_index()
    y = s.resample("10min").mean()
    y = y.reindex(pd.date_range(y.index.min(), y.index.max(), freq="10min"))
    nan_raw = int(y.isna().sum())
    y = y.interpolate(limit=6, limit_area="inside")
    H = 6
    yt = y.shift(-H)
    base = pd.DataFrame({
        "persistencia": y, "ayer": y.shift(144 - H), "semana": y.shift(1008 - H),
        "delta_diario": y + y.shift(144 - H) - y.shift(144),
        "delta_semanal": y + y.shift(1008 - H) - y.shift(1008),
        "media_deltas": y + 0.5 * ((y.shift(144 - H) - y.shift(144)) + (y.shift(1008 - H) - y.shift(1008))),
    })
    ok = (y.index >= pd.Timestamp(anio, 7, 1)) & (y.index < pd.Timestamp(anio, 9, 1)) & yt.notna().to_numpy() & base.notna().all(axis=1).to_numpy()
    r = yt[ok].to_numpy()
    fila = {"verano": anio, "n": int(ok.sum()), "nan10min": nan_raw, "min_dem": float(y.min())}
    for c in base:
        p = base.loc[ok, c].to_numpy()
        fila[c] = 100 * np.mean(np.abs(r - p) / r)
        fila["MAE_" + c] = 1000 * np.mean(np.abs(r - p))
    b, v4s, v41, v43 = DOC[anio]
    fila.update(doc_mejor_ingenua=b, doc_V4_sin_verano=v4s, doc_V4_1anio=v41, doc_V4_3anios=v43)
    filas.append(fila)
t = pd.DataFrame(filas).set_index("verano")
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
cols = ["n", "nan10min", "persistencia", "ayer", "semana", "delta_diario", "delta_semanal", "media_deltas",
        "doc_mejor_ingenua", "doc_V4_sin_verano", "doc_V4_1anio", "doc_V4_3anios"]
print(t[cols].round(2))
print("\nmean 2022-2026:"); print(t[cols[2:]].mean().round(2))
print("\nMAE kW:"); print(t[[c for c in t if c.startswith("MAE_")]].round(0))
