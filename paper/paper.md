---
title: "Pronóstico de demanda eléctrica de muy corto plazo ante niveles no vistos: de Tetuán a El Niño de 2026 en el SEIN"
subtitle: "Trabajo final (TB1) · Metodología para Data Science (1ACC0240) · UPC · ciclo 2026-2 · Grupo 3"
author:
  - "Vilchez, Rody"
  - "[Apellidos], Marcelo"
  - "[Apellidos], Adrián"
  - "[Apellidos], Andre"
  - "[Apellidos], Olenka"
date: "Borrador del 19 de noviembre de 2026"
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

Resultados. En Tetuán, el modelo queda entre 41 y 56 % por debajo de la mejor de las tres referencias históricas
en la prueba.[^tet-prueba] Frente al promedio de los deltas diario y semanal, gana en Zona 1 y pierde en las zonas
2 y 3. En Ceuta, el objetivo en razón le gana al modelo en nivel en la corrida histórica.[^ceuta] En el reanálisis,
el V4 sin verano queda en 2.33 % de MAPE frente a 2.06 % del delta semanal, que gana los cinco veranos.
En el SEIN, durante 2026
(ICEN de 3.98 en agosto, el mayor desde 1997-98), un modelo entrenado hasta 2025 y sin tocar durante la prueba
redujo el error a 1 hora en 51.7 % (Norte), 57.9 % (Centro) y 29.1 % (Sur) frente a la mejor referencia, y a 24
horas en 34.5, 42.2 y 11.9 %; la mejora fue mayor que en 2025 en cinco de los seis casos.[^fr26] Reentrenar cada
semana y agregar clima o El Niño cambian el error alrededor de 1 %: a 1 hora ayudan poco; a 24 horas, con
temperaturas fuera de todo lo visto, el clima **empeora** el pronóstico en el Norte y el Centro.[^abl26]
"Sin efecto" también es un resultado.

Recomendación para el operador: pronosticar la razón con la media de 24 horas, medirse contra la mejor referencia
ingenua, reentrenar cada semana a 1 hora y no apoyarse en el clima a 24 horas durante un evento extraordinario.
La app del proyecto ejecuta el modelo y permite probar escenarios.

Como extensión posterior a la prueba, se compararon ocho modelos fundacionales de series de tiempo sin entrenar
(zero-shot) sobre las mismas filas: a 1 hora los mejores ya le ganan al modelo elegido en las tres áreas; a 24
horas, no en el Centro ni el Norte. Ajustando Chronos-2 con datos hasta 2024 y el feriado como covariable, y
combinándolo con un híbrido que suma el pronóstico de un fundacional al XGBoost en razón, el error del Centro
baja de 54.6 a 48.2 MW a 1 hora y de 86.1 a 75.2 a 24 horas en 2025, y el Sur a 24 horas, el punto débil, de 56.7
a 51.8; en 2026 se sostiene (48.8 y 71.9 en el Centro; 44.6 frente a 48.3 en el Sur), con diferencias que excluyen
el cero en los doce casos.[^fm]

# 3. Introducción al problema

**El problema del operador.** El Comité de Operación Económica del Sistema (COES) opera el SEIN y programa cada
día qué centrales generan y con qué reserva. Conoce la demanda cuando ya ocurrió. Para equilibrar la carga
necesita anticiparla a dos plazos: **una hora**, para la coordinación en tiempo real (redespacho, reserva
rotante, arranque de unidades rápidas), y **24 horas**, para el programa del día siguiente. Y la necesita **por
área operativa** (Norte, Centro y Sur), porque los enlaces de transmisión entre áreas tienen límite: un desvío en
el Norte no siempre se cubre desde el Centro.[^spec-negocio] Subestimar cuesta más que sobrestimar: obliga a
arrancar generación cara de urgencia o, en el extremo, a cortar carga.

**Por qué ahora.** El Niño Costero de 2026 es extraordinario: el Índice Costero El Niño (ICEN) llegó a 3.98 en
agosto, el valor más alto desde 1997-98 (y siguió subiendo: 4.50 en setiembre), y la demanda del Norte creció entre 4 y
17 % sobre 2025 (17 % en julio).[^nb01-sein][^nino-nov] Es exactamente la situación en la que un pronóstico entrenado con el pasado puede fallar: la
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
prueba a 1 hora (del 1 de enero al 17 de octubre de 2026; a 24 horas, 13,871, hasta el 16 de octubre), con 26
variables en M0 y 33 en M3.[^nb01-sein][^nb03-datos] La prueba termina el 17 de octubre a 1 hora y el 16 a 24
horas (y no el 23) porque ERA5 llega con unos cinco días de rezago y las filas se exigen completas para todas las
variantes. **Las filas de 2026 se apartan en la primera celda del notebook de
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

**Extensión posterior a la prueba: modelos fundacionales.** Después de cerrar la prueba de 2026 se agregó una
comparación con modelos fundacionales de series de tiempo: redes preentrenadas con millones de series de otros
rubros, que pronostican una serie nueva sin entrenarse con ella (*zero-shot*). Como 2026 ya se había usado en la
prueba, esta extensión **no es una prueba ciega**: todo lo que se elige se elige con 2025, y 2026 es una
confirmación posterior. El protocolo: ocho modelos de Hugging Face (Simons-297M, Timestral-209M, t0-gamma,
Chronos-2, Toto-2.0, TimesFM 3.0, TimesFM 2.5 y TiRex-2), cada uno con un contexto de 2,048 periodos (43 días) de
demanda del área hasta t, pidiendo 48 pasos y guardando los pasos 2 (1 hora) y 48 (24 horas) con sus cuantiles 0.1
y 0.9; los mismos orígenes y las mismas filas que el Random Forest en 2025 y 2026; los 336 huecos de la serie se
interpolan solo en el contexto. Después, Chronos-2 con covariables (temperatura pronosticada simulada y feriados,
bajo la misma regla de información); **cuatro variantes de ajuste fino** de Chronos-2 solo con datos hasta 2024
(tasa de aprendizaje 1e-6 o 1e-5, con y sin el feriado como covariable futura), elegidas con 2025; un
**híbrido**: el XGBoost global en razón (M0) recibe como variables el pronóstico zero-shot del fundacional, el
ancho de su intervalo y su pronóstico al otro horizonte, todos divididos por la media de 24 horas, y se entrena
con orígenes de marzo de 2016 a 2024; y, por último, una **combinación lineal** del mejor Chronos-2 ajustado y del
híbrido, con un peso por horizonte y área fijado en 2025. Los resultados están en la sección 5.5 y el detalle, en
el notebook 04.[^fm]

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

**La app, Curva.** Una app web propia (backend FastAPI y frontend en HTML/JS) que ejecuta los modelos del proyecto
sobre las capas reales del SEIN y pone a la vista cuánto acertó. Tiene tres pantallas: **«Ahora»** (la demanda de
este momento o de cualquier hora del historial en repaso, el pico y la mayor subida de las próximas 24 horas
anotados sobre la curva, el pronóstico con su rango y «lo que dijimos ayer para esta hora» frente a lo que pasó;
tocar o arrastrar el gráfico fija la hora, y un selector propio de fecha y hora en formato peruano reemplaza a los
controles del navegador), **«Confianza»** (el error mes a mes y día a día de la prueba de 2026, la cobertura del
rango contra su meta, el seguimiento en vivo y el contexto internacional) y **«Detalle»** (el modelo, los escenarios
"¿y si hace más calor?", el diagnóstico completo y el registro en vivo). El selector de modelo ofrece tres: el
XGBoost base (el único que responde a los escenarios, porque usa el clima), el híbrido XGBoost + Simons y el
combinado de la sección 5.5, que es el que abre por defecto; los dos últimos necesitan GPU y la app lee sus
pronósticos precalculados. El backend calcula las variables con la misma función que los notebooks, sirve la web
comprimida y expone el registro en vivo.[^app] La rúbrica nombra Streamlit; el grupo eligió una app propia
asumiendo ese riesgo, con la condición de que ejecute el modelo.

**Cómo se validó el diseño.** Con un método de medir antes y después tomado de una auditoría previa de diseño
centrado en las personas: línea base medida antes de tocar nada, un cambio mínimo por iteración atado a una métrica
que falla, re-medición con el mismo arnés, lo probado y revertido con cifras, y límites declarados. Los
instrumentos son sintéticos: tareas con Playwright y tiempos estimados con el Keystroke-Level Model (Card, Moran y
Newell, 1980), axe-core para WCAG 2.2, un lector de atención entrenado con las miradas de UEyes (Jiang et al., 2023;
CC 0.69 en su test oficial), una prueba de 5 segundos y una de primer clic sintéticas, y un playtest con cinco
personas sintéticas por ronda al estilo RITE (Medlock et al., 2002). **Nada se probó con personas**; el protocolo de
30 minutos con cinco personas está escrito y es lo siguiente. Los resultados están en la sección 5.6.[^hcd]

**El pronóstico en vivo.** Desde el 13 de noviembre de 2026, una corrida diaria baja el anexo del IEOD del COES
(que sale a la mañana siguiente del día que describe), valida el día (48 periodos, sin vacíos, Norte + Centro +
Sur = SEIN, empalme sin salto), emite con Chronos-2 ajustado con calendario el perfil de hoy a 24 horas desde cada
origen de ayer, y registra cada pronóstico con su sello de tiempo, el sha256 de los pesos y del anexo y el commit del
código, **antes de que exista su real**. El registro distingue tres tipos: *ex ante estricto* (el periodo todavía
no empezaba al emitirse), *en vivo* (el periodo ya había empezado, pero el COES no podía haber publicado su real) y
*reconstruido* (emitido después: el relleno del 23 de octubre al 12 de noviembre y todo el horizonte de 1 hora,
que necesita la demanda de una hora antes, publicada al día siguiente). La evaluación cruza el registro con el real
que llega al otro día y se rehace en cada corrida.[^vivo]

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

