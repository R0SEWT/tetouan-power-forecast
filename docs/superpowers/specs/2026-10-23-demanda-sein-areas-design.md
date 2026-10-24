# Demanda eléctrica por área del SEIN ante eventos extraordinarios: diseño del proyecto

Fecha: 2026-10-23. Estado: borrador para revisión del grupo.

## 1. Objetivo

Pronosticar con una hora de anticipación la demanda eléctrica de las tres áreas operativas del Sistema Eléctrico
Interconectado Nacional (SEIN): **Norte, Centro y Sur**, cada 30 minutos, con datos públicos del COES. Además, medir
cuánto ayudan las **variables exógenas** (clima, El Niño, fallas del sistema) cuando ocurre un evento
extraordinario, es decir, cuando la demanda se sale de lo que el modelo vio al entrenar.

La pregunta del proyecto:

> ¿Qué tan bien se pronostica la demanda de cada área cuando el sistema vive un evento extraordinario, y cuánto
> mejora el pronóstico al sumar el clima, El Niño y las fallas del sistema?

Las tres áreas viven realidades distintas, por eso se modelan por separado:

- **Norte:** lluvias e inundaciones con El Niño (marzo de 2017 y de 2023).
- **Centro:** Lima, con calor en los veranos con Niño.
- **Sur:** casi sin efecto costero de El Niño, y con la sequía andina como riesgo.

Sirve a tres cosas a la vez:

1. **El TB1 del curso** (CRISP-DM, short paper, app HTML y exposición en la semana 15), con un caso peruano.
2. **Una pregunta abierta:** no encontramos estudios revisados por pares que midan el efecto de El Niño sobre la
   demanda de Lima o del SEIN ([`docs/peru/nino.md`](../../peru/nino.md), §3.1).
3. **Un caso vivo:** El Niño Costero de 2026 es extraordinario. El ICEN llegó a 3.98 en agosto, el mayor desde
   1997-98, y ENFEN prevé esa magnitud hasta enero de 2027. Es una prueba fuera de distribución que ocurre ahora.

## 2. Lo ya decidido (no se reabre aquí)

- **Cambio de caso:** de Tetuán a la demanda del SEIN. La profesora aprobó el cambio y que **el COES cuenta como
  fuente abierta**.
- **Serie base:** demanda del COES por **área operativa** (Norte, Centro, Sur), cada 30 minutos. No se usan las
  subáreas: cambian entre años (siete en 2017, una en 2026).
- **El Niño, el SAIDI de Osinergmin y los eventos del COES son exógenos:** ayudan a explicar los periodos
  extraordinarios, pero no son lo que se predice.
- **Regla de información:** cada variable entra solo con lo que se sabía en el momento de predecir, con su rezago de
  publicación real (§5).
- **Se reutiliza la metodología de Tetuán:**
  - medallón con auditoría;
  - objetivo en razón con la media de 24 h;
  - modelo global de las áreas;
  - tres referencias ingenuas;
  - origen móvil;
  - bootstrap por días.

  Tetuán (2017, tres zonas) y Ceuta (validación externa) quedan como **antecedente metodológico**: muestran por qué
  el objetivo en razón aguanta niveles que el modelo no vio.
- **Diseño de la app:** el de Wachi y el del visor de concurrente. Ver la [spec de la app](2026-10-23-app-design.md).
- **Datos pesados y cómputo en Colab;** las capas viven en el Drive.

## 3. Alcance de este corte (TB1, hasta la semana 15)

Dentro:

- **Medallón del COES:**
  - demanda por área, de enero de 2015 a octubre de 2026;
  - demanda del SEIN y la Programación Diaria;
  - eventos relevantes.
- **Exógenas:**
  - temperatura horaria de ERA5 por área;
  - ICEN y Niño 1+2;
  - feriados;
  - SAIDI por área.
- **Modelado:**
  - horizonte de 1 h (t+2 en pasos de 30 min);
  - Ridge, Random Forest y Gradient Boosting, con búsqueda de hiperparámetros y validación cruzada temporal;
  - modelo por área frente a modelo global.
- **Ablación de exógenas** (§7.3): el experimento central.
- **Evaluación:**
  - validación en 2025;
  - prueba en 2026, fuera de distribución;
  - errores por régimen.
- **App HTML, short paper y exposición.**

Fuera (quedan anotados como pendientes, no entran a este plan):

- **El horizonte de 24 h frente a la Programación Diaria del COES.** Entra solo si sobra tiempo después de la fase 3
  (§11, decisión abierta 2).
- **Las 31 distribuidoras por subestación** (demanda por barras): es un dato sucio y no aporta a la pregunta por
  áreas.
