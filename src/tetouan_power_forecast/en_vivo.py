"""Tubería diaria «en vivo»: con el anexo del IEOD de ayer, el pronóstico a 24 h de hoy, registrado antes del real.

El COES publica la demanda por área del día D en el anexo diario del IEOD (`AnexoA_DDMM.xlsx`, hoja `DEMANDA_AREAS`)
hacia las 09:45 del día D+1. Es la misma fuente y la misma definición que la capa silver, así que la serie sigue sin
costura: la silver histórica (hasta el 22 de octubre de 2026) más una capa en vivo que solo crece.

Qué es en vivo y qué no:

- A 24 h sí. Con los datos hasta el fin de D, el modelo pronostica desde cada uno de los 48 orígenes de D el periodo
  24 h después: los 48 periodos de D+1. Quedan registrados con el sello de la corrida antes de que el COES publique
  su real, que llega en el anexo de D+1 (el día D+2).
- A 1 h no. Cada origen necesita la demanda de una hora antes del objetivo, que llega al día siguiente junto con el
  real. El pronóstico a 1 h del día D se emite igual, para seguirlo, pero siempre como «reconstruido».

Cada fila del registro lleva un `tipo`, que sale del sello `emitido_en` y no de lo que diga la corrida:

- `ex_ante_estricto`: al emitirse, el periodo objetivo todavía no empezaba.
- `en_vivo`: el periodo ya había empezado, pero su día no había terminado, así que el COES no podía haber publicado
  su real (el anexo cubre el día entero y sale después). Es una cota conservadora: una fila emitida entre el fin del
  día y la publicación también sería en vivo, pero aquí cuenta como reconstruida.
- `reconstruido`: se emitió después (el relleno inicial, el 1 h y cualquier corrida atrasada). Usa solo los datos
  hasta su origen, pero no se registró antes de conocerse el real.

El modelo de esta versión es Chronos-2 ajustado con feriados (`chronos2ftcal`), el mejor individual a 24 h en la prueba
de 2026, con la misma inferencia de `experimentos/fundacionales/chronos2_variantes.py`: 2048 periodos de contexto, el
feriado como covariable pasada y futura y los cuantiles 10, 50 y 90 %. Cualquier modelo que devuelva sus pronósticos
con el formato de esos experimentos (`ChronosAjustado.pronosticar`) entra igual; así se sumará el combinado cuando
estén los pesos de Simons (ver `experimentos/en_vivo/README.md`).

Capas, dentro de la carpeta de datos (`TETOUAN_DATA`):

- coes/bronze/ieod_diario/AAAA-MM-DD/: el anexo tal cual, con las correcciones del COES aparte (con su sha256 en el
  nombre), y coes/bronze/ieod_diario/procedencia.jsonl, una línea por descarga.
- coes/silver/demanda_areas_en_vivo.parquet: la demanda cada 30 minutos desde el día siguiente a la silver histórica,
  que no se toca; con el sha256 del anexo de cada día.
- reportes/sein/en_vivo/pronosticos.parquet: el registro. Solo crece: una fila emitida nunca se reescribe y una
  segunda corrida no la duplica.
- reportes/sein/en_vivo/seguimiento.parquet: el error de cada periodo que ya tiene real; resumen.parquet: el MAE y la
  cobertura por día y acumulados, por tipo, frente a la mejor referencia ingenua. Se rehacen en cada corrida.
- reportes/sein/en_vivo/corridas.jsonl y diario.log: una línea por corrida, con su duración.

Uso, con el entorno que tiene Chronos-2 (`experimentos/en_vivo/entorno.sh`):

    python -m tetouan_power_forecast.en_vivo diario      # ingesta → pronóstico → evaluación
    python -m tetouan_power_forecast.en_vivo relleno     # lo mismo, sin emitir el día de hoy
"""

import argparse
import contextlib
import datetime as dt
import hashlib
import html
import json
import logging
import os
import re
import subprocess
import sys
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from tetouan_power_forecast import coes
from tetouan_power_forecast.medallon import _reemplazar, raiz_datos

LIMA = ZoneInfo("America/Lima")
PASO = pd.Timedelta(minutes=30)
DIA = pd.Timedelta(days=1)
PERIODOS_DIA = 48
AREAS = ["NORTE", "CENTRO", "SUR"]
PASOS = {"1h": 2, "24h": 48}
CONTEXTO = 2048
CUANTILES = (0.1, 0.5, 0.9)
ARRANQUE = dt.date(2026, 10, 23)  # el primer día que no está en la silver histórica
TIPOS = ("ex_ante_estricto", "en_vivo", "reconstruido")
GRUPOS = {"en_vivo": ("ex_ante_estricto", "en_vivo"), "ex_ante_estricto": ("ex_ante_estricto",),
          "reconstruido": ("reconstruido",)}
# Las referencias ingenuas del proyecto (variables_sein): a 24 h, «persistencia» es lo mismo que «ayer».
REFERENCIAS = {"1h": ["persistencia", "ayer", "semana_pasada"], "24h": ["ayer", "semana_pasada"]}
CLAVE = ["modelo", "version_pesos", "horizonte", "area", "objetivo"]
COLUMNAS_REGISTRO = ["fecha_objetivo", "objetivo", "origen", "area", "horizonte", "pred", "q10", "q90", "modelo",
                     "version_pesos", "emitido_en", "datos_hasta", "datos_sha256", "tipo", "version_codigo"]
