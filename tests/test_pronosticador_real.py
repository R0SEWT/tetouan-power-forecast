"""Pruebas del pronosticador real de la app, con capas sintéticas y modelos chicos."""

import warnings

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    from fastapi.testclient import TestClient

from app.backend.contrato import Escenario
from app.backend.main import crear_app
from app.backend.pronosticador import FRASE_M0_SIN_ESCENARIOS, Pronosticador
from app.backend.pronosticador_real import (
    GRUPOS_IMPORTANCIA,
    MEDIO,
    PronosticadorReal,
    _bootstrap_mae,
    carpeta_modelos,
    entrenar,
)

PEDIDO = {"area": "centro", "origen": "2026-01-20T15:00", "horizonte": "24h", "variante": "M3"}


def _capas(raiz):
    """Demanda de 2024 a febrero de 2026, que depende de la hora, el día y la temperatura, y sus exógenas."""
    rng = np.random.default_rng(0)
    fechas = pd.date_range("2024-01-01 00:30", "2026-03-01 00:00", freq="30min")
    hora = fechas.hour + fechas.minute / 60
    horas = pd.date_range("2023-12-31", "2026-03-05", freq="h")
    temp_hora = 20 + 4 * np.sin(2 * np.pi * (horas.day_of_year - 45) / 365) + 3 * np.sin(2 * np.pi * (horas.hour - 15) / 24)
    temperatura = pd.DataFrame({"fecha_hora": horas, "norte": temp_hora + 5, "centro": temp_hora, "sur": temp_hora - 4})
    temp_periodo = pd.Series(temp_hora, index=horas).reindex(fechas, method="ffill").to_numpy()
    demanda = pd.DataFrame({"DateTime": fechas})
    for area, nivel in [("NORTE", 1000.0), ("CENTRO", 4000.0), ("SUR", 1700.0)]:
        diario = 1 + 0.15 * np.sin(2 * np.pi * (hora - 14) / 24)
        domingo = np.where(fechas.day_of_week == 6, 0.9, 1.0)
        calor = 1 + 0.01 * np.maximum(temp_periodo - 20, 0)
        demanda[area] = nivel * diario * domingo * calor + rng.normal(0, nivel * 0.005, len(fechas))
    demanda["SEIN"] = demanda[["NORTE", "CENTRO", "SUR"]].sum(axis=1)
    (raiz / "coes" / "silver").mkdir(parents=True)
    demanda.to_parquet(raiz / "coes" / "silver" / "demanda_areas.parquet", index=False)
    meses = pd.date_range("2023-08-01", "2026-02-01", freq="MS")
    semanas = pd.date_range("2023-12-06", "2026-03-05", freq="7D")
    inicios = pd.to_datetime(rng.choice(fechas[:-100], 200, replace=False))
    exogenas = {
        "temperatura_areas": temperatura,
        "icen": pd.DataFrame({"mes": meses, "icen": np.linspace(-0.5, 2.0, len(meses))}),
        "nino12_semanal": pd.DataFrame({"semana": semanas, "nino12_sst": 24.0, "nino12_ssta": 0.3}),
        "eventos_coes": pd.DataFrame({"inicio": inicios, "final": inicios + pd.Timedelta(hours=2)}),
    }
    (raiz / "exogenas" / "silver").mkdir(parents=True)
    for nombre, tabla in exogenas.items():
        tabla.to_parquet(raiz / "exogenas" / "silver" / f"{nombre}.parquet", index=False)
    adaptacion = pd.DataFrame([
        {"Horizonte": "24h", "Política": politica, "Variante": v, "Área": "Centro", "MAE (MW)": mae}
        for politica, v, mae in [("fijo", "M0", 80.0), ("fijo", "M3", 81.0), ("semanal", "M0", 79.0),
                                 ("semanal", "M3", 78.5), ("alerta ENFEN", "M3", 79.5), ("semanal + alerta", "M3", 78.4)]])
    (raiz / "reportes" / "sein" / "prueba_2026").mkdir(parents=True)
    adaptacion.to_csv(raiz / "reportes" / "sein" / "prueba_2026" / "adaptacion.csv", index=False)


