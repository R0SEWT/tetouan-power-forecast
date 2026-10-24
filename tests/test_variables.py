import numpy as np
import pandas as pd
import pytest

from experimentos.historico import rolling as R
from tetouan_power_forecast.datos import ZONAS
from tetouan_power_forecast.variables import (
    CLIMA,
    ESCALA,
    REFERENCIAS,
    columnas_modelo,
    dataset_global,
    dataset_razon,
)


@pytest.fixture
def silver():
    """Siete semanas cada 10 minutos, alrededor del Ramadán, con ruido para que nada sea constante."""
    fechas = pd.date_range("2017-05-13", periods=7 * 1008, freq="10min")
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"DateTime": fechas})
    for c in CLIMA:
        df[c] = rng.normal(20, 3, len(fechas))
    hora = fechas.hour + fechas.minute / 60
    for z, nivel in enumerate([30_000, 20_000, 15_000]):
        df[ZONAS[z]] = nivel * (1 + 0.3 * np.sin(2 * np.pi * (hora - 14) / 24)) + rng.normal(0, 300, len(fechas))
    return df


def test_reproduce_las_variables_y_el_objetivo_de_v4_en_historico(silver):
    datos = dataset_razon(silver, zona=1)
    X, yobj, yt, base = R.features(silver, ZONAS[0], [ZONAS[1], ZONAS[2]], R.VARIANTES["V4_ratio_m24"])
    validas = X.notna().all(axis=1) & yobj.notna()
    X, yt, base = X[validas].reset_index(drop=True), yt[validas].reset_index(drop=True), base[validas]
    assert len(datos) == len(X)
    nombres = {f"{ZONAS[0]}_l0": "Zona_t", f"{ZONAS[1]}_l6": "Zone2_t_minus_6", "own_lag24h": "Zona_lag_24h",
               "own_lag1w_t": "Zona_lag_1w_t", "m24_level_rel": "Zona_m24_vs_m7d", "Ramadan": "Ramadan",
               "Feriado": "Feriado", "T_mean_24h": "T_mean_24h"}
    for viejo, nuevo in nombres.items():
        np.testing.assert_allclose(datos[nuevo], X[viejo], err_msg=nuevo)
    np.testing.assert_allclose(datos["real"], yt)
    np.testing.assert_allclose(datos[ESCALA], base["m24"])
    np.testing.assert_allclose(datos["semana_pasada"], base["semana"])
    # Mismas variables que V4, más la escala
    assert len(columnas_modelo(datos)) == X.shape[1] + 1


def test_el_ramadan_y_los_feriados_miran_la_fecha_de_t_mas_6(silver):
    datos = dataset_razon(silver, zona=1).set_index("DateTime")
    assert datos.loc["2017-05-26 23:00", "Ramadan"] == 1  # t+6 cae el 27 de mayo
    assert datos.loc["2017-05-26 22:50", "Ramadan"] == 0
    assert datos.loc["2017-06-25 23:50", "Ramadan"] == 0  # t+6 ya es 26 de junio
    assert datos.loc["2017-06-25 23:50", "Feriado"] == 1


def test_sin_huecos_ni_filas_sin_objetivo(silver):
    datos = dataset_razon(silver, zona=2)
    assert not datos.isna().any().any()
    assert datos["DateTime"].min() == pd.Timestamp("2017-05-20 00:00")  # una semana de historia
    assert datos["DateTime"].max() == silver["DateTime"].max() - pd.Timedelta(hours=1)
    assert not any(c.startswith("Zone2") for c in datos.columns)  # la propia zona es Zona_*
    assert {"Zone1_t", "Zone3_t_minus_2"} <= set(datos.columns)
    assert set(REFERENCIAS) <= set(datos.columns) and not set(REFERENCIAS) & set(columnas_modelo(datos))


def test_global_apila_las_tres_zonas_con_las_mismas_columnas(silver):
    datos = dataset_global(silver)
    assert datos.groupby("zona").size().nunique() == 1 and set(datos["zona"]) == {1, 2, 3}
    assert not any(c.startswith("Zone") for c in datos.columns)
    assert datos["DateTime"].is_monotonic_increasing
    zona3 = datos[datos["zona"] == 3].reset_index(drop=True)
    np.testing.assert_allclose(zona3["real"], dataset_razon(silver, zona=3)["real"])