**Reanálisis descriptivo con referencias fuertes.** Se evalúan las mismas 7,841 filas por zona. El delta suma
a la demanda actual el cambio a la hora objetivo observado el día anterior o la semana anterior. La última
columna es la reducción relativa del MAE del modelo frente al promedio de ambos deltas. Las ventanas ya se habían
examinado y el protocolo documenta el cambio de comparadores respecto de la evaluación original.

| Zona | Modelo global (MAE) | Delta diario (MAE) | Promedio de deltas (MAE) | Reducción relativa frente al promedio |
|---|---:|---:|---:|---:|
| 1 | 462.5 | 567.5 | 480.7 | +3.8 % |
| 2 | 429.4 | 489.9 | 413.2 | −3.9 % |
| 3 | 429.0 | 392.1 | 368.2 | −16.5 % |

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

En la evaluación original, el objetivo en razón le gana al objetivo en nivel en los 25 pares de verano e historia de
2022 a 2026. No haber visto
un verano cuesta 0.38 puntos con la razón (+20 %) y 0.77 con el nivel (+37 %, hasta 1.2 puntos en 2024). El segundo
año baja el MAPE 0.1 puntos y el tercero casi nada. Con eso se respondía la pregunta de Tetuán: lo que más pesa es
haber visto un verano; con un año más de datos, el error de verano bajaría alrededor de un 20 %, no a la mitad. Esa
cifra mide cuánto empeora el propio modelo sin verano, no cómo queda frente a una referencia estacional fuerte.

**Reanálisis descriptivo sobre las mismas filas.** Se regeneró el V4 sin verano con la receta histórica.
El promedio de V4 regenerado (2.33 %) queda 0.02 puntos por encima del agregado de la corrida original. Los
cinco veranos tienen 8,928 pares cada uno, sin demanda no positiva. El delta semanal gana en los cinco y el
promedio de ambos deltas obtiene el menor MAPE de los tres métodos de la tabla.

| Verano | V4 sin verano, MAPE % | Delta semanal, MAPE % | Promedio de deltas, MAPE % |
|---|---:|---:|---:|
| 2022 | 2.73 | 2.33 | 2.03 |
| 2023 | 2.07 | 1.97 | 1.78 |
| 2024 | 2.78 | 2.29 | 2.17 |
| 2025 | 1.88 | 1.76 | 1.59 |
| 2026 | 2.18 | 1.98 | 1.77 |
| Media de los cinco veranos | 2.33 | 2.06 | 1.87 |

El [protocolo de reanálisis](../docs/protocolo-reanalisis-tb1.md) documenta las ventanas y métricas.

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

**El modelo fijo frente a las referencias** (del 1 de enero al 17 de octubre de 2026 a 1 hora y al 16 de octubre
a 24 horas; modelo entrenado hasta 2025 y sin tocar):[^fr26]

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

| Horizonte | Área | Clima (M1 − M0) | El Niño (M2 − M1) | Fallas (M3 − M2) | Clima + El Niño (M2 − M0) | Todas (M3 − M0) |
|---|---|---|---|---|---|---|
| 1 h | Norte | −0.09 (−0.18 a 0.01) | −0.00 (−0.06 a 0.05) | −0.01 (−0.05 a 0.04) | −0.09 (−0.18 a 0.01) | −0.10 (−0.19 a 0.00) |
| 1 h | Centro | **−0.46 (−0.71 a −0.20)** | −0.09 (−0.25 a 0.06) | 0.02 (−0.11 a 0.16) | **−0.55 (−0.82 a −0.30)** | **−0.53 (−0.78 a −0.27)** |
| 1 h | Sur | 0.04 (−0.03 a 0.11) | −0.02 (−0.09 a 0.06) | −0.04 (−0.11 a 0.02) | 0.02 (−0.06 a 0.11) | −0.02 (−0.11 a 0.06) |
| 24 h | Norte | **+0.42 (0.16 a 0.68)** | −0.03 (−0.19 a 0.09) | **−0.13 (−0.22 a −0.04)** | **+0.39 (0.14 a 0.62)** | **+0.25 (0.03 a 0.48)** |
| 24 h | Centro | **+1.35 (0.10 a 2.97)** | −0.01 (−0.48 a 0.44) | 0.14 (−0.20 a 0.48) | **+1.34 (0.19 a 2.74)** | **+1.48 (0.24 a 3.03)** |
| 24 h | Sur | 0.02 (−0.28 a 0.32) | **+0.83 (0.46 a 1.23)** | −0.08 (−0.31 a 0.16) | **+0.85 (0.44 a 1.30)** | **+0.77 (0.32 a 1.25)** |

En negrita, los intervalos que no cruzan el cero. A 1 hora, el clima ayuda algo en el Centro (−0.46 MW sobre
54 MW, menos del 1 %) y nada en las otras áreas. A 24 horas, **el clima empeora** el pronóstico en el Norte y el
Centro, y El Niño empeora el Sur. Es el riesgo que se declaró con la hipótesis 4: temperaturas fuera del rango de
entrenamiento, con las que los árboles no extrapolan, sumadas a un pronóstico de temperatura simulado con error.
Como el efecto de la variable de fallas no se interpreta (sección 4.4), el efecto de "las exógenas" se lee en la
columna M2 − M0 (clima y El Niño, sin fallas): −0.55 MW en el Centro a 1 hora (IC −0.82 a −0.30), nada en el Norte
ni el Sur, y +0.39, +1.34 y +0.85 MW a 24 horas en el Norte, el Centro y el Sur.

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
reentrenar sin exógenas no se distingue de no hacerlo; con exógenas sí baja el error (M2: −0.16, −0.72 y −0.66 MW;
D − B en el Centro, −0.87), pero solo compensa parte del daño del clima: el M2 reentrenado (29.2 / 78.8 / 48.5 MW
en el Norte / Centro / Sur) sigue por encima del modelo fijo sin exógenas (29.0 / 78.1 / 48.3). Reentrenar solo con la alerta de ENFEN (4 veces) es peor que cada semana en el Centro y el Sur,
y sumarla a la semanal no agrega nada (diferencias de 0.00 a 0.02 MW).

**Las hipótesis, una por una:**[^hip26]

| Hipótesis | ¿Se cumple? | Evidencia |
|---|---|---|
| 1a. A le gana a la mejor referencia a 1 h en las tres áreas | Sí | Norte 51.7 %, Centro 57.9 %, Sur 29.1 % |
| 1b. En el Norte la mejora a 1 h baja respecto de 2025 (49 %) pero queda sobre 25 % | No | Subió: Norte 51.7 % |
| 1c. A 24 h le gana en el Centro y el Norte | Sí | Norte 34.5 %, Centro 42.2 % (y Sur 11.9 %) |
| 2. Reentrenar cada semana (C − A) en el Norte a 1 h: negativo y su intervalo no cruza el cero | Sí | −0.14 MW (IC −0.19 a −0.09) |
| 3. M3 − M0 a 1 h no se distingue de cero en ninguna área | No | Centro −0.53 MW (IC −0.78 a −0.27), por el clima; sin la variable de fallas (M2 − M0), −0.55 (IC −0.82 a −0.30) |
| 4. El clima ayuda a 24 h en el Centro | No, en sentido contrario | +1.35 MW (IC 0.10 a 2.97) |
| 5. El Niño no mejora en ningún horizonte ni área | Sí | Ningún M2 − M1 con intervalo bajo cero |

Tres hipótesis no se cumplieron, y dos de ellas fallaron en la dirección que más interesa al operador: el modelo
fue **mejor** de lo esperado en el Norte (1b) y el clima a 24 horas, **peor** (4). Se reportan tal como quedaron
escritas.

## 5.5 Extensión posterior a la prueba: modelos fundacionales

Esta sección se agregó después de la prueba de 2026 (sección 4.4): 2026 ya se había usado en el notebook 03, así
que lo que sigue se eligió con 2025 y en 2026 solo se confirma. MAE en MW, Norte / Centro / Sur, sobre las mismas
filas que el modelo elegido:[^fm]

| Modelo | 2025, 1 h | 2025, 24 h | 2026, 1 h | 2026, 24 h |
|---|---|---|---|---|
| Random Forest elegido (A, M0) | 19.7 / 54.6 / 24.1 | 28.8 / 86.1 / 56.7 | 20.2 / 54.1 / 22.4 | 29.0 / 78.1 / 48.3 |
| XGBoost global base (mismas filas que el híbrido) | 19.6 / 53.6 / 24.7 | 28.6 / 85.9 / 57.7 | 20.0 / 54.1 / 22.5 | 29.3 / 80.7 / 49.4 |
| Simons-297M, zero-shot | 18.8 / 49.7 / 22.4 | 30.0 / 92.9 / 54.2 | 19.3 / 50.6 / 21.3 | 30.9 / 83.4 / 46.8 |
| Timestral-209M, zero-shot | 19.0 / 50.0 / 22.5 | 30.5 / 97.6 / 54.2 | 19.5 / 51.0 / 21.4 | 31.5 / 87.1 / 46.8 |
| Chronos-2, zero-shot | 19.4 / 52.2 / 23.2 | 33.0 / 101.0 / 55.2 | 19.9 / 52.6 / 21.6 | 31.6 / 87.3 / 46.9 |
| Chronos-2, ajuste fino hasta 2024, sin covariables | 19.0 / 50.8 / 22.8 | 29.6 / 89.8 / 53.3 | 19.3 / 51.0 / 21.3 | 29.9 / 81.6 / 45.3 |
| Chronos-2, ajustado hasta 2024 con el feriado como covariable ("ajustado con calendario") | 18.8 / 49.8 / 22.9 | 27.1 / 75.6 / 51.8 | 19.2 / 50.3 / 21.1 | 28.2 / 72.5 / 44.6 |
| TimesFM 2.5, zero-shot | 19.9 / 56.0 / 23.8 | 31.2 / 107.5 / 57.0 | 20.6 / 57.0 / 22.4 | 32.0 / 98.5 / 49.3 |
| Híbrido: XGBoost + Chronos-2 | 18.7 / 49.9 / 23.5 | 28.6 / 82.7 / 56.9 | 19.0 / 50.0 / 21.2 | 28.7 / 77.3 / 49.7 |
| Híbrido: XGBoost + Simons | 18.6 / 49.0 / 23.5 | 27.9 / 81.3 / 57.0 | 18.9 / 49.2 / 21.2 | 28.7 / 75.6 / 49.8 |
| **Combinación: Chronos-2 ajustado con calendario + híbrido XGBoost + Simons (pesos fijados en 2025)** | **18.5 / 48.2 / 22.5** | **26.9 / 75.2 / 51.8** | **18.8 / 48.8 / 20.9** | **27.9 / 71.9 / 44.6** |

