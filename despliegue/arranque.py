"""Arranque del contenedor: baja el paquete de datos de un dataset del Hub, lo verifica y levanta la API en ``$PORT``.

Es el ``CMD`` del ``Dockerfile`` (``python -m despliegue.arranque``). Si la descarga o la verificación fallan, la app
no se cae: arranca con los datos de prueba sintéticos y la web muestra el motivo (``aviso`` de ``GET /salud``).

Variables de entorno:

- ``PORT``: el puerto (7860, el de Hugging Face Spaces; Cloud Run y otros ponen el suyo).
- ``TPF_HF_DATASET``: el dataset con el paquete (``usuario/curva-datos``) o, para probar sin red, una carpeta local con
  el mismo contenido (la que arma ``python -m despliegue.paquete``). Sin ella se usa ``TETOUAN_DATA`` si se montó una
  carpeta de datos con los modelos y, si no, los datos de prueba sintéticos (una vista pública sin datos del COES).
- ``HF_TOKEN``: el token con que se lee el dataset si es privado (un secreto del Space). Solo se usa el de la variable:
  nunca uno guardado en el disco.
- ``TPF_CACHE``: dónde quedan los datos (por defecto ``~/datos``); pasa a ser ``TETOUAN_DATA``.
- ``TPF_RECARGA_MIN``: cada cuántos minutos se vuelve a pedir al dataset el registro en vivo (15; 0 lo apaga). La API
  relee esos archivos cuando cambian, sin reiniciar: así llega la corrida de cada mañana (``actualizar_hf.py``).
"""

from __future__ import annotations

import filecmp
import logging
import os
import re
import shutil
import threading
import time
from pathlib import Path

from despliegue.paquete import EN_VIVO, METADATOS_APP, verificar

log = logging.getLogger("curva.arranque")
REPO_ID = re.compile(r"^[\w.-]+/[\w.-]+$")
INTENTOS = 3


class FuenteCarpeta:
    """Una carpeta local con el contenido del dataset: simula la descarga sin red (pruebas y ensayos)."""

    def __init__(self, carpeta: Path):
        self.carpeta = Path(carpeta)

    def __str__(self) -> str:
        return f"la carpeta {self.carpeta}"

    def bajar(self, destino: Path, rutas: tuple[str, ...] | None = None) -> None:
        if not self.carpeta.is_dir():
            raise FileNotFoundError(f"no existe la carpeta {self.carpeta}")
        if rutas is None:
            relativas = (p.relative_to(self.carpeta) for p in sorted(self.carpeta.rglob("*")) if p.is_file())
            rutas = tuple(str(r) for r in relativas if not any(parte.startswith(".") for parte in r.parts))
        for ruta in rutas:
            origen, final = self.carpeta / ruta, Path(destino) / ruta
            if not origen.exists() or (final.exists() and filecmp.cmp(origen, final, shallow=False)):
                continue
            final.parent.mkdir(parents=True, exist_ok=True)
            temporal = final.with_name(final.name + ".bajando")
            shutil.copyfile(origen, temporal)
            temporal.replace(final)  # de una vez, como la descarga del Hub: la API nunca lee un archivo a medias


class FuenteHub:
    """El dataset del Hub de Hugging Face, con ``snapshot_download`` (solo baja lo que cambió)."""

    def __init__(self, repo_id: str, token: str | None):
        self.repo_id, self.token = repo_id, token

    def __str__(self) -> str:
        return f"el dataset {self.repo_id}"

    def bajar(self, destino: Path, rutas: tuple[str, ...] | None = None) -> None:
        from huggingface_hub import snapshot_download

        # token=False si no hay HF_TOKEN: que nunca use un token guardado en el disco de quien lo corra
        snapshot_download(repo_id=self.repo_id, repo_type="dataset", local_dir=destino,
                          token=self.token or False, allow_patterns=list(rutas) if rutas else None)


