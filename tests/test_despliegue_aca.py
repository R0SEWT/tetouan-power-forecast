"""El despliegue en Azure Container Apps: la especificación de la app, su verificación y los comandos de az, sin red."""

import copy
import itertools
import json
from types import SimpleNamespace

import pytest

from despliegue import publicar_aca
from despliegue.publicar_aca import ErrorAzure

ENTORNO_ID = "/subscriptions/x/resourceGroups/curva-aca-rg/providers/Microsoft.App/managedEnvironments/curva-aca-env"
IMAGEN = "ghcr.io/r0sewt/curva:sha-1234567"


def como_azure(spec: dict) -> dict:
    """Lo que devolvería ``az containerapp show`` después de aplicar ``spec``: lo mismo más lo que agrega Azure."""
    app = copy.deepcopy(spec)
    app["id"] = "/subscriptions/x/resourceGroups/curva-aca-rg/providers/Microsoft.App/containerApps/curva"
    p = app["properties"]
    p["configuration"]["ingress"].update(fqdn="curva.algo.brazilsouth.azurecontainerapps.io", transport="Http",
                                         traffic=None, exposedPort=None, clientCertificateMode=None)
    p["configuration"].update(registries=None, secrets=None, maxInactiveRevisions=100)
    for sonda in p["template"]["containers"][0]["probes"]:
        sonda["successThreshold"] = 1
        if "httpGet" in sonda:
            sonda["httpGet"]["scheme"] = "HTTP"
    p["template"]["containers"][0]["resources"]["ephemeralStorage"] = "4Gi"
    p["template"]["scale"].update(cooldownPeriod=None, pollingInterval=None)  # la API devuelve vacíos los por defecto
    p.update(latestRevisionName="curva--abc", latestReadyRevisionName="curva--abc", provisioningState="Succeeded")
    return app


def test_todo_lo_que_va_a_azure_es_ascii():
    texto = json.dumps(publicar_aca.especificacion(IMAGEN, 0, ENTORNO_ID))
    assert texto.isascii()
    assert all(t.isascii() for t in [*publicar_aca.VARIABLES, *publicar_aca.VARIABLES.values(),
                                      *publicar_aca.ETIQUETAS.values()])
    with pytest.raises(ErrorAzure):
        publicar_aca.referencia("sha-año")


def test_la_especificacion_pide_lo_acordado():
    spec = publicar_aca.especificacion(IMAGEN, 0, ENTORNO_ID)
    p = spec["properties"]
    c = p["template"]["containers"][0]
    assert spec["location"] == "brazilsouth" and spec["tags"] == {"proyecto": "curva", "curso": "upc-mds"}
    assert p["workloadProfileName"] == "Consumption"
    assert c["resources"] == {"cpu": 1.0, "memory": "2Gi"}
    assert p["template"]["scale"]["minReplicas"] == 0 and p["template"]["scale"]["maxReplicas"] == 1
    assert p["template"]["scale"]["rules"][0]["http"]
    ingreso = p["configuration"]["ingress"]
    assert ingreso["external"] is True and ingreso["targetPort"] == 7860 and ingreso["allowInsecure"] is False
    variables = {e["name"]: e["value"] for e in c["env"]}
    assert variables["TPF_HF_DATASET"] == "rosewt/curva-datos" and variables["TPF_PRONOSTICADOR"] == "real"
    assert variables["PORT"] == "7860" and "HF_TOKEN" not in variables  # el dataset es público
    assert "registries" not in p["configuration"] and "secrets" not in p["configuration"]  # la imagen es pública
    assert variables["TPF_CALENTAR"] == "0"  # el puerto abre antes de los ~30 s en que la plataforma da 503
    # La sonda de arranque es la que Container Apps pone por defecto: TCP cada 1 s, hasta 240 fallas (4 min)
    arranque = next(s for s in c["probes"] if s["type"] == "Startup")
    assert arranque["tcpSocket"]["port"] == 7860 and arranque["periodSeconds"] == 1
    assert arranque["periodSeconds"] * arranque["failureThreshold"] >= 4 * 60
    # las otras dos son TCP (no /salud): con la CPU ocupada en un cálculo largo, el puerto igual acepta conexiones
    for sonda in c["probes"]:
        assert "tcpSocket" in sonda and sonda["initialDelaySeconds"] <= 60 and sonda["periodSeconds"] <= 240