Los otros cuatro modelos zero-shot (t0-gamma, Toto-2.0, TimesFM 3.0 y TiRex-2) quedan entre Simons y TimesFM 2.5
en 2026 a 1 hora en el Centro (50.7, 51.8, 53.2 y 59.5 MW) y ninguno supera a Simons; seis de los ocho le ganan al
Random Forest a 1 hora (TimesFM 2.5 y TiRex-2, no). Sus filas completas están en la sección 2 del notebook
04.[^fm-otros] Darles cuatro veces más historia (8,192 periodos, 171 días, en vez de 2,048) casi no cambia el
resultado: con Simons, 91.5 frente a 92.9 MW en el Centro a 24 horas en 2025 (82.1 frente a 83.4 en 2026) y lo
mismo a 1 hora.[^fm] El "XGBoost global base" es el mismo algoritmo del híbrido sin las variables
fundacionales, entrenado sobre las mismas filas (desde marzo de 2016): no es el XGBoost del notebook 03, que
entrena con todo y, para 2026, hasta 2025.

**El híbrido frente al modelo elegido**, con intervalos del 95 % por bootstrap de días. En 2025: Centro −5.62 MW
(IC −6.58 a −4.81) a 1 hora y −4.77 (IC −7.18 a −2.57) a 24 horas; Norte −1.10 y −0.90, distinguibles de cero;
Sur −0.60 (IC −1.14 a 0.10) y +0.28 (IC −0.79 a 1.36), que no se distinguen. En 2026 mejora a 1 hora en las tres
áreas (Centro −4.85, IC −5.44 a −4.27); a 24 horas mejora el Centro (−2.57, IC −4.32 a −0.90), no se distingue en
el Norte y **empeora** el Sur (+1.54, IC 0.34 a 2.79).[^fm]

**Chronos-2 ajustado con calendario frente al modelo elegido.** De las cuatro variantes de ajuste fino (tasa de
aprendizaje 1e-6 o 1e-5, con y sin feriado), elegidas con 2025, la mejor es la de tasa 1e-6 con el feriado como
covariable futura (3,000 pasos; 26 minutos en una GPU A100). Le gana al Random Forest con intervalos del 95 % que
excluyen el cero en todos los casos salvo el Norte a 24 horas en 2026 (−0.77 MW, IC −1.65 a 0.12); en el Centro a
24 horas, −10.5 MW en 2025 (IC −13.8 a −7.2) y −5.7 en 2026 (IC −8.3 a −3.1). Su intervalo 10-90 cubre alrededor
del 75 % de los periodos, algo estrecho; los cuantiles de los zero-shot sin ajustar están bien calibrados (Simons:
81 % a 1 hora y 80 % a 24 horas). La variante con tasa 1e-5 sobreajusta (Sur a 24 horas, 63.9 MW en 2025). La
temperatura como covariable no ayuda, ni en zero-shot ni ajustado; los feriados solos sí mejoran el Centro a 24
horas en 2025 (de 101.0 a 93.0 MW).[^fm]

**La combinación final.** Una combinación lineal del Chronos-2 ajustado con calendario y del híbrido XGBoost +
Simons, con el peso del Chronos-2 fijado en 2025 por horizonte y área (0.35 / 0.45 / 0.65 a 1 hora y 0.70 / 0.85 /
0.95 a 24 horas, Norte / Centro / Sur), le gana al Random Forest en los doce casos, siempre con una diferencia que
excluye el cero, y es la mejor de la tabla en todos salvo el Sur a 1 hora en 2025 (22.5 frente a 22.4 de Simons
zero-shot). Diferencias de MAE frente al modelo elegido, en MW, con su intervalo del 95 %:[^fm]

| Año | Horizonte | Norte | Centro | Sur |
|---|---|---|---|---|
| 2025 | 1 h | −1.21 (−1.51 a −0.96) | −6.39 (−7.63 a −5.37) | −1.56 (−1.88 a −1.28) |
| 2025 | 24 h | −1.96 (−2.71 a −1.24) | −10.85 (−14.08 a −7.73) | −4.92 (−7.09 a −2.86) |
| 2026 | 1 h | −1.37 (−1.56 a −1.14) | −5.22 (−5.84 a −4.57) | −1.55 (−1.81 a −1.28) |
| 2026 | 24 h | −1.08 (−1.80 a −0.35) | −6.23 (−8.67 a −3.81) | −3.71 (−5.49 a −1.87) |

Con la regla del notebook 02 (la mayor mejora media frente a la mejor referencia en 2025, promediada entre áreas
y horizontes), la combinación queda primera (40.7 % frente a 35.2 % del Random Forest; en 2026, 42.3 frente a
37.9 %) y el Chronos-2 ajustado con calendario es el mejor modelo individual (40.0 %), a menos de un punto. En el
Centro, la combinación reduce el error alrededor de 12 % a 1 hora y a 24 horas en 2025, y lo sostiene en 2026 (10
y 8 %). **Los pesos de 2025 son dentro de muestra, así que sus diferencias de 2025 son optimistas; la de 2026
queda fuera del entrenamiento y de la selección, pero sobre un año ya inspeccionado en el notebook 03.** Su
intervalo 10-90 cubre entre 77 y 80 % de los periodos en 2025 y entre 77 y 81 % en
2026. Mes a mes y por régimen de El Niño, su ventaja frente al Random Forest es parecida en los meses neutros y en
los cálidos fuertes o extraordinarios: no se adapta mejor al cambio de nivel de 2026, que el objetivo en razón ya
absorbía; es mejor en general. Los peores meses del zero-shot a 24 horas son abril y julio, los de Semana Santa y
Fiestas Patrias: el fundacional ve la forma reciente de la curva, pero no sabe qué día es mañana.[^fm]

**Lo que se aprende:**

1. **Sin entrenar nada, los mejores fundacionales ya ganan a 1 hora en las tres áreas:** Simons queda unos 5 MW por
   debajo del Random Forest en el Centro (49.7 frente a 54.6 en 2025; 50.6 frente a 54.1 en 2026), alrededor de
   9 % menos error.
2. **A 24 horas, sin entrenar, no ganan en el Centro ni el Norte** (92.9 frente a 86.1 y 30.0 frente a 28.8 en
   2025): les falta el calendario, y 43 días de contexto es poco para el programa del día siguiente. Sí ganan en el
   Sur, el punto débil del proyecto (54.2 frente a 56.7 en 2025; 46.8 frente a 48.3 en 2026, aunque en 2026 la
   diferencia no se distingue de cero). **Con ajuste fino hasta 2024 y el feriado como covariable, Chronos-2 sí
   gana a 24 horas en las tres áreas** (27.1 / 75.6 / 51.8 MW en 2025 y 28.2 / 72.5 / 44.6 en 2026, frente a 28.8 /
   86.1 / 56.7 y 29.0 / 78.1 / 48.3 del Random Forest).
3. **La temperatura como covariable no ayuda a Chronos-2**, ni en zero-shot ni ajustado, coherente con la
   hipótesis 1 y con la ablación: a 1 hora no mejora y en 2026 a 24 horas lo empeora (Centro, 97.6 frente a 87.3
   MW en zero-shot). El feriado sí ayuda.
4. **La propuesta final es la combinación** del Chronos-2 ajustado con calendario y del híbrido XGBoost + Simons:
   el modelo preentrenado aporta el patrón reciente de la serie y el XGBoost, el calendario y el nivel. Le gana al
   Random Forest en los doce casos; el híbrido solo es el mejor en cinco de los seis casos de 2025 a 1 hora y
   pierde a 24 horas frente al ajustado.
5. **Costo.** Generar el pronóstico fundacional exige GPU (entre 1 y 13 milisegundos por pronóstico de 48 pasos en
   una L4 de Colab; el ajuste fino con feriados, 26 minutos); el XGBoost del híbrido entrena en segundos en CPU. La
   app leería los pronósticos precomputados, como la tabla de adaptación.