COLUMNAS_EN_VIVO = ["DateTime", *coes.AREAS, "sha256", "archivo", "descargado_utc"]
PESOS_CHRONOS = Path.home() / ".cache" / "tpf-vivo" / "pesos" / "chronos2ftcal" / "finetuned-ckpt"
SIN_PUBLICAR = 75  # EX_TEMPFAIL: el anexo todavía no sale, se reintenta más tarde
INVALIDO = 3  # el anexo no pasa las validaciones: no se emite nada y hay que mirarlo
VENTANA_SALTO = pd.Timedelta(days=730)

log = logging.getLogger("tetouan_power_forecast.en_vivo")


class AnexoNoPublicado(LookupError):
    def __init__(self, dia):
        self.dia = dia
        super().__init__(f"El COES todavía no publica el anexo del IEOD del {dia:%Y-%m-%d} (suele salir hacia "
                         "las 09:45 del día siguiente). Reintenta más tarde.")


class AnexoInvalido(ValueError):
    """El anexo o la serie no pasan las validaciones: no se agrega ni se emite nada."""


@dataclass(frozen=True)
class Rutas:
    raiz: Path

    @property
    def bronze(self):
        return self.raiz / "coes" / "bronze" / "ieod_diario"

    @property
    def procedencia(self):
        return self.bronze / "procedencia.jsonl"

    @property
    def silver(self):
        return self.raiz / "coes" / "silver" / "demanda_areas.parquet"

    @property
    def en_vivo(self):
        return self.raiz / "coes" / "silver" / "demanda_areas_en_vivo.parquet"

    @property
    def reportes(self):
        return self.raiz / "reportes" / "sein" / "en_vivo"

    @property
    def pronosticos(self):
        return self.reportes / "pronosticos.parquet"

    @property
    def seguimiento(self):
        return self.reportes / "seguimiento.parquet"

    @property
    def resumen(self):
        return self.reportes / "resumen.parquet"

    @property
    def corridas(self):
        return self.reportes / "corridas.jsonl"

    @property
    def log(self):
        return self.reportes / "diario.log"


def rutas(raiz=None):
    return raiz if isinstance(raiz, Rutas) else Rutas(raiz_datos(raiz))


def _ahora_utc():
    return pd.Timestamp.now(tz="UTC")


def _hoy_lima():
    return dt.datetime.now(LIMA).date()


def _dias(desde, hasta):
    return [desde + dt.timedelta(days=k) for k in range((hasta - desde).days + 1)]


def _anotar(ruta, linea):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a") as salida:  # solo se agrega
        salida.write(json.dumps(linea, ensure_ascii=False, default=str) + "\n")


def _escribir_parquet(ruta, df):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    _reemplazar(ruta, lambda r: df.to_parquet(r, index=False))


# ---- Ingesta ------------------------------------------------------------------------------------------------------

_CELDA = re.compile(r"<td[^>]*?onclick=\"openBlob\('([^']+)',\s*'F'[^\"]*\"[^>]*>(.*?)</td>", re.DOTALL)


def metadatos_listado(texto):
    """La firma de cada archivo de una carpeta del navegador: tamaño, publicación, observaciones y modificaciones.

    Si el COES corrige un anexo, cambia el tamaño o se llenan las observaciones («Se actualizó el despacho…»): con
    comparar la firma basta para saber si hay que volver a bajarlo, sin bajarlo.
    """
    celdas = {}
    for ruta, contenido in _CELDA.findall(texto):
        texto_celda = re.sub(r"<[^>]+>", "", html.unescape(contenido))
        celdas.setdefault(html.unescape(ruta), []).append(re.sub(r"\s+", " ", texto_celda).strip())
    # La primera celda es el ícono y la segunda el nombre
    return {ruta: " | ".join(valores[2:]) for ruta, valores in celdas.items()}


class Portal:
    """El navegador de archivos del COES, con pocas peticiones: espaciadas, con reintentos (los de `coes._pedir`)."""

    def __init__(self, pedir=coes._pedir, pausa=3.0, dormir=time.sleep):
        self._pedir = pedir
        self._pausa = pausa
        self._dormir = dormir
        self._ultima = None
        self.peticiones = 0
        self.bytes = 0
        self._html = {}
        self._navegador = coes.Navegador(self._listar)

    def _espaciar(self):
        if self._ultima is not None:
            falta = self._pausa - (time.monotonic() - self._ultima)
            if falta > 0:
                self._dormir(falta)
        self._ultima = time.monotonic()
        self.peticiones += 1

    def _listar(self, ruta):
        self._espaciar()
        datos = {"baseDirectory": coes.BASE_IEOD, "url": ruta, "indicador": "S"}
        contenido = self._pedir(f"{coes.URL_PORTAL}/browser/vistadatos", datos)
        self.bytes += len(contenido)
        texto = contenido.decode("utf-8", "replace")
        self._html[ruta] = texto
        return coes.parsear_listado(texto)

    def anexos(self, dia):
        """[(ruta, firma)] de los anexos en Excel del día; vacía si el COES todavía no los publica."""
        salida = []
        for ruta in self._navegador.anexos_del_dia(dia):
            carpeta = ruta.rsplit("/", 1)[0] + "/"
            salida.append((ruta, metadatos_listado(self._html.get(carpeta, "")).get(ruta, "")))
        return salida

    def descargar(self, ruta):
        self._espaciar()
        contenido = self._pedir(f"{coes.URL_PORTAL}/browser/download?" + urllib.parse.urlencode({"url": ruta}),
                                timeout=300)
        self.bytes += len(contenido)
        return contenido


