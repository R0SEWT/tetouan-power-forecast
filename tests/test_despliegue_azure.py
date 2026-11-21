"""El despliegue en Azure App Service: requirements.txt desde uv.lock, el zip, los comandos de az y la prueba de humo."""

import itertools
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
                     "TPF_HF_DATASET=rosewt/curva-datos", "WEBSITES_CONTAINER_START_TIME_LIMIT=1800",
                     "--docker-container-logging filesystem", "proyecto=curva", "curso=upc-mds",
                     "account get-access-token --scope https://appservice.azure.com/.default",
                     "POST https://curva-sein.scm.azurewebsites.net/api/publish?type=zip&async=true"):
        assert esperado in salida, esperado
    assert "account set" not in salida  # nunca cambia la suscripción por defecto del CLI
    # en B1 no caben dos copias de la app: se detiene antes de subir el zip y se prende después
    assert salida.index("webapp stop") < salida.index("/api/publish") < salida.index("webapp start")
    assert "webapp deploy" not in salida  # pide el token de Kudu en el tenant por defecto del CLI (403 aquí)


class AzFalso:
    """Responde lo que Azure devolvería si todo quedó bien; ``cambios`` lo estropea a propósito."""

    simular = False

    def __init__(self, cambios=None, cuenta=None, ajustes=None):
        self.cambios = cambios or {}
        self.cuenta = cuenta or {"name": "Azure for Students", "state": "Enabled", "user": {"name": "u1@upc.edu.pe"}}
        self.ajustes = dict(publicar_azure.AJUSTES, **(ajustes or {}))
        self.mensajes, self.escrituras = [], []

    def mostrar(self, texto):
        self.mensajes.append(texto)

    def __call__(self, *args, **kwargs):
        clave = " ".join(args[:3])
        palabras = list(itertools.takewhile(lambda a: not a.startswith("--"), args))
        if palabras[-1] not in ("show", "list"):  # set, update, create, config, stop, start...
            self.escrituras.append(args)
            return None
        respuestas = {
            "account show": self.cuenta,
            "group show --name": {"name": "curva-rg"},
            "webapp show --name": {"httpsOnly": True, "tags": dict(publicar_azure.ETIQUETAS)},
            "webapp config show": dict(publicar_azure.CONFIG),
            "webapp config appsettings": [{"name": k, "value": v} for k, v in self.ajustes.items()],
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
                           solo_config=False, espera=1, no_esperar=True, en_caliente=False, logs=0, reiniciar=False)
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


def test_calentar_pide_lo_que_la_web_carga_primero_y_sigue_si_algo_falla():
    from despliegue import arranque

    pedidos = []

    class Cliente:
        def get(self, ruta):
            pedidos.append(ruta)
            if ruta == "/diagnostico/sur":
                raise RuntimeError("se cayó")
            return SimpleNamespace(status_code=422 if ruta == "/ahora/sur" else 200)

    assert arranque.calentar(None, cliente=Cliente()) == len(arranque.CALENTAR) - 2  # una falla no corta el resto
    assert pedidos == list(arranque.CALENTAR)
    assert pedidos[0] == "/resumen" and "/confianza/centro?horizonte=24h&variante=M3" in pedidos


def test_calentar_con_la_api_de_verdad_deja_el_resumen_listo():
    pytest.importorskip("fastapi")
    from app.backend.main import crear_app
    from despliegue import arranque

    assert arranque.calentar(crear_app(), rutas=("/salud", "/resumen", "/ahora/norte")) == 3


def test_en_caliente_no_detiene_la_app(monkeypatch, capsys):
    monkeypatch.setattr(publicar_azure, "requisitos", lambda raiz=None: "fastapi==1\n")
    assert publicar_azure.main(["--dry-run", "--en-caliente"]) == 0
    salida = capsys.readouterr().out
    assert "webapp stop" not in salida and "/api/publish" in salida