**Límites propios de esta extensión.** Un solo año de validación para elegir (2025) y una confirmación posterior
en un año ya usado (2026); la diferencia entre los primeros puestos es de pocos puntos y los pesos de la
combinación se fijaron en 2025, donde se evalúan dentro de muestra; no se puede auditar qué vieron los modelos al
preentrenarse (varios se entrenaron con series de carga eléctrica de otros países), así que no se puede descartar
que series parecidas estén en sus datos; las licencias difieren por modelo (Chronos-2, Apache-2.0, y Simons,
OpenMDW-1.1, permiten cualquier uso; TimesFM 3.0 es solo para uso no comercial y Timestral limita el uso en
empresas grandes) y condicionan un uso operativo; no se buscaron hiperparámetros del híbrido, no se ajustaron
otros modelos ni se reentrenó durante 2026. El ajuste fino con calendario se repitió con dos semillas más (tres en
total, misma receta): el MAE cambia como mucho 0.19 MW entre semillas en los doce casos (Centro a 24 horas en 2026;
entre 0.01 y 0.09 en los demás), muy por debajo de su ventaja sobre el Random Forest (−10.5 MW en el Centro a 24
horas en 2025). Una revisión del código línea por línea no encontró fugas: el ajuste solo ve datos hasta el 31 de
diciembre de 2024 a las 23:30, sin conjunto de validación ni selección de checkpoint; en inferencia la única
covariable futura es el feriado, que se conoce de antemano; y los 336 periodos interpolados son siete días enteros
de 2017 a 2020 (los que faltan en el silver), ninguno dentro del contexto de un origen de 2025 o 2026.[^semillas]
Como los errores de días consecutivos están correlacionados, el bootstrap por días puede quedar angosto; como
comprobación adicional, todavía fuera del notebook 04, se remuestrearon semanas y meses enteros y la combinación
sigue ganando al Random Forest en los doce casos (por semanas, en 2026: Norte −1.37 MW, IC −1.63 a −1.14; Centro
−5.22, IC −6.18 a −4.40; Sur −1.55, IC −1.90 a −1.23 a 1 hora; −1.08, IC −1.91 a −0.36; −6.23, IC −9.32 a −3.43; y
−3.71, IC −5.85 a −1.68 a 24 horas; por meses, Centro a 24 horas, IC −9.19 a −2.93).[^bloques] Por último, 2026 no
entra en ningún ajuste ni elección, pero ya se había inspeccionado en el notebook 03: una prueba realmente intacta
sería el periodo posterior al 22 de octubre de 2026.

## 5.6 La app y su validación de diseño (sintética)

Dos pasadas de medición. La primera, sobre la vista del área, con cuatro tareas fijas en un caso reproducible
(Centro, martes 10 de marzo de 2026, 19:00, a 24 horas): ver el pronóstico con su rango y lo real (T1), saber si se
puede confiar (T2), el efecto de 2 °C más (T3) y con qué fase de El Niño se equivoca más (T4). De la línea base a
la segunda iteración, T1 pasó de cumplirse a medias (2 de 4 cifras: el rango no aparecía) a cumplirse entera; el
tiempo estimado de las cuatro tareas en el celular bajó de 27.8 a 24.2 s (y a 17.8 s en escritorio con las
pantallas nuevas); axe pasó de 6 infracciones a 0; la página pesó 115 KB en vez de 157 y dejó de pedir nada a
terceros; y desaparecieron las tres menciones a una comparación con la Programación Diaria del COES que el proyecto
no hizo. No mejoró el tiempo hasta ver el número en red lenta hasta que se partió el script y se sirvió comprimido
(de 829 a 660-682 ms).[^hcd]

La segunda pasada atacó lo que el dueño señalaba como dolor principal ("cuando abro la app como que me pierdo") con
un arnés de atención y una serie de PR pequeños, cada uno con una medición clave y un umbral fijado antes:[^hcd]

| PR | Qué cambió | Medición clave: antes → después |
|---|---|---|
| 1 | Qué es Curva, dicho en la cabecera y el título | Prueba de 5 s "¿qué es esto?": responde en 1 de 4 vistas → 4 de 4 |
| 2 | Una cifra del presente al frente | Atención a 3 s en la cifra de ahora: 1.2 % → 8.2 %; "¿cuánta demanda hay ahora?": 0 → 3 de 4 vistas |
| 3 | La pregunta del día | Prueba de 5 s: 3 / 4 / 4 / 5 → 5 / 5 / 6 / 5 de 6 (cuatro vistas); cifras a la vista: 61 / 36 → 10 / 10 |
| 4 | Cada término explicado donde aparece | Términos sin definir en «Ahora» y «Confianza»: 5 / 3 y 2 / 2 → 0 |
| 5 | Tocar o arrastrar el gráfico fija la hora | Pedir otra hora del mismo día: 6 acciones, 3.2 s → 1 acción, 2.7 s |
| 6 | Selector propio de fecha y hora (dd/mm/aaaa, 24 h) | Pulsaciones de T1: 13 → 4; el caso se ve «10/03/2026» y «19:00» en un Chrome en inglés |
| 7 | El gráfico de un vistazo | Contraste de la banda en claro: 1.22 → 1.63:1; atención en el punto de «ahora»: 0.0-0.1 → 0.4-0.6 % (**no cumple** el 3 % buscado) |
| 10 | Confianza honesta de un vistazo | Atención a 3 s en el aviso de cobertura en vivo: 0.1 % → 6.0 %; selectores: 20.7 % → 0.3 % |
| 14 | Partir el script | Peso de «Ahora»: 78 → 44 KB; número en red lenta: 844-878 → 660-682 ms |

Un playtest sintético (cinco personas sintéticas por ronda, al estilo RITE) encontró y corrigió tropiezos que el
arnés no veía: el enlace a los escenarios desde el día de hoy (primer clic de T3 desde hoy, 0 → 100 %), el chip de
El Niño que parecía botón (T4 desde las tres entradas, 0 → 100 %) y la madrugada, cuando todavía no llegó el real
de ayer (explica qué día es hoy y hasta cuándo hay real: 0 → 5 de 5); una línea "¿Acertamos ayer?" bajo la
respuesta se probó y se revirtió porque no movió su medida más que el ruido. **Todo esto es sintético:** un lector
que predice dónde caen los primeros vistazos, reglas explícitas sobre lo que está a la vista y evaluadores
sintéticos que son complacientes y aplanan a los grupos (Agnew et al., 2024). Sirve para detectar regresiones y
decidir qué observar, no para afirmar que alguien entendió una cifra; lo que valida o desmiente todo lo anterior
son las sesiones con personas, con el protocolo ya escrito.[^hcd]

## 5.7 Pronóstico en vivo: seguimiento en curso

Desde el 13 de noviembre la tubería diaria emite el perfil de hoy antes de conocerse su real. Son pocos días: lo
que sigue es **seguimiento en curso, no un resultado**. Cifras al 17 de noviembre de 2026 (24 horas, Chronos-2
ajustado con calendario, frente a la mejor referencia ingenua en las mismas filas):[^vivo]

| Tramo | Periodos por área | Centro: MAE (referencia) · sesgo · cobertura 10-90 | Norte | Sur |
|---|---|---|---|---|
| En vivo (13 a 17 de noviembre, emitido antes de que el COES pudiera publicar el real) | 240 (5 días) | 90.7 MW (120.3) · −68.3 · 66.7 % | 20.0 (26.5) · −0.1 · 89.2 % | 60.7 (67.2) · +40.4 · 63.7 % |
| Ex ante estricto (solo los periodos que aún no empezaban al emitirse) | 120 | 99.2 (135.6) · −94.0 · 60.0 % | 19.0 (23.2) · −0.7 · 92.5 % | 70.2 (77.9) · +42.7 · 57.5 % |
| Reconstruido, 23 de octubre a 12 de noviembre (emitido después, con los datos hasta su origen) | 1,008 (21 días) | 79.6 (140.8) · −21.3 · 73.2 % | 32.1 (45.6) · +18.1 · 74.3 % | 34.4 (49.7) · +1.6 · 84.5 % |

A 1 hora todo es reconstruido (26 días): 51.3 MW en el Centro frente a 135.6 de la persistencia, 20.6 frente a 41.9
en el Norte y 22.7 frente a 33.6 en el Sur. El modelo le gana a la referencia en todos los tramos y áreas, pero en
el Centro **subestima** (sesgo de −68 MW en vivo y −94 en lo ex ante estricto) y el rango del 80 % cubre menos de
lo que promete (67 % en vivo; 73 % en el reconstruido), mientras que en el Sur sobrestima. Noviembre no es el arranque de El Niño sino su pico: para el ENFEN, el evento costero empezó en **marzo de 2026**
(la alerta se activó el 13 de febrero), es de magnitud extraordinaria desde agosto y el pronóstico es que siga así
hasta febrero de 2027 (Comunicado Oficial N.° 20-2026, del 13 de noviembre). El ICEN subió de 0.96 en marzo a 3.98
en agosto y 4.50 en setiembre (IGP; el temporal de octubre, 4.69), y la anomalía de Niño 1+2 estaba en +5.4 °C el
11 de noviembre (NOAA). Lima estuvo unos +4.6 °C sobre lo normal de 1991-2020 entre el 1 de octubre y el 12 de
noviembre según ERA5 (un reanálisis, no una estación; el doble que en 1997 por estas fechas), y desde el 20 de
octubre su media diaria pasó los 23-24 °C, el umbral desde el que la demanda del Centro sube alrededor de 1.9 % por
°C. Qué hay detrás del sesgo del Centro, y por qué no es "un régimen de El Niño", se revisa en la sección
5.8.[^nino-nov]

## 5.8 Diagnóstico del sesgo de noviembre: ¿calor o deriva?

Un análisis del 14 de noviembre sobre 2025, 2026 y el tramo en vivo (código en `experimentos/sesgo/`, PR #53, sin
fusionar), con la misma regla de información del modo en vivo (para corregir el día X solo valen los errores
hasta X − 1):[^sesgo]

