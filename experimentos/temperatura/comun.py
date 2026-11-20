"""Temperatura pronosticada a un día: fuente, ajuste de nivel, vigencia en cada origen y variables por área.

**Regla de información.** Para un origen t (fin del último periodo observado, hora de Lima) solo vale lo que se
sabía en t. Un valor del desfase N para la hora v viene de una corrida iniciada a más tardar en v − 24·N h, que se
publica unas horas después; se toma una demora de publicación conservadora `DEMORA` = 8 h (GFS sale a las ~4–5 h y
el IFS de ECMWF a las ~7 h). Así, el pronóstico de desfase N de un día Y entero (hasta su hora 23) se conoce desde
Y + 23 h − 24·N h + DEMORA, y en el origen t se usa la **edición vigente**: el menor N ≥ 1 ya publicado.

- A 24 h, el día objetivo X se emite desde los orígenes de X − 1: desde las 07:00 de X − 1 vale el desfase 2 y antes
  el 3. La temperatura de la hora objetivo usa el desfase 2 (publicado ≥ 16 h antes del origen).
- A 1 h, desde las 07:00 de X vale el desfase 1 y antes el 2; la hora objetivo usa el desfase 1.
- Los días pasados (X − 1, X − 2… para la media móvil) usan su edición vigente con la misma regla. No se usa ERA5
  en el pronóstico: llega con 5 días de retraso.

**Nivel.** ERA5 (la temperatura «observada» del proyecto) y el modelo de pronóstico no tienen el mismo nivel (en
Lima, ERA5 queda ~1 °C arriba). El pronóstico se lleva al nivel de ERA5 con la diferencia media por área, desfase,
mes y hora estimada solo con fechas anteriores a `FIN_AJUSTE` (2025): así el umbral, estimado con ERA5, vale igual.
"""

import json
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd

from experimentos.temperatura import descarga
from tetouan_power_forecast import temperatura_pronosticada as tp
from tetouan_power_forecast.exogenas import CIUDADES
from tetouan_power_forecast.medallon import raiz_datos

RAIZ = raiz_datos()
SALIDA = RAIZ / "reportes" / "sein" / "temperatura"
FUND = RAIZ / "reportes" / "sein" / "fundacionales"
PASO = pd.Timedelta(minutes=30)
HORA = pd.Timedelta(hours=1)
DIA = pd.Timedelta(days=1)
DEMORA = tp.DEMORA
PASOS = {"1h": 2, "24h": 48}
AREAS = ["norte", "centro", "sur"]
FIN_AJUSTE = tp.FIN_AJUSTE
# Umbral de enfriamiento por área (°C de media diaria, nivel ERA5): el codo de una regresión de la demanda diaria con
# efectos fijos de año-mes y día de la semana, solo con 2016–2024 sin feriados ni 2020 (umbral.py). Centro: Lima.
UMBRAL = tp.UMBRAL
MODELO_PRONOSTICO = "gfs_seamless"  # se elige en fuente.py con 2025 (archivo desde 2021)
VARIABLES = ["tp_media", "tp_max", "tp_min_noche", "tp_cdd", "tp_media_3d", "tp_dcdd", "tp_obj"]


# ---- Fuentes -------------------------------------------------------------------------------------------------------


def era5_horaria(hasta=None):
    """ERA5 horario por área: la silver del proyecto y, después de su último día, ERA5 de Open-Meteo (mismos puntos,
    misma media por área; idéntico donde se solapan). Una consulta, guardada en la carpeta de salida."""
    silver = pd.read_parquet(RAIZ / "exogenas" / "silver" / "temperatura_areas.parquet").set_index("fecha_hora")
    silver = silver[AREAS].sort_index()
    desde = (silver.index.max() + DIA).normalize().date()
    hasta = pd.Timestamp(hasta or pd.Timestamp.now().normalize() - 5 * DIA).date()
    if hasta <= desde:
        return silver
    lugares = descarga.LUGARES
    archivo = SALIDA / "open_meteo" / f"era5_{desde}_{hasta}.json"
    if not archivo.exists():
        archivo.parent.mkdir(parents=True, exist_ok=True)
        parametros = {"latitude": ",".join(f"{x[2]}" for x in lugares),
                      "longitude": ",".join(f"{x[3]}" for x in lugares), "start_date": f"{desde}",
                      "end_date": f"{hasta}", "hourly": "temperature_2m", "models": "era5",
                      "timezone": "America/Lima"}
        archivo.write_bytes(descarga.pedir("https://archive-api.open-meteo.com/v1/archive?"
                                           + urllib.parse.urlencode(parametros)))
    respuesta = json.loads(archivo.read_text())
    tiempo = pd.to_datetime(respuesta[0]["hourly"]["time"])
    m = np.array([[np.nan if v is None else v for v in r["hourly"]["temperature_2m"]] for r in respuesta])
    nueva = pd.DataFrame({a: m[[i for i, x in enumerate(lugares) if x[0] == a]].mean(axis=0) for a in AREAS},
                         index=tiempo).dropna()
    return pd.concat([silver, nueva[nueva.index > silver.index.max()]]).sort_index()


