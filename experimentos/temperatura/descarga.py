"""Baja el archivo de pronósticos de temperatura de Open-Meteo (Previous Runs API) para las seis ciudades.

Qué archiva y cómo se usa: ver `tetouan_power_forecast.temperatura_pronosticada`. Aquí se bajan dos modelos para
elegir la fuente con 2025 (`fuente.py`): GFS (`gfs_seamless`, desde marzo de 2021) y «best match» (desde enero de
2024). Una consulta por modelo y año con las seis ciudades; lo bajado queda tal cual en
`exogenas/bronze/open_meteo_previous_runs/` y no se vuelve a pedir si cubre las fechas.

Uso: python -m experimentos.temperatura.descarga  [--hasta AAAA-MM-DD]
"""

import argparse
import datetime as dt

import pandas as pd

from tetouan_power_forecast import temperatura_pronosticada as tp

MODELOS = ("best_match", "gfs_seamless")
LUGARES = tp.LUGARES
pedir = tp.pedir


def bajar(raiz=None, hasta=None, progreso=print):
    tp.bajar_anios(raiz, hasta, modelos=MODELOS, progreso=progreso)


def leer(raiz=None):
    """Tabla larga por hora (Lima), modelo, desfase y área (media de las ciudades del área, °C)."""
    partes = []
    for modelo in MODELOS:
        for n, horaria in tp.leer(raiz, modelo).items():
            largo = horaria.rename_axis("fecha_hora").reset_index().melt("fecha_hora", var_name="area",
                                                                          value_name="temp")
            partes.append(largo.assign(modelo=modelo, desfase=n))
    return pd.concat(partes, ignore_index=True)[["fecha_hora", "modelo", "desfase", "area", "temp"]]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--hasta", type=dt.date.fromisoformat)
    args = parser.parse_args(argv)
    bajar(hasta=args.hasta)
    t = leer()
    print(t.groupby(["modelo", "desfase", "area"])["temp"].agg(["count", lambda s: s.notna().mean()]).round(3))


if __name__ == "__main__":
    main()
