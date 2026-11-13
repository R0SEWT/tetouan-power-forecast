"""Los modelos de la app que usan modelos fundacionales: el híbrido y el combinado (al final del archivo).

El híbrido es el XGBoost global en razón más el pronóstico de un modelo fundacional como variable.

El modelo fundacional (Simons, sin ajustar) pronostica las 24 h siguientes desde cada origen, mirando solo la
demanda hasta ese origen. Necesita GPU, así que se calcula aparte (``experimentos`` del notebook 04) y la app lee
sus pronósticos ya guardados: ``reportes/sein/fundacionales/simons_c2048.parquet``. El XGBoost recibe, además de
las variables de M0, tres variables por origen, todas divididas por ``media_24h``: el pronóstico fundacional del
horizonte, el ancho de su intervalo 10–90 % y el pronóstico del otro horizonte. Los modelos están en
``modelos/sein/fundacionales/xgb_simons_{1h,24h}.joblib`` y se entrenaron con datos hasta 2024.

**Qué se declara.**

- Solo hay pronóstico híbrido para los orígenes que el fundacional ya calculó. Fuera de ese rango la API
  responde 422; dentro, si falta un origen suelto, ese periodo usa la mejor referencia, como el modelo base.
- No usa clima, El Niño ni fallas: se comporta como «solo demanda» (M0) sea cual sea la variante pedida, los
  escenarios no lo cambian y su sensibilidad a esas variables es plana.
- El rango del 90 % sale de sus errores relativos de 2025, que el modelo no vio al entrenar; en 2025 ese rango
  está calibrado con los mismos datos que cubre.
- El diagnóstico compara, en la prueba de 2026, el híbrido con el XGBoost base de la app y con la mejor
  referencia. La tabla de reentrenamiento del notebook 03 no aplica a este modelo.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from tetouan_power_forecast.medallon import raiz_datos
from tetouan_power_forecast.modelado_sein import CODIGO_AREA, gradient_boosting_global, portable
from tetouan_power_forecast.variables_sein import PASO

from .contrato import (
    PASOS,
    Ablacion,
    Componente,
    Diagnostico,
    Escenario,
    Horizonte,
    Importancia,
    Intervalo,
    MaeRegimen,
    Pronostico,
    Residuos,
    Resumen,
    Serie,
    Variante,
)
from .pronosticador import estado_nino
from .pronosticador_real import (
    DIA,
    FIN_DESARROLLO,
    FIN_ENTRENAMIENTO,
    GRUPOS_IMPORTANCIA,
    HIPERPARAMETROS,
    PronosticadorReal,
    _bootstrap_mae,
    _con_nulos,
    _feriados,
    _redondear,
    armar_datasets,
    cargar_capas,
)

FUNDACIONAL = "simons"
ARCHIVO_FUNDACIONAL = f"{FUNDACIONAL}_c2048.parquet"
COLUMNAS_FUNDACIONALES = [f"fm_{FUNDACIONAL}_pred", f"fm_{FUNDACIONAL}_ancho", f"fm_{FUNDACIONAL}_otro"]
ID_HIBRIDO = "hibrido"


def carpeta_hibrido(raiz=None) -> Path:
    return raiz_datos(raiz) / "modelos" / "sein" / "fundacionales"


def ruta_fundacional(raiz=None) -> Path:
    return raiz_datos(raiz) / "reportes" / "sein" / "fundacionales" / ARCHIVO_FUNDACIONAL


def hibrido_disponible(raiz=None) -> bool:
    carpeta = carpeta_hibrido(raiz)
    return ruta_fundacional(raiz).exists() and all((carpeta / f"xgb_{FUNDACIONAL}_{h}.joblib").exists() for h in PASOS)


def _leer_fundacional(raiz=None, con_entrenamiento=False) -> pd.DataFrame:
    """Los pronósticos fundacionales por (área, origen). Los de antes de 2025 van en un archivo ``_train`` aparte."""
    ruta = ruta_fundacional(raiz)
    piezas = [pd.read_parquet(ruta)]
    ruta_ent = ruta.with_name(ruta.stem + "_train.parquet")
    if con_entrenamiento and ruta_ent.exists():
        piezas.insert(0, pd.read_parquet(ruta_ent))
    fm = pd.concat(piezas, ignore_index=True)
    fm["area_cod"] = fm["area"].str.upper().map(CODIGO_AREA)
    return fm.drop_duplicates(["area_cod", "DateTime"]).set_index(["area_cod", "DateTime"]).sort_index()


def _variables_fundacionales(fundacional: pd.DataFrame, nombre_h: str, filas: pd.DataFrame) -> pd.DataFrame:
    """Añade las tres variables fundacionales del origen de cada fila, en razón a ``media_24h``."""
    h = PASOS[nombre_h]
    otro = next(p for p in PASOS.values() if p != h)
    clave = pd.MultiIndex.from_arrays([filas["area_cod"].to_numpy(), pd.to_datetime(filas["DateTime"]).to_numpy()])
    f = fundacional.reindex(clave)
    escala = filas["media_24h"].to_numpy(dtype=float)
    filas = filas.copy()
    filas[COLUMNAS_FUNDACIONALES[0]] = f[f"pred_{h}"].to_numpy() / escala
    filas[COLUMNAS_FUNDACIONALES[1]] = (f[f"q90_{h}"] - f[f"q10_{h}"]).to_numpy() / escala
    filas[COLUMNAS_FUNDACIONALES[2]] = f[f"pred_{otro}"].to_numpy() / escala
    return filas


def entrenar_hibrido(raiz=None, hiperparametros=None, progreso=print) -> Path:
    """Entrena el XGBoost apilado con los objetivos hasta 2024 y lo guarda en ``modelos/sein/fundacionales/``.

    Necesita los pronósticos fundacionales de los orígenes de entrenamiento (archivo ``_train``). Es la misma
    receta que corrió en Colab para el notebook 04; aquí queda para poder repetirla.
    """
    from tetouan_power_forecast.variables_sein import columnas_variante

    demanda, exogenas = cargar_capas(raiz)
    datos = armar_datasets(demanda, exogenas, _feriados())
    fundacional = _leer_fundacional(raiz, con_entrenamiento=True)
    destino = carpeta_hibrido(raiz)
    destino.mkdir(parents=True, exist_ok=True)
    for nombre_h, pasos in PASOS.items():
        columnas = [*columnas_variante(next(iter(datos[nombre_h].values())), "M0"), *COLUMNAS_FUNDACIONALES]
        filas = pd.concat([_variables_fundacionales(fundacional, nombre_h, d[d.index < FIN_ENTRENAMIENTO - pasos * PASO])
                           for d in datos[nombre_h].values()], ignore_index=True).dropna(subset=[*columnas, "real"])
        modelo = gradient_boosting_global(**(hiperparametros or HIPERPARAMETROS)).fit(filas[columnas], filas["real"])
        joblib.dump(portable(modelo), destino / f"xgb_{FUNDACIONAL}_{nombre_h}.joblib")
        progreso(f"híbrido {nombre_h}: {len(filas):,} filas")
    return destino


class PronosticadorHibrido(PronosticadorReal):
    """El XGBoost apilado sobre el pronóstico fundacional. Comparte las capas y los datasets del modelo base."""

    id = ID_HIBRIDO
    variantes = ("M0",)
    descripcion = ("Suma al modelo el pronóstico de un modelo fundacional (Simons) calculado aparte con GPU. "
                   "Usa solo la demanda: no tiene escenarios de clima ni de El Niño.")

    def __init__(self, base: PronosticadorReal, raiz=None):
        raiz = raiz if raiz is not None else base._raiz
        if not hibrido_disponible(raiz):
            raise FileNotFoundError(
                f"Faltan los modelos del híbrido en {carpeta_hibrido(raiz)} o los pronósticos fundacionales en "
                f"{ruta_fundacional(raiz)}.")
        # Las capas y los datasets son los del modelo base: no se cargan dos veces
        self._base = base
        self.respaldo = base  # fuera de su rango de fechas responde el modelo base
        self._raiz = raiz
        self._meta = base._meta
        self._demanda, self._exogenas, self._datos, self._real = base._demanda, base._exogenas, base._datos, base._real
        self._modelos_hibridos = {h: joblib.load(carpeta_hibrido(raiz) / f"xgb_{FUNDACIONAL}_{h}.joblib") for h in PASOS}
        self._fundacional = _leer_fundacional(raiz)
        self._columnas_hibrido = {h: [*base._columnas(h, "M0"), *COLUMNAS_FUNDACIONALES] for h in PASOS}
        self._predicciones = {}
        self._diagnosticos = {}
        self._resumen = None
        self.modelo = "Híbrido: XGBoost + Simons"
        self.nombre = "Híbrido (XGBoost + Simons)"
        self.version_datos = base.version_datos
        origenes = self._fundacional.index.get_level_values("DateTime")
        # A 24 h, los periodos de un día se emiten el día anterior: el primer día completo es el siguiente
        self.fecha_min = (origenes.min().normalize() + pd.Timedelta(days=1)).date()
        self.fecha_max = min(base.fecha_max, (origenes.max().normalize() - pd.Timedelta(days=1)).date())
        self._intervalos = self._calibrar_intervalos()

    # ---- núcleo --------------------------------------------------------------------------------

    def _columnas(self, nombre_h: str, variante: str) -> list[str]:
        return self._base._columnas(nombre_h, "M0")

    def _con_fundacional(self, nombre_h: str, filas: pd.DataFrame) -> pd.DataFrame:
        return _variables_fundacionales(self._fundacional, nombre_h, filas)

    def _predecir_filas(self, nombre_h: str, variante: str, filas: pd.DataFrame) -> np.ndarray:
        columnas = self._columnas_hibrido[nombre_h]
        filas = self._con_fundacional(nombre_h, filas)
        salida = np.full(len(filas), np.nan)
        completas = filas[columnas].notna().all(axis=1).to_numpy()
        if completas.any():
            salida[completas] = self._modelos_hibridos[nombre_h].predict(filas.loc[completas, columnas])
        return salida

    def _calibrar_intervalos(self) -> dict[str, list[float]]:
        """Cuantiles 5 y 95 % del error relativo de 2025, que el modelo no vio (se entrenó hasta 2024)."""
        intervalos = {}
        for nombre_h, pasos in PASOS.items():
            for area, d in self._datos[nombre_h].items():
                val = d[(d.index >= FIN_ENTRENAMIENTO) & (d.index < FIN_DESARROLLO - pasos * PASO)].dropna(subset=["real"])
                pred = self._predicciones_area(area, nombre_h, "M0").reindex(val.index)
                relativo = (val["real"] / pred - 1).dropna()
                if len(relativo) >= DIA:
                    intervalos[f"{area}_{nombre_h}"] = [float(relativo.quantile(0.05)), float(relativo.quantile(0.95))]
        return intervalos

    def _intervalo(self, area: str, horizonte: Horizonte, variante: Variante, pred: np.ndarray) -> Intervalo:
        bajo, alto = self._intervalos.get(f"{area}_{horizonte}", [-0.03, 0.03])
        return Intervalo(inferior=_redondear(pred * (1 + min(bajo, 0.0))),
                         superior=_redondear(pred * (1 + max(alto, 0.0))))

    # ---- contrato: el híbrido es «solo demanda», pida lo que pida la variante ------------------

    def serie(self, area: str, fecha: date, horizonte: Horizonte, variante: Variante) -> Serie:
        return super().serie(area, fecha, horizonte, "M0")

    def pronosticar(self, area, origen, horizonte: Horizonte, variante: Variante, escenario: Escenario) -> Pronostico:
        return super().pronosticar(area, origen, horizonte, "M0", escenario)

    def resumen(self) -> Resumen:
        if self._resumen is None:
            resumen = super().resumen()
            corte = {**resumen.fechas_corte, "disponible_desde": self.fecha_min.isoformat(),
                     "validacion_hasta": "2025-12-31 (el híbrido se entrenó hasta 2024)"}
            self._resumen = resumen.model_copy(update={"fechas_corte": corte})
        return self._resumen

    def _calcular_diagnostico(self, area: str) -> Diagnostico:
        nombre_ref = self._mejor_referencia(area, "24h")
        rng = np.random.default_rng(0)
        prueba = self._prueba(area, "24h")
        prueba = prueba[prueba.index >= FIN_DESARROLLO]
        hibrido = self._predicciones_area(area, "24h", "M0").reindex(prueba.index).to_numpy()

        # Error por régimen de El Niño en la prueba de 2026
        filas = prueba.dropna(subset=[nombre_ref])
        pred = pd.Series(hibrido, index=prueba.index).reindex(filas.index).to_numpy()
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

        # El híbrido frente al XGBoost base de la app (M0 y M3), en las mismas filas y con intervalo por días
        dias = prueba.index.normalize().to_numpy()
        candidatos = {"M0": self._base._predicciones_area(area, "24h", "M0").reindex(prueba.index).to_numpy(),
                      "M3": self._base._predicciones_area(area, "24h", "M3").reindex(prueba.index).to_numpy(),
                      ID_HIBRIDO: hibrido}
        ablacion = []
        for nombre, p in candidatos.items():
            error = np.abs(prueba["real"].to_numpy() - p)
            bajo, alto = _bootstrap_mae(error, dias, rng)
            ablacion.append(Ablacion(variante=nombre, mae=round(float(np.nanmean(error)), 1), ic_inf=round(bajo, 1),
                                     ic_sup=round(alto, 1)))

        # Importancia por grupo: cuánto sube el MAE al desordenar juntas las variables del grupo
        columnas = self._columnas_hibrido["24h"]
        muestra = self._con_fundacional("24h", prueba).dropna(subset=columnas)
        muestra = muestra.iloc[np.linspace(0, len(muestra) - 1, min(len(muestra), 4000)).astype(int)]
        modelo = self._modelos_hibridos["24h"]
        real = muestra["real"].to_numpy()
        base = np.abs(real - modelo.predict(muestra[columnas])).mean()
        grupos = {"demanda_reciente": GRUPOS_IMPORTANCIA["demanda_reciente"], "calendario": GRUPOS_IMPORTANCIA["calendario"],
                  "fundacional": COLUMNAS_FUNDACIONALES}
        importancias = []
        for grupo, variables in grupos.items():
            presentes = [c for c in variables if c in columnas]
            desordenada = muestra[columnas].copy()
            desordenada[presentes] = muestra[presentes].to_numpy()[rng.permutation(len(muestra))]
            error = np.abs(real - modelo.predict(desordenada)).mean()
            importancias.append(Importancia(variable=grupo, valor=round(float(error - base), 1)))
        importancias.sort(key=lambda x: x.valor, reverse=True)

        elegidos = prueba.iloc[np.linspace(0, len(prueba) - 1, min(len(prueba), 240)).astype(int)]
        predicho = pd.Series(hibrido, index=prueba.index).reindex(elegidos.index).to_numpy()
        ok = ~np.isnan(predicho)
        return Diagnostico(mae_por_regimen=por_regimen, ablacion=ablacion, adaptacion=[], importancias=importancias,
                           residuos=Residuos(real=_redondear(elegidos["real"].to_numpy()[ok]),
                                             predicho=_redondear(predicho[ok])))


# ---- combinado -----------------------------------------------------------------------------------

ID_COMBINADO = "combinado"
ARCHIVO_AJUSTADO = "chronos2ftcal_c2048.parquet"
ARCHIVO_PESOS = "combinado.json"
# Peso del fundacional ajustado en la mezcla; el resto es del híbrido. Viven en ``combinado.json``, junto a los
# modelos del híbrido (ver ``guardar_pesos``); estos son los del notebook 04 y se usan si falta el archivo.
PESOS_POR_DEFECTO = {
    "1h": {"norte": 0.35, "centro": 0.45, "sur": 0.65},
    "24h": {"norte": 0.70, "centro": 0.85, "sur": 0.95},
}
ORIGEN_PESOS = ("Notebook 04: para cada horizonte y área, el peso con menor MAE en la validación de 2025 "
                "(rejilla de 0 a 1 cada 0.05). Se fijaron con 2025 y se aplican tal cual a 2026.")


def ruta_ajustado(raiz=None) -> Path:
    return raiz_datos(raiz) / "reportes" / "sein" / "fundacionales" / ARCHIVO_AJUSTADO


def ruta_pesos(raiz=None) -> Path:
    return carpeta_hibrido(raiz) / ARCHIVO_PESOS


def ruta_tabla_pesos(raiz=None) -> Path:
    """La tabla de pesos que escribe el notebook 04."""
    return raiz_datos(raiz) / "reportes" / "sein" / "fundacionales" / "tablas" / "pesos_combinacion.csv"


def combinado_disponible(raiz=None) -> bool:
    return hibrido_disponible(raiz) and ruta_ajustado(raiz).exists()


def leer_pesos(raiz=None) -> tuple[dict[str, dict[str, float]], str]:
    """Los pesos del ajustado por horizonte y área y de dónde salen. Sin ``combinado.json``, los por defecto."""
    ruta = ruta_pesos(raiz)
    if not ruta.exists():
        return PESOS_POR_DEFECTO, f"{ORIGEN_PESOS} (valores por defecto: falta {ruta.name})"
    datos = json.loads(ruta.read_text())
    try:
        pesos = {h: {a: float(datos["pesos_ajustado"][h][a]) for a in areas} for h, areas in PESOS_POR_DEFECTO.items()}
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{ruta} no trae un peso numérico por horizonte y área: {error}") from error
    fuera = [f"{h} {a}" for h, areas in pesos.items() for a, w in areas.items() if not 0 <= w <= 1]
    if fuera:
        raise ValueError(f"{ruta}: pesos fuera de 0-1 en {', '.join(fuera)}")
    return pesos, str(datos.get("origen") or ORIGEN_PESOS)


def guardar_pesos(raiz=None) -> Path:
    """Escribe ``combinado.json`` con los pesos de la tabla del notebook 04 (o los por defecto si no está)."""
    pesos = {h: dict(areas) for h, areas in PESOS_POR_DEFECTO.items()}
    tabla = ruta_tabla_pesos(raiz)
    if tabla.exists():
        filas = pd.read_csv(tabla)
        for _, f in filas.iterrows():
            pesos[f["Horizonte"]][f["Área"].lower()] = round(float(f["Peso del primero"]), 2)
    ruta = ruta_pesos(raiz)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({
        "pesos_ajustado": pesos,
        "formula": "pronóstico = peso · Chronos-2 ajustado + (1 − peso) · híbrido (XGBoost + Simons)",
        "ajustado": ARCHIVO_AJUSTADO,
        "origen": ORIGEN_PESOS,
        "tabla": str(tabla.relative_to(raiz_datos(raiz))) if tabla.exists() else None,
    }, ensure_ascii=False, indent=2) + "\n")
    return ruta


class PronosticadorCombinado(PronosticadorHibrido):
    """Mezcla lineal de dos pronósticos: Chronos-2 con ajuste fino y feriados, y el híbrido.

    ``pronóstico = peso · ajustado + (1 − peso) · híbrido``, con el peso de ``combinado.json``. Chronos-2 se
    ajustó con datos hasta 2024 y, como Simons, se calcula aparte con GPU: la app lee sus pronósticos guardados
    (``reportes/sein/fundacionales/chronos2ftcal_c2048.parquet``). Los pesos y el rango del 90 % (cuantiles 5 y
    95 % del error relativo de la mezcla) se fijaron con 2025, así que en 2025 las cifras son optimistas; la
    prueba es 2026. Como el híbrido, usa solo la demanda y el calendario.
    """

    id = ID_COMBINADO
    descripcion = ("Recomendado: mezcla el híbrido con un segundo modelo fundacional (Chronos-2) ajustado a estas "
                   "series con datos hasta 2024. Es el de menor error en 2026. Usa solo la demanda.")

    def __init__(self, hibrido: PronosticadorHibrido, raiz=None):
        raiz = raiz if raiz is not None else hibrido._raiz
        if not ruta_ajustado(raiz).exists():
            raise FileNotFoundError(f"Faltan los pronósticos del fundacional ajustado en {ruta_ajustado(raiz)}.")
        self._hibrido = hibrido
        self._base = hibrido._base
        self.respaldo = hibrido._base
        self._modelos_hibridos, self._columnas_hibrido = hibrido._modelos_hibridos, hibrido._columnas_hibrido
        self._fundacional = hibrido._fundacional
        self._raiz = raiz
        self._meta = hibrido._meta
        self._demanda, self._exogenas, self._datos, self._real = (hibrido._demanda, hibrido._exogenas, hibrido._datos,
                                                                  hibrido._real)
        ajustado = pd.read_parquet(ruta_ajustado(raiz))
        ajustado["area_cod"] = ajustado["area"].str.upper().map(CODIGO_AREA)
        self._ajustado = ajustado.drop_duplicates(["area_cod", "DateTime"]).set_index(["area_cod", "DateTime"]).sort_index()
        self.pesos, self.origen_pesos = leer_pesos(raiz)
        self._peso_por_codigo = {h: {CODIGO_AREA[a.upper()]: w for a, w in pesos.items()}
                                 for h, pesos in self.pesos.items()}
        self._predicciones = {}
        self._diagnosticos = {}
        self._resumen = None
        self.modelo = "Combinado: Chronos-2 ajustado + híbrido"
        self.nombre = "Combinado (recomendado)"
        self.version_datos = hibrido.version_datos
        origenes = self._ajustado.index.get_level_values("DateTime")
        self.fecha_min = max(hibrido.fecha_min, (origenes.min().normalize() + pd.Timedelta(days=1)).date())
        self.fecha_max = min(hibrido.fecha_max, (origenes.max().normalize() - pd.Timedelta(days=1)).date())
        self._intervalos = self._calibrar_intervalos()

    def _predecir_ajustado(self, nombre_h: str, filas: pd.DataFrame) -> np.ndarray:
        clave = pd.MultiIndex.from_arrays([filas["area_cod"].to_numpy(), pd.to_datetime(filas["DateTime"]).to_numpy()])
        return self._ajustado[f"pred_{PASOS[nombre_h]}"].reindex(clave).to_numpy(dtype=float)

    def _predecir_filas(self, nombre_h: str, variante: str, filas: pd.DataFrame) -> np.ndarray:
        peso = filas["area_cod"].map(self._peso_por_codigo[nombre_h]).to_numpy(dtype=float)
        return (peso * self._predecir_ajustado(nombre_h, filas)
                + (1 - peso) * self._hibrido._predecir_filas(nombre_h, variante, filas))

    def serie(self, area: str, fecha: date, horizonte: Horizonte, variante: Variante) -> Serie:
        """La serie del día con sus dos piezas y sus pesos, para que la app muestre cómo se arma cada número."""
        serie = super().serie(area, fecha, horizonte, variante)
        inicios = pd.date_range(pd.Timestamp(fecha), periods=DIA, freq="30min")
        emision = self._emision(inicios, horizonte)
        filas = self._datos[horizonte][area].reindex(emision)
        peso = self.pesos[horizonte][area]
        hibrido = self._hibrido._predicciones_area(area, horizonte, "M0").reindex(emision).to_numpy()
        componentes = [
            Componente(id="ajustado", nombre="Chronos-2 ajustado", peso=round(peso, 2),
                       valores=_con_nulos(self._predecir_ajustado(horizonte, filas))),
            Componente(id=ID_HIBRIDO, nombre="Híbrido (XGBoost + Simons)", peso=round(1 - peso, 2),
                       valores=_con_nulos(hibrido)),
        ]
        return serie.model_copy(update={"componentes": componentes})

    def _calcular_diagnostico(self, area: str) -> Diagnostico:
        """Como el del híbrido, pero compara las piezas de la mezcla y mide qué se pierde al quitar cada una."""
        diagnostico = super()._calcular_diagnostico(area)
        rng = np.random.default_rng(0)
        prueba = self._prueba(area, "24h")
        prueba = prueba[prueba.index >= FIN_DESARROLLO]
        dias, real = prueba.index.normalize().to_numpy(), prueba["real"].to_numpy()
        piezas = {"M0": self._base._predicciones_area(area, "24h", "M0").reindex(prueba.index).to_numpy(),
                  ID_HIBRIDO: self._hibrido._predicciones_area(area, "24h", "M0").reindex(prueba.index).to_numpy(),
                  "ajustado": self._predecir_ajustado("24h", prueba),
                  ID_COMBINADO: self._predicciones_area(area, "24h", "M0").reindex(prueba.index).to_numpy()}
        ablacion, mae = [], {}
        for nombre, p in piezas.items():
            error = np.abs(real - p)
            mae[nombre] = float(np.nanmean(error))
            bajo, alto = _bootstrap_mae(error, dias, rng)
            ablacion.append(Ablacion(variante=nombre, mae=round(mae[nombre], 1), ic_inf=round(bajo, 1),
                                     ic_sup=round(alto, 1)))
        # Lo que sube el error si la mezcla se queda sin una de sus dos piezas
        importancias = [Importancia(variable="ajustado", valor=round(mae[ID_HIBRIDO] - mae[ID_COMBINADO], 1)),
                        Importancia(variable=ID_HIBRIDO, valor=round(mae["ajustado"] - mae[ID_COMBINADO], 1))]
        importancias.sort(key=lambda x: x.valor, reverse=True)
        return diagnostico.model_copy(update={"ablacion": ablacion, "importancias": importancias})


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["entrenar"]:
        print(f"modelos del híbrido en {entrenar_hibrido()}")
        return 0
    if argv[:1] == ["pesos"]:
        ruta = guardar_pesos()
        print(f"pesos del combinado en {ruta}:\n{ruta.read_text()}")
        return 0
    print("Uso: python -m app.backend.pronosticador_hibrido {entrenar|pesos}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
