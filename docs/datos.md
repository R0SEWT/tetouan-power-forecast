# Datos

## Procedencia

| | |
|---|---|
| Dataset | [*Power Consumption of Tetouan City*](https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city), UCI Machine Learning Repository, ID 849 |
| Autores | Abdulwahed Salam y Abdelaaziz El Hibaoui (2018), [doi:10.24432/C5B034](https://doi.org/10.24432/C5B034) |
| Licencia | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Origen | SCADA de **Amendis**, el operador del servicio público de distribución de agua y electricidad de Tetuán desde 2002. La energía llega de la ONEE (Office National de l'Électricité et de l'Eau Potable) en alta tensión (63 kV), se transforma a media tensión (20 kV) y se distribuye a clientes de baja y media tensión. |
| Cobertura | Un registro cada 10 minutos, del 1 de enero al 30 de diciembre de 2017 (el 31 de diciembre no viene) |

UCI solo describe las zonas como "zone 1/2/3 of Tetouan city" y no da unidades. El origen en Amendis,
las subestaciones y la unidad (kW) vienen de la descripción del dataset que circula en Kaggle y en
repositorios que lo usan, no de una fuente primaria. Sirven como contexto, pero hay que citarlos como tal.

## Las tres zonas

La red se alimenta de tres subestaciones: **Quads, Smir y Boussafou**. Ninguna fuente primaria dice
qué subestación corresponde a cada zona. Circulan dos asignaciones que se contradicen, las dos sin
respaldo: Zona 1 = Quads, Zona 2 = Smir y Zona 3 = Boussafou (en varios artículos) y Zona 1 = Quads,
Zona 2 = Boussafou y Zona 3 = Smir (en un artículo de divulgación). Ninguna **está confirmada**; ver el
[estado del arte](estado-del-arte.md#4-identidad-de-las-zonas).

Los datos son coherentes con que la Zona 3 sea Smir, la zona costera y turística: es la que más sube en
julio y agosto, la única cuyo consumo no baja el fin de semana y la que más cae fuera de temporada.
Es un indicio, no una prueba. Las cifras y el razonamiento completo están en la
[investigación](investigacion.md).

## Variables

| Variable | Descripción | Unidad |
|---|---|---|
| `DateTime` | Inicio del periodo de 10 minutos | — |
| `Temperature` | Temperatura de la ciudad | °C |
| `Humidity` | Humedad relativa | % |
| `Wind Speed` | Velocidad del viento | sin unidad en la fuente |
| `general diffuse flows` | Radiación solar difusa general | sin unidad en la fuente |
| `diffuse flows` | Radiación solar difusa | sin unidad en la fuente |
| `Zone 1/2/3 Power Consumption` | Consumo de cada zona | kW (según fuentes secundarias) |

## Capas

El pipeline (`src/tetouan_power_forecast/medallon.py`) arma tres capas en `data/`, que no se versiona:

| Capa | Archivo | Qué es |
|---|---|---|
| bronze | `bronze/uci849_tetouan.csv` y `.json` | El CSV tal como lo sirve UCI, sin tocar, más su procedencia: URL, DOI, licencia, fecha de descarga y sha256. Al reutilizarlo se comprueba el sha256. |
| silver | `silver/tetouan_2017.parquet` y `auditoria.md` | Columnas normalizadas, `DateTime` como fecha y orden cronológico. Pasa una auditoría (columnas, cobertura completa del periodo, nulos, infinitos, duplicados, continuidad cada 10 minutos, rangos físicos) que corta el pipeline si algo falla. |
| gold | `gold/t6_zona{1,2,3}.parquet` | El dataset t+6 de una zona: calendario con codificación cíclica, rezagos, estadísticas móviles y la columna `particion` (70/15/15 cronológico). Las 6 filas anteriores a cada corte quedan como `hueco`, porque su objetivo cae en la partición siguiente: no se usan ni para entrenar ni para evaluar. |

```bash
uv run tetouan all             # bronze, silver y gold de la Zona 1
uv run tetouan gold --zona 3   # el gold de otra zona
uv run tetouan silver --forzar # rehace una capa aunque ya exista
```

Cada capa se reutiliza si ya existe. Conviene, porque UCI tarda varios minutos en servir el CSV.

## Dónde viven: Google Drive + Colab

Las capas compartidas viven en Google Drive, en `Mi unidad/datalake/tetouan-power-forecast/`, y se
procesan en Colab con [`notebooks/00_medallon.ipynb`](../notebooks/00_medallon.ipynb). El bronze ya
está subido, así que en Colab el silver y el gold se arman en segundos sin volver a descargar de UCI.

- **En Colab**, `usar_drive()` monta el Drive y apunta el pipeline a esa carpeta. Si te compartieron la
  carpeta, agrégala a tu unidad con *Organizar › Agregar acceso directo*: también se reconoce el acceso
  directo `Mi unidad/tetouan-power-forecast`.

  ```python
  from tetouan_power_forecast.medallon import cargar_gold, usar_drive

  usar_drive()
  df = cargar_gold(zona=1)
  ```

- **En local**, se sincroniza con [rclone](https://rclone.org/) (aquí el remoto se llama `gdrive`):

  ```bash
  rclone copy gdrive:datalake/tetouan-power-forecast data   # bajar las capas
  rclone copy data gdrive:datalake/tetouan-power-forecast   # subir las que armaste
  ```

  Con `TETOUAN_DATA` se usa otra carpeta en lugar de `./data`.
