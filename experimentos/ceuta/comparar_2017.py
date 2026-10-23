"""Ceuta y Tetuán en el mismo año: qué tanto se parecen y si podrían ser la misma serie.

Baja de REData (la API oficial de REE) la demanda horaria de Ceuta de 2017, doce consultas de unos 56 KB,
y la compara con las zonas de Tetuán promediadas por hora: escala, estacionalidad, correlaciones, fin de
semana, feriados de cada país y Ramadán (docs/historico.md, opción 8). Guarda las respuestas en
<datos>/ceuta/bronze/redata/ y la tabla en <datos>/reportes/ceuta/comparacion_2017.csv.

Uso: python -m experimentos.ceuta.comparar_2017
"""

import json
import time

import pandas as pd

from experimentos.historico import rolling as R
from tetouan_power_forecast.ceuta import ZONA_HORARIA, _descargar_texto
from tetouan_power_forecast.medallon import _reemplazar, _ruta, cargar_silver

URL_REDATA = ("https://apidatos.ree.es/es/datos/demanda/evolucion?start_date={inicio}T00:00"
              "&end_date={fin}T23:59&time_trunc=hour&geo_trunc=electric_system&geo_limit=ceuta&geo_ids=8744")
ANIO = 2017
# Feriados que solo tiene uno de los dos lados, más los islámicos (fechas aproximadas, ±1 día)
FERIADOS = {
    "España": ["2017-01-06", "2017-04-13", "2017-04-14", "2017-08-15", "2017-10-12", "2017-12-06", "2017-12-08",
               "2017-12-25"],
    "Fiesta del Cordero": ["2017-09-01"],
    "Fin del Ramadán": ["2017-06-26"],
    "Mawlid": ["2017-12-01"],
}


def horaria_redata(anio=ANIO, raiz=None, descargar=_descargar_texto, pausa=1.0):
    """Demanda horaria de Ceuta en MW, en hora local peninsular; un archivo por mes, sin repetir descargas."""
    valores = []
    for mes in pd.period_range(f"{anio}-01", f"{anio}-12", freq="M"):
        destino = _ruta(raiz, "ceuta/bronze/redata", f"{mes}.json")
        if not destino.exists():
            texto = descargar(URL_REDATA.format(inicio=mes.start_time.date(), fin=mes.end_time.date()))
            json.loads(texto)  # que sea JSON válido antes de guardarlo
            _reemplazar(destino, lambda ruta, texto=texto: ruta.write_text(texto))
            time.sleep(pausa)
        valores += json.loads(destino.read_text())["included"][0]["attributes"]["values"]
    serie = pd.Series([v["value"] for v in valores],
                      index=pd.to_datetime([v["datetime"] for v in valores], utc=True), name="Ceuta")
    serie = serie[~serie.index.duplicated()].sort_index()
    serie.index = serie.index.tz_convert(ZONA_HORARIA).tz_localize(None)
    return serie[~serie.index.duplicated()]  # la hora repetida de octubre queda una sola vez


def efecto_dia(diario, dia):
    """% del consumo del día contra el mismo día de la semana dos semanas antes y dos después."""
    dia = pd.Timestamp(dia)
    referencia = [dia + pd.Timedelta(weeks=k) for k in (-2, -1, 1, 2)]
    return 100 * (diario.loc[dia] / diario.loc[[d for d in referencia if d in diario.index]].mean() - 1)


def comparar(ceuta, tetuan):
    """Una columna por serie (Ceuta, las tres zonas y su suma), con las cifras de docs/historico.md."""
    horas = (tetuan.set_index("DateTime")[list(R.ZC.values())].resample("h").mean() / 1000)
    horas.columns = [f"Zona {z}" for z in R.ZC]
    horas["Tetuán"] = horas.sum(axis=1)
    series = pd.concat([ceuta, horas], axis=1, join="inner")
    diario = series.resample("D").mean()
    mensual = series.groupby(series.index.month).mean()
    perfil = series.groupby(series.index.hour).mean()
    ram = R.RAMADAN
    previas = (pd.Timestamp(ram[0]) - pd.Timedelta(weeks=4), pd.Timestamp(ram[0]) - pd.Timedelta(days=1))

    def noche(desde, hasta):
        tramo = series.loc[desde:hasta]
        return tramo[tramo.index.hour < 3].mean()

    filas = {
        "demanda media (MW)": series.mean(),
        "mes más alto / mes más bajo": mensual.max() / mensual.min(),
        "julio / promedio": mensual.loc[7] / series.mean(),
        "correlación del perfil horario medio con Ceuta": perfil.corrwith(perfil["Ceuta"]),
        "correlación hora a hora con Ceuta": series.corrwith(series["Ceuta"]),
        "correlación de la variación diaria con Ceuta": diario.diff().corrwith(diario["Ceuta"].diff()),
        "sábado / promedio": diario[diario.index.day_of_week == 5].mean() / diario.mean(),
        "Ramadán, 0 a 3 h contra las 4 semanas previas (%)": 100 * (noche(*ram) / noche(*previas) - 1),
    }
    for nombre, dias in FERIADOS.items():
        efectos = pd.DataFrame({dia: diario.apply(efecto_dia, dia=dia) for dia in dias})
        if len(dias) == 1:
            filas[f"{nombre} (%)"] = efectos.iloc[:, 0]
        else:
            filas[f"feriados de {nombre}, mínimo (%)"] = efectos.min(axis=1)
            filas[f"feriados de {nombre}, máximo (%)"] = efectos.max(axis=1)
    return pd.DataFrame(filas).T.round(2)


def main():
    tabla = comparar(horaria_redata(), cargar_silver())
    with pd.option_context("display.width", 200, "display.max_columns", 10):
        print(tabla)
    R.guardar(tabla.rename_axis("medida").reset_index(), "comparacion_2017.csv", carpeta="ceuta")


if __name__ == "__main__":
    main()
