"""Parte 1 del diagnóstico de sesgo: ¿los errores grandes y la subestimación se concentran en días o noches cálidos,
o es una deriva de nivel sostenida?

Para Chronos-2 ajustado (`c2`), la combinación (`comb`), el XGBoost híbrido en razón (`xgb`) y el Random Forest (`rf`),
a 1 h y 24 h, en 2025, 2026 y el tramo en vivo, por separado. Todo se resume por día objetivo: MAE, sesgo (pronóstico
menos real: negativo es subestimar), error del pico diario y cobertura del rango 10–90.

Uso: python -m experimentos.sesgo.diagnostico   (escribe CSV en reportes/sein/sesgo/)
"""

import holidays
import numpy as np
import pandas as pd

from experimentos.sesgo import comun as c

MODELOS = ["c2", "comb", "xgb", "rf"]
NOMBRES = {"c2": "Chronos-2 ajustado", "comb": "Combinación", "xgb": "XGBoost híbrido (razón)", "rf": "Random Forest",
           "ref": "Mejor referencia"}
UMBRAL_EPISODIO = 0.01  # sesgo diario por debajo de −1 % del nivel del día
DIAS_EPISODIO = 3


def panel():
    p = pd.concat([c.panel_backtest(), c.panel_vivo()], ignore_index=True)
    for m in MODELOS:
        col = "rf" if m == "rf" else f"pred_{m}"
        p[f"e_{m}"] = p[col] - p["real"]
    # La mejor referencia de cada tramo, horizonte y área (la de menor MAE en esas filas)
    p["ref"] = np.nan
    for _, g in p.groupby(["tramo", "horizonte", "area"]):
        mejor = min(c.REFS, key=lambda r: (g[r] - g["real"]).abs().mean())
        p.loc[g.index, "ref"] = g[mejor]
        p.loc[g.index, "ref_nombre"] = mejor
    p["e_ref"] = p["ref"] - p["real"]
    return p


def tipo_dia(dias):
    dias = pd.DatetimeIndex(dias)
    pe = holidays.country_holidays("PE", years=range(2015, 2028))
    tipo = np.where(dias.day_of_week == 6, "domingo", np.where(dias.day_of_week == 5, "sábado", "laborable"))
    return np.where([d in pe for d in dias], "feriado", tipo)


def racha(serie_bool):
    """Días seguidos en que se cumple la condición, contando el de hoy (0 si hoy no se cumple)."""
    salida, n = [], 0
    for v in serie_bool:
        n = n + 1 if v else 0
        salida.append(n)
    return np.array(salida)


