#!/usr/bin/env bash
# Un comando para el día de la exposición (docs/demo/README.md): revisa lo necesario, levanta Curva, comprueba
# /salud y las cifras del guion, y abre el navegador en el paso 1 (y el paso 2 en otra pestaña).
#   docs/demo/demo.sh                 # todo; la app queda corriendo hasta Ctrl+C
#   docs/demo/demo.sh --verificar     # revisa y apaga: para el ensayo de la víspera
#   docs/demo/demo.sh --descargar     # antes, baja del Drive los datos que usa la app (rclone con acceso)
#   docs/demo/demo.sh --sin-navegador # no abre el navegador
# Variables: TETOUAN_DATA (carpeta de datos), PUERTO_API (8000), PUERTO_WEB (8080), UV_PROJECT_ENVIRONMENT.
set -uo pipefail

raiz="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$raiz" || exit 1
verificar=0
navegador=1
descargar=0
for opcion in "$@"; do
  case "$opcion" in
    --verificar) verificar=1; navegador=0 ;;
    --sin-navegador) navegador=0 ;;
    --descargar) descargar=1 ;;
    -h | --help) sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opción desconocida: $opcion (usa --help)"; exit 2 ;;
  esac
done

paso() { printf '\n== %s\n' "$*"; }
bien() { printf '   OK     %s\n' "$*"; }
aviso() { printf '   AVISO  %s\n' "$*"; }
morir() { printf '\nNO SE PUDO SEGUIR. %s\n' "$*" >&2; exit 1; }

paso "1/5 Herramientas"
command -v curl >/dev/null || morir "Falta curl. En Ubuntu: sudo apt install curl. Después vuelve a correr este comando."
command -v uv >/dev/null || morir "Falta uv, el gestor de Python del proyecto. Instálalo con
    curl -LsSf https://astral.sh/uv/install.sh | sh
cierra y abre la terminal, y vuelve a correr docs/demo/demo.sh."
bien "curl y uv $(uv --version | cut -d' ' -f2)"

paso "2/5 Datos"
export TETOUAN_DATA="${TETOUAN_DATA:-$raiz/../tetouan-power-forecast/data}"
drive="gdrive:datalake/tetouan-power-forecast"
if ((descargar)); then
  command -v rclone >/dev/null || morir "--descargar necesita rclone (https://rclone.org/install/) configurado con un
remoto «gdrive:» que vea el Drive del proyecto. Si no lo tienes, pide la carpeta de datos al dueño (README del kit)."
  rclone listremotes | grep -qx 'gdrive:' || morir "rclone no tiene el remoto «gdrive:». Configúralo con rclone config
o pide la carpeta de datos al dueño (README del kit)."
  echo "   Bajando del Drive a $TETOUAN_DATA (la primera vez, unos 240 MB; después solo lo que cambió)..."
  for carpeta in coes/silver exogenas/silver modelos/sein/app reportes/sein/modelado reportes/sein/prueba_2026 \
    reportes/sein/en_vivo reportes/sein/app; do
    rclone copy "$drive/$carpeta" "$TETOUAN_DATA/$carpeta" --exclude ".corrida.lock" \
      || morir "No se pudo bajar $carpeta del Drive."
  done
  # De los fundacionales, solo lo que lee la app (no los pesos de Chronos-2, 478 MB, que usa la corrida en vivo)
  rclone copy "$drive/modelos/sein/fundacionales" "$TETOUAN_DATA/modelos/sein/fundacionales" \
    --include "combinado.json" --include "xgb_simons_*.joblib" \
    || morir "No se pudieron bajar los modelos fundacionales del Drive."
  rclone copy "$drive/reportes/sein/fundacionales" "$TETOUAN_DATA/reportes/sein/fundacionales" \
    --include "simons_c2048.parquet" --include "chronos2ftcal_c2048.parquet" --include "tablas/**" \
    || morir "No se pudieron bajar los pronósticos fundacionales del Drive."
