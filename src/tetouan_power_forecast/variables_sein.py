"""Dataset del objetivo en razón para la demanda de cada área del SEIN, cada 30 minutos, a 1 h o a 24 h.

Una fila por momento t (el final de un periodo de 30 minutos, como lo publica el COES): las variables que se
conocían en t, la media de 24 h del área (la escala que usa `ModeloRazon`), la demanda real en t+H y las
referencias ingenuas. Las variables están agrupadas como en la ablación de la spec (§8.3): `M0` (demanda y
calendario), `clima`, `nino`, `fallas` y `saidi`.

Regla de información (spec §6): cada exógena entra con lo que ya se había publicado en t. La excepción declarada
es el supuesto de colaboración entre el COES y ENFEN: a 24 h, la temperatura de t+H se toma como un pronóstico
recibido, que se simula con la observada más un error.
"""

import numpy as np
import pandas as pd

from tetouan_power_forecast.exogenas import (
    fallas_en_curso,
    icen_disponible,
    nino12_disponible,
    saidi_disponible,
)

PASO = pd.Timedelta(minutes=30)
PERIODOS_DIA = 48
SEMANA = 7 * PERIODOS_DIA
HORIZONTES = {"1h": 2, "24h": 48}
AREAS = ["NORTE", "CENTRO", "SUR"]
ESCALA = "media_24h"
REFERENCIAS = ["persistencia", "ayer", "semana_pasada"]
NO_PREDICTORAS = ["DateTime", "area", "particion", "real", *REFERENCIAS]
CUARENTENA = (pd.Timestamp("2020-03-16"), pd.Timestamp("2020-07-01"))  # estricta; la reactivación, por la tabla
ERROR_PRONOSTICO_TEMP_C = 1.5  # desviación del error simulado del pronóstico a un día (supuesto, spec §13.2)
FIN_CLIMATOLOGIA = pd.Timestamp("2025-01-01")  # la climatología sale solo del entrenamiento
GRUPOS = {
    "clima": ["temp", "temp_media_24h", "temp_anomalia", "temp_objetivo"],
    "nino": ["icen", "nino12_ssta"],
    "fallas": ["fallas_en_curso"],
    "saidi": ["saidi_m2"],
}
VARIANTES = {
    "M0": [],
    "M1": ["clima"],
    "M2": ["clima", "nino"],
    "M3": ["clima", "nino", "fallas"],
    "M4": ["clima", "nino", "fallas", "saidi"],
}


def _relativo(serie, escala, rezagos, prefijo):
    return {f"{prefijo}_t" if r == 0 else f"{prefijo}_t_menos_{r}": serie.shift(r) / escala for r in rezagos}


def _temperatura_conocida(temperatura, area, fechas):
    """La última temperatura horaria del área que ya existía en cada fecha (la de las 01:00 recién a las 01:00).

    Pasado el archivo de clima queda vacía: falta la hora que ya se habría publicado y repetir la última sería
    inventar el dato.
    """
    horaria = temperatura.set_index("fecha_hora")[area.lower()].sort_index().dropna()
    fechas = pd.DatetimeIndex(fechas)
    conocida = horaria.reindex(fechas, method="ffill")
    return conocida.where(fechas < horaria.index.max() + pd.Timedelta(hours=1)).to_numpy()


def _temperatura_interpolada(temperatura, area, fechas):
    """La temperatura del área en cada fecha, interpolada entre horas: solo para el pronóstico de t+H.

    Solo entre dos horas observadas: fuera del archivo de clima queda vacía, sin alargar la última.
    """
    horaria = temperatura.set_index("fecha_hora")[area.lower()].sort_index().dropna()
    unida = horaria.reindex(horaria.index.union(pd.DatetimeIndex(fechas)))
    return unida.interpolate(method="time", limit_area="inside").reindex(pd.DatetimeIndex(fechas)).to_numpy()


def error_pronostico_diario(fechas, sigma, semilla=0):
    """Un error de pronóstico por día de emisión: el COES recibe un pronóstico al día, no uno cada 30 minutos.

    Con ruido independiente cada periodo, la media de 24 h lo promediaría y el supuesto quedaría demasiado
    benigno. La semilla fija hace que entrenamiento, validación y prueba vean el mismo pronóstico degradado.
    """
    dias = pd.Series(pd.to_datetime(np.asarray(fechas))).dt.normalize()
    unicos = np.sort(dias.unique())
    errores = np.random.default_rng(semilla).normal(0, sigma, len(unicos))
    return dias.map(dict(zip(unicos, errores, strict=True))).to_numpy()


