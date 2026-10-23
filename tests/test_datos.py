import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast import HORIZONTE
from tetouan_power_forecast.datos import (
    PERIODOS_DIA,
    TARGET,
    ZONAS,
    columnas_predictoras,
    construir_dataset,
    cortes_particion,
    limpiar,
)


@pytest.fixture
def crudo():
    # Tres días cada 10 minutos, con el formato de UCI y un nombre de columna con doble espacio
    n = 3 * PERIODOS_DIA
    fechas = pd.date_range("2017-01-01", periods=n, freq="10min")
    df = pd.DataFrame({
        "DateTime": fechas.strftime("%m/%d/%Y %H:%M"),
        "Temperature": 15.0,
        "Humidity": 70.0,
        "Wind Speed": 0.08,
        "general diffuse flows": 0.05,
        "diffuse  flows": 0.1,
    })
    for i, zona in enumerate(ZONAS, start=1):
        df[zona] = np.arange(n, dtype=float) * i + 1_000
    return limpiar(df.iloc[::-1])  # desordenado a propósito


def test_limpiar_normaliza_columnas_y_ordena(crudo):
    assert "diffuse flows" in crudo.columns
    assert crudo["DateTime"].is_monotonic_increasing


def test_objetivo_es_el_consumo_seis_periodos_despues(crudo):
    df = construir_dataset(crudo)
    fila = df.iloc[0]
    original = crudo.set_index("DateTime")["Zone 1 Power Consumption"]
    esperado = original[fila["DateTime"] + pd.Timedelta(minutes=10 * HORIZONTE)]
    assert fila[TARGET] == esperado


def test_rezago_diario_apunta_al_dia_anterior_del_periodo_predicho(crudo):
    df = construir_dataset(crudo)
    fila = df.iloc[0]
    original = crudo.set_index("DateTime")["Zone 1 Power Consumption"]
    esperado = original[fila["DateTime"] - pd.Timedelta(minutes=10 * (PERIODOS_DIA - HORIZONTE))]
    assert fila["Zone1_lag_24h"] == esperado


def test_quita_filas_sin_historial_ni_objetivo(crudo):
    df = construir_dataset(crudo)
    assert len(df) == len(crudo) - (PERIODOS_DIA - HORIZONTE) - HORIZONTE
    assert not df.isnull().any().any()


def test_predictoras_excluyen_objetivo_fecha_y_consumo_crudo(crudo):
    cols = columnas_predictoras(construir_dataset(crudo))
    assert TARGET not in cols and "DateTime" not in cols
    assert not set(ZONAS) & set(cols)
    assert "Zone1_t" in cols


def test_cortes_particion():
    assert cortes_particion(1000) == (700, 850)


def test_por_zona_cambia_el_objetivo_y_sus_variables_propias(crudo):
    df = construir_dataset(crudo, zona=3)
    original = crudo.set_index("DateTime")["Zone 3 Power Consumption"]
    fila = df.iloc[0]
    assert fila["Target_Zone3_t_plus_6"] == original[fila["DateTime"] + pd.Timedelta(minutes=60)]
    assert {"Zone3_lag_24h", "Zone3_Rolling_Mean_1h"} <= set(df.columns)
