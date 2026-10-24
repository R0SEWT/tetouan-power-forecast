"""Variables exógenas del caso peruano, cada una con la información que de verdad había en el momento de predecir.

| Fuente | Qué aporta | Cuándo se conoce |
|---|---|---|
| IGP/ENFEN, ICEN | Régimen de El Niño Costero (mensual) | El definitivo del mes m sale entre los días ~10 y 20 de m+2 |
| NOAA CPC, Niño 1+2 OISST | Temperatura del mar frente al norte (semanal) | ~9 días después del centro de la semana |
| Open-Meteo, ERA5 | Temperatura horaria por ciudad | ~5 días; se usa como sustituto del dato observado del operador |
| Osinergmin, SAIDI/SAIFI | Duración y frecuencia de cortes por sistema eléctrico (mensual) | ~5 semanas |
| COES, eventos relevantes | Fallas con empresa, ubicación, inicio y fin | Durante la operación |

Capas: <datos>/exogenas/bronze/ (las respuestas sin tocar, con su procedencia) y <datos>/exogenas/silver/ (tablas
ordenadas). Las descargas se corren en Colab.
"""

import datetime as dt
import hashlib
import io
import json
import re
import urllib.parse

import numpy as np
import openpyxl
import pandas as pd

from tetouan_power_forecast.coes import URL_PORTAL, _pedir
from tetouan_power_forecast.medallon import _reemplazar, _ruta

URL_ICEN = "http://met.igp.gob.pe/datos/ICEN.txt"
URL_NINO12_SEMANAL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
URL_ERA5 = "https://archive-api.open-meteo.com/v1/archive"
URL_SAIDI = "https://www.datosabiertos.gob.pe/sites/default/files/Indicadores_Calidad_SAIDI_SAIFI.csv"
URL_EVENTOS = f"{URL_PORTAL}/eventos/relevantes/ExportarEvento"
INICIO = dt.date(2016, 1, 1)
REZAGO_NINO12_DIAS = 9
DURACION_MAX_FALLA = pd.Timedelta(days=2)  # más larga es una indisponibilidad, no una falla
# Sin `models`, Open-Meteo da su "best match", que mezcla IFS HRES (desde 2017), ERA5 y ERA5-Land: la serie
# cambiaría de fuente dentro del periodo de estudio. Se pide ERA5 solo, con la misma fuente de 2016 a hoy.
MODELO_ERA5 = "era5"
# Ciudades por área de la spec v2 (§6): costeras, sin Cusco por la altura. La tabla del paquete puede reemplazarlas.
CIUDADES = {
    "norte": {"Piura": (-5.194, -80.632), "Chiclayo": (-6.771, -79.841), "Trujillo": (-8.112, -79.029)},
    "centro": {"Lima": (-12.046, -77.043)},
    "sur": {"Arequipa": (-16.399, -71.535), "Tacna": (-18.006, -70.246)},
}


def _guardar_crudo(raiz, nombre, url, contenido, **consulta):
    """Guarda la respuesta sin tocar y su procedencia; `consulta` agrega lo que se pidió (modelo, fechas…)."""
    destino = _ruta(raiz, "exogenas/bronze", nombre)
    _reemplazar(destino, lambda r: r.write_bytes(contenido))
    procedencia = {"url": url, **consulta, "bytes": len(contenido), "sha256": hashlib.sha256(contenido).hexdigest(),
                   "descargado_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds")}
    texto = json.dumps(procedencia, ensure_ascii=False, indent=2) + "\n"
    _reemplazar(destino.with_name(destino.name + ".procedencia.json"), lambda r: r.write_text(texto))
    return destino


# --- El Niño ---------------------------------------------------------------------------------------------------

def leer_icen(texto):
    """El ICEN oficial (`yy mm valor`, comentarios con %), como serie mensual con el mes en su primer día."""
    filas = [linea.split() for linea in texto.splitlines() if linea.strip() and not linea.lstrip().startswith("%")]
    df = pd.DataFrame([(int(a), int(m), float(v)) for a, m, v in filas], columns=["anio", "mes", "icen"])
    df["mes"] = pd.to_datetime({"year": df["anio"], "month": df["mes"], "day": 1})
    return df[["mes", "icen"]]


def icen_disponible(fechas, icen):
    """El último ICEN definitivo publicado en cada fecha: el del mes m−2 desde el día 20, el de m−3 antes."""
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)))
    rezago = np.where(fechas.dt.day >= 20, 2, 3)
    meses = fechas.dt.to_period("M") - rezago
    valores = icen.set_index(icen["mes"].dt.to_period("M"))["icen"]
    return pd.Series(valores.reindex(meses).to_numpy(), index=fechas.index, name="icen")


