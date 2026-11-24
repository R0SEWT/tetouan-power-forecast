# Guion de la exposición final (TB1)

Exposición de 20 minutos · Grupo 3 · Metodología para Data Science · UPC 2026-2

> **De dónde salen las cifras.** Todas salen del borrador del paper (`paper/paper.md`, versión del 19 de
> noviembre, con el reanálisis de Tetuán y Ceuta del 23 de noviembre) o de la auditoría metodológica
> (`docs/auditoria-metodologica.md`). Cada bloque dice la sección y la tabla. Si el paper cambia antes de la
> exposición (por ejemplo, al recortarlo), hay que revisar las cifras de este guion contra la versión final. Lo
> que todavía no existe está marcado como **[PENDIENTE]**.
>
> **La demo tiene su kit: [`docs/demo/README.md`](demo/README.md)**, con la lista de 30 minutos antes, el recorrido
> con sus URL y tiempos medidos, el plan B (capturas en PDF y video) y las preguntas probables de la profesora.

## Cómo usar este guion

- Cada expositor lee **solo su bloque** y la hoja de cifras de la guía de defensa (`docs/guia-defensa.md`).
- Las frases entre comillas se pueden decir tal cual. No hay que memorizarlas: basta con decir la idea y la cifra.
- Las cifras van escritas en la diapositiva, así que se pueden leer. MW se lee «megavatios» y kW, «kilovatios».
- Si te quedas en blanco: lee el título de la diapositiva y la cifra grande, y pasa al siguiente punto.
- Meta en el ensayo: **terminar en 19 minutos**. El minuto que sobra se lo comen los cambios de expositor y la demo.
- **Todos tienen que estar y hablar.** En la rúbrica (criterio I), la ausencia de un integrante está en el nivel
  «Insuficiente» (`course-meto-data-science/docs/tb1-final-requisitos.md`, secciones (b) y (d); es un borrador
  hecho sin acceso al Aula).
- La exposición es **virtual, por Class Collaborate**, con los cinco con cámara y audio; después vienen unos 10
  minutos de preguntas de la profesora. **Una sola persona (Expositor 5) comparte pantalla todo el tiempo**, con la
  presentación y la app abiertas. Los demás dicen «siguiente, por favor». Así no se pierde tiempo cambiando de
  pantalla. **El Expositor 3 es el respaldo:** si se cae la conexión del Expositor 5, comparte él (la presentación en
  PDF, las capturas y el video de la demo).

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
8. **Antes de 2026: lo que aprendimos con poca historia**
   Tres filas: Tetuán, gana a las tres reglas simples (41 a 56 % menos error), pero frente al promedio de los
   deltas gana en 1 de 3 zonas; Ceuta, el delta semanal gana los 5 veranos (2.06 frente a 2.33 %); SEIN 2023-2025,
   gana a las tres reglas en 108 de 108 meses-área. Figura 5 del paper. (§5.1, §5.2 y §5.3, con sus reanálisis)
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
    Tres conclusiones (Tetuán y Ceuta; el SEIN; el método), la recomendación para el operador en cuatro puntos, la
    lección («cambiar el objetivo movió más de 1,200 kW; cambiar el algoritmo, 18») y los límites en una línea.
    (§2, §5.1, §5.2, §6.4 y §7)

**Diapositivas de respaldo** (van después de la 12; solo se muestran en el plan B o si preguntan):

- **R1, R2 y R3.** Capturas de la app: «Ahora», escenarios con +2 °C y «Confianza» con el seguimiento en vivo, ya
  tomadas en `docs/demo/capturas/` (`R1-ahora.png`, `R2-escenarios-2c.png`, `R3-confianza-en-vivo.png`; además
  `R2b-diagnostico.png`). Sirven también como la figura 13 del informe técnico, pendiente en su §6.1. El plan B de la
  demo usa la secuencia completa de `docs/demo/plan-b-capturas.pdf`.
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
| 10:30–11:40 | 1:10 | 8 · Antes de 2026: poca historia | 4 |
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
- «El Índice Costero El Niño, el ICEN, llegó a 3.98 en agosto, el valor más alto desde 1997-98, y siguió subiendo:
  4.50 en setiembre.»
