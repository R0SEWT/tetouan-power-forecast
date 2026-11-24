"""Reproduce las tablas descriptivas de Tetuán y Ceuta para TB1."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from experimentos.ceuta import validacion as ceuta
from experimentos.historico import rolling as R
from tetouan_power_forecast.ceuta import (
    SERIE,
    cargar_silver_ceuta,
    huecos_cortos_rellenos,
)
from tetouan_power_forecast.referencias import referencias

PASO = pd.Timedelta(minutes=10)
HORIZONTE = 6 * PASO


def evaluar(serie, ventana, demanda, predicciones):
    origen = pd.DatetimeIndex(predicciones.index)
    objetivo = origen + HORIZONTE
    base = referencias(demanda, origen, objetivo, PASO).droplevel("objetivo")
    real_observado = demanda.reindex(objetivo).to_numpy()
    hay_real = np.isfinite(real_observado)
    if not np.allclose(
        real_observado[hay_real], predicciones.loc[hay_real, "real"], rtol=0, atol=0.001,
    ):
        raise ValueError(f"El real guardado no coincide con el objetivo en {serie} {ventana}")
    guardadas = predicciones.drop(columns="real")
    if "persistencia" in guardadas:
        if not np.allclose(guardadas["persistencia"], base["persistencia"], rtol=0, atol=0.001):
            raise ValueError(f"La persistencia guardada no coincide con el origen en {serie}")
        guardadas = guardadas.drop(columns="persistencia")
    metodos = guardadas.join(base, validate="one_to_one")
    validas = hay_real & np.isfinite(metodos).all(axis=1).to_numpy()
    real = real_observado[validas]
    if not len(real):
        raise ValueError(f"Sin filas emparejadas en {serie} {ventana}")
    errores = metodos[validas].sub(real, axis=0).abs()
    mae = errores.mean()
    positivo = real > 0
    mape = errores[positivo].div(real[positivo], axis=0).mean() * 100
    if {"ayer", "semana_pasada"} <= set(metodos):
        historica = mae[["persistencia", "ayer", "semana_pasada"]].idxmin()
        mae["mejor_historica"] = mae[historica]
        mape["mejor_historica"] = mape[historica]
    return pd.DataFrame({
        "serie": serie,
        "ventana": ventana,
        "metodo": mae.index,
        "filas": len(real),
        "filas_fuera": len(predicciones) - len(real),
        "reales_no_positivos": int((~positivo).sum()),
        "MAE": mae.to_numpy(),
        "MAPE": mape.to_numpy(),
        "skill_MAE_persistencia": 1 - mae.to_numpy() / mae["persistencia"]
        if mae["persistencia"] else np.nan,
    })


def tetuan(raiz):
    bruto = pd.read_csv(raiz / "bronze/uci849_tetouan.csv")
    bruto.columns = bruto.columns.str.split().str.join(" ")
    bruto["DateTime"] = pd.to_datetime(bruto["DateTime"], format="%m/%d/%Y %H:%M")
    demanda = bruto.set_index("DateTime")
    for zona in range(1, 4):
        ruta = raiz / f"reportes/modelado/predicciones_prueba_zona{zona}.csv"
        predicciones = pd.read_csv(ruta, parse_dates=["DateTime"], index_col="DateTime")
        predicciones = predicciones.rename(columns={
            "Gradient Boosting global": "hgb_global",
            "Gradient Boosting global, reentrenado cada semana": "hgb_semanal",
        }).drop(columns="Gradient Boosting por zona")
        resultados = evaluar(
            f"Tetuán Z{zona}", 2017, demanda[f"Zone {zona} Power Consumption"], predicciones,
        )
        if len(predicciones) != 7841 or resultados["filas_fuera"].any():
            raise ValueError(f"La zona {zona} perdió la comparabilidad con el test de nb02")
        yield resultados


def veranos_ceuta(raiz):
    bruto = cargar_silver_ceuta(raiz).sort_values("DateTime").reset_index(drop=True)
    real = bruto.set_index("DateTime")[SERIE]
    # Se reproduce la receta de entrenamiento original de V4. La evaluación y
    # los comparadores usan la serie observada y excluyen los objetivos imputados.
    modelo_datos = bruto.copy()
    modelo_datos[SERIE] = huecos_cortos_rellenos(bruto[SERIE])
    prep = {
        nombre: R.features(modelo_datos, SERIE, [], variante, feriados=[],
                           ramadanes=ceuta.RAMADANES)
        for nombre, variante in ceuta.VARIANTES.items()
    }
    validas = np.ones(len(bruto), dtype=bool)
    for X, yobj, _, base in prep.values():
        validas &= (X.notna().all(axis=1) & yobj.notna()).to_numpy()
        validas &= base[["semana", "ayer"]].notna().all(axis=1).to_numpy()
    fechas = bruto.loc[validas, "DateTime"].reset_index(drop=True)
    variante = "V4_razon_sin_anual"
    X, yobj, yt, base = (obj.iloc[validas] for obj in prep[variante])
    for verano in range(2022, 2027):
        entrenamiento, prueba = ceuta.ventanas(fechas, verano)
        train = entrenamiento["sin_verano"]
        modelo = R.modelo().fit(X.iloc[train], yobj.iloc[train])
        pred = R.reconstruir(ceuta.VARIANTES[variante], modelo.predict(X.iloc[prueba]),
                             base.iloc[prueba])
        predicciones = pd.DataFrame({
            "real": yt.iloc[prueba].to_numpy(),
            "v4_sin_verano": np.asarray(pred),
            "ayer": base["ayer"].iloc[prueba].to_numpy(),
            "semana_pasada": base["semana"].iloc[prueba].to_numpy(),
        }, index=fechas.iloc[prueba])
        yield evaluar("Ceuta", verano, real, predicciones)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", required=True, type=Path)
    parser.add_argument("--serie", choices=("tetuan", "ceuta", "ambas"), default="ambas")
    parser.add_argument("--salida", required=True, type=Path)
    args = parser.parse_args()
    tablas = []
    if args.serie in {"tetuan", "ambas"}:
        tablas.extend(tetuan(args.datos))
    if args.serie in {"ceuta", "ambas"}:
        tablas.extend(veranos_ceuta(args.datos))
    resultados = pd.concat(tablas, ignore_index=True)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    resultados.to_csv(args.salida, index=False)
    print(resultados.pivot(index=["serie", "ventana"], columns="metodo",
                           values="MAPE").round(3).to_string())


if __name__ == "__main__":
    main()
