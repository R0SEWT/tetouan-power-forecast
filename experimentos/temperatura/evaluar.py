"""Evaluación: ¿la temperatura pronosticada con umbral reduce el error del pico diario del Centro en días cálidos?

Medida principal (escrita antes de mirar 2025): el error absoluto medio del pico diario del Centro a 24 h (|máximo
pronosticado − máximo real| de los 48 periodos del día objetivo) en el 10 % y el 20 % de días más cálidos de cada año,
por la temperatura media ERA5 del día objetivo en el área. También la hora del pico (|hora pronosticada − real|) y el
error con signo del pico. Guardas: MAE y sesgo globales por área y horizonte, y días normales (el 80 % restante) no
empeoran. IC 95 % por bootstrap de semanas (lunes a domingo del día objetivo, 2,000 réplicas).

Lo que se elige se elige con 2025; 2026 y el tramo en vivo solo se reportan.

Uso: python -m experimentos.temperatura.evaluar   (escribe tablas en reportes/sein/temperatura/)
"""

import numpy as np
import pandas as pd

from experimentos.temperatura import comun as c
from experimentos.temperatura import correccion as cr
from experimentos.temperatura import panel as pn

N_BOOT = 2000
NOMBRES = {
    "c2": "Chronos-2 ajustado", "comb": "Combinación", "rf": "Random Forest", "xgb": "XGBoost + Simons (guardado)",
    "xgb_s": "XGBoost + Simons", "xgb_s_tobs": "XGB + temp. (entrena observada)",
    "xgb_s_tobs_oraculo": "XGB + temp. observada (oráculo)", "xgb_s_tmix": "XGB + temp. (entrena mixta)",
    "xgb_s_tcdd": "XGB + grados sobre umbral", "c2cdd": "Chronos-2 ajustado + grados (covariable)",
    "c2fija_tp_cdd": "Chronos-2 + corrección fija (grados)", "c2fija_tp_dcdd": "Chronos-2 + corrección fija (cambio)",
    "c2linea_tp_cdd": "Chronos-2 + corrección en línea (grados)",
    "c2linea_tp_dcdd": "Chronos-2 + corrección en línea (cambio)",
    "c2linea_oraculo": "Chronos-2 + corrección en línea, temp. observada (oráculo)",
    "comb_tmix": "Combinación con XGB + temp. (mixta)", "comb_tcdd": "Combinación con XGB + grados",
    "comb_tobs": "Combinación con XGB + temp. (observada)", "c2_s2": "Chronos-2 ajustado, semilla 2",
    "c2_s3": "Chronos-2 ajustado, semilla 3",
}
# Cada candidato se compara con su base (la misma familia sin temperatura) y con Chronos-2 ajustado
BASE = {"xgb_s_tobs": "xgb_s", "xgb_s_tobs_oraculo": ("xgb_s", "xgb_s_tobs"), "xgb_s_tmix": "xgb_s", "xgb_s_tcdd": "xgb_s",
        "c2cdd": "c2", "c2fija_tp_cdd": "c2", "c2linea_oraculo": "c2linea_tp_cdd", "c2fija_tp_dcdd": "c2", "c2linea_tp_cdd": "c2", "c2linea_tp_dcdd": "c2",
        "comb_tmix": "comb_s", "comb_tcdd": "comb_s", "comb_tobs": "comb_s", "c2_s2": "c2", "c2_s3": "c2",
        "xgb": "xgb_s", "comb": "c2", "rf": "c2", "xgb_s": "c2", "comb_s": "c2"}


