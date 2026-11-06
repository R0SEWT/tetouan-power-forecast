import itertools

import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from xgboost import XGBRegressor

from tetouan_power_forecast.modelado_sein import (
    bloques,
    candidatos,
    categoria_icen,
    columnas_sin_grupo,
    es_hora_pico,
    gradient_boosting_global,
    horas_mayor_demanda,
    mejor_referencia,
    portable,
    predecir_global,
    predecir_local,
    predecir_por_bloques,
    preparar_datasets,
    subestimacion_sobre_p90,
    tramo,
)
from tetouan_power_forecast.modelos import ModeloRazon
from tetouan_power_forecast.variables_sein import AREAS, PASO, columnas_variante

HUECO = 2 * PASO


@pytest.fixture
def demanda():
    """De enero de 2024 a febrero de 2025: cruza el corte entre entrenamiento y validación, y la climatología de la
    temperatura (que sale de 2024) cubre los meses evaluados."""
    fechas = pd.date_range("2024-01-01 00:30", "2025-02-10 00:00", freq="30min")
    rng = np.random.default_rng(0)
    hora = fechas.hour + fechas.minute / 60
    df = pd.DataFrame({"DateTime": fechas})
    for area, nivel in zip(AREAS, [1200.0, 4100.0, 1700.0], strict=True):
        df[area] = nivel * (1 + 0.2 * np.sin(2 * np.pi * (hora - 14) / 24)) + rng.normal(0, 10, len(fechas))
    df["SEIN"] = df[AREAS].sum(axis=1)
    return df


@pytest.fixture
def exogenas():
    horas = pd.date_range("2023-12-31", "2025-02-12", freq="h")
    return {
        "temperatura": pd.DataFrame({"fecha_hora": horas, "norte": 25.0, "centro": 20.0, "sur": 15.0}),
        "icen": pd.DataFrame({"mes": pd.date_range("2023-09-01", "2025-02-01", freq="MS"), "icen": 0.5}),
        "nino12": pd.DataFrame({"semana": pd.date_range("2023-12-06", "2025-02-12", freq="7D"),
                                "nino12_sst": 24.0, "nino12_ssta": 0.3}),
        "eventos": pd.DataFrame({"inicio": pd.to_datetime(["2025-01-05 10:00"]),
                                 "final": pd.to_datetime(["2025-01-05 11:00"])}),
    }


def test_los_candidatos_son_los_de_la_spec():
    modelos = candidatos(dispositivo="cpu")
    assert set(modelos) == {"Ridge", "Random Forest", "Gradient Boosting"}
    assert all(isinstance(m, ModeloRazon) for m, _ in modelos.values())
    assert max(modelos["Random Forest"][1]["estimador__max_samples"]) <= 0.3
    assert isinstance(modelos["Random Forest"][0].estimador, RandomForestRegressor)  # en la CPU, el de sklearn
    gb = modelos["Gradient Boosting"][0].estimador
    assert isinstance(gb, XGBRegressor) and gb.get_params()["device"] == "cpu"
    for modelo, espacio in modelos.values():  # cada hiperparámetro del espacio existe en su estimador
        assert set(espacio) <= set(modelo.get_params())


def test_portable_deja_xgboost_en_la_cpu_sin_tocar_el_original(demanda):
    locales, _ = preparar_datasets(demanda, horizonte=2, variantes=["M0"])
    d = tramo(locales["NORTE"], "entrenamiento")
    cols = columnas_variante(d, "M0")
    modelo = gradient_boosting_global(n_estimators=5, dispositivo="cpu").fit(d[cols], d["real"])
    antes = modelo.predict(d[cols])
    modelo.estimador_.set_params(device="cuda")  # como quedaría tras entrenar en Colab
    copia = portable(modelo)
    assert copia.estimador_.get_params()["device"] == "cpu"
    assert modelo.estimador_.get_params()["device"] == "cuda"
    np.testing.assert_allclose(copia.predict(d[cols]), antes)


def test_el_global_y_los_locales_quedan_en_las_mismas_filas(demanda, exogenas):
    locales, global_ = preparar_datasets(demanda, horizonte=2, **exogenas)
    assert set(locales) == set(AREAS)
    for area in AREAS:
        propio = global_[global_["area"] == area]
        assert (propio["DateTime"].to_numpy() == locales[area]["DateTime"].to_numpy()).all()
        assert (propio["particion"].to_numpy() == locales[area]["particion"].to_numpy()).all()
        np.testing.assert_allclose(propio["real"], locales[area]["real"])
    assert set(global_["area_cod"]) == {0, 1, 2}
    assert "area_cod" in columnas_variante(global_, "M0")
    assert not {c for c in global_.columns if c.startswith(("Norte_", "Centro_", "Sur_"))}
    assert {"Norte_t", "Sur_t"} <= set(locales["CENTRO"].columns)
    assert set(locales["CENTRO"]["particion"]) >= {"entrenamiento", "validacion"}


def test_el_tramo_de_desarrollo_junta_entrenamiento_y_validacion(demanda):
    locales, _ = preparar_datasets(demanda, horizonte=2, variantes=["M0"])
    datos = locales["NORTE"]
    desarrollo = tramo(datos, "desarrollo")
    assert len(desarrollo) == (datos["particion"] != "prueba").sum()  # no hay prueba: entra todo, con el hueco
    assert len(tramo(datos, "validacion")) == (datos["particion"] == "validacion").sum()