fi
necesarios=(
  coes/silver/demanda_areas.parquet
  exogenas/silver/temperatura_areas.parquet exogenas/silver/icen.parquet
  exogenas/silver/nino12_semanal.parquet exogenas/silver/eventos_coes.parquet
  modelos/sein/app/metadatos.json
  modelos/sein/fundacionales/combinado.json modelos/sein/fundacionales/xgb_simons_{1h,24h}.joblib
  reportes/sein/fundacionales/simons_c2048.parquet reportes/sein/fundacionales/chronos2ftcal_c2048.parquet
  reportes/sein/modelado/predicciones_validacion_24h_centro.csv reportes/sein/prueba_2026/adaptacion.csv
)
faltan=0
for archivo in "${necesarios[@]}"; do
  if [[ ! -f "$TETOUAN_DATA/$archivo" ]]; then
    printf '   FALTA  %s\n' "$archivo"
    faltan=$((faltan + 1))
  fi
done
if ((faltan)); then
  morir "Faltan $faltan archivo(s) en la carpeta de datos ($TETOUAN_DATA).
Sin ellos la app arranca con datos de prueba y la demo va al plan B. Para conseguirlos:
  - Pide al dueño la carpeta «data» del proyecto (Drive: datalake/tetouan-power-forecast) y déjala junto al repo,
    en $(cd "$raiz/.." && pwd)/tetouan-power-forecast/data; o di dónde está:
        TETOUAN_DATA=/ruta/a/data docs/demo/demo.sh
  - Si tienes rclone con acceso a ese Drive: docs/demo/demo.sh --descargar"
fi
bien "Carpeta de datos: $TETOUAN_DATA"
if [[ -f "$TETOUAN_DATA/reportes/sein/en_vivo/pronosticos.parquet" ]]; then
  bien "Registro en vivo presente (su fecha se revisa en el paso 4)"
else
  aviso "No está el registro en vivo (reportes/sein/en_vivo): el paso 1 mostrará el último día del historial."
fi

paso "3/5 Python y dependencias"
# Lo que levantar.sh no agrega con --with (fastapi, uvicorn, xgboost y holidays van aparte)
if uv run --no-sync python -c "import pandas, sklearn, pyarrow" 2>/dev/null; then
  bien "Entorno listo"
elif [[ -n ${UV_PROJECT_ENVIRONMENT:-} ]]; then
  morir "El entorno de UV_PROJECT_ENVIRONMENT ($UV_PROJECT_ENVIRONMENT) no tiene pandas, scikit-learn o pyarrow.
demo.sh no instala nada en un entorno ajeno: quita esa variable (unset UV_PROJECT_ENVIRONMENT) y vuelve a correr."
else
  echo "   Instalando dependencias (la primera vez tarda unos minutos y necesita internet)..."
  uv sync --frozen --inexact --extra app || morir "No se pudieron instalar las dependencias con uv. Revisa la conexión a
internet y vuelve a correr. Si persiste, usa el plan B del README del kit."
  bien "Dependencias instaladas"
fi
# Todos los modelos que nombra metadatos.json (la API carga cada uno al arrancar y se cae si falta alguno)
faltan_modelos=$(uv run --no-sync python - "$TETOUAN_DATA/modelos/sein/app" <<'PY'
import json, sys
from pathlib import Path
carpeta = Path(sys.argv[1])
for clave in json.loads((carpeta / "metadatos.json").read_text())["columnas"]:
    if not (carpeta / f"xgboost_global_{clave}.joblib").is_file():
        print(f"modelos/sein/app/xgboost_global_{clave}.joblib")
PY
) || morir "No se pudo leer $TETOUAN_DATA/modelos/sein/app/metadatos.json: vuelve a copiar esa carpeta de datos."
if [[ -n $faltan_modelos ]]; then
  printf '   FALTA  %s\n' $faltan_modelos
  morir "metadatos.json nombra modelos que no están en la carpeta de datos. Vuelve a copiar modelos/sein/app completa
(del Drive del dueño, o con docs/demo/demo.sh --descargar); sin ellos la API no arranca."
fi
bien "Están todos los modelos que nombra metadatos.json"

