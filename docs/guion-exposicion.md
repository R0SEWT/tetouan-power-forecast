# Guion de la exposición final (TB1)

Exposición de 20 minutos · Grupo 3 · Metodología para Data Science · UPC 2026-2

> **De dónde salen las cifras.** Todas salen del borrador del paper (`paper/paper.md`, versión del 19 de
> noviembre) o de la auditoría metodológica (`docs/auditoria-metodologica.md`). Cada bloque dice la sección y la
> tabla. Si el paper cambia antes de la exposición (por ejemplo, al recortarlo), hay que revisar las cifras de
> este guion contra la versión final. Lo que todavía no existe está marcado como **[PENDIENTE]**.

## Cómo usar este guion

- Cada expositor lee **solo su bloque** y la hoja de cifras de la guía de defensa (`docs/guia-defensa.md`).
- Las frases entre comillas se pueden decir tal cual. No hay que memorizarlas: basta con decir la idea y la cifra.
- Las cifras van escritas en la diapositiva, así que se pueden leer. MW se lee «megavatios» y kW, «kilovatios».
- Si te quedas en blanco: lee el título de la diapositiva y la cifra grande, y pasa al siguiente punto.
- Meta en el ensayo: **terminar en 19 minutos**. El minuto que sobra se lo comen los cambios de expositor y la demo.
- **Todos tienen que estar y hablar.** En la rúbrica (criterio I), la ausencia de un integrante está en el nivel
  «Insuficiente» (`course-meto-data-science/docs/tb1-final-requisitos.md`, secciones (b) y (d); es un borrador
  hecho sin acceso al Aula).
- Si la exposición es virtual, como el avance: **una sola persona (Expositor 5) comparte pantalla todo el tiempo**,
  con la presentación y la app abiertas. Los demás dicen «siguiente, por favor». Así no se pierde tiempo cambiando
  de pantalla.

## Reparto

| Expositor | Tiempo | Diapositivas | Qué cuenta | Criterio de la rúbrica |
|---|---|---|---|---|
| 1 | 0:00–3:00 y 18:40–20:00 | 1, 2, 3 y 12 | El problema, El Niño, los objetivos; el cierre | I, II |
| 2 | 3:00–6:30 | 4 y 5 | Los datos y lo que encontramos en ellos | III |
| 3 | 6:30–10:30 | 6 y 7 | Preparación y modelado | IV, V |
| 4 | 10:30–14:40 | 8, 9 y 10 | Resultados | V |
| 5 | 14:40–18:40 | 11 y demo | Modelos fundacionales, la app y el seguimiento en vivo | V, VI |

Sugerencia: el bloque del Expositor 3 es el más técnico; conviene que lo tome quien mejor conozca los notebooks. El
Expositor 5 tiene que ser quien pueda levantar la app.

## Las diapositivas (12 + respaldo)

Regla de diseño: una idea por diapositiva, la cifra principal en grande y poco texto. Las figuras son las de la
tabla de la sección 6.1 del paper.

1. **Pronóstico de demanda eléctrica ante niveles nunca vistos: de Tetuán a El Niño de 2026**
   Curso, UPC, Grupo 3 y los cinco integrantes. Fondo limpio.
2. **El problema: el COES necesita saber la demanda antes de que ocurra**
   Dos columnas: «1 hora» (operación en tiempo real: redespacho, reserva, arranque de unidades rápidas) y «24 horas»
   (programa del día siguiente). Debajo: «Por área: Norte, Centro y Sur, porque los enlaces entre áreas tienen
   límite». Una línea final: «Subestimar cuesta más que sobrestimar». (§3 y tabla de negocio de §4.1)
3. **¿Por qué ahora? El Niño Costero de 2026**
   Cifras grandes: «ICEN 3.98 en agosto, el mayor desde 1997-98» y «Norte: hasta +17 % sobre 2025». Objetivo
   general en una línea. Tres objetivos: OE1 Tetuán, OE2 Ceuta, OE3 SEIN. Criterio de éxito: «ganarle a la mejor de
   tres reglas simples en cada área y horizonte». Figura 3 del paper. (§3 y §4.1)
4. **Tres casos, de menor a mayor dificultad**
   Tabla de tres columnas: Tetuán (UCI, 2017, cada 10 min, 52,416 registros), Ceuta (Red Eléctrica, 2019-2026,
   391,975 intervalos), SEIN (COES, 2016 a octubre de 2026, cada 30 min, 189,504 periodos). Exógenas del SEIN:
   clima (ERA5), El Niño (ICEN y Niño 1+2), eventos del COES y feriados. Línea de tiempo: «2016-2024 entrenar ·
   2025 elegir · 2026 probar». (tabla de §4.2)
