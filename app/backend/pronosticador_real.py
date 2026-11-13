"""El pronosticador real de la app: el XGBoost global del notebook 02 sobre las capas del SEIN.

La app sirve el XGBoost global y no el Random Forest elegido en el notebook 02: en 2025 y en la prueba de 2026
quedaron empatados (notebooks 02 y 03), y el XGBoost pesa decenas de MB en vez de 1 GB y predice en milisegundos.
Se entrena una vez con entrenamiento + validación (2016-2025), con los hiperparámetros del notebook 02:

    TETOUAN_DATA=<carpeta de datos> uv run python -m app.backend.pronosticador_real entrenar

y la API lo usa con ``TPF_PRONOSTICADOR=real`` (ver ``main.py``).

**Convención de tiempo.** El silver del IEOD marca cada periodo con su final (00:30 es de 00:00 a 00:30); el
contrato, con su inicio. Un origen O del contrato es el inicio del último periodo observado, así que lo último que
se conoce termina en O + 30 min. El periodo que empieza en S se pronostica con la fila del dataset de
S + 30 min − H: el pronóstico a H emitido H pasos antes, que solo usa información hasta el origen. A 24 h, el último
periodo se pronostica desde el origen mismo y los anteriores, con lo que se sabía un poco antes. La excepción es la
declarada en la spec (§2 y §6): a 24 h, ``temp_objetivo`` es el pronóstico de temperatura que el COES recibiría de
ENFEN, simulado con la temperatura observada de ERA5 más un error por día de emisión.

**De dónde sale cada parte.** El pronóstico, las series, los escenarios, la sensibilidad, las métricas de 2026, el
error por régimen, la ablación, la importancia y los residuos se calculan aquí con el modelo, siempre sobre la
prueba de 2026, que el modelo no vio (con 2025 adentro serían errores dentro de muestra). La adaptación (fijo
frente a reentrenado cada semana) no se puede reentrenar en vivo: sale de la tabla del notebook 03, con el Random
Forest. Los intervalos del 90 % usan los errores fuera de muestra de 2025 del notebook 02 cuando están; si no, los
de este modelo en 2025 (dentro de muestra, más angostos de lo debido).
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from tetouan_power_forecast.coes import cargar_demanda_areas
from tetouan_power_forecast.exogenas import icen_disponible
from tetouan_power_forecast.medallon import raiz_datos
from tetouan_power_forecast.modelado_sein import CODIGO_AREA, gradient_boosting_global, portable
from tetouan_power_forecast.variables_sein import (
    AREAS,
    GRUPOS,
    PASO,
    REFERENCIAS,
    columnas_variante,
    dataset_area,
)

from .contrato import (
    FECHA_MIN,
    FORMATO_FECHA_HORA,
    PASOS,
    Ablacion,
    AciertoPico,
    Adaptacion,
    Diagnostico,
    Escenario,
    Horizonte,
    Importancia,
    Intervalo,
    MaeRegimen,
    MesSeguimiento,
    MetricaPrueba,
    Pronostico,
    RegimenNino,
    Residuos,
    Resumen,
    Seguimiento,
    Sensibilidad,
    Serie,
    VariableSensibilidad,
    Variante,
)
from .pico import acierto_pico, umbral_rampa
from .pronosticador import (
    FRASE_M0_SIN_ESCENARIOS,
    NOMBRE_REFERENCIA,
    estado_nino,
    frase_base,
    frase_escenario,
)

# Lo que se entrena y con qué. Los hiperparámetros son los del XGBoost global del notebook 02.
VARIANTES_APP: dict[str, list[str]] = {"1h": ["M0", "M3"], "24h": ["M0", "M1", "M2", "M3"]}
HIPERPARAMETROS = {"colsample_bytree": 0.7, "learning_rate": 0.0358, "max_depth": 10, "min_child_weight": 20,
                   "n_estimators": 800, "reg_lambda": 1.0, "subsample": 0.85}
FIN_ENTRENAMIENTO = pd.Timestamp("2025-01-01")
FIN_DESARROLLO = pd.Timestamp("2026-01-01")  # el modelo de la app se entrena hasta aquí
MEDIO = pd.Timedelta(minutes=30)
DIA = 48
# media_24h no va en ningún grupo: es la escala con que ModeloRazon vuelve a MW, no una variable. Desordenarla rompe
# esa reconstrucción y aparecería como "la más importante" sin serlo.
GRUPOS_IMPORTANCIA = {
    "demanda_reciente": ["Area_t", "Area_t_menos_1", "Area_t_menos_2", "Area_t_menos_4", "Area_ayer",
                         "Area_semana_pasada", "Area_media_1h", "Area_desv_1h", "Area_m24_vs_m7d"],
    "calendario": ["Hour", "MinuteOfDay", "DayOfWeek", "Time_Sin", "Time_Cos", "Week_Sin", "Week_Cos", "Obj_Sin",
                   "Obj_Cos", "DiaSemanaObjetivo", "FinDeSemanaObjetivo", "FeriadoObjetivo", "Cuarentena"],
    "clima": GRUPOS["clima"],
    "nino": GRUPOS["nino"],
    "fallas": GRUPOS["fallas"],
}
POLITICA_CONTRATO = {"fijo": "fijo", "semanal": "semanal", "alerta ENFEN": "alerta_enfen"}


def carpeta_modelos(raiz=None) -> Path:
    return raiz_datos(raiz) / "modelos" / "sein" / "app"


def _feriados():
    try:
        import holidays
    except ImportError:
        print("Aviso: falta el paquete holidays (extra app); los feriados quedan en cero y el modelo no los ve.",
              file=sys.stderr)
        return []
    return list(holidays.PE(years=range(2016, 2028)))


def cargar_capas(raiz=None):
    """La demanda por área y las exógenas del silver, como las leen los notebooks."""
    carpeta = raiz_datos(raiz) / "exogenas" / "silver"
    demanda = cargar_demanda_areas(raiz).sort_values("DateTime").reset_index(drop=True)
    exogenas = {
        "temperatura": pd.read_parquet(carpeta / "temperatura_areas.parquet"),
        "icen": pd.read_parquet(carpeta / "icen.parquet"),
        "nino12": pd.read_parquet(carpeta / "nino12_semanal.parquet"),
        "eventos": pd.read_parquet(carpeta / "eventos_coes.parquet"),
    }
    return demanda, exogenas


def armar_datasets(demanda, exogenas, feriados=()):
    """Por horizonte y área, el dataset de cada momento t, con o sin objetivo conocido.

    A diferencia de los notebooks, no se descartan las filas sin objetivo: son las de los orígenes más recientes,
    que la app sí tiene que poder pronosticar. Cada fila lleva el código del área, como el dataset global.
    """
    datos = {}
    for nombre_h, pasos in PASOS.items():
        datos[nombre_h] = {}
        for area in AREAS:
            d = dataset_area(demanda, area, horizonte=pasos, feriados=feriados, otras_areas=False, **exogenas)
            d.insert(2, "area_cod", CODIGO_AREA[area])
            datos[nombre_h][area.lower()] = d.set_index("DateTime", drop=False)
    return datos


def _apilar(datos_h, columnas, desde=None, hasta=None, con_objetivo=True):
    piezas = []
    for d in datos_h.values():
        filas = d
        if desde is not None:
            filas = filas[filas.index >= desde]
        if hasta is not None:
            filas = filas[filas.index < hasta]
        filas = filas.dropna(subset=columnas + (["real"] if con_objetivo else []))
        piezas.append(filas)
    return pd.concat(piezas, ignore_index=True)


def _cuantiles_notebook_02(raiz, area, nombre_h, variante):
    """Cuantiles 5 y 95 % del error relativo fuera de muestra de 2025 (modelo fijo del notebook 02)."""
    ruta = raiz_datos(raiz) / "reportes" / "sein" / "modelado" / f"predicciones_validacion_{nombre_h}_{area}.csv"
    columna = f"fijo_{variante}"
    if not ruta.exists():
        return None
    tabla = pd.read_csv(ruta)
    if columna not in tabla:
        return None
    relativo = (tabla["real"] / tabla[columna] - 1).dropna()
    return [float(relativo.quantile(0.05)), float(relativo.quantile(0.95))]


def entrenar(raiz=None, hiperparametros=None, progreso=print):
    """Entrena los modelos de la app con 2016-2025 y los guarda con sus metadatos en ``modelos/sein/app/``."""
    hiperparametros = hiperparametros or HIPERPARAMETROS
    demanda, exogenas = cargar_capas(raiz)
    datos = armar_datasets(demanda, exogenas, _feriados())
    destino = carpeta_modelos(raiz)
    destino.parent.mkdir(parents=True, exist_ok=True)
    carpeta = Path(tempfile.mkdtemp(prefix="app-", dir=destino.parent))  # se publica entera al final
    meta = {"modelo": "XGBoost global (hiperparámetros del notebook 02)", "hiperparametros": hiperparametros,
            "entrenado_hasta": str(FIN_DESARROLLO - MEDIO), "columnas": {}, "mejor_referencia": {}, "intervalos": {}}
    for nombre_h, variantes in VARIANTES_APP.items():
        muestra = next(iter(datos[nombre_h].values()))
        for v in variantes:
            columnas = columnas_variante(muestra, v)
            filas = _apilar(datos[nombre_h], columnas, hasta=FIN_DESARROLLO - PASOS[nombre_h] * PASO)
            modelo = gradient_boosting_global(**hiperparametros).fit(filas[columnas], filas["real"])
            joblib.dump(portable(modelo), carpeta / f"xgboost_global_{nombre_h}_{v}.joblib")
            meta["columnas"][f"{nombre_h}_{v}"] = columnas
            progreso(f"{nombre_h} {v}: {len(filas):,} filas")
            if v not in ("M0", "M3"):
                continue
            for area, d in datos[nombre_h].items():
                cuantiles = _cuantiles_notebook_02(raiz, area, nombre_h, v)
                if cuantiles is None:  # respaldo: el error de este modelo en 2025, dentro de muestra
                    val = _validacion(d, nombre_h).dropna(subset=columnas + ["real"])
                    relativo = val["real"] / portable(modelo).predict(val[columnas]) - 1
                    cuantiles = [float(relativo.quantile(0.05)), float(relativo.quantile(0.95))]
                meta["intervalos"][f"{area}_{nombre_h}_{v}"] = cuantiles
    for nombre_h, por_area in datos.items():
        for area, d in por_area.items():
            val = _validacion(d, nombre_h).dropna(subset=["real", *REFERENCIAS])
            candidatas = REFERENCIAS if nombre_h == "1h" else ["ayer", "semana_pasada"]  # a 24 h, ayer = persistencia
            mae = {r: float((val["real"] - val[r]).abs().mean()) for r in candidatas}
            meta["mejor_referencia"][f"{area}_{nombre_h}"] = min(mae, key=mae.get)
    (carpeta / "metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    _publicar(carpeta, destino)
    progreso(f"modelos y metadatos en {destino}")
    return destino


def _validacion(d, nombre_h):
    """Las filas de 2025 cuyo objetivo también cae en 2025: sin el hueco, a 24 h alcanzarían enero de 2026."""
    return d[(d.index >= FIN_ENTRENAMIENTO) & (d.index < FIN_DESARROLLO - PASOS[nombre_h] * PASO)]


def _publicar(nueva, destino):
    """Reemplaza la carpeta de modelos de una vez: la API nunca ve una mezcla de dos entrenamientos."""
    vieja = destino.with_name(destino.name + ".anterior")
    shutil.rmtree(vieja, ignore_errors=True)
    if destino.exists():
        destino.rename(vieja)
    nueva.rename(destino)
    shutil.rmtree(vieja, ignore_errors=True)


def _bootstrap_mae(error, dias, rng, n=300):
    """Intervalo al 95 % del MAE remuestreando días enteros, solo los que tienen datos.

    Cada remuestra pondera los días por su cantidad de periodos, igual que el MAE que se reporta.
    """
    error, dias = np.asarray(error, dtype=float), np.asarray(dias)
    ok = ~np.isnan(error)
    unicos, posicion = np.unique(dias[ok], return_inverse=True)
    suma = np.bincount(posicion, weights=error[ok])
    cuenta = np.bincount(posicion).astype(float)
    remuestras = rng.integers(0, len(unicos), size=(n, len(unicos)))
    medias = suma[remuestras].sum(axis=1) / cuenta[remuestras].sum(axis=1)
    return float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


def _texto(momento) -> str:
    return pd.Timestamp(momento).strftime(FORMATO_FECHA_HORA)


def _redondear(x) -> list[float]:
    return [round(float(v), 1) for v in np.asarray(x, dtype=float)]


def _sin_nan(x) -> np.ndarray:
    """Rellena por interpolación lo que quede vacío: el contrato no admite nulos en el pronóstico."""
    serie = pd.Series(np.asarray(x, dtype=float))
    if serie.isna().all():
        return np.zeros(len(serie))
    return serie.interpolate(limit_direction="both").to_numpy()


def _con_nulos(x) -> list[float | None]:
    return [None if np.isnan(v) else round(float(v), 1) for v in np.asarray(x, dtype=float)]


class PronosticadorReal:
    """Cumple el ``Protocol`` ``Pronosticador`` con el XGBoost global y las capas reales del SEIN."""

    descripcion = "El modelo del proyecto: XGBoost sobre la demanda, con o sin clima, El Niño y fallas."
    variantes: tuple[str, ...] = ("M0", "M3")
    respaldo = None  # el modelo que responde fuera del rango de fechas de este; el base no lo necesita

    def __init__(self, raiz=None):
        carpeta = carpeta_modelos(raiz)
        ruta_meta = carpeta / "metadatos.json"
        if not ruta_meta.exists():
            raise FileNotFoundError(
                f"No hay modelos de la app en {carpeta}. Entrénalos con: "
                "uv run python -m app.backend.pronosticador_real entrenar")
        self._meta = json.loads(ruta_meta.read_text())
        self._modelos = {clave: joblib.load(carpeta / f"xgboost_global_{clave}.joblib") for clave in self._meta["columnas"]}
        self._raiz = raiz
        self._demanda, self._exogenas = cargar_capas(raiz)
        self._datos = armar_datasets(self._demanda, self._exogenas, _feriados())
        self._real = {a.lower(): self._demanda.set_index("DateTime")[a].astype(float) for a in AREAS}
        self._predicciones: dict[tuple[str, str, str], pd.Series] = {}
        self._diagnosticos: dict[str, Diagnostico] = {}
        self._resumen: Resumen | None = None
        self.modelo = "XGBoost global"
        self.nombre = "Base (XGBoost)"
        self.version_datos = f"IEOD hasta {self._demanda['DateTime'].max():%Y-%m-%d}"
        self.fecha_min = FECHA_MIN
        self.fecha_max = self._ultima_fecha()

    # ---- núcleo --------------------------------------------------------------------------------

    def _columnas(self, nombre_h: str, variante: str) -> list[str]:
        return self._meta["columnas"][f"{nombre_h}_{variante}"]

    def _ultima_fecha(self) -> date:
        """El último día completo que se puede pronosticar a 1 h y a 24 h con todas las variables de M3."""
        ultimas = []
        for nombre_h in PASOS:
            columnas = self._columnas(nombre_h, "M3")
            for d in self._datos[nombre_h].values():
                ultimas.append(d.dropna(subset=columnas).index.max())
        return (min(ultimas) - pd.Timedelta(days=1)).date()

    def _predecir_filas(self, nombre_h: str, variante: str, filas: pd.DataFrame) -> np.ndarray:
        columnas = self._columnas(nombre_h, variante)
        salida = np.full(len(filas), np.nan)
        completas = filas[columnas].notna().all(axis=1).to_numpy()
        if completas.any():
            salida[completas] = self._modelos[f"{nombre_h}_{variante}"].predict(filas.loc[completas, columnas])
        return salida

    def _predicciones_area(self, area: str, nombre_h: str, variante: str) -> pd.Series:
        """Las predicciones de todas las filas desde 2025, una vez por área, horizonte y variante."""
        clave = (area, nombre_h, variante)
        if clave not in self._predicciones:
            d = self._datos[nombre_h][area]
            filas = d[d.index >= pd.Timestamp(FECHA_MIN) - pd.Timedelta(days=2)]
            self._predicciones[clave] = pd.Series(self._predecir_filas(nombre_h, variante, filas), index=filas.index)
        return self._predicciones[clave]

    def _mejor_referencia(self, area: str, nombre_h: str) -> str:
        return self._meta["mejor_referencia"][f"{area}_{nombre_h}"]

    @staticmethod
    def _emision(inicios: pd.DatetimeIndex, nombre_h: str) -> pd.DatetimeIndex:
        """La fila del dataset con que se pronostica cada periodo: final del periodo menos H pasos."""
        return inicios + MEDIO - PASOS[nombre_h] * PASO

    def _completar(self, pred: np.ndarray, referencia: np.ndarray) -> np.ndarray:
        """Si al modelo le falta una variable en algún periodo (huecos del clima), usa la mejor referencia."""
        return _sin_nan(np.where(np.isnan(pred), referencia, pred))

    def _real_en(self, area: str, inicios: pd.DatetimeIndex) -> np.ndarray:
        return self._real[area].reindex(inicios + MEDIO).to_numpy()

    def _variante(self, variante: str) -> str:
        """La variante que de verdad usa este modelo (el híbrido y el combinado solo distinguen M0)."""
        return variante if variante in self.variantes else "M0"

    def _periodos(self, area: str, horizonte: Horizonte, variante: str, inicios: pd.DatetimeIndex):
        """Pronóstico, real y mejor referencia de cada periodo, como los muestra la serie del día.

        Como en ``serie``, si al modelo le falta una variable en un periodo se usa la mejor referencia.
        """
        emision = self._emision(inicios, horizonte)
        filas = self._datos[horizonte][area].reindex(emision)
        referencia = filas[self._mejor_referencia(area, horizonte)].to_numpy(dtype=float)
        pred = self._predicciones_area(area, horizonte, self._variante(variante)).reindex(emision).to_numpy()
        return np.where(np.isnan(pred), referencia, pred), self._real_en(area, inicios), referencia

    def _cache(self, nombre: str) -> dict:
        # El híbrido y el combinado no llaman a este __init__: la caché se crea al primer uso
        return self.__dict__.setdefault(nombre, {})

    # ---- contrato ------------------------------------------------------------------------------

    def serie(self, area: str, fecha: date, horizonte: Horizonte, variante: Variante) -> Serie:
        inicios = pd.date_range(pd.Timestamp(fecha), periods=DIA, freq="30min")
        emision = self._emision(inicios, horizonte)
        filas = self._datos[horizonte][area].reindex(emision)
        nombre_ref = self._mejor_referencia(area, horizonte)
        referencia = _sin_nan(filas[nombre_ref].to_numpy(dtype=float))
        pred = self._completar(self._predicciones_area(area, horizonte, variante).reindex(emision).to_numpy(),
                               referencia)
        real = self._real_en(area, inicios)
        return Serie(
            fecha_hora=[_texto(x) for x in inicios],
            real=_con_nulos(real),
            pronostico=_redondear(pred),
            referencia=_redondear(referencia),
            referencia_nombre=nombre_ref,
            programacion_diaria=None,  # la Programación Diaria del COES no está en las capas
            hueco=[bool(x) for x in np.isnan(real)],
            preliminar=[False] * DIA,  # el IEOD no marca datos preliminares
            intervalo=self._intervalo(area, horizonte, variante, pred),
        )

    def _intervalo(self, area: str, horizonte: Horizonte, variante: Variante, pred: np.ndarray) -> Intervalo:
        """Rango del 90 %: los cuantiles 5 y 95 % del error relativo de la validación de 2025."""
        bajo, alto = self._meta["intervalos"].get(f"{area}_{horizonte}_{variante}", [-0.03, 0.03])
        return Intervalo(inferior=_redondear(pred * (1 + min(bajo, 0.0))),
                         superior=_redondear(pred * (1 + max(alto, 0.0))))

    def _filas_desde_origen(self, area: str, origen: datetime, horizonte: Horizonte):
        pasos = PASOS[horizonte]
        inicios = pd.date_range(pd.Timestamp(origen) + MEDIO, periods=pasos, freq="30min")
        filas = self._datos[horizonte][area].reindex(self._emision(inicios, horizonte))
        return inicios, filas

    @staticmethod
    def _aplicar_escenario(filas: pd.DataFrame, escenario: Escenario) -> pd.DataFrame:
        filas = filas.copy()
        if escenario.delta_temp_c and "temp_objetivo" in filas:
            filas["temp_objetivo"] = filas["temp_objetivo"] + escenario.delta_temp_c
        if escenario.nino == "neutro":
            for columna in GRUPOS["nino"]:
                if columna in filas:
                    filas[columna] = 0.0
        if escenario.falla == "ninguna" and "fallas_en_curso" in filas:
            filas["fallas_en_curso"] = 0.0
        return filas

    def pronosticar(self, area: str, origen: datetime, horizonte: Horizonte, variante: Variante,
                    escenario: Escenario) -> Pronostico:
        inicios, filas = self._filas_desde_origen(area, origen, horizonte)
        nombre_ref = self._mejor_referencia(area, horizonte)
        referencia = _sin_nan(filas[nombre_ref].to_numpy(dtype=float))
        base = self._completar(self._predecir_filas(horizonte, variante, filas), referencia)
        usa_exogenas = variante != "M0"
        pred = base
        if not escenario.es_base and usa_exogenas:
            pred = self._completar(self._predecir_filas(horizonte, variante, self._aplicar_escenario(filas, escenario)),
                                   referencia)
        momentos = [x.to_pydatetime() for x in inicios]
        if escenario.es_base:
            frase = frase_base(momentos, list(pred), list(referencia), NOMBRE_REFERENCIA[nombre_ref], horizonte)
        elif not usa_exogenas:
            frase = FRASE_M0_SIN_ESCENARIOS
        else:
            frase = frase_escenario(momentos, list(base), list(pred), escenario)
        return Pronostico(
            fecha_hora=[_texto(x) for x in inicios],
            pronostico=_redondear(pred),
            referencia=_redondear(referencia),
            real=_con_nulos(self._real_en(area, inicios)),
            intervalo=self._intervalo(area, horizonte, variante, pred),
            frase=frase,
        )

    def sensibilidad(self, area: str, origen: datetime, variable: VariableSensibilidad) -> Sensibilidad:
        _, filas = self._filas_desde_origen(area, origen, "1h")
        fila = filas.iloc[[-1]]  # la emitida en el origen: pronostica el periodo que empieza 1 h después
        if variable == "temperatura":
            actual = float(fila["temp"].iloc[0])
            valores = round(actual * 2) / 2 + np.arange(-6.0, 6.5, 1.0)
            prueba = pd.concat([fila] * len(valores), ignore_index=True)
            prueba["temp"] = valores
            prueba["temp_objetivo"] = valores
            prueba["temp_anomalia"] = fila["temp_anomalia"].iloc[0] + (valores - actual)
        else:
            valores = np.arange(-1.5, 4.51, 0.5)
            prueba = pd.concat([fila] * len(valores), ignore_index=True)
            prueba["icen"] = valores
        return Sensibilidad(valores=[round(float(v), 2) for v in valores],
                            pronostico=_redondear(_sin_nan(self._predecir_filas("1h", "M3", prueba))))

    # ---- resumen y diagnóstico -----------------------------------------------------------------

    def _prueba(self, area: str, nombre_h: str) -> pd.DataFrame:
        d = self._datos[nombre_h][area]
        fin = pd.Timestamp(self.fecha_max) + pd.Timedelta(days=1)
        return d[(d.index >= FIN_DESARROLLO) & (d.index < fin)].dropna(subset=["real"])

    def resumen(self) -> Resumen:
        if self._resumen is None:
            metricas = {}
            for area in self._datos["24h"]:
                prueba = self._prueba(area, "24h")
                pred = self._predicciones_area(area, "24h", "M3").reindex(prueba.index).to_numpy()
                bien = ~np.isnan(pred)
                error = np.abs(prueba["real"].to_numpy()[bien] - pred[bien])
                metricas[area] = MetricaPrueba(
                    mae_mw=round(float(error.mean()), 1),
                    mape_pct=round(float(np.mean(error / prueba["real"].to_numpy()[bien]) * 100), 2),
                    mejor_referencia=self._mejor_referencia(area, "24h"))
            icen = self._exogenas["icen"]
            ultimo_icen = icen_disponible(pd.Series([pd.Timestamp(self.fecha_max)]), icen).iloc[0]
            if np.isnan(ultimo_icen):  # sin ICEN publicado para esa fecha: el último que haya
                ultimo_icen = float(icen.dropna(subset=["icen"]).sort_values("mes")["icen"].iloc[-1])
            publicado = (pd.Timestamp(self.fecha_max).to_period("M") - (2 if self.fecha_max.day >= 20 else 3))
            corte = {
                "entrenamiento_hasta": str((FIN_ENTRENAMIENTO - pd.Timedelta(days=1)).date()),
                "validacion_hasta": str((FIN_DESARROLLO - pd.Timedelta(days=1)).date()),
                "prueba_hasta": self.fecha_max.isoformat(),
                "demanda": f"{self._demanda['DateTime'].max():%Y-%m-%d}",
                "clima": f"{self._exogenas['temperatura']['fecha_hora'].max():%Y-%m-%d}",
                "icen": f"{icen['mes'].max():%Y-%m}",
                "nino12": f"{self._exogenas['nino12']['semana'].max():%Y-%m-%d}",
                "fallas": f"{self._exogenas['eventos']['inicio'].max():%Y-%m-%d}",
            }
            self._resumen = Resumen(
                fechas_corte=corte,
                regimen_nino=RegimenNino(estado=estado_nino(float(ultimo_icen)), icen=round(float(ultimo_icen), 2),
                                         mes=str(publicado)),
                metricas_prueba=metricas, modelo=self.modelo, version_datos=self.version_datos)
        return self._resumen

    def seguimiento(self, area: str, horizonte: Horizonte, variante: Variante) -> Seguimiento:
        """MAE por mes del periodo pronosticado y cobertura del rango probable, en la prueba de 2026.

        Son las mismas filas que el error de 2026 del resumen y del diagnóstico (orígenes desde 2026, que el modelo
        no vio), restringidas a las que también tienen valor de la referencia.
        """
        clave = (area, horizonte, self._variante(variante))
        cache = self._cache("_seguimientos")
        if clave in cache:
            return cache[clave]
        nombre_ref = self._mejor_referencia(area, horizonte)
        prueba = self._prueba(area, horizonte)
        prueba = prueba[prueba.index >= FIN_DESARROLLO]
        pred = self._predicciones_area(area, horizonte, clave[2]).reindex(prueba.index).to_numpy()
        intervalo = self._intervalo(area, horizonte, clave[2], pred)
        tabla = pd.DataFrame({
            "real": prueba["real"].to_numpy(dtype=float), "pred": pred,
            "ref": prueba[nombre_ref].to_numpy(dtype=float),
            "inferior": np.asarray(intervalo.inferior, dtype=float), "superior": np.asarray(intervalo.superior, dtype=float),
        }, index=prueba.index + PASOS[horizonte] * PASO - MEDIO)  # inicio del periodo pronosticado
        tabla = tabla.dropna()
        if tabla.empty:
            raise LookupError(f"No hay pronósticos de {FIN_DESARROLLO.year} con dato real para {area} a {horizonte}.")
        tabla["e_modelo"] = (tabla["real"] - tabla["pred"]).abs()
        tabla["e_ref"] = (tabla["real"] - tabla["ref"]).abs()
        tabla["dentro"] = (tabla["real"] >= tabla["inferior"]) & (tabla["real"] <= tabla["superior"])

        def fila(mes, t):
            return MesSeguimiento(mes=mes, mae_modelo=round(float(t["e_modelo"].mean()), 1),
                                  mae_referencia=round(float(t["e_ref"].mean()), 1),
                                  cobertura_pct=round(100 * float(t["dentro"].mean()), 1), periodos=len(t))

        meses = [fila(str(m), t) for m, t in tabla.groupby(tabla.index.to_period("M"))]
        cache[clave] = Seguimiento(horizonte=horizonte, referencia_nombre=nombre_ref, meses=meses,
                                   total=fila(str(FIN_DESARROLLO.year), tabla))
        return cache[clave]

    def umbral_rampa(self, area: str) -> float | None:
        """La subida horaria que marca una «rampa fuerte»: percentil 95 de la mayor de cada día, 2016-2024."""
        cache = self._cache("_umbrales")
        if area not in cache:
            cache[area] = umbral_rampa(self._real[area], FIN_ENTRENAMIENTO)
        return cache[area]

    def acierto_pico(self, area: str, variante: Variante = "M3") -> AciertoPico | None:
        """Qué tan bien ubica el máximo de cada día de 2026, a 24 h, con los mismos valores de la serie del día."""
        clave = (area, self._variante(variante))
        cache = self._cache("_aciertos")
        if clave not in cache:
            dias = pd.date_range(FIN_DESARROLLO, pd.Timestamp(self.fecha_max), freq="D")
            inicios = pd.date_range(dias[0], periods=len(dias) * DIA, freq="30min")
            pred, real, referencia = self._periodos(area, "24h", clave[1], inicios)
            cache[clave] = acierto_pico(*(x.reshape(len(dias), DIA) for x in (pred, real, referencia)))
        return cache[clave]

    def diagnostico(self, area: str) -> Diagnostico:
        if area not in self._diagnosticos:
            self._diagnosticos[area] = self._calcular_diagnostico(area)
        return self._diagnosticos[area]

    def _calcular_diagnostico(self, area: str) -> Diagnostico:
        nombre_ref = self._mejor_referencia(area, "24h")
        rng = np.random.default_rng(0)

        # Error por régimen de El Niño (ICEN definitivo del mes que se predice), solo en la prueba de 2026:
        # el modelo se entrenó con 2025, así que ahí sus errores serían dentro de muestra
        prueba = self._prueba(area, "24h")
        filas = prueba.dropna(subset=[nombre_ref])
        pred = self._predicciones_area(area, "24h", "M3").reindex(filas.index).to_numpy()
        bien = ~np.isnan(pred)
        filas, pred = filas[bien], pred[bien]
        objetivo = (filas.index + PASOS["24h"] * PASO).to_period("M")
        icen = self._exogenas["icen"].set_index(self._exogenas["icen"]["mes"].dt.to_period("M"))["icen"]
        estados = np.array([estado_nino(x) if not np.isnan(x) else "sin_icen" for x in objetivo.map(icen).astype(float)])
        por_regimen = []
        for estado in ("neutro", "debil", "moderado", "fuerte", "extraordinario"):
            m = estados == estado
            if m.sum() >= DIA:
                por_regimen.append(MaeRegimen(
                    regimen=estado, modelo=round(float(np.abs(filas["real"].to_numpy()[m] - pred[m]).mean()), 1),
                    referencia=round(float(np.abs(filas["real"] - filas[nombre_ref]).to_numpy()[m].mean()), 1)))

        # Ablación en la prueba de 2026, con intervalo por bootstrap de los días que tienen datos
        dias = prueba.index.normalize().to_numpy()
        ablacion, mae = [], {}
        for v in VARIANTES_APP["24h"]:
            p = self._predicciones_area(area, "24h", v).reindex(prueba.index).to_numpy()
            error = np.abs(prueba["real"].to_numpy() - p)
            mae[v] = float(np.nanmean(error))
            bajo, alto = _bootstrap_mae(error, dias, rng)
            ablacion.append(Ablacion(variante=v, mae=round(mae[v], 1), ic_inf=round(bajo, 1), ic_sup=round(alto, 1)))

        # Importancia por grupo: cuánto sube el MAE al desordenar juntas las variables del grupo (M3)
        columnas = self._columnas("24h", "M3")
        muestra = prueba.dropna(subset=columnas)
        muestra = muestra.iloc[np.linspace(0, len(muestra) - 1, min(len(muestra), 4000)).astype(int)]
        base = np.abs(muestra["real"].to_numpy() - self._predecir_filas("24h", "M3", muestra)).mean()
        importancias = []
        for grupo, variables in GRUPOS_IMPORTANCIA.items():
            presentes = [c for c in variables if c in columnas]
            if not presentes:
                continue
            desordenada = muestra.copy()
            orden = rng.permutation(len(muestra))
            desordenada[presentes] = muestra[presentes].to_numpy()[orden]
            error = np.abs(muestra["real"].to_numpy() - self._predecir_filas("24h", "M3", desordenada)).mean()
            importancias.append(Importancia(variable=grupo, valor=round(float(error - base), 1)))
        importancias.sort(key=lambda x: x.valor, reverse=True)

        # Residuos: 240 periodos de la prueba
        elegidos = prueba.iloc[np.linspace(0, len(prueba) - 1, min(len(prueba), 240)).astype(int)]
        predicho = self._predicciones_area(area, "24h", "M3").reindex(elegidos.index).to_numpy()
        ok = ~np.isnan(predicho)
        return Diagnostico(
            mae_por_regimen=por_regimen,
            ablacion=ablacion,
            adaptacion=self._adaptacion_notebook_03(area),
            importancias=importancias,
            residuos=Residuos(real=_redondear(elegidos["real"].to_numpy()[ok]), predicho=_redondear(predicho[ok])))

    def _adaptacion_notebook_03(self, area: str) -> list[Adaptacion]:
        """Fijo, semanal y alerta de ENFEN a 24 h, de la tabla del notebook 03 (Random Forest)."""
        ruta = raiz_datos(self._raiz) / "reportes" / "sein" / "prueba_2026" / "adaptacion.csv"
        if not ruta.exists():
            return []
        tabla = pd.read_csv(ruta)
        filas = tabla[(tabla["Horizonte"] == "24h") & (tabla["Área"] == area.capitalize())
                      & tabla["Variante"].isin(["M0", "M3"]) & tabla["Política"].isin(POLITICA_CONTRATO)]
        return [Adaptacion(politica=POLITICA_CONTRATO[f["Política"]], exogenas=f["Variante"] == "M3",
                           mae=round(float(f["MAE (MW)"]), 1)) for _, f in filas.iterrows()]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["entrenar"]:
        print("Uso: python -m app.backend.pronosticador_real entrenar")
        return 2
    entrenar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