1. **El calor explica poco del sesgo diario.** Las variables de calor (anomalía media y mínima del día y su cambio
   frente a la semana anterior) explican entre 1 y 8 % de lo que varía el sesgo diario a 24 horas en 2025 y 2026. Un
   sesgo de hoy casi no anticipa el de mañana (autocorrelación a un día de −0.06 a 0.22). Lo que sí hay es una
   **deriva lenta de estación**, del orden de 0.5 a 1 % del nivel: el sesgo mensual del Centro sale negativo cuando
   arranca o arrecia el calor (−43 MW en febrero de 2025; −19 en enero y febrero de 2026; −39 del 3 al 13 de
   noviembre, con 10 de 11 días bajo cero) y positivo cuando se enfría (+5 a +28 entre marzo y mayo). El 13 de
   noviembre, el día más cálido del periodo en Lima y el de mayor demanda (pico de 5,572 MW), el pico quedó 275 MW
   por debajo; el 1 y 2 de noviembre (feriado y lunes siguiente) dieron −103 y −119 MW en el Centro pero +60 y +87
   en el Norte: calendario, no calor.
2. **La falla ya estaba en 2026, en el pico de los días calurosos, no en el MAE.** En el 10 % de días más cálidos
   de 2026, el pico diario del Centro quedó 38 MW más corto que en el resto (IC 95 % por semanas −72 a −6; con la
   combinación, 41 MW; con el XGBoost en razón, 51) aunque el MAE del día no empeoró (+4.6 MW, IC −9.5 a +20.8),
   porque el resto del día compensa. **Esto matiza la hipótesis 1:** la temperatura no aporta en promedio, pero el
   pico de los días cálidos sí queda corto.
3. **Ningún remedio barato ayuda en la historia.** De 88 variantes de corrección del sesgo con los errores
   recientes, ninguna baja el MAE de 2025 (la menos mala lo sube 0.25 %; las de un día, entre 19 y 46 %) y en 2026 la
   mejor queda en 0.0 %; en vivo sí habría ayudado (unos 3 %), pero son 22 días. Corregir por temperatura, ajustado
   en 2025, tampoco mejora 2026 (con las anomalías empeora el Centro 5.6 MW, porque El Niño las lleva fuera de lo
   visto). **No se adopta ninguna.** El XGBoost en razón no sufre menos con el calor sino más (Centro 2026: sesgo
   de −22 frente a −6 MW de Chronos-2; pico −91 frente a −83): la lección de Tetuán no protege aquí.
