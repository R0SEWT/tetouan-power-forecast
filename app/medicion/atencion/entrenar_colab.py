"""Entrena el lector de atención sobre UEyes y valida el port a numpy. Se corre en Colab, no en la laptop.

Reproduce el procedimiento de R0SEWT/myPage (site/audit/fetch_ueyes.py, ueyes_feats.py, ueyes_train.py):
1. Baja de Zenodo solo imágenes y mapas de calor de UEyes (Jiang et al., CHI 2023) con lecturas por rango (~1,3 GB
   de un zip de 12,9 GB), en tramos contiguos para no chocar con el límite de peticiones de Zenodo.
2. Extrae rasgos congelados de DINOv2-S (`facebook/dinov2-small`, capas 8 y 12, proporción nativa, fp16).
3. Entrena la cabeza (conv pequeña + prior de posición) en el split oficial de entrenamiento y la evalúa en el
   de prueba contra un modelo de solo sesgo central (CC↑, KLD↓), para 3 s, 7 s y 1 s de visión libre.
4. Comprueba que `saliencia.py` (numpy, pesos timm) da los mismos rasgos y mapas que torch/transformers.
5. Exporta `cabeza_ueyes_<dur>.npz` y `metricas.json`, que son lo único que se baja a la laptop.

Uso en la VM (desacoplado, retomable): `python entrenar_colab.py > entrenar.log 2>&1`. Estado en `estado.json`.
"""

import csv
import itertools
import json
import os
import random
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

T0 = time.time()
TRABAJO = os.environ.get("TRABAJO", "/content/ueyes")
os.makedirs(TRABAJO, exist_ok=True)
os.chdir(TRABAJO)
DURACIONES = ["3s", "7s", "1s"]
ZENODO = "https://zenodo.org/api/records/8010312"
URL = ZENODO + "/files/UEyes_dataset.zip/content"


def leer_json(ruta):
    with open(ruta) as f:
        return json.load(f)


def escribir_json(ruta, x):
    with open(ruta, "w") as f:
        json.dump(x, f, indent=1)


def escribir(ruta, datos: bytes):
    with open(ruta, "wb") as f:
        f.write(datos)


def filas_ueyes():
    with open("ueyesdata/image_types.csv") as f:
        return list(csv.DictReader(f, delimiter=";"))


def estado(**kw):
    e = leer_json("estado.json") if os.path.exists("estado.json") else {}
    e.update(kw, minutos=round((time.time() - T0) / 60, 1))
    escribir_json("estado.json", e)
    print("ESTADO", kw, flush=True)


def instalar():
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "remotezip", "timm"], check=True)


# ---------- 1. datos ----------