5. **Lo que encontramos en los datos**
   Cuatro hallazgos con un ícono cada uno: «+27 % de demanda en nueve años», «el pico se movió», «el Sur es
   distinto», «El Niño no es una sola señal». Figuras 1 y 2 del paper. (§4.2)
6. **Preparación: tres decisiones**
   (1) Regla de información: solo lo que se sabía al predecir. (2) Objetivo en razón: demanda futura ÷ media de las
   últimas 24 h; Tetuán: 613.4 frente a 738.5 kW. (3) Partición por fechas con hueco: 154,791 / 17,518 / 13,920
   periodos por área. Un esquema simple de la línea de tiempo con el hueco. (§4.3)
7. **Modelado: tres algoritmos y una regla para elegir**
   Ridge, Random Forest y XGBoost; validación cruzada temporal de 5 pliegues; regla escrita antes. Tabla corta de
   2025: Random Forest 43.2 %, XGBoost 42.9 %, Ridge 26.4 %. Importancia en el Centro: demanda y calendario
   248.0 MW, clima 1.10 MW. Figura 8 del paper. (§4.4 y §5.3)
8. **Antes de 2026: ¿el método se sostiene?**
   Tres filas: Tetuán, 41 a 56 % menos error que la mejor referencia; Ceuta, sin haber visto un verano, 2.31 % de
   error frente a 4.62 %; SEIN 2023-2025, gana en 108 de 108 meses-área. Figura 5 del paper. (§5.1, §5.2 y §5.3)
9. **La prueba: 2026 con El Niño extraordinario**
   Tabla de seis celdas: a 1 h, 51.7 / 57.9 / 29.1 %; a 24 h, 34.5 / 42.2 / 11.9 %. Dos mensajes: «mejor que en
   2025 en 5 de 6 casos» y «en el Norte, la mejora sube con El Niño: 42.9 % en enero, 61.6 % en septiembre».
   Figura 9 o 10 del paper. (§5.4)
10. **¿Qué ayuda a adaptarse?**
    Dos barras: «sumar clima y El Niño» y «reentrenar cada semana», ambas alrededor del 1 % del error. Una alerta:
    «A 24 h, el clima empeoró el pronóstico (Centro +1.35 MW)». Una línea: «Tres hipótesis no se cumplieron: 1b, 3
    y 4». Cierre: «"Sin efecto" también es un resultado». (§5.4 y §6.4)
11. **Frente a los modelos fundacionales: solos ganan a 1 hora; ajustados y combinados, en todo**
    Tres cifras grandes, Centro (2025): «A 1 hora: 55 → 48 MW», «A 24 horas: 86 → 75 MW» y «Sur a 24 horas: 57 →
    52 MW». Debajo: «8 modelos preentrenados sin entrenar (zero-shot) · Chronos-2 ajustado con nuestros datos hasta
    2024 + nuestro XGBoost» y «Extensión posterior a la prueba: elegido con 2025, confirmado en 2026». (§5.5, tabla
    de MAE)
12. **Conclusiones y recomendación**
    Tres conclusiones (una por objetivo), la recomendación para el operador en cuatro puntos, la lección («cambiar el
    objetivo movió más de 1,200 kW; cambiar el algoritmo, 18») y los límites en una línea. (§2, §6.4 y §7)

**Diapositivas de respaldo** (van después de la 12; solo se muestran en el plan B o si preguntan):

- **R1, R2 y R3.** Capturas de la app: «Ahora», escenarios con +2 °C y «Confianza» con el seguimiento en vivo (plan B de la demo; sirven también como
  la figura 13 del paper, que sigue pendiente, §6.1).
- **R4.** Tabla «Las hipótesis, una por una» (§5.4).
- **R5.** Tablas de ablación y de adaptación de 2026 (§5.4).
- **R6.** Limitaciones (§6.4).
- **R7.** Tabla completa de los modelos fundacionales, 2025 y 2026 (§5.5).

## Cronograma

