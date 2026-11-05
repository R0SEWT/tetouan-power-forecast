"""Modelado y evaluación del caso peruano: lo que comparten el notebook 02 del SEIN, los experimentos y la app.

Los candidatos de la spec (§7) y el modelo global, los datasets por área y el global sobre las mismas filas, las
políticas de reentrenamiento del experimento de adaptación (§8.4) y los regímenes en los que se desagrega el error
(§8.5). Las métricas se calculan siempre en MW, sobre `real`.
"""

import shutil

import numpy as np
import pandas as pd
from scipy.stats import loguniform
from sklearn.base import clone
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from tetouan_power_forecast.modelos import ModeloRazon
from tetouan_power_forecast.variables_sein import (
    AREAS,
    GRUPOS,
    PASO,
    REFERENCIAS,
    columnas_variante,
    dataset_area,
    filas_comunes,
    particion,
)

CODIGO_AREA = {area: i for i, area in enumerate(AREAS)}  # la categórica del modelo global
# Categorías del ICEN según ENFEN (Nota Técnica 01-2024): las cálidas, que son las que importan aquí, van completas;
# el lado frío queda en una sola.
CATEGORIAS_ICEN = [
    (-np.inf, -1.0, "fría"),
    (-1.0, 0.4, "neutra"),
    (0.4, 1.0, "cálida débil"),
    (1.0, 1.7, "cálida moderada"),
    (1.7, 3.0, "cálida fuerte"),
    (3.0, np.inf, "cálida extraordinaria"),
]
VARIANTES_ABLACION = ["M0", "M1", "M2", "M3"]  # M4 espera el SAIDI por área
DISPOSITIVO = "cuda" if shutil.which("nvidia-smi") else "cpu"  # los árboles van a la GPU cuando la hay


def random_forest(semilla=0, dispositivo=DISPOSITIVO, **parametros):
    """Random Forest: el de cuML en la GPU, el de scikit-learn en la CPU. Los dos usan los mismos hiperparámetros.

    En el Centro a 1 h dan el mismo MAE en 2025 (54.71 frente a 54.70 MW) y el de cuML ajusta unas cinco veces más
    rápido. Con un solo stream (`n_streams=1`), el bosque de cuML es reproducible con la misma semilla.
    """
    if dispositivo == "cuda":
        from cuml.ensemble import RandomForestRegressor as RandomForestGPU

        return RandomForestGPU(random_state=semilla, n_streams=1, **parametros)
    return RandomForestRegressor(n_jobs=-1, random_state=semilla, **parametros)


def gradient_boosting(semilla=0, dispositivo=DISPOSITIVO, **parametros):
    """Gradient Boosting con XGBoost (histogramas), en la GPU cuando la hay; es determinista en las dos."""
    return XGBRegressor(tree_method="hist", device=dispositivo, random_state=semilla, **parametros)


def candidatos(semilla=0, dispositivo=DISPOSITIVO):
    """Los tres algoritmos de la spec (§7), envueltos en `ModeloRazon`, con su espacio de hiperparámetros.

    Random Forest (cuML en la GPU) y Gradient Boosting (XGBoost) corren en la GPU cuando la hay; Ridge, que ajusta
    en segundos, en la CPU. Random Forest lleva `max_samples` ≤ 0.3: con 150,000 periodos por área, cada árbol ve
    una muestra chica.
    """
    return {
        "Ridge": (
            ModeloRazon(make_pipeline(StandardScaler(), Ridge())),
            {"estimador__ridge__alpha": np.logspace(-3, 3, 13)},
        ),
        "Random Forest": (
            ModeloRazon(random_forest(semilla, dispositivo)),
            {
                "estimador__n_estimators": [100, 200, 300],
                "estimador__max_depth": [12, 16, 20],
                "estimador__min_samples_leaf": [5, 20, 50],
                "estimador__max_features": [0.3, 0.5, 1.0],
                "estimador__max_samples": [0.1, 0.2, 0.3],
            },
        ),
        "Gradient Boosting": (
            ModeloRazon(gradient_boosting(semilla, dispositivo)),
            {
                "estimador__learning_rate": loguniform(0.02, 0.2),
                "estimador__n_estimators": [200, 300, 500, 800],
                "estimador__max_depth": [4, 6, 8, 10],
                "estimador__min_child_weight": [20, 50, 100],
                "estimador__reg_lambda": [0.0, 0.1, 1.0, 10.0],
                "estimador__subsample": [0.7, 0.85, 1.0],
                "estimador__colsample_bytree": [0.7, 0.85, 1.0],
            },
        ),
    }


