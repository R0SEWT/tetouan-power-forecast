"""Playtest sintético, paso 3: codifica las respuestas del evaluador y calcula las medidas por pantalla.

La codificación es por reglas (sin otro evaluador automático), para que dos corridas del análisis den lo mismo:

- **Primer clic**: el texto que cita el jugador se ubica entre los controles visibles de esa pantalla
  (``pantallas.json``, por coincidencia de texto; una fecha o una hora citadas se ubican en su campo). Se califica
  con las expresiones de ``tareas.json``: *acierto*, *aceptable* (lleva por un camino más largo), *equivocado*,
  *no es control* (toca algo que no se puede tocar: una falsa affordance) o *no sabe*.
- **Lecturas**: las cifras que copia el jugador se comparan con los oráculos de la API (tolerancia de 1 MW, o de
  medio punto si la cifra se redondeó).
- **Tropiezos**: cada fallo es un tropiezo con su pantalla, su paso, su tipo, su objetivo y una severidad de 1 a 4
  (escala de Nielsen): 4 = no sabe qué hacer o se lleva una cifra equivocada; 3 = primer clic equivocado, toca algo
  que no es un control, no entiende qué es o qué momento muestra; 2 = acierta dudando (seguridad ≤ 2) o lee la cifra
  sin su rango; 1 = una duda o una palabra que no entiende.

    python3 app/medicion/juego/analizar.py punta              # resultados/punta/analisis.{json,md}
    python3 app/medicion/juego/analizar.py develop punta      # y resultados/comparacion-develop-punta.md
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RES = AQUI / "resultados"
NO_SABE = {"", "no se", "nada", "ninguno", "ninguna", "no lo se", "no sabria"}

# Términos canónicos: el primer patrón que calce da el nombre con que se cuenta la palabra no entendida
TERMINOS = [
    ("MW / megavatios", r"\bmw\b|megavat"),
    ("COES", r"\bcoes\b"),
    ("SEIN", r"\bsein\b"),
    ("rango del N %", r"rango"),
    ("referencia", r"referencia"),
    ("El Niño costero / ICEN", r"nino|icen"),
    ("CSV", r"\bcsv\b"),
    ("IEOD", r"\bieod\b"),
    ("Chronos-2 / modelo fundacional", r"chronos|fundacional|series de tiempo"),
    ("MAE / MAPE / WAPE", r"\bmae\b|\bmape\b|\bwape\b"),
    ("cobertura", r"cobertura|cubrio"),
    ("sesgo / subestima", r"sesgo|subestim|sobreestim"),
    ("régimen", r"regimen"),
    ("repaso", r"repaso"),
    ("umbral", r"umbral"),
    ("rampa / mayor subida", r"rampa|subida"),
    ("pico", r"\bpico\b"),
    ("medias horas / periodos", r"medias horas|periodos"),
    ("reconstruido / registro en vivo", r"reconstru|registro"),
    ("horizonte / 24 h", r"horizonte|\b24 ?h\b|\b1 ?h\b"),
    ("Simons (componente del modelo)", r"simons"),
    ("modelo / híbrido / XGBoost", r"modelo|hibrido|xgboost|combinado"),
    ("escenario / supuesto", r"escenario|supuesto"),
    ("ENFEN", r"enfen"),
    ("PJM / Elia (referencias externas)", r"\bpjm\b|\belia\b"),
    ("MM/DD (fecha al revés)", r"\d{1,2}/\d{1,2}/\d{4}|am\b|pm\b"),
]


def norm(texto: str) -> str:
    """Minúsculas, sin tildes ni comillas, espacios simples."""
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[«»\"“”‘’'`→←↓↑·•…]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip(" .,:;!?¿¡-")


def tokens(texto: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9+°%]+", norm(texto)) if len(w) > 1 or w.isdigit()}


def parecido(a: str, b: str) -> float:
    """1 si son iguales, 0.9 si uno contiene al otro (con al menos 4 letras), si no Jaccard de palabras."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if min(len(na), len(nb)) >= 4 and (na in nb or nb in na):
        return 0.9
    ta, tb = tokens(a), tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


MESES = r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
# Horas y fechas no son cantidades: «a las 15:30» no es un cambio de 15 MW ni «10 de marzo» una cifra de 10
NO_CANTIDAD = re.compile(r"\b\d{1,2}:\d{2}(?:\s*(?:am|pm|h)\b)?|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b|"
                         rf"\b\d{{1,2}} de (?:{MESES})\b|\b(?:19|20)\d{{2}}-\d{{2}}-\d{{2}}\b", re.IGNORECASE)


def numeros(texto: str) -> list[float]:
    """Las cantidades de un texto, con coma o punto de miles o de decimales («4,456», «4.456», «71,9», «1.66»),
    sin contar horas ni fechas."""
    salida = []
    limpio = NO_CANTIDAD.sub(" ", str(texto))
    for m in re.finditer(r"\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?", limpio):
        s = m.group().replace(" ", "")
        if "," in s and "." in s:
            dec = "," if s.rfind(",") > s.rfind(".") else "."
            s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
        elif "," in s or "." in s:
            sep = "," if "," in s else "."
            partes = s.split(sep)
            s = "".join(partes) if all(len(p) == 3 for p in partes[1:]) else s.replace(sep, ".")
        try:
            salida.append(float(s))
        except ValueError:
            continue
    return salida


