"""Efecto de la transferencia de carga del 25-oct y del reentrenamiento semanal en la prueba.

Ver docs/historico.md, opción 4. Uso: python -m experimentos.historico.quiebre
"""

import numpy as np
import pandas as pd

from experimentos.historico import rolling as R

VARS = {
    "V0_repo_nivel": R.VARIANTES["V0_repo_nivel"],
    "V4_ratio_m24": R.VARIANTES["V4_ratio_m24"],
    "V5_ratio+anual": {"anual": True, "extra": True, "objetivo": "ratio"},
}
VENTANAS = [("01-24 oct", "2017-10-01", "2017-10-25 11:00"),
            ("25 oct-05 nov", "2017-10-25 11:00", "2017-11-06"),
            ("06 nov-30 dic", "2017-11-06", "2018-01-01")]
H = R.H


def mape(real, p):
    return 100 * np.mean(np.abs(real - p) / real)


def main():
    df = R.base_frame()
    fechas_all = df["DateTime"]
    filas = []
    for sn, (serie, otras) in R.SERIES.items():
        prep = {vn: R.features(df, serie, otras, v) for vn, v in VARS.items()}
        valid = np.ones(len(df), bool)
        for X, yobj, _, _ in prep.values():
            valid &= X.notna().all(axis=1).to_numpy() & yobj.notna().to_numpy()
        idx = np.where(valid)[0]
        f = fechas_all.iloc[idx].reset_index(drop=True)
        ini_test = fechas_all.iloc[int(len(df) * 0.85)]  # inicio de la prueba sobre el frame completo
        for vn, (X, yobj, yt, base) in prep.items():
            Xv, yo = X.iloc[idx].reset_index(drop=True), yobj.iloc[idx].reset_index(drop=True)
            ytv, bv = yt.iloc[idx].reset_index(drop=True), base.iloc[idx].reset_index(drop=True)
            v = VARS[vn]
            # (1) Entrenado hasta el 1-oct y evaluado antes y después del quiebre, sin reentrenar
            corte = pd.Timestamp("2017-10-01")
            tr = np.where(f < corte - pd.Timedelta(minutes=10 * H))[0]
            mdl = R.modelo().fit(Xv.iloc[tr], yo.iloc[tr])
            for nombre, a, b in VENTANAS:
                te = np.where((f >= a) & (f < b))[0]
                p = R.reconstruir(v, mdl.predict(Xv.iloc[te]), bv.iloc[te])
                filas.append({"serie": sn, "metodo": vn, "esquema": "entrenado hasta 1-oct",
                              "ventana": nombre, "MAPE": mape(ytv.iloc[te].to_numpy(), p)})
            # (2) Prueba: un solo ajuste frente a reentrenar cada semana (1008 pasos)
            te_all = np.where(f >= ini_test)[0]
            tr = np.where(f < ini_test - pd.Timedelta(minutes=10 * H))[0]
            mdl = R.modelo().fit(Xv.iloc[tr], yo.iloc[tr])
            p1 = R.reconstruir(v, mdl.predict(Xv.iloc[te_all]), bv.iloc[te_all])
            ps = np.empty(len(te_all))
            for k in range(0, len(te_all), 1008):
                bloque = te_all[k:k + 1008]
                trk = np.where(f < f.iloc[bloque[0]] - pd.Timedelta(minutes=10 * H))[0]
                mk = R.modelo().fit(Xv.iloc[trk], yo.iloc[trk])
                ps[k:k + len(bloque)] = R.reconstruir(v, mk.predict(Xv.iloc[bloque]), bv.iloc[bloque])
            real = ytv.iloc[te_all].to_numpy()
            filas.append({"serie": sn, "metodo": vn, "esquema": "prueba oficial", "ventana": "un ajuste",
                          "MAPE": mape(real, p1)})
            filas.append({"serie": sn, "metodo": vn, "esquema": "prueba oficial",
                          "ventana": "reentreno semanal", "MAPE": mape(real, ps)})
            print(sn, vn, "ok", flush=True)
        # Referencias "semana pasada" y "ayer" en las mismas ventanas
        _, _, yt, base = prep["V0_repo_nivel"]
        bv, ytv = base.iloc[idx].reset_index(drop=True), yt.iloc[idx].reset_index(drop=True)
        for nombre, a, b in VENTANAS:
            te = np.where((f >= a) & (f < b))[0]
            for bn in ["semana", "ayer"]:
                filas.append({"serie": sn, "metodo": "naive_" + bn, "esquema": "entrenado hasta 1-oct",
                              "ventana": nombre,
                              "MAPE": mape(ytv.iloc[te].to_numpy(), bv[bn].iloc[te].to_numpy())})
    R.guardar(pd.DataFrame(filas), "resultados_quiebre.csv")


if __name__ == "__main__":
    main()
