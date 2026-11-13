"""Pronóstico zero-shot con modelos fundacionales sobre la demanda por área del SEIN (se ejecuta en la VM de Colab).

Para cada origen t (fin del periodo, cada 30 min) de 2025 y 2026 se da como contexto la demanda hasta t y se piden 48
pasos. Se guardan los pasos 2 (1 h) y 48 (24 h), que son los horizontes del proyecto, con sus cuantiles 0.1 y 0.9.
Es retomable: escribe un parquet por bloque de orígenes.

Uso: python fm_bench.py <modelo> [contexto] [inicio] [fin]
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

MODELO = sys.argv[1]
CONTEXTO = int(sys.argv[2]) if len(sys.argv) > 2 else 2048
INICIO = pd.Timestamp(sys.argv[3] if len(sys.argv) > 3 else "2025-01-01")
FIN = pd.Timestamp(sys.argv[4] if len(sys.argv) > 4 else "2026-10-23")
AREAS = ["NORTE", "CENTRO", "SUR"]
H = 48
PASOS = [2, 48]
BLOQUE = 4096  # orígenes por archivo
SUFIJO = "_" + sys.argv[5] if len(sys.argv) > 5 and not sys.argv[5][0].isdigit() else ""
SALIDA = Path(f"/content/fm/{MODELO}_c{CONTEXTO}{SUFIJO}")
SALIDA.mkdir(parents=True, exist_ok=True)

demanda = pd.read_parquet("/content/datos/demanda_areas.parquet").set_index("DateTime")[AREAS]
demanda = demanda.asfreq("30min").interpolate(limit_direction="both")  # 336 huecos de la capa silver
valores = demanda.to_numpy(dtype=np.float32)
fechas = demanda.index
origenes = np.flatnonzero((fechas >= INICIO) & (fechas < FIN))

from adaptadores import cargar

predecir = cargar(MODELO, H)  # predecir(contextos [B, C]) -> (punto [B, H], q10 [B, H], q90 [B, H])

inicio = time.time()
for b in range(0, len(origenes), BLOQUE):
    destino = SALIDA / f"bloque_{b // BLOQUE:04d}.parquet"
    if destino.exists():
        continue
    idx = origenes[b:b + BLOQUE]
    partes = []
    for j, area in enumerate(AREAS):
        contextos = np.stack([valores[i - CONTEXTO + 1:i + 1, j] for i in idx])
        punto, q10, q90 = predecir(contextos)
        fila = {"DateTime": fechas[idx], "area": area}
        for p in PASOS:
            fila[f"pred_{p}"] = punto[:, p - 1]
            fila[f"q10_{p}"] = q10[:, p - 1]
            fila[f"q90_{p}"] = q90[:, p - 1]
        partes.append(pd.DataFrame(fila))
    pd.concat(partes).to_parquet(destino.with_suffix(".tmp"))
    destino.with_suffix(".tmp").rename(destino)
    hechos = min(b + BLOQUE, len(origenes))
    print(f"[{time.strftime('%H:%M')}] {MODELO} {hechos}/{len(origenes)} orígenes · {(time.time() - inicio) / 60:.1f} min",
          flush=True)
pd.concat(pd.read_parquet(f) for f in sorted(SALIDA.glob("bloque_*.parquet"))).to_parquet(f"/content/fm/{MODELO}_c{CONTEXTO}{SUFIJO}.parquet")
print("TERMINO", MODELO, flush=True)
