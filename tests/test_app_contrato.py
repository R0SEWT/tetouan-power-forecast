"""Pruebas del contrato de la API de la app, con el pronosticador de prueba."""

import json
import re
import warnings
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

with warnings.catch_warnings():
    # Starlette recomienda httpx2 para el cliente de pruebas; con httpx funciona igual.
    warnings.simplefilter("ignore", UserWarning)
    from fastapi.testclient import TestClient

from app.backend.contrato import AREAS
from app.backend.main import crear_app
from app.backend.pronosticador import Pronosticador, PronosticadorDePrueba

FECHA_HORA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:(00|30)$")
WEB = Path(__file__).resolve().parents[1] / "app" / "web"


@pytest.fixture(scope="module")
def cliente():
    return TestClient(crear_app(PronosticadorDePrueba()))


def pedido(**cambios):
    base = {"area": "centro", "origen": "2026-02-26T15:00", "horizonte": "24h", "variante": "M3"}
    return base | cambios


# ---- /salud, /areas y /resumen ---------------------------------------------------------------


def test_salud(cliente):
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok", "modelo": "prueba", "version_datos": "sin-datos"}


def test_modelos_lista_el_que_se_sirve(cliente):
    r = cliente.get("/modelos")
    assert r.status_code == 200
    modelos = r.json()
    assert [m["id"] for m in modelos] == [cliente.get("/salud").json()["modelo"]]
    assert all(m["nombre"] for m in modelos)
    assert modelos[0]["respaldo"] is None


def test_areas_con_la_paleta_de_wong(cliente):
    assert cliente.get("/areas").json() == [
        {"id": "norte", "nombre": "Norte", "color": "#E69F00"},
        {"id": "centro", "nombre": "Centro", "color": "#0072B2"},
        {"id": "sur", "nombre": "Sur", "color": "#009E73"},
    ]


def test_resumen(cliente):
    r = cliente.get("/resumen").json()
    assert set(r) == {"fechas_corte", "regimen_nino", "metricas_prueba", "modelo", "version_datos"}
    assert r["regimen_nino"] == {"estado": "extraordinario", "icen": 3.98, "mes": "2026-08"}
    assert set(r["metricas_prueba"]) == {a.id for a in AREAS}
    for m in r["metricas_prueba"].values():
        assert m["mae_mw"] > 0 and m["mape_pct"] > 0
        assert m["mejor_referencia"] in {"persistencia", "ayer", "semana_pasada"}
    assert all(isinstance(v, str) for v in r["fechas_corte"].values())


# ---- /series ---------------------------------------------------------------------------------


@pytest.mark.parametrize("horizonte", ["1h", "24h"])
@pytest.mark.parametrize("variante", ["M0", "M3"])
def test_series_tiene_48_periodos(cliente, horizonte, variante):
    r = cliente.get(
        "/series/norte",
        params={"fecha": "2025-07-14", "horizonte": horizonte, "variante": variante},
    )
    assert r.status_code == 200
    s = r.json()
    for campo in ("fecha_hora", "real", "pronostico", "referencia", "hueco", "preliminar"):
        assert len(s[campo]) == 48, campo
    assert s["fecha_hora"][0] == "2025-07-14T00:00"
    assert s["fecha_hora"][-1] == "2025-07-14T23:30"
    assert all(FECHA_HORA.match(x) for x in s["fecha_hora"])
    assert all(isinstance(x, (int, float)) for x in s["pronostico"] + s["referencia"])
    assert s["referencia_nombre"] in {"persistencia", "ayer", "semana_pasada"}
    if horizonte == "1h":
        assert s["programacion_diaria"] is None
    else:
        assert len(s["programacion_diaria"]) == 48


@pytest.mark.parametrize("horizonte", ["1h", "24h"])
def test_series_trae_el_rango_probable_de_cada_periodo(cliente, horizonte):
    s = cliente.get("/series/norte", params={"fecha": "2025-07-14", "horizonte": horizonte}).json()
    inferior, superior = s["intervalo"]["inferior"], s["intervalo"]["superior"]
    assert len(inferior) == len(superior) == 48
    assert all(a <= p <= b for a, p, b in zip(inferior, s["pronostico"], superior, strict=True))