def pronostico_horario(modelo=MODELO_PRONOSTICO, tabla=None):
    """{desfase: DataFrame horario (índice fecha_hora de Lima, columnas = áreas)} del archivo de Open-Meteo."""
    tabla = descarga.leer() if tabla is None else tabla
    t = tabla[tabla["modelo"] == modelo]
    return {n: g.pivot(index="fecha_hora", columns="area", values="temp")[AREAS].sort_index()
            for n, g in t.groupby("desfase")}


ajuste_nivel = tp.ajuste_nivel
aplicar_ajuste = tp.aplicar_ajuste


def pronostico_ajustado(modelo=MODELO_PRONOSTICO, era5=None, tabla=None):
    era5 = era5_horaria() if era5 is None else era5
    pron = pronostico_horario(modelo, tabla)
    return aplicar_ajuste(pron, ajuste_nivel(pron, era5))


# ---- Diarias y vigencia --------------------------------------------------------------------------------------------


diarias = tp.diarias
edicion_vigente = tp.edicion_vigente


def variables_origen(origenes, horizonte, por_desfase, horarias, area, umbral=UMBRAL, observada=False):
    """Las variables de temperatura de cada origen para el área: un DataFrame indexado por origen.

    `por_desfase` = {N: diarias(horaria del desfase N)} y `horarias` = {N: horaria} (para la hora objetivo). Con
    `observada=True` se pasan las diarias y la horaria de ERA5 bajo cualquier N (el «oráculo»: pronóstico perfecto).
    """
    origenes = pd.DatetimeIndex(origenes)
    pasos = PASOS[horizonte]
    objetivo = origenes + pasos * PASO
    dia_x = (objetivo - PASO).normalize()

    def valor(columna, dia):
        if observada:
            return por_desfase[1][area][columna].reindex(dia).to_numpy()
        n = edicion_vigente(dia, origenes)
        salida = np.full(len(dia), np.nan)
        for k in np.unique(n):
            m = n == k
            if k in por_desfase:
                salida[m] = por_desfase[k][area][columna].reindex(dia[m]).to_numpy()
        return salida

    media = valor("media", dia_x)
    cdd = valor("cdd", dia_x)
    previas = [valor("media", dia_x - j * DIA) for j in (1, 2)]
    cdd_previos = np.nanmean(np.column_stack([valor("cdd", dia_x - j * DIA) for j in range(1, 8)]), axis=1)
    n_obj = 1 if observada else (2 if horizonte == "24h" else 1)
    hor = horarias[n_obj][area].dropna()
    unida = hor.reindex(hor.index.union(objetivo))
    t_obj = unida.interpolate(method="time", limit_area="inside").reindex(objetivo).to_numpy()
    return pd.DataFrame({
        "tp_media": media, "tp_max": valor("max", dia_x), "tp_min_noche": valor("min_noche", dia_x),
        "tp_cdd": cdd, "tp_media_3d": (media + previas[0] + previas[1]) / 3, "tp_dcdd": cdd - cdd_previos,
        "tp_obj": t_obj,
    }, index=origenes)


def tabla_variables(origenes, fuente="pronostico", modelo=MODELO_PRONOSTICO, era5=None, tabla=None):
    """Variables por (horizonte, área, origen) en formato largo: fuente «pronostico» (edición vigente, nivel ERA5)
    u «observada» (ERA5)."""
    era5 = era5_horaria() if era5 is None else era5
    if fuente == "observada":
        horarias = {1: era5}
    else:
        horarias = pronostico_ajustado(modelo, era5, tabla)
        horarias = {n: h for n, h in horarias.items() if n >= 1}
    por_desfase = {n: diarias(h) for n, h in horarias.items()}
    partes = []
    for horizonte in PASOS:
        for area in AREAS:
            v = variables_origen(origenes, horizonte, por_desfase, horarias, area, observada=fuente == "observada")
            partes.append(v.assign(horizonte=horizonte, area=area.upper()).rename_axis("DateTime").reset_index())
    return pd.concat(partes, ignore_index=True)


def cdd_por_edicion(modelo=MODELO_PRONOSTICO, era5=None, tabla=None):
    """Por día y área, los grados sobre el umbral observados (ERA5) y pronosticados en cada edición (desfases 1–3):
    lo que necesita Chronos-2 como covariable (una fila por día; el script de la VM aplica la edición vigente)."""
    era5 = era5_horaria() if era5 is None else era5
    horarias = pronostico_ajustado(modelo, era5, tabla)
    obs = diarias(era5)
    por_n = {n: diarias(h) for n, h in horarias.items() if n >= 1}
    partes = []
    for area in AREAS:
        d = pd.DataFrame({"obs": obs[area]["cdd"], **{f"v{n}": por_n[n][area]["cdd"] for n in por_n}})
        partes.append(d.rename_axis("dia").reset_index().assign(area=area.upper()))
    return pd.concat(partes, ignore_index=True)


def guardar(df, nombre, carpeta=None):
    carpeta = Path(carpeta or SALIDA)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    if nombre.endswith(".csv"):
        df.to_csv(ruta, index=False)
    else:
        df.to_parquet(ruta, index=False)
    return ruta


def ciudades():
    return CIUDADES
