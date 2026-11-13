"""¿Ubica bien el modelo la hora del máximo de cada día? Prueba de 2026, a 24 h, por área y modelo.

Para cada día de 2026 con sus 48 periodos reales se toma la serie del día a 24 h, la misma que dibuja la app: cada
periodo es el pronóstico directo a 24 h emitido 24 h antes (no hay un pronóstico de varios pasos). La hora del
máximo pronosticado acierta si cae a ±1 h de la del máximo real. También se mide el error medio del máximo diario
en MW, y lo mismo para la mejor referencia simple del área a 24 h.

Usa los modelos que sirve la app (el base con clima y El Niño, y el híbrido y el combinado si están sus archivos)
con el mismo código que la API (``acierto_pico``), así que las cifras son las que la app muestra junto al pico.
Guarda <datos>/reportes/sein/app/pico_2026.csv.

Uso: TETOUAN_DATA=<datos> python -m experimentos.sein.pico_2026
"""

import sys

import pandas as pd

from app.backend.contrato import AREAS
from tetouan_power_forecast.medallon import raiz_datos


def tabla(pronosticadores) -> pd.DataFrame:
    """Una fila por modelo y área, con el acierto de la hora del máximo y el error del máximo diario."""
    filas = []
    for p in pronosticadores:
        for area in AREAS:
            a = p.acierto_pico(area.id, "M3")
            filas.append({
                "Modelo": getattr(p, "nombre", p.modelo), "Área": area.nombre, "Días": a.dias,
                "Hora del máximo a ±1 h (%)": a.pct_hora, "Referencia: hora a ±1 h (%)": a.pct_hora_referencia,
                "Error del máximo (MW)": a.mae_pico_mw, "Referencia: error del máximo (MW)": a.mae_pico_referencia_mw,
            })
    return pd.DataFrame(filas)


def modelos_de_la_app(raiz=None) -> list:
    from app.backend.pronosticador_hibrido import (
        PronosticadorCombinado,
        PronosticadorHibrido,
        combinado_disponible,
        hibrido_disponible,
    )
    from app.backend.pronosticador_real import PronosticadorReal

    base = PronosticadorReal(raiz)
    modelos = [base]
    if hibrido_disponible(raiz):
        modelos.append(PronosticadorHibrido(base, raiz))
        if combinado_disponible(raiz):
            modelos.append(PronosticadorCombinado(modelos[-1], raiz))
    return modelos


def main(argv=None):
    raiz = (argv or sys.argv[1:] or [None])[0]
    resultado = tabla(modelos_de_la_app(raiz))
    destino = raiz_datos(raiz) / "reportes" / "sein" / "app" / "pico_2026.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(destino, index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(resultado.to_string(index=False))
    print(f"\nGuardado en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
