#!/usr/bin/env python3
"""Publica Curva en Hugging Face: el dataset con el paquete de datos y el Space Docker que lo baja al arrancar.

Con el token PERSONAL del dueño (permiso de escritura) en ``HF_TOKEN``, desde la raíz del repo:

    export HF_TOKEN=hf_...                     # el de tu cuenta personal, nunca el de una cuenta de trabajo
    uv run --no-project --with "huggingface_hub>=1.33,<2" python despliegue/publicar_hf.py USUARIO

Qué hace, en orden (y nada de lo que ya está hecho):

1. Revisa que el token sea de ``USUARIO`` (o de una de sus organizaciones), con permiso de escritura, y que no sea de
   una cuenta de trabajo del CIP (``cip-itlicenses``, organizaciones ``cipotato*``): si lo es, se detiene.
2. Arma el paquete de datos (``despliegue/paquete.py``) y lo sube al dataset ``USUARIO/curva-datos``, que crea si no
   existe. Solo sube lo que cambió.
3. Crea el Space ``USUARIO/curva`` (Docker, CPU básico gratuito) si no existe, le pone la variable ``TPF_HF_DATASET``
   y, si el dataset es privado, el secreto ``HF_TOKEN`` para leerlo (``HF_TOKEN_LECTURA`` si lo exportas: mejor un
   token de solo lectura), y sube el código. Cada commit de código reconstruye el Space.
4. Espera a que el Space quede en «Running» y comprueba ``/salud`` (con el token: un Space privado lo pide).

Los dos repos se crean PRIVADOS. Si ya existen, su visibilidad no se toca salvo que se pida (``--privado`` o
``--publico`` para el Space, ``--dataset-publico`` para el dataset). ``--dry-run`` muestra el plan sin usar la red.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:  # para correrlo como script: python despliegue/publicar_hf.py
    sys.path.insert(0, str(RAIZ))

from despliegue.cuenta import ErrorCuenta, revisar_destino, token_personal, verificar_cuenta
from despliegue.paquete import ErrorPaquete, armar_paquete, mb, peso, verificar

SPACE = "curva"
DATASET = "curva-datos"
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "curva-hf"
# El código que necesita la imagen (ver el Dockerfile); el README del Space se genera aparte
CODIGO = ("Dockerfile", ".dockerignore", "pyproject.toml", "uv.lock", "app/__init__.py",
          "despliegue/__init__.py", "despliegue/arranque.py", "despliegue/paquete.py")
CARPETAS_CODIGO = ("src", "app/backend", "app/web")
BORRAR_EN_SPACE = ["src/**", "app/**", "despliegue/**"]  # lo que ya no está en el código se borra del Space
BORRAR_EN_DATASET = ["coes/**", "exogenas/**", "modelos/**", "reportes/**"]
ESTADOS_ERROR = {"BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR", "NO_APP_FILE", "DELETING"}
ESTADOS_DETENIDO = {"STOPPED", "PAUSED", "SLEEPING"}


class ErrorPublicacion(RuntimeError):
    """Algo del Hub impide seguir (plan de la cuenta, build fallido, Space que no responde)."""


def datos_por_defecto() -> Path:
    return Path(os.environ.get("TETOUAN_DATA") or RAIZ.parent / "tetouan-power-forecast" / "data")


def archivos_codigo(raiz: Path = RAIZ) -> list[str]:
    """Las rutas relativas del código que se sube al Space."""
    rutas = [r for r in CODIGO if (raiz / r).exists()]
    for carpeta in CARPETAS_CODIGO:
        for archivo in sorted((raiz / carpeta).rglob("*")):
            relativa = archivo.relative_to(raiz)
            if archivo.is_file() and "__pycache__" not in relativa.parts and archivo.suffix != ".pyc":
                rutas.append(str(relativa))
    return rutas


def ficha_space(titulo: str, dataset: str | None) -> str:
    """El README.md del Space: su configuración (YAML) y una nota de qué es."""
    datos = (f"Al arrancar baja el paquete de datos del dataset `{dataset}` (ver `despliegue/README.md` del repositorio "
             "del proyecto). La demanda que muestra es la que publica el COES." if dataset else
             "No tiene dataset: muestra los datos de prueba sintéticos.")
    vinculo = f"datasets:\n- {dataset}\n" if dataset else ""
    return f"""---