def calza(texto: str, valores: list[float]) -> bool:
    """¿Alguna cifra del texto es uno de los valores? 1 MW de tolerancia; en cifras chicas, medio punto o redondeo."""
    for x in numeros(texto):
        for v in valores:
            tol = 1.0 if v >= 100 else (0.51 if v >= 10 else 0.06)
            if abs(x - v) <= tol:
                return True
    return False


def termino(palabra: str) -> str:
    n = norm(palabra)
    for nombre, patron in TERMINOS:
        if re.search(patron, n):
            return nombre
    return n[:40]


# --- Ubicar lo que cita el jugador -------------------------------------------------------------------------------

def ubicar(cita: str, pantalla: dict) -> dict:
    """El control (o, si no, el texto) de la pantalla que mejor corresponde a la cita."""
    n = norm(cita)
    if n in NO_SABE or n.startswith(("no se ", "no sabria")):
        return {"tipo": "no_sabe"}
    controles = [(c, v["archivo"]) for v in pantalla["vistas"] for c in v["controles"]]
    if re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", n):
        for c, archivo in controles:
            if c["tipo"] == "input:date":
                return {"tipo": "control", "etiqueta": c["etiqueta"], "zona": c["zona"], "vista": archivo}
    if re.search(r"\b\d{1,2}:\d{2}\s*(am|pm)\b", n):
        for c, archivo in controles:
            if c["tipo"] == "input:time":
                return {"tipo": "control", "etiqueta": c["etiqueta"], "zona": c["zona"], "vista": archivo}
    mejor, puntaje = None, 0.0
    for c, archivo in controles:
        p = max(parecido(cita, c["etiqueta"]), parecido(cita, c.get("valor") or ""))
        if p > puntaje:
            mejor, puntaje = (c, archivo), p
    if mejor and puntaje >= 0.5:
        c, archivo = mejor
        return {"tipo": "control", "etiqueta": c["etiqueta"], "zona": c["zona"], "vista": archivo}
    textos = [(t, v["archivo"]) for v in pantalla["vistas"] for t in v["textos"]]
    mejor, puntaje = None, 0.0
    for t, archivo in textos:
        p = parecido(cita, t["t"])
        if p > puntaje:
            mejor, puntaje = (t, archivo), p
    if mejor and puntaje >= 0.4:
        t, archivo = mejor
        campo = campo_de_etiqueta(t, archivo, pantalla)
        if campo:
            return campo
        return {"tipo": "texto", "etiqueta": t["t"][:60], "zona": t["zona"], "vista": archivo}
    return {"tipo": "fuera", "etiqueta": cita[:60]}


def campo_de_etiqueta(texto: dict, archivo: str, pantalla: dict) -> dict | None:
    """Un texto corto junto a un campo de la misma zona es su etiqueta: tocarla activa el campo («Ver otro día»)."""
    if len(texto["t"]) > 40:
        return None
    vista = next(v for v in pantalla["vistas"] if v["archivo"] == archivo)
    campos = [c for c in vista["controles"] if c["tipo"].startswith("input:") and c["zona"] == texto["zona"]]
    if not campos:
        return None
    n = norm(texto["t"])
    preferido = {"input:date": r"dia|fecha", "input:time": r"hora|\blas\b", "input:checkbox": r"mostrar|referencia"}
    elegido = next((c for c in campos if re.search(preferido.get(c["tipo"], "$^"), n)), campos[0])
    return {"tipo": "control", "etiqueta": f"{texto['t']} ({elegido['tipo']})", "zona": elegido["zona"],
            "vista": archivo}


def calificar_clic(cita: str, pantalla: dict, regla: dict) -> dict:
    lugar = ubicar(cita, pantalla)
    if lugar["tipo"] == "no_sabe":
        return {**lugar, "resultado": "no_sabe"}
    if lugar["tipo"] != "control":
        return {**lugar, "resultado": "no_es_control"}
    candidatos = [norm(lugar["etiqueta"]), norm(cita)]
    if any(re.search(p, c) for p in regla["aciertos"] for c in candidatos):
        return {**lugar, "resultado": "acierto"}
    if any(re.search(p, c) for p in regla.get("aceptables", []) for c in candidatos):
        return {**lugar, "resultado": "aceptable"}
    return {**lugar, "resultado": "equivocado"}


def zona_de(cita: str, pantalla: dict) -> str:
    lugar = ubicar(cita, pantalla)
    return lugar.get("zona") or "no ubicada"


# --- Codificar una sesión ----------------------------------------------------------------------------------------

COMPRENDE = (r"pronost|predic|estim|calcul|prev|anticip|proyecc|adivin|va a (usar|consumir|gastar)|se usara|futur",
             r"electric|energ|\bluz\b|demanda|consumo|megavat|\bmw\b")