def gradient_boosting_global(semilla=0, dispositivo=DISPOSITIVO, **parametros):
    """El Gradient Boosting de las tres áreas apiladas. `area_cod` (0, 1, 2) entra como número: con dos cortes, un
    árbol separa cualquier área."""
    return ModeloRazon(gradient_boosting(semilla, dispositivo, **parametros))


def portable(modelo):
    """El modelo listo para guardarse y cargarse en una máquina sin GPU (la app): XGBoost pasa a la CPU y el
    Random Forest de cuML, si se puede, al de scikit-learn. Devuelve una copia ajustada; no cambia el original."""
    import copy

    salida = copy.deepcopy(modelo)
    estimador = salida.estimador_
    if isinstance(estimador, XGBRegressor):
        estimador.set_params(device="cpu")
    elif type(estimador).__module__.startswith("cuml") and hasattr(estimador, "as_sklearn"):
        salida.estimador_ = estimador.as_sklearn()
    return salida


def preparar_datasets(demanda, horizonte, variantes=tuple(VARIANTES_ABLACION), feriados=(), **exogenas):
    """Los datasets por área y el global de un horizonte, sobre las mismas filas y con la partición.

    Por área, `dataset_area` con las otras áreas como variables (spec §6). El global apila las tres áreas con solo
    sus propias variables y `area_cod` como categórica, en las mismas filas y en el mismo orden que cada dataset
    local, así las predicciones de los dos se comparan periodo a periodo. Quedan las filas completas para todas
    las `variantes` (`filas_comunes`).
    """
    locales, piezas = {}, []
    for area in AREAS:
        datos = dataset_area(demanda, area, horizonte=horizonte, feriados=feriados, **exogenas)
        datos["particion"] = particion(datos["DateTime"], horizonte)
        locales[area] = filas_comunes(datos, variantes).reset_index(drop=True)
        propio = dataset_area(demanda, area, horizonte=horizonte, feriados=feriados, otras_areas=False, **exogenas)
        propio = propio.set_index("DateTime").loc[locales[area]["DateTime"]].reset_index()
        propio.insert(2, "area_cod", CODIGO_AREA[area])
        propio["particion"] = locales[area]["particion"].to_numpy()
        piezas.append(propio)
    return locales, pd.concat(piezas, ignore_index=True)


def tramo(datos, nombre, fin_entrenamiento="2025-01-01"):
    """Las filas de una partición. "desarrollo" es entrenamiento + validación, para el modelo final."""
    if nombre == "desarrollo":
        hueco_antes_de_validacion = (datos["particion"] == "hueco") & (datos["DateTime"] < pd.Timestamp(fin_entrenamiento))
        return datos[datos["particion"].isin(["entrenamiento", "validacion"]) | hueco_antes_de_validacion]
    return datos[datos["particion"] == nombre]


def en(nombre):
    return lambda datos: tramo(datos, nombre)


def mejor_referencia(datos):
    """La referencia ingenua con menor MAE en esas filas."""
    return min(REFERENCIAS, key=lambda ref: float(np.mean(np.abs(datos["real"] - datos[ref]))))


def columnas_sin_grupo(datos, grupo, base="M3"):
    """Las columnas de una variante sin uno de sus grupos de exógenas: la ablación que quita un grupo (§8.3)."""
    return [c for c in columnas_variante(datos, base) if c not in GRUPOS[grupo]]


def _columnas(datos, columnas):
    """`columnas` puede ser una variante ("M0"…), una función del dataset o la lista de columnas."""
    if isinstance(columnas, str):
        return columnas_variante(datos, columnas)
    return columnas(datos) if callable(columnas) else list(columnas)


def predecir_local(modelo, locales, columnas, entrenar, evaluar):
    """Un modelo por área (clonado), ajustado con las filas de `entrenar` y evaluado en las de `evaluar`.

    `columnas` es una variante ("M0"…), una función del dataset (por ejemplo, `columnas_sin_grupo`) o la lista
    de columnas. Devuelve {área: predicciones en MW}.
    """
    salida = {}
    for area, datos in locales.items():
        tr, te = entrenar(datos), evaluar(datos)
        cols = _columnas(datos, columnas)
        salida[area] = clone(modelo).fit(tr[cols], tr["real"]).predict(te[cols])
    return salida


def predecir_global(modelo, global_, columnas, entrenar, evaluar):
    """Un solo modelo de las tres áreas; devuelve {área: predicciones} en el orden del dataset local de cada área."""
    tr, te = entrenar(global_), evaluar(global_)
    cols = _columnas(global_, columnas)
    pred = clone(modelo).fit(tr[cols], tr["real"]).predict(te[cols])
    return {area: pred[(te["area"] == area).to_numpy()] for area in AREAS}


