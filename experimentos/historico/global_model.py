"""Modelo global (tres zonas apiladas) frente a uno local, con el objetivo en razón (docs/historico.md, opción 2).

Uso: python -m experimentos.historico.global_model
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from experimentos.historico import rolling as R

V = {"anual": False, "extra": True, "objetivo": "ratio"}


def main():
    df = R.base_frame()
    prep = {}
    for z in (1, 2, 3):
        X, yobj, yt, base = R.features(df, R.ZC[z], [], V)  # solo variables de la propia zona
        X = X.rename(columns=lambda c, z=z: c.replace(R.ZC[z], "own"))
        X["zona"] = z
        prep[z] = (X, yobj, yt, base)
    valid = np.ones(len(df), bool)
    for X, yobj, _, _ in prep.values():
        valid &= X.notna().all(axis=1).to_numpy() & yobj.notna().to_numpy()
    idx = np.where(valid)[0]
    fechas = df["DateTime"].iloc[idx].reset_index(drop=True)
    filas = []
    for fold, tr, te in R.plegados(fechas):
        Xg = pd.concat([prep[z][0].iloc[idx].iloc[tr] for z in (1, 2, 3)])
        yg = pd.concat([prep[z][1].iloc[idx].iloc[tr] for z in (1, 2, 3)])
        categorica = [c == "zona" for c in Xg.columns]
        global_ = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, early_stopping=False,
                                                random_state=0, categorical_features=categorica).fit(Xg, yg)
        for z in (1, 2, 3):
            X, yobj, yt, base = prep[z]
            Xv, yo, ytv, bv = X.iloc[idx], yobj.iloc[idx], yt.iloc[idx], base.iloc[idx]
            real = ytv.iloc[te].to_numpy()
            escala = bv["m24"].iloc[te].to_numpy()
            local = R.modelo().fit(Xv.iloc[tr].drop(columns="zona"), yo.iloc[tr])
            predicciones = {
                "local_propia": escala * local.predict(Xv.iloc[te].drop(columns="zona")),
                "global_3zonas": escala * global_.predict(Xv.iloc[te]),
            }
            for nombre, p in predicciones.items():
                filas.append({"serie": f"Z{z}", "fold": fold, "metodo": nombre, **R._errores(real, p)})
        print(fold, "ok", flush=True)
    R.guardar(pd.DataFrame(filas), "resultados_global.csv")


if __name__ == "__main__":
    main()
