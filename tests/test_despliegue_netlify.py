"""La web en Netlify: las reglas de proxy cubren toda la API y la web espera al servidor dormido en vez de fallar."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.backend.main import crear_app
from app.backend.pronosticador import PronosticadorDePrueba

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "despliegue" / "publicar_netlify.sh"


def lista_bash(nombre: str) -> list[str]:
    return re.search(rf"^{nombre}=\(([^)]*)\)", SCRIPT.read_text(), flags=re.MULTILINE).group(1).split()


def test_las_reglas_de_netlify_cubren_todas_las_rutas_de_la_api():
    """Una ruta nueva de la API sin su regla daría 404 en curva.rosewt.dev (Netlify no la mandaría al servidor)."""
    fijas, por_area = set(lista_bash("rutas_fijas")), set(lista_bash("rutas_por_area"))
    rutas = {r.path for r in crear_app(PronosticadorDePrueba(), web=None).routes
             if getattr(r, "methods", None) and not r.path.startswith(("/docs", "/redoc", "/openapi"))}
    esperadas_fijas = {r.strip("/") for r in rutas if "{" not in r}
    esperadas_por_area = {r.strip("/").split("/")[0] for r in rutas if "{" in r}
    assert fijas == esperadas_fijas
    assert por_area == esperadas_por_area
    assert all(r.endswith("/{area}") for r in rutas if "{" in r)  # el comodín /* de Netlify cubre un solo segmento


def rutas_de_la_api() -> tuple[set[str], set[str]]:
    rutas = {r.path for r in crear_app(PronosticadorDePrueba(), web=None).routes
             if getattr(r, "methods", None) and not r.path.startswith(("/docs", "/redoc", "/openapi"))}
    return {r for r in rutas if "{" not in r}, {r.split("{")[0] for r in rutas if "{" in r}


def test_robots_bloquea_todas_las_rutas_de_datos_y_deja_la_portada():
    lineas = (RAIZ / "app" / "web" / "robots.txt").read_text().splitlines()
    bloqueadas = {linea.split(":", 1)[1].strip() for linea in lineas if linea.startswith("Disallow:")}
    exactas, prefijos = rutas_de_la_api()
    assert bloqueadas == exactas | prefijos
    assert "Allow: /" in lineas and "User-agent: *" in lineas
    # los archivos de la web no quedan bloqueados (p. ej. /confianza.js frente a /confianza/)
    web = {"/" + p.name for p in (RAIZ / "app" / "web").iterdir()}
    assert not any(w.startswith(b) for w in web for b in bloqueadas)


def test_las_respuestas_de_datos_se_cachean_en_netlify_y_los_errores_nunca():
    from fastapi.testclient import TestClient

    from app.backend.main import CACHE_CDN, CACHE_NAVEGADOR

    c = TestClient(crear_app(PronosticadorDePrueba()))
    exactas, prefijos = rutas_de_la_api()
    for ruta in ["/salud", "/modelos", "/areas", "/resumen", "/ahora/centro", "/en-vivo/centro", "/diagnostico/centro",
                 "/confianza/centro?horizonte=24h&variante=M3"]:
        r = c.get(ruta)
        assert r.status_code == 200, ruta
        assert r.headers["cache-control"] == CACHE_NAVEGADOR == "public, max-age=60"
        assert r.headers["netlify-cdn-cache-control"] == CACHE_CDN == "public, s-maxage=1800"
        # la clave de la caché: los parámetros que usa la API, y ningún otro
        assert r.headers["netlify-vary"] == "query=ahora|fecha|horizonte|modelo|origen|variante"
    # cubre todas las rutas GET de la API (las de área, por su prefijo)
    assert {"/salud", "/modelos", "/areas", "/resumen"} <= exactas and "/ahora/" in prefijos
    for r in (c.get("/series/atlantida?fecha=2026-01-01"), c.get("/confianza/centro?horizonte=3h"),
              c.post("/pronostico", json={})):
        assert r.status_code >= 400 and r.headers["cache-control"] == "no-store"
        assert "netlify-cdn-cache-control" not in r.headers
    assert "netlify-cdn-cache-control" not in c.get("/").headers  # la web estática: la sirve Netlify


@pytest.mark.skipif(shutil.which("bash") is None, reason="hace falta bash")
def test_el_dry_run_arma_la_web_y_las_reglas_sin_publicar():
    salida = subprocess.run(["bash", str(SCRIPT), "--dry-run"], capture_output=True, text=True, check=True).stdout
    assert "/salud" in salida and "/confianza/*" in salida and " 200" in salida
    assert "azurecontainerapps.io/ahora/:splat 200" in salida
    assert "deploy" not in salida  # no llamó a la CLI


# El bloque de app/web/app.js que reintenta, corrido en node con un fetch, un reloj y temporizadores falsos
ARNES = r"""
const fuente = require('fs').readFileSync(process.argv[1], 'utf8');
const inicio = fuente.indexOf('const DESPERTAR_MS');
const fin = fuente.indexOf('\nasync function api(');
let ahora = 0;
const aviso = { oculto: true, visto: false,
  get hidden() { return this.oculto; }, set hidden(v) { this.oculto = v; if (!v) this.visto = true; } };