# Lo que le importó al jugador, en categorías (una respuesta puede caer en varias)
IMPORTO = {
    "rendición de cuentas (acertó, cuánto se equivoca)": r"acert|equivoc|error|fiar|confi|rango|referencia|honest",
    "el pico y la hora de más consumo": r"pico|hora .*mas|mas luz|mayor demanda|punta",
    "la cifra de ahora": r"cifra|ahora|en este momento|cuanta (luz|electricidad)",
    "los datos para descargar": r"csv|descarg|datos limpios|tabla",
    "nada": r"no me sirve|\bnada\b|no me ayuda|no me importa",
}
# Lo primero que mira es la cifra del momento o la respuesta a la pregunta (el hito de la pantalla)
ZONAS_CIFRA = {"cifra_ahora", "respuesta", "#ahRespuesta"}
ESPERADO_MOMENTO = {"hoy": "hoy_en_vivo", "repaso-1030": "dia_pasado", "repaso-1900": "dia_pasado"}


def momento_esperado(nombre: str, momento: str | None, capturado: str | None) -> set[str]:
    """Las respuestas correctas a «¿qué momento muestra?». De madrugada, la entrada en vivo muestra días pasados (el
    momento del oráculo es de antes del día de la captura): decir que es un día pasado también es correcto."""
    esperado = {ESPERADO_MOMENTO[nombre]}
    if nombre == "hoy" and momento and capturado and momento[:10] < capturado[:10]:
        esperado.add("dia_pasado")
    return esperado
CLIC_2C = r"\+\s*2\s*(°|o|grados)?\s*c?\b"
# Marcadores de confusión en la voz alta (codificación clásica del protocolo de pensar en voz alta)
CONFUSION = (r"no entiendo|no entendi|no se (que|si|donde|cual|por que)|confund|me pierdo|perdid|no queda claro|"
             r"no tengo idea|enredad|complicad|raro|extran|no me queda|no estoy segur|al reves|contradic")


def recorte(texto: str, palabras: int = 28) -> str:
    p = str(texto).split()
    return " ".join(p[:palabras]) + (" …" if len(p) > palabras else "")