- **Costos marginales, generación hidroeléctrica y el estado de alerta de ENFEN armado desde los PDF.**
- **Pronósticos de clima:** se usa la temperatura observada hasta t, no un pronóstico de t+2.

## 4. Datos

Detalle, verificación y calidad en [`docs/peru/energia.md`](../../peru/energia.md) y
[`docs/peru/nino.md`](../../peru/nino.md).

| Fuente | Qué aporta | Resolución y cobertura | Acceso | Calidad conocida |
|---|---|---|---|---|
| **COES, IEOD, hoja `DEMANDA_AREAS`** | Demanda de SEIN, Norte, Centro y Sur | 30 min, de oct-2011 a D+1 | Un anexo xlsx por día (1.0-1.3 MB, ~400 MB/año), con el navegador de archivos del portal. **Solo en Colab** | En el IEOD, Norte + Centro + Sur = SEIN exacto. Los nombres de carpetas y archivos cambian según el año (`03_MARZO` / `03_Marzo`, `Anexo_0203.xlsx` / `AnexoA_2210.xlsx`) |
| COES, demanda del SEIN (portal) | SEIN ejecutado y Programación Diaria y Semanal | 30 min, del 2000 a casi hoy | Un xlsx por año (~0.63 MB) | 2015-2026 sin huecos ni duplicados. Queda **+1-1.5 % sobre el IEOD**: no se mezclan las dos fuentes en una serie. Hay caídas reales, como −30 % el 26-ago-2025 |
| COES, eventos relevantes | Falla en curso: empresa, ubicación, inicio y fin | Por evento, de 2017 a hoy (≥ 1,769 eventos por año) | Un xlsx por año (~110 KB) | Texto libre y pocos duplicados. Falta asignar cada evento a un área (§11, decisión 4) |
| Open-Meteo, ERA5 | Temperatura horaria por ciudad | Horaria, desde 1940; ~5 días de rezago | API, CC BY 4.0 | Completa. La lluvia de ERA5 en Lima no sirve (137 mm/año en una ciudad hiperárida) |
| IGP y ENFEN, ICEN | Régimen de El Niño Costero | Mensual, 1950 a 2026-08 | TXT de 16 KB | Sin huecos. El definitivo del mes m sale en m+2; el ICENtmp de m+1 se revisa. Cambió de método en dic-2024 |
| NOAA CPC, Niño 1+2 (OISST) | Temperatura del mar frente al norte | Semanal, de 1981 a hoy; ~9 días de rezago | TXT de 149 KB, dominio público | Sin huecos |
| Osinergmin, SAIDI y SAIFI | Duración y frecuencia de los cortes por sistema | Mensual, de 2004 a 2026-03; ~5 semanas de rezago | datosabiertos.gob.pe, ODC-By, CSV de 6.5 MB | Limpio. Pico del norte en marzo de 2017 (7.06) y de 2023 (4.60), contra 1.6-3.8 el resto |
| Feriados del Perú | Calendario | Diario, 2015-2026 | gob.pe: leyes y decretos de días no laborables | Hay que armarlo a mano; incluye los no laborables decretados |

**Por qué empezar en 2015:**

- La demanda por área existe desde 2011, pero el pico diario cambió de lugar: en 2015 el 98 % de los días tenía el
  máximo entre las 18 y las 23 h, y en 2026 solo el 29 %, porque el pico se fue al mediodía.
- Empezar en 2015 deja dentro del entrenamiento dos eventos: El Niño Costero de 2017 y el de 2023 con el ciclón Yaku.

## 5. Variables y regla de información

Todo se mide en t: el momento en que se emite el pronóstico de t+2.

| Grupo | Variables | Disponible en t |
|---|---|---|
| Demanda del área | Rezagos t, t−1, t−2 y t−4; mismo momento de ayer (t+2−48) y de la semana pasada (t+2−336); media y desviación de la última hora; todo dividido por la media de 24 h del área | Sí: el COES publica con ~30 min de retraso |
| Nivel reciente | Media de 24 h sobre la de 7 días | Sí |
| Calendario | Hora, minuto del día, día de la semana; seno y coseno diario y semanal; feriado y no laborable de la fecha de t+2 | Sí: se conoce de antemano |
| Clima (ERA5) | Temperatura del área en t; media de 24 h; anomalía frente a la climatología 1991-2020 de la hora y del mes | Sí en la práctica (en el histórico se usa el reanálisis como si fuera el dato en tiempo real) |
| El Niño | ICEN(m−2) definitivo; Niño 1+2 de la última semana publicada | Sí, con su rezago |
| Fallas | Eventos del COES en curso en el área en t; minutos desde el inicio | Sí: se registran en la operación (falta verificar con cuánto retraso se publican) |
| SAIDI del área | SAIDI del área en m−2, como "estrés de la red" | Sí, con su rezago. Se usa sobre todo para estratificar la evaluación (§7.4) |
| Contexto | Indicador de cuarentena (desde el 16-mar-2020) | Sí |

