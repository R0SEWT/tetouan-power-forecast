"""Evaluación de modelos fundacionales de series de tiempo y del apilado sobre el SEIN.

Cada modelo deja un parquet con una fila por origen y área: `DateTime` es el origen t (fin del último periodo
observado) y `pred_2` y `pred_48` son los pronósticos de t + 1 h y t + 24 h, con sus cuantiles `q10_*` y `q90_*`.
Aquí se comparan con el modelo elegido en las mismas filas de los notebooks 02 (validación de 2025) y 03 (prueba de
2026), con la misma vara: la mejor referencia ingenua y el intervalo por bootstrap de días.
"""

from pathlib import Path

import numpy as np
import pandas as pd

from tetouan_power_forecast.evaluacion import bootstrap_diferencia_mae
from tetouan_power_forecast.variables_sein import AREAS, HORIZONTES, REFERENCIAS

ELEGIDO = "fijo_M0"  # el Random Forest por área, sin exógenas y sin reentrenar: la columna de los notebooks 02 y 03
NOMBRE_ELEGIDO = "Random Forest por área (elegido)"
TRAMOS = {"2025": "modelado/predicciones_validacion", "2026": "prueba_2026/predicciones"}
REJILLA = np.linspace(0, 1, 21)


def cargar_pronosticos(carpeta):
    """Los pronósticos por origen de cada modelo que haya en la carpeta: {nombre: tabla}.

    Los archivos `*_train` son pronósticos sobre el entrenamiento (las variables del apilado) y no se evalúan.
    """
    return {f.stem: pd.read_parquet(f) for f in sorted(Path(carpeta).glob("*.parquet")) if not f.stem.endswith("_train")}


def cargar_base(reportes, tramo, horizonte, area):
    """Las filas de un tramo, horizonte y área: origen, real, las tres referencias y el modelo elegido."""
    ruta = Path(reportes) / f"{TRAMOS[tramo]}_{horizonte}_{area.lower()}.csv"
    return pd.read_csv(ruta, parse_dates=["DateTime"])[["DateTime", "real", *REFERENCIAS, ELEGIDO]]


def alinear(base, pronosticos, area, paso):
    """Une a las filas de la base el pronóstico de un modelo a `paso` periodos; falla si falta algún origen."""
    de_area = pronosticos[pronosticos["area"] == area].set_index("DateTime")
    columnas = {f"pred_{paso}": "pred", f"q10_{paso}": "q10", f"q90_{paso}": "q90"}
    unido = base.join(de_area[list(columnas)].rename(columns=columnas), on="DateTime")
    if unido["pred"].isna().any():
        raise ValueError(f"faltan {int(unido['pred'].isna().sum())} orígenes del pronóstico en {area}")
    return unido


def mae_mejor_referencia(base):
    """El MAE de la mejor de las tres referencias ingenuas en esas filas."""
    return min(float((base[r] - base["real"]).abs().mean()) for r in REFERENCIAS)


def cobertura(real, bajo, alto):
    """Porcentaje de periodos en que lo real cae dentro del intervalo; NaN si el modelo no da intervalo."""
    bajo, alto = np.asarray(bajo, dtype=float), np.asarray(alto, dtype=float)
    if np.isnan(bajo).all() or np.isnan(alto).all():
        return float("nan")
    real = np.asarray(real, dtype=float)
    return float(100 * ((real >= bajo) & (real <= alto)).mean())


def peso_combinacion(real, pred, otro, rejilla=REJILLA):
    """El peso w de `w · pred + (1 − w) · otro` con menor MAE. Se fija en 2025 y se aplica tal cual en 2026."""
    real, pred, otro = (np.asarray(x, dtype=float) for x in (real, pred, otro))
    maes = [np.abs(w * pred + (1 - w) * otro - real).mean() for w in rejilla]
    return float(rejilla[int(np.argmin(maes))])


