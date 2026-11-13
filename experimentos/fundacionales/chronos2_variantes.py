"""Chronos-2 sobre los mismos orígenes que fm_bench, con covariables y/o pesos ajustados (VM de Colab).

Covariables (regla de información del proyecto):
- temp (pasada): la última temperatura horaria del área ya publicada en cada instante (como _temperatura_conocida).
- temp (futura): el pronóstico simulado = temperatura interpolada de t+k + un error N(0, 1.5 °C) por día de emisión
  (como temp_objetivo / error_pronostico_diario, semilla 0). Nunca la observada. Fuera del archivo de clima se repite
  el último valor conocido en el origen.
- feriado (pasada y futura): calendario de Perú, conocido de antemano.

Uso: python chronos2_variantes.py <nombre> <modelo|ruta> <cov:0 sin, 1 temperatura+feriado, 2 solo feriado> <inicio> <fin> [contexto]
"""

import sys
import time
from pathlib import Path

import holidays
import numpy as np
import pandas as pd
import torch
from chronos import Chronos2Pipeline

NOMBRE, MODELO, COV, INICIO, FIN = sys.argv[1], sys.argv[2], int(sys.argv[3]), pd.Timestamp(sys.argv[4]), pd.Timestamp(sys.argv[5])
CONTEXTO = int(sys.argv[6]) if len(sys.argv) > 6 else 2048
AREAS = ["NORTE", "CENTRO", "SUR"]
H, PASOS, BLOQUE, LOTE = 48, [2, 48], 4096, 1024
SALIDA = Path(f"/content/fm/{NOMBRE}_c{CONTEXTO}")
SALIDA.mkdir(parents=True, exist_ok=True)


def cargar_datos():
    demanda = pd.read_parquet("/content/datos/demanda_areas.parquet").set_index("DateTime")[AREAS]
    demanda = demanda.asfreq("30min").interpolate(limit_direction="both")
    fechas = demanda.index
    temperatura = pd.read_parquet("/content/datos/temperatura_areas.parquet")
    conocida, interpolada = {}, {}
    for a in AREAS:
        horaria = temperatura.set_index("fecha_hora")[a.lower()].sort_index().dropna()
        conocida[a] = horaria.reindex(fechas, method="ffill").bfill().to_numpy(dtype=np.float32)  # tras el archivo: último valor
        unida = horaria.reindex(horaria.index.union(fechas))
        interpolada[a] = unida.interpolate(method="time", limit_area="inside").reindex(fechas).to_numpy(dtype=np.float32)
    dias = pd.Series(fechas).dt.normalize()
    unicos = np.sort(dias.unique())
    error = dias.map(dict(zip(unicos, np.random.default_rng(0).normal(0, 1.5, len(unicos))))).to_numpy(dtype=np.float32)
    pe = holidays.country_holidays("PE", years=range(2015, 2028))
    dia_periodo = (fechas - pd.Timedelta(minutes=30)).normalize()  # DateTime marca el fin del periodo
    feriado = np.array([d in pe for d in dia_periodo], dtype=np.float32)
    return demanda.to_numpy(dtype=np.float32), fechas, conocida, interpolada, error, feriado


if __name__ == "__main__":
    valores, fechas, conocida, interpolada, error, feriado = cargar_datos()
    origenes = np.flatnonzero((fechas >= INICIO) & (fechas < FIN))
    origenes = origenes[origenes + H < len(fechas) + H]  # todos; el futuro fuera del índice se rellena abajo
    pipe = Chronos2Pipeline.from_pretrained(MODELO, device_map="cuda")
    n = len(fechas)
    inicio = time.time()
    for b in range(0, len(origenes), BLOQUE):
        destino = SALIDA / f"bloque_{b // BLOQUE:04d}.parquet"
        if destino.exists():
            continue
        idx = origenes[b:b + BLOQUE]
        partes = []
        for j, area in enumerate(AREAS):
            if COV:
                entradas = []
                for i in idx:
                    fut = np.arange(i + 1, i + 1 + H)
                    dentro = np.minimum(fut, n - 1)
                    temp_fut = interpolada[area][dentro] + error[i]
                    temp_fut = np.where((fut < n) & ~np.isnan(temp_fut), temp_fut, conocida[area][i])
                    # feriado futuro: calendario; pasado el índice se calcula igual con el último día (aprox.)
                    pas = {"temp": conocida[area][i - CONTEXTO + 1:i + 1], "feriado": feriado[i - CONTEXTO + 1:i + 1]}
                    futc = {"temp": temp_fut.astype(np.float32), "feriado": feriado[dentro]}
                    if COV == 2:  # solo calendario
                        del pas["temp"], futc["temp"]
                    entradas.append({"target": valores[i - CONTEXTO + 1:i + 1, j], "past_covariates": pas,
                                     "future_covariates": futc})
            else:
                entradas = np.stack([valores[i - CONTEXTO + 1:i + 1, j] for i in idx])[:, None, :]
            with torch.inference_mode():
                q, _ = pipe.predict_quantiles(entradas, prediction_length=H, quantile_levels=[0.1, 0.5, 0.9],
                                              batch_size=LOTE, context_length=CONTEXTO)
            q = np.stack([x.detach().float().cpu().numpy()[0] for x in q])  # [B, H, 3]
            fila = {"DateTime": fechas[idx], "area": area}
            for p in PASOS:
                fila[f"pred_{p}"], fila[f"q10_{p}"], fila[f"q90_{p}"] = q[:, p - 1, 1], q[:, p - 1, 0], q[:, p - 1, 2]
            partes.append(pd.DataFrame(fila))
        pd.concat(partes).to_parquet(destino.with_suffix(".tmp"))
        destino.with_suffix(".tmp").rename(destino)
        print(f"[{time.strftime('%H:%M')}] {NOMBRE} {min(b + BLOQUE, len(origenes))}/{len(origenes)} · {(time.time() - inicio) / 60:.1f} min", flush=True)
    pd.concat(pd.read_parquet(f) for f in sorted(SALIDA.glob("bloque_*.parquet"))).to_parquet(f"/content/fm/{NOMBRE}_c{CONTEXTO}.parquet")
    print("TERMINO", NOMBRE, flush=True)
