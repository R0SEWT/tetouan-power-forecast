"""El máximo y la mayor subida de las próximas 24 h, y qué tan bien ubica un modelo el máximo de cada día.

Las próximas 24 h desde un origen son las del pronóstico a 24 h (``/pronostico``): cada periodo es el pronóstico
directo a 24 h emitido 24 h antes de ese periodo, el mismo que dibuja la serie del día. No hay un pronóstico de
varios pasos encadenado: el perfil se arma con 48 orígenes consecutivos, todos ya emitidos en el origen.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contrato import AciertoPico, Pico, PicoRampa, Pronostico, Rampa

PERIODOS_HORA = 2  # una hora son dos periodos de 30 minutos
TOLERANCIA_PICO = 2  # ±1 h, en periodos
MIN_SUBIDAS_DIA = 44  # un día cuenta para el umbral si tiene al menos 44 de sus 48 subidas horarias


def pico_rampa(p: Pronostico, umbral: float | None = None, acierto: AciertoPico | None = None,
               modelo: str | None = None) -> PicoRampa:
    """El periodo con más demanda pronosticada (con su rango) y la mayor subida en una hora."""
    pred = np.asarray(p.pronostico, dtype=float)
    j = int(np.argmax(pred))
    pico = Pico(fecha_hora=p.fecha_hora[j], valor=round(float(pred[j]), 1),
                inferior=p.intervalo.inferior[j], superior=p.intervalo.superior[j])
    subidas = pred[PERIODOS_HORA:] - pred[:-PERIODOS_HORA]
    rampa = None
    if len(subidas) and subidas.max() > 0:
        k = int(np.argmax(subidas))
        subida = round(float(subidas[k]), 1)
        rampa = Rampa(desde=p.fecha_hora[k], hasta=p.fecha_hora[k + PERIODOS_HORA], subida_mw=subida,
                      fuerte=umbral is not None and subida > umbral,
                      umbral_mw=None if umbral is None else round(float(umbral), 1))
    return PicoRampa(desde=p.fecha_hora[0], hasta=p.fecha_hora[-1], pico=pico, rampa=rampa, acierto=acierto,
                     modelo=modelo)


def umbral_rampa(real: pd.Series, hasta: pd.Timestamp, percentil: float = 95) -> float | None:
    """Percentil de la mayor subida horaria de cada día con la demanda real anterior a ``hasta``.

    ``real`` va indexada por el final de cada periodo de 30 minutos. Se usa la mayor subida de cada día y no
    todas las subidas: con todas, casi cualquier tarde superaría el umbral y la marca no diría nada.
    """
    s = real[real.index < hasta].sort_index()
    s = s[~s.index.duplicated()].asfreq("30min")
    subida = (s - s.shift(PERIODOS_HORA)).dropna()
    if subida.empty:
        return None
    dia = (subida.index - pd.Timedelta(minutes=30)).normalize()
    por_dia = subida.groupby(dia).agg(["max", "count"])
    maximos = por_dia.loc[por_dia["count"] >= MIN_SUBIDAS_DIA, "max"]
    return float(np.percentile(maximos, percentil)) if len(maximos) else None


def acierto_pico(pred: np.ndarray, real: np.ndarray, referencia: np.ndarray) -> AciertoPico | None:
    """Cada fila es un día de 48 periodos. Solo cuentan los días con todos los valores.

    La hora del máximo acierta si cae a ±1 h (dos periodos) de la del máximo real.
    """
    pred, real, referencia = (np.asarray(x, dtype=float) for x in (pred, real, referencia))
    completos = np.isfinite(pred).all(axis=1) & np.isfinite(real).all(axis=1) & np.isfinite(referencia).all(axis=1)
    if not completos.any():
        return None
    pred, real, referencia = pred[completos], real[completos], referencia[completos]
    hora_real, pico_real = real.argmax(axis=1), real.max(axis=1)

    def medir(x):
        acierta = np.abs(x.argmax(axis=1) - hora_real) <= TOLERANCIA_PICO
        return round(100 * float(acierta.mean()), 1), round(float(np.abs(x.max(axis=1) - pico_real).mean()), 1)

    pct, mae = medir(pred)
    pct_ref, mae_ref = medir(referencia)
    return AciertoPico(dias=int(completos.sum()), pct_hora=pct, pct_hora_referencia=pct_ref, mae_pico_mw=mae,
                       mae_pico_referencia_mw=mae_ref)