def test_el_rango_de_la_serie_es_el_del_pronostico_emitido_h_antes(cliente):
    s = cliente.get("/series/centro", params={"fecha": "2026-03-10", "horizonte": "24h"}).json()
    p = cliente.post("/pronostico", json=pedido(origen="2026-03-09T19:00", horizonte="24h")).json()
    i = s["fecha_hora"].index("2026-03-10T19:00")
    assert p["fecha_hora"][-1] == "2026-03-10T19:00"
    assert s["pronostico"][i] == p["pronostico"][-1]
    assert s["intervalo"]["inferior"][i] == p["intervalo"]["inferior"][-1]
    assert s["intervalo"]["superior"][i] == p["intervalo"]["superior"][-1]


def test_series_dice_que_modelo_respondio(cliente):
    s = cliente.get("/series/sur", params={"fecha": "2026-03-10", "horizonte": "24h"}).json()
    assert s["modelo"] == "prueba" and s["componentes"] is None


def test_series_marca_los_huecos(cliente):
    s = cliente.get("/series/centro", params={"fecha": "2026-02-26", "horizonte": "24h"}).json()
    assert any(s["hueco"])
    assert all((r is None) == h for r, h in zip(s["real"], s["hueco"], strict=True))


def test_series_marca_lo_preliminar(cliente):
    s = cliente.get("/series/sur", params={"fecha": "2026-10-30"}).json()
    assert all(s["preliminar"])


def test_series_area_inexistente(cliente):
    r = cliente.get("/series/oeste", params={"fecha": "2026-02-26"})
    assert r.status_code == 404
    assert "oeste" in r.json()["detail"]


@pytest.mark.parametrize("fecha", ["2024-12-31", "2026-11-01"])
def test_series_fecha_fuera_de_rango(cliente, fecha):
    r = cliente.get("/series/centro", params={"fecha": fecha})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "params",
    [{"fecha": "2026-02-26", "horizonte": "2h"}, {"fecha": "2026-02-26", "variante": "M9"}],
)
def test_series_parametros_invalidos(cliente, params):
    assert cliente.get("/series/centro", params=params).status_code == 422


# ---- /pronostico -----------------------------------------------------------------------------


@pytest.mark.parametrize(("horizonte", "pasos"), [("1h", 2), ("24h", 48)])
def test_pronostico_cubre_el_horizonte(cliente, horizonte, pasos):
    r = cliente.post("/pronostico", json=pedido(horizonte=horizonte))
    assert r.status_code == 200
    p = r.json()
    assert set(p) == {"fecha_hora", "pronostico", "referencia", "real", "intervalo", "frase", "modelo"}
    assert p["modelo"] == "prueba"
    for campo in ("fecha_hora", "pronostico", "referencia", "real"):
        assert len(p[campo]) == pasos, campo
    assert p["fecha_hora"][0] == "2026-02-26T15:30"
    assert all(
        inf <= x <= sup
        for inf, x, sup in zip(
            p["intervalo"]["inferior"], p["pronostico"], p["intervalo"]["superior"], strict=True
        )
    )
    assert p["frase"]


def test_pronostico_es_determinista(cliente):
    a = cliente.post("/pronostico", json=pedido()).json()
    b = cliente.post("/pronostico", json=pedido()).json()
    assert a == b


def test_pronostico_sin_dato_real_despues_del_corte(cliente):
    p = cliente.post("/pronostico", json=pedido(origen="2026-10-31T23:30")).json()
    assert p["real"] == [None] * 48


def test_escenario_con_mas_calor_sube_la_demanda(cliente):
    base = cliente.post("/pronostico", json=pedido()).json()
    calor = cliente.post("/pronostico", json=pedido(escenario={"delta_temp_c": 4})).json()
    pico = max(range(48), key=lambda j: base["pronostico"][j])
    assert calor["pronostico"][pico] > base["pronostico"][pico]
    assert calor["frase"] != base["frase"]


def test_escenario_sin_la_falla_en_curso(cliente):
    base = cliente.post("/pronostico", json=pedido()).json()
    sin_falla = cliente.post("/pronostico", json=pedido(escenario={"falla": "ninguna"})).json()
    assert sin_falla["pronostico"][0] > base["pronostico"][0]


def test_escenario_no_cambia_m0(cliente):
    base = cliente.post("/pronostico", json=pedido(variante="M0")).json()
    calor = cliente.post(
        "/pronostico", json=pedido(variante="M0", escenario={"delta_temp_c": 2})
    ).json()
    assert calor["pronostico"] == base["pronostico"]
    assert "M0" in calor["frase"]