4. **El rango adaptativo sí cumple lo que promete.** El rango 10-90 del modelo cubría 74-76 % en 2025 y 2026, no
   80 %. Con un ajuste conforme por lado (ACI, γ = 0.2, elegido con 2025) que abre o cierra cada borde según cuántos
   periodos quedaron fuera el día anterior, la cobertura a 24 horas pasa a 79.3-80.1 % en 2025, 79.3-80.5 % en 2026 y
   81.8-85.9 % en vivo, con un rango 12-18 % más ancho y el mismo puntaje de intervalo (±2 %). Queda **propuesto**
   como modelo en paralelo (`chronos2ftcal+rango`, PR #53, sin fusionar); no cambia lo emitido ni lo que muestra la
   app.

5. **Noviembre no es un «régimen de El Niño» que el ICEN pueda marcar** (revisión del 19 de noviembre). En los 26
   días con real (23 de octubre a 17 de noviembre), el sesgo diario del Centro no sigue la temperatura del día:
   r = −0.14 con la anomalía media (IC 95 % −0.50 a +0.26) y −0.18 con la mínima quitada la tendencia; con tan pocos
   días no se separa el calor de una deriva. Norte y Sur están **sobrestimados** en noviembre (+1.6 y +1.0 % del
   nivel), al revés de lo que diría un régimen de calor; y el ICEN lleva en «extraordinaria» desde agosto, meses en
   los que el sesgo mensual del Centro fue casi nulo (entre −9 y +11 MW de junio a octubre, con anomalías de +2.6 a
   +4.4 °C): la categoría no distingue el mes que falla de los que no. Lo que cambió es que la temperatura absoluta
   cruzó el umbral: el sesgo negativo aparece cuando Lima entra en terreno de verano, como en enero y febrero de
   2025 y de 2026, solo que este año llegó dos meses antes. Del 1 al 17 de noviembre el sesgo va en −1.2 % del nivel
   (16 de 17 días bajo cero) y el error del pico empeora semana a semana (−110, −118 y −191 MW, los últimos dos días
   solos): en el borde superior de la deriva que estimó el diagnóstico, o algo por encima; a 1 hora casi desaparece
   (−8 MW). La demanda del Centro va 11 % sobre noviembre de 2025 (del 3 al 17: 4,673 frente a 4,202 MW); con la
   respuesta a la temperatura estimada en 2016-2025 (casi nula bajo 22 °C, 1.0 %/°C entre 22 y 24 y 1.9 %/°C sobre
   24 °C), el calor de Lima explica unos 5.6 puntos, la tendencia habitual otros 2.5 a 3 y quedan unos 3 sin
   explicar, vigentes desde junio, que no se pudieron atribuir.[^nino-nov]

Lo que falta para el pico es información que el modelo no tiene: la temperatura **pronosticada** para el día
objetivo, como exceso sobre un umbral de 23 °C (la *Previous Runs API* de Open-Meteo guarda el pronóstico a un día
para Lima desde 2024, con 0.94 °C de error en la media diaria frente a su análisis), probada como covariable
futura, eligiendo con 2025 y reportando 2026 y el tramo en vivo, con el sesgo y el error del pico del Centro en los
días con pronóstico de 23 °C o más como métricas escritas antes. Sin implementar.

## 5.9 Contexto internacional

Para situar las cifras, lo que publican operadores con auditoría externa, **sin que sea una comparación de igual a
igual** (otro tamaño de sistema, otro perímetro, otro horizonte y otros años):[^refs-int]

- **REE (España).** La CNMC liga parte de la retribución de Red Eléctrica al error de su pronóstico; el indicador
  es la suma de errores absolutos horarios sobre la demanda del año (en la práctica, un WAPE). Diario: 1.600 % en
  2024 y 1.694 % en 2025; intradiario (emitido 3 h antes): 1.202 % y 1.249 %. Para decidir si un cambio cuenta, la
  CNMC corrige por la autocorrelación de los errores horarios al 99 %: la misma preocupación que el bootstrap por
  bloques de la sección 5.5.
- **NESO (Gran Bretaña)** publica cada mes un archivo abierto con el pronóstico del día siguiente, lo real y el
  error de cada media hora desde abril de 2021, y Ofgem lo usa en su esquema de incentivos. **PJM** informa a su
  comité el error horario y del pico de cada mes (enero de 2026: 1.73 % y 1.87 %).
- En conjunto, el error al día siguiente que publican los operadores está entre 1.5 y 3 %. El combinado del
  proyecto, en la prueba de 2026 a 24 horas, da un WAPE de 1.64 % en el Centro, 2.44 % en el Norte y 2.46 % en el Sur
  (MAPE de 1.66, 2.50 y 2.49 %). La comparación con una edición identificada del Programa Diario del COES queda
  pendiente; lo que ningún operador revisado hace es poner
  el error y la cobertura del rango en el mismo tablero del pronóstico, que es lo que hace la pantalla «Confianza».

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
| 13 | Captura de «Detalle»: escenarios de temperatura y diagnóstico *(pendiente: tomarla en la demo; las de «Ahora» y «Confianza» son la figura 19)* | `app/web/index.html` | 4.6 |
| 14 | Modelos fundacionales sin entrenar: mejora frente a la mejor referencia por modelo, área y horizonte, 2025 y 2026 | `notebooks/04_sein_modelos_fundacionales.ipynb` (rama `feature/modelos-fundacionales`, PR #32), celda 7 | 5.5 |
| 15 | Mes a mes en 2025 y 2026: el Random Forest, el mejor zero-shot, el mejor ajuste fino, el híbrido y la combinación, por área y horizonte | `04_sein_modelos_fundacionales.ipynb`, celda 19 | 5.5 |
| 16 | Peso en disco frente a rendimiento (MAE del Centro en 2026, a 1 y 24 h) de todos los modelos, con la frontera de lo mejor con ese peso o menos. *Nota:* el peso de varios fundacionales es estimado (parámetros × 4 bytes), marcado con círculo vacío | `paper/figuras/fig5_peso_rendimiento.png` (gráfico del 13-nov sobre las tablas del notebook 04) | 5.5 |
| 17 | Sesgo diario a 24 h del 1 de octubre al 13 de noviembre y temperatura de Lima: el feriado, la subida lenta del Centro y el 13 de noviembre | `paper/figuras/fig6_sesgo_diario_en_vivo.png` (diagnóstico del 14-nov, `experimentos/sesgo/graficos.py`, PR #53) | 5.8 |
| 18 | Cobertura del rango 10-90 antes y después del rango adaptativo, por año y área | `paper/figuras/fig7_cobertura_rango_adaptativo.png` (mismo diagnóstico) | 5.8 |
| 19 | Capturas de «Ahora» (escritorio y celular) y de «Confianza» | `docs/img/curva-ahora-escritorio.jpg`, `docs/img/curva-ahora-movil.jpg`, `docs/img/app-hcd/it8-confianza-escritorio.jpg` | 4.6 |
| 20 | Lima: temperatura media diaria de 2016-2025 por mes (cajas) y cada día de 2026 (puntos), con la franja de 23-24 °C desde la que la demanda del Centro sube ~1.9 % por °C | `paper/figuras/fig8_lima_noviembre_en_verano.png` (revisión del 19-nov; ERA5 de Open-Meteo; del 13 al 18-nov, análisis del modelo) | 5.7, 5.8 |
| 21 | Anomalía diaria de temperatura por área (ERA5, base 1991-2020) y sesgo diario a 24 h del Centro, Norte y Sur, 1 de octubre a 17 de noviembre | `paper/figuras/fig9_anomalia_y_sesgo_diario.png` (misma revisión) | 5.8 |

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
- **Explicabilidad con SHAP (notebook 05).** Sobre el XGBoost de la app (M3), en una muestra de 2025 y 2026, los
  valores SHAP pasados a MW confirman lo que dice la permutación con otro método y otro modelo: en 2026, a 1 hora, la
  demanda reciente mueve el pronóstico 347 MW en el Centro y el calendario 93, frente a 6.6 del clima y 4.9 de El Niño;
  a 24 horas mandan `Area_semana_pasada` y la hora del día. Las exógenas pesan más en 2026 que en 2025 sin mejorar el
  error. Los tres casos locales muestran un pico del Centro acertado con 13 MW de error, el peor error de 2026 (776 MW,
  el feriado del lunes 29 de junio, por restar el feriado sobre un punto de partida de fin de semana) y que en pleno
  El Niño sus variables mueven el pronóstico del Norte menos de 20 MW. El notebook incluye la sección de privacidad y
  seguridad del modelo del Entregable 8.

## 6.3 La app

Curva traduce el modelo a la decisión del operador (sección 4.6): «Ahora» pone la cifra del momento, el pico de las
próximas 24 horas y «lo que dijimos ayer» frente a lo que pasó; «Confianza» pone el error, la cobertura del rango
contra su meta y el seguimiento en vivo antes que el pronóstico; «Detalle» deja mover la temperatura pronosticada
("¿y si mañana hace 2 °C más?", solo con el XGBoost base, el único que usa el clima) y expone el diagnóstico sobre
2026. La adaptación (fijo frente a reentrenado) no se reentrena en vivo; muestra la tabla del notebook 03. Lo que
se midió de su diseño, y lo que no, está en la sección 5.6.

## 6.4 Limitaciones y amenazas a la validez

Lo que un lector debe tener en cuenta antes de generalizar los resultados.

1. **Un solo año y un solo evento en la prueba.** Los intervalos de 2026 miden la incertidumbre dentro de 2026
   (bootstrap de días); no dicen nada de otro Niño ni de otro año. A 24 horas, los errores de días vecinos siguen
   correlacionados y los intervalos pueden ser algo angostos.
2. **Efectos chicos y muchas comparaciones.** Los efectos del reentrenamiento y de las exógenas son de alrededor
   del 1 % del error: los que se distinguen de cero van de 0.09 MW (reentrenar en el Sur a 1 hora) a 1.48 MW (todas
   las exógenas juntas a 24 horas en el Centro; el clima solo, 1.35), menos del 2 % del MAE de 78 MW del Centro a
   24 horas. En 2026 se calcularon 66 intervalos al 95 % sin corrección por
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
   los dos se elija; la app ejecuta el XGBoost (y abre con el combinado, precalculado).
6. **Hipótesis.** Se escribieron después de explorar los datos de 2026 (el crecimiento del Norte ya se conocía: el
   texto original de la hipótesis 1 hablaba de "10 a 17 %", tomado del diseño de octubre; el análisis exploratorio
   midió entre 4 y 17 % según el mes, que es la cifra de este paper) y antes de evaluar ningún modelo en ellos. El origen móvil de 2023-2025 usa hiperparámetros elegidos con datos
   hasta 2024: mide estabilidad, no es una prueba ciega.
7. **Periodo y datos.** La prueba va del 1 de enero al 17 de octubre de 2026 a 1 hora y al 16 de octubre a 24
   horas (la recorta el rezago de ERA5); la
   demanda "en t" sale del IEOD validado, no del SCADA; los feriados son los nacionales; M4 (SAIDI) no se corrió.
   La corrida de 2026 se retomó tres veces desde una caché de predicciones por bloque, con cálculos deterministas.
8. **Lo que no se hizo.** No se comparó con la Programación Diaria del COES ni se modeló el SEIN directo a 24 horas:
   el modelo se mide contra referencias ingenuas, no contra el pronóstico oficial. Queda como trabajo futuro
   (sección 7).
9. **Tetuán y Ceuta.** En Tetuán, la unidad (kW) y la identidad de las zonas no tienen fuente primaria, la
   temperatura del dataset no coincide con fuentes externas, el modelo pierde en el Ramadán de la Zona 3 y su
   ventaja baja tras la transferencia del 25 de octubre. Ceuta se corrió sin ajuste de hiperparámetros, con una
   semilla y sin intervalos: sostiene la dirección del resultado, no su tamaño, y es otro sistema con otra mezcla
   de clientes. En el reanálisis, el promedio de los deltas le gana al modelo en las Zonas 2 y 3 de Tetuán y el
   delta semanal le gana al modelo sin verano en los cinco veranos de Ceuta (§5.1 y §5.2); son resultados
   descriptivos sobre ventanas ya examinadas.
10. **Validez de constructo.** El MAE no refleja la asimetría entre subestimar y sobrestimar; por eso se reporta
    aparte la subestimación en las horas de mayor demanda.
11. **La extensión con modelos fundacionales no es una prueba ciega.** Se hizo después de la prueba de 2026, así
    que sus cifras de 2026 confirman una elección hecha con 2025 pero no la ponen a prueba por primera vez. Además,
    no se puede descartar que series parecidas estén en el preentrenamiento de los modelos, las licencias difieren
    por modelo y el "XGBoost global base" de esa comparación no es el del notebook 03 (distinta ventana de
    entrenamiento). Los pesos de la combinación final se fijaron en 2025, así que sus cifras de 2025 son dentro de
    muestra; la de 2026 queda fuera del entrenamiento y de la selección, pero sobre un año ya inspeccionado, y ahí
    su diferencia con el modelo elegido excluye el cero en los seis casos. Una prueba realmente intacta sería el
    periodo posterior al 22 de octubre de 2026 (trabajo futuro).
12. **El pronóstico en vivo es un seguimiento en curso.** Cinco días emitidos de verdad antes del real (al 17 de
    noviembre) y 21 reconstruidos; en vivo el Centro subestima y el rango del 80 % cubre 67 %. El modelo en vivo es
    Chronos-2 ajustado con calendario, no el combinado (faltan los pesos de Simons en esa máquina), y "en vivo"
    significa con un día de retraso: el COES publica el real de cada día a la mañana siguiente, así que el
    horizonte de 1 hora solo puede reconstruirse.
13. **El diagnóstico del sesgo es sobre pocos días en vivo** (22) y con ERA5 como temperatura; los deciles de calor
    se ordenan dentro de cada año; los episodios se definen con el error del propio modelo. Sus remedios no se
    adoptaron; el rango adaptativo es una propuesta (PR #53) todavía sin fusionar. La revisión de El Niño del 19 de
    noviembre usa 26 días con autocorrelación y unas 50 correlaciones (que salgan algunas de 0.4 a 0.5 por azar es
    esperable); la temperatura de Lima es de un reanálisis, no de estación (ERA5 da unos 2 °C menos de anomalía que
    Campo de Marte), y del 13 al 18 de noviembre es el análisis de un modelo; el umbral de 23-24 °C se estimó con
    días de enero a abril, y que valga en noviembre es un supuesto.
14. **La validación del diseño es sintética**: atención predicha, tareas de robot, tiempos estimados y evaluadores
    sintéticos. Detecta regresiones; no dice que alguien entendió. Faltan las sesiones con personas.
15. **El contexto internacional no es una comparación de igual a igual:** otros sistemas, perímetros, horizontes y
    años; se cita para dar orden de magnitud.

# 7. Conclusiones y lecciones aprendidas

**Conclusiones, una por objetivo.**

- **OE1 (Tetuán).** Con un solo año de datos se puede pronosticar a una hora sin aprender el nivel: el modelo en
  razón queda entre 41 y 56 % por debajo de la mejor de las tres referencias históricas en la prueba y le gana en
  los 24 meses-zona del origen móvil, incluido el primer verano que nunca vio. Frente a la persistencia, que es lo
  que la literatura reporta, la mejora (−55 a −75 %) supera a la de los trabajos publicados sobre el dataset. Pero
  frente al promedio de los deltas diario y semanal, una referencia estacional más fuerte, gana en la Zona 1
  (3.8 %) y pierde en las Zonas 2 y 3 (−3.9 y −16.5 %): con un año de datos, esa referencia no se supera en dos de
  tres zonas, y esa es la medida más honesta.
- **OE2 (Ceuta).** El objetivo en razón le gana al nivel en los 25 pares de verano e historia, y el segundo y el
  tercer año aportan poco. Pero en el reanálisis sobre las mismas filas, el delta semanal le gana al modelo sin
  verano en los cinco veranos (2.06 frente a 2.33 % de MAPE): la elección del objetivo se repite en otro sistema,
  pero sin un verano visto no alcanza a una referencia estacional fuerte.
- **OE3 (SEIN).** Durante El Niño extraordinario de 2026, un modelo entrenado hasta 2025 y sin tocar le gana a la
  mejor referencia en las tres áreas y los dos horizontes (51.7, 57.9 y 29.1 % a 1 hora; 34.5, 42.2 y 11.9 % a
  24 horas), más que en un año normal, y no se degrada a medida que El Niño se intensifica. Lo que sostiene el
  pronóstico frente a esas referencias es la razón con la media de 24 horas, no las exógenas ni el
  reentrenamiento (la comparación con referencias estacionales y con el programa del COES queda pendiente):
  reentrenar cada semana baja el error alrededor del 1 % a 1 hora; a 24 horas, sin exógenas, no se distingue de no
  hacerlo, y con clima y El Niño (M2) baja el error en las tres áreas (−0.16, −0.72 y −0.66 MW)
  sin llegar al nivel del modelo fijo sin exógenas; el clima ayuda menos del 1 % a 1 hora en el Centro y
  **empeora** el pronóstico a 24 horas con temperaturas nunca vistas; El Niño no ayuda en ningún caso. Para el
  operador: modelo en razón, reentrenado cada semana, con el clima a 1 hora y sin exógenas a 24 horas, donde el
  fijo sin exógenas (29.0 / 78.1 / 48.3 MW) sigue por debajo del M2 reentrenado (29.2 / 78.8 / 48.5).[^adap26]

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
   superan a "ayer", y el propio modelo de Tetuán no supera al promedio de los deltas en dos de tres zonas.
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

**Extensión: modelos fundacionales.** Después de la prueba, ocho modelos preentrenados sin entrenar ya le ganan al
modelo elegido a 1 hora en las tres áreas (Simons: 49.7 frente a 54.6 MW en el Centro en 2025), pero no a 24 horas
en el Centro ni el Norte. Ajustando Chronos-2 con datos hasta 2024 y el feriado como covariable, y combinándolo
con el híbrido que suma el pronóstico de Simons al XGBoost en razón, el error del Centro baja de 54.6 a 48.2 MW a
1 hora y de 86.1 a 75.2 a 24 horas en 2025 (48.8 y 71.9 en 2026), y el Sur a 24 horas, el punto débil, de 56.7 a
51.8 (44.6 frente a 48.3 en 2026), con diferencias que excluyen el cero en los doce casos (en 2026, −6.2 MW en el
Centro a 24 horas, IC −8.7 a −3.8). Se propone como siguiente versión del modelo, con tres cuidados: se eligió
con un solo año y se confirmó en uno ya usado, los pesos de la combinación son de 2025 (dentro de muestra), y
exige GPU para generar el pronóstico fundacional.

**La app y el pronóstico en vivo.** Curva ejecuta los tres modelos, abre con el combinado y dice cuánto acertó;
su diseño se midió antes y después con instrumentos sintéticos (de 2 de 4 cifras de la tarea principal a 4 de 4;
cifras a la vista en la primera apertura, 61 → 10; atención en la cifra de ahora, 1.2 → 8.2 %; fijar otra hora,
6 acciones → 1), con la salvedad de que nada se probó aún con personas. Desde el 13 de noviembre una tubería diaria
emite el pronóstico del día antes de conocer su real: en cinco días en vivo le gana a la referencia en las tres
áreas, pero el Centro subestima y su rango queda corto; el diagnóstico atribuye eso a una deriva lenta de estación
y al pico de los días más cálidos, no al calor día a día, y ningún remedio barato lo arregla en la historia. El
Niño no empezó en noviembre (para el ENFEN, en marzo de 2026; extraordinario desde agosto) y no hay base para
tratar el mes como un régimen del ICEN: lo nuevo es que Lima cruzó los 23-24 °C de media desde fines de octubre, y
lo que vale la pena probar es la temperatura pronosticada con ese umbral, midiendo el pico. Lo que sí cumple lo que
promete es un rango adaptativo, propuesto y sin fusionar.

**Trabajo futuro.** Seis cosas que este trabajo no hizo y que un lector del COES pediría primero: (1) comparar el
pronóstico a 24 horas con la Programación Diaria del COES, evaluada sobre el perímetro del portal y en igualdad de
origen y horizonte, que es la vara oficial; (2) medir la sensibilidad del resultado a 24 horas al error del
pronóstico de temperatura (1 y 2 °C, como preveía el diseño), para saber si el daño del clima depende del supuesto;
(3) construir una variable de fallas que sí separe la operación normal de una falla (solo eventos con
interrupción de carga o potencia indisponible, por área) y repetir la ablación con ella; y (4) llevar la combinación
con modelos fundacionales a una prueba realmente intacta (el periodo posterior al 22 de octubre de 2026 y el
próximo año), con contextos más largos (8,192 periodos) y una licencia que permita el uso operativo; (5) probar
un pronóstico de temperatura a un día con archivo histórico como covariable futura, mirando sobre todo el pico
del Centro, y sumar el combinado y el rango adaptativo a la tubería en vivo; y (6) las sesiones con cinco personas
que validen o desmientan la medición sintética del diseño.

# 8. Bibliografía

*(Formato APA provisional; ajustar a la norma que indique el curso.)*

- Agnew, W., et al. (2024). The illusion of artificial inclusion. En *CHI 2024*.
- Amershi, S., et al. (2019). Guidelines for human-AI interaction. En *CHI 2019*.
- Ansari, A. F., et al. (2025). *Chronos-2: From univariate to universal forecasting* [Preprint]. arXiv.
  https://arxiv.org/abs/2510.15821. Modelo: `amazon/chronos-2` (Hugging Face, Apache-2.0).
- Card, S. K., Moran, T. P., & Newell, A. (1980). The keystroke-level model for user performance time with
  interactive systems. *Communications of the ACM, 23*(7), 396-410.
- CNMC. (2025, 2026). Resoluciones RAP/DE/012/25 y RAP/DE/016/26 sobre el incentivo al error de la previsión de
  demanda de Red Eléctrica (2024 y 2025). https://www.cnmc.es/sites/default/files/6336322.pdf;
  https://www.cnmc.es/sites/default/files/6915601.pdf; umbrales 2023-2025:
  https://www.cnmc.es/sites/default/files/5241389.pdf
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
- Das, A., Kong, W., Sen, R., & Zhou, Y. (2024). A decoder-only foundation model for time-series forecasting. En
  *Proceedings of the 41st International Conference on Machine Learning (ICML)*. Modelos:
  `google/timesfm-2.5-200m-pytorch` y `google/timesfm-3.0-pytorch` (Hugging Face).
- ENFEN. (2024). *Nota Técnica ENFEN 01-2024: categorías del Índice Costero El Niño*. Comisión Multisectorial
  ENFEN.
- ENFEN. (2026a). *Comunicado Oficial ENFEN N.° 03-2026* (13 de febrero de 2026: activación de la Alerta de El Niño
  Costero). https://enfen.imarpe.gob.pe/download/comunicado-oficial-enfen-n-03-2026/
- ENFEN. (2026b). *Comunicado Oficial ENFEN N.° 20-2026* (13 de noviembre de 2026).
  https://enfen.imarpe.gob.pe/download/comunicado-oficial-enfen-n-20-2026/
- ENFEN. (2026c). *Informe Técnico ENFEN, Año 12, N.° 20* (al 11 de noviembre de 2026).
  https://enfen.imarpe.gob.pe/download/informe-tecnico-enfen-ano-12-n20-al-11-noviembre-2026/?wpdmdl=2219
- Gronier, G. (2016). Measuring the first impression: Testing the validity of the 5 second test. *Journal of
  Usability Studies, 12*(1), 8-25.
- Hewamalage, H., Ackermann, K., & Bergmeir, C. (2023). Forecast evaluation for data scientists: Common pitfalls
  and best practices. *Data Mining and Knowledge Discovery, 37*, 788-832.
- Hong, T., & Fan, S. (2016). Probabilistic electric load forecasting: A tutorial review. *International Journal of
  Forecasting, 32*(3), 914-938.
- Hong, T., Pinson, P., & Fan, S. (2014). Global Energy Forecasting Competition 2012. *International Journal of
  Forecasting, 30*(2), 357-363.
- IGP. (2026). *Índice Costero El Niño (ICEN)* [Serie mensual]. Instituto Geofísico del Perú.
  http://met.igp.gob.pe/datos/ICEN.txt
- Jiang, Y., et al. (2023). UEyes: Understanding visual saliency across user interface types. En *CHI 2023*.
  Datos: Zenodo, https://doi.org/10.5281/zenodo.8010312 (CC BY 4.0).
- Kaljevic, T., Arzola, I., & Zhang, Y. (2026). *Benchmarking time series foundation models for load forecasting
  under covariate uncertainty* [Preprint]. arXiv. https://arxiv.org/abs/2610.07232
- Kay, M., Kola, T., Hullman, J., & Munson, S. (2016). When (ish) is my bus? User-centered visualizations of
  uncertainty in everyday, mobile predictive systems. En *CHI 2016*.
- Medlock, M. C., Wixon, D., Terrano, M., Romero, R., & Fulton, B. (2002). Using the RITE method to improve
  products: A definition and a case study. En *Usability Professionals Association*.
- Kshetrimayum, N., Hoque, N., & Nath, D. (2024). PConvLSTM: An effective parallel ConvLSTM-based model for
  short-term electricity load forecasting. *International Journal of Data Science and Analytics*.
- Meyer, M., et al. (2024). *Benchmarking time series foundation models for short-term household electricity load
  forecasting* [Preprint]. arXiv. https://arxiv.org/abs/2410.09487
- Modelos fundacionales usados en la extensión, por su ficha de Hugging Face *[PENDIENTE: fecha de consulta,
  versión y licencia de cada ficha; referencia académica de los que la tengan]*: `abel-lab/Simons-297M`,
  `mistralai/Timestral-209M`, `theforecastingcompany/t0-gamma`, `Datadog/Toto-2.0-313m` y `NX-AI/TiRex-2`.
- Montero-Manso, P., & Hyndman, R. J. (2021). Principles and algorithms for forecasting groups of time series:
  Locality and globality. *International Journal of Forecasting, 37*(4), 1632-1653.
- NESO. (2026). *Day-ahead half-hourly demand forecast performance* [Archivo abierto desde abril de 2021].
  https://www.neso.energy/data-portal/day-ahead-half-hourly-demand-forecast-performance
- Nielsen, J. (1994). *Usability engineering*. Morgan Kaufmann.
- NOAA Climate Prediction Center. (2026a). *Weekly Niño 1+2 SST and anomalies* [Serie semanal, base 1991-2020].
  https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for
- NOAA Climate Prediction Center. (2026b). *ENSO Diagnostic Discussion* (12 de noviembre de 2026).
  https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml
- Open-Meteo. (2026). *Historical Weather API (reanálisis ERA5 de ECMWF)*. CC BY 4.0.
  https://open-meteo.com/en/docs/historical-weather-api
- Osinergmin. (2026). *SAIDI y SAIFI por sistema eléctrico* [Dataset]. Plataforma Nacional de Datos Abiertos.
  https://www.datosabiertos.gob.pe
- Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research,
  12*, 2825-2830.
- PJM. (2026). *System operations report*, Operating Committee, 5 de febrero de 2026.
  https://www.pjm.com/-/media/DotCom/committees-groups/committees/oc/2026/20260205/20260205-item-07---system-operations-report.pdf
- Red Eléctrica de España. (2026). *Seguimiento de la demanda: previsión, programada y real*.
  https://www.ree.es/en/node/14136
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
[^nb03-datos]: `notebooks/03_sein_prueba_2026.ipynb`, celda 5: 13,920 filas de prueba a 1 h (del 1 de enero al 17
    de octubre de 2026 a las 23:30) y 13,871 a 24 h (hasta el 16 de octubre a las 23:00).
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
[^fm]: `notebooks/04_sein_modelos_fundacionales.ipynb` (rama `feature/modelos-fundacionales`, commit `bf1098b`,
    PR #32), ejecutado el 13 de noviembre de 2026: §2 zero-shot (celda 7), §3 contexto 8,192 (celda 9), §4 Chronos-2
    (celda 11), §5 híbrido (celda 13), §6 combinación (celdas 15 y 17), §7 mes a mes y regímenes (celdas 19 y 20),
    §8 intervalos (celda 22), §10 costo (celda 26), §11 propuesta (celda 28) y conclusiones (celda 31). Los
    pronósticos se generaron en Colab (GPU L4) con `experimentos/fundacionales/` (`fm_bench.py`, `adaptadores.py`,
    `chronos2_variantes.py`, `ajuste_fino.py`, `apilar.py`) y se evalúan con
    `src/tetouan_power_forecast/fundacionales.py`. Tablas en `data/reportes/sein/fundacionales/tablas/`
    (`comparacion.csv`: MAE, Δ frente al elegido con IC y cobertura; `pesos_combinacion.csv`; `ranking.csv`;
    `mensual.csv`; `regimenes_2026.csv`); pronósticos por origen en `*_c2048.parquet`, incluida
    `combinacion_c2048.parquet`. **Verificación local:** los MAE de 2026 se reprodujeron fila a fila
    sobre las 13,920 / 13,871 filas de la prueba (`predicciones_{1h,24h}_*.csv`), los de 2025 a 1 h también, y los
    de los híbridos a 24 h coinciden con el JSON; los intervalos de 2026 del híbrido con Simons frente al Random
    Forest se reprodujeron con `bootstrap_diferencia_mae` (Centro 1 h −4.85, IC −5.46 a −4.23; 24 h −2.57, IC −4.19
    a −0.90; Sur 24 h +1.54, IC 0.29 a 2.80; Norte 24 h −0.24, IC −0.78 a 0.30). El Chronos-2 ajustado con
    calendario (`chronos2ftcal_c2048.parquet`) y la combinación con los pesos indicados también se reprodujeron
    fila a fila en 2026 (18.8 / 48.8 / 20.9 y 27.9 / 71.9 / 44.6) y a 1 h en 2025, con el Δ del ajustado frente al
    Random Forest en el Norte a 24 h (−0.77, IC −1.65 a 0.12) y la cobertura 10-90 (74 a 77 %). Los intervalos de
    2025 y los de la combinación, la mejora media, el contexto de 8,192, el costo y las licencias se toman de las
    tablas y las conclusiones del notebook 04 y no se recalcularon en local.
[^semillas]: Pronósticos por semilla del ajuste fino con calendario: `chronos2ftcal_c2048.parquet` (semilla
    original) y `chronos2ftcal_s2_c2048.parquet` y `_s3` (corrida del 13-nov, en el Drive). Rango del MAE entre las
    tres semillas calculado en local sobre las filas de la prueba de 2026 y los orígenes de 2025: 0.02 / 0.06 / 0.04
    MW a 1 h y 0.06 / 0.08 / 0.09 a 24 h en 2025 (Norte / Centro / Sur); 0.02 / 0.08 / 0.01 y 0.07 / 0.19 / 0.03 en
    2026. Los días faltantes del silver (uno en 2017, dos por año de 2018 a 2020): notebook 01 del SEIN, celda 6.
[^bloques]: Comprobación adicional del 13-nov sobre `reportes/sein/fundacionales/combinacion_c2048.parquet`, aún
    fuera del notebook 04: bootstrap pareado remuestreando semanas enteras (y, aparte, meses) en vez de días. Por
    semanas, 2025: Norte −1.21 (IC −1.62 a −0.90), Centro −6.39 (−8.23 a −5.05), Sur −1.56 (−1.93 a −1.24) a 1 h;
    −1.96 (−2.90 a −1.15), −10.85 (−15.42 a −6.92), −4.92 (−8.05 a −2.21) a 24 h. 2026: los del texto. Verificación
    local de 2026 con el mismo esquema (semilla 0): Centro a 24 h, semanas −9.35 a −3.34 y meses −9.06 a −3.15; los
    doce casos siguen excluyendo el cero. Los de 2025 no se reprodujeron en local (las predicciones de validación
    del Random Forest están en el Drive).
[^hcd]: `docs/app-hcd.md` (iteraciones 1 a 8: tablas de §6, iteración 8 y "Recorrido de demo"), `docs/auditoria/`
    (`metodo.md`, `linea-base.md`, `plan.md` con la tabla de PR y sus mediciones, `plan-juego.md` con la ronda RITE)
    y los resultados versionados en `app/medicion/resultados/`. Cifras del playtest: `plan-juego.md`, "Estado tras la
    ronda RITE". Todo sintético, medido el 13 y 14 de noviembre de 2026.
[^vivo]: `experimentos/en_vivo/README.md` (qué es en vivo y qué no, tipos de fila, validaciones) y
    `src/tetouan_power_forecast/en_vivo.py`; registro en `data/reportes/sein/en_vivo/` (`pronosticos.parquet`,
    `seguimiento.parquet`, `resumen.parquet`, `corridas.jsonl`). Cifras leídas de `resumen.parquet` (nivel
    "acumulado") el 19 de noviembre, con datos del COES hasta el 17 de noviembre (51 corridas). ICEN y Niño 1+2:
    capas silver del proyecto (`exogenas/silver/icen.parquet` y `nino12_semanal.parquet`).
[^sesgo]: Diagnóstico del 14 de noviembre de 2026 (`experimentos/sesgo/`: `diagnostico.py`, `remedios.py`,
    `graficos.py`; tablas en `reportes/sein/sesgo/`; PR #53, sin fusionar). Intervalos por bootstrap de semanas
    enteras, 2,000 réplicas. Temperatura de ERA5; del 8 al 13 de noviembre, el análisis de la API de pronóstico de
    Open-Meteo llevado al nivel de ERA5.
[^refs-int]: Revisión de productos del 13 de noviembre de 2026; se citan solo las cifras verificadas en su fuente:
    CNMC (resoluciones RAP/DE/012/25 y RAP/DE/016/26 y umbrales 2023-2025), NESO (archivo abierto de desempeño) y PJM
    (informe del Operating Committee del 5-feb-2026). El WAPE y el MAPE de 2026 del combinado: `docs/app-hcd.md`,
    iteración 8 (tabla de «Confianza»), calculados sobre las 13,824 medias horas de la prueba.
[^nino-nov]: Revisión del 19 de noviembre de 2026 contra fuentes oficiales (cálculos reproducibles fuera del repo).
    ENFEN, Comunicado Oficial N.° 20-2026 (13-nov) e Informe Técnico Año 12 N.° 20 (al 11-nov), tablas 1, 3, 9 y
    10; Comunicado N.° 03-2026 (13-feb, activación de la alerta). ICEN de setiembre: 4.50 en el archivo oficial del
    IGP (`ICEN.txt`, consultado el 19-nov); la Tabla 3 del Informe Técnico N.° 20 trae 4.98, probable errata (el
    temporal de setiembre del informe anterior era 4.58 y el de octubre es 4.69, que con 4.98 sería una bajada que
    no cuadra con el mar). Niño 1+2: NOAA CPC, `wksst9120.for` (base 1991-2020): +5.3, +5.4, +5.6 y +5.4 °C las
    semanas del 21-oct al 11-nov. Temperatura: ERA5 de Open-Meteo en los mismos puntos del proyecto, climatología
    1991-2020 por día del año (±7 días); del 13 al 18-nov, análisis de su modelo de pronóstico corrido +1.1 °C para
    empalmar con ERA5. Correlaciones sobre `seguimiento.parquet` (26 días, IC de Fisher). Respuesta de la demanda
    del Centro a la temperatura de Lima: regresión con 2016-2025, efectos fijos de año-mes y día de la semana, IC por
    bootstrap de meses: ~0 %/°C bajo 22 °C (IC −0.4 a +0.3), +1.0 %/°C entre 22 y 24 (0.3 a 1.6) y +1.9 %/°C sobre
    24 °C (1.5 a 2.4). Crecimiento del Centro del 3 al 17-nov frente a 2025, mismo día de la semana: +11.2 %.
[^fm-otros]: MAE de 2026 a 1 h en el Centro calculados sobre las filas de la prueba desde
    `t0_c2048.parquet`, `toto2_c2048.parquet`, `timesfm3_c2048.parquet` y `tirex2_c2048.parquet` (51.8, 50.7, 53.2 y
    59.5 MW); el efecto de las covariables, desde `chronos2cov_c2048.parquet` frente a `chronos2_c2048.parquet`
    (Centro, 24 h, 2026: 97.6 frente a 87.3). Coinciden con `tablas/comparacion.csv` del notebook 04.
