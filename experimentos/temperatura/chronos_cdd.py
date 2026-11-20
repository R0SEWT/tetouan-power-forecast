"""(c) Chronos-2 ajustado con feriados y con los grados sobre el umbral pronosticados como covariable. VM de Colab.

La misma receta que `chronos2ftcal` (experimentos/fundacionales/ajuste_fino.py: datos ≤ 2024, lr 1e-6, 3000 pasos,
ajuste completo, contexto 2048, 48 pasos, lote 256), con una covariable más: `cdd`, los grados de la media diaria
sobre el umbral del área (nivel ERA5), repetidos en los 48 periodos del día.

- Ajuste: la serie de `cdd` es la del pronóstico de desfase 2 (GFS, nivel ERA5) donde existe (desde marzo de 2021) y
  la observada antes. Chronos-2 la trata como conocida a futuro dentro de cada ventana.
- Pronóstico desde el origen t: en el contexto y en los 48 pasos siguientes, cada día lleva su **edición vigente**
  en t (comun.edicion_vigente: el menor desfase ya publicado, con 8 h de demora). Nunca la observada.

Entradas en la VM: /content/datos/demanda_areas.parquet (silver + capa en vivo, sin huecos) y
/content/datos/cdd_por_edicion.parquet (comun.cdd_por_edicion).
Uso: python chronos_cdd.py ajuste            → /content/ft/ft_cal_cdd
     python chronos_cdd.py pronostico INICIO FIN → /content/fm/chronos2ftcalcdd_c2048.parquet
"""

import os
import sys
import time
from pathlib import Path

import holidays
import numpy as np
import pandas as pd

AREAS = ["NORTE", "CENTRO", "SUR"]
CONTEXTO, H, PASOS = 2048, 48, (2, 48)
DEMORA_H = 8
BLOQUE, LOTE = 4096, int(os.environ.get("LOTE", "192"))
FT = Path("/content/ft/ft_cal_cdd")
SALIDA = Path("/content/fm/chronos2ftcalcdd_c2048")


def cargar():
    demanda = pd.read_parquet("/content/datos/demanda_areas.parquet").set_index("DateTime")[AREAS]
    demanda = demanda.asfreq("30min").interpolate(limit_direction="both")
    fechas = demanda.index
    dia_periodo = (fechas - pd.Timedelta(minutes=30)).normalize()
    pe = holidays.country_holidays("PE", years=range(2015, 2029))
    feriado = np.array([d in pe for d in dia_periodo], dtype=np.float32)
    cdd = pd.read_parquet("/content/datos/cdd_por_edicion.parquet")
    return demanda.to_numpy(dtype=np.float32), fechas, dia_periodo, feriado, cdd


def tablas_diarias(cdd, area, dias):
    """[4, n_dias] con obs, v1, v2, v3 para los días `dias` (sin dato: la edición siguiente, luego la observada, 0)."""
    t = cdd[cdd["area"] == area].set_index("dia").reindex(dias)
    m = t[["obs", "v1", "v2", "v3"]].to_numpy(dtype=np.float32).T
    for k in (3, 2, 1):  # una edición vacía toma la siguiente más antigua y, al final, la observada
        siguiente = m[k + 1] if k < 3 else m[0]
        m[k] = np.where(np.isnan(m[k]), siguiente, m[k])
    m[0] = np.where(np.isnan(m[0]), m[1], m[0])
    return np.nan_to_num(m, nan=0.0)


def ajuste():
    from chronos import Chronos2Pipeline

    valores, fechas, dia_periodo, feriado, cdd = cargar()
    fin = int(np.flatnonzero(fechas < "2025-01-01")[-1]) + 1
    dias = pd.DatetimeIndex(np.sort(dia_periodo.unique()))
    pos = dias.get_indexer(dia_periodo)
    entradas = []
    for j, area in enumerate(AREAS):
        m = tablas_diarias(cdd, area, dias)
        v2 = cdd[cdd["area"] == area].set_index("dia")["v2"].reindex(dias).to_numpy()
        serie = np.where(np.isnan(v2), m[0], m[2])[pos].astype(np.float32)  # pronóstico donde existe
        entradas.append({"target": valores[:fin, j],
                         "past_covariates": {"feriado": feriado[:fin], "cdd": serie[:fin]},
                         "future_covariates": {"feriado": None, "cdd": None}})
    assert fechas[fin - 1] < pd.Timestamp("2025-01-01") and all(len(e["target"]) == fin for e in entradas)
    pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cuda")
    t = time.time()
    pipe.fit(entradas, prediction_length=H, context_length=CONTEXTO, learning_rate=1e-6, num_steps=3000,
             batch_size=256, output_dir=str(FT), finetune_mode="full")
    print(f"AJUSTE ft_cal_cdd: {(time.time() - t) / 60:.1f} min", flush=True)
    print("FIN_FT", flush=True)