@pytest.mark.parametrize(
    "escenario", [{"delta_temp_c": 2}, {"nino": "neutro"}, {"falla": "ninguna"}]
)
def test_a_1h_no_hay_escenarios(cliente, escenario):
    r = cliente.post("/pronostico", json=pedido(horizonte="1h", escenario=escenario))
    assert r.status_code == 422
    assert "1 h no hay escenarios" in r.json()["detail"]


def test_a_1h_el_escenario_base_si_vale(cliente):
    base = {"delta_temp_c": 0, "nino": "observado", "falla": "observada"}
    r = cliente.post("/pronostico", json=pedido(horizonte="1h", escenario=base))
    assert r.status_code == 200


def test_pronostico_area_inexistente(cliente):
    assert cliente.post("/pronostico", json=pedido(area="oeste")).status_code == 404


@pytest.mark.parametrize(
    "cambios",
    [
        {"origen": "2024-12-31T23:30"},
        {"origen": "2026-11-01T00:00"},
        {"origen": "2026-02-26T15:15"},
        {"origen": "26/02/2026 15:00"},
        {"origen": "2026-02-30T15:00"},
        {"horizonte": "6h"},
        {"variante": "M2"},
        {"escenario": {"delta_temp_c": 3}},
        {"escenario": {"nino": "fuerte"}},
    ],
)
def test_pronostico_entradas_invalidas(cliente, cambios):
    assert cliente.post("/pronostico", json=pedido(**cambios)).status_code == 422


# ---- /sensibilidad ---------------------------------------------------------------------------


@pytest.mark.parametrize("variable", ["temperatura", "icen"])
def test_sensibilidad(cliente, variable):
    r = cliente.post(
        "/sensibilidad", json={"area": "centro", "origen": "2026-02-26T15:00", "variable": variable}
    )
    assert r.status_code == 200
    s = r.json()
    assert set(s) == {"valores", "pronostico"}
    assert len(s["valores"]) == len(s["pronostico"]) >= 5
    assert s["valores"] == sorted(s["valores"])


def test_sensibilidad_a_la_temperatura_es_pequena_a_1h(cliente):
    s = cliente.post(
        "/sensibilidad",
        json={"area": "centro", "origen": "2026-02-26T15:00", "variable": "temperatura"},
    ).json()
    rango = max(s["pronostico"]) - min(s["pronostico"])
    assert 0 < rango < 0.05 * min(s["pronostico"])


def test_sensibilidad_errores(cliente):
    base = {"area": "centro", "origen": "2026-02-26T15:00", "variable": "temperatura"}
    assert cliente.post("/sensibilidad", json=base | {"area": "oeste"}).status_code == 404
    assert cliente.post("/sensibilidad", json=base | {"variable": "lluvia"}).status_code == 422
    assert (
        cliente.post("/sensibilidad", json=base | {"origen": "2027-01-01T00:00"}).status_code == 422
    )


# ---- /diagnostico ----------------------------------------------------------------------------


def test_diagnostico(cliente):
    r = cliente.get("/diagnostico/norte")
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"mae_por_regimen", "ablacion", "adaptacion", "importancias", "residuos"}
    assert {x["regimen"] for x in d["mae_por_regimen"]} >= {"neutro", "extraordinario"}
    variantes = {x["variante"] for x in d["ablacion"]}
    assert {"M0", "M3"} <= variantes
    for x in d["ablacion"]:
        assert x["ic_inf"] <= x["mae"] <= x["ic_sup"]
    assert {x["politica"] for x in d["adaptacion"]} == {"fijo", "semanal", "alerta_enfen"}
    assert all(isinstance(x["exogenas"], bool) for x in d["adaptacion"])
    assert all({"variable", "valor"} == set(x) for x in d["importancias"])
    assert len(d["residuos"]["real"]) == len(d["residuos"]["predicho"]) > 0


def test_diagnostico_area_inexistente(cliente):
    assert cliente.get("/diagnostico/oeste").status_code == 404


# ---- /seguimiento y /pico --------------------------------------------------------------------


