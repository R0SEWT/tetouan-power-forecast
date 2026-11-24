#!/bin/bash
# usage: fetch_coes.sh OUTDIR YEAR_START YEAR_END
OUT=$1; UA="Mozilla/5.0 (X11; Linux x86_64) research-bot"
mkdir -p "$OUT"
for y in $(seq $2 $3); do for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
  last=$(date -d "$y-$m-01 +1 month -1 day" +%d)
  f="$OUT/d_${y}${m}.json"; [ -s "$f" ] && continue
  curl -sS -A "$UA" -X POST --data-urlencode "fechaInicial=01/$m/$y" --data-urlencode "fechaFinal=$last/$m/$y" -o "$f" -w "$y-$m %{http_code} %{size_download}\n" "https://www.coes.org.pe/Portal/portalinformacion/Demanda"
  sleep 1.5
done; done
