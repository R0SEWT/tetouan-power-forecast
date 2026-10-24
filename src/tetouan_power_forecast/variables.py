"""Variables del objetivo en razón (V4 de docs/historico.md) para una zona o para las tres apiladas.

El modelo no aprende el consumo en t+6 sino su razón con la media de las últimas 24 h, y todas las
variables de consumo van divididas por la media de 24 h de su zona. Así no tiene que aprender el nivel de
cada época, que con un solo año no puede generalizar. No hay calendario anual (mes, día del año): con un
año, funciona como identificador de época.
"""

import numpy as np
import pandas as pd

from tetouan_power_forecast.datos import PERIODOS_DIA, ZONAS
from tetouan_power_forecast.metricas import HORIZONTE

SEMANA = 7 * PERIODOS_DIA
CLIMA = ["Temperature", "Humidity", "Wind Speed", "general diffuse flows", "diffuse flows"]
# Feriados y Ramadán de Marruecos en 2017, de la fecha de t+6. Son aproximados: el grupo debe verificarlos.
FERIADOS = ["2017-01-11", "2017-05-01", "2017-06-26", "2017-06-27", "2017-07-30", "2017-08-14",
            "2017-08-20", "2017-08-21", "2017-09-01", "2017-09-02", "2017-09-21", "2017-11-06",
            "2017-11-18", "2017-12-01", "2017-01-01"]
RAMADAN = ("2017-05-27", "2017-06-25")
ESCALA = "media_24h"  # media de 24 h de la zona, en kW: lleva la razón de vuelta a kW
REFERENCIAS = ["persistencia", "ayer", "semana_pasada"]
NO_PREDICTORAS = ["DateTime", "particion", "real", *REFERENCIAS]


def _consumo_relativo(consumo, prefijo):
    """Rezagos t, t−1, t−2 y t−6 divididos por la media de 24 h de la misma serie."""
    escala = consumo.rolling(PERIODOS_DIA).mean()
    return {f"{prefijo}_t" if lag == 0 else f"{prefijo}_t_minus_{lag}": consumo.shift(lag) / escala
            for lag in [0, 1, 2, 6]}


def dataset_razon(silver, zona=1, otras_zonas=True, feriados=FERIADOS, ramadan=RAMADAN):
    """Una fila por momento t: variables, media de 24 h, consumo real en t+6 y referencias ingenuas.

    Las variables de la propia zona se llaman `Zona_*`; las de las otras, `Zone2_t`, `Zone3_t_minus_1`,
    etc. Quita las filas incompletas: la primera semana (rezago semanal) y la última hora (sin objetivo).
    """
    df = silver.sort_values("DateTime").reset_index(drop=True)
    fecha = df["DateTime"].dt
    y = df[ZONAS[zona - 1]]
    m24 = y.rolling(PERIODOS_DIA).mean()
    minuto = fecha.hour * 60 + fecha.minute
    dia_objetivo = (df["DateTime"] + pd.Timedelta(minutes=10 * HORIZONTE)).dt.normalize()
    columnas = {
        "DateTime": df["DateTime"],
        "Hour": fecha.hour,
        "MinuteOfDay": minuto,
        "DayOfWeek": fecha.day_of_week,
        "IsWeekend": (fecha.day_of_week >= 5).astype(int),
        "Time_Sin": np.sin(2 * np.pi * minuto / 1440),
        "Time_Cos": np.cos(2 * np.pi * minuto / 1440),
        "Week_Sin": np.sin(2 * np.pi * fecha.day_of_week / 7),
        "Week_Cos": np.cos(2 * np.pi * fecha.day_of_week / 7),
        **{c: df[c] for c in CLIMA},
        "Feriado": dia_objetivo.isin(pd.to_datetime(feriados)).astype(int),
        "Ramadan": dia_objetivo.between(*map(pd.Timestamp, ramadan)).astype(int),
        "T_mean_24h": df["Temperature"].rolling(PERIODOS_DIA).mean(),
        **_consumo_relativo(y, "Zona"),
    }
    if otras_zonas:
        for z in (1, 2, 3):
            if z != zona:
                columnas.update(_consumo_relativo(df[ZONAS[z - 1]], f"Zone{z}"))
    columnas.update({
        "Zona_lag_24h": y.shift(PERIODOS_DIA - HORIZONTE) / m24,  # mismo momento de ayer que t+6
        "Zona_Rolling_Mean_1h": y.rolling(6).mean() / m24,
        "Zona_Rolling_Std_1h": y.rolling(6).std() / m24,
        "Zona_lag_1w": y.shift(SEMANA - HORIZONTE) / m24,  # mismo momento de la semana pasada que t+6
        "Zona_lag_1w_t": y.shift(SEMANA) / m24,
        "Zona_m24_vs_m7d": m24 / y.rolling(SEMANA).mean(),  # si el último día está sobre la última semana
        ESCALA: m24,
        "real": y.shift(-HORIZONTE),
        "persistencia": y,
        "ayer": y.shift(PERIODOS_DIA - HORIZONTE),
        "semana_pasada": y.shift(SEMANA - HORIZONTE),
    })
    return pd.DataFrame(columnas).dropna().reset_index(drop=True)


def dataset_global(silver, **kwargs):
    """Las tres zonas apiladas, solo con variables de la propia zona y la zona como categórica."""
    partes = [dataset_razon(silver, zona=z, otras_zonas=False, **kwargs).assign(zona=z) for z in (1, 2, 3)]
    return pd.concat(partes).sort_values(["DateTime", "zona"], kind="stable").reset_index(drop=True)


def columnas_modelo(datos):
    """Lo que recibe el modelo: las variables y la media de 24 h (que el modelo en razón separa)."""
    return [c for c in datos.columns if c not in NO_PREDICTORAS]