@pytest.fixture(scope="module")
def pronosticador(tmp_path_factory):
    raiz = tmp_path_factory.mktemp("datos")
    _capas(raiz)
    entrenar(raiz, hiperparametros={"n_estimators": 20, "max_depth": 4, "learning_rate": 0.3}, progreso=lambda *_: None)
    return PronosticadorReal(raiz)


@pytest.fixture(scope="module")
def cliente(pronosticador):
    return TestClient(crear_app(pronosticador))


def test_cumple_el_protocolo_y_conoce_su_rango(pronosticador):
    assert isinstance(pronosticador, Pronosticador)
    assert pronosticador.modelo == "XGBoost global"
    assert pronosticador.fecha_min.isoformat() == "2025-01-01"
    assert pd.Timestamp("2026-02-20") <= pd.Timestamp(pronosticador.fecha_max) < pd.Timestamp("2026-03-01")


@pytest.mark.parametrize("horizonte", ["1h", "24h"])
@pytest.mark.parametrize("variante", ["M0", "M3"])
def test_series_de_un_dia(cliente, horizonte, variante):
    r = cliente.get("/series/norte", params={"fecha": "2025-07-14", "horizonte": horizonte, "variante": variante})
    assert r.status_code == 200
    s = r.json()
    for campo in ("fecha_hora", "real", "pronostico", "referencia", "hueco", "preliminar"):
        assert len(s[campo]) == 48, campo
    assert s["fecha_hora"][0] == "2025-07-14T00:00" and s["fecha_hora"][-1] == "2025-07-14T23:30"
    assert s["programacion_diaria"] is None
    assert s["referencia_nombre"] in {"persistencia", "ayer", "semana_pasada"}
    assert not any(s["hueco"])
    inferior, superior = s["intervalo"]["inferior"], s["intervalo"]["superior"]
    assert all(a <= p <= b for a, p, b in zip(inferior, s["pronostico"], superior, strict=True))
    mape = np.mean(np.abs(np.array(s["pronostico"]) / np.array(s["real"]) - 1))
    assert mape < 0.1  # pronostica la demanda, no otra cosa


def test_cada_periodo_se_pronostica_con_la_fila_emitida_h_pasos_antes():
    inicios = pd.date_range("2026-01-20 15:30", periods=3, freq="30min")
    # el periodo de 15:30 a 16:00 termina a las 16:00: a 1 h se pronostica desde las 15:00, a 24 h desde el día antes
    assert list(PronosticadorReal._emision(inicios, "1h")) == list(inicios + MEDIO - pd.Timedelta(hours=1))
    assert list(PronosticadorReal._emision(inicios, "24h")) == list(inicios + MEDIO - pd.Timedelta(hours=24))


@pytest.mark.parametrize(("horizonte", "pasos"), [("1h", 2), ("24h", 48)])
def test_pronostico_desde_un_origen(cliente, pronosticador, horizonte, pasos):
    r = cliente.post("/pronostico", json=PEDIDO | {"horizonte": horizonte})
    assert r.status_code == 200
    p = r.json()
    assert len(p["pronostico"]) == pasos and p["fecha_hora"][0] == "2026-01-20T15:30"
    assert all(i <= x <= s for i, x, s in zip(p["intervalo"]["inferior"], p["pronostico"], p["intervalo"]["superior"],
                                              strict=True))
    assert p["frase"]
    # Regla de información: ninguna fila usada es posterior a lo que se conocía en el origen
    _, filas = pronosticador._filas_desde_origen("centro", pd.Timestamp("2026-01-20 15:00"), horizonte)
    assert filas.index.max() == pd.Timestamp("2026-01-20 15:30")


def test_el_escenario_cambia_las_variables_de_m3():
    filas = pd.DataFrame({"temp_objetivo": [20.0, 21.0], "icen": [1.5, 1.5], "nino12_ssta": [0.8, 0.8],
                          "fallas_en_curso": [2.0, 0.0], "Area_t": [1.0, 1.1]})
    cambiadas = PronosticadorReal._aplicar_escenario(filas, Escenario(delta_temp_c=2, nino="neutro", falla="ninguna"))
    assert list(cambiadas["temp_objetivo"]) == [22.0, 23.0]
    assert (cambiadas[["icen", "nino12_ssta", "fallas_en_curso"]] == 0).all().all()
    assert list(cambiadas["Area_t"]) == [1.0, 1.1] and list(filas["temp_objetivo"]) == [20.0, 21.0]


