---
title: "Pronóstico de demanda eléctrica de muy corto plazo ante niveles no vistos: de Tetuán a El Niño de 2026 en el SEIN"
subtitle: "Trabajo final (TB1) · Metodología para Data Science (1ACC0240) · UPC · ciclo 2026-2 · Grupo 3"
author:
  - "Vilchez, Rody"
  - "[Apellidos], Marcelo"
  - "[Apellidos], Adrián"
  - "[Apellidos], Andre"
  - "[Apellidos], Olenka"
date: "Borrador del 12 de noviembre de 2026"
lang: es
---

> **Pendientes del Aula Virtual** (no se inventan): extensión máxima, plantilla, normas de citación y nombre
> del archivo del short paper; fecha y hora de la entrega; apellidos de los integrantes. Mientras no se confirmen,
> este borrador usa citas estilo APA y el nombre tentativo `TB1_MDS_Grupo03.pdf`. Las notas al pie dicen de qué
> notebook, celda o tabla sale cada cifra; se quitan en la versión final.
>
> **Extensión.** El cuerpo (secciones 1 a 8) tiene unas 10,000 palabras, con 14 tablas: largo para un short paper.
> Si la plantilla limita la extensión, recortar en este orden sin perder lo esencial: (1) el glosario y la tabla de
> negocio de 4.1 (dejar el texto); (2) los hallazgos de Tetuán en 4.2 y la tabla de búsqueda de hiperparámetros
> en 4.4; (3) la tabla de adaptación de 2026 (dejar C − A, D − B y la frase de la alerta); (4) 5.3 completo salvo
> la tabla de elección y el párrafo de las exógenas; (5) la mitad de las lecciones aprendidas (dejar la 1, la 2 y
> la 4). Las limitaciones (6.4) y la tabla de hipótesis no se recortan.

# 1. Título del proyecto

**Pronóstico de demanda eléctrica de muy corto plazo ante niveles no vistos: de Tetuán a El Niño de 2026 en el
Sistema Eléctrico Interconectado Nacional (SEIN) del Perú.** Un problema de regresión sobre series de tiempo,
resuelto de punta a punta con CRISP-DM y puesto a prueba en tres sistemas eléctricos.

# 2. Resumen ejecutivo

Un operador de red necesita saber cuánta energía se va a demandar dentro de una hora y mañana a esta hora. Los
modelos de pronóstico suelen fallar cuando la demanda llega a niveles que no vieron al entrenar: por ejemplo, en
el primer verano de una serie corta, o durante un evento extraordinario. Este trabajo propone **una sola
metodología y la pone a prueba tres veces**, cada vez en una situación más difícil: la ciudad de Tetuán
(Marruecos), con un único año de datos; Ceuta (España), un sistema vecino con siete veranos; y las tres áreas
operativas del SEIN del Perú durante El Niño Costero extraordinario de 2026, el caso central.

La metodología tiene cuatro piezas: el modelo aprende la **razón** entre la demanda futura y la media de las
últimas 24 horas, no el nivel; se usan solo variables que el operador conoce en el momento de predecir (**regla
de información**); el modelo se compara contra la **mejor de tres referencias ingenuas** (lo mismo que ahora,
que ayer o que la semana pasada a esa hora); y toda diferencia se reporta con su intervalo por **bootstrap de
días**.

Resultados. En Tetuán, el modelo queda entre 41 y 56 % por debajo de la mejor referencia ingenua en la prueba y le
gana en los 24 meses-zona del origen móvil.[^tet-prueba] En Ceuta, el objetivo en razón le gana al modelo en
nivel en los 25 pares de verano e historia, y entrenar sin haber visto un verano cuesta 0.38 puntos de MAPE
(2.31 frente a 1.93 %), la mitad del error de la mejor referencia (4.62 %).[^ceuta] En el SEIN, durante 2026
(ICEN de 3.98 en agosto, el mayor desde 1997-98), un modelo entrenado hasta 2025 y sin tocar durante la prueba
redujo el error a 1 hora en 51.7 % (Norte), 57.9 % (Centro) y 29.1 % (Sur) frente a la mejor referencia, y a 24
horas en 34.5, 42.2 y 11.9 %; la mejora fue mayor que en 2025 en cinco de los seis casos.[^fr26] Reentrenar cada
semana y agregar clima o El Niño cambian el error alrededor de 1 %: a 1 hora ayudan poco; a 24 horas, con
temperaturas fuera de todo lo visto, el clima **empeora** el pronóstico en el Norte y el Centro.[^abl26]
"Sin efecto" también es un resultado.

Recomendación para el operador: pronosticar la razón con la media de 24 horas, medirse contra la mejor referencia
ingenua, reentrenar cada semana a 1 hora y no apoyarse en el clima a 24 horas durante un evento extraordinario.
La app del proyecto ejecuta el modelo y permite probar escenarios.

# 3. Introducción al problema

**El problema del operador.** El Comité de Operación Económica del Sistema (COES) opera el SEIN y programa cada
día qué centrales generan y con qué reserva. Conoce la demanda cuando ya ocurrió. Para equilibrar la carga
necesita anticiparla a dos plazos: **una hora**, para la coordinación en tiempo real (redespacho, reserva
rotante, arranque de unidades rápidas), y **24 horas**, para el programa del día siguiente. Y la necesita **por
área operativa** (Norte, Centro y Sur), porque los enlaces de transmisión entre áreas tienen límite: un desvío en
el Norte no siempre se cubre desde el Centro.[^spec-negocio] Subestimar cuesta más que sobrestimar: obliga a
arrancar generación cara de urgencia o, en el extremo, a cortar carga.

**Por qué ahora.** El Niño Costero de 2026 es extraordinario: el Índice Costero El Niño (ICEN) llegó a 3.98 en
agosto, el valor más alto desde 1997-98, y la demanda del Norte creció entre 4 y 17 % sobre 2025 (17 % en
julio).[^nb01-sein] Es exactamente la situación en la que un pronóstico entrenado con el pasado puede fallar: la
demanda sale del rango que el modelo vio.

**El vacío.** Revisamos unos 70 trabajos que usan el dataset público de Tetuán: casi ninguno se compara con
referencias ingenuas (solo dos con la persistencia y ninguno con "ayer" o "la semana pasada"), muchos pronostican
a 10 minutos, donde copiar el valor actual ya da un R² de 0.99, y varios usan información del instante que
pronostican.[^eda-tet] Para el Perú no encontramos estudios revisados por pares que midan el efecto de El Niño
sobre la demanda de Lima o del SEIN.[^spec-negocio]

**Objetivo general.** Desarrollar y validar una metodología de pronóstico de la demanda eléctrica a muy corto plazo
que se sostenga cuando la demanda se sale de lo que el modelo vio al entrenar, y medir qué ayuda más a adaptarla
durante un evento extraordinario.

**Objetivos específicos** (uno por caso, en orden de dificultad):

- **OE1 · Tetuán.** Con el consumo de las tres zonas de Tetuán (2017, cada 10 minutos, un solo año), diseñar un
  pronóstico a una hora que no dependa de aprender el nivel y situarlo frente a los trabajos publicados sobre el
  mismo dataset.
- **OE2 · Ceuta.** Verificar que la elección generaliza a un sistema vecino con varios años (2019-2026), en
  particular a veranos que el modelo no vio.
- **OE3 · SEIN.** Pronosticar la demanda de las tres áreas del SEIN cada 30 minutos, a 1 y 24 horas, y medir durante
  El Niño de 2026 qué ayuda más a adaptar el pronóstico: sumar información exógena (clima, El Niño, fallas) o
  reentrenar con más frecuencia.

Las hipótesis del OE3 se escribieron antes de evaluar ningún modelo en 2026 (sección 4.5) y se contrastan una por
una en la sección 5.4.

# 4. Metodología CRISP-DM aplicada

CRISP-DM organiza el trabajo en seis fases que se recorren en ciclo: comprensión del negocio, comprensión de los
datos, preparación, modelado, evaluación e implementación (Chapman et al., 2000). Aquí cada fase se describe para
los tres casos, con el SEIN como caso central. Lo que es común a los tres (el objetivo en razón, las referencias
ingenuas, el origen móvil y el bootstrap) se explica una vez.

> **Glosario corto.** *Persistencia:* pronosticar que dentro de una hora se consumirá lo mismo que ahora.
> *Referencia ingenua:* una regla sin aprendizaje (persistencia, ayer a la misma hora, la semana pasada a la misma
> hora). *Objetivo en razón:* el modelo predice demanda(t+H) ÷ media de las últimas 24 h, y el resultado se
> multiplica por esa media para volver a MW. *Origen móvil:* evaluar mes a mes entrenando solo con lo anterior a
> cada mes. *Bootstrap de días:* remuestrear días enteros para obtener un intervalo del 95 % de una diferencia de
> error. *Ablación:* medir cuánto cambia el error al agregar o quitar un grupo de variables. *MAE:* error absoluto
> medio, en MW (o kW). *MAPE:* el mismo error en porcentaje.

## 4.1 Comprensión del negocio