- «Y la demanda del Norte creció hasta 17 % sobre 2025.»
- «Ese es justo el caso en que un modelo entrenado con el pasado puede fallar: la demanda sale de lo que vio.»
- «Nuestro objetivo es una metodología que aguante eso, y medir qué ayuda más a adaptarla.»
- «La probamos tres veces, cada vez más difícil: Tetuán, Ceuta y el SEIN.»
- «Y fijamos el criterio de éxito antes de modelar: el modelo tiene que ganarle a la mejor de tres reglas simples,
  en cada área y en cada horizonte.»
- «Las reglas son: lo mismo que ahora, lo mismo que ayer a esa hora y lo mismo que la semana pasada a esa hora.»

**Cifras:** ICEN de 3.98 (agosto de 2026) y 4.50 (setiembre, IGP); Norte hasta +17 % sobre 2025 (julio). **Fuente:**
§3, «Por qué ahora». Para el ENFEN el evento empezó en marzo de 2026 (§5.7): no decir que empezó en noviembre.
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

- «Antes de 2026 probamos el método con poca historia: Tetuán y Ceuta.»
- «En Tetuán, con un año de datos, el modelo tuvo entre 41 y 56 % menos error que las tres reglas simples.»
- «Después probamos una regla más fuerte, el delta: la demanda de ahora más lo que cambió a esa hora ayer o la
  semana pasada.»
- «Frente al promedio de los dos deltas, el modelo gana en una zona y pierde en dos.»
- «En Ceuta, el delta semanal le gana los cinco veranos: 2.06 contra 2.33 % de error.»
- «La lección: con poca historia, la conclusión depende de contra qué te comparas.»
- «Por eso en el SEIN entrenamos con nueve años, solo con lo que se sabía al predecir, y probamos fuera de lo
  visto. De 2023 a 2025 le ganó a las tres reglas en los 108 meses-área.»

**Cifras:** Tetuán, frente a las tres reglas: 44.8 / 55.9 / 40.7 % (§5.1, tabla de la prueba); frente al promedio de
los deltas: +3.8 / −3.9 / −16.5 % (§5.1, «Reanálisis descriptivo con referencias fuertes»). Ceuta, modelo sin verano
2.33 % frente a 2.06 % del delta semanal, que gana los cinco veranos (§5.2, «Reanálisis descriptivo»). SEIN 108 de
108 meses-área frente a la mejor de las tres reglas, mejora mediana de 44.6 % (§5.3, «Estable en el tiempo»).

**Ojo:** no decir que en Tetuán «le gana a todo» ni que el delta es «un error del modelo»: es una referencia más
fuerte que agregamos después, sobre ventanas ya vistas, y el resultado es descriptivo
(`docs/protocolo-reanalisis-tb1.md`). Tampoco decir que en el SEIN le gana al delta o al COES: esas comparaciones
están en curso (guía de defensa, preguntas 31 a 34).

### 11:40–13:20 · Diapositiva 9 · Expositor 4

**Qué decir:**

- «Ahora, la prueba de verdad: 2026, con El Niño extraordinario.»
- «El modelo se entrenó hasta 2025 y no se tocó durante la prueba. La corrimos una sola vez.»
- «A una hora, el error bajó 51.7 % en el Norte, 57.9 % en el Centro y 29.1 % en el Sur, frente a la mejor de
  las tres reglas simples.»
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

> **Todo lo de la demo está en el kit: [`docs/demo/README.md`](demo/README.md)** (lista de 30 minutos antes, el
> recorrido con sus URL, el plan B y las preguntas probables de la profesora). Lo de aquí es el resumen.

La app se llama **Curva** y tiene tres pantallas: «Ahora», «Confianza» y «Detalle» (README, «Qué es»; paper §4.6 y
§5.6). El recorrido es «Ahora» de hoy → un día de El Niño en repaso → tocar el pico → «¿Y si hace más calor?» →
«Confianza», con la cobertura honesta y el seguimiento en vivo. Medido con un expositor simulado (140 palabras por
minuto): **2:13**, con 47 segundos de margen (`docs/demo/cronometro.json`). Se ensaya con cronómetro.

**Antes de la exposición** (la víspera y 30 minutos antes; detalle en el kit):

