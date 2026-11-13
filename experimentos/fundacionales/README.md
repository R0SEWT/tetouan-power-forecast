# Modelos fundacionales y modelo híbrido (SEIN)

Los scripts con que se generaron los pronósticos que evalúa el
[notebook 04](../../notebooks/04_sein_modelos_fundacionales.ipynb). Corren en Colab con GPU (L4 para la inferencia,
A100 para el ajuste fino); el notebook solo lee sus salidas, que están en el Drive en
`reportes/sein/fundacionales/`.

| Script | Qué hace |
|---|---|
| `instalar.sh` | Instala los ocho modelos sin degradar el torch de Colab |
| `adaptadores.py` | Una función por modelo: contextos `[B, C]` → mediana y cuantiles 10 y 90 a 48 pasos |
| `fm_bench.py` | Pronóstico zero-shot desde cada origen (cada 30 min), retomable por bloques |
| `cola.sh` | Corre en serie las líneas `modelo contexto` de una cola |
| `chronos2_variantes.py` | Chronos-2 con covariables (1: temperatura y feriados; 2: solo feriados; 3: calendario ampliado) o con pesos ajustados |
| `ajuste_fino.py` | Ajuste fino de Chronos-2 con la demanda hasta 2024 (comprueba el corte con un `assert`; acepta semilla) |
| `apilar.py` | XGBoost global en razón con el pronóstico fundacional como variable |

## Cómo reproducir

En la VM, con `demanda_areas.parquet` y `temperatura_areas.parquet` (capas silver) en `/content/datos/` y los
scripts en `/content/`:

```bash
bash instalar.sh
python fm_bench.py simons 2048 2025-01-01 2026-10-23          # validación y prueba → /content/fm/simons_c2048.parquet
python fm_bench.py simons 2048 2016-03-01 2025-01-01 train    # orígenes de entrenamiento, para el apilado
python chronos2_variantes.py chronos2cal amazon/chronos-2 2 2025-01-01 2026-10-23   # solo feriados
python ajuste_fino.py ft_cal 1e-6 3000 full 2                 # ajuste fino con feriados, datos ≤ 2024
python ajuste_fino.py ft_cal_s2 1e-6 3000 full 2 2            # la misma receta con otra semilla (la original usó 42)
python chronos2_variantes.py chronos2ftcal /content/ft/ft_cal/finetuned-ckpt 2 2025-01-01 2026-10-23
python apilar.py simons                                       # lee las dos salidas de Simons de /content/fm/; necesita el repo en /content/tpf y las capas en /content/datalake
```

Cada corrida deja un parquet con una fila por origen y área: `DateTime` (el origen), `area`, `pred_2`, `q10_2`,
`q90_2`, `pred_48`, `q10_48` y `q90_48`. La evaluación está en `tetouan_power_forecast.fundacionales`.

## Versiones y licencias

Colab con Python 3.13, torch 2.14.1 y numpy 2.4.6.

| Modelo | Paquete | Pesos | Licencia de los pesos |
|---|---|---|---|
| Chronos-2 | `chronos-forecasting` 2.3.2 | `amazon/chronos-2` | Apache-2.0 |
| Simons | `simons` 0.1.1 | `abel-lab/Simons-297M` | OpenMDW-1.1 |
| Timestral | `timestral` 1.0.0 | `mistralai/Timestral-209M` | MIT modificada (limita el uso en empresas grandes) |
| T0-gamma | `tfc-t0` 0.6.1 | `theforecastingcompany/t0-gamma` | Apache-2.0 |
| Toto 2.0 | `toto-2` 2.0.0 | `Datadog/Toto-2.0-313m` | Apache-2.0 |
| TimesFM 2.5 | `timesfm` 3.0.2 | `google/timesfm-2.5-200m-pytorch` | Apache-2.0 |
| TimesFM 3.0 | `timesfm` 3.0.2 | `google/timesfm-3.0-pytorch` | No comercial (aquí, uso académico) |
| TiRex-2 | `tirex-2` 0.5.0 | `NX-AI/TiRex-2` | Apache-2.0 |

## Notas

- El contexto es la demanda del área hasta el origen; los 336 huecos de la capa silver se interpolan.
- La temperatura futura que se da como covariable es el pronóstico simulado del proyecto (observada más un error
  de 1.5 °C por día de emisión), nunca la observada.
- El ajuste fino y el apilado se entrenan con datos hasta 2024. Las variantes se comparan en 2025.
