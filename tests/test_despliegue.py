"""Pruebas del despliegue (despliegue/): paquete de datos, arranque del contenedor y scripts de publicación, sin red."""

import json
import re
import threading
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from despliegue import actualizar_hf, arranque, publicar_hf
from despliegue.cuenta import ErrorCuenta, token_personal, verificar_cuenta
from despliegue.paquete import (
    EN_VIVO,
    ESTATICOS,
    MANIFIESTO,
    METADATOS_APP,
    ErrorPaquete,
    armar_paquete,
    verificar,
)

RAIZ = Path(__file__).resolve().parents[1]
CLAVES = ["1h_M0", "24h_M3"]


def datos_falsos(carpeta: Path) -> Path:
    """Una carpeta de datos con la forma de la real: todos los archivos del paquete, chicos."""
    for ruta in [*ESTATICOS, *EN_VIVO]:
        (carpeta / ruta).parent.mkdir(parents=True, exist_ok=True)
        (carpeta / ruta).write_bytes(f"contenido de {ruta}".encode())
    (carpeta / METADATOS_APP).write_text(json.dumps({"columnas": {c: ["Area_t"] for c in CLAVES}}))
    for clave in CLAVES:
        joblib.dump({"clave": clave, "pesos": np.arange(1000.0)}, carpeta / f"modelos/sein/app/xgboost_global_{clave}.joblib")
    joblib.dump({"simons": True}, carpeta / "modelos/sein/fundacionales/xgb_simons_1h.joblib")
    (carpeta / "modelos/sein/app_viejo.joblib").write_bytes(b"no va en el paquete")
    return carpeta


# ---- inventario y paquete --------------------------------------------------------------------------------------------


def test_el_inventario_coincide_con_las_rutas_que_usa_el_codigo(tmp_path, monkeypatch):
    """Si alguien cambia dónde lee la app un archivo, el paquete lo dejaría fuera: esto lo detecta."""
    from app.backend import pronosticador_hibrido as hib
    from app.backend import pronosticador_real as real
    from tetouan_power_forecast.en_vivo import rutas

    datos = datos_falsos(tmp_path)
    leidos = []

    def leer(ruta, *a, **k):
        leidos.append(Path(ruta).relative_to(datos).as_posix())
        return pd.DataFrame({"DateTime": pd.to_datetime(["2026-01-01"])})

    monkeypatch.setattr(pd, "read_parquet", leer)
    real.cargar_capas(datos)
    relativas = {
        *leidos,
        (real.carpeta_modelos(datos) / "metadatos.json").relative_to(datos).as_posix(),
        hib.ruta_fundacional(datos).relative_to(datos).as_posix(),
        hib.ruta_ajustado(datos).relative_to(datos).as_posix(),
        hib.ruta_pesos(datos).relative_to(datos).as_posix(),
        *[(hib.carpeta_hibrido(datos) / f"xgb_{hib.FUNDACIONAL}_{h}.joblib").relative_to(datos).as_posix()
          for h in ("1h", "24h")],
        "reportes/sein/prueba_2026/adaptacion.csv",  # ruta escrita en _adaptacion_notebook_03
    }
    assert relativas == set(ESTATICOS)
    r = rutas(datos)
    assert {p.relative_to(datos).as_posix() for p in (r.pronosticos, r.seguimiento, r.resumen)} == set(EN_VIVO)


