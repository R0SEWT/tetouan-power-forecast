"""Download REE 5-min Ceuta demand for Jun 23 - Sep 1 of 2022-2026 (one request/day, 1 s pause)."""
import json, sys, time, urllib.request
from datetime import date, timedelta
from pathlib import Path
out = Path(sys.argv[1])
URL = "https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?curva=CEUTAAU&fecha={}"
for anio in range(2022, 2027):
    f = out / f"{anio}.jsonl"
    hechos = set()
    if f.exists():
        hechos = {json.loads(l)["fecha"] for l in f.read_text().splitlines() if l.strip()}
    d = date(anio, 6, 23)
    with f.open("a") as fh:
        while d <= date(anio, 9, 1):
            if str(d) not in hechos:
                req = urllib.request.Request(URL.format(d), headers={"User-Agent": "academic-research-client"})
                for k in range(3):
                    try:
                        txt = urllib.request.urlopen(req, timeout=60).read().decode()
                        break
                    except Exception as e:
                        time.sleep(5 * (k + 1)); txt = None
                if txt is not None:
                    fh.write(json.dumps({"fecha": str(d), "respuesta": txt}) + "\n"); fh.flush()
                time.sleep(1.0)
            d += timedelta(days=1)
    print(anio, "ok", flush=True)
