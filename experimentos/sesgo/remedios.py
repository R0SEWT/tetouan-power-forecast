"""Parte 2: remedios baratos para Chronos-2 ajustado, elegidos solo con 2025 (2026 y el tramo en vivo solo se reportan).

1. Corrección de sesgo en línea con la regla de información del modo en vivo: para el día objetivo X solo se usan los
   errores de los días objetivo ≤ X − 1 (al emitir X ya llegó el real de X − 1 y nada más). Variantes: ventana de
   1, 3, 7, 14 o 28 días o exponencial; global o por media hora del día; aditiva o en razón; con media o mediana;
   con o sin amortiguación.
2. Rango adaptativo para la cobertura nominal del 80 %: escala del rango ajustada en línea (ACI, por lado) o los
   cuantiles móviles de los errores de cada borde (estilo CQR), con la misma regla de información.
3. Una prueba mínima de corrección por temperatura (si la parte 1 muestra efecto de calor).

Uso: python -m experimentos.sesgo.remedios
"""

import itertools

import numpy as np
import pandas as pd

from experimentos.sesgo import comun as c
from experimentos.sesgo import diagnostico as dg

N_BOOT = 2000
ALFA = 0.2  # rango 10–90


# ---- Matrices día × media hora ---------------------------------------------------------------------------------------

def matrices(errores):
    """{(horizonte, área): (pred, real)} como tablas día objetivo × media hora (0 = 00:30, 47 = 24:00)."""
    e = errores.copy()
    e["franja"] = ((e["objetivo"] - c.PASO) - e["dia"]) // c.PASO
    salida = {}
    for (h, a), g in e.groupby(["horizonte", "area"]):
        dias = pd.date_range(g["dia"].min(), g["dia"].max())
        pred = g.pivot_table(index="dia", columns="franja", values="pred").reindex(dias)
        real = g.pivot_table(index="dia", columns="franja", values="real").reindex(dias)
        q10 = g.pivot_table(index="dia", columns="franja", values="q10").reindex(dias)
        q90 = g.pivot_table(index="dia", columns="franja", values="q90").reindex(dias)
        salida[(h, a)] = {"pred": pred, "real": real, "q10": q10, "q90": q90}
    return salida


# ---- Corrección de sesgo ---------------------------------------------------------------------------------------------

VARIANTES = []
for tipo, nivel, estimador, lam in itertools.product(["aditiva", "razon"], ["global", "hora"], ["media", "mediana"],
                                                      [1.0, 0.5]):
    for ventana in [1, 3, 7, 14, 28]:
        if estimador == "mediana" and ventana < 3:
            continue
        VARIANTES.append({"tipo": tipo, "nivel": nivel, "estimador": estimador, "ventana": ventana, "lam": lam})
    if estimador == "media":
        for vida in [3, 7]:
            VARIANTES.append({"tipo": tipo, "nivel": nivel, "estimador": "exponencial", "ventana": vida, "lam": lam})


def nombre_variante(v):
    if v is None:
        return "sin corrección"
    est = {"media": "media", "mediana": "mediana", "exponencial": "exp"}[v["estimador"]]
    vent = f"vida {v['ventana']} d" if v["estimador"] == "exponencial" else f"{v['ventana']} d"
    return f"{v['tipo']} · {v['nivel']} · {est} · {vent} · λ={v['lam']:g}"


def _rodar(df, v):
    """Estadístico de la ventana que termina en el día anterior (shift 1): la regla de información."""
    previo = df.shift(1)
    if v["estimador"] == "exponencial":
        return previo.ewm(halflife=v["ventana"], min_periods=1, ignore_na=True).mean()
    rod = previo.rolling(v["ventana"], min_periods=1)
    return rod.median() if v["estimador"] == "mediana" else rod.mean()


