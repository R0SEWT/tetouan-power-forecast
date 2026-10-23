"""Pipeline bronze → silver → gold del dataset de UCI.

- bronze: el CSV tal como lo entrega UCI, más su procedencia (URL, DOI, licencia, fecha, sha256).
- silver: columnas normalizadas, DateTime como fecha, orden cronológico y una auditoría de calidad
  que corta el pipeline si algo no cuadra.
- gold: el dataset t+6 de una zona, con la partición cronológica 70/15/15 marcada en `particion`.

Cada capa se guarda en data/<capa>/ y se reutiliza si ya existe: UCI tarda minutos en servir el CSV.
"""

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from tetouan_power_forecast.datos import ZONAS, construir_dataset, cortes_particion, limpiar
from tetouan_power_forecast.metricas import HORIZONTE

FUENTE = {
    "dataset": "Power Consumption of Tetouan City",
    "uci_id": 849,
    "url": "https://archive.ics.uci.edu/static/public/849/data.csv",
    "pagina": "https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city",
    "doi": "10.24432/C5B034",
    "licencia": "CC BY 4.0",
    "origen": "SCADA de Amendis, operador de distribución eléctrica de Tetuán (según la descripción "
    "del dataset en Kaggle; UCI no lo detalla)",
}
COLUMNAS = ["DateTime", "Temperature", "Humidity", "Wind Speed", "general diffuse flows",
            "diffuse flows", *ZONAS]
# Periodo que cubre el dataset de UCI: un registro cada 10 minutos (el 31 de diciembre no viene)
COBERTURA = ("2017-01-01 00:00", "2017-12-30 23:50")
# Rangos físicos posibles, no "normales": fuera de ellos el dato es un error de captura.
# Además, el consumo de cada zona tiene que ser estrictamente positivo.
RANGOS = {
    "Temperature": (-10, 50),
    "Humidity": (0, 100),
    "Wind Speed": (0, None),
    "general diffuse flows": (0, None),
    "diffuse flows": (0, None),
}
PARTICIONES = ("entrenamiento", "validacion", "prueba")
# Filas cuyo objetivo (t+6) cae en la partición siguiente: no se usan ni para entrenar ni para evaluar
HUECO = "hueco"
# Dentro de "Mi unidad": la carpeta original y el acceso directo que crea quien la recibe compartida
CARPETAS_DRIVE = ("datalake/tetouan-power-forecast", "tetouan-power-forecast")
CSV_BRONZE = "uci849_tetouan.csv"


def raiz_datos(raiz=None):
    return Path(raiz or os.environ.get("TETOUAN_DATA", "data"))


def usar_drive(carpeta=None, montaje="/content/drive"):
    """En Colab: monta Google Drive y deja ahí las capas del medallón.

    Entre las carpetas de CARPETAS_DRIVE (o `carpeta`, si se pasa) prefiere la que ya tiene el bronze,
    así una carpeta personal vacía no tapa a la compartida. La guarda en TETOUAN_DATA para que bronze,
    silver, gold y cargar_gold la usen sin tener que pasarla.
    """
    try:
        from google.colab import drive
    except ImportError as error:
        raise RuntimeError(
            "usar_drive() solo funciona en Colab; en local, baja las capas con rclone (docs/datos.md)"
        ) from error
    drive.mount(montaje)
    mi_unidad = Path(montaje) / "MyDrive"
    candidatas = [mi_unidad / c for c in ([carpeta] if carpeta else CARPETAS_DRIVE)]
    con_bronze = [c for c in candidatas if (c / "bronze" / CSV_BRONZE).is_file()]
    existentes = [c for c in candidatas if c.is_dir()]
    raiz = (con_bronze or existentes or candidatas)[0]
    print(f"Capas del medallón en: Mi unidad/{raiz.relative_to(mi_unidad)}")
    os.environ["TETOUAN_DATA"] = str(raiz)
    return raiz


def _ruta(raiz, capa, nombre):
    ruta = raiz_datos(raiz) / capa / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


def _reemplazar(ruta, escribir):
    """Escribe en un archivo temporal y lo mueve al final: una corrida cortada no deja una capa a medias."""
    temporal = ruta.with_name(f".{ruta.name}.tmp")
    escribir(temporal)
    os.replace(temporal, ruta)


def _descargar(url, timeout=600, intentos=3, espera=10):
    """Descarga con reintentos: UCI es lento y a veces corta la conexión."""
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as respuesta:
                return respuesta.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if intento == intentos:
                raise
            time.sleep(espera * intento)


