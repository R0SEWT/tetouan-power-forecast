"""Temperatura pronosticada y corrección por calor: edición vigente, β sin mirar el futuro, caché y el modelo en
paralelo del modo en vivo. Sin red: Open-Meteo se reemplaza por respuestas sintéticas."""

import datetime as dt
import json
import urllib.error

import numpy as np
import pandas as pd
import pytest

from tests.test_en_vivo import LIMA_10_05, ModeloFalso, _con_tres_dias, _silencio, raiz  # noqa: F401
from tetouan_power_forecast import en_vivo as ev
from tetouan_power_forecast import temperatura_pronosticada as tp


def _respuesta(desde, hasta, temp=None):
    """Una respuesta de Open-Meteo con las seis ciudades: la misma temperatura en todas las variables."""
    tiempo = pd.date_range(desde, f"{hasta} 23:00", freq="h")
    temp = temp or {"norte": 26.0, "centro": 25.0, "sur": 19.0}
    salida = []
    for area, _, _, _ in tp.LUGARES:
        horas = {"time": [f"{t:%Y-%m-%dT%H:%M}" for t in tiempo]}
        for variable in tp.VARIABLES:
            horas[variable] = [temp[area]] * len(tiempo)
        salida.append({"hourly": horas})
    return json.dumps(salida).encode()


def _archivo_anual(carpeta_datos, anio, desde, hasta, temp=None):
    destino = tp.carpeta(carpeta_datos) / f"{tp.MODELO}_{anio}.json"
    tp._guardar(destino, _respuesta(desde, hasta, temp), modelo=tp.MODELO, desde=desde, hasta=hasta)


def _sin_ajuste(carpeta_datos):
    """Ajuste de nivel cero (en las pruebas no hay ERA5 de 2021–2024)."""
    filas = [{"mes": m, "hora": h, "desfase": n, **{a: 0.0 for a in tp.AREAS}}
             for n in tp.DESFASES for m in range(1, 13) for h in range(24)]
    pd.DataFrame(filas).to_csv(tp.carpeta(carpeta_datos) / f"ajuste_nivel_{tp.MODELO}.csv", index=False)


# ---- Edición vigente y días ---------------------------------------------------------------------------------------


def test_edicion_vigente_respeta_la_publicacion():
    x = pd.Timestamp("2026-11-13")
    dias = pd.DatetimeIndex([x] * 6 + [x - pd.Timedelta(days=1)])
    origenes = pd.DatetimeIndex(["2026-11-12 06:30", "2026-11-12 07:00", "2026-11-12 23:30", "2026-11-13 06:30",
                                 "2026-11-13 07:00", "2026-11-11 12:00", "2026-11-12 12:00"])
    # 24 h (orígenes en X − 1): desfase 3 antes de las 07:00 y 2 después; 1 h (orígenes en X): 2 y luego 1
    assert list(tp.edicion_vigente(dias, origenes)) == [3, 2, 2, 2, 1, 3, 1]


def test_dia_objetivo_por_el_fin_del_periodo():
    origenes = pd.DatetimeIndex(["2026-11-12 00:00", "2026-11-12 00:30", "2026-11-12 23:00", "2026-11-12 23:30"])
    assert list(tp.dia_objetivo(origenes, "24h").day) == [12, 13, 13, 13]  # 24:00 del 12 es su último periodo
    assert list(tp.dia_objetivo(origenes, "1h").day) == [12, 12, 12, 13]


def test_diarias_dejan_vacio_un_dia_incompleto_y_cuentan_grados():
    horas = pd.date_range("2026-11-01", periods=48, freq="h")
    t = pd.DataFrame({"norte": 27.0, "centro": 24.5, "sur": 18.0}, index=horas)
    t.iloc[30, 1] = np.nan
    d = tp.diarias(t)
    assert d["centro"]["cdd"].iloc[0] == pytest.approx(1.5) and np.isnan(d["centro"]["media"].iloc[1])
    assert d["sur"]["cdd"].iloc[0] == 0 and d["norte"]["cdd"].iloc[0] == pytest.approx(1.25)


# ---- β en línea -----------------------------------------------------------------------------------------------------


def _continuos(dias, r_por_dia, x=2.0, horizonte="24h"):
    filas = []
    for dia, r in zip(dias, r_por_dia, strict=True):
        objetivos = pd.date_range(dia + tp.PASO, periods=48, freq="30min")
        filas.append(pd.DataFrame({"horizonte": horizonte, "area": "CENTRO", "objetivo": objetivos,
                                   "pred": 1000.0, "real": 1000.0 * (1 + r), "tp_cdd": x}))
    return pd.concat(filas, ignore_index=True)


