"""Apilado: XGBoost global en razón (M0) + pronósticos zero-shot de modelos fundacionales como variables. Corre en la VM.

Entrena con orígenes cuyo objetivo cae ≤2024 (hueco de H pasos), predice 2025 (validación) y 2026 (prueba).
Uso: python apilar.py chronos2 [simons]
"""
import json
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.insert(0, "/content/tpf")
from app.backend.pronosticador_real import HIPERPARAMETROS, _feriados, armar_datasets, cargar_capas
from tetouan_power_forecast.modelado_sein import gradient_boosting_global, portable
from tetouan_power_forecast.variables_sein import PASO, columnas_variante

FMS = sys.argv[1:]
RAIZ = "/content/datalake"
SAL = Path("/content/stk")
SAL.mkdir(exist_ok=True)
PASOS = {"1h": 2, "24h": 48}
FIN_ENT, INICIO_FM = pd.Timestamp("2025-01-01"), pd.Timestamp("2016-03-01")
log = lambda *a: print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)

demanda, exogenas = cargar_capas(RAIZ)
datos = armar_datasets(demanda, exogenas, _feriados())
fm = {}
for m in FMS:
    # las dos salidas de fm_bench.py: los orígenes de entrenamiento (sufijo train) y los de 2025 y 2026
    f = pd.concat([pd.read_parquet(f"/content/fm/{m}_c2048_train.parquet"), pd.read_parquet(f"/content/fm/{m}_c2048.parquet")])
    f["area"] = f["area"].str.lower()
    fm[m] = f.drop_duplicates(["DateTime", "area"]).set_index(["area", "DateTime"])


def con_fm(d, area, h):
    """Añade las variables fundacionales, en razón a media_24h (la escala del objetivo)."""
    d = d.copy()
    otro = 48 if h == 2 else 2
    for m, f in fm.items():
        s = f.loc[area].reindex(d.index)
        d[f"fm_{m}_pred"] = s[f"pred_{h}"].to_numpy() / d["media_24h"]
        d[f"fm_{m}_ancho"] = (s[f"q90_{h}"] - s[f"q10_{h}"]).to_numpy() / d["media_24h"]
        d[f"fm_{m}_otro"] = s[f"pred_{otro}"].to_numpy() / d["media_24h"]
    return d


def cols_fm(ms):
    return [f"fm_{m}_{k}" for m in ms for k in ("pred", "ancho", "otro")]


CONFIGS = {"xgb_base_todo": None, "xgb_base": []}
for m in FMS:
    CONFIGS[f"xgb_{m}"] = [m]
if len(FMS) > 1:
    CONFIGS["xgb_ambos"] = list(FMS)
import os

if os.environ.get("SOLO_AREA"):
    CONFIGS = {"xgb_simons_area": ["simons"], "xgb_base_area": []}


class PorArea:
    """Un modelo por área (misma receta), con la interfaz de uno solo."""

    def fit(self, X, y):
        self.m = {c: gradient_boosting_global(**HIPERPARAMETROS).fit(X[X["area_cod"] == c], y[X["area_cod"] == c])
                  for c in sorted(X["area_cod"].unique())}
        return self

    def predict(self, X):
        p = np.empty(len(X))
        for c, m in self.m.items():
            k = (X["area_cod"] == c).to_numpy()
            p[k] = m.predict(X[k])
        return p


preds = {c: [] for c in CONFIGS}
resumen, importancias = [], []
rng = np.random.default_rng(0)
for nombre_h, h in PASOS.items():
    por_area = {a: con_fm(d, a, h) for a, d in datos[nombre_h].items()}
    base = [c for c in columnas_variante(next(iter(por_area.values())), "M0") if not c.startswith("fm_")]
    todas = pd.concat(por_area.values(), ignore_index=True)
    fmc = cols_fm(FMS)
    for cfg, ms in CONFIGS.items():
        cols = base + (cols_fm(ms) if ms else [])
        necesarias = base + ["real"] + ([] if ms is None else fmc)  # mismas filas para base y apilados
        ent = todas[(todas["DateTime"] < FIN_ENT - h * PASO)].dropna(subset=necesarias)
        if ms is not None:
            ent = ent[ent["DateTime"] >= INICIO_FM]
        t0 = time.time()
        if cfg.endswith("_area"):
            modelo = PorArea().fit(ent[cols], ent["real"])
        else:
            modelo = gradient_boosting_global(**HIPERPARAMETROS).fit(ent[cols], ent["real"])
            joblib.dump(portable(modelo), SAL / f"{cfg}_{nombre_h}.joblib")
        ev = todas[todas["DateTime"] >= FIN_ENT].dropna(subset=cols)
        p = modelo.predict(ev[cols])
        out = pd.DataFrame({"DateTime": ev["DateTime"].to_numpy(), "area": ev["area"].str.upper().to_numpy(), f"pred_{h}": p, "real": ev["real"].to_numpy(),
                            "area_cod": ev["area_cod"].to_numpy()})
        val = out[(out["DateTime"] < pd.Timestamp("2026-01-01") - h * PASO) & out["real"].notna()]
        for cod, g in out.groupby("area_cod"):
            v = val[val["area_cod"] == cod]
            rel = v["real"] / v[f"pred_{h}"] - 1
            out.loc[g.index, f"q10_{h}"] = g[f"pred_{h}"] * (1 + rel.quantile(0.1))
            out.loc[g.index, f"q90_{h}"] = g[f"pred_{h}"] * (1 + rel.quantile(0.9))
        preds[cfg].append(out.drop(columns="real"))
        mae = (val[f"pred_{h}"] - val["real"]).abs().groupby(val["area_cod"]).mean().round(2).to_dict()
        resumen.append({"config": cfg, "h": nombre_h, "filas_ent": len(ent), "seg": round(time.time() - t0), "mae_2025": mae,
                        "columnas": cols})
        log(cfg, nombre_h, len(ent), "filas ·", round(time.time() - t0), "s · MAE 2025 por área:", mae)
        if ms:  # importancia por permutación por grupo en 2025 (la escala media_24h no se permuta)
            v = todas[(todas["DateTime"] >= FIN_ENT) & (todas["DateTime"] < pd.Timestamp("2026-01-01") - h * PASO)]
            v = v.dropna(subset=cols + ["real"]).sample(30000, random_state=0)
            ref = np.abs(modelo.predict(v[cols]) - v["real"]).mean()
            for c in cols:
                if c == "media_24h":
                    continue
                sube = []
                for _ in range(3):
                    x = v[cols].copy()
                    x[c] = rng.permutation(x[c].to_numpy())
                    sube.append(np.abs(modelo.predict(x) - v["real"]).mean() - ref)
                importancias.append({"config": cfg, "h": nombre_h, "variable": c,
                                     "grupo": "fundacional" if c.startswith("fm_") else "demanda y calendario",
                                     "aumento_mae_mw": float(np.mean(sube))})

CODIGO = None
for cfg, piezas in preds.items():
    a, b = piezas
    j = a.merge(b, on=["DateTime", "area_cod"], how="outer", suffixes=("", "_y"))
    if "area_y" in j:
        j["area"] = j["area"].fillna(j["area_y"])
        j = j.drop(columns="area_y")
    j.drop(columns="area_cod").to_parquet(SAL / f"{cfg}_c2048.parquet")
(SAL / f"resumen_{'_'.join(FMS)}{os.environ.get('SOLO_AREA','')}.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1))
pd.DataFrame(importancias).to_csv(SAL / f"importancias_{'_'.join(FMS)}{os.environ.get('SOLO_AREA','')}.csv", index=False)
log("TERMINO", FMS)