def test_armar_paquete_comprime_los_modelos_y_los_lee_joblib(tmp_path):
    datos, paquete = datos_falsos(tmp_path / "datos"), tmp_path / "paquete"
    mensajes = []
    manifiesto = armar_paquete(datos, paquete, progreso=mensajes.append)
    modelo = paquete / "modelos/sein/app/xgboost_global_24h_M3.joblib"
    assert modelo.read_bytes()[:6] == b"\xfd7zXZ\x00"  # xz
    assert joblib.load(modelo)["clave"] == "24h_M3"
    np.testing.assert_array_equal(joblib.load(modelo)["pesos"], np.arange(1000.0))
    assert not (paquete / "modelos/sein/app_viejo.joblib").exists()
    assert set(manifiesto["archivos"]) == {*ESTATICOS, *[f"modelos/sein/app/xgboost_global_{c}.joblib" for c in CLAVES]}
    assert manifiesto["en_vivo"] == list(EN_VIVO)
    assert verificar(paquete) == []
    assert "Curva" in (paquete / "README.md").read_text()
    # La segunda vez no recomprime nada y el manifiesto queda igual (subirlo de nuevo no hace commit)
    antes = (paquete / MANIFIESTO).read_text()
    mensajes.clear()
    armar_paquete(datos, paquete, progreso=mensajes.append)
    assert not any("comprime" in m or "copia" in m for m in mensajes)
    assert (paquete / MANIFIESTO).read_text() == antes


def test_verificar_detecta_archivos_rotos_o_faltantes(tmp_path):
    paquete = tmp_path / "paquete"
    armar_paquete(datos_falsos(tmp_path / "datos"), paquete, progreso=lambda _: None)
    (paquete / "exogenas/silver/icen.parquet").write_bytes(b"otro contenido de igual largo..")
    (paquete / "coes/silver/demanda_areas.parquet").unlink()
    problemas = verificar(paquete)
    assert any("falta coes/silver/demanda_areas.parquet" in p for p in problemas)
    assert any("icen.parquet" in p for p in problemas)
    assert verificar(tmp_path) == [f"no hay {MANIFIESTO} legible en {tmp_path}"]


def test_sin_los_modelos_de_la_app_no_hay_paquete(tmp_path):
    with pytest.raises(ErrorPaquete, match="modelos de la app"):
        armar_paquete(tmp_path, tmp_path / "paquete")


def test_los_opcionales_pueden_faltar(tmp_path):
    datos = datos_falsos(tmp_path / "datos")
    (datos / "reportes/sein/fundacionales/simons_c2048.parquet").unlink()
    (datos / EN_VIVO[0]).unlink()
    manifiesto = armar_paquete(datos, tmp_path / "paquete", progreso=lambda _: None)
    assert manifiesto["omitidos"] == ["reportes/sein/fundacionales/simons_c2048.parquet"]
    assert EN_VIVO[0] not in manifiesto["en_vivo"]
    assert verificar(tmp_path / "paquete") == []


# ---- arranque del contenedor -----------------------------------------------------------------------------------------


@pytest.fixture
def paquete(tmp_path):
    destino = tmp_path / "dataset"
    armar_paquete(datos_falsos(tmp_path / "datos"), destino, progreso=lambda _: None)
    return destino


def test_arranque_baja_el_paquete_y_usa_el_modelo_real(paquete, tmp_path):
    cache = tmp_path / "cache"
    cambios, fuente, carpeta = arranque.preparar({"TPF_HF_DATASET": str(paquete), "TPF_CACHE": str(cache)})
    assert cambios == {"TETOUAN_DATA": str(cache), "TPF_PRONOSTICADOR": "real", "TPF_SI_FALLA": "prueba"}
    assert isinstance(fuente, arranque.FuenteCarpeta) and carpeta == cache
    assert verificar(cache) == []


def test_si_la_descarga_falla_arranca_con_datos_de_prueba_y_lo_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(arranque.time, "sleep", lambda _: None)
    cambios, fuente, _ = arranque.preparar({"TPF_HF_DATASET": str(tmp_path / "no-existe"),
                                            "TPF_CACHE": str(tmp_path / "cache")})
    assert cambios["TPF_PRONOSTICADOR"] == "prueba" and fuente is None
    assert "No se pudieron bajar los datos reales" in cambios["TPF_AVISO"]


def test_un_paquete_corrupto_tambien_cae_a_los_datos_de_prueba(paquete, tmp_path, monkeypatch):
    monkeypatch.setattr(arranque.time, "sleep", lambda _: None)
    (paquete / "exogenas/silver/icen.parquet").write_bytes(b"x")
    cambios, _, _ = arranque.preparar({"TPF_HF_DATASET": str(paquete), "TPF_CACHE": str(tmp_path / "cache")})
    assert cambios["TPF_PRONOSTICADOR"] == "prueba"
    assert "verificación" in cambios["TPF_AVISO"]


