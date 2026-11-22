#!/usr/bin/env bash
# Publica la web de Curva en https://curva.rosewt.dev: un sitio de Netlify con la web estática (app/web), que carga al
# instante desde su CDN aunque el servidor esté dormido, y reglas de proxy (_redirects) que mandan solo las rutas de la
# API a Azure Container Apps (despliegue/publicar_aca.py). La web llama a la API en su mismo origen; si el servidor
# está en cero réplicas, la primera llamada lo despierta (~20 s) y la web muestra «Despertando el servidor...» y
# reintenta hasta ~60 s (app/web/app.js, pedirDespertando). Ver despliegue/README.md, sección «Netlify».
#
#   bash despliegue/publicar_netlify.sh ["mensaje"]      # arma la carpeta, publica en producción y prueba
#   bash despliegue/publicar_netlify.sh --dry-run        # solo arma la carpeta y muestra las reglas
#
# Requiere la CLI de Netlify con sesión iniciada en la cuenta personal (la que administra la zona rosewt.dev), o npx,
# que la descarga. El sitio se creó una vez (ver el README); este script solo publica.
set -euo pipefail
cd "$(dirname "$0")/.."

sitio_id="1e12ea46-b8c6-4245-9ef1-06fd67209b14"   # curva-rosewt (cuenta r0sewt)
dominio="${CURVA_DOMINIO:-curva.rosewt.dev}"   # para probar antes del dominio: CURVA_DOMINIO=curva-rosewt.netlify.app
origen="https://curva.jollyocean-4175cf43.brazilsouth.azurecontainerapps.io"   # la app de Container Apps
# Las rutas de la API (app/backend/main.py). Un test comprueba que estén todas: una ruta nueva sin regla daría 404.
rutas_fijas=(salud modelos areas resumen pronostico sensibilidad)
rutas_por_area=(series diagnostico seguimiento pico en-vivo ahora confianza)

carpeta="$(mktemp -d)"
trap 'rm -rf "$carpeta"' EXIT
cp -r app/web/. "$carpeta/"
{
  echo "# Generado por despliegue/publicar_netlify.sh: la API va a Container Apps (Netlify espera hasta 26 s)."
  for r in "${rutas_fijas[@]}"; do printf '/%-14s %s/%s 200\n' "$r" "$origen" "$r"; done
  for r in "${rutas_por_area[@]}"; do printf '/%-14s %s/%s/:splat 200\n' "$r/*" "$origen" "$r"; done
} > "$carpeta/_redirects"

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "Carpeta: $(find "$carpeta" -type f | wc -l) archivos, $(du -sk "$carpeta" | cut -f1) KB. Reglas:"
  cat "$carpeta/_redirects"
  exit 0
fi

if command -v netlify >/dev/null 2>&1; then netlify=(netlify); else netlify=(npx -y netlify-cli); fi
commit="$(git rev-parse --short HEAD 2>/dev/null || echo sin-commit)"
"${netlify[@]}" deploy --prod --no-build --dir "$carpeta" --site "$sitio_id" --message "${1:-publicar_netlify.sh desde $commit}"

# Prueba: la web sale del CDN y la API responde a través del proxy (puede tardar si el servidor dormía).
# CURVA_SIN_DESPERTAR=1 prueba solo la web, sin pedir /salud (no prende el servidor si está en cero réplicas).
codigo=$(curl -s -o /dev/null -w '%{http_code}' "https://$dominio/")
[[ "$codigo" == 200 ]] || { echo "ERROR: https://$dominio/ respondió $codigo" >&2; exit 1; }
if [[ -n "${CURVA_SIN_DESPERTAR:-}" ]]; then echo "publicado: https://$dominio (la web responde 200)"; exit 0; fi
for intento in 1 2 3 4 5 6; do
  codigo=$(curl -s -o /dev/null -w '%{http_code}' --max-time 40 "https://$dominio/salud" || true)
  [[ "$codigo" == 200 ]] && break
  sleep 10
done
[[ "$codigo" == 200 ]] || { echo "ERROR: https://$dominio/salud respondió $codigo" >&2; exit 1; }
echo "publicado: https://$dominio (la web y /salud responden 200)"
