"""Antes y después de un PR: tabla de la atención por AOI y máscaras lado a lado.

    uv run --no-sync python app/medicion/atencion/comparar.py base it1 --pantallas inicio,ahora \\
        --vistas escritorio,movil --temas light --salida docs/auditoria/<pr>/

Cada PR de la serie mide su AOI clave con esto. Antes de creer una diferencia, compárala con el ruido del instrumento
(`analizar.py --comparar`: dos corridas del mismo build).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("antes")
    ap.add_argument("despues")
    ap.add_argument("--pantallas", default=None)
    ap.add_argument("--vistas", default=None)
    ap.add_argument("--temas", default="light")
    ap.add_argument("--duracion", default="3s")
    ap.add_argument("--salida", default=None, help="carpeta para las máscaras antes|después (JPEG)")
    a = ap.parse_args()
    leer = lambda e: json.loads((RAIZ / "resultados" / "atencion" / f"{e}.json").read_text())
    A, D = leer(a.antes), leer(a.despues)
    filtro = lambda n, campo, i: getattr(a, campo) is None or n.split("-")[i] in getattr(a, campo).split(",")
    nombres = [n for n in D["capturas"] if n in A["capturas"] and filtro(n, "pantallas", 0) and filtro(n, "vistas", 1) and filtro(n, "temas", 2)]
    print(f"| captura | AOI | {a.antes} | {a.despues} |\n|---|---|---|---|")
    for n in nombres:
        aa, dd = A["capturas"][n]["atencion"][a.duracion], D["capturas"][n]["atencion"][a.duracion]
        for k in dd:
            if k in aa and (aa[k]["area"] or dd[k]["area"]):
                f = lambda x: f"{100 * x['cuota']:.1f} % (lift {x['lift']})" if x["area"] else "fuera de la vista"
                print(f"| {n} | {k} | {f(aa[k])} | {f(dd[k])} |")
    if a.salida:
        out = Path(a.salida)
        out.mkdir(parents=True, exist_ok=True)
        try:
            fuente = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
        except OSError:
            fuente = ImageFont.load_default()
        for n in nombres:
            ims = [Image.open(RAIZ / "resultados" / "tmp" / "atencion" / e / "mapas" / f"{n}.jpg") for e in (a.antes, a.despues)]
            k = 0.5 if ims[0].width > 800 else 0.8
            ims = [im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS) for im in ims]
            hoja = Image.new("RGB", (ims[0].width + ims[1].width + 12, max(i.height for i in ims) + 32), (24, 26, 26))
            d = ImageDraw.Draw(hoja)
            d.text((8, 6), f"ANTES · atención {a.duracion}", fill=(230, 120, 120), font=fuente)
            d.text((ims[0].width + 20, 6), f"DESPUÉS · atención {a.duracion}", fill=(90, 220, 160), font=fuente)
            hoja.paste(ims[0], (0, 32))
            hoja.paste(ims[1], (ims[0].width + 12, 32))
            hoja.save(out / f"atencion-{n}.jpg", quality=76, optimize=True)


if __name__ == "__main__":
    main()
