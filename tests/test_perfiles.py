import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast import HORIZONTE
from tetouan_power_forecast.datos import PERIODOS_DIA, ZONAS
from tetouan_power_forecast.perfiles import (
    NOMBRES,
    efecto_feriados,
    errores_referencias,
    firma_de_carga,
    perfil_diario,
    referencias_ingenuas,
)


@pytest.fixture
def silver():
    """Un año cada 10 minutos: ciclo diario puro en la Zona 1, más calor y verano en la Zona 3."""
    fechas = pd.date_range("2017-01-01", "2017-12-30 23:50", freq="10min")
    hora = fechas.hour + fechas.minute / 60
    diario = 1 + 0.3 * np.sin(2 * np.pi * (hora - 14) / 24)
    temperatura = 18 + 8 * np.sin(2 * np.pi * (fechas.day_of_year - 110) / 365)
    df = pd.DataFrame({"DateTime": fechas, "Temperature": temperatura})
    df[ZONAS[0]] = 30_000 * diario
    df[ZONAS[1]] = 20_000 * diario * np.where(fechas.day_of_week == 6, 0.8, 1.0)
    df[ZONAS[2]] = 15_000 * diario * (1 + 0.04 * (temperatura - 18))
    return df


def test_referencia_de_ayer_acierta_un_ciclo_diario_puro(silver):
    errores = errores_referencias(referencias_ingenuas(silver, zona=1))
    assert errores.loc["ayer", "MAPE (%)"] == pytest.approx(0, abs=1e-9)
    assert errores.loc["persistencia", "MAPE (%)"] > 1


def test_referencias_se_alinean_con_el_horizonte(silver):
    refs = referencias_ingenuas(silver, zona=2)
    t = refs.index[0]
    serie = silver.set_index("DateTime")[ZONAS[1]]
    assert refs.loc[t, "real"] == serie[t + pd.Timedelta(minutes=10 * HORIZONTE)]
    assert refs.loc[t, "semana_pasada"] == serie[t - pd.Timedelta(minutes=10 * (7 * PERIODOS_DIA - HORIZONTE))]


def test_firma_distingue_zona_laboral_y_zona_sensible_al_calor(silver):
    firma = firma_de_carga(silver)
    assert list(firma.columns) == NOMBRES
    assert firma.loc["Parte de la demanda de la ciudad (%)"].sum() == pytest.approx(100)
    assert firma.loc["Domingo de día / laborable (9-17 h)", "Zona 2"] == pytest.approx(0.8, abs=0.01)
    calor = firma.loc["Sensibilidad al calor en verano (%/°C)"]
    assert calor["Zona 3"] > 3 and abs(calor["Zona 1"]) < 0.1


def test_perfil_diario_promedia_uno(silver):
    assert perfil_diario(silver).mean().to_numpy() == pytest.approx([1, 1, 1])


def test_efecto_feriados_es_neutro_si_no_cambia_el_consumo(silver):
    efecto = efecto_feriados(silver)
    assert efecto["Zona 1"].to_numpy() == pytest.approx(np.ones(len(efecto)))


def test_tabla_markdown():
    from tetouan_power_forecast.perfiles import tabla_markdown

    df = pd.DataFrame({"a": [1.234, 2.0]}, index=["x", "y"])
    assert tabla_markdown(df).splitlines() == ["| | a |", "|---|---:|", "| x | 1.23 |", "| y | 2.00 |"]


def test_comparar_periodos_detecta_una_transferencia_entre_zonas(silver):
    from tetouan_power_forecast.perfiles import comparar_periodos

    despues = silver["DateTime"] >= "2017-10-25 12:00"
    silver.loc[despues, ZONAS[0]] -= 3_000
    silver.loc[despues, ZONAS[1]] += 3_000
    tabla = comparar_periodos(silver)
    assert tabla.loc["Zona 1", "cambio (%)"] < -5 and tabla.loc["Zona 2", "cambio (%)"] > 5
    assert tabla.loc["Zona 1 + Zona 2", "cambio (%)"] == pytest.approx(0, abs=1e-6)