def correccion(m, v):
    """La corrección de cada día × media hora para una variante: devuelve (sumar, multiplicar) a aplicar al pronóstico.

    Aditiva: pred − λ·b, con b el error medio (pronóstico − real) de la ventana. En razón: pred·(1 + λ·(r − 1)), con
    r = real / pronóstico de la ventana. «global» usa el promedio del día; «hora», cada media hora por separado.
    """
    pred, real = m["pred"], m["real"]
    if v["tipo"] == "aditiva":
        err = pred - real
        diario = err.mean(axis=1) if v["nivel"] == "global" else err
        b = _rodar(diario.to_frame() if v["nivel"] == "global" else diario, v)
        b = b.iloc[:, 0] if v["nivel"] == "global" else b
        b = b.fillna(0)
        resta = (pd.DataFrame(np.repeat(b.to_numpy()[:, None], pred.shape[1], 1), index=pred.index,
                              columns=pred.columns) if v["nivel"] == "global" else b)
        return -v["lam"] * resta, pd.DataFrame(1.0, index=pred.index, columns=pred.columns)
    validos = pred.notna() & real.notna()
    if v["nivel"] == "global":
        razon_dia = (real.where(validos).sum(axis=1) / pred.where(validos).sum(axis=1)).where(validos.any(axis=1))
        r = _rodar(razon_dia.to_frame(), v).iloc[:, 0].fillna(1.0)
        r = pd.DataFrame(np.repeat(r.to_numpy()[:, None], pred.shape[1], 1), index=pred.index, columns=pred.columns)
    else:
        r = _rodar((real / pred).where(validos), v).fillna(1.0)
    return pd.DataFrame(0.0, index=pred.index, columns=pred.columns), 1 + v["lam"] * (r - 1)


def aplicar(panel, mats, v, columnas=("pred_c2", "q10_c2", "q90_c2")):
    """El panel con las columnas corregidas (`*_corr`). Solo para Chronos-2 ajustado (el modelo en vivo)."""
    salida = panel.copy()
    franja = ((salida["objetivo"] - c.PASO) - salida["dia"]) // c.PASO
    for col in columnas:
        salida[col.replace("_c2", "_corr")] = salida[col]
    if v is None:
        return salida
    for (h, a), m in mats.items():
        suma, mult = correccion(m, v)
        filas = (salida["horizonte"] == h) & (salida["area"] == a)
        idx_dia = suma.index.get_indexer(salida.loc[filas, "dia"])
        idx_fr = franja[filas].to_numpy().astype(int)
        ok = idx_dia >= 0
        s = np.zeros(filas.sum())
        k = np.ones(filas.sum())
        s[ok] = suma.to_numpy()[idx_dia[ok], idx_fr[ok]]
        k[ok] = mult.to_numpy()[idx_dia[ok], idx_fr[ok]]
        for col in columnas:
            nueva = col.replace("_c2", "_corr")
            salida.loc[filas, nueva] = salida.loc[filas, col].to_numpy() * k + s
    return salida


def evaluar_variantes(panel, mats, tramo="2025"):
    filas = []
    base = panel[panel["tramo"] == tramo]
    mae0 = base.assign(ae=(base["pred_c2"] - base["real"]).abs()).groupby(["horizonte", "area"])["ae"].mean()
    for i, v in enumerate([None, *VARIANTES]):
        p = aplicar(base, mats, v, columnas=("pred_c2",))
        g = p.assign(ae=(p["pred_corr"] - p["real"]).abs(), e=p["pred_corr"] - p["real"])
        r = g.groupby(["horizonte", "area"]).agg(mae=("ae", "mean"), sesgo=("e", "mean")).reset_index()
        r["razon_mae"] = r["mae"] / mae0.reindex(pd.MultiIndex.from_frame(r[["horizonte", "area"]])).to_numpy()
        r["variante"] = nombre_variante(v)
        r["id"] = i - 1
        filas.append(r)
    return pd.concat(filas, ignore_index=True)


def elegir(tabla):
    """La variante con menor razón de MAE media entre las tres áreas, por horizonte (una sola para todas las áreas)."""
    medias = tabla.groupby(["horizonte", "id", "variante"])["razon_mae"].agg(["mean", "max"]).reset_index()
    elegidas = {}
    for h, g in medias.groupby("horizonte"):
        mejor = g.sort_values("mean").iloc[0]
        elegidas[h] = int(mejor["id"])
    return elegidas, medias


