"""(b) Capa de corrección pequeña y monótona sobre Chronos-2 ajustado: el pronóstico se multiplica por
1 + β_b · x, con x los grados sobre el umbral del día objetivo (`tp_cdd`) o su cambio frente a la semana previa
(`tp_dcdd`), un β ≥ 0 por bloque de horas del periodo objetivo (madrugada, mañana, tarde, noche) y sin intercepto: no
corrige el nivel (eso ya se probó y no sirve), solo agrega demanda cuando hace calor.

**Sin residuos dentro de muestra del ajuste fino.** Chronos-2 ajustado se entrenó con 2016–2024, así que sus errores
en esos años no sirven para estimar nada. Dos formas de evitarlo:

- `fija`: β se estima con los errores de Chronos-2 **zero-shot** (sin ajuste fino) en 2016–2024, que no vio esos datos
  al pronosticar, con la temperatura observada (sin 2020-03 a 2020-06). Se aplica tal cual desde 2025.
- `en_linea`: β se reestima cada día con los errores de Chronos-2 ajustado desde el 1-ene-2025, solo con los días
  objetivo ya cerrados al emitir (a 24 h, hasta X − 2; a 1 h, hasta X − 1) y con la temperatura pronosticada.

β por bloque tiene forma cerrada: max(0, Σ x·r / Σ x²), con r = real / pronóstico − 1, porque los bloques no se cruzan.
"""

import numpy as np
import pandas as pd

from experimentos.temperatura import comun as c
from tetouan_power_forecast import temperatura_pronosticada as tp

CUARENTENA = (pd.Timestamp("2020-03-01"), pd.Timestamp("2020-07-01"))
bloque = tp.bloque


def beta(x, r, b):
    """β ≥ 0 por bloque (forma cerrada)."""
    salida = np.zeros(4)
    for k in range(4):
        m = (b == k) & np.isfinite(x) & np.isfinite(r)
        den = (x[m] ** 2).sum()
        salida[k] = max(0.0, (x[m] * r[m]).sum() / den) if den > 0 else 0.0
    return salida


def residuos_zero_shot(variables_obs, demanda):
    """Errores relativos de Chronos-2 zero-shot en 2016–2024 por (horizonte, área, origen), con x observada."""
    tabla = pd.read_parquet(c.FUND / "entrenamiento" / "chronos2_c2048.parquet")
    largo = demanda.stack()
    partes = []
    for horizonte, paso in c.PASOS.items():
        t = pd.DataFrame({"horizonte": horizonte, "area": tabla["area"].str.upper(), "origen": tabla["DateTime"],
                          "pred": tabla[f"pred_{paso}"]})
        t["objetivo"] = t["origen"] + paso * c.PASO
        t["real"] = largo.reindex(pd.MultiIndex.from_arrays([t["objetivo"], t["area"]])).to_numpy()
        partes.append(t)
    t = pd.concat(partes, ignore_index=True)
    t = t[(t["objetivo"] < pd.Timestamp("2025-01-01")) & ~t["objetivo"].between(*CUARENTENA)]
    v = variables_obs.rename(columns={"DateTime": "origen"})
    t = t.merge(v, on=["horizonte", "area", "origen"], how="inner")
    t["r"] = t["real"] / t["pred"] - 1
    t["bloque"] = bloque(t["objetivo"])
    return t.dropna(subset=["r"])


def ajuste_fijo(residuos, variable):
    """β por (horizonte, área) con los errores zero-shot de 2016–2024."""
    return {(h, a): beta(g[variable].to_numpy(), g["r"].to_numpy(), g["bloque"].to_numpy())
            for (h, a), g in residuos.groupby(["horizonte", "area"])}


def aplicar_fija(p, betas, variable, base="c2", nombre=None):
    nombre = nombre or f"c2fija_{variable}"
    b = bloque(p["objetivo"])
    factor = np.ones(len(p))
    for (h, a), bt in betas.items():
        m = ((p["horizonte"] == h) & (p["area"] == a)).to_numpy()
        factor[m] = 1 + bt[b[m]] * p.loc[m, variable].to_numpy()
    p[f"pred_{nombre}"] = p[f"pred_{base}"] * factor
    return nombre


def aplicar_en_linea(p, continuos, variable, base="c2", nombre=None):
    """β reestimado cada día objetivo con los errores de los días ya cerrados (desde 2025), con la misma función que
    usa el modo en vivo (`temperatura_pronosticada.betas_en_linea`).

    `continuos` tiene el pronóstico de Chronos-2 ajustado y su real por (horizonte, área, objetivo) de 2025 al último
    día, sin cortes, con la variable de cada origen. Devuelve el nombre de la columna nueva en `p` y los β por día.
    """
    nombre = nombre or f"c2linea_{variable}"
    betas = tp.betas_en_linea(continuos, variable)
    factor = np.ones(len(p))
    for (h, a), g in p.groupby(["horizonte", "area"]):
        factor[g.index] = tp.factor_calor(betas, h, a, g["objetivo"], g[variable])
    p[f"pred_{nombre}"] = p[f"pred_{base}"] * factor
    return nombre, betas
