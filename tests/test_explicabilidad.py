import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.explicabilidad import (
    FAMILIAS,
    a_mw,
    contribuciones,
    familia_de,
    importancia,
    por_familia,
)
from tetouan_power_forecast.modelado_sein import gradient_boosting_global, preparar_datasets, tramo
from tetouan_power_forecast.variables_sein import columnas_variante


def test_cada_variable_de_m3_cae_en_una_sola_familia():
    todas = [c for columnas in FAMILIAS.values() for c in columnas]
    assert len(todas) == len(set(todas))
    assert familia_de("Area_semana_pasada") == "Demanda reciente"
    assert familia_de("FeriadoObjetivo") == "Calendario"
    assert familia_de("area_cod") == "Código de área"
    assert familia_de("nino12_ssta") == "El Niño"
    assert familia_de("media_24h") == "Otras"  # la escala no es una variable


def test_en_mw_la_explicacion_suma_el_pronostico():
    valores = np.array([[0.02, -0.01], [0.0, 0.05]])
    base = np.array([1.0, 1.0])
    escala = np.array([1000.0, 2000.0])
    v_mw, base_mw = a_mw(valores, base, escala)
    np.testing.assert_allclose(base_mw + v_mw.sum(axis=1), escala * (base + valores.sum(axis=1)))
    np.testing.assert_allclose(v_mw[1], [0.0, 100.0])


def test_familias_suman_y_la_importancia_ordena():
    v = pd.DataFrame({"Area_t": [10.0, -20.0], "Area_ayer": [5.0, 5.0], "temp": [1.0, -1.0], "icen": [0.0, 2.0]})
    f = por_familia(v)
    assert f.loc[1, "Demanda reciente"] == -15.0  # dentro de una familia, los signos se compensan
    np.testing.assert_allclose(f.sum(axis=1), v.sum(axis=1))
    imp = importancia(v)
    assert list(imp.index[:2]) == ["Area_t", "Area_ayer"] and imp["Area_t"] == 15.0


def test_contribuciones_junta_el_resto_sin_perder_nada():
    fila = pd.Series({"a": 5.0, "b": -30.0, "c": 1.0, "d": 2.0})
    datos = pd.Series({"a": 0.9, "b": 1.1, "c": 3, "d": 4})
    tabla = contribuciones(fila, datos, top=2)
    assert list(tabla["variable"]) == ["b", "a", "otras 2 variables"]
    assert tabla["contribucion_mw"].sum() == pytest.approx(fila.sum())
    assert tabla.loc[0, "valor"] == 1.1


def test_con_xgboost_la_explicacion_reconstruye_el_pronostico_en_mw():
    """Con las contribuciones de XGBoost (las mismas que da TreeExplainer), base + Σ φ, por la escala, es el
    pronóstico de `ModeloRazon` en MW."""
    xgb = pytest.importorskip("xgboost")
    fechas = pd.date_range("2024-01-01 00:30", "2025-02-10 00:00", freq="30min")
    hora = fechas.hour + fechas.minute / 60
    rng = np.random.default_rng(0)
    demanda = pd.DataFrame({"DateTime": fechas})
    for area, nivel in [("NORTE", 1200.0), ("CENTRO", 4100.0), ("SUR", 1700.0)]:
        demanda[area] = nivel * (1 + 0.2 * np.sin(2 * np.pi * (hora - 14) / 24)) + rng.normal(0, 10, len(fechas))
    demanda["SEIN"] = demanda[["NORTE", "CENTRO", "SUR"]].sum(axis=1)
    _, global_ = preparar_datasets(demanda, 2, variantes=["M0"])
    cols = columnas_variante(global_, "M0")
    tr, va = tramo(global_, "entrenamiento"), tramo(global_, "validacion")
    modelo = gradient_boosting_global(n_estimators=20, max_depth=3, dispositivo="cpu").fit(tr[cols], tr["real"])
    X = va[cols].drop(columns="media_24h")
    contrib = modelo.estimador_.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    v_mw, base_mw = a_mw(contrib[:, :-1], contrib[:, -1], va["media_24h"])
    np.testing.assert_allclose(base_mw + v_mw.sum(axis=1), modelo.predict(va[cols]), rtol=1e-4)
