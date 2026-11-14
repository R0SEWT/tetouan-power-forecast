"""Atención predicha sobre capturas de interfaz, en numpy (sin torch).

Modelo: lector de saliencia sobre rasgos congelados de DINOv2 ViT-S/14 (Oquab et al., 2023), entrenado
con las miradas de UEyes (Jiang et al., CHI 2023), con el mismo diseño que el lector de R0SEWT/myPage
(site/audit/ueyes_train.py): rasgos de las capas 8 y 12, cabeza convolucional pequeña y un prior de
posición aprendido. La cabeza se entrena en Colab (`entrenar_colab.py`) y sus pesos viven en `modelo/`;
aquí solo se aplica, de modo que la medición corre en la laptop con numpy, scipy y Pillow.

Backbone: `timm/vit_small_patch14_dinov2.lvd142m` (Apache-2.0), los mismos pesos que
`facebook/dinov2-small`. `entrenar_colab.py` comprueba que esta implementación reproduce la de
`transformers` (rasgos y mapas) antes de exportar la cabeza.
"""

from __future__ import annotations

import glob
import json
import os
import struct
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.special import erf

MEDIA = np.array([0.485, 0.456, 0.406], np.float32)
DESV = np.array([0.229, 0.224, 0.225], np.float32)
AREA = 448 * 448
PARCHE = 14
CAPAS = (8, 12)
CABEZAS = 6
REPO_TIMM = "timm/vit_small_patch14_dinov2.lvd142m"
URL_TIMM = f"https://huggingface.co/{REPO_TIMM}/resolve/main/model.safetensors"
DIR_MODELO = Path(__file__).resolve().parent / "modelo"


# ---------- pesos ----------