def codificar(registro: dict, pantalla: dict, oraculos: dict, tareas: dict, capturado: str | None = None) -> dict:
    r = registro["respuesta"]
    nombre = registro["pantalla"]
    c = {"sesion": registro["sesion"], "pantalla": nombre, "persona": registro["persona"],
         "repeticion": registro["repeticion"], "tropiezos": []}
    trop = c["tropiezos"]

    def tropiezo(paso, tipo, objetivo, severidad, evidencia):
        trop.append({"pantalla": nombre, "paso": paso, "tipo": tipo, "objetivo": objetivo,
                     "severidad": severidad, "evidencia": recorte(evidencia)})

    c["confusion"] = len(re.findall(CONFUSION, norm(r.get("voz_alta", ""))))
    for d in r.get("dudas", []):
        tropiezo("duda", "duda", zona_de(d.get("donde", ""), pantalla), 1, d.get("que", ""))
    c["dudas"] = [zona_de(d.get("donde", ""), pantalla) for d in r.get("dudas", [])]
    c["terminos"] = sorted({termino(p) for p in r.get("palabras_no_entendidas", []) if norm(p)})
    for t in c["terminos"]:
        tropiezo("palabra", "palabra", t, 1, t)

    tipo = registro["sesion"] if registro["sesion"] in ("confianza", "escenarios", "escenario-2c") else "entrada"
    if tipo == "entrada":
        texto_es = norm(r.get("que_es", ""))
        c["comprende"] = all(re.search(p, texto_es) for p in COMPRENDE)
        if not c["comprende"]:
            tropiezo("qué es", "no entiende qué es", "primera impresión", 3, r.get("que_es", ""))
        c["mira_primero"] = zona_de(r.get("mira_primero", {}).get("texto", ""), pantalla)
        esperado = momento_esperado(nombre, oraculos["lectura"][nombre].get("momento"), capturado)
        c["momento_ok"] = r.get("momento", {}).get("tipo") in esperado
        if not c["momento_ok"]:
            tropiezo("momento", "confunde el momento", r.get("momento", {}).get("tipo", "?"), 3,
                     r.get("momento", {}).get("texto", ""))
        o = oraculos["lectura"][nombre]
        lectura = r.get("lectura", {}).get("texto", "")
        grupos = {g: calza(lectura, o[g]) for g in ("cifra", "pronostico", "inferior", "superior")}
        c["lectura_cifra"] = grupos["cifra"]
        c["lectura_completa"] = all(grupos.values())
        if not grupos["cifra"]:
            tropiezo("lectura", "lectura errónea", "cifra del momento", 4, lectura)
        elif not c["lectura_completa"]:
            faltan = ", ".join(g for g, ok in grupos.items() if not ok)
            tropiezo("lectura", "lectura incompleta", f"falta {faltan}", 2, lectura)
        c["clics"] = {}
        for clic in r.get("primeros_clics", []):
            t = clic.get("tarea")
            if t not in tareas or t in c["clics"]:
                continue
            cal = calificar_clic(clic.get("texto_exacto", ""), pantalla, tareas[t])
            cal["seguridad"] = clic.get("seguridad")
            c["clics"][t] = cal
            objetivo = cal.get("etiqueta") or "—"
            if cal["resultado"] == "no_sabe":
                tropiezo(f"{t} primer clic", "no sabe qué tocar", "—", 4, clic.get("por_que", ""))
            elif cal["resultado"] == "no_es_control":
                tropiezo(f"{t} primer clic", "toca algo que no es control", objetivo, 3, clic.get("por_que", ""))
            elif cal["resultado"] == "equivocado":
                tropiezo(f"{t} primer clic", "primer clic equivocado", objetivo, 3, clic.get("por_que", ""))
            elif (clic.get("seguridad") or 5) <= 2:
                tropiezo(f"{t} primer clic", "acierta dudando", objetivo, 2, clic.get("por_que", ""))
        c["volveria"] = r.get("volveria_manana")
        c["le_importo"] = r.get("le_importo", "")
        c["importo"] = [k for k, patron in IMPORTO.items() if re.search(patron, norm(c["le_importo"]))]
        c["por_que_volveria"] = r.get("por_que_volveria", "")
        c["seguridad"] = r.get("lectura", {}).get("seguridad")
    elif tipo == "confianza":
        o = oraculos["t2"]
        t2 = r.get("t2", {})
        c["t2_error"] = calza(t2.get("texto", ""), o["error"])
        esperado = "si" if o["mejor_que_referencia"] else "no"
        c["t2_referencia"] = t2.get("mejor_que_referencia") == esperado
        c["t2_ok"] = c["t2_error"] and c["t2_referencia"]
        if not c["t2_ok"]:
            falta = "el error" if not c["t2_error"] else "la comparación con la referencia"
            tropiezo("t2 lectura", "lectura errónea", falta, 4, t2.get("texto", ""))
        t4 = r.get("t4", {})
        regimen = [norm(x) for x in oraculos["t4"]["régimen"]]
        c["t4_ok"] = any(x in norm(t4.get("texto", "")) for x in regimen)
        if not c["t4_ok"]:
            tropiezo("t4 lectura", "lectura errónea", "régimen con más error", 4, t4.get("texto", ""))
        c["seguridad"] = t2.get("seguridad")
    elif tipo == "escenarios":
        clic = r.get("clic", {})
        cal = calificar_clic(clic.get("texto_exacto", ""), pantalla, {"aciertos": [CLIC_2C]})
        c["clic"] = cal
        c["t3_clic_ok"] = cal["resultado"] == "acierto"
        if not c["t3_clic_ok"]:
            tropiezo("t3 clic +2 °C", "primer clic equivocado" if cal["resultado"] == "equivocado"
                     else cal["resultado"].replace("_", " "), cal.get("etiqueta") or "—",
                     4 if cal["resultado"] == "no_sabe" else 3, clic.get("por_que", ""))
        c["seguridad"] = clic.get("seguridad")
    elif tipo == "escenario-2c":
        lectura = r.get("lectura", {}).get("texto", "")
        valores = [x for alt in oraculos["t3"]["cambio del escenario"] for x in numeros(alt)]
        c["t3_lectura_ok"] = calza(lectura, valores)
        if not c["t3_lectura_ok"]:
            tropiezo("t3 lectura", "lectura errónea", "cambio con +2 °C", 4, lectura)
        c["seguridad"] = r.get("lectura", {}).get("seguridad")
    return c


# --- Medidas -----------------------------------------------------------------------------------------------------

def media(xs) -> float | None:
    xs = [float(x) for x in xs if x is not None]
    return round(statistics.mean(xs), 3) if xs else None


def por_repeticion(codigos: list[dict], f) -> dict:
    """La medida calculada en cada repetición (sobre las cinco personas): su media, mínimo y máximo."""
    grupos = defaultdict(list)
    for c in codigos:
        v = f(c)
        if v is not None:
            grupos[c["repeticion"]].append(float(v))
    reps = [statistics.mean(v) for _, v in sorted(grupos.items()) if v]
    todos = [x for v in grupos.values() for x in v]
    if not todos:
        return {"media": None, "min": None, "max": None, "n": 0, "reps": 0}
    return {"media": round(statistics.mean(todos), 3), "min": round(min(reps), 3),
            "max": round(max(reps), 3), "n": len(todos), "reps": len(reps)}


def acuerdo(codigos: list[dict], f) -> float | None:
    """Fracción de personas cuya respuesta (sí/no) es la misma en todas sus repeticiones."""
    por_persona = defaultdict(list)
    for c in codigos:
        v = f(c)
        if v is not None:
            por_persona[c["persona"]].append(bool(v))
    casos = [len(set(v)) == 1 for v in por_persona.values() if len(v) > 1]
    return round(sum(casos) / len(casos), 3) if casos else None


def exito_clic(c, t, amplio=True):
    if t not in c.get("clics", {}):
        return None
    return c["clics"][t]["resultado"] in (("acierto", "aceptable") if amplio else ("acierto",))


