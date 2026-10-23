import json
from datetime import date, timedelta

import pandas as pd
import pytest

from tetouan_power_forecast.ceuta import (
    CLIMA,
    SERIE,
    bronze_ceuta,
    clima_ceuta,
    huecos_cortos_rellenos,
    parsear_respuesta,
    silver_ceuta,
)


def _jsonp(marcas, base=20.0):
    valores = [{"ts": ts, "dem": base + i * 0.01, "gas": 0.0, "die": 0.0} for i, ts in enumerate(marcas)]
    return "null(" + json.dumps({"valoresHorariosGeneracion": valores}) + ");"


def _respuesta_dia(dia):
    """Como REE: de las 21:00 del día anterior a las 04:00 del siguiente, cada 5 minutos, en hora local."""
    inicio = pd.Timestamp(dia) - pd.Timedelta(hours=3)
    marcas = pd.date_range(inicio, pd.Timestamp(dia) + pd.Timedelta(hours=28), freq="5min")
    return _jsonp([f"{m:%Y-%m-%d %H:%M}" for m in marcas])


def test_el_salto_de_marzo_queda_continuo_en_utc():
    marcas = ["2023-03-26 01:50", "2023-03-26 01:55", "2023-03-26 03:00", "2023-03-26 03:05"]
    df = parsear_respuesta(_jsonp(marcas))
    assert list(df["DateTime"].diff().dropna().unique()) == [pd.Timedelta("5min")]
    assert df["DateTime"].iloc[0] == pd.Timestamp("2023-03-26 00:50")  # UTC+1 en invierno


def test_la_hora_repetida_de_octubre_no_se_pisa():
    marcas = ["2023-10-29 01:55", "2023-10-29 02:00", "2023-10-29 02:05",
              "2023-10-29 02:00", "2023-10-29 02:05", "2023-10-29 03:00"]
    df = parsear_respuesta(_jsonp(marcas))
    assert not df["DateTime"].duplicated().any()
    assert df["DateTime"].is_monotonic_increasing
    assert df["DateTime"].iloc[1] == pd.Timestamp("2023-10-29 00:00")  # verano, UTC+2
    assert df["DateTime"].iloc[3] == pd.Timestamp("2023-10-29 01:00")  # invierno, UTC+1


def test_respuesta_con_formato_inesperado():
    with pytest.raises(ValueError, match="JSONP"):
        parsear_respuesta("<html>error</html>")


def test_bronze_guarda_por_mes_y_retoma_sin_repetir(tmp_path):
    pedidos = []

    def descargar(url):
        pedidos.append(url)
        return _respuesta_dia(url.rsplit("=", 1)[-1])

    bronze_ceuta(tmp_path, desde=date(2023, 1, 30), hasta=date(2023, 2, 2), descargar=descargar, pausa=0,
                 progreso=lambda texto: None)
    carpeta = tmp_path / "ceuta" / "bronze" / "demanda"
    assert sorted(p.name for p in carpeta.glob("*.jsonl")) == ["2023-01.jsonl", "2023-02.jsonl"]
    assert len(pedidos) == 4
    assert json.loads((carpeta / "procedencia.json").read_text())["aviso_legal"].startswith("https://www.ree.es")

    def falla(url):
        raise AssertionError("no debía volver a descargar")

    bronze_ceuta(tmp_path, desde=date(2023, 1, 30), hasta=date(2023, 2, 2), descargar=falla, pausa=0,
                 progreso=lambda texto: None)


@pytest.fixture
def raiz(tmp_path):
    desde, hasta = date(2023, 1, 2), date(2023, 1, 8)
    bronze_ceuta(tmp_path, desde=desde, hasta=hasta, descargar=lambda url: _respuesta_dia(url.rsplit("=", 1)[-1]),
                 pausa=0, progreso=lambda texto: None)
    horas = pd.date_range("2022-12-31", "2023-01-10", freq="h")
    clima = {"hourly": {"time": [f"{h:%Y-%m-%dT%H:%M}" for h in horas],
                        **{clave: [float(i) for i in range(len(horas))] for clave in CLIMA}}}
    clima_ceuta(tmp_path, desde=desde, hasta=hasta, descargar=lambda url: json.dumps(clima))
    return tmp_path


