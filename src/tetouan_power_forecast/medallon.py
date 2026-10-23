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
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from tetouan_power_forecast.datos import ZONAS, construir_dataset, cortes_particion, limpiar

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


def raiz_datos(raiz=None):
    return Path(raiz or os.environ.get("TETOUAN_DATA", "data"))


def _ruta(raiz, capa, nombre):
    ruta = raiz_datos(raiz) / capa / nombre
    ruta.parent.mkdir(parents=True, exist_ok=True)
    return ruta


def _descargar(url, timeout=600):
    with urllib.request.urlopen(url, timeout=timeout) as respuesta:
        return respuesta.read()


def bronze(raiz=None, forzar=False, descargar=_descargar):
    """Guarda el CSV de UCI sin tocarlo y su procedencia. Devuelve la ruta del CSV."""
    csv = _ruta(raiz, "bronze", "uci849_tetouan.csv")
    if csv.exists() and not forzar:
        return csv
    contenido = descargar(FUENTE["url"])
    csv.write_bytes(contenido)
    procedencia = {
        **FUENTE,
        "descargado_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "bytes": len(contenido),
        "sha256": hashlib.sha256(contenido).hexdigest(),
    }
    csv.with_suffix(".json").write_text(json.dumps(procedencia, ensure_ascii=False, indent=2) + "\n")
    return csv


def auditar(df):
    """Chequeos de calidad del silver. Devuelve una tabla con chequeo, ok y detalle."""
    intervalos = df["DateTime"].diff().dropna()
    chequeos = [
        ("Columnas esperadas", list(df.columns) == COLUMNAS, f"{len(df.columns)} columnas"),
        ("Sin valores faltantes", not df.isnull().any().any(), f"{int(df.isnull().sum().sum())} nulos"),
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
    df.to_parquet(destino, index=False)
    return destino


def gold(raiz=None, zona=1, forzar=False):
    """Construye el dataset t+6 de la zona y marca la partición cronológica."""
    destino = _ruta(raiz, "gold", f"t6_zona{zona}.parquet")
    if destino.exists() and not forzar:
        return destino
    df = construir_dataset(pd.read_parquet(silver(raiz)), zona=zona)
    fin_train, fin_val = cortes_particion(len(df))
    df["particion"] = pd.Categorical(
        [PARTICIONES[0]] * fin_train + [PARTICIONES[1]] * (fin_val - fin_train)
        + [PARTICIONES[2]] * (len(df) - fin_val),
        categories=PARTICIONES,
    )
    df.to_parquet(destino, index=False)
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
