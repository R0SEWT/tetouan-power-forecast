import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.exogenas import saidi_disponible
from tetouan_power_forecast.variables_sein import (
    AREAS,
    columnas_variante,
    dataset_area,
    error_pronostico_diario,
    filas_comunes,
    particion,
)


@pytest.fixture
def demanda():
    """Tres semanas cada 30 minutos, con la marca al final del periodo, como el silver del IEOD."""
    fechas = pd.date_range("2025-03-01 00:30", periods=21 * 48, freq="30min")
    rng = np.random.default_rng(0)
    hora = fechas.hour + fechas.minute / 60
    df = pd.DataFrame({"DateTime": fechas})
    for area, nivel in zip(AREAS, [1200.0, 4100.0, 1700.0], strict=True):
        df[area] = nivel * (1 + 0.2 * np.sin(2 * np.pi * (hora - 14) / 24)) + rng.normal(0, 10, len(fechas))
    df["SEIN"] = df[AREAS].sum(axis=1)
    return df


@pytest.fixture
def temperatura():
    horas = pd.date_range("2025-02-28", "2025-03-25", freq="h")
    return pd.DataFrame({"fecha_hora": horas, "norte": np.arange(len(horas), dtype=float),
                         "centro": 20.0, "sur": 15.0})


def test_referencias_y_objetivo_a_1_h(demanda):
    datos = dataset_area(demanda, "CENTRO", horizonte=2)
    y = demanda["CENTRO"]
    assert np.allclose(datos["persistencia"], y)
    np.testing.assert_allclose(datos["real"], y.shift(-2))
    np.testing.assert_allclose(datos["ayer"], y.shift(46))
    np.testing.assert_allclose(datos["semana_pasada"], y.shift(334))
    assert {"Norte_t", "Sur_t_menos_2"} <= set(datos.columns) and "Centro_t" not in datos.columns


def test_a_24_h_ayer_es_la_persistencia(demanda):
    datos = dataset_area(demanda, "NORTE", horizonte=48)
    np.testing.assert_allclose(datos["ayer"], datos["persistencia"])
    np.testing.assert_allclose(datos["real"], demanda["NORTE"].shift(-48))


def test_la_temperatura_en_t_es_la_ultima_hora_ya_publicada(demanda, temperatura):
    datos = dataset_area(demanda, "NORTE", horizonte=2, temperatura=temperatura).set_index("DateTime")
    base = temperatura.set_index("fecha_hora")["norte"]
    assert datos.loc["2025-03-02 00:30", "temp"] == base["2025-03-02 00:00"]  # no la de las 01:00
    assert datos.loc["2025-03-02 01:00", "temp"] == base["2025-03-02 01:00"]
    # A 1 h no hay pronóstico de temperatura: temp_objetivo es la de t
    assert datos.loc["2025-03-02 00:30", "temp_objetivo"] == datos.loc["2025-03-02 00:30", "temp"]


def test_a_24_h_la_temperatura_pronosticada_lleva_un_error_por_dia(demanda, temperatura):
    sin_error = dataset_area(demanda, "NORTE", horizonte=48, temperatura=temperatura, error_temp_c=0)
    con_error = dataset_area(demanda, "NORTE", horizonte=48, temperatura=temperatura, error_temp_c=2.0)
    diferencia = (con_error["temp_objetivo"] - sin_error["temp_objetivo"]).round(9).groupby(
        con_error["DateTime"].dt.date)
    assert (diferencia.nunique() == 1).all()  # un mismo error en todo el día de emisión
    assert diferencia.first().std() > 0.5
    # El objetivo de las 00:30 de mañana se interpola entre las 00:00 y la 01:00
    fila = sin_error.set_index("DateTime").loc["2025-03-02 00:30"]
    base = temperatura.set_index("fecha_hora")["norte"]
    assert fila["temp_objetivo"] == pytest.approx((base["2025-03-03 00:00"] + base["2025-03-03 01:00"]) / 2)


def test_error_diario_reproducible():
    fechas = pd.date_range("2025-01-01", periods=96, freq="30min")
    a, b = error_pronostico_diario(fechas, 1.0, 3), error_pronostico_diario(fechas, 1.0, 3)
    np.testing.assert_array_equal(a, b)
    assert len(set(a[:48])) == 1 and a[0] != a[48]


def test_variantes_y_filas_comunes(demanda, temperatura):
    eventos = pd.DataFrame({"inicio": pd.to_datetime(["2025-03-05 10:00"]),
                            "final": pd.to_datetime(["2025-03-05 11:00"])})
    datos = dataset_area(demanda, "SUR", horizonte=2, temperatura=temperatura, eventos=eventos,
                         fin_climatologia="2025-03-15")
    m0, m3 = set(columnas_variante(datos, "M0")), set(columnas_variante(datos, "M3"))
    assert "temp" not in m0 and "fallas_en_curso" not in m0
    assert {"temp", "temp_anomalia", "fallas_en_curso"} <= m3
    assert "real" not in m3 and "media_24h" in m3
    comunes = filas_comunes(datos)
    assert not comunes[sorted(m3 | {"real", "persistencia", "ayer", "semana_pasada"})].isna().any().any()
    assert comunes.index.min() == 335  # la media de 7 días (336 periodos) recién está completa ahí


def test_particion_con_hueco():
    fechas = pd.date_range("2024-12-31 22:00", "2025-01-01 02:00", freq="30min")
    etiquetas = particion(fechas, horizonte=2)
    # t = 23:00 ya predice las 00:00 (fin del último periodo de 2024): va al hueco
    assert list(etiquetas) == ["entrenamiento"] * 2 + ["hueco"] * 2 + ["validacion"] * 5


def test_saidi_entra_segun_su_publicacion():
    saidi = pd.Series([1.0, 2.0, 3.0], index=pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]))
    serie = saidi_disponible(pd.to_datetime(["2026-05-03", "2026-05-08"]), saidi)
    assert serie.tolist() == [2.0, 3.0]  # el 3 de mayo todavía no salió marzo