def temperatura_dia():
    """Media diaria por área: ERA5 y, para los días que ERA5 todavía no cubre, el desfase 0 de GFS (casi un
    análisis) llevado al nivel de ERA5. Más la anomalía frente a una climatología de 2016–2024 (tres armónicos)."""
    era5 = c.era5_horaria()
    pron = c.pronostico_ajustado(era5=era5)
    obs, ana = c.diarias(era5), c.diarias(pron[0])
    filas = []
    for area in c.AREAS:
        t = obs[area]["media"].combine_first(ana[area]["media"]).dropna()
        doy = t.index.day_of_year.to_numpy()
        w = 2 * np.pi * doy / 365.25
        X = np.column_stack([np.ones(len(t))] + [f(k * w) for k in (1, 2, 3) for f in (np.cos, np.sin)])
        m = t.index < c.FIN_AJUSTE
        b = np.linalg.lstsq(X[m], t.to_numpy()[m], rcond=None)[0]
        fuente = np.where(t.index.isin(obs[area]["media"].dropna().index), "era5", "gfs_analisis")
        filas.append(pd.DataFrame({"dia": t.index, "area": area.upper(), "temp_dia": t.to_numpy(),
                                   "anom_dia": t.to_numpy() - X @ b, "fuente_temp": fuente}))
    return pd.concat(filas, ignore_index=True)


def continuos_c2(dem):
    """Chronos-2 ajustado por (horizonte, área, objetivo) de 2025 al último día con real, sin cortes."""
    tabla = pd.read_parquet(pn.GUARDADOS["c2"])
    partes = []
    for h, paso in c.PASOS.items():
        partes.append(pd.DataFrame({"horizonte": h, "area": tabla["area"], "origen": tabla["DateTime"],
                                    "objetivo": tabla["DateTime"] + paso * c.PASO, "pred": tabla[f"pred_{paso}"]}))
    hist = pd.concat(partes, ignore_index=True)
    reg = pd.read_parquet(c.RAIZ / "reportes" / "sein" / "en_vivo" / "pronosticos.parquet")
    reg = reg[reg["modelo"] == "chronos2ftcal"][["horizonte", "area", "origen", "objetivo", "pred"]]
    clave = ["horizonte", "area", "objetivo"]
    todo = pd.concat([hist, reg[~reg.set_index(clave).index.isin(hist.set_index(clave).index)]], ignore_index=True)
    largo = dem.stack()
    todo["real"] = largo.reindex(pd.MultiIndex.from_arrays([todo["objetivo"], todo["area"]])).to_numpy()
    todo["dia"] = pn.dia_objetivo(todo["objetivo"])
    todo["bloque"] = cr.bloque(todo["objetivo"])
    return todo


def armar(progreso=print):
    """El panel con todos los modelos, las variables pronosticadas de cada origen y las correcciones."""
    dem = pn.demanda()
    p = pn.panel()
    v_pron = pd.read_parquet(c.SALIDA / "variables_pronostico.parquet").rename(columns={"DateTime": "origen"})
    v_obs = pd.read_parquet(c.SALIDA / "variables_observada.parquet")
    p = p.merge(v_pron, on=["horizonte", "area", "origen"], how="left")
    # (b) corrección fija: errores de Chronos-2 zero-shot 2016–2024
    res = cr.residuos_zero_shot(v_obs, dem)
    betas_fijas = {}
    for variable in ("tp_cdd", "tp_dcdd"):
        betas = cr.ajuste_fijo(res, variable)
        cr.aplicar_fija(p, betas, variable)
        betas_fijas[variable] = betas
    progreso("β fijas (zero-shot 2016–2024):", {k: {kk: np.round(vv, 4).tolist() for kk, vv in b.items()}
                                                 for k, b in betas_fijas.items()})
    # (b) corrección en línea con los errores de Chronos-2 ajustado desde 2025
    cont = continuos_c2(dem).merge(v_pron, on=["horizonte", "area", "origen"], how="left")
    betas_linea = {}
    for variable in ("tp_cdd", "tp_dcdd"):
        _, betas_linea[variable] = cr.aplicar_en_linea(p, cont, variable)
    # La misma corrección en línea con la temperatura observada (oráculo): mide lo que cuesta el error del pronóstico
    obs = v_obs.rename(columns={"DateTime": "origen", "tp_cdd": "tp_cdd_obs"})[["horizonte", "area", "origen",
                                                                                 "tp_cdd_obs"]]
    p = p.merge(obs, on=["horizonte", "area", "origen"], how="left")
    cont = cont.merge(obs, on=["horizonte", "area", "origen"], how="left")
    cr.aplicar_en_linea(p, cont, "tp_cdd_obs", nombre="c2linea_oraculo")
    # Combinaciones con el peso fijado en 2025 (como la combinación del proyecto)
    pesos = {"comb_s": pn.combinar(p, "c2", "xgb_s", "comb_s")}
    for k, x in (("comb_tmix", "xgb_s_tmix"), ("comb_tcdd", "xgb_s_tcdd"), ("comb_tobs", "xgb_s_tobs")):
        if f"pred_{x}" in p:
            pesos[k] = pn.combinar(p, "c2", x, k)
    return p, {"fijas": betas_fijas, "linea": betas_linea, "pesos": pesos, "residuos_zero_shot": res}


