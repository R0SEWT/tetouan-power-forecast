#!/usr/bin/env bash
# Publica la exposición en el sitio de Netlify «mds-rosewt» (cuenta r0sewt), que el catálogo uni.rosewt.dev (repo
# R0SEWT/uni) monta en /mds/ con un proxy: el TB1 queda en https://uni.rosewt.dev/mds/tb1/ y, directo, en
# https://mds-rosewt.netlify.app/tb1/.
#
#   bash publicar.sh          # renderiza el deck (HTML y PDF) y lo publica como /tb1/
#
# Cómo funciona: sitio/ es la raíz del sitio. index.html (la portada del curso) se versiona; cada entrega
# (sitio/tb1/) es el deck renderizado y su PDF, que no se versionan (el HTML pesa unos 9 MB). Netlify publica
# sitio/ entero, así que una entrega anterior tiene que seguir en sitio/ al publicar la siguiente.
#
# Requiere quarto, Chrome (para el PDF) y la CLI de Netlify con sesión iniciada (netlify login), o npx, que la
# descarga. Las cifras salen de la carpeta de datos (ver slides/README.md); sin ella se usan las versionadas.
set -euo pipefail
cd "$(dirname "$0")"

entrega="${1:-tb1}"
[[ "$entrega" =~ ^(tb1)$ ]] || { echo "error: la entrega es tb1, no '$entrega'" >&2; exit 1; }

bash slides/render.sh --pdf
mkdir -p "sitio/$entrega"
cp slides/_site/index.html "sitio/$entrega/index.html"
cp slides/_site/deck.pdf "sitio/$entrega/curva-$entrega.pdf"

if command -v netlify >/dev/null 2>&1; then netlify=(netlify); else netlify=(npx -y netlify-cli); fi
commit="$(git rev-parse --short HEAD)"
# El id del sitio y no su nombre: la CLI no siempre encuentra el sitio por nombre al desplegar. --no-build: no hay
# nada que construir en Netlify, se sube sitio/ tal cual.
sitio_id="e78baa63-6784-4ffd-9fc8-eb8beb2a0994"   # mds-rosewt
"${netlify[@]}" deploy --prod --no-build --dir sitio --site "$sitio_id" \
  --message "$entrega desde $commit ($(git rev-parse --abbrev-ref HEAD))"

echo "publicado: https://mds-rosewt.netlify.app/$entrega/ (y https://uni.rosewt.dev/mds/$entrega/ cuando el catálogo lo monte)"
