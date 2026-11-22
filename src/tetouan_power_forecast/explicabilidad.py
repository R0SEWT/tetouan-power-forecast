"""Explicabilidad del modelo de la app: valores SHAP en MW y por familias de variables (notebook 05).

El XGBoost de la app va envuelto en `ModeloRazon`: el árbol predice la razón demanda(t+H) / media_24h(t) y el
envoltorio la multiplica por `media_24h`. Los valores SHAP del árbol (TreeExplainer) suman la razón:
``razón = base + Σ φ``. Multiplicados por la `media_24h` de cada fila suman el pronóstico en MW, de forma exacta:
``pronóstico = media_24h · base + Σ media_24h · φ``. Por eso `media_24h` no aparece como variable: es la escala, y su
efecto es el punto de partida de cada explicación (``media_24h · base``, el nivel del último día).

Este módulo no importa `shap`: recibe los valores ya calculados, así se prueba sin la dependencia.
"""

import numpy as np
import pandas as pd

from tetouan_power_forecast.variables_sein import GRUPOS

# Las mismas familias que la importancia por grupo de la app (`GRUPOS_IMPORTANCIA`), más el código del área del modelo
# global. Juntas, demanda reciente, calendario y código de área forman el grupo «M0 (demanda y calendario)» del
# notebook 02.
FAMILIAS = {
    "Demanda reciente": ["Area_t", "Area_t_menos_1", "Area_t_menos_2", "Area_t_menos_4", "Area_ayer",
                         "Area_semana_pasada", "Area_media_1h", "Area_desv_1h", "Area_m24_vs_m7d"],
    "Calendario": ["Hour", "MinuteOfDay", "DayOfWeek", "Time_Sin", "Time_Cos", "Week_Sin", "Week_Cos", "Obj_Sin",
                   "Obj_Cos", "DiaSemanaObjetivo", "FinDeSemanaObjetivo", "FeriadoObjetivo", "Cuarentena"],
    "Código de área": ["area_cod"],
    "Clima": GRUPOS["clima"],
    "El Niño": GRUPOS["nino"],
    "Fallas": GRUPOS["fallas"],
}
FAMILIAS_M0 = ("Demanda reciente", "Calendario", "Código de área")

# El nombre de cada variable en palabras de quien programa la operación, para los gráficos que lee el negocio
# (Entregable 8). Las de demanda van en razón: divididas por la media de las últimas 24 h del área. «Hora objetivo»
# es t+H, la hora que se pronostica.
NOMBRES_LLANOS = {
    "Area_t": "Demanda ahora (÷ media 24 h)",
    "Area_t_menos_1": "Demanda hace 30 min (÷ media 24 h)",
    "Area_t_menos_2": "Demanda hace 1 h (÷ media 24 h)",
    "Area_t_menos_4": "Demanda hace 2 h (÷ media 24 h)",
    "Area_ayer": "Demanda 24 h antes de la hora objetivo (÷ media 24 h)",
    "Area_semana_pasada": "Demanda 7 días antes de la hora objetivo (÷ media 24 h)",
    "Area_media_1h": "Media de la última hora (÷ media 24 h)",
    "Area_desv_1h": "Variación en la última hora (÷ media 24 h)",
    "Area_m24_vs_m7d": "Último día frente a la semana (media 24 h ÷ media 7 días)",
    "Hour": "Hora del día (ahora)",
    "MinuteOfDay": "Minuto del día (ahora)",
    "DayOfWeek": "Día de la semana (ahora)",
    "Time_Sin": "Hora del día (ahora, seno)",
    "Time_Cos": "Hora del día (ahora, coseno)",
    "Week_Sin": "Día de la semana (ahora, seno)",
    "Week_Cos": "Día de la semana (ahora, coseno)",
    "Obj_Sin": "Hora objetivo (seno)",
    "Obj_Cos": "Hora objetivo (coseno)",
    "DiaSemanaObjetivo": "Día de la semana objetivo",
    "FinDeSemanaObjetivo": "Fin de semana objetivo",
    "FeriadoObjetivo": "Feriado el día objetivo",
    "Cuarentena": "Cuarentena de 2020",
    "area_cod": "Área (código)",
    "temp": "Temperatura ahora",
    "temp_media_24h": "Temperatura media de 24 h",
    "temp_anomalia": "Anomalía de temperatura (frente a lo normal)",
    "temp_objetivo": "Temperatura pronosticada a la hora objetivo",
    "icen": "ICEN (El Niño costero)",
    "nino12_ssta": "Anomalía del mar en Niño 1+2",
    "fallas_en_curso": "Fallas en curso en la red",
}


def llano(columna: str) -> str:
    """El nombre llano de una variable (el de la columna si no tiene uno)."""
    return NOMBRES_LLANOS.get(columna, columna)


def familia_de(columna: str) -> str:
    for familia, columnas in FAMILIAS.items():
        if columna in columnas:
            return familia
    return "Otras"


def a_mw(valores, base, escala):
    """Pasa los valores SHAP de la razón (filas × variables) y su base a MW, con la escala de cada fila."""
    escala = np.asarray(escala, dtype=float)
    return np.asarray(valores, dtype=float) * escala[:, None], np.asarray(base, dtype=float) * escala


def por_familia(valores_mw: pd.DataFrame) -> pd.DataFrame:
    """La contribución de cada familia en cada fila: la suma de las de sus variables (SHAP es aditivo)."""
    return valores_mw.T.groupby(valores_mw.columns.map(familia_de)).sum().T


def importancia(valores_mw: pd.DataFrame) -> pd.Series:
    """Importancia global: el valor absoluto medio de la contribución, de mayor a menor (en MW)."""
    return valores_mw.abs().mean().sort_values(ascending=False)


def contribuciones(fila_mw: pd.Series, datos: pd.Series, top=8) -> pd.DataFrame:
    """Las `top` variables que más mueven un pronóstico, con su valor, y el resto sumado en una sola fila."""
    orden = fila_mw.abs().sort_values(ascending=False).index
    elegidas = list(orden[:top])
    tabla = pd.DataFrame({"variable": elegidas, "valor": [datos[c] for c in elegidas],
                          "contribucion_mw": fila_mw[elegidas].to_numpy()})
    resto = orden[top:]
    if len(resto):
        tabla.loc[len(tabla)] = [f"otras {len(resto)} variables", np.nan, float(fila_mw[resto].sum())]
    return tabla
