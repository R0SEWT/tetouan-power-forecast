"""Delta baselines on the exact rows of notebook 02 (dataset_razon + gold partition)."""
import sys
import numpy as np, pandas as pd
CSV = sys.argv[1]
H, D, W = 6, 144, 1008
ZON = ["Zone 1 Power Consumption", "Zone 2 Power Consumption", "Zone 3 Power Consumption"]
df = pd.read_csv(CSV)
df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)
df["DateTime"] = pd.to_datetime(df["DateTime"], format="%m/%d/%Y %H:%M")
df = df.sort_values("DateTime").reset_index(drop=True)
# gold zone 1 rows: needs shift(138), target shift(-6), rolling 6 -> dropna
y1 = df[ZON[0]]
g = pd.DataFrame({"DateTime": df["DateTime"], "a": y1.shift(D - H), "b": y1.shift(-H), "c": y1.rolling(6).std(),
                  "d": df[ZON[1]].shift(6), "e": df[ZON[2]].shift(6)}).dropna().reset_index(drop=True)
n = len(g); ft, fv = int(n * .7), int(n * .85)
lab = np.array(["entrenamiento"] * ft + ["validacion"] * (fv - ft) + ["prueba"] * (n - fv), dtype=object)
for f in (ft, fv): lab[f - H:f] = "hueco"
part = pd.Series(lab, index=g["DateTime"])
print("gold rows", n, "test starts", g.loc[fv, "DateTime"])

def mae(a, b): return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))
def mape(a, b): a = np.asarray(a); return float(100 * np.mean(np.abs(a - np.asarray(b)) / a))

rows, monthly = [], []
for z in (1, 2, 3):
    y = df[ZON[z - 1]]
    d = pd.DataFrame({
        "DateTime": df["DateTime"], "real": y.shift(-H),
        "persistencia": y, "ayer": y.shift(D - H), "semana_pasada": y.shift(W - H),
        "delta_diario": y + (y.shift(D - H) - y.shift(D)),
        "delta_semanal": y + (y.shift(W - H) - y.shift(W)),
        "need": y.rolling(W).mean() + y.shift(W),
    })
    # also average of the two deltas
    d["delta_prom"] = (d["delta_diario"] + d["delta_semanal"]) / 2
    d = d.dropna().reset_index(drop=True)
    d["particion"] = d["DateTime"].map(part)
    assert d["particion"].notna().all()
    for p in ("validacion", "prueba"):
        s = d[d["particion"] == p]
        for m in ("persistencia", "ayer", "semana_pasada", "delta_diario", "delta_semanal", "delta_prom"):
            r = s["real"]; pr = s[m]
            r2 = 1 - np.sum((r - pr) ** 2) / np.sum((r - r.mean()) ** 2)
            rows.append({"zona": z, "tramo": p, "n": len(s), "metodo": m, "MAE": mae(r, pr), "MAPE": mape(r, pr), "R2": r2})
        if p == "prueba":
            pico = ((s["DateTime"] + pd.Timedelta(minutes=60)).dt.hour.between(19, 22))
            for m in ("semana_pasada", "ayer", "delta_diario", "delta_semanal"):
                rows.append({"zona": z, "tramo": "prueba_pico", "n": int(pico.sum()), "metodo": m,
                             "MAE": mae(s["real"][pico], s[m][pico]), "MAPE": np.nan, "R2": np.nan})
    # monthly months Mar-Oct over desarrollo (< test start - 1h)
    ini = d.loc[d["particion"] == "prueba", "DateTime"].min()
    dev = d[d["DateTime"] < ini - pd.Timedelta(hours=1)]
    for mes, s in dev.groupby(dev["DateTime"].dt.to_period("M")):
        if mes.month < 3: continue
        rec = {"zona": z, "mes": str(mes)}
        for m in ("persistencia", "ayer", "semana_pasada", "delta_diario", "delta_semanal"):
            rec[m] = mae(s["real"], s[m])
        rec["mejor_3ref"] = min(rec["persistencia"], rec["ayer"], rec["semana_pasada"])
        monthly.append(rec)
    # transfer windows on validation (as nb02 cell 31)
    va = d[d["particion"] == "validacion"]
    for et, f in [("antes", va["DateTime"] < "2017-10-25"), ("despues", va["DateTime"] >= "2017-10-26")]:
        s = va[f]
        rows.append({"zona": z, "tramo": f"val_{et}_25oct", "n": len(s), "metodo": "delta_diario", "MAE": mae(s["real"], s["delta_diario"]), "MAPE": mape(s["real"], s["delta_diario"]), "R2": np.nan})
        rows.append({"zona": z, "tramo": f"val_{et}_25oct", "n": len(s), "metodo": "delta_semanal", "MAE": mae(s["real"], s["delta_semanal"]), "MAPE": mape(s["real"], s["delta_semanal"]), "R2": np.nan})
pd.set_option("display.width", 200)
R = pd.DataFrame(rows)
print(R.pivot_table(index=["tramo", "metodo"], columns="zona", values="MAE").round(1))
print(R[R.tramo.isin(["validacion", "prueba"])].pivot_table(index=["tramo", "metodo"], columns="zona", values=["MAPE", "R2"]).round(3))
M = pd.DataFrame(monthly)
print(M.round(0).to_string())