| Tiempo | Duración | Diapositiva | Expositor |
|---|---|---|---|
| 0:00–0:20 | 0:20 | 1 · Título | 1 |
| 0:20–1:40 | 1:20 | 2 · El problema | 1 |
| 1:40–3:00 | 1:20 | 3 · El Niño y los objetivos | 1 |
| 3:00–4:30 | 1:30 | 4 · Tres casos | 2 |
| 4:30–6:30 | 2:00 | 5 · Lo que encontramos | 2 |
| 6:30–8:40 | 2:10 | 6 · Preparación | 3 |
| 8:40–10:30 | 1:50 | 7 · Modelado | 3 |
| 10:30–11:40 | 1:10 | 8 · Antes de 2026 | 4 |
| 11:40–13:20 | 1:40 | 9 · La prueba de 2026 | 4 |
| 13:20–14:40 | 1:20 | 10 · ¿Qué ayuda a adaptarse? | 4 |
| 14:40–15:40 | 1:00 | 11 · Modelos fundacionales | 5 |
| 15:40–18:40 | 3:00 | Demo de la app | 5 |
| 18:40–20:00 | 1:20 | 12 · Conclusiones | 1 |

---

## El guion, bloque por bloque

### 0:00–0:20 · Diapositiva 1 · Expositor 1

**Qué decir:**

- «Buenas noches. Somos el Grupo 3.»
- «Nuestro trabajo pronostica la demanda eléctrica del Perú una hora y un día antes.»
- «Y lo pone a prueba en el peor momento posible: El Niño Costero de 2026.»

**Cifra:** ninguna.

### 0:20–1:40 · Diapositiva 2 · Expositor 1

**Qué decir:**

- «El COES es el que opera el sistema eléctrico nacional, el SEIN.»
- «Todos los días decide qué centrales generan y cuánta reserva deja.»
- «El problema es que la demanda la conoce recién cuando ya ocurrió.»
- «Por eso necesita anticiparla a dos plazos.»
- «A una hora, para la operación en tiempo real: subir o bajar centrales, arrancar unidades rápidas.»
- «A 24 horas, para armar el programa del día siguiente.»
- «Y la necesita por área: Norte, Centro y Sur. Las líneas entre áreas tienen límite, así que un desvío en el Norte
  no siempre se cubre desde el Centro.»
- «Equivocarse por abajo cuesta más que equivocarse por arriba: obliga a arrancar generación cara de urgencia o, en
  el extremo, a cortar carga.»

**Cifra:** ninguna. **Fuente:** §3 («El problema del operador») y la tabla de negocio de §4.1.

### 1:40–3:00 · Diapositiva 3 · Expositor 1

**Qué decir:**

- «¿Por qué ahora? Porque 2026 es un año extraordinario.»
- «El Índice Costero El Niño, el ICEN, llegó a 3.98 en agosto. Es el valor más alto desde 1997-98.»
- «Y la demanda del Norte creció hasta 17 % sobre 2025.»
- «Ese es justo el caso en que un modelo entrenado con el pasado puede fallar: la demanda sale de lo que vio.»
- «Nuestro objetivo es una metodología que aguante eso, y medir qué ayuda más a adaptarla.»
- «La probamos tres veces, cada vez más difícil: Tetuán, Ceuta y el SEIN.»
- «Y fijamos el criterio de éxito antes de modelar: el modelo tiene que ganarle a la mejor de tres reglas simples,
  en cada área y en cada horizonte.»
- «Las reglas son: lo mismo que ahora, lo mismo que ayer a esa hora y lo mismo que la semana pasada a esa hora.»

**Cifras:** ICEN de 3.98 (agosto de 2026); Norte hasta +17 % sobre 2025 (julio). **Fuente:** §3, «Por qué ahora».
Criterio de éxito: §4.1, «Criterios de éxito», punto 1.

**Pase:** «Ahora [Expositor 2] les cuenta con qué datos trabajamos.»

### 3:00–4:30 · Diapositiva 4 · Expositor 2

**Qué decir:**

- «Trabajamos con tres sistemas eléctricos, todos con datos públicos.»
- «Tetuán, en Marruecos: un dataset de la UCI con un solo año, 2017, cada 10 minutos.»
- «Ceuta, en España: siete veranos de datos de Red Eléctrica. Nos sirve para ver si lo de Tetuán se repite en otro
  sistema.»
- «Y el caso central, el SEIN: datos del COES de 2016 a octubre de 2026, cada 30 minutos, por área. Son 189,504
  periodos.»
- «A la demanda le sumamos el clima, los índices de El Niño, los eventos del COES y los feriados.»
- «Partimos el tiempo en tres: entrenamos con 2016 a 2024, elegimos el modelo con 2025 y probamos en 2026, una sola
  vez.»

**Cifras:** 52,416 registros (Tetuán), 391,975 intervalos (Ceuta), 189,504 periodos (SEIN). **Fuente:** tabla de los
tres casos en §4.2.

