# Validación externa en Ceuta

¿Cuánto histórico hace falta para pronosticar un verano a una hora? Tetuán tiene un solo año y no lo puede
responder. Ceuta, un sistema aislado a menos de 40 km, tiene la demanda de REE desde 2019 (ver
[`docs/historico.md`](../../docs/historico.md), opción 8).

`validacion.py` entrena con cuatro historias que terminan el 30 de junio de cada año y evalúa julio y agosto,
de 2020 a 2026:

| Historia | Qué representa |
|---|---|
| `sin_verano` | Enero a junio del mismo año: el modelo nunca vio un verano, como la Zona 3 de Tetuán |
| `1_anio`, `2_anios`, `3_anios` | Los 12, 24 o 36 meses anteriores: uno, dos o tres veranos previos |

Compara el modelo en nivel con calendario anual (V0) con el objetivo en razón sin calendario anual (V4) y con
las tres referencias ingenuas. El verano de 2020, con el confinamiento, se reporta aparte.

## Cómo correrlo

En Colab, con [`notebooks/00b_ceuta.ipynb`](../../notebooks/00b_ceuta.ipynb). Baja los datos al Drive, arma el
silver y corre la validación. La primera descarga hace unas 2,700 consultas a REE (~1 h, ~105 MB), así que
conviene no hacerla en local.

Si las capas ya están en `data/ceuta/`:

```bash
uv run python -m experimentos.ceuta.validacion
```

Escribe `reportes/ceuta/resultados_validacion.csv` dentro de la carpeta de datos.

## Ceuta y Tetuán en 2017

`comparar_2017.py` baja de REData, la API oficial de REE, la demanda horaria de Ceuta de 2017 (12
consultas, unos 700 KB) y la compara con las tres zonas: escala, estacionalidad, correlaciones, fin de
semana, feriados de cada país y Ramadán. Solo necesita el silver de Tetuán, así que se puede correr en
local:

```bash
uv run python -m experimentos.ceuta.comparar_2017
```

Guarda las respuestas en `ceuta/bronze/redata/` y la tabla en `reportes/ceuta/comparacion_2017.csv`. La
forma diaria se parece a la de las zonas 1 y 2, pero no son la misma serie: cada una tiene los feriados y
el fin de semana de su país.

## Resultado

Corrida del 23 de octubre de 2026. MAPE (%) medio de julio y agosto de 2022 a 2026, los veranos con las
cuatro historias:

| Historia | V0, nivel con calendario anual | V4, razón sin calendario anual |
|---|---:|---:|
| `sin_verano` | 2.93 | 2.33 |
| `1_anio` | 2.12 | 1.94 |
| `2_anios` | 1.98 | 1.84 |
| `3_anios` | 1.97 | 1.82 |

La mejor referencia ingenua promedia 4.63 %. V4 le gana a V0 en los 25 pares de verano e historia, y todos
los modelos le ganan a la mejor ingenua en todos los veranos. Sin haber visto un verano, V4 pierde 0.39
puntos (un 20 % más de error); V0, 0.81 (38 %). Más de un año de historia aporta poco. La tabla por verano
y lo que significa para Tetuán están en
[`docs/historico.md`](../../docs/historico.md#resultado-de-la-validación-externa).

## Alcance

- **Ceuta es otro sistema**, con otra mezcla de clientes. Lo que se aprende ahí es evidencia indirecta sobre
  Tetuán, no una validación sobre Amendis.
- **El clima es ERA5 (Open-Meteo)**, no una estación local. Las dos variables de radiación se mapean a las
  columnas de radiación difusa de Tetuán solo para reutilizar el pipeline.
- **Las fechas del Ramadán son aproximadas, y no hay una lista verificada de los feriados de Ceuta**, así que
  esa variable queda en 0.
- **Los datos de REE no se suben a ningún repositorio:** su aviso legal solo permite usos académicos que
  citen la fuente.
