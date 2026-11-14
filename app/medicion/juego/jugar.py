"""Playtest sintético, paso 2: un evaluador automático externo hace de jugador que no conoce Curva.

Cada sesión es una llamada aislada al evaluador (``agy``, solo lectura: ``--mode plan``) con una carpeta temporal
que tiene **solo** las capturas de esa pantalla (o, en la variante ``texto``, solo el árbol de accesibilidad), sin el
código fuente ni las otras pantallas, para que no pueda adelantarse ni hacer trampa. El evaluador recibe una persona,
la consigna y un guion de pensar en voz alta, y responde un JSON con un esquema fijo (``--json-schema``).

Sesiones (las de «entrada» son la primera apertura; las demás, el paso siguiente del camino de una tarea):

- ``entrada-hoy``, ``entrada-1030``, ``entrada-1900``: qué cree que es, qué mira primero, qué momento muestra, la
  lectura de la cifra, el primer clic de las cuatro tareas, dudas, palabras y si volvería mañana.
- ``confianza``: T2 (cuánto se equivoca y si es mejor que la referencia) y T4 (régimen de El Niño con más error).
- ``escenarios``: T3, qué tocaría para ver +2 °C.  ``escenario-2c``: T3, cuánto cambia la demanda.

    uv run --no-sync python app/medicion/juego/jugar.py punta --repeticiones 3 --paralelo 5
    uv run --no-sync python app/medicion/juego/jugar.py punta --modo texto --sesiones entrada-hoy --repeticiones 1

Cada respuesta se guarda al llegar en ``app/medicion/juego/tmp/<etiqueta>/crudo/<modo>/<sesión>/<persona>-r<N>.json``
(fuera de git) y, al terminar, todas se juntan en ``resultados/<etiqueta>/respuestas-<modo>.jsonl`` (versionado, una
línea por sesión). ``--carpeta`` cambia ``<modo>``, p. ej. para guardar aparte la corrida de otro modelo.
Una sesión que ya tiene respuesta no se repite (se puede cortar y retomar).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
# El modelo del evaluador, fijado para que las corridas sean comparables. La línea base se jugó con este; una primera
# corrida con otro modelo (que se quedó sin cuota) queda en respuestas-imagen-argon.jsonl como control entre modelos.
MODELO = "gemini-3.8-flash-medium"

SESIONES = {
    "entrada-hoy": {"pantalla": "hoy", "tipo": "entrada"},
    "entrada-1030": {"pantalla": "repaso-1030", "tipo": "entrada"},
    "entrada-1900": {"pantalla": "repaso-1900", "tipo": "entrada"},
    "confianza": {"pantalla": "confianza", "tipo": "confianza"},
    "escenarios": {"pantalla": "escenarios", "tipo": "escenarios"},
    "escenario-2c": {"pantalla": "escenario-2c", "tipo": "escenario-2c"},
}

# --- Esquemas de respuesta ---------------------------------------------------------------------------------------

TEXTO = {"type": "string"}
IMAGEN = {"type": "integer", "minimum": 1, "maximum": 3}
SEGURIDAD = {"type": "integer", "minimum": 1, "maximum": 5}
DUDAS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"donde": TEXTO, "imagen": IMAGEN, "que": TEXTO},
        "required": ["donde", "imagen", "que"],
    },
}
PALABRAS = {"type": "array", "items": TEXTO}
CLIC = {
    "type": "object",
    "properties": {"texto_exacto": TEXTO, "imagen": IMAGEN, "seguridad": SEGURIDAD, "por_que": TEXTO},
    "required": ["texto_exacto", "imagen", "seguridad", "por_que"],
}
LECTURA = {
    "type": "object",
    "properties": {"texto": TEXTO, "seguridad": SEGURIDAD},
    "required": ["texto", "seguridad"],
}


def _objeto(propiedades: dict) -> dict:
    return {"type": "object", "properties": propiedades, "required": list(propiedades)}


ESQUEMAS = {
    "entrada": _objeto({
        "que_es": TEXTO,
        "para_quien": TEXTO,
        "mira_primero": _objeto({"texto": TEXTO, "imagen": IMAGEN}),
        "voz_alta": TEXTO,
        "momento": _objeto({"tipo": {"type": "string", "enum": ["hoy_en_vivo", "dia_pasado", "no_se"]},
                            "texto": TEXTO}),
        "lectura": LECTURA,
        "primeros_clics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"tarea": {"type": "string", "enum": ["t1", "t2", "t3", "t4"]}, **CLIC["properties"]},
                "required": ["tarea", *CLIC["required"]],
            },
        },
        "dudas": DUDAS,
        "palabras_no_entendidas": PALABRAS,
        "le_importo": TEXTO,
        "volveria_manana": {"type": "string", "enum": ["si", "no", "tal_vez"]},
        "por_que_volveria": TEXTO,
        "que_cambiarias": TEXTO,
    }),
    "confianza": _objeto({
        "voz_alta": TEXTO,
        "t2": _objeto({"texto": TEXTO, "mejor_que_referencia": {"type": "string", "enum": ["si", "no", "no_se"]},
                       "seguridad": SEGURIDAD}),
        "t4": LECTURA,
        "si_no_lo_encuentras": _objeto({"texto_exacto": TEXTO, "imagen": IMAGEN}),
        "dudas": DUDAS,
        "palabras_no_entendidas": PALABRAS,
    }),
    "escenarios": _objeto({"voz_alta": TEXTO, "clic": CLIC, "dudas": DUDAS, "palabras_no_entendidas": PALABRAS}),
    "escenario-2c": _objeto({"voz_alta": TEXTO, "lectura": LECTURA, "dudas": DUDAS,
                             "palabras_no_entendidas": PALABRAS}),
}

# --- Guion -------------------------------------------------------------------------------------------------------

COMUN = """Vas a participar en una prueba de una aplicación web. No eres un evaluador ni un experto en diseño: \
eres {nombre}. {perfil} {motivo}

