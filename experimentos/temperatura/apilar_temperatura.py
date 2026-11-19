"""(a) XGBoost híbrido en razón con Simons (`xgb_simons`) más variables de temperatura. Corre en la VM de Colab.

Mismo armado que `experimentos/fundacionales/apilar.py` (variables M0, Simons en razón a media_24h, hiperparámetros
del notebook 02, entrenamiento con orígenes cuyo objetivo cae ≤ 2024). Configuraciones:

- `xgb_s`: sin temperatura (la referencia, reentrenada aquí para comparar en igualdad).
- `xgb_s_tobs`: entrena con la temperatura observada (ERA5) y predice con la pronosticada (edición vigente). También
  guarda la predicción con la observada (`xgb_s_tobs_oraculo`): la diferencia mide lo que se pierde por el error del
  pronóstico.
- `xgb_s_tmix`: entrena con la pronosticada donde el archivo existe (GFS, desde marzo de 2021) y con la observada
  antes; predice con la pronosticada.
- `xgb_s_tcdd`: como `tmix`, pero solo con los grados sobre el umbral y su cambio (`tp_cdd`, `tp_dcdd`).

Predice 2025, 2026 y el tramo en vivo (orígenes hasta el último con Simons). Los cuantiles 10 y 90 salen del error
relativo de 2025, como en apilar.py.

Necesita en la VM: el repo en /content/tpf (con este directorio), las capas en /content/datalake (coes/silver con la
capa en vivo, exogenas/silver, reportes/sein/temperatura/variables_*.parquet) y las salidas de Simons en /content/fm/
(simons_c2048_train, simons_c2048 y simons_c2048_vivo).
Uso: python apilar_temperatura.py
"""

import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, "/content/tpf")
from app.backend.pronosticador_real import HIPERPARAMETROS, _feriados, armar_datasets, cargar_capas
from tetouan_power_forecast import en_vivo
from tetouan_power_forecast.modelado_sein import gradient_boosting_global, portable
from tetouan_power_forecast.variables_sein import PASO, columnas_variante

RAIZ = Path("/content/datalake")
SAL = Path("/content/stk_temp")
SAL.mkdir(exist_ok=True)
PASOS = {"1h": 2, "24h": 48}
FIN_ENT, INICIO_FM = pd.Timestamp("2025-01-01"), pd.Timestamp("2016-03-01")
VARS = ["tp_media", "tp_max", "tp_min_noche", "tp_cdd", "tp_media_3d", "tp_dcdd", "tp_obj"]
CONFIGS = {  # nombre: (variables de temperatura, fuente en el entrenamiento)
    "xgb_s": ([], None),
    "xgb_s_tobs": (VARS, "observada"),
    "xgb_s_tmix": (VARS, "mixta"),
    "xgb_s_tcdd": (["tp_cdd", "tp_dcdd"], "mixta"),
}
log = lambda *a: print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def cargar_variables():
    carpeta = RAIZ / "reportes" / "sein" / "temperatura"
    obs = pd.read_parquet(carpeta / "variables_observada.parquet")
    pron = pd.read_parquet(carpeta / "variables_pronostico.parquet")
    clave = ["horizonte", "area", "DateTime"]
    obs, pron = obs.set_index(clave).sort_index(), pron.set_index(clave).sort_index()
    mixta = pron.reindex(obs.index.union(pron.index))
    falta = mixta[VARS].isna().any(axis=1)
    mixta.loc[falta, VARS] = obs.reindex(mixta.index[falta])[VARS].to_numpy()
    return {"observada": obs, "pronostico": pron, "mixta": mixta}


def con_temperatura(d, area, nombre_h, fuente):
    s = fuente.loc[(nombre_h, area.upper())].reindex(d.index)
    for v in VARS:
        d[v] = s[v].to_numpy()
    return d