def combinar_modelos(reportes, primero, segundo, rejilla=REJILLA):
    """Combina dos modelos: `w · primero + (1 − w) · segundo`, con un peso por horizonte y área fijado en 2025.

    Devuelve la combinación con el mismo formato que cualquier modelo (para evaluarla y servirla igual) y la tabla
    de pesos. Los cuantiles se combinan con el mismo peso: es una aproximación, no un intervalo calibrado.
    """
    claves = ["DateTime", "area"]
    junto = primero.merge(segundo, on=claves, suffixes=("_a", "_b"))
    salida, pesos = junto[claves].copy(), []
    for horizonte, paso in HORIZONTES.items():
        w_area = {}
        for area in AREAS:
            base = cargar_base(reportes, "2025", horizonte, area)
            a, b = alinear(base, primero, area, paso), alinear(base, segundo, area, paso)
            w_area[area] = peso_combinacion(base["real"], a["pred"], b["pred"], rejilla)
            pesos.append({"Horizonte": horizonte, "Área": area.capitalize(), "Peso del primero": w_area[area]})
        w = junto["area"].map(w_area).to_numpy()
        for columna in (f"pred_{paso}", f"q10_{paso}", f"q90_{paso}"):
            salida[columna] = w * junto[f"{columna}_a"].to_numpy() + (1 - w) * junto[f"{columna}_b"].to_numpy()
    return salida, pd.DataFrame(pesos)


def _fila(tramo, horizonte, area, modelo, real, pred, mejor):
    error = np.abs(np.asarray(pred, dtype=float) - np.asarray(real, dtype=float))
    return {"Año": tramo, "Horizonte": horizonte, "Área": area.capitalize(), "Modelo": modelo, "MAE (MW)": error.mean(),
            "MAPE (%)": 100 * (error / np.asarray(real, dtype=float)).mean(),
            "Mejora vs. mejor referencia (%)": 100 * (1 - error.mean() / mejor), "Periodos": len(error)}


def comparar(reportes, pronosticos, n=2000, semilla=0):
    """Compara cada modelo con el elegido en las filas de los notebooks 02 y 03.

    Devuelve tres tablas: la comparación (con la diferencia de MAE frente al elegido y su intervalo al 95 % por
    bootstrap de días, y la cobertura del intervalo 10–90), la combinación lineal con el elegido (el peso se fija en
    2025) y el MAE por mes.
    """
    comparacion, combinacion, mensual, pesos = [], [], [], {}
    for tramo in TRAMOS:  # 2025 primero: ahí se fijan los pesos
        for horizonte, paso in HORIZONTES.items():
            for area in AREAS:
                base = cargar_base(reportes, tramo, horizonte, area)
                mejor = mae_mejor_referencia(base)
                comparacion.append(_fila(tramo, horizonte, area, NOMBRE_ELEGIDO, base["real"], base[ELEGIDO], mejor))
                mes = base["DateTime"].dt.to_period("M").astype(str)
                error_elegido = (base[ELEGIDO] - base["real"]).abs()
                for nombre, tabla in pronosticos.items():
                    j = alinear(base, tabla, area, paso)
                    delta, bajo, alto = bootstrap_diferencia_mae(j["real"], j["pred"], j[ELEGIDO], j["DateTime"], n, semilla)
                    comparacion.append({**_fila(tramo, horizonte, area, nombre, j["real"], j["pred"], mejor),
                                        "Δ MAE vs. elegido (MW)": delta, "IC 95 % bajo": bajo, "IC 95 % alto": alto,
                                        "Cobertura 10–90 (%)": cobertura(j["real"], j["q10"], j["q90"])})
                    clave = (nombre, horizonte, area)
                    if tramo == "2025":
                        pesos[clave] = peso_combinacion(j["real"], j["pred"], j[ELEGIDO])
                    w = pesos[clave]
                    mezcla = w * j["pred"] + (1 - w) * j[ELEGIDO]
                    delta, bajo, alto = bootstrap_diferencia_mae(j["real"], mezcla, j[ELEGIDO], j["DateTime"], n, semilla)
                    combinacion.append({"Año": tramo, "Horizonte": horizonte, "Área": area.capitalize(), "Modelo": nombre,
                                        "Peso del modelo": w, "MAE (MW)": float((mezcla - j["real"]).abs().mean()),
                                        "Δ MAE vs. elegido (MW)": delta, "IC 95 % bajo": bajo, "IC 95 % alto": alto})
                    por_mes = pd.DataFrame({"Mes": mes, "MAE (MW)": (j["pred"] - j["real"]).abs(),
                                            "MAE del elegido (MW)": error_elegido}).groupby("Mes").mean().reset_index()
                    mensual.append(por_mes.assign(Horizonte=horizonte, Área=area.capitalize(), Modelo=nombre))
    return pd.DataFrame(comparacion), pd.DataFrame(combinacion), pd.concat(mensual, ignore_index=True)


def separar_nombre(nombre):
    """`simons_c2048` → ("simons", 2048): el modelo y la longitud del contexto en periodos."""
    modelo, _, contexto = nombre.rpartition("_c")
    return (modelo, int(contexto)) if contexto.isdigit() else (nombre, None)