def bajar_ueyes():
    """Lee del zip de Zenodo (12,9 GB) solo lo que hace falta. Zenodo limita las peticiones por minuto (429)
    y cada conexión va lenta, así que en vez de una petición por archivo (como myPage) se piden tramos
    contiguos de ~48 MB del zip y se descomprimen aquí: ~30 peticiones en lugar de ~8000."""
    if os.path.exists("ueyesdata/.completo"):
        return
    import threading
    import urllib.request
    import zlib

    import requests
    from remotezip import RemoteZip

    meta = json.load(urllib.request.urlopen(ZENODO))
    escribir_json("zenodo.json", {"licencia": meta.get("metadata", {}).get("license"), "doi": meta.get("doi"),
                                  "titulo": meta.get("metadata", {}).get("title")})
    z0 = RemoteZip(URL)
    todas = sorted(z0.infolist(), key=lambda i: i.header_offset)
    fin_de = {a.filename: b.header_offset for a, b in itertools.pairwise(todas)}
    pref = ("UEyes_dataset/images/",) + tuple(f"UEyes_dataset/saliency_maps/heatmaps_{d}/" for d in DURACIONES)

    def util(n):
        return ("__MACOSX" not in n and "/._" not in n and not n.endswith("/") and not n.endswith(".DS_Store")
                and (n.startswith(pref) or n.endswith("image_types.csv")))

    quiero = [i for i in todas if util(i.filename) and i.filename in fin_de]
    def salida(n):
        return "ueyesdata/" + n.replace("UEyes_dataset/", "")

    pendientes = [i for i in quiero if not os.path.exists(salida(i.filename))]
    tramos, actual = [], []
    for i in pendientes:
        if actual and (fin_de[i.filename] - actual[0].header_offset > 48e6 or i.header_offset - fin_de[actual[-1].filename] > 2e6):
            tramos.append(actual)
            actual = []
        actual.append(i)
    if actual:
        tramos.append(actual)
    estado(etapa="bajando", archivos=len(quiero), pendientes=len(pendientes), tramos=len(tramos))
    hechos = [0]
    candado = threading.Lock()

    def bajar(tramo):
        a, b = tramo[0].header_offset, fin_de[tramo[-1].filename] - 1
        for intento in range(8):
            try:
                r = requests.get(URL, headers={"Range": f"bytes={a}-{b}"}, timeout=600)
                if r.status_code == 429:
                    time.sleep(30 * (intento + 1))
                    continue
                r.raise_for_status()
                datos = r.content
                if len(datos) != b - a + 1:
                    raise OSError(f"tramo corto {len(datos)} de {b - a + 1}")
                break
            except Exception as e:  # noqa: BLE001
                print("reintento", a, e, flush=True)
                time.sleep(10 * (intento + 1))
        else:
            print("fallo el tramo", a, flush=True)
            return
        for i in tramo:
            o = i.header_offset - a
            if datos[o:o + 4] != b"PK\x03\x04":
                print("cabecera rara", i.filename, flush=True)
                continue
            n_nombre = int.from_bytes(datos[o + 26:o + 28], "little")
            n_extra = int.from_bytes(datos[o + 28:o + 30], "little")
            ini = o + 30 + n_nombre + n_extra
            crudo = datos[ini:ini + i.compress_size]
            contenido = zlib.decompress(crudo, -15) if i.compress_type == 8 else crudo
            if len(contenido) != i.file_size:
                print("tamaño raro", i.filename, flush=True)
                continue
            os.makedirs(os.path.dirname(salida(i.filename)), exist_ok=True)
            escribir(salida(i.filename), contenido)
        with candado:
            hechos[0] += 1
            if hechos[0] % 3 == 0:
                estado(etapa="bajando", tramos_hechos=hechos[0], tramos=len(tramos))

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(bajar, tramos))
    faltan = [i.filename for i in quiero if not os.path.exists(salida(i.filename))]
    if faltan:
        raise SystemExit(f"faltan {len(faltan)} archivos; volver a lanzar para retomar")
    escribir("ueyesdata/.completo", b"ok")


# ---------- 2. rasgos ----------

def extraer_rasgos():
    import torch
    from PIL import Image
    from transformers import AutoModel

    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = AutoModel.from_pretrained("facebook/dinov2-small", output_hidden_states=True).eval().to(dev)
    media = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    desv = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    area = 448 * 448

    def prep(im):
        w, h = im.size
        s = (area / (w * h)) ** 0.5
        ancho = max(14, round(w * s / 14) * 14)
        alto = max(14, round(h * s / 14) * 14)
        x = torch.from_numpy(np.asarray(im.convert("RGB").resize((ancho, alto), Image.BICUBIC))).permute(2, 0, 1).float() / 255
        return ((x - media) / desv)[None], alto // 14, ancho // 14

    @torch.no_grad()
    def feats(im):
        x, gh, gw = prep(im)
        o = m(pixel_values=x.to(dev))
        hs = [o.hidden_states[i][0, 1:] for i in (8, 12)]
        return torch.cat(hs, -1).reshape(gh, gw, -1).permute(2, 0, 1).half().cpu()

    os.makedirs("ueyesfeat", exist_ok=True)
    filas = filas_ueyes()
    for i, r in enumerate(filas):
        n = r["Image Name"]
        out = f"ueyesfeat/{n}.pt"
        if os.path.exists(out) or not os.path.exists(f"ueyesdata/images/{n}"):
            continue
        torch.save(feats(Image.open(f"ueyesdata/images/{n}")), out)
        if i % 200 == 0:
            estado(etapa="rasgos", hechos=i, total=len(filas))
    return feats


# ---------- 3. entrenamiento (idéntico a myPage salvo nombres) ----------