def medidas_pantalla(codigos: list[dict], tareas: dict) -> dict:
    m = {"sesiones": len(codigos),
         "dudas_por_sesion": por_repeticion(codigos, lambda c: len(c["dudas"])),
         "terminos_por_sesion": por_repeticion(codigos, lambda c: len(c["terminos"])),
         "confusion_por_sesion": por_repeticion(codigos, lambda c: c["confusion"]),
         "seguridad": por_repeticion(codigos, lambda c: c.get("seguridad"))}
    zonas = Counter(z for c in codigos for z in c["dudas"])
    m["dudas_zonas"] = zonas.most_common(6)
    terminos = Counter(t for c in codigos for t in c["terminos"])
    m["terminos_top"] = [(t, round(n / len(codigos), 2)) for t, n in terminos.most_common(8)]
    if codigos and "clics" in codigos[0]:
        m["comprende"] = por_repeticion(codigos, lambda c: c["comprende"])
        m["momento_ok"] = por_repeticion(codigos, lambda c: c["momento_ok"])
        m["lectura_cifra"] = por_repeticion(codigos, lambda c: c["lectura_cifra"])
        m["lectura_completa"] = por_repeticion(codigos, lambda c: c["lectura_completa"])
        m["primer_clic"] = {t: por_repeticion(codigos, lambda c, t=t: exito_clic(c, t)) for t in tareas}
        m["primer_clic_estricto"] = {t: por_repeticion(codigos, lambda c, t=t: exito_clic(c, t, False))
                                     for t in tareas}
        m["primer_clic_medio"] = por_repeticion(
            codigos, lambda c: media([exito_clic(c, t) for t in tareas]))
        m["no_es_control"] = Counter(c["clics"][t].get("etiqueta", "")[:50] for c in codigos
                                     for t in c["clics"] if c["clics"][t]["resultado"] == "no_es_control"
                                     ).most_common(4)
        m["mira_primero"] = Counter(c["mira_primero"] for c in codigos).most_common(4)
        m["mira_primero_cifra"] = por_repeticion(codigos, lambda c: c["mira_primero"] in ZONAS_CIFRA)
        m["volveria"] = dict(Counter(c["volveria"] for c in codigos))
        m["importo"] = [(k, round(n / len(codigos), 2)) for k, n in
                        Counter(k for c in codigos for k in c["importo"]).most_common()]
        m["volveria_si_o_tal_vez"] = por_repeticion(codigos, lambda c: c["volveria"] in ("si", "tal_vez"))
        m["acuerdo_entre_repeticiones"] = {
            "comprende": acuerdo(codigos, lambda c: c["comprende"]),
            "lectura_cifra": acuerdo(codigos, lambda c: c["lectura_cifra"]),
            **{f"clic_{t}": acuerdo(codigos, lambda c, t=t: exito_clic(c, t)) for t in tareas},
        }
        m["embudo"] = embudo(codigos)
    for clave in ("t2_ok", "t4_ok", "t3_clic_ok", "t3_lectura_ok"):
        if codigos and clave in codigos[0]:
            m[clave] = por_repeticion(codigos, lambda c, k=clave: c[k])
            m[f"acuerdo_{clave}"] = acuerdo(codigos, lambda c, k=clave: c[k])
    return m


PASOS_EMBUDO = [
    ("abre la pantalla", lambda c: True),
    ("dice qué es", lambda c: c["comprende"]),
    ("lee la cifra del momento", lambda c: c["lectura_cifra"]),
    ("sabe qué momento muestra", lambda c: c["momento_ok"]),
    ("acierta el primer clic en 3 de 4 tareas",
     lambda c: sum(bool(exito_clic(c, t)) for t in ("t1", "t2", "t3", "t4")) >= 3),
    ("volvería mañana (sí o tal vez)", lambda c: c["volveria"] in ("si", "tal_vez")),
]


def embudo(codigos: list[dict]) -> list[dict]:
    """Cuántas sesiones pasan cada paso habiendo pasado todos los anteriores, y en cuál se pierde cada una."""
    vivos = list(codigos)
    salida = []
    for nombre, f in PASOS_EMBUDO:
        vivos = [c for c in vivos if f(c)]
        salida.append({"paso": nombre, "quedan": len(vivos), "de": len(codigos)})
    return salida


def embudos_tareas(por_sesion: dict) -> dict:
    """Por tarea, cuántas corridas (persona × repetición) hacen todos los pasos sin tropezar."""
    def indice(sesion):
        return {(c["persona"], c["repeticion"]): c for c in por_sesion.get(sesion, [])}
    hoy, r1900 = indice("entrada-hoy"), indice("entrada-1900")
    conf, esc, esc2 = indice("confianza"), indice("escenarios"), indice("escenario-2c")
    caminos = {
        "t1": [("primer clic desde hoy", hoy, lambda c: exito_clic(c, "t1")),
               ("lee lo pronosticado, el rango y lo real (repaso 19:00)", r1900,
                lambda c: c["lectura_completa"])],
        "t2": [("primer clic desde hoy", hoy, lambda c: exito_clic(c, "t2")),
               ("lee el error y la comparación (Confianza)", conf, lambda c: c["t2_ok"])],
        "t3": [("primer clic desde el repaso de las 19:00", r1900, lambda c: exito_clic(c, "t3")),
               ("toca +2 °C", esc, lambda c: c["t3_clic_ok"]),
               ("lee el cambio", esc2, lambda c: c["t3_lectura_ok"])],
        "t4": [("primer clic desde hoy", hoy, lambda c: exito_clic(c, "t4")),
               ("lee el régimen con más error (Confianza)", conf, lambda c: c["t4_ok"])],
    }
    salida = {}
    for t, pasos in caminos.items():
        claves = set.intersection(*[set(idx) for _, idx, _ in pasos]) if all(idx for _, idx, _ in pasos) else set()
        vivos = sorted(claves)
        filas = []
        for nombre, idx, f in pasos:
            vivos = [k for k in vivos if f(idx[k])]
            filas.append({"paso": nombre, "quedan": len(vivos), "de": len(claves)})
        salida[t] = filas
    return salida