const document = { getElementById: () => aviso };
const API = '';
const respuestas = JSON.parse(process.argv[2]);
const duracion = Number(process.argv[3]);
let temporizadores = [];
let siguiente = 0;
function setTimeout(f, ms) { siguiente += 1; temporizadores.push({ cuando: ahora + ms, f, id: siguiente }); return siguiente; }
function clearTimeout(id) { temporizadores = temporizadores.filter((t) => t.id !== id); }
function correrHasta(t) {  // corre en orden los temporizadores que vencen antes de t
  for (;;) {
    temporizadores.sort((a, b) => a.cuando - b.cuando);
    const x = temporizadores[0];
    if (!x || x.cuando > t) break;
    temporizadores.shift();
    ahora = x.cuando;
    x.f();
  }
  ahora = Math.max(ahora, t);
}
const pedidos = [];
async function fetch(ruta) {
  pedidos.push(ruta);
  correrHasta(ahora + duracion);  // lo que tarda cada intento (el proxy de Netlify espera hasta 26 s)
  const r = respuestas.length > 1 ? respuestas.shift() : respuestas[0];
  if (r === 0) throw new TypeError('sin conexión');
  return { status: r, ok: r < 400 };
}
globalThis.Date = { now: () => ahora };
eval(fuente.slice(inicio, fin) + `
(async () => {
  let listo = false;
  let r;
  pedirDespertando('/salud', undefined, null).then((x) => { r = x; listo = true; });
  while (!listo) {
    await new Promise((s) => setImmediate(s));
    if (!listo && temporizadores.length) correrHasta(Math.min(...temporizadores.map((t) => t.cuando)));
  }
  console.log(JSON.stringify({ estado: r ? r.status : null, pedidos: pedidos.length, avisoVisto: aviso.visto,
                               avisoAlFinal: !aviso.hidden, segundos: ahora / 1000 }));
})();`);
"""


def despertar(respuestas: list[int], duracion_ms: int = 2000) -> dict:
    salida = subprocess.run(["node", "-e", ARNES, str(RAIZ / "app" / "web" / "app.js"), json.dumps(respuestas),
                             str(duracion_ms)],
                            capture_output=True, text=True, check=True, timeout=30).stdout
    return json.loads(salida)


@pytest.mark.skipif(shutil.which("node") is None, reason="hace falta node")
def test_la_web_espera_al_servidor_dormido_con_un_aviso_y_no_con_un_error():
    # El proxy da 504 (venció su espera), la plataforma 503 mientras arranca y 502; luego responde
    r = despertar([504, 503, 502, 200])
    assert r["estado"] == 200 and r["pedidos"] == 4
    assert r["avisoVisto"] and not r["avisoAlFinal"]
    # Con intentos que tardan los 26 s del proxy, el arranque de ~30 s igual entra en el plazo
    r = despertar([504, 200], duracion_ms=26000)
    assert r["estado"] == 200 and r["pedidos"] == 2
    assert r["avisoVisto"] and not r["avisoAlFinal"]  # el aviso se ve mientras espera y se va al llegar los datos


@pytest.mark.skipif(shutil.which("node") is None, reason="hace falta node")
def test_si_el_proxy_retiene_el_pedido_mientras_despierta_tambien_se_avisa():
    """El proxy espera al servidor hasta 26 s: el pedido no falla, pero tarda ~20 s. Pasados 4 s se avisa."""
    r = despertar([200], duracion_ms=22000)
    assert r["estado"] == 200 and r["pedidos"] == 1 and r["avisoVisto"] and not r["avisoAlFinal"]
    r = despertar([200], duracion_ms=3000)  # el cálculo más lento con el servidor prendido: sin aviso
    assert r["estado"] == 200 and not r["avisoVisto"]


@pytest.mark.skipif(shutil.which("node") is None, reason="hace falta node")
def test_la_web_deja_de_esperar_a_los_60_s_y_muestra_el_error():
    for duracion in (2000, 26000):
        r = despertar([503], duracion_ms=duracion)
        assert r["estado"] == 503 and not r["avisoAlFinal"]
        assert 60 <= r["segundos"] < 60 + 8 + duracion / 1000  # el último intento empieza antes de los 60 s


@pytest.mark.skipif(shutil.which("node") is None, reason="hace falta node")
def test_un_error_de_verdad_o_sin_conexion_no_se_reintenta():
    for estado in (200, 404, 422, 500):
        r = despertar([estado])
        assert r["estado"] == estado and r["pedidos"] == 1 and not r["avisoVisto"]
    # sin conexión: el error con «Reintentar» sale enseguida (el arnés de medición corta la API y lo espera así)
    r = despertar([0])
    assert r["estado"] is None and r["pedidos"] == 1 and not r["avisoVisto"]