def _sha256(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def bronze(raiz=None, forzar=False, descargar=_descargar):
    """Guarda el CSV de UCI sin tocarlo y su procedencia. Devuelve la ruta del CSV.

    Si ya existe, lo reutiliza solo después de comprobar que coincide con el sha256 de su procedencia.
    """
    csv = _ruta(raiz, "bronze", CSV_BRONZE)
    procedencia_json = csv.with_suffix(".json")
    if csv.exists() and procedencia_json.exists() and not forzar:
        esperado = json.loads(procedencia_json.read_text())["sha256"]
        if _sha256(csv) != esperado:
            raise ValueError(f"{csv} no coincide con el sha256 de su procedencia; rehazlo con forzar=True")
        return csv
    contenido = descargar(FUENTE["url"])
    procedencia = {
        **FUENTE,
        "descargado_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "bytes": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }
    _reemplazar(csv, lambda ruta: ruta.write_bytes(contenido))
    texto = json.dumps(procedencia, ensure_ascii=False, indent=2) + "\n"
    _reemplazar(procedencia_json, lambda ruta: ruta.write_text(texto))
    return csv


def auditar(df, cobertura=None):
    """Chequeos de calidad del silver. Devuelve una tabla con chequeo, ok y detalle."""
    inicio, fin = map(pd.Timestamp, cobertura or COBERTURA)
    esperados = len(pd.date_range(inicio, fin, freq="10min"))
    numericas = df.select_dtypes("number")
    intervalos = df["DateTime"].diff().dropna()
    chequeos = [
        ("Columnas esperadas", list(df.columns) == COLUMNAS, f"{len(df.columns)} columnas"),
        ("Cubre el periodo esperado", len(df) == esperados and len(df) > 0
         and df["DateTime"].min() == inicio and df["DateTime"].max() == fin,
         f"{len(df):,} registros de {esperados:,} esperados ({inicio:%d/%m/%Y %H:%M} a {fin:%d/%m/%Y %H:%M})"),
        ("Sin valores faltantes", not df.isnull().any().any(), f"{int(df.isnull().sum().sum())} nulos"),
        ("Sin valores infinitos", not np.isinf(numericas).any().any(),
         f"{int(np.isinf(numericas).sum().sum())} infinitos"),
        ("Sin filas duplicadas", not df.duplicated().any(), f"{int(df.duplicated().sum())} duplicadas"),
        ("Sin fechas repetidas", not df["DateTime"].duplicated().any(),
         f"{int(df['DateTime'].duplicated().sum())} repetidas"),
        ("Un registro cada 10 minutos, sin huecos", bool((intervalos == pd.Timedelta("10min")).all()),
         f"{int((intervalos != pd.Timedelta('10min')).sum())} intervalos distintos de 10 min"),
    ]
    for columna, (minimo, maximo) in RANGOS.items():
        fuera = df[columna] < minimo
        if maximo is not None:
            fuera |= df[columna] > maximo
        limite = f">= {minimo}" if maximo is None else f"entre {minimo} y {maximo}"
        chequeos.append((f"{columna} {limite}", not fuera.any(), f"{int(fuera.sum())} fuera de rango"))
    for columna in ZONAS:
        fuera = df[columna] <= 0
        chequeos.append((f"{columna} > 0", not fuera.any(), f"{int(fuera.sum())} fuera de rango"))
    return pd.DataFrame(chequeos, columns=["chequeo", "ok", "detalle"])


def silver(raiz=None, forzar=False):
    """Limpia el bronze, lo audita y guarda el silver. Falla si algún chequeo no pasa."""
    destino = _ruta(raiz, "silver", "tetouan_2017.parquet")
    if destino.exists() and not forzar:
        return destino
    df = limpiar(pd.read_csv(bronze(raiz)))
    auditoria = auditar(df)
    reporte = [
        "# Auditoría del silver",
        "",
        f"Registros: {len(df):,} · desde {df['DateTime'].min()} hasta {df['DateTime'].max()}",
        "",
        "| Chequeo | Resultado | Detalle |",
        "|---|---|---|",
        *(f"| {c} | {'ok' if ok else 'FALLA'} | {d} |" for c, ok, d in auditoria.itertuples(index=False)),
    ]
    destino.with_name("auditoria.md").write_text("\n".join(reporte) + "\n")
    if not auditoria["ok"].all():
        fallas = auditoria.loc[~auditoria["ok"], "chequeo"].tolist()
        raise ValueError(f"El silver no pasa la auditoría: {fallas}. Ver {destino.with_name('auditoria.md')}")
    _reemplazar(destino, lambda ruta: df.to_parquet(ruta, index=False))
    return destino


def etiquetas_particion(n):
    """Partición cronológica 70/15/15 de n filas, con un hueco de HORIZONTE filas antes de cada corte.

    El objetivo de una fila está HORIZONTE periodos adelante: en las últimas HORIZONTE filas de
    entrenamiento y de validación cae en la partición siguiente, así que esas filas quedan fuera.
    """
    fin_train, fin_val = cortes_particion(n)
    etiquetas = np.array([PARTICIONES[0]] * fin_train + [PARTICIONES[1]] * (fin_val - fin_train)
                         + [PARTICIONES[2]] * (n - fin_val), dtype=object)
    for fin in (fin_train, fin_val):
        etiquetas[fin - HORIZONTE:fin] = HUECO
    return pd.Categorical(etiquetas, categories=[PARTICIONES[0], HUECO, *PARTICIONES[1:]])


def gold(raiz=None, zona=1, forzar=False):
    """Construye el dataset t+6 de la zona y marca la partición cronológica."""
    destino = _ruta(raiz, "gold", f"t6_zona{zona}.parquet")
    if destino.exists() and not forzar:
        return destino
    df = construir_dataset(pd.read_parquet(silver(raiz)), zona=zona)
    df["particion"] = etiquetas_particion(len(df))
    _reemplazar(destino, lambda ruta: df.to_parquet(ruta, index=False))
    return destino


def cargar_silver(raiz=None):
    return pd.read_parquet(silver(raiz))


def cargar_gold(zona=1, raiz=None):
    """El dataset listo para modelar; construye las capas que falten."""
    return pd.read_parquet(gold(raiz, zona=zona))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tetouan", description=__doc__.splitlines()[0])
    parser.add_argument("capa", choices=["bronze", "silver", "gold", "all"])
    parser.add_argument("--zona", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--raiz", help="carpeta de datos (por defecto, $TETOUAN_DATA o ./data)")
    parser.add_argument("--forzar", action="store_true", help="rehace la capa aunque ya exista")
    args = parser.parse_args(argv)

    if args.capa in ("bronze", "all"):
        print(bronze(args.raiz, forzar=args.forzar))
    if args.capa in ("silver", "all"):
        print(silver(args.raiz, forzar=args.forzar))
    if args.capa in ("gold", "all"):
        print(gold(args.raiz, zona=args.zona, forzar=args.forzar))


if __name__ == "__main__":
    main()