title: {titulo}
emoji: ⚡
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
short_description: Pronóstico de la demanda eléctrica del Perú por área
startup_duration_timeout: 30m
{vinculo}---

# Curva

Pronóstico de la demanda eléctrica del SEIN peruano (Norte, Centro y Sur) a 1 h y a 24 h, con su rango y su error
publicado. La API (FastAPI) sirve también la web, en el mismo origen; la salud está en `/salud`.

{datos}
"""


def armar_codigo(destino: Path, dataset: str | None, titulo: str) -> list[str]:
    """Copia el código del Space a ``destino`` y escribe su README. Devuelve las rutas."""
    rutas = archivos_codigo()
    for ruta in rutas:
        (destino / ruta).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RAIZ / ruta, destino / ruta)
    (destino / "README.md").write_text(ficha_space(titulo, dataset))
    return [*rutas, "README.md"]


def _peso_carpeta(carpeta: Path) -> int:
    return sum(p.stat().st_size for p in carpeta.rglob("*") if p.is_file())


def _get(url: str, token: str, intentos: int = 6) -> tuple[int, dict | str]:
    """GET con el token (un Space privado lo pide). Reintenta mientras el Space termina de abrir el puerto."""
    for intento in range(intentos):
        try:
            pedido = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(pedido, timeout=60) as r:
                texto = r.read().decode()
                try:
                    return r.status, json.loads(texto)
                except ValueError:
                    return r.status, texto[:300]
        except urllib.error.HTTPError as error:
            if error.code < 500 or intento == intentos - 1:
                return error.code, error.read().decode(errors="replace")[:300]
        except OSError as error:
            if intento == intentos - 1:
                return 0, str(error)
        time.sleep(10)
    return 0, "sin respuesta"


class Publicador:
    def __init__(self, args, token: str | None):
        self.args, self.token = args, token
        self.usuario = args.usuario
        self.dataset_id = f"{args.usuario}/{args.dataset}"
        self.space_id = f"{args.usuario}/{args.space}"
        self.api = None
        if token is not None:
            from huggingface_hub import HfApi

            self.api = HfApi(token=token)  # siempre explícito: nunca el token guardado en el disco

    # ---- datos ------------------------------------------------------------------------------------------------------

    def paquete(self) -> Path:
        destino = self.args.paquete
        print(f"Paquete de datos: {self.args.datos} → {destino}")
        manifiesto = armar_paquete(self.args.datos, destino, progreso=lambda t: print(t))
        problemas = verificar(destino)
        if problemas:
            raise ErrorPaquete("el paquete armado no pasa la verificación: " + "; ".join(problemas))
        paquete, originales = peso(manifiesto, destino)
        print(f"  {mb(paquete)} ({len(manifiesto['archivos'])} estáticos y {len(manifiesto['en_vivo'])} del registro "
              f"en vivo; los originales pesan {mb(originales)})")
        return destino

    def subir_datos(self, carpeta: Path) -> bool:
        """Crea el dataset si falta y sube el paquete. Devuelve True si hubo un commit nuevo."""
        api = self.api
        existe = api.repo_exists(self.dataset_id, repo_type="dataset")
        if not existe:
            api.create_repo(self.dataset_id, repo_type="dataset", private=not self.args.dataset_publico)
            print(f"Dataset creado: {self.dataset_id} ({'público' if self.args.dataset_publico else 'privado'})")
        elif self.args.dataset_publico:
            api.update_repo_settings(self.dataset_id, repo_type="dataset", private=False)
        antes = api.dataset_info(self.dataset_id).sha if existe else None
        api.upload_folder(repo_id=self.dataset_id, repo_type="dataset", folder_path=carpeta,
                          commit_message="Paquete de datos de la app", delete_patterns=BORRAR_EN_DATASET)
        info = api.dataset_info(self.dataset_id)
        nuevo = info.sha != antes
        print(f"Dataset {self.dataset_id}: {'subido, commit ' + info.sha[:8] if nuevo else 'sin cambios'} "
              f"({'privado' if info.private else 'PÚBLICO'})")
        return nuevo

    # ---- Space ------------------------------------------------------------------------------------------------------

    def crear_space(self) -> None:
        api = self.api
        if api.repo_exists(self.space_id, repo_type="space"):
            if self.args.privado is not None:
                api.update_repo_settings(self.space_id, repo_type="space", private=self.args.privado)
            info = api.space_info(self.space_id)
            print(f"Space {self.space_id}: ya existe ({'privado' if info.private else 'PÚBLICO'})")
            return
        from huggingface_hub.errors import HfHubHTTPError

        privado = True if self.args.privado is None else self.args.privado
        try:
            api.create_repo(self.space_id, repo_type="space", space_sdk="docker", space_hardware="cpu-basic",
                            private=privado)
        except HfHubHTTPError as error:
            estado = getattr(error.response, "status_code", None)
            texto = str(error)
            if estado in (402, 403) or any(p in texto.lower() for p in ("pro subscription", "billing", "quota", "paid")):
                raise ErrorPublicacion(
                    f"Hugging Face no deja crear el Space Docker en la cuenta «{self.usuario}» ({estado}): {texto}\n"
                    "Desde julio de 2026 los Spaces Docker en CPU básico piden plan PRO (o facturación) en cuentas "
                    "personales. El dataset sí quedó subido. Opciones en despliegue/README.md, «Si Spaces no deja "
                    "crear el Space».") from error
            raise
        print(f"Space creado: {self.space_id} (Docker, CPU básico, {'privado' if privado else 'PÚBLICO'})")

    def configurar(self, con_datos: bool, dataset_privado: bool) -> bool:
        """Variables y secretos del Space. Devuelve True si cambió algo (eso reinicia el Space)."""
        api, cambio = self.api, False
        variables = {k: v.value for k, v in api.get_space_variables(self.space_id).items()}
        deseadas = {"TPF_HF_DATASET": self.dataset_id} if con_datos else {}
        if self.args.recarga is not None:
            deseadas["TPF_RECARGA_MIN"] = str(self.args.recarga)
        for clave, valor in deseadas.items():
            if variables.get(clave) != valor:
                api.add_space_variable(self.space_id, clave, valor, description="La pone despliegue/publicar_hf.py")
                print(f"  variable {clave}={valor}")
                cambio = True
        if not con_datos and "TPF_HF_DATASET" in variables:
            api.delete_space_variable(self.space_id, "TPF_HF_DATASET")
            print("  variable TPF_HF_DATASET borrada: el Space queda con los datos de prueba sintéticos")
            cambio = True
        if con_datos and dataset_privado:
            secretos = set(api.get_space_secrets(self.space_id))
            if "HF_TOKEN" not in secretos or self.args.rotar_token:
                lectura = os.environ.get("HF_TOKEN_LECTURA", "").strip()
                if not lectura:
                    print("  aviso: el secreto HF_TOKEN del Space será tu token de escritura. Mejor un token de solo "
                          "lectura: créalo y vuelve a correr con HF_TOKEN_LECTURA=... y --rotar-token")
                api.add_space_secret(self.space_id, "HF_TOKEN", lectura or self.token,
                                     description="Lee el dataset privado con los datos de la app")
                print("  secreto HF_TOKEN puesto (su valor no se muestra)")
                cambio = True
        return cambio

    def subir_codigo(self, con_datos: bool) -> bool:
        api = self.api
        antes = api.space_info(self.space_id).sha
        with tempfile.TemporaryDirectory(prefix="curva-space-") as temporal:
            rutas = armar_codigo(Path(temporal), self.dataset_id if con_datos else None, self.args.titulo)
            api.upload_folder(repo_id=self.space_id, repo_type="space", folder_path=temporal,
                              commit_message="Código de la app", delete_patterns=BORRAR_EN_SPACE)
        despues = api.space_info(self.space_id).sha
        nuevo = despues != antes
        print(f"Código ({len(rutas)} archivos): {'subido, commit ' + despues[:8] if nuevo else 'sin cambios'}")
        return nuevo

    def esperar(self, minutos: float, cambio: bool) -> str:
        """Hasta «Running». Si se acaba de subir código o reiniciar, primero espera a que el Space deje la etapa en que
        estaba (el contenedor viejo, o el error de la vez anterior): hasta 2 min, porque un cambio de variables a veces
        no lo reinicia."""
        api, limite, anterior, inicio = self.api, time.monotonic() + minutos * 60, None, time.monotonic()
        inicial, salio = None, not cambio
        while True:
            etapa = str(api.get_space_runtime(self.space_id).stage).split(".")[-1]
            if etapa != anterior:
                print(f"  {time.monotonic() - inicio:5.0f} s  {etapa}")
                anterior = etapa
            inicial = inicial or etapa
            salio = salio or etapa != inicial or time.monotonic() - inicio > 120
            if salio and etapa == "RUNNING":
                return etapa
            if salio and etapa in ESTADOS_ERROR:
                self.mostrar_logs(build=etapa != "RUNTIME_ERROR")
                raise ErrorPublicacion(f"El Space quedó en {etapa}. Los logs: https://huggingface.co/spaces/"
                                       f"{self.space_id}?logs=container (o ?logs=build)")
            if time.monotonic() > limite:
                raise ErrorPublicacion(f"El Space sigue en {etapa} después de {minutos:g} min.")
            time.sleep(15)

    def mostrar_logs(self, build: bool, lineas: int = 40) -> None:
        try:
            salida = list(self.api.fetch_space_logs(self.space_id, build=build))
        except Exception as error:  # noqa: BLE001 - los logs son una ayuda: si no llegan, se dice y se sigue
            print(f"  (no se pudieron leer los logs: {error})")
            return
        print(f"  últimas líneas del log de {'build' if build else 'ejecución'}:")
        for linea in "".join(salida).splitlines()[-lineas:]:
            print(f"    {linea}")

    def host(self) -> str:
        info = self.api.space_info(self.space_id)
        host = getattr(info, "host", None)
        if host:
            return host.rstrip("/")
        sub = getattr(info, "subdomain", None) or self.space_id.replace("/", "-").replace("_", "-").replace(".", "-")
        return f"https://{sub.lower()}.hf.space"

    def comprobar(self, con_datos: bool) -> dict:
        url = self.host()
        estado, salud = _get(f"{url}/salud", self.token)
        if estado != 200 or not isinstance(salud, dict):
            raise ErrorPublicacion(f"{url}/salud respondió {estado}: {salud}")
        print(f"  {url}/salud → modelo «{salud.get('modelo')}», datos «{salud.get('version_datos')}»")
        if salud.get("aviso"):
            print(f"  aviso de la app: {salud['aviso']}")
        if con_datos and salud.get("modelo") == "prueba":
            self.mostrar_logs(build=False)
            raise ErrorPublicacion("El Space responde, pero con los datos de prueba: no pudo usar el dataset.")
        return salud

    # ---- todo -------------------------------------------------------------------------------------------------------

    def publicar(self) -> None:
        args = self.args
        nombre = verificar_cuenta(self.api.whoami(), self.usuario)
        print(f"Cuenta del token: {nombre} (publica en {self.usuario})")
        con_datos = not args.sin_datos
        datos_nuevos, dataset_privado = False, True
        if con_datos:
            datos_nuevos = self.subir_datos(self.paquete())
            dataset_privado = bool(self.api.dataset_info(self.dataset_id).private)
        if args.solo_datos:
            return
        self.crear_space()
        reconfigurado = self.configurar(con_datos, dataset_privado)
        codigo_nuevo = self.subir_codigo(con_datos)
        etapa = str(self.api.get_space_runtime(self.space_id).stage).split(".")[-1]
        reiniciado = False
        if not (reconfigurado or codigo_nuevo) and (datos_nuevos or etapa in ESTADOS_DETENIDO | ESTADOS_ERROR):
            self.api.restart_space(self.space_id)  # datos nuevos (o Space parado): que los vuelva a bajar
            print("Space reiniciado para que baje los datos nuevos" if datos_nuevos else f"Space reiniciado ({etapa})")
            reiniciado = True
        if args.no_esperar:
            return
        print(f"Esperando a que {self.space_id} quede en «Running» (hasta {args.espera:g} min):")
        inicio = time.monotonic()
        self.esperar(args.espera, cambio=reconfigurado or codigo_nuevo or reiniciado)
        self.comprobar(con_datos)
        print(f"Listo en {time.monotonic() - inicio:.0f} s: https://huggingface.co/spaces/{self.space_id}")

    def plan(self) -> None:
        """--dry-run: lo que haría, sin red y sin token."""
        args = self.args
        con_datos = not args.sin_datos
        print("Simulación (--dry-run): no se usa la red ni el token.")
        print(f"1. Revisar que HF_TOKEN sea de «{self.usuario}», con escritura y no de una cuenta de trabajo.")
        if con_datos:
            carpeta = self.paquete()
            print(f"2. Crear (si falta) el dataset {self.dataset_id}, "
                  f"{'público' if args.dataset_publico else 'privado'}, y subir {mb(_peso_carpeta(carpeta))} "
                  "(solo lo que cambió).")
        else:
            print("2. Sin dataset (--sin-datos): el Space mostrará los datos de prueba sintéticos.")
        if args.solo_datos:
            return
        privado = "privado" if args.privado in (None, True) else "PÚBLICO"
        print(f"3. Crear (si falta) el Space {self.space_id}: Docker, CPU básico, {privado}.")
        if con_datos:
            print(f"   Variable TPF_HF_DATASET={self.dataset_id}; secreto HF_TOKEN si el dataset es privado "
                  f"({'HF_TOKEN_LECTURA' if os.environ.get('HF_TOKEN_LECTURA') else 'tu token de escritura'}).")
        rutas = archivos_codigo()
        total = sum((RAIZ / r).stat().st_size for r in rutas)
        print(f"   Subir el código: {len(rutas) + 1} archivos, {mb(total)} (README del Space generado):")
        for ruta in [r for r in rutas if "/" not in r or r.startswith("despliegue/")]:
            print(f"     {ruta}")
        print(f"     ... y {sum(r.startswith(CARPETAS_CODIGO) for r in rutas)} archivos de {', '.join(CARPETAS_CODIGO)}")
        if not args.no_esperar:
            print(f"4. Esperar «Running» (hasta {args.espera:g} min) y comprobar "
                  f"https://{self.space_id.replace('/', '-').lower()}.hf.space/salud con el token.")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Publica Curva en Hugging Face (dataset de datos y Space Docker).")
    p.add_argument("usuario", help="tu usuario personal de Hugging Face (o una organización tuya)")
    p.add_argument("--space", default=SPACE, help=f"nombre del Space (por defecto, {SPACE})")
    p.add_argument("--dataset", default=DATASET, help=f"nombre del dataset (por defecto, {DATASET})")
    p.add_argument("--titulo", default="Curva", help="título del Space")
    p.add_argument("--datos", type=Path, default=datos_por_defecto(),
                   help="carpeta de datos completa (por defecto, TETOUAN_DATA o ../tetouan-power-forecast/data)")
    p.add_argument("--paquete", type=Path, default=CACHE / "paquete",
                   help="dónde se arma el paquete (se reutiliza: no recomprime lo que no cambió)")
    visibilidad = p.add_mutually_exclusive_group()
    visibilidad.add_argument("--privado", dest="privado", action="store_true", default=None,
                             help="Space privado (es lo que se hace al crearlo si no se pide otra cosa)")
    visibilidad.add_argument("--publico", dest="privado", action="store_false",
                             help="Space PÚBLICO: cualquiera ve la app y la demanda del COES que muestra")
    p.add_argument("--dataset-publico", action="store_true", help="dataset PÚBLICO (por defecto, privado)")
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--sin-datos", action="store_true", help="Space sin dataset: solo datos de prueba sintéticos")
    modo.add_argument("--solo-datos", action="store_true", help="sube solo el dataset (sin Space)")
    p.add_argument("--recarga", type=float, help="minutos entre recargas del registro en vivo (la app usa 15)")
    p.add_argument("--rotar-token", action="store_true", help="vuelve a poner el secreto HF_TOKEN del Space")
    p.add_argument("--espera", type=float, default=30, help="minutos máximos de espera a «Running» (30)")
    p.add_argument("--no-esperar", action="store_true", help="no espera al build ni comprueba /salud")
    p.add_argument("--dry-run", action="store_true", help="muestra lo que haría, sin red")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        revisar_destino(args.usuario)
        if args.dry_run:
            Publicador(args, None).plan()
            return 0
        Publicador(args, token_personal()).publicar()
    except (ErrorCuenta, ErrorPaquete, ErrorPublicacion) as error:
        print(f"\nError: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
