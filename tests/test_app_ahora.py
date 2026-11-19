"""Pruebas de «Ahora» y «Confianza» (GET /ahora/{area} y GET /confianza/{area}).

El historial se prueba con el pronosticador de prueba; el modo en vivo, con el registro de la tubería diaria armado
con el portal y el modelo falsos de ``test_en_vivo.py``.
"""

import datetime as dt
import random
import warnings

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("fastapi")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)  # Starlette recomienda httpx2; con httpx funciona igual
    from fastapi.testclient import TestClient

from test_en_vivo import LIMA_10_05, ModeloFalso, _con_tres_dias, _demanda, _silencio

from app.backend.ahora import causas_probables, dias_pico
from app.backend.main import crear_app
from app.backend.pronosticador import PronosticadorDePrueba
from tetouan_power_forecast import en_vivo as ev


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    # Sin registro en vivo: una carpeta vacía (si no, leería el de TETOUAN_DATA)
    return TestClient(crear_app(PronosticadorDePrueba(), web=None, en_vivo=tmp_path_factory.mktemp("sin-vivo")))


@pytest.fixture
def raiz(tmp_path):
    """La silver histórica sintética de ``test_en_vivo.py``: 60 días hasta el 23 de octubre de 2026 a las 00:00."""
    destino = tmp_path / "coes" / "silver" / "demanda_areas.parquet"
    destino.parent.mkdir(parents=True)
    _demanda(pd.date_range("2026-08-24 00:30", "2026-10-23 00:00", freq="30min"), ruido=3.0).to_parquet(destino,
                                                                                                    index=False)
    return tmp_path


def _mae(real, otro):
    pares = [(r, o) for r, o in zip(real, otro) if r is not None and o is not None]
    return round(sum(abs(r - o) for r, o in pares) / len(pares), 1)


# ---- Ahora, repaso con el historial ---------------------------------------------------------------------------


def test_ahora_repaso_arma_hoy_y_las_proximas_24_h(cliente):
    d = cliente.get("/ahora/centro", params={"origen": "2026-03-10T19:00", "variante": "M3"}).json()
    assert d["modo"] == "repaso" and d["modelo"] == "prueba" and d["nivel_rango_pct"] == 90
    assert d["origen"] == d["ahora"] == "2026-03-10T19:00" and d["datos_hasta"] == "2026-03-10T19:30"
    # De las 00:00 del día hasta 24 h después del origen: 39 periodos del día más 48
    assert len(d["fecha_hora"]) == 39 + 48 == len(d["pronostico"]) == len(d["real"]) == len(d["referencia"])
    assert d["fecha_hora"][0] == "2026-03-10T00:00" and d["fecha_hora"][-1] == "2026-03-11T19:00"
    assert d["i_origen"] == d["i_ahora"] == 38
    # Lo real solo hasta el origen; lo que pasó después va aparte
    assert all(x is None for x in d["real"][39:]) and d["real"][38] is not None
    assert all(x is None for x in d["real_despues"][:39]) and d["real_despues"][39] is not None
    assert all(i <= v <= s for i, v, s in zip(d["inferior"], d["pronostico"], d["superior"]))

    serie = cliente.get("/series/centro", params={"fecha": "2026-03-10", "horizonte": "24h", "variante": "M3"}).json()
    assert d["pronostico"][:39] == serie["pronostico"][:39] and d["real"][:39] == serie["real"][:39]
    # Las cifras salen de las mismas rutas que ya existían
    assert d["cifra_ahora"] == {"fecha_hora": "2026-03-10T19:00", "valor": serie["real"][38], "fuente": "real",
                                "inferior": None, "superior": None}
    una = cliente.post("/pronostico", json={"area": "centro", "origen": "2026-03-10T19:00", "horizonte": "1h",
                                            "variante": "M3"}).json()
    assert d["en_1h"]["fecha_hora"] == "2026-03-10T20:00" and d["en_1h"]["valor"] == una["pronostico"][-1]
    assert d["en_1h"]["fuente"] == "pronostico_1h"
    a24 = cliente.post("/pronostico", json={"area": "centro", "origen": "2026-03-10T19:00", "horizonte": "24h",
                                            "variante": "M3"}).json()
    assert d["pronostico"][39:] == a24["pronostico"]
    assert d["manana"]["fecha_hora"] == "2026-03-11T19:00" and d["manana"]["valor"] == a24["pronostico"][-1]
    # Lo que dijimos ayer para esta hora: el pronóstico a 24 h de la serie del día, contra el real
    ayer = d["ayer"]
    assert ayer["fuente"] == "historial" and ayer["emitido"] == "2026-03-09T19:00"
    assert ayer["pronostico"] == serie["pronostico"][38] and ayer["real"] == serie["real"][38]
    assert ayer["diferencia"] == pytest.approx(serie["pronostico"][38] - serie["real"][38], abs=0.11)
    assert ayer["dentro"] == (serie["intervalo"]["inferior"][38] <= serie["real"][38] <= serie["intervalo"]["superior"][38])
    # El error del día completo (repaso) y hasta el origen
    assert d["error_dia"]["mae_modelo"] == _mae(serie["real"], serie["pronostico"])
    assert d["error_dia"]["mae_referencia"] == _mae(serie["real"], serie["referencia"])
    assert d["error_hasta_origen"]["periodos"] == 39
    assert d["error_hasta_origen"]["mae_modelo"] == _mae(serie["real"][:39], serie["pronostico"][:39])
    assert d["dias_disponibles"] == [["2025-01-01", "2026-10-31"]]


