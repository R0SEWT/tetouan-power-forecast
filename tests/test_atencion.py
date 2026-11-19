"""El lector de atención en numpy (app/medicion/atencion): remuestreo, cabeza y utilidades del análisis.

La equivalencia completa con torch/transformers (rasgos y mapas, CC ≥ 0.9997) se comprueba en Colab al entrenar
(`entrenar_colab.py`, guardada en `modelo/metricas.json`); aquí se fija lo que no necesita los pesos de DINOv2.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

DIR = Path(__file__).resolve().parents[1] / "app" / "medicion" / "atencion"
sys.path.insert(0, str(DIR))

import analizar
import saliencia


def test_bicubico_aa_identidad_y_filas_que_suman_uno():
    assert np.allclose(saliencia.pesos_bicubico_aa(37, 37), np.eye(37))
    for n_out in (22, 24, 28, 43, 47):
        m = saliencia.pesos_bicubico_aa(37, n_out)
        assert m.shape == (n_out, 37)
        assert np.allclose(m.sum(1), 1)


def test_bilineal_como_torch_align_corners_false():
    # torch.nn.functional.interpolate([0, 1], size=4, mode='linear', align_corners=False) == [0, .25, .75, 1]
    m = saliencia.pesos_bilineal(2, 4)
    assert np.allclose(m @ np.array([0.0, 1.0]), [0, 0.25, 0.75, 1])
    # y al reducir no extrapola
    assert np.allclose(saliencia.pesos_bilineal(4, 2) @ np.arange(4.0), [0.5, 2.5])


def test_cabeza_da_una_distribucion_sobre_la_rejilla():
    z = np.load(saliencia.DIR_MODELO / "cabeza_ueyes_3s.npz")
    w = {k: z[k].astype(np.float32) for k in z.files}
    f = np.random.default_rng(0).normal(size=(768, 24, 43)).astype(np.float32)
    lp = saliencia.cabeza(f, w)
    assert lp.shape == (24, 43)
    assert np.isclose(np.exp(lp).sum(), 1, atol=1e-5)


def test_modelo_entrenado_y_validado():
    m = json.loads((saliencia.DIR_MODELO / "metricas.json").read_text())
    for d in ("1s", "3s", "7s"):
        assert m[d]["lector"]["todo"]["cc"] > m[d]["sesgo_central"]["todo"]["cc"] + 0.1
    assert m["validacion"]["dif_pesos_timm_vs_hf"] == 0
    assert m["validacion"]["cc_mapa_min"] > 0.999


def test_lee_safetensors(tmp_path):
    a = np.arange(6, dtype=np.float32).reshape(2, 3)
    cab = json.dumps({"x": {"dtype": "F32", "shape": [2, 3], "data_offsets": [0, a.nbytes]}}).encode()
    ruta = tmp_path / "m.safetensors"
    ruta.write_bytes(len(cab).to_bytes(8, "little") + cab + a.tobytes())
    assert np.array_equal(saliencia.leer_safetensors(ruta)["x"], a)


def test_cifras_separa_magnitudes_horas_y_fechas():
    k = analizar.cifras("Ahora · 21:30 4,880 MW rango 4,806 – 4,953 datos al 12/11, +325 y 91.1 %")
    assert k == {"magnitudes": 5, "horas": 1, "fechas": 1}


def test_raices_y_colores():
    assert analizar.raices("Repasar un día") == {"repas", "dia"}
    assert analizar.color_rgba("rgba(42, 120, 214, 0.16)") == (42, 120, 214, 0.16)
    assert analizar.color_rgba("color(srgb 0.5 0.5 0.5)") is None


@pytest.mark.skipif(not list((Path.home() / ".cache" / "huggingface" / "hub").glob("models--timm--vit_small_patch14_dinov2*")),
                    reason="sin los pesos de DINOv2-S en la caché local")
def test_lector_completo_en_una_captura_sintetica():
    from PIL import Image

    im = Image.new("RGB", (375, 812), "white")
    mapa = saliencia.Lector("3s").mapa(im)
    assert mapa.shape == (812, 375)
    assert np.isclose(mapa.sum(), 1)


def test_mascara_ignora_cajas_fuera_de_la_ventana():
    # el enlace «Saltar al contenido» vive en y < 0: no puede marcar media pantalla
    assert not analizar.mascara([[12, -60, 191, -13]], 375, 812).any()
    assert analizar.mascara([[0, -10, 10, 10]], 375, 812).sum() == 100
    assert analizar.area_cajas([[0, 0, 10, 10], [5, 5, 15, 15]]) == 175
