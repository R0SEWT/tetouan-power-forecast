"""Firma de carga de cada zona y referencias ingenuas: la evidencia de docs/investigacion.md.

Para regenerar las tablas del documento: `uv run python -m tetouan_power_forecast.perfiles`.
"""

import numpy as np
import pandas as pd

from tetouan_power_forecast.datos import PERIODOS_DIA, ZONAS
from tetouan_power_forecast.metricas import HORIZONTE, metricas

NOMBRES = ["Zona 1", "Zona 2", "Zona 3"]
TEMPORADA_MEDIA = [3, 4, 5, 10]  # meses sin calor ni frío marcados, para comparar perfiles
# Ramadán 2017 en Marruecos fue del 27 de mayo al 25 de junio; se comparan sus días interiores
# con las cuatro semanas anteriores.
RAMADAN = ("2017-05-28", "2017-06-24")
PREVIO_RAMADAN = ("2017-04-29", "2017-05-26")
# Feriados de 2017 que cayeron en día laborable (los religiosos, según el calendario marroquí)
FERIADOS = {
    "11-ene · Manifiesto de la Independencia": "2017-01-11",
    "1-may · Día del Trabajo": "2017-05-01",
    "26-jun · Eid al-Fitr": "2017-06-26",
    "27-jun · Eid al-Fitr": "2017-06-27",
    "14-ago · Oued Ed-Dahab": "2017-08-14",
    "21-ago · Día de la Juventud": "2017-08-21",
    "1-sep · Eid al-Adha": "2017-09-01",
    "6-nov · Marcha Verde": "2017-11-06",
    "1-dic · Mawlid": "2017-12-01",
}
# Transferencia de carga de la Zona 1 a la Zona 2 el 25-oct-2017, cerca del mediodía
TRANSFERENCIA = {"antes": ("2017-10-11", "2017-10-24"), "despues": ("2017-10-26", "2017-11-08")}
REFERENCIAS = {
    "persistencia": "el consumo actual (t)",
    "ayer": "el mismo momento de ayer (t+6−144)",
    "semana_pasada": "el mismo momento de la semana pasada (t+6−1008)",
}


def consumo_por_zona(silver):
    """El consumo de las tres zonas, indexado por fecha y con columnas Zona 1..3."""
    return silver.set_index("DateTime")[ZONAS].set_axis(NOMBRES, axis=1)


def perfil_diario(silver):
    """Consumo medio por hora en días laborables de temporada media (1 = media del día)."""
    c = consumo_por_zona(silver)
    base = c[c.index.month.isin(TEMPORADA_MEDIA) & (c.index.day_of_week < 5)]
    perfil = base.groupby(base.index.hour).mean()
    return perfil / perfil.mean()


def perfil_mensual(silver):
    """Consumo medio por mes (1 = promedio anual de la zona)."""
    c = consumo_por_zona(silver)
    return c.groupby(c.index.month).mean() / c.mean()


def sensibilidad_temperatura(silver, meses):
    """Cambio del consumo diario por cada °C de temperatura media, en % del consumo medio."""
    dia = silver.set_index("DateTime")[[*ZONAS, "Temperature"]].resample("D").mean()
    dia = dia[dia.index.month.isin(meses)]
    pendientes = [np.polyfit(dia["Temperature"], dia[z], 1)[0] / dia[z].mean() * 100 for z in ZONAS]
    return pd.Series(pendientes, index=NOMBRES)


def efecto_feriados(silver):
    """Consumo de cada feriado frente al mismo día de semana de las dos semanas antes y después."""
    diario = consumo_por_zona(silver).resample("D").mean()
    fechas = {pd.Timestamp(f) for f in FERIADOS.values()}
    filas = {}
    for nombre, fecha in FERIADOS.items():
        fecha = pd.Timestamp(fecha)
        vecinos = [fecha + pd.Timedelta(weeks=k) for k in (-2, -1, 1, 2)]
        vecinos = [v for v in vecinos if v in diario.index and v not in fechas]
        filas[nombre] = diario.loc[fecha] / diario.loc[vecinos].mean()
    return pd.DataFrame(filas).T


def _razon(c, numerador, denominador, horas=None):
    if horas:
        numerador, denominador = numerador.between_time(*horas), denominador.between_time(*horas)
    return numerador.mean() / denominador.mean()