def fuente_de(valor: str, token: str | None):
    """La fuente de ``TPF_HF_DATASET``: una carpeta (empieza por ``/``, ``.`` o ``file://``) o un repo ``dueño/nombre``."""
    if valor.startswith(("/", ".", "file://")):
        return FuenteCarpeta(Path(valor.removeprefix("file://")))
    if not REPO_ID.match(valor):
        raise ValueError(f"«{valor}» no es un dataset del Hub (dueño/nombre) ni una carpeta")
    return FuenteHub(valor, token)


def _breve(error: Exception) -> str:
    texto = " ".join(str(error).split()) or type(error).__name__
    return texto if len(texto) <= 300 else texto[:297] + "..."


def preparar(entorno=None) -> tuple[dict[str, str], object | None, Path | None]:
    """Deja los datos listos. Devuelve las variables que hay que fijar, la fuente (para recargar) y la carpeta."""
    entorno = os.environ if entorno is None else entorno
    cambios = {"TPF_SI_FALLA": "prueba"}  # si el modelo real no carga, la API arranca con el de prueba y lo dice
    valor = entorno.get("TPF_HF_DATASET", "").strip()
    if not valor:
        datos = entorno.get("TETOUAN_DATA")
        if datos and not entorno.get("TPF_PRONOSTICADOR") and (Path(datos) / METADATOS_APP).exists():
            cambios["TPF_PRONOSTICADOR"] = "real"
        modo = cambios.get("TPF_PRONOSTICADOR") or entorno.get("TPF_PRONOSTICADOR") or "prueba"
        log.info("Sin TPF_HF_DATASET: pronosticador «%s» (TETOUAN_DATA=%s)", modo, datos or "sin definir")
        return cambios, None, None
    cache = Path(entorno.get("TPF_CACHE") or Path.home() / "datos")
    try:
        fuente = fuente_de(valor, entorno.get("HF_TOKEN") or None)
        inicio = time.monotonic()
        for intento in range(1, INTENTOS + 1):
            try:
                fuente.bajar(cache)
                break
            except Exception as error:  # red, permisos, repo inexistente: se reintenta (y si no, se avisa)
                if intento == INTENTOS:
                    raise
                log.warning("No se pudo bajar %s (intento %d): %s", fuente, intento, _breve(error))
                time.sleep(5 * intento)
        problemas = verificar(cache)
        if problemas:
            raise RuntimeError("el paquete bajado no pasa la verificación: " + "; ".join(problemas[:3]))
        log.info("Datos listos en %s, bajados desde %s (%.0f s)", cache, fuente, time.monotonic() - inicio)
    except Exception as error:  # noqa: BLE001 - cualquier falla deja la app en datos de prueba, con aviso
        aviso = (f"No se pudieron bajar los datos reales ({_breve(error)}). Se muestran datos de prueba sintéticos; "
                 "revisa los logs del Space y el dataset.")
        log.error("%s", aviso)
        return {**cambios, "TPF_PRONOSTICADOR": "prueba", "TPF_AVISO": aviso}, None, None
    return {**cambios, "TETOUAN_DATA": str(cache), "TPF_PRONOSTICADOR": "real"}, fuente, cache


def recargar(fuente, cache: Path, minutos: float, parar: threading.Event) -> None:
    """Cada ``minutos``, vuelve a pedir el registro en vivo. La API relee esos archivos cuando cambian."""
    while not parar.wait(minutos * 60):
        try:
            fuente.bajar(cache, EN_VIVO)
        except Exception as error:  # noqa: BLE001 - un corte de red no tumba la app: reintenta en la próxima
            log.warning("No se pudo recargar el registro en vivo: %s", _breve(error))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    cambios, fuente, cache = preparar()
    os.environ.update(cambios)
    minutos = float(os.environ.get("TPF_RECARGA_MIN") or 15)
    if fuente is not None and minutos > 0:
        hilo = threading.Thread(target=recargar, args=(fuente, cache, minutos, threading.Event()), daemon=True,
                                name="recarga-en-vivo")
        hilo.start()
        log.info("El registro en vivo se recarga desde %s cada %g min", fuente, minutos)
    import uvicorn

    uvicorn.run("app.backend.main:app", host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "7860")),
                proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