def diario(p, temp_diaria=None):
    """Una fila por (tramo, horizonte, área, modelo, día objetivo) con su error y lo que pasaba ese día."""
    temp_diaria = c.temperatura_diaria() if temp_diaria is None else temp_diaria
    filas = []
    claves = ["tramo", "horizonte", "area", "dia"]
    base = p.groupby(claves).agg(n=("real", "size"), real=("real", "mean"), real_max=("real", "max")).reset_index()
    for m in [*MODELOS, "ref"]:
        col = "rf" if m == "rf" else ("ref" if m == "ref" else f"pred_{m}")
        if p[col].isna().all():
            continue
        g = p.assign(ae=p[f"e_{m}"].abs())
        agg = {"mae": ("ae", "mean"), "sesgo": (f"e_{m}", "mean"), "pred_max": (col, "max")}
        if f"q10_{m}" in p:
            dentro = ((g["real"] >= g[f"q10_{m}"]) & (g["real"] <= g[f"q90_{m}"])).astype(float)
            g["dentro"] = dentro.where(g[f"q10_{m}"].notna())
            agg["cobertura"] = ("dentro", "mean")
        d = g[g[col].notna()].groupby(claves).agg(**agg).reset_index()
        filas.append(d.assign(modelo=m))
    d = pd.concat(filas, ignore_index=True).merge(base, on=claves)
    d["error_pico"] = d["pred_max"] - d["real_max"]
    d["sesgo_pct"] = 100 * d["sesgo"] / d["real"]
    d["mae_pct"] = 100 * d["mae"] / d["real"]
    # Lo que pasaba ese día: temperatura del día objetivo, calendario, nivel y crecimiento de la demanda
    t = temp_diaria.sort_values(["area", "dia"]).copy()
    for col in ("temp_media", "temp_min"):
        previa = t.groupby("area")[col].transform(lambda s: s.shift(1).rolling(7, min_periods=5).mean())
        t[f"d_{col}"] = t[col] - previa  # frente a la semana anterior: el calor «nuevo» que el modelo no vio
    d = d.merge(t, on=["dia", "area"], how="left")
    d["tipo_dia"] = tipo_dia(d["dia"])
    d["mes"] = d["dia"].dt.month
    dem = c.demanda()
    nivel = dem.groupby(c.dia_objetivo(dem.index)).mean()
    largo = nivel.stack().rename("x")
    sem = largo.groupby(level=1).shift(7)
    crec = (largo / sem - 1).rename("crec_semanal")
    d = d.join(crec, on=["dia", "area"])
    d["crec_semanal"] = 100 * d["crec_semanal"]
    # Deciles y grupos dentro de cada tramo y área (la ordenación es relativa: 2026 entero es cálido)
    grupo = d.groupby(["tramo", "horizonte", "area", "modelo"])
    for col, nombre in (("anom_media", "decil_anom"), ("anom_min", "decil_anom_min"), ("real", "quintil_nivel")):
        q = 10 if nombre.startswith("decil") else 5
        d[nombre] = grupo[col].transform(lambda s, q=q: pd.qcut(s.rank(method="first"), q, labels=False) + 1)
    d["calido"] = grupo["anom_media"].transform(lambda s: s >= s.quantile(2 / 3))
    d["racha_calida"] = 0
    for _, g in d.sort_values("dia").groupby(["tramo", "horizonte", "area", "modelo"]):
        d.loc[g.index, "racha_calida"] = racha(g["calido"].to_numpy())
    d["top10_calido"] = grupo["anom_media"].transform(lambda s: s >= s.quantile(0.9))
    d["top10_noche"] = grupo["anom_min"].transform(lambda s: s >= s.quantile(0.9))
    d["semana"] = d["dia"].dt.to_period("W").dt.start_time
    return d


def bootstrap_grupos(valor, grupo, semana, n=2000, semilla=0):
    """Media de `valor` donde `grupo` es verdadero menos donde es falso, con IC 95 % remuestreando semanas enteras."""
    df = pd.DataFrame({"v": valor, "g": grupo.astype(bool), "s": semana}).dropna()
    s = df.groupby(["s", "g"])["v"].agg(["sum", "count"]).unstack(fill_value=0)
    sumas, cuentas = s["sum"].to_numpy(), s["count"].to_numpy()
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(s), size=(n, len(s)))
    tot_s, tot_c = sumas[idx].sum(axis=1), cuentas[idx].sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        dif = tot_s[:, 1] / tot_c[:, 1] - tot_s[:, 0] / tot_c[:, 0]
    punto = df.loc[df.g, "v"].mean() - df.loc[~df.g, "v"].mean()
    return punto, *np.nanpercentile(dif, [2.5, 97.5])


def calidos_frente_al_resto(d, columna="top10_calido"):
    filas = []
    for (tramo, h, area, m), g in d.groupby(["tramo", "horizonte", "area", "modelo"]):
        if g[columna].sum() < 2:
            continue
        fila = {"tramo": tramo, "horizonte": h, "area": area, "modelo": m, "dias_calidos": int(g[columna].sum()),
                "dias": len(g)}
        for v in ("mae", "sesgo", "error_pico"):
            fila[f"{v}_calidos"] = g.loc[g[columna], v].mean()
            fila[f"{v}_resto"] = g.loc[~g[columna], v].mean()
            dif, bajo, alto = bootstrap_grupos(g[v], g[columna], g["semana"])
            fila[f"dif_{v}"], fila[f"dif_{v}_bajo"], fila[f"dif_{v}_alto"] = dif, bajo, alto
        filas.append(fila)
    return pd.DataFrame(filas)