**Ojo:** no decir que se usó el SAIDI. Aparece en la tabla de fuentes, pero esa variante (M4) no se corrió (§4.3).

### 4:30–6:30 · Diapositiva 5 · Expositor 2

**Qué decir:**

- «Antes de modelar exploramos los datos. Cuatro cosas cambiaron nuestro diseño.»
- «Uno: la demanda crece. La media del SEIN pasó de 5,496 megavatios en 2016 a 6,982 en 2025. Es 27 % más.»
- «Si el modelo aprende el nivel, queda viejo rápido. De ahí sale nuestra idea principal, que les explica mi
  compañero.»
- «Dos: el pico se movió. En 2016, el 87 % de los días el máximo caía entre las seis y las once de la noche. Desde
  2023, solo entre el 25 y el 33 %.»
- «Por eso las horas de mayor demanda las definimos por área y por año.»
- «Tres: el Sur es distinto. El domingo casi no baja y la temperatura no explica su demanda. Es carga minera e
  industrial.»
- «Cuatro: El Niño no es una sola señal. En 2017 la demanda del Norte cayó; en 2023 y en 2026, subió.»
- «Si el efecto cambia de signo, es difícil que el índice de El Niño ayude como variable. Lo vamos a ver en los
  resultados.»
- «Y un aviso de calidad: la variable de fallas del COES está activa en el 91 % de los periodos de 2025. Refleja cómo
  se registran los eventos, no si la red falla.»

**Cifras:** +27 % (5,496 → 6,982 MW); pico entre las 18 y las 23 h: 87 % de los días en 2016, entre 25 y 33 % desde
2023; Sur: el domingo −0.6 % y correlación con la temperatura de −0.07; Norte: −6 a −7 % en 2017, +2 a 6 % en 2023,
+4 a 17 % en 2026; fallas activas en el 91 % de los periodos. **Fuente:** §4.2, «Qué se encontró en el SEIN».

**Pase:** «[Expositor 3] les explica cómo preparamos los datos.»

### 6:30–8:40 · Diapositiva 6 · Expositor 3

**Qué decir:**

- «Tomamos tres decisiones de preparación.»
- «La primera es la regla de información: cada variable entra solo con lo que el operador sabía en el momento de
  predecir.»
- «Por ejemplo, el ICEN se publica con dos o tres meses de rezago, y así entra. De la temperatura, solo la última
  hora ya publicada.»
- «Así evitamos la fuga de información, que es el error más común en series de tiempo. Y está cubierto con pruebas
  automáticas en el código.»
- «La segunda es la más importante: no le pedimos al modelo los megavatios. Le pedimos una razón.»
- «La razón es la demanda futura dividida entre la media de las últimas 24 horas. Después multiplicamos por esa
  media para volver a megavatios.»
- «¿Por qué? Porque los modelos de árboles no pueden predecir valores que nunca vieron. Pero la forma del día, en
  comparación con ayer, sí la conocen.»
- «En Tetuán, con el mismo algoritmo: pidiendo el nivel, 738.5 kilovatios de error; pidiendo la razón, 613.4.»
- «La tercera: partimos por fechas, nunca al azar, y dejamos un hueco entre tramos para que nada del futuro se cuele.»
- «Quedan 154,791 periodos para entrenar, 17,518 para validar y 13,920 para la prueba, en cada área.»
- «Y 2026 se apartó en la primera celda del notebook de modelado. No volvió a aparecer hasta la prueba final.»
- «Esta idea de la razón nació de un error nuestro. Lo contamos al final.»

**Cifras:** ICEN de m−2 desde el día 20 y de m−3 antes (tabla de la regla de información, §4.3); Tetuán, validación
de la Zona 1: nivel 738.5 kW, razón 613.4 kW, mejor referencia 1,159.6 kW (§4.3, «El objetivo en razón»); 154,791 /
17,518 / 13,920 periodos a 1 h (§4.3, «Partición con hueco»).

### 8:40–10:30 · Diapositiva 7 · Expositor 3

**Qué decir:**

- «Probamos tres familias de algoritmos: Ridge, que es una regresión lineal; Random Forest; y XGBoost.»
- «Buscamos los hiperparámetros con validación cruzada temporal: cinco pliegues, siempre entrenando con el pasado y
  validando con lo que viene después.»
- «Y escribimos la regla para elegir antes de ver los resultados: gana el que más reduce el error frente a la mejor
  referencia, en promedio de las tres áreas.»
- «En 2025 ganó Random Forest, con 43.2 % de mejora. Pero XGBoost quedó en 42.9 %. En la práctica es un empate, así
  que reportamos los dos.»
