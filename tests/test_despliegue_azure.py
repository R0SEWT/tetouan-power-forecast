"""El despliegue en Azure App Service: requirements.txt desde uv.lock, el zip, los comandos de az y la prueba de humo."""

import json
import re
import shutil
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from despliegue import humo, publicar_azure
from despliegue.publicar_azure import ErrorAzure

RAIZ = Path(__file__).resolve().parents[1]


def lock() -> dict[str, str]:
    return {p["name"]: p["version"] for p in tomllib.loads((RAIZ / "uv.lock").read_text())["package"]}


@pytest.mark.skipif(shutil.which("uv") is None, reason="hace falta uv")
def test_requisitos_fijan_las_versiones_del_lock_sin_nccl_y_con_xgboost_cpu():
    texto = publicar_azure.requisitos()
    assert texto.isascii()
    versiones = lock()
    paquetes = {}
    for linea in texto.splitlines():
        if linea.startswith("#"):
            continue
        nombre, version = re.match(r"^([\w.-]+)==([^\s;]+)", linea).groups()
        paquetes[nombre] = version
    assert not any("nccl" in p for p in paquetes)
    assert "xgboost" not in paquetes and paquetes["xgboost-cpu"] == versiones["xgboost"]
    for nombre in ("pandas", "numpy", "scikit-learn", "fastapi", "uvicorn", "huggingface-hub", "holidays", "pyarrow"):
        assert paquetes[nombre] == versiones[nombre], nombre
    assert "pytest" not in paquetes and "jupyterlab" not in paquetes  # sin el grupo dev


def test_el_zip_lleva_lo_que_copia_el_dockerfile_y_no_el_lock(tmp_path):
    destino = tmp_path / "curva.zip"
    rutas = publicar_azure.armar_zip(destino, texto_requisitos="fastapi==1\n")
    with zipfile.ZipFile(destino) as z:
        nombres = set(z.namelist())
        assert z.read("requirements.txt") == b"fastapi==1\n"
    assert nombres == set(rutas)
    copiados = re.findall(r"^COPY (?!--from)(.+) \./", (RAIZ / "Dockerfile").read_text(), flags=re.MULTILINE)
    for linea in copiados:
        for ruta in linea.split():
            if ruta in ("pyproject.toml", "uv.lock"):
                continue  # las dependencias van en requirements.txt
            assert ruta in nombres or any(n.startswith(ruta + "/") for n in nombres), ruta
    assert {"despliegue/arranque.py", "app/backend/main.py", "app/web/index.html"} <= nombres
    assert not nombres & {"pyproject.toml", "uv.lock", "Dockerfile"}  # con ellos Oryx usaría uv y el lock con NCCL
    assert not any("__pycache__" in n or n.endswith(".pyc") for n in nombres)


def test_todo_lo_que_va_a_azure_es_ascii():
    textos = [publicar_azure.INICIO, publicar_azure.RUNTIME, *publicar_azure.ETIQUETAS.values(),
              *publicar_azure.AJUSTES, *publicar_azure.AJUSTES.values(),
              *(str(v) for v in publicar_azure.CONFIG.values())]
    assert all(t.isascii() for t in textos)
    with pytest.raises(ErrorAzure):
        publicar_azure.ascii_o_error("año", "un valor")
    with pytest.raises(ErrorAzure):
        publicar_azure.Azure().comando("webapp", "config", "set", "--startup-file", "python «arranque»")


def test_cada_comando_lleva_la_suscripcion_explicita():
    comando = publicar_azure.Azure().comando("group", "show", "--name", "curva-rg")
    assert comando[comando.index("--subscription") + 1] == "Azure for Students"


def test_dry_run_no_llama_a_az(monkeypatch, capsys):
    monkeypatch.setattr(publicar_azure, "requisitos", lambda raiz=None: "fastapi==1\n")

    def prohibido(comando, *a, **k):
        raise AssertionError(f"no debía correr {comando}")

    monkeypatch.setattr(publicar_azure.subprocess, "run", prohibido)
    assert publicar_azure.main(["--dry-run"]) == 0
    salida = capsys.readouterr().out
    lineas_az = [linea for linea in salida.splitlines() if linea.strip().startswith("az ")]
    assert lineas_az and all("--subscription 'Azure for Students'" in linea for linea in lineas_az)
    for esperado in ("brazilsouth", "--sku B1", "--is-linux", "PYTHON:3.13", "--always-on true", "--https-only true",
                     "TPF_HF_DATASET=rosewt/curva-datos", "WEBSITES_CONTAINER_START_TIME_LIMIT=900",
                     "--docker-container-logging filesystem", "proyecto=curva", "curso=upc-mds",
                     "account get-access-token --scope https://appservice.azure.com/.default",
                     "POST https://curva-sein.scm.azurewebsites.net/api/publish?type=zip&async=true"):
        assert esperado in salida, esperado
    assert "account set" not in salida  # nunca cambia la suscripción por defecto del CLI
    assert "webapp deploy" not in salida  # pide el token de Kudu en el tenant por defecto del CLI (403 aquí)


