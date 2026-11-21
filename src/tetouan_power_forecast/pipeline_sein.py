"""El pipeline del SEIN en una sola llamada: de la carpeta de datos a los datasets listos para modelar.

    from tetouan_power_forecast.pipeline_sein import pipeline_sein
    resultado = pipeline_sein("ruta/a/los/datos")  # None: $TETOUAN_DATA o ./data
    resultado.datasets["24h"]["global"]            # el dataset del modelo global a 24 h

o desde la consola: ``python -m tetouan_power_forecast.pipeline_sein --raiz <carpeta> [--hasta AAAA-MM-DD] [--guardar]``.

Hace, en orden, los mismos pasos que los notebooks 01 a 03 del SEIN:

1. **Cargar** las capas silver de la carpeta: la demanda por área del IEOD y las exógenas (temperatura de ERA5, ICEN,
   Niño 1+2 y eventos del COES), con el sha256 de cada archivo. Si falta una, corta y dice cuál.
2. **Validar** la demanda: las columnas, que no haya marcas de tiempo repetidas, cuántos periodos de 30 minutos faltan,
   cuántos valores no son positivos y cuánto se aparta Norte + Centro + Sur del SEIN. Corta solo si falta una columna
   o hay fechas repetidas (romperían los rezagos); lo demás lo reporta, como la auditoría del silver.
3. **Recortar** a una fecha de corte opcional (`hasta`), para reproducir una corrida con los datos que había entonces.
4. **Feriados** del Perú de los años que cubre la demanda (paquete `holidays`; sin él, quedan en cero y lo avisa).
5. **Armar los datasets** de cada horizonte con `preparar_datasets`: variables en razón con la regla de información,
   partición (entrenamiento 2016-2024, validación 2025 y prueba 2026, con un hueco de H pasos antes de cada corte) y
   solo las filas completas para M0 a M3, por área y global.
6. **Verificar la regla de información** en una muestra: la temperatura de t es la última hora ya publicada.
7. **Procedencia**: versión del pipeline y del paquete, ruta, sha256 de las capas y filas por partición. `guardar` la
   escribe junto a los datasets en ``gold/sein/<VERSION>/``.

`VERSION` sube cuando cambia lo que sale (variables, partición o regla de información), no cuando cambian los datos:
dos corridas con la misma versión y el mismo sha256 de las capas dan los mismos datasets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from tetouan_power_forecast.medallon import raiz_datos
from tetouan_power_forecast.modelado_sein import VARIANTES_ABLACION, preparar_datasets
from tetouan_power_forecast.variables_sein import AREAS, HORIZONTES, PASO

VERSION = "v1"
CAPAS = {
    "demanda": "coes/silver/demanda_areas.parquet",
    "temperatura": "exogenas/silver/temperatura_areas.parquet",
    "icen": "exogenas/silver/icen.parquet",
    "nino12": "exogenas/silver/nino12_semanal.parquet",
    "eventos": "exogenas/silver/eventos_coes.parquet",
}
COLUMNAS_DEMANDA = ["DateTime", "SEIN", *AREAS]


@dataclass
class ResultadoPipeline:
    """Lo que devuelve `pipeline_sein`: los datasets por horizonte, las capas de entrada y su procedencia."""

    datasets: dict  # {"1h": {"locales": {"NORTE": df, ...}, "global": df}, "24h": {...}}
    demanda: pd.DataFrame
    exogenas: dict
    feriados: list
    procedencia: dict = field(default_factory=dict)


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _version_paquete() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("tetouan-power-forecast")
    except PackageNotFoundError:  # corre desde el código fuente, sin instalar
        return "sin instalar"


def cargar_capas_sein(raiz=None) -> tuple[pd.DataFrame, dict, dict]:
    """Las capas silver del SEIN de la carpeta `raiz`: la demanda, las exógenas y el sha256 de cada archivo."""
    carpeta = raiz_datos(raiz)
    faltan = [ruta for ruta in CAPAS.values() if not (carpeta / ruta).exists()]
    if faltan:
        raise FileNotFoundError(f"Faltan capas en {carpeta}: {', '.join(faltan)}. Ármalas con 00_medallon_coes y "
                                "00c_exogenas.")
    tablas = {nombre: pd.read_parquet(carpeta / ruta) for nombre, ruta in CAPAS.items()}
    huellas = {nombre: _sha256(carpeta / ruta) for nombre, ruta in CAPAS.items()}
    demanda = tablas.pop("demanda")
    return demanda, tablas, huellas


def validar_demanda(demanda: pd.DataFrame) -> dict:
    """Chequea la demanda antes de armar las variables. Corta si falta una columna o hay fechas repetidas."""
    faltan = [c for c in COLUMNAS_DEMANDA if c not in demanda.columns]
    if faltan:
        raise ValueError(f"A la demanda le faltan columnas: {faltan}")
    fechas = pd.to_datetime(demanda["DateTime"])
    repetidas = int(fechas.duplicated().sum())
    if repetidas:
        raise ValueError(f"La demanda tiene {repetidas} marcas de tiempo repetidas: los rezagos quedarían corridos")
    esperados = len(pd.date_range(fechas.min(), fechas.max(), freq=PASO))
    suma = demanda[AREAS].sum(axis=1, min_count=len(AREAS))
    return {
        "periodos": len(demanda),
        "desde": str(fechas.min()),
        "hasta": str(fechas.max()),
        "periodos_faltantes": esperados - len(demanda),
        "valores_vacios": {a: int(demanda[a].isna().sum()) for a in AREAS},
        "no_positivos": int((demanda[AREAS] <= 0).any(axis=1).sum()),
        "desvio_max_areas_vs_sein_mw": round(float((suma - demanda["SEIN"]).abs().max()), 3),
    }


def feriados_peru(desde: int, hasta: int) -> list:
    """Los feriados nacionales del Perú de `desde` a `hasta` (inclusive). Sin el paquete `holidays`, ninguno."""
    try:
        import holidays
    except ImportError:
        warnings.warn("Falta el paquete holidays: los feriados quedan en cero y el modelo no los ve.", stacklevel=2)
        return []
    return sorted(holidays.PE(years=range(desde, hasta + 1)))


def verificar_regla_de_informacion(datos: pd.DataFrame, temperatura: pd.DataFrame, area: str, n=200, semilla=0):
    """La temperatura de cada fila tiene que ser la última hora ya publicada en t, nunca una posterior."""
    con_temp = datos.dropna(subset=["temp"])
    if con_temp.empty:
        return 0
    muestra = con_temp.sample(min(n, len(con_temp)), random_state=semilla)
    horaria = temperatura.set_index("fecha_hora")[area.lower()].sort_index().dropna()
    esperada = horaria.reindex(pd.DatetimeIndex(muestra["DateTime"]), method="ffill").to_numpy()
    if not np.allclose(muestra["temp"].to_numpy(), esperada):
        raise AssertionError(f"Regla de información rota en {area}: la temperatura de t no es la última publicada")
    return len(muestra)


def pipeline_sein(raiz=None, horizontes=tuple(HORIZONTES), variantes=tuple(VARIANTES_ABLACION), hasta=None,
                  verificar=True) -> ResultadoPipeline:
    """De la carpeta de datos `raiz` a los datasets del SEIN listos para modelar, con su procedencia.

    `horizontes` son claves de `HORIZONTES` ("1h", "24h"); `hasta` recorta la demanda a esa fecha (inclusive) para
    reproducir una corrida pasada. Ver los pasos en el docstring del módulo.
    """
    demanda, exogenas, huellas = cargar_capas_sein(raiz)
    if hasta is not None and "DateTime" in demanda.columns:
        demanda = demanda[pd.to_datetime(demanda["DateTime"]) <= pd.Timestamp(hasta)]
    calidad = validar_demanda(demanda)  # la de lo que entra al modelo, ya recortado
    demanda = demanda.sort_values("DateTime").reset_index(drop=True)
    anios = demanda["DateTime"].dt.year
    feriados = feriados_peru(int(anios.min()), int(anios.max()) + 1)

    datasets, filas = {}, {}
    for nombre_h in horizontes:
        locales, global_ = preparar_datasets(demanda, HORIZONTES[nombre_h], variantes=list(variantes),
                                             feriados=feriados, **exogenas)
        datasets[nombre_h] = {"locales": locales, "global": global_}
        filas[nombre_h] = {a: locales[a]["particion"].value_counts().to_dict() for a in AREAS}
        if verificar:
            for a in AREAS:
                verificar_regla_de_informacion(locales[a], exogenas["temperatura"], a)

    procedencia = {
        "version_pipeline": VERSION,
        "version_paquete": _version_paquete(),
        "ejecutado": datetime.now(UTC).isoformat(timespec="seconds"),
        "raiz": str(raiz_datos(raiz).resolve()),
        "hasta": None if hasta is None else str(pd.Timestamp(hasta)),
        "capas": {nombre: {"ruta": CAPAS[nombre], "sha256": huella} for nombre, huella in huellas.items()},
        "calidad_demanda": calidad,
        "feriados": len(feriados),
        "variantes": list(variantes),
        "filas_por_particion": filas,
        "regla_de_informacion_verificada": bool(verificar),
    }
    return ResultadoPipeline(datasets, demanda, exogenas, feriados, procedencia)


def guardar(resultado: ResultadoPipeline, destino=None) -> Path:
    """Escribe los datasets y la procedencia en ``destino`` (por defecto, ``<raiz>/gold/sein/<VERSION>/``)."""
    carpeta = Path(destino) if destino else Path(resultado.procedencia["raiz"]) / "gold" / "sein" / VERSION
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre_h, partes in resultado.datasets.items():
        partes["global"].to_parquet(carpeta / f"{nombre_h}_global.parquet", index=False)
        for area, datos in partes["locales"].items():
            datos.to_parquet(carpeta / f"{nombre_h}_{area.lower()}.parquet", index=False)
    (carpeta / "procedencia.json").write_text(json.dumps(resultado.procedencia, ensure_ascii=False, indent=2,
                                                        default=str))
    return carpeta


def main(argv=None):
    parser = argparse.ArgumentParser(description="Pipeline del SEIN: de las capas silver a los datasets")
    parser.add_argument("--raiz", help="carpeta de datos (por defecto, $TETOUAN_DATA o ./data)")
    parser.add_argument("--hasta", help="fecha de corte de la demanda, para reproducir una corrida pasada")
    parser.add_argument("--guardar", action="store_true", help=f"escribe los datasets en gold/sein/{VERSION}/")
    args = parser.parse_args(argv)
    resultado = pipeline_sein(args.raiz, hasta=args.hasta)
    print(json.dumps(resultado.procedencia, ensure_ascii=False, indent=2, default=str))
    if args.guardar:
        print("Datasets en", guardar(resultado))
    return 0


if __name__ == "__main__":
    sys.exit(main())