def test_lo_aplicado_pasa_la_verificacion_y_lo_distinto_no():
    spec = publicar_aca.especificacion(IMAGEN, 0, ENTORNO_ID)
    app = como_azure(spec)
    assert publicar_aca.diferencias(app, IMAGEN, 0) == []
    assert publicar_aca.diferencias(None, IMAGEN, 0) == ["la app no existe"]
    assert len(publicar_aca.diferencias(app, "ghcr.io/r0sewt/curva:sha-7654321", 1)) == 2
    otra = copy.deepcopy(app)
    c = otra["properties"]["template"]["containers"][0]
    c["probes"][0]["periodSeconds"] = 5
    c["env"].append({"name": "HF_TOKEN", "secretRef": "hf"})
    otra["properties"]["configuration"]["ingress"]["allowInsecure"] = True
    otra["properties"]["template"]["scale"]["maxReplicas"] = 3
    otra["tags"] = {"proyecto": "curva"}
    problemas = publicar_aca.diferencias(otra, IMAGEN, 0)
    assert len(problemas) == 5
    for palabra in ("sondas", "variables", "allowInsecure", "máximo", "curso"):
        assert any(palabra in p for p in problemas), palabra


def test_referencia_solo_acepta_la_imagen_de_curva():
    assert publicar_aca.referencia("sha-1234567") == IMAGEN
    assert publicar_aca.referencia("sha256:ab") == "ghcr.io/r0sewt/curva@sha256:ab"
    assert publicar_aca.referencia("ghcr.io/r0sewt/curva:latest") == "ghcr.io/r0sewt/curva:latest"
    for ajena in ("docker.io/library/nginx:latest", "ghcr.io/r0sewt/curva-otra:sha-1", "ghcr.io/otro/curva:x"):
        with pytest.raises(ErrorAzure):
            publicar_aca.referencia(ajena)


class RegistroFalso:
    def __init__(self, etiquetas):
        self.etiquetas, self.pedidas = etiquetas, []

    def digest(self, etiqueta):
        self.pedidas.append(etiqueta)
        return self.etiquetas.get(etiqueta)


def test_resolver_comprueba_la_etiqueta_y_fija_latest_a_su_digest():
    registro = RegistroFalso({"sha-1234567": "sha256:aaa", "latest": "sha256:bbb"})
    assert publicar_aca.resolver("sha-1234567", registro) == IMAGEN
    assert publicar_aca.resolver("latest", registro) == "ghcr.io/r0sewt/curva@sha256:bbb"
    with pytest.raises(ErrorAzure, match="workflow"):
        publicar_aca.resolver("sha-0000000", registro)


def test_el_entorno_no_guarda_logs_ni_tiene_perfiles_dedicados():
    bien = {"tags": dict(publicar_aca.ETIQUETAS),
            "properties": {"appLogsConfiguration": {"destination": None, "logAnalyticsConfiguration": None},
                           "workloadProfiles": [{"name": "Consumption", "workloadProfileType": "Consumption"}]}}
    assert publicar_aca.problemas_entorno(bien) == []
    mal = copy.deepcopy(bien)
    mal["properties"]["appLogsConfiguration"] = {"destination": "log-analytics",
                                                 "logAnalyticsConfiguration": {"customerId": "x"}}
    mal["properties"]["workloadProfiles"].append({"name": "D4", "workloadProfileType": "D4"})
    assert len(publicar_aca.problemas_entorno(mal)) == 2


def test_costo_descuenta_lo_gratis():
    assert publicar_aca.costo_mes(180_000, 360_000, 2_000_000) == 0
    # prendida todo el mes y siempre activa: (2 628 000 - 180 000) vCPU-s y (5 256 000 - 360 000) GiB-s
    siempre = publicar_aca.costo_mes(730 * 3600, 2 * 730 * 3600, 0)
    assert siempre == pytest.approx(2_448_000 * 0.000024 + 4_896_000 * 0.000003)
    # en reposo se cobra la CPU a la tarifa reducida; lo gratis se descuenta primero de lo activo
    reposo = publicar_aca.costo_mes(0, 2 * 730 * 3600, 0, vcpu_reposo_s=730 * 3600)
    assert reposo == pytest.approx(2_448_000 * 0.000003 + 4_896_000 * 0.000003)