def test_pico_y_rampa_anotados_coinciden_con_pico(cliente):
    """El criterio de la revisión: en 3 áreas × 10 orígenes al azar, la anotación coincide con /pico."""
    azar = random.Random(7)
    for area in ("norte", "centro", "sur"):
        for _ in range(10):
            dia = dt.date(2025, 1, 2) + dt.timedelta(days=azar.randrange(650))
            origen = f"{dia}T{azar.randrange(24):02d}:{azar.choice(['00', '30'])}"
            d = cliente.get(f"/ahora/{area}", params={"origen": origen}).json()
            p = cliente.get(f"/pico/{area}", params={"origen": origen}).json()
            assert d["pico"] == p["pico"], (area, origen)
            assert d["rampa"] == p["rampa"], (area, origen)


def test_ahora_sin_registro_en_vivo_muestra_el_ultimo_dia_del_historial(cliente):
    d = cliente.get("/ahora/sur", params={"ahora": "2026-11-13T17:40"}).json()
    assert d["modo"] == "repaso" and d["origen"] == "2026-10-31T17:30"
    assert d["avisos"] and "en vivo" in d["avisos"][0]


def test_ahora_errores_en_lenguaje_llano(cliente):
    assert cliente.get("/ahora/oeste").status_code == 404
    assert cliente.get("/ahora/centro", params={"origen": "2026-03-10T19:15"}).status_code == 422
    assert cliente.get("/ahora/centro", params={"modelo": "otro"}).status_code == 404
    r = cliente.get("/ahora/centro", params={"origen": "2027-02-01T10:00"})
    assert r.status_code == 422
    assert r.json()["detail"] == "No hay datos para repasar el 2027-02-01. Hay del 2025-01-01 al 2026-10-31."


# ---- Ahora, con el registro en vivo ---------------------------------------------------------------------------


def _cliente_vivo(raiz):
    _con_tres_dias(raiz)
    ev.emitir(raiz, ModeloFalso(), ahora=lambda: LIMA_10_05, progreso=_silencio)
    ev.evaluar(raiz, _silencio)
    return TestClient(crear_app(PronosticadorDePrueba(), web=None, en_vivo=ev.rutas(raiz).reportes))


