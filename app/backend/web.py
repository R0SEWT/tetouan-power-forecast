"""La web estática (``app/web``) servida comprimida con gzip.

La monta el backend bajo su mismo origen (``http://localhost:8000/``) y la sirve sola ``app/levantar.sh`` en
``:8080`` (``uvicorn app.backend.web:app``), en lugar de ``python -m http.server``, que no comprime: a 1.6 Mbps,
``app.js`` y ``style.css`` bajan en ~33 KB en vez de ~120 KB. Este módulo no importa los modelos, así que el
servidor de la web arranca al instante.
"""

from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

WEB = Path(__file__).resolve().parents[1] / "web"
# Por debajo de esto gzip no ahorra nada que se note (la cabecera y la latencia pesan más).
GZIP_MINIMO = 500


def archivos_web(directorio: Path = WEB) -> StaticFiles:
    """Los archivos de la web, con ``index.html`` en ``/``."""
    return StaticFiles(directory=directorio, html=True)


def crear_web(directorio: Path = WEB) -> Starlette:
    """Un servidor que solo sirve la web, comprimida."""
    return Starlette(
        routes=[Mount("/", app=archivos_web(directorio))],
        middleware=[Middleware(GZipMiddleware, minimum_size=GZIP_MINIMO)],
    )


app = crear_web()