def definir_modelo():
    import torch
    import torch.nn.functional as F
    from torch import nn

    class Bias(nn.Module):
        def __init__(s):
            super().__init__()
            s.b = nn.Parameter(torch.zeros(1, 1, 24, 24))

        def forward(s, gh, gw):
            return F.interpolate(s.b, (gh, gw), mode="bilinear", align_corners=False)[0, 0]

    class Head(nn.Module):
        def __init__(s, c=768):
            super().__init__()
            s.net = nn.Sequential(nn.Conv2d(c, 96, 1), nn.GELU(), nn.Conv2d(96, 32, 3, padding=1), nn.GELU(), nn.Conv2d(32, 1, 3, padding=1))
            s.bias = Bias()

        def forward(s, f, use_feat=True):
            gh, gw = f.shape[1:]
            x = s.bias(gh, gw)
            if use_feat:
                x = x + s.net(f[None])[0, 0]
            return F.log_softmax(x.flatten(), 0).view(gh, gw)

    return Head


def entrenar(dur, Head):
    import torch
    from PIL import Image

    torch.manual_seed(0)
    random.seed(0)
    torch.set_num_threads(4)
    filas = [r for r in filas_ueyes()
             if os.path.exists(f"ueyesfeat/{r['Image Name']}.pt") and os.path.exists(f"ueyesdata/saliency_maps/heatmaps_{dur}/{r['Image Name']}")]

    def load(r):
        f = torch.load(f"ueyesfeat/{r['Image Name']}.pt").float()
        gh, gw = f.shape[1:]
        g = np.asarray(Image.open(f"ueyesdata/saliency_maps/heatmaps_{dur}/{r['Image Name']}").convert("L").resize((gw, gh), Image.BOX), dtype=np.float32)
        g = torch.from_numpy(g) + 1e-6
        return f, g / g.sum(), r["Category"]

    data = [(load(r), r["Train/Test"]) for r in filas]
    train = [d for d, s in data if s == "Train"]
    test = [d for d, s in data if s == "Test"]

    def cc(p, g):
        p = p - p.mean()
        g = g - g.mean()
        return (p * g).sum() / (p.norm() * g.norm() + 1e-9)

    def kld(logp, g):
        return (g * (torch.log(g) - logp)).sum()

    def fit(use_feat, epochs):
        h = Head()
        opt = torch.optim.AdamW(h.parameters(), 3e-4 if use_feat else 3e-2, weight_decay=1e-4)
        for ep in range(epochs):
            random.shuffle(train)
            tot = 0
            for f, g, _ in train:
                lp = h(f, use_feat)
                loss = kld(lp, g) - 2 * cc(lp.exp(), g)
                opt.zero_grad()
                loss.backward()
                opt.step()
                tot += loss.item()
            print(dur, "modelo" if use_feat else "sesgo", ep, round(tot / len(train), 4), flush=True)
        return h

    @torch.no_grad()
    def evaluate(h, use_feat):
        res = {}
        for f, g, cat in test:
            lp = h(f, use_feat)
            res.setdefault(cat, []).append((cc(lp.exp(), g).item(), kld(lp, g).item()))
        allv = [v for vs in res.values() for v in vs]
        out = {c: {"cc": round(float(np.mean([a for a, _ in v])), 3), "kld": round(float(np.mean([b for _, b in v])), 3), "n": len(v)} for c, v in res.items()}
        out["todo"] = {"cc": round(float(np.mean([a for a, _ in allv])), 3), "kld": round(float(np.mean([b for _, b in allv])), 3), "n": len(allv)}
        return out

    hb = fit(False, 6)
    hm = fit(True, 8)
    met = {"n_train": len(train), "n_test": len(test), "sesgo_central": evaluate(hb, False), "lector": evaluate(hm, True)}
    torch.save(hm.state_dict(), f"cabeza_ueyes_{dur}.pt")
    np.savez(f"cabeza_ueyes_{dur}.npz", **{k: v.detach().numpy().astype(np.float32) for k, v in hm.state_dict().items()})
    return hm, met


# ---------- 4. validación del port numpy ----------