def leer_nino12_semanal(texto):
    """El archivo semanal de CPC: semana (centro), SST y anomalía de Niño 1+2 (las dos primeras columnas)."""
    filas = []
    for linea in texto.splitlines():
        semana = re.match(r"^\s*(\d{2}[A-Z]{3}\d{4})", linea)
        if not semana:
            continue
        numeros = re.findall(r"-?\d+\.\d", linea[semana.end():])
        filas.append((pd.to_datetime(semana.group(1), format="%d%b%Y"), float(numeros[0]), float(numeros[1])))
    return pd.DataFrame(filas, columns=["semana", "nino12_sst", "nino12_ssta"])


def nino12_disponible(fechas, nino12, rezago_dias=REZAGO_NINO12_DIAS):
    """La última anomalía semanal de Niño 1+2 publicada en cada fecha (centro de la semana + rezago)."""
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)), name="fecha")
    publicada = nino12.assign(publicada=nino12["semana"] + pd.Timedelta(days=rezago_dias)).sort_values("publicada")
    unido = pd.merge_asof(fechas.to_frame().reset_index().sort_values("fecha"), publicada[["publicada", "nino12_ssta"]],
                          left_on="fecha", right_on="publicada")
    return unido.sort_values("index").set_index("index")["nino12_ssta"].rename("nino12_ssta")


def bronze_nino(raiz=None, descargar=_pedir):
    icen = _guardar_crudo(raiz, "icen.txt", URL_ICEN, descargar(URL_ICEN))
    nino12 = _guardar_crudo(raiz, "nino12_semanal.txt", URL_NINO12_SEMANAL, descargar(URL_NINO12_SEMANAL))
    return icen, nino12


# --- Clima (ERA5 vía Open-Meteo) --------------------------------------------------------------------------------

def url_era5(lat, lon, desde, hasta, modelo=MODELO_ERA5):
    parametros = {"latitude": lat, "longitude": lon, "start_date": f"{desde}", "end_date": f"{hasta}",
                  "hourly": "temperature_2m,apparent_temperature,relative_humidity_2m", "models": modelo,
                  "timezone": "America/Lima"}
    return f"{URL_ERA5}?{urllib.parse.urlencode(parametros)}"


def _cubre(archivo, consulta):
    """Si lo ya bajado sirve para `consulta`: mismo modelo y coordenadas, y fechas que contienen las pedidas."""
    procedencia = archivo.with_name(archivo.name + ".procedencia.json")
    if not (archivo.exists() and procedencia.exists()):
        return False
    previa = json.loads(procedencia.read_text())
    return (all(previa.get(clave) == consulta[clave] for clave in ("modelo", "latitud", "longitud"))
            and previa.get("desde", "9999-12-31") <= consulta["desde"] and previa.get("hasta", "") >= consulta["hasta"])


def bronze_era5(raiz=None, ciudades=CIUDADES, desde=INICIO, hasta=None, descargar=_pedir, progreso=print):
    """Una consulta por ciudad a Open-Meteo (ERA5 horario, hora de Lima).

    Una ciudad ya bajada se repite solo si lo guardado no cubre lo pedido: otro modelo, otras coordenadas o menos
    fechas (al correrlo otro día, `hasta` avanza y se rehace con la historia completa).
    """
    hasta = hasta or (dt.date.today() - dt.timedelta(days=7))  # ERA5 llega con unos días de retraso
    for area, lugares in ciudades.items():
        for ciudad, (lat, lon) in lugares.items():
            nombre = f"era5/{area}_{ciudad.lower()}.json"
            consulta = {"modelo": MODELO_ERA5, "latitud": lat, "longitud": lon, "desde": f"{desde}",
                        "hasta": f"{hasta}"}
            if _cubre(_ruta(raiz, "exogenas/bronze", nombre), consulta):
                continue
            url = url_era5(lat, lon, desde, hasta)
            contenido = descargar(url)
            json.loads(contenido)  # que sea JSON válido antes de guardarlo
            _guardar_crudo(raiz, nombre, url, contenido, **consulta)
            progreso(f"ERA5 {area}/{ciudad}: listo")


def leer_era5(texto):
    horario = json.loads(texto)["hourly"]
    df = pd.DataFrame(horario).rename(columns={"time": "fecha_hora"})
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    return df


