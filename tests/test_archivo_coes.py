import hashlib
import json

from tetouan_power_forecast.archivo_coes import Archivo, capturar_json


def test_versiones_conservan_bytes_y_hora_de_observacion(tmp_path):
    ruta = "https://example.test/demanda"
    objetivo = "2026-11-24"
    archivos = []
    for contenido in (b'[{"mw": 1}]', b'[{"mw": 1}]', b'[{"mw": 2}]'):
        captura = Archivo(tmp_path)
        captura.guardar("programacion", objetivo, ruta, contenido, "json")
        archivos.append(captura.cerrar())

    registros = [json.loads(archivo.read_text())[0] for archivo in archivos]
    primero, repetido, revisado = registros
    assert primero["archivo"] == repetido["archivo"] != revisado["archivo"]
    assert len(set(archivos)) == 3
    for contenido, registro in zip((b'[{"mw": 1}]', b'[{"mw": 1}]', b'[{"mw": 2}]'), registros):
        assert (tmp_path / registro["archivo"]).read_bytes() == contenido
        assert registro["sha256"] == hashlib.sha256(contenido).hexdigest()
        assert registro["observado_utc"].endswith("+00:00")


def test_captura_rechaza_json_que_no_es_un_pronostico(tmp_path):
    captura = Archivo(tmp_path)
    capturar_json(captura, "pronostico", "2026-11-24", "https://example.test",
                  lambda *_: b"[42]", campos=("fecha",))
    assert [evento["estado"] for evento in captura.eventos] == ["error"]
    assert not (tmp_path / "objetos").exists()
