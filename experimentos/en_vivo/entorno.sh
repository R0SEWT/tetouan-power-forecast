#!/usr/bin/env bash
# Prepara el entorno de la tubería en vivo en ~/.cache/tpf-vivo (fuera del repo y fuera de /tmp):
#   venv/                                  Python 3.13 con torch para CPU, chronos-forecasting 2.3.2, holidays,
#                                          pandas, pyarrow y openpyxl (las versiones con que se verificó)
#   pesos/chronos2ftcal/finetuned-ckpt/    Chronos-2 ajustado con feriados (478 MB), extraído de chronos2ftcal.tar
#
# torch pesa ~180 MB de descarga: si ya está instalado en otro entorno de la máquina, TORCH_DESDE lo enlaza (cp -al,
# sin copiar ni descargar). Si no, se baja de la rueda para CPU de PyTorch.
#
#   experimentos/en_vivo/entorno.sh RUTA/chronos2ftcal.tar
#   TORCH_DESDE=/ruta/a/otro/.venv/lib/python3.13/site-packages experimentos/en_vivo/entorno.sh RUTA/chronos2ftcal.tar
set -euo pipefail
base="${TPF_VIVO:-$HOME/.cache/tpf-vivo}"
tar_pesos="${1:?Uso: entorno.sh RUTA/chronos2ftcal.tar}"
venv="$base/venv"
sp="$venv/lib/python3.13/site-packages"

[[ -x "$venv/bin/python" ]] || uv venv "$venv" --python 3.13
if ! "$venv/bin/python" -c "import torch" 2>/dev/null; then
  if [[ -n "${TORCH_DESDE:-}" ]]; then
    for p in "$TORCH_DESDE"/torch "$TORCH_DESDE"/torch-*.dist-info "$TORCH_DESDE"/torchgen "$TORCH_DESDE"/functorch; do
      cp -al "$p" "$sp/" 2>/dev/null || cp -a "$p" "$sp/"
    done
  else
    uv pip install --python "$venv/bin/python" --index-url https://download.pytorch.org/whl/cpu "torch==2.14.*"
  fi
fi
# Con torch ya instalado, uv lo respeta y no lo vuelve a bajar
uv pip install --python "$venv/bin/python" "chronos-forecasting==2.3.2" "transformers==5.16.1" "holidays==0.108" \
  "pandas==3.1.1" "pyarrow==26.0.1" "numpy==2.5.4" openpyxl

mkdir -p "$base/pesos/chronos2ftcal"
if [[ ! -f "$base/pesos/chronos2ftcal/finetuned-ckpt/model.safetensors" ]]; then
  tar xf "$tar_pesos" -C "$base/pesos/chronos2ftcal"
fi
sha256sum "$base/pesos/chronos2ftcal/finetuned-ckpt/model.safetensors"
"$venv/bin/python" -c "import torch, chronos; print('torch', torch.__version__, '· chronos', chronos.__version__ if hasattr(chronos, '__version__') else '2.3.2')"
