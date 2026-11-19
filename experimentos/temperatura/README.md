# Temperatura pronosticada a un día con umbral (SEIN)

Pregunta: ¿la temperatura **pronosticada** del día objetivo, con un efecto de umbral (enfriamiento sobre ~23 °C de
media en Lima), reduce el error del **pico diario del Centro** en los días cálidos sin empeorar el resto? Lo que se
elige se elige con 2025; 2026 (hasta el 22-oct) y el tramo en vivo (23-oct → último día con real) solo se reportan.
Informe: `temperatura-pronosticada-2026-11.md` (fuera del repo, en la carpeta personal del dueño).

## Piezas

| Archivo | Qué hace | Dónde corre |
|---|---|---|
| `descarga.py` | Baja el archivo de Open-Meteo (Previous Runs API): GFS desde marzo de 2021 y «best match» desde 2024, una consulta por modelo y año | Local (~14 MB) |
| `fuente.py` | Umbral de cada área con 2016–2024 y elección de la fuente con 2025 | Local |
| `comun.py` | Variables de temperatura de cada origen: edición vigente, nivel ERA5, grados sobre el umbral | Local |
| `apilar_temperatura.py` | (a) XGBoost híbrido con Simons + temperatura (observada, mixta o solo grados) | Colab (L4, ~1 min) |
| `chronos_cdd.py` | (c) Chronos-2 reajustado con feriados + grados sobre el umbral como covariable futura. **No tiene resultados:** la sesión de Colab se cayó antes de terminar | Colab (A100, ~30 min de ajuste y ~60 de pronóstico) |
| `correccion.py` | (b) Corrección monótona sobre Chronos-2 ajustado: fija (errores zero-shot 2016–2024) o en línea (errores desde 2025) | Local |
| `panel.py`, `evaluar.py` | Panel de 2025, 2026 y en vivo; pico diario, días cálidos e IC por semanas | Local |
| `graficos.py` | Los cuatro gráficos del informe | Local |

La lógica que también usa el modo en vivo (descarga con caché, ajuste de nivel, edición vigente, β en línea) está en
`src/tetouan_power_forecast/temperatura_pronosticada.py`; el modelo en paralelo, en `en_vivo.emitir_calor`.

## Regla de información

El desfase N de Open-Meteo para la hora v sale de una corrida iniciada a más tardar en v − 24·N h. Con una demora de
publicación de 8 h, en el origen t vale la **edición vigente** del día objetivo: a 24 h, el desfase 2 desde las 07:00
del día anterior y el 3 antes; a 1 h, el desfase 1 desde las 07:00 del mismo día y el 2 antes. La corrección en línea
usa solo errores de días objetivo ya cerrados al emitir (a 24 h, hasta X − 2).

## Cómo reproducir

Con `TETOUAN_DATA` apuntando a la carpeta de datos y el entorno del proyecto:

```bash
export PYTHONPATH=$PWD/src:$PWD
python -m experimentos.temperatura.descarga --hasta 2026-11-20   # archivo de Open-Meteo
python -m experimentos.temperatura.fuente                        # umbral.csv y fuente.csv
python - <<'EOF'                                                 # variables de cada origen (observada y pronosticada)
import pandas as pd
from experimentos.temperatura import comun as c
origenes = pd.date_range("2016-03-01", "2026-11-20", freq="30min")
for fuente in ("observada", "pronostico"):
    c.guardar(c.tabla_variables(origenes, fuente), f"variables_{fuente}.parquet")
c.cdd_por_edicion().to_parquet("cdd_por_edicion.parquet", index=False)
EOF
```

En Colab (`colab new -s tstk --gpu L4` y `colab new -s tft --gpu A100`), con el repo en `/content/tpf`, las capas en
`/content/datalake` (silver de demanda con la capa en vivo, exógenas y `reportes/sein/temperatura/variables_*.parquet`),
la serie completa de demanda y `cdd_por_edicion.parquet` en `/content/datos/` y los Simons guardados en `/content/fm/`:

```bash
python fm_bench.py simons 2048 2026-10-22 2026-11-20 vivo         # Simons del tramo en vivo
python experimentos/temperatura/apilar_temperatura.py             # (a) → /content/stk_temp/*_c2048.parquet
python chronos_cdd.py ajuste && python chronos_cdd.py pronostico 2025-01-01 2026-11-20   # (c)
```

Todo lo largo se lanza desacoplado (`subprocess.Popen(..., start_new_session=True)`) y se consulta cada pocos minutos.
Las salidas van a `reportes/sein/temperatura/pronosticos/`. Luego, en local:

```bash
python -m experimentos.temperatura.evaluar      # comparacion.csv, diario.parquet, betas y pesos
python -m experimentos.temperatura.graficos DESTINO
```

## Resultados

En `reportes/sein/temperatura/` de la carpeta de datos (y en el Drive, `datalake/tetouan-power-forecast/reportes/sein/temperatura/`):
`comparacion.csv` (cada modelo frente a su base y a Chronos-2 ajustado, por tramo, horizonte, área y grupo de días, con
IC), `diario.parquet` (una fila por día y modelo), `umbral.csv`, `fuente.csv`, `betas_fijas.csv`, `betas_en_linea.csv`,
`pesos_combinaciones.csv` y los pronósticos por origen en `pronosticos/`.
