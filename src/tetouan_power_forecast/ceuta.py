"""Ceuta como validación externa: demanda de REE cada 5 minutos desde 2019 y clima de ERA5.

Ceuta es un sistema eléctrico aislado a menos de 40 km de Tetuán, con varios años de datos. Sirve para
probar el pipeline donde Tetuán no alcanza: entrenar con uno, dos o tres años y evaluar en el verano
siguiente (docs/historico.md, opción 8).

Capas, dentro de la misma carpeta de datos que el medallón de Tetuán:

- ceuta/bronze/demanda/AAAA-MM.jsonl: las respuestas de REE sin tocar, una línea por día consultado.
- ceuta/bronze/clima.json: la respuesta de Open-Meteo (ERA5 horario).
- ceuta/silver/ceuta.parquet: hora UTC cada 10 minutos, demanda en kW y clima interpolado, con auditoría.

Las descargas son lentas (una consulta por día) y conviene correrlas en Colab, no en local. Los datos de
REE no se suben a ningún repositorio: su aviso legal solo permite usos académicos que citen la fuente.
"""

import json
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from tetouan_power_forecast.medallon import _reemplazar, _ruta

URL_REE = ("https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula"
           "?curva=CEUTAAU&fecha={fecha}")
URL_CLIMA = "https://archive-api.open-meteo.com/v1/archive"
INICIO = date(2019, 5, 11)  # primer día con datos de Ceuta en el servicio de REE
LATITUD, LONGITUD = 35.889, -5.319  # Ceuta
ZONA_HORARIA = "Europe/Madrid"  # las marcas de REE están en hora local peninsular
SERIE = "Ceuta"
# Variables de ERA5 con el mismo nombre que las del dataset de Tetuán, para reutilizar el pipeline
CLIMA = {
    "temperature_2m": "Temperature",
    "relative_humidity_2m": "Humidity",
    "wind_speed_10m": "Wind Speed",
    "shortwave_radiation": "general diffuse flows",
    "diffuse_radiation": "diffuse flows",
}
FUENTES = {
    "demanda": {
        "fuente": "Red Eléctrica (REE), Seguimiento de la demanda de energía eléctrica, sistema de Ceuta",
        "pagina": "https://demanda.ree.es/visiona/home",
        "servicio": URL_REE,
        "aviso_legal": "https://www.ree.es/es/aviso-legal",
        "uso": "Académico y no comercial, citando a REE como fuente, sin alterar el sentido de los datos e "
               "indicando la fecha de actualización. Los datos crudos no se suben a ningún repositorio.",
    },
    "clima": {
        "fuente": "Open-Meteo Historical Weather API (reanálisis ERA5 de ECMWF)",
        "pagina": "https://open-meteo.com/en/docs/historical-weather-api",
        "licencia": "CC BY 4.0 (citar a Open-Meteo y a ERA5)",
    },
}


def _descargar_texto(url, timeout=60, intentos=3, espera=10):
    peticion = urllib.request.Request(url, headers={"User-Agent": "tetouan-power-forecast (investigación académica)"})
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
                return respuesta.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if intento == intentos:
                raise
            time.sleep(espera * intento)


def parsear_respuesta(texto):
    """Respuesta JSONP de REE → DataFrame con DateTime en UTC (sin zona) y la demanda en MW.

    En el cambio de hora de octubre la hora local de 2:00 a 2:55 aparece dos veces: la primera es horario
    de verano y la segunda, de invierno. En el de marzo esa hora no existe.
    """
    cuerpo = re.search(r"\((\{.*\})\)", texto, re.DOTALL)
    if cuerpo is None:
        raise ValueError("La respuesta de REE no tiene el formato JSONP esperado")
    valores = json.loads(cuerpo.group(1)).get("valoresHorariosGeneracion") or []
    df = pd.DataFrame(valores, columns=["ts", "dem"])
    if df.empty:
        return pd.DataFrame(columns=["DateTime", "dem"])
    local = pd.to_datetime(df["ts"], format="%Y-%m-%d %H:%M")
    verano = ~df["ts"].duplicated(keep="first")  # la primera aparición de una hora repetida es la de verano
    utc = local.dt.tz_localize(ZONA_HORARIA, ambiguous=verano.to_numpy(), nonexistent="shift_forward")
    return pd.DataFrame({"DateTime": utc.dt.tz_convert("UTC").dt.tz_localize(None), "dem": df["dem"].astype(float)})