def por_grupo(d, columna):
    """MAE, sesgo y error del pico (en MW y en % del nivel) por cada valor de `columna`."""
    agg = d.groupby(["tramo", "horizonte", "area", "modelo", columna]).agg(
        dias=("mae", "size"), mae=("mae", "mean"), sesgo=("sesgo", "mean"), mae_pct=("mae_pct", "mean"),
        sesgo_pct=("sesgo_pct", "mean"), error_pico=("error_pico", "mean"),
        error_pico_abs=("error_pico", lambda x: x.abs().mean()), anom_media=("anom_media", "mean"),
        anom_min=("anom_min", "mean"))
    return agg.reset_index()


def autocorrelacion(d, rezagos=14):
    filas = []
    for (tramo, h, area, m), g in d.groupby(["tramo", "horizonte", "area", "modelo"]):
        s = g.set_index("dia")["sesgo"].asfreq("D")
        filas.append({"tramo": tramo, "horizonte": h, "area": area, "modelo": m,
                      **{f"r{k}": s.autocorr(k) for k in range(1, rezagos + 1)}})
    return pd.DataFrame(filas)


def episodios(d, umbral=UMBRAL_EPISODIO, minimo=DIAS_EPISODIO):
    """Rachas de ≥ `minimo` días seguidos con sesgo diario < −umbral × nivel del día (subestimación sostenida)."""
    filas = []
    for (tramo, h, area, m), g in d.sort_values("dia").groupby(["tramo", "horizonte", "area", "modelo"]):
        g = g.set_index("dia")
        bajo = (g["sesgo"] < -umbral * g["real"]).reindex(pd.date_range(g.index.min(), g.index.max()), fill_value=False)
        grupo = (bajo != bajo.shift()).cumsum()
        for _, tramo_dias in bajo[bajo].groupby(grupo[bajo]):
            if len(tramo_dias) < minimo:
                continue
            x = g.loc[tramo_dias.index.intersection(g.index)]
            filas.append({"tramo": tramo, "horizonte": h, "area": area, "modelo": m, "inicio": tramo_dias.index[0],
                          "fin": tramo_dias.index[-1], "dias": len(tramo_dias), "sesgo": x["sesgo"].mean(),
                          "sesgo_pct": x["sesgo_pct"].mean(), "mae": x["mae"].mean(),
                          "anom_media": x["anom_media"].mean(), "anom_min": x["anom_min"].mean(),
                          "d_temp_media": x["d_temp_media"].mean(), "d_temp_min": x["d_temp_min"].mean(),
                          "crec_semanal": x["crec_semanal"].mean(), "pct_calidos": 100 * x["calido"].mean(),
                          "feriados": int((x["tipo_dia"] == "feriado").sum()),
                          "meses": ",".join(sorted({f"{v:02d}" for v in x["mes"]}))})
    return pd.DataFrame(filas)


def regresion_sesgo(d, n=1000, semilla=0):
    """Sesgo diario (% del nivel) frente a calor (anomalía del día y su cambio frente a la semana previa), al sesgo
    del día anterior y al crecimiento semanal de la demanda. Coeficientes estandarizados con IC por semanas."""
    variables = ["anom_media", "anom_min", "d_temp_media", "d_temp_min", "sesgo_ayer", "crec_semanal"]
    filas = []
    for (tramo, h, area, m), g in d.sort_values("dia").groupby(["tramo", "horizonte", "area", "modelo"]):
        g = g.set_index("dia").asfreq("D")
        g["sesgo_ayer"] = g["sesgo_pct"].shift(1)
        g = g.dropna(subset=["sesgo_pct", *variables])
        if len(g) < 15:
            continue
        X = (g[variables] - g[variables].mean()) / g[variables].std()
        y = (g["sesgo_pct"] - g["sesgo_pct"].mean()) / g["sesgo_pct"].std()
        Xm = np.column_stack([np.ones(len(X)), X.to_numpy()])
        beta = np.linalg.lstsq(Xm, y.to_numpy(), rcond=None)[0]
        r2 = 1 - ((y.to_numpy() - Xm @ beta) ** 2).sum() / (y.to_numpy() ** 2).sum()
        semanas = g["semana"].to_numpy()
        unicas = np.unique(semanas)
        rng = np.random.default_rng(semilla)
        boots = []
        for _ in range(n):
            elegidas = rng.choice(unicas, len(unicas))
            idx = np.concatenate([np.flatnonzero(semanas == s) for s in elegidas])
            boots.append(np.linalg.lstsq(Xm[idx], y.to_numpy()[idx], rcond=None)[0])
        boots = np.array(boots)
        fila = {"tramo": tramo, "horizonte": h, "area": area, "modelo": m, "dias": len(g), "r2": r2}
        for j, v in enumerate(variables, start=1):
            fila[v] = beta[j]
            fila[f"{v}_bajo"], fila[f"{v}_alto"] = np.percentile(boots[:, j], [2.5, 97.5])
        filas.append(fila)
    return pd.DataFrame(filas)