| | 1 hora | 24 horas |
|---|---|---|
| **Quién decide** | Coordinación de la operación en tiempo real del COES | Programación de la operación (el programa diario) |
| **Qué decide** | Redespacho, reserva rotante, arranque de unidades rápidas, maniobras entre áreas | Qué unidades se programan para mañana y con qué reserva; compra de combustible |
| **Costo de subestimar** | Reserva insuficiente: arrancar diésel caro o cortar carga | Programar poca generación: desvíos caros en tiempo real |
| **Costo de sobrestimar** | Reserva ociosa y arranques innecesarios | Unidades comprometidas de más |

Fuente: diseño del proyecto.[^spec-negocio]

**Criterios de éxito**, definidos antes de modelar:[^spec-eval]

1. En cada área y horizonte, el MAE del modelo queda por debajo del de la mejor de las tres referencias ingenuas,
   en el origen móvil y en la prueba.
2. En las horas de mayor demanda también le gana, y se reporta qué fracción de esas horas subestima más que el
   percentil 90 del error de la referencia (un umbral fijo de 5 % daría cero a 1 hora).
3. El tamaño del efecto de las exógenas y del reentrenamiento se reporta con su intervalo, contra una hipótesis
   escrita de antemano. No hay una meta fija de mejora.
4. Se reporta dónde falla el modelo.

En Tetuán el problema es el mismo a escala de ciudad: el centro de control del distribuidor (Amendis) decide cada
10 minutos, mirando una hora adelante, si transfiere carga entre tres subestaciones antes de un pico; en 2017 esa
maniobra quedó registrada en los datos (una transferencia de la Zona 1 a la Zona 2 el 25 de octubre).[^negocio-tet]
Ceuta no tiene decisión propia en este trabajo: es la validación externa del OE2.

**Supuesto de colaboración COES-ENFEN.** Se simula que el operador recibe en tiempo real los datos y pronósticos
de clima y de El Niño de ENFEN (SENAMHI, IGP e IMARPE). En el histórico, el dato observado hace de pronóstico
recibido, degradado con un error realista. Es un supuesto del trabajo, no un dato del COES, y se discute en la
sección 6.4.

## 4.2 Comprensión de los datos

| | Tetuán (OE1) | Ceuta (OE2) | SEIN (OE3) |
|---|---|---|---|
| **Fuente** | UCI 849, *Power Consumption of Tetouan City* (Salam y El Hibaoui, 2018), CC BY 4.0 | Red Eléctrica de España (REE), uso académico citando la fuente | COES, anexo diario del IEOD; datos públicos del operador |
| **Series** | Tres zonas de distribución, en kW | Demanda de la ciudad, en MW | Norte, Centro y Sur, en MW (y su suma, el SEIN) |
| **Periodo y resolución** | 2017, cada 10 min (52,416 registros) | May-2019 a oct-2026, cada 10 min (391,975 intervalos) | Ene-2016 a 23-oct-2026, cada 30 min (189,504 periodos) |
| **Exógenas** | Clima del propio dataset (temperatura, humedad, viento, radiación) | Clima de ERA5 (Open-Meteo) | ERA5 por área, ICEN (IGP), Niño 1+2 (NOAA), eventos del COES, SAIDI (Osinergmin), feriados |
| **Partición** | 70/15/15 cronológica; prueba: 6-nov a 30-dic | Un verano por vez (jul-ago), entrenando con 0, 1, 2 o 3 años | Entrenamiento 2016-2024, validación 2025, prueba ene-oct 2026 |

Fuentes: documentación de datos del proyecto y los notebooks de comprensión.[^datos-fuentes]

**Qué se encontró en el SEIN** (notebook `01_sein_datos_preparacion`):[^nb01-sein]

- **Calidad.** 189,504 periodos de 30 minutos, sin valores negativos ni en cero; faltan un día de 2017 y dos en
  cada año de 2018 a 2020, en las tres áreas a la vez. Norte + Centro + Sur = SEIN de forma exacta, salvo
  periodos de 2019 (hasta 5.7 MW) y de 2026 (hasta 47.6 MW). Esto último no afecta a los modelos, que pronostican
  las áreas y no la columna SEIN.
- **Crecimiento.** La demanda media del SEIN pasó de 5,496 MW en 2016 a 6,982 MW en 2025 (+27 %), con la caída de
  la cuarentena en 2020. El Centro es el 60 % del sistema, el Sur el 25 % y el Norte el 15 %, y el Norte gana
  peso. **Con la demanda creciendo así, un modelo que aprenda el nivel queda viejo rápido.** De aquí sale el
  objetivo en razón.
- **El pico se movió.** En 2016, el 87 % de los días el máximo del SEIN caía entre las 18 y las 23 h; desde 2023,
  entre 25 y 33 %. El cambio viene del Centro. Por eso las horas de mayor demanda se definen por área y por año.
- **El Sur es distinto.** El domingo el Norte y el Centro consumen 7.5 y 9 % menos que el promedio; en el Sur casi
  no hay diferencia (−0.6 %), y la temperatura no explica su demanda (r = −0.07, frente a 0.34 en el Centro). Es
  carga minera e industrial.
- **El Niño no es una sola señal.** En 2017 la demanda del Norte cayó 6 a 7 % en marzo y abril (lluvias y daños);
  en 2023 creció 2 a 6 %; en 2026 crece 4 a 17 %. Con efectos de signo distinto según el episodio, el ICEN
  difícilmente ayuda como variable.
- **Las fallas del COES tienen tendencia.** Los eventos en curso por periodo pasaron de 0.47 en 2016 a 1.67 en
  2025, y en 2025 hay al menos uno en curso en el 91 % de los periodos: la variable refleja cómo se registran
  los eventos, no si la red falla. Se discute en 4.4 y 6.4.
- **Qué tan difícil es cada área.** A 1 hora, la mejor referencia es la persistencia en las tres áreas (MAPE de
  3.0 a 3.4 % en el Centro, 3.6 a 4.4 % en el Norte y 1.7 a 2.3 % en el Sur según el año); a 24 horas gana "la
  semana pasada" en el Norte y el Centro, y la persistencia en el Sur.

**Qué se encontró en Tetuán** (notebook `01_datos_preparacion`):[^eda-tet] archivo completo (sin nulos ni huecos,
solo falta el 31 de diciembre); la velocidad del viento toma dos estados (no es una medición continua y no se
interpreta como tal); los atípicos de la Zona 3 son demanda real de verano y no se eliminan; las tres zonas tienen
firmas distintas (urbana mixta, laboral y costera de veraneo); el 25 de octubre hubo una transferencia de carga de
la Zona 1 a la Zona 2 (−12.5 % y +11.3 %); el Ramadán sube el consumo de madrugada entre 41 y 45 %; la
persistencia es la referencia más débil y la mejor es "ayer" en las Zonas 1 y 3 y "semana pasada" en la Zona 2.
La validación cruzada temporal del modelo en nivel mostró el punto débil: en el pliegue que empieza el verano
(junio-julio) el modelo pierde contra "ayer" porque tiene que predecir niveles que no vio.

**Sesgos y limitaciones de los datos.** En Tetuán, la unidad (kW) y la identidad de las zonas vienen de fuentes
secundarias, y la temperatura del dataset no coincide con ninguna fuente externa (correlación 0.83 con ERA5). En
el SEIN, la demanda "en tiempo real" se toma del IEOD, que el COES valida y publica al día siguiente: es el
sustituto del SCADA que el operador sí tiene en vivo. El COES no publica licencia para sus datos; se cita como
fuente.

## 4.3 Preparación de los datos

**Regla de información.** Cada variable entra solo con lo que se sabía en t, el momento en que se emite el
pronóstico de t+H (H = 2 pasos a 1 hora, 48 a 24 horas), con su rezago real de publicación:[^regla]

| Grupo | Variables | Disponible en t |
|---|---|---|
| Demanda del área (M0) | Demanda en t, t−1, t−2 y t−4; la de ayer y la de la semana pasada a la hora de t+H; media y desviación de la última hora; todo dividido por la media de 24 h del área. Las otras dos áreas, igual, divididas por su propia media. Media de 24 h sobre la de 7 días | Sí (SCADA; aquí, el IEOD) |
| Calendario (M0) | Hora, minuto del día, día de la semana, seno y coseno diario y semanal, de t y de t+H; feriado nacional de t+H; indicador de la cuarentena estricta de 2020 | Sí, se conoce de antemano |
| Clima | Temperatura del área en t (la última hora ya publicada de ERA5), media de 24 h y anomalía frente a la climatología 2016-2024. A 24 h, además, la temperatura pronosticada para t+H (ver abajo) | Como observado: ERA5, con 5 días de rezago, hace de sustituto. A 24 h: supuesto de colaboración |
| El Niño | ICEN definitivo según su fecha de publicación (el de m−2 desde el día 20, el de m−3 antes); Niño 1+2 de la última semana publicada (9 días) | Sí, con su rezago |
| Fallas | Eventos del COES en curso en t, cada uno como mucho 2 días | Sí; el retraso de publicación del registro no se midió |

El pronóstico de temperatura a 24 h se simula con la temperatura observada de t+H más un error gaussiano de 1.5 °C
de desviación, sorteado una vez por día de emisión y por área (el COES recibiría un pronóstico al día), con la
misma semilla en entrenamiento, validación y prueba. Es un pronóstico **optimista**: parte del valor que ocurrió,
sin sesgo. Se discute en 6.4.

