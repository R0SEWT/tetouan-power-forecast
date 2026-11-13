# Corre en serie las líneas de /content/fm/cola.txt ("modelo contexto"); se pueden agregar líneas mientras corre.
cd /content
while true; do
  linea=$(grep -vxFf /content/fm/hechos.txt /content/fm/cola.txt | head -1)
  [ -z "$linea" ] && { echo "[$(date +%H:%M)] COLA VACIA" >> /content/fm/cola.log; sleep 60; [ -f /content/fm/PARAR ] && break; continue; }
  echo "[$(date +%H:%M)] INICIA $linea" >> /content/fm/cola.log
  python /content/fm_bench.py $linea 2025-01-01 2026-10-23 >> /content/fm/cola.log 2>&1 || echo "[$(date +%H:%M)] FALLO $linea" >> /content/fm/cola.log
  echo "$linea" >> /content/fm/hechos.txt
done