class AzFalso:
    """Responde como Azure con la app ya creada como se pide; ``app`` la reemplaza (``None``: no existe)."""

    simular = False

    def __init__(self, app="igual", replicas=1, grupo_tags=None, recursos=None, aplica=False):
        spec = publicar_aca.especificacion(IMAGEN, 0, ENTORNO_ID)
        self.app = como_azure(spec) if app == "igual" else app
        self.aplica, self.escritos = aplica, []
        self.replicas = replicas
        self.grupo_tags = dict(publicar_aca.ETIQUETAS) if grupo_tags is None else grupo_tags
        self.recursos = recursos or [{"type": "Microsoft.App/managedEnvironments"},
                                     {"type": "Microsoft.App/containerApps"}]
        self.mensajes, self.escrituras = [], []

    def mostrar(self, texto):
        self.mensajes.append(texto)

    def __call__(self, *args, puede_faltar=False, timeout=None, texto=False):
        palabras = list(itertools.takewhile(lambda a: not a.startswith("--"), args))
        clave = " ".join(palabras)
        if palabras[-1] not in ("show", "list"):
            self.escrituras.append(args)
            if self.aplica and palabras == ["rest"] and "put" in args:
                with open(args[args.index("--body") + 1].removeprefix("@")) as archivo:
                    self.escritos.append(json.load(archivo))
                self.app = como_azure(self.escritos[-1])  # Azure aplica lo pedido
            return "línea de log\n" if texto else None
        respuestas = {
            "account show": {"name": "Azure for Students", "state": "Enabled", "user": {"name": "u1@upc.edu.pe"}},
            "group show": {"name": "curva-aca-rg", "tags": self.grupo_tags},
            "containerapp env show": {"id": ENTORNO_ID, "tags": dict(publicar_aca.ETIQUETAS), "properties": {
                "appLogsConfiguration": {"destination": None},
                "workloadProfiles": [{"name": "Consumption", "workloadProfileType": "Consumption"}]}},
            "containerapp show": self.app,
            "containerapp replica list": [{"name": f"r{i}"} for i in range(self.replicas)],
            "resource list": self.recursos,
            "containerapp logs show": "línea de log\n",
        }
        return respuestas.get(clave)


def args(**cambios):
    valores = {"app": "curva", "grupo": "curva-aca-rg", "entorno": "curva-aca-env", "region": "brazilsouth",
               "imagen": None, "minimo": None, "estado": False, "logs": 0, "metricas": 0,
               "apagar": False, "borrar": False, "si": False, "probar": False, "espera": 1, "no_esperar": True,
               "dry_run": False}
    return SimpleNamespace(**{**valores, **cambios})


def test_sin_cambios_no_escribe_nada_y_conserva_imagen_y_minimo():
    az = AzFalso()
    publicar_aca.Publicador(args(), az, RegistroFalso({})).publicar()
    assert az.escrituras == []
    assert any("no se escribe nada" in m for m in az.mensajes)


def test_otra_imagen_actualiza_con_yaml_y_verifica():
    az = AzFalso(aplica=True)
    nueva = "ghcr.io/r0sewt/curva:sha-7654321"
    publicar_aca.Publicador(args(imagen="sha-7654321"), az, RegistroFalso({"sha-7654321": "sha256:c"})).publicar()
    assert [e[:3] for e in az.escrituras] == [("rest", "--method", "put")]
    assert az.escritos[0]["properties"]["template"]["containers"][0]["image"] == nueva
    assert az.escritos[0]["properties"]["template"]["scale"]["minReplicas"] == 0  # el mínimo se conserva


def test_crea_la_app_con_la_imagen_del_commit(monkeypatch):
    monkeypatch.setattr(publicar_aca, "etiqueta_del_commit", lambda raiz=None: "sha-1234567")
    az = AzFalso(app=None, aplica=True)
    registro = RegistroFalso({"sha-1234567": "sha256:a"})
    publicar_aca.Publicador(args(), az, registro).publicar()
    assert registro.pedidas == ["sha-1234567"]  # comprobó que la imagen existe antes de crear
    assert [e[:3] for e in az.escrituras] == [("rest", "--method", "put")]
    assert az.escritos[0]["properties"]["template"]["scale"]["minReplicas"] == 0