def test_quitar_un_grupo_desde_m3(demanda, exogenas):
    locales, _ = preparar_datasets(demanda, horizonte=2, **exogenas)
    columnas = columnas_sin_grupo(locales["SUR"], "clima")
    assert "icen" in columnas and "fallas_en_curso" in columnas
    assert not {"temp", "temp_media_24h", "temp_anomalia", "temp_objetivo"} & set(columnas)


def test_predecir_local_y_global_devuelven_una_prediccion_por_fila_evaluada(demanda, exogenas):
    locales, global_ = preparar_datasets(demanda, horizonte=2, **exogenas)
    entrenar, evaluar = (lambda d: tramo(d, "entrenamiento")), (lambda d: tramo(d, "validacion"))
    hgb = ModeloRazon(HistGradientBoostingRegressor(max_iter=5, early_stopping=False, random_state=0))
    local = predecir_local(hgb, locales, "M0", entrenar, evaluar)
    global_pred = predecir_global(gradient_boosting_global(n_estimators=5, dispositivo="cpu"), global_,
                                  lambda d: columnas_sin_grupo(d, "nino"), entrenar, evaluar)
    for area in AREAS:
        n = len(evaluar(locales[area]))
        assert len(local[area]) == n == len(global_pred[area])
        assert isinstance(local[area], np.ndarray) and isinstance(global_pred[area], np.ndarray)
        assert np.isfinite(local[area]).all() and np.isfinite(global_pred[area]).all()
        assert abs(local[area].mean() / evaluar(locales[area])["real"].mean() - 1) < 0.1  # en MW, no en razón


def test_los_bloques_cubren_la_evaluacion_sin_huecos_ni_solapes():
    fechas = pd.date_range("2025-01-01 00:30", "2025-01-22 00:00", freq="30min")  # miércoles a miércoles
    unico = bloques(fechas, "fijo")
    assert unico == [(fechas[0], fechas[-1] + PASO)]
    semanales = bloques(fechas, "periodica")
    assert [d for d, _ in semanales] == [fechas[0], *pd.to_datetime(["2025-01-06", "2025-01-13", "2025-01-20"])]
    assert all(h == siguiente for (_, h), (siguiente, _) in itertools.pairwise(semanales))
    assert semanales[-1][1] == fechas[-1] + PASO
    alerta = np.where(fechas < pd.Timestamp("2025-01-10 12:00"), "neutra", "cálida débil")
    assert [d for d, _ in bloques(fechas, "alerta", alerta=alerta)] == [fechas[0], pd.Timestamp("2025-01-10 12:00")]
    combinada = bloques(fechas, "periodica+alerta", alerta=alerta)
    assert len(combinada) == len(semanales) + 1
    with pytest.raises(ValueError):
        bloques(fechas, "mensual")


def test_cada_bloque_se_entrena_solo_con_lo_anterior_al_hueco(demanda):
    locales, _ = preparar_datasets(demanda, horizonte=2, variantes=["M0"])
    validacion = tramo(locales["NORTE"], "validacion")
    cortes = bloques(validacion["DateTime"], "periodica")
    vistos = []

    def predecir(entrenar, evaluar):
        vistos.append({area: entrenar(d)["DateTime"].max() for area, d in locales.items()})
        return {area: evaluar(d)["persistencia"].to_numpy() for area, d in locales.items()}

    pred = predecir_por_bloques(predecir, cortes, HUECO, seleccionar=lambda d: tramo(d, "validacion"))
    assert len(vistos) == len(cortes)
    for (desde, _), maximos in zip(cortes, vistos, strict=True):
        assert all(m < desde - HUECO for m in maximos.values())
    for area in AREAS:
        np.testing.assert_allclose(pred[area], tramo(locales[area], "validacion")["persistencia"])


def test_categorias_del_icen_segun_enfen():
    assert list(categoria_icen([-1.5, 0.0, 0.5, 1.2, 2.0, 3.98])) == [
        "fría", "neutra", "cálida débil", "cálida moderada", "cálida fuerte", "cálida extraordinaria"]
    assert categoria_icen([np.nan])[0] is None


def test_horas_de_mayor_demanda_por_anio_y_la_mascara(demanda):
    locales, _ = preparar_datasets(demanda, horizonte=2, variantes=["M0"])
    datos = locales["CENTRO"]
    horas = horas_mayor_demanda(datos, HUECO, n=3)
    assert set(horas) == {2024, 2025}
    assert horas[2025] == {19, 20, 21}  # el seno de la demanda sintética tiene su máximo a las 20 h
    pico = es_hora_pico(datos["DateTime"], horas, HUECO)
    assert pico.sum() == sum(((datos["DateTime"] + HUECO).dt.hour.isin(horas[anio])
                              & ((datos["DateTime"] + HUECO).dt.year == anio)).sum() for anio in horas)


def test_subestimacion_sobre_el_p90_de_la_referencia():
    real = np.full(100, 100.0)
    referencia = real - np.linspace(0, 10, 100)  # errores de 0 a 10: el p90 está en 9
    pred = real.copy()
    pred[:20] -= 9.5  # veinte periodos subestimados por encima del umbral
    assert subestimacion_sobre_p90(real, pred, referencia) == pytest.approx(0.2)
    assert subestimacion_sobre_p90(real, pred, referencia, mascara=np.arange(100) >= 20) == 0.0


def test_la_mejor_referencia_es_la_de_menor_mae():
    datos = pd.DataFrame({"real": [10.0, 10.0], "persistencia": [12.0, 8.0], "ayer": [10.5, 10.5],
                          "semana_pasada": [10.0, 13.0]})
    assert mejor_referencia(datos) == "ayer"