Nunca has visto esta aplicación y nadie te la explicó. Solo tienes {material} No puedes hacer clic: cuando haga \
falta, di qué tocarías copiando el texto exacto que ves en la pantalla (si el elemento no tiene texto, descríbelo y \
di dónde está).

Piensa en voz alta como lo haría {nombre}: en primera persona, frases cortas, con sus palabras. Si {nombre} no \
entendería algo, dilo; no adivines lo que quiso decir quien la diseñó y no uses conocimientos que {nombre} no tiene. \
Sé honesto aunque la respuesta sea «no sé» o «aquí me pierdo». No abras ni busques ningún otro archivo. Responde en \
español.
"""

DUDAS_Y_PALABRAS = """«dudas»: los lugares donde dudaste o te perdiste: el texto exacto de ese lugar, la imagen y qué \
te hizo dudar (lista vacía si no dudaste). «palabras_no_entendidas»: las palabras, siglas o cifras que {nombre} no \
entiende, copiadas tal como aparecen (lista vacía si las entiende todas)."""

GUIONES = {
    "entrada": """Abres el enlace por primera vez.

1. Primero abre SOLO vista-1.png y mírala como si tuvieras 5 segundos. Responde «que_es» (qué crees que es y para \
qué sirve, en una o dos frases), «para_quien» y «mira_primero» (el texto exacto de lo primero que miraste y la imagen).
2. Ahora mira {todas} con calma, en orden, y piensa en voz alta en «voz_alta» (máximo 150 palabras, en el orden en \
que miras las cosas).
3. «momento»: ¿la pantalla habla de hoy, en vivo, o de un día pasado? ¿De qué día y hora?
4. «lectura»: según la pantalla, ¿cuánta electricidad se usaba en el momento que muestra? ¿Cuánto se había \
pronosticado para ese momento y entre qué valores podía estar? Copia las cifras con su unidad tal como las ves. Si no \
lo encuentras, dilo. Y qué tan seguro estás (1 = nada, 5 = totalmente).
5. «primeros_clics»: para cada una de estas cuatro tareas, ¿qué tocarías primero para lograrla, empezando desde esta \
pantalla? Una entrada por tarea: el texto exacto del elemento, la imagen donde está, qué tan seguro estás (1 a 5) y \
por qué. Si no sabes qué tocar, escribe «no sé» en texto_exacto.
{tareas}
6. {dudas_y_palabras}
7. Al final: «le_importo» (qué te importó o te sirvió de verdad, en una frase), «volveria_manana» (si, no o tal_vez), \
«por_que_volveria» y «que_cambiarias» (una sola cosa).""",
    "confianza": """Estabas en otra pantalla de esta aplicación. Querías esto: «{t2}». Tocaste «Confianza» y llegaste \