def _guardar_version(carpeta, nombre, contenido, sha):
    """Guarda el anexo tal cual. Si ya había otro con el mismo nombre (una corrección), el nuevo va aparte."""
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / nombre
    if destino.exists() and hashlib.sha256(destino.read_bytes()).hexdigest() != sha:
        base, _, extension = nombre.rpartition(".")
        destino = carpeta / f"{base}.{sha[:12]}.{extension}"
    if not destino.exists():
        _reemplazar(destino, lambda r: r.write_bytes(contenido))
    return destino


def _bajar(dia, ruta, firma, portal, r):
    contenido = portal.descargar(ruta)
    sha = hashlib.sha256(contenido).hexdigest()
    destino = _guardar_version(r.bronze / f"{dia:%Y-%m-%d}", coes._nombre(ruta), contenido, sha)
    info = {"fecha": f"{dia:%Y-%m-%d}", "ruta_coes": ruta, "archivo": destino.name, "bytes": len(contenido),
            "sha256": sha, "firma": firma, "descargado_utc": _ahora_utc().isoformat(timespec="seconds")}
    return coes.leer_demanda_areas(destino, dia), info


def bajar_dia(dia, portal, raiz=None):
    """Baja el anexo de `dia`, lo guarda en el bronze y devuelve su demanda cada 30 min y su procedencia."""
    r = rutas(raiz)
    anexos = portal.anexos(dia)
    if not anexos:
        raise AnexoNoPublicado(dia)
    for ruta, firma in anexos:  # en 2026 hay uno solo (AnexoA_DDMM.xlsx); antes hubo varios
        df, info = _bajar(dia, ruta, firma, portal, r)
        if df is not None:
            validar_dia(df, dia)
            return df, info
    raise AnexoInvalido(f"{dia}: ningún anexo trae la hoja DEMANDA_AREAS")


def validar_dia(df, dia):
    """Los 48 periodos del día, sin vacíos, positivos y con Norte + Centro + Sur = SEIN (±1 MW)."""
    esperado = pd.date_range(pd.Timestamp(dia) + PASO, periods=PERIODOS_DIA, freq="30min")
    if df["DateTime"].tolist() != list(esperado):
        raise AnexoInvalido(f"{dia}: el anexo no trae los 48 periodos del día ({len(df)} filas)")
    if df[coes.AREAS].isna().any().any():
        raise AnexoInvalido(f"{dia}: hay periodos vacíos en DEMANDA_AREAS")
    if (df[coes.AREAS] <= 0).any().any():
        raise AnexoInvalido(f"{dia}: hay demandas no positivas en DEMANDA_AREAS")
    desvio = float((df[AREAS].sum(axis=1) - df["SEIN"]).abs().max())
    if desvio > 1:
        raise AnexoInvalido(f"{dia}: Norte + Centro + Sur no suman el SEIN (desvío de {desvio:.1f} MW)")


def validar_empalme(previa, nuevo):
    """El día nuevo empieza justo después del último dato y sin salto: su primer cambio de 30 minutos cae dentro de
    lo que se vio a esa misma hora en los dos últimos años (cuantiles 0.1–99.9 %, con una holgura de media banda y
    al menos el 2 % del nivel del área).

    Devuelve el cambio de cada área en el empalme, en MW.
    """
    ultimo = previa["DateTime"].iloc[-1]
    primero = nuevo["DateTime"].iloc[0]
    if primero != ultimo + PASO:
        raise AnexoInvalido(f"no empalma: el último dato es de {ultimo} y el primero nuevo de {primero}")
    salto = (nuevo[coes.AREAS].iloc[0] - previa[coes.AREAS].iloc[-1]).astype(float)
    historia = previa[previa["DateTime"] > ultimo - VENTANA_SALTO].set_index("DateTime")[coes.AREAS]
    cambios = historia.diff()
    cambios = cambios[cambios.index.time == primero.time()].dropna()
    if len(cambios) >= 30:  # con menos días no hay con qué comparar
        for area in coes.AREAS:
            bajo, alto = cambios[area].quantile([0.001, 0.999])
            holgura = max((alto - bajo) / 2, 0.02 * float(historia[area].mean()))
            if not bajo - holgura <= salto[area] <= alto + holgura:
                raise AnexoInvalido(
                    f"salto en el empalme del {primero:%Y-%m-%d %H:%M}: {area} cambia {salto[area]:+.0f} MW en 30 "
                    f"minutos; a esa hora lo normal va de {bajo:+.0f} a {alto:+.0f} MW. ¿Cambió la definición del área?")
    return {area: round(float(v), 1) for area, v in salto.items()}


def cargar_en_vivo(raiz=None):
    r = rutas(raiz)
    if not r.en_vivo.exists():
        return pd.DataFrame({c: pd.Series(dtype="datetime64[ns]" if c == "DateTime" else float if c in coes.AREAS
                                          else str) for c in COLUMNAS_EN_VIVO})
    return pd.read_parquet(r.en_vivo)


def serie_completa(raiz=None):
    """La demanda cada 30 minutos: la silver histórica más la capa en vivo, validando que empalmen sin huecos."""
    r = rutas(raiz)
    historia = pd.read_parquet(r.silver, columns=["DateTime", *coes.AREAS])
    vivo = cargar_en_vivo(r)
    if len(vivo):
        if vivo["DateTime"].iloc[0] != historia["DateTime"].iloc[-1] + PASO:
            raise AnexoInvalido(f"la capa en vivo empieza en {vivo['DateTime'].iloc[0]} y la silver histórica "
                                f"termina en {historia['DateTime'].iloc[-1]}: no empalman")
        serie = pd.concat([historia, vivo[["DateTime", *coes.AREAS]]], ignore_index=True)
    else:
        serie = historia
    pasos = serie["DateTime"].diff().iloc[1:]
    if not (pasos == PASO).all():
        malos = serie["DateTime"].iloc[1:][pasos.to_numpy() != PASO]
        raise AnexoInvalido(f"la serie no va cada 30 minutos: {len(malos)} saltos, el primero en {malos.iloc[0]}")
    return serie


