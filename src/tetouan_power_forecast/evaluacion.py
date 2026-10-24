"""Cómo se evalúa cada modelo frente a las referencias ingenuas (docs/negocio.md, criterios de éxito)."""

import numpy as np
import pandas as pd

from tetouan_power_forecast.metricas import HORIZONTE, metricas

HORAS_PICO = range(19, 23)  # 19:00 a 22:50, la hora del periodo que se predice


def errores(real, pred):
    mae, rmse, mape = metricas(real, pred)
    return {"MAE (kW)": mae, "RMSE (kW)": rmse, "MAPE (%)": mape}


def hora_objetivo(fechas):
    """La hora del periodo que se predice (t+6), no la del momento en que se predice."""
    return (pd.Series(fechas) + pd.Timedelta(minutes=10 * HORIZONTE)).dt.hour.to_numpy()


def subestimacion_pico(real, pred, fechas, umbral=0.05):
    """Fracción de los periodos pico en los que el pronóstico queda más de `umbral` por debajo del real."""
    real, pred = np.asarray(real, dtype=float), np.asarray(pred, dtype=float)
    pico = np.isin(hora_objetivo(fechas), HORAS_PICO)
    return float(np.mean(pred[pico] < (1 - umbral) * real[pico]))


def mae_por_grupo(real, predicciones, grupos):
    """MAE (kW) de cada método en cada grupo (mes, hora, día de semana…); una columna por método."""
    real = np.asarray(real, dtype=float)
    errores_abs = pd.DataFrame({k: np.abs(real - np.asarray(v, dtype=float)) for k, v in predicciones.items()})
    return errores_abs.groupby(np.asarray(grupos)).mean()


def bootstrap_diferencia_mae(real, pred, referencia, fechas, n=2000, semilla=0):
    """Diferencia de MAE (modelo − referencia) con su intervalo al 95 %, remuestreando días enteros.

    Los errores de periodos cercanos están correlacionados: remuestrear días, y no periodos sueltos, da
    un intervalo más honesto (bootstrap por bloques).
    """
    dias = pd.Series(pd.to_datetime(np.asarray(fechas))).dt.normalize().to_numpy()
    diferencia = np.abs(np.asarray(real) - np.asarray(pred)) - np.abs(np.asarray(real) - np.asarray(referencia))
    por_dia = pd.DataFrame({"dia": dias, "dif": diferencia}).groupby("dia")["dif"].agg(["sum", "count"])
    suma, cuenta = por_dia["sum"].to_numpy(), por_dia["count"].to_numpy()
    rng = np.random.default_rng(semilla)
    muestras = rng.integers(0, len(suma), size=(n, len(suma)))
    medias = suma[muestras].sum(axis=1) / cuenta[muestras].sum(axis=1)
    return float(diferencia.mean()), float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


def plegados_mensuales(fechas, desde_mes=3, dias_minimos=7):
    """Origen móvil mensual: cada mes se evalúa con un modelo entrenado con todo lo anterior.

    El entrenamiento termina una hora (HORIZONTE periodos) antes del mes, para que ningún objetivo t+6
    caiga dentro del mes evaluado. Los meses con menos de `dias_minimos` días de datos se omiten.
    """
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)))
    plegados = []
    for mes in pd.period_range(pd.Timestamp(fechas.min().year, desde_mes, 1), fechas.max(), freq="M"):
        inicio, fin = mes.start_time, mes.end_time
        te = np.flatnonzero(((fechas >= inicio) & (fechas <= fin)).to_numpy())
        if len(te) == 0 or fechas.iloc[te].dt.normalize().nunique() < dias_minimos:
            continue
        tr = np.flatnonzero((fechas < inicio - pd.Timedelta(minutes=10 * HORIZONTE)).to_numpy())
        plegados.append((f"{mes:%Y-%m}", tr, te))
    return plegados