def test_sin_dataset_usa_la_carpeta_montada_o_los_datos_de_prueba(tmp_path):
    cambios, fuente, _ = arranque.preparar({})
    assert "TPF_PRONOSTICADOR" not in cambios and fuente is None
    datos = datos_falsos(tmp_path)
    cambios, _, _ = arranque.preparar({"TETOUAN_DATA": str(datos)})
    assert cambios["TPF_PRONOSTICADOR"] == "real"


def test_fuente_de():
    assert isinstance(arranque.fuente_de("/datos/paquete", None), arranque.FuenteCarpeta)
    assert isinstance(arranque.fuente_de("file:///datos", None), arranque.FuenteCarpeta)
    hub = arranque.fuente_de("rosewt/curva-datos", "hf_x")
    assert isinstance(hub, arranque.FuenteHub) and hub.repo_id == "rosewt/curva-datos"
    with pytest.raises(ValueError):
        arranque.fuente_de("no es un repo", None)


def test_la_recarga_trae_el_registro_nuevo_y_la_api_lo_relee(paquete, tmp_path):
    from app.backend.en_vivo import LectorEnVivo

    cache = tmp_path / "cache"
    pd.DataFrame({"valor": [1]}).to_parquet(paquete / EN_VIVO[0])
    fuente = arranque.FuenteCarpeta(paquete)
    fuente.bajar(cache)
    lector = LectorEnVivo(cache / "reportes/sein/en_vivo")
    assert lector._leer("pronosticos.parquet")["valor"].tolist() == [1]
    pd.DataFrame({"valor": [1, 2]}).to_parquet(paquete / EN_VIVO[0])

    parar = threading.Event()

    class UnaVuelta:
        def bajar(self, destino, rutas=None):
            fuente.bajar(destino, rutas)
            assert rutas == EN_VIVO
            parar.set()

    arranque.recargar(UnaVuelta(), cache, minutos=0.0001, parar=parar)
    assert lector._leer("pronosticos.parquet")["valor"].tolist() == [1, 2]


# ---- la API con el aviso ---------------------------------------------------------------------------------------------


def _cliente(app):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        from fastapi.testclient import TestClient
    return TestClient(app)


def test_salud_lleva_el_aviso():
    pytest.importorskip("fastapi")
    from app.backend.main import crear_app

    assert _cliente(crear_app()).get("/salud").json()["aviso"] is None
    assert _cliente(crear_app(aviso="sin datos")).get("/salud").json()["aviso"] == "sin datos"


def test_si_el_modelo_real_no_carga_la_api_arranca_en_prueba_solo_si_se_pide(tmp_path, monkeypatch):
    pytest.importorskip("fastapi")
    from app.backend import main

    monkeypatch.setenv("TPF_PRONOSTICADOR", "real")
    monkeypatch.setenv("TETOUAN_DATA", str(tmp_path))
    monkeypatch.delenv("TPF_SI_FALLA", raising=False)
    with pytest.raises(FileNotFoundError):
        main._app_por_defecto()
    monkeypatch.setenv("TPF_SI_FALLA", "prueba")
    salud = _cliente(main._app_por_defecto()).get("/salud").json()
    assert salud["modelo"] == "prueba"
    assert "No se pudo cargar el modelo real" in salud["aviso"]


def test_la_web_busca_la_api_en_su_mismo_origen():
    """En el Space la web está detrás de HTTPS sin puerto: buscar la API en :8000 la dejaría sin datos."""
    for archivo in ("app.js", "index.html"):
        texto = (RAIZ / "app/web" / archivo).read_text()
        assert "location.origin" in texto and "location.port === '8080'" in texto, archivo
    assert 'id="bannerAviso"' in (RAIZ / "app/web/index.html").read_text()


# ---- cuenta y scripts de publicación ---------------------------------------------------------------------------------


