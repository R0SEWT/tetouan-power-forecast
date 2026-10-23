import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from tetouan_power_forecast.datos import PERIODOS_DIA, ZONAS, limpiar, nombre_objetivo
from tetouan_power_forecast.medallon import (
    PARTICIONES,
    auditar,
    bronze,
    gold,
    raiz_datos,
    silver,
    usar_drive,
)


def _csv_uci(n=3 * PERIODOS_DIA):
    """Un CSV con el formato de UCI: fechas sin ceros a la izquierda y dobles espacios."""
    fechas = pd.date_range("2017-01-01", periods=n, freq="10min")
    df = pd.DataFrame({
        "DateTime": [f"{f.month}/{f.day}/{f.year} {f.hour}:{f.minute:02d}" for f in fechas],
        "Temperature": 15.0,
        "Humidity": 70.0,
        "Wind Speed": 0.08,
        "general diffuse flows": 0.05,
        "diffuse flows": 0.1,
        "Zone 1 Power Consumption": np.linspace(30_000, 31_000, n),
        "Zone 2  Power Consumption": np.linspace(20_000, 21_000, n),
        "Zone 3  Power Consumption": np.linspace(17_000, 18_000, n),
    })
    return df.to_csv(index=False).encode()


@pytest.fixture
def raiz(tmp_path):
    contenido = _csv_uci()
    bronze(tmp_path, descargar=lambda url: contenido)
    return tmp_path


def test_bronze_guarda_el_csv_intacto_con_su_procedencia(raiz):
    csv = raiz / "bronze" / "uci849_tetouan.csv"
    procedencia = json.loads(csv.with_suffix(".json").read_text())
    assert csv.read_bytes() == _csv_uci()
    assert procedencia["sha256"] == hashlib.sha256(_csv_uci()).hexdigest()
    assert procedencia["licencia"] == "CC BY 4.0"


def test_bronze_no_vuelve_a_descargar(raiz):
    def falla(url):
        raise AssertionError("no debía descargar")

    bronze(raiz, descargar=falla)


def test_silver_pasa_la_auditoria_y_deja_el_reporte(raiz):
    df = pd.read_parquet(silver(raiz))
    assert list(df.columns)[6:] == ZONAS
    assert df["DateTime"].is_monotonic_increasing
    assert "FALLA" not in (raiz / "silver" / "auditoria.md").read_text()


def test_auditoria_detecta_huecos_duplicados_y_rangos():
    df = limpiar(pd.read_csv(pd.io.common.BytesIO(_csv_uci())))
    df = pd.concat([df.drop(index=10), df.iloc[[20]]]).sort_values("DateTime")
    df.loc[df.index[0], "Humidity"] = 140
    df.loc[df.index[1], "Zone 3 Power Consumption"] = 0
    fallas = set(auditar(df.reset_index(drop=True)).query("not ok")["chequeo"])
    assert fallas == {
        "Sin filas duplicadas",
        "Sin fechas repetidas",
        "Un registro cada 10 minutos, sin huecos",
        "Humidity entre 0 y 100",
        "Zone 3 Power Consumption > 0",
    }


def test_silver_corta_el_pipeline_si_la_auditoria_falla(tmp_path):
    malo = pd.read_csv(pd.io.common.BytesIO(_csv_uci()))
    malo.loc[5, "Humidity"] = -3
    bronze(tmp_path, descargar=lambda url: malo.to_csv(index=False).encode())
    with pytest.raises(ValueError, match="Humidity"):
        silver(tmp_path)
    assert not (tmp_path / "silver" / "tetouan_2017.parquet").exists()


def test_gold_marca_la_particion_cronologica(raiz):
    df = pd.read_parquet(gold(raiz))
    proporciones = df["particion"].value_counts(normalize=True)
    assert proporciones["entrenamiento"] == pytest.approx(0.70, abs=0.01)
    assert list(df["particion"].unique()) == list(PARTICIONES)  # en orden, sin mezclar


def test_gold_por_zona_usa_el_objetivo_de_esa_zona(raiz):
    df = pd.read_parquet(gold(raiz, zona=3))
    assert nombre_objetivo(3) in df.columns
    assert "Zone3_lag_24h" in df.columns and "Zone1_lag_24h" not in df.columns


@pytest.fixture
def colab(monkeypatch, tmp_path):
    """Simula google.colab.drive: montar no hace nada y "Mi unidad" vive en tmp_path."""
    import sys
    import types

    drive = types.SimpleNamespace(mount=lambda ruta: None)
    modulo = types.ModuleType("google.colab")
    modulo.drive = drive
    monkeypatch.setitem(sys.modules, "google.colab", modulo)
    monkeypatch.delenv("TETOUAN_DATA", raising=False)
    return tmp_path


def test_usar_drive_prefiere_la_carpeta_original(colab):
    (colab / "MyDrive" / "datalake" / "tetouan-power-forecast").mkdir(parents=True)
    (colab / "MyDrive" / "tetouan-power-forecast").mkdir()
    raiz = usar_drive(montaje=colab)
    assert raiz == colab / "MyDrive" / "datalake" / "tetouan-power-forecast"
    assert raiz_datos() == raiz


def test_usar_drive_encuentra_el_acceso_directo_compartido(colab):
    (colab / "MyDrive" / "tetouan-power-forecast").mkdir(parents=True)
    assert usar_drive(montaje=colab) == colab / "MyDrive" / "tetouan-power-forecast"


def test_usar_drive_fuera_de_colab_explica_que_hacer(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "google.colab", None)
    with pytest.raises(RuntimeError, match="rclone"):
        usar_drive()
