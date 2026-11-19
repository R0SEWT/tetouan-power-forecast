"""Datos comunes del diagnóstico de sesgo: el panel de pronósticos con su real y la temperatura con su anomalía.

El panel tiene una fila por (tramo, horizonte, área, origen): el real, las tres referencias ingenuas, el Random Forest
elegido (`fijo_M0`) y los pronósticos de Chronos-2 ajustado (`c2`), de la combinación (`comb`) y del XGBoost híbrido
en razón (`xgb`), con sus cuantiles 10 y 90. `dia` es el día del periodo objetivo (los periodos se fechan por su fin,
así que el de las 00:00 es del día anterior), como `fecha_objetivo` en el registro en vivo.

Tramos: «2025» y «2026» son las filas de los notebooks 02 y 03 (las mismas que las tablas del proyecto); «vivo» son
los días objetivo del registro en vivo (23-oct → último día con real). Para que las correcciones en línea tengan su
historia sin cortes, `errores_continuos` arma el error diario de Chronos-2 ajustado de 2025 hasta el último día con
real, juntando los parquet de los experimentos y el registro en vivo.
"""

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from tetouan_power_forecast import en_vivo
from tetouan_power_forecast.medallon import raiz_datos

RAIZ = raiz_datos()
FUND = RAIZ / "reportes" / "sein" / "fundacionales"
SALIDA = RAIZ / "reportes" / "sein" / "sesgo"
PASO = pd.Timedelta(minutes=30)
PASOS = {"1h": 2, "24h": 48}
AREAS = ["NORTE", "CENTRO", "SUR"]
MODELOS = {"c2": "chronos2ftcal_c2048", "comb": "combinacion_c2048", "xgb": "xgb_simons_c2048"}
TRAMOS = {"2025": "modelado/predicciones_validacion", "2026": "prueba_2026/predicciones"}
REFS = ["persistencia", "ayer", "semana_pasada"]
FIN_CLIMA = pd.Timestamp("2025-01-01")
# Las ciudades de exogenas.CIUDADES, en el mismo orden (Norte: Piura, Chiclayo, Trujillo; Centro: Lima; Sur: Arequipa, Tacna)
COORDS = [(-5.194, -80.632), (-6.771, -79.841), (-8.112, -79.029), (-12.046, -77.043), (-16.399, -71.535),
          (-18.006, -70.246)]
GRUPOS_CIUDAD = {"norte": [0, 1, 2], "centro": [3], "sur": [4, 5]}


def dia_objetivo(objetivo):
    return (pd.DatetimeIndex(objetivo) - PASO).normalize()


def demanda():
    """La demanda cada 30 minutos: silver histórica + capa en vivo (la de la tubería diaria)."""
    return en_vivo.serie_completa(RAIZ).set_index("DateTime")[AREAS]


def _pronosticos(nombre):
    return pd.read_parquet(FUND / f"{nombre}.parquet")


def panel_backtest():
    """Las filas de 2025 y 2026 de los notebooks 02 y 03 con los tres modelos alineados."""
    pron = {k: _pronosticos(v) for k, v in MODELOS.items()}
    partes = []
    for tramo, prefijo in TRAMOS.items():
        for horizonte, paso in PASOS.items():
            for area in AREAS:
                base = pd.read_csv(RAIZ / "reportes" / "sein" / f"{prefijo}_{horizonte}_{area.lower()}.csv",
                                   parse_dates=["DateTime"])[["DateTime", "real", *REFS, "fijo_M0"]]
                base = base.rename(columns={"DateTime": "origen", "fijo_M0": "rf"})
                for k, tabla in pron.items():
                    t = tabla[tabla["area"] == area].set_index("DateTime")
                    cols = {f"pred_{paso}": f"pred_{k}", f"q10_{paso}": f"q10_{k}", f"q90_{paso}": f"q90_{k}"}
                    base = base.join(t[list(cols)].rename(columns=cols), on="origen")
                base.insert(0, "area", area)
                base.insert(0, "horizonte", horizonte)
                base.insert(0, "tramo", tramo)
                base["objetivo"] = base["origen"] + paso * PASO
                partes.append(base)
    panel = pd.concat(partes, ignore_index=True)
    panel["dia"] = dia_objetivo(panel["objetivo"])
    assert panel.filter(like="pred_").notna().all().all(), "faltan pronósticos en el panel"
    return panel