**Variantes para la ablación:** M0 (demanda y calendario), M1 (+ clima), M2 (+ El Niño), M3 (+ fallas). M4 (+
SAIDI por área) no se corrió: fue lo primero en el orden de recorte del plan. Las cuatro variantes se evalúan
sobre las mismas filas (las completas para todas), así las comparaciones son periodo a periodo.

**El objetivo en razón.** El modelo aprende demanda(t+H) ÷ media de 24 h(t) y la predicción vuelve a MW
multiplicando por esa media. Así un modelo de árboles, que no extrapola fuera del rango que vio, puede predecir
niveles nuevos: solo tiene que acertar la forma del día respecto del último día. En Tetuán se comparó con el
objetivo en nivel y con el cambio respecto de t, con el mismo algoritmo sin ajustar: el nivel dio 738.5 kW de MAE
en la validación de la Zona 1, el cambio 793.6 y la razón 613.4, frente a 1,159.6 kW de la mejor
referencia.[^tet-objetivo] **Sin calendario anual** (mes, día del año): con un solo año funciona como
identificador de época (en Tetuán, quitarlo mejoró el MAE 8.3 % en la validación cruzada temporal), y en el SEIN
el nivel reciente ya lo captura la razón.

**Partición con hueco.** Entre un tramo y el siguiente quedan H pasos sin usar (las filas cuyo objetivo cae en el
tramo siguiente), para que ningún objetivo del entrenamiento se filtre en la validación ni en la prueba. En el
SEIN, cada área queda con 154,791 periodos de entrenamiento (2016-2024), 17,518 de validación (2025) y 13,920 de
prueba (1 de enero al 17 de octubre de 2026) a 1 hora, con 26 variables en M0 y 33 en M3.[^nb01-sein] La
prueba termina el 17 de octubre (y no el 23) porque ERA5 llega con unos cinco días de rezago y las filas se
exigen completas para todas las variantes. **Las filas de 2026 se apartan en la primera celda del notebook de
modelado y no vuelven a aparecer hasta el notebook de la prueba.**

**Reproducibilidad.** Las capas de datos siguen un esquema medallón (bronze: el archivo tal como lo sirve la
fuente, con su sha256 y fecha de descarga; silver: tablas auditadas; gold: el dataset con la regla de información
ya aplicada). Las razones y los rezagos los calcula una sola función (`dataset_area`), usada por los notebooks y
por la app, y están cubiertos por pruebas automáticas (por ejemplo, que la temperatura en t sea la última hora ya
publicada y que a 24 h "ayer" coincida con la persistencia).[^regla]

## 4.4 Modelado

**Algoritmos** (criterio V de la rúbrica): tres familias, todas con el objetivo en razón.

- **Ridge:** regresión lineal con regularización L2, variables estandarizadas. Si las variables en razón ya dicen
  casi todo, un modelo lineal debería andar bien.
- **Random Forest** (scikit-learn, CPU): árboles promediados; capta interacciones como hora × día de la semana.
  Con `max_samples` ≤ 0.3, cada árbol ve una muestra chica de los 155,000 periodos.
- **Gradient Boosting** (XGBoost, GPU en el SEIN; `HistGradientBoostingRegressor` en Tetuán): árboles que
  corrigen a los anteriores; suele ser el más preciso en datos tabulares.

**Búsqueda de hiperparámetros con validación cruzada temporal.** `TimeSeriesSplit` con 5 pliegues y un hueco de
H pasos, **solo sobre el entrenamiento**, minimizando el MAE en MW; Ridge en grilla y los otros dos con búsqueda
aleatoria. Para acotar el cómputo, la búsqueda se hizo en el Centro (dos tercios de la demanda) a 1 hora con M0, y
los hiperparámetros ganadores se reutilizaron en las otras áreas, a 24 horas y en las variantes con
exógenas.[^busq26]

| Algoritmo (SEIN, Centro, 1 h, M0) | Combinaciones | MAE en la validación cruzada (MW) | Minutos | Mejores hiperparámetros |
|---|---:|---:|---:|---|
| Ridge | 13 | 72.80 | 0.1 | alpha = 100 |
| Random Forest | 15 | 51.79 | 9.1 | 100 árboles, profundidad 20, hoja mínima 5, 30 % de variables y de muestras por árbol |
| Gradient Boosting (XGBoost) | 30 | 50.34 | 3.0 | 800 árboles, tasa 0.036, profundidad 10, peso mínimo 20, submuestreo 0.85 |

Fuente: notebook 02 del SEIN, §3.[^busq26]

**Un modelo global o uno por área.** Además de un modelo por área, un solo XGBoost aprende de las tres áreas
apiladas, con el código del área como variable y solo las variables de la propia área. Como el objetivo y las
variables están en razón, las tres áreas "hablan el mismo idioma" y el modelo ve tres veces más ejemplos. Sus
hiperparámetros se buscan con la misma validación cruzada, sobre las fechas, para que las tres áreas de una fecha
queden del mismo lado. En Tetuán, con un solo año, el global fue el elegido (49.0 % de mejora media frente a 48.2 %
del mejor por zona); en el SEIN, con nueve años por área, empató (4.5).[^tet-eleccion][^sel26]

**Regla de elección, escrita antes de ver las cifras:** la mayor mejora del MAE frente a la mejor referencia de
cada área, **promediada entre las tres áreas**, en la validación. Es lo que pide el criterio de éxito y no
favorece al Centro, que tiene más demanda.

**Políticas de reentrenamiento (experimento de adaptación).** Para medir qué ayuda más cuando el nivel cambia:

| | Sin exógenas (M0) | Con exógenas (M3) |
|---|---|---|
| **Modelo fijo** (entrenado hasta el fin del tramo anterior) | A | B |
| **Reentrenado cada semana** (ventana creciente, hueco de H pasos, hiperparámetros congelados) | C | D |

Más dos variantes: reentrenar solo cuando cambia la categoría del ICEN ya publicado (la "alerta de ENFEN"), sola
y sumada a la semanal; y, por la razón que se explica abajo, la variante M2 (clima y El Niño, sin fallas) fija y
semanal.

**Sobre la variable de fallas.** En la comprensión de los datos se vio que `fallas_en_curso` es mayor que cero en
el 91 % de los periodos de 2025 y crece año a año por cómo se registran los eventos. Tal como se pudo construir
con el registro público, **no distingue la operación normal de una falla**. Se mantuvo en M3 para comparar 2026
con 2025, pero su efecto no es interpretable; por eso los resultados "con exógenas" se leen sobre M2 cuando
corresponde.

**Importancia de variables.** Por permutación en la validación de 2025: cuánto sube el MAE (en MW) al desordenar
una variable, por área y agregada por grupo. La columna de escala (`media_24h`) no es una variable del modelo
(el estimador no la ve; solo multiplica la predicción) y no entra en la importancia: desordenarla rompe la vuelta
a MW, y el aumento del error que resulta no mide información, sino ese artefacto.

## 4.5 Evaluación

- **Métricas:** MAE (la del criterio de éxito), RMSE, MAPE y R², siempre en MW sobre la predicción reconstruida.
  El R² se reporta porque se lee fácil, pero con una serie tan autocorrelada hasta la persistencia lo tiene cerca
  de 1: no sirve solo para decidir.
- **Referencias:** persistencia, ayer y semana pasada a la hora de t+H; el modelo se compara contra la mejor de las
  tres en cada área, horizonte y tramo. A 24 horas, "ayer" coincide con la persistencia.
- **Origen móvil mensual:** cada mes desde enero de 2023 se predice con un modelo entrenado con todo lo anterior
  (menos el hueco), con la climatología de la temperatura cerrada antes del primer mes evaluado. Mide si el modelo
  le gana a la referencia **todos** los meses, con El Niño de 2023 adentro.
- **Intervalos:** toda diferencia de MAE (modelo − referencia, variante − variante, política − política) va con un
  intervalo del 95 % por bootstrap de días enteros (2,000 réplicas), pareado sobre los mismos periodos.
- **Regímenes:** horas de mayor demanda (las cuatro con más demanda media, por área y año), feriados y fines de
  semana, fallas en curso, categoría de El Niño según el ICEN definitivo del mes, y, en 2026, días con
  temperatura por encima de todo lo visto en 2016-2025.
- **Diagnóstico:** real contra predicho y distribución de residuos (el equivalente de la matriz de confusión en una
  regresión), y una semana de pronóstico contra lo real.
- **Hipótesis antes que resultados.** Lo que se esperaba de 2026 se escribió al cierre de la evaluación de 2025
  (seis hipótesis, sección 5.4), después de explorar los datos de 2026 pero **antes de evaluar ningún modelo en
  ellos**, y se evaluó con reglas fijadas en código. **La prueba de 2026 se corrió una sola vez**, con el modelo,
  los hiperparámetros, las variantes y las políticas fijados en 2025 y verificados contra lo guardado. La corrida
  se interrumpió tres veces por caídas de la sesión y se retomó desde una caché de predicciones por bloque; los
  cálculos son deterministas con semilla fija y no se cambió ninguna elección.

## 4.6 Implementación

