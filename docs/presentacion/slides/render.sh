#!/usr/bin/env bash
# Renderiza el deck: datos.py (las series de D3, las cifras del texto, las tablas del respaldo y la portada, desde
# las tablas de los notebooks) y quarto render. Deja _site/index.html, un solo archivo que se abre sin servidor y
# sin red.
#
#   bash render.sh          # el deck
#   bash render.sh --pdf    # además, _site/deck.pdf (respaldo para el plan B o para imprimir)
#
# datos.py necesita la carpeta de datos (TETOUAN_DATA, ./data o la del checkout principal). Si no está, se
# renderiza con lo que ya está versionado (datos.js, _deck.yml, generado/ e img/portada.svg).
set -euo pipefail
cd "$(dirname "$0")"

command -v quarto >/dev/null 2>&1 || { echo "error: falta quarto (https://quarto.org)" >&2; exit 1; }

if command -v uv >/dev/null 2>&1 && uv run --quiet python datos.py; then
  :
else
  echo "aviso: no se pudo correr datos.py (¿falta la carpeta de datos?); se usan los datos versionados" >&2
fi
quarto render index.qmd

if [ "${1:-}" = "--pdf" ]; then
  chrome="$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)"
  [ -n "$chrome" ] || { echo "error: --pdf necesita Chrome o Chromium" >&2; exit 1; }
  perfil="$(mktemp -d)"
  trap 'rm -rf "$perfil"' EXIT
  # ?print-pdf: reveal pone una diapositiva por página, con los fragmentos visibles, y los gráficos dibujan su
  # estado final (sin animar)
  "$chrome" --headless=new --disable-gpu --no-sandbox --hide-scrollbars --user-data-dir="$perfil" \
    --window-size=1280,720 --virtual-time-budget=20000 --run-all-compositor-stages-before-draw \
    --no-pdf-header-footer --print-to-pdf="$PWD/_site/deck.pdf" "file://$PWD/_site/index.html?print-pdf" 2>/dev/null
  echo "PDF en $PWD/_site/deck.pdf"
fi
echo "deck en $PWD/_site/index.html"