@pytest.mark.parametrize("horizonte", ["1h", "24h"])
def test_seguimiento(cliente, horizonte):
    r = cliente.get("/seguimiento/norte", params={"horizonte": horizonte})
    assert r.status_code == 200
    s = r.json()
    assert set(s) == {"horizonte", "referencia_nombre", "meta_cobertura_pct", "meses", "total"}
    assert [m["mes"] for m in s["meses"]] == [f"2026-{m:02d}" for m in range(1, 11)]
    assert s["total"]["periodos"] == sum(m["periodos"] for m in s["meses"])
    for m in [*s["meses"], s["total"]]:
        assert m["mae_modelo"] > 0 and m["mae_referencia"] > 0 and 0 <= m["cobertura_pct"] <= 100
    # el modelo de prueba le gana a la referencia en el año
    assert s["total"]["mae_modelo"] < s["total"]["mae_referencia"]


def test_seguimiento_errores(cliente):
    assert cliente.get("/seguimiento/oeste").status_code == 404
    assert cliente.get("/seguimiento/sur", params={"horizonte": "6h"}).status_code == 422
    assert cliente.get("/seguimiento/sur", params={"modelo": "otro"}).status_code == 404


def test_pico_y_rampa_de_las_proximas_24_h(cliente):
    r = cliente.get("/pico/centro", params={"origen": "2026-03-09T19:00"})
    assert r.status_code == 200
    pr = r.json()
    p = cliente.post("/pronostico", json=pedido(origen="2026-03-09T19:00")).json()
    assert pr["desde"] == "2026-03-09T19:30" and pr["hasta"] == "2026-03-10T19:00"
    assert pr["pico"]["valor"] == max(p["pronostico"])
    assert pr["pico"]["inferior"] <= pr["pico"]["valor"] <= pr["pico"]["superior"]
    assert pr["rampa"]["subida_mw"] > 0 and isinstance(pr["rampa"]["fuerte"], bool)
    assert pr["rampa"]["hasta"] > pr["rampa"]["desde"]
    assert pr["acierto"]["dias"] > 200 and 0 <= pr["acierto"]["pct_hora"] <= 100
    assert pr["modelo"] == "prueba"


def test_pico_errores(cliente):
    assert cliente.get("/pico/oeste", params={"origen": "2026-03-09T19:00"}).status_code == 404
    assert cliente.get("/pico/centro", params={"origen": "2026-03-09T19:15"}).status_code == 422
    assert cliente.get("/pico/centro", params={"origen": "2027-01-01T00:00"}).status_code == 422
    assert cliente.get("/pico/centro").status_code == 422


def test_pico_rampa_a_mano():
    from app.backend.contrato import Intervalo, Pronostico
    from app.backend.pico import pico_rampa

    horas = [f"2026-03-10T{h // 2:02d}:{30 * (h % 2):02d}" for h in range(6)]
    valores = [100.0, 110.0, 150.0, 170.0, 160.0, 120.0]
    p = Pronostico(fecha_hora=horas, pronostico=valores, referencia=valores, real=[None] * 6,
                   intervalo=Intervalo(inferior=[v - 5 for v in valores], superior=[v + 5 for v in valores]),
                   frase="")
    r = pico_rampa(p, umbral=50.0)
    assert r.pico.fecha_hora == "2026-03-10T01:30" and (r.pico.inferior, r.pico.superior) == (165.0, 175.0)
    # mayor subida en una hora: de 00:30 (110) a 01:30 (170), +60 MW
    assert (r.rampa.desde, r.rampa.hasta, r.rampa.subida_mw, r.rampa.fuerte) == ("2026-03-10T00:30", "2026-03-10T01:30", 60.0, True)
    assert not pico_rampa(p, umbral=60.0).rampa.fuerte and pico_rampa(p).rampa.umbral_mw is None
    bajando = p.model_copy(update={"pronostico": sorted(valores, reverse=True)})
    assert pico_rampa(bajando).rampa is None