def _ultimo_dia(serie):
    return (serie["DateTime"].iloc[-1] - PASO).date()


def _lineas_procedencia(r):
    if not r.procedencia.exists():
        return []
    return [json.loads(x) for x in r.procedencia.read_text().splitlines() if x.strip()]


def _revisar_correccion(dia, portal, r, vivo, progreso):
    """Vuelve a mirar la carpeta de un día ya ingerido; si el COES corrigió el anexo, baja la versión nueva.

    Lo emitido no se toca: solo cambia el real con que se evalúa. Devuelve la capa en vivo (corregida o igual).
    """
    previas = [x for x in _lineas_procedencia(r) if x["fecha"] == f"{dia:%Y-%m-%d}" and x.get("sha256")]
    if not previas:
        return vivo, None
    previa = previas[-1]
    firma = dict(portal.anexos(dia)).get(previa["ruta_coes"], "")
    if not firma or not previa.get("firma") or firma == previa["firma"]:
        return vivo, None
    df, info = _bajar(dia, previa["ruta_coes"], firma, portal, r)
    if info["sha256"] == previa["sha256"]:
        _anotar(r.procedencia, {**info, "estado": "sin_cambios"})
        return vivo, None
    validar_dia(df, dia)
    filas = (vivo["DateTime"] > pd.Timestamp(dia)) & (vivo["DateTime"] <= pd.Timestamp(dia) + DIA)
    antes, despues = vivo.loc[filas, coes.AREAS].to_numpy(dtype=float), df[coes.AREAS].to_numpy(dtype=float)
    cambio = float(np.abs(antes - despues).max())
    vivo = vivo.copy()
    vivo.loc[filas, coes.AREAS] = df[coes.AREAS].to_numpy()
    vivo.loc[filas, ["sha256", "archivo", "descargado_utc"]] = [info["sha256"], info["archivo"], info["descargado_utc"]]
    _escribir_parquet(r.en_vivo, vivo)
    _anotar(r.procedencia, {**info, "estado": "corregido", "cambio_max_mw": round(cambio, 3)})
    progreso(f"{dia}: el COES corrigió el anexo; la demanda cambió hasta {cambio:.1f} MW (lo emitido no se toca)")
    return vivo, dia


def ingerir(raiz=None, hoy=None, portal=None, revisar=2, progreso=print):
    """Baja los anexos que falten desde el último día de la serie hasta ayer y los agrega a la capa en vivo.

    Se detiene en el primer día que el COES todavía no publica (`faltante`): la serie no puede tener huecos. Cuando
    entra un día nuevo, vuelve a mirar los `revisar` días anteriores por si el COES los corrigió.
    """
    r = rutas(raiz)
    hoy = hoy or _hoy_lima()
    portal = portal or Portal()
    serie = serie_completa(r)
    vivo = cargar_en_vivo(r)
    previos = sorted({(t - PASO).date() for t in vivo["DateTime"]})
    nuevos, corregidos, faltante = [], [], None
    dia = _ultimo_dia(serie) + dt.timedelta(days=1)
    while dia < hoy:
        try:
            df, info = bajar_dia(dia, portal, r)
        except AnexoNoPublicado:
            faltante = dia
            break
        salto = validar_empalme(serie, df)
        df = df.assign(sha256=info["sha256"], archivo=info["archivo"], descargado_utc=info["descargado_utc"])
        vivo = pd.concat([vivo, df[COLUMNAS_EN_VIVO]], ignore_index=True) if len(vivo) else df[COLUMNAS_EN_VIVO]
        serie = pd.concat([serie, df[["DateTime", *coes.AREAS]]], ignore_index=True)
        _escribir_parquet(r.en_vivo, vivo)  # día por día: lo ya bajado no se pierde si algo falla después
        _anotar(r.procedencia, {**info, "estado": "ok", "salto_empalme_mw": salto})
        nuevos.append(dia)
        progreso(f"{dia}: anexo {info['archivo']} ({info['bytes'] / 1e6:.2f} MB), SEIN medio "
                 f"{df['SEIN'].mean():,.0f} MW, empalme {salto}")
        dia += dt.timedelta(days=1)
    if nuevos and revisar:
        for anterior in [d for d in previos if d < nuevos[0]][-revisar:]:
            vivo, corregido = _revisar_correccion(anterior, portal, r, vivo, progreso)
            if corregido:
                corregidos.append(corregido)
    return {"nuevos": nuevos, "corregidos": corregidos, "faltante": faltante, "ultimo_dia": _ultimo_dia(serie),
            "peticiones": portal.peticiones, "bytes": portal.bytes}


# ---- Pronóstico ---------------------------------------------------------------------------------------------------


def feriados(fechas):
    """1 si el periodo cae en un feriado de Perú, fechado por su inicio (como en chronos2_variantes.py).

    El rango de años sale de las fechas: no se queda en cero al cambiar de año.
    """
    import holidays

    dias = (pd.DatetimeIndex(fechas) - PASO).normalize()
    calendario = holidays.country_holidays("PE", years=range(dias.year.min() - 1, dias.year.max() + 2))
    return np.array([d in calendario for d in dias], dtype=np.float32)