class AzFalso:
    """Responde lo que Azure devolvería si todo quedó bien; ``cambios`` lo estropea a propósito."""

    simular = False

    def __init__(self, cambios=None, cuenta=None):
        self.cambios = cambios or {}
        self.cuenta = cuenta or {"name": "Azure for Students", "state": "Enabled", "user": {"name": "u1@upc.edu.pe"}}
        self.mensajes = []

    def mostrar(self, texto):
        self.mensajes.append(texto)

    def __call__(self, *args, **kwargs):
        clave = " ".join(args[:3])
        respuestas = {
            "account show": self.cuenta,
            "webapp show --name": {"httpsOnly": True, "tags": dict(publicar_azure.ETIQUETAS)},
            "webapp config show": dict(publicar_azure.CONFIG),
            "webapp config appsettings": [{"name": k, "value": v} for k, v in publicar_azure.AJUSTES.items()],
            "webapp log show": {"httpLogs": {"fileSystem": {"enabled": True}}},
            "appservice plan show": {"kind": "linux", "properties": {"reserved": True}, "sku": {"name": "B1"},
                                     "tags": dict(publicar_azure.ETIQUETAS)},
        }
        respuesta = respuestas.get(clave)
        if isinstance(respuesta, dict):
            respuesta = {**respuesta, **self.cambios.get(clave, {})}
        return respuesta


def publicador(az):
    args = SimpleNamespace(app="curva-sein", grupo="curva-rg", plan="curva-plan", region="brazilsouth", sku=None,
                           solo_config=False, espera=1, no_esperar=True)
    return publicar_azure.Publicador(args, az)


def test_sku_cambia_el_plan_existente_tambien_con_solo_config(monkeypatch, capsys):
    monkeypatch.setattr(publicar_azure, "requisitos", lambda raiz=None: "fastapi==1\n")
    assert publicar_azure.main(["--dry-run", "--solo-config", "--sku", "B2"]) == 0
    salida = capsys.readouterr().out
    assert "appservice plan update --name curva-plan --resource-group curva-rg --sku B2" in salida
    assert salida.index("plan update") < salida.index("webapp config set")  # F1 no admite «Always On»
    assert "plan create" not in salida and "webapp deploy" not in salida and "/api/publish" not in salida


def test_verificar_lee_de_vuelta_y_detecta_lo_que_no_quedo():
    assert publicador(AzFalso()).verificar() == []
    problemas = publicador(AzFalso({"webapp config show": {"alwaysOn": False, "appCommandLine": "python ?arranque"},
                                    "webapp show --name": {"httpsOnly": False}})).verificar()
    assert len(problemas) == 3
    assert any("alwaysOn" in p for p in problemas) and any("appCommandLine" in p for p in problemas)


def test_solo_publica_en_la_suscripcion_de_estudiante_con_la_cuenta_upc():
    publicador(AzFalso()).revisar_cuenta()
    for cuenta in ({"name": "Azure for Students", "user": {"name": "alguien@cgiar.org"}},
                   {"name": "Otra suscripcion", "user": {"name": "u1@upc.edu.pe"}}):
        with pytest.raises(ErrorAzure):
            publicador(AzFalso(cuenta=cuenta)).revisar_cuenta()


