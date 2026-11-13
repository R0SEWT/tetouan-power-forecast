"""Ajuste fino de Chronos-2 solo con datos hasta 2024-12-31. Uso: python ajuste_fino.py <nombre> <lr> <pasos> <full|lora> <cov:0|1>"""
import sys
import time

import numpy as np
from chronos import Chronos2Pipeline

nombre, lr, pasos, modo, cov = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4], int(sys.argv[5])
sys.path.insert(0, "/content")
sys.argv = ["chronos2_variantes", "x", "x", "0", "2025-01-01", "2025-01-02"]  # chronos2_variantes lee sus argumentos al importarse
from chronos2_variantes import AREAS, cargar_datos

valores, fechas, conocida, interpolada, error, feriado = cargar_datos()
fin = int(np.flatnonzero(fechas < "2025-01-01")[-1]) + 1
if cov:
    # en el ajuste la temperatura "conocida a futuro" es la interpolada más el error diario (el pronóstico simulado)
    entradas = [{"target": valores[:fin, j],
                 "past_covariates": {"temp": np.nan_to_num(interpolada[a][:fin] + error[:fin], nan=float(np.nanmean(interpolada[a][:fin]))),
                                     "feriado": feriado[:fin]},
                 "future_covariates": {"temp": None, "feriado": None}} for j, a in enumerate(AREAS)]
    if cov == 2:  # solo calendario
        for e in entradas:
            del e["past_covariates"]["temp"], e["future_covariates"]["temp"]
else:
    entradas = [valores[:fin, j] for j in range(len(AREAS))]
pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cuda")
t = time.time()
kw = {"finetune_mode": modo}
nuevo = pipe.fit(entradas, prediction_length=48, context_length=2048, learning_rate=lr, num_steps=pasos, batch_size=256,
                 output_dir=f"/content/ft/{nombre}", **kw)
print(f"AJUSTE {nombre} lr={lr} pasos={pasos} modo={modo} cov={cov}: {(time.time() - t) / 60:.1f} min", flush=True)
print("FIN_FT", nombre, flush=True)
