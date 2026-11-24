"""Datos del deck: lee las tablas que ya escribieron los notebooks y los experimentos, y escribe lo que el deck cita.

    TETOUAN_DATA=/ruta/a/los/datos uv run python docs/presentacion/slides/datos.py

Sin TETOUAN_DATA busca ./data y, si no está, la carpeta de datos del checkout principal. Escribe:

  datos.js            las series de los gráficos de D3 (js/graficos.js), en window.DATOS
  _deck.yml           las cifras del texto, que index.qmd lee con {{< meta deck.… >}}
  generado/*.md       las tablas del respaldo (hipótesis, ablación, adaptación, fundacionales)
  img/portada.svg     el fondo de la portada: la demanda media mensual del SEIN, 2016-2026

No recalcula ningún modelo ni redondea antes de tiempo: cada cifra sale de una tabla de reportes/ (o de la
capa silver de la demanda) y se formatea al final. Lo poco que solo está en el informe técnico (paper/paper.md)
va en DEL_INFORME, con su sección. Donde una cifra calculada aquí también está escrita en el informe, se
comprueba que coincida: si los notebooks cambian y el informe no, este script falla en vez de publicar dos
cifras distintas. Los cuatro archivos se versionan, así que el deck se renderiza sin los datos.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
RAIZ_REPO = AQUI.parents[2]  # docs/presentacion/slides → raíz del repo
AREAS = ["Norte", "Centro", "Sur"]
HORIZONTES = ["1h", "24h"]
MENOS = "−"  # signo menos tipográfico, como en el informe

# Lo que solo está en el informe técnico (paper/paper.md, versión del 19 de noviembre con el reanálisis del 23).
DEL_INFORME = {
    # §4.2, tabla de los tres casos
    "tetuan_registros": "52,416",
    "ceuta_intervalos": "391,975",
    # §4.2, «Qué se encontró en el SEIN»
    "pico_2016": "87",
    "pico_desde_2023": "25 y 33",
    "sur_domingo": f"{MENOS}0.6",
    "sur_r_temperatura": f"{MENOS}0.07",
    "fallas_activas": "91",
    "norte_2017": f"{MENOS}6 a {MENOS}7",
    "norte_2023": "+2 a 6",
    # §4.3, «El objetivo en razón» (Tetuán, validación de la Zona 1, mismo algoritmo sin ajustar)
    "tetuan_nivel_kw": "738.5",
    "tetuan_razon_kw": "613.4",
    "tetuan_ref_kw": "1,159.6",
    # §4.3, «Partición con hueco» (por área, a 1 hora)
    "periodos_entrenamiento": "154,791",
    "periodos_validacion": "17,518",
    "periodos_prueba": "13,920",
    # §5.3, «Algoritmos y elección» (mejora media frente a la mejor referencia, validación de 2025, M0 a 1 h)
    "val_rf": 43.2,
    "val_xgb": 42.9,
    "val_ridge": 26.4,
    # §5.3, «Las exógenas casi no aportan» (importancia por permutación en el Centro)
    "imp_demanda_mw": "248.0",
    "imp_clima_mw": "1.10",
    # §5.3, «Estable en el tiempo» (origen móvil 2023-2025)
    "movil_meses": "108",
    "movil_mediana": "44.6",
    # §3, «Por qué ahora» (IGP)
    "icen_setiembre": "4.50",
    # §7, lección 1
    "leccion_algoritmo_kw": "18",
    "leccion_objetivo_kw": "1,200",
}

# Peso en disco de cada modelo de la figura 16 del informe técnico (paper/figuras/fig5_peso_rendimiento.png,
# gráfico del 13-nov sobre las tablas del notebook 04), en MB y redondeado como se lee en su escala
# logarítmica. estimado=True: el archivo de pesos no se guardó y el peso es parámetros × 4 bytes (Simons 297M,
# Toto 313M, TimesFM 2.5 200M); t0-gamma, TimesFM 3.0 y TiRex-2 se leen de la figura. Chronos-2 y su ajuste
# fino pesan lo mismo (477.9 MB, el archivo model.safetensors del ajustado). El híbrido es Simons + su XGBoost y
# el combinado, el híbrido + Chronos-2 ajustado: heredan lo estimado de Simons.
PESOS = {
    "Random Forest por área (elegido)": ("Random Forest por área", "arbol", 1040, False),
    "xgb_base_c2048": ("XGBoost global", "arbol", 19, False),
    "chronos2_c2048": ("Chronos-2", "zeroshot", 478, False),
    "timestral_c2048": ("Timestral", "zeroshot", 840, False),
    "simons_c2048": ("Simons", "zeroshot", 1188, True),
    "toto2_c2048": ("Toto 2.0", "zeroshot", 1252, True),
    "t0_c2048": ("t0-gamma", "zeroshot", 1030, True),
    "timesfm25_c2048": ("TimesFM 2.5", "zeroshot", 800, True),
    "timesfm3_c2048": ("TimesFM 3.0", "zeroshot", 1330, True),
    "tirex2_c2048": ("TiRex-2", "zeroshot", 330, True),
    "chronos2ftcal_c2048": ("Chronos-2 ajustado", "ajustado", 478, False),
    "xgb_simons_c2048": ("Híbrido XGBoost + Simons", "hibrido", 1208, True),
    "combinacion_c2048": ("Combinado", "combinado", 1686, True),
}

# Filas de la tabla de fundacionales del respaldo, en el orden del informe (§5.5): archivo → nombre.
FILAS_FUNDACIONALES = [
    ("Random Forest por área (elegido)", "Random Forest elegido"),
    ("xgb_base_c2048", "XGBoost global base"),
    ("simons_c2048", "Simons-297M, sin entrenar"),
    ("timestral_c2048", "Timestral-209M, sin entrenar"),
    ("chronos2_c2048", "Chronos-2, sin entrenar"),
    ("chronos2ft_a_c2048", "Chronos-2 ajustado, sin covariables"),
    ("chronos2ftcal_c2048", "Chronos-2 ajustado con calendario"),
    ("timesfm25_c2048", "TimesFM 2.5, sin entrenar"),
    ("xgb_chronos2_c2048", "Híbrido: XGBoost + Chronos-2"),
    ("xgb_simons_c2048", "Híbrido: XGBoost + Simons"),
    ("combinacion_c2048", "**Combinado: Chronos-2 ajustado + híbrido (pesos de 2025)**"),
]

# Las hipótesis de 2026 con palabras de la exposición; el veredicto y la evidencia salen de hipotesis.csv.
HIPOTESIS = {
    "1a": "El modelo fijo le gana a la mejor referencia a 1 h en las tres áreas",
    "1b": "En el Norte, la mejora a 1 h baja respecto de 2025 (49 %), pero queda sobre 25 %",
    "1c": "A 24 h le gana en el Centro y el Norte",
    "2": "Reentrenar cada semana baja el error del Norte a 1 h, con un intervalo que no cruza el cero",
    "3": "Sumar todas las exógenas a 1 h no se distingue de cero en ninguna área",
    "4": "El clima ayuda a 24 h en el Centro",
    "5": "El Niño no mejora en ningún horizonte ni área",
}


# ------------------------------------------------------------------ formato
def dec(x: float, d: int = 1) -> str:
    """1 decimal, punto decimal y coma de miles, con el menos tipográfico (como el informe)."""
    texto = f"{x:,.{d}f}"
    return texto.replace("-", MENOS)


def con_signo(x: float, d: int = 2) -> str:
    return ("+" if x > 0 else "") + dec(x, d)


def miles(x: float) -> str:
    return dec(x, 0)


def ic(fila: pd.Series, columna: str = "Δ MAE (MW)") -> str:
    return f"{con_signo(fila[columna])} ({dec(fila['IC 95 % bajo'], 2)} a {dec(fila['IC 95 % alto'], 2)})"


def comprobar(nombre: str, calculado: float, en_el_informe: float, tolerancia: float = 0.051) -> None:
    if abs(calculado - en_el_informe) > tolerancia:
        raise SystemExit(f"{nombre}: la tabla da {calculado:.3f} y el informe dice {en_el_informe}. Revisar.")


# ------------------------------------------------------------------ dónde están los datos
def raiz_datos() -> Path:
    candidatas = [os.environ.get("TETOUAN_DATA"), RAIZ_REPO / "data",
                  RAIZ_REPO.parent / "tetouan-power-forecast" / "data"]
    for c in candidatas:
        if c and (Path(c) / "reportes" / "sein").is_dir():
            return Path(c)
    raise SystemExit("No encuentro la carpeta de datos: TETOUAN_DATA=/ruta/a/los/datos (ver docs/datos.md).")


# ------------------------------------------------------------------ (1) un día del Centro, como lo muestra Curva
def dia_centro(raiz: Path, fecha: str = "2026-08-27", hora: str = "19:00") -> dict:
    """El combinado a 24 horas para el Centro del día de la demo, con el rango del 90 % de la app.

    Rehace lo que hace app/backend/pronosticador_hibrido.py: el pronóstico emitido 24 horas antes
    (combinacion_c2048.parquet, una fila por origen) y el rango con los cuantiles 5 y 95 % de su error
    relativo en 2025. La capa silver del COES marca cada media hora por su final (19:30 es el periodo de
    19:00 a 19:30) y la app la rotula por su inicio: aquí, igual que la app.
    """
    demanda = pd.read_parquet(raiz / "coes" / "silver" / "demanda_areas.parquet").set_index("DateTime")["CENTRO"]
    comb = pd.read_parquet(raiz / "reportes" / "sein" / "fundacionales" / "combinacion_c2048.parquet")
    comb = comb[comb["area"] == "CENTRO"].set_index("DateTime").sort_index()
    paso = pd.Timedelta(hours=24)
    comb["fin"] = comb.index + paso
    comb["real"] = demanda.reindex(comb["fin"]).to_numpy()
    validacion = comb[(comb.index >= "2025-01-01") & (comb.index < pd.Timestamp("2026-01-01") - paso)]
    relativo = (validacion["real"] / validacion["pred_48"] - 1).dropna()
    q05, q95 = float(relativo.quantile(0.05)), float(relativo.quantile(0.95))
    inicio = pd.Timestamp(fecha)
    dia = comb[(comb["fin"] > inicio) & (comb["fin"] <= inicio + pd.Timedelta(days=1))].copy()
    assert len(dia) == 48, "el día no tiene 48 medias horas"
    dia["semana"] = demanda.reindex(dia["fin"] - pd.Timedelta(days=7)).to_numpy()
    puntos = [{
        "h": (f - pd.Timedelta(minutes=30)).strftime("%H:%M"),
        "pred": float(p), "bajo": float(p * (1 + q05)), "alto": float(p * (1 + q95)),
        "real": float(r), "semana": float(s),
    } for f, p, r, s in zip(dia["fin"], dia["pred_48"], dia["real"], dia["semana"])]
    destacado = next(p for p in puntos if p["h"] == hora)
    mae = float(np.mean([abs(p["real"] - p["pred"]) for p in puntos]))
    mae_semana = float(np.mean([abs(p["real"] - p["semana"]) for p in puntos]))
    # Las cifras de la demo (docs/guion-exposicion.md, verificadas contra la app el 20-nov)
    comprobar("demo, pronóstico de las 19:00", destacado["pred"], 4810, 0.5)
    comprobar("demo, real de las 19:00", destacado["real"], 4772, 0.5)
    comprobar("demo, MAE del día", mae, 40.7)
    comprobar("demo, MAE de la semana pasada", mae_semana, 77.0)
    return {"fecha": fecha, "hora": hora, "puntos": puntos, "destacado": destacado, "nivel": 90,
            "mae": mae, "mae_semana": mae_semana}


# ------------------------------------------------------------------ (2) la prueba de 2026 por área y horizonte
def prueba_2026(reportes: Path, comparacion: pd.DataFrame) -> list[dict]:
    fr = pd.read_csv(reportes / "sein" / "prueba_2026" / "frente_referencias.csv")
    salida = []
    for h in HORIZONTES:
        for a in AREAS:
            d = fr[(fr["Horizonte"] == h) & (fr["Área"] == a)]
            ref = d[d["Método"].str.startswith("Mejor referencia")].iloc[0]
            rf = d[d["Método"].str.startswith("Random Forest")].iloc[0]
            xgb = d[d["Método"].str.startswith("Gradient Boosting global")].iloc[0]
            c = comparacion[(comparacion["Año"] == 2026) & (comparacion["Horizonte"] == h)
                            & (comparacion["Área"] == a)].set_index("Archivo")
            # La comparación de los fundacionales usa las mismas filas que el modelo elegido
            comprobar(f"RF {h} {a}: fundacionales frente a la prueba",
                      c.loc["Random Forest por área (elegido)", "MAE (MW)"], rf["MAE (MW)"], 0.01)
            mae_ref = float(ref["MAE (MW)"])
            comb = float(c.loc["combinacion_c2048", "MAE (MW)"])
            salida.append({
                "horizonte": h, "area": a,
                "referencia": ref["Método"].split("(")[1].rstrip(")"), "ref": mae_ref,
                "rf": float(rf["MAE (MW)"]), "xgb": float(xgb["MAE (MW)"]), "comb": comb,
                "mejora_rf": float(rf["Mejora vs. mejor referencia (%)"]),
                "mejora_xgb": float(xgb["Mejora vs. mejor referencia (%)"]),
                "mejora_comb": 100 * (1 - comb / mae_ref),
                "ic_rf": [float(rf["IC 95 % bajo"]), float(rf["IC 95 % alto"])],
            })
    return salida


def mejora_2025(reportes: Path) -> dict:
    """Mejora del Random Forest elegido frente a la mejor referencia en la validación de 2025 (notebook 02)."""
    mejoras = {}
    for h in HORIZONTES:
        for a in AREAS:
            p = pd.read_csv(reportes / "sein" / "modelado" / f"predicciones_validacion_{h}_{a.lower()}.csv")
            refs = [(p[r] - p["real"]).abs().mean() for r in ("persistencia", "ayer", "semana_pasada")]
            mejoras[(h, a)] = 100 * (1 - (p["fijo_M0"] - p["real"]).abs().mean() / min(refs))
    return mejoras


# ------------------------------------------------------------------ (3) mes a mes en 2026
def mensual_2026(reportes: Path, raiz: Path) -> dict:
    m = pd.read_csv(reportes / "sein" / "prueba_2026" / "mensual.csv")
    paneles = []
    for h in HORIZONTES:
        for a in AREAS:
            d = m[(m["Horizonte"] == h) & (m["Área"] == a)].sort_values("Mes")
            paneles.append({"horizonte": h, "area": a, "meses": [
                {"mes": f["Mes"], "modelo": f["Fijo (A)"], "ref": f["Mejor referencia"], "mejora": f["Mejora A (%)"]}
                for _, f in d.iterrows()]})
    icen = pd.read_parquet(raiz / "exogenas" / "silver" / "icen.parquet")
    icen = icen[icen["mes"] >= "2026-01-01"]
    return {"paneles": paneles, "icen": [{"mes": f"{f.mes:%Y-%m}", "icen": float(f.icen)} for f in icen.itertuples()]}


# ------------------------------------------------------------------ (4) Tetuán y Ceuta frente a las referencias fuertes
def reanalisis(reportes: Path) -> dict:
    r = pd.read_csv(reportes / "tb1" / "reanalisis.csv", dtype={"ventana": str})
    mae = r.set_index(["serie", "ventana", "metodo"]).sort_index()
    tetuan = []
    for z in (1, 2, 3):
        s = mae.loc[(f"Tetuán Z{z}", "2017")]
        mejor = r[(r["serie"] == f"Tetuán Z{z}") & r["metodo"].isin(["persistencia", "ayer", "semana_pasada"])]
        nombre_mejor = mejor.loc[mejor["MAE"].idxmin(), "metodo"]
        modelo, hist, deltas = s.loc["hgb_global", "MAE"], s.loc["mejor_historica", "MAE"], s.loc["promedio_deltas", "MAE"]
        tetuan.append({"zona": f"Zona {z}", "modelo": modelo, "historica": hist, "deltas": deltas,
                       "nombre_historica": {"ayer": "ayer", "semana_pasada": "semana pasada"}.get(nombre_mejor, nombre_mejor),
                       "frente_historica": 100 * (1 - modelo / hist), "frente_deltas": 100 * (1 - modelo / deltas)})
    ceuta = []
    for v in range(2022, 2027):
        s = mae.loc[("Ceuta", str(v))]
        ceuta.append({"verano": v, "modelo": s.loc["v4_sin_verano", "MAPE"], "delta": s.loc["delta_semanal", "MAPE"],
                      "deltas": s.loc["promedio_deltas", "MAPE"]})
    for z, (hist, deltas) in zip(tetuan, [(44.8, 3.8), (55.9, -3.9), (40.7, -16.5)]):  # §5.1
        comprobar(f"Tetuán {z['zona']} frente a la mejor histórica", z["frente_historica"], hist)
        comprobar(f"Tetuán {z['zona']} frente al promedio de los deltas", z["frente_deltas"], deltas)
    media_modelo = float(np.mean([c["modelo"] for c in ceuta]))
    media_delta = float(np.mean([c["delta"] for c in ceuta]))
    comprobar("Ceuta, modelo sin verano", media_modelo, 2.33)  # §5.2
    comprobar("Ceuta, delta semanal", media_delta, 2.06)
    return {"tetuan": tetuan, "ceuta": ceuta, "ceuta_modelo": media_modelo, "ceuta_delta": media_delta,
            "ceuta_gana_delta": sum(c["delta"] < c["modelo"] for c in ceuta)}


# ------------------------------------------------------------------ (5) peso frente a rendimiento
def peso_rendimiento(comparacion: pd.DataFrame) -> list[dict]:
    d = comparacion[(comparacion["Año"] == 2026) & (comparacion["Área"] == "Centro")]
    salida = []
    for archivo, (nombre, tipo, mb, estimado) in PESOS.items():
        filas = d[d["Archivo"] == archivo].set_index("Horizonte")["MAE (MW)"]
        salida.append({"nombre": nombre, "tipo": tipo, "mb": mb, "estimado": estimado,
                       "mae_1h": float(filas["1h"]), "mae_24h": float(filas["24h"])})
    return salida


# ------------------------------------------------------------------ tablas del respaldo (markdown)
def tabla_hipotesis(reportes: Path) -> str:
    h = pd.read_csv(reportes / "sein" / "prueba_2026" / "hipotesis.csv")
    filas = ["| Hipótesis, escrita al cerrar 2025 | ¿Se cumple? | Evidencia en 2026 |", "|:--|:--|:--|"]
    for _, f in h.iterrows():
        clave = f["Hipótesis"].split(".")[0]
        veredicto = f["¿Se cumple?"] if f["¿Se cumple?"] == "Sí" else f"**{f['¿Se cumple?']}**"
        if clave == "4":
            veredicto = "**No, al revés**"
        evidencia = f["Evidencia"].replace("-", MENOS).replace("1h ", "1 h ").replace("24h ", "24 h ")
        if clave == "1b":
            evidencia = "Subió: " + evidencia
        if clave == "4" and not evidencia.startswith(("+", MENOS)):
            evidencia = "+" + evidencia
        if clave == "3":  # el área que la rompe; las otras dos se distinguen de cero
            evidencia = next(p.strip() for p in evidencia.split(";") if p.strip().startswith("Centro"))
        if clave == "5":
            evidencia = "Ningún efecto de El Niño (M2 − M1) con intervalo bajo cero"
        filas.append(f"| {clave}. {HIPOTESIS[clave]} | {veredicto} | {evidencia} |")
    return "\n".join(filas) + "\n"


def tabla_ablacion(reportes: Path) -> str:
    a = pd.read_csv(reportes / "sein" / "prueba_2026" / "ablacion.csv")
    columnas = [("Clima (M1 − M0)", "Clima"), ("El Niño (M2 − M1)", "El Niño"), ("Sin fallas (M2 − M0)", "Clima + El Niño")]
    filas = ["| Horizonte · área | " + " | ".join(n for _, n in columnas) + " |", "|:--|" + "--:|" * len(columnas)]
    for h in HORIZONTES:
        for area in AREAS:
            celdas = []
            for contraste, _ in columnas:
                f = a[(a["Horizonte"] == h) & (a["Área"] == area) & (a["Contraste"] == contraste)].iloc[0]
                texto = ic(f)
                celdas.append(f"**{texto}**" if f["Distinguible"] else texto)
            filas.append(f"| {h.replace('h', ' h')} · {area} | " + " | ".join(celdas) + " |")
    return "\n".join(filas) + "\n"


def tabla_adaptacion(reportes: Path) -> str:
    e = pd.read_csv(reportes / "sein" / "prueba_2026" / "efectos_adaptacion.csv")
    contrastes = [
        ("Reentrenar sin exógenas (C − A)", "Reentrenar, sin exógenas"),
        ("Reentrenar sin fallas (semanal M2 − fijo M2)", "Reentrenar, con clima y El Niño"),
        ("Alerta en vez de semanal (alerta − semanal, M3)", "Solo con la alerta de ENFEN, en vez de cada semana"),
    ]
    filas = ["| Horizonte | Contraste | Norte | Centro | Sur |", "|:--|:--|--:|--:|--:|"]
    for h in HORIZONTES:
        for contraste, nombre in contrastes:
            d = e[(e["Horizonte"] == h) & (e["Contraste"] == contraste)].set_index("Área")
            if d.empty:
                continue
            celdas = [(f"**{ic(d.loc[x])}**" if d.loc[x, "Distinguible"] else ic(d.loc[x])) for x in AREAS]
            filas.append(f"| {h.replace('h', ' h')} | {nombre} | " + " | ".join(celdas) + " |")
    return "\n".join(filas) + "\n"


def tabla_fundacionales(comparacion: pd.DataFrame) -> str:
    cab = "| Modelo | 2025, 1 h | 2025, 24 h | 2026, 1 h | 2026, 24 h |"
    filas = [cab, "|:--|--:|--:|--:|--:|"]
    for archivo, nombre in FILAS_FUNDACIONALES:
        celdas = []
        for anio in (2025, 2026):
            for h in HORIZONTES:
                d = comparacion[(comparacion["Archivo"] == archivo) & (comparacion["Año"] == anio)
                                & (comparacion["Horizonte"] == h)].set_index("Área")["MAE (MW)"]
                texto = " / ".join(dec(d[a]) for a in AREAS)
                celdas.append(f"**{texto}**" if nombre.startswith("**") else texto)
        filas.append(f"| {nombre} | " + " | ".join(celdas) + " |")
    return "\n".join(filas) + "\n"


# ------------------------------------------------------------------ portada
def portada(raiz: Path) -> str:
    """La demanda media mensual del SEIN, 2016-2026, con 2026 resaltado y una línea en el máximo de 2016-2025.
    Colores fijos: una imagen de fondo no hereda el CSS."""
    d = pd.read_parquet(raiz / "coes" / "silver" / "demanda_areas.parquet").set_index("DateTime")["SEIN"]
    mensual = d.resample("MS").mean().dropna()
    techo = float(mensual[mensual.index < "2026-01-01"].max())
    ancho, alto = 900.0, 520.0
    x0, x1 = mensual.index.min(), mensual.index.max()
    y0, y1 = float(mensual.min()) * 0.97, float(mensual.max()) * 1.02

    def xy(t, v):
        return (ancho * ((t - x0) / (x1 - x0)), alto * (1 - (v - y0) / (y1 - y0)))

    puntos = [xy(t, v) for t, v in mensual.items()]
    antes = [p for (t, _), p in zip(mensual.items(), puntos) if t < pd.Timestamp("2026-01-01")]
    desde = [p for (t, _), p in zip(mensual.items(), puntos) if t >= pd.Timestamp("2025-12-01")]

    def camino(ps):
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in ps)

    _, y_techo = xy(x0, techo)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-20 -20 {ancho + 40:.0f} {alto + 40:.0f}">'
            f'<line x1="0" x2="{ancho:.0f}" y1="{y_techo:.1f}" y2="{y_techo:.1f}" stroke="#7F93AA" '
            'stroke-width="2" stroke-dasharray="6 6"/>'
            f'<path d="{camino(antes)}" fill="none" stroke="#B8C2CE" stroke-opacity="0.55" stroke-width="3" '
            'stroke-linejoin="round"/>'
            f'<path d="{camino(desde)}" fill="none" stroke="#7DB3F2" stroke-width="6" stroke-linejoin="round" '
            'stroke-linecap="round"/></svg>\n')


# ------------------------------------------------------------------ todo junto
def main() -> None:
    raiz = raiz_datos()
    reportes = raiz / "reportes"
    comparacion = pd.read_csv(reportes / "sein" / "fundacionales" / "tablas" / "comparacion.csv")

    dia = dia_centro(raiz)
    prueba = prueba_2026(reportes, comparacion)
    m2025 = mejora_2025(reportes)
    mensual = mensual_2026(reportes, raiz)
    rean = reanalisis(reportes)
    peso = peso_rendimiento(comparacion)

    p = {(x["horizonte"], x["area"]): x for x in prueba}
    for (h, a), en_el_informe in {("1h", "Norte"): 51.7, ("1h", "Centro"): 57.9, ("1h", "Sur"): 29.1,
                                  ("24h", "Norte"): 34.5, ("24h", "Centro"): 42.2, ("24h", "Sur"): 11.9}.items():
        comprobar(f"prueba 2026, {h} {a}", p[(h, a)]["mejora_rf"], en_el_informe)  # §5.4
    mas_que_2025 = sum(p[k]["mejora_rf"] > m2025[k] for k in p)
    comprobar("RF, mejora media de 2025 a 1 h", np.mean([m2025[("1h", a)] for a in AREAS]), DEL_INFORME["val_rf"])

    panel = {(x["horizonte"], x["area"]): x["meses"] for x in mensual["paneles"]}
    norte_1h = {f["mes"]: f["mejora"] for f in panel[("1h", "Norte")]}
    sur_24h = {f["mes"]: f["mejora"] for f in panel[("24h", "Sur")]}
    perdidas = [(k, f["mes"]) for k, meses in panel.items() for f in meses if f["mejora"] < 0]
    assert perdidas == [(("24h", "Sur"), "2026-10")], f"el único mes perdido ya no es el Sur a 24 h en octubre: {perdidas}"

    ab = pd.read_csv(reportes / "sein" / "prueba_2026" / "ablacion.csv").set_index(["Horizonte", "Contraste", "Área"])
    ad = pd.read_csv(reportes / "sein" / "prueba_2026" / "efectos_adaptacion.csv").set_index(
        ["Horizonte", "Contraste", "Área"])
    hip = pd.read_csv(reportes / "sein" / "prueba_2026" / "hipotesis.csv")
    no_cumplen = [f["Hipótesis"].split(".")[0] for _, f in hip.iterrows() if f["¿Se cumple?"] != "Sí"]
    clima_1h = ab.loc[("1h", "Clima (M1 − M0)", "Centro")]
    clima_24h = ab.loc[("24h", "Clima (M1 − M0)", "Centro")]
    clima_24h_norte = ab.loc[("24h", "Clima (M1 − M0)", "Norte")]
    exo_1h = ab.loc[("1h", "Sin fallas (M2 − M0)", "Centro")]
    reent = {a: ad.loc[("1h", "Reentrenar sin exógenas (C − A)", a)] for a in AREAS}

    c = comparacion.set_index(["Año", "Horizonte", "Área", "Archivo"])["MAE (MW)"]
    rfc = "Random Forest por área (elegido)"
    fm = {f"fm{anio}_{h}_{a.lower()}_{m}": c[(anio, h, a, arch)] for anio in (2025, 2026) for h in HORIZONTES
          for a in AREAS for m, arch in (("rf", rfc), ("comb", "combinacion_c2048"))}
    simons_1h = c[(2025, "1h", "Centro", "simons_c2048")]

    icen = {f["mes"]: f["icen"] for f in mensual["icen"]}
    demanda = pd.read_parquet(raiz / "coes" / "silver" / "demanda_areas.parquet").set_index("DateTime")
    anual = demanda["SEIN"].groupby(demanda.index.year).mean()
    mensual_areas = demanda[["NORTE"]].resample("MS").mean()
    interanual = (100 * (mensual_areas / mensual_areas.shift(12) - 1)).loc["2026-03":"2026-10", "NORTE"]
    cron = json.loads((RAIZ_REPO / "docs" / "demo" / "cronometro.json").read_text(encoding="utf-8"))
    demo_s = cron["recorrido"]["total"]

    t = rean["tetuan"]
    deck = {
        **{k: (dec(v) if isinstance(v, float) else v) for k, v in DEL_INFORME.items()},
        # Tres casos y lo que se encontró (capa silver del COES)
        "sein_periodos": miles(len(demanda)),
        "sein_2016": miles(anual[2016]), "sein_2025": miles(anual[2025]),
        "sein_crecimiento": dec(100 * (anual[2025] / anual[2016] - 1), 0),
        "norte_2026": f"+{dec(interanual.min(), 0)} a {dec(interanual.max(), 0)}",
        "norte_max": dec(interanual.max(), 0),
        "icen_agosto": dec(icen["2026-08"], 2),
        # La prueba de 2026 (frente_referencias.csv) y su comparación con 2025
        **{f"mejora_{h}_{a.lower()}": dec(p[(h, a)]["mejora_rf"]) for h in HORIZONTES for a in AREAS},
        "mas_que_2025": str(mas_que_2025),
        "norte_enero": dec(norte_1h["2026-01"]), "norte_septiembre": dec(norte_1h["2026-09"]),
        "sur_octubre": dec(sur_24h["2026-10"]),
        "icen_enero": dec(icen["2026-01"], 2),
        # Reanálisis de Tetuán y Ceuta
        "tetuan_hist_min": dec(min(z["frente_historica"] for z in t), 0),
        "tetuan_hist_max": dec(max(z["frente_historica"] for z in t), 0),
        "tetuan_gana_deltas": str(sum(z["frente_deltas"] > 0 for z in t)),
        "tetuan_pierde_deltas": str(sum(z["frente_deltas"] < 0 for z in t)),
        "ceuta_modelo": dec(rean["ceuta_modelo"], 2), "ceuta_delta": dec(rean["ceuta_delta"], 2),
        "ceuta_gana_delta": str(rean["ceuta_gana_delta"]),
        # Adaptación (ablacion.csv, efectos_adaptacion.csv, hipotesis.csv)
        "clima_1h_centro": con_signo(clima_1h["Δ MAE (MW)"]),
        "exo_1h_centro": con_signo(exo_1h["Δ MAE (MW)"]),
        "clima_24h_centro": con_signo(clima_24h["Δ MAE (MW)"]),
        "clima_24h_centro_ic": f"{dec(clima_24h['IC 95 % bajo'], 2)} a {dec(clima_24h['IC 95 % alto'], 2)}",
        "clima_24h_norte": con_signo(clima_24h_norte["Δ MAE (MW)"]),
        "reentrenar_1h": " / ".join(con_signo(reent[a]["Δ MAE (MW)"]) for a in AREAS),
        "reentrenar_1h_centro": con_signo(reent["Centro"]["Δ MAE (MW)"]),
        "rf_1h_centro": dec(p[("1h", "Centro")]["rf"]),
        "hipotesis_no": ", ".join(no_cumplen[:-1]) + " y " + no_cumplen[-1],
        "hipotesis_no_n": str(len(no_cumplen)),
        # Fundacionales (comparacion.csv)
        **{k: dec(v) for k, v in fm.items()},
        "simons_1h_centro_2025": dec(simons_1h),
        # El día de la demo (combinacion_c2048.parquet y la capa silver)
        "dia_pred": miles(dia["destacado"]["pred"]), "dia_real": miles(dia["destacado"]["real"]),
        "dia_bajo": miles(dia["destacado"]["bajo"]), "dia_alto": miles(dia["destacado"]["alto"]),
        "dia_mae": dec(dia["mae"]), "dia_mae_semana": dec(dia["mae_semana"]),
        "demo_duracion": f"{int(demo_s // 60)}:{round(demo_s % 60):02d}",
    }
    assert deck["hipotesis_no"] == "1b, 3 y 4", deck["hipotesis_no"]

    datos = {
        "dia": dia,
        "prueba": prueba,
        "mensual": mensual,
        "reanalisis": rean,
        "peso": peso,
        "barras": {
            "validacion": [
                {"etiqueta": "Random Forest", "valor": DEL_INFORME["val_rf"], "clase": "b-rf", "texto": "43.2 %"},
                {"etiqueta": "XGBoost", "valor": DEL_INFORME["val_xgb"], "clase": "b-xgb", "texto": "42.9 %"},
                {"etiqueta": "Ridge", "valor": DEL_INFORME["val_ridge"], "clase": "b-gris", "texto": "26.4 %"},
            ],
            "adaptacion": [
                {"etiqueta": "Error del modelo fijo", "valor": p[("1h", "Centro")]["rf"], "clase": "b-tinta",
                 "texto": f"{deck['rf_1h_centro']} MW"},
                {"etiqueta": "Sumar clima y El Niño", "valor": abs(exo_1h["Δ MAE (MW)"]), "clase": "b-rf",
                 "texto": f"{deck['exo_1h_centro']} MW"},
                {"etiqueta": "Reentrenar cada semana", "valor": abs(reent["Centro"]["Δ MAE (MW)"]), "clase": "b-rf",
                 "texto": f"{deck['reentrenar_1h_centro']} MW"},
            ],
        },
    }
    for b in datos["barras"]["validacion"]:  # el texto es el valor del informe, con un decimal
        assert b["texto"] == f"{dec(b['valor'])} %"

    js = ("// Generado por datos.py desde las tablas de reportes/. No editar a mano.\n"
          "window.DATOS = " + json.dumps(datos, ensure_ascii=False, indent=1, default=float) + ";\n")
    (AQUI / "datos.js").write_text(js, encoding="utf-8")
    yml = "# Generado por datos.py. No editar a mano: se rehace desde las tablas de reportes/.\ndeck:\n"
    yml += "".join(f'  {k}: "{v}"\n' for k, v in deck.items())
    (AQUI / "_deck.yml").write_text(yml, encoding="utf-8")
    generado = AQUI / "generado"
    generado.mkdir(exist_ok=True)
    (generado / "hipotesis.md").write_text(tabla_hipotesis(reportes), encoding="utf-8")
    (generado / "ablacion.md").write_text(tabla_ablacion(reportes), encoding="utf-8")
    (generado / "adaptacion.md").write_text(tabla_adaptacion(reportes), encoding="utf-8")
    (generado / "fundacionales.md").write_text(tabla_fundacionales(comparacion), encoding="utf-8")
    (AQUI / "img" / "portada.svg").write_text(portada(raiz), encoding="utf-8")
    print(f"datos.js, _deck.yml, generado/*.md e img/portada.svg desde {raiz}: {len(deck)} cifras, "
          f"{len(prueba)} celdas de la prueba, {len(peso)} modelos con su peso")


if __name__ == "__main__":
    main()