def test_acierto_del_pico_a_mano():
    import numpy as np

    from app.backend.pico import acierto_pico

    real = np.tile(np.sin(np.linspace(0, np.pi, 48)), (4, 1))  # máximo en el periodo 23 o 24
    pico_real = int(real[0].argmax())
    pred = real.copy()
    pred[1] = np.roll(real[1], 2)  # dos periodos tarde: acierta (±1 h)
    pred[2] = np.roll(real[2], 3)  # tres periodos: no
    pred[3] = real[3] + 2.0  # en la hora, 2 MW arriba
    referencia = np.roll(real, 6, axis=1)
    a = acierto_pico(pred, real, referencia)
    assert a.dias == 4 and a.pct_hora == 75.0 and a.pct_hora_referencia == 0.0
    assert a.mae_pico_mw == 0.5 and pico_real in (23, 24)
    real[0, 5] = np.nan  # un día sin todos sus datos no cuenta
    assert acierto_pico(pred, real, referencia).dias == 3


def test_umbral_de_rampa_usa_la_mayor_subida_de_cada_dia():
    import numpy as np
    import pandas as pd

    from app.backend.pico import umbral_rampa

    fin = pd.date_range("2024-01-01 00:30", periods=48 * 20, freq="30min")
    subida_del_dia = np.repeat(np.arange(1, 21) * 10.0, 48)  # el día k sube 10·k MW por media hora a las 18:00
    valores = np.where((fin - pd.Timedelta(minutes=30)).hour == 18, subida_del_dia, 0.0).cumsum()
    real = pd.Series(valores, index=fin)
    assert umbral_rampa(real, pd.Timestamp("2024-01-21"), percentil=50) == pytest.approx(np.median(np.arange(1, 21) * 20.0))
    assert umbral_rampa(real, pd.Timestamp("2023-01-01")) is None


# ---- infraestructura -------------------------------------------------------------------------


def test_el_pronosticador_de_prueba_cumple_el_protocolo():
    assert isinstance(PronosticadorDePrueba(), Pronosticador)


def test_cors_permite_el_frontend_local(cliente):
    r = cliente.options(
        "/resumen",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rechaza_otros_origenes(cliente):
    r = cliente.get("/salud", headers={"Origin": "https://ejemplo.com"})
    assert "access-control-allow-origin" not in r.headers


def test_frontend_sin_librerias_externas():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    externos = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    assert all(u.startswith("https://fonts.") for u in externos), externos
    assert '<html lang="es"' in html
    json.loads((WEB / "manifest.json").read_text(encoding="utf-8"))


# ---- Web servida por el backend, comprimida ------------------------------------------------------


SERIE = ("/series/centro", {"fecha": "2025-07-14", "horizonte": "24h", "variante": "M0"})


def test_api_comprimida_con_gzip(cliente):
    r = cliente.get(SERIE[0], params=SERIE[1], headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["content-encoding"] == "gzip"
    assert len(r.json()["pronostico"]) == 48  # el cliente la descomprime


def test_api_sin_gzip_si_no_se_acepta_o_es_corta(cliente):
    r = cliente.get(SERIE[0], params=SERIE[1], headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in r.headers
    assert len(r.json()["pronostico"]) == 48
    # Por debajo de 500 bytes no vale la pena comprimir.
    assert "content-encoding" not in cliente.get("/salud", headers={"Accept-Encoding": "gzip"}).headers


def test_backend_sirve_la_web_en_su_origen(cliente):
    r = cliente.get("/", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.text == (WEB / "index.html").read_text(encoding="utf-8")
    js = cliente.get("/app.js", headers={"Accept-Encoding": "gzip"})
    assert js.status_code == 200
    assert js.headers["content-encoding"] == "gzip"
    assert "javascript" in js.headers["content-type"]
    assert js.content == (WEB / "app.js").read_bytes()


def test_rutas_de_la_api_antes_que_los_archivos(cliente):
    assert cliente.get("/salud").json()["estado"] == "ok"
    assert cliente.get("/no-existe.js").status_code == 404
    assert cliente.get("/docs").status_code == 200


def test_sin_carpeta_web_solo_api(tmp_path):
    c = TestClient(crear_app(PronosticadorDePrueba(), web=tmp_path / "no-hay"))
    assert c.get("/").status_code == 404
    assert c.get("/salud").status_code == 200


def test_servidor_solo_web_comprime():
    from app.backend.web import crear_web

    c = TestClient(crear_web())
    css = c.get("/style.css", headers={"Accept-Encoding": "gzip"})
    assert css.status_code == 200
    assert css.headers["content-encoding"] == "gzip"
    assert css.content == (WEB / "style.css").read_bytes()
    assert c.get("/").text == (WEB / "index.html").read_text(encoding="utf-8")