# ---- Rango adaptativo ------------------------------------------------------------------------------------------------

METODOS_RANGO = ([{"metodo": "modelo"}]
                 + [{"metodo": "aci", "gamma": g} for g in (0.02, 0.05, 0.1, 0.2, 0.5)]
                 + [{"metodo": "cqr", "ventana": w} for w in (7, 14, 28, 56)]
                 + [{"metodo": "residuos", "ventana": w} for w in (7, 14, 28, 56)])


def nombre_rango(r):
    if r["metodo"] == "modelo":
        return "cuantiles del modelo"
    if r["metodo"] == "aci":
        return f"ACI por lado (γ={r['gamma']:g})"
    if r["metodo"] == "cqr":
        return f"cuantiles móviles de cada borde ({r['ventana']} d)"
    return f"cuantiles móviles de los residuos ({r['ventana']} d)"


def rango(m, suma, mult, r):
    """Bordes del rango corregido por día × media hora, con la regla de información (solo días ≤ X − 1).

    `m` trae pred, real, q10 y q90 del modelo; la corrección de sesgo (suma, mult) se aplica antes a los tres.
    - modelo: los cuantiles del modelo, corridos con la corrección.
    - aci: cada borde se aleja o acerca del centro con un factor que se ajusta cada día según cuántos periodos
      del día anterior quedaron fuera por ese lado (meta 10 %): log f ← log f + γ·(fuera − 0.10).
    - cqr: a cada borde se le suma el cuantil 10 % (o 90 %) de real − borde en los últimos W días.
    - residuos: centro ± los cuantiles 10 y 90 % de real − centro en los últimos W días (ignora el ancho del modelo).
    """
    p = m["pred"] * mult + suma
    lo = m["q10"] * mult + suma
    hi = m["q90"] * mult + suma
    y = m["real"]
    if r["metodo"] == "modelo":
        return lo, hi
    if r["metodo"] == "aci":
        dl, dh = (p - lo).to_numpy(), (hi - p).to_numpy()
        yv, pv = y.to_numpy(), p.to_numpy()
        fl = fh = 0.0
        LO, HI = np.full_like(pv, np.nan), np.full_like(pv, np.nan)
        for i in range(len(pv)):
            LO[i] = pv[i] - np.exp(fl) * dl[i]
            HI[i] = pv[i] + np.exp(fh) * dh[i]
            ok = ~np.isnan(yv[i]) & ~np.isnan(LO[i])
            if ok.any():  # el real de este día llega después: sirve desde el día siguiente
                fl += r["gamma"] * (np.mean(yv[i][ok] < LO[i][ok]) - ALFA / 2)
                fh += r["gamma"] * (np.mean(yv[i][ok] > HI[i][ok]) - ALFA / 2)
        return (pd.DataFrame(LO, index=p.index, columns=p.columns), pd.DataFrame(HI, index=p.index, columns=p.columns))
    w = r["ventana"]
    if r["metodo"] == "cqr":
        bl, bh = (y - lo), (y - hi)
    else:
        bl = bh = (y - p)
    # cuantil de todos los periodos de los últimos W días (sin el de hoy)
    def movil(b, q):
        vals = b.to_numpy()
        out = np.full(len(vals), np.nan)
        for i in range(len(vals)):
            ventana = vals[max(0, i - w):i].ravel()
            ventana = ventana[~np.isnan(ventana)]
            if len(ventana) >= 48:
                out[i] = np.quantile(ventana, q)
        return pd.Series(out, index=b.index)
    ql, qh = movil(bl, ALFA / 2).fillna(0), movil(bh, 1 - ALFA / 2).fillna(0)
    if r["metodo"] == "cqr":
        return lo.add(ql, axis=0), hi.add(qh, axis=0)
    return p.add(ql, axis=0), p.add(qh, axis=0)