No hay calendario anual (mes, día del año): en Tetuán, con un año de datos, funcionó como identificador de época.
Aquí hay doce años, así que se prueba en la ablación (§7.3).

Las ciudades de ERA5 por área son una propuesta a confirmar (§11, decisión 3): Norte, Piura, Chiclayo y Trujillo;
Centro, Lima; Sur, Arequipa y Cusco.

## 6. Modelado

- **Series:** las tres áreas, con un modelo global (las áreas apiladas y el área como categórica) frente a uno por
  área. El SEIN se reporta como la suma de las tres.
- **Objetivo:** la demanda del área en t+2 dividida por su media de 24 h (`ModeloRazon`). Las métricas se calculan
  siempre en MW.
- **Algoritmos (criterio V de la rúbrica):**
  - Ridge, la referencia lineal;
  - Random Forest;
  - Gradient Boosting (`HistGradientBoostingRegressor`).

  Hiperparámetros con `RandomizedSearchCV` y `TimeSeriesSplit(gap=2)` sobre el entrenamiento; para el global,
  `CVPorFecha`.
- **Importancia de variables:** por permutación, en la validación, por área y por grupo de variables.

## 7. Evaluación

### 7.1 Partición

| Tramo | Fechas | Para qué |
|---|---|---|
| Entrenamiento | ene-2015 a dic-2024 | Ajuste y búsqueda de hiperparámetros. Incluye 2017, la cuarentena de 2020 y 2023 |
| Validación | ene-2025 a dic-2025 | Elegir el modelo y las exógenas |
| **Prueba fuera de distribución** | ene-2026 a oct-2026 | El Niño extraordinario: se toca una sola vez, al final |

Entre cada tramo queda un hueco de 2 pasos (1 h).

### 7.2 Referencias

- **Ingenuas, por área:**
  - persistencia (t);
  - ayer a la misma hora (t+2−48);
  - semana pasada a la misma hora (t+2−336).

  El criterio compara contra la mejor de las tres en cada tramo.
- **Oficial, solo para el SEIN:** la Programación Diaria del COES (MAPE de 1.5-1.9 %). Es un pronóstico del día
  anterior, así que se compara con cuidado: a 1 h el modelo tiene más información.

### 7.3 Ablación de exógenas: el experimento central

El mismo algoritmo y la misma partición, sumando un grupo a la vez:

| Variante | Variables |
|---|---|
| M0 | Demanda y calendario |
| M1 | M0 + clima |
| M2 | M1 + El Niño |
| M3 | M2 + fallas del COES |
| M4 | M3 + SAIDI(m−2) |

En cada variante se reporta el MAE en general y en cada régimen (§7.4). La respuesta a la pregunta del proyecto es
la diferencia M3 − M0 dentro de los periodos extraordinarios, con su intervalo por bootstrap de días.

### 7.4 Regímenes (dónde se desagrega el error)

- **El Niño:** según el ICEN y la clasificación de ENFEN (Nota Técnica 01-2024): neutro, débil, moderado, fuerte y
  extraordinario. 2026 es la prueba extrema.
- **Red golpeada:** meses con SAIDI alto en el área (sobre su percentil 90).
- **Fallas:** horas con un evento del COES en curso en el área.
- **Calendario:** feriados y no laborables; laborable frente a fin de semana; horas de mayor demanda.
- **Cuarentena:** 2020.

Además, origen móvil mensual de 2023 a 2025 (36 pliegues por área) para ver la estabilidad mes a mes.

### 7.5 Criterios de éxito (a confirmar por el grupo)

1. En cada área, el MAE del modelo elegido queda por debajo del de la mejor referencia ingenua, en el origen móvil
   y en la prueba.
2. En las horas de mayor demanda también le gana a la mejor referencia. Se reporta qué fracción de esas horas se
   subestima en más de 5 %.
3. En los periodos extraordinarios, las exógenas (M3 frente a M0) reducen el MAE con un intervalo que no cruza el
   cero.

   **Meta propuesta:** al menos 10 % menos en la prueba de 2026 en el área Centro.
4. Se reporta honestamente dónde falla: por ejemplo, si la Prueba 2026 obliga al modelo a extrapolar la temperatura
   (en Lima, la máxima de octubre va +4.8 °C, fuera del rango 2015-2024).

## 8. Estructura del repo

Se mantiene el repo y su infraestructura (CI, ramas protegidas, medallón en Drive). Se renombra (§11, decisión 1).