def test_beta_solo_usa_dias_cerrados_al_emitir():
    dias = pd.date_range("2025-01-01", periods=5, freq="D")
    c = _continuos(dias, [0.0, 0.0, 0.10, 0.0, 0.0])
    b = tp.betas_en_linea(c).set_index("dia")
    # A 24 h, el día X usa hasta X − 2: el error grande del 3 recién entra el 5
    assert b.loc["2025-01-04", "beta_2"] == 0
    assert b.loc["2025-01-05", "beta_2"] == pytest.approx(0.10 * 2 / (3 * 4))  # Σ x·r / Σ x² con 3 días de x = 2
    c1 = _continuos(dias, [0.0, 0.0, 0.10, 0.0, 0.0], horizonte="1h")
    b1 = tp.betas_en_linea(c1).set_index("dia")
    assert b1.loc["2025-01-03", "beta_2"] == 0 and b1.loc["2025-01-04", "beta_2"] > 0


def test_beta_no_baja_el_pronostico_y_sin_calor_no_corrige():
    dias = pd.date_range("2025-01-01", periods=6, freq="D")
    b = tp.betas_en_linea(_continuos(dias, [-0.05] * 6))
    assert (b[[f"beta_{k}" for k in range(4)]] == 0).all().all()  # monótona: nunca resta
    betas = tp.betas_en_linea(_continuos(dias, [0.02] * 6))
    objetivos = pd.date_range("2025-01-06 00:30", periods=48, freq="30min")
    assert np.allclose(tp.factor_calor(betas, "24h", "CENTRO", objetivos, np.zeros(48)), 1)
    f = tp.factor_calor(betas, "24h", "CENTRO", objetivos, np.full(48, 2.0))
    assert np.allclose(f, 1 + 0.01 * 2)
    assert np.allclose(tp.factor_calor(betas, "24h", "NORTE", objetivos, np.full(48, 2.0)), 1)  # sin β: 1


def test_bloques_del_dia():
    objetivos = pd.DatetimeIndex(["2026-11-13 00:30", "2026-11-13 07:00", "2026-11-13 07:30", "2026-11-13 19:00",
                                  "2026-11-13 19:30", "2026-11-14 00:00"])
    assert list(tp.bloque(objetivos)) == [0, 0, 1, 2, 3, 3]


# ---- Caché y descarga -----------------------------------------------------------------------------------------------


def test_lectura_gana_la_consulta_mas_nueva(tmp_path):
    _archivo_anual(tmp_path, 2026, "2026-11-01", "2026-11-10", {"norte": 26.0, "centro": 25.0, "sur": 19.0})
    reciente = tp.carpeta(tmp_path) / "reciente" / f"{tp.MODELO}_2026-11-11.json"
    tp._guardar(reciente, _respuesta("2026-11-08", "2026-11-12", {"norte": 26.0, "centro": 27.0, "sur": 19.0}))
    t = tp.leer(tmp_path)
    assert t[2].loc["2026-11-05 12:00", "centro"] == 25.0 and t[2].loc["2026-11-09 12:00", "centro"] == 27.0
    assert t[2].index.max() == pd.Timestamp("2026-11-12 23:00")


def test_bajar_reciente_tolera_la_red_y_usa_la_cache(tmp_path):
    llamadas = []

    def caida(url):
        llamadas.append(url)
        raise urllib.error.URLError("sin red")

    assert tp.bajar_reciente(tmp_path, dt.date(2026, 11, 19), descargar=caida) is False
    assert not (tp.carpeta(tmp_path) / "reciente").exists() or not list((tp.carpeta(tmp_path) / "reciente").glob("*"))

    def bien(url):
        llamadas.append(url)
        return _respuesta("2026-10-10", "2026-11-21")

    assert tp.bajar_reciente(tmp_path, dt.date(2026, 11, 19), descargar=bien) is True
    assert tp.bajar_reciente(tmp_path, dt.date(2026, 11, 19), descargar=caida) is True  # ya estaba: no pide
    assert len(llamadas) == 2 and "past_days=40" in llamadas[1]


def test_una_pagina_de_error_no_se_guarda(tmp_path):
    with pytest.raises(ValueError):
        tp._guardar(tmp_path / "x.json", b"<html>error</html>")
    assert not (tmp_path / "x.json").exists()


