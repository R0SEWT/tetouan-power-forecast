"""Cómo se evalúa cada modelo frente a las referencias ingenuas (docs/negocio.md, criterios de éxito)."""

import numpy as np
import pandas as pd

from tetouan_power_forecast.metricas import HORIZONTE, metricas

HORAS_PICO = range(19, 23)  # 19:00 a 22:50, la hora del periodo que se predice
ADELANTO = pd.Timedelta(minutes=10 * HORIZONTE)  # Tetuán: 6 pasos de 10 minutos; el SEIN pasa el suyo


def errores(real, pred):
    mae, rmse, mape = metricas(real, pred)
    return {"MAE (kW)": mae, "RMSE (kW)": rmse, "MAPE (%)": mape}


def hora_objetivo(fechas, adelanto=ADELANTO):
    """La hora del periodo que se predice (t+6), no la del momento en que se predice."""
    return (pd.Series(fechas) + adelanto).dt.hour.to_numpy()


def subestimacion_pico(real, pred, fechas, umbral=0.05, horas_pico=HORAS_PICO, adelanto=ADELANTO):
    """Fracción de los periodos pico en los que el pronóstico queda más de `umbral` por debajo del real."""
    real, pred = np.asarray(real, dtype=float), np.asarray(pred, dtype=float)
    pico = np.isin(hora_objetivo(fechas, adelanto), horas_pico)
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


def plegados_mensuales(fechas, desde_mes=3, dias_minimos=7, adelanto=ADELANTO, desde=None):
    """Origen móvil mensual: cada mes se evalúa con un modelo entrenado con todo lo anterior.

    El entrenamiento termina `adelanto` antes del mes (en Tetuán, una hora), para que ningún objetivo caiga
    dentro del mes evaluado. Los meses con menos de `dias_minimos` días de datos se omiten. `desde` fija el primer
    mes evaluado; si no se pasa, es `desde_mes` del primer año.
    """
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)))
    plegados = []
    inicio_meses = pd.Timestamp(desde) if desde is not None else pd.Timestamp(fechas.min().year, desde_mes, 1)
    for mes in pd.period_range(inicio_meses, fechas.max(), freq="M"):
        inicio, fin = mes.start_time, mes.end_time
        te = np.flatnonzero(((fechas >= inicio) & (fechas <= fin)).to_numpy())
        if len(te) == 0 or fechas.iloc[te].dt.normalize().nunique() < dias_minimos:
            continue
        tr = np.flatnonzero((fechas < inicio - adelanto).to_numpy())
        plegados.append((f"{mes:%Y-%m}", tr, te))
    return plegados
