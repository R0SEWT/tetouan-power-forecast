"""Temperatura pronosticada a un día (archivo de corridas previas de Open-Meteo) y la corrección por calor del
pronóstico de Chronos-2 ajustado.

**Qué archiva Open-Meteo** (Previous Runs API, https://open-meteo.com/en/docs/previous-runs-api, y el anuncio del
archivo en su boletín): para cada hora válida v, `temperature_2m_previous_dayN` es lo que pronosticaba el modelo con N
días de antelación. No es una corrida fija: de cada corrida se descartan las primeras 24·N horas y el resto se cose en
una serie continua, así que una hora ya pasada queda con la corrida iniciada entre v − 24·N − U y v − 24·N (U = horas
entre corridas: 6 en GFS). Para horas futuras la serie trae la corrida más reciente (todavía puede cambiar). Se usa
GFS (`gfs_seamless`), archivado desde marzo de 2021; «best match» solo desde 2024 y fue peor en 2025.

**Regla de información.** Para un origen t solo vale lo que se sabía en t. El desfase N de un día Y entero (hasta su
hora 23) sale de corridas iniciadas a más tardar en Y + 23 h − 24·N h y se publica, como mucho, `DEMORA` = 8 h
después. En el origen t se usa la **edición vigente**: el menor N ≥ 1 ya publicado. A 24 h (día objetivo X, orígenes
en X − 1) es el desfase 2 desde las 07:00 de X − 1 y el 3 antes; a 1 h, el 1 desde las 07:00 de X y el 2 antes. Lo que
usa la regla ya está asentado cuando se emite, así que consultar el archivo después da los mismos valores.

**Nivel.** ERA5 (la temperatura del proyecto, con la que se estimó el umbral) y GFS no tienen el mismo nivel: en Lima,
GFS queda ~0.5 °C más cálido en verano y hasta 1.3 °C más frío en invierno. El pronóstico se lleva al nivel de ERA5 con la diferencia media por desfase, área, mes y hora, solo con fechas < 2025.

**Corrección por calor** (`chronos2ftcal+calor`): pronóstico × (1 + β_b · grados), con los grados de la media diaria
pronosticada sobre el umbral del área en el día objetivo y un β ≥ 0 por bloque de horas, reestimado cada día con los
errores de Chronos-2 ajustado desde el 1-ene-2025 (fuera de muestra: su ajuste fino solo vio hasta 2024) y solo con
días objetivo ya cerrados al emitir (a 24 h, hasta X − 2; a 1 h, hasta X − 1). Elegida con 2025 en
`experimentos/temperatura/` (informe de noviembre de 2026).
"""

import datetime as dt
import http.client
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from tetouan_power_forecast.exogenas import CIUDADES
from tetouan_power_forecast.medallon import _reemplazar, raiz_datos

URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
MODELO = "gfs_seamless"
INICIO_ARCHIVO = {"gfs_seamless": dt.date(2021, 3, 1), "best_match": dt.date(2024, 1, 1)}
DESFASES = (0, 1, 2, 3)
VARIABLES = ["temperature_2m"] + [f"temperature_2m_previous_day{n}" for n in DESFASES if n]
LUGARES = [(area, ciudad, lat, lon) for area, ciudades in CIUDADES.items() for ciudad, (lat, lon) in ciudades.items()]
AREAS = list(CIUDADES)  # norte, centro, sur
PASO = pd.Timedelta(minutes=30)
HORA = pd.Timedelta(hours=1)
DIA = pd.Timedelta(days=1)
PASOS = {"1h": 2, "24h": 48}
DEMORA = pd.Timedelta(hours=8)
FIN_AJUSTE = pd.Timestamp("2025-01-01")
INICIO_CORRECCION = pd.Timestamp("2025-01-01")
DIAS_RECIENTES = 40
# Umbral de enfriamiento (°C de media diaria, nivel ERA5): el codo de la demanda diaria del área frente a su temperatura,
# con efectos fijos de año-mes y día de la semana, solo 2016–2024 (experimentos/temperatura/umbral.py).
UMBRAL = {"centro": 23.0, "norte": 25.75, "sur": 20.25}
# Bloque de horas del periodo objetivo (periodos 1–48 del día, fechados por su fin): madrugada (00:30–07:00), mañana
# (07:30–13:00), tarde (13:30–19:00) y noche (19:30–24:00)
BLOQUES = np.array([0] * 14 + [1] * 12 + [2] * 12 + [3] * 10)
# Retraso de los errores que ya se conocen al emitir el día X: a 24 h los orígenes empiezan en X − 1 a las 00:30
RETRASO = {"24h": 2, "1h": 1}

log = logging.getLogger(__name__)


