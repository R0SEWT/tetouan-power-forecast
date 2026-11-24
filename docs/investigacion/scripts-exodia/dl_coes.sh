#!/bin/bash
# Download COES programmed vs executed demand month by month
S=/tmp/claude-1000/-home-cip-exodia-Code-exprimental/6eb617d0-39a3-45e8-8eeb-156768150d8d/scratchpad
for y in 2022 2023 2024 2025 2026; do
  for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
    if [ "$y$m" \> "202611" ]; then break; fi
    d="$S/downloads/coes_dem_$y$m"; [ -s "$d/data.json" ] && continue
    mkdir -p "$d"
    last=$(date -d "$y-$m-01 +1 month -1 day" +%d)
    fin="$last/$m/$y"; [ "$y$m" = "202611" ] && fin="21/11/2026"
    code=$(curl -sL -A "Mozilla/5.0 research-bot" -X POST --data-urlencode "fechaInicial=01/$m/$y" --data-urlencode "fechaFinal=$fin" -o "$d/data.json" -w "%{http_code}" "https://www.coes.org.pe/Portal/portalinformacion/Demanda")
    echo "$y$m $code $(stat -c %s $d/data.json)"
    sleep 3
  done
done