def main():
    demanda = en_vivo.serie_completa(RAIZ)  # silver histórica + capa en vivo, sin huecos
    _, exogenas = cargar_capas(RAIZ)
    datos = armar_datasets(demanda, exogenas, _feriados())
    fm = pd.concat([pd.read_parquet(f"/content/fm/simons_c2048{s}.parquet") for s in ("_train", "", "_vivo")])
    fm["area"] = fm["area"].str.lower()
    fm = fm.drop_duplicates(["DateTime", "area"], keep="first").set_index(["area", "DateTime"]).sort_index()
    temp = cargar_variables()
    preds, resumen = {}, []
    for nombre_h, h in PASOS.items():
        otro = 48 if h == 2 else 2
        piezas = []
        for area, d in datos[nombre_h].items():
            d = d.copy()
            s = fm.loc[area].reindex(d.index)
            d["fm_simons_pred"] = s[f"pred_{h}"].to_numpy() / d["media_24h"]
            d["fm_simons_ancho"] = (s[f"q90_{h}"] - s[f"q10_{h}"]).to_numpy() / d["media_24h"]
            d["fm_simons_otro"] = s[f"pred_{otro}"].to_numpy() / d["media_24h"]
            piezas.append(d)
        todas = pd.concat(piezas, ignore_index=True).set_index("DateTime", drop=False)
        base = [c for c in columnas_variante(todas, "M0") if not c.startswith("fm_")]
        base += ["fm_simons_pred", "fm_simons_ancho", "fm_simons_otro"]
        for cfg, (variables, fuente_ent) in CONFIGS.items():
            cols = base + variables
            ent = todas[(todas["DateTime"] < FIN_ENT - h * PASO) & (todas["DateTime"] >= INICIO_FM)].copy()
            if variables:
                ent = pd.concat([con_temperatura(g.copy(), a, nombre_h, temp[fuente_ent])
                                 for a, g in ent.groupby("area")])
            ent = ent.dropna(subset=base + ["real"] + VARS if variables else base + ["real"])
            t0 = time.time()
            modelo = gradient_boosting_global(**HIPERPARAMETROS).fit(ent[cols], ent["real"])
            joblib.dump(portable(modelo), SAL / f"{cfg}_{nombre_h}.joblib")
            ev0 = todas[todas["DateTime"] >= FIN_ENT].copy()
            fuentes_ev = {cfg: "pronostico"} if variables else {cfg: None}
            if fuente_ent == "observada":
                fuentes_ev[f"{cfg}_oraculo"] = "observada"
            for nombre, fuente_ev in fuentes_ev.items():
                ev = ev0 if fuente_ev is None else pd.concat(
                    [con_temperatura(g.copy(), a, nombre_h, temp[fuente_ev]) for a, g in ev0.groupby("area")])
                ev = ev.dropna(subset=cols)
                p = modelo.predict(ev[cols])
                out = pd.DataFrame({"DateTime": ev["DateTime"].to_numpy(), "area": ev["area"].str.upper().to_numpy(),
                                    f"pred_{h}": p, "real": ev["real"].to_numpy()})
                val = out[(out["DateTime"] < pd.Timestamp("2026-01-01") - h * PASO) & out["real"].notna()]
                for a, g in out.groupby("area"):
                    v = val[val["area"] == a]
                    rel = v["real"] / v[f"pred_{h}"] - 1
                    out.loc[g.index, f"q10_{h}"] = g[f"pred_{h}"] * (1 + rel.quantile(0.1))
                    out.loc[g.index, f"q90_{h}"] = g[f"pred_{h}"] * (1 + rel.quantile(0.9))
                preds.setdefault(nombre, []).append(out.drop(columns="real"))
                mae = (val[f"pred_{h}"] - val["real"]).abs().groupby(val["area"]).mean().round(2).to_dict()
                resumen.append({"config": nombre, "h": nombre_h, "filas_ent": len(ent), "seg": round(time.time() - t0),
                                "mae_2025": mae, "columnas": cols})
                log(nombre, nombre_h, len(ent), "filas ·", round(time.time() - t0), "s · MAE 2025:", mae)
    for nombre, piezas in preds.items():
        a, b = piezas
        j = a.merge(b, on=["DateTime", "area"], how="outer")
        j.to_parquet(SAL / f"{nombre}_c2048.parquet")
    (SAL / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1))
    log("TERMINO")


if __name__ == "__main__":
    main()