a esta pantalla.

1. Mira {todas} en orden y piensa en voz alta en «voz_alta» (máximo 120 palabras).
2. «t2»: según esta pantalla, ¿cuánto se equivoca normalmente el pronóstico? Copia la cifra o cifras con su unidad en \
«texto». En «mejor_que_referencia»: ¿lo hace mejor que la referencia simple? (si, no o no_se). Y tu seguridad (1 a 5).
3. «t4»: ahora también quieres esto: «{t4}». Con lo que ves aquí, ¿en qué situación de El Niño se equivoca más? \
Copia el nombre y la cifra en «texto»; si no lo ves, dilo. Y tu seguridad (1 a 5).
4. «si_no_lo_encuentras»: si te faltó algo, ¿qué tocarías para buscarlo? (texto exacto e imagen; «nada» si ya lo \
encontraste todo).
5. {dudas_y_palabras}""",
    "escenarios": """Querías esto: «{t3}». En la pantalla anterior tocaste «¿Y si hace más calor?» y llegaste aquí.

1. Mira {todas} en orden y piensa en voz alta en «voz_alta» (máximo 120 palabras).
2. «clic»: ¿qué tocarías ahora para ver qué pasa con 2 °C más de calor? El texto exacto del elemento, la imagen, tu \
seguridad (1 a 5) y por qué. Si no sabes qué tocar, escribe «no sé».
3. {dudas_y_palabras}""",
    "escenario-2c": """Querías esto: «{t3}». En la pantalla anterior tocaste «¿Y si hace más calor?» y después «+2 °C». \
Esta es la pantalla que quedó.