```
notebooks/
  00_medallon_coes.ipynb       Colab: bronze (IEOD, SEIN, eventos, ERA5, ICEN, Niño 1+2, SAIDI) → silver → gold
  01_datos_preparacion.ipynb   comprensión y preparación de los datos (CRISP-DM 2 y 3)
  02_modelado_evaluacion.ipynb CRISP-DM 4 y 5: algoritmos, global frente a local, ablación, prueba 2026
src/<paquete>/
  medallon.py, metricas.py     se reutilizan
  coes.py                      nuevo: descarga retomable y lectura del IEOD con sus formatos por año
  exogenas.py                  nuevo: ERA5, ICEN, Niño 1+2, eventos, SAIDI y feriados, con su rezago
  variables.py, modelos.py,    se generalizan: resolución (30 min) y horizonte (2 pasos) como parámetros,
  evaluacion.py                hoy fijos en 10 min y 6 pasos
app/                           la PWA (ver la spec de la app)
docs/
  negocio.md, datos.md         se reescriben para el caso peruano
  peru/energia.md, nino.md     la investigación de datos (este corte)
  antecedentes/                Tetuán y Ceuta: historico.md, investigacion.md y estado-del-arte.md
  superpowers/specs/           esta spec y la de la app
experimentos/                  historico/ y ceuta/ se conservan como antecedente
```

**Qué se reutiliza tal cual:**
- el patrón del medallón: escritura atómica, procedencia con sha256, descargas retomables por mes y auditoría que
  reporta sin cortar;
- `ModeloRazon` y `CVPorFecha`;
- el bootstrap por días;
- el origen móvil;
- la estructura del notebook 02 de Tetuán.

**Qué hay que generalizar:** `HORIZONTE` y `PERIODOS_DIA`, que hoy son 6 y 144.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| El IEOD cambia de formato y de nombres de archivo según el año (2011-2026) | Fase 0 (§10): inventariar las rutas de todos los años antes de bajar. Leer la hoja por su contenido (`SEIN`, `NORTE`, `CENTRO`, `SUR`), no por su posición. Probar con un día de cada año |
| ~4.5 GB de IEOD para 2015-2026 | Todo en Colab, retomable por mes; en el bronze solo se guarda la hoja `DEMANDA_AREAS` |
| La asignación de los eventos del COES a un área es ambigua | Por empresa y subestación, con una tabla a mano que se revisa. Si no alcanza, M3 se hace solo para el SEIN |
| La temperatura de 2026 está fuera del rango de entrenamiento | Es parte de la pregunta: se reporta como prueba de extrapolación, con el objetivo en razón como defensa (antecedente de Tetuán y Ceuta) |
| El dato preliminar se revisa después (no medido) | Fijar la fecha de descarga en la procedencia y no mezclar el portal con el IEOD |
| Deriva: el pico pasó al mediodía | Origen móvil y validación en el año más reciente; las horas de mayor demanda se definen por área y por año, no fijas en 18-23 h |
| Tiempo: tres semanas | El horizonte de 24 h y el estado de alerta de ENFEN quedan fuera. Si la fase 0 se atrasa, M3 y M4 se recortan antes que la app |

## 10. Plan por fases

| Fase | Fechas | Entregable |
|---|---|---|
| 0. Datos | 24 al 27 de oct | Rutas del IEOD verificadas año por año; bronze y silver de las áreas, el SEIN, los eventos y las exógenas en el Drive, con auditoría |
| 1. Comprensión y preparación | 28 de oct al 2 de nov | Notebook 01: firma de cada área, efectos de El Niño de 2017, 2023 y 2026, calidad y gold |
| 2. Modelado | 3 al 8 de nov | Notebook 02: algoritmos con búsqueda de hiperparámetros, global frente a local y ablación M0-M4 |
| 3. Evaluación y app | 9 al 12 de nov | Prueba de 2026, regímenes, importancia de variables; app con datos precalculados |
| 4. Paper y exposición | 13 al 16 de nov | Short paper con la estructura del enunciado, ensayo de 20 minutos |

## 11. Decisiones abiertas

1. **Nombre del repo y del paquete.** Propuesta: renombrar el repo a `sein-power-forecast` (GitHub redirige el nombre
   viejo) y el paquete a `pronostico_demanda`. Alternativa: un repo nuevo, que pierde el CI, las protecciones y la
   historia.
2. **Horizonte de 24 h** frente a la Programación Diaria del COES. Es otra pregunta (programación, no operación) y
   duplica el modelado. Propuesta: solo si sobra tiempo, y solo para el SEIN.
3. **Ciudades por área para ERA5,** y si ponderarlas por población o por demanda. Hay que verificar qué
   departamentos forman cada área operativa del COES.
4. **Cómo asignar los eventos del COES a un área:** por empresa, por subestación o por texto.
5. **La meta de mejora de las exógenas** en los periodos extraordinarios (hoy, 10 % en el área Centro).
