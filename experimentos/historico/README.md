# Experimentos: cómo sortear el año único de histórico

Los scripts que respaldan las cifras de [`docs/historico.md`](../../docs/historico.md). Todos leen el
silver del medallón y guardan sus resultados en `<datos>/reportes/historico/`. En local, `<datos>` es
`data/`; en Colab, la carpeta del Drive.

| Script | Qué compara | Tiempo aproximado |
|---|---|---|
| `rolling` | Objetivo en nivel, cambio y razón, con y sin calendario anual, con origen móvil mensual y en la prueba | ~1.5 min por serie |
| `global_model` | Un modelo para las tres zonas frente a uno por zona | Algunos minutos |
| `quiebre` | El efecto de la transferencia del 25 de octubre y de reentrenar cada semana | Algunos minutos |
| `lomo` | El verano con el mes fuera, con margen (cota optimista) | ~20 s |
| `cuota` | La cuota de la Zona 1 dentro de Zona 1 + Zona 2: punto de quiebre, días en espejo y detector | Segundos |

Los tiempos se midieron en una máquina de 8 núcleos con `OMP_NUM_THREADS=8`. Si se corren varios a la
vez, conviene bajar los hilos de cada uno, o usar Colab.

## En local

Desde la raíz del repo, con las capas en `data/` (`uv run tetouan all`):

```bash
uv run python -m experimentos.historico.rolling Z1,Z2,Z3,S12
uv run python -m experimentos.historico.global_model
uv run python -m experimentos.historico.quiebre
uv run python -m experimentos.historico.lomo
uv run python -m experimentos.historico.cuota
```

`rolling` acepta las series que se quieran correr: `Z1`, `Z2`, `Z3` y `S12` (la suma de la Zona 1 y la
Zona 2).

## En Colab

```python
!git clone -q -b develop https://github.com/R0SEWT/tetouan-power-forecast
%cd tetouan-power-forecast
!pip install -q -e .

import os, sys
sys.path[:0] = [os.path.abspath("src"), os.path.abspath(".")]  # el kernel no lee el .pth editable

from tetouan_power_forecast.medallon import usar_drive
usar_drive()  # las capas y los resultados quedan en el Drive

!python -m experimentos.historico.rolling Z1,Z2,Z3,S12
```

## Alcance

- **Es una prueba rápida:** un solo `HistGradientBoostingRegressor` con hiperparámetros fijos, sin
  búsqueda y con una semilla.
- **La variante `V0_repo_nivel` reproduce las variables del gold**, no el notebook del grupo.
- **Lo robusto es la dirección y el tamaño relativo de los efectos.** Las cifras finales salen del
  notebook de modelado.
- **Las fechas de los feriados y del Ramadán son aproximadas.**
