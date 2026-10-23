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

## Alcance

- **Ceuta es otro sistema**, con otra mezcla de clientes. Lo que se aprende ahí es evidencia indirecta sobre
  Tetuán, no una validación sobre Amendis.
- **El clima es ERA5 (Open-Meteo)**, no una estación local. Las dos variables de radiación se mapean a las
  columnas de radiación difusa de Tetuán solo para reutilizar el pipeline.
- **Las fechas del Ramadán son aproximadas, y no hay una lista verificada de los feriados de Ceuta**, así que
  esa variable queda en 0.
- **Los datos de REE no se suben a ningún repositorio:** su aviso legal solo permite usos académicos que
  citen la fuente.
