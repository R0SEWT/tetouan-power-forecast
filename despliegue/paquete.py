"""El paquete de datos de la app en producción: solo los archivos que la API lee de verdad.

**Cómo se midió.** Con la carpeta de datos completa (675 MB) y ``TPF_PRONOSTICADOR=real``, se levantó la API bajo
``strace -f -e trace=openat`` y se recorrieron todos sus endpoints: las tres áreas, los tres modelos (combinado, base e
híbrido), los dos horizontes, todas las variantes, escenarios, sensibilidad, «Ahora» en vivo y en repaso, «Confianza»
y la web (193 pedidos, todos 200). Estos son todos los archivos de la carpeta de datos que el proceso abrió. Lo demás
(los pesos de Chronos-2, que solo usa la corrida diaria; el bronze; las otras capas y reportes) no hace falta.

El paquete conserva las rutas relativas de la carpeta de datos: en el contenedor, la carpeta donde se baja es
``TETOUAN_DATA`` tal cual. Los modelos (``.joblib``) se guardan comprimidos con xz, que ``joblib.load`` reconoce solo:
pesan un tercio y la app los lee igual. Solo usa la biblioteca estándar, así que se arma sin el entorno del proyecto.

    python -m despliegue.paquete ../tetouan-power-forecast/data /tmp/paquete   # arma el paquete y lo verifica
"""

from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

# Lo que la API abre al arrancar y al responder (medido; ver el docstring). Los modelos de la app salen de
# ``modelos/sein/app/metadatos.json`` (uno por horizonte y variante), así que no se listan aquí.
ESTATICOS: tuple[str, ...] = (
    "coes/silver/demanda_areas.parquet",
    "exogenas/silver/eventos_coes.parquet",
    "exogenas/silver/icen.parquet",
    "exogenas/silver/nino12_semanal.parquet",
    "exogenas/silver/temperatura_areas.parquet",
    "modelos/sein/app/metadatos.json",
    "modelos/sein/fundacionales/combinado.json",
    "modelos/sein/fundacionales/xgb_simons_1h.joblib",
    "modelos/sein/fundacionales/xgb_simons_24h.joblib",
    "reportes/sein/fundacionales/chronos2ftcal_c2048.parquet",
    "reportes/sein/fundacionales/simons_c2048.parquet",
    "reportes/sein/prueba_2026/adaptacion.csv",
)
METADATOS_APP = "modelos/sein/app/metadatos.json"
# Opcionales: sin ellos la app arranca con el modelo base (sin híbrido ni combinado) o sin la tabla del notebook 03
OPCIONALES = frozenset({
    "modelos/sein/fundacionales/combinado.json",
    "modelos/sein/fundacionales/xgb_simons_1h.joblib",
    "modelos/sein/fundacionales/xgb_simons_24h.joblib",
    "reportes/sein/fundacionales/chronos2ftcal_c2048.parquet",
    "reportes/sein/fundacionales/simons_c2048.parquet",
    "reportes/sein/prueba_2026/adaptacion.csv",
})
# El registro de la corrida diaria en vivo: cambia cada mañana y se sube aparte (``actualizar_hf.py``). La demanda en
# vivo (``coes/silver/demanda_areas_en_vivo.parquet``) no va: la API no la lee; el real de los días en vivo viene en
# ``seguimiento.parquet``.
EN_VIVO: tuple[str, ...] = (
    "reportes/sein/en_vivo/pronosticos.parquet",
    "reportes/sein/en_vivo/seguimiento.parquet",
    "reportes/sein/en_vivo/resumen.parquet",
)
MANIFIESTO = "MANIFIESTO.json"
VERSION = 1
PRESET_XZ = 6
BLOQUE = 1 << 20


class ErrorPaquete(RuntimeError):
    """Faltan archivos o no coinciden con el manifiesto."""


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(BLOQUE), b""):
            h.update(bloque)
    return h.hexdigest()


def archivos_estaticos(origen: Path) -> list[str]:
    """Los estáticos que hay que llevar: la lista fija más un modelo por cada horizonte y variante de la app."""
    ruta_meta = origen / METADATOS_APP
    if not ruta_meta.exists():
        raise ErrorPaquete(f"No están los modelos de la app en {ruta_meta.parent}: sin ellos no hay modelo real.")
    claves = json.loads(ruta_meta.read_text())["columnas"]
    modelos = [f"modelos/sein/app/xgboost_global_{clave}.joblib" for clave in claves]
    return sorted({*ESTATICOS, *modelos})