# ---- Modelo en paralelo en vivo ----------------------------------------------------------------------------------


def test_calor_en_paralelo_no_toca_al_base_y_no_se_repite(raiz):  # noqa: F811
    _con_tres_dias(raiz)
    ev.emitir(raiz, ModeloFalso(), ahora=lambda: LIMA_10_05, progreso=_silencio)
    base = ev.leer_registro(raiz)
    assert ev.emitir_calor(raiz, "falso", progreso=_silencio) == 0  # sin archivo de temperatura no hace nada
    _archivo_anual(raiz, 2026, "2026-08-01", "2026-10-31")
    _sin_ajuste(raiz)

    def caida(url):
        raise urllib.error.URLError("sin red")

    n = ev.emitir_calor(raiz, "falso", hoy=dt.date(2026, 10, 26), ahora=lambda: LIMA_10_05 + pd.Timedelta(hours=1),
                        descargar=caida, progreso=_silencio)
    registro = ev.leer_registro(raiz)
    assert n == len(base)
    pd.testing.assert_frame_equal(registro.iloc[:len(base)], base)  # lo emitido no cambia
    calor = registro[registro["modelo"] == "falso+calor"]
    assert set(calor["version_pesos"]) == {"v1+" + ev.VERSION_CALOR}
    j = calor.merge(base, on=["horizonte", "area", "objetivo"], suffixes=("", "_base"))
    assert (j["pred"] >= j["pred_base"] - 1e-9).all()  # la corrección solo suma
    assert np.allclose((j["q90"] / j["q90_base"]), (j["pred"] / j["pred_base"]))
    assert ev.emitir_calor(raiz, "falso", hoy=dt.date(2026, 10, 26), descargar=caida, progreso=_silencio) == 0
    assert ev.es_paralelo("falso+calor") and not ev.es_paralelo("chronos2ftcal")


def test_calor_salta_los_dias_sin_pronostico_de_temperatura(raiz):  # noqa: F811
    _con_tres_dias(raiz)
    ev.emitir(raiz, ModeloFalso(), ahora=lambda: LIMA_10_05, progreso=_silencio)
    _archivo_anual(raiz, 2026, "2026-08-01", "2026-10-24")  # no llega al 25 ni al 26
    _sin_ajuste(raiz)
    mensajes = []
    ev.emitir_calor(raiz, "falso", hoy=dt.date(2026, 10, 26), descargar=lambda url: _respuesta("2026-08-01",
                                                                                                "2026-10-24"),
                    progreso=mensajes.append)
    calor = ev.leer_registro(raiz).query("modelo == 'falso+calor'")
    assert pd.to_datetime(calor["fecha_objetivo"]).max() == pd.Timestamp("2026-10-24")
    assert any("sin pronóstico de temperatura" in m for m in mensajes)


def test_correr_emite_el_paralelo_y_un_fallo_no_frena_al_base(raiz, monkeypatch):  # noqa: F811
    from tests.test_en_vivo import COESFalso, _anexo, _dias, _portal

    falso = COESFalso({d: _anexo(d) for d in _dias(dt.date(2026, 10, 23), 3)})
    _archivo_anual(raiz, 2026, "2026-08-01", "2026-10-31")
    _sin_ajuste(raiz)
    codigo = ev.correr("diario", raiz, portal=_portal(falso), modelo=ModeloFalso(), hoy=dt.date(2026, 10, 26),
                       ahora=lambda: LIMA_10_05, progreso=_silencio, temperatura=lambda url: b"no es json")
    assert codigo == 0
    registro = ev.leer_registro(raiz)
    assert {"falso", "falso+calor"} <= set(registro["modelo"])
    corrida = json.loads(ev.rutas(raiz).corridas.read_text().splitlines()[-1])
    assert corrida["filas_calor"] == (registro["modelo"] == "falso+calor").sum()

    def revienta(*a, **k):
        raise RuntimeError("falla de prueba")

    monkeypatch.setattr(ev, "emitir_calor", revienta)
    falso.publicados[dt.date(2026, 10, 26)] = _anexo(dt.date(2026, 10, 26))
    assert ev.correr("diario", raiz, portal=_portal(falso), modelo=ModeloFalso(), hoy=dt.date(2026, 10, 27),
                     ahora=lambda: LIMA_10_05 + pd.Timedelta(days=1), progreso=_silencio) == 0
    corrida = json.loads(ev.rutas(raiz).corridas.read_text().splitlines()[-1])
    assert corrida["filas_calor"].startswith("error")