def panel_vivo():
    """Los días objetivo del registro en vivo (Chronos-2 ajustado), con real y referencias."""
    seg = pd.read_parquet(RAIZ / "reportes" / "sein" / "en_vivo" / "seguimiento.parquet")
    seg = seg[seg["modelo"] == "chronos2ftcal"]
    salida = pd.DataFrame({
        "tramo": "vivo", "horizonte": seg["horizonte"], "area": seg["area"], "origen": seg["origen"],
        "real": seg["real"], "persistencia": seg["persistencia"], "ayer": seg["ayer"],
        "semana_pasada": seg["semana_pasada"], "rf": np.nan, "pred_c2": seg["pred"], "q10_c2": seg["q10"],
        "q90_c2": seg["q90"], "objetivo": seg["objetivo"], "dia": pd.to_datetime(seg["fecha_objetivo"]),
        "tipo": seg["tipo"],
    })
    return salida.reset_index(drop=True)


def errores_continuos(dem=None):
    """Pronóstico de Chronos-2 ajustado por objetivo, de 2025 al último día con real, sin cortes.

    Hasta el último origen de los parquet (22-oct-2026) sale de ahí; después, del registro en vivo (que para los
    orígenes comunes da lo mismo, ver `verificar` en en_vivo). Una fila por (horizonte, área, objetivo).
    """
    dem = demanda() if dem is None else dem
    largo = dem.stack()
    tabla = _pronosticos(MODELOS["c2"])
    partes = []
    for horizonte, paso in PASOS.items():
        p = pd.DataFrame({"horizonte": horizonte, "area": tabla["area"], "origen": tabla["DateTime"],
                          "objetivo": tabla["DateTime"] + paso * PASO, "pred": tabla[f"pred_{paso}"],
                          "q10": tabla[f"q10_{paso}"], "q90": tabla[f"q90_{paso}"]})
        partes.append(p)
    hist = pd.concat(partes, ignore_index=True)
    seg = pd.read_parquet(RAIZ / "reportes" / "sein" / "en_vivo" / "pronosticos.parquet")
    seg = seg[seg["modelo"] == "chronos2ftcal"][["horizonte", "area", "origen", "objetivo", "pred", "q10", "q90"]]
    clave = ["horizonte", "area", "objetivo"]
    todo = pd.concat([hist, seg[~seg.set_index(clave).index.isin(hist.set_index(clave).index)]], ignore_index=True)
    todo["real"] = largo.reindex(pd.MultiIndex.from_arrays([todo["objetivo"], todo["area"]])).to_numpy()
    todo["dia"] = dia_objetivo(todo["objetivo"])
    return todo.sort_values(["horizonte", "area", "objetivo"]).reset_index(drop=True)


# ---- Temperatura ---------------------------------------------------------------------------------------------------


def _bajar(url, destino):
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        pedido = urllib.request.Request(url, headers={"User-Agent": "tpf-diagnostico"})
        with urllib.request.urlopen(pedido, timeout=120) as r:
            destino.write_bytes(r.read())
    return json.loads(destino.read_text())


def _por_area(respuesta):
    tiempo = pd.to_datetime(respuesta[0]["hourly"]["time"])
    m = np.array([r["hourly"]["temperature_2m"] for r in respuesta], dtype=float)
    return pd.DataFrame({a: m[i].mean(axis=0) for a, i in GRUPOS_CIUDAD.items()}, index=tiempo)


