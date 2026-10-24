#!/bin/bash
# Reintenta descargas de Open-Meteo archive (ERA5) por ciudad; sale cuando todas existen o tras N intentos
OUT=$1; mkdir -p $OUT; cd $OUT
V=temperature_2m_max,temperature_2m_min,temperature_2m_mean,apparent_temperature_max,precipitation_sum
for attempt in $(seq 1 15); do
  pending=0
  for c in "lima -12.046 -77.043" "piura -5.194 -80.632" "tumbes -3.567 -80.451" "chiclayo -6.771 -79.841"; do
    set -- $c
    f=${1}_era5.csv
    if [ -s $f ] && head -1 $f | grep -q latitude; then continue; fi
    pending=1
    curl -sS -m 150 -o $f.tmp -w "try$attempt $1 %{http_code} %{size_download} %{time_total}\n" "https://archive-api.open-meteo.com/v1/archive?latitude=$2&longitude=$3&start_date=2015-01-01&end_date=2024-12-31&daily=$V&timezone=America%2FLima&models=era5&format=csv" && head -1 $f.tmp | grep -q latitude && mv $f.tmp $f
  done
  [ $pending = 0 ] && { echo DONE; exit 0; }
  sleep 60
done
echo GAVEUP