def temperatura_por_area(raiz=None, ciudades=CIUDADES, pesos=None):
    """Temperatura horaria por área: media (o media ponderada con `pesos[area][ciudad]`) de sus ciudades."""
    carpeta = _ruta(raiz, "exogenas/bronze/era5", "x").parent
    areas = {}
    for area, lugares in ciudades.items():
        series = {c: leer_era5((carpeta / f"{area}_{c.lower()}.json").read_text()).set_index("fecha_hora")
                  ["temperature_2m"] for c in lugares}
        tabla = pd.DataFrame(series)
        w = pd.Series({c: (pesos or {}).get(area, {}).get(c, 1.0) for c in lugares})
        areas[area] = (tabla * w).sum(axis=1, min_count=len(lugares)) / w.sum()
    return pd.DataFrame(areas).rename_axis("fecha_hora").reset_index()


# --- Calidad de suministro (SAIDI/SAIFI de Osinergmin) ----------------------------------------------------------

def bronze_saidi(raiz=None, descargar=_pedir):
    return _guardar_crudo(raiz, "saidi_saifi.csv", URL_SAIDI, descargar(URL_SAIDI))


def leer_saidi(contenido):
    """El CSV de Osinergmin: un mes por fila y sistema eléctrico, con el SAIDI y el SAIFI totales y por origen."""
    df = pd.read_csv(io.BytesIO(contenido) if isinstance(contenido, bytes) else contenido, encoding="utf-8-sig")
    df["mes"] = pd.to_datetime(df["MES"].astype(str), format="%Y%m")
    columnas = {"CODIGO_EMPRESA": "empresa", "NOMBRE_EMPRESA": "nombre_empresa", "COD_SIST_ELEC": "sistema",
                "NOM_SIST_ELEC": "nombre_sistema"}
    medidas = [c for c in df.columns if c.startswith(("SAIDI", "SAIFI"))]
    salida = df.rename(columns=columnas)[["mes", *columnas.values(), *medidas]]
    return salida.rename(columns={c: c.lower() for c in medidas})


def saidi_por_area(saidi, empresa_area, columna_empresa="nombre_empresa"):
    """SAIDI mensual por área: mediana de sus sistemas. `empresa_area` tiene `empresa_coes` y `area`.

    La mediana, y no la media, porque unos pocos sistemas rurales con cortes largos no deben mover todo el área.
    Los sistemas de empresas sin área asignada quedan fuera, y se cuentan en la columna `sin_area`.
    """
    clave = saidi[columna_empresa].str.upper().str.replace(r"[^A-Z0-9 ]", "", regex=True).str.strip()
    mapa = empresa_area.assign(clave=empresa_area["empresa_coes"].str.upper()
                               .str.replace(r"[^A-Z0-9 ]", "", regex=True).str.strip())
    unido = saidi.assign(clave=clave).merge(mapa[["clave", "area"]], on="clave", how="left")
    por_area = unido.dropna(subset=["area"]).groupby(["mes", "area"])["saidi"].median().unstack("area")
    por_area["sin_area"] = unido[unido["area"].isna()].groupby("mes").size()
    return por_area.fillna({"sin_area": 0}).reset_index()


# --- Fallas (eventos relevantes del COES) -----------------------------------------------------------------------

def url_eventos(anio):
    parametros = {"FechaInicio": f"01/01/{anio}", "FechaFin": f"01/01/{anio + 1}", "IdTipoEvento": 0,
                  "Version": "N", "IdTipoEmpresa": 0, "IdEmpresa": 0, "IdFamilia": 0, "IndInterrupcion": -1}
    return f"{URL_EVENTOS}?{urllib.parse.urlencode(parametros)}"


def bronze_eventos(raiz=None, desde_anio=INICIO.year, hasta_anio=None, descargar=_pedir, progreso=print):
    """Un Excel por año. El año en curso se vuelve a bajar siempre; los cerrados, solo si faltan."""
    hasta_anio = hasta_anio or dt.date.today().year
    for anio in range(desde_anio, hasta_anio + 1):
        nombre = f"eventos/{anio}.xlsx"
        if _ruta(raiz, "exogenas/bronze", nombre).exists() and anio < dt.date.today().year:
            continue
        _guardar_crudo(raiz, nombre, url_eventos(anio), descargar(url_eventos(anio)))
        progreso(f"Eventos {anio}: listo")


def _fecha_hora(valor):
    if isinstance(valor, dt.datetime):
        return pd.Timestamp(valor)
    return pd.to_datetime(valor, dayfirst=True, errors="coerce")