1. Levantar y comprobar todo con un comando: `docs/demo/demo.sh` desde la raíz del repo. Revisa las dependencias y
   los datos, levanta la app (si 8000 u 8080 están ocupados, usa otros puertos y lo dice), comprueba `/salud` y que las
   cifras de esta tabla coinciden con las de la app, y abre las dos pestañas del recorrido. La víspera:
   `docs/demo/demo.sh --verificar`.
2. Si dice «prueba» o falta el combinado (o aparece el chip «Datos de prueba: series sintéticas»), ese día se va
   directo al plan B.
3. La cabecera de «Ahora» debe decir «Hoy · datos del COES al [ayer], 24:00». Si dice un día anterior, no se arregla:
   el paso 1 se hace igual, con la frase de «sin dato nuevo» (abajo).
4. Chrome con **zoom del 150 %** y se comparte **la ventana de Chrome**: así el texto se lee aunque Collaborate achique
   la pantalla compartida.
5. El Expositor 3 tiene descargados el PDF de capturas y el video del recorrido (`docs/demo/plan-b-capturas.pdf` y
   `docs/demo/recorrido-demo.mp4`) y puede compartir pantalla en Collaborate: es el respaldo.
6. El Expositor 5 y el Expositor 3 abren unos minutos antes la app publicada,
   **https://curva.rosewt.dev/#/ahora/centro?fecha=2026-08-27&hora=19:00**, y la dejan abierta: es la misma app, con
   las mismas cifras, y si estaba dormida tarda unos 22 segundos en despertar.

**El recorrido, minuto a minuto** (días fijos, que no dependen de la fecha en que se expone: el principal, Centro,
jueves 27 de agosto de 2026, 19:00; el respaldo, martes 10 de marzo de 2026, 19:00):

| Tiempo | Dónde | Qué decir |
|---|---|---|
| 15:40–16:05 | **«Ahora», hoy**, Centro (pestaña 1): `http://localhost:8080/#/ahora/centro`. Al final, bajar hasta «Lo que dijimos para ayer a esta hora» (sin dato nuevo se llama «Lo que se dijo un día antes»). | «Esta es Curva: corre nuestros modelos sobre la demanda que publica el COES. Lo real llega hasta ayer, porque el COES publica cada día a la mañana siguiente; desde la línea punteada todo es pronóstico, emitido hoy antes de conocer el real. [bajar] Aquí, lo que dijimos para ayer a esta hora y lo que pasó.» |
| 16:05–16:41 | **Un día de El Niño** (pestaña 2): `http://localhost:8080/#/ahora/centro?fecha=2026-08-27&hora=19:00`. Tocar en el gráfico el punto del pico («Pico 5,007 · 15:00»); después, un clic en el título «¿Acertamos…?». | «Ahora, un día de la prueba: el 27 de agosto de 2026, el mes en que el ICEN llegó a 3.98. El modelo no vio 2026 al entrenarse. Un día antes pronosticó 4,810 megavatios para las 19:00; fue 4,772, dentro del rango. [tocar el pico] Toco el pico: para las 15:00 del día siguiente dijo 5,007 y fue 5,027.» |
| 16:41–17:09 | Enlace **«¿Y si hace más calor?»** (abre «Detalle» en ese momento, sección «¿Y si…?»). Elegir **+2 °C** y bajar hasta la frase «Si hiciera 2 °C más…». | «¿Y si mañana hace dos grados más? Lo calcula el XGBoost, el único modelo que usa el clima. [+2 °C] El pico sube 8 megavatios, 0.2 %: casi nada. Y en 2026 el clima empeoró el pronóstico a 24 horas: no conviene apoyarse en él en un evento extraordinario.» |
| 17:09–17:48 | **«Confianza»**, en la cabecera (queda en el Centro, a 24 horas). Leer el titular y la tarjeta roja «En vivo, desde el 13 nov». | «Aquí la app dice cuánto acertó: en 2026 le ganó a la referencia los diez meses, con 71.9 megavatios de error a 24 horas, 47 % menos, y su rango del 90 % cubrió el 91 %. Y lo honesto: en vivo, desde el 13 de noviembre, el rango del 80 % cubre el [leer la cifra roja] %: queda corto y lo mostramos en rojo. Es seguimiento en curso, no un resultado.» |
| 17:48–17:53 | Volver a la presentación. | «El diseño lo medimos con instrumentos sintéticos; falta probarlo con personas.» **Pase:** «[Expositor 1] cierra.» |

