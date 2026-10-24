import numpy as np
import pandas as pd

from experimentos.sein.linea_base import correr
from tetouan_power_forecast.variables_sein import AREAS


def test_la_linea_base_corre_de_punta_a_punta_con_datos_chicos():
    fechas = pd.date_range("2024-01-01 00:30", "2025-01-20 00:00", freq="30min")  # un año: la climatología cubre enero
    hora = fechas.hour + fechas.minute / 60
    rng = np.random.default_rng(0)
    demanda = pd.DataFrame({"DateTime": fechas})
    for area, nivel in zip(AREAS, [1200.0, 4100.0, 1700.0], strict=True):
        demanda[area] = nivel * (1 + 0.2 * np.sin(2 * np.pi * (hora - 14) / 24)) + rng.normal(0, 10, len(fechas))
    demanda["SEIN"] = demanda[AREAS].sum(axis=1)
    horas = pd.date_range("2023-12-31", "2025-01-25", freq="h")
    exogenas = {
        "temperatura": pd.DataFrame({"fecha_hora": horas, "norte": 25.0, "centro": 20.0, "sur": 15.0}),
        "icen": pd.DataFrame({"mes": pd.date_range("2023-09-01", "2025-01-01", freq="MS"), "icen": 0.5}),
        "nino12": pd.DataFrame({"semana": pd.date_range("2023-12-06", "2025-01-15", freq="7D"),
                                "nino12_sst": 24.0, "nino12_ssta": 0.3}),
        "eventos": pd.DataFrame({"inicio": pd.to_datetime(["2025-01-05 10:00"]),
                                 "final": pd.to_datetime(["2025-01-05 11:00"])}),
    }
    resultados = correr(demanda, exogenas, horizontes={"1h": 2}, variantes=["M0", "M3"], max_iter=10,
                        progreso=lambda texto: None)
    assert set(resultados["area"]) == set(AREAS)
    assert {"M0", "M3", "ref_persistencia", "M3 - M0 (MAE, IC 95 %)"} <= set(resultados["metodo"])
    assert (resultados.loc[resultados["metodo"] == "M0", "filas_validacion"] > 0).all()