- «Ridge quedó lejos, con 26.4 %: aquí sí importan las combinaciones de hora, día y demanda reciente.»
- «¿Qué variables pesan más? Lo medimos con importancia por permutación.»
- «En el Centro, la demanda reciente y el calendario suman 248 megavatios de importancia. El clima, apenas 1.1.»
- «En palabras simples: lo que más sirve para saber la demanda de la próxima hora es la demanda de ahora.»

**Cifras:** mejora media de 43.2 % (Random Forest), 42.9 % (XGBoost por área y global), 26.4 % (Ridge): §5.3, tabla
«Algoritmos y elección». Búsqueda con 5 pliegues: §4.4, tabla de búsqueda de hiperparámetros. Importancia en el
Centro: 248.0 MW (demanda y calendario) frente a 1.10 MW (clima): §5.3, «Las exógenas casi no aportan», y §6.2.

**Pase:** «[Expositor 4] les muestra los resultados.»

### 10:30–11:40 · Diapositiva 8 · Expositor 4

**Qué decir:**

- «Antes de la prueba de 2026, el método pasó tres filtros.»
- «En Tetuán, con un solo año de datos, el error quedó entre 41 y 56 % por debajo de la mejor referencia. Y le
  ganó en los 24 meses-zona.»
- «En Ceuta, sin haber visto nunca un verano, el modelo en razón tuvo 2.31 % de error, contra 4.62 % de la mejor
  regla simple.»
- «Y en el SEIN, mes a mes de 2023 a 2025, le ganó a la mejor referencia en los 108 meses-área, con El Niño de 2023
  adentro.»

**Cifras:** Tetuán 44.8 / 55.9 / 40.7 % (§5.1, tabla de la prueba); Ceuta 2.31 % frente a 4.62 % de MAPE (§5.2,
tabla de MAPE); SEIN 108 de 108 meses-área, mejora mediana de 44.6 % (§5.3, «Estable en el tiempo»).

### 11:40–13:20 · Diapositiva 9 · Expositor 4

**Qué decir:**

- «Ahora, la prueba de verdad: 2026, con El Niño extraordinario.»
- «El modelo se entrenó hasta 2025 y no se tocó durante la prueba. La corrimos una sola vez.»
- «A una hora, el error bajó 51.7 % en el Norte, 57.9 % en el Centro y 29.1 % en el Sur, frente a la mejor
  referencia.»
- «A 24 horas, 34.5, 42.2 y 11.9 %.»
- «Ganó en las tres áreas y en los dos horizontes, con intervalos lejos del cero.»
- «Y lo más interesante: en cinco de los seis casos la mejora fue mayor que en 2025, que fue un año normal.»
- «En el Norte, la mejora subió a medida que El Niño crecía: de 42.9 % en enero a 61.6 % en septiembre.»
- «El único mes en que perdió fue en el Sur, a 24 horas, en octubre.»
- «La clave es la razón con la media de 24 horas: absorbe el salto de nivel.»

**Cifras:** §5.4, tabla «El modelo fijo frente a las referencias» (Random Forest; periodo del 1 de enero al 17 de
octubre de 2026 a 1 h y al 16 de octubre a 24 h). Mejora del Norte por mes y la pérdida del Sur a 24 h en octubre (−4.1 %): §5.4, «No se degrada a
medida que El Niño se intensifica».

### 13:20–14:40 · Diapositiva 10 · Expositor 4

**Qué decir:**

- «Nuestra pregunta del tercer objetivo era: ¿qué ayuda más a adaptarse, sumar clima y El Niño, o reentrenar más
  seguido?»
- «La respuesta: las dos cosas mueven el error alrededor de 1 %. Es poco.»
- «A una hora, el clima ayuda algo solo en el Centro: menos de medio megavatio sobre 54.»
- «A 24 horas, el clima empeoró el pronóstico en el Norte y el Centro. Hubo temperaturas que nunca se habían visto,
  y los árboles no extrapolan.»
- «Reentrenar cada semana baja un poco el error a una hora en las tres áreas. A 24 horas, sin exógenas, no se
  distingue de no hacerlo; con clima y El Niño baja algo, pero no alcanza al modelo sin exógenas.»
- «Escribimos nuestras hipótesis antes de evaluar el modelo en 2026. Tres no se cumplieron, y lo reportamos así.»
- «Para nosotros, "sin efecto" también es un resultado.»