def test_silver_queda_cada_10_minutos_en_kw_con_clima(raiz):
    df = pd.read_parquet(silver_ceuta(raiz))
    assert list(df["DateTime"].diff().dropna().unique()) == [pd.Timedelta("10min")]
    assert df[SERIE].between(20_000, 60_000).all()  # 20 MW en la respuesta → kW
    assert not df[list(CLIMA.values())].isna().any().any()
    # El clima horario se interpola: a los 10 minutos de una hora vale un sexto más
    fila = df.set_index("DateTime").loc[pd.Timestamp("2023-01-05 00:10"), "Temperature"]
    previa = df.set_index("DateTime").loc[pd.Timestamp("2023-01-05 00:00"), "Temperature"]
    assert fila - previa == pytest.approx(1 / 6)
    assert "REVISAR" not in (raiz / "ceuta" / "silver" / "auditoria.md").read_text()


def test_huecos_cortos_se_rellenan_y_los_largos_no():
    serie = pd.Series([1.0, None, 3.0] + [None] * 8 + [12.0])
    rellena = huecos_cortos_rellenos(serie)
    assert rellena.iloc[1] == 2.0
    assert rellena.iloc[3:11].isna().all()


def test_el_dia_de_hoy_no_se_pide_por_defecto(tmp_path, monkeypatch):
    pedidos = []
    ayer = date.today() - timedelta(days=1)
    bronze_ceuta(tmp_path, desde=ayer, descargar=lambda url: pedidos.append(url) or _respuesta_dia(f"{ayer}"),
                 pausa=0, progreso=lambda texto: None)
    assert all(f"{date.today():%Y-%m-%d}" not in url for url in pedidos)


def test_ventanas_de_la_validacion_no_cruzan_al_verano():
    from experimentos.ceuta.validacion import ventanas

    fechas = pd.Series(pd.date_range("2020-01-01", "2023-09-30", freq="10min"))
    entrenamiento, prueba = ventanas(fechas, 2022)
    assert set(entrenamiento) == {"sin_verano", "1_anio", "2_anios"}  # 3 años pediría datos desde jul-2019
    assert fechas[prueba].min() == pd.Timestamp("2022-07-01") and fechas[prueba].max() < pd.Timestamp("2022-09-01")
    for tr in entrenamiento.values():
        assert fechas[tr].max() + pd.Timedelta(hours=1) < pd.Timestamp("2022-07-01")
    assert fechas[entrenamiento["sin_verano"]].min() == pd.Timestamp("2022-01-01")
    assert fechas[entrenamiento["2_anios"]].min() == pd.Timestamp("2020-07-01")


def test_la_hora_repetida_de_octubre_con_las_marcas_2a_y_2b_de_ree():
    marcas = ["2019-10-27 01:55", "2019-10-27 2A:00", "2019-10-27 2A:55",
              "2019-10-27 2B:00", "2019-10-27 2B:55", "2019-10-27 03:00"]
    df = parsear_respuesta(_jsonp(marcas))
    esperado = pd.to_datetime(["2019-10-26 23:55", "2019-10-27 00:00", "2019-10-27 00:55",
                               "2019-10-27 01:00", "2019-10-27 01:55", "2019-10-27 02:00"])
    assert list(df["DateTime"]) == list(esperado)  # 2A en horario de verano (UTC+2), 2B en invierno (UTC+1)


def test_una_marca_de_hora_desconocida_falla_diciendo_cual_es():
    with pytest.raises(ValueError, match="24:00"):
        parsear_respuesta(_jsonp(["2019-10-27 23:55", "2019-10-27 24:00"]))