def info(nombre="rosewt", orgs=(), rol="write"):
    return {"name": nombre, "orgs": [{"name": o} for o in orgs], "auth": {"accessToken": {"role": rol}}}


def test_verificar_cuenta():
    assert verificar_cuenta(info(), "rosewt") == "rosewt"
    assert verificar_cuenta(info(orgs=["Percep3"]), "Percep3") == "rosewt"
    for mala, destino in [(info("cip-itlicenses"), "cip-itlicenses"), (info(orgs=["CIPotato"]), "rosewt"),
                          (info(), "cipotato-it"), (info("otra"), "rosewt"), (info(rol="read"), "rosewt")]:
        with pytest.raises(ErrorCuenta):
            verificar_cuenta(mala, destino)


def test_el_token_solo_sale_de_hf_token():
    assert token_personal({"HF_TOKEN": " hf_abc "}) == "hf_abc"
    with pytest.raises(ErrorCuenta, match="HF_TOKEN"):
        token_personal({})


def test_el_space_lleva_todo_lo_que_copia_el_dockerfile():
    rutas = set(publicar_hf.archivos_codigo())
    copiados = []
    for linea in (RAIZ / "Dockerfile").read_text().splitlines():
        if linea.startswith("COPY") and "--from" not in linea:
            copiados += linea.split()[1:-1]
    for fuente in copiados:
        assert fuente in rutas or any(r.startswith(fuente.rstrip("/") + "/") for r in rutas), fuente
    assert "src/tetouan_power_forecast/tablas/feriados_pe_2015_2026.csv" in rutas
    assert not any(r.startswith(("tests/", "notebooks/", "data/")) or "__pycache__" in r for r in rutas)


def test_la_ficha_del_space_usa_el_puerto_del_dockerfile():
    ficha = publicar_hf.ficha_space("Curva", "rosewt/curva-datos")
    assert re.search(r"^sdk: docker$", ficha, re.MULTILINE) and re.search(r"^app_port: 7860$", ficha, re.MULTILINE)
    assert "- rosewt/curva-datos" in ficha
    corta = re.search(r"^short_description: (.*)$", ficha, re.MULTILINE).group(1)
    assert len(corta) <= 60
    assert "PORT=7860" in (RAIZ / "Dockerfile").read_text()
    assert "datasets:" not in publicar_hf.ficha_space("Curva", None)


def test_publicar_en_dry_run_no_usa_la_red(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    datos = datos_falsos(tmp_path / "datos")
    assert publicar_hf.main(["rosewt", "--dry-run", "--datos", str(datos), "--paquete", str(tmp_path / "p")]) == 0
    salida = capsys.readouterr().out
    assert "rosewt/curva-datos, privado" in salida and "rosewt/curva: Docker, CPU básico, privado" in salida
    assert publicar_hf.main(["rosewt", "--dry-run", "--sin-datos"]) == 0
    assert publicar_hf.main(["cip-itlicenses", "--dry-run"]) == 2
    assert publicar_hf.main(["rosewt"]) == 2  # sin HF_TOKEN no sigue


def test_actualizar_solo_sube_lo_que_cambio(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    datos, estado = datos_falsos(tmp_path / "datos"), tmp_path / "estado.json"
    argumentos = ["rosewt", "--datos", str(datos), "--estado", str(estado)]
    assert actualizar_hf.main([*argumentos, "--dry-run"]) == 0
    assert "pronosticos.parquet" in capsys.readouterr().out
    actualizar_hf.guardar_estado(estado, actualizar_hf.cambiados(datos, {}))
    assert actualizar_hf.main(argumentos) == 0  # ya subido: ni siquiera pide el token
    assert "al día" in capsys.readouterr().out
    (datos / EN_VIVO[1]).write_bytes(b"seguimiento nuevo")
    assert list(actualizar_hf.cambiados(datos, actualizar_hf.leer_estado(estado))) == [EN_VIVO[1]]
    assert actualizar_hf.main(argumentos) == 2  # cambió algo y no hay HF_TOKEN

