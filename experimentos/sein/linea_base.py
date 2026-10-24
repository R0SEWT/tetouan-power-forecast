"""Línea base del caso peruano en la validación de 2025: ¿cuánto ayudan las exógenas a 1 h y a 24 h?

Para cada área y horizonte entrena un Gradient Boosting en razón (`ModeloRazon`) con las variantes M0 a M3 de la
spec (§8.3) sobre 2016-2024 y lo evalúa en 2025 contra las tres referencias ingenuas, sobre las mismas filas
para todas las variantes. La diferencia M3 − M0 va con su intervalo por bootstrap de días. La prueba de 2026 no
se toca. Lee el silver de áreas y el de exógenas de la carpeta de datos y guarda
<datos>/reportes/sein/linea_base.csv.

Uso: python -m experimentos.sein.linea_base
"""

import time

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from experimentos.historico.rolling import guardar
from tetouan_power_forecast.coes import cargar_demanda_areas
from tetouan_power_forecast.evaluacion import bootstrap_diferencia_mae, errores
from tetouan_power_forecast.medallon import raiz_datos
from tetouan_power_forecast.modelos import ModeloRazon
from tetouan_power_forecast.variables_sein import (
    AREAS,
    HORIZONTES,
    REFERENCIAS,
    columnas_variante,
    dataset_area,
    filas_comunes,
    particion,
)

VARIANTES = ["M0", "M1", "M2", "M3"]  # M4 espera la tabla empresa → área para el SAIDI


def modelo(max_iter=300):
    return ModeloRazon(HistGradientBoostingRegressor(max_iter=max_iter, learning_rate=0.05, early_stopping=False,
                                                     random_state=0))


def cargar_exogenas(raiz=None):
    carpeta = raiz_datos(raiz) / "exogenas" / "silver"
    leer = {nombre: pd.read_parquet(carpeta / f"{nombre}.parquet")
            for nombre in ["temperatura_areas", "icen", "nino12_semanal", "eventos_coes"]}
    return {"temperatura": leer["temperatura_areas"], "icen": leer["icen"], "nino12": leer["nino12_semanal"],
            "eventos": leer["eventos_coes"]}


def feriados_pe():
    try:
        import holidays
    except ImportError:
        print("sin el paquete holidays: los feriados quedan en cero")
        return []
    return list(holidays.PE(years=range(2016, 2027)))


def correr(demanda, exogenas, horizontes=HORIZONTES, variantes=VARIANTES, max_iter=300, feriados=(), progreso=print):
    filas = []
    for nombre_h, h in horizontes.items():
        for area in AREAS:
            inicio = time.time()
            datos = dataset_area(demanda, area, horizonte=h, feriados=feriados, **exogenas)
            datos["particion"] = particion(datos["DateTime"], h)
            comunes = filas_comunes(datos, variantes)
            tr = comunes[comunes["particion"] == "entrenamiento"]
            va = comunes[comunes["particion"] == "validacion"]
            maes = {ref: errores(va["real"], va[ref])["MAE (kW)"] for ref in REFERENCIAS}
            mejor = min(maes, key=maes.get)
            base = {"horizonte": nombre_h, "area": area, "filas_entrenamiento": len(tr), "filas_validacion": len(va)}
            for ref in REFERENCIAS:
                e = errores(va["real"], va[ref])
                filas.append({**base, "metodo": f"ref_{ref}", "mae_mw": e["MAE (kW)"], "mape_pct": e["MAPE (%)"],
                              "mejora_vs_mejor_ref_pct": 100 * (1 - e["MAE (kW)"] / maes[mejor])})
            predicciones = {}
            for variante in variantes:
                columnas = columnas_variante(comunes, variante)
                pred = modelo(max_iter).fit(tr[columnas], tr["real"]).predict(va[columnas])
                predicciones[variante] = pred
                e = errores(va["real"], pred)
                filas.append({**base, "metodo": variante, "mae_mw": e["MAE (kW)"], "mape_pct": e["MAPE (%)"],
                              "mejora_vs_mejor_ref_pct": 100 * (1 - e["MAE (kW)"] / maes[mejor]),
                              "variables": len(columnas) - 1})
            if "M0" in predicciones and "M3" in predicciones:
                dif, bajo, alto = bootstrap_diferencia_mae(va["real"], predicciones["M3"], predicciones["M0"],
                                                           va["DateTime"])
                filas.append({**base, "metodo": "M3 - M0 (MAE, IC 95 %)", "mae_mw": dif, "ic_bajo": bajo,
                              "ic_alto": alto})
            progreso(f"{nombre_h} {area}: {time.time() - inicio:.0f} s · mejor referencia {mejor}")
    return pd.DataFrame(filas)


def main():
    inicio = time.time()
    resultados = correr(cargar_demanda_areas(), cargar_exogenas(), feriados=feriados_pe())
    guardar(resultados, "linea_base.csv", carpeta="sein")
    tabla = resultados[~resultados["metodo"].str.startswith("M3 -")].pivot_table(
        index=["horizonte", "area"], columns="metodo", values="mae_mw")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print("\nMAE (MW) en la validación de 2025:")
        print(tabla.round(1))
        print("\nM3 − M0 (MW) con su intervalo:")
        print(resultados[resultados["metodo"].str.startswith("M3 -")][
            ["horizonte", "area", "mae_mw", "ic_bajo", "ic_alto"]].round(2).to_string(index=False))
    print("minutos:", round((time.time() - inicio) / 60, 1))


if __name__ == "__main__":
    main()