def _comprime(ruta: str) -> bool:
    return ruta.endswith(".joblib")


def _escribir(origen: Path, destino: Path, comprimir: bool) -> None:
    """Copia (o comprime con xz) de una vez: quien lea ``destino`` nunca ve un archivo a medias."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_name(destino.name + ".tmp")
    if comprimir:
        with open(origen, "rb") as entrada, lzma.open(temporal, "wb", preset=PRESET_XZ) as salida:
            shutil.copyfileobj(entrada, salida, BLOQUE)
    else:
        shutil.copyfile(origen, temporal)
    temporal.replace(destino)


def _leer_manifiesto(carpeta: Path) -> dict | None:
    ruta = carpeta / MANIFIESTO
    try:
        return json.loads(ruta.read_text())
    except (OSError, ValueError):
        return None


def armar_paquete(origen: Path, destino: Path, comprimir: bool = True, progreso=print) -> dict:
    """Arma en ``destino`` el paquete de datos de la app a partir de la carpeta de datos ``origen``.

    Escribe los archivos con sus rutas relativas, ``MANIFIESTO.json`` (bytes y sha256 de cada estático y del archivo
    original del que sale) y ``README.md`` (la ficha del dataset). Si ``destino`` ya tiene un paquete armado con los
    mismos originales, no vuelve a comprimirlos. Devuelve el manifiesto.
    """
    origen, destino = Path(origen), Path(destino)
    estaticos = archivos_estaticos(origen)
    faltan = [r for r in estaticos if not (origen / r).exists() and r not in OPCIONALES]
    if faltan:
        raise ErrorPaquete(f"Faltan en {origen}: {', '.join(faltan)}")
    previo = (_leer_manifiesto(destino) or {}).get("archivos", {})
    destino.mkdir(parents=True, exist_ok=True)
    archivos, omitidos = {}, []
    for ruta in estaticos:
        fuente = origen / ruta
        if not fuente.exists():
            omitidos.append(ruta)
            continue
        huella_origen = sha256(fuente)
        comprimido = comprimir and _comprime(ruta)
        anterior = previo.get(ruta, {})
        if not (anterior.get("sha256_origen") == huella_origen and anterior.get("xz", False) == comprimido
                and (destino / ruta).exists() and sha256(destino / ruta) == anterior.get("sha256")):
            progreso(f"  {'comprime' if comprimido else 'copia'} {ruta}")
            _escribir(fuente, destino / ruta, comprimido)
        archivos[ruta] = {"bytes": (destino / ruta).stat().st_size, "sha256": sha256(destino / ruta),
                          "bytes_origen": fuente.stat().st_size, "sha256_origen": huella_origen, "xz": comprimido}
    en_vivo = []
    for ruta in EN_VIVO:
        if (origen / ruta).exists():
            _escribir(origen / ruta, destino / ruta, comprimir=False)
            en_vivo.append(ruta)
        else:
            progreso(f"  aviso: no está {ruta}; la app arranca sin el registro en vivo")
    manifiesto = {
        "version": VERSION,
        "generado": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "archivos": archivos,
        "en_vivo": en_vivo,
        "omitidos": omitidos,
    }
    # La fecha cambia en cada corrida; si lo demás no cambió, se conserva la anterior (subir de nuevo no hace commit)
    anterior = _leer_manifiesto(destino)
    if anterior and {k: v for k, v in anterior.items() if k != "generado"} == {
            k: v for k, v in manifiesto.items() if k != "generado"}:
        manifiesto["generado"] = anterior["generado"]
    (destino / MANIFIESTO).write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2) + "\n")
    (destino / "README.md").write_text(ficha_dataset(manifiesto, destino))
    return manifiesto


def verificar(carpeta: Path, completo: bool = True) -> list[str]:
    """Los problemas del paquete en ``carpeta`` frente a su manifiesto (vacío si está bien).

    Con ``completo``, compara también el sha256 de cada archivo; si no, solo que estén y que pesen lo mismo.
    """
    carpeta = Path(carpeta)
    manifiesto = _leer_manifiesto(carpeta)
    if manifiesto is None:
        return [f"no hay {MANIFIESTO} legible en {carpeta}"]
    if manifiesto.get("version") != VERSION:
        return [f"{MANIFIESTO} es de la versión {manifiesto.get('version')}; esta app lee la {VERSION}"]
    problemas = []
    for ruta, datos in manifiesto.get("archivos", {}).items():
        archivo = carpeta / ruta
        if not archivo.exists():
            problemas.append(f"falta {ruta}")
        elif archivo.stat().st_size != datos["bytes"]:
            problemas.append(f"{ruta} pesa {archivo.stat().st_size} bytes y el manifiesto dice {datos['bytes']}")
        elif completo and sha256(archivo) != datos["sha256"]:
            problemas.append(f"{ruta} no coincide con su sha256")
    if METADATOS_APP not in manifiesto.get("archivos", {}):
        problemas.append(f"el manifiesto no trae {METADATOS_APP}")
    return problemas


def peso(manifiesto: dict, carpeta: Path | None = None) -> tuple[int, int]:
    """Bytes del paquete (estáticos más registro en vivo) y bytes de los originales."""
    paquete = sum(d["bytes"] for d in manifiesto["archivos"].values())
    originales = sum(d["bytes_origen"] for d in manifiesto["archivos"].values())
    if carpeta is not None:
        vivo = sum((Path(carpeta) / r).stat().st_size for r in manifiesto.get("en_vivo", [])
                   if (Path(carpeta) / r).exists())
        paquete, originales = paquete + vivo, originales + vivo
    return paquete, originales


def mb(n: int) -> str:
    return f"{n / 1e6:.1f} MB"


def ficha_dataset(manifiesto: dict, carpeta: Path) -> str:
    """La ficha (README.md) del dataset en el Hub."""
    paquete, originales = peso(manifiesto, carpeta)
    filas = "\n".join(f"| `{r}` | {mb(d['bytes'])} |" for r, d in sorted(manifiesto["archivos"].items()))
    vivo = "\n".join(f"| `{r}` | {mb((carpeta / r).stat().st_size)} |" for r in manifiesto.get("en_vivo", []))
    return f"""---