Entre 17:53 y 18:40 quedan 47 segundos de margen. **Paso extra de 30 segundos** (la corrida diaria, «Detalle» → «En
vivo»): solo si al terminar «Confianza» el reloj marca 17:50 o menos; si no, se guarda para las preguntas (texto en el
kit). Si la profesora pregunta por mantenimiento (datos nuevos, columnas que cambian, reentrenar, automatización), las
respuestas cortas están en el kit, «Preguntas probables de la profesora».

**Cifras:** día principal, 27/08/2026 a las 19:00 (Centro, 24 h, combinado): pronóstico 4,810 MW, rango 4,629 a 4,974,
real 4,772; el día completo, 40.7 MW frente a 77.0 de «la semana pasada» (47 % menos), solo al marcar «Mostrar lo que
pasó después» (sin marcarlo se ve el error hasta las 19:00: 43.4 frente a 82.8). Al tocar el pico (28/08, 15:00):
dijimos 5,007 (4,819 a 5,178), fue 5,027. Desde ahí, +2 °C sube el pico de las 15:30 en 8 MW (+0.2 %). «Confianza»
(2026, combinado, Centro): 10 de 10 meses; 71.9 MW frente a 135.4 a 24 h (−47 %; 48.8 MW a 1 h, en «A 1 hora»);
cobertura del rango del 90 %, 91.1 %. En vivo (Chronos-2 ajustado con calendario, 24 h), al 19 de noviembre: 7 días,
Centro 82.9 MW frente a 133.3 de la referencia, cobertura del 80 %, 70.2 %; reconstruido del 23-oct al 12-nov, 73.2 %
(§5.7 del informe técnico; el short paper, tabla 7, da las cifras al 17 de noviembre). **La cifra en vivo cambia cada
día: leerla de la pantalla, no de aquí** (`demo.sh` la imprime antes de empezar). Día de respaldo, 10/03/2026 a las
19:00: dijimos 4,767 (4,588 a 4,929), fue 4,784; el día completo, 31.1 MW frente a 65.9 (53 % menos, también al
marcar «Mostrar lo que pasó después»); al tocar el pico (11/03, 14:30), dijimos 4,977 y fue 4,961, y +2 °C sube el
pico 20 MW. Todas verificadas contra la app con los modelos de Colab el 20 de noviembre (`docs/demo/verificar.py`).

**Si no hay dato nuevo ese día** (el COES no publicó, o la laptop no tiene la copia del día del registro en vivo): la
pantalla dice que el pronóstico de hoy todavía no sale y muestra lo último que se pronosticó. Se dice: «Hoy el COES
todavía no publicó la demanda de ayer: la app lo dice y muestra lo último que se pronosticó. Por eso decimos "en vivo
con un día de retraso", no "tiempo real".» El resto del recorrido usa días fijos y no cambia.

**Lo que no hay que decir en la demo:**

- «Tiempo real»: el COES publica el real de cada día a la mañana siguiente; «en vivo» significa emitido antes de que
  exista el real, con un día de retraso. El horizonte de 1 hora en vivo solo puede reconstruirse.
- «El combinado está en vivo»: en vivo corre Chronos-2 ajustado con calendario (faltan los pesos de Simons en esa
  máquina). El combinado es el de la prueba de 2026 y el que abre la app.
- «Validado con usuarios»: toda la medición del diseño es sintética; las sesiones con personas están por hacer.
- «El Niño empezó en noviembre»: para el ENFEN empezó en marzo de 2026 (alerta desde el 13 de febrero), es
  extraordinario desde agosto y seguiría así hasta febrero de 2027 (Comunicado N.° 20-2026, 13-nov). ICEN 4.50 en
  setiembre; Niño 1+2 en +5.4 °C al 11-nov. Noviembre es su pico, no su arranque. Y el sesgo del Centro no es «un
  régimen Niño»: lo nuevo es que Lima cruzó los 23-24 °C de media desde fines de octubre (§5.8, punto 5).
- La fase de El Niño del día de repaso a partir del chip «El Niño costero: extraordinario»: el chip muestra el último
  ICEN publicado, no el de ese día (en agosto sí era extraordinario; en marzo, no).