def temperatura_reciente(desde="2026-10-01", hasta="2026-11-13", cache=None):
    """Open-Meteo para después del archivo de clima: ERA5 (el mismo de la silver) mientras exista y, para los últimos
    días, el análisis de su API de pronóstico (`past_days`, modelo «best match»: no es una estación), corrido al nivel
    de ERA5 con la diferencia media por área y hora en los días comunes. Dos peticiones en total.
    """
    cache = Path(cache or SALIDA / "open_meteo")
    lat = ",".join(f"{a}" for a, _ in COORDS)
    lon = ",".join(f"{b}" for _, b in COORDS)
    era5 = _bajar("https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(
        {"latitude": lat, "longitude": lon, "start_date": desde, "end_date": hasta, "hourly": "temperature_2m",
         "models": "era5", "timezone": "America/Lima"}), cache / f"era5_{desde}_{hasta}.json")
    analisis = _bajar("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(
        {"latitude": lat, "longitude": lon, "past_days": 45, "forecast_days": 2, "hourly": "temperature_2m",
         "timezone": "America/Lima"}), cache / f"analisis_hasta_{hasta}.json")
    e, a = _por_area(era5).dropna(), _por_area(analisis)
    comun = e.index.intersection(a.index)
    ajuste = (e.loc[comun] - a.loc[comun]).groupby(comun.hour).mean()
    a_ajustado = a + ajuste.reindex(a.index.hour).to_numpy()
    resto = a_ajustado[(a_ajustado.index > e.index.max()) & (a_ajustado.index < pd.Timestamp(hasta) + pd.Timedelta(days=1))]
    salida = pd.concat([e.assign(fuente="era5"), resto.assign(fuente="analisis_ajustado")])
    return salida, ajuste


def temperatura():
    """Temperatura horaria por área (silver ERA5 + Open-Meteo reciente) con su climatología ≤2024 y anomalía.

    Climatología: por hora del día, tres armónicos del día del año ajustados con 2016–2024 (una media por hora y
    día del año, suavizada).
    """
    silver = pd.read_parquet(RAIZ / "exogenas" / "silver" / "temperatura_areas.parquet").set_index("fecha_hora")
    reciente, _ = temperatura_reciente()
    nueva = reciente[reciente.index > silver.index.max()].drop(columns="fuente")
    t = pd.concat([silver, nueva]).sort_index()
    t = t[~t.index.duplicated()]
    fuente = pd.Series("era5_silver", index=t.index)
    fuente.loc[reciente.index[reciente.index > silver.index.max()]] = reciente.loc[
        reciente.index > silver.index.max(), "fuente"].to_numpy()
    doy = t.index.dayofyear.to_numpy()
    hora = t.index.hour.to_numpy()
    w = 2 * np.pi * doy / 365.25
    X = np.column_stack([np.ones(len(t))] + [f(k * w) for k in (1, 2, 3) for f in (np.cos, np.sin)])
    entren = (t.index < FIN_CLIMA)
    clima = pd.DataFrame(index=t.index, columns=t.columns, dtype=float)
    for area in t.columns:
        y = t[area].to_numpy()
        for h in range(24):
            m = (hora == h) & entren & ~np.isnan(y)
            beta, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
            sel = hora == h
            clima.loc[sel, area] = X[sel] @ beta
    anomalia = t - clima
    return t, clima, anomalia, fuente


def temperatura_diaria():
    """Por día y área: media, mínima (la de la madrugada, 00–07 h) y media nocturna (19–24 h), con sus anomalías."""
    t, clima, anom, fuente = temperatura()
    filas = []
    for area in t.columns:
        df = pd.DataFrame({"t": t[area], "c": clima[area], "a": anom[area]})
        df["dia"] = df.index.normalize()
        madrugada = df[df.index.hour < 7]
        noche = df[df.index.hour >= 19]
        d = pd.DataFrame({
            "temp_media": df.groupby("dia")["t"].mean(), "anom_media": df.groupby("dia")["a"].mean(),
            "temp_min": madrugada.groupby("dia")["t"].min(),
            "anom_min": madrugada.groupby("dia")["t"].min() - madrugada.groupby("dia")["c"].min(),
            "temp_noche": noche.groupby("dia")["t"].mean(), "anom_noche": noche.groupby("dia")["a"].mean(),
        })
        d["area"] = area.upper()
        filas.append(d.reset_index())
    diaria = pd.concat(filas, ignore_index=True)
    diaria["fuente"] = diaria["dia"].map(fuente.groupby(fuente.index.normalize()).last())
    return diaria


def guardar(df, nombre):
    SALIDA.mkdir(parents=True, exist_ok=True)
    df.to_csv(SALIDA / f"{nombre}.csv", index=False)
    return SALIDA / f"{nombre}.csv"


if os.environ.get("TPF_SESGO_DEBUG"):
    print(RAIZ)