def modelos(p):
    return [m.removeprefix("pred_") for m in p.columns if m.startswith("pred_")]


def diario(p, temp):
    """Una fila por (tramo, horizonte, área, modelo, día objetivo) con los 48 periodos: MAE, sesgo y pico."""
    filas = []
    claves = ["tramo", "horizonte", "area", "dia"]
    completos = p.groupby(claves)["real"].transform("size") == 48
    p = p[completos & p["real"].notna()].sort_values(claves + ["objetivo"])
    real = p.groupby(claves)["real"]
    base = pd.DataFrame({"real": real.mean(), "real_max": real.max(),
                         "hora_real": real.apply(lambda s: (s.to_numpy().argmax() + 1) / 2)})
    for m in modelos(p):
        col = f"pred_{m}"
        g = p[claves + ["real", col]].copy()
        ok = g.groupby(claves)[col].transform(lambda s: s.notna().all())
        g = g[ok]
        if g.empty:
            continue
        e = g[col] - g["real"]
        g = g.assign(ae=e.abs(), e=e)
        agg = g.groupby(claves).agg(mae=("ae", "mean"), sesgo=("e", "mean"), pred_max=(col, "max"))
        agg["hora_pred"] = g.groupby(claves)[col].apply(lambda s: (s.to_numpy().argmax() + 1) / 2)
        filas.append(agg.reset_index().assign(modelo=m))
    d = pd.concat(filas, ignore_index=True).merge(base.reset_index(), on=claves)
    d["error_pico"] = d["pred_max"] - d["real_max"]
    d["error_pico_abs"] = d["error_pico"].abs()
    d["error_hora_pico"] = (d["hora_pred"] - d["hora_real"]).abs()
    d = d.merge(temp, on=["dia", "area"], how="left")
    d["semana"] = d["dia"].dt.to_period("W").dt.start_time
    # Días cálidos dentro de cada tramo y área (con el mismo conjunto de días para todos los modelos)
    dias_t = d.drop_duplicates(["tramo", "horizonte", "area", "dia"])
    for q, nombre in ((0.9, "top10"), (0.8, "top20")):
        corte = dias_t.groupby(["tramo", "horizonte", "area"])["temp_dia"].quantile(q).rename(f"corte_{nombre}")
        d = d.join(corte, on=["tramo", "horizonte", "area"])
        d[nombre] = d["temp_dia"] >= d[f"corte_{nombre}"]
        corte_a = dias_t.groupby(["tramo", "horizonte", "area"])["anom_dia"].quantile(q).rename(f"cortea_{nombre}")
        d = d.join(corte_a, on=["tramo", "horizonte", "area"])
        d[f"{nombre}_anom"] = d["anom_dia"] >= d[f"cortea_{nombre}"]
    d["normal"] = ~d["top20"]
    d["todos"] = True
    return d