def aplicar_rango(panel, mats, v, r):
    salida = panel.copy()
    franja = ((salida["objetivo"] - c.PASO) - salida["dia"]) // c.PASO
    salida["lo"], salida["hi"] = np.nan, np.nan
    for (h, a), m in mats.items():
        if v is None:
            suma = pd.DataFrame(0.0, index=m["pred"].index, columns=m["pred"].columns)
            mult = suma + 1
        else:
            suma, mult = correccion(m, v)
        lo, hi = rango(m, suma, mult, r)
        filas = (salida["horizonte"] == h) & (salida["area"] == a)
        idx_dia = lo.index.get_indexer(salida.loc[filas, "dia"])
        idx_fr = franja[filas].to_numpy().astype(int)
        ok = idx_dia >= 0
        vl, vh = np.full(filas.sum(), np.nan), np.full(filas.sum(), np.nan)
        vl[ok] = lo.to_numpy()[idx_dia[ok], idx_fr[ok]]
        vh[ok] = hi.to_numpy()[idx_dia[ok], idx_fr[ok]]
        salida.loc[filas, "lo"], salida.loc[filas, "hi"] = vl, vh
    return salida


def puntaje_intervalo(y, lo, hi, alfa=ALFA):
    return (hi - lo) + (2 / alfa) * np.maximum(lo - y, 0) + (2 / alfa) * np.maximum(y - hi, 0)


def resumen_rango(p):
    dentro = (p["real"] >= p["lo"]) & (p["real"] <= p["hi"])
    return pd.Series({"cobertura": 100 * dentro.mean(), "ancho": (p["hi"] - p["lo"]).mean(),
                      "debajo": 100 * (p["real"] < p["lo"]).mean(), "encima": 100 * (p["real"] > p["hi"]).mean(),
                      "puntaje": puntaje_intervalo(p["real"], p["lo"], p["hi"]).mean()})


# ---- Bootstrap por semanas -------------------------------------------------------------------------------------------

def bootstrap_semanas(ae_a, ae_b, dias, n=N_BOOT, semilla=0):
    """MAE(a) − MAE(b) con IC 95 % remuestreando semanas enteras (lunes a domingo del día objetivo)."""
    semana = pd.DatetimeIndex(dias).to_period("W").start_time
    dif = np.asarray(ae_a, dtype=float) - np.asarray(ae_b, dtype=float)
    ok = ~np.isnan(dif)
    g = pd.DataFrame({"s": semana[ok], "d": dif[ok]}).groupby("s")["d"].agg(["sum", "count"])
    suma, cuenta = g["sum"].to_numpy(), g["count"].to_numpy()
    if len(g) < 2:
        return float(dif[ok].mean()), np.nan, np.nan
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(g), size=(n, len(g)))
    medias = suma[idx].sum(axis=1) / cuenta[idx].sum(axis=1)
    return float(dif[ok].mean()), float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


# ---- Factor fijo (referencia: se ajusta en 2025, no se puede elegir con 2025) ---------------------------------------

def factores_fijos(panel):
    """Por horizonte y área, el factor de cada lado que da 10 % fuera por ese lado en 2025 (dentro de la muestra)."""
    salida = {}
    b = panel[panel["tramo"] == "2025"]
    for (h, a), g in b.groupby(["horizonte", "area"]):
        dl = (g["pred_c2"] - g["q10_c2"]).to_numpy()
        dh = (g["q90_c2"] - g["pred_c2"]).to_numpy()
        y, p = g["real"].to_numpy(), g["pred_c2"].to_numpy()
        kl = np.quantile((p - y) / dl, 1 - ALFA / 2)  # y < p − k·dl en el 10 % de los periodos
        kh = np.quantile((y - p) / dh, 1 - ALFA / 2)
        salida[(h, a)] = (kl, kh)
    return salida


def aplicar_fijo(panel, factores):
    salida = panel.copy()
    salida["lo"], salida["hi"] = np.nan, np.nan
    for (h, a), (kl, kh) in factores.items():
        f = (salida["horizonte"] == h) & (salida["area"] == a)
        p = salida.loc[f, "pred_c2"]
        salida.loc[f, "lo"] = p - kl * (p - salida.loc[f, "q10_c2"])
        salida.loc[f, "hi"] = p + kh * (salida.loc[f, "q90_c2"] - p)
    return salida