def r2_por_bloque(d):
    """¿Qué explica el sesgo diario (% del nivel)? R² de tres bloques por separado: calor (anomalías del día y su
    cambio frente a la semana previa), persistencia (el sesgo de ayer) y salto de nivel (crecimiento frente a hace una
    semana, que no se conoce al emitir)."""
    bloques = {"calor": ["anom_media", "anom_min", "d_temp_media", "d_temp_min"], "persistencia": ["sesgo_ayer"],
               "salto_de_nivel": ["crec_semanal"]}
    filas = []
    for (tramo, h, area, m), g in d.sort_values("dia").groupby(["tramo", "horizonte", "area", "modelo"]):
        g = g.set_index("dia").asfreq("D")
        g["sesgo_ayer"] = g["sesgo_pct"].shift(1)
        fila = {"tramo": tramo, "horizonte": h, "area": area, "modelo": m}
        for nombre, cols in bloques.items():
            x = g.dropna(subset=["sesgo_pct", *cols])
            if len(x) < 15:
                fila[nombre] = np.nan
                continue
            X = np.column_stack([np.ones(len(x)), x[cols].to_numpy()])
            y = x["sesgo_pct"].to_numpy()
            res = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]
            fila[nombre] = 1 - (res ** 2).sum() / ((y - y.mean()) ** 2).sum()
            fila["dias"] = len(x)
        filas.append(fila)
    return pd.DataFrame(filas)


def sesgo_por_hora(p, d):
    """Sesgo medio por hora del día objetivo, en días cálidos (tercio superior) y en el resto."""
    marca = d[d["modelo"] == "c2"][["tramo", "horizonte", "area", "dia", "calido"]]
    x = p.merge(marca, on=["tramo", "horizonte", "area", "dia"])
    x["hora"] = (x["objetivo"] - c.PASO).dt.hour
    filas = []
    for m in ["c2", "comb", "xgb"]:
        if x[f"e_{m}"].notna().any():
            g = x.groupby(["tramo", "horizonte", "area", "calido", "hora"])[f"e_{m}"].mean().rename("sesgo")
            filas.append(g.reset_index().assign(modelo=m))
    return pd.concat(filas, ignore_index=True)


def main():
    p = panel()
    d = diario(p)
    c.guardar(d, "diario")
    salidas = {
        "calidos_vs_resto": calidos_frente_al_resto(d, "top10_calido"),
        "noches_calidas_vs_resto": calidos_frente_al_resto(d, "top10_noche"),
        "por_decil_anomalia": por_grupo(d, "decil_anom"),
        "por_decil_anomalia_minima": por_grupo(d, "decil_anom_min"),
        "por_racha_calida": por_grupo(d.assign(racha=d["racha_calida"].clip(upper=5)), "racha"),
        "por_tipo_dia": por_grupo(d, "tipo_dia"),
        "por_mes": por_grupo(d, "mes"),
        "por_nivel": por_grupo(d, "quintil_nivel"),
        "autocorrelacion": autocorrelacion(d),
        "episodios": episodios(d),
        "regresion_sesgo": regresion_sesgo(d),
        "r2_por_bloque": r2_por_bloque(d),
        "sesgo_por_hora": sesgo_por_hora(p, d),
    }
    for nombre, tabla in salidas.items():
        print(nombre, c.guardar(tabla, nombre))
    return d, salidas


if __name__ == "__main__":
    main()