paso "4/5 Levantar la app"
ocupado() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
libre() {
  local p=$1
  while ocupado "$p"; do p=$((p + 1)); done
  echo "$p"
}
pedido_api="${PUERTO_API:-8000}"
pedido_web="${PUERTO_WEB:-8080}"
PUERTO_API=$(libre "$pedido_api")
PUERTO_WEB=$(libre "$pedido_web")
if [[ $PUERTO_WEB == "$PUERTO_API" ]]; then PUERTO_WEB=$(libre $((PUERTO_API + 1))); fi
[[ $PUERTO_API != "$pedido_api" ]] && aviso "El puerto $pedido_api está ocupado (¿otra copia de la app?): la API va en $PUERTO_API."
[[ $PUERTO_WEB != "$pedido_web" ]] && aviso "El puerto $pedido_web está ocupado: la web va en $PUERTO_WEB."
export PUERTO_API PUERTO_WEB
api="http://localhost:$PUERTO_API"
base="http://localhost:$PUERTO_WEB/"
# Como levantar.sh: la web de :8080 busca la API en :8000; con otros puertos se le dice dónde está
[[ $PUERTO_API != 8000 || $PUERTO_WEB != 8080 ]] && base+="?api=$api"
registro="${TMPDIR:-/tmp}/curva-demo-$PUERTO_API.log"
app/levantar.sh >"$registro" 2>&1 &
pid=$!
apagar() {
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    echo "App apagada."
  fi
}
trap apagar EXIT
trap 'exit 130' INT TERM
printf '   Esperando a la API en %s ' "$api"
for _ in $(seq 1 90); do
  if curl -sf "$api/salud" >/dev/null; then break; fi
  if ! kill -0 "$pid" 2>/dev/null || grep -qE "Traceback|startup failed|address already in use" "$registro"; then
    echo
    tail -n 15 "$registro" >&2
    morir "La API no pudo arrancar (registro completo: $registro). Si dice «address already in use», otro programa
tomó el puerto: vuelve a correr demo.sh. Si no, plan B del README."
  fi
  printf '.'
  sleep 2
done
echo
curl -sf "$api/salud" >/dev/null || morir "La API no respondió en 3 minutos (registro: $registro). Plan B del README."
# Que la API que respondió sea la de este arranque y no otra que tomó el puerto entre la revisión y el arranque
grep -q "Uvicorn running on http://127.0.0.1:$PUERTO_API" "$registro" \
  || morir "Respondió en :$PUERTO_API una API que no es la de este arranque. Vuelve a correr demo.sh."
bien "La API responde: $(curl -sf "$api/salud")"
if curl -sf "$base" >/dev/null; then bien "La web responde en http://localhost:$PUERTO_WEB"; else
  aviso "La web no responde en :$PUERTO_WEB; se usa la que sirve la API, en :$PUERTO_API."
  base="http://localhost:$PUERTO_API/"  # servida por la API, la web la busca en su mismo origen
fi

paso "5/5 Cifras del guion"
salida_cifras="${TMPDIR:-/tmp}/curva-demo-cifras-$PUERTO_API.txt"
uv run --no-sync python docs/demo/verificar.py --api "$api" | tee "$salida_cifras"
cifras=${PIPESTATUS[0]}
if ((cifras == 1)); then
  aviso "Hay cifras que no coinciden con el guion (arriba). Si dice «prueba» o falta el combinado: plan B."
elif ((cifras > 1)); then
  morir "No se pudieron comprobar las cifras. Plan B del README."
fi

paso1="${base}#/ahora/centro"
paso2="${base}#/ahora/centro?fecha=2026-08-27&hora=19:00"
respaldo="${base}#/ahora/centro?fecha=2026-03-10&hora=19:00"
if ((verificar)); then
  echo
  if ((cifras != 0)); then echo "Ensayo: hay cifras que no coinciden; revisa arriba."
  elif grep -q "AVISO" "$salida_cifras"; then echo "Ensayo: listo, con avisos (léelos arriba)."
  else echo "Ensayo: todo listo."; fi
  exit "$cifras"
fi

abrir() {
  if command -v xdg-open >/dev/null; then xdg-open "$1" >/dev/null 2>&1
  elif command -v open >/dev/null; then open "$1"
  elif command -v cmd.exe >/dev/null; then cmd.exe /c start "" "$1" >/dev/null 2>&1
  else return 1; fi
}
if ((navegador)); then
  abrir "$paso1" && sleep 1 && abrir "$paso2" || aviso "No pude abrir el navegador: abre a mano las URL de abajo."
fi
cat <<EOF

Listo. Curva está corriendo. Pestañas de la demo (en Chrome, zoom 150 %: Ctrl y + hasta 150 %):
  Paso 1, hoy:           $paso1
  Paso 2, 27/08/2026:    $paso2   (los pasos 3 y 4 siguen con clics desde aquí)
  Respaldo, 10/03/2026:  $respaldo
Registro de la app: $registro
Ctrl+C para apagarla al terminar.
EOF
wait "$pid"
