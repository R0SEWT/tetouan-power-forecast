#!/usr/bin/env python3
"""Sube al dataset del Space el registro de la corrida diaria en vivo, para ponerlo después de ``diario.sh``.

Solo sube los archivos del registro (``paquete.EN_VIVO``: pronósticos, seguimiento y resumen) que cambiaron desde la
última subida: guarda sus sha256 en ``~/.cache/curva-hf/``, así que las corridas que no cambian nada no usan la red. El
Space los vuelve a pedir cada ``TPF_RECARGA_MIN`` minutos (15) y la API los relee sin reiniciar; con ``--reiniciar``,
además reinicia el Space (si se apagó la recarga).

    HF_TOKEN=hf_... python despliegue/actualizar_hf.py USUARIO            # con el Python que tenga huggingface_hub
    python despliegue/actualizar_hf.py USUARIO --dry-run                  # qué subiría, sin red

Códigos de salida: 0 subido o sin cambios; 1 error (la red, el token); 2 cuenta prohibida o sin token.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from despliegue.cuenta import ErrorCuenta, revisar_destino, token_personal, verificar_cuenta
from despliegue.paquete import EN_VIVO, mb, sha256
from despliegue.publicar_hf import CACHE, DATASET, SPACE, datos_por_defecto


def cambiados(datos: Path, estado: dict) -> dict[str, str]:
    """Los archivos del registro que existen y cuyo sha256 difiere del de la última subida, con su sha256."""
    salida = {}
    for ruta in EN_VIVO:
        archivo = datos / ruta
        if archivo.exists():
            huella = sha256(archivo)
            if estado.get(ruta) != huella:
                salida[ruta] = huella
    return salida


def leer_estado(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text())
    except (OSError, ValueError):
        return {}


def guardar_estado(ruta: Path, estado: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(json.dumps(estado, indent=2, sort_keys=True) + "\n")
    temporal.replace(ruta)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Sube el registro en vivo al dataset de la app en Hugging Face.")
    p.add_argument("usuario", help="tu usuario personal de Hugging Face")
    p.add_argument("--dataset", default=DATASET, help=f"nombre del dataset (por defecto, {DATASET})")
    p.add_argument("--space", default=SPACE, help=f"nombre del Space, para --reiniciar (por defecto, {SPACE})")
    p.add_argument("--datos", type=Path, default=datos_por_defecto(), help="carpeta de datos (TETOUAN_DATA)")
    p.add_argument("--estado", type=Path, help="dónde se guardan los sha256 de lo subido")
    p.add_argument("--reiniciar", action="store_true", help="reinicia el Space después de subir")
    p.add_argument("--forzar", action="store_true", help="sube aunque nada haya cambiado desde la última vez")
    p.add_argument("--dry-run", action="store_true", help="muestra qué subiría, sin red")
    args = p.parse_args(argv)
    dataset_id = f"{args.usuario}/{args.dataset}"
    ruta_estado = args.estado or CACHE / f"subido-{args.usuario}-{args.dataset}.json"
    ahora = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    try:
        revisar_destino(args.usuario)
        estado = {} if args.forzar else leer_estado(ruta_estado)
        nuevos = cambiados(args.datos, estado)
        if not nuevos:
            print(f"{ahora} INFO hf: el registro en vivo ya está al día en {dataset_id}")
            return 0
        detalle = ", ".join(f"{Path(r).name} ({mb((args.datos / r).stat().st_size)})" for r in nuevos)
        if args.dry_run:
            print(f"Subiría a {dataset_id}: {detalle}" + (" y reiniciaría el Space" if args.reiniciar else ""))
            return 0
        token = token_personal()
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")  # una línea por corrida en el log del cron
        from huggingface_hub import CommitOperationAdd, HfApi

        api = HfApi(token=token)  # explícito: nunca el token guardado en el disco
        verificar_cuenta(api.whoami(), args.usuario)
        operaciones = [CommitOperationAdd(path_in_repo=r, path_or_fileobj=str(args.datos / r)) for r in nuevos]
        antes = api.dataset_info(dataset_id).sha
        api.create_commit(dataset_id, operaciones, repo_type="dataset", commit_message=f"Registro en vivo al {ahora}")
        guardar_estado(ruta_estado, {**estado, **nuevos})
        if api.dataset_info(dataset_id).sha == antes:  # el Hub ya tenía esos mismos archivos: no hubo commit
            print(f"{ahora} INFO hf: el registro en vivo ya estaba en {dataset_id}")
            return 0
        print(f"{ahora} INFO hf: subido a {dataset_id}: {detalle}")
        if args.reiniciar:
            api.restart_space(f"{args.usuario}/{args.space}")
            print(f"{ahora} INFO hf: Space {args.usuario}/{args.space} reiniciado")
    except ErrorCuenta as error:
        print(f"{ahora} ERROR hf: {error}", file=sys.stderr)
        return 2
    except Exception as error:  # noqa: BLE001 - la red o el Hub: queda en el log del cron y se reintenta
        print(f"{ahora} ERROR hf: no se pudo subir el registro en vivo: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