def test_m0_ignora_el_escenario(cliente):
    escenario = {"delta_temp_c": 4, "nino": "neutro", "falla": "ninguna"}
    base = cliente.post("/pronostico", json=PEDIDO | {"variante": "M0"}).json()
    con = cliente.post("/pronostico", json=PEDIDO | {"variante": "M0", "escenario": escenario}).json()
    assert con["pronostico"] == base["pronostico"] and con["frase"] == FRASE_M0_SIN_ESCENARIOS


def test_escenario_a_1_h_no_se_permite(cliente):
    r = cliente.post("/pronostico", json=PEDIDO | {"horizonte": "1h", "escenario": {"delta_temp_c": 2}})
    assert r.status_code == 422


@pytest.mark.parametrize(("variable", "n"), [("temperatura", 13), ("icen", 13)])
def test_sensibilidad(cliente, variable, n):
    s = cliente.post("/sensibilidad", json={"area": "sur", "origen": "2026-01-20T15:00", "variable": variable}).json()
    assert len(s["valores"]) == len(s["pronostico"]) == n


def test_resumen_con_las_metricas_de_2026(cliente):
    r = cliente.get("/resumen").json()
    assert set(r["metricas_prueba"]) == {"norte", "centro", "sur"}
    assert all(m["mae_mw"] > 0 and 0 < m["mape_pct"] < 20 for m in r["metricas_prueba"].values())
    assert r["regimen_nino"]["estado"] in {"neutro", "debil", "moderado", "fuerte", "extraordinario"}
    assert r["fechas_corte"]["prueba_hasta"] < "2026-03-01"


def test_diagnostico(cliente):
    d = cliente.get("/diagnostico/centro").json()
    assert [a["variante"] for a in d["ablacion"]] == ["M0", "M1", "M2", "M3"]
    assert all(a["ic_inf"] <= a["mae"] <= a["ic_sup"] for a in d["ablacion"])
    assert {(a["politica"], a["exogenas"]) for a in d["adaptacion"]} == {
        ("fijo", False), ("fijo", True), ("semanal", False), ("semanal", True), ("alerta_enfen", True)}
    assert {i["variable"] for i in d["importancias"]} >= {"demanda_reciente", "calendario", "clima"}
    assert len(d["residuos"]["real"]) == len(d["residuos"]["predicho"]) > 0
    assert cliente.get("/diagnostico/norte").json()["adaptacion"] == []  # sin filas del Norte en la tabla


def test_fecha_fuera_del_rango_con_datos(cliente, pronosticador):
    despues = (pd.Timestamp(pronosticador.fecha_max) + pd.Timedelta(days=1)).date().isoformat()
    r = cliente.get("/series/centro", params={"fecha": despues})
    assert r.status_code == 422
    assert pronosticador.fecha_max.isoformat() in r.json()["detail"]


def test_sin_modelos_entrenados_lo_dice(tmp_path):
    with pytest.raises(FileNotFoundError, match="entrenar"):
        PronosticadorReal(tmp_path)


def test_el_bootstrap_ignora_los_dias_sin_datos():
    dias = np.repeat(np.arange(10), 4)
    error = np.full(40, 10.0)
    error[:4] = np.nan  # el primer día no tiene ningún pronóstico válido
    bajo, alto = _bootstrap_mae(error, dias, np.random.default_rng(0))
    assert bajo == alto == 10.0  # con días en cero, el intervalo bajaría de 10


def test_entrenar_publica_la_carpeta_entera(pronosticador):
    carpeta = carpeta_modelos(pronosticador._raiz)
    vecinos = sorted(x.name for x in carpeta.parent.iterdir())
    assert vecinos == ["app"]  # ni temporales ni la anterior
    assert len(list(carpeta.glob("xgboost_global_*.joblib"))) == 6 and (carpeta / "metadatos.json").exists()


def test_la_escala_no_cuenta_como_variable_en_la_importancia():
    assert not any("media_24h" in variables for variables in GRUPOS_IMPORTANCIA.values())


