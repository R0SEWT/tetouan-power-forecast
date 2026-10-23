"""Validación externa en Ceuta: ¿cuánto histórico hace falta para pronosticar un verano a una hora?

Para cada verano (julio y agosto) de 2020 a 2026 se entrena con cuatro historias distintas, todas
terminadas el 30 de junio de ese año, y se evalúa el verano:

- `sin_verano`: enero a junio del mismo año. Es la situación de Tetuán: el modelo nunca vio un verano.
- `1_anio`, `2_anios`, `3_anios`: los 12, 24 o 36 meses anteriores, que incluyen uno, dos o tres veranos.

Se comparan el modelo en nivel con calendario anual (V0 de docs/historico.md), el objetivo en razón sin
calendario anual (V4) y las tres referencias ingenuas. El verano de 2020, con el confinamiento, se reporta
aparte. Lee el silver de Ceuta y guarda resultados_validacion.csv en <datos>/reportes/ceuta/.

Uso: python -m experimentos.ceuta.validacion
"""

import time

import numpy as np
import pandas as pd

from experimentos.historico import rolling as R
from tetouan_power_forecast.ceuta import SERIE, cargar_silver_ceuta, huecos_cortos_rellenos

# Ramadán en Ceuta (calendario marroquí y español, aproximado a ±1 día). Sin feriados: no hay una lista
# verificada de los de Ceuta, así que la variable queda en 0.
RAMADANES = [
    ("2019-05-06", "2019-06-04"), ("2020-04-24", "2020-05-23"), ("2021-04-13", "2021-05-12"),
    ("2022-04-02", "2022-05-01"), ("2023-03-23", "2023-04-20"), ("2024-03-11", "2024-04-09"),
    ("2025-03-01", "2025-03-30"), ("2026-02-18", "2026-03-19"),
]
VARIANTES = {"V0_nivel_con_anual": R.VARIANTES["V0_repo_nivel"], "V4_razon_sin_anual": R.VARIANTES["V4_ratio_m24"]}
HISTORIAS = {"sin_verano": None, "1_anio": 1, "2_anios": 2, "3_anios": 3}
VERANOS = range(2020, 2027)


def ventanas(fechas, anio):
    """Índices de entrenamiento por historia y de prueba (julio y agosto) para un verano."""
    inicio_prueba = pd.Timestamp(anio, 7, 1)
    prueba = np.where((fechas >= inicio_prueba) & (fechas < pd.Timestamp(anio, 9, 1)))[0]
    corte = inicio_prueba - pd.Timedelta(minutes=10 * R.H)  # ningún objetivo t+6 del entrenamiento en julio
    entrenamiento = {}
    for nombre, anios in HISTORIAS.items():
        desde = pd.Timestamp(anio, 1, 1) if anios is None else inicio_prueba - pd.DateOffset(years=anios)
        tr = np.where((fechas >= desde) & (fechas < corte))[0]
        if len(tr) and fechas[tr[0]] - desde <= pd.Timedelta(days=7):  # la historia está completa
            entrenamiento[nombre] = tr
    return entrenamiento, prueba


def main():
    t0 = time.time()
    df = cargar_silver_ceuta().sort_values("DateTime").reset_index(drop=True)
    df[SERIE] = huecos_cortos_rellenos(df[SERIE])
    prep = {vn: R.features(df, SERIE, [], v, feriados=[], ramadanes=RAMADANES) for vn, v in VARIANTES.items()}
    valid = np.ones(len(df), bool)
    for X, yobj, _, base in prep.values():
        valid &= X.notna().all(axis=1).to_numpy() & yobj.notna().to_numpy()
        valid &= base[["semana", "ayer"]].notna().all(axis=1).to_numpy()
    idx = np.where(valid)[0]
    fechas = df["DateTime"].iloc[idx].reset_index(drop=True)
    filas = []
    for anio in VERANOS:
        entrenamiento, te = ventanas(fechas, anio)
        if not len(te):
            continue
        _, _, yt, base = prep["V4_razon_sin_anual"]
        real = yt.iloc[idx].iloc[te].to_numpy()
        for referencia in ["persistencia", "ayer", "semana"]:
            filas.append({"verano": anio, "historia": "-", "metodo": "naive_" + referencia, "filas_train": 0,
                          **R._errores(real, base.iloc[idx].iloc[te][referencia].to_numpy())})
        for historia, tr in entrenamiento.items():
            for vn, v in VARIANTES.items():
                X, yobj, yt, base = prep[vn]
                Xv, yo, bv = X.iloc[idx], yobj.iloc[idx], base.iloc[idx]
                modelo = R.modelo().fit(Xv.iloc[tr], yo.iloc[tr])
                p = R.reconstruir(v, modelo.predict(Xv.iloc[te]), bv.iloc[te])
                filas.append({"verano": anio, "historia": historia, "metodo": vn, "filas_train": len(tr),
                              **R._errores(real, p)})
            print(anio, historia, "ok", flush=True)
    resultados = pd.DataFrame(filas)
    R.guardar(resultados, "resultados_validacion.csv", carpeta="ceuta")
    sin_2020 = resultados[resultados["verano"] != 2020]
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print("\nMAPE (%) medio de los veranos 2021 en adelante:")
        print(sin_2020.pivot_table(index="historia", columns="metodo", values="MAPE", aggfunc="mean").round(2))
    print("segundos:", round(time.time() - t0))


if __name__ == "__main__":
    main()