- El control «Falla en curso» de los escenarios: la variable de fallas no se pudo evaluar (auditoría, G2).

**Plan B (si falla la app o la conexión de quien comparte):**

- **Regla:** si en 20 segundos la app no carga, sale un error o aparece el chip «Datos de prueba», no se arregla en
  vivo.
- **Si falla la app local y el Expositor 5 sigue conectado:** pasa a la pestaña de **https://curva.rosewt.dev** (ya
  despierta) y sigue el mismo recorrido. Si esa tampoco responde: «Para no perder tiempo, les muestro las capturas que
  tomamos con el mismo recorrido.» Comparte `docs/demo/plan-b-capturas.pdf` (una página por paso, también son R1-R3) y dice el
  mismo texto de la tabla. Dura lo mismo.
- **Si se cae la conexión o la laptop del Expositor 5:** el **Expositor 3** dice «Sigo yo», comparte su pestaña de
  https://curva.rosewt.dev o, si no responde, el PDF (o el video
  `docs/demo/recorrido-demo.mp4`, 2:15, sin audio) y dice las frases desde el paso en que se cortó.
- Al final, ofrecer: «Si desean, en las preguntas la mostramos en vivo».

### 18:40–20:00 · Diapositiva 12 · Expositor 1

**Qué decir:**

- «Para cerrar, tres conclusiones.»
- «Uno: con poca historia, una regla estacional fuerte es difícil de superar: el delta le ganó al modelo en dos
  zonas de Tetuán y en los cinco veranos de Ceuta.»
- «Dos: en El Niño de 2026, el modelo entrenado hasta 2025 y sin tocar le ganó a las tres reglas simples en todas
  las áreas y horizontes. Combinado con un modelo fundacional, mejora más.»
- «Tres: lo que más aporta es pedir la razón, no el nivel. No el clima, ni reentrenar.»
- «Nuestra recomendación para el operador: pronosticar la razón, medirse contra la regla simple más fuerte,
  reentrenar cada semana a una hora y no apoyarse en el clima a 24 horas durante un evento extraordinario.»
- «Y la lección más grande: CRISP-DM es un ciclo. En el Entregable 7 nuestros modelos perdían contra "ayer a la
  misma hora". Volvimos a la preparación.»
- «Cambiar de algoritmo movió 18 kilovatios. Cambiar el objetivo, más de 1,200.»
- «Nuestros límites: un solo año y un solo evento, la comparación con el COES y con los deltas en el SEIN sigue en
  curso, y el seguimiento en vivo lleva pocos días.»
- «Muchas gracias. Quedamos atentos a sus preguntas.»

**Cifras:** Tetuán y Ceuta frente a los deltas: §5.1 y §5.2 (reanálisis); SEIN y combinación: §5.4 y §5.5;
recomendación: §2 (último párrafo); 18 kW frente a más de 1,200 kW: §7, lección 1; límites: §6.4, puntos 1, 8 y 9.
**Ojo:** no decir que el modelo le gana al COES ni al pronóstico oficial (guía de defensa, pregunta 33).

---

## Checklist del día

- Los cinco conectados a Collaborate 15 minutos antes, con micrófono y cámara probados. El Expositor 5 y el
  Expositor 3 comprueban que pueden compartir pantalla.
- El Expositor 5 corrió `docs/demo/demo.sh` 30 minutos antes (todo en OK) y sigue la lista de verificación del kit
  (`docs/demo/README.md`): presentación y app abiertas, Chrome al 150 %, las dos pestañas del recorrido, y la cabecera
  de «Ahora» dice «datos del COES al [ayer]».
- La cifra de cobertura en vivo de «Confianza» se lee de la pantalla ese día: cambia cada mañana (`demo.sh` la
  imprime).
- El Expositor 3 tiene el PDF de la presentación, `docs/demo/plan-b-capturas.pdf` y `docs/demo/recorrido-demo.mp4`.
- Una persona (por ejemplo, el Expositor 2, que termina temprano) lleva el tiempo y avisa por el chat del grupo si
  a los 10:30 todavía no empezó el Expositor 4.
- Si el paper cambió, revisar las cifras de las diapositivas 8, 9, 10 y 12 contra la versión final.