# ---- Temperatura -----------------------------------------------------------------------------------------------------

def prueba_temperatura(panel, diario):
    """Corrección del nivel del día por temperatura, ajustada en 2025 y aplicada tal cual en 2026 y en vivo.

    Dos juegos de variables: «anomalía» (anomalía media y mínima frente a la climatología ≤2024) y «cambio» (temperatura
    media y mínima frente a la semana previa: no depende del nivel de El Niño; sin intercepto, para que no arrastre el
    sesgo medio de 2025). «disponible»: lo observado hasta el fin
    de X − 1 (el de ayer). «oráculo»: el del propio día X, como si hubiera un pronóstico de temperatura perfecto (cota
    superior: no se puede usar en vivo).
    """
    d = diario[diario["modelo"] == "c2"].sort_values("dia").copy()
    juegos = {"anomalía": ["anom_media", "anom_min"], "cambio": ["d_temp_media", "d_temp_min"]}
    feats = sorted({f for v in juegos.values() for f in v})
    temp = c.temperatura_diaria().sort_values("dia")
    for col in ("temp_media", "temp_min"):
        temp[f"d_{col}"] = temp[col] - temp.groupby("area")[col].transform(
            lambda s: s.shift(1).rolling(7, min_periods=5).mean())
    previa = temp.assign(dia=temp["dia"] + pd.Timedelta(days=1)).set_index(["dia", "area"])[feats]
    ayer = previa.reindex(pd.MultiIndex.from_frame(d[["dia", "area"]]))
    for f in feats:
        d[f"{f}_ayer"] = ayer[f].to_numpy()
    filas, coefs = [], []
    salida = panel.copy()
    variantes = {f"{j} · {cuando}": ([f"{f}_ayer" for f in cols] if cuando == "disponible" else cols)
                 for j, cols in juegos.items() for cuando in ("disponible", "oráculo")}
    for variante, cols in variantes.items():
        salida[f"pred_temp_{variante}"] = salida["pred_c2"]
        for (h, a), g in d.groupby(["horizonte", "area"]):
            ent = g[(g["tramo"] == "2025")].dropna(subset=[*cols, "sesgo"])
            X = np.column_stack([np.ones(len(ent)), ent[cols].to_numpy()])
            if variante.startswith("cambio"):  # sin intercepto: con cambio cero no se corrige nada
                X[:, 0] = 0
            beta = np.linalg.lstsq(X, ent["sesgo"].to_numpy(), rcond=None)[0]
            coefs.append({"variante": variante, "horizonte": h, "area": a, "intercepto": beta[0],
                          **{k.removesuffix("_ayer"): b for k, b in zip(cols, beta[1:])}})
            todos = g.dropna(subset=cols)
            ajuste = pd.Series(np.column_stack([np.ones(len(todos)), todos[cols].to_numpy()]) @ beta,
                               index=pd.MultiIndex.from_frame(todos[["tramo", "dia"]]))
            f = (salida["horizonte"] == h) & (salida["area"] == a)
            clave = pd.MultiIndex.from_frame(salida.loc[f, ["tramo", "dia"]])
            corr = ajuste.reindex(clave).fillna(0).to_numpy()
            salida.loc[f, f"pred_temp_{variante}"] = salida.loc[f, "pred_c2"].to_numpy() - corr
    for (t, h, a), g in salida.groupby(["tramo", "horizonte", "area"]):
        base = (g["pred_c2"] - g["real"]).abs()
        for variante in variantes:
            ae = (g[f"pred_temp_{variante}"] - g["real"]).abs()
            dif, bajo, alto = bootstrap_semanas(ae, base, g["dia"])
            filas.append({"tramo": t, "horizonte": h, "area": a, "variante": variante, "mae_c2": base.mean(),
                          "mae_temp": ae.mean(), "dif": dif, "bajo": bajo, "alto": alto,
                          "sesgo_temp": (g[f"pred_temp_{variante}"] - g["real"]).mean()})
    return pd.DataFrame(filas), pd.DataFrame(coefs)


