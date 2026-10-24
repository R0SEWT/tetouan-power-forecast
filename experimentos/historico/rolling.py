"""Variantes de objetivo y de variables evaluadas con origen móvil mensual (docs/historico.md, opciones 1 y 5).

Lee el silver del medallón y guarda resultados_rolling_<series>.csv en <datos>/reportes/historico/.
Uso: python -m experimentos.historico.rolling [Z1,Z2,Z3,S12]
"""

import sys
import time

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from tetouan_power_forecast.medallon import _reemplazar, cargar_silver, raiz_datos
from tetouan_power_forecast.variables import FERIADOS, RAMADAN

H = 6  # horizonte: 6 periodos de 10 minutos
DAY = 144
WEEK = 1008
ZC = {1: "Zone 1 Power Consumption", 2: "Zone 2 Power Consumption", 3: "Zone 3 Power Consumption"}
WEATHER = ["Temperature", "Humidity", "Wind Speed", "general diffuse flows", "diffuse flows"]


def base_frame():
    df = cargar_silver().sort_values("DateTime").reset_index(drop=True)
    df["S12"] = df[ZC[1]] + df[ZC[2]]
    return df


def guardar(resultados, nombre, carpeta="historico"):
    """Escribe en un temporal y lo mueve al final: una corrida cortada no deja un CSV a medias."""
    destino = raiz_datos() / "reportes" / carpeta / nombre
    destino.parent.mkdir(parents=True, exist_ok=True)
    _reemplazar(destino, lambda ruta: resultados.to_csv(ruta, index=False))
    print("resultados en", destino)


def features(df, serie, otras, variante, feriados=FERIADOS, ramadanes=(RAMADAN,)):
    """Devuelve X, el objetivo que aprende el modelo, el consumo real en t+6 y las referencias.

    `feriados` y `ramadanes` (pares de fechas de inicio y fin) cambian para otro sistema, como Ceuta.
    """
    f = pd.DataFrame(index=df.index)
    t = df["DateTime"].dt
    y = df[serie]
    f["Hour"] = t.hour
    f["MinuteOfDay"] = t.hour * 60 + t.minute
    f["DayOfWeek"] = t.day_of_week
    f["IsWeekend"] = (t.day_of_week >= 5).astype(int)
    # Calendario de t, como en el gold; el de t+6 se conoce de antemano y queda para el modelado
    f["Time_Sin"] = np.sin(2 * np.pi * f["MinuteOfDay"] / 1440)
    f["Time_Cos"] = np.cos(2 * np.pi * f["MinuteOfDay"] / 1440)
    f["Week_Sin"] = np.sin(2 * np.pi * f["DayOfWeek"] / 7)
    f["Week_Cos"] = np.cos(2 * np.pi * f["DayOfWeek"] / 7)
    if variante["anual"]:
        f["Day"] = t.day
        f["Month"] = t.month
        f["DayOfYear"] = t.day_of_year
        f["Year_Sin"] = np.sin(2 * np.pi * (t.day_of_year - 1) / 365)
        f["Year_Cos"] = np.cos(2 * np.pi * (t.day_of_year - 1) / 365)
    for w in WEATHER:
        f[w] = df[w]
    if variante["extra"]:
        fecha_obj = (df["DateTime"] + pd.Timedelta(minutes=10 * H)).dt.normalize()
        f["Feriado"] = fecha_obj.isin(pd.to_datetime(list(feriados))).astype(int)
        en_ramadan = pd.Series(False, index=df.index)
        for inicio, fin in ramadanes:
            en_ramadan |= (fecha_obj >= inicio) & (fecha_obj <= fin)
        f["Ramadan"] = en_ramadan.astype(int)
        f["T_mean_24h"] = df["Temperature"].rolling(DAY).mean()

    m24 = y.rolling(DAY).mean()
    norm = variante["objetivo"] == "ratio"
    escala = m24 if norm else 1.0
    for s in [serie, *otras]:
        esc_s = df[s].rolling(DAY).mean() if norm else 1.0
        for lag in [0, 1, 2, 6]:
            f[f"{s}_l{lag}"] = df[s].shift(lag) / esc_s
    f["own_lag24h"] = y.shift(DAY - H) / escala
    f["own_rm1h"] = y.rolling(6).mean() / escala
    f["own_rs1h"] = y.rolling(6).std() / escala
    if variante["extra"]:
        f["own_lag1w"] = y.shift(WEEK - H) / escala
        f["own_lag1w_t"] = y.shift(WEEK) / escala  # cambio semanal hasta t
    if norm:
        f["m24_level_rel"] = m24 / y.rolling(WEEK).mean()

    yt = y.shift(-H)
    if variante["objetivo"] == "nivel":
        yobj = yt
    elif variante["objetivo"] == "delta":
        yobj = yt - y
    else:
        yobj = yt / m24
    base = pd.DataFrame({
        "persistencia": y, "ayer": y.shift(DAY - H), "semana": y.shift(WEEK - H), "y0": y, "m24": m24})
    return f, yobj, yt, base