def firma_de_carga(silver):
    """Indicadores que distinguen una zona residencial, laboral o turística. Filas: indicador."""
    c = consumo_por_zona(silver)
    media = c[c.index.month.isin(TEMPORADA_MEDIA)]
    laborable, domingo = media[media.index.day_of_week < 5], media[media.index.day_of_week == 6]
    mensual = perfil_mensual(silver)
    ramadan, previo = c.loc[slice(*RAMADAN)], c.loc[slice(*PREVIO_RAMADAN)]
    return pd.DataFrame({
        "Parte de la demanda de la ciudad (%)": c.mean() / c.mean().sum() * 100,
        "Factor de carga (media / máximo)": c.mean() / c.max(),
        "Domingo de día / laborable (9-17 h)": _razon(c, domingo, laborable, ("09:00", "17:00")),
        "Julio / promedio anual": mensual.loc[7],
        "Mes más alto / mes más bajo": mensual.max() / mensual.min(),
        "Sensibilidad al calor en verano (%/°C)": sensibilidad_temperatura(silver, [6, 7, 8, 9]),
        "Ramadán de día / mes previo (9-16 h)": _razon(c, ramadan, previo, ("09:00", "16:00")),
        "Ramadán de madrugada / mes previo (0-4 h)": _razon(c, ramadan, previo, ("00:00", "03:50")),
    }).T


def comparar_periodos(silver, antes=TRANSFERENCIA["antes"], despues=TRANSFERENCIA["despues"]):
    """Consumo medio de cada zona y de Zona 1 + Zona 2 en dos periodos, y su cambio en %."""
    c = consumo_por_zona(silver)
    c["Zona 1 + Zona 2"] = c["Zona 1"] + c["Zona 2"]
    tabla = pd.DataFrame({"antes (kW)": c.loc[slice(*antes)].mean(), "después (kW)": c.loc[slice(*despues)].mean()})
    tabla["cambio (%)"] = (tabla["después (kW)"] / tabla["antes (kW)"] - 1) * 100
    return tabla


def referencias_ingenuas(silver, zona=1):
    """Para cada momento t: el consumo real en t+6 y lo que predice cada referencia ingenua."""
    s = silver.set_index("DateTime")[ZONAS[zona - 1]]
    return pd.DataFrame({
        "real": s.shift(-HORIZONTE),
        "persistencia": s,
        "ayer": s.shift(PERIODOS_DIA - HORIZONTE),
        "semana_pasada": s.shift(7 * PERIODOS_DIA - HORIZONTE),
    }).dropna()


def errores_referencias(referencias):
    """MAE (kW) y MAPE (%) de cada referencia ingenua."""
    filas = {}
    for nombre in REFERENCIAS:
        mae, _, mape = metricas(referencias["real"], referencias[nombre])
        filas[nombre] = {"MAE (kW)": mae, "MAPE (%)": mape}
    return pd.DataFrame(filas).T


def tabla_markdown(df, decimales=2):
    """Una tabla markdown sin dependencias extra (pandas.to_markdown pide tabulate)."""
    indice = [" · ".join(map(str, i)) if isinstance(i, tuple) else str(i) for i in df.index]
    lineas = ["| | " + " | ".join(map(str, df.columns)) + " |", "|---|" + "---:|" * len(df.columns)]
    for nombre, fila in zip(indice, df.itertuples(index=False)):
        lineas.append(f"| {nombre} | " + " | ".join(f"{v:,.{decimales}f}" for v in fila) + " |")
    return "\n".join(lineas)


def main():
    from tetouan_power_forecast.medallon import cargar_gold, cargar_silver

    silver = cargar_silver()
    print("## Firma de carga\n")
    print(tabla_markdown(firma_de_carga(silver)))
    print("\n## Feriados en día laborable (consumo del feriado / mismo día de semana sin feriado)\n")
    print(tabla_markdown(efecto_feriados(silver)))
    print("\n## Transferencia de carga del 25 de octubre (11-24 oct frente a 26 oct-8 nov)\n")
    print(tabla_markdown(comparar_periodos(silver), decimales=1))
    print("\n## MAPE (%) de las referencias ingenuas a t+6, por partición\n")
    filas = {}
    for zona in (1, 2, 3):
        refs = referencias_ingenuas(silver, zona)
        particion = cargar_gold(zona).set_index("DateTime")["particion"]
        for parte in ("validacion", "prueba"):
            momentos = particion.index[particion == parte].intersection(refs.index)
            filas[(f"Zona {zona}", parte)] = errores_referencias(refs.loc[momentos])["MAPE (%)"]
    print(tabla_markdown(pd.DataFrame(filas).T))


if __name__ == "__main__":
    main()