# ---- Comparación final -----------------------------------------------------------------------------------------------

def comparar(p, subconjuntos):
    """MAE, sesgo, pico, cobertura y ancho de cada modelo; Δ MAE frente a Chronos-2 ajustado con IC por semanas.

    `subconjuntos`: {nombre: función(panel) -> máscara}. Modelos: Random Forest, mejor referencia, Chronos-2 ajustado,
    con la mejor corrección de sesgo de 2025 (`c2_sesgo`, que no se adopta), con el rango adaptativo elegido con 2025
    (`c2_rango`: el mismo pronóstico central), la combinación y el XGBoost híbrido.
    """
    modelos = {"rf": "rf", "ref": "ref", "c2": "pred_c2", "c2_sesgo": "pred_corr", "c2_rango": "pred_c2",
               "comb": "pred_comb", "xgb": "pred_xgb"}
    rangos = {"c2": ("q10_c2", "q90_c2"), "c2_sesgo": ("q10_corr", "q90_corr"), "c2_rango": ("lo", "hi"),
              "comb": ("q10_comb", "q90_comb"), "xgb": ("q10_xgb", "q90_xgb")}
    filas = []
    for nombre, mascara in subconjuntos.items():
        sub = p[mascara(p)]
        for (t, h, a), g in sub.groupby(["tramo", "horizonte", "area"]):
            base = (g["pred_c2"] - g["real"]).abs()
            for m, col in modelos.items():
                if g[col].isna().all():
                    continue
                err = g[col] - g["real"]
                dia = g.assign(pr=g[col]).groupby("dia").agg(pm=("pr", "max"), rm=("real", "max"))
                fila = {"subconjunto": nombre, "tramo": t, "horizonte": h, "area": a, "modelo": m,
                        "dias": g["dia"].nunique(), "mae": err.abs().mean(), "sesgo": err.mean(),
                        "error_pico": (dia["pm"] - dia["rm"]).mean(),
                        "error_pico_abs": (dia["pm"] - dia["rm"]).abs().mean()}
                if m in rangos and g[rangos[m][0]].notna().any():
                    lo, hi = g[rangos[m][0]], g[rangos[m][1]]
                    fila["cobertura"] = 100 * ((g["real"] >= lo) & (g["real"] <= hi)).mean()
                    fila["ancho"] = (hi - lo).mean()
                    fila["puntaje_intervalo"] = puntaje_intervalo(g["real"], lo, hi).mean()
                if m not in ("c2", "c2_rango"):
                    dif, bajo, alto = bootstrap_semanas(err.abs(), base, g["dia"])
                    fila.update({"dif_vs_c2": dif, "dif_bajo": bajo, "dif_alto": alto})
                filas.append(fila)
    return pd.DataFrame(filas)


def bootstrap_cobertura(p, lo, hi, n=N_BOOT, semilla=0):
    """Cobertura (%) con IC 95 % remuestreando semanas."""
    dentro = ((p["real"] >= p[lo]) & (p["real"] <= p[hi])).astype(float).to_numpy()
    semana = pd.DatetimeIndex(p["dia"]).to_period("W").start_time
    g = pd.DataFrame({"s": semana, "d": dentro}).groupby("s")["d"].agg(["sum", "count"])
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(g), size=(n, len(g)))
    cov = g["sum"].to_numpy()[idx].sum(axis=1) / g["count"].to_numpy()[idx].sum(axis=1)
    return 100 * dentro.mean(), *(100 * np.percentile(cov, [2.5, 97.5]))