**Cifras:** clima a 1 h en el Centro, −0.46 MW (IC −0.71 a −0.20) sobre un error de 54 MW; clima a 24 h, Norte
+0.42 MW y Centro +1.35 MW (IC 0.10 a 2.97): §5.4, tabla «Ablación de exógenas en 2026». Reentrenar a 1 h sin
exógenas: −0.14 / −0.43 / −0.09 MW: §5.4, tabla «Experimento de adaptación en 2026». Hipótesis 1b, 3 y 4: §5.4,
tabla «Las hipótesis, una por una». Efectos de 0.09 a 1.48 MW, alrededor del 1 % del error: §6.4, punto 2.

**Ojo:** no decir «las fallas no ayudan». La variable de fallas no se pudo evaluar (auditoría, G2).

**Pase:** «[Expositor 5] les cuenta cómo quedamos frente a los modelos fundacionales y les muestra la app.»

### 14:40–15:40 · Diapositiva 11 · Expositor 5 · Modelos fundacionales

**Qué decir:**

- «Además probamos ocho modelos fundacionales de series de tiempo, como Chronos-2 y TimesFM.»
- «Son modelos preentrenados con millones de series de otros rubros, que pronostican una serie nueva sin entrenarse
  con ella. Los corrimos así, sin entrenar, sobre las mismas filas que nuestro modelo.»
- «Sin entrenar, ya ganan a una hora. A 24 horas no, en el Centro ni en el Norte: les falta el calendario.»
- «Entonces ajustamos uno, Chronos-2, con nuestros datos hasta 2024 y el feriado, y lo sumamos a nuestro modelo.»
- «En el Centro, el error baja de 55 a 48 megavatios a una hora y de 86 a 75 a 24 horas. Y el Sur a 24 horas, que
  era nuestro punto débil, mejora de 57 a 52.»
- «¿Por qué funciona? El modelo preentrenado aporta el patrón reciente de la serie; nuestro XGBoost, el calendario
  y el nivel.»
- «Es una extensión posterior a la prueba: lo elegimos con 2025 y en 2026 se sostiene. Y necesita GPU para generar
  el pronóstico; la app lo lee ya calculado y es el modelo con el que abre.»

**Cifras:** §5.5, tabla de MAE (2025, Centro): Random Forest 54.6 → combinación 48.2 MW a 1 h; 86.1 → 75.2 a 24 h;
Sur a 24 h, 56.7 → 51.8. En 2026: 54.1 → 48.8, 78.1 → 71.9 y 48.3 → 44.6, con intervalos que excluyen el cero en
los seis casos (Centro a 24 h: −6.2 MW, IC −8.7 a −3.8). Simons zero-shot a 1 h en el Centro: 49.7. **Ojo:** no
decir que fue una prueba ciega en 2026 ni que reemplaza al modelo del paper; es «la siguiente versión propuesta» y
sus pesos se fijaron en 2025, así que las cifras de 2025 son optimistas (§6.4, punto 11). Tampoco decir «prueba
limpia» para 2026: queda fuera del entrenamiento y de la selección, pero ya se había inspeccionado. Si preguntan por
la suerte de una semilla: el ajuste fino se repitió con tres semillas y el error cambia como mucho 0.2 MW (§5.5).

**Si preguntan por el detalle:** la tabla completa está en la diapositiva de respaldo R7 y en el notebook 04.

### 15:40–18:40 · Demo de la app · Expositor 5

La app se llama **Curva** y tiene tres pantallas: «Ahora», «Confianza» y «Detalle» (README, «Qué es»; paper §4.6 y
§5.6). El recorrido es «Ahora» → tocar el gráfico → «¿Y si hace más calor?» → «Confianza», con la cobertura honesta
y el seguimiento en vivo. Dura 3 minutos; se ensaya con cronómetro.

**Antes de la exposición (el día anterior y 30 minutos antes):**

1. Levantar la app con el modelo real: `app/levantar.sh` desde la raíz del repo (API en `:8000`, web en `:8080`;
   README, «Levantarla en 3 pasos»). La terminal debe decir `Pronosticador: real`.
2. Abrir `http://localhost:8080/#/` y comprobar que **no** aparece el chip «Datos de prueba: series sintéticas». Si
   aparece, ese día se va directo al plan B.
3. Comprobar que la corrida de la mañana entró: la cabecera de «Ahora» debe decir «Hoy · datos del COES al [ayer],
   24:00». Si dice un día anterior, correr `experimentos/en_vivo/diario.sh` (sale con 75 si el COES todavía no
   publicó el anexo; reintentar más tarde). Si a la hora de la exposición sigue sin el día de ayer, el paso 1 del
   recorrido se hace en **repaso** (segunda ruta) y se dice que el registro en vivo llega hasta el último día
   cargado.