def reconstruir(variante, pred, base):
    """Lleva la predicción del objetivo de la variante de vuelta a kW."""
    if variante["objetivo"] == "nivel":
        return pred
    if variante["objetivo"] == "delta":
        return base["y0"].to_numpy() + pred
    return base["m24"].to_numpy() * pred


def modelo():
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, early_stopping=False,
                                         random_state=0)


VARIANTES = {
    "V0_repo_nivel": {"anual": True, "extra": False, "objetivo": "nivel"},
    "V1_sin_anual": {"anual": False, "extra": False, "objetivo": "nivel"},
    "V2_sin_anual+sem+fer+T24": {"anual": False, "extra": True, "objetivo": "nivel"},
    "V3_delta": {"anual": False, "extra": True, "objetivo": "delta"},
    "V4_ratio_m24": {"anual": False, "extra": True, "objetivo": "ratio"},
}


def plegados(fechas):
    """Origen móvil mensual: entrena con todo lo anterior al mes (menos H pasos) y prueba el mes."""
    out = []
    for m in range(3, 13):
        ini = pd.Timestamp(2017, m, 1)
        fin = pd.Timestamp(2018, 1, 1) if m == 12 else pd.Timestamp(2017, m + 1, 1)
        tr = np.where(fechas < ini - pd.Timedelta(minutes=10 * H))[0]
        te = np.where((fechas >= ini) & (fechas < fin))[0]
        out.append((f"{m:02d}", tr, te))
    # Prueba: el último 15 %, entrenando con el 85 % anterior
    n = len(fechas)
    c2 = int(n * 0.85)
    out.append(("test_oficial", np.arange(0, c2 - H), np.arange(c2, n)))
    return out


def _errores(real, pred):
    return {"MAE": np.mean(np.abs(real - pred)), "MAPE": 100 * np.mean(np.abs(real - pred) / real)}


def correr(series_cfg, variantes, df):
    filas = []
    for nombre_serie, (serie, otras) in series_cfg.items():
        prep = {vn: features(df, serie, otras, v) for vn, v in variantes.items()}
        # Filas válidas comunes a todas las variantes y referencias
        valid = np.ones(len(df), bool)
        for X, yobj, _, base in prep.values():
            valid &= X.notna().all(axis=1).to_numpy() & yobj.notna().to_numpy()
            valid &= base[["semana", "ayer"]].notna().all(axis=1).to_numpy()
        idx = np.where(valid)[0]
        fechas = df["DateTime"].iloc[idx].reset_index(drop=True)
        for fold, tr, te in plegados(fechas):
            for vn, v in variantes.items():
                X, yobj, yt, base = prep[vn]
                Xv, yo, ytv, bv = X.iloc[idx], yobj.iloc[idx], yt.iloc[idx], base.iloc[idx]
                mdl = modelo().fit(Xv.iloc[tr], yo.iloc[tr])
                p = reconstruir(v, mdl.predict(Xv.iloc[te]), bv.iloc[te])
                filas.append({"serie": nombre_serie, "fold": fold, "metodo": vn,
                              **_errores(ytv.iloc[te].to_numpy(), p)})
            bt = base.iloc[idx].iloc[te]
            real = yt.iloc[idx].iloc[te].to_numpy()
            for b in ["persistencia", "ayer", "semana"]:
                filas.append({"serie": nombre_serie, "fold": fold, "metodo": "naive_" + b,
                              **_errores(real, bt[b].to_numpy())})
            print(nombre_serie, fold, "ok", flush=True)
    return pd.DataFrame(filas)


SERIES = {
    "Z1": (ZC[1], [ZC[2], ZC[3]]),
    "Z2": (ZC[2], [ZC[1], ZC[3]]),
    "Z3": (ZC[3], [ZC[1], ZC[2]]),
    "S12": ("S12", [ZC[3]]),
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    t0 = time.time()
    cfg = {k: SERIES[k] for k in argv[0].split(",")} if argv else SERIES
    res = correr(cfg, VARIANTES, base_frame())
    guardar(res, "resultados_rolling_" + "_".join(cfg) + ".csv")
    print("segundos:", round(time.time() - t0))


if __name__ == "__main__":
    main()