def main():
    p = dg.panel()
    errores = c.errores_continuos()
    mats = matrices(errores)
    diario = dg.diario(p)

    # 1. Corrección de sesgo: se elige con 2025
    grilla = pd.concat([evaluar_variantes(p, mats, t).assign(tramo=t) for t in ("2025", "2026", "vivo")])
    c.guardar(grilla, "grilla_sesgo")
    mejores, medias = elegir(grilla[grilla["tramo"] == "2025"])
    adoptadas = {}
    for h, i in mejores.items():
        fila = medias[(medias["horizonte"] == h) & (medias["id"] == i)].iloc[0]
        # se adopta solo si baja el MAE al menos 1 % en promedio y no empeora ningún área en 2025
        adoptadas[h] = i if (i >= 0 and fila["mean"] <= 0.99 and fila["max"] <= 1.0) else None
        print(f"Sesgo {h}: mejor variante en 2025 = {fila['variante']} (MAE × {fila['mean']:.4f}, peor área × "
              f"{fila['max']:.4f}) → {'se adopta' if adoptadas[h] is not None else 'no se adopta'}")
    # La mejor variante de 2025 se reporta igual (como «corr»), aunque no se adopte
    partes = []
    for h, i in mejores.items():
        v = None if i < 0 else VARIANTES[i]
        if v is None:  # en 2025 ninguna gana: se reporta la mejor con corrección real
            g = medias[(medias["horizonte"] == h) & (medias["id"] >= 0)].sort_values("mean").iloc[0]
            v = VARIANTES[int(g["id"])]
        partes.append(aplicar(p[p["horizonte"] == h], mats, v).assign(variante_sesgo=nombre_variante(v)))
    p = pd.concat(partes).sort_index()

    # 2. Rango adaptativo: se elige con 2025 (la cobertura más cercana al 80 % en el área que peor queda)
    filas = []
    for r in METODOS_RANGO:
        q = aplicar_rango(p, mats, None, r)
        for (t, h, a), g in q.groupby(["tramo", "horizonte", "area"]):
            filas.append({"tramo": t, "horizonte": h, "area": a, "metodo": nombre_rango(r), **resumen_rango(g)})
    fijos = factores_fijos(p)
    q = aplicar_fijo(p, fijos)
    for (t, h, a), g in q.groupby(["tramo", "horizonte", "area"]):
        filas.append({"tramo": t, "horizonte": h, "area": a, "metodo": "factor fijo de 2025 (referencia)",
                      **resumen_rango(g)})
    rangos = pd.DataFrame(filas)
    c.guardar(rangos, "grilla_rango")
    r25 = rangos[(rangos["tramo"] == "2025") & ~rangos["metodo"].str.startswith("factor fijo")]
    criterio = r25.assign(desvio=(r25["cobertura"] - 80).abs()).groupby(["horizonte", "metodo"]).agg(
        peor=("desvio", "max"), puntaje=("puntaje", "mean")).reset_index()
    rango_elegido = {}
    for h, g in criterio.groupby("horizonte"):
        cerca = g[g["peor"] <= g["peor"].min() + 0.5]
        rango_elegido[h] = cerca.sort_values("puntaje").iloc[0]["metodo"]
        print(f"Rango {h}: elegido con 2025 = {rango_elegido[h]}")
    partes = []
    for h, nombre in rango_elegido.items():
        r = next(x for x in METODOS_RANGO if nombre_rango(x) == nombre)
        partes.append(aplicar_rango(p[p["horizonte"] == h], mats, None, r))
    p = pd.concat(partes).sort_index()
    if rango_elegido.get("24h") == "ACI por lado (γ=0.2)":
        dif, n = verificar_rango_en_vivo(p)
        print(f"Rango de la tubería en vivo frente al de este análisis: diferencia máxima {dif:.4f} MW en {n} filas")

    # 3. Subconjuntos: episodios de la parte 1 (Chronos-2 a 24 h), días cálidos y el resto
    epi = dg.episodios(diario)
    epi = epi[(epi["modelo"] == "c2") & (epi["horizonte"] == "24h")]
    dias_epi = {(f.tramo, f.area, d) for f in epi.itertuples() for d in pd.date_range(f.inicio, f.fin)}
    calidos = diario[(diario["modelo"] == "c2") & diario["top10_calido"]]
    dias_cal = set(zip(calidos["tramo"], calidos["horizonte"], calidos["area"], calidos["dia"]))

    def en_epi(x):
        return pd.Series([k in dias_epi for k in zip(x["tramo"], x["area"], x["dia"])], index=x.index)

    def en_cal(x):
        return pd.Series([k in dias_cal for k in zip(x["tramo"], x["horizonte"], x["area"], x["dia"])], index=x.index)

    subconjuntos = {
        "todos": lambda x: pd.Series(True, index=x.index),
        "episodios": en_epi,
        "dias_normales": lambda x: ~en_epi(x) & ~en_cal(x),
        "top10_calidos": en_cal,
        "13-nov": lambda x: x["dia"] == pd.Timestamp("2026-11-13"),
        "13-nov ex ante": lambda x: (x["dia"] == pd.Timestamp("2026-11-13")) & (x.get("tipo") == "ex_ante_estricto"),
        "vivo 3–13 nov": lambda x: (x["tramo"] == "vivo") & (x["dia"] >= pd.Timestamp("2026-11-03")),
    }
    comparacion = comparar(p, subconjuntos)
    c.guardar(comparacion, "comparacion")
    cob = []
    for (t, h, a), g in p.groupby(["tramo", "horizonte", "area"]):
        for nombre, (lo, hi) in {"modelo": ("q10_c2", "q90_c2"), "adaptativo": ("lo", "hi")}.items():
            v, bajo, alto = bootstrap_cobertura(g, lo, hi)
            cob.append({"tramo": t, "horizonte": h, "area": a, "rango": nombre, "cobertura": v, "bajo": bajo,
                        "alto": alto, "ancho": (g[hi] - g[lo]).mean()})
    c.guardar(pd.DataFrame(cob), "cobertura_ic")

    # 4. Temperatura
    temp, coefs = prueba_temperatura(p, diario)
    c.guardar(temp, "prueba_temperatura")
    c.guardar(coefs, "coeficientes_temperatura")
    p.to_parquet(c.SALIDA / "panel_remedios.parquet", index=False)
    return p, grilla, rangos, comparacion, temp