def test_si_azure_no_aplica_lo_pedido_falla():
    az = AzFalso()  # el update no cambia nada: la verificación lo nota
    with pytest.raises(ErrorAzure, match="no quedó"):
        publicar_aca.Publicador(args(minimo=1), az, RegistroFalso({})).publicar()


def test_logs_con_la_app_en_cero_no_pide_el_stream():
    az = AzFalso(replicas=0)
    publicar_aca.Publicador(args(logs=20), az, RegistroFalso({})).publicar()
    assert az.escrituras == [] and any("cero réplicas" in m for m in az.mensajes)
    az = AzFalso(replicas=1)
    publicar_aca.Publicador(args(logs=20), az, RegistroFalso({})).publicar()
    assert any("línea de log" in m for m in az.mensajes)


def test_borrar_se_niega_con_grupos_ajenos():
    for grupo in ("curva-rg", "aire-distribuido-rg"):
        with pytest.raises(ErrorAzure):
            publicar_aca.Publicador(args(borrar=True, si=True, grupo=grupo), AzFalso(), RegistroFalso({})).publicar()
    with pytest.raises(ErrorAzure, match="etiquetas"):
        publicar_aca.Publicador(args(borrar=True, si=True), AzFalso(grupo_tags={}), RegistroFalso({})).publicar()
    ajeno = AzFalso(recursos=[{"type": "Microsoft.Web/sites"}])
    with pytest.raises(ErrorAzure, match="no son de Container Apps"):
        publicar_aca.Publicador(args(borrar=True, si=True), ajeno, RegistroFalso({})).publicar()
    az = AzFalso()
    publicar_aca.Publicador(args(borrar=True, si=True), az, RegistroFalso({})).publicar()
    assert az.escrituras == [("group", "delete", "--name", "curva-aca-rg", "--yes")]


def test_borrar_pide_escribir_el_nombre(monkeypatch):
    az = AzFalso()
    monkeypatch.setattr("builtins.input", lambda _: "curva")
    publicar_aca.Publicador(args(borrar=True), az, RegistroFalso({})).publicar()
    assert az.escrituras == []


def test_dry_run_no_llama_a_az_ni_a_la_red(monkeypatch, capsys):
    def prohibido(*a, **k):
        raise AssertionError(f"no debía correr {a}")

    monkeypatch.setattr(publicar_aca.subprocess, "run", prohibido)
    monkeypatch.setattr(publicar_aca.Registro, "digest", prohibido)
    assert publicar_aca.main(["--dry-run", "--imagen", "sha-1234567"]) == 0
    salida = capsys.readouterr().out
    lineas_az = [linea for linea in salida.splitlines() if linea.strip().startswith("az ")]
    assert lineas_az and all("--subscription 'Azure for Students'" in linea for linea in lineas_az)
    for esperado in ("group create --name curva-aca-rg --location brazilsouth", "--logs-destination none",
                     "--enable-workload-profiles true", "proyecto=curva", "curso=upc-mds",
                     ("rest --method put --url https://management.azure.com/subscriptions/SUSCRIPCION/"
                      "resourceGroups/curva-aca-rg/providers/Microsoft.App/containerApps/curva?api-version=2025-07-01"),
                     '"image": "ghcr.io/r0sewt/curva:sha-1234567"', '"minReplicas": 0', '"maxReplicas": 1',
                     '"memory": "2Gi"', '"targetPort": 7860'):
        assert esperado in salida, esperado
    assert "account set" not in salida  # nunca cambia la suscripción por defecto del CLI
    for opcion in ("--estado", "--logs", "--metricas", "--apagar", "--borrar"):
        assert publicar_aca.main(["--dry-run", opcion]) == 0, opcion
    salida = capsys.readouterr().out
    assert "containerapp ingress disable" in salida and "group delete --name curva-aca-rg --yes" in salida
    assert "containerapp logs show" in salida and "monitor metrics list" in salida