def test_el_arranque_corre_como_archivo_sin_pythonpath(tmp_path):
    """App Service corre ``python despliegue/arranque.py`` desde la carpeta de la app, sin el PYTHONPATH del Dockerfile."""
    # -S: sin site-packages, para que el proyecto instalado en modo editable no esconda que falta src/ en el path
    codigo = ("import runpy, sys; from importlib.util import find_spec; m = runpy.run_path(sys.argv[1]); "
              "print(m['EN_VIVO'][0]); print(find_spec('tetouan_power_forecast').origin); "
              "print(find_spec('app.backend.main').origin)")
    entorno = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    r = subprocess.run([sys.executable, "-S", "-c", codigo, str(RAIZ / "despliegue/arranque.py")], cwd=tmp_path,
                       env=entorno, capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    vivo, paquete, api = r.stdout.split()
    assert vivo == "reportes/sein/en_vivo/pronosticos.parquet"
    assert Path(paquete) == RAIZ / "src/tetouan_power_forecast/__init__.py"
    assert Path(api) == RAIZ / "app/backend/main.py"


# ---- prueba de humo --------------------------------------------------------------------------------------------------


def respuestas_sanas(aviso=None, modelo="combinado"):
    html = ('<!doctype html><html><link href="manifest.json"><link href="style.css">'
            '<script src="app.js?v=2"></script></html>')

    def pedir(base, ruta, cuerpo=None, timeout=60):
        if ruta == "/salud":
            valor = {"estado": "ok", "modelo": modelo, "version_datos": "2026-11-21", "aviso": aviso}
        elif ruta == "/modelos":
            valor = [{"id": "combinado", "fecha_max": "2026-10-15"}]
        elif ruta == "/areas":
            valor = [{"id": a} for a in humo.AREAS]
        elif ruta == "/":
            valor = html
        elif ruta.endswith((".js", ".css")):
            valor = "/* recurso */"
        else:
            valor = {"ok": True}
        return 200, valor, 0.05, 100

    return pedir


def test_humo_pasa_con_la_app_sana(monkeypatch):
    monkeypatch.setattr(humo, "pedir", respuestas_sanas())
    filas = humo.comprobar("https://curva.example", mostrar=lambda _: None)
    rutas = [ruta for ruta, *_ in filas]
    assert "GET /salud" in rutas and "GET /ahora/norte" in rutas and "GET /confianza/sur" in rutas
    assert "GET /app.js" in rutas and "GET /style.css" in rutas
    assert not any("manifest" in r for r in rutas)  # «manifest.json» no es «manifest.js»
    assert any(r.startswith("POST /pronostico") for r in rutas)


@pytest.mark.parametrize("aviso, modelo", [("No se pudieron bajar los datos reales", "combinado"), (None, "prueba")])
def test_humo_falla_si_cayo_a_los_datos_de_prueba(monkeypatch, aviso, modelo):
    monkeypatch.setattr(humo, "pedir", respuestas_sanas(aviso, modelo))
    with pytest.raises(humo.ErrorHumo):
        humo.comprobar("https://curva.example", mostrar=lambda _: None)


# ---- Kudu ------------------------------------------------------------------------------------------------------------


class KuduFalso(publicar_azure.Kudu):
    """Kudu con respuestas en cola: ``latest`` devuelve primero el despliegue anterior y luego el nuevo."""

    def __init__(self, estados, anterior="viejo"):
        super().__init__(az=None, app="curva-sein")
        self.estados, self.anterior, self.subido = list(estados), anterior, False

    def token(self):
        return "token-falso"

    def pedir(self, ruta, datos=None, timeout=120):
        if ruta.startswith("/api/publish"):
            self.subido = True
            return 202, b""
        if ruta == "/api/deployments/latest":
            if not self.subido or not self.estados:
                return 200, json.dumps({"id": self.anterior, "status": 4, "complete": True}).encode()
            return 200, self.estados.pop(0).encode()
        if ruta.endswith("/log"):
            return 200, b'[{"message": "pip install fallo", "details_url": null}]'
        return 404, b""


def test_kudu_espera_el_despliegue_nuevo_y_no_toma_el_anterior(tmp_path, monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    zip_ruta = tmp_path / "curva.zip"
    zip_ruta.write_bytes(b"PK")
    kudu = KuduFalso(['{"id": "viejo", "status": 4, "complete": true}',
                      '{"id": "nuevo", "status": 1, "complete": false}',
                      '{"id": "nuevo", "status": 4, "complete": true}'])
    mensajes = []
    assert kudu.desplegar(zip_ruta, mostrar=mensajes.append)["id"] == "nuevo"
    assert any("compilando" in m for m in mensajes)


def test_kudu_falla_con_el_log_si_la_compilacion_falla(tmp_path, monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    zip_ruta = tmp_path / "curva.zip"
    zip_ruta.write_bytes(b"PK")
    kudu = KuduFalso(['{"id": "nuevo", "status": 3, "complete": true}'])
    with pytest.raises(ErrorAzure, match="pip install fallo"):
        kudu.desplegar(zip_ruta, mostrar=lambda _: None)


# ---- calentar la API al arrancar -------------------------------------------------------------------------------------


def test_calentar_espera_la_salud_y_pide_lo_que_la_web_carga_primero(monkeypatch):
    from despliegue import arranque

    monkeypatch.setattr(arranque.time, "sleep", lambda _: None)
    pedidos, intentos = [], iter([OSError("cargando"), OSError("cargando"), 200])

    def pedir(ruta, timeout):
        if ruta == "/salud":
            respuesta = next(intentos)
            if isinstance(respuesta, Exception):
                raise respuesta
            return respuesta
        pedidos.append(ruta)
        if ruta == "/diagnostico/sur":
            raise TimeoutError("lento")
        return 200

    assert arranque.calentar(7860, pedir=pedir) == len(arranque.CALENTAR) - 1  # una falla no corta el resto
    assert pedidos == list(arranque.CALENTAR)
    assert pedidos[0] == "/resumen" and "/confianza/centro?horizonte=24h&variante=M3" in pedidos


def test_calentar_se_rinde_si_la_api_no_abre(monkeypatch):
    from despliegue import arranque

    reloj = iter(range(0, 10_000, 100))
    monkeypatch.setattr(arranque.time, "monotonic", lambda: next(reloj))
    monkeypatch.setattr(arranque.time, "sleep", lambda _: None)

    def pedir(ruta, timeout):
        raise ConnectionRefusedError

    assert arranque.calentar(7860, espera_s=300, pedir=pedir) == 0