def bloques(fechas, politica="fijo", frecuencia="W-MON", alerta=None):
    """Los tramos [desde, hasta) en que se parte una evaluación según la política de reentrenamiento (spec §8.4).

    "fijo": un solo bloque. "periodica": uno nuevo en cada marca de `frecuencia` (cada lunes a las 00:00).
    "alerta": uno nuevo cada vez que cambia `alerta`, una serie alineada con `fechas` (por ejemplo, la categoría
    del ICEN conocida en t). "periodica+alerta": las dos marcas juntas. Antes de cada bloque, el modelo se
    reentrena con todo lo anterior menos el hueco de H pasos (`predecir_por_bloques`).
    """
    fechas = pd.Series(pd.to_datetime(np.asarray(fechas)))
    if not fechas.is_monotonic_increasing:
        raise ValueError("las fechas de la evaluación tienen que venir ordenadas")
    inicio, fin = fechas.iloc[0], fechas.iloc[-1] + PASO
    cortes = {inicio}
    politicas = set(politica.split("+"))
    if not politicas <= {"fijo", "periodica", "alerta"}:
        raise ValueError(f"política desconocida: {politica}")
    if "periodica" in politicas:
        cortes |= {c for c in pd.date_range(inicio.normalize(), fin, freq=frecuencia) if inicio < c < fin}
    if "alerta" in politicas:
        if alerta is None:
            raise ValueError("la política de alerta necesita la serie de alerta")
        serie = pd.Series(np.asarray(alerta, dtype=object))
        cambia = (serie != serie.shift()).to_numpy().copy()
        cambia[0] = False
        cortes |= set(fechas[cambia])
    cortes = sorted(cortes)
    return list(zip(cortes, [*cortes[1:], fin], strict=True))


def predecir_por_bloques(predecir, bloques, hueco, seleccionar=lambda datos: datos):
    """Concatena las predicciones de los bloques; antes de cada uno se reentrena con todo lo anterior al hueco.

    `predecir(entrenar, evaluar)` devuelve {área: predicciones} (por ejemplo, `predecir_local` con sus otros
    argumentos fijados). `seleccionar` restringe las filas evaluadas, por ejemplo a la validación.
    """
    partes = {area: [] for area in AREAS}
    for desde, hasta in bloques:
        def entrenar(datos, desde=desde):
            return datos[datos["DateTime"] < desde - hueco]

        def evaluar(datos, desde=desde, hasta=hasta):
            filas = seleccionar(datos)
            return filas[filas["DateTime"].between(desde, hasta, inclusive="left")]

        for area, pred in predecir(entrenar, evaluar).items():
            partes[area].append(np.asarray(pred))
    return {area: np.concatenate(p) for area, p in partes.items()}


def categoria_icen(valores):
    """La categoría de ENFEN de cada valor del ICEN; los valores vacíos quedan en None."""
    v = np.asarray(valores, dtype=float)
    etiquetas = np.full(v.shape, None, dtype=object)
    for bajo, alto, nombre in CATEGORIAS_ICEN:
        etiquetas[(v >= bajo) & (v < alto)] = nombre
    return etiquetas


def horas_mayor_demanda(datos, adelanto, n=4):
    """Las `n` horas del día con más demanda media, por año, del periodo que se predice (spec §8.5).

    Se definen por área y por año porque el pico se movió del atardecer al mediodía.
    """
    objetivo = datos["DateTime"] + adelanto
    media = datos.groupby([objetivo.dt.year.to_numpy(), objetivo.dt.hour.to_numpy()])["real"].mean()
    return {anio: set(grupo.sort_values(ascending=False).index.get_level_values(1)[:n])
            for anio, grupo in media.groupby(level=0)}


def es_hora_pico(fechas, horas_por_anio, adelanto):
    """Máscara de los periodos cuyo objetivo cae en las horas de mayor demanda de su año."""
    objetivo = pd.Series(pd.to_datetime(np.asarray(fechas))) + adelanto
    pares = zip(objetivo.dt.year.to_numpy(), objetivo.dt.hour.to_numpy(), strict=True)
    return np.array([hora in horas_por_anio.get(anio, set()) for anio, hora in pares])


def subestimacion_sobre_p90(real, pred, referencia, mascara=None):
    """Fracción de los periodos en que el modelo subestima más que el p90 del error absoluto de la referencia.

    Es el criterio 2 de la spec (§8.5) para las horas de mayor demanda: un umbral fijo de 5 % daría cero a 1 h.
    """
    real, pred, referencia = (np.asarray(x, dtype=float) for x in (real, pred, referencia))
    mascara = np.ones(len(real), dtype=bool) if mascara is None else np.asarray(mascara, dtype=bool)
    umbral = np.percentile(np.abs(real[mascara] - referencia[mascara]), 90)
    return float(np.mean((real[mascara] - pred[mascara]) > umbral))
