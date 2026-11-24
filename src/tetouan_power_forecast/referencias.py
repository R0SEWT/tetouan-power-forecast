"""Referencias estacionales cuyo insumo más reciente es el origen observado."""

import numpy as np
import pandas as pd

DIA = pd.Timedelta(days=1)
SEMANA = 7 * DIA


def referencias(demanda: pd.Series, origenes, objetivos, paso: pd.Timedelta) -> pd.DataFrame:
    """Calcula referencias por fechas exactas, con NaN si falta un dato necesario."""
    origen = pd.DatetimeIndex(origenes)
    objetivo = pd.DatetimeIndex(objetivos)
    claves = pd.MultiIndex.from_arrays([origen, objetivo], names=["origen", "objetivo"])
    if claves.has_duplicates or origen.hasnans or objetivo.hasnans:
        raise ValueError("Orígenes y objetivos deben formar pares únicos con fechas válidas")
    anticipacion = objetivo - origen
    if (
        paso <= pd.Timedelta(0) or DIA % paso != pd.Timedelta(0)
        or (anticipacion <= pd.Timedelta(0)).any()
        or (anticipacion % paso != pd.Timedelta(0)).any()
    ):
        raise ValueError("La anticipación debe ser positiva y un múltiplo del paso")
    if not isinstance(demanda.index, pd.DatetimeIndex) or not demanda.index.is_unique:
        raise ValueError("Se requiere una serie de demanda con fechas únicas")
    if not (demanda.index.tz == origen.tz == objetivo.tz):
        raise ValueError("Demanda, origen y objetivo deben usar la misma zona horaria")

    def valores(fechas):
        return demanda.reindex(fechas).to_numpy(dtype=float)

    def rezago(periodo):
        return ((anticipacion - paso) // periodo + 1) * periodo

    actual = valores(origen)
    diario = rezago(DIA)
    semanal = rezago(SEMANA)
    delta_diario = actual + (valores(objetivo - diario) - valores(origen - diario))
    delta_semanal = actual + (valores(objetivo - semanal) - valores(origen - semanal))

    # Ventana temporal cerrada por la derecha. Los huecos impiden completar las 24 h.
    ordenada = demanda.sort_index()
    if len(ordenada) and (((ordenada.index - ordenada.index[0]) % paso) != pd.Timedelta(0)).any():
        raise ValueError("La serie de demanda debe estar en una rejilla regular")
    nivel = ordenada.rolling(DIA, min_periods=DIA // paso).mean()
    nivel_origen = nivel.reindex(origen).to_numpy(dtype=float)
    ajustadas = []
    for semana in range(1, 5):
        desplazamiento = semana * semanal
        nivel_anterior = nivel.reindex(origen - desplazamiento).to_numpy(dtype=float)
        factor = np.divide(
            nivel_origen, nivel_anterior, out=np.full(len(origen), np.nan),
            where=nivel_anterior != 0,
        )
        ajustadas.append(valores(objetivo - desplazamiento) * factor)

    return pd.DataFrame({
        "persistencia": actual,
        "delta_diario": delta_diario,
        "delta_semanal": delta_semanal,
        "promedio_deltas": (delta_diario + delta_semanal) / 2,
        "semana_ajustada": ajustadas[0],
        "cuatro_semanas_ajustadas": np.mean(ajustadas, axis=0),
    }, index=claves)