La app ejecuta el modelo sobre las capas reales del SEIN: un backend (FastAPI) que carga el XGBoost global
entrenado con 2016-2025, calcula las variables con la misma función que los notebooks y responde pronósticos a 1 y
24 horas por área; y un frontend web (HTML/JS) con tres vistas: **pronóstico** (el origen que el usuario elige, la
predicción, el intervalo empírico del 90 % y las tres referencias), **escenarios** ("¿y si mañana hace más calor?",
sobre el supuesto de colaboración) y **diagnóstico** (real contra predicho, residuos, error por régimen, ablación
e importancia, siempre sobre la prueba de 2026).[^app] Sirve el XGBoost global y no el Random Forest elegido
porque empataron en 2025 y en 2026 y el XGBoost pesa decenas de MB en vez de 1 GB. La rúbrica nombra Streamlit;
el grupo eligió una app propia asumiendo ese riesgo, con la condición de que ejecute el modelo y no muestre
resultados precalculados.

# 5. Resultados del modelo

## 5.1 Tetuán (OE1)

**Elección.** En la validación (13-sep a 6-nov), con los hiperparámetros buscados en la Zona 1, la mejora media
frente a la mejor referencia fue 49.0 % para el Gradient Boosting global, 48.2 % para Ridge y para el Gradient
Boosting por zona, y 46.9 % para Random Forest.[^tet-eleccion] Que Ridge quede a un punto de los árboles dice algo
importante: la ganancia está en las variables en razón, no en el algoritmo.

**Prueba** (6-nov a 30-dic de 2017, 7,841 periodos por zona), modelo global entrenado hasta el hueco anterior a la
prueba:[^tet-prueba]

| Zona | Mejor referencia (MAE kW) | Modelo (MAE kW · MAPE) | Mejora | Diferencia de MAE, IC 95 % | MAE en horas pico: modelo / referencia | Reentrenado cada semana |
|---|---|---|---:|---|---|---:|
| Zona 1 | Semana pasada, 838.1 | 462.5 · 1.63 % | 44.8 % | −375.6 (−474.2 a −285.8) | 365.5 / 652.6 | 446.3 (46.7 %) |
| Zona 2 | Semana pasada, 973.5 | 429.4 · 1.91 % | 55.9 % | −544.1 (−727.2 a −394.1) | 335.1 / 832.6 | 415.0 (57.4 %) |
| Zona 3 | Ayer, 723.1 | 429.0 · 3.63 % | 40.7 % | −294.0 (−441.6 a −168.9) | 350.6 / 553.6 | 415.5 (42.5 %) |

En el origen móvil (marzo a octubre), el modelo le gana a la mejor referencia del mes en los 24 meses-zona; en
julio, el primer mes de verano que el modelo nunca vio, la Zona 3 queda en 554 kW frente a 934 de la mejor
referencia.[^tet-movil] Dónde pierde: en el Ramadán, en la Zona 3, 631 frente a 588 kW de la mejor referencia
(−7.4 %); y tras la transferencia del 25 de octubre la ventaja en la Zona 1 baja de 51.2 a 39.2 %, aunque sigue
ganando.[^tet-regimenes]

**Qué pesa.** Por permutación en la validación, la importancia se concentra en el consumo actual (`Zona_t`:
4,100.8 / 2,920.4 / 1,827.9 kW en las Zonas 1 / 2 / 3), el de ayer a la hora de t+6 (`Zona_lag_24h`: 939.3 /
537.6 / 581.6) y el de la semana pasada (`Zona_lag_1w`: 683.9 / 475.3 / 311.9); el clima en t casi no aporta a
una hora (la temperatura queda en cero o por debajo).[^tet-imp]

**Frente al estado del arte.** La comparación justa es la mejora frente a la persistencia, que es lo único que los
trabajos publicados reportan; contra la mejor referencia (tabla anterior) la mejora es menor y es la que vale
para el criterio de éxito.[^tet-sota]

| Trabajo | Serie | Entrenamiento y prueba | Error del modelo | Error de la persistencia | Mejora frente a la persistencia |
|---|---|---|---|---|---|
| Wei (2023) | Cada zona, cada 10 min | Entrena con enero; prueba de febrero a diciembre | MAE 1,866 · 1,281 · 2,013 kW | — | −14 % · −11 % · **+44 %** |
| Al-Quraan et al. (2023) | Total, medias horarias | 80/20, sin decir si es cronológica | MAPE 3.43 % | MAPE 6.64 % | −48 % |
| Kshetrimayum et al. (2024) | Total, medias horarias | Origen móvil, 4 pliegues | MAPE 2.49 % | MAPE 6.60 % | −62 % |
| **Este trabajo**, pliegue de marzo | Cada zona, cada 10 min | Entrena con enero y febrero; prueba en marzo | MAE 612 · 483 · 375 kW | MAE 2,279 · 1,372 · 1,419 kW | **−73 % · −65 % · −74 %** |
| **Este trabajo**, prueba | Cada zona, cada 10 min | Entrena hasta el 6-nov; prueba nov-dic | MAE 462 · 429 · 429 kW | MAE 1,821 · 1,567 · 951 kW | **−75 % · −73 % · −55 %** |
| **Este trabajo**, prueba | Total (suma de las zonas) | Igual | MAPE 1.42 % *(por verificar)* | MAPE 6.48 % *(por verificar)* | −78 % *(por verificar)* |

Wei (2023) es el antecedente más cercano (cada zona a 60 minutos, partición cronológica) y perdió contra la
persistencia en la Zona 3 porque entrenó solo con enero y no vio el verano: es el síntoma que el objetivo en razón
corrige. Las obras a 10 minutos, las que estiman el mismo instante y las que solo reportan métricas normalizadas
no son comparables.

## 5.2 Ceuta (OE2)

Mismo pipeline, con el clima de ERA5, entrenando hasta el 30 de junio de cada año y evaluando julio y agosto. "Sin
verano" entrena con enero a junio del mismo año, como el pliegue de julio de Tetuán; "1, 2 y 3 años", con los 12,
24 o 36 meses anteriores. MAPE (%) de julio y agosto, media de 2022 a 2026:[^ceuta]

| Mejor ingenua | Nivel, sin verano | Razón, sin verano | Nivel, 1 año | Razón, 1 año | Razón, 2 años | Razón, 3 años |
|---:|---:|---:|---:|---:|---:|---:|
| 4.62 | 2.87 | **2.31** | 2.10 | **1.93** | 1.84 | 1.81 |

El objetivo en razón le gana al objetivo en nivel en los 25 pares de verano e historia (2020-2026). No haber visto
un verano cuesta 0.38 puntos con la razón (+20 %) y 0.77 con el nivel (+37 %, hasta 1.2 puntos en 2024). El segundo
año baja el MAPE 0.1 puntos y el tercero casi nada. Con eso se responde la pregunta de Tetuán: lo que más pesa es
haber visto un verano; con un año más de datos, el error de verano bajaría alrededor de un 20 %, no a la mitad.

## 5.3 SEIN: validación en 2025 (OE3, año normal)

**Algoritmos y elección**, M0 a 1 hora, con los hiperparámetros buscados en el Centro:[^sel26]

| Método | Norte: MAE (MW) · mejora | Centro | Sur | Mejora media |
|---|---|---|---|---:|
| Mejor referencia (persistencia) | 38.54 · — | 122.69 · — | 32.14 · — | — |
| Ridge por área | 26.05 · 32.4 % | 80.51 · 34.4 % | 28.17 · 12.4 % | 26.4 % |
| **Random Forest por área** | 19.67 · 49.0 % | 54.62 · 55.5 % | 24.06 · 25.1 % | **43.2 %** |
| Gradient Boosting por área | 19.58 · 49.2 % | 53.12 · 56.7 % | 24.79 · 22.9 % | 42.9 % |
| Gradient Boosting global | 19.59 · 49.2 % | 53.54 · 56.4 % | 24.72 · 23.1 % | 42.9 % |

Por la regla fijada de antemano, el elegido es el **Random Forest por área**, pero los tres modelos de árboles
están empatados en la práctica: 0.3 puntos de diferencia, que decide el Sur; XGBoost gana en el Centro y el Norte.
Se decidió reportar también el XGBoost global en 2026. Ridge queda muy atrás: aquí, a diferencia de Tetuán, las
interacciones entre la hora, el día y la demanda reciente sí importan. A 24 horas, el Random Forest queda en 28.83,
86.10 y 56.72 MW (29 %, 39 % y 14 % de mejora frente a "semana pasada", "semana pasada" y la persistencia); **el
Sur a 24 horas es el punto débil** (R² de 0.33).[^val24]

**Estable en el tiempo.** En el origen móvil, el modelo le gana a la mejor referencia del mes en los **108
meses-área** de 2023 a 2025, con una mejora mediana de 44.6 %; durante El Niño de 2023 (marzo a julio) el Norte se
mantuvo entre 47 y 50 %. Los cuatro meses más flojos son del Sur, entre diciembre y abril (el peor, enero de 2025,
2.6 %).[^movil25]

**Donde más importa.** En las cuatro horas de mayor demanda, la mejora se sostiene (55 % en el Norte, 33 % en el
Centro y 35 % en el Sur a 1 hora). El modelo subestima por encima del percentil 90 del error de la referencia en
menos del 1 % de esas horas a 1 hora y entre 1.2 y 2.4 % a 24 horas.[^reg25]

