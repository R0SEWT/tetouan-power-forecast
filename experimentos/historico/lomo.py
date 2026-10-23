"""Verano: origen móvil (cota pesimista) frente a mes fuera con margen (cota optimista).

Ver docs/historico.md, «Cómo estimar el desempeño en la temporada que la prueba no cubre».
Uso: python -m experimentos.historico.lomo
"""

import numpy as np
import pandas as pd

from experimentos.historico import rolling as R

BUFFER = 144  # un día de margen a cada lado del mes evaluado


def main():
    df = R.base_frame()
    filas = []
    for zona in (3, 1):
        serie, otras = R.ZC[zona], [R.ZC[z] for z in (1, 2, 3) if z != zona]
        prep = {vn: R.features(df, serie, otras, R.VARIANTES[vn]) for vn in ("V0_repo_nivel", "V4_ratio_m24")}
        valid = np.ones(len(df), bool)
        for X, yobj, _, base in prep.values():
            valid &= X.notna().all(axis=1).to_numpy() & yobj.notna().to_numpy()
            valid &= base[["semana", "ayer"]].notna().all(axis=1).to_numpy()
        idx = np.where(valid)[0]
        fechas = df["DateTime"].iloc[idx].reset_index(drop=True)
        for m in (7, 8):
            ini, fin = pd.Timestamp(2017, m, 1), pd.Timestamp(2017, m + 1, 1)
            te = np.where((fechas >= ini) & (fechas < fin))[0]
            lo, hi = te.min() - BUFFER, te.max() + BUFFER
            tr = np.r_[np.arange(0, lo), np.arange(hi + 1, len(idx))]
            for vn, (X, yobj, yt, base) in prep.items():
                Xv, yo, ytv, bv = X.iloc[idx], yobj.iloc[idx], yt.iloc[idx], base.iloc[idx]
                mdl = R.modelo().fit(Xv.iloc[tr], yo.iloc[tr])
                p = R.reconstruir(R.VARIANTES[vn], mdl.predict(Xv.iloc[te]), bv.iloc[te])
                filas.append({"serie": f"Z{zona}", "mes": m, "esquema": "mes_fuera_con_buffer",
                              "metodo": vn, **R._errores(ytv.iloc[te].to_numpy(), p)})
            print(zona, m, "ok", flush=True)
    R.guardar(pd.DataFrame(filas), "resultados_lomo.csv")


if __name__ == "__main__":
    main()