def test_kudu_espera_a_que_despierte_antes_de_subir(tmp_path, monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    zip_ruta = tmp_path / "curva.zip"
    zip_ruta.write_bytes(b"PK")
    kudu = KuduFalso(['{"id": "nuevo", "status": 4, "complete": true}'])
    original, fallas = kudu.pedir, iter([TimeoutError("The read operation timed out"), (503, b"")])

    def pedir(ruta, datos=None, timeout=120):
        if ruta == "/api/deployments/latest" and not kudu.subido:
            falla = next(fallas, None)
            if isinstance(falla, Exception):
                raise falla
            if falla is not None:
                return falla
        return original(ruta, datos, timeout)

    kudu.pedir = pedir
    mensajes = []
    assert kudu.desplegar(zip_ruta, mostrar=mensajes.append)["id"] == "nuevo"
    assert sum("todavía no responde" in m for m in mensajes) == 2


def test_configurar_no_reescribe_lo_que_ya_esta_bien(monkeypatch):
    """Cada escritura reinicia la app; en B1 un reinicio con la app viva no cabe en memoria."""
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    monkeypatch.setattr(publicar_azure.humo, "pedir", lambda base, ruta, timeout=60: (403, "", 0.1, 0))
    az = AzFalso()
    assert publicador(az).configurar() is False
    assert az.escrituras == []
    az = AzFalso(ajustes={"TPF_RECARGA_MIN": "30"})
    assert publicador(az).configurar() is True  # la dejó detenida: la prende quien sigue
    assert az.escrituras[0][:2] == ("webapp", "stop") and len(az.escrituras) == 2
    assert az.escrituras[1][:4] == ("webapp", "config", "appsettings", "set")
    assert "TPF_RECARGA_MIN=15" in az.escrituras[1] and not any("TPF_HF_DATASET" in x for x in az.escrituras[1])


def test_reiniciar_detiene_y_prende(monkeypatch, capsys):
    monkeypatch.setattr(publicar_azure, "requisitos", lambda raiz=None: "fastapi==1\n")
    assert publicar_azure.main(["--dry-run", "--reiniciar"]) == 0
    salida = capsys.readouterr().out
    assert salida.index("webapp stop") < salida.index("webapp start")
    assert "webapp restart" not in salida and "/api/publish" not in salida and "config set" not in salida


def test_reiniciar_espera_a_que_la_app_deje_de_responder(monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    codigos = iter([200, 200, 403])
    monkeypatch.setattr(publicar_azure.humo, "pedir", lambda base, ruta, timeout=60: (next(codigos), "", 0.1, 0))
    az = AzFalso()
    publicador(az).reiniciar()
    assert [e[:2] for e in az.escrituras] == [("webapp", "stop"), ("webapp", "start")]
    assert next(codigos, "agotado") == "agotado"  # preguntó hasta que dejó de dar 200


def test_en_b1_detiene_la_app_antes_de_cambiar_la_configuracion(monkeypatch):
    """Un cambio de configuración reinicia la app solapada; en B1 no caben dos copias."""
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    monkeypatch.setattr(publicar_azure.humo, "pedir", lambda base, ruta, timeout=60: (403, "", 0.1, 0))
    az = AzFalso(ajustes={"TPF_RECARGA_MIN": "30"})
    pub = publicador(az)
    pub.args.solo_config = True
    monkeypatch.setattr(pub, "verificar", list)  # el Azure falso no cambia al escribir: nada que reclamar
    pub.publicar()
    pasos = [e[:2] if e[0] == "webapp" and e[1] in ("stop", "start") else e[:4] for e in az.escrituras]
    assert pasos == [("webapp", "stop"), ("webapp", "config", "appsettings", "set"), ("webapp", "start")]


def test_sin_cambios_de_configuracion_no_detiene_nada():
    az = AzFalso()
    pub = publicador(az)
    pub.args.solo_config = True
    pub.publicar()
    assert az.escrituras == []


def test_si_la_verificacion_falla_vuelve_a_prender_la_app(monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    monkeypatch.setattr(publicar_azure.humo, "pedir", lambda base, ruta, timeout=60: (403, "", 0.1, 0))
    az = AzFalso(ajustes={"TPF_RECARGA_MIN": "30"})  # sigue mal después de escribir: la verificación falla
    pub = publicador(az)
    with pytest.raises(ErrorAzure, match="TPF_RECARGA_MIN"):
        pub.publicar()
    assert az.escrituras[-1][:2] == ("webapp", "start")


def test_si_una_escritura_falla_vuelve_a_prender_la_app(monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    monkeypatch.setattr(publicar_azure.humo, "pedir", lambda base, ruta, timeout=60: (403, "", 0.1, 0))

    class AzQueFalla(AzFalso):
        def __call__(self, *args, **kwargs):
            if args[:4] == ("webapp", "config", "appsettings", "set"):
                raise ErrorAzure("az webapp config: 500")
            return super().__call__(*args, **kwargs)

    az = AzQueFalla(ajustes={"TPF_RECARGA_MIN": "30"})
    pub = publicador(az)
    pub.args.solo_config = True
    with pytest.raises(ErrorAzure, match="500"):
        pub.publicar()
    assert [e[:2] for e in az.escrituras] == [("webapp", "stop"), ("webapp", "start")]


def test_si_falla_armar_el_despliegue_la_app_no_queda_detenida(monkeypatch):
    monkeypatch.setattr(publicar_azure.time, "sleep", lambda _: None)
    monkeypatch.setattr(publicar_azure.humo, "pedir", lambda base, ruta, timeout=60: (403, "", 0.1, 0))

    def sin_uv(raiz=None):
        raise ErrorAzure("hace falta uv")

    monkeypatch.setattr(publicar_azure, "requisitos", sin_uv)
    az = AzFalso(ajustes={"TPF_RECARGA_MIN": "30"})
    pub = publicador(az)
    monkeypatch.setattr(pub, "verificar", list)
    with pytest.raises(ErrorAzure, match="uv"):
        pub.publicar()
    assert az.escrituras[-1][:2] == ("webapp", "start")
