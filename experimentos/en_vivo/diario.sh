#!/usr/bin/env bash
# La corrida diaria en vivo (ingesta → pronóstico → evaluación), para cron o un timer de systemd.
# Códigos de salida: 0 listo; 75 el COES todavía no publica el anexo de ayer u otra corrida está en curso (reintentar
# más tarde); 3 un anexo no pasa las validaciones (no se emitió nada: mirarlo a mano); 1 cualquier otro error.
#   experimentos/en_vivo/diario.sh              # diario
#   experimentos/en_vivo/diario.sh evaluacion   # cualquier otro comando del módulo
set -uo pipefail
raiz="$(cd "$(dirname "$0")/../.." && pwd)"
export TETOUAN_DATA="${TETOUAN_DATA:-$raiz/../tetouan-power-forecast/data}"
export PYTHONPATH="$raiz/src${PYTHONPATH:+:$PYTHONPATH}"
python="${TPF_VIVO_PYTHON:-$HOME/.cache/tpf-vivo/venv/bin/python}"
if [[ $# -eq 0 ]]; then set -- diario; fi
exec "$python" -m tetouan_power_forecast.en_vivo "$@"
