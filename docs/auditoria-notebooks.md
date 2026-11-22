# Auditoría de los notebooks entregables

Revisión de los notebooks que se entregan con el TB1 frente a lo que pide la rúbrica y lo que dijo la profesora:
EDA y preparación «en notebook», limpio, modular, comentado y reproducible (criterios III y IV), importancia de
variables (criterio V), **al menos tres comentarios por gráfico** y un **pipeline parametrizado** por la ruta de los
datos, con versión. Las fuentes están en `course-meto-data-science/docs/tb1-final-requisitos.md`.

## Cómo se contó

- **Comentarios por gráfico:** para cada celda de código con una imagen, las viñetas (o, si no hay viñetas, las frases)
  de las celdas markdown que vienen **justo debajo**, hasta el siguiente título. Se contó con un script y se revisó a
  mano. Un comentario cuenta si dice algo del negocio o de la decisión (qué significa para el operador o para el
  modelo), no si describe el gráfico. Las conclusiones del final no cuentan como comentarios de un gráfico.
- **Celdas vacías y código muerto:** celdas sin contenido, y los imports y variables sin uso que marca `ruff`
  (F401, F841, F811) sobre el código de cada notebook.
- **Transformaciones justificadas:** si el texto dice por qué se hace cada transformación, no solo qué se hace.
- **Pipeline:** si hay una función que recibe la ruta de los datos y hace todos los pasos, con versión.

## Resultado

| Notebook | Gráficos (imágenes) | Gráficos con menos de 3 comentarios: antes → después | Celdas vacías | Código muerto | Transformaciones justificadas | Pipeline parametrizado por ruta |
|---|---|---|---|---|---|---|
| `01_datos_preparacion` (Tetuán) | 11 (11) | 2 → 0 | 0 | Un import (`HORIZONTE`) que la celda 55 redefinía: **quitado**. `rmse_m` y `y_val`/`y_test` quedan, en celdas con salida | Sí: atípicos, variables descartadas, objetivo t+6, rezagos, codificación cíclica, sin imputación, fuga | Parcial → **sí**: `bronze/silver/gold(raiz)` y `tetouan all --raiz` existían pero el notebook no los mostraba; ahora hay una sección «Pipeline reproducible» que corre el medallón en una carpeta nueva y comprueba que da las mismas capas gold |
| `02_modelado_evaluacion` (Tetuán) | 4 (5) | 4 → 0 | 0, pero las **conclusiones estaban vacías**: ahora escritas con sus tablas | Ninguno | No aplica (modelado); justifica el objetivo en razón y el modelo global | Lee las capas con `cargar_silver` y `cargar_gold` desde la ruta de datos |
| `01_sein_datos_preparacion` | 6 (6) | 6 → 0 | 0 | Ninguno | Sí, en la preparación y los hallazgos; la sección nueva agrega una tabla con el porqué de cada paso | No → **sí**: `pipeline_sein(ruta)`, nuevo, con test; la sección «Pipeline reproducible» lo corre y comprueba que reproduce las filas por partición de la preparación paso a paso |
| `02_sein_modelado_evaluacion` | 5 (6) | 5 → 0 | 0 | Ninguno | No aplica | Arma los datasets con `preparar_datasets`, la función que llama el pipeline |
| `03_sein_prueba_2026` | 2 (3) | 2 → 0 | 0 | Un import sin uso (`hora_objetivo`): **quitado** | No aplica | Igual que el 02 |
| `04_sein_modelos_fundacionales` | 2 (2) | 2 → 0 | 0 | Ninguno | No aplica | Lee los pronósticos desde la ruta de datos (`raiz_datos`) |
| `05_sein_explicabilidad` (nuevo) | 7 (7) | — → 0 | 0 | Ninguno | No aplica | Parte de `pipeline_sein(RAIZ, hasta=…)` |
| **Total de los entregables previos** | **30** | **21 → 0** | | | | |

Antes, todos los gráficos de los notebooks del SEIN (01 a 04) y del 02 de Tetuán tenían las cifras solo en los
«Hallazgos» o las «Conclusiones» del final, sin nada debajo del gráfico. El 01 de Tetuán ya comentaba casi todos.

## Qué se cambió y qué no

- **Comentarios:** cada gráfico tiene debajo una celda «Lectura del gráfico» con al menos tres puntos, en español
  llano, con cifras que ya estaban en las salidas del propio notebook (o en su prosa). No se inventó ninguna cifra; las
  que se leen de un gráfico van como aproximadas.
- **Sin reejecutar lo pesado.** Los notebooks 02 y 03 del SEIN (de 2 a 3 h en Colab) no se reejecutaron: solo se
  agregó markdown y se quitó un import. En los notebooks de preparación se ejecutó **solo la celda nueva** del pipeline
  (con las celdas de configuración), así que ninguna salida publicada cambió. El notebook 05 se ejecutó completo en una
  laptop (unos dos minutos).
- **Pipeline:** `src/tetouan_power_forecast/pipeline_sein.py` (versión `v1`) carga las capas silver con su sha256,
  valida la demanda, recorta a una fecha de corte opcional, arma los datasets de 1 h y 24 h con la regla de información
  y la partición, verifica la regla en una muestra y devuelve la procedencia; `guardar` la escribe con los datasets en
  `gold/sein/v1/`. También corre desde la consola. Test: `tests/test_pipeline_sein.py`.
- **Explicabilidad:** `notebooks/05_sein_explicabilidad.ipynb` y `src/tetouan_power_forecast/explicabilidad.py` (con
  test), que pasa los valores SHAP de la razón a MW y los agrupa por familias de variables.

## Pendiente

- Validar con el grupo las lecturas nuevas y las conclusiones del notebook 02 de Tetuán, que se escribieron ahora.
- El notebook 05 propone dos mejoras que no se implementaron porque implican reentrenar o cambiar la tubería en vivo:
  una variable que diga si el día anterior fue domingo o feriado (el peor error de 2026 es un feriado en lunes) y un
  control de saltos aislados por área en la validación del anexo (el traspaso del 4 de agosto pasa la validación
  actual).
- El Entregable 8 (explicabilidad, privacidad y seguridad) está en `entregables/Entregable8_MDS_Grupo03.ipynb`, con
  su PDF: parte del notebook 05 y suma la importancia por permutación lado a lado, LIME como contraste del peor
  error, la búsqueda de datos personales en los eventos del COES y los riesgos del despliegue público.
