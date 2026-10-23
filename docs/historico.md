# Cómo sortear que solo hay un año de histórico

Investigación de apoyo a la [comprensión del negocio](negocio.md) y a las fases de modelado y
evaluación. Responde tres preguntas: si hay datos externos que extiendan o complementen el 2017, qué
estrategias de modelado funcionan con poco histórico y cómo evaluar y reportar la limitación con
honestidad.

Las cifras marcadas con **(experimento)** salen de una prueba rápida sobre el silver
(`tetouan_2017.parquet`) con `HistGradientBoostingRegressor` (300 iteraciones, tasa 0.05, sin ajuste de
hiperparámetros) evaluado con origen móvil mensual. El diseño está en el [anexo](#anexo-el-experimento)
y los scripts, en [`experimentos/historico/`](../experimentos/historico/). Sirven para ordenar las
opciones, no como resultado final del proyecto: el modelado tiene que reproducirlas con su propio
pipeline.

## Resumen

No hay otro año público de Tetuán (UCI solo tiene 2017 y la ONEE dejó de publicar sus curvas de carga
hacia 2008): la salida es dejar de pedirle al modelo que aprenda el nivel de 2017. Con origen móvil mensual,
pronosticar la razón entre el consumo en t+6 y la media de las últimas 24 h, sin calendario anual, bajó
el MAE medio del modelo actual un 17, 21 y 37 % (zonas 1, 2 y 3), quitó el salto del verano y le ganó a
la mejor referencia ingenua en los 10 meses; un modelo global de las tres zonas sumó otro 5 a 10 %.
Recomiendo: objetivo relativo y modelo global; origen móvil mensual con el verano de la Zona 3 como
rango; pronosticar también la Zona 1 + la Zona 2 y reentrenar cada semana en la prueba, por la
transferencia del 25 de octubre; y Chronos-2 sin ajuste en Colab Pro como referencia adicional. La
[validación externa en Ceuta](#resultado-de-la-validación-externa), con los veranos de 2020 a 2026,
respalda la elección: el objetivo en razón le ganó al modelo actual en todos los casos, y entrenar sin
haber visto un verano subió su MAPE de julio y agosto de 1.94 a 2.33 %, la mitad que la mejor referencia
ingenua (4.63 %).

## Opciones ordenadas por impacto y factibilidad

Los síntomas que cada opción ataca:

- **(a)** los árboles no extrapolan a niveles que no vieron: el fold de verano casi duplica el error;
- **(b)** con un año, el calendario anual (mes, día del año, seno y coseno anual) funciona como
  identificador de época: quitarlo mejora el MAE un 7.7 %;
- **(c)** el verano de la Zona 3 cae en el entrenamiento y la prueba de noviembre-diciembre no lo evalúa;
- **(d)** la transferencia de carga de la Zona 1 a la Zona 2 del 25 de octubre deja el final de la
  validación y toda la prueba en un régimen de nivel que el entrenamiento no tiene.

| # | Opción | Qué resuelve | Esfuerzo | Riesgo | Fuente |
|---|---|---|---|---|---|
| 1 | [Objetivo relativo](#1-pronosticar-el-cambio-relativo-no-el-nivel): razón a la media de 24 h (o cambio respecto de t) | a, c, d | Bajo: medio día | Bajo. En la Zona 3 de noviembre el cambio superó a la razón | Experimento |
| 2 | [Modelo global](#2-un-modelo-global-para-las-tres-zonas) de las tres zonas (requiere la 1) | a, c | Bajo: medio día | Bajo-medio: hay que definir variables simétricas entre zonas | Montero-Manso y Hyndman (2021); experimento |
| 3 | [Origen móvil mensual](#evaluación-honesta-con-un-solo-año), verano como rango y prueba con reentrenamiento semanal | c; mide a y d | Bajo-medio: 1 día | Bajo | Tashman (2000); Cerqueira et al. (2020); Bergmeir et al. (2018) |
| 4 | [Pronosticar la Zona 1 + la Zona 2](#4-la-transferencia-del-25-de-octubre-pronosticar-también-la-zona-1--la-zona-2), cuota de 24 h como variable, detectar y declarar el quiebre | d | Bajo: medio día | Bajo | Experimento; `ruptures` |
| 5 | [Sin calendario anual](#5-calendario-anual-fuera-temperatura-suavizada-feriados-y-ramadán-dentro); temperatura media de 24 h, feriados, Ramadán y rezago semanal | b | Bajo (ya planificado) | Bajo; por sí solo cambia poco | Wang, Liu y Hong (2016); experimento |
| 6 | [Chronos-2 sin ajuste](#6-modelos-fundacionales-como-referencia-sin-entrenamiento) como referencia adicional (Colab Pro, T4 o L4) | a, c, como control | Medio-bajo: 1 día | Medio: no hay evidencia a 1 h con datos de 10 min; tiende a subestimar picos | Ansari et al. (2025); Kaljevic et al. (2026); Meyer et al. (2024) |
| 7 | [Clima de varios años](#7-clima-de-varios-años-para-tetuán) (ERA5 vía Open-Meteo) para situar 2017 | c, como validez externa | Bajo: medio día | Bajo | Open-Meteo; ECMWF |
| 8 | [Ceuta](#8-ceuta-el-único-sistema-comparable-con-varios-años-a-5-minutos) (REE, 5 min, 2019-2026) como validación externa o preentrenamiento | a, b, c en un sistema vecino | Hecha la validación externa | Medio-alto: servicio no documentado, licencia restrictiva, otro sistema | REE; [experimento en Ceuta](#resultado-de-la-validación-externa) |
| 9 | [Día similar](#9-día-similar-y-vecinos-más-cercanos) o vecinos más cercanos | a, en parte | Bajo: medio día | Bajo; poca ganancia esperada | Dudek (2015) |

Las opciones 1 a 5 caben en una semana y no necesitan librerías nuevas. La 6 suma `chronos-forecasting`
y una sesión de GPU. De la 8 ya está hecha la validación externa; el preentrenamiento con Ceuta, no.

---

## Cuánto histórico hace falta a muy corto plazo

- **De minutos a una hora, la trayectoria reciente domina.** Taylor (2008) evaluó pronósticos de 10 a 30
  minutos con datos minuto a minuto de Gran Bretaña usando **30 semanas**: 20 para estimar y 10 para
  evaluar. Los mejores métodos fueron variantes de suavizamiento exponencial con estacionalidad doble
  (intradiaria y semanal), y los métodos basados en pronósticos del clima solo empezaron a aportar más
  allá de una hora, combinados con los anteriores.
- **Los años hacen falta para aprender lo anual:** la estacionalidad del año, la respuesta al calor y los
  días especiales. Por eso la competencia de referencia del área, GEFCom2012, entregó unos 4.5 años de
  carga horaria de 20 zonas (Hong, Pinson y Fan, 2014), y los modelos de referencia del área estiman
  tendencia, calendario y temperatura sobre varios años.
- **No encontré un estudio controlado que diga cuántos años bastan a una hora.** La evidencia es
  indirecta. En el benchmark de hogares de Meyer et al. (2024), los Transformers entrenados desde cero
  usaron un año de calibración y los modelos fundacionales sin entrenar rindieron igual.
- **Lo que muestra Ceuta** ([validación externa](#resultado-de-la-validación-externa), julio y agosto de
  2022 a 2026): con el objetivo en razón, el MAPE fue de 2.33 % entrenando solo con enero a junio, 1.94 %
  con un año, 1.84 % con dos y 1.82 % con tres. Lo que más pesa es haber visto un verano; el segundo año
  aporta 0.1 puntos y el tercero, casi nada.
- **Lo que muestra el experimento:** con el objetivo relativo, el pliegue de marzo (entrenado con solo
  enero y febrero) ya logra un MAPE de 2.3 % en la Zona 1, frente a 3.3 % de la mejor referencia ingenua;
  con más meses baja a 1.5-1.9 %.

**Consecuencia para el proyecto:** un año alcanza para aprender la dinámica intradiaria y semanal, que es
lo que decide el pronóstico a una hora. No alcanza para aprender el ciclo anual ni el nivel de verano.
Lo que conviene es **no pedirle al modelo que aprenda el nivel** (opciones 1 y 2) y no afirmar en el
paper que el modelo generaliza a otros años. En Ceuta, no haber visto un verano subió el MAPE un 20 % con
el objetivo en razón y un 38 % con el modelo actual.

## 1. Pronosticar el cambio relativo, no el nivel

**Qué resuelve:** (a) y buena parte de (c) y (d).

Un modelo de árboles, aunque sea un *boosting* que suma muchos árboles, es constante por tramos: para
valores de las variables más allá de los que vio, repite lo que aprendió en el borde y no extrapola la
tendencia. Sus predicciones quedan pegadas al rango de niveles del entrenamiento, y con un solo año el
nivel de cada mes se vuelve una seña de "en qué parte del año estoy". A una hora, casi todo lo que hay que saber es el nivel actual. Conviene que el modelo aprenda
solo lo que cambia respecto de ahora.

Dos variantes probadas (experimento):

- **Cambio:** el objetivo es `y(t+6) − y(t)` y el pronóstico, `y(t) + f(X)`.
- **Razón:** el objetivo es `y(t+6) / m24(t)`, donde `m24` es la media de las últimas 144 observaciones
  (24 h), y los rezagos de cada zona se dividen por su propia `m24`. El pronóstico es `m24(t) · f(X)`.

MAE en kW, origen móvil mensual (10 pliegues, de marzo a diciembre). "Actual" reproduce las variables
del gold con el objetivo en nivel. Las dos variantes relativas, además, no tienen calendario anual y suman
el rezago semanal, feriados, Ramadán y la temperatura media de 24 h (opción 5):

| | Zona 1 | Zona 2 | Zona 3 |
|---|---:|---:|---:|
| Actual (nivel): media de los 10 meses | 867 | 683 | 803 |
| Cambio: media de los 10 meses | 793 (−8.5 %) | 598 (−12.4 %) | 577 (−28.1 %) |
| **Razón: media de los 10 meses** | **721 (−16.8 %)** | **542 (−20.6 %)** | **509 (−36.6 %)** |
| Pliegue de julio: actual → razón | 1,701 → 929 | 1,354 → 601 | 2,175 → 678 |
| Peor pliegue / pliegue mediano: actual → razón | 2.17 → 1.47 | 2.09 → 1.37 | 2.77 → 1.40 |
| Meses en que le gana a la mejor ingenua (de 10): actual → razón | 9 → 10 | 10 → 10 | 6 → 10 |
| Prueba, MAPE: actual → razón (mejor ingenua) | 2.07 → **1.68 %** (2.92 %) | 2.48 → 2.05 % (4.29 %) | 5.30 → 4.31 % (6.06 %) |

- El salto del verano desaparece: el peor mes pasa de duplicar al mes típico a superarlo en 40-50 %.
- En la Zona 3, el modelo actual pierde contra "ayer" en 4 de los 10 meses (en julio, 6.6 % contra 3.4 %
  de MAPE); con la razón le gana en todos.
- En la prueba de la Zona 1, la razón queda **43 % por debajo del MAE de la mejor referencia ingenua**
  ("semana pasada"), por encima de la meta propuesta de 20 %.
- La razón fue mejor que el cambio en casi todos los pliegues. La excepción es la Zona 3 en noviembre
  (MAPE de 5.5 % contra 4.3 %), cuando el consumo cae rápido al salir de la temporada y la media de 24 h
  queda atrás. Vale la pena probar las dos por zona o promediarlas.

**Cómo se implementaría aquí (medio día).** En `construir_dataset` se agrega la escala y se dividen por
ella el objetivo y las variables de consumo. Las métricas se siguen calculando en kW, sobre el
pronóstico reconstruido:

```python
m24 = {z: df[ZONAS[z - 1]].rolling(PERIODOS_DIA).mean() for z in (1, 2, 3)}   # conocido en t
df["escala"] = m24[zona]
df["objetivo_rel"] = df[nombre_objetivo(zona)] / df["escala"]
for z in (1, 2, 3):                                # rezagos de cada zona sobre su propio nivel
    for c in [c for c in df.columns if c.startswith(f"Zone{z}_")]:
        df[c] = df[c] / m24[z]
df["nivel_24h_vs_7d"] = m24[zona] / df[ZONAS[zona - 1]].rolling(7 * PERIODOS_DIA).mean()

modelo.fit(X_train, df_train["objetivo_rel"])
y_hat = modelo.predict(X_test) * df_test["escala"]   # kW, comparable con las referencias
```

`TransformedTargetRegressor` de scikit-learn no sirve aquí, porque la transformación depende de una
columna de cada fila.

## 2. Un modelo global para las tres zonas

**Qué resuelve:** (a) y (c). Con el objetivo relativo, las tres zonas comparten la misma dinámica (pico al
anochecer, ciclo semanal, Ramadán). Entrenarlas juntas triplica las filas y le muestra al modelo tres
"estaciones" distintas en el mismo año: la subida de verano de la Zona 3 enseña algo sobre la de la
Zona 1. Montero-Manso y Hyndman (2021) muestran que un modelo global puede igualar a los locales sin
suponer que las series se parecen y que su complejidad no crece con el número de series.

**Experimento:** las tres zonas apiladas, solo con las variables de la propia zona más la zona como
variable categórica, objetivo en razón:

| MAE, media de 10 meses | Zona 1 | Zona 2 | Zona 3 |
|---|---:|---:|---:|
| Local, solo variables propias | 730 | 543 | 518 |
| Local con los rezagos de las otras zonas (opción 1) | 721 | 542 | 509 |
| **Global, 3 zonas** | **659 (−9.7 %)** | **518 (−4.6 %)** | **474 (−8.5 %)** |
| Prueba, MAPE: local (opción 1) → global | 1.68 → 1.63 % | 2.05 → 1.93 % | 4.31 → 3.73 % |

Los porcentajes comparan contra el local con las mismas variables. El global gana en casi todos los
meses; en julio, la Zona 3 baja de 2.46 % a 2.06 % de MAPE.

**Cómo se implementaría aquí (medio día, después de la opción 1):** concatenar el gold de las tres zonas
con una columna `zona`, renombrar las variables de la zona objetivo como `propia_*` y declarar `zona`
como categórica (`HistGradientBoostingRegressor(categorical_features=...)`). Un ajuste por pliegue y un
solo modelo para la app. Sin el objetivo relativo no tiene sentido: los niveles de las zonas difieren
hasta el doble. No probé el global con los rezagos de las otras zonas; habría que definirlos de forma
simétrica (por ejemplo, la suma de las otras dos).

## 3. Evaluar con origen móvil mensual y reportar el verano como rango

**Qué resuelve:** (c) y la medición de (a) y (d). Es la opción que más pesa en el paper y la que menos
cuesta. El detalle está en [Evaluación honesta con un solo año](#evaluación-honesta-con-un-solo-año).

## 4. La transferencia del 25 de octubre: pronosticar también la Zona 1 + la Zona 2

**Qué resuelve:** (d).

**Lo que muestran los datos** (verificado sobre el silver):

- Desde las 11 h del 25 de octubre, la Zona 1 cae y la Zona 2 sube en espejo frente al mismo momento del
  día anterior: hacia las 18 h, unos −4.9 MW y +4.9 MW. Comparando las dos semanas anteriores con las dos
  posteriores, la Zona 1 queda 12.5 % abajo, la Zona 2 11.3 % arriba, la suma de ambas solo baja 3.3 % y
  la Zona 3, 6.6 % (la caída estacional).
- La **cuota de la Zona 1 en la suma** se movió entre 0.584 y 0.647 (media semanal) hasta el 25 de
  octubre, y en las semanas completas posteriores queda entre 0.546 y 0.562. Es un nivel que el
  entrenamiento no tiene. Buscar el único punto de quiebre que mejor parte la cuota diaria (mínimos
  cuadrados) da exactamente el 25 de octubre (0.619 antes, 0.554 después).
- **No es la única maniobra.** Hay días con cambios en espejo frente al día anterior (correlación entre
  ambas zonas menor a −0.9) el 8 y el 9 de marzo, el 21 de abril, el 7 de julio y el 5 de octubre, además
  del 25 de octubre. El 20 de abril hay un día completo transferido: frente al jueves anterior, la Zona 1
  baja 10.0 %, la Zona 2 sube 22.1 % y la suma, 1.5 %. Las transferencias son operación normal; la del
  25 de octubre es la única que se queda.

Estas cifras salen del script `cuota` ([`experimentos/historico/`](../experimentos/historico/)).

**Cuánto afecta (experimento).** Modelos entrenados hasta el 30 de septiembre, sin reentrenar, MAPE:

| | 1-24 oct | 25 oct-5 nov | 6 nov-30 dic |
|---|---:|---:|---:|
| Zona 1, nivel (actual) | 2.47 | 3.06 | 3.35 |
| Zona 1, razón | 1.72 | 2.28 | 1.73 |
| Zona 1, "semana pasada" | 3.27 | **8.07** | 3.00 |
| Zona 2, nivel (actual) | 2.48 | 3.52 | 3.88 |
| Zona 2, razón | 2.05 | 2.29 | 2.17 |
| Zona 2, "semana pasada" | 3.42 | **8.14** | 4.40 |
| Zona 1 + Zona 2, razón | 1.34 | 1.60 | 1.48 |
| Zona 1 + Zona 2, "semana pasada" | 2.47 | 2.96 | 3.08 |

- El modelo en nivel **no se recupera** sin reentrenar: sigue aprendido con la topología anterior. El de
  razón se recupera en cuanto la media de 24 h incorpora el nuevo nivel.
- "Semana pasada" se dispara durante la semana posterior (8 % en ambas zonas), porque compara contra la
  topología anterior. La suma no lo nota.
- **Reentrenar cada semana** dentro de la prueba oficial (6-nov a 30-dic) ayuda sobre todo al modelo en
  nivel: su MAPE pasa de 2.10 a 1.86 % en la Zona 1, de 2.87 a 2.20 % en la Zona 2 y de 2.33 a 1.63 % en
  la suma. Con la razón, de 1.67 a 1.61 %, de 2.07 a 1.92 % y de 1.45 a 1.37 %.

**Qué hacer:**

1. **Agregar la serie Zona 1 + Zona 2** como cuarto objetivo, con el mismo pipeline. Es invariante a las
   transferencias entre esas dos subestaciones y es justo la carga que el operador reparte cuando decide
   una maniobra. En el paper se reportan la Zona 1, la Zona 2 y su suma; si el error de la suma es mucho
   menor que el de las partes, la diferencia mide lo que cuesta no conocer las maniobras. En la prueba, el
   MAE de la suma es 0.78 veces la suma de los MAE de las dos zonas (experimento): parte de los errores se
   compensa.
2. **Objetivo relativo** (opción 1) y **reentrenamiento semanal** en la evaluación de la prueba.
3. **La cuota de la Zona 1 en la suma durante las últimas 24 h** como variable (se conoce en t): le dice al
   modelo cuál es la topología vigente.
4. **Detectar y documentar el quiebre.** Para el paper, una detección fuera de línea sobre la cuota diaria
   con `ruptures` (BSD-2-Clause; `rpt.Binseg` o `rpt.Pelt`) o con la búsqueda por mínimos cuadrados de
   arriba. Para la app, un detector simple: la cuota de cada día frente a la media y la desviación de las 4
   semanas anteriores. Con un umbral de −2.5 desviaciones marca el 20 de abril y del 25 al 28 de octubre,
   pero también da cuatro falsas alarmas en el año (14 de febrero, 4 y 24 de julio y 28 de septiembre).
   Como usa la cuota del día completo, avisa al cierre del día. Sirve como alerta, no como variable del
   modelo.
5. **Declararlo.** En la operación real, el centro de control conoce sus propias maniobras, y un sistema en
   producción recibiría el estado de la topología como entrada. El dataset no lo trae: es información
   faltante, no ruido.

No conviene una variable "después del 25 de octubre" (se aprendería con 12 días y en la prueba valdría
siempre 1) ni borrar el periodo.

## 5. Calendario anual fuera; temperatura suavizada, feriados y Ramadán dentro

**Qué resuelve:** (b).

**Experimento**, con el objetivo en nivel:

| Cambio de MAE frente al actual | Zona 1 | Zona 2 | Zona 3 |
|---|---:|---:|---:|
| Sin calendario anual: media de 10 meses | −2.4 % | −0.9 % | −3.2 % |
| Sin calendario anual: prueba | +8.3 % | −3.4 % | −1.8 % |
| Sin calendario anual + rezago semanal, feriados, Ramadán y temperatura media de 24 h: media de 10 meses | −2.7 % | −0.7 % | −4.0 % |

Con el objetivo en razón, volver a agregar el calendario anual **empeora** el pronóstico de los meses que
el modelo no vio. Entrenando hasta el 30 de septiembre y pronosticando del 6 de noviembre al 30 de
diciembre sin reentrenar, el MAPE pasa de 1.73 a 2.32 % en la Zona 1 y de 4.31 a 4.77 % en la Zona 3.
En la prueba oficial, que ya incluye unos días de noviembre en el entrenamiento, la diferencia casi
desaparece (1.67 contra 1.72 % en la Zona 1). Es el síntoma (b): mes y día del año ayudan solo cuando la
época ya está en el entrenamiento.

Quitar el calendario anual va en la dirección de la ablación del grupo, pero con el objetivo en nivel el
efecto es chico e inestable: en la prueba de la Zona 1 empeora. El argumento para quitarlo no es la
ganancia sino la validez: con un año, mes y día del año no se pueden distinguir de "esta época de 2017",
y no hay forma de comprobar que generalicen a otro año.

Lo que lo reemplaza:

- **Temperatura media de las últimas 24 h** (y, si se quiere, de 7 días) además de la de t: representa la
  inercia térmica de los edificios y es la seña física de la estación. Wang, Liu y Hong (2016) mostraron
  que modelar este "efecto de lo reciente" con temperaturas rezagadas y medias móviles mejoró los
  pronósticos un 18-20 % a nivel agregado y un 13-15 % a nivel de zona, aunque en horizontes más largos
  que una hora.
- **Feriados y Ramadán** con la fecha del periodo a predecir (t+6), que se conoce de antemano. Son las
  únicas señas anuales que sí se repiten igual otro año (con su fecha hijri).
- **Rezago semanal** (t+6−1008), que ya estaba pendiente.

Advertencia: la temperatura del dataset no coincide con ninguna fuente externa (opción 7), y según ERA5
2017 no tuvo un verano extremo (máxima de 36.6 °C, contra 39 °C en 2020 y 2023). En un verano más
caluroso, el modelo también estaría fuera del rango de temperatura que vio (el dataset llega a 40.0 °C).
El objetivo relativo atenúa el problema, pero no lo elimina.

## 6. Modelos fundacionales como referencia sin entrenamiento

**Qué resuelve:** (a) y (c), indirectamente. Un modelo preentrenado con miles de series no aprende el
nivel de 2017: pronostica a partir del contexto reciente, así que no tiene el problema de extrapolar ni
de memorizar épocas. Sirve como **cuarta referencia**, más exigente que las ingenuas, y como control:
si el modelo propio pierde contra él justo en el verano de la Zona 3, el problema es el entrenamiento con
un solo año y no el horizonte.

| Modelo | Licencia de los pesos | Tamaño | Covariables | ¿10 min? | Colab | Evidencia en carga eléctrica |
|---|---|---|---|---|---|---|
| **Chronos-2** (Amazon, oct-2025) | Apache-2.0 | 120 M (versión *small*, 28 M) | Pasadas y futuras conocidas, nativas | Sí (agnóstico a la frecuencia); contexto de hasta 8192 pasos | Sí: GPU T4 o CPU con la *small* | La mejor en el benchmark de Kaljevic et al. (2026) |
| **TimesFM 2.5** (Google, sep-2025) | Apache-2.0 | 200 M | Vía XReg desde oct-2025 | Sí; contexto de hasta 16 k | Sí, con GPU | Segunda línea en Kaljevic et al.; a la par de los Transformers entrenados en Meyer et al. |
| TimesFM 3.0 (ago-2026) | **No comercial, no productiva** | — | Nativas | Sí | Sin verificar | Sin evaluaciones independientes que haya encontrado |
| **TTM r2** (IBM Granite) | Apache-2.0 | ~0.8-1 M | Exógenas al ajustarlo | Sí: soporta 10 min; contexto de 512, 1024 o 1536 | Sí, **corre en CPU** | Solo las del propio autor; no encontré un benchmark de carga independiente |
| Moirai 2.0 (Salesforce) | **CC-BY-NC-4.0, "solo investigación"** | 11 M (*small*) | Sí | Sí | Sí, pero se instala desde GitHub | Segunda en Kaljevic et al.; Moirai 1.1 quedó entre los peores en Meyer et al. |
| Lag-Llama | Apache-2.0 | 2.5 M | No | Sí | Sí | Entre los peores en Meyer et al. |
| TimeGPT (Nixtla) | Propietario, API de pago | — | Sí | Sí | Requiere enviar los datos a la API | Liao et al. (2025) reportan ventaja con pocos datos, sin garantía |

Qué reportan en carga eléctrica:

- **Kaljevic, Arzola y Zhang (2026)** comparan cuatro modelos fundacionales y cuatro entrenados desde
  cero (DLinear, PatchTST, Informer, TimesNet) en tres series horarias de 5 años (ISO-NE, una empresa
  norteamericana y CAISO), a un día. Usando solo el histórico, el MAPE sin entrenar fue de 3.44, 2.86 y
  2.72 % con Chronos-2, 3.52, 3.06 y 2.85 % con Moirai 2.0 y 3.91, 3.38 y 3.27 % con TimesFM 2.5. El
  mejor de los entrenados, TimesNet, obtuvo 4.02, 3.14 y 3.08 %. Ajustar Chronos-2 bajó su MAPE a 3.23,
  2.69 y 2.55 %. No incluyen un modelo de árboles como referencia.
- **Meyer et al. (2024, aceptado en IEEE Access)** evalúan, sin entrenar, Chronos, Chronos-Bolt,
  TimesFM, Time-MoE, Sundial, Moirai y Lag-Llama en consumo horario de más de 300 hogares, a 24-168 h.
  Concluyen que rinden como los Transformers entrenados con un año de calibración y que los mejores
  los superan cuando el contexto crece. Advierten que tienden a subestimar los picos extremos, que es
  justo el error caro de este proyecto.
- **Liao et al. (2025, Applied Energy)** ajustan TimeGPT con poco histórico de carga y reportan que
  supera a modelos estadísticos y de ML, sobre todo a horizontes cortos, pero aclaran que la ventaja no
  está garantizada si la carga difiere de los datos de preentrenamiento.
- Ninguno de estos trabajos evalúa subestaciones a una hora con datos cada 10 minutos. **No hay evidencia
  directa para este caso; hay que medirlo.**

Riesgo de fuga: revisé las listas de datos de preentrenamiento publicadas de GiftEvalPretrain (que usa
TimesFM 2.5), LOTSA (Moirai), `autogluon/chronos_datasets` y la de TTM r2, y **no aparece el dataset de
Tetuán**. El corpus completo de Chronos-2 tiene además datos sintéticos y no lo pude revisar entero, así
que conviene declararlo como riesgo residual en el paper.

**Cómo se implementaría aquí (1 día; en Colab Pro, leyendo el gold desde Drive).** Chronos-2 sin ajuste,
como una referencia más en la tabla de resultados, con los mismos pliegues del origen móvil y la misma
prueba.

- **Runtime:** una GPU **T4** alcanza; **L4** si está disponible. Una A100 no hace falta para inferencia.
  Según fuentes de terceros (no verifiqué la tabla oficial de Google), una T4 consume unas 1.8 unidades de
  cómputo por hora y una A100, entre 10 y 15.
- **Tiempo estimado:** el paper de Chronos-2 reporta 300 series por segundo en una A10G (contexto de 2048
  y 64 pasos). Con un origen por hora, la prueba de las tres zonas son unos 4,000 contextos y el año
  completo del origen móvil, unos 26,000: del orden de 15 segundos y 1.5 minutos en una GPU de la clase de
  la A10G o la L4, y quizá dos a tres veces más en una T4. Con un origen cada 10 minutos, unos 160,000
  contextos: de 10 a 30 minutos. A eso se suman unos minutos de instalación y descarga del modelo. Son
  estimaciones a partir de la cifra del paper, no mediciones.
- **Ajuste fino (segunda etapa, opcional):** `Chronos2Pipeline.fit` permite ajustar el modelo completo o
  con LoRA, con `prediction_length=6` y datos de validación. Kaljevic et al. usaron 1000 pasos, lote de 64
  y tasa de 1e-6. Con Colab Pro es factible (no lo medí; del orden de decenas de minutos en una L4 o A100),
  pero solo con los datos de entrenamiento de cada pliegue, para no filtrar el futuro.

Un origen por hora, contexto de 14 días (2016 pasos) y el paso 6 de la mediana como pronóstico puntual:

```python
# pip install "chronos-forecasting>=2.0"
import numpy as np, torch
from chronos import Chronos2Pipeline

pipe = Chronos2Pipeline.from_pretrained(
    "amazon/chronos-2", device_map="cuda" if torch.cuda.is_available() else "cpu")

s = silver.set_index("DateTime")["Zone 1 Power Consumption"].to_numpy()
idx_origenes = np.arange(inicio_prueba, len(s) - 6, 6)          # un origen por hora
contextos = [s[t - 2016 + 1 : t + 1] for t in idx_origenes]       # 14 días hasta t, inclusive
q, _ = pipe.predict_quantiles(contextos, prediction_length=6, quantile_levels=[0.1, 0.5, 0.9])
p50 = np.array([x[0, 5, 1].item() for x in q])                  # paso t+6, cuantil 0.5
real = s[idx_origenes + 6]
```

La forma de la salida (`n_variates × prediction_length × cuantiles`) es la que documenta el código de
`Chronos2Pipeline.predict_quantiles`. No ejecuté este fragmento sobre los datos del proyecto. Las otras
dos zonas y la temperatura se pueden pasar como `past_covariates` en la forma de diccionario que acepta
`predict`. Los cuantiles 0.1 y 0.9 dan, de paso, los intervalos que la investigación propone como
diferencial para la app.

## 7. Clima de varios años para Tetuán

**Qué resuelve:** (c) y la validez externa, pero **no extiende el entrenamiento**. Más años de clima
sin la carga de esos años no enseñan al modelo cómo responde el consumo al calor. Sí permiten saber si
2017 fue un año típico y cuánto más calor puede venir del que el modelo vio.

| Fuente | Licencia | Acceso | Resolución | Cobertura | ¿Sirve a 1 h? |
|---|---|---|---|---|---|
| **Open-Meteo Historical** (ERA5, ERA5-Land, IFS) | CC BY 4.0 (citar a Open-Meteo); uso gratuito no comercial, 10,000 consultas/día | API REST sin registro | Horaria; ERA5 0.25°, ERA5-Land 0.1°, IFS 9 km | ERA5 desde 1940, ERA5-Land desde 1950, IFS desde 2017; 5 días de retraso | Como clima observado sí; no da 10 minutos |
| **ERA5 en el CDS de Copernicus** | CC BY para *ERA5 hourly single levels*, según ECMWF | API `cdsapi` con cuenta | Horaria, 0.25° | Desde 1940 | Igual que arriba, más trabajo |
| **Meteostat**, estación 60318 Tetuán / Sania Ramel (aeropuerto) | CC BY 4.0, citar a Meteostat y a sus proveedores | Descarga masiva por estación (`bulk.meteostat.net`) o librería de Python | Horaria | 1950-2026; casi completa desde 2014 | Sí, es una estación real |
| **NASA POWER** | Uso libre; pide un agradecimiento al proyecto POWER. No encontré un texto de licencia formal | API REST sin registro | Horaria; meteorología a 0.5° × 0.625° (MERRA-2), radiación a 1° | Desde 2001 | Resolución gruesa para una ciudad costera |

**Comprobaciones (experimento):**

- La temperatura del dataset **no coincide** con ninguna fuente externa. Su correlación horaria con
  ERA5 en el punto de Tetuán es 0.83 (0.85 desfasando una hora) y con la estación del aeropuerto, 0.82 a
  0.83. En julio, el dataset promedia 27.2 °C; ERA5, 23.8 °C; la estación del aeropuerto, 25.3 °C. El
  sensor del dataset parece estar en la ciudad, no en la costa. **No se puede reemplazar ni completar con
  datos externos sin calibrarlos.**
- **2017 fue un año climáticamente típico.** Según ERA5, la temperatura media de 2017 (17.7 °C) quedó en
  el puesto 11 de 30 (1995-2024; media de 17.5 °C) y la de julio-agosto (23.9 °C) en el 19 de 30 (media de
  24.2 °C). Tuvo 2 días de julio-agosto por encima del percentil 95 de la máxima (34.0 °C), frente a 3 de
  media. La máxima de julio-agosto fue 36.6 °C en 2017, y llegó a 39.0 °C en 2020 y 39.2 °C en 2023.
  **Un verano caluroso pondría al modelo fuera del rango de temperatura que vio.**

**Cómo se implementaría aquí (medio día):** una llamada a Open-Meteo con las coordenadas de Tetuán
(35.58, −5.37) para 1995-2024 a resolución diaria. Va como contexto en la sección de amenazas a la validez
del paper, no como variable del modelo.

## 8. Ceuta: el único sistema comparable con varios años a 5 minutos

**Qué resuelve:** (a), (b) y (c) en un sistema vecino, no en Tetuán. No extiende el histórico de
Amendis, pero permite responder con datos dos preguntas que con 2017 no se pueden: si el pipeline
aguanta un año y un verano que no vio, y cuánto mejora con dos o tres años de entrenamiento.

**Qué es:** Red Eléctrica (REE) publica la demanda del sistema eléctrico de Ceuta, una ciudad aislada
eléctricamente a menos de 40 km de Tetuán, **cada 5 minutos, en MW**, desde el **11 de mayo de 2019
hasta hoy** (comprobado consultando días de 2019 a octubre de 2026). También hay serie para Melilla
(comprobado en 2023).

**Qué tan comparable es (experimento, 24 días muestreados de 2023, dos por mes):**

| | Ceuta 2023 | Zona 1 | Zona 2 | Zona 3 |
|---|---:|---:|---:|---:|
| Demanda media | ~22 MW | 32.3 MW | 21.0 MW | 17.8 MW |
| Mes más alto / mes más bajo | 1.26 | 1.26 | 1.40 | 2.55 |
| Julio / promedio | 1.14 | 1.11 | 1.15 | 1.58 |
| Correlación del perfil horario medio con Ceuta | — | 0.88 | 0.90 | 0.67 |

Escala, estacionalidad y forma diaria se parecen mucho a las de la Zona 1 y la Zona 2. La Zona 3, con su
veraneo, no tiene equivalente en Ceuta.

**Cómo se accede:**

- **Datos a 5 minutos:** el servicio que alimenta la web *Seguimiento de la demanda* de REE devuelve un día
  por consulta, en JSONP:
  `https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?curva=CEUTAAU&fecha=AAAA-MM-DD`
  (campo `dem`; `MELILLAAU` para Melilla). Son unas 2,700 consultas para todo el periodo; con una pausa de
  un segundo entre consultas, menos de una hora. **No es una API documentada:** la deduje del código de
  la web y puede cambiar sin aviso.
- **API oficial (REData):** `apidatos.ree.es` es pública y sin registro, pero para Ceuta solo devolvió
  agregados (probé la demanda mensual de 2017 con `geo_limit=ceuta&geo_ids=8744`). El widget de demanda
  en tiempo real no respondió para Ceuta.
- **e·sios:** la API de REE con todos los indicadores pide un token personal, que se solicita por correo.
  No verifiqué qué indicador corresponde a la demanda de Ceuta.
- **Clima de Ceuta:** el dataset de REE no trae clima; habría que unirlo con ERA5 de Open-Meteo para las
  coordenadas de Ceuta.

**Licencia:** no es abierta. El aviso legal de REE reserva la reproducción a su autorización escrita,
salvo usos informativos, no comerciales y académicos que citen a REE como fuente, no alteren el sentido de
los datos e indiquen la fecha de actualización. Para el proyecto: citar la fuente, **no subir los datos
crudos al repositorio** y descargarlos con un script.

**Cómo se implementaría aquí (2 a 3 días; opcional):**

1. Un script `ceuta.py` que descargue y guarde el bronze, remuestree a 10 minutos y una el ERA5.
2. **Validación externa** (lo más valioso): correr el mismo pipeline en Ceuta entrenando con un año y
   probando en el verano siguiente, y repetir con dos y tres años. La curva de error contra años de
   entrenamiento contesta "cuánto histórico hace falta" con un sistema parecido.
3. **Preentrenamiento** (más arriesgado): un modelo global que entrene con Ceuta 2019-2025 y Tetuán 2017,
   con una variable de sistema. Ceuta aporta veranos y Ramadanes en distintas estaciones.

**Implementación:** la ingesta está en `src/tetouan_power_forecast/ceuta.py` y la validación (entrenar sin
verano o con 1, 2 o 3 años y evaluar julio y agosto de 2020 a 2026), en
[`experimentos/ceuta/`](../experimentos/ceuta/). Todo se corre en Colab con
[`notebooks/00b_ceuta.ipynb`](../notebooks/00b_ceuta.ipynb).

**Riesgos:** el endpoint no documentado; las zonas horarias (Ceuta usa la hora peninsular española; la
del dataset de Tetuán no está documentada); y que Ceuta es otro sistema, con otra mezcla de clientes. Lo
que se aprenda ahí es evidencia indirecta, no una validación sobre Amendis.

### Resultado de la validación externa

Se corrió en Colab con los datos descargados el 23 de octubre de 2026. El silver tiene 391,975
intervalos de 10 minutos, del 11 de mayo de 2019 al 22 de octubre de 2026, sin fechas repetidas y con el
clima completo; a 878 intervalos (0.22 %) les falta la demanda y 4 tienen una demanda no positiva. Los
huecos de hasta una hora se rellenan por interpolación y los demás quedan fuera de la evaluación.

Para cada verano se entrenaron el modelo actual (V0, en nivel y con calendario anual) y el objetivo en
razón (V4, sin calendario anual), con las variables del [anexo](#anexo-el-experimento) salvo que en
Ceuta no hay otras zonas ni una lista de feriados. Las cuatro historias terminan el 30 de junio: *sin
verano* es enero a junio del mismo año, como el pliegue de julio del origen móvil de Tetuán; *1, 2 y 3
años* son los 12, 24 o 36 meses anteriores. Se evalúan julio y agosto.

MAPE (%) de julio y agosto en Ceuta:

| Verano | Mejor ingenua | Actual, sin verano | Razón, sin verano | Actual, 1 año | Razón, 1 año | Razón, 2 años | Razón, 3 años |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2020 (confinamiento) | 4.72 ("semana pasada") | 2.60 | 2.06 | 1.84 | 1.70 | — | — |
| 2021 | 3.85 ("semana pasada") | 2.61 | 2.37 | 1.62 | 1.53 | 1.48 | — |
| 2022 | 4.58 (persistencia) | 3.18 | 2.93 | 2.54 | 2.43 | 2.34 | 2.33 |
| 2023 | 4.84 (persistencia) | 2.43 | 2.07 | 1.95 | 1.86 | 1.74 | 1.75 |
| 2024 | 4.47 (persistencia) | 3.68 | 2.62 | 2.30 | 2.02 | 1.90 | 1.91 |
| 2025 | 4.60 (persistencia) | 2.35 | 1.89 | 1.84 | 1.69 | 1.54 | 1.50 |
| 2026 | 4.64 (persistencia) | 3.03 | 2.14 | 1.96 | 1.71 | 1.67 | 1.63 |
| **Media 2022-2026** | **4.63** | **2.93** | **2.33** | **2.12** | **1.94** | **1.84** | **1.82** |

Con dos y tres años, el modelo actual promedia 1.98 y 1.97 %. Las medias son de 2022 a 2026, los únicos
veranos con las cuatro historias.

- **Todos los modelos le ganan a la mejor referencia ingenua en todos los veranos.** El objetivo en razón
  tiene entre un 37 y un 68 % menos MAE que ella; el modelo actual sin verano, en 2024, solo un 13 %.
- **El objetivo en razón le gana al modelo actual en los 25 pares de verano e historia.** Con al menos un
  verano visto, el MAE baja entre un 3 y un 14 %; sin verano visto, entre un 9 y un 31 %.
- **No haber visto un verano cuesta poco con el objetivo en razón:** de 1.94 a 2.33 % (+0.39 puntos, un
  20 % más). Con el modelo actual, de 2.12 a 2.93 % (+0.81 puntos, un 38 % más), y el salto llega a 1.4
  puntos en 2024.
- **Más años aportan poco:** el segundo baja el MAPE 0.1 puntos y el tercero no cambia nada (1.84 contra
  1.82 %).
- **La mejor referencia ingenua cambia con el sistema:** en Ceuta es la persistencia desde 2022; en
  Tetuán, "ayer" o "semana pasada" según la zona y el mes. Por eso cada comparación va contra la mejor
  ingenua de su propio periodo.

**Qué significa para Tetuán.** En el origen móvil de Tetuán, la cota pesimista de julio (sin verano
previo) queda, con el objetivo en razón, un 26 % por encima de la optimista en la Zona 1 (2.70 contra
2.15 %) y un 23 % en la Zona 3 (2.46 contra 2.00 %). En Ceuta, la distancia entre no haber visto un
verano y haber visto uno es del mismo orden (20 %). Eso respalda reportar el verano de Tetuán como ese
rango, y da una cifra para el paper: con un año más de datos, el error de verano bajaría alrededor de un
20 %, no a la mitad. Sigue siendo evidencia de otro sistema, con otra mezcla de clientes y sin el veraneo
de la Zona 3.

Los resultados por verano están en `reportes/ceuta/resultados_validacion.csv`, dentro de la carpeta de
datos; el diseño y cómo correrlo, en [`experimentos/ceuta/`](../experimentos/ceuta/).

## 9. Día similar y vecinos más cercanos

**Qué resuelve:** (a), parcialmente. Los métodos de patrones de Dudek (2015) buscan en el histórico los
días cuya forma reciente (normalizada por su nivel) se parece a la actual y promedian lo que pasó
después. Son interpretables, no dependen del nivel y trabajan bien con poco histórico porque no estiman
muchos parámetros. A una hora adelante, sin embargo, son casi una versión más fina de las referencias
"ayer" y "semana pasada".

**Cómo se implementaría aquí (medio día; opcional):** `KNeighborsRegressor` de scikit-learn sobre las
últimas 24 h divididas por su media, con el objetivo también normalizado. Sirve como referencia
adicional o para la app ("días parecidos al de hoy"). No espero que le gane al modelo de árboles con
objetivo relativo.

## Qué no recomiendo y por qué

- **Buscar otro año de Tetuán o de la ONEE para este plazo.** UCI solo tiene 2017 y no encontré otra
  publicación de Amendis. La ONEE dejó de publicar sus curvas de carga hacia 2008; desde entonces solo
  aparece la del día de máxima demanda, como imagen, en su informe anual (Bennouna, 2024). Escribir a los
  autores del dataset no cuesta nada, pero no hay que planificar con esa respuesta.
- **Preentrenar con España peninsular, ENTSO-E u Open Power System Data.** Son demandas de sistemas de
  decenas de GW, horarias o cuartohorarias y mucho más suaves que una subestación de 30 MW; OPSD además se
  detuvo a mediados de 2020. La forma a una hora de un país no informa la de una subestación. No verifiqué
  que los términos de ENTSO-E sean una licencia abierta tipo CC BY. Si se quiere un sistema externo, Ceuta
  es mucho más parecido.
- **Empezar por ajustar (*fine-tuning*) modelos fundacionales.** Con Colab Pro es factible, pero la
  ganancia reportada es modesta (en Kaljevic et al., ajustar Chronos-2 bajó su MAPE entre 0.17 y 0.21
  puntos, a un día), con un año el riesgo de sobreajuste es alto y cada pliegue exige un ajuste aparte
  para no filtrar el futuro. Primero, la versión sin ajuste; el ajuste, solo si esa referencia resulta
  competitiva y queda tiempo.
- **TimeGPT.** Es una API cerrada: hay que enviar los datos fuera, la prueba gratuita es limitada y los
  resultados no se pueden reproducir sin la cuenta. Chronos-2 cubre el mismo papel con pesos abiertos.
- **Moirai y Lag-Llama.** Moirai tiene licencia no comercial "solo para investigación" (aceptable en un
  curso, pero no aporta sobre Chronos-2) y se instala desde GitHub; Lag-Llama quedó entre los peores en el
  benchmark de hogares.
- **Redes profundas entrenadas desde cero** (LSTM, Transformers). Necesitan más datos que los árboles,
  ajuste de hiperparámetros caro y no resuelven la extrapolación. Con un año, el riesgo de sobreajuste es
  mayor que la ganancia esperada.
- **Aumentación sintética** (ruido, escalado de magnitud, mezcla de días). No crea información sobre
  regímenes que no se observaron: escalar el verano para "inventar" uno más caluroso supone una respuesta
  al calor que no se puede validar. Con el objetivo relativo, la aumentación de nivel deja de ser
  necesaria. No encontré evidencia de que ayude a una hora en subestaciones.
- **Reemplazar la temperatura del dataset por ERA5 o por la del aeropuerto.** No son el mismo sensor
  (correlación de 0.83 y 2 a 3 °C de diferencia en julio).
- **Una variable "después del 25 de octubre"** o borrar el periodo de la transferencia. La variable se
  aprendería con 12 días y en la prueba valdría siempre 1; borrar el periodo oculta justo el tipo de cambio
  que el operador produce.
- **Validación cruzada aleatoria** (`KFold` con `shuffle=True`). Con datos cada 10 minutos, filas vecinas
  casi idénticas quedan a ambos lados de la partición y el error sale optimista.

## Evaluación honesta con un solo año

### Diseño

1. **Origen móvil mensual con ventana creciente.** Para cada mes de marzo a diciembre: entrenar con todo
   lo anterior (menos un hueco de 6 pasos, para que ningún objetivo del entrenamiento caiga dentro del mes
   evaluado), predecir el mes y guardar el error por zona. Son 10 pliegues alineados con el calendario, que
   se leen como estaciones, a diferencia de los de `TimeSeriesSplit`, que tienen tamaño fijo y no
   coinciden con los meses. Es el esquema de origen móvil de Tashman (2000) y el que Cerqueira, Torgo y
   Mozetič (2020) encontraron más fiable para series reales no estacionarias.
2. **La prueba de noviembre-diciembre se mantiene**, pero con **reentrenamiento semanal**: el modelo se
   reajusta cada 7 días con todo lo observado hasta ese momento, como lo haría el centro de control. No usa
   información futura y muestra si el modelo se adapta al régimen posterior a la transferencia.
3. **Cada pliegue se compara contra la mejor referencia ingenua de ese mismo pliegue**, no contra una fija,
   porque la mejor cambia con la estación y la zona.

### Cómo estimar el desempeño en la temporada que la prueba no cubre

Para el verano de la Zona 3 conviene reportar un rango, no un número:

- **Cota pesimista:** el pliegue de julio del origen móvil, en el que el modelo nunca vio un verano: es el
  caso de desplegarlo sin haber pasado por uno. El pliegue de agosto ya entrenó con julio, así que mide el
  desempeño después de un mes de verano, no sin haber visto ninguno.
- **Cota optimista:** dejar fuera el mes (julio o agosto) y entrenar con el resto del año, incluido el
  futuro. El margen es de un día antes del mes, para que ningún objetivo del entrenamiento caiga dentro
  de él, y de ocho días después, porque el rezago y la media semanales miran una semana atrás. Es lo más cerca que se puede estar de "ya vio un verano". Bergmeir,
  Hyndman y Koo (2018) justifican la validación cruzada en modelos autorregresivos cuando los rezagos
  relevantes están entre las variables, pero solo si los residuos no quedan autocorrelacionados, así que
  hay que presentarla como cota, no como estimación insesgada.

Experimento, MAPE en verano (modelo actual / objetivo en razón):

| | Origen móvil | Mes fuera con margen (cota optimista) | Mejor ingenua del mes |
|---|---:|---:|---:|
| Zona 3, julio (cota pesimista: sin verano previo) | 6.62 / 2.46 % | 4.21 / 2.00 % | 3.38 % ("ayer") |
| Zona 3, agosto (ya vio julio) | 3.57 / 3.17 % | 3.16 / 3.04 % | 4.01 % ("ayer") |
| Zona 1, julio (cota pesimista: sin verano previo) | 4.61 / 2.70 % | 2.90 / 2.15 % | 4.37 % ("ayer") |
| Zona 1, agosto (ya vio julio) | 2.33 / 1.98 % | 2.23 / 1.92 % | 3.69 % ("ayer") |

Con el objetivo en razón, julio en la Zona 3 queda entre 2.0 y 2.5 % de MAPE y agosto, después de ver
julio, entre 3.0 y 3.2 %, siempre por debajo de la mejor ingenua. Con el modelo actual, julio va de 4.2 a
6.6 %, y la cota pesimista pierde contra "ayer". Ese rango, junto con la mejor ingenua, es lo que se reporta para
la temporada que la prueba no cubre. En Ceuta, con varios años, no haber visto un verano costó un 20 % más
de MAPE con el objetivo en razón ([resultado](#resultado-de-la-validación-externa)), del mismo orden que
la distancia entre las dos cotas de julio.

### Cómo tratar la transferencia en la evaluación

- Partir la validación en antes y después del 25 de octubre y reportar ambas.
- Reportar la Zona 1, la Zona 2 **y su suma**, para separar el error de pronosticar la demanda del de no
  anticipar una maniobra.
- Marcar la semana del 25 de octubre al 1 de noviembre: ahí la referencia "semana pasada" compara contra
  la topología anterior y su error se infla.

### Incertidumbre de las comparaciones

Un solo periodo de prueba de 8 semanas y errores autocorrelacionados hacen que diferencias de pocos puntos
porcentuales puedan ser ruido. Hewamalage, Ackermann y Bergmeir (2023) recomiendan acompañar las
comparaciones con pruebas estadísticas adecuadas a series. Una forma simple: *bootstrap* por bloques de
días de la diferencia de MAE entre el modelo y la mejor referencia, con su intervalo al 95 %.

### Texto para la sección de amenazas a la validez del short paper

Hay que adaptarlo a lo que el grupo implemente finalmente (por ejemplo, si se quita o no el calendario
anual).

> **Amenazas a la validez.** *Externa:* los datos cubren un único año (2017), con un verano
> climáticamente típico según ERA5 (puesto 19 de 30 en temperatura media de julio-agosto entre 1995 y
> 2024); el desempeño ante veranos más calurosos, como los de 2020 y 2023, o ante el crecimiento de la
> demanda no está evaluado, y los resultados corresponden a tres subestaciones de una ciudad. *Interna:*
> el 25 de octubre una transferencia de carga entre las zonas 1 y 2 cambió su nivel (−12.5 % y +11.3 %),
> de modo que la prueba ocurre en un régimen que el entrenamiento no contiene; con un solo año, las
> variables de calendario anual pueden identificar épocas en vez de estaciones, por lo que se
> excluyeron. *De constructo:* la unidad (kW) y la identidad de las zonas provienen de fuentes
> secundarias, y el MAPE no refleja la asimetría del costo entre subestimar y sobrestimar un pico, que se
> reporta aparte. *De conclusión:* la prueba abarca ocho semanas con errores autocorrelacionados; las
> diferencias se acompañan de intervalos por *bootstrap* por bloques y del error por mes del origen móvil.
> El verano de la Zona 3 solo se evalúa con origen móvil, como un rango entre una cota pesimista y una
> optimista. Como evidencia indirecta, en Ceuta, un sistema vecino con datos de 2019 a 2026, entrenar sin
> haber visto un verano subió el MAPE de julio y agosto de 1.94 a 2.33 %, todavía la mitad que la mejor
> referencia ingenua.

## Anexo: el experimento

**Cómo reproducirlo.** Los scripts están en [`experimentos/historico/`](../experimentos/historico/) y leen
el silver del medallón. Se corren desde la raíz del repo, en local o en Colab
([instrucciones](../experimentos/historico/README.md)):

| Script | Qué produce | Tablas de este documento |
|---|---|---|
| `rolling` | Variantes V0 a V4 y las referencias ingenuas, por mes y en la prueba | Opción 1, opción 5 y los resultados por mes |
| `global_model` | Modelo global de las tres zonas frente al local | Opción 2 |
| `quiebre` | Antes y después del 25 de octubre, y reentrenamiento semanal | Opción 4 |
| `lomo` | Mes fuera con margen (cota optimista del verano) | Evaluación honesta |
| `cuota` | Cuota de la Zona 1, punto de quiebre, días en espejo y detector | Opción 4 |

Al pasar los scripts al repo se volvió a correr `rolling Z1`, que dio exactamente las mismas cifras. En
`lomo` se amplió el margen posterior a ocho días, para que las variables semanales no miren el mes
evaluado; sus cifras son las de esa corrida. `cuota` se escribió después y sus cifras reemplazan a las
del primer análisis.

**Datos.** El silver de 2017 (52,416 filas). El primer origen válido es el 8 de enero, por el rezago
semanal y la media de 7 días. Objetivos: el consumo en t+6 de cada zona y de la Zona 1 + la Zona 2.

**Variantes.**

| | Variables | Objetivo |
|---|---|---|
| Actual (V0) | Las del gold: hora, minuto del día, día, mes, día de la semana, día del año, fin de semana; senos y cosenos diario, semanal y anual; las cinco de clima en t; rezagos 0, 1, 2 y 6 de las tres zonas; rezago de 24 h hacia t+6; media y desviación móviles de 1 h | Nivel |
| Sin calendario anual (V1) | V0 sin día, mes, día del año ni seno y coseno anual | Nivel |
| V2 | V1 + rezago semanal (t+6−1008 y t−1008), feriado y Ramadán de la fecha de t+6, temperatura media de 24 h | Nivel |
| Cambio (V3) | V2 | `y(t+6) − y(t)` |
| Razón (V4) | V2 con las variables de consumo divididas por la media de 24 h de su zona, más la media de 24 h sobre la de 7 días | `y(t+6) / m24(t)` |
| V5 | V4 + calendario anual | Razón |
| Global | V4 solo con variables de la propia zona; tres zonas apiladas, zona como categórica | Razón |

Feriados: los de la [investigación](investigacion.md) más el 1 de enero, el 30 de julio, el 20 de agosto,
el 2 de septiembre, el 21 de septiembre y el 18 de noviembre. Ramadán: del 27 de mayo al 25 de junio de
2017. Ambas listas son aproximadas y el grupo debe verificarlas.

**Modelo.** `HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, early_stopping=False,
random_state=0)`, sin ajuste de hiperparámetros y con una sola semilla.

**Esquemas.**

- Origen móvil: para cada mes de marzo a diciembre, entrenamiento con los orígenes anteriores al día 1
  menos 60 minutos y evaluación con los orígenes del mes.
- Prueba en las tablas generales: el último 15 % de los orígenes válidos (desde el 7 de noviembre a las
  09:50), entrenando con todo lo anterior menos 6 pasos. En el análisis de la transferencia y del
  reentrenamiento semanal, la prueba empieza el 6 de noviembre a las 09:30, como la partición oficial.
- Mes fuera: julio o agosto como prueba, con un día de margen antes y ocho después, y el resto del año
  como entrenamiento.
- Las métricas se calculan sobre el nivel reconstruido, en kW.

**Resultados por mes (MAPE, %).**

| Zona 1 | mar | abr | may | jun | jul | ago | sep | oct | nov | dic | prueba |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Actual | 2.28 | 2.56 | 2.96 | 2.92 | 4.61 | 2.33 | 2.28 | 2.56 | 2.61 | 1.83 | 2.07 |
| Razón | 2.32 | 2.52 | 2.91 | 3.14 | 2.70 | 1.98 | 2.04 | 1.89 | 1.80 | 1.54 | 1.68 |
| Global | 2.02 | 2.21 | 2.57 | 3.14 | 2.00 | 1.81 | 1.89 | 1.84 | 1.77 | 1.51 | 1.63 |
| Mejor ingenua | 3.30 | 4.34 | 3.98 | 5.05 | 4.37 | 3.69 | 4.69 | 3.50 | 3.17 | 2.87 | 2.92 |

| Zona 2 | mar | abr | may | jun | jul | ago | sep | oct | nov | dic | prueba |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Actual | 3.12 | 3.92 | 3.36 | 3.30 | 5.35 | 2.85 | 3.40 | 2.62 | 2.71 | 2.19 | 2.48 |
| Razón | 2.82 | 3.59 | 3.24 | 3.58 | 2.53 | 2.12 | 2.62 | 2.09 | 2.22 | 1.84 | 2.05 |
| Global | 2.69 | 3.41 | 2.98 | 3.44 | 2.26 | 2.00 | 2.64 | 2.02 | 2.09 | 1.83 | 1.93 |
| Mejor ingenua | 4.69 | 6.42 | 5.78 | 6.99 | 6.10 | 4.44 | 6.62 | 5.03 | 4.69 | 4.10 | 4.29 |

| Zona 3 | mar | abr | may | jun | jul | ago | sep | oct | nov | dic | prueba |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Actual | 2.17 | 4.43 | 2.66 | 3.81 | 6.62 | 3.57 | 6.38 | 4.20 | 6.15 | 3.48 | 5.30 |
| Razón | 2.34 | 2.25 | 2.72 | 2.88 | 2.46 | 3.17 | 3.81 | 2.63 | 5.52 | 2.56 | 4.31 |
| Global | 2.32 | 2.18 | 2.86 | 2.85 | 2.06 | 3.04 | 3.20 | 2.66 | 4.64 | 2.53 | 3.73 |
| Mejor ingenua | 3.38 | 3.24 | 3.21 | 3.50 | 3.38 | 4.01 | 6.65 | 3.91 | 7.68 | 3.93 | 6.06 |

La mejor ingenua es, en cada mes, la de menor error entre persistencia, "ayer" y "semana pasada". Las
referencias de la prueba coinciden con las de la investigación (2.92 % contra 2.94 % de "semana pasada" en
la Zona 1), lo que indica que el experimento está alineado con el pipeline del grupo.

**Limitaciones.** Sin ajuste de hiperparámetros, una sola semilla y sin intervalos de confianza. La
variante "actual" reproduce las variables del gold, no el notebook ni los hiperparámetros del grupo, así
que los porcentajes pueden cambiar con su pipeline. Lo robusto es la dirección y el tamaño relativo de
los efectos.

## Fuentes

### Datos

- Salam, A. y El Hibaoui, A. (2018). *Power Consumption of Tetouan City* [dataset]. UCI, CC BY 4.0.
  <https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city>
- Bennouna, A. (2024, 26 de julio). Impact de l'autoproduction sur la demande d'électricité sur le réseau
  marocain. *EcoActu*. Sobre la publicación de curvas de carga de la ONE hasta 2008:
  <https://ecoactu.ma/impact-autoproduction-demande-electricite/>
- REE, *Seguimiento de la demanda de energía eléctrica* (web): <https://demanda.ree.es/visiona/home>.
  Servicio que la alimenta, consultado para Ceuta y Melilla:
  <https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/demandaGeneracionPeninsula?curva=CEUTAAU&fecha=2023-07-05>.
  Los datos de Ceuta de la validación externa se descargaron el 23 de octubre de 2026.
- REE, REData API: <https://www.ree.es/es/apidatos>. Consulta de la demanda mensual de Ceuta en 2017:
  <https://apidatos.ree.es/es/datos/demanda/evolucion?start_date=2017-01-01T00:00&end_date=2017-12-31T23:59&time_trunc=month&geo_trunc=electric_system&geo_limit=ceuta&geo_ids=8744>
- REE, aviso legal (condiciones de reutilización): <https://www.ree.es/es/aviso-legal>
- Cliente de e·sios con el procedimiento para pedir el token (documentación de terceros):
  <https://www.mintlify.com/datons/python-esios/core/client>
- Open Power System Data, *Time series*: <https://data.open-power-system-data.org/time_series/>
- ENTSO-E, Transparency Platform: <https://www.entsoe.eu/data/transparency-platform/>
- Open-Meteo, Historical Weather API: <https://open-meteo.com/en/docs/historical-weather-api>; licencia:
  <https://open-meteo.com/en/licence>; límites de uso: <https://open-meteo.com/en/pricing>
- ECMWF, licencia CC BY de ERA5 *hourly single levels*: <https://confluence.ecmwf.int/x/l-xCDQ>
- Meteostat, estación 60318 (Tetuán / Sania Ramel): <https://meteostat.net/en/station/60318>; licencia:
  <https://dev.meteostat.net/license.html>; descarga masiva usada:
  <https://bulk.meteostat.net/v2/hourly/60318.csv.gz>
- NASA POWER, API horaria: <https://power.larc.nasa.gov/docs/services/api/temporal/hourly/>; metodología
  y resoluciones: <https://power.larc.nasa.gov/docs/methodology/>; texto de agradecimiento sugerido:
  <https://docs.ropensci.org/nasapower/>

### Modelos fundacionales

- Chronos (código y modelos, Apache-2.0): <https://github.com/amazon-science/chronos-forecasting>;
  ficha de Chronos-2: <https://huggingface.co/amazon/chronos-2>
- Ansari, A. F. et al. (2025). *Chronos-2: From Univariate to Universal Forecasting*.
  <https://arxiv.org/abs/2510.15821>
- TimesFM (código; licencias de 2.5 y 3.0): <https://github.com/google-research/timesfm>; ficha de
  TimesFM 2.5: <https://huggingface.co/google/timesfm-2.5-200m-pytorch>
- TTM r2 (IBM Granite): <https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2>
- Moirai 2.0: <https://huggingface.co/Salesforce/moirai-2.0-R-small>
- Lag-Llama: <https://huggingface.co/time-series-foundation-models/Lag-Llama>
- TimeGPT, planes y precios: <https://docs.nixtla.io/docs/getting-started-timegpt_subscription_plans_and_pricing>
- Consumo de unidades de cómputo de Colab por GPU (fuentes de terceros, sin verificar contra Google):
  <https://www.thundercompute.com/blog/google-colab-alternatives>,
  <https://www.spheron.network/blog/google-colab-alternatives-8-gpu-clouds-compared-2026/>
- Listas de datos de preentrenamiento revisadas:
  <https://huggingface.co/datasets/Salesforce/GiftEvalPretrain>,
  <https://huggingface.co/datasets/Salesforce/lotsa_data>,
  <https://huggingface.co/datasets/autogluon/chronos_datasets>
- Kaljevic, T., Arzola, I. y Zhang, Y. (2026). *Benchmarking Time Series Foundation Models for Load
  Forecasting Under Covariate Uncertainty*. <https://arxiv.org/abs/2610.07232>
- Meyer, M. et al. (2024). *Benchmarking Time Series Foundation Models for Short-Term Household
  Electricity Load Forecasting*. <https://arxiv.org/abs/2410.09487>
- Liao, W. et al. (2025). TimeGPT in load forecasting: A large time series model perspective. *Applied
  Energy*, 379, 124973. <https://arxiv.org/abs/2404.04885>
- Emami, P., Sahu, A. y Graf, P. (2023). *BuildingsBench: A Large-Scale Dataset of 900K Buildings and
  Benchmark for Short-Term Load Forecasting*. NeurIPS Datasets & Benchmarks.
  <https://arxiv.org/abs/2307.00142>

### Pronóstico de carga y evaluación

- Taylor, J. W. (2008). An evaluation of methods for very short-term load forecasting using
  minute-by-minute British data. *International Journal of Forecasting*, 24(4), 645-658.
  <https://users.ox.ac.uk/~mast0315/MinByMinLoad.pdf>
- Wang, P., Liu, B. y Hong, T. (2016). Electric load forecasting with recency effect: A big data approach.
  *International Journal of Forecasting*, 32(3), 585-597.
  <https://ideas.repec.org/a/eee/intfor/v32y2016i3p585-597.html>; resumen de los autores:
  <https://blog.drhongtao.com/2015/02/load-forecasting-recency-effect-big-data.html>
- Hong, T., Pinson, P. y Fan, S. (2014). Global Energy Forecasting Competition 2012. *International
  Journal of Forecasting*, 30(2), 357-363. <https://ideas.repec.org/a/eee/intfor/v30y2014i2p357-363.html>;
  datos: <https://blog.drhongtao.com/2016/07/gefcom2012-load-forecasting-data.html>
- Montero-Manso, P. y Hyndman, R. J. (2021). Principles and algorithms for forecasting groups of time
  series: Locality and globality. *International Journal of Forecasting*, 37(4), 1632-1653.
  <https://arxiv.org/abs/2008.00444>
- Dudek, G. (2015). Pattern similarity-based methods for short-term load forecasting, Part 1:
  Principles. *Applied Soft Computing*, 37, 277-287. <https://gdudek.el.pcz.pl/files/SBFM_Principles_15.pdf>
- Truong, C., Oudre, L. y Vayatis, N. *ruptures: change point detection in Python* (BSD-2-Clause).
  <https://github.com/deepcharles/ruptures>; <https://arxiv.org/abs/1801.00826>
- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: an analysis and review.
  *International Journal of Forecasting*, 16(4), 437-450. <https://doi.org/10.1016/S0169-2070(00)00065-0>
- Cerqueira, V., Torgo, L. y Mozetič, I. (2020). Evaluating time series forecasting models: An empirical
  study on performance estimation methods. *Machine Learning*, 109, 1997-2028.
  <https://arxiv.org/abs/1905.11744>
- Bergmeir, C., Hyndman, R. J. y Koo, B. (2018). A note on the validity of cross-validation for
  evaluating autoregressive time series prediction. *Computational Statistics & Data Analysis*, 120,
  70-83. Versión de trabajo: <https://ideas.repec.org/p/msh/ebswps/2015-10.html>
- Hewamalage, H., Ackermann, K. y Bergmeir, C. (2023). Forecast evaluation for data scientists: common
  pitfalls and best practices. *Data Mining and Knowledge Discovery*.
  <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9718476/>

### Lo que no pude verificar

- Los términos de reutilización de ENTSO-E y la licencia del paquete de OPSD.
- El indicador de e·sios para la demanda de Ceuta y si su resolución es de 5 o 10 minutos.
- En qué fechas caen los 4 valores no positivos del silver de Ceuta. Un cero en julio o agosto daría un
  MAPE infinito, así que ahí no hay ceros; un valor negativo sí movería el MAPE de ese verano, de forma
  parecida para todos los métodos, y apenas el MAE.
- Un texto de licencia formal de NASA POWER (solo el agradecimiento que pide).
- El corpus completo de preentrenamiento de Chronos-2 (solo las listas publicadas).
- La longitud exacta del histórico que usaron Wang, Liu y Hong (2016).
- El desempeño de cualquier modelo fundacional sobre este dataset: el fragmento de Chronos-2 no se
  ejecutó.
- La tabla oficial de consumo de unidades de cómputo de Colab por tipo de GPU y los tiempos de
  inferencia en T4 o L4 (son estimaciones a partir de la cifra del paper de Chronos-2).
- Si la temporada de Ramadán y la hora oficial de Marruecos en 2017 coinciden con la marca de tiempo del
  dataset (afecta la alineación con Ceuta y con ERA5).

