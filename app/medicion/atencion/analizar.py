"""Analiza las capturas de `capturar.mjs`: atención predicha por AOI, métricas baratas y la primera apertura.

    uv run --no-sync python app/medicion/atencion/analizar.py --etiqueta base [--comparar base-r2]

Lee   app/medicion/resultados/tmp/atencion/<etiqueta>/  (capturas y capturas.json)
Escribe app/medicion/resultados/atencion/<etiqueta>.json y .md, y los mapas superpuestos en el directorio tmp.

La atención es sintética: un lector de saliencia de visión libre entrenado con miradas de UEyes. Predice los primeros
vistazos (1, 3 y 7 s), no la búsqueda dirigida por una tarea, y no reemplaza a personas.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from saliencia import DIR_MODELO, Dinov2, cabeza, leer_safetensors, remuestrear, ruta_backbone

RAIZ = Path(__file__).resolve().parents[1]
DURACIONES = ("1s", "3s", "7s")
GENERICAS = ("fijo", "controles", "texto")

# ---------- términos: cuándo aparece y qué frase lo explica en la misma pantalla ----------
TERMINOS = [
    ("SEIN", r"\bSEIN\b", r"Sistema Eléctrico Interconectado"),
    ("COES", r"\bCOES\b", r"Comité de Operación|operador del sistema"),
    ("MW", r"\bMW\b", r"megavatio"),
    ("ICEN", r"\bICEN\b", r"[Íí]ndice [Cc]ostero"),
    ("El Niño costero", r"El Niño costero", r"temperatura del mar|calentamiento del mar|anomalía"),
    ("rango del N %", r"[Rr]ango", r"\d+ de cada 10|cae aquí"),
    ("referencia", r"[Rr]eferencia", r"repetir|si se repitiera|lo mismo que"),
    ("umbral (de rampa)", r"\bumbral\b", r"umbral[^.]{0,60}(percentil|se considera|cuando)"),
    ("(pron.)", r"\(pron\.\)", r"pron\. = pronóstico"),
    ("repaso", r"\b[Rr]epas(o|ar)\b", r"Repaso de un día del historial|así se veía"),
    ("reconstruido", r"\breconstruid[oa]\b", r"reconstruid[oa][^.]{0,120}(se calculó|después|con los datos)"),
    ("en vivo", r"\b[Ee]n vivo\b", r"en vivo[^.]{0,80}(cada mañana|antes de conocerse|emitido)"),
    ("MAPE", r"\bMAPE\b", r"% de la demanda \(MAPE\)|error porcentual"),
    ("WAPE", r"\bWAPE\b", r"ponderado"),
    ("cobertura", r"[Cc]obertura", r"cayó dentro del rango|cae dentro del rango"),
    ("error medio", r"[Ee]rror medio", r"absoluto|menos es mejor|en promedio"),
    ("sesgo", r"\b[Ss]esgo\b", r"(sobre|sub)estim"),
    ("IEOD", r"\bIEOD\b", r"Informe de Evaluación"),
    ("Chronos-2", r"Chronos", r"modelo fundacional"),
    ("combinado", r"\b[Cc]ombinado\b", r"mezcla|ponderad|× \d"),
    ("horizonte / anticipación", r"\b(horizonte|anticipación)\b", r"con cuánta anticipación"),
]

# ---------- vocabulario: el mismo concepto con nombres distintos entre pantallas ----------
CONCEPTOS = {
    "el pronóstico": {"Pronóstico": r"\bPronóstico\b", "Modelo": r"^Modelo$"},
    "el rango": {"Rango del N %": r"Rango del \d+ %", "Rango probable": r"Rango probable", "rango (a secas)": r"^rango \d|· rango"},
    "la referencia": {"Referencia (…)": r"Referencia \(", "Referencia: …": r"Referencia: ", "referencia simple": r"referencia simple"},
    "el máximo del día": {"Pico de hoy": r"Pico de hoy", "Pico de las próximas 24 h": r"Pico de las próximas 24 h", "Pico 24 h": r"Pico 24 h",
                          "Máximo": r"Máximo"},
    "el error": {"Error medio": r"Error medio", "MAE": r"\bMAE\b", "Error a esa hora": r"Error a esa hora", "Diferencia": r"^Diferencia$"},
}

# ---------- prueba de 5 segundos (sintética): qué se puede responder con lo que hay a la vista ----------
PREGUNTAS_5S = [
    ("¿Qué es esto?", ["que_es"], r"(?i)demanda|pron[oó]stic"),
    ("¿De qué zona habla?", ["titulo"], r"Norte|Centro|Sur"),
    ("¿Cuánta demanda hay ahora?", ["cifra_ahora"], r"\d"),
    ("¿Es real o pronóstico, y hasta cuándo hay datos?", ["estado_datos", "modo"], r"COES|[Rr]eal"),
    ("¿Viene más o menos demanda?", ["grafico", "pico_24h"], None),
]
UMBRAL_5S = 0.05  # cuota de atención a 7 s que se exige a la respuesta (fijado antes de medir)

# ---------- prueba de primer clic (sintética): olor de la información + atención ----------
TAREAS_CLIC = [
    ("T1 pronóstico de un día pasado (10-mar, 19:00)", "pronóstico día fecha pasado historial marzo hora calendario", r"(?i)^repasar|^ahFecha$"),
    ("T2 ¿me puedo fiar del número?", "fiar confianza confiable bueno error acierta precisión", r"^Confianza$|confianza mes a mes|Diagnóstico"),
    ("T3 ¿y si hace 2 °C más?", "calor temperatura grados escenario clima", r"más calor|^Detalle$|¿Y si"),
    ("T4 ¿con qué fase de El Niño yerra más?", "niño fase error equivoca fenómeno", r"^Confianza$|Diagnóstico"),
    ("T5 ver la demanda del Sur", "sur", r"\bSur\b"),
    ("T6 descargar los datos", "descargar datos csv exportar tabla", r"CSV|tabla"),
]
VACIAS = {"del", "las", "los", "una", "uno", "para", "por", "con", "que", "más", "mas", "hace", "ver", "hoy"}


def sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def raices(t: str) -> set[str]:
    return {sin_acentos(w)[:5] for w in re.findall(r"[a-záéíóúñü]+", t.lower()) if len(w) >= 3 and w not in VACIAS}


def mascara(cajas, ancho, alto):
    m = np.zeros((alto, ancho), bool)
    for x0, y0, x1, y1 in cajas:  # recortadas a la ventana: una caja fuera (y1 < 0) no puede volverse un índice negativo
        m[max(0, y0):max(0, min(alto, y1)), max(0, x0):max(0, min(ancho, x1))] = True
    return m


def area_cajas(cajas):
    """Área de la unión de las cajas, también lo que queda fuera de la ventana."""
    if not cajas:
        return 0
    dx, dy = min(0, *(b[0] for b in cajas)), min(0, *(b[1] for b in cajas))
    movidas = [[x0 - dx, y0 - dy, x1 - dx, y1 - dy] for x0, y0, x1, y1 in cajas]
    return int(mascara(movidas, max(b[2] for b in movidas), max(b[3] for b in movidas)).sum())


def color_rgba(c: str):
    m = re.match(r"rgba?\((\d+), (\d+), (\d+)(?:, ([\d.]+))?\)", c)
    if not m:
        return None
    return (int(m[1]), int(m[2]), int(m[3]), round(float(m[4]) if m[4] else 1.0, 2))


def cifras(texto: str) -> dict[str, int]:
    horas = re.findall(r"\b\d{1,2}:\d{2}\b", texto)
    fechas = re.findall(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", texto)
    resto = re.sub(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", " ", texto)
    magnitudes = re.findall(r"[+−-]?\d[\d,]*(?:\.\d+)?", resto)
    return {"magnitudes": len(magnitudes), "horas": len(horas), "fechas": len(fechas)}


class Analizador:
    def __init__(self):
        self.vit = Dinov2(leer_safetensors(ruta_backbone()))
        self.cabezas = {}
        for d in DURACIONES:
            z = np.load(DIR_MODELO / f"cabeza_ueyes_{d}.npz")
            self.cabezas[d] = {k: z[k].astype(np.float32) for k in z.files}

    def mapas(self, im: Image.Image) -> dict[str, np.ndarray]:
        f = self.vit.rasgos(im)
        out = {}
        for d, w in self.cabezas.items():
            m = np.clip(remuestrear(np.exp(cabeza(f, w)), im.size[1], im.size[0]), 0, None)
            out[d] = m / m.sum()
        return out


def atribuir(c, ancho, alto):
    """Máscaras exclusivas por prioridad: AOI de la pantalla, luego barras fijas, controles y texto."""
    fijos = [mascara([f["caja"]], ancho, alto) for f in c["fijos"]]
    crudas = {}
    for n in c["aoi_orden"]:
        a = c["aoi"].get(n, {"cajas": [], "tapan": []})
        m = mascara(a["cajas"], ancho, alto)
        for i in a["tapan"]:
            m &= ~fijos[i]
        crudas[n] = m
    crudas["fijo"] = np.logical_or.reduce(fijos) if fijos else np.zeros((alto, ancho), bool)
    crudas["controles"] = mascara([x["caja"] for x in c["interactivos"]], ancho, alto)
    crudas["texto"] = mascara([x["caja"] for x in c["textos"]], ancho, alto)
    tomado = np.zeros((alto, ancho), bool)
    exclusivas = {}
    for n, m in crudas.items():
        exclusivas[n] = m & ~tomado
        tomado |= m
    exclusivas["resto"] = ~tomado
    return crudas, exclusivas


def superponer(im, sal, c, exclusivas, cuotas, ruta):
    base = np.asarray(im.convert("RGB"), np.float32)
    hm = sal / sal.max()
    ov = base * 0.42
    ov[..., 0] += 255 * hm * 0.95
    ov[..., 1] += 190 * hm**1.5 * 0.8
    out = Image.fromarray(np.clip(ov, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(out)
    try:
        fuente = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    except OSError:
        fuente = ImageFont.load_default()
    for n in c["aoi_orden"]:
        cajas = [b for b in c["aoi"].get(n, {}).get("cajas", []) if b[1] < im.size[1] and b[3] > 0]
        if not cajas or not exclusivas[n].any():
            continue
        x0, y0 = min(b[0] for b in cajas), min(b[1] for b in cajas)
        x1, y1 = max(b[2] for b in cajas), max(b[3] for b in cajas)
        d.rectangle([x0, y0, x1, y1], outline=(80, 220, 255), width=2)
        rotulo = f"{n} {100 * cuotas[n]:.1f}%"
        ty = max(0, y0 - 15)
        d.rectangle([x0, ty, x0 + 8 * len(rotulo), ty + 15], fill=(10, 30, 40))
        d.text((x0 + 3, ty), rotulo, fill=(120, 230, 255), font=fuente)
    out.save(ruta, quality=80)


def analizar_captura(c, im, mapas, dir_mapas):
    alto, ancho = im.size[1], im.size[0]
    crudas, exclusivas = atribuir(c, ancho, alto)
    r = {"atencion": {}, "aoi": {}}
    for d, sal in mapas.items():
        r["atencion"][d] = {}
        for n, m in exclusivas.items():
            masa, area = float(sal[m].sum()), float(m.mean())
            r["atencion"][d][n] = {"cuota": round(masa, 4), "area": round(area, 4), "lift": round(masa / area, 2) if area > 0 else None}
    for n in c["aoi_orden"]:
        a = c["aoi"].get(n, {"cajas": [], "existe": False})
        total = area_cajas(a["cajas"])
        r["aoi"][n] = {"existe": a["existe"], "a_la_vista": round(float(crudas[n].sum()) / total, 3) if total else 0.0,
                       "arriba_px": min((b[1] for b in a["cajas"]), default=None)}
    for d, sal in mapas.items():  # el de 3 s sin sufijo (láminas y PR); los otros, para comparar.py --duracion
        sufijo = "" if d == "3s" else f"-{d}"
        superponer(im, sal, c, exclusivas, {k: v["cuota"] for k, v in r["atencion"][d].items()}, dir_mapas / f"{c['nombre']}{sufijo}.jpg")

    # Lo que compite en la primera pantalla
    vis = [t for t in c["textos"] if t["visible"]]
    texto_vis = " ".join(t["t"] for t in vis)
    texto_todo = " ".join(t["t"] for t in c["textos"])
    ayudas = " ".join(t["ayuda"] for t in c["textos"] if t["ayuda"])
    k = cifras(" ".join(t["t"] for t in vis if not t["svg"]))
    k["en_el_grafico"] = sum(cifras(t["t"])["magnitudes"] for t in vis if t["svg"])
    controles = [x for x in c["interactivos"] if x["visible"]]
    r["primera_pantalla"] = {
        "controles": len(controles),
        "controles_lista": [x["etiqueta"][:40] for x in controles],
        "cifras": k,
        "palabras": len(re.findall(r"\w+", texto_vis)),
        "pantallas_de_alto": round(c["doc"]["alto"] / c["vp"]["alto"], 2),
    }
    terminos = []
    for nombre, aparece, define in TERMINOS:
        if re.search(aparece, texto_vis):
            definido = bool(re.search(define, texto_todo) or re.search(define, ayudas))
            terminos.append({"termino": nombre, "definido_en_pantalla": definido,
                             "definido_a_la_vista": bool(re.search(define, texto_vis))})
    r["terminos"] = terminos

    sal7, sal3 = mapas["7s"], mapas["3s"]
    if all(n in c["aoi"] for n in ("cifra_ahora", "que_es")):
        preguntas = []
        for q, aois, rx in PREGUNTAS_5S:
            m = np.logical_or.reduce([exclusivas[n] for n in aois])
            cajas = [b for n in aois for b in c["aoi"][n]["cajas"]]
            dentro = [t["t"] for t in vis if any(b[0] - 2 <= (t["caja"][0] + t["caja"][2]) / 2 <= b[2] + 2 and b[1] - 2 <= (t["caja"][1] + t["caja"][3]) / 2 <= b[3] + 2 for b in cajas)]
            a_la_vista = bool(m.any()) and (rx is None or bool(re.search(rx, " ".join(dentro))))
            cuota = float(sal7[m].sum())
            preguntas.append({"pregunta": q, "a_la_vista": a_la_vista, "cuota_7s": round(cuota, 3), "responde": a_la_vista and cuota >= UMBRAL_5S})
        # ¿Qué puedo hacer aquí? Un control fuera de la cabecera y la barra, que se mire más que su tamaño.
        cab = [f["caja"] for f in c["fijos"]] + [[0, 0, ancho, 64]]
        def en_cabecera(b):
            cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            return any(x0 <= cx <= x1 and y0 <= cy <= y1 for x0, y0, x1, y1 in cab)
        cuota_control = {}
        for i, x in enumerate(controles):
            m = mascara([x["caja"]], ancho, alto)
            cuota_control[i] = (float(sal3[m].sum()), float(m.mean()))
        mejores = [(a, a / ar, x["etiqueta"][:40], en_cabecera(x["caja"]))
                   for x, (a, ar) in zip(controles, cuota_control.values(), strict=True) if ar > 0]
        mejores.sort(reverse=True)
        propios = [b for b in mejores if not b[3]]
        preguntas.append({"pregunta": "¿Qué puedo hacer aquí?", "a_la_vista": bool(propios),
                          "cuota_7s": round(propios[0][0], 3) if propios else 0.0,
                          "responde": bool(propios) and propios[0][1] >= 1.0,
                          "control_mas_mirado": propios[0][2] if propios else None})
        r["prueba_5s"] = preguntas
        r["controles_mas_mirados"] = [{"control": e, "cuota_3s": round(a, 3), "lift": round(lf, 2)} for a, lf, e, _ in mejores[:5]]
        clics = []
        for tarea, palabras, correcto in TAREAS_CLIC:
            kw = raices(palabras)
            filas = []
            for i, x in enumerate(controles):
                olor = len(kw & raices(f"{x['etiqueta']} {x['grupo']}"))
                filas.append((olor, cuota_control[i][0], x))
            filas.sort(key=lambda f: (f[0], f[1]), reverse=True)
            ok = [f for f in filas if re.search(correcto, f[2]["etiqueta"]) or re.search(correcto, f[2]["id"])]
            pred = filas[0] if filas else None
            clics.append({"tarea": tarea, "predicho": pred[2]["etiqueta"][:40] if pred else None, "por": ("palabras" if pred and pred[0] else "atención"),
                          "acierta": bool(pred and ok and pred[2] is ok[0][2]), "destino_a_la_vista": bool(ok),
                          "destino_olor": ok[0][0] if ok else 0})
        r["primer_clic"] = clics

    # Métricas baratas
    multi = [x for x in c["lineas"]]
    r["lectura"] = {"bloques": len(multi), "ch_linea_mediana": statistics.median([x["ch"] for x in multi]) if multi else None,
                    "ch_linea_max": max((x["ch"] for x in multi), default=None),
                    "sobre_80": [f"{x['sel']} {x['ch']}" for x in multi if x["ch"] > 80],
                    "bajo_25": [f"{x['sel']} {x['ch']}" for x in multi if x["ch"] < 25]}
    tokens = {color_rgba(v) for v in c["colores"]["tokens"].values()} - {None}
    fuera, mezclas = {}, {}
    for u in c["colores"]["usados"]:
        rgba = color_rgba(u["color"])
        if rgba is None:
            mezclas[u["color"]] = u["ejemplo"]
            continue
        if any(abs(rgba[0] - t[0]) <= 1 and abs(rgba[1] - t[1]) <= 1 and abs(rgba[2] - t[2]) <= 1 and abs(rgba[3] - t[3]) <= 0.02 for t in tokens):
            continue
        fuera.setdefault(u["color"], []).append(f"{u['prop']}:{u['ejemplo']}")
    r["color"] = {"tokens": len(tokens), "usados": len({u["color"] for u in c["colores"]["usados"]}), "fuera_del_sistema": {k: v[:3] for k, v in fuera.items()},
                  "mezclas_derivadas": len(mezclas)}
    tam = {float(k): v for k, v in c["tipografia"]["tamanos"].items()}
    r["tipografia"] = {"tamanos": sorted(tam), "n_tamanos": len(tam), "familias": c["tipografia"]["familias"]}
    r["desborde"] = {"horizontal_px": c["desborde"]["horizontal_px"], "elementos": c["desborde"]["elementos"][:5]}
    r["orientacion"] = {"pantalla_marcada": [x["etiqueta"] for x in c["interactivos"] if x["actual"] == "page" and x["visible"]],
                        "estado_datos": c["modo"]}
    return r


def laminas(capturas, dir_mapas, destino: Path, alto=430):
    """Una lámina por pantalla y tema con los cuatro viewports lado a lado (para el documento y los PR)."""
    destino.mkdir(parents=True, exist_ok=True)
    try:
        fuente = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except OSError:
        fuente = ImageFont.load_default()
    grupos = {}
    for c in capturas:
        grupos.setdefault((c["pantalla"], c["tema"]), []).append(c)
    for (pantalla, tema), cs in grupos.items():
        ims = []
        for c in cs:
            im = Image.open(dir_mapas / f"{c['nombre']}.jpg")
            ims.append((c["vista"], im.resize((round(im.width * alto / im.height), alto), Image.LANCZOS)))
        hoja = Image.new("RGB", (sum(i.width for _, i in ims) + 12 * (len(ims) - 1), alto + 28), (24, 26, 26))
        d = ImageDraw.Draw(hoja)
        x = 0
        for vista, im in ims:
            hoja.paste(im, (x, 28))
            d.text((x + 6, 5), f"{pantalla} · {vista} · atención 3 s", fill=(120, 230, 255), font=fuente)
            x += im.width + 12
        nombre = f"atencion-{pantalla}-{'claro' if tema == 'light' else 'oscuro'}.jpg"
        hoja.save(destino / nombre, quality=70, optimize=True)


def jaccard(a, b):
    a, b = set(a), set(b)
    return round(len(a & b) / len(a | b), 2) if a | b else None


def consistencia(capturas):
    out = {}
    por = {}
    for c in capturas:
        por.setdefault((c["vista"], c["tema"]), {})[c["pantalla"]] = c
    for (vista, tema), ps in por.items():
        fila = {}
        for a, b in (("ahora", "confianza"), ("ahora", "detalle"), ("confianza", "detalle")):
            if a in ps and b in ps:
                fa = {t["fs"] for t in ps[a]["textos"]}
                fb = {t["fs"] for t in ps[b]["textos"]}
                ca = {u["color"] for u in ps[a]["colores"]["usados"]}
                cb = {u["color"] for u in ps[b]["colores"]["usados"]}
                fila[f"{a}~{b}"] = {"tamanos": jaccard(fa, fb), "colores": jaccard(ca, cb)}
        out[f"{vista}-{tema}"] = fila
    return out


def vocabulario(capturas):
    """Qué nombre recibe cada concepto en cada pantalla (escritorio, claro), en todo el texto de la pantalla."""
    out = {}
    for c in capturas:
        if c["vista"] != "escritorio" or c["tema"] != "light":
            continue
        textos = [t["t"] for t in c["textos"]]
        out[c["pantalla"]] = {k: sorted(n for n, rx in v.items() if any(re.search(rx, t) for t in textos)) for k, v in CONCEPTOS.items()}
    return out


def tabla_md(res, capturas):
    L = [f"# Auditoría de atención: {res['etiqueta']}", "", f"Lector UEyes (3 s): {res['modelo']}", ""]
    for pantalla in dict.fromkeys(c["pantalla"] for c in capturas):
        cs = [c for c in capturas if c["pantalla"] == pantalla]
        aois = cs[0]["aoi_orden"] + list(GENERICAS) + ["resto"]
        L += [f"## {pantalla}", "", "Cuota de la atención predicha a 3 s (lift = cuota ÷ área; «—» = fuera de la vista).", "",
              "| vista · tema | " + " | ".join(aois) + " |", "|---|" + "---|" * len(aois)]
        for c in cs:
            a = res["capturas"][c["nombre"]]["atencion"]["3s"]
            celdas = [f"{100 * a[n]['cuota']:.1f} ({a[n]['lift']})" if a[n]["area"] > 0 else "—" for n in aois]
            L.append(f"| {c['vista']} · {c['tema']} | " + " | ".join(celdas) + " |")
        L.append("")
    L += ["## Métricas baratas", "", "| captura | pantallas de alto | controles a la vista | cifras a la vista (magnitudes / en el gráfico) | términos sin definir a la vista | ch/línea mediana (máx) | bloques > 80 ch | colores fuera del sistema | tamaños de letra | desborde horizontal |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for c in capturas:
        x = res["capturas"][c["nombre"]]
        p = x["primera_pantalla"]
        sin = [t["termino"] for t in x["terminos"] if not t["definido_a_la_vista"]]
        L.append(f"| {c['nombre']} | {p['pantallas_de_alto']} | {p['controles']} | {p['cifras']['magnitudes']} / {p['cifras']['en_el_grafico']} | {len(sin)} | "
                 f"{x['lectura']['ch_linea_mediana']} ({x['lectura']['ch_linea_max']}) | {len(x['lectura']['sobre_80'])} | {len(x['color']['fuera_del_sistema'])} | {x['tipografia']['n_tamanos']} | {x['desborde']['horizontal_px']} |")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--etiqueta", default="base")
    ap.add_argument("--comparar", default=None, help="otra etiqueta del mismo build, para estimar el ruido")
    ap.add_argument("--laminas", default=None, help="carpeta donde dejar una lámina por pantalla y tema")
    a = ap.parse_args()
    dir_tmp = RAIZ / "resultados" / "tmp" / "atencion" / a.etiqueta
    datos = json.loads((dir_tmp / "capturas.json").read_text())
    capturas = datos["capturas"]
    for c in capturas:  # una AOI no puede llamarse como una categoría genérica
        for n in [n for n in c["aoi_orden"] if n in (*GENERICAS, "resto")]:
            c["aoi_orden"][c["aoi_orden"].index(n)] = f"panel_{n}"
            c["aoi"][f"panel_{n}"] = c["aoi"].pop(n)
    dir_mapas = dir_tmp / "mapas"
    dir_mapas.mkdir(exist_ok=True)
    met = json.loads((DIR_MODELO / "metricas.json").read_text())
    res = {"etiqueta": a.etiqueta, "fecha_capturas": datos["fecha"],
           "modelo": f"CC {met['3s']['lector']['todo']['cc']} en el test oficial de UEyes (sesgo central {met['3s']['sesgo_central']['todo']['cc']})",
           "capturas": {}}
    an = Analizador()
    for c in capturas:
        im = Image.open(dir_tmp / f"{c['nombre']}.png").convert("RGB")
        res["capturas"][c["nombre"]] = analizar_captura(c, im, an.mapas(im), dir_mapas)
        print(c["nombre"], {k: v["cuota"] for k, v in res["capturas"][c["nombre"]]["atencion"]["3s"].items()}, flush=True)
    res["consistencia"] = consistencia(capturas)
    res["vocabulario"] = vocabulario(capturas)
    if a.laminas:
        laminas(capturas, dir_mapas, Path(a.laminas))
    if a.comparar:
        otra = json.loads((RAIZ / "resultados" / "atencion" / f"{a.comparar}.json").read_text())
        difs = [abs(v["cuota"] - otra["capturas"][n]["atencion"]["3s"][k]["cuota"])
                for n, x in res["capturas"].items() if n in otra["capturas"] for k, v in x["atencion"]["3s"].items()]
        res["ruido"] = {"contra": a.comparar, "dif_max": round(max(difs), 4), "dif_p95": round(float(np.percentile(difs, 95)), 4)}
    salida = RAIZ / "resultados" / "atencion"
    salida.mkdir(parents=True, exist_ok=True)
    (salida / f"{a.etiqueta}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
    (salida / f"{a.etiqueta}.md").write_text(tabla_md(res, capturas))
    print(f"Guardado en {salida / a.etiqueta}.json y .md")


if __name__ == "__main__":
    main()