# ---- modelo híbrido -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def hibrido(pronosticador):
    """Un "fundacional" sintético (lo real más ruido) desde febrero de 2024 y el apilado entrenado con él."""
    from app.backend.pronosticador_hibrido import (
        PronosticadorHibrido,
        entrenar_hibrido,
        ruta_fundacional,
    )

    raiz = pronosticador._raiz
    rng = np.random.default_rng(1)
    piezas = []
    for area, serie in pronosticador._real.items():
        origenes = serie.index[(serie.index >= "2024-02-01") & (serie.index < "2026-02-20")]
        fila = {"DateTime": origenes, "area": area.upper()}
        for h in (2, 48):
            pred = serie.reindex(origenes + h * pd.Timedelta(minutes=30)).to_numpy() * (1 + rng.normal(0, 0.01, len(origenes)))
            fila[f"pred_{h}"], fila[f"q10_{h}"], fila[f"q90_{h}"] = pred, pred * 0.98, pred * 1.02
        piezas.append(pd.DataFrame(fila))
    todo = pd.concat(piezas, ignore_index=True).dropna()
    ruta = ruta_fundacional(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    todo[todo["DateTime"] < "2025-01-01"].to_parquet(ruta.with_name(ruta.stem + "_train.parquet"), index=False)
    todo[todo["DateTime"] >= "2025-01-01"].to_parquet(ruta, index=False)
    entrenar_hibrido(raiz, hiperparametros={"n_estimators": 20, "max_depth": 4, "learning_rate": 0.3},
                     progreso=lambda *_: None)
    return PronosticadorHibrido(pronosticador)


@pytest.fixture(scope="module")
def cliente_dos(pronosticador, hibrido):
    return TestClient(crear_app(pronosticador, [hibrido]))


def test_modelos_lista_el_base_primero_y_el_hibrido(cliente_dos, hibrido):
    modelos = cliente_dos.get("/modelos").json()
    assert [m["id"] for m in modelos] == ["XGBoost global", "hibrido"]
    assert modelos[1]["variantes"] == ["M0"]
    assert modelos[1]["fecha_min"] == "2025-01-02" == hibrido.fecha_min.isoformat()


def test_sin_parametro_modelo_responde_el_base(cliente_dos, cliente):
    ruta = "/series/centro?fecha=2026-01-15&horizonte=24h&variante=M0"
    assert cliente_dos.get(ruta).json() == cliente.get(ruta).json()


@pytest.mark.parametrize("horizonte", ["1h", "24h"])
def test_serie_del_hibrido_usa_el_fundacional_del_origen_correcto(cliente_dos, hibrido, horizonte):
    r = cliente_dos.get(f"/series/centro?fecha=2026-01-15&horizonte={horizonte}&modelo=hibrido")
    assert r.status_code == 200
    serie = r.json()
    inicios = pd.to_datetime(serie["fecha_hora"])
    emision = hibrido._emision(inicios, horizonte)
    filas = hibrido._datos[horizonte]["centro"].reindex(emision)
    esperado = hibrido._predecir_filas(horizonte, "M0", filas)
    assert np.allclose(serie["pronostico"], np.round(esperado, 1))
    # El fundacional sintético casi acierta lo real, así que el híbrido debe quedar cerca de lo real
    real = np.array(serie["real"], dtype=float)
    assert np.mean(np.abs(np.array(serie["pronostico"]) - real)) < 0.03 * real.mean()
    assert all(i <= p <= s for i, p, s in zip(serie["intervalo"]["inferior"], serie["pronostico"],
                                              serie["intervalo"]["superior"], strict=True))


def test_pronostico_del_hibrido_ignora_variante_y_escenario(cliente_dos):
    pedido = {"area": "sur", "origen": "2026-01-15T10:00", "horizonte": "24h", "modelo": "hibrido"}
    base = cliente_dos.post("/pronostico", json={**pedido, "variante": "M0"}).json()
    con_calor = cliente_dos.post("/pronostico", json={**pedido, "variante": "M3", "escenario": {"delta_temp_c": 4}}).json()
    assert len(base["pronostico"]) == 48
    assert con_calor["pronostico"] == base["pronostico"]
    assert con_calor["frase"] == FRASE_M0_SIN_ESCENARIOS


def test_hibrido_fuera_de_su_rango_y_modelo_desconocido(cliente_dos):
    r = cliente_dos.get("/series/centro?fecha=2025-01-01&horizonte=24h&modelo=hibrido")
    assert r.status_code == 422 and "2025-01-02" in r.json()["detail"]
    assert cliente_dos.get("/series/centro?fecha=2026-01-15&modelo=otro").status_code == 404
    pedido = {"area": "centro", "origen": "2026-01-15T10:00", "horizonte": "1h", "modelo": "otro"}
    assert cliente_dos.post("/pronostico", json=pedido).status_code == 404


def test_resumen_y_diagnostico_del_hibrido(cliente_dos):
    resumen = cliente_dos.get("/resumen?modelo=hibrido").json()
    assert resumen["modelo"].startswith("Híbrido") and resumen["fechas_corte"]["disponible_desde"] == "2025-01-02"
    d = cliente_dos.get("/diagnostico/centro?modelo=hibrido").json()
    assert [a["variante"] for a in d["ablacion"]] == ["M0", "M3", "hibrido"]
    assert all(a["ic_inf"] <= a["mae"] <= a["ic_sup"] for a in d["ablacion"])
    assert {i["variable"] for i in d["importancias"]} == {"demanda_reciente", "calendario", "fundacional"}
    assert d["adaptacion"] == [] and len(d["residuos"]["real"]) > 100


def test_sensibilidad_del_hibrido_es_plana(cliente_dos):
    pedido = {"area": "centro", "origen": "2026-01-15T10:00", "variable": "temperatura", "modelo": "hibrido"}
    pronostico = cliente_dos.post("/sensibilidad", json=pedido).json()["pronostico"]
    assert len(set(pronostico)) == 1


# ---- modelo combinado -----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def combinado(hibrido):
    """Un "fundacional ajustado" sintético con sesgo de +2 %: la mezcla debe caer entre sus dos piezas."""
    from app.backend.pronosticador_hibrido import PronosticadorCombinado, ruta_ajustado

    piezas = []
    for area, serie in hibrido._real.items():
        origenes = serie.index[(serie.index >= "2025-01-01") & (serie.index < "2026-02-20")]
        fila = {"DateTime": origenes, "area": area.upper()}
        for h in (2, 48):
            pred = serie.reindex(origenes + h * pd.Timedelta(minutes=30)).to_numpy() * 1.02
            fila[f"pred_{h}"], fila[f"q10_{h}"], fila[f"q90_{h}"] = pred, pred * 0.98, pred * 1.02
        piezas.append(pd.DataFrame(fila))
    pd.concat(piezas, ignore_index=True).dropna().to_parquet(ruta_ajustado(hibrido._raiz), index=False)
    return PronosticadorCombinado(hibrido)


@pytest.fixture(scope="module")
def cliente_tres(pronosticador, hibrido, combinado):
    return TestClient(crear_app(pronosticador, [hibrido, combinado]))


@pytest.mark.parametrize(("horizonte", "area"), [("1h", "norte"), ("24h", "centro"), ("24h", "sur")])
def test_el_combinado_mezcla_con_el_peso_del_area_y_el_horizonte(cliente_tres, combinado, hibrido, horizonte, area):
    ruta = f"/series/{area}?fecha=2026-01-15&horizonte={horizonte}"
    mezcla = np.array(cliente_tres.get(f"{ruta}&modelo=combinado").json()["pronostico"])
    del_hibrido = np.array(cliente_tres.get(f"{ruta}&modelo=hibrido").json()["pronostico"])
    inicios = pd.date_range("2026-01-15", periods=48, freq="30min")
    paso = {"1h": 2, "24h": 48}[horizonte]
    # el ajustado sintético es lo real × 1.02, emitido H pasos antes del final de cada periodo
    ajustado = combinado._real[area].reindex(inicios + pd.Timedelta(minutes=30)).to_numpy() * 1.02
    peso = combinado.pesos[horizonte][area]
    assert np.allclose(mezcla, peso * ajustado + (1 - peso) * del_hibrido, atol=0.11)
    filas = combinado._datos[horizonte][area].reindex(combinado._emision(inicios, horizonte))
    assert np.allclose(combinado._predecir_ajustado(horizonte, filas), ajustado)
    assert paso == len(cliente_tres.post("/pronostico", json={
        "area": area, "origen": "2026-01-15T10:00", "horizonte": horizonte, "modelo": "combinado"}).json()["pronostico"])


def test_modelos_y_diagnostico_del_combinado(cliente_tres):
    modelos = cliente_tres.get("/modelos").json()
    assert [m["id"] for m in modelos] == ["XGBoost global", "hibrido", "combinado"]
    assert [m["nombre"] for m in modelos] == ["Base (XGBoost)", "Híbrido (XGBoost + Simons)", "Combinado (recomendado)"]
    d = cliente_tres.get("/diagnostico/centro?modelo=combinado").json()
    assert [a["variante"] for a in d["ablacion"]] == ["M0", "hibrido", "ajustado", "combinado"]
    assert {i["variable"] for i in d["importancias"]} == {"ajustado", "hibrido"}
    resumen = cliente_tres.get("/resumen?modelo=combinado").json()
    assert set(resumen["metricas_prueba"]) == {"norte", "centro", "sur"}


# ---- pesos del combinado en un archivo -----------------------------------------------------------


def test_sin_archivo_de_pesos_usa_los_del_notebook_04(tmp_path):
    from app.backend.pronosticador_hibrido import PESOS_POR_DEFECTO, leer_pesos

    pesos, origen = leer_pesos(tmp_path)
    assert pesos == PESOS_POR_DEFECTO and pesos["24h"]["centro"] == 0.85
    assert "2025" in origen and "por defecto" in origen


def test_guardar_pesos_lee_la_tabla_del_notebook_04(tmp_path):
    from app.backend.pronosticador_hibrido import guardar_pesos, leer_pesos, ruta_tabla_pesos

    tabla = ruta_tabla_pesos(tmp_path)
    tabla.parent.mkdir(parents=True)
    filas = [{"Horizonte": h, "Área": a, "Peso del primero": w, "Primero": "x", "Segundo": "y"}
             for h, a, w in [("1h", "Norte", 0.35000000000000003), ("1h", "Centro", 0.5), ("1h", "Sur", 0.6),
                             ("24h", "Norte", 0.7000000000000001), ("24h", "Centro", 0.8), ("24h", "Sur", 0.9)]]
    pd.DataFrame(filas).to_csv(tabla, index=False)
    ruta = guardar_pesos(tmp_path)
    pesos, origen = leer_pesos(tmp_path)
    assert pesos["1h"] == {"norte": 0.35, "centro": 0.5, "sur": 0.6}
    assert pesos["24h"] == {"norte": 0.7, "centro": 0.8, "sur": 0.9}
    assert "validación de 2025" in origen and ruta.name == "combinado.json"


def test_pesos_invalidos_se_rechazan(tmp_path):
    import json

    from app.backend.pronosticador_hibrido import leer_pesos, ruta_pesos

    ruta = ruta_pesos(tmp_path)
    ruta.parent.mkdir(parents=True)
    ruta.write_text(json.dumps({"pesos_ajustado": {"1h": {"norte": 1.4, "centro": 0.5, "sur": 0.5},
                                                   "24h": {"norte": 0.5, "centro": 0.5, "sur": 0.5}}}))
    with pytest.raises(ValueError, match="fuera de 0-1"):
        leer_pesos(tmp_path)
    ruta.write_text(json.dumps({"pesos_ajustado": {"1h": {"norte": 0.5}}}))
    with pytest.raises(ValueError, match="peso numérico"):
        leer_pesos(tmp_path)


def test_el_combinado_usa_los_pesos_del_archivo(hibrido):
    import json

    from app.backend.pronosticador_hibrido import PronosticadorCombinado, ruta_pesos

    ruta = ruta_pesos(hibrido._raiz)
    pesos = {"1h": {"norte": 0.1, "centro": 0.2, "sur": 0.3}, "24h": {"norte": 0.4, "centro": 0.5, "sur": 0.6}}
    ruta.write_text(json.dumps({"pesos_ajustado": pesos, "origen": "prueba"}))
    try:
        otro = PronosticadorCombinado(hibrido)
    finally:
        ruta.unlink()
    assert otro.pesos == pesos and otro.origen_pesos == "prueba"
    s = otro.serie("centro", pd.Timestamp("2026-01-15").date(), "24h", "M0")
    assert [c.peso for c in s.componentes] == [0.5, 0.5]


# ---- el combinado por defecto, con respaldo en el base ------------------------------------------


@pytest.fixture(scope="module")
def cliente_defecto(pronosticador, hibrido, combinado):
    """Como en la app con los datos reales: el combinado primero y el base como respaldo."""
    return TestClient(crear_app(combinado, [pronosticador, hibrido]))


def test_modelos_con_el_combinado_primero_y_su_respaldo(cliente_defecto):
    modelos = cliente_defecto.get("/modelos").json()
    assert [m["id"] for m in modelos] == ["combinado", "XGBoost global", "hibrido"]
    assert [m["respaldo"] for m in modelos] == ["XGBoost global", None, "XGBoost global"]


def test_sin_modelo_responde_el_combinado_dentro_de_su_rango(cliente_defecto):
    ruta = "/series/centro?fecha=2026-01-15&horizonte=24h&variante=M3"
    s = cliente_defecto.get(ruta).json()
    assert s["modelo"] == "combinado"
    assert s == cliente_defecto.get(f"{ruta}&modelo=combinado").json()
    p = cliente_defecto.post("/pronostico", json=PEDIDO | {"origen": "2026-01-15T10:00"}).json()
    assert p["modelo"] == "combinado"


def test_sin_modelo_fuera_del_rango_responde_el_base_y_lo_dice(cliente_defecto, combinado):
    assert combinado.fecha_min.isoformat() == "2025-01-02"
    ruta = "/series/centro?fecha=2025-01-01&horizonte=24h&variante=M3"
    s = cliente_defecto.get(ruta).json()
    assert s["modelo"] == "XGBoost global" and s["componentes"] is None
    assert s == cliente_defecto.get(f"{ruta}&modelo=XGBoost global").json()
    p = cliente_defecto.post("/pronostico", json=PEDIDO | {"origen": "2025-01-01T10:00"}).json()
    assert p["modelo"] == "XGBoost global"
    # Pedido a mano, el combinado no inventa: fuera de su rango responde 422
    r = cliente_defecto.get(f"{ruta}&modelo=combinado")
    assert r.status_code == 422 and "2025-01-02" in r.json()["detail"]


def test_la_ficha_del_combinado_suma_sus_piezas(cliente_defecto, combinado):
    s = cliente_defecto.get("/series/sur?fecha=2026-01-20&horizonte=24h").json()
    ajustado, hibrido = s["componentes"]
    assert (ajustado["id"], hibrido["id"]) == ("ajustado", "hibrido")
    assert ajustado["peso"] == combinado.pesos["24h"]["sur"] and round(ajustado["peso"] + hibrido["peso"], 6) == 1
    suma = [ajustado["peso"] * a + hibrido["peso"] * h for a, h in zip(ajustado["valores"], hibrido["valores"], strict=True)]
    assert np.allclose(suma, s["pronostico"], atol=0.11)  # cada número va redondeado a 0.1 MW


# ---- seguimiento del error y de la cobertura en 2026 ---------------------------------------------


@pytest.mark.parametrize("horizonte", ["1h", "24h"])
def test_seguimiento_mes_a_mes(cliente_defecto, horizonte):
    r = cliente_defecto.get(f"/seguimiento/centro?horizonte={horizonte}&modelo=XGBoost global")
    assert r.status_code == 200
    s = r.json()
    assert s["horizonte"] == horizonte and s["meta_cobertura_pct"] == 90
    assert [m["mes"] for m in s["meses"]] == ["2026-01", "2026-02"]
    assert s["total"]["mes"] == "2026" and s["total"]["periodos"] == sum(m["periodos"] for m in s["meses"])
    ponderado = sum(m["mae_modelo"] * m["periodos"] for m in s["meses"]) / s["total"]["periodos"]
    assert abs(ponderado - s["total"]["mae_modelo"]) < 0.1
    assert all(0 <= m["cobertura_pct"] <= 100 and m["mae_referencia"] > 0 for m in s["meses"])


def test_el_seguimiento_coincide_con_el_error_de_2026(cliente_defecto):
    """El total es el mismo error de 2026 del resumen (base, 24 h, M3) y del diagnóstico (combinado)."""
    base = cliente_defecto.get("/seguimiento/norte?modelo=XGBoost global").json()["total"]
    resumen = cliente_defecto.get("/resumen?modelo=XGBoost global").json()["metricas_prueba"]["norte"]
    assert base["mae_modelo"] == resumen["mae_mw"]
    total = cliente_defecto.get("/seguimiento/centro").json()["total"]
    diagnostico = cliente_defecto.get("/diagnostico/centro").json()["ablacion"]
    assert total["mae_modelo"] == next(a["mae"] for a in diagnostico if a["variante"] == "combinado")


def test_la_cobertura_es_la_del_rango_que_muestra_la_serie(combinado):
    s = combinado.seguimiento("centro", "1h", "M0")
    dentro = n = 0
    for dia in pd.date_range("2026-01-01", combinado.fecha_max, freq="D"):
        serie = combinado.serie("centro", dia.date(), "1h", "M0")
        for real, inf, sup in zip(serie.real, serie.intervalo.inferior, serie.intervalo.superior, strict=True):
            if real is not None:
                n, dentro = n + 1, dentro + (inf <= real <= sup)
    assert abs(100 * dentro / n - s.total.cobertura_pct) < 1.0


# ---- pico y rampa de las próximas 24 h -----------------------------------------------------------


def test_pico_y_rampa_salen_del_pronostico_a_24_h(cliente_defecto):
    r = cliente_defecto.get("/pico/centro?origen=2026-01-15T10:00")
    assert r.status_code == 200
    pr = r.json()
    p = cliente_defecto.post("/pronostico", json=PEDIDO | {"origen": "2026-01-15T10:00"}).json()
    assert pr["modelo"] == p["modelo"] == "combinado"
    assert (pr["desde"], pr["hasta"]) == (p["fecha_hora"][0], p["fecha_hora"][-1])
    j = int(np.argmax(p["pronostico"]))
    assert pr["pico"] == {"fecha_hora": p["fecha_hora"][j], "valor": p["pronostico"][j],
                          "inferior": p["intervalo"]["inferior"][j], "superior": p["intervalo"]["superior"][j]}
    subidas = np.array(p["pronostico"][2:]) - np.array(p["pronostico"][:-2])
    k = int(np.argmax(subidas))
    assert pr["rampa"]["subida_mw"] == pytest.approx(subidas[k], abs=0.05)
    assert (pr["rampa"]["desde"], pr["rampa"]["hasta"]) == (p["fecha_hora"][k], p["fecha_hora"][k + 2])
    assert pr["rampa"]["umbral_mw"] > 0 and pr["rampa"]["fuerte"] == (pr["rampa"]["subida_mw"] > pr["rampa"]["umbral_mw"])
    acierto = pr["acierto"]
    assert acierto["dias"] > 30 and 0 <= acierto["pct_hora"] <= 100 and acierto["mae_pico_mw"] >= 0


def test_el_acierto_del_pico_es_el_de_las_series_del_dia(combinado):
    """La cifra que muestra la app (y escribe el script) sale de las mismas series del día que dibuja."""
    a = combinado.acierto_pico("norte")
    aciertos = dias = 0
    for dia in pd.date_range("2026-01-01", combinado.fecha_max, freq="D"):
        s = combinado.serie("norte", dia.date(), "24h", "M0")
        if any(x is None for x in s.real):
            continue
        dias += 1
        aciertos += abs(int(np.argmax(s.pronostico)) - int(np.argmax(s.real))) <= 2
    assert a.dias == dias and a.pct_hora == pytest.approx(100 * aciertos / dias, abs=0.05)


def test_el_script_del_pico_tabula_cada_modelo_y_area(pronosticador, hibrido, combinado):
    from experimentos.sein.pico_2026 import tabla

    t = tabla([combinado, pronosticador, hibrido])
    assert len(t) == 9 and set(t["Área"]) == {"Norte", "Centro", "Sur"}
    fila = t[(t["Modelo"] == combinado.nombre) & (t["Área"] == "Centro")].iloc[0]
    assert fila["Hora del máximo a ±1 h (%)"] == combinado.acierto_pico("centro").pct_hora
