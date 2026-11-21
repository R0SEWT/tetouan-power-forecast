"""El pipeline del SEIN de punta a punta, sobre capas sintéticas escritas en una carpeta temporal."""

import json

import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.modelado_sein import preparar_datasets
from tetouan_power_forecast.pipeline_sein import (
    CAPAS,
    VERSION,
    guardar,
    pipeline_sein,
    validar_demanda,
    verificar_regla_de_informacion,
)
from tetouan_power_forecast.variables_sein import AREAS


def _escribir_capas(raiz, fin="2026-02-15 00:00"):
    """De enero de 2024 a febrero de 2026: cruza los dos cortes de la partición, y la climatología de la temperatura
    (que sale de 2024) cubre todos los meses."""
    rng = np.random.default_rng(0)
    fechas = pd.date_range("2024-01-01 00:30", fin, freq="30min")
    hora = fechas.hour + fechas.minute / 60
    demanda = pd.DataFrame({"DateTime": fechas})
    for area, nivel in zip(AREAS, [1200.0, 4100.0, 1700.0], strict=True):
        demanda[area] = nivel * (1 + 0.2 * np.sin(2 * np.pi * (hora - 14) / 24)) + rng.normal(0, 10, len(fechas))
    demanda["SEIN"] = demanda[AREAS].sum(axis=1)
    horas = pd.date_range("2023-12-30", "2026-02-20", freq="h")
    temp = 20 + 3 * np.sin(2 * np.pi * (horas.hour - 15) / 24)
    tablas = {
        "demanda": demanda,
        "temperatura": pd.DataFrame({"fecha_hora": horas, "norte": temp + 5, "centro": temp, "sur": temp - 4}),
        "icen": pd.DataFrame({"mes": pd.date_range("2023-09-01", "2026-02-01", freq="MS"), "icen": 0.5}),
        "nino12": pd.DataFrame({"semana": pd.date_range("2023-12-06", "2026-02-20", freq="7D"),
                                "nino12_sst": 24.0, "nino12_ssta": 0.3}),
        "eventos": pd.DataFrame({"inicio": pd.to_datetime(["2025-03-05 10:00"]),
                                 "final": pd.to_datetime(["2025-03-05 11:00"])}),
    }
    for nombre, tabla in tablas.items():
        ruta = raiz / CAPAS[nombre]
        ruta.parent.mkdir(parents=True, exist_ok=True)
        tabla.to_parquet(ruta, index=False)
    return tablas


@pytest.fixture(scope="module")
def carpeta(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("datos")
    _escribir_capas(raiz)
    return raiz


@pytest.fixture(scope="module")
def resultado(carpeta):
    return pipeline_sein(carpeta)


def test_arma_los_dos_horizontes_por_area_y_global(resultado):
    assert set(resultado.datasets) == {"1h", "24h"}
    for partes in resultado.datasets.values():
        assert set(partes["locales"]) == set(AREAS)
        assert set(partes["global"]["area_cod"]) == {0, 1, 2}
        for datos in partes["locales"].values():
            assert {"entrenamiento", "validacion", "prueba"} <= set(datos["particion"])
            assert datos.drop(columns=["particion"]).notna().all().all()  # solo filas completas para M0 a M3


def test_da_lo_mismo_que_armar_los_datasets_a_mano(carpeta, resultado):
    tablas = {nombre: pd.read_parquet(carpeta / ruta) for nombre, ruta in CAPAS.items()}
    demanda = tablas.pop("demanda")
    locales, global_ = preparar_datasets(demanda, 48, feriados=resultado.feriados, **tablas)
    pd.testing.assert_frame_equal(global_, resultado.datasets["24h"]["global"])
    pd.testing.assert_frame_equal(locales["SUR"], resultado.datasets["24h"]["locales"]["SUR"])


def test_la_procedencia_identifica_la_corrida(carpeta, resultado):
    p = resultado.procedencia
    assert p["version_pipeline"] == VERSION
    assert set(p["capas"]) == set(CAPAS) and all(len(c["sha256"]) == 64 for c in p["capas"].values())
    assert p["calidad_demanda"]["periodos_faltantes"] == 0 and p["calidad_demanda"]["no_positivos"] == 0
    conteo = p["filas_por_particion"]["1h"]["CENTRO"]
    assert sum(conteo.values()) == len(resultado.datasets["1h"]["locales"]["CENTRO"])
    assert p["regla_de_informacion_verificada"]
    assert pipeline_sein(carpeta, horizontes=["1h"]).procedencia["capas"] == p["capas"]  # mismas capas, misma huella


def test_hasta_reproduce_una_corrida_con_los_datos_de_entonces(carpeta):
    recortado = pipeline_sein(carpeta, horizontes=["1h"], hasta="2026-01-31 23:30")
    assert recortado.demanda["DateTime"].max() == pd.Timestamp("2026-01-31 23:30")
    assert recortado.procedencia["calidad_demanda"]["hasta"] == "2026-01-31 23:30:00"
    assert recortado.datasets["1h"]["global"]["DateTime"].max() < pd.Timestamp("2026-01-31 23:30")


def test_guardar_escribe_datasets_y_procedencia(tmp_path, resultado):
    carpeta = guardar(resultado, tmp_path / "salida")
    leido = pd.read_parquet(carpeta / "1h_global.parquet")
    pd.testing.assert_frame_equal(leido, resultado.datasets["1h"]["global"])
    assert (carpeta / "24h_norte.parquet").exists()
    assert json.loads((carpeta / "procedencia.json").read_text())["version_pipeline"] == VERSION


def test_falta_una_capa(tmp_path):
    _escribir_capas(tmp_path)
    (tmp_path / CAPAS["icen"]).unlink()
    with pytest.raises(FileNotFoundError, match="icen"):
        pipeline_sein(tmp_path)


def test_la_validacion_corta_con_fechas_repetidas_o_columnas_faltantes(tmp_path):
    demanda = _escribir_capas(tmp_path)["demanda"]
    with pytest.raises(ValueError, match="repetidas"):
        validar_demanda(pd.concat([demanda, demanda.tail(1)]))
    with pytest.raises(ValueError, match="SUR"):
        validar_demanda(demanda.drop(columns="SUR"))
    hueco = validar_demanda(demanda.drop(index=[10, 11]))
    assert hueco["periodos_faltantes"] == 2


def test_detecta_una_temperatura_del_futuro(resultado):
    datos = resultado.datasets["1h"]["locales"]["NORTE"].copy()
    temperatura = resultado.exogenas["temperatura"]
    assert verificar_regla_de_informacion(datos, temperatura, "NORTE") == 200
    datos["temp"] = datos["temp"].shift(-2)  # la de una hora después: un dato que en t todavía no existía
    with pytest.raises(AssertionError, match="Regla de información"):
        verificar_regla_de_informacion(datos.dropna(subset=["temp"]), temperatura, "NORTE")