def validar(hm):
    import torch
    import torch.nn.functional as F
    from huggingface_hub import hf_hub_download
    from PIL import Image
    from transformers import AutoModel

    sys.path.insert(0, os.environ.get("DIR_SALIENCIA", "/content"))
    import saliencia as sal

    ruta = hf_hub_download("timm/vit_small_patch14_dinov2.lvd142m", "model.safetensors")
    pt = sal.leer_safetensors(ruta)
    hf = AutoModel.from_pretrained("facebook/dinov2-small", output_hidden_states=True).eval()
    sd = {k: v.numpy() for k, v in hf.state_dict().items()}
    # pesos: los mismos números en las dos distribuciones
    dif_pesos = max(
        float(np.abs(pt["pos_embed"] - sd["embeddings.position_embeddings"]).max()),
        float(np.abs(pt["blocks.7.attn.qkv.weight"] - np.concatenate([
            sd.get(f"encoder.layer.7.attention.{q[0]}_proj.weight", sd.get(f"encoder.layer.7.attention.attention.{q}.weight"))
            for q in ("query", "key", "value")])).max()),
        float(np.abs(pt["blocks.11.mlp.fc2.weight"] - sd["encoder.layer.11.mlp.fc2.weight"]).max()),
    )
    # interpolación del embedding de posición, para las rejillas de nuestros viewports
    pe = torch.from_numpy(pt["pos_embed"][0, 1:].reshape(37, 37, -1)).permute(2, 0, 1)[None]
    dif_interp = 0.0
    for gh, gw in [(24, 43), (28, 37), (47, 22), (30, 34)]:
        ref = F.interpolate(pe, size=(gh, gw), mode="bicubic", align_corners=False, antialias=True)[0].numpy()
        dif_interp = max(dif_interp, float(np.abs(ref - sal.remuestrear(pe[0].numpy(), gh, gw, "bicubico_aa")).max()))
    vit = sal.Dinov2(pt)
    w = {k: v.detach().numpy() for k, v in hm.state_dict().items()}
    filas = [r for r in filas_ueyes() if r["Train/Test"] == "Test"]
    random.Random(1).shuffle(filas)
    casos = []
    for r, tam in zip(filas[:12], [None, (1366, 768), (1024, 768), (375, 812)] * 3):
        im = Image.open(f"ueyesdata/images/{r['Image Name']}").convert("RGB")
        if tam:
            im = im.resize(tam, Image.BICUBIC)
        x, gh, gw = sal.preparar(im)
        with torch.no_grad():
            o = hf(pixel_values=torch.from_numpy(x).permute(2, 0, 1)[None])
            ft = torch.cat([o.hidden_states[i][0, 1:] for i in (8, 12)], -1).reshape(gh, gw, -1).permute(2, 0, 1).half().float()
            lt = hm(ft).exp().numpy()
        fn = vit.rasgos(im)
        ln = np.exp(sal.cabeza(fn, w))
        a, b = lt.ravel() - lt.mean(), ln.ravel() - ln.mean()
        casos.append({"img": r["Image Name"], "rejilla": [gh, gw], "dif_rasgos_max": round(float(np.abs(ft.numpy() - fn).max()), 4),
                      "dif_rasgos_media": round(float(np.abs(ft.numpy() - fn).mean()), 6), "cc_mapa": round(float(a @ b / np.linalg.norm(a) / np.linalg.norm(b)), 6),
                      "dif_mapa_max_rel": round(float(np.abs(lt - ln).max() / lt.max()), 6)})
    return {"dif_pesos_timm_vs_hf": dif_pesos, "dif_interp_pos": dif_interp, "casos": casos,
            "cc_mapa_min": min(c["cc_mapa"] for c in casos)}


def main():
    instalar()
    bajar_ueyes()
    estado(etapa="datos listos")
    extraer_rasgos()
    estado(etapa="rasgos listos")
    Head = definir_modelo()
    met = leer_json("metricas.json") if os.path.exists("metricas.json") else {}
    met["zenodo"] = leer_json("zenodo.json") if os.path.exists("zenodo.json") else None
    for dur in DURACIONES:
        if dur in met:
            continue
        _, m = entrenar(dur, Head)
        met[dur] = m
        escribir_json("metricas.json", met)
        estado(etapa=f"entrenado {dur}", cc=m["lector"]["todo"]["cc"], cc_sesgo=m["sesgo_central"]["todo"]["cc"])
    if "validacion" not in met:
        import torch

        hm = Head()
        hm.load_state_dict(torch.load("cabeza_ueyes_3s.pt"))
        hm.eval()
        met["validacion"] = validar(hm)
        escribir_json("metricas.json", met)
        estado(etapa="validado", cc_mapa_min=met["validacion"]["cc_mapa_min"])
    estado(etapa="fin")


if __name__ == "__main__":
    main()