**Las exógenas casi no aportan.** A 1 hora, ninguna variante se aleja de M0 más de 0.32 MW (menos del 0.6 % del
error); el clima mejora el Centro −0.25 MW (IC −0.47 a −0.01) y nada en el Norte ni el Sur. A 24 horas, el clima
mejora el Centro −0.61 MW (IC −1.15 a −0.07), un 0.7 %, y no se distingue de cero en el Norte ni el Sur. Quitar El
Niño de M3 mejora un poco el Centro a 1 hora (−0.40 MW).[^abl25] En la importancia por permutación, el clima suma
1.10 MW en el Centro frente a 248.0 MW del grupo de demanda y calendario (`Area_t` sola, 119.5 MW; la media de la
última hora, 55.3); El Niño, 0.04, y las fallas, −0.01. En el Norte y el Sur, el grupo de demanda y calendario
pesa 49.5 y 43.4 MW, y el clima, 0.18 y 0.23.[^imp25]

**Reentrenar ayuda poco en un año normal.** Reentrenar cada semana (52 veces) baja el error a 1 hora como mucho
0.56 MW (Centro, con exógenas), menos del 1 %; sin exógenas se distingue de cero en el Centro (−0.31 MW) y el Sur
(−0.12) pero no en el Norte (−0.03). A 24 horas, solo en el Centro con exógenas (−0.59 MW). Reentrenar solo cuando
cambia la alerta de ENFEN (2 veces en 2025) es peor que cada semana.[^adap25]

## 5.4 SEIN: la prueba de 2026 (OE3, El Niño extraordinario)

**Las hipótesis, escritas al cierre de 2025:**

1. **Nivel fuera de lo visto.** El modelo fijo le gana a la mejor referencia a 1 hora en las tres áreas; en el
   Norte, la mejora baja respecto de 2025 (49 %) pero queda sobre 25 %. A 24 horas gana en el Centro y el Norte;
   el Sur puede perder.
2. **Reentrenar** cada semana ayuda más que en 2025, sobre todo en el Norte: la diferencia es negativa y su
   intervalo no cruza el cero.
3. **Exógenas a 1 hora:** M3 − M0 sigue sin distinguirse de cero.
4. **Exógenas a 24 horas:** el clima sigue ayudando en el Centro. Riesgo declarado: la temperatura de 2026 sale del
   rango de entrenamiento y los árboles no extrapolan.
5. **El Niño y fallas:** el ICEN y el Niño 1+2 no mejoran a M0 en ningún horizonte.
6. **"Sin efecto" también es un resultado.**

**El modelo fijo frente a las referencias** (1 de enero al 17 de octubre de 2026; modelo entrenado hasta 2025 y
sin tocar):[^fr26]

| Horizonte | Área | Mejor referencia: MAE (MW) · MAPE | Random Forest (elegido): MAE · MAPE · mejora | Δ MAE, IC 95 % | XGBoost global: MAE · mejora |
|---|---|---|---|---|---|
| 1 h | Norte | Persistencia, 41.8 · 3.67 % | 20.2 · 1.79 % · **51.7 %** | −21.6 (−22.1 a −21.1) | 19.9 · 52.4 % |
| 1 h | Centro | Persistencia, 128.5 · 2.98 % | 54.1 · 1.25 % · **57.9 %** | −74.5 (−75.9 a −72.9) | 53.4 · 58.4 % |
| 1 h | Sur | Persistencia, 31.6 · 1.74 % | 22.4 · 1.24 % · **29.1 %** | −9.2 (−9.6 a −8.7) | 22.4 · 29.2 % |
| 24 h | Norte | Semana pasada, 44.2 · 3.92 % | 29.0 · 2.58 % · **34.5 %** | −15.3 (−18.1 a −12.7) | 29.3 · 33.8 % |
| 24 h | Centro | Semana pasada, 135.3 · 3.12 % | 78.1 · 1.80 % · **42.2 %** | −57.1 (−71.3 a −45.3) | 80.0 · 40.9 % |
| 24 h | Sur | Persistencia, 54.8 · 3.04 % | 48.3 · 2.68 % · **11.9 %** | −6.5 (−8.9 a −4.4) | 48.9 · 10.8 % |

El método se sostiene fuera de lo visto: con el ICEN en 3.98 y la demanda del Norte hasta 17 % sobre 2025, el
modelo fijo le gana a la mejor referencia en las tres áreas y los dos horizontes, con intervalos lejos del cero, y
la mejora es **mayor que en 2025 en cinco de los seis casos** (salvo el Sur a 24 horas). Predecir la razón con la
media de 24 horas absorbe el salto de nivel. El XGBoost global empata, como en 2025.

**No se degrada a medida que El Niño se intensifica.** La mejora del Norte a 1 hora pasa de 42.9 % en enero a entre
51 y 53 % de abril a agosto, y a 61.6 % en septiembre.[^mes26] Los días con temperatura por encima de todo lo
visto en 2016-2025 (105 en el Norte, 91 en el Centro, 4 en el Sur) no son peores para el modelo a 1 hora (Norte:
54.8 % de mejora fuera de lo visto frente a 50.0 % dentro); a 24 horas en el Centro sí lo son (35.3 frente a
44.8 %). En la categoría "cálida extraordinaria" del ICEN, la mejora a 1 hora es 51.7, 56.9 y 33.0 %. El único mes,
área y horizonte en que el modelo pierde es el Sur a 24 horas en octubre (−4.1 %). En las horas de mayor demanda
de 2026, la mejora es 53.0, 34.6 y 30.3 % a 1 hora, y la subestimación por encima del percentil 90 de la
referencia queda en 0.09, 0.99 y 0.95 % de esas horas (1.6, 0.5 y 1.9 % a 24 horas).[^reg26]

**Ablación de exógenas en 2026** (modelo fijo; diferencia de MAE en MW con su intervalo; negativo = la variable
ayuda):[^abl26]

| Horizonte | Área | Clima (M1 − M0) | El Niño (M2 − M1) | Fallas (M3 − M2) | Todas (M3 − M0) |
|---|---|---|---|---|---|
| 1 h | Norte | −0.09 (−0.18 a 0.01) | −0.00 (−0.06 a 0.05) | −0.01 (−0.05 a 0.04) | −0.10 (−0.19 a 0.00) |
| 1 h | Centro | **−0.46 (−0.71 a −0.20)** | −0.09 (−0.25 a 0.06) | 0.02 (−0.11 a 0.16) | **−0.53 (−0.78 a −0.27)** |
| 1 h | Sur | 0.04 (−0.03 a 0.11) | −0.02 (−0.09 a 0.06) | −0.04 (−0.11 a 0.02) | −0.02 (−0.11 a 0.06) |
| 24 h | Norte | **+0.42 (0.16 a 0.68)** | −0.03 (−0.19 a 0.09) | **−0.13 (−0.22 a −0.04)** | **+0.25 (0.03 a 0.48)** |
| 24 h | Centro | **+1.35 (0.10 a 2.97)** | −0.01 (−0.48 a 0.44) | 0.14 (−0.20 a 0.48) | **+1.48 (0.24 a 3.03)** |
| 24 h | Sur | 0.02 (−0.28 a 0.32) | **+0.83 (0.46 a 1.23)** | −0.08 (−0.31 a 0.16) | **+0.77 (0.32 a 1.25)** |

En negrita, los intervalos que no cruzan el cero. A 1 hora, el clima ayuda algo en el Centro (−0.46 MW sobre
54 MW, menos del 1 %) y nada en las otras áreas. A 24 horas, **el clima empeora** el pronóstico en el Norte y el
Centro, y El Niño empeora el Sur. Es el riesgo que se declaró con la hipótesis 4: temperaturas fuera del rango de
entrenamiento, con las que los árboles no extrapolan, sumadas a un pronóstico de temperatura simulado con error.
El efecto de las fallas no se interpreta (sección 4.4).

**Experimento de adaptación en 2026** (41 reentrenamientos semanales; 4 por alerta de ENFEN):[^adap26]

| Horizonte | Contraste | Norte | Centro | Sur |
|---|---|---|---|---|
| 1 h | Reentrenar sin exógenas (C − A) | **−0.14 (−0.19 a −0.09)** | **−0.43 (−0.56 a −0.29)** | **−0.09 (−0.15 a −0.03)** |
| 1 h | Reentrenar con exógenas (D − B) | **−0.17 (−0.23 a −0.11)** | **−0.60 (−0.78 a −0.42)** | **−0.21 (−0.29 a −0.14)** |
| 1 h | Reentrenar, M2 (semanal − fijo) | **−0.21 (−0.28 a −0.14)** | **−0.70 (−0.86 a −0.53)** | **−0.16 (−0.23 a −0.09)** |
| 1 h | Exógenas con reentrenamiento (D − C) | **−0.13 (−0.21 a −0.03)** | **−0.70 (−0.94 a −0.45)** | **−0.14 (−0.22 a −0.07)** |
| 1 h | Alerta en vez de semanal (M3) | 0.05 (−0.01 a 0.10) | **+0.20 (0.06 a 0.36)** | **+0.09 (0.03 a 0.16)** |
| 24 h | Reentrenar sin exógenas (C − A) | 0.02 (−0.07 a 0.10) | −0.05 (−0.32 a 0.22) | −0.14 (−0.32 a 0.03) |
| 24 h | Reentrenar con exógenas (D − B) | −0.07 (−0.21 a 0.06) | **−0.87 (−1.45 a −0.37)** | **−0.57 (−0.87 a −0.30)** |
| 24 h | Reentrenar, M2 (semanal − fijo) | **−0.16 (−0.29 a −0.03)** | **−0.72 (−1.19 a −0.27)** | **−0.66 (−0.97 a −0.37)** |
| 24 h | Exógenas con reentrenamiento (D − C) | 0.16 (−0.04 a 0.37) | 0.66 (−0.38 a 1.91) | 0.35 (−0.07 a 0.75) |

