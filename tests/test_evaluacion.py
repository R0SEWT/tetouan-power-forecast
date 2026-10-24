import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.evaluacion import (
    bootstrap_diferencia_mae,
    hora_objetivo,
    mae_por_grupo,
    plegados_mensuales,
    subestimacion_pico,
)


def test_la_hora_pico_es_la_del_periodo_que_se_predice():
    fechas = pd.to_datetime(["2017-03-01 18:00", "2017-03-01 18:50", "2017-03-01 22:00"])
    assert list(hora_objetivo(fechas)) == [19, 19, 23]
    real = np.array([100.0, 100.0, 100.0])
    pred = np.array([90.0, 99.0, 50.0])  # el tercero no es pico: no cuenta
    assert subestimacion_pico(real, pred, fechas) == 0.5


def test_mae_por_grupo():
    tabla = mae_por_grupo([10, 10, 10, 10], {"a": [9, 11, 10, 14], "b": [10, 10, 10, 10]}, [1, 1, 2, 2])
    assert tabla.loc[1, "a"] == 1 and tabla.loc[2, "a"] == 2 and (tabla["b"] == 0).all()


def test_bootstrap_por_dias():
    fechas = pd.date_range("2017-11-01", periods=144 * 20, freq="10min")
    real = np.full(len(fechas), 100.0)
    mejor, peor = real + 1, real + 3
    media, bajo, alto = bootstrap_diferencia_mae(real, mejor, peor, fechas, n=200)
    assert media == pytest.approx(-2) and bajo == pytest.approx(-2) and alto == pytest.approx(-2)
    ruidoso = real + np.random.default_rng(0).normal(0, 5, len(fechas))
    media, bajo, alto = bootstrap_diferencia_mae(real, ruidoso, peor, fechas, n=200)
    assert bajo < media < alto


def test_plegados_mensuales_dejan_una_hora_y_omiten_meses_cortos():
    fechas = pd.Series(pd.date_range("2017-01-08", "2017-11-06 09:20", freq="10min"))
    plegados = plegados_mensuales(fechas)
    assert [nombre for nombre, _, _ in plegados] == [f"2017-{m:02d}" for m in range(3, 11)]  # noviembre: 6 días
    for nombre, tr, te in plegados:
        assert fechas[te].min() == pd.Timestamp(f"{nombre}-01")
        assert fechas[tr].max() == pd.Timestamp(f"{nombre}-01") - pd.Timedelta(minutes=70)