def test_ahora_en_vivo_marca_la_hora_de_lima_dentro_del_pronostico(raiz):
    c = _cliente_vivo(raiz)
    d = c.get("/ahora/centro", params={"ahora": "2026-10-26T15:10"}).json()
    assert d["modo"] == "en_vivo" and d["nivel_rango_pct"] == 80 and d["modelo"] == "en_vivo:falso"
    # Con un día de retraso: el último real es el fin del 25; la ventana es el 25 (real) y el 26 (pronóstico)
    assert d["origen"] == "2026-10-25T23:30" and d["datos_hasta"] == "2026-10-26T00:00"
    assert d["fecha_hora"][0] == "2026-10-25T00:00" and d["fecha_hora"][-1] == "2026-10-26T23:30"
    assert d["i_origen"] == 47 and d["ahora"] == "2026-10-26T15:00" and d["i_ahora"] == 48 + 30
    assert d["emitido_en"] == "2026-10-26T10:05" and d["real_despues"] is None
    assert all(x is None for x in d["real"][48:]) and all(x is not None for x in d["real"][:48])
    assert set(d["tipo"][:48]) == {"reconstruido"} and set(d["tipo"][48:]) == {"en_vivo", "ex_ante_estricto"}
    # «Ahora» es un pronóstico (el real llega mañana), y mañana a esta hora todavía no se emite
    assert d["cifra_ahora"]["fuente"] == "pronostico_24h" and d["cifra_ahora"]["fecha_hora"] == "2026-10-26T15:00"
    assert d["en_1h"]["fecha_hora"] == "2026-10-26T16:00" and d["manana"] is None and "mañana" in d["manana_motivo"]
    # Lo que dijimos para ayer a esta hora, con su etiqueta del registro
    registro = pd.read_parquet(ev.rutas(raiz).pronosticos)
    fila = registro[(registro["area"] == "CENTRO") & (registro["horizonte"] == "24h")
                    & (registro["objetivo"] == pd.Timestamp("2026-10-25 15:30"))].iloc[0]
    assert d["ayer"]["fecha_hora"] == "2026-10-25T15:00" and d["ayer"]["fuente"] == "reconstruido"
    assert d["ayer"]["pronostico"] == round(fila["pred"], 1) and d["ayer"]["inferior"] == round(fila["q10"], 1)
    # El pico de las 24 h siguientes al origen es el del día de hoy
    assert d["pico"]["valor"] == max(d["pronostico"][48:])
    assert d["dias_disponibles"][1] == ["2026-10-23", "2026-10-25"]


def test_ahora_en_vivo_atrasado_lo_dice(raiz):
    d = _cliente_vivo(raiz).get("/ahora/norte", params={"ahora": "2026-10-27T08:00"}).json()
    assert d["modo"] == "en_vivo" and d["i_ahora"] == d["i_origen"]
    assert "Todavía no llega la demanda del 2026-10-26" in d["avisos"][0]


def test_ahora_repaso_del_tramo_en_vivo(raiz):
    c = _cliente_vivo(raiz)
    # El 18 de octubre no está en el historial del modelo de prueba... pero sí el 24 en el registro: se usa el
    # registro solo fuera del rango del modelo, así que se prueba con un modelo cuyo rango termina antes.
    p = PronosticadorDePrueba()
    p.fecha_max = dt.date(2026, 10, 20)
    c = TestClient(crear_app(p, web=None, en_vivo=ev.rutas(raiz).reportes))
    d = c.get("/ahora/sur", params={"origen": "2026-10-24T19:00"}).json()
    assert d["modo"] == "repaso" and d["modelo"] == "en_vivo:falso"
    assert d["cifra_ahora"]["fuente"] == "real" and d["en_1h"]["fuente"] == "pronostico_1h"
    assert d["en_1h"]["fecha_hora"] == "2026-10-24T20:00"
    assert d["ayer"]["fuente"] == "reconstruido" and d["error_dia"]["periodos"] == 48
    assert c.get("/ahora/sur", params={"origen": "2026-10-21T19:00"}).status_code == 422