def dataset_area(demanda, area, horizonte=2, temperatura=None, icen=None, nino12=None, eventos=None,
                 saidi_area=None, feriados=(), otras_areas=True, error_temp_c=ERROR_PRONOSTICO_TEMP_C, semilla=0,
                 fin_climatologia=FIN_CLIMATOLOGIA):
    """El dataset de un área (`NORTE`, `CENTRO` o `SUR`) para pronosticar t+`horizonte` pasos de 30 minutos.

    `demanda` es el silver del IEOD (`DateTime`, `SEIN`, `NORTE`, `CENTRO`, `SUR`, en MW). Las exógenas son
    opcionales: si falta una, su grupo no se agrega. `saidi_area` es una serie mensual del SAIDI del área (índice:
    primer día del mes). `feriados` es una colección de fechas. La climatología de la temperatura (para la
    anomalía) sale solo de las fechas anteriores a `fin_climatologia`, el fin del entrenamiento.
    """
    df = demanda.sort_values("DateTime").reset_index(drop=True)
    fechas = df["DateTime"]
    t = fechas.dt
    y = df[area].astype(float)
    m24 = y.rolling(PERIODOS_DIA).mean()
    objetivo = fechas + horizonte * PASO
    minuto = t.hour * 60 + t.minute
    minuto_obj = objetivo.dt.hour * 60 + objetivo.dt.minute
    feriados = pd.to_datetime(list(feriados)).normalize() if len(feriados) else pd.DatetimeIndex([])
    columnas = {
        "DateTime": fechas,
        "Hour": t.hour,
        "MinuteOfDay": minuto,
        "DayOfWeek": t.day_of_week,
        "Time_Sin": np.sin(2 * np.pi * minuto / 1440),
        "Time_Cos": np.cos(2 * np.pi * minuto / 1440),
        "Week_Sin": np.sin(2 * np.pi * t.day_of_week / 7),
        "Week_Cos": np.cos(2 * np.pi * t.day_of_week / 7),
        "Obj_Sin": np.sin(2 * np.pi * minuto_obj / 1440),
        "Obj_Cos": np.cos(2 * np.pi * minuto_obj / 1440),
        "DiaSemanaObjetivo": objetivo.dt.day_of_week,
        "FinDeSemanaObjetivo": (objetivo.dt.day_of_week >= 5).astype(int),
        "FeriadoObjetivo": objetivo.dt.normalize().isin(feriados).astype(int),
        "Cuarentena": ((fechas >= CUARENTENA[0]) & (fechas < CUARENTENA[1])).astype(int),
        **_relativo(y, m24, [0, 1, 2, 4], "Area"),
        "Area_ayer": y.shift(PERIODOS_DIA - horizonte) / m24 if horizonte < PERIODOS_DIA else y / m24,
        "Area_semana_pasada": y.shift(SEMANA - horizonte) / m24,
        "Area_media_1h": y.rolling(2).mean() / m24,
        "Area_desv_1h": y.rolling(2).std() / m24,
        "Area_m24_vs_m7d": m24 / y.rolling(SEMANA).mean(),
    }
    if otras_areas:
        for otra in AREAS:
            if otra != area:
                serie = df[otra].astype(float)
                columnas.update(_relativo(serie, serie.rolling(PERIODOS_DIA).mean(), [0, 2], otra.capitalize()))
    if temperatura is not None:
        temp = pd.Series(_temperatura_conocida(temperatura, area, fechas), index=df.index)
        hist = pd.DataFrame({"temp": temp, "hora": t.hour, "mes": t.month})[fechas < pd.Timestamp(fin_climatologia)]
        clima = hist.groupby(["mes", "hora"])["temp"].mean()
        normal = pd.MultiIndex.from_arrays([t.month, t.hour]).map(clima.to_dict().get).astype(float)
        temp_obj = pd.Series(_temperatura_interpolada(temperatura, area, objetivo), index=df.index)
        ruido = error_pronostico_diario(fechas, error_temp_c, semilla)
        columnas.update({
            "temp": temp,
            "temp_media_24h": temp.rolling(PERIODOS_DIA).mean(),
            "temp_anomalia": temp - normal,
            # El pronóstico de t+H que el COES recibiría de ENFEN (supuesto de colaboración, spec §2)
            "temp_objetivo": temp_obj + ruido if horizonte >= PERIODOS_DIA else temp,
        })
    if icen is not None:
        columnas["icen"] = icen_disponible(fechas, icen).to_numpy()
    if nino12 is not None:
        columnas["nino12_ssta"] = nino12_disponible(fechas, nino12).to_numpy()
    if eventos is not None:
        columnas["fallas_en_curso"] = fallas_en_curso(fechas, eventos).to_numpy()
    if saidi_area is not None:
        columnas["saidi_m2"] = saidi_disponible(fechas, saidi_area).to_numpy()
    columnas.update({
        ESCALA: m24,
        "real": y.shift(-horizonte),
        "persistencia": y,
        "ayer": y.shift(PERIODOS_DIA - horizonte) if horizonte < PERIODOS_DIA else y,
        "semana_pasada": y.shift(SEMANA - horizonte),
    })
    datos = pd.DataFrame(columnas)
    datos.insert(1, "area", area)
    return datos


def columnas_variante(datos, variante):
    """Las columnas que ve el modelo en una variante de la ablación (más la escala, que separa `ModeloRazon`)."""
    exogenas = {c for grupo in GRUPOS.values() for c in grupo}
    base = [c for c in datos.columns if c not in NO_PREDICTORAS and c not in exogenas]
    extra = [c for grupo in VARIANTES[variante] for c in GRUPOS[grupo] if c in datos.columns]
    return base + extra


def particion(fechas, horizonte, fin_entrenamiento="2025-01-01", fin_validacion="2026-01-01"):
    """Entrenamiento hasta 2024, validación 2025 y prueba 2026, con un hueco de `horizonte` pasos antes de cada corte."""
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)))
    hueco = horizonte * PASO
    corte1, corte2 = pd.Timestamp(fin_entrenamiento), pd.Timestamp(fin_validacion)
    etiqueta = np.select(
        [fechas < corte1 - hueco, (fechas >= corte1) & (fechas < corte2 - hueco), fechas >= corte2],
        ["entrenamiento", "validacion", "prueba"], default="hueco")
    return etiqueta


def filas_comunes(datos, variantes=tuple(VARIANTES)):
    """Las filas completas para todas las variantes: así M0 a M4 se comparan sobre los mismos periodos."""
    columnas = set(REFERENCIAS) | {"real"}
    for variante in variantes:
        columnas |= set(columnas_variante(datos, variante))
    return datos[datos[sorted(columnas)].notna().all(axis=1)]