def _meses(desde, hasta):
    mes = date(desde.year, desde.month, 1)
    while mes <= hasta:
        yield mes
        mes = date(mes.year + mes.month // 12, mes.month % 12 + 1, 1)


def bronze_ceuta(raiz=None, desde=INICIO, hasta=None, descargar=_descargar_texto, pausa=1.0, progreso=print):
    """Baja la demanda de Ceuta día por día y la guarda por mes. Se puede cortar y retomar.

    Un mes ya completo no se vuelve a bajar; el mes en curso se rehace para sumar los días nuevos.
    """
    hasta = hasta or (datetime.now(UTC).date() - timedelta(days=1))
    carpeta = _ruta(raiz, "ceuta/bronze/demanda", "x").parent
    bajados = 0
    for mes in _meses(desde, hasta):
        archivo = carpeta / f"{mes:%Y-%m}.jsonl"
        fin_mes = min(date(mes.year + mes.month // 12, mes.month % 12 + 1, 1) - timedelta(days=1), hasta)
        dias = [mes + timedelta(days=k) for k in range((fin_mes - mes).days + 1) if mes + timedelta(days=k) >= desde]
        if archivo.exists() and len(archivo.read_text().splitlines()) == len(dias):
            continue
        lineas = []
        for dia in dias:
            texto = descargar(URL_REE.format(fecha=f"{dia:%Y-%m-%d}"))
            lineas.append(json.dumps({"fecha": f"{dia:%Y-%m-%d}", "respuesta": texto}, ensure_ascii=False))
            bajados += 1
            if pausa:
                time.sleep(pausa)
        contenido = "\n".join(lineas) + "\n"
        _reemplazar(archivo, lambda ruta, contenido=contenido: ruta.write_text(contenido))
        progreso(f"{mes:%Y-%m}: {len(dias)} días")
    procedencia = {**FUENTES["demanda"], "desde": f"{desde}", "hasta": f"{hasta}",
                   "actualizado_utc": datetime.now(UTC).isoformat(timespec="seconds")}
    texto = json.dumps(procedencia, ensure_ascii=False, indent=2) + "\n"
    _reemplazar(carpeta / "procedencia.json", lambda ruta: ruta.write_text(texto))
    progreso(f"Bronze de Ceuta al día ({bajados} días bajados en esta corrida)")
    return carpeta


def clima_ceuta(raiz=None, desde=INICIO, hasta=None, descargar=_descargar_texto, forzar=False):
    """Clima horario de ERA5 para Ceuta (una sola consulta a Open-Meteo)."""
    destino = _ruta(raiz, "ceuta/bronze", "clima.json")
    if destino.exists() and not forzar:
        return destino
    hasta = hasta or (datetime.now(UTC).date() - timedelta(days=7))  # ERA5 se publica con unos días de retraso
    url = (f"{URL_CLIMA}?latitude={LATITUD}&longitude={LONGITUD}&start_date={desde}&end_date={hasta}"
           f"&hourly={','.join(CLIMA)}&wind_speed_unit=ms&timezone=UTC")
    texto = descargar(url)
    json.loads(texto)  # que sea JSON válido antes de guardarlo
    _reemplazar(destino, lambda ruta: ruta.write_text(texto))
    procedencia = json.dumps({**FUENTES["clima"], "consulta": url,
                              "descargado_utc": datetime.now(UTC).isoformat(timespec="seconds")},
                             ensure_ascii=False, indent=2) + "\n"
    _reemplazar(destino.with_name("clima_procedencia.json"), lambda ruta: ruta.write_text(procedencia))
    return destino


def demanda_10min(bronze):
    """Lee los meses del bronze, quita los solapes entre días y promedia cada 10 minutos (en kW)."""
    partes = []
    for archivo in sorted(bronze.glob("*.jsonl")):
        for linea in archivo.read_text().splitlines():
            if linea.strip():
                partes.append(parsear_respuesta(json.loads(linea)["respuesta"]))
    cinco = pd.concat(partes).drop_duplicates("DateTime").set_index("DateTime").sort_index()["dem"]
    diez = cinco.resample("10min").mean() * 1000  # MW → kW, como el dataset de Tetuán
    return diez.rename(SERIE)


def clima_10min(ruta_clima, indice):
    """Pasa el clima horario de ERA5 a cada 10 minutos por interpolación lineal en el tiempo."""
    datos = json.loads(ruta_clima.read_text())["hourly"]
    horario = pd.DataFrame({nombre: datos[clave] for clave, nombre in CLIMA.items()},
                           index=pd.to_datetime(datos["time"]))
    return horario.reindex(horario.index.union(indice)).interpolate(method="time").reindex(indice)


def auditar_ceuta(df):
    esperado = pd.date_range(df["DateTime"].min(), df["DateTime"].max(), freq="10min")
    faltantes = int(df[SERIE].isna().sum())
    chequeos = [
        ("Un registro cada 10 minutos", len(df) == len(esperado), f"{len(df):,} de {len(esperado):,}"),
        ("Sin fechas repetidas", not df["DateTime"].duplicated().any(), f"{int(df['DateTime'].duplicated().sum())}"),
        ("Demanda sin huecos de más de 1 hora", int(df[SERIE].isna().rolling(7).sum().fillna(0).max()) < 7,
         f"{faltantes:,} intervalos de 10 min sin demanda ({faltantes / len(df):.2%})"),
        ("Demanda positiva", bool((df[SERIE].dropna() > 0).all()), f"{int((df[SERIE] <= 0).sum())} no positivas"),
        ("Clima completo", not df[list(CLIMA.values())].isna().any().any(),
         f"{int(df[list(CLIMA.values())].isna().any(axis=1).sum()):,} intervalos sin clima"),
    ]
    return pd.DataFrame(chequeos, columns=["chequeo", "ok", "detalle"])


def silver_ceuta(raiz=None, forzar=False):
    """Demanda cada 10 minutos en UTC, con el clima, y su auditoría. No corta por huecos: los reporta."""
    destino = _ruta(raiz, "ceuta/silver", "ceuta.parquet")
    if destino.exists() and not forzar:
        return destino
    bronze = _ruta(raiz, "ceuta/bronze/demanda", "x").parent
    demanda = demanda_10min(bronze)
    clima = clima_10min(_ruta(raiz, "ceuta/bronze", "clima.json"), demanda.index)
    df = pd.concat([clima, demanda], axis=1).rename_axis("DateTime").reset_index()
    df = df[df["DateTime"] <= clima.dropna().index.max()]  # hasta donde llega ERA5
    auditoria = auditar_ceuta(df)
    reporte = ["# Auditoría del silver de Ceuta", "",
               f"Registros: {len(df):,} · desde {df['DateTime'].min()} hasta {df['DateTime'].max()} (UTC)", "",
               "| Chequeo | Resultado | Detalle |", "|---|---|---|",
               *(f"| {c} | {'ok' if ok else 'REVISAR'} | {d} |" for c, ok, d in auditoria.itertuples(index=False))]
    destino.with_name("auditoria.md").write_text("\n".join(reporte) + "\n")
    _reemplazar(destino, lambda ruta: df.to_parquet(ruta, index=False))
    return destino


def cargar_silver_ceuta(raiz=None):
    return pd.read_parquet(silver_ceuta(raiz))


def huecos_cortos_rellenos(serie, limite=6):
    """Interpola huecos de hasta `limite` intervalos (1 hora); los más largos quedan enteros como faltantes.

    `interpolate(limit=...)` de pandas rellenaría los primeros intervalos de un hueco largo, por eso se mide
    cada racha de faltantes.
    """
    faltante = serie.isna()
    racha = (faltante != faltante.shift()).cumsum()
    corto = faltante & (faltante.groupby(racha).transform("sum") <= limite)
    return serie.where(~corto, serie.interpolate(limit_area="inside"))
