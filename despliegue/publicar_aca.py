#!/usr/bin/env python3
"""Publica Curva en Azure Container Apps (plan Consumption) con la imagen ya construida en ``ghcr.io/r0sewt/curva``.

La imagen la construye GitHub Actions (``.github/workflows/imagen.yml``) en cada push a la rama del despliegue: en la
laptop no se construye ni se baja nada. Container Apps la baja de ghcr.io sin credenciales (el paquete es público) y
la app se apaga sola (cero réplicas) cuando nadie la usa; la primera visita la vuelve a prender. Desde la raíz del
repo, con ``az login`` hecho con la cuenta UPC (no hace falta que sea la suscripción por defecto del CLI):

    python despliegue/publicar_aca.py --dry-run               # muestra los comandos, sin tocar Azure
    python despliegue/publicar_aca.py                         # crea lo que falte, aplica la configuración y verifica
    python despliegue/publicar_aca.py --imagen sha-abc1234    # pasa a otra imagen (la etiqueta de un commit)
    python despliegue/publicar_aca.py --estado                # URL, imagen, revisión y réplicas prendidas
    python despliegue/publicar_aca.py --logs                  # las últimas líneas del contenedor (si está prendido)
    python despliegue/publicar_aca.py --metricas 24           # réplicas, pedidos, memoria y costo de las últimas 24 h
    python despliegue/publicar_aca.py --apagar                # la detiene: nadie la puede despertar
    python despliegue/publicar_aca.py --prender               # la vuelve a prender (y sigue apagándose sola)
    python despliegue/publicar_aca.py --borrar                # borra el grupo de recursos entero (pide confirmar)

Qué hace, en orden (y nada de lo que ya está hecho):

1. Revisa que la suscripción sea «Azure for Students» y la cuenta, de la UPC; pasa ``--subscription`` en CADA comando.
2. Crea, si faltan, el grupo de recursos y el entorno de Container Apps (perfiles de carga, solo el perfil
   Consumption, SIN Log Analytics: los logs no se guardan, se leen en vivo), con etiquetas.
3. Arma la especificación completa de la app (imagen, 1 vCPU y 2 GiB, de 0 a 1 réplica, regla de escala HTTP, ingreso
   externo HTTPS al puerto 7860, sondas y variables), toda en ASCII, y la escribe solo si Azure tiene algo distinto.
   Después la LEE DE VUELTA y se detiene si algo no quedó.
4. Si cambió algo, espera ``/salud`` (eso prende la app desde cero) y corre la prueba de humo (``humo.py``).

Lo que se elige y se conserva entre corridas: la imagen (``--imagen``; si no se da, la que ya tiene la app o, al
crearla, la del commit actual) y el mínimo de réplicas (``--minimo``; si no se da, el que ya tiene, o 0 al crearla).
Todo lo demás se fuerza a lo de este archivo.

**Por qué ``az rest`` (un PUT) y no ``az containerapp create/update``:** el PUT reemplaza la app entera con el JSON
de ``especificacion``, en una versión fija de la API (``API``): lo que no está ahí no queda (por ejemplo, una variable
agregada a mano en el portal), y el CLI no interpreta nada en el medio. ``az rest`` saca el token del tenant de la
suscripción que va en la URL, así que no le pasa lo de Kudu en App Service (ver ``publicar_azure.py``).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:  # para correrlo como script: python despliegue/publicar_aca.py
    sys.path.insert(0, str(RAIZ))

from despliegue import humo
from despliegue.publicar_azure import SUSCRIPCION, Azure, ErrorAzure, ascii_o_error, revisar_cuenta

GRUPO, ENTORNO, APP = "curva-aca-rg", "curva-aca-env", "curva"
REGION = "brazilsouth"  # la más cercana a Lima entre las que permite la suscripción (ver publicar_azure.py)
REGISTRO, REPOSITORIO = "ghcr.io", "r0sewt/curva"
IMAGEN = f"{REGISTRO}/{REPOSITORIO}"
PERFIL = "Consumption"
# El modo del entorno. «Express» es el que creó el CLI (extensión containerapp 1.3.0b4) sin pedirlo, y con el que se
# midió todo: mismas tarifas Consumption y cuotas gratis, sin cargo por el entorno, y arranques en frío de ~21 s
# (agenda el contenedor en ~1 s). No admite dominios propios: para eso hace falta «WorkloadProfiles». Se fija aquí para
# no depender del valor por defecto del CLI, que cambia entre versiones.
MODO = "Express"
API = "2025-07-01"  # la versión estable de la API de Microsoft.App con que se escribe y se lee la app
PUERTO = 7860
CPU, MEMORIA = 1.0, "2Gi"  # la app ocupa ~1 GB al arrancar y 1.25-1.6 GB en uso
MAX_REPLICAS = 1
# Segundos sin pedidos antes de bajar a cero réplicas. 300 es el valor por defecto de Container Apps, y la API lo
# devuelve vacío (null) aunque se mande: la verificación toma el vacío como 300
ESPERA_A_CERO = ESPERA_POR_DEFECTO = 300
CONCURRENCIA = 10  # pedidos simultáneos por réplica antes de pedir otra (con una réplica como máximo, no cambia nada)
ETIQUETAS = {"proyecto": "curva", "curso": "upc-mds"}
SALUD = "/salud"
VARIABLES = {
    "TPF_HF_DATASET": "rosewt/curva-datos",  # público: no hace falta HF_TOKEN
    "TPF_PRONOSTICADOR": "real",
    "TPF_RECARGA_MIN": "15",  # relee el registro en vivo del dataset cada 15 min (no mantiene la app prendida)
    "PORT": str(PUERTO),
    "MALLOC_ARENA_MAX": "2",  # menos memoria fragmentada
    "TPF_CALENTAR": "0",  # abrir el puerto antes de los ~30 s en que la plataforma se rinde (ver SONDAS)
}
# Arranque en frío: la plataforma retiene el primer pedido mientras prende la réplica, pero a los ~30 s se rinde y
# responde 503 «App port is not ready» (se midió: la app abrió el puerto a los 31 s y el primer visitante vio ese error).
# Por eso (1) el puerto se abre sin calentar antes (TPF_CALENTAR=0: abre ~10 s antes, a los ~20 s; en esta CPU cada
# cálculo que se saltea tarda ~1 s cuando la web lo pide) y (2) la sonda de arranque es la que Container Apps pone por
# defecto: TCP cada 1 s, hasta 240 fallas (4 min). Con una sonda HTTP, el tope documentado de 10 fallas obliga a elegir
# entre detectar tarde (cada 10 s o más) o reiniciar pronto. El puerto lo abre uvicorn recién cuando los modelos están
# cargados, así que «el puerto responde» es «la app está lista». Las otras dos también son TCP: con la única CPU
# ocupada en un cálculo largo, /salud puede tardar, pero el puerto sigue aceptando conexiones.
SONDAS = (
    {"type": "Startup", "tcpSocket": {"port": PUERTO}, "initialDelaySeconds": 1, "periodSeconds": 1,
     "timeoutSeconds": 3, "failureThreshold": 240},
    {"type": "Readiness", "tcpSocket": {"port": PUERTO}, "initialDelaySeconds": 1, "periodSeconds": 10,
     "timeoutSeconds": 5, "failureThreshold": 3},
    {"type": "Liveness", "tcpSocket": {"port": PUERTO}, "initialDelaySeconds": 1, "periodSeconds": 30,
     "timeoutSeconds": 5, "failureThreshold": 3},
)
# Grupos que este script nunca borra (el de App Service, el de otro curso y el de Network Watcher)
PROTEGIDOS = frozenset({"curva-rg", "aire-distribuido-rg", "networkwatcherrg"})
# Precios públicos del plan Consumption en Brazil South (USD; API de precios de Azure, 21/11/2026) y lo gratis por
# suscripción y mes
VCPU_ACTIVO, VCPU_REPOSO, GIB = 0.000024, 0.000003, 0.000003
MILLON_PEDIDOS = 0.40
GRATIS_VCPU_S, GRATIS_GIB_S, GRATIS_PEDIDOS = 180_000, 360_000, 2_000_000
SEGUNDOS_MES = 730 * 3600


def referencia(imagen: str) -> str:
    """``sha-abc1234`` (o ``latest`` o ``sha256:...``) a la referencia completa en ghcr.io; nunca otro repositorio."""
    imagen = imagen.strip()
    if "/" not in imagen:
        imagen = f"{IMAGEN}@{imagen}" if imagen.startswith("sha256:") else f"{IMAGEN}:{imagen}"
    if not imagen.startswith((IMAGEN + ":", IMAGEN + "@")):
        raise ErrorAzure(f"la imagen tiene que ser de {IMAGEN}: {imagen}")
    return ascii_o_error(imagen, "la imagen")


def etiqueta_del_commit(raiz: Path = RAIZ) -> str:
    """La etiqueta que el workflow le pone a la imagen del commit actual (``sha-`` y 7 caracteres)."""
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=raiz, capture_output=True, text=True, check=True).stdout
    return f"sha-{sha.strip()[:7]}"


class Registro:
    """La API de ghcr.io sin credenciales (el paquete es público): si existe una etiqueta y a qué digest apunta."""

    ACEPTA = ("application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, "
              "application/vnd.docker.distribution.manifest.v2+json")

    def __init__(self, base: str = f"https://{REGISTRO}", repositorio: str = REPOSITORIO):
        self.base, self.repositorio = base, repositorio

    def _abrir(self, url: str, cabeceras: dict | None = None, metodo: str = "GET"):
        pedido = urllib.request.Request(url, headers={"User-Agent": "curva-publicar-aca/1", **(cabeceras or {})},
                                        method=metodo)
        return urllib.request.urlopen(pedido, timeout=30)

    def digest(self, etiqueta: str) -> str | None:
        """El digest de la etiqueta, o ``None`` si no existe. Falla si el paquete no se puede leer sin credenciales."""
        try:
            with self._abrir(f"{self.base}/token?scope=repository:{self.repositorio}:pull") as r:
                token = json.loads(r.read())["token"]
            with self._abrir(f"{self.base}/v2/{self.repositorio}/manifests/{etiqueta}", metodo="HEAD",
                             cabeceras={"Authorization": f"Bearer {token}", "Accept": self.ACEPTA}) as r:
                return r.headers.get("Docker-Content-Digest")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code in (401, 403):
                raise ErrorAzure(f"{REGISTRO}/{self.repositorio} no se puede leer sin credenciales "
                                 f"(HTTP {error.code}): ¿el paquete dejó de ser público?") from error
            raise ErrorAzure(f"{REGISTRO} respondió HTTP {error.code} al buscar {etiqueta}") from error
        except (OSError, KeyError, ValueError) as error:
            raise ErrorAzure(f"no se pudo consultar {REGISTRO}: {error}") from error


def resolver(imagen: str, registro: Registro | None = None) -> str:
    """Comprueba que la imagen exista en ghcr.io. ``latest`` se fija a su digest: con una etiqueta móvil, cada arranque
    desde cero bajaría la imagen que fuera la última en ese momento, distinta de la revisión que se verificó."""
    ref = referencia(imagen)
    registro = registro or Registro()
    if "@" in ref:
        etiqueta = ref.split("@", 1)[1]
    else:
        etiqueta = ref.rsplit(":", 1)[1]
    digest = registro.digest(etiqueta)
    if digest is None:
        raise ErrorAzure(f"{ref} no está en {REGISTRO}: ¿se hizo push del commit y terminó el workflow «Imagen»? "
                         "(https://github.com/R0SEWT/tetouan-power-forecast/actions/workflows/imagen.yml)")
    return f"{IMAGEN}@{digest}" if etiqueta == "latest" else ref


def especificacion(imagen: str, minimo: int, entorno_id: str, region: str = REGION) -> dict:
    """La app completa, el cuerpo del PUT a la API de Container Apps (crea o reemplaza la app entera)."""
    return {
        "location": region,  # la del entorno: Container Apps exige que la app esté en la misma región
        "tags": dict(ETIQUETAS),
        "properties": {
            "environmentId": entorno_id,
            "workloadProfileName": PERFIL,
            "configuration": {
                "activeRevisionsMode": "Single",
                # «http» (HTTP/1.1, lo que habla uvicorn): con «auto» la API igual guarda y devuelve «Http»
                "ingress": {"external": True, "targetPort": PUERTO, "transport": "http", "allowInsecure": False,
                            "traffic": [{"latestRevision": True, "weight": 100}]},
            },
            "template": {
                "containers": [{
                    "name": APP,
                    "image": imagen,
                    "resources": {"cpu": CPU, "memory": MEMORIA},
                    "env": [{"name": k, "value": v} for k, v in VARIABLES.items()],
                    "probes": [json.loads(json.dumps(s)) for s in SONDAS],
                }],
                "scale": {
                    "minReplicas": minimo,
                    "maxReplicas": MAX_REPLICAS,
                    "cooldownPeriod": ESPERA_A_CERO,
                    "rules": [{"name": "http", "http": {"metadata": {"concurrentRequests": str(CONCURRENCIA)}}}],
                },
            },
        },
    }


CAMPOS_SONDA = ("initialDelaySeconds", "periodSeconds", "timeoutSeconds", "failureThreshold")


def _sondas(sondas) -> list[tuple]:
    filas = []
    for s in sondas or []:
        http, tcp = s.get("httpGet") or {}, s.get("tcpSocket") or {}
        destino = ("http", http.get("path"), http.get("port")) if http else ("tcp", None, tcp.get("port"))
        filas.append((s.get("type"), *destino, *(s.get(c) for c in CAMPOS_SONDA)))
    return sorted(filas, key=lambda f: str(f[0]))


def diferencias(app: dict | None, imagen: str, minimo: int) -> list[str]:
    """Lo que la app en Azure tiene distinto de lo pedido (vacío: está como se pide). Sirve para decidir si hay que
    escribir y para verificar después de escribir."""
    if app is None:
        return ["la app no existe"]
    p = app.get("properties") or {}
    conf, plantilla = p.get("configuration") or {}, p.get("template") or {}
    contenedores = plantilla.get("containers") or [{}]
    c, ingreso, escala = contenedores[0], conf.get("ingress") or {}, plantilla.get("scale") or {}
    problemas = []

    def igual(que, actual, esperado):
        if actual != esperado:
            problemas.append(f"{que} es {actual!r}, no {esperado!r}")

    for k, v in ETIQUETAS.items():
        igual(f"la etiqueta {k}", (app.get("tags") or {}).get(k), v)
    igual("el perfil de carga", p.get("workloadProfileName"), PERFIL)
    igual("el modo de revisiones", conf.get("activeRevisionsMode"), "Single")
    igual("el ingreso externo", ingreso.get("external"), True)
    igual("el puerto del ingreso", ingreso.get("targetPort"), PUERTO)
    igual("el transporte", str(ingreso.get("transport")).lower(), "http")
    igual("allowInsecure (HTTP sin TLS)", ingreso.get("allowInsecure"), False)
    igual("la cantidad de contenedores", len(contenedores), 1)
    igual("la imagen", c.get("image"), imagen)
    recursos = c.get("resources") or {}
    igual("la CPU", float(recursos.get("cpu") or 0), CPU)
    igual("la memoria", recursos.get("memory"), MEMORIA)
    igual("las variables", {e.get("name"): e.get("value") for e in c.get("env") or []}, VARIABLES)
    igual("las sondas", _sondas(c.get("probes")), _sondas(SONDAS))
    igual("el mínimo de réplicas", escala.get("minReplicas"), minimo)
    igual("el máximo de réplicas", escala.get("maxReplicas"), MAX_REPLICAS)
    igual("la espera antes de bajar a cero", escala.get("cooldownPeriod") or ESPERA_POR_DEFECTO, ESPERA_A_CERO)
    reglas = [(r.get("name"), ((r.get("http") or {}).get("metadata") or {}).get("concurrentRequests"))
              for r in escala.get("rules") or []]
    igual("las reglas de escala", reglas, [("http", str(CONCURRENCIA))])
    igual("los registros con credenciales", conf.get("registries") or [], [])  # la imagen es pública
    igual("los secretos", conf.get("secrets") or [], [])
    return problemas


def problemas_entorno(entorno: dict) -> list[str]:
    """Lo que el entorno tiene distinto de lo pedido: el modo, sin Log Analytics, solo el perfil Consumption, etiquetas."""
    p, problemas = entorno.get("properties") or {}, []
    if (p.get("environmentMode") or "").lower() != MODO.lower():
        problemas.append(f"el entorno está en modo {p.get('environmentMode')!r}, no {MODO!r}")
    logs = p.get("appLogsConfiguration") or {}
    if logs.get("destination") not in (None, "", "none") or logs.get("logAnalyticsConfiguration"):
        problemas.append(f"el entorno guarda logs ({logs.get('destination')}): eso cobra aparte")
    perfiles = sorted(w.get("workloadProfileType") or "" for w in p.get("workloadProfiles") or [])
    if perfiles != [PERFIL]:
        problemas.append(f"el entorno tiene los perfiles {perfiles}: uno dedicado cobra una tarifa fija por hora")
    for k, v in ETIQUETAS.items():
        if (entorno.get("tags") or {}).get(k) != v:
            problemas.append(f"la etiqueta {k}={v} no está en el entorno")
    return problemas


def costo_mes(vcpu_s: float, gib_s: float, pedidos: float, vcpu_reposo_s: float = 0) -> float:
    """USD de un mes con esos consumos, descontando lo gratis (se descuenta primero de lo activo)."""
    activo = max(0.0, vcpu_s - GRATIS_VCPU_S)
    reposo = max(0.0, vcpu_reposo_s - max(0.0, GRATIS_VCPU_S - vcpu_s))
    return (activo * VCPU_ACTIVO + reposo * VCPU_REPOSO + max(0.0, gib_s - GRATIS_GIB_S) * GIB
            + max(0.0, pedidos - GRATIS_PEDIDOS) / 1e6 * MILLON_PEDIDOS)


class Publicador:
    def __init__(self, args, az: Azure, registro: Registro | None = None):
        self.args, self.az, self.registro = args, az, registro or Registro()
        self.base = ["--resource-group", args.grupo]

    # --- lectura ---
    def app(self) -> dict | None:
        return None if self.az.simular else self.az("containerapp", "show", "--name", self.args.app, *self.base,
                                                    puede_faltar=True)

    def url(self, app: dict | None) -> str:
        fqdn = (((app or {}).get("properties") or {}).get("configuration") or {}).get("ingress") or {}
        return f"https://{fqdn['fqdn']}" if fqdn.get("fqdn") else ""

    # --- creación ---
    def etiquetas(self) -> list[str]:
        return ["--tags", *[f"{k}={v}" for k, v in ETIQUETAS.items()]]

    def crear_base(self) -> str:
        """El grupo y el entorno, si faltan. Devuelve el id del entorno."""
        a, az = self.args, self.az
        if a.grupo.lower() in PROTEGIDOS:
            raise ErrorAzure(f"{a.grupo} es de otro despliegue: este script no lo usa")
        grupo = None if az.simular else az("group", "show", "--name", a.grupo, puede_faltar=True)
        if grupo is None:
            az.mostrar(f"Grupo de recursos {a.grupo} en {a.region}:")
            az("group", "create", "--name", a.grupo, "--location", a.region, *self.etiquetas())
        elif any((grupo.get("tags") or {}).get(k) != v for k, v in ETIQUETAS.items()):
            raise ErrorAzure(f"el grupo {a.grupo} existe pero no tiene las etiquetas {ETIQUETAS}: no es de este "
                             "despliegue")
        entorno = None if az.simular else az("containerapp", "env", "show", "--name", a.entorno, *self.base,
                                             puede_faltar=True)
        if entorno is None:
            az.mostrar(f"Entorno {a.entorno} (perfil Consumption, sin Log Analytics):")
            entorno = az("containerapp", "env", "create", "--name", a.entorno, *self.base, "--location", a.region,
                         "--environment-mode", MODO, "--logs-destination", "none", *self.etiquetas(), timeout=1800)
            if not az.simular:
                entorno = az("containerapp", "env", "show", "--name", a.entorno, *self.base)
        if az.simular:
            self.region_entorno = a.region
            return (f"/subscriptions/SUSCRIPCION/resourceGroups/{a.grupo}/providers/Microsoft.App/"
                    f"managedEnvironments/{a.entorno}")
        # La app va en la región del entorno (si ya existía en otra, manda la suya: «Brazil South» -> brazilsouth)
        self.region_entorno = (entorno.get("location") or a.region).lower().replace(" ", "")
        problemas = problemas_entorno(entorno)
        if problemas:
            raise ErrorAzure("el entorno no quedó como se pide:\n  - " + "\n  - ".join(problemas))
        return entorno["id"]

    def elegir(self, app: dict | None) -> tuple[str, int]:
        """La imagen y el mínimo de réplicas: lo pedido; si no, lo que ya tiene la app; si no existe, el commit y 0."""
        a = self.args
        plantilla = ((app or {}).get("properties") or {}).get("template") or {}
        if a.imagen:
            imagen = referencia(a.imagen) if self.az.simular else resolver(a.imagen, self.registro)
        elif app is not None:
            imagen = (plantilla.get("containers") or [{}])[0].get("image", "")
        else:
            etiqueta = etiqueta_del_commit()
            imagen = referencia(etiqueta) if self.az.simular else resolver(etiqueta, self.registro)
        if a.minimo is not None:
            minimo = a.minimo
        else:
            minimo = (plantilla.get("scale") or {}).get("minReplicas") or 0 if app is not None else 0
        return imagen, minimo

    def aplicar(self, app: dict | None, imagen: str, minimo: int, entorno_id: str) -> bool:
        """Escribe la especificación (PUT) si Azure tiene algo distinto y espera a que quede aplicada. Devuelve si
        escribió."""
        a, az = self.args, self.az
        pendientes = diferencias(app, imagen, minimo) if not az.simular else ["--dry-run"]
        if not pendientes:
            az.mostrar("La app ya está como se pide: no se escribe nada.")
            return False
        if app is not None:
            az.mostrar("Cambios:\n  - " + "\n  - ".join(pendientes))
        spec = especificacion(imagen, minimo, entorno_id, getattr(self, "region_entorno", self.args.region))
        # Un PUT reemplaza todo: los dominios propios que tenga la app (los vincula «az containerapp hostname bind»,
        # fuera de este script) se conservan
        ingreso_actual = (((app or {}).get("properties") or {}).get("configuration") or {}).get("ingress") or {}
        if ingreso_actual.get("customDomains"):
            spec["properties"]["configuration"]["ingress"]["customDomains"] = ingreso_actual["customDomains"]
        texto = ascii_o_error(json.dumps(spec, indent=2), "la especificación")
        # El id de la app sale del id del entorno: /subscriptions/<id>/resourceGroups/<grupo>/...
        suscripcion_id = entorno_id.split("/")[2]
        url = (f"https://management.azure.com/subscriptions/{suscripcion_id}/resourceGroups/{a.grupo}/providers/"
               f"Microsoft.App/containerApps/{a.app}?api-version={API}")
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = Path(carpeta) / "curva-aca.json"
            archivo.write_text(texto)
            az.mostrar(f"App {a.app} ({'crear' if app is None else 'actualizar'}; imagen {imagen}, mínimo {minimo}):")
            if az.simular:
                az.mostrar("    " + texto.replace("\n", "\n    "))
            az("rest", "--method", "put", "--url", url, "--body", f"@{archivo}", "--headers",
               "Content-Type=application/json", timeout=300)
        self.esperar_aplicada()
        return True

    def esperar_aplicada(self, segundos: float = 900) -> None:
        """El PUT vuelve enseguida y Azure sigue aplicando: espera a que la app quede «Succeeded»."""
        if self.az.simular:
            return
        limite, estado = time.monotonic() + segundos, None
        while time.monotonic() < limite:
            estado = ((self.app() or {}).get("properties") or {}).get("provisioningState")
            if estado == "Succeeded":
                return
            if estado in ("Failed", "Canceled"):
                raise ErrorAzure(f"Azure no pudo aplicar la app (estado {estado}): revisa --estado y, en el portal, "
                                 "la app -> Revisions")
            time.sleep(5)
        raise ErrorAzure(f"la app sigue en «{estado}» después de {segundos:.0f} s")

    def verificar(self, imagen: str, minimo: int) -> dict | None:
        """Lee de vuelta la app y falla si algo no quedó como se pidió."""
        if self.az.simular:
            return None
        app = self.app()
        problemas = diferencias(app, imagen, minimo)
        if problemas:
            raise ErrorAzure("la app no quedó como se pidió:\n  - " + "\n  - ".join(problemas))
        self.az.mostrar("Configuración verificada (leída de vuelta de Azure).")
        return app

    # --- operación ---
    def probar(self, url: str, imagen: str) -> None:
        if self.az.simular or self.args.no_esperar or not url:
            return
        self.az.mostrar(f"Prueba de humo en {url} (prende la app desde cero; espera hasta {self.args.espera:.0f} min):")
        if humo.main([url, "--esperar", str(self.args.espera * 60)]) != 0:
            raise ErrorAzure("la prueba de humo falló: revisa los logs (python despliegue/publicar_aca.py --logs)")
        # Que haya respondido la revisión nueva: la activa, con todo el tráfico, sana y con la imagen pedida
        revisiones = self.az("containerapp", "revision", "list", "--name", self.args.app, *self.base) or []
        activa = [r for r in revisiones if (r.get("properties") or {}).get("trafficWeight")]
        rp = (activa[0].get("properties") or {}) if len(activa) == 1 else {}
        imagen_activa = ((rp.get("template") or {}).get("containers") or [{}])[0].get("image")
        if imagen_activa != imagen or rp.get("healthState") != "Healthy":
            raise ErrorAzure(f"la revisión con tráfico no es la nueva (imagen {imagen_activa}, salud "
                             f"{rp.get('healthState')}): revisa --estado y --logs")
        self.az.mostrar(f"Listo: {url} (revisión {activa[0].get('name')}, {imagen})")

    def estado(self) -> None:
        a, az = self.args, self.az
        app = az("containerapp", "show", "--name", a.app, *self.base)
        revisiones = az("containerapp", "revision", "list", "--name", a.app, *self.base)
        replicas = az("containerapp", "replica", "list", "--name", a.app, *self.base)
        if az.simular:
            return
        p = app.get("properties") or {}
        plantilla = p.get("template") or {}
        escala = plantilla.get("scale") or {}
        az.mostrar(f"URL: {self.url(app)} ({p.get('runningStatus')})")
        az.mostrar(f"Imagen: {(plantilla.get('containers') or [{}])[0].get('image')}")
        az.mostrar(f"Réplicas: de {escala.get('minReplicas')} a {escala.get('maxReplicas')}; prendidas ahora: "
                   f"{len(replicas or [])}")
        for r in replicas or []:
            for c in (r.get("properties") or {}).get("containers") or []:
                az.mostrar(f"  {r.get('name')}: {c.get('runningState')}, lista {c.get('ready')}, reinicios "
                           f"{c.get('restartCount')} ({c.get('runningStateDetails')})")
        for r in revisiones or []:
            rp = r.get("properties") or {}
            if rp.get("active"):
                az.mostrar(f"Revisión {r.get('name')}: {rp.get('runningState')}, salud {rp.get('healthState')}, "
                           f"{rp.get('replicas')} réplica(s), creada {rp.get('createdTime')}")

    def logs(self, lineas: int) -> None:
        """Las últimas líneas del contenedor, leídas en vivo de la réplica prendida (el entorno no guarda logs)."""
        a, az = self.args, self.az
        if not az.simular and not az("containerapp", "replica", "list", "--name", a.app, *self.base):
            az.mostrar("La app está en cero réplicas: no hay logs que leer (el entorno no los guarda, ver README). "
                       "Ábrela en el navegador y vuelve a pedirlos; --estado muestra los reinicios.")
            return
        salida = az("containerapp", "logs", "show", "--name", a.app, *self.base, "--type", "console", "--tail",
                    str(min(lineas, 300)), "--format", "text", texto=True, timeout=120)
        if salida is not None:
            az.mostrar(salida.rstrip() or "Sin líneas.")

    def metricas(self, horas: float) -> None:
        """Réplicas, pedidos, memoria y CPU del periodo, y el costo de un mes con ese mismo uso."""
        a, az = self.args, self.az
        app = az("containerapp", "show", "--name", a.app, *self.base)
        fin = datetime.now(UTC).replace(second=0, microsecond=0)
        inicio = fin - timedelta(hours=horas)
        series = {}
        for metrica, agregado in (("Replicas", "Maximum"), ("Requests", "Total"), ("WorkingSetBytes", "Maximum"),
                                  ("UsageNanoCores", "Maximum"), ("RestartCount", "Maximum")):
            r = az("monitor", "metrics", "list", "--resource", (app or {}).get("id", "ID_DE_LA_APP"), "--metric",
                   metrica, "--aggregation", agregado, "--interval", "PT1M", "--start-time",
                   inicio.isoformat(timespec="minutes").replace("+00:00", "Z"), "--end-time",
                   fin.isoformat(timespec="minutes").replace("+00:00", "Z"))
            if r is None:
                continue
            puntos = [d for v in r.get("value") or [] for t in v.get("timeseries") or [] for d in t.get("data") or []]
            series[metrica] = [d.get(agregado.lower()) or 0 for d in puntos]
        if az.simular:
            return
        replica_s = sum(series.get("Replicas", [])) * 60
        pedidos = sum(series.get("Requests", []))
        memoria = max(series.get("WorkingSetBytes", [0]) or [0]) / 2**30
        cpu = max(series.get("UsageNanoCores", [0]) or [0]) / 1e9
        reinicios = max(series.get("RestartCount", [0]) or [0])
        factor = SEGUNDOS_MES / (horas * 3600)
        vcpu_s, gib_s = replica_s * CPU, replica_s * float(MEMORIA.removesuffix("Gi"))
        az.mostrar(f"Últimas {horas:g} h: {replica_s / 60:.0f} min con una réplica prendida, {pedidos:.0f} pedidos, "
                   f"memoria máxima {memoria:.2f} GiB de {MEMORIA}, CPU máxima {cpu:.2f} de {CPU:g} vCPU, "
                   f"reinicios {reinicios:.0f}.")
        az.mostrar(f"Consumo: {vcpu_s:.0f} vCPU-s y {gib_s:.0f} GiB-s. Un mes con este mismo uso: "
                   f"{vcpu_s * factor:.0f} vCPU-s, {gib_s * factor:.0f} GiB-s, {pedidos * factor:.0f} pedidos "
                   f"-> {costo_mes(vcpu_s * factor, gib_s * factor, pedidos * factor):.2f} USD (descontado lo gratis).")

    def _parar_o_prender(self, accion: str, estado: str) -> None:
        """POST a ``/stop`` o ``/start`` de la API (el CLI de esta versión no trae esos comandos) y espera el estado."""
        a, az = self.args, self.az
        app_id = ((None if az.simular else self.app()) or {}).get("id") or (
            f"/subscriptions/SUSCRIPCION/resourceGroups/{a.grupo}/providers/Microsoft.App/containerApps/{a.app}")
        az("rest", "--method", "post", "--url", f"https://management.azure.com{app_id}/{accion}?api-version={API}",
           timeout=300)
        if az.simular:
            return
        limite = time.monotonic() + 600
        while time.monotonic() < limite:
            actual = ((self.app() or {}).get("properties") or {}).get("runningStatus")
            if actual == estado:
                return
            time.sleep(5)
        raise ErrorAzure(f"la app no quedó «{estado}» en 10 min (está «{actual}»)")

    def apagar(self) -> None:
        """Detiene la app: nadie la puede despertar hasta ``--prender``. La configuración queda intacta."""
        self.az.mostrar(f"Se detiene {self.args.app}: la URL deja de responder hasta --prender.")
        self._parar_o_prender("stop", "Stopped")
        self.az.mostrar("Detenida. Para prenderla: python despliegue/publicar_aca.py --prender")

    def prender(self) -> None:
        """Vuelve a prender una app detenida con ``--apagar`` (sigue escalando a cero sola)."""
        self.az.mostrar(f"Se prende {self.args.app}:")
        self._parar_o_prender("start", "Running")
        self.probar(self.url(self.app()), self.imagen_actual())

    def imagen_actual(self) -> str:
        plantilla = ((self.app() or {}).get("properties") or {}).get("template") or {}
        return (plantilla.get("containers") or [{}])[0].get("image", "")

    def borrar(self) -> None:
        a, az = self.args, self.az
        if a.grupo.lower() in PROTEGIDOS:
            raise ErrorAzure(f"{a.grupo} no se borra con este script")
        if not az.simular:
            grupo = az("group", "show", "--name", a.grupo, puede_faltar=True)
            if grupo is None:
                az.mostrar(f"El grupo {a.grupo} no existe: no hay nada que borrar.")
                return
            if any((grupo.get("tags") or {}).get(k) != v for k, v in ETIQUETAS.items()):
                raise ErrorAzure(f"el grupo {a.grupo} no tiene las etiquetas {ETIQUETAS}: no se borra")
            ajenos = [r["type"] for r in az("resource", "list", *self.base) or []
                      if not r["type"].lower().startswith("microsoft.app/")]
            if ajenos:
                raise ErrorAzure(f"el grupo {a.grupo} tiene recursos que no son de Container Apps ({ajenos}): "
                                 "no se borra")
            if not a.si and input(f"Se borra {a.grupo} con todo lo que tiene (no se puede deshacer). Escribe su "
                                  "nombre para seguir: ").strip() != a.grupo:
                az.mostrar("No se borró nada.")
                return
        az.mostrar(f"Borrando {a.grupo} (unos minutos):")
        az("group", "delete", "--name", a.grupo, "--yes", timeout=1800)
        if not az.simular:
            az.mostrar(f"Borrado {a.grupo}.")

    def publicar(self) -> None:
        a = self.args
        revisar_cuenta(self.az)
        if a.estado:
            return self.estado()
        if a.logs:
            return self.logs(a.logs)
        if a.metricas:
            return self.metricas(a.metricas)
        if a.apagar:
            return self.apagar()
        if a.prender:
            return self.prender()
        if a.borrar:
            return self.borrar()
        entorno_id = self.crear_base()
        app = self.app()
        imagen, minimo = self.elegir(app)
        escribio = self.aplicar(app, imagen, minimo, entorno_id)
        app = self.verificar(imagen, minimo)
        if escribio or a.probar:
            self.probar(self.url(app), imagen)
        elif app is not None:
            self.az.mostrar(f"URL: {self.url(app)}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Publica Curva en Azure Container Apps (Consumption, imagen de ghcr.io).")
    p.add_argument("--app", default=APP, help=f"nombre de la app (por defecto, {APP})")
    p.add_argument("--grupo", default=GRUPO, help=f"grupo de recursos (por defecto, {GRUPO})")
    p.add_argument("--entorno", default=ENTORNO, help=f"entorno de Container Apps (por defecto, {ENTORNO})")
    p.add_argument("--region", default=REGION, help=f"región al crear (por defecto, {REGION})")
    p.add_argument("--imagen", help=f"etiqueta (sha-abc1234, latest) o referencia de {IMAGEN}; si no se da, la que ya "
                                    "tiene la app o, al crearla, la del commit actual")
    p.add_argument("--minimo", type=int, choices=(0, 1),
                   help="réplicas siempre prendidas (0: se apaga sola; 1: nunca se apaga y cobra todo el tiempo); si "
                        "no se da, se conserva el que tiene la app")
    p.add_argument("--estado", action="store_true", help="muestra URL, imagen, revisión y réplicas, y termina")
    p.add_argument("--logs", type=int, nargs="?", const=60, default=0, metavar="LINEAS",
                   help="las últimas líneas del contenedor (60; hasta 300) si hay una réplica prendida")
    p.add_argument("--metricas", type=float, nargs="?", const=24, default=0, metavar="HORAS",
                   help="réplicas, pedidos, memoria y costo de las últimas HORAS (24)")
    p.add_argument("--apagar", action="store_true", help="detiene la app (nadie la puede despertar hasta --prender)")
    p.add_argument("--prender", action="store_true", help="vuelve a prender la app detenida y corre la prueba de humo")
    p.add_argument("--borrar", action="store_true", help="borra el grupo de recursos entero (pide escribir su nombre)")
    p.add_argument("--si", action="store_true", help="con --borrar, no pide confirmación")
    p.add_argument("--probar", action="store_true", help="corre la prueba de humo aunque no haya cambios")
    p.add_argument("--espera", type=float, default=15, help="minutos máximos de espera a /salud (15)")
    p.add_argument("--no-esperar", action="store_true", help="no espera a /salud ni corre la prueba de humo")
    p.add_argument("--dry-run", action="store_true", help="muestra los comandos de az, sin tocar Azure")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    az = Azure(simular=args.dry_run)
    if args.dry_run:
        print(f"Simulación (--dry-run): no se llama a az. Destino: {args.app} en {args.entorno} ({args.grupo}, "
              f"{args.region}), suscripción «{SUSCRIPCION}».")
    try:
        Publicador(args, az).publicar()
    except (ErrorAzure, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