def huella(archivo):
    sha = hashlib.sha256()
    with open(archivo, "rb") as entrada:
        for bloque in iter(lambda: entrada.read(1 << 22), b""):
            sha.update(bloque)
    return sha.hexdigest()


class ChronosAjustado:
    """Chronos-2 con ajuste fino y feriados (`chronos2ftcal`), en CPU, como `chronos2_variantes.py` con cov 2.

    `pronosticar(demanda, origenes)` devuelve una fila por (origen, área) con `pred_p`, `q10_p` y `q90_p` para
    p = 2 y 48 pasos: el formato de los parquet de `experimentos/fundacionales`. Otro modelo (el combinado) solo
    tiene que cumplir lo mismo y tener `nombre` y `version`.
    """

    nombre = "chronos2ftcal"
    descripcion = "Chronos-2 ajustado con feriados"

    def __init__(self, pesos=None, lote=128, bloque=384, dispositivo="cpu"):
        self.pesos = Path(pesos or os.environ.get("TPF_PESOS_CHRONOS") or PESOS_CHRONOS)
        archivo = self.pesos / "model.safetensors"
        if not archivo.exists():
            raise FileNotFoundError(f"No están los pesos de Chronos-2 ajustado en {archivo}. Extrae chronos2ftcal.tar "
                                    "ahí (experimentos/en_vivo/entorno.sh) o pasa --pesos.")
        self.version = huella(archivo)
        self.lote, self.bloque, self.dispositivo = lote, bloque, dispositivo
        self._pipe = None

    def pronosticar(self, demanda, origenes, progreso=print):
        import torch
        from chronos import Chronos2Pipeline

        if self._pipe is None:
            self._pipe = Chronos2Pipeline.from_pretrained(str(self.pesos), device_map=self.dispositivo)
        horizonte = max(PASOS.values())
        posiciones = demanda.index.get_indexer(pd.DatetimeIndex(origenes))
        if (posiciones < CONTEXTO - 1).any():
            raise ValueError(f"hay orígenes sin {CONTEXTO} periodos de contexto o fuera de la serie")
        inicio = int(posiciones.min()) - CONTEXTO + 1
        fechas = pd.date_range(demanda.index[inicio], periods=int(posiciones.max()) + horizonte + 1 - inicio,
                               freq="30min")
        feriado = feriados(fechas)  # conocido de antemano: también para los periodos después del último dato
        valores = demanda[AREAS].to_numpy(dtype=np.float32)
        entradas, claves = [], []
        for j, area in enumerate(AREAS):
            for i in posiciones:
                k = i - inicio
                entradas.append({"target": valores[i - CONTEXTO + 1:i + 1, j],
                                 "past_covariates": {"feriado": feriado[k - CONTEXTO + 1:k + 1]},
                                 "future_covariates": {"feriado": feriado[k + 1:k + 1 + horizonte]}})
                claves.append((demanda.index[i], area))
        cuantiles, empezo = [], time.monotonic()
        for b in range(0, len(entradas), self.bloque):
            with torch.inference_mode():
                q, _ = self._pipe.predict_quantiles(entradas[b:b + self.bloque], prediction_length=horizonte,
                                                    quantile_levels=list(CUANTILES), batch_size=self.lote,
                                                    context_length=CONTEXTO)
            cuantiles.extend(x.detach().float().cpu().numpy()[0] for x in q)  # [H, 3] de la única variable
            progreso(f"Chronos-2: {len(cuantiles)}/{len(entradas)} series · {time.monotonic() - empezo:.0f} s")
        q = np.stack(cuantiles)
        salida = pd.DataFrame(claves, columns=["DateTime", "area"])
        for p in PASOS.values():
            salida[f"pred_{p}"], salida[f"q10_{p}"], salida[f"q90_{p}"] = q[:, p - 1, 1], q[:, p - 1, 0], q[:, p - 1, 2]
        return salida


def clasificar(emitido_en, objetivos):
    """El tipo de cada fila según cuándo se emitió frente a su periodo objetivo (fin del periodo, hora de Lima)."""
    inicios = (pd.DatetimeIndex(objetivos) - PASO)
    empieza = inicios.tz_localize(LIMA)
    fin_del_dia = (inicios.normalize() + DIA).tz_localize(LIMA)
    emitido = pd.Timestamp(emitido_en)
    return np.where(emitido < empieza, "ex_ante_estricto", np.where(emitido < fin_del_dia, "en_vivo", "reconstruido"))


def leer_registro(raiz=None):
    r = rutas(raiz)
    if not r.pronosticos.exists():
        return pd.DataFrame(columns=COLUMNAS_REGISTRO)
    return pd.read_parquet(r.pronosticos)


def agregar_al_registro(raiz, nuevas):
    """Agrega filas al registro sin tocar las que ya estaban; las que ya existen (misma clave) no se repiten."""
    r = rutas(raiz)
    previas = leer_registro(r)
    if len(previas):
        hechas = set(previas[CLAVE].itertuples(index=False, name=None))
        nuevas = nuevas[[k not in hechas for k in nuevas[CLAVE].itertuples(index=False, name=None)]]
    nuevas = nuevas.drop_duplicates(CLAVE)
    if nuevas.empty:
        return 0
    todo = pd.concat([previas, nuevas[COLUMNAS_REGISTRO]], ignore_index=True) if len(previas) else nuevas
    try:  # lo ya emitido queda igual, fila por fila (no debería fallar nunca)
        pd.testing.assert_frame_equal(todo.iloc[:len(previas)].reset_index(drop=True), previas.reset_index(drop=True),
                                      check_dtype=False)
    except AssertionError as error:
        raise RuntimeError(f"el registro cambiaría filas ya emitidas: {error}") from error
    _escribir_parquet(r.pronosticos, todo[COLUMNAS_REGISTRO].reset_index(drop=True))
    return len(nuevas)


