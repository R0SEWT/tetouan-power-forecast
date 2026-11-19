"""Panel de evaluación: pronósticos por origen de todos los modelos, con su real, en 2025, 2026 y el tramo en vivo.

Una fila por (tramo, horizonte, área, origen). «2025» y «2026» son las filas de los notebooks 02 y 03 (las mismas que
las tablas del proyecto, con el Random Forest elegido `rf`); «vivo» son los días objetivo del registro en vivo
(23-oct → último día con real), con los orígenes de Chronos-2 ajustado. `dia` es el día del periodo objetivo (los
periodos se fechan por su fin), como `fecha_objetivo` en el registro.
"""

import numpy as np
import pandas as pd

from experimentos.temperatura import comun as c
from tetouan_power_forecast import en_vivo

TRAMOS = {"2025": "modelado/predicciones_validacion", "2026": "prueba_2026/predicciones"}
REFS = ["persistencia", "ayer", "semana_pasada"]
AREAS = ["NORTE", "CENTRO", "SUR"]
REJILLA = np.linspace(0, 1, 21)
PRON = c.SALIDA / "pronosticos"
# Pronósticos guardados del proyecto (experimentos/fundacionales) y los de este experimento
GUARDADOS = {"c2": c.FUND / "chronos2ftcal_c2048.parquet", "comb": c.FUND / "combinacion_c2048.parquet",
             "xgb": c.FUND / "xgb_simons_c2048.parquet", "c2_s2": c.FUND / "chronos2ftcal_s2_c2048.parquet",
             "c2_s3": c.FUND / "chronos2ftcal_s3_c2048.parquet"}
NUEVOS = {"xgb_s": "xgb_s_c2048", "xgb_s_tobs": "xgb_s_tobs_c2048", "xgb_s_tobs_oraculo": "xgb_s_tobs_oraculo_c2048",
          "xgb_s_tmix": "xgb_s_tmix_c2048", "xgb_s_tcdd": "xgb_s_tcdd_c2048", "c2cdd": "chronos2ftcalcdd_c2048"}


def dia_objetivo(objetivo):
    return (pd.DatetimeIndex(objetivo) - c.PASO).normalize()


def demanda():
    return en_vivo.serie_completa(c.RAIZ).set_index("DateTime")[AREAS]


def pronosticos():
    """{nombre: tabla por origen} de los modelos disponibles (los que falten se omiten)."""
    salida = {}
    for k, ruta in GUARDADOS.items():
        if ruta.exists():
            salida[k] = pd.read_parquet(ruta)
    for k, nombre in NUEVOS.items():
        ruta = PRON / f"{nombre}.parquet"
        if ruta.exists():
            salida[k] = pd.read_parquet(ruta)
    return salida


def _unir(base, pron, horizonte, area):
    paso = c.PASOS[horizonte]
    for k, tabla in pron.items():
        t = tabla[tabla["area"] == area].drop_duplicates("DateTime").set_index("DateTime")
        cols = {f"pred_{paso}": f"pred_{k}", f"q10_{paso}": f"q10_{k}", f"q90_{paso}": f"q90_{k}"}
        cols = {a: b for a, b in cols.items() if a in t}
        base = base.join(t[list(cols)].rename(columns=cols), on="origen")
    return base


def panel(pron=None):
    pron = pronosticos() if pron is None else pron
    partes = []
    for tramo, prefijo in TRAMOS.items():
        for horizonte, paso in c.PASOS.items():
            for area in AREAS:
                base = pd.read_csv(c.RAIZ / "reportes" / "sein" / f"{prefijo}_{horizonte}_{area.lower()}.csv",
                                   parse_dates=["DateTime"])[["DateTime", "real", *REFS, "fijo_M0"]]
                base = base.rename(columns={"DateTime": "origen", "fijo_M0": "pred_rf"})
                base = _unir(base, pron, horizonte, area)
                base.insert(0, "area", area)
                base.insert(0, "horizonte", horizonte)
                base.insert(0, "tramo", tramo)
                base["objetivo"] = base["origen"] + paso * c.PASO
                partes.append(base)
    # Tramo en vivo: los orígenes del registro de Chronos-2 ajustado con real
    seg = pd.read_parquet(c.RAIZ / "reportes" / "sein" / "en_vivo" / "seguimiento.parquet")
    seg = seg[seg["modelo"] == "chronos2ftcal"]
    for (horizonte, area), g in seg.groupby(["horizonte", "area"]):
        base = pd.DataFrame({"origen": g["origen"].to_numpy(), "real": g["real"].to_numpy(),
                             **{r: g[r].to_numpy() for r in REFS}, "pred_rf": np.nan})
        vivo = {k: v for k, v in pron.items() if k != "c2"}
        base = _unir(base, vivo, horizonte, area)
        base["pred_c2"], base["q10_c2"], base["q90_c2"] = g["pred"].to_numpy(), g["q10"].to_numpy(), g["q90"].to_numpy()
        base["tipo"] = g["tipo"].to_numpy()
        base.insert(0, "area", area)
        base.insert(0, "horizonte", horizonte)
        base.insert(0, "tramo", "vivo")
        base["objetivo"] = base["origen"] + c.PASOS[horizonte] * c.PASO
        partes.append(base)
    p = pd.concat(partes, ignore_index=True)
    p["dia"] = dia_objetivo(p["objetivo"])
    return p


def combinar(p, primero, segundo, nombre, rejilla=REJILLA):
    """w · primero + (1 − w) · segundo con el peso de menor MAE en 2025 por horizonte y área (se aplica tal cual)."""
    p[f"pred_{nombre}"] = np.nan
    pesos = {}
    for (h, a), g in p[p["tramo"] == "2025"].groupby(["horizonte", "area"]):
        g = g.dropna(subset=[f"pred_{primero}", f"pred_{segundo}"])
        maes = [np.abs(w * g[f"pred_{primero}"] + (1 - w) * g[f"pred_{segundo}"] - g["real"]).mean() for w in rejilla]
        pesos[(h, a)] = float(rejilla[int(np.argmin(maes))])
    w = np.array([pesos.get((h, a), np.nan) for h, a in zip(p["horizonte"], p["area"], strict=True)])
    p[f"pred_{nombre}"] = w * p[f"pred_{primero}"] + (1 - w) * p[f"pred_{segundo}"]
    return pesos
