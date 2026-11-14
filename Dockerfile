# Curva en un contenedor: la API (FastAPI) y la web, que la API sirve en su mismo origen.
#
#   docker build -t curva .
#   docker run --rm -p 8000:8000 curva                       # con datos de prueba sintéticos
#   docker run --rm -p 8000:8000 -v "$PWD/data:/datos" \
#     -e TETOUAN_DATA=/datos -e TPF_PRONOSTICADOR=real curva  # con el modelo real (capas del SEIN y modelos entrenados)
#
# y abrir http://localhost:8000/ (la salud, en /salud). Los datos no van en la imagen: se montan.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src:/app
WORKDIR /app

# Primero las dependencias (cambian poco), después el código
COPY pyproject.toml ./
COPY src ./src
RUN pip install ".[app]"
COPY app/backend ./app/backend
COPY app/web ./app/web
COPY app/__init__.py ./app/__init__.py

RUN useradd --create-home curva
USER curva
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/salud', timeout=4)"
CMD ["uvicorn", "app.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