pretty_name: Curva, datos de la app
tags:
- time-series
- electricity
---

# Curva: datos de la app en producción

El paquete mínimo que necesita la app Curva (pronóstico de la demanda eléctrica del SEIN peruano por área) para servir
el modelo real. Lo baja el Space al arrancar; lo arma `despliegue/paquete.py` del repositorio del proyecto.

- **Peso:** {mb(paquete)} (los originales pesan {mb(originales)}; los modelos van comprimidos con xz).
- **Generado:** {manifiesto['generado']}.
- **Fuente de la demanda:** la demanda por área que publica el COES en el IEOD. Las exógenas: ERA5 (temperatura),
  ENFEN (ICEN), NOAA (Niño 1+2) y los eventos del COES.

| Archivo | Peso |
|---|---|
{filas}

Registro de la corrida diaria en vivo (se actualiza cada mañana con `despliegue/actualizar_hf.py`):

| Archivo | Peso |
|---|---|
{vivo}

`MANIFIESTO.json` trae el sha256 de cada archivo; el Space lo verifica antes de usar los datos.
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Arma y verifica el paquete de datos de la app.")
    parser.add_argument("origen", type=Path, nargs="?", default=Path(os.environ.get("TETOUAN_DATA", "data")),
                        help="carpeta de datos completa (por defecto, TETOUAN_DATA)")
    parser.add_argument("destino", type=Path, nargs="?", help="carpeta del paquete (por defecto, una temporal)")
    parser.add_argument("--sin-comprimir", action="store_true", help="copia los modelos tal cual")
    args = parser.parse_args(argv)
    destino = args.destino or Path(tempfile.mkdtemp(prefix="curva-paquete-"))
    try:
        manifiesto = armar_paquete(args.origen, destino, comprimir=not args.sin_comprimir)
    except ErrorPaquete as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    problemas = verificar(destino)
    paquete, originales = peso(manifiesto, destino)
    print(f"Paquete en {destino}: {mb(paquete)} (originales: {mb(originales)}), "
          f"{len(manifiesto['archivos'])} archivos estáticos y {len(manifiesto['en_vivo'])} del registro en vivo.")
    for problema in problemas:
        print(f"  problema: {problema}", file=sys.stderr)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