# ---- Descarga ------------------------------------------------------------------------------------------------------


def carpeta(raiz=None):
    return raiz_datos(raiz) / "exogenas" / "bronze" / "open_meteo_previous_runs"


def url(modelo, **rango):
    """La consulta de las seis ciudades. `rango`: start_date/end_date o past_days/forecast_days."""
    parametros = {"latitude": ",".join(f"{x[2]}" for x in LUGARES), "longitude": ",".join(f"{x[3]}" for x in LUGARES),
                  "hourly": ",".join(VARIABLES), "timezone": "America/Lima", **{k: f"{v}" for k, v in rango.items()}}
    if modelo != "best_match":
        parametros["models"] = modelo
    return f"{URL}?{urllib.parse.urlencode(parametros)}"


def pedir(direccion, intentos=3, espera=10, timeout=180, dormir=time.sleep):
    """GET con reintentos; lanza el último error si no sale."""
    for intento in range(1, intentos + 1):
        try:
            pedido = urllib.request.Request(direccion, headers={"User-Agent": "tpf-temperatura"})
            with urllib.request.urlopen(pedido, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if intento == intentos:
                raise
            log.warning(f"Open-Meteo: reintento {intento} tras {error}")
            dormir(espera * intento)
    return None


def _guardar(archivo, contenido, **meta):
    archivo.parent.mkdir(parents=True, exist_ok=True)
    json.loads(contenido)  # una respuesta que no es JSON (una página de error) no se guarda
    _reemplazar(archivo, lambda r: r.write_bytes(contenido))
    meta = {**meta, "bytes": len(contenido), "descargado_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    _reemplazar(archivo.with_name(archivo.name + ".procedencia.json"),
                lambda r: r.write_text(json.dumps(meta, ensure_ascii=False, indent=1)))


def bajar_anios(raiz=None, hasta=None, modelos=(MODELO,), descargar=pedir, progreso=print):
    """El archivo por modelo y año (una consulta por año con las seis ciudades). Un año ya bajado no se repite si
    cubre lo pedido."""
    hasta = hasta or dt.date.today() + dt.timedelta(days=1)
    for modelo in modelos:
        inicio = INICIO_ARCHIVO[modelo]
        for anio in range(inicio.year, hasta.year + 1):
            desde, fin = max(inicio, dt.date(anio, 1, 1)), min(hasta, dt.date(anio, 12, 31))
            archivo = carpeta(raiz) / f"{modelo}_{anio}.json"
            meta = archivo.with_name(archivo.name + ".procedencia.json")
            if archivo.exists() and meta.exists() and json.loads(meta.read_text()).get("hasta", "") >= f"{fin}":
                continue
            direccion = url(modelo, start_date=desde, end_date=fin)
            _guardar(archivo, descargar(direccion), url=direccion, modelo=modelo, desde=f"{desde}", hasta=f"{fin}")
            progreso(f"Open-Meteo {modelo} {anio}: hasta {fin}")


def bajar_reciente(raiz=None, hoy=None, modelo=MODELO, descargar=pedir, dias=DIAS_RECIENTES):
    """Los últimos `dias` y los próximos 3, una vez por día (caché por fecha). Devuelve True si hay archivo de hoy.

    Si la red falla no se cae: queda lo que ya estaba guardado y quien llama decide si le alcanza.
    """
    hoy = hoy or dt.date.today()
    archivo = carpeta(raiz) / "reciente" / f"{modelo}_{hoy:%Y-%m-%d}.json"
    if archivo.exists():
        return True
    direccion = url(modelo, past_days=dias, forecast_days=3)
    try:
        _guardar(archivo, descargar(direccion), url=direccion, modelo=modelo, hoy=f"{hoy}")
    except (OSError, ValueError, http.client.HTTPException) as error:  # red, disco o una respuesta que no es JSON
        log.warning(f"Open-Meteo no respondió ({error}); se sigue con lo guardado")
        return False
    return True


def _leer_archivo(archivo):
    respuesta = json.loads(archivo.read_text())
    respuesta = respuesta if isinstance(respuesta, list) else [respuesta]
    tiempo = pd.to_datetime(respuesta[0]["hourly"]["time"])
    salida = {}
    for n, variable in zip(DESFASES, VARIABLES, strict=True):
        m = np.array([[np.nan if v is None else v for v in r["hourly"][variable]] for r in respuesta], dtype=float)
        por_area = {}
        for area in AREAS:
            idx = [i for i, x in enumerate(LUGARES) if x[0] == area]
            valores = m[idx]
            por_area[area] = np.where(np.isnan(valores).any(axis=0), np.nan, valores.mean(axis=0))
        salida[n] = pd.DataFrame(por_area, index=tiempo)
    return salida


def leer(raiz=None, modelo=MODELO):
    """{desfase: horaria por área (media de sus ciudades, °C)}: los años y luego las consultas recientes, en orden;
    para una misma hora gana la consulta más nueva (la que ya tiene la hora asentada)."""
    archivos = sorted(carpeta(raiz).glob(f"{modelo}_[0-9][0-9][0-9][0-9].json"))
    archivos += sorted((carpeta(raiz) / "reciente").glob(f"{modelo}_*.json"))
    archivos = [a for a in archivos if not a.name.endswith(".procedencia.json")]
    if not archivos:
        raise FileNotFoundError(f"No hay pronósticos de temperatura de {modelo} en {carpeta(raiz)}")
    partes = [_leer_archivo(a) for a in archivos]
    salida = {}
    for n in DESFASES:
        todo = pd.concat([p[n] for p in partes])
        todo = todo[~todo.index.duplicated(keep="last")].sort_index()
        salida[n] = todo
    return salida


# ---- Nivel, días y edición vigente -------------------------------------------------------------------------------


def era5_silver(raiz=None):
    t = pd.read_parquet(raiz_datos(raiz) / "exogenas" / "silver" / "temperatura_areas.parquet")
    return t.set_index("fecha_hora")[AREAS].sort_index()


def ajuste_nivel(pron, era5, hasta=FIN_AJUSTE):
    """Diferencia media ERA5 − pronóstico por desfase, mes y hora (una columna por área), con fechas < `hasta`."""
    ajustes = {}
    for n, p in pron.items():
        comun = p.index.intersection(era5.index)
        comun = comun[comun < hasta]
        dif = (era5.loc[comun] - p.loc[comun]).dropna()
        ajustes[n] = dif.groupby([dif.index.month, dif.index.hour]).mean()
    return ajustes


def aplicar_ajuste(pron, ajustes):
    salida = {}
    for n, p in pron.items():
        clave = pd.MultiIndex.from_arrays([p.index.month, p.index.hour])
        salida[n] = p + ajustes[n].reindex(clave).to_numpy()
    return salida


def tabla_ajuste(ajustes):
    """Los ajustes en formato largo (para guardarlos)."""
    return pd.concat([a.rename_axis(["mes", "hora"]).reset_index().assign(desfase=n) for n, a in ajustes.items()],
                     ignore_index=True)


def ajustes_desde_tabla(tabla):
    return {int(n): g.drop(columns="desfase").set_index(["mes", "hora"])[AREAS] for n, g in tabla.groupby("desfase")}


def diarias(horaria, umbral=UMBRAL):
    """Por área: media de las 24 horas, máxima, mínima de la madrugada (00–07 h) y grados sobre el umbral. Un día
    con alguna hora vacía queda vacío."""
    salida = {}
    dia = horaria.index.normalize()
    cuenta = horaria.notna().groupby(dia).sum()
    madrugada = horaria[horaria.index.hour < 7]
    for area in AREAS:
        d = pd.DataFrame({
            "media": horaria[area].groupby(dia).mean(),
            "max": horaria[area].groupby(dia).max(),
            "min_noche": madrugada[area].groupby(madrugada.index.normalize()).min(),
        })
        d = d.where((cuenta[area] == 24).reindex(d.index, fill_value=False))
        d["cdd"] = (d["media"] - umbral[area]).clip(lower=0)
        salida[area] = d
    return salida


def edicion_vigente(dia, origen, demora=DEMORA):
    """El menor desfase N ≥ 1 cuyo pronóstico del día `dia` entero ya estaba publicado en `origen`."""
    falta = (pd.DatetimeIndex(dia) + pd.Timedelta(hours=23) + demora - pd.DatetimeIndex(origen)) / HORA
    return np.maximum(1, np.ceil(np.asarray(falta, dtype=float) / 24)).astype(int)


def dia_objetivo(origenes, horizonte):
    return (pd.DatetimeIndex(origenes) + PASOS[horizonte] * PASO - PASO).normalize()


def valor_vigente(por_desfase, area, columna, dias, origenes):
    """El valor diario (`columna` de `diarias`) de cada día en su edición vigente en cada origen."""
    dias, origenes = pd.DatetimeIndex(dias), pd.DatetimeIndex(origenes)
    n = edicion_vigente(dias, origenes)
    salida = np.full(len(dias), np.nan)
    for k in np.unique(n):
        m = n == k
        if k in por_desfase:
            salida[m] = por_desfase[k][area][columna].reindex(dias[m]).to_numpy()
    return salida


def grados_por_desfase(raiz=None, pron=None, ajustes=None):
    """{desfase ≥ 1: diarias} del pronóstico llevado al nivel de ERA5."""
    pron = leer(raiz) if pron is None else pron
    ajustes = ajuste_nivel(pron, era5_silver(raiz)) if ajustes is None else ajustes
    ajustada = aplicar_ajuste({n: p for n, p in pron.items() if n >= 1}, ajustes)
    return {n: diarias(h) for n, h in ajustada.items()}


def grados_origen(por_desfase, origenes, horizonte, area):
    """Grados sobre el umbral del día objetivo de cada origen, en su edición vigente (NaN si no hay dato)."""
    return valor_vigente(por_desfase, area.lower(), "cdd", dia_objetivo(origenes, horizonte), origenes)


# ---- Corrección por calor ------------------------------------------------------------------------------------------


def bloque(objetivo):
    """Bloque de horas (0–3) del periodo objetivo (fechado por su fin)."""
    inicio = pd.DatetimeIndex(objetivo) - PASO
    k = (inicio - inicio.normalize()) // PASO
    return BLOQUES[np.asarray(k, dtype=int)]


def betas_en_linea(continuos, columna="tp_cdd", desde=INICIO_CORRECCION):
    """β ≥ 0 por (horizonte, área, día objetivo, bloque) con los errores de los días ya cerrados al emitir.

    `continuos` trae `horizonte`, `area`, `objetivo`, `pred`, `real` y `columna` (los grados del origen). β de un bloque
    = max(0, Σ x·r / Σ x²) con r = real / pred − 1, acumulado desde `desde` hasta el día X − RETRASO[horizonte].
    """
    filas = []
    c = continuos[continuos["objetivo"] - PASO >= desde].copy()
    c["dia"] = (c["objetivo"] - PASO).dt.normalize()
    c["b"] = bloque(c["objetivo"])
    r = (c["real"] / c["pred"] - 1).to_numpy()
    x = c[columna].to_numpy(dtype=float)
    ok = np.isfinite(r) & np.isfinite(x)
    c["xr"], c["xx"] = np.where(ok, x * r, 0.0), np.where(ok, x * x, 0.0)
    for (h, a), g in c.groupby(["horizonte", "area"]):
        dias = pd.date_range(g["dia"].min(), g["dia"].max() + RETRASO[h] * DIA, freq="D")
        suma = g.groupby(["dia", "b"])[["xr", "xx"]].sum().unstack(fill_value=0.0)
        suma = suma.reindex(columns=pd.MultiIndex.from_product([["xr", "xx"], range(4)]), fill_value=0.0)
        acum = suma.reindex(dias, fill_value=0.0).cumsum().shift(RETRASO[h], fill_value=0.0)
        xr, xx = acum["xr"].to_numpy(), acum["xx"].to_numpy()
        beta = np.where(xx > 0, np.maximum(0.0, xr / np.where(xx > 0, xx, 1.0)), 0.0)
        filas.append(pd.DataFrame({"horizonte": h, "area": a, "dia": dias,
                                   **{f"beta_{k}": beta[:, k] for k in range(4)}}))
    return pd.concat(filas, ignore_index=True)


def factor_calor(betas, horizonte, area, objetivos, grados):
    """1 + β · grados para cada periodo objetivo (con el β de su día y bloque; sin β, 1)."""
    objetivos = pd.DatetimeIndex(objetivos)
    dias = (objetivos - PASO).normalize()
    b = betas[(betas["horizonte"] == horizonte) & (betas["area"] == area)].set_index("dia")
    tabla = b[[f"beta_{k}" for k in range(4)]].reindex(dias).to_numpy()
    beta = tabla[np.arange(len(objetivos)), bloque(objetivos)]
    return 1 + np.nan_to_num(beta) * np.asarray(grados, dtype=float)


def guardar_ajuste(raiz=None, ruta=None):
    """Calcula el ajuste de nivel (ERA5 − GFS, fechas < 2025) y lo deja junto a los pronósticos de temperatura."""
    ajustes = ajuste_nivel(leer(raiz), era5_silver(raiz))
    ruta = Path(ruta or carpeta(raiz) / f"ajuste_nivel_{MODELO}.csv")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tabla_ajuste(ajustes).to_csv(ruta, index=False)
    return ruta


def cargar_ajuste(raiz=None):
    """El ajuste de nivel guardado; si no está, lo calcula (necesita la silver de ERA5 y el archivo hasta 2024)."""
    ruta = carpeta(raiz) / f"ajuste_nivel_{MODELO}.csv"
    if not ruta.exists():
        guardar_ajuste(raiz, ruta)
    return ajustes_desde_tabla(pd.read_csv(ruta))
