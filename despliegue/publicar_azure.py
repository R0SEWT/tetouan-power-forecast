#!/usr/bin/env python3
"""Publica Curva en Azure App Service (Linux, plan B1) con el crédito de la suscripción «Azure for Students».

Es un despliegue de CÓDIGO: arma un zip con el código de la app y un ``requirements.txt`` sacado de ``uv.lock``, lo
sube, y App Service (su compilador, Oryx) instala las dependencias en Azure. En la laptop no se construye ninguna imagen
ni se baja nada pesado: el zip pesa ~1 MB. Los datos (68 MB) los baja la app al arrancar del dataset público
``rosewt/curva-datos`` (``despliegue/arranque.py``). Desde la raíz del repo, con ``az login`` hecho con la cuenta UPC:

    python despliegue/publicar_azure.py --dry-run      # muestra los comandos, sin tocar Azure
    python despliegue/publicar_azure.py                # crea lo que falte, configura, despliega y prueba
    python despliegue/publicar_azure.py --solo-config  # solo vuelve a aplicar y verificar la configuración
    python despliegue/publicar_azure.py --logs         # las últimas líneas del log de la app (y de la plataforma)
    python despliegue/publicar_azure.py --reiniciar    # detener y prender (en B1, en vez de az webapp restart)

Qué hace, en orden (y nada de lo que ya está hecho):

1. Revisa que la suscripción sea «Azure for Students» y la cuenta, de la UPC. Pasa ``--subscription`` en CADA comando:
   no cambia la suscripción por defecto del CLI (que en la máquina del dueño es la del trabajo).
2. Crea, si faltan, el grupo de recursos, el plan B1 Linux y la Web App (Python 3.13), con etiquetas.
3. Configura y luego VERIFICA leyendo de vuelta: «Always On», HTTPS obligatorio, TLS 1.2, sin FTP, comando de inicio,
   comprobación de salud, variables de la app y logs del contenedor. Todo en ASCII (Azure dañó tildes y comillas en
   otro despliegue de esta suscripción).
4. Sube el zip a Kudu (el sitio SCM de la app) y espera a que la compilación termine; luego espera ``/salud`` y corre la
   prueba de humo (``humo.py``).

**Por qué no ``az webapp deploy`` ni ``az webapp log tail``:** piden el token de Kudu en el tenant de la suscripción POR
DEFECTO del CLI, no en el de ``--subscription``. En la máquina del dueño la de por defecto es de otro tenant (el del
trabajo) y Kudu responde 403 (se comprobó: el mismo pedido con un token del tenant de la UPC da 200). Este script pide
el token con ``az account get-access-token --subscription``, que sí elige el tenant correcto, y habla con la API de Kudu
directamente. El token no se imprime ni se guarda. La autenticación básica (usuario y clave de publicación) queda
apagada, como la crea Azure.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:  # para correrlo como script: python despliegue/publicar_azure.py
    sys.path.insert(0, str(RAIZ))

from despliegue import humo

SUSCRIPCION = "Azure for Students"
DOMINIO = "@upc.edu.pe"  # la cuenta con que se entra a esa suscripción; nunca la del trabajo
GRUPO, PLAN, APP = "curva-rg", "curva-plan", "curva-sein"
# La más cercana a Lima entre las que permite la política de la suscripción (brazilsouth, mexicocentral, eastus2,
# canadacentral, southcentralus): ~104 ms de conexión TCP desde Lima, frente a 131 de East US 2 y 155 de Mexico Central
REGION = "brazilsouth"
SKU = "B1"
# Planes de 1.75 GB o menos: no caben a la vez la app vieja y la nueva (~1.2 GB cada una) mientras App Service cambia de
# una a otra. Al desplegar en B1 así, la máquina se quedó sin memoria y Azure movió la app a otra (~10 min caída). En
# estos planes el script detiene la app mientras Oryx compila y la vuelve a prender con el código nuevo.
PLANES_CHICOS = frozenset({"F1", "B1", "S1"})
RUNTIME = "PYTHON:3.13"  # la misma versión del Dockerfile
ETIQUETAS = {"proyecto": "curva", "curso": "upc-mds"}
INICIO = "python despliegue/arranque.py"
SALUD = "/salud"
AJUSTES = {
    "SCM_DO_BUILD_DURING_DEPLOYMENT": "true",  # Oryx instala requirements.txt en Azure
    "TPF_HF_DATASET": "rosewt/curva-datos",  # público: no hace falta token
    "TPF_PRONOSTICADOR": "real",
    "TPF_CACHE": "/tmp/curva-datos",  # disco local: cada arranque baja el paquete limpio (segundos dentro de Azure)
    "TPF_RECARGA_MIN": "15",
    "HF_HOME": "/tmp/hf",  # la caché de huggingface_hub, fuera del /home persistente
    "MALLOC_ARENA_MAX": "2",  # menos memoria fragmentada: la B1 tiene 1.75 GB y la app usa ~1.25
    "PYTHONUNBUFFERED": "1",
    "WEBSITES_CONTAINER_START_TIME_LIMIT": "900",  # 15 min para bajar los datos y cargar los modelos (230 s por defecto)
}
CONFIG = {  # lo que se espera leer de vuelta en ``az webapp config show``
    "alwaysOn": True,
    "http20Enabled": True,
    "minTlsVersion": "1.2",
    "ftpsState": "Disabled",
    "linuxFxVersion": RUNTIME.replace(":", "|"),
    "appCommandLine": INICIO,
    "healthCheckPath": SALUD,
}
# El código que va al zip: lo mismo que copia el Dockerfile, sin pyproject.toml ni uv.lock (con ellos Oryx usaría uv
# y el lock completo, NCCL incluido); las dependencias van en requirements.txt
CODIGO = ("app/__init__.py", "despliegue/__init__.py", "despliegue/arranque.py", "despliegue/paquete.py")
CARPETAS_CODIGO = ("src", "app/backend", "app/web")
EXTRAS = ("app", "despliegue")
# XGBoost para Linux depende de NCCL (cientos de MB, solo para varias GPU). xgboost-cpu es la misma versión compilada
# sin CUDA: el módulo se llama igual y las predicciones salen idénticas (se compararon 462 pedidos de la API)
SIN_NCCL = ("nvidia-nccl-cu12", "nvidia-nccl-cu13")


ESTADOS_KUDU = {0: "pendiente", 1: "compilando", 2: "desplegando", 3: "falló", 4: "listo", 5: "en conflicto",
                6: "a medias"}


class ErrorAzure(RuntimeError):
    """Algo de Azure impide seguir (suscripción equivocada, un comando que falla, una configuración que no quedó)."""


def ascii_o_error(valor: str, que: str) -> str:
    if not valor.isascii():
        raise ErrorAzure(f"{que} tiene caracteres que no son ASCII: {valor!r}")
    return valor


def version_bloqueada(paquete: str, lock: Path = RAIZ / "uv.lock") -> str:
    for p in tomllib.loads(lock.read_text())["package"]:
        if p["name"] == paquete:
            return p["version"]
    raise ErrorAzure(f"{paquete} no está en {lock.name}")


def requisitos(raiz: Path = RAIZ) -> str:
    """El requirements.txt: las versiones exactas de ``uv.lock`` (extras app y despliegue), sin NCCL y con xgboost-cpu."""
    uv = shutil.which("uv")
    if uv is None:
        raise ErrorAzure("hace falta uv para sacar requirements.txt de uv.lock")
    excluir = [arg for paquete in ("xgboost", *SIN_NCCL) for arg in ("--no-emit-package", paquete)]
    comando = [uv, "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes", "--no-header",
               "--no-annotate", *[arg for extra in EXTRAS for arg in ("--extra", extra)], *excluir]
    lineas = subprocess.run(comando, cwd=raiz, check=True, capture_output=True, text=True).stdout.splitlines()
    lineas = [linea for linea in lineas if linea.strip() and not linea.startswith("#")]
    cabecera = ["# Generado por despliegue/publicar_azure.py desde uv.lock (no editar a mano): extras "
                + " y ".join(EXTRAS) + ", sin NCCL, con xgboost-cpu (la misma version, sin CUDA)."]
    texto = "\n".join([*cabecera, *lineas, f"xgboost-cpu=={version_bloqueada('xgboost', raiz / 'uv.lock')}"]) + "\n"
    return ascii_o_error(texto, "requirements.txt")


def archivos_codigo(raiz: Path = RAIZ) -> list[str]:
    """Las rutas relativas del código que va al zip."""
    rutas = [r for r in CODIGO if (raiz / r).exists()]
    for carpeta in CARPETAS_CODIGO:
        for archivo in sorted((raiz / carpeta).rglob("*")):
            relativa = archivo.relative_to(raiz)
            if archivo.is_file() and "__pycache__" not in relativa.parts and archivo.suffix != ".pyc":
                rutas.append(relativa.as_posix())
    return rutas


def armar_zip(destino: Path, raiz: Path = RAIZ, texto_requisitos: str | None = None) -> list[str]:
    """Escribe el zip del despliegue (código + requirements.txt en la raíz). Devuelve las rutas que lleva."""
    rutas = archivos_codigo(raiz)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("requirements.txt", texto_requisitos if texto_requisitos is not None else requisitos(raiz))
        for ruta in rutas:
            z.write(raiz / ruta, ruta)
    return ["requirements.txt", *rutas]


class Azure:
    """Llama a ``az`` siempre con la suscripción explícita. En ``--dry-run`` solo imprime los comandos."""

    def __init__(self, suscripcion: str = SUSCRIPCION, simular: bool = False, mostrar=print):
        self.suscripcion, self.simular, self.mostrar = suscripcion, simular, mostrar

    def comando(self, *args: str) -> list[str]:
        for arg in args:
            ascii_o_error(arg, "un argumento de az")
        return ["az", *args, "--subscription", self.suscripcion, "--only-show-errors", "-o", "json"]

    def __call__(self, *args: str, puede_faltar: bool = False, timeout: float = 600):
        comando = self.comando(*args)
        if self.simular:
            self.mostrar("  " + " ".join(f"'{a}'" if " " in a or "|" in a else a for a in comando))
            return None
        r = subprocess.run(comando, capture_output=True, text=True, timeout=timeout, check=False)
        if r.returncode != 0:
            if puede_faltar and ("ResourceNotFound" in r.stderr or "could not be found" in r.stderr
                                 or "was not found" in r.stderr or "ResourceGroupNotFound" in r.stderr):
                return None
            raise ErrorAzure(f"az {' '.join(args[:3])}: {r.stderr.strip()[:800]}")
        return json.loads(r.stdout) if r.stdout.strip() else None


class Kudu:
    """La API de Kudu (``https://APP.scm.azurewebsites.net``) con un token de Entra ID del tenant de la suscripción."""

    def __init__(self, az: Azure, app: str):
        self.az, self.app = az, app
        self.base = f"https://{app}.scm.azurewebsites.net"
        self._token: tuple[str, float] | None = None

    ALCANCE = "https://appservice.azure.com/.default"

    def token(self) -> str:
        if self._token is None or time.monotonic() > self._token[1]:
            r = self.az("account", "get-access-token", "--scope", self.ALCANCE)
            self._token = (r["accessToken"], time.monotonic() + 30 * 60)
        return self._token[0]

    def pedir(self, ruta: str, datos: bytes | None = None, timeout: float = 120) -> tuple[int, bytes]:
        cabeceras = {"Authorization": f"Bearer {self.token()}", "User-Agent": "curva-publicar-azure/1"}
        if datos is not None:
            cabeceras["Content-Type"] = "application/octet-stream"
        pedido = urllib.request.Request(self.base + ruta, data=datos, headers=cabeceras,
                                        method="POST" if datos is not None else "GET")
        try:
            with urllib.request.urlopen(pedido, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def json(self, ruta: str):
        codigo, cuerpo = self.pedir(ruta)
        if codigo == 404:
            return None
        if codigo != 200:
            raise ErrorAzure(f"Kudu {ruta}: HTTP {codigo} {cuerpo[:300]!r}")
        return json.loads(cuerpo) if cuerpo.strip() else None

    def ultimo(self) -> dict | None:
        try:
            return self.json("/api/deployments/latest")
        except (ErrorAzure, OSError):  # Kudu ocupado o despertando: se vuelve a preguntar
            return None

    def despertar(self, minutos: float = 10, mostrar=print) -> dict | None:
        """Espera a que Kudu responda (tras detener la app o cambiar de máquina tardó más de 2 min en contestar).
        Devuelve el último despliegue, o ``None`` si todavía no hay ninguno."""
        limite = time.monotonic() + minutos * 60
        while True:
            try:
                codigo, cuerpo = self.pedir("/api/deployments/latest", timeout=60)
                if codigo in (200, 404):
                    return json.loads(cuerpo) if codigo == 200 and cuerpo.strip() else None
                problema = f"HTTP {codigo}"
            except OSError as error:
                problema = str(error) or type(error).__name__
            if time.monotonic() >= limite:
                raise ErrorAzure(f"Kudu ({self.base}) no respondió en {minutos:.0f} min: {problema}")
            mostrar(f"  Kudu todavía no responde ({problema}); reintento en 20 s")
            time.sleep(20)

    def log_despliegue(self, id_despliegue: str, lineas: int = 40) -> list[str]:
        mensajes = []
        for entrada in self.json(f"/api/deployments/{id_despliegue}/log") or []:
            mensajes.append(entrada.get("message", ""))
            if entrada.get("details_url"):
                detalle = self.json(entrada["details_url"].removeprefix(self.base)) or []
                mensajes.extend("    " + d.get("message", "") for d in detalle)
        return mensajes[-lineas:]

    def desplegar(self, zip_ruta: Path, minutos: float = 30, mostrar=print) -> dict:
        """Sube el zip (OneDeploy) y espera a que Oryx compile y la app se reinicie con el código nuevo.

        Aunque se pide asíncrono, en Linux Kudu respondió recién al terminar la compilación (~7 min la primera vez): por
        eso el plazo del POST es largo, y si sí responde enseguida (202) se sigue el estado en ``deployments/latest``."""
        anterior = (self.despertar(mostrar=mostrar) or {}).get("id")
        codigo, cuerpo = self.pedir("/api/publish?type=zip&async=true", zip_ruta.read_bytes(), timeout=minutos * 60)
        if codigo not in (200, 202):
            raise ErrorAzure(f"Kudu no aceptó el zip: HTTP {codigo} {cuerpo[:300]!r}")
        limite, visto, primera = time.monotonic() + minutos * 60, None, True
        while time.monotonic() < limite:
            if not primera:
                time.sleep(10)
            primera = False
            estado = self.ultimo() or {}
            if estado.get("id") in (None, anterior):
                continue
            texto = ESTADOS_KUDU.get(estado.get("status"), str(estado.get("status")))
            if texto != visto:
                mostrar(f"  Kudu: {texto}" + (f" ({estado['status_text']})" if estado.get("status_text") else ""))
                visto = texto
            if estado.get("complete"):
                if estado.get("status") != 4:
                    log = "\n    ".join(self.log_despliegue(estado["id"]))
                    raise ErrorAzure(f"el despliegue {estado['id']} terminó «{texto}». Log:\n    {log}")
                return estado
        raise ErrorAzure(f"el despliegue no terminó en {minutos:.0f} min (ver {self.base}/api/deployments/latest)")

    def logs(self, lineas: int = 60) -> str:
        """Las últimas líneas de los logs del contenedor de la app y de la plataforma (los más recientes)."""
        archivos = sorted(self.json("/api/logs/docker") or [], key=lambda a: a.get("lastUpdated", ""))
        salida = []
        for sufijo in ("_docker.log", "_default_docker.log"):
            elegidos = [a for a in archivos if a["href"].endswith(sufijo) and (sufijo != "_docker.log"
                        or not a["href"].endswith(("_default_docker.log", "_scm_docker.log")))]
            if not elegidos:
                continue
            codigo, cuerpo = self.pedir(elegidos[-1]["href"].removeprefix(self.base), timeout=60)
            texto = cuerpo.decode(errors="replace").splitlines()[-lineas:] if codigo == 200 else [f"HTTP {codigo}"]
            salida += [f"== {elegidos[-1]['href'].rsplit('/', 1)[-1]} ==", *texto]
        return "\n".join(salida) or "No hay logs del contenedor todavía."


class Publicador:
    def __init__(self, args, az: Azure):
        self.args, self.az = args, az
        self.base = ["--resource-group", args.grupo]

    @property
    def url(self) -> str:
        return f"https://{self.args.app}.azurewebsites.net"

    def revisar_cuenta(self) -> None:
        cuenta = self.az("account", "show")
        if cuenta is None:  # --dry-run
            return
        usuario = (cuenta.get("user") or {}).get("name", "")
        if cuenta.get("name") != SUSCRIPCION or not usuario.lower().endswith(DOMINIO):
            raise ErrorAzure(f"la suscripción es «{cuenta.get('name')}» con una cuenta que no es {DOMINIO}: "
                             f"este script solo publica en «{SUSCRIPCION}» con la cuenta de la UPC")
        self.az.mostrar(f"Suscripción «{cuenta['name']}» ({cuenta.get('state')}), cuenta {DOMINIO}.")

    def etiquetas(self) -> list[str]:
        return ["--tags", *[f"{k}={v}" for k, v in ETIQUETAS.items()]]

    def crear(self) -> None:
        a, az = self.args, self.az
        if az.simular or az("group", "show", "--name", a.grupo, puede_faltar=True) is None:
            az.mostrar(f"Grupo de recursos {a.grupo} en {a.region}:")
            az("group", "create", "--name", a.grupo, "--location", a.region, *self.etiquetas())
        plan = None if az.simular else az("appservice", "plan", "show", "--name", a.plan, *self.base,
                                          puede_faltar=True)
        if plan is None:
            az.mostrar(f"Plan {a.plan} ({a.sku or SKU}, Linux):")
            az("appservice", "plan", "create", "--name", a.plan, *self.base, "--location", a.region, "--is-linux",
               "--sku", a.sku or SKU, "--number-of-workers", "1", *self.etiquetas())
        if az.simular or az("webapp", "show", "--name", a.app, *self.base, puede_faltar=True) is None:
            az.mostrar(f"Web App {a.app} ({RUNTIME}):")
            az("webapp", "create", "--name", a.app, *self.base, "--plan", a.plan, "--runtime", RUNTIME,
               "--startup-file", INICIO, "--https-only", "true", *self.etiquetas())

    def cambiar_sku(self) -> None:
        """Con ``--sku``, si el plan ya existe en otro tamaño, lo cambia (subir a B2, o volver de F1 a B1)."""
        a, az = self.args, self.az
        if not a.sku:
            return
        plan = None if az.simular else az("appservice", "plan", "show", "--name", a.plan, *self.base)
        if az.simular or plan["sku"]["name"] != a.sku:
            az.mostrar(f"Plan {a.plan}: a {a.sku}" + (f" (era {plan['sku']['name']})" if plan else "") + ":")
            az("appservice", "plan", "update", "--name", a.plan, *self.base, "--sku", a.sku)

    def leer(self) -> dict:
        """Lo que hoy tiene Azure: el sitio, su configuración, sus variables, los logs y el plan."""
        a, az = self.args, self.az
        return {
            "sitio": az("webapp", "show", "--name", a.app, *self.base),
            "config": az("webapp", "config", "show", "--name", a.app, *self.base),
            "ajustes": {s["name"]: s["value"] for s in az("webapp", "config", "appsettings", "list", "--name", a.app,
                                                           *self.base)},
            "logs": az("webapp", "log", "show", "--name", a.app, *self.base),
            "plan": az("appservice", "plan", "show", "--name", a.plan, *self.base),
        }

    def configurar(self) -> None:
        """Aplica solo lo que falta. Cada cambio de configuración reinicia la app, y en B1 un reinicio arranca la copia
        nueva con la vieja viva (no caben las dos): por eso no se reescribe lo que ya está bien."""
        a, az = self.args, self.az
        az.mostrar("Configuración:")
        actual = None if az.simular else self.leer()
        config = (actual or {}).get("config") or {}
        if az.simular or any(config.get(k) != v for k, v in CONFIG.items()):
            az("webapp", "config", "set", "--name", a.app, *self.base, "--always-on", "true", "--http20-enabled",
               "true", "--min-tls-version", "1.2", "--ftps-state", "Disabled", "--linux-fx-version",
               CONFIG["linuxFxVersion"], "--startup-file", INICIO, "--generic-configurations",
               json.dumps({"healthCheckPath": SALUD}))
        sitio = (actual or {}).get("sitio") or {}
        if az.simular or not sitio.get("httpsOnly") or any((sitio.get("tags") or {}).get(k) != v
                                                         for k, v in ETIQUETAS.items()):
            az("webapp", "update", "--name", a.app, *self.base, "--https-only", "true", "--set",
               *[f"tags.{k}={v}" for k, v in ETIQUETAS.items()])
        ajustes = (actual or {}).get("ajustes") or {}
        faltan = {k: v for k, v in AJUSTES.items() if az.simular or ajustes.get(k) != v}
        if faltan:
            az("webapp", "config", "appsettings", "set", "--name", a.app, *self.base, "--settings",
               *[f"{k}={v}" for k, v in faltan.items()])
        if az.simular or not self._logs_activos((actual or {}).get("logs") or {}):
            az("webapp", "log", "config", "--name", a.app, *self.base, "--docker-container-logging", "filesystem")

    @staticmethod
    def _logs_activos(logs: dict) -> bool:
        return ((logs.get("httpLogs") or {}).get("fileSystem") or {}).get("enabled") is True

    def verificar(self) -> list[str]:
        """Lee de vuelta lo configurado y devuelve lo que no quedó como se pidió."""
        a = self.args
        if self.az.simular:
            return []
        actual = self.leer()
        sitio, config, ajustes, plan = actual["sitio"], actual["config"], actual["ajustes"], actual["plan"]
        problemas = []
        if not sitio.get("httpsOnly"):
            problemas.append("HTTPS obligatorio no quedó activado")
        for k, v in ETIQUETAS.items():
            if (sitio.get("tags") or {}).get(k) != v:
                problemas.append(f"la etiqueta {k}={v} no quedó en la Web App")
        for clave, esperado in CONFIG.items():
            if config.get(clave) != esperado:
                problemas.append(f"{clave} es {config.get(clave)!r}, no {esperado!r}")
        for clave, esperado in AJUSTES.items():
            if ajustes.get(clave) != esperado:
                problemas.append(f"la variable {clave} es {ajustes.get(clave)!r}, no {esperado!r}")
        if not self._logs_activos(actual["logs"]):
            problemas.append("los logs (filesystem) no quedaron activados")
        propiedades = plan.get("properties") or {}  # az 2.9x anida aquí «reserved» (antes venía arriba)
        if not (plan.get("reserved") or propiedades.get("reserved")) or plan.get("kind") != "linux":
            problemas.append("el plan no es Linux")
        if a.sku and (plan.get("sku") or {}).get("name") != a.sku:
            problemas.append(f"el plan es {(plan.get('sku') or {}).get('name')}, no {a.sku}")
        for k, v in ETIQUETAS.items():
            if (plan.get("tags") or {}).get(k) != v:
                problemas.append(f"la etiqueta {k}={v} no quedó en el plan")
        return problemas

    def reiniciar(self) -> None:
        """Detiene y prende la app. En B1 es la forma segura: «az webapp restart» arranca la copia nueva mientras la
        vieja sigue viva, la máquina se queda sin memoria y la app tarda más (o Azure la mueve de máquina)."""
        a, az = self.args, self.az
        az.mostrar(f"Reinicio de {a.app} (detener y prender):")
        az("webapp", "stop", "--name", a.app, *self.base)
        if not az.simular:
            self.esperar_detenida()
        az("webapp", "start", "--name", a.app, *self.base)

    def esperar_detenida(self, segundos: float = 300) -> None:
        """«az webapp stop» vuelve enseguida, pero el contenedor sigue respondiendo unos segundos: si se prende antes,
        no se reinicia nada. Espera a que ``/salud`` deje de dar 200."""
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            try:
                codigo = humo.pedir(self.url, "/salud", timeout=10)[0]
            except OSError:
                return
            if codigo != 200:
                return
            time.sleep(3)
        raise ErrorAzure(f"la app sigue respondiendo {segundos:.0f} s después de detenerla")

    def desplegar(self) -> None:
        a, az = self.args, self.az
        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "curva.zip"
            texto = requisitos()
            rutas = armar_zip(destino, texto_requisitos=texto)
            az.mostrar(f"Zip: {len(rutas)} archivos, {destino.stat().st_size / 1e6:.1f} MB "
                       f"({len(texto.splitlines()) - 1} dependencias fijas). Despliegue (Oryx compila en Azure):")
            inicio = time.monotonic()
            kudu = Kudu(az, a.app)
            sku = a.sku or SKU if az.simular else az("appservice", "plan", "show", "--name", a.plan,
                                                       *self.base)["sku"]["name"]
            detener = sku in PLANES_CHICOS and not a.en_caliente
            if detener:
                az.mostrar(f"El plan es {sku}: no caben dos copias de la app. Se detiene mientras compila "
                           "(~10 min sin servicio) y se prende con el código nuevo.")
                az("webapp", "stop", "--name", a.app, *self.base)
            try:
                if az.simular:
                    az("account", "get-access-token", "--scope", Kudu.ALCANCE)
                    az.mostrar(f"  POST {kudu.base}/api/publish?type=zip&async=true  (el zip, con ese token)")
                    return
                estado = kudu.desplegar(destino, mostrar=az.mostrar)
                az.mostrar(f"Compilado y desplegado en {time.monotonic() - inicio:.0f} s "
                           f"(despliegue {estado['id'][:12]}).")
            finally:
                if detener:  # también si la compilación falló: vuelve a prender (con el código que haya quedado)
                    az("webapp", "start", "--name", a.app, *self.base)

    def publicar(self) -> None:
        self.revisar_cuenta()
        if self.args.logs:
            self.az.mostrar(Kudu(self.az, self.args.app).logs(self.args.logs))
            return
        if self.args.reiniciar:
            self.reiniciar()
            self.probar()
            return
        if not self.args.solo_config:
            self.crear()
        self.cambiar_sku()  # antes de configurar: F1 no admite «Always On»
        self.configurar()
        problemas = self.verificar()
        if problemas:
            raise ErrorAzure("la configuración no quedó como se pidió:\n  - " + "\n  - ".join(problemas))
        if not self.az.simular:
            self.az.mostrar("Configuración verificada (leída de vuelta de Azure).")
        if self.args.solo_config:
            return
        self.desplegar()
        self.probar()

    def probar(self) -> None:
        """Espera ``/salud`` y corre la prueba de humo (salvo en --dry-run o con --no-esperar)."""
        if self.az.simular or self.args.no_esperar:
            return
        self.az.mostrar(f"Prueba de humo en {self.url} (espera hasta {self.args.espera:.0f} min a /salud):")
        if humo.main([self.url, "--esperar", str(self.args.espera * 60)]) != 0:
            raise ErrorAzure("la prueba de humo falló: revisa los logs (python despliegue/publicar_azure.py --logs)")
        self.az.mostrar(f"Listo: {self.url}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Publica Curva en Azure App Service (código + Oryx, plan B1 Linux).")
    p.add_argument("--app", default=APP, help=f"nombre de la Web App (por defecto, {APP}): {APP}.azurewebsites.net")
    p.add_argument("--grupo", default=GRUPO, help=f"grupo de recursos (por defecto, {GRUPO})")
    p.add_argument("--plan", default=PLAN, help=f"plan de App Service (por defecto, {PLAN})")
    p.add_argument("--region", default=REGION, help=f"región al crear (por defecto, {REGION})")
    p.add_argument("--sku", help=f"tamaño del plan (al crearlo, {SKU}); si se da y el plan existe con otro, lo cambia")
    p.add_argument("--solo-config", action="store_true", help="solo aplica y verifica la configuración")
    p.add_argument("--reiniciar", action="store_true",
                   help="detiene y prende la app (en B1, en vez de az webapp restart) y corre la prueba de humo")
    p.add_argument("--logs", type=int, nargs="?", const=60, default=0, metavar="LINEAS",
                   help="muestra las últimas líneas de los logs del contenedor (60) y termina")
    p.add_argument("--espera", type=float, default=15, help="minutos máximos de espera a /salud tras desplegar (15)")
    p.add_argument("--no-esperar", action="store_true", help="no espera a /salud ni corre la prueba de humo")
    p.add_argument("--en-caliente", action="store_true",
                   help="despliega sin detener la app (solo en planes con memoria para dos copias, desde B2)")
    p.add_argument("--dry-run", action="store_true", help="muestra los comandos de az, sin tocar Azure")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    az = Azure(simular=args.dry_run)
    if args.dry_run:
        print(f"Simulación (--dry-run): no se llama a az. Destino: {args.app} en {args.grupo} ({args.region}), "
              f"suscripción «{SUSCRIPCION}».")
    try:
        Publicador(args, az).publicar()
    except (ErrorAzure, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