4. Abrir en pestañas aparte las rutas del recorrido (repaso, escenarios y «Confianza») para no escribirlas en vivo.
5. Tomar las capturas R1 («Ahora»), R2 (escenarios con +2 °C) y R3 («Confianza» con el seguimiento en vivo) con el
   mismo recorrido y ponerlas en la presentación. Mientras no se tomen, sirven `docs/img/curva-ahora-escritorio.jpg`
   y `docs/img/app-hcd/it8-confianza-escritorio.jpg`.
6. El Expositor 3 tiene el PDF de la presentación con las capturas, por si se cae la conexión del Expositor 5.

**El recorrido, minuto a minuto** (el caso de repaso está verificado con el arnés: Centro, martes 10 de marzo de 2026,
19:00, a 24 horas, combinado; `docs/app-hcd.md`, «Recorrido de demo»):

| Tiempo | Dónde | Qué decir |
|---|---|---|
| 15:40–16:20 | **«Ahora»**, Centro: `http://localhost:8080/#/` (hoy). Si no hay día de hoy, el repaso: `http://localhost:8080/#/ahora/centro?fecha=2026-03-10&hora=19:00`. | «Esta es Curva. Corre nuestros modelos sobre la demanda que publica el COES. Arriba, cuánta demanda hay ahora, cuánta en una hora y el pico de las próximas 24 horas con su hora. Lo real llega hasta ayer a las 24:00, porque el COES publica cada día a la mañana siguiente; todo lo que sigue es pronóstico, emitido hoy en la mañana, antes de conocer el real. Al lado, "Lo que dijimos ayer para esta hora": lo que dijimos, lo que pasó y si cayó dentro del rango.» |
| 16:20–16:40 | **Tocar o arrastrar el gráfico** hasta la hora del pico. | «Tocar el gráfico fija la hora: las cifras y el rango se mueven con el dedo. El pronóstico va con su rango, la banda donde debería caer la demanda 8 de cada 10 veces en vivo (9 de cada 10 en el repaso de 2026).» |
| 16:40–17:20 | Enlace **«¿Y si hace más calor?»** (abre «Detalle» en el mismo momento, sección «¿Y si…?»; en vivo abre el último día con clima cargado). Elegir **+2 °C**. En repaso: `http://localhost:8080/#/area/centro?fecha=2026-03-10&hora=19:00&horizonte=24h&variante=M0&modelo=combinado` y la sección «¿Y si…?». | «A 24 horas podemos preguntar: ¿y si mañana hace dos grados más? El pronóstico sube unos 15 megavatios. Lo calcula el modelo base, el XGBoost, porque es el único que usa el clima; el combinado, el que abre por defecto, no lo usa. Esto supone que el COES recibe el pronóstico de ENFEN. Y ojo: en 2026, a 24 horas, el clima empeoró el pronóstico; por eso no recomendamos apoyarse en él en un evento extraordinario.» |
| 17:20–18:20 | **«Confianza»**, Centro: `http://localhost:8080/#/confianza/centro`. Leer el titular y las cinco cifras; bajar a «El seguimiento en vivo». | «Aquí la app dice cuánto acertó. En 2026 se equivocó menos que la referencia los diez meses, y el rango del 90 % cubrió el 91 % de las medias horas. Y aquí está lo honesto: desde el 13 de noviembre emitimos el pronóstico de cada día antes de que exista su real. [Leer la cifra de la pantalla.] Al 17 de noviembre, en cinco días en vivo, el modelo le gana a la referencia, pero en el Centro subestima y su rango del 80 % cubrió el 67 %: lo mostramos en rojo. Es seguimiento en curso, no un resultado.» |
| 18:20–18:40 | Volver a la presentación. | «Lo que ven lo medimos antes y después de cada cambio con instrumentos sintéticos; todavía no lo probamos con personas: es lo siguiente. Regreso a la presentación.» **Pase:** «[Expositor 1] cierra.» |