# ---- Confianza ---------------------------------------------------------------------------------------------------


def test_confianza_reune_el_seguimiento_el_sesgo_y_el_dia_a_dia(cliente):
    r = cliente.get("/confianza/centro", params={"horizonte": "24h"})
    assert r.status_code == 200
    d = r.json()
    seg = cliente.get("/seguimiento/centro", params={"horizonte": "24h"}).json()
    assert d["seguimiento"] == seg and d["modelo"] == "prueba" and d["umbral_pico_pct"] == 3.0
    assert 0 < d["wape_pct"] < 10 and 0 < d["mape_pct"] < 10
    assert d["sesgo"]["periodos"] > 13000 and 0 <= d["sesgo"]["subestima_pct"] <= 100
    assert d["dias"][0]["fecha"] == "2026-01-01" and len(d["dias"]) > 250
    # Un día a mano, con la serie del día
    dia = d["dias"][40]
    s = cliente.get("/series/centro", params={"fecha": dia["fecha"], "horizonte": "24h", "variante": "M3"}).json()
    jr = int(np.argmax(s["real"]))
    jp = int(np.argmax(s["pronostico"]))
    assert dia["pico_real"] == s["real"][jr] and dia["hora_real"] == s["fecha_hora"][jr][11:]
    assert dia["pico_pronostico"] == s["pronostico"][jp]
    assert dia["error_pct"] == pytest.approx(100 * (s["pronostico"][jp] - s["real"][jr]) / s["real"][jr], abs=0.01)
    assert d["acierto"]["dias"] > 200 and d["dias_en_vivo"] == []
    assert cliente.get("/confianza/oeste").status_code == 404
    assert cliente.get("/confianza/centro", params={"horizonte": "6h"}).status_code == 422


def test_confianza_trae_el_dia_a_dia_del_registro_en_vivo(raiz):
    d = _cliente_vivo(raiz).get("/confianza/norte").json()
    assert [x["fecha"] for x in d["dias_en_vivo"]] == ["2026-10-23", "2026-10-24", "2026-10-25"]


def test_causas_probables_solo_del_calendario():
    pytest.importorskip("holidays")
    f = dt.date
    causas = causas_probables([f(2026, 4, 2), f(2026, 4, 4), f(2026, 4, 6), f(2026, 11, 2), f(2026, 3, 11),
                               f(2026, 7, 29), f(2026, 7, 30), f(2026, 3, 14)])
    assert causas[f(2026, 4, 2)] == "feriado (Jueves Santo), en un fin de semana largo"
    assert causas[f(2026, 4, 4)] == "fin de semana largo (feriado de Jueves Santo)"
    assert causas[f(2026, 4, 6)] == "día siguiente a un fin de semana largo (Jueves Santo)"
    assert causas[f(2026, 11, 2)] == "día siguiente a un feriado (Todos los Santos)"
    assert causas[f(2026, 7, 29)].startswith("feriado (")
    assert causas[f(2026, 7, 30)].startswith("día siguiente a un feriado")
    # Un miércoles y un sábado cualquiera: sin causa (no se inventa)
    assert f(2026, 3, 11) not in causas and f(2026, 3, 14) not in causas


def test_dias_pico_salta_los_dias_incompletos():
    pred = np.array([[1.0] * 47 + [3.0], [2.0] * 48])
    real = np.array([[1.0] * 46 + [2.0, 1.0], [np.nan] + [2.0] * 47])
    dias = dias_pico([dt.date(2026, 3, 11), dt.date(2026, 3, 12)], pred, real)
    assert len(dias) == 1
    assert dias[0].hora_real == "23:00" and dias[0].hora_pronostico == "23:30" and dias[0].error_pct == 50.0
