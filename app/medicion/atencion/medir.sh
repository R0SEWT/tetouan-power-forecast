#!/usr/bin/env bash
# Auditoría de atención en un comando: captura, lector UEyes, métricas baratas y primera apertura.
#   app/medicion/atencion/medir.sh base                 # todas las pantallas, viewports y temas
#   app/medicion/atencion/medir.sh it1 --pantallas inicio --vistas escritorio,movil
# Requiere la app levantada (app/levantar.sh) y el venv del proyecto (UV_PROJECT_ENVIRONMENT). Si la app no está en
# :8080/:8000, pasa TPF_WEB y TPF_API. La primera vez baja DINOv2-S (~85 MB) si no está en la caché de Hugging Face.
set -euo pipefail
cd "$(dirname "$0")/.."
etiqueta="${1:-base}"
shift || true
node atencion/capturar.mjs --etiqueta "$etiqueta" "$@"
uv run --no-sync python atencion/analizar.py --etiqueta "$etiqueta" ${COMPARAR:+--comparar "$COMPARAR"} ${LAMINAS:+--laminas "$LAMINAS"}