# ---- Puente con la tubería en vivo -----------------------------------------------------------------------------------

def estado_inicial_rango(errores=None, gamma=0.2):
    """El estado del ACI de `en_vivo.factores_rango` al cerrar la víspera de `en_vivo.INICIO_RANGO`, recorriendo los
    pronósticos guardados de Chronos-2 ajustado desde 2025 con f = 0. Es lo que va en `ESTADO_RANGO_CHRONOS`."""
    from tetouan_power_forecast import en_vivo

    errores = c.errores_continuos() if errores is None else errores
    previos = errores[errores["dia"] < pd.Timestamp(en_vivo.INICIO_RANGO)].rename(columns={"dia": "fecha_objetivo"})
    _, estado = en_vivo.factores_rango(previos, None, gamma)
    return estado


def verificar_rango_en_vivo(panel_rango, errores=None):
    """Que la tubería (`en_vivo.factores_rango` con el estado guardado, sobre el registro en vivo) dé el mismo rango que
    este análisis en el tramo en vivo. Devuelve la diferencia máxima en MW."""
    from tetouan_power_forecast import en_vivo

    seg = pd.read_parquet(c.RAIZ / "reportes" / "sein" / "en_vivo" / "seguimiento.parquet")
    seg = seg[seg["modelo"] == "chronos2ftcal"].copy()
    seg["fecha_objetivo"] = pd.to_datetime(seg["fecha_objetivo"])
    factores, _ = en_vivo.factores_rango(seg, en_vivo.ESTADO_RANGO_CHRONOS)
    j = seg.merge(factores, on=["horizonte", "area", "fecha_objetivo"])
    j["lo"] = j["pred"] - np.exp(j["f_bajo"]) * (j["pred"] - j["q10"])
    j["hi"] = j["pred"] + np.exp(j["f_alto"]) * (j["q90"] - j["pred"])
    v = panel_rango[panel_rango["tramo"] == "vivo"][["horizonte", "area", "objetivo", "lo", "hi"]]
    k = j.merge(v, on=["horizonte", "area", "objetivo"], suffixes=("", "_analisis"))
    return float(max((k["lo"] - k["lo_analisis"]).abs().max(), (k["hi"] - k["hi_analisis"]).abs().max())), len(k)


if __name__ == "__main__":
    main()