def bootstrap(dif, semana, n=N_BOOT, semilla=0):
    """Media de las diferencias diarias con IC 95 % remuestreando semanas enteras."""
    df = pd.DataFrame({"d": dif, "s": semana}).dropna()
    if df.empty:
        return np.nan, np.nan, np.nan
    s = df.groupby("s")["d"].agg(["sum", "count"])
    sumas, cuentas = s["sum"].to_numpy(), s["count"].to_numpy()
    idx = np.random.default_rng(semilla).integers(0, len(s), size=(n, len(s)))
    medias = sumas[idx].sum(axis=1) / cuentas[idx].sum(axis=1)
    return float(df["d"].mean()), *np.percentile(medias, [2.5, 97.5])


def comparar(d, subconjuntos=("todos", "top10", "top20", "normal", "top10_anom", "top20_anom"),
             metricas=("error_pico_abs", "error_pico", "error_hora_pico", "mae", "sesgo"), contra=None):
    """Para cada modelo y su base (o `contra`), la media de cada métrica y la diferencia con IC por semanas."""
    filas = []
    claves = ["tramo", "horizonte", "area", "dia"]
    for (tramo, h, a), g in d.groupby(["tramo", "horizonte", "area"]):
        anchos = g.pivot_table(index=claves, columns="modelo", values=list(metricas))
        info = g.drop_duplicates(claves).set_index(claves)
        for m in g["modelo"].unique():
            ref = contra or BASE.get(m)
            refs = {ref} if isinstance(ref, str) or ref is None else set(ref)
            for base in (refs | {"c2"}) - {None, m}:
                if (metricas[0], base) not in anchos:
                    continue
                for sub in subconjuntos:
                    k = info.index[info[sub].reindex(info.index).fillna(False).to_numpy(bool)]
                    k = k.intersection(anchos.index)
                    if len(k) == 0:
                        continue
                    sem = info.loc[k, "semana"].to_numpy()
                    fila = {"tramo": tramo, "horizonte": h, "area": a, "modelo": m, "base": base, "subconjunto": sub}
                    ok = anchos.loc[k, (metricas[0], m)].notna() & anchos.loc[k, (metricas[0], base)].notna()
                    fila["dias"] = int(ok.sum())
                    for met in metricas:
                        x, y = anchos.loc[k, (met, m)], anchos.loc[k, (met, base)]
                        fila[met] = float(x[ok].mean())
                        fila[f"{met}_base"] = float(y[ok].mean())
                        dif, bajo, alto = bootstrap((x - y)[ok].to_numpy(), sem[ok.to_numpy()])
                        fila[f"d_{met}"], fila[f"d_{met}_bajo"], fila[f"d_{met}_alto"] = dif, bajo, alto
                    filas.append(fila)
    return pd.DataFrame(filas)


def main():
    p, extra = armar()
    temp = temperatura_dia()
    d = diario(p, temp)
    comp = comparar(d)
    c.guardar(d, "diario.parquet")
    c.guardar(comp, "comparacion.csv")
    c.guardar(temp, "temperatura_dia.csv")
    betas = [{"tipo": "fija", "variable": v, "horizonte": h, "area": a, **{f"beta_{i}": b[i] for i in range(4)}}
             for v, bs in extra["fijas"].items() for (h, a), b in bs.items()]
    c.guardar(pd.DataFrame(betas), "betas_fijas.csv")
    linea = pd.concat([b.assign(variable=v) for v, b in extra["linea"].items()])
    c.guardar(linea, "betas_en_linea.csv")
    pesos = [{"combinacion": k, "horizonte": h, "area": a, "peso_chronos": w}
             for k, ps in extra["pesos"].items() for (h, a), w in ps.items()]
    c.guardar(pd.DataFrame(pesos), "pesos_combinaciones.csv")
    sel = comp[(comp["area"] == "CENTRO") & (comp["horizonte"] == "24h") & comp["subconjunto"].isin(["top10", "top20"])]
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.max_rows", 500):
        print(sel[["tramo", "subconjunto", "modelo", "base", "dias", "error_pico_abs", "error_pico_abs_base",
                   "d_error_pico_abs", "d_error_pico_abs_bajo", "d_error_pico_abs_alto", "d_error_pico"]].round(1))
    return p, d, comp, extra


if __name__ == "__main__":
    main()
