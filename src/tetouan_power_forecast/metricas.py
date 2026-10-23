"""Métricas de error con las que se compara cada modelo contra el baseline de persistencia."""

import numpy as np

HORIZONTE = 6  # 6 periodos de 10 minutos = 1 hora


def metricas(y_real, y_pred):
    """Devuelve (MAE, RMSE, MAPE en %). MAE y RMSE quedan en kW, la unidad del consumo."""
    y_real = np.asarray(y_real, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mae = np.mean(np.abs(y_real - y_pred))
    rmse = np.sqrt(np.mean((y_real - y_pred) ** 2))
    mape = np.mean(np.abs((y_real - y_pred) / y_real)) * 100
    return mae, rmse, mape
