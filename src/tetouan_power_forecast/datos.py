"""Limpieza y construcción del dataset t+6, igual que en el notebook 01 (allí, con zona = 1)."""

import numpy as np
import pandas as pd

from tetouan_power_forecast.metricas import HORIZONTE

ZONAS = ["Zone 1 Power Consumption", "Zone 2 Power Consumption", "Zone 3 Power Consumption"]
PERIODOS_DIA = 144  # 144 periodos de 10 minutos = 24 horas


def nombre_objetivo(zona=1):
    return f"Target_Zone{zona}_t_plus_6"


TARGET = nombre_objetivo(1)


def limpiar(df):
    """Normaliza los nombres de columnas, convierte DateTime a fecha y ordena en el tiempo."""
    df = df.copy()
    df.columns = df.columns.str.strip().str.replace(r"\s+", " ", regex=True)
    df["DateTime"] = pd.to_datetime(df["DateTime"], format="%m/%d/%Y %H:%M")
    return df.sort_values("DateTime").reset_index(drop=True)


def construir_dataset(df, zona=1):
    """Agrega calendario, objetivo t+6, rezagos y estadísticas móviles; quita filas incompletas."""
    df = df.copy()
    fecha = df["DateTime"].dt
    consumo = df[ZONAS[zona - 1]]

    # Componentes temporales
    df["Hour"] = fecha.hour
    df["MinuteOfDay"] = fecha.hour * 60 + fecha.minute
    df["Day"] = fecha.day
    df["Month"] = fecha.month
    df["DayOfWeek"] = fecha.day_of_week  # 0 = lunes, 6 = domingo
    df["DayOfYear"] = fecha.day_of_year
    df["IsWeekend"] = (df["DayOfWeek"] >= 5).astype(int)

    # Codificación cíclica: diaria (1440 min), semanal (7 días) y anual (365 días)
    df["Time_Sin"] = np.sin(2 * np.pi * df["MinuteOfDay"] / 1440)
    df["Time_Cos"] = np.cos(2 * np.pi * df["MinuteOfDay"] / 1440)
    df["Week_Sin"] = np.sin(2 * np.pi * df["DayOfWeek"] / 7)
    df["Week_Cos"] = np.cos(2 * np.pi * df["DayOfWeek"] / 7)
    df["Year_Sin"] = np.sin(2 * np.pi * (df["DayOfYear"] - 1) / 365)
    df["Year_Cos"] = np.cos(2 * np.pi * (df["DayOfYear"] - 1) / 365)

    # Objetivo: consumo de la zona una hora adelante
    df[nombre_objetivo(zona)] = consumo.shift(-HORIZONTE)

    # Rezagos de las tres zonas: t, t-1, t-2 y t-6
    for lag in [0, 1, 2, 6]:
        sufijo = "_t" if lag == 0 else f"_t_minus_{lag}"
        for z, columna in enumerate(ZONAS, start=1):
            df[f"Zone{z}{sufijo}"] = df[columna].shift(lag)

    # Mismo momento del día anterior al periodo que se predice (t+6-144 = t-138)
    df[f"Zone{zona}_lag_24h"] = consumo.shift(PERIODOS_DIA - HORIZONTE)

    # Estadísticas móviles de la última hora (t-5 a t)
    df[f"Zone{zona}_Rolling_Mean_1h"] = consumo.rolling(window=6).mean()
    df[f"Zone{zona}_Rolling_Std_1h"] = consumo.rolling(window=6).std()

    return df.dropna().reset_index(drop=True)


def columnas_predictoras(df_model):
    """Todas las columnas menos la fecha, el consumo crudo (duplica Zone*_t) y los objetivos."""
    excluir = {"DateTime", "particion", *ZONAS, *(nombre_objetivo(z) for z in (1, 2, 3))}
    return [c for c in df_model.columns if c not in excluir]


def cortes_particion(n, train=0.70, val=0.15):
    """Índices donde termina entrenamiento y validación en la partición cronológica 70/15/15."""
    return int(n * train), int(n * (train + val))