def agrupar_tropiezos(codigos: list[dict], minimo: int = 2) -> list[dict]:
    """Los tropiezos agrupados por pantalla, paso, tipo y objetivo, con su frecuencia y su puntaje."""
    por_pantalla = Counter(c["pantalla"] for c in codigos)
    grupos = defaultdict(list)
    for c in codigos:
        vistos = set()
        for t in c["tropiezos"]:
            if t["severidad"] < minimo:
                continue
            clave = (t["pantalla"], t["paso"], t["tipo"], t["objetivo"])
            if clave in vistos:
                continue
            vistos.add(clave)
            grupos[clave].append((c["persona"], c["repeticion"], t))
    salida = []
    for (pant, paso, tipo, objetivo), casos in grupos.items():
        sev = max(t["severidad"] for _, _, t in casos)
        frec = len(casos) / por_pantalla[pant]
        evidencias = sorted({t["evidencia"] for _, _, t in casos if t["evidencia"]}, key=lambda e: (len(e), e))
        salida.append({"pantalla": pant, "paso": paso, "tipo": tipo, "objetivo": objetivo, "severidad": sev,
                       "frecuencia": round(frec, 3), "personas": len({p for p, _, _ in casos}),
                       "puntaje": round(frec * sev, 3),
                       "evidencia": evidencias[len(evidencias) // 2] if evidencias else ""})
    return sorted(salida, key=lambda x: (-x["puntaje"], -x["severidad"]))


# --- Lectura de resultados ---------------------------------------------------------------------------------------

def cargar(etiqueta: str, modo: str = "imagen") -> tuple[dict, dict]:
    base = RES / etiqueta
    manifiesto = json.loads((base / "pantallas.json").read_text())
    pantallas = {p["pantalla"]: p for p in manifiesto["pantallas"]}
    tareas = json.loads((AQUI / "tareas.json").read_text())
    por_sesion = defaultdict(list)
    fallidas = 0
    archivo = base / f"respuestas-{modo}.jsonl"
    for linea in archivo.read_text().splitlines() if archivo.exists() else []:
        reg = json.loads(linea)
        if "respuesta" not in reg:
            fallidas += 1
            continue
        por_sesion[reg["sesion"]].append(codificar(reg, pantallas[reg["pantalla"]], manifiesto["oraculos"], tareas,
                                                     manifiesto.get("capturado_lima")))
    return manifiesto, {"por_sesion": dict(por_sesion), "fallidas": fallidas, "tareas": tareas}


def analizar(etiqueta: str, modo: str = "imagen") -> dict:
    manifiesto, d = cargar(etiqueta, modo)
    todas = [c for cs in d["por_sesion"].values() for c in cs]
    return {
        "etiqueta": etiqueta,
        "modo": modo,
        "capturado_lima": manifiesto["capturado_lima"],
        "sesiones_validas": len(todas),
        "sesiones_fallidas": d["fallidas"],
        "por_pantalla": {s: medidas_pantalla(cs, d["tareas"]) for s, cs in sorted(d["por_sesion"].items())},
        "embudos_tareas": embudos_tareas(d["por_sesion"]),
        "tropiezos": agrupar_tropiezos(todas, minimo=1),
        "codigos": d["por_sesion"],
    }


# --- Informe -----------------------------------------------------------------------------------------------------

ZONAS = {
    "cuando": "controles de fecha y hora", "#navPantallas": "navegación (Ahora · Confianza · Detalle)",
    "regimen": "chip de El Niño", "#ahBueno": "«¿Qué tan bueno es?»", "titulo": "título",
    "#ahOrigen": "«De dónde sale» (pie)", "respuesta": "respuesta a la pregunta", "#ahCifras": "tarjetas de cifras",
    "#ahAyer": "«Lo que dijimos ayer»", "dijimos_ayer": "«Lo que dijimos ayer»", "#ahLeyenda": "leyenda del gráfico",
    "grafico": "gráfico", "cifra_ahora": "cifra de ahora", "areas": "selector de área", "modo": "párrafo de modo",
    "otras_cifras": "otras cifras", "pico_24h": "pico", "linea_ahora": "línea de «ahora»", "que_es": "marca",
    "estado_datos": "estado de los datos", "#ahAviso": "aviso", "lead": "párrafo de entrada",
    "cobertura": "cobertura", "#cfStats": "cifras de Confianza", "#cfCob": "cobertura", "#cfVivo": "en vivo",
    "#cfDia": "error por día", "titular": "titular", "aviso_vivo": "aviso en vivo", "mes_a_mes": "error mes a mes",
    "selectores": "selectores", "#cfMes": "error mes a mes", "#cfRegimen": "error por régimen",
    "#ahDespuesCampo": "«Mostrar lo que pasó después»", "#ahRespuesta": "respuesta a la pregunta",
    "panel_controles": "panel de controles de «Detalle»", "#panel-escenarios": "panel de escenarios",
    "no ubicada": "no ubicada",
}


def legible(zona: str) -> str:
    return ZONAS.get(zona, zona)


def pct(m: dict | None) -> str:
    if not m or m.get("media") is None:
        return "—"
    if m["min"] == m["max"]:
        return f"{100 * m['media']:.0f} %"
    return f"{100 * m['media']:.0f} % ({100 * m['min']:.0f}–{100 * m['max']:.0f})"


def num(m: dict | None) -> str:
    if not m or m.get("media") is None:
        return "—"
    return f"{m['media']:.1f} ({m['min']:.1f}–{m['max']:.1f})"


def informe(a: dict) -> str:
    lineas = [f"# Playtest sintético: {a['etiqueta']} ({a['modo']})", "",
              (f"Capturas de {a['capturado_lima']} (Lima). Sesiones válidas: {a['sesiones_validas']}; "
               f"fallidas: {a['sesiones_fallidas']}. Entre paréntesis, el rango entre repeticiones (cada una "
               "sobre las cinco personas): es el ruido del evaluador."), ""]
    entradas = {s: m for s, m in a["por_pantalla"].items() if "primer_clic" in m}
    if entradas:
        lineas += ["## Primera apertura", "", "| Medida | " + " | ".join(entradas) + " |",
                   "|---|" + "---|" * len(entradas)]
        filas = [("Dice qué es", lambda m: pct(m["comprende"])),
                 ("Sabe qué momento muestra", lambda m: pct(m["momento_ok"])),
                 ("Lee la cifra del momento", lambda m: pct(m["lectura_cifra"])),
                 ("Lee cifra, pronóstico y rango", lambda m: pct(m["lectura_completa"])),
                 ("Lo primero que mira es la cifra o la respuesta", lambda m: pct(m["mira_primero_cifra"])),
                 ("Primer clic acertado (media de 4 tareas)", lambda m: pct(m["primer_clic_medio"]))]
        filas += [(f"…{t}", lambda m, t=t: pct(m["primer_clic"][t])) for t in ("t1", "t2", "t3", "t4")]
        filas += [("Dudas por sesión", lambda m: num(m["dudas_por_sesion"])),
                  ("Marcadores de confusión en la voz alta", lambda m: num(m["confusion_por_sesion"])),
                  ("Términos no entendidos por sesión", lambda m: num(m["terminos_por_sesion"])),
                  ("Volvería mañana (sí o tal vez)", lambda m: pct(m["volveria_si_o_tal_vez"]))]
        for nombre, f in filas:
            lineas.append(f"| {nombre} | " + " | ".join(f(m) for m in entradas.values()) + " |")
        for s, m in entradas.items():
            pasos = " → ".join(f"{p['paso']} {p['quedan']}/{p['de']}" for p in m["embudo"])
            lineas += ["", f"**Embudo, {s}:** {pasos}.",
                       f"Términos más citados: {', '.join(f'{t} ({100 * f:.0f} %)' for t, f in m['terminos_top'][:6])}.",
                       f"Dudas por zona: {', '.join(f'{legible(z)} ({n})' for z, n in m['dudas_zonas'])}.",
                       f"Mira primero: {', '.join(f'{legible(z)} ({n})' for z, n in m['mira_primero'])}.",
                       f"Le importó: {', '.join(f'{k} ({100 * f:.0f} %)' for k, f in m['importo'])}.",
                       f"Acuerdo entre repeticiones: {m['acuerdo_entre_repeticiones']}."]
    pasos = {s: m for s, m in a["por_pantalla"].items() if "primer_clic" not in m}
    if pasos:
        lineas += ["", "## Pasos siguientes", "", "| Pantalla | Medida | Valor | Dudas / sesión | Términos / sesión |",
                   "|---|---|---|---|---|"]
        for s, m in pasos.items():
            for clave in ("t2_ok", "t4_ok", "t3_clic_ok", "t3_lectura_ok"):
                if clave in m:
                    lineas.append(f"| {s} | {clave} | {pct(m[clave])} | {num(m['dudas_por_sesion'])} | "
                                  f"{num(m['terminos_por_sesion'])} |")
    lineas += ["", "## Embudos de las tareas (corridas sin tropezar en ningún paso)", ""]
    for t, filas in a["embudos_tareas"].items():
        lineas.append(f"- **{t}**: " + " → ".join(f"{f['paso']} {f['quedan']}/{f['de']}" for f in filas))
    lineas += ["", "## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)", "",
               "| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |",
               "|---|---|---|---|---|---|---|---|"]
    for t in a["tropiezos"][:20]:
        lineas.append(f"| {t['pantalla']} | {t['paso']} | {t['tipo']} | {legible(t['objetivo'])[:40]} | {t['severidad']} | "
                      f"{100 * t['frecuencia']:.0f} % | {t['personas']} | {t['evidencia'][:160]} |")
    return "\n".join(lineas) + "\n"


def comparar(a: dict, b: dict) -> str:
    """Antes (a) y después (b): cada medida con su rango entre repeticiones; la diferencia cuenta si no se solapan."""
    def fila(nombre, ma, mb, es_pct=True):
        if not ma or not mb or ma.get("media") is None or mb.get("media") is None:
            return None
        f = pct if es_pct else num
        delta = mb["media"] - ma["media"]
        solapan = not (mb["min"] > ma["max"] or mb["max"] < ma["min"])
        d = f"{100 * delta:+.0f} pts" if es_pct else f"{delta:+.1f}"
        if min(ma.get("reps", 0), mb.get("reps", 0)) < 2:
            veredicto = "sin repeticiones"
        elif abs(delta) < 1e-9:
            veredicto = "igual"
        else:
            veredicto = "dentro del ruido" if solapan else "**supera el ruido**"
        return f"| {nombre} | {f(ma)} | {f(mb)} | {d} | {veredicto} |"

    lineas = [f"# Playtest sintético: {a['etiqueta']} → {b['etiqueta']}", "",
              (f"Capturas: {a['capturado_lima']} y {b['capturado_lima']}. Sesiones válidas: "
               f"{a['sesiones_validas']} y {b['sesiones_validas']}. Entre paréntesis, el rango entre las "
               "repeticiones; una diferencia **supera el ruido** solo si los dos rangos no se solapan."), "",
              "| Medida | Antes | Después | Δ | ¿Ruido? |", "|---|---|---|---|---|"]
    for s in a["por_pantalla"]:
        ma, mb = a["por_pantalla"][s], b["por_pantalla"].get(s)
        if not mb:
            continue
        candidatas = []
        if "primer_clic" in ma:
            candidatas = [("dice qué es", ma["comprende"], mb["comprende"], True),
                          ("sabe qué momento muestra", ma["momento_ok"], mb["momento_ok"], True),
                          ("lee la cifra del momento", ma["lectura_cifra"], mb["lectura_cifra"], True),
                          ("lee cifra, pronóstico y rango", ma["lectura_completa"], mb["lectura_completa"], True),
                          ("lo primero que mira es la cifra o la respuesta", ma["mira_primero_cifra"],
                           mb["mira_primero_cifra"], True),
                          ("primer clic (media)", ma["primer_clic_medio"], mb["primer_clic_medio"], True)]
            candidatas += [(f"primer clic {t}", ma["primer_clic"][t], mb["primer_clic"][t], True)
                           for t in ("t1", "t2", "t3", "t4")]
            candidatas += [("volvería (sí o tal vez)", ma["volveria_si_o_tal_vez"], mb["volveria_si_o_tal_vez"],
                            True)]
        for clave in ("t2_ok", "t4_ok", "t3_clic_ok", "t3_lectura_ok"):
            if clave in ma:
                candidatas.append((clave, ma[clave], mb.get(clave), True))
        candidatas += [("dudas por sesión", ma["dudas_por_sesion"], mb["dudas_por_sesion"], False),
                       ("marcadores de confusión", ma["confusion_por_sesion"], mb["confusion_por_sesion"], False),
                       ("términos no entendidos por sesión", ma["terminos_por_sesion"], mb["terminos_por_sesion"],
                        False)]
        for nombre, x, y, es_pct in candidatas:
            f = fila(f"{s}: {nombre}", x, y, es_pct)
            if f:
                lineas.append(f)
    lineas += ["", "## Embudos de las tareas (corridas sin tropezar)", "", "| Tarea | Antes | Después |",
               "|---|---|---|"]
    for t in a["embudos_tareas"]:
        fa, fb = a["embudos_tareas"][t][-1], b["embudos_tareas"][t][-1]
        lineas.append(f"| {t} | {fa['quedan']}/{fa['de']} | {fb['quedan']}/{fb['de']} |")
    return "\n".join(lineas) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("etiquetas", nargs="+", help="una etiqueta, o dos para comparar (antes después)")
    ap.add_argument("--modo", default="imagen", help="la corrida (respuestas-<modo>.jsonl): imagen, texto o imagen-argon")
    a = ap.parse_args()
    analisis = []
    for e in a.etiquetas:
        r = analizar(e, a.modo)
        sufijo = "" if a.modo == "imagen" else f"-{a.modo}"
        (RES / e / f"analisis{sufijo}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1))
        (RES / e / f"analisis{sufijo}.md").write_text(informe(r))
        analisis.append(r)
        print(f"{e}: {r['sesiones_validas']} sesiones válidas, {r['sesiones_fallidas']} fallidas")
    if len(analisis) == 2:
        sufijo = "" if a.modo == "imagen" else f"-{a.modo}"
        destino = RES / f"comparacion-{a.etiquetas[0]}-{a.etiquetas[1]}{sufijo}.md"
        destino.write_text(comparar(*analisis))
        print(f"Comparación: {destino}")


if __name__ == "__main__":
    main()
