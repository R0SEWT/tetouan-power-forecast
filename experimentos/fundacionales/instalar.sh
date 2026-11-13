# Instala los ocho modelos en la VM de Colab (Python 3.13, torch 2.14.1) sin degradar torch ni numpy.
# Todo va con --no-deps: varios paquetes fijan versiones de torch más viejas que la de Colab.
set -x
pip install -q --no-deps "chronos-forecasting==2.3.2" "timesfm==3.0.2" "tirex-2==0.5.0" "tfc-t0==0.6.1" "toto-2==2.0.0"
pip install -q --no-deps "git+https://github.com/mistralai/timestral.git"   # timestral 1.0.0
pip install -q --no-deps "git+https://github.com/Abel-ai-lab/Simons"       # simons 0.1.1
pip install -q --no-deps jaxtyping rotary-embedding-torch dd-unit-scaling unit-scaling wadler-lindig gluonts toolz lightning torchmetrics
pip install -q holidays peft