def leer_eventos(archivo):
    """Los eventos de un año: la cabecera es la fila con la celda "Empresa", en la columna que sea."""
    libro = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
    try:
        filas = list(libro[libro.sheetnames[0]].iter_rows(values_only=True))
    finally:
        libro.close()

    def columna_empresa(fila):
        return next((j for j, c in enumerate(fila or ()) if isinstance(c, str) and c.strip() == "Empresa"), None)

    i = next(i for i, fila in enumerate(filas) if columna_empresa(fila) is not None)
    j = columna_empresa(filas[i])
    nombres = ["empresa", "ubicacion", "familia", "equipo", "inicio", "final", "descripcion"]
    datos = [fila[j:j + 7] for fila in filas[i + 1:] if len(fila) > j and fila[j]]
    df = pd.DataFrame(datos, columns=nombres)
    for columna in ("inicio", "final"):
        df[columna] = df[columna].map(_fecha_hora)
    return df.drop_duplicates().reset_index(drop=True)


def fallas_en_curso(fechas, eventos, duracion_max=DURACION_MAX_FALLA):
    """Cuántos eventos estaban en curso en cada fecha. Sin área: el total del SEIN.

    Un evento cuenta desde su inicio hasta su final, pero como mucho `duracion_max`: en el registro hay
    indisponibilidades de meses o años (en 2023, un evento empieza en 2021 y otro termina en 2026) que no son
    fallas de la operación. Se recorta y no se descarta, porque en el momento de predecir no se sabe cuánto
    va a durar un evento que acaba de empezar.
    """
    claves = [c for c in ("empresa", "ubicacion", "equipo", "inicio", "final") if c in eventos.columns]
    validos = eventos.dropna(subset=["inicio", "final"]).drop_duplicates(subset=claves)  # un evento, una vez
    validos = validos[validos["final"] >= validos["inicio"]]
    final = np.minimum(validos["final"].to_numpy(), (validos["inicio"] + duracion_max).to_numpy())
    t = pd.to_datetime(np.asarray(fechas)).to_numpy()
    inicio = np.sort(validos["inicio"].to_numpy())
    final = np.sort(final)
    return pd.Series(np.searchsorted(inicio, t, side="right") - np.searchsorted(final, t, side="right"),
                     name="fallas_en_curso")


def saidi_disponible(fechas, saidi_mensual, dia_publicacion=7):
    """El último SAIDI mensual publicado en cada fecha: el de m−2 desde el día `dia_publicacion`, el de m−3 antes.

    Osinergmin publica con ~5 semanas de rezago (el corte del 7 de mayo trajo marzo). `saidi_mensual` es una serie
    con el primer día de cada mes como índice.
    """
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)))
    rezago = np.where(fechas.dt.day >= dia_publicacion, 2, 3)
    meses = (fechas.dt.to_period("M") - rezago).dt.to_timestamp()
    return pd.Series(saidi_mensual.reindex(meses).to_numpy(), index=fechas.index, name="saidi")


def silver_exogenas(raiz=None, ciudades=CIUDADES, progreso=print):
    """Las exógenas del bronze como tablas ordenadas en <datos>/exogenas/silver/."""
    bronze = _ruta(raiz, "exogenas/bronze", "x").parent
    tablas = {
        "icen": leer_icen((bronze / "icen.txt").read_text(encoding="utf-8", errors="replace")),
        "nino12_semanal": leer_nino12_semanal((bronze / "nino12_semanal.txt").read_text()),
        "temperatura_areas": temperatura_por_area(raiz, ciudades),
        "saidi_saifi": leer_saidi((bronze / "saidi_saifi.csv").read_bytes()),
        # Un evento que cruza de un año a otro aparece en los dos archivos: se deja una vez
        "eventos_coes": pd.concat([leer_eventos(a).assign(anio_archivo=int(a.stem))
                                   for a in sorted((bronze / "eventos").glob("*.xlsx"))], ignore_index=True)
        .drop_duplicates(subset=["empresa", "ubicacion", "equipo", "inicio", "final"]),
    }
    for nombre, tabla in tablas.items():
        destino = _ruta(raiz, "exogenas/silver", f"{nombre}.parquet")
        _reemplazar(destino, lambda r, t=tabla: t.to_parquet(r, index=False))
        progreso(f"{nombre}: {len(tabla):,} filas")
    return _ruta(raiz, "exogenas/silver", "x").parent