def pronostico(inicio, fin):
    import torch
    from chronos import Chronos2Pipeline

    valores, fechas, dia_periodo, _, cdd = cargar()
    n = len(fechas)
    dias = pd.DatetimeIndex(np.sort(dia_periodo.unique()))
    ultimo = dias[-1] + pd.Timedelta(days=2)
    dias = pd.date_range(dias[0], ultimo, freq="D")  # el futuro del último origen también
    tablas = {a: tablas_diarias(cdd, a, dias) for a in AREAS}
    # posición de día y día de cada periodo, extendido 48 pasos después del último dato
    todas = pd.date_range(fechas[0], periods=n + H, freq="30min")
    dia_todas = (todas - pd.Timedelta(minutes=30)).normalize()
    pos_dia = dias.get_indexer(dia_todas)
    pe = holidays.country_holidays("PE", years=range(2015, 2029))
    feriado_todas = np.array([d in pe for d in dia_todas], dtype=np.float32)
    dia_ns = dia_todas.to_numpy().astype("datetime64[h]").astype(np.int64)  # horas desde la época
    t_ns = todas.to_numpy().astype("datetime64[m]").astype(np.int64) / 60.0
    origenes = np.flatnonzero((fechas >= pd.Timestamp(inicio)) & (fechas < pd.Timestamp(fin)))
    pipe = Chronos2Pipeline.from_pretrained(str(FT / "finetuned-ckpt"), device_map="cuda")
    SALIDA.mkdir(parents=True, exist_ok=True)
    empezo, bloques = time.time(), []
    for b in range(0, len(origenes), BLOQUE):
        idx = origenes[b:b + BLOQUE]
        destino = SALIDA / f"bloque_{idx[0]}_{idx[-1]}.parquet"
        bloques.append(destino)
        if destino.exists():
            continue
        ventana = idx[:, None] + np.arange(-CONTEXTO + 1, H + 1)[None, :]  # [B, C + H]
        falta = dia_ns[ventana] + 23 + DEMORA_H - t_ns[idx][:, None]  # horas hasta que sale el día entero
        edicion = np.clip(np.ceil(falta / 24), 1, 3).astype(int)
        partes = []
        for j, area in enumerate(AREAS):
            covar = tablas[area][edicion, pos_dia[ventana]]
            entradas = [{"target": valores[i - CONTEXTO + 1:i + 1, j],
                         "past_covariates": {"feriado": feriado_todas[i - CONTEXTO + 1:i + 1],
                                             "cdd": covar[k, :CONTEXTO]},
                         "future_covariates": {"feriado": feriado_todas[i + 1:i + 1 + H], "cdd": covar[k, CONTEXTO:]}}
                        for k, i in enumerate(idx)]
            with torch.inference_mode():
                q, _ = pipe.predict_quantiles(entradas, prediction_length=H, quantile_levels=[0.1, 0.5, 0.9],
                                              batch_size=LOTE, context_length=CONTEXTO)
            q = np.stack([x.detach().float().cpu().numpy()[0] for x in q])
            fila = {"DateTime": fechas[idx], "area": area}
            for p in PASOS:
                fila[f"pred_{p}"], fila[f"q10_{p}"], fila[f"q90_{p}"] = q[:, p - 1, 1], q[:, p - 1, 0], q[:, p - 1, 2]
            partes.append(pd.DataFrame(fila))
        pd.concat(partes).to_parquet(destino.with_suffix(".tmp"))
        destino.with_suffix(".tmp").rename(destino)
        print(f"[{time.strftime('%H:%M')}] {min(b + BLOQUE, len(origenes))}/{len(origenes)} · "
              f"{(time.time() - empezo) / 60:.1f} min", flush=True)
    pd.concat(pd.read_parquet(f) for f in bloques).to_parquet("/content/fm/chronos2ftcalcdd_c2048.parquet")
    print("TERMINO", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "ajuste":
        ajuste()
    else:
        pronostico(sys.argv[2], sys.argv[3])