1. Mira {todas} en orden y piensa en voz alta en «voz_alta» (máximo 120 palabras).
2. «lectura»: ¿cuánto cambia la demanda con 2 °C más de calor? Copia la cifra con su unidad y di a qué hora se \
refiere. Si no lo encuentras, dilo. Y tu seguridad (1 a 5).
3. {dudas_y_palabras}""",
}


def material(modo: str, carpeta: Path, vistas: int) -> tuple[str, str]:
    """Qué tiene el jugador y cómo se nombra «todo» en el guion."""
    if modo == "texto":
        return ((f"la descripción de la página que leería un lector de pantalla, en el archivo "
                 f"{carpeta}/pagina.txt: no ves la pantalla, escuchas esa descripción de arriba abajo (las "
                 "«imágenes» del guion son, para ti, ese único archivo; usa imagen = 1)."), "la descripción completa")
    abajo = {1: "", 2: " vista-2.png es lo que verías si bajas con la rueda del ratón.",
             3: " vista-2.png y vista-3.png son lo que verías si bajas con la rueda del ratón."}[vistas]
    todas = "vista-1.png" if vistas == 1 else " y ".join(
        [", ".join(f"vista-{i}.png" for i in range(1, vistas)), f"vista-{vistas}.png"])
    return (f"las capturas de pantalla de la carpeta {carpeta}: vista-1.png es lo que ves al abrir.{abajo}", todas)


def guion(sesion: str, persona: dict, tareas: dict, carpeta: Path, vistas: int, modo: str) -> str:
    tipo = SESIONES[sesion]["tipo"]
    que, todas = material(modo, carpeta, vistas)
    lista = "\n".join(f"   - {k}: {t['consigna']}" for k, t in tareas.items())
    cuerpo = GUIONES[tipo].format(todas=todas, tareas=lista, dudas_y_palabras=DUDAS_Y_PALABRAS,
                                  t2=tareas["t2"]["consigna"], t3=tareas["t3"]["consigna"],
                                  t4=tareas["t4"]["consigna"])
    return (COMUN.format(material=que, **persona) + "\n" + cuerpo).format(nombre=persona["nombre"])


# --- Ejecución ---------------------------------------------------------------------------------------------------

def preparar_carpeta(origen: Path, modo: str) -> tuple[Path, int]:
    """Una carpeta temporal con solo lo que el jugador puede ver de esta pantalla."""
    carpeta = Path(tempfile.mkdtemp(prefix="juego-"))
    if modo == "texto":
        shutil.copy(origen / "aria.yaml", carpeta / "pagina.txt")
        return carpeta, 1
    # Solo las vistas que lista el manifiesto de esa captura (no restos de una captura anterior)
    manifiesto = origen.parent / "manifiesto.json"
    vistas = sorted(origen.glob("vista-*.png"))
    if manifiesto.exists():
        pantalla = next(p for p in json.loads(manifiesto.read_text())["pantallas"] if p["pantalla"] == origen.name)
        vistas = [origen / v["archivo"] for v in pantalla["vistas"]]
    for v in vistas:
        shutil.copy(v, carpeta / v.name)
    return carpeta, len(vistas)


def jugar_una(etiqueta: str, sesion: str, persona: dict, rep: int, modo: str, modelo: str | None,
              tareas: dict, destino: Path) -> dict:
    pantalla = SESIONES[sesion]["pantalla"]
    origen = AQUI / "tmp" / etiqueta / pantalla
    carpeta, vistas = preparar_carpeta(origen, modo)
    esquema = Path(tempfile.mkstemp(prefix="esquema-", suffix=".json")[1])
    esquema.write_text(json.dumps(ESQUEMAS[SESIONES[sesion]["tipo"]], ensure_ascii=False))
    texto = guion(sesion, persona, tareas, carpeta, vistas, modo)
    orden = ["agy", "--mode", "plan", "--print-timeout", "400s", "--add-dir", str(carpeta),
             "--json-schema", str(esquema), "--output-format", "json", "-p", texto]
    if modelo:
        orden[1:1] = ["--model", modelo]
    registro = {"etiqueta": etiqueta, "sesion": sesion, "pantalla": pantalla, "persona": persona["id"],
                "repeticion": rep, "modo": modo, "modelo": modelo or "por defecto", "vistas": vistas,
                "inicio": datetime.now().isoformat(timespec="seconds")}
    try:
        for intento in (1, 2):
            t0 = time.time()
            try:
                r = subprocess.run(orden, cwd=carpeta, capture_output=True, text=True, timeout=420, check=False)
                salida = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
            except (subprocess.TimeoutExpired, json.JSONDecodeError, IndexError) as error:
                salida = {"status": "ERROR", "error": repr(error)}
            registro.update({"intento": intento, "segundos": round(time.time() - t0, 1),
                             "estado": salida.get("status", "ERROR"), "uso": salida.get("usage")})
            respuesta = salida.get("structured_output")
            if respuesta is None and salida.get("response"):
                try:
                    respuesta = json.loads(salida["response"])
                except json.JSONDecodeError:
                    registro["crudo"] = salida["response"]
            if respuesta is not None and registro["estado"] == "SUCCESS":
                registro["respuesta"] = respuesta
                registro.pop("crudo", None)
                break
            registro["error"] = salida.get("error") or (r.stderr[-500:] if "r" in locals() else "")
            if "quota" in str(registro["error"]).lower():
                break  # sin cuota no tiene sentido reintentar
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)
        esquema.unlink(missing_ok=True)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=1))
    return registro


def leer_respuestas(etiqueta: str, corrida: str) -> list[dict]:
    """Las respuestas válidas ya juntadas de una corrida (``respuestas-<corrida>.jsonl``)."""
    archivo = AQUI / "resultados" / etiqueta / f"respuestas-{corrida}.jsonl"
    if not archivo.exists():
        return []
    return [json.loads(linea) for linea in archivo.read_text().splitlines() if linea.strip()]


def juntar(etiqueta: str, corrida: str) -> int:
    """Junta en el JSONL versionado las respuestas válidas de tmp/ con las que ya estaban; devuelve cuántas hay."""
    def clave(r: dict) -> tuple:
        return r["sesion"], r["persona"], r["repeticion"]

    todas = {clave(r): r for r in leer_respuestas(etiqueta, corrida)}
    for archivo in (AQUI / "tmp" / etiqueta / "crudo" / corrida).glob("*/*.json"):
        r = json.loads(archivo.read_text())
        if "respuesta" in r:
            todas[clave(r)] = r
    destino = AQUI / "resultados" / etiqueta / f"respuestas-{corrida}.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("".join(json.dumps(todas[k], ensure_ascii=False) + "\n" for k in sorted(todas)))
    return len(todas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("etiqueta")
    ap.add_argument("--personas", default="", help="ids separados por comas (por defecto, todas)")
    ap.add_argument("--sesiones", default="", help="sesiones separadas por comas (por defecto, todas)")
    ap.add_argument("--repeticiones", type=int, default=3)
    ap.add_argument("--paralelo", type=int, default=5)
    ap.add_argument("--modo", choices=["imagen", "texto"], default="imagen")
    ap.add_argument("--modelo", default=MODELO, help="modelo del evaluador ('' = el que use por defecto)")
    ap.add_argument("--carpeta", default="", help="nombre de la corrida (por defecto, el del modo)")
    a = ap.parse_args()
    personas = json.loads((AQUI / "personas.json").read_text())
    if a.personas:
        personas = [p for p in personas if p["id"] in a.personas.split(",")]
    tareas = json.loads((AQUI / "tareas.json").read_text())
    sesiones = a.sesiones.split(",") if a.sesiones else list(SESIONES)
    corrida = a.carpeta or a.modo
    base = AQUI / "tmp" / a.etiqueta / "crudo" / corrida
    hechas = {(r["sesion"], r["persona"], r["repeticion"]) for r in leer_respuestas(a.etiqueta, corrida)}
    trabajos = []
    for rep in range(1, a.repeticiones + 1):
        for s in sesiones:
            for p in personas:
                destino = base / s / f"{p['id']}-r{rep}.json"
                ya = destino.exists() and "respuesta" in json.loads(destino.read_text())
                if ya or (s, p["id"], rep) in hechas:
                    continue
                trabajos.append((s, p, rep, destino))
    print(f"{len(trabajos)} sesiones por jugar ({a.etiqueta}, {a.modo}, modelo {a.modelo or 'por defecto'})")
    with ThreadPoolExecutor(max_workers=a.paralelo) as grupo:
        futuros = {grupo.submit(jugar_una, a.etiqueta, s, p, rep, a.modo, a.modelo or None, tareas, d): (s, p, rep)
                   for s, p, rep, d in trabajos}
        for i, f in enumerate(as_completed(futuros), 1):
            s, p, rep = futuros[f]
            if f.cancelled():
                continue
            r = f.result()
            print(f"[{i}/{len(trabajos)}] {s} {p['id']} r{rep}: {r['estado']} en {r.get('segundos')} s", flush=True)
            if "quota" in str(r.get("error", "")).lower():
                print("El evaluador se quedó sin cuota: se cancelan las sesiones pendientes.", flush=True)
                for pendiente in futuros:
                    pendiente.cancel()
    print(f"{juntar(a.etiqueta, corrida)} respuestas en resultados/{a.etiqueta}/respuestas-{corrida}.jsonl")


if __name__ == "__main__":
    main()