def leer_safetensors(ruta: str | os.PathLike) -> dict[str, np.ndarray]:
    """Lee un .safetensors con numpy (solo F32/F16), sin depender del paquete safetensors."""
    with open(ruta, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        cab = json.loads(f.read(n))
        datos = f.read()
    tipos = {"F32": np.float32, "F16": np.float16}
    out = {}
    for k, v in cab.items():
        if k == "__metadata__":
            continue
        a, b = v["data_offsets"]
        out[k] = np.frombuffer(datos[a:b], dtype=tipos[v["dtype"]]).reshape(v["shape"]).astype(np.float32)
    return out


def ruta_backbone() -> Path:
    """Busca los pesos de DINOv2-S en la caché de Hugging Face; si no están, los baja una vez (~85 MB)."""
    if os.environ.get("DINOV2_PESOS"):
        return Path(os.environ["DINOV2_PESOS"])
    hf = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    patron = hf / f"models--{REPO_TIMM.replace('/', '--')}" / "snapshots" / "*" / "model.safetensors"
    hallados = sorted(glob.glob(str(patron)))
    if hallados:
        return Path(hallados[0])
    destino = Path.home() / ".cache" / "tpf-atencion" / "dinov2_vits14.safetensors"
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        print(f"Descargando {URL_TIMM} (~85 MB, una sola vez)…", flush=True)
        urllib.request.urlretrieve(URL_TIMM, destino.with_suffix(".tmp"))
        destino.with_suffix(".tmp").rename(destino)
    return destino


# ---------- remuestreo idéntico al de torch.nn.functional.interpolate ----------

def _cubica_aa(x: np.ndarray, a: float = -0.5) -> np.ndarray:
    x = np.abs(x)
    return np.where(x < 1, ((a + 2) * x - (a + 3)) * x * x + 1, np.where(x < 2, (((x - 5) * x + 8) * x - 4) * a, 0.0))


def pesos_bicubico_aa(n_in: int, n_out: int) -> np.ndarray:
    """Matriz (n_out, n_in) de interpolate(mode='bicubic', antialias=True, align_corners=False)."""
    escala = n_in / n_out
    soporte = 2.0 * max(escala, 1.0)
    inv = 1.0 / max(escala, 1.0)
    m = np.zeros((n_out, n_in), np.float64)
    for i in range(n_out):
        c = escala * (i + 0.5)
        x0 = max(int(c - soporte + 0.5), 0)
        x1 = min(int(c + soporte + 0.5), n_in)
        j = np.arange(x0, x1)
        w = _cubica_aa((j - c + 0.5) * inv)
        m[i, x0:x1] = w / w.sum()
    return m


def pesos_bilineal(n_in: int, n_out: int) -> np.ndarray:
    """Matriz (n_out, n_in) de interpolate(mode='bilinear', align_corners=False), sin antialias."""
    escala = n_in / n_out
    m = np.zeros((n_out, n_in), np.float64)
    for i in range(n_out):
        s = max(escala * (i + 0.5) - 0.5, 0.0)
        i0 = min(int(s), n_in - 1)
        i1 = min(i0 + 1, n_in - 1)
        lam = s - i0
        m[i, i0] += 1 - lam
        m[i, i1] += lam
    return m


def remuestrear(a: np.ndarray, alto: int, ancho: int, modo: str = "bilineal") -> np.ndarray:
    """Remuestrea las dos últimas dimensiones de `a` (…, h, w) a (alto, ancho)."""
    f = pesos_bilineal if modo == "bilineal" else pesos_bicubico_aa
    mh = f(a.shape[-2], alto).astype(np.float32)
    mw = f(a.shape[-1], ancho).astype(np.float32)
    return np.einsum("ih,...hw,jw->...ij", mh, a.astype(np.float32), mw, optimize=True)


# ---------- DINOv2 ViT-S/14 ----------

def _ln(x, g, b, eps=1e-6):
    m = x.mean(-1, keepdims=True)
    v = ((x - m) ** 2).mean(-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps) * g + b


def _gelu(x):
    return 0.5 * x * (1.0 + erf(x / np.sqrt(2.0)))


def _softmax(x, eje=-1):
    x = x - x.max(eje, keepdims=True)
    e = np.exp(x)
    return e / e.sum(eje, keepdims=True)


def preparar(im: Image.Image) -> tuple[np.ndarray, int, int]:
    """Igual que myPage: lleva la imagen a ~448² px de área conservando la proporción, en múltiplos de 14."""
    w, h = im.size
    s = (AREA / (w * h)) ** 0.5
    ancho = max(PARCHE, round(w * s / PARCHE) * PARCHE)
    alto = max(PARCHE, round(h * s / PARCHE) * PARCHE)
    x = np.asarray(im.convert("RGB").resize((ancho, alto), Image.BICUBIC), np.float32) / 255
    return (x - MEDIA) / DESV, alto // PARCHE, ancho // PARCHE


class Dinov2:
    def __init__(self, pesos: dict[str, np.ndarray]):
        self.p = pesos
        self.n_bloques = 1 + max(int(k.split(".")[1]) for k in pesos if k.startswith("blocks."))

    def rasgos(self, im: Image.Image) -> np.ndarray:
        """Rasgos (768, gh, gw): salidas de los bloques 8 y 12 sin el token CLS, redondeadas a fp16 como en myPage."""
        p = self.p
        x, gh, gw = preparar(im)
        d = p["cls_token"].shape[-1]
        parches = x.reshape(gh, PARCHE, gw, PARCHE, 3).transpose(0, 2, 4, 1, 3).reshape(gh * gw, -1)
        t = parches @ p["patch_embed.proj.weight"].reshape(d, -1).T + p["patch_embed.proj.bias"]
        pe = p["pos_embed"][0]
        lado = round((pe.shape[0] - 1) ** 0.5)
        rejilla = pe[1:].reshape(lado, lado, d).transpose(2, 0, 1)
        rejilla = remuestrear(rejilla, gh, gw, modo="bicubico_aa").transpose(1, 2, 0).reshape(gh * gw, d)
        t = np.concatenate([p["cls_token"][0] + pe[:1], t + rejilla], 0).astype(np.float32)
        salidas = {}
        dh = d // CABEZAS
        for i in range(self.n_bloques):
            b = f"blocks.{i}."
            h = _ln(t, p[b + "norm1.weight"], p[b + "norm1.bias"])
            qkv = (h @ p[b + "attn.qkv.weight"].T + p[b + "attn.qkv.bias"]).reshape(-1, 3, CABEZAS, dh).transpose(1, 2, 0, 3)
            q, k, v = qkv[0], qkv[1], qkv[2]
            a = _softmax(q @ k.transpose(0, 2, 1) * dh**-0.5)
            o = (a @ v).transpose(1, 0, 2).reshape(-1, d)
            t = t + p[b + "ls1.gamma"] * (o @ p[b + "attn.proj.weight"].T + p[b + "attn.proj.bias"])
            h = _ln(t, p[b + "norm2.weight"], p[b + "norm2.bias"])
            h = _gelu(h @ p[b + "mlp.fc1.weight"].T + p[b + "mlp.fc1.bias"]) @ p[b + "mlp.fc2.weight"].T + p[b + "mlp.fc2.bias"]
            t = (t + p[b + "ls2.gamma"] * h).astype(np.float32)
            if i + 1 in CAPAS:
                salidas[i + 1] = t[1:]
        f = np.concatenate([salidas[c] for c in CAPAS], -1).reshape(gh, gw, -1).transpose(2, 0, 1)
        return f.astype(np.float16).astype(np.float32)


# ---------- cabeza entrenada sobre UEyes ----------

def _conv3(x, w, b):
    c, h, ww = x.shape
    xp = np.pad(x, ((0, 0), (1, 1), (1, 1)))
    cols = np.stack([xp[:, i:i + h, j:j + ww] for i in range(3) for j in range(3)], 1).reshape(c * 9, h * ww)
    return (w.reshape(w.shape[0], -1) @ cols + b[:, None]).reshape(-1, h, ww)


def cabeza(f: np.ndarray, w: dict[str, np.ndarray]) -> np.ndarray:
    """log-probabilidad (gh, gw) de fijación, como Head.forward de myPage."""
    gh, gw = f.shape[1:]
    x = remuestrear(w["bias.b"][0, 0], gh, gw, modo="bilineal")
    y = w["net.0.weight"][:, :, 0, 0] @ f.reshape(f.shape[0], -1) + w["net.0.bias"][:, None]
    y = _gelu(y).reshape(-1, gh, gw)
    y = _gelu(_conv3(y, w["net.2.weight"], w["net.2.bias"]))
    y = _conv3(y, w["net.4.weight"], w["net.4.bias"])[0]
    z = (x + y).ravel()
    z = z - z.max()
    return (z - np.log(np.exp(z).sum())).reshape(gh, gw)


class Lector:
    """Aplica el lector UEyes a una captura y devuelve un mapa de atención (alto, ancho) que suma 1."""

    def __init__(self, duracion: str = "3s", backbone: str | os.PathLike | None = None):
        self.duracion = duracion
        self.vit = Dinov2(leer_safetensors(backbone or ruta_backbone()))
        datos = np.load(DIR_MODELO / f"cabeza_ueyes_{duracion}.npz")
        self.w = {k: datos[k].astype(np.float32) for k in datos.files}

    def rejilla(self, im: Image.Image) -> np.ndarray:
        return np.exp(cabeza(self.vit.rasgos(im), self.w))

    def mapa(self, im: Image.Image) -> np.ndarray:
        r = self.rejilla(im)
        m = np.clip(remuestrear(r, im.size[1], im.size[0], modo="bilineal"), 0, None)
        return m / m.sum()
