# Curva en un contenedor: la API (FastAPI) y la web, que la API sirve en su mismo origen. Es también la imagen del
# Space de Hugging Face (ver despliegue/README.md): puerto 7860, usuario con uid 1000 y los datos bajados al arrancar.
#
#   docker build -t curva .
#   docker run --rm -p 7860:7860 curva                                    # datos de prueba sintéticos
#   docker run --rm -p 7860:7860 -e TPF_HF_DATASET=usuario/curva-datos \
#     -e HF_TOKEN curva                                                   # baja el paquete de datos del Hub
#   docker run --rm -p 7860:7860 -v "$PWD/data:/datos:ro" \
#     -e TETOUAN_DATA=/datos curva                                        # con una carpeta de datos montada
#
# y abrir http://localhost:7860/ (la salud, en /salud). Los datos no van en la imagen: se bajan o se montan.
FROM python:3.13-slim

# uv instala exactamente las versiones de uv.lock: las mismas con que se entrenaron y se probaron los modelos
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONPATH=/app/src:/app \
    PORT=7860

WORKDIR /app
# Primero las dependencias (cambian poco), después el código. NCCL (para varias GPU) no hace falta en la CPU.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra app --extra despliegue \
      --no-install-package nvidia-nccl-cu13

# Hugging Face corre el contenedor con el uid 1000: los datos se bajan a su carpeta personal
RUN useradd --create-home --uid 1000 user
COPY src ./src
COPY app/__init__.py ./app/__init__.py
COPY app/backend ./app/backend
COPY app/web ./app/web
COPY despliegue/__init__.py despliegue/arranque.py despliegue/paquete.py ./despliegue/

USER user
ENV HOME=/home/user \
    TPF_CACHE=/home/user/datos
EXPOSE 7860
# La descarga de los datos y la carga de los modelos tardan antes de que el puerto responda
HEALTHCHECK --interval=30s --timeout=5s --start-period=10m \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"7860\")}/salud', timeout=4)"
CMD ["python", "-m", "despliegue.arranque"]