Diferencias de MAE en MW, con su intervalo del 95 %; en negrita, las que no cruzan el cero. Reentrenar cada
semana baja el error a 1 hora en las tres áreas, ahora también en el Norte, donde en 2025 no se distinguía de
cero; con exógenas (sin la variable de fallas) llega a −0.70 MW en el Centro, cerca del 1 % del error. A 24 horas,
reentrenar sin exógenas no se distingue de no hacerlo, pero sí compensa parte del daño del clima (D − B en el
Centro, −0.87 MW). Reentrenar solo con la alerta de ENFEN (4 veces) es peor que cada semana en el Centro y el Sur,
y sumarla a la semanal no agrega nada (diferencias de 0.00 a 0.02 MW).

**Las hipótesis, una por una:**[^hip26]

| Hipótesis | ¿Se cumple? | Evidencia |
|---|---|---|
| 1a. A le gana a la mejor referencia a 1 h en las tres áreas | Sí | Norte 51.7 %, Centro 57.9 %, Sur 29.1 % |
| 1b. En el Norte la mejora a 1 h baja respecto de 2025 (49 %) pero queda sobre 25 % | No | Subió: Norte 51.7 % |
| 1c. A 24 h le gana en el Centro y el Norte | Sí | Norte 34.5 %, Centro 42.2 % (y Sur 11.9 %) |
| 2. Reentrenar cada semana (C − A) en el Norte a 1 h: negativo y su intervalo no cruza el cero | Sí | −0.14 MW (IC −0.19 a −0.09) |
| 3. M3 − M0 a 1 h no se distingue de cero en ninguna área | No | Centro −0.53 MW (IC −0.78 a −0.27), por el clima |
| 4. El clima ayuda a 24 h en el Centro | No, en sentido contrario | +1.35 MW (IC 0.10 a 2.97) |
| 5. El Niño no mejora en ningún horizonte ni área | Sí | Ningún M2 − M1 con intervalo bajo cero |

Tres hipótesis no se cumplieron, y dos de ellas fallaron en la dirección que más interesa al operador: el modelo
fue **mejor** de lo esperado en el Norte (1b) y el clima a 24 horas, **peor** (4). Se reportan tal como quedaron
escritas.

# 6. Visualización y análisis

## 6.1 Figuras propuestas

Todas las figuras salen de los notebooks ejecutados; se indica el notebook y la celda (índice desde 0, contando las
celdas de texto) para exportarlas a la versión final.

| N.º | Qué muestra | Dónde está | Sección |
|---|---|---|---|
| 1 | Demanda media mensual del SEIN y de sus áreas, 2016-2026: el crecimiento, la caída de 2020 y el salto del Norte en 2026 | `notebooks/01_sein_datos_preparacion.ipynb`, celda 8 | 4.2 |
| 2 | Perfil diario medio en tres años: cómo se movió el pico del atardecer al mediodía | `01_sein_datos_preparacion.ipynb`, celda 10 | 4.2 |
| 3 | El ICEN y la demanda de cada área frente al mismo mes del año anterior (2017, 2023 y 2026) | `01_sein_datos_preparacion.ipynb`, celda 16 | 4.2 |
| 4 | Tetuán: la transferencia de carga del 25 de octubre (consumo por hora del 18-oct al 1-nov y la diferencia con el día anterior) | `notebooks/01_datos_preparacion.ipynb`, celda 32 | 4.2 |
| 5 | Origen móvil del SEIN a 1 h, 2023-2025: MAE del modelo sobre el de la mejor referencia, por mes y área (por debajo de 100 el modelo gana) | `notebooks/02_sein_modelado_evaluacion.ipynb`, celda 26 | 5.3 |
| 6 | Real contra predicho y distribución de residuos en 2025, por área (el equivalente de la matriz de confusión) | `02_sein_modelado_evaluacion.ipynb`, celda 31 (segunda figura) | 6.2 |
| 7 | Error por hora del día en 2025: modelo frente a la mejor referencia, por área y horizonte | `02_sein_modelado_evaluacion.ipynb`, celda 29 | 6.2 |
| 8 | Importancia de variables por permutación (las 15 principales) y por grupo, sin la escala `media_24h` (ver nota) | `02_sein_modelado_evaluacion.ipynb`, celda 33, versión del PR #30 | 5.3 |
| 9 | Error mes a mes en 2026: modelo fijo, reentrenado y mejor referencia, por área y horizonte | `notebooks/03_sein_prueba_2026.ipynb`, celda 16 | 5.4 |
| 10 | Norte, dos semanas de julio de 2026 (el pico de El Niño): lo real, el modelo fijo, el reentrenado y la referencia, a 1 y 24 h; y los residuos del modelo fijo | `03_sein_prueba_2026.ipynb`, celda 20 | 6.2 |
| 11 | Tetuán: origen móvil mensual y error por hora en la prueba | `notebooks/02_modelado_evaluacion.ipynb`, celdas 22 y 26 | 5.1 |
| 12 | La iteración del Entregable 7: los mismos modelos en nivel y en razón frente a las tres referencias | `entregables/Entregable6_MDS_Grupo03.ipynb`, celda 86 | 7 |
| 13 | Captura de la app: vista de pronóstico y de escenarios *(pendiente: tomarla en la demo)* | `app/web/index.html` | 4.6 |

Nota a la figura 8: `media_24h` es la escala con la que la razón vuelve a MW, no una variable que el modelo vea;
al permutarla se rompe la reconstrucción y salía como la más importante. Desde el PR #30 los notebooks la excluyen
de la importancia; la figura se exporta de esa versión.

## 6.2 Qué dicen las figuras

- **Real contra predicho y residuos (figuras 6 y 10).** Es el equivalente de la matriz de confusión: los puntos
  deben caer sobre la diagonal y los residuos repartirse alrededor de cero. Cada panel lleva en el título la media
  y la desviación de los residuos. *[Por redactar al exportar la figura: decir si hay sesgo hacia subestimar, que es
  el error caro, y en qué área la cola es más larga.]*
- **Dos semanas de julio de 2026 (figura 10).** El pico de El Niño en el Norte, con lo real, el modelo fijo, el
  reentrenado y la mejor referencia a 1 y 24 horas. *[Por redactar al exportar la figura: dónde llega tarde la
  persistencia y en qué días falla "la semana pasada".]*
- **Mes a mes (figuras 5 y 9).** En ningún mes-área de 2023 a 2025 el modelo queda por encima de la mejor
  referencia a 1 hora (108 de 108), y en 2026 la mejora del Norte a 1 hora **sube** a medida que avanza el año
  (de 42.9 % en enero a 61.6 % en septiembre). El Sur a 24 horas es el único lugar donde las curvas se cruzan
  (octubre de 2026, −4.1 %).[^movil25][^mes26]
- **Error por hora (figura 7).** Permite ver en qué horas del día el modelo le saca más ventaja a la referencia y
  comprobar que en las horas de mayor demanda la ventaja se mantiene (55, 33 y 35 % en 2025).[^reg25] *[Por
  redactar al exportar la figura.]*
- **Importancia (figura 8).** La demanda reciente y el calendario (grupo M0) suman 49.5 MW en el Norte, 248.0 en
  el Centro y 43.4 en el Sur; dentro del grupo mandan `Area_t` (23.0 / 119.5 / 22.7) y la media de la última hora
  (10.1 / 55.3 / 11.2), y después el calendario diario (`Time_Cos` y `MinuteOfDay`, unos 14-15 MW en el Centro).
  El clima suma 0.18 / 1.10 / 0.23 MW; El Niño, 0.02 / 0.04 / 0.02; las fallas, 0.00 / −0.01 / 0.00.[^imp25]

## 6.3 La app

