#!/usr/bin/env bash
# Levanta la app en local: backend FastAPI en :8000 y la web estática en :8080.
#   app/levantar.sh            # modelo real si encuentra los datos; si no, el simulado
#   TPF_PRONOSTICADOR=prueba app/levantar.sh
# Variables: TETOUAN_DATA (carpeta de datos), UV_PROJECT_ENVIRONMENT (venv), PUERTO_API, PUERTO_WEB.
set -euo pipefail
raiz="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$raiz/src:$raiz${PYTHONPATH:+:$PYTHONPATH}"
export TETOUAN_DATA="${TETOUAN_DATA:-$raiz/../tetouan-power-forecast/data}"
if [[ -z "${TPF_PRONOSTICADOR:-}" ]]; then
  if [[ -f "$TETOUAN_DATA/modelos/sein/app/metadatos.json" ]]; then export TPF_PRONOSTICADOR=real; else export TPF_PRONOSTICADOR=prueba; fi
fi
echo "Pronosticador: $TPF_PRONOSTICADOR (datos: $TETOUAN_DATA)"
cd "$raiz"
uv run --no-sync --with fastapi --with xgboost --with uvicorn --with holidays \
  uvicorn app.backend.main:app --port "${PUERTO_API:-8000}" &
api=$!
python3 -m http.server "${PUERTO_WEB:-8080}" --directory "$raiz/app/web" &
web=$!
trap 'kill $api $web 2>/dev/null' EXIT INT TERM
echo "Abre http://localhost:${PUERTO_WEB:-8080}"
wait