**Cifras:** repaso del 10/03/2026 a las 19:00 (Centro, 24 h, combinado): pronóstico 4,767 MW, rango 4,588 a 4,929,
real 4,784; error del día 31.1 MW, 53 % menos que «la semana pasada» (65.9); +2 °C → +15 MW (`docs/app-hcd.md`,
«Recorrido de demo»). «Confianza» (2026, combinado, Centro): 10 de 10 meses; cobertura del rango del 90 %, 91.1 %
(`docs/app-hcd.md`, iteración 8). En vivo al 17 de noviembre (Chronos-2 ajustado con calendario, 24 h): Centro, MAE
90.7 frente a 120.3 de la referencia, sesgo −68 MW, cobertura 66.7 %; reconstruido del 23-oct al 12-nov, 73.2 %
(§5.7 del informe técnico; short paper, tabla 7). **La cifra en vivo cambia cada día: leerla de la pantalla, no de
aquí.**

**Lo que no hay que decir en la demo:**

- «Tiempo real»: el COES publica el real de cada día a la mañana siguiente; «en vivo» significa emitido antes de que
  exista el real, con un día de retraso. El horizonte de 1 hora en vivo solo puede reconstruirse.
- «El combinado está en vivo»: en vivo corre Chronos-2 ajustado con calendario (faltan los pesos de Simons en esa
  máquina). El combinado es el de la prueba de 2026 y el que abre la app.
- «Validado con usuarios»: toda la medición del diseño es sintética; las sesiones con personas están por hacer.
- «El Niño empezó en noviembre»: viene de atrás (ICEN 0.96 en marzo, 3.98 en agosto). Si preguntan por noviembre:
  **[PENDIENTE: situación de El Niño en noviembre, con fuentes oficiales]**.
- El control «Falla en curso» de los escenarios: la variable de fallas no se pudo evaluar (auditoría, G2).

**Plan B (si la app falla):**

- **Regla:** si en 20 segundos la app no carga, sale un error o aparece el chip «Datos de prueba», no se arregla en
  vivo.
- **Frase:** «La app corre en una máquina del grupo. Para no perder tiempo, les muestro las capturas que tomamos con
  el mismo recorrido.»
- Pasar a R1 («Ahora»), R2 (escenarios) y R3 («Confianza») y decir el mismo texto de la tabla. Dura lo mismo.
- Si se cae la conexión del Expositor 5: el Expositor 3 comparte el PDF y sigue desde donde se quedó.
- Al final, ofrecer: «Si desean, en la defensa la mostramos en vivo».

### 18:40–20:00 · Diapositiva 12 · Expositor 1

**Qué decir:**

- «Para cerrar, tres conclusiones.»
- «Uno: con un solo año de datos se puede pronosticar a una hora sin aprender el nivel. Lo mostró Tetuán.»
- «Dos: no haber visto un verano cuesta un 20 % más de error, no el doble. Lo mostró Ceuta.»
- «Tres: durante El Niño de 2026, un modelo entrenado hasta 2025 y sin tocar le ganó a la mejor referencia en las
  tres áreas y en los dos horizontes.»
- «Lo que sostiene el pronóstico es el método: la razón y una vara exigente. No el clima, ni reentrenar.»
- «Nuestra recomendación para el operador: pronosticar la razón, medirse contra la mejor regla simple, reentrenar
  cada semana a una hora y no apoyarse en el clima a 24 horas durante un evento extraordinario.»
- «Y la lección más grande: CRISP-DM es un ciclo. En el Entregable 7 nuestros modelos perdían contra "ayer a la
  misma hora". Volvimos a la preparación.»
- «Cambiar de algoritmo movió 18 kilovatios. Cambiar el objetivo, más de 1,200.»
- «Nuestros límites: probamos un solo año y un solo evento, no nos comparamos con el pronóstico oficial del COES, y
  el seguimiento en vivo lleva pocos días.»
- «Muchas gracias. Quedamos atentos a sus preguntas.»

**Cifras:** conclusiones por objetivo: §7; recomendación: §2 (último párrafo); 18 kW frente a más de 1,200 kW: §7,
lección 1; límites: §6.4, puntos 1 y 8.

---

## Checklist del día

- Los cinco conectados 15 minutos antes, con micrófono probado (y cámara, si la piden).
- El Expositor 5 comparte pantalla: presentación y app abiertas, la app en «Ahora» (Centro) con la corrida de la
  mañana hecha (la cabecera dice «datos del COES al [ayer]») y las rutas del recorrido en pestañas aparte.
- La cifra de cobertura en vivo de «Confianza» se lee de la pantalla ese día: cambia cada mañana.
- El Expositor 3 tiene el PDF con las capturas de respaldo.
- Una persona (por ejemplo, el Expositor 2, que termina temprano) lleva el tiempo y avisa por el chat del grupo si
  a los 10:30 todavía no empezó el Expositor 4.
- Si el paper cambió, revisar las cifras de las diapositivas 8, 9 y 10 contra la versión final.