La app traduce el modelo a la decisión del operador: para un origen y un área, muestra la predicción a 1 y 24
horas con su intervalo y las tres referencias, deja mover la temperatura pronosticada ("¿y si mañana hace 2 °C
más?") y expone el diagnóstico sobre 2026. La adaptación (fijo frente a reentrenado) no se reentrena en vivo;
muestra la tabla del notebook 03.

## 6.4 Limitaciones y amenazas a la validez

Lo que un lector debe tener en cuenta antes de generalizar los resultados.

1. **Un solo año y un solo evento en la prueba.** Los intervalos de 2026 miden la incertidumbre dentro de 2026
   (bootstrap de días); no dicen nada de otro Niño ni de otro año. A 24 horas, los errores de días vecinos siguen
   correlacionados y los intervalos pueden ser algo angostos.
2. **Efectos chicos y muchas comparaciones.** Los efectos del reentrenamiento y de las exógenas son de alrededor
   del 1 % del error (de 0.09 a 1.48 MW). En 2026 se calcularon 66 intervalos al 95 % sin corrección por
   comparaciones múltiples: se esperan dos o tres "distinguibles" por azar. La conclusión robusta es el tamaño
   (pequeño), no cada signo.
3. **El supuesto de colaboración COES-ENFEN es optimista.** A 1 hora, el "observado" es ERA5, un reanálisis en
   grilla de 0.25° publicado con cinco días de rezago, no una estación en tiempo real. A 24 horas, el pronóstico
   simulado parte de la temperatura que efectivamente ocurrió, con un error sin sesgo e independiente entre días
   (1.5 °C); un pronóstico real tiene sesgos y errores correlacionados, y empeora durante eventos extraordinarios.
   Se probó un solo nivel de error (el plan preveía 1 y 2 °C). La lectura favorable: si aun con un pronóstico
   optimista el clima empeora el pronóstico de demanda a 24 horas en 2026, con uno real difícilmente ayudaría.
4. **La variable de fallas no se pudo evaluar.** Tal como se construye con el registro público, está activa el 91 %
   del tiempo. Los resultados "con exógenas" se apoyan en M2.
5. **Empate entre algoritmos y búsqueda acotada.** Random Forest y XGBoost difieren en 0.3 puntos, sin intervalo;
   la búsqueda de hiperparámetros se hizo solo en el Centro a 1 hora, con presupuestos distintos por algoritmo
   (15 y 30 combinaciones), y se reutilizó en las otras áreas y horizontes. Ninguna conclusión depende de cuál de
   los dos se elija; la app corre el XGBoost.
6. **Hipótesis.** Se escribieron después de explorar los datos de 2026 (el crecimiento del Norte ya se conocía)
   y antes de evaluar ningún modelo en ellos. El origen móvil de 2023-2025 usa hiperparámetros elegidos con datos
   hasta 2024: mide estabilidad, no es una prueba ciega.
7. **Periodo y datos.** La prueba va del 1 de enero al 17 de octubre de 2026 (la recorta el rezago de ERA5); la
   demanda "en t" sale del IEOD validado, no del SCADA; los feriados son los nacionales; M4 (SAIDI) no se corrió.
   La corrida de 2026 se retomó tres veces desde una caché de predicciones por bloque, con cálculos deterministas.
8. **Lo que no se hizo.** No se comparó con la Programación Diaria del COES ni se modeló el SEIN directo a 24 horas:
   el modelo se mide contra referencias ingenuas, no contra el pronóstico oficial.
9. **Tetuán y Ceuta.** En Tetuán, la unidad (kW) y la identidad de las zonas no tienen fuente primaria, la
   temperatura del dataset no coincide con fuentes externas, el modelo pierde en el Ramadán de la Zona 3 y su
   ventaja baja tras la transferencia del 25 de octubre. Ceuta se corrió sin ajuste de hiperparámetros, con una
   semilla y sin intervalos: sostiene la dirección del resultado, no su tamaño, y es otro sistema con otra mezcla
   de clientes.
10. **Validez de constructo.** El MAE no refleja la asimetría entre subestimar y sobrestimar; por eso se reporta
    aparte la subestimación en las horas de mayor demanda.

# 7. Conclusiones y lecciones aprendidas

**Conclusiones, una por objetivo.**

- **OE1 (Tetuán).** Con un solo año de datos se puede pronosticar a una hora sin aprender el nivel: el modelo en
  razón queda entre 41 y 56 % por debajo de la mejor referencia ingenua en la prueba y le gana en los 24 meses-zona
  del origen móvil, incluido el primer verano que nunca vio. Frente a la persistencia, que es lo que la
  literatura reporta, la mejora (−55 a −75 %) supera a la de los trabajos publicados sobre el dataset, y la
  comparación contra la mejor de tres referencias, que casi nadie hace, es la que da la medida honesta.
- **OE2 (Ceuta).** La elección generaliza: el objetivo en razón le gana al nivel en los 25 pares de verano e
  historia, y no haber visto un verano cuesta un 20 % más de error, no el doble. Lo que más pesa es ver un
  verano; el segundo y el tercer año aportan poco.
- **OE3 (SEIN).** Durante El Niño extraordinario de 2026, un modelo entrenado hasta 2025 y sin tocar le gana a la
  mejor referencia en las tres áreas y los dos horizontes (51.7, 57.9 y 29.1 % a 1 hora; 34.5, 42.2 y 11.9 % a
  24 horas), más que en un año normal, y no se degrada a medida que El Niño se intensifica. Lo que sostiene el
  pronóstico es la metodología (la razón con la media de 24 horas y la vara exigente), no las exógenas ni el
  reentrenamiento: reentrenar cada semana baja el error alrededor del 1 % a 1 hora y nada a 24 horas; el clima
  ayuda menos del 1 % a 1 hora en el Centro y **empeora** el pronóstico a 24 horas con temperaturas nunca vistas;
  El Niño no ayuda en ningún caso. Para el operador: modelo en razón, reentrenado cada semana, con el clima a
  1 hora y sin exógenas a 24 horas.

**Lecciones aprendidas.**

1. **CRISP-DM es un ciclo, y la evaluación devuelve el trabajo a la preparación.** El Entregable 7 del grupo
   (4 de noviembre) evaluaba dos modelos en nivel y contra la persistencia: le ganaban a la persistencia pero
   **perdían contra "ayer a la misma hora"** (Random Forest 1,795 kW y XGBoost 1,958 frente a 1,007 kW de
   "ayer").[^e7] La corrección no fue cambiar de algoritmo sino volver a la preparación: tres referencias en vez
   de una, el objetivo en razón, sin calendario anual, y un hueco de una hora. Con eso los mismos dos modelos
   quedaron cerca de la mitad del error de "ayer" (XGBoost 526 kW, Random Forest 544). Cambiar de algoritmo movió
   18 kW; cambiar el objetivo, más de 1,200.
2. **La referencia define la conclusión.** Contra la persistencia cualquier modelo parece bueno; contra la mejor
   de tres referencias, solo los que aprenden la forma del día. Varios trabajos publicados sobre Tetuán no
   superan a "ayer".
3. **Los árboles no extrapolan; la razón sí.** Pedirle al modelo que aprenda el nivel con un año de datos, o con
   una demanda que crece 27 % en nueve años, es pedirle lo que no puede. Pedirle la forma respecto del último día
   es lo que aguanta un verano nuevo o un Niño extraordinario.
4. **"Sin efecto" es un resultado.** Escribir las hipótesis antes de la prueba y reportar los intervalos obligó a
   decir que las exógenas casi no aportan y que el clima a 24 horas puede dañar. Sin eso, la tentación habría
   sido buscar el corte donde el clima "ayuda".
5. **La disciplina temporal se programa y se prueba.** La regla de información, los huecos y los bloques de
   reentrenamiento viven en funciones con tests, no en celdas sueltas: es lo que permitió correr la prueba de
   2026 una sola vez con confianza.
6. **El cómputo se diseña.** Buscar hiperparámetros en un área y reutilizarlos, poner XGBoost en la GPU y dejar el
   Random Forest en la CPU (la versión en GPU no era reproducible), y guardar cada bloque apenas termina, fue lo
   que hizo posible una prueba de tres horas en Colab que se cayó tres veces.

# 8. Bibliografía

*(Formato APA provisional; ajustar a la norma que indique el curso.)*

- Al-Quraan, M. M., Khan, A. R., Centeno, A., Zoha, A., Imran, M. A., & Mohjazi, L. (2023). FedraTrees: A novel
  computation-communication efficient federated learning framework investigated in smart grids. *Engineering
  Applications of Artificial Intelligence, 124*, 106654. https://doi.org/10.1016/j.engappai.2023.106654
- Bergmeir, C., Hyndman, R. J., & Koo, B. (2018). A note on the validity of cross-validation for evaluating
  autoregressive time series prediction. *Computational Statistics & Data Analysis, 120*, 70-83.
- Cerqueira, V., Torgo, L., & Mozetič, I. (2020). Evaluating time series forecasting models: An empirical study on
  performance estimation methods. *Machine Learning, 109*, 1997-2028.
- Chapman, P., Clinton, J., Kerber, R., Khabaza, T., Reinartz, T., Shearer, C., & Wirth, R. (2000). *CRISP-DM 1.0:
  Step-by-step data mining guide*. SPSS.
- Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. En *Proceedings of the 22nd ACM SIGKDD
  International Conference on Knowledge Discovery and Data Mining* (pp. 785-794).
- COES. (2016-2026). *Informe de Evaluación de la Operación Diaria (IEOD), anexo diario; Eventos relevantes*.
  Comité de Operación Económica del Sistema Interconectado Nacional. https://www.coes.org.pe
- ENFEN. (2024). *Nota Técnica ENFEN 01-2024: categorías del Índice Costero El Niño*. Comisión Multisectorial
  ENFEN.
- Hewamalage, H., Ackermann, K., & Bergmeir, C. (2023). Forecast evaluation for data scientists: Common pitfalls
  and best practices. *Data Mining and Knowledge Discovery, 37*, 788-832.
- Hong, T., & Fan, S. (2016). Probabilistic electric load forecasting: A tutorial review. *International Journal of
  Forecasting, 32*(3), 914-938.
- Hong, T., Pinson, P., & Fan, S. (2014). Global Energy Forecasting Competition 2012. *International Journal of
  Forecasting, 30*(2), 357-363.
- IGP. (2026). *Índice Costero El Niño (ICEN)* [Serie mensual]. Instituto Geofísico del Perú.
  http://met.igp.gob.pe/datos/ICEN.txt
- Kshetrimayum, N., Hoque, N., & Nath, D. (2024). PConvLSTM: An effective parallel ConvLSTM-based model for
  short-term electricity load forecasting. *International Journal of Data Science and Analytics*.
- Montero-Manso, P., & Hyndman, R. J. (2021). Principles and algorithms for forecasting groups of time series:
  Locality and globality. *International Journal of Forecasting, 37*(4), 1632-1653.
- NOAA Climate Prediction Center. (2026). *Weekly Niño 1+2 SST and anomalies* [Serie semanal].
  https://www.cpc.ncep.noaa.gov/data/indices/
- Open-Meteo. (2026). *Historical Weather API (reanálisis ERA5 de ECMWF)*. CC BY 4.0.
  https://open-meteo.com/en/docs/historical-weather-api
- Osinergmin. (2026). *SAIDI y SAIFI por sistema eléctrico* [Dataset]. Plataforma Nacional de Datos Abiertos.
  https://www.datosabiertos.gob.pe
- Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research,
  12*, 2825-2830.
- Red Eléctrica de España. (2026). *Seguimiento de la demanda de energía eléctrica: Ceuta* [Datos cada 5 minutos].
  https://demanda.ree.es/visiona/home
- Salam, A., & El Hibaoui, A. (2018). *Power consumption of Tetouan city* [Dataset]. UCI Machine Learning
  Repository. https://doi.org/10.24432/C5B034
- Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. *International
  Journal of Forecasting, 16*(4), 437-450.
- Taylor, J. W. (2008). An evaluation of methods for very short-term load forecasting using minute-by-minute British
  data. *International Journal of Forecasting, 24*(4), 645-658.
- Wang, P., Liu, B., & Hong, T. (2016). Electric load forecasting with recency effect: A big data approach.
  *International Journal of Forecasting, 32*(3), 585-597.
- Wei, N. (2023). Short-term electricity load forecasting of Tetouan city at different time horizons. En *IEEE
  International Conference on Electrical, Computer, Communications and Mechatronics Engineering (ICECCME)*.

---

## Anexo (se quita en la versión final): de dónde sale cada cifra

Todas las cifras del borrador salen de un notebook ejecutado o de una tabla que ese notebook escribió. Ninguna
se calculó a mano. Convención de las notas: `notebook, celda N` cuenta las celdas desde 0, incluidas las de texto.
Las tablas de 2025 son de la corrida del notebook 02 del SEIN del 4 de noviembre (Colab, L4;
`reportes/sein/modelado/`); las de 2026, de la corrida única del notebook 03 del 6 de noviembre
(`reportes/sein/prueba_2026/`, copiadas en `data/reportes/sein/prueba_2026/` del repo local).

[^tet-prueba]: `notebooks/02_modelado_evaluacion.ipynb`, celda 24 (tabla de la prueba y tabla de criterios con
    intervalos) y `reportes/modelado/prueba.csv`. Mejora frente a la mejor referencia: 44.8, 55.9 y 40.7 %.
[^ceuta]: `docs/historico.md`, §8, "Resultado de la validación externa" (tabla de MAPE por verano y medias
    2022-2026); el CSV de origen es `reportes/ceuta/resultados_validacion.csv` en el Drive.
[^fr26]: `data/reportes/sein/prueba_2026/frente_referencias.csv` (notebook 03, celda 9).
[^abl26]: `data/reportes/sein/prueba_2026/ablacion.csv` (notebook 03, celda 11).
[^spec-negocio]: `docs/superpowers/specs/2026-10-23-demanda-sein-areas-design.md` (rama del PR #11), §1 y §2.
[^nb01-sein]: `notebooks/01_sein_datos_preparacion.ipynb`: auditoría (celda 6), participación por área (celda 8),
    deriva del pico (celda 10), fallas (celda 18), referencias por año (celda 22), partición (celda 24) y la
    celda de hallazgos (celda 26).
[^eda-tet]: `docs/estado-del-arte.md` (resumen y §3); `notebooks/01_datos_preparacion.ipynb`, celdas 44
    (hallazgos), 66 (validación cruzada temporal) y 72 (ablación); `docs/investigacion.md`, §2 y §3.
[^spec-eval]: Spec, §8.5 "Regímenes y criterios".
[^negocio-tet]: `docs/negocio.md`, §2 a §4 y §8; `docs/investigacion.md`, transferencia del 25 de octubre.
[^datos-fuentes]: `docs/datos.md`; `docs/historico.md`, §8 (Ceuta: 391,975 intervalos); README, sección "Datos";
    notebook 01 del SEIN, celda 3 (189,504 periodos).
[^regla]: `src/tetouan_power_forecast/variables_sein.py` (`dataset_area`, `error_pronostico_diario`, `particion`);
    `src/tetouan_power_forecast/exogenas.py` (`icen_disponible`, `nino12_disponible`, `fallas_en_curso`);
    tests en `tests/test_variables_sein.py` y `tests/test_exogenas.py`.
[^tet-objetivo]: `notebooks/02_modelado_evaluacion.ipynb`, celda 9 (nivel, cambio y razón en la validación de la
    Zona 1). El −8.3 % del calendario anual: `01_datos_preparacion.ipynb`, celda 72.
[^busq26]: `reportes/sein/modelado/busqueda.csv` (notebook 02 del SEIN, celda 9).
[^tet-eleccion]: `notebooks/02_modelado_evaluacion.ipynb`, celda 17, y `reportes/modelado/comparacion_validacion.csv`.
[^sel26]: `reportes/sein/modelado/comparacion_validacion_1h.csv` y notebook 02 del SEIN, celdas 7 (referencias) y
    15 (comparación y elección).
[^app]: `app/backend/pronosticador_real.py` (docstring) y `app/backend/contrato.py`.
[^tet-movil]: `reportes/modelado/origen_movil.csv` (notebook 02 de Tetuán, celda 21): julio, Zona 3, Gradient
    Boosting global 554.3 kW frente a 934.1 de "ayer".
[^tet-regimenes]: `notebooks/02_modelado_evaluacion.ipynb`, celdas 27 (feriados y Ramadán) y 29 (transferencia).
[^tet-sota]: `docs/paper/estructura.md`, Tabla 1, y `docs/estado-del-arte.md`, tabla 2.1 (filas 6, 7 y 10) y §3.2.
    Las cifras propias: `reportes/modelado/prueba.csv` (persistencia 1,821.3, 1,567.4 y 950.8 kW) y
    `origen_movil.csv` (marzo: modelo 611.7, 483.4 y 375.2; persistencia 2,279.2, 1,372.3 y 1,419.0). La fila
    "Total" viene de `estructura.md` y cita archivos de predicciones del Drive que no se pudieron verificar en local.
[^val24]: `reportes/sein/modelado/comparacion_validacion_24h.csv` y notebook 02 del SEIN, celda 17; R² del Sur:
    0.33.
[^movil25]: Notebook 02 del SEIN, celda 25 (salida: "M0: le gana a la mejor referencia en 108 de 108 meses-área")
    y conclusiones (celda 36); `reportes/sein/modelado/origen_movil.csv`.
[^reg25]: `reportes/sein/modelado/regimenes.csv` (notebook 02, celda 28): mayor demanda a 1 h, mejora M0 55.0,
    33.0 y 34.9 %; subestimación > p90: 0.07, 0.92 y 0.72 %.
[^abl25]: `reportes/sein/modelado/ablacion.csv` (notebook 02, celda 19).
[^imp25]: `reportes/sein/modelado/importancias.csv` e `importancias_por_grupo.csv` en el Drive, versión del PR #30
    (`fix/importancia-sin-escala`, commit `c687feb`; las anteriores, con la fila `media_24h`, quedaron en `respaldo/`);
    salida de la celda 33 del notebook 02 del SEIN en esa rama. Los valores por variable no cambian: solo se quita la
    fila de la escala.
[^tet-imp]: `notebooks/02_modelado_evaluacion.ipynb`, celda 33, versión del PR #30 (sin la fila de la escala
    `media_24h`); `reportes/modelado/importancias.csv` en el Drive.
[^adap25]: `reportes/sein/modelado/adaptacion.csv` y `efectos_adaptacion.csv` (notebook 02, celdas 22 y 23).
[^mes26]: `data/reportes/sein/prueba_2026/mensual.csv` (notebook 03, celda 16).
[^reg26]: `data/reportes/sein/prueba_2026/regimenes.csv` (notebook 03, celda 18) y la salida de esa celda ("Días
    con temperatura fuera de lo visto en 2026: Norte 105, Centro 91, Sur 4").
[^adap26]: `data/reportes/sein/prueba_2026/adaptacion.csv` y `efectos_adaptacion.csv` (notebook 03, celdas 13 y 14).
[^hip26]: `data/reportes/sein/prueba_2026/hipotesis.csv` (notebook 03, celda 22); las hipótesis, en el notebook 02,
    celda 34.
[^e7]: `entregables/Entregable6_MDS_Grupo03.ipynb`, celda 93 (conclusiones): "ayer" 1,007 kW (MAPE 3.5 %); en nivel,
    Random Forest 1,795 y XGBoost 1,958; en razón, XGBoost 526 (MAPE 1.8 %) y Random Forest 544.