def emisiones_pendientes(registro, modelo, version, ultimo_dia, desde=ARRANQUE, hasta_objetivo=None):
    """[(horizonte, día objetivo)] que faltan en el registro: 24 h hasta el día siguiente al último dato, 1 h hasta
    el último día con dato."""
    hechas = set()
    if len(registro):
        propias = registro[(registro["modelo"] == modelo) & (registro["version_pesos"] == version)]
        hechas = set(zip(propias["horizonte"], pd.to_datetime(propias["fecha_objetivo"]).dt.date))
    pendientes = []
    for horizonte, ultimo_objetivo in (("24h", ultimo_dia + dt.timedelta(days=1)), ("1h", ultimo_dia)):
        if hasta_objetivo is not None:
            ultimo_objetivo = min(ultimo_objetivo, hasta_objetivo)
        pendientes += [(horizonte, d) for d in _dias(desde, ultimo_objetivo) if (horizonte, d) not in hechas]
    return pendientes


def _version_codigo():
    raiz = Path(__file__).resolve().parents[2]
    try:
        salida = subprocess.run(["git", "-C", str(raiz), "rev-parse", "--short", "HEAD"], check=False,
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return ""
    return salida.stdout.strip()


def emitir(raiz=None, modelo=None, desde=ARRANQUE, hasta_objetivo=None, ahora=_ahora_utc, progreso=print):
    """Emite lo que falte en el registro con los datos que hay y lo agrega. Devuelve cuántas filas agregó.

    Para cada día objetivo X: a 24 h, desde los 48 orígenes del día anterior (datos hasta el fin de X − 1); a 1 h,
    desde los orígenes una hora antes de cada periodo de X (datos hasta el fin de X). El sello `emitido_en` se toma
    después de calcular, justo antes de escribir.
    """
    r = rutas(raiz)
    serie = serie_completa(r)
    modelo = modelo or ChronosAjustado()
    pendientes = emisiones_pendientes(leer_registro(r), modelo.nombre, modelo.version, _ultimo_dia(serie), desde,
                                      hasta_objetivo)
    if not pendientes:
        progreso("Pronóstico: no falta nada por emitir")
        return 0
    progreso(f"Pronóstico: {len(pendientes)} emisiones pendientes, de {min(d for _, d in pendientes)} a "
             f"{max(d for _, d in pendientes)}")
    demanda = serie.set_index("DateTime")[AREAS].asfreq("30min").interpolate(limit_direction="both")
    planes = []
    for horizonte, dia in pendientes:
        objetivos = pd.date_range(pd.Timestamp(dia) + PASO, periods=PERIODOS_DIA, freq="30min")
        datos_hasta = pd.Timestamp(dia) + (pd.Timedelta(0) if horizonte == "24h" else DIA)
        planes.append((horizonte, dia, objetivos, objetivos - PASOS[horizonte] * PASO, datos_hasta))
    origenes = pd.DatetimeIndex(sorted(set().union(*(set(p[3]) for p in planes))))
    pronostico = modelo.pronosticar(demanda, origenes, progreso).set_index(["DateTime", "area"]).sort_index()
    emitido = ahora()
    vivo = cargar_en_vivo(r)
    sha_por_dia = dict(zip(vivo["DateTime"].iloc[::PERIODOS_DIA].dt.normalize(), vivo["sha256"].iloc[::PERIODOS_DIA]))
    version_codigo = _version_codigo()
    filas = []
    for horizonte, dia, objetivos, desde_origen, datos_hasta in planes:
        p = PASOS[horizonte]
        tipo = clasificar(emitido, objetivos)
        for area in AREAS:
            fila = pronostico.reindex(pd.MultiIndex.from_arrays([desde_origen, [area] * PERIODOS_DIA]))
            filas.append(pd.DataFrame({
                "fecha_objetivo": pd.Timestamp(dia), "objetivo": objetivos, "origen": desde_origen, "area": area,
                "horizonte": horizonte, "pred": fila[f"pred_{p}"].to_numpy(dtype=float),
                "q10": fila[f"q10_{p}"].to_numpy(dtype=float), "q90": fila[f"q90_{p}"].to_numpy(dtype=float),
                "modelo": modelo.nombre, "version_pesos": modelo.version, "emitido_en": emitido,
                "datos_hasta": datos_hasta, "datos_sha256": sha_por_dia.get(datos_hasta - DIA),
                "tipo": tipo, "version_codigo": version_codigo,
            }))
    nuevas = pd.concat(filas, ignore_index=True)
    if nuevas[["pred", "q10", "q90"]].isna().any().any():
        raise RuntimeError("el modelo devolvió pronósticos vacíos: no se registra nada")
    agregadas = agregar_al_registro(r, nuevas)
    cuenta = nuevas["tipo"].value_counts().to_dict()
    progreso(f"Pronóstico: {agregadas} filas nuevas en el registro ({cuenta}), emitidas {emitido:%Y-%m-%d %H:%M} UTC")
    return agregadas


# ---- Evaluación ---------------------------------------------------------------------------------------------------


def _metricas(g, refs):
    error = (g["pred"] - g["real"]).to_numpy(dtype=float)
    fila = {"periodos": len(g), "dias": int(g["fecha_objetivo"].nunique()),
            "desde": pd.Timestamp(g["fecha_objetivo"].min()), "hasta": pd.Timestamp(g["fecha_objetivo"].max()),
            "mae_modelo": float(np.abs(error).mean()), "sesgo": float(error.mean()),
            "cobertura_pct": float(100 * g["dentro"].mean())}
    for ref in REFERENCIAS["1h"]:
        fila[f"mae_{ref}"] = float((g[ref] - g["real"]).abs().mean()) if ref in refs else np.nan
    return fila


def resumir(seguimiento):
    """MAE, sesgo y cobertura 10–90 % por día y acumulados, por grupo de tipo, horizonte y área.

    La mejor referencia se elige en el acumulado de cada grupo (la de menor MAE en esas mismas filas) y es la misma
    en sus días. «en_vivo» junta las filas en vivo y las ex ante estrictas; «ex_ante_estricto» las separa.
    """
    filas = []
    for grupo, tipos in GRUPOS.items():
        sub = seguimiento[seguimiento["tipo"].isin(tipos)]
        for (modelo, version, horizonte, area), g in sub.groupby(["modelo", "version_pesos", "horizonte", "area"]):
            refs = REFERENCIAS[horizonte]
            acumulado = _metricas(g, refs)
            mejor = min(refs, key=lambda ref: acumulado[f"mae_{ref}"])
            base = {"grupo": grupo, "modelo": modelo, "version_pesos": version, "horizonte": horizonte, "area": area,
                    "referencia": mejor}
            partes = [("acumulado", pd.NaT, acumulado)]
            partes += [("dia", pd.Timestamp(f), _metricas(gd, refs)) for f, gd in g.groupby("fecha_objetivo")]
            for nivel, fecha, m in partes:
                filas.append({"nivel": nivel, "fecha": fecha, **base, **m, "mae_referencia": m[f"mae_{mejor}"],
                              "mejora_pct": 100 * (1 - m["mae_modelo"] / m[f"mae_{mejor}"])})
    return pd.DataFrame(filas)


def evaluar(raiz=None, progreso=print):
    """Cruza el registro con el real que ya llegó: error por periodo (seguimiento) y por día y acumulado (resumen)."""
    r = rutas(raiz)
    registro = leer_registro(r)
    if registro.empty:
        progreso("Evaluación: el registro está vacío")
        return None, None
    largo = serie_completa(r).set_index("DateTime")[AREAS].stack()

    def valor(fechas, areas):
        return largo.reindex(pd.MultiIndex.from_arrays([pd.DatetimeIndex(fechas), areas])).to_numpy(dtype=float)

    seg = registro.copy()
    seg["real"] = valor(seg["objetivo"], seg["area"])
    seg["persistencia"] = valor(seg["origen"], seg["area"])
    seg["ayer"] = valor(seg["objetivo"] - DIA, seg["area"])
    seg["semana_pasada"] = valor(seg["objetivo"] - 7 * DIA, seg["area"])
    seg = seg[seg["real"].notna()].reset_index(drop=True)
    seg["error"] = seg["pred"] - seg["real"]
    seg["error_abs"] = seg["error"].abs()
    seg["dentro"] = (seg["real"] >= seg["q10"]) & (seg["real"] <= seg["q90"])
    resumen = resumir(seg) if len(seg) else pd.DataFrame()
    _escribir_parquet(r.seguimiento, seg)
    _escribir_parquet(r.resumen, resumen)
    progreso(f"Evaluación: {len(seg):,} periodos con real de {len(registro):,} emitidos")
    return seg, resumen


def tabla_acumulada(resumen, horizonte="24h"):
    """El acumulado de cada grupo y área, en texto, para el log y el informe."""
    if resumen is None or resumen.empty:
        return "sin periodos con real todavía"
    acum = resumen[(resumen["nivel"] == "acumulado") & (resumen["horizonte"] == horizonte)]
    lineas = []
    for f in acum.sort_values(["grupo", "area"]).itertuples():
        lineas.append(f"{horizonte} {f.grupo:<16} {f.area:<6} {f.dias:>2} días · MAE {f.mae_modelo:6.1f} MW · "
                      f"{f.referencia} {f.mae_referencia:6.1f} MW ({f.mejora_pct:+.0f} %) · sesgo {f.sesgo:+6.1f} · "
                      f"cobertura 10–90 {f.cobertura_pct:5.1f} %")
    return "\n".join(lineas)


# ---- Verificación del entorno -------------------------------------------------------------------------------------


def verificar(raiz=None, desde="2026-10-20 00:00", origenes=48, modelo=None, progreso=print):
    """Compara la inferencia de aquí con los pronósticos guardados de Colab (`chronos2ftcal_c2048.parquet`).

    Usa solo la silver histórica, como los experimentos. Devuelve la diferencia máxima en MW por columna.
    """
    r = rutas(raiz)
    guardado = pd.read_parquet(r.raiz / "reportes" / "sein" / "fundacionales" / "chronos2ftcal_c2048.parquet")
    demanda = (pd.read_parquet(r.silver).set_index("DateTime")[AREAS].asfreq("30min")
               .interpolate(limit_direction="both"))
    modelo = modelo or ChronosAjustado()
    nuevo = modelo.pronosticar(demanda, pd.date_range(desde, periods=origenes, freq="30min"), progreso)
    junto = nuevo.merge(guardado, on=["DateTime", "area"], suffixes=("", "_colab"))
    columnas = [c for c in nuevo.columns if c.startswith(("pred_", "q10_", "q90_"))]
    return {c: float((junto[c] - junto[f"{c}_colab"]).abs().max()) for c in columnas} | {"filas": len(junto)}


# ---- Comandos -----------------------------------------------------------------------------------------------------


@contextlib.contextmanager
def _candado(ruta):
    """Una sola corrida a la vez (un cron cada 30 minutos podría pisarse con una corrida lenta)."""
    import fcntl

    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w") as archivo:
        try:
            fcntl.flock(archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(archivo, fcntl.LOCK_UN)


def correr(comando, raiz=None, portal=None, modelo=None, hoy=None, ahora=_ahora_utc, revisar=2, desde=ARRANQUE,
           progreso=None):
    """Corre `diario` (ingesta → pronóstico → evaluación) o `relleno` (lo mismo sin emitir el día de hoy).

    Devuelve el código de salida: 0 si todo salió, `SIN_PUBLICAR` (75) si el anexo de ayer todavía no está o si
    otra corrida está en curso, `INVALIDO` (3) si un anexo no pasa las validaciones y 1 ante cualquier otro error.
    Cada corrida deja una línea en corridas.jsonl con su duración.
    """
    r = rutas(raiz)
    progreso = progreso or log.info
    hoy = hoy or _hoy_lima()
    empezo, inicio_utc = time.monotonic(), _ahora_utc()
    linea = {"comando": comando, "inicio_utc": inicio_utc.isoformat(timespec="seconds"), "hoy_lima": f"{hoy}"}
    with _candado(r.reportes / ".corrida.lock") as libre:
        if not libre:
            progreso("Otra corrida está en curso: se deja para la próxima")
            return SIN_PUBLICAR
        codigo, mensaje = 1, "error inesperado: el detalle queda en el log"  # si algo revienta más abajo
        try:
            ingesta = ingerir(r, hoy=hoy, portal=portal, revisar=revisar, progreso=progreso)
            linea.update({k: ingesta[k] for k in ("peticiones", "bytes")},
                         nuevos=[f"{d}" for d in ingesta["nuevos"]], corregidos=[f"{d}" for d in ingesta["corregidos"]],
                         ultimo_dia=f"{ingesta['ultimo_dia']}")
            hasta = hoy - dt.timedelta(days=1) if comando == "relleno" else None
            linea["filas_emitidas"] = emitir(r, modelo, desde=desde, hasta_objetivo=hasta, ahora=ahora,
                                             progreso=progreso)
            _, resumen = evaluar(r, progreso)
            progreso("Acumulado:\n" + tabla_acumulada(resumen))
            if ingesta["faltante"] is not None:
                codigo, mensaje = SIN_PUBLICAR, str(AnexoNoPublicado(ingesta["faltante"]))
            else:
                codigo, mensaje = 0, f"listo: datos hasta el {ingesta['ultimo_dia']}"
        except AnexoInvalido as error:
            codigo, mensaje = INVALIDO, f"Anexo o serie inválidos, no se emitió nada: {error}"
        finally:  # también si revienta: la corrida queda anotada con su duración y el error sigue su curso
            duracion = time.monotonic() - empezo
            linea.update(codigo=codigo, mensaje=mensaje, duracion_s=round(duracion, 1),
                         fin_utc=_ahora_utc().isoformat(timespec="seconds"))
            _anotar(r.corridas, linea)
            progreso(f"{mensaje} · duración {duracion:.1f} s · código {codigo}")
    return codigo


def _configurar_log(r):
    r.reportes.mkdir(parents=True, exist_ok=True)
    formato = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    for manejador in (logging.FileHandler(r.log, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        manejador.setFormatter(formato)
        log.addHandler(manejador)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m tetouan_power_forecast.en_vivo", description=__doc__.split("\n")[0])
    parser.add_argument("comando", choices=["diario", "relleno", "ingesta", "pronostico", "evaluacion", "verificar"])
    parser.add_argument("--raiz", help="carpeta de datos (por defecto TETOUAN_DATA)")
    parser.add_argument("--pesos", help=f"carpeta de Chronos-2 ajustado (por defecto {PESOS_CHRONOS})")
    parser.add_argument("--revisar", type=int, default=2, help="días anteriores a revisar por correcciones del COES")
    parser.add_argument("--pausa", type=float, default=3.0, help="segundos entre peticiones al COES")
    parser.add_argument("--desde", type=dt.date.fromisoformat, default=ARRANQUE, help="primer día objetivo")
    parser.add_argument("--hoy", type=dt.date.fromisoformat, help="fecha de Lima de la corrida (para pruebas)")
    args = parser.parse_args(argv)
    r = rutas(args.raiz)
    _configurar_log(r)
    try:
        return _ejecutar(args, r)
    except Exception:
        log.exception(f"{args.comando}: la corrida falló")
        raise


def _ejecutar(args, r):
    portal = Portal(pausa=args.pausa)
    modelo = None
    if args.comando in ("diario", "relleno", "pronostico", "verificar"):
        modelo = ChronosAjustado(args.pesos)
    if args.comando in ("diario", "relleno"):
        return correr(args.comando, r, portal=portal, modelo=modelo, hoy=args.hoy, revisar=args.revisar,
                      desde=args.desde)
    if args.comando == "ingesta":
        resultado = ingerir(r, hoy=args.hoy, portal=portal, revisar=args.revisar, progreso=log.info)
        log.info(f"Ingesta: {resultado}")
        return SIN_PUBLICAR if resultado["faltante"] else 0
    if args.comando == "pronostico":
        emitir(r, modelo, desde=args.desde, progreso=log.info)
        return 0
    if args.comando == "evaluacion":
        _, resumen = evaluar(r, log.info)
        log.info("Acumulado:\n" + tabla_acumulada(resumen))
        return 0
    log.info(f"Verificación contra Colab: {verificar(r, modelo=modelo, progreso=log.info)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
