# Primera apertura: «cuando abro la app como que me pierdo»

El dueño lo dijo así, y es el hallazgo número uno de la auditoría. Este documento mide qué ve alguien que no conoce
Curva en sus primeros 5 a 10 segundos (la URL raíz, sin parámetros), revisa qué enseña el diseño de niveles de
videojuegos sobre ese momento y propone tres conceptos de primera apertura, cada uno con la medición que diría si
funciona. **No se implementa nada todavía**: los bocetos están en
[`bocetos/primera-apertura.html`](bocetos/primera-apertura.html) y el orden de los PR, en [`plan.md`](plan.md).

## 1. Lo que pasa hoy en la primera apertura

Medido con el arnés de atención ([`metodo.md`](metodo.md)) sobre `develop`, en la URL raíz (en vivo, viernes 13 de
noviembre a las 22:30 de Lima, Centro), sin desplazarse. Detalle en [`linea-base.md`](linea-base.md).

| Primera pantalla, sin desplazarse | Escritorio 1366×768 | Proyector 1920×1080 | Tablet 1024×768 | Móvil 375×812 |
|---|---|---|---|---|
| Controles a la vista | 12 | 14 | 12 | 10 |
| Cifras a la vista (magnitudes + horas) | 40 + 16 | 56 + 22 | 29 + 14 | 22 + 11 |
| Palabras a la vista | 356 | 577 | 249 | 170 |
| Términos a la vista sin definir en la pantalla | 9 de 11 | 9 de 10 | 8 de 9 | 7 de 7 |
| Prueba de 5 s sintética (preguntas respondidas) | 4 de 6 | 3 de 6 | 3 de 6 | 3 de 6 |
| «¿Cuánta demanda hay ahora?»: atención a 7 s en la cifra (umbral 5 %) | 1.1 % | 0.8 % | 1.8 % | 3.0 % |
| Lo más mirado (3 s) | tarjetas de área 18.7 % | gráfico 15.4 % | tarjetas de área 23.5 % | título 18.9 % |
| Primer clic sintético acertado (6 tareas) | 3 | 3 | 3 | 3 |

Lo que dicen esas cifras:

1. **No hay un punto de entrada.** Compiten 12 controles y 56 cifras en la primera pantalla de un portátil. La
   atención se reparte entre las tres tarjetas de área (18.7 %; la más mirada de todas es la de **Norte**, 9.4 %, no
   la del área elegida), la marca, el título y el párrafo que explica el modo. La cifra que responde la pregunta
   principal, «cuánta demanda hay ahora», se lleva el 1.2 %; el pico, el 2.2 %; la línea de «ahora» en el gráfico,
   0.0 %. En el móvil, el gráfico ni siquiera entra en la primera pantalla (empieza a 989 px de 812).
2. **No se entiende qué es ni con qué palabras habla.** «¿Qué es esto?» solo se responde en el escritorio y al límite
   (5.2 % contra un umbral de 5 %), gracias al subtítulo «Demanda del SEIN por áreas», que no dice «pronóstico» ni
   «electricidad» y que en tablet y móvil no se muestra. A la vista hay 11 términos sin definir (SEIN, COES, MW, ICEN,
   El Niño costero, rango del 80 %, referencia, umbral, «(pron.)», repaso y en vivo); 9 no se explican en ninguna
   parte de la pantalla. **Repaso** frente a **Hoy** se explica en un párrafo de 101 caracteres por línea que la
   persona tiene que leer entero.
3. **El camino a cada tarea depende de adivinar.** Con la regla de «olor de información» (el control cuya etiqueta
   comparte palabras con la tarea, como en CogTool-Explorer), desde la raíz se acierta el primer clic en 3 de 6
   tareas: «¿y si hace más calor?» y «¿con qué fase de El Niño se equivoca?» no tienen ningún control con sus palabras
   (en vivo no aparece el enlace «¿Y si hace más calor?» y «Confianza» no dice «error» ni «El Niño»), y la descarga
   queda bajo el pliegue. Ver el pronóstico de un día pasado cuesta 15 acciones, 13 de ellas pulsaciones en los
   controles nativos de fecha y hora (7.1 s estimados con KLM), que además muestran `03/10/2026` y `07:00 PM` en un
   navegador en inglés.

Además: la cifra más grande de la pantalla (el pico, a 40 px) habla del pasado a las 22:30 («según el pronóstico, ya
pasó»), una de las cinco tarjetas de cifras está vacía en vivo («Mañana a esta hora: —») y «lo que dijimos ayer», la
rendición de cuentas que distingue a Curva, se lleva el 0.7 % en escritorio y queda fuera de la vista en tablet y
móvil.

## 2. Lo que enseña el diseño de niveles

El primer nivel de un videojuego resuelve el mismo problema que la primera pantalla de Curva: alguien que no sabe
nada tiene que entender, en segundos y sin manual, qué es esto, dónde está y qué puede hacer. Ocho principios, con
su fuente y su traducción a un producto de datos:

| Principio | De dónde viene | En Curva |
|---|---|---|
| **Enseñar haciendo, no con texto** | El World 1-1 de *Super Mario Bros.* (1985) enseña a saltar, a evitar enemigos y qué hace un bloque «?» sin una línea de instrucciones; sus autores lo describen como un nivel armado para que el jugador entienda «gradual y naturalmente» qué está haciendo (Miyamoto y Tezuka, entrevista en Eurogamer, 2015). Un experimento con más de 45,000 jugadores encontró que los tutoriales solo mejoraron el juego más complejo; en los juegos cuyas mecánicas se descubren experimentando no cambiaron nada (Andersen et al., CHI 2012) | Nada de tutoriales de texto ni carruseles de bienvenida: Curva tiene pocas mecánicas (elegir área, elegir momento, leer el rango). La primera pantalla tiene que enseñarlas usándolas |
| **Un primer cuarto seguro con una sola cosa por hacer** | La meseta inicial de *Breath of the Wild* (Nintendo, 2017) es un área cerrada donde se aprenden las mecánicas básicas antes de salir al mundo abierto | La primera apertura muestra una sola pregunta y una sola cifra; las otras cuatro cifras, las tres áreas y los controles de fecha esperan a que la persona haga su primera acción |
| **Una idea nueva por pantalla** (revelación progresiva) | Cada cámara de *Portal* (Valve, 2007) introduce una mecánica y la combina con las ya aprendidas; la revelación progresiva en interfaces (Nielsen, 2006) | «Ahora» presenta ahora, lo que viene y el pico; el rango, la referencia y la rampa aparecen cuando se piden o en el segundo paso; «Repaso» se descubre al tocar el pasado del gráfico |
| **Puntos de referencia visibles** («weenies») | Disney llamaba *weenie* al hito que atrae a la gente a través del espacio (el castillo al final de Main Street); Scott Rogers lo llevó al diseño de niveles (*Level Up!*, Wiley, 2010; charla en GDC 2009). Kevin Lynch describe los hitos y las sendas como lo que hace legible una ciudad (*The Image of the City*, 1960) | Un único hito por pantalla: el punto de «ahora» sobre la curva (hoy, 0.0 % de la atención) y una sola cifra grande que hable del presente, no del pico que ya pasó |
| **Señales consistentes** | Hodent (*The Gamer's Brain*, CRC Press, 2017) aplica percepción y atención al diseño de juegos: lo que tiene la misma función debe verse igual; Norman (*The Design of Everyday Things*, 2013) llama a esto significantes | Un nombre por concepto («Pronóstico» y no también «Modelo»; «Pico» y no también «Máximo»; un solo rango); el azul solo para el pronóstico y todo lo tocable con la misma forma |
| **Bucle corto acción → respuesta** | La sensación de control nace de la respuesta inmediata a cada acción (Swink, *Game Feel*, 2008); los «átomos de habilidad» acción → simulación → respuesta → modelo mental (Cook, *The Chemistry of Game Design*, 2007) | Tocar o arrastrar el gráfico cambia la hora y las cifras al instante (hoy el gráfico de «Ahora» solo muestra un tooltip; fijar la hora exige escribir en dos campos) |
| **Recompensa temprana** | Para Koster, la diversión es aprender un patrón (*A Theory of Fun*, 2004); la primera impresión se forma en fracciones de segundo (Lindgaard et al., 2006) y la prueba de 5 segundos la mide (Gronier, 2016) | Un «ah, ya entendí» en los primeros 5 s: la respuesta a una pregunta concreta («¿cuánta electricidad usará Lima esta noche?») antes que una tabla de cifras |
| **Dificultad opcional** | Los modos de asistencia permiten jugar el mismo juego con otro nivel de exigencia (el *Assist Mode* de *Celeste*, 2018) | «Ciudadano» y «Operador» como niveles: el mismo dato con menos o más mecánicas a la vista (el modo operador/público ya estaba en el prototipo y no se llevó) |

Lo que no se toma: la gamificación de premios, rachas y puntos. El objetivo es la legibilidad del primer nivel, no la
retención a la fuerza. Y la lección de Andersen et al. vale también al revés: si en el futuro Curva suma mecánicas
complejas (escenarios combinados, comparación de modelos), ahí sí puede justificarse ayuda contextual.

## 3. Tres conceptos de primera apertura

Cada uno se mide contra la línea base con el mismo arnés, en las cuatro vistas y en claro y oscuro, comparando
capturas del mismo momento del día (o en repaso, que es reproducible). Los umbrales se fijan aquí, antes de probar.

### A · El primer nivel es el gráfico (enseñar haciendo)

En la primera visita (sin marca en `localStorage`), «Ahora» abre en tres pasos **sobre el propio gráfico**, cada uno
con una acción: (1) el punto de «ahora» resaltado y una frase: «Este punto es ahora: el Centro usa unos 4,880 MW; a
la izquierda, lo que ya pasó; a la derecha, lo que viene» (tocar el punto para seguir); (2) el pico señalado; (3)
«Arrastra para ver otra hora», que exige arrastrar y así enseña el control nuevo (PR de clic y arrastre). Se puede
saltar y no vuelve a aparecer. Una sola cifra a la vista en el paso 1.

| Medición | Base (escritorio / móvil) | Umbral |
|---|---|---|
| Prueba de 5 s sintética, en el paso 1 | 4 / 3 de 6 | ≥ 5 de 6 en las cuatro vistas |
| Atención a 3 s en el punto de «ahora» (línea, punto y pastilla) | 0.0 % (lift 0.09) / fuera de la vista | ≥ 3 % y lift ≥ 2 |
| Cifras a la vista en el paso 1 | 40 + 16 / 22 + 11 | ≤ 5 |
| Primer clic sintético acertado (6 tareas) | 3 / 3 | ≥ 5 |
| KLM hasta fijar otra hora (T1) | 7.1 s, 15 acciones | ≤ 4 s, ≤ 3 acciones |
| Lo que no debe empeorar | axe 0, KLM de T1–T4 ≤ 17.8 s, peso ≤ 76 KB | igual o mejor |

Riesgo: un recorrido que tapa la pantalla es justo el tutorial de texto que Andersen et al. no recomiendan para
mecánicas simples. Por eso cada paso exige una acción sobre el gráfico real y el recorrido entero cabe en tres.

### B · La pregunta del día (un hito y una recompensa temprana)

Arriba de todo, una pregunta en lenguaje llano con su respuesta y el gráfico que la prueba: «¿Cuánta electricidad
usará Lima y el centro esta noche? A las 22:30, unos 4,650 MW: un 5 % menos que ahora». La pregunta cambia según la
hora (de mañana, el pico; de noche, lo que queda del día; en repaso, «¿acertamos?»). Las cinco cifras pasan a un
bloque «Todas las cifras de hoy», a un toque; las tres áreas, a un selector compacto.

| Medición | Base (escritorio / móvil) | Umbral |
|---|---|---|
| Atención a 3 s en la pregunta y su respuesta | (no existe) cifra de ahora 1.2 % / 2.1 % | ≥ 15 % en las cuatro vistas |
| «¿Qué es esto?» y «¿cuánta demanda hay ahora?» en la prueba de 5 s | sí al límite, no / no, no | sí y sí en las cuatro vistas |
| Cifras a la vista sin desplazarse | 40 + 16 / 22 + 11 | ≤ 12 en total |
| Palabras a la vista | 356 / 170 | ≤ 150 / ≤ 90 |
| Lo que no debe empeorar | T1–T4 cumplidas; cifras del caso iguales a las de la API | igual |

Riesgo: el operador que ya sabe lo que busca pierde un toque para ver las cinco cifras. Se mitiga con el concepto C
(en «Operador» las cifras vuelven a la primera pantalla).

### C · Niveles: Ciudadano y Operador, con estados vacíos que enseñan

La primera apertura entra en **Ciudadano**: tres cifras (ahora, lo más alto de hoy, cómo acertamos ayer), palabras
llanas, cada término explicado donde aparece (COES «el operador de la red», MW, el rango como «8 de cada 10 veces»)
y los vacíos convertidos en una indicación («Mañana a esta hora se calcula mañana a las 10:00; mientras, mira cómo
acertamos ayer →»). **Operador** muestra lo de hoy: las cinco cifras, rampa, referencia, umbral y el acceso al
detalle. La elección se recuerda y viaja en la URL.

| Medición | Base (escritorio / móvil) | Umbral (Ciudadano) |
|---|---|---|
| Términos a la vista sin definir en la pantalla | 9 / 7 | 0 |
| Controles a la vista | 12 / 10 | ≤ 6 |
| Tarjetas vacías en la fila de cifras (en vivo) | 1 de 5 | 0 |
| Prueba de 5 s sintética | 4 / 3 de 6 | ≥ 5 de 6 |
| Operador: KLM de T1–T4 | 17.8 / 18.8 s | ≤ base |

Riesgo: dos niveles duplican lo que hay que mantener y probar. Decisión del dueño (público objetivo de la app).

### Cómo se elige

Los tres no se excluyen: A es el aprendizaje, B el hito y C la dificultad. El plan propone probar primero lo más
barato que mueve más la prueba de 5 s (B, sin recorrido ni niveles), después A apoyado en el clic y arrastre del
gráfico, y dejar C a la decisión del dueño. La validación final no es sintética: cinco personas que no conocen Curva,
una prueba de 5 segundos y tres tareas de primer clic, antes y después (Nielsen: cinco personas encuentran la mayoría
de los problemas de una interfaz).

## Referencias

- Andersen, E., O'Rourke, E., Liu, Y.-E., Snider, R., Lowdermilk, J., Truong, D., Cooper, S. y Popović, Z. (2012). *The impact of tutorials on games of varying complexity*. CHI 2012, 59–68.
- Miyamoto, S. y Tezuka, T. (2015). Entrevista sobre el diseño del World 1-1 de *Super Mario Bros.*, Eurogamer (video, septiembre de 2015).
- Nintendo (2017). *The Legend of Zelda: Breath of the Wild* (la meseta inicial). Valve (2007). *Portal*. Maddy Makes Games (2018). *Celeste* (Assist Mode).
- Rogers, S. (2010). *Level Up! The Guide to Great Video Game Design*. Wiley (capítulo sobre Disneyland y los *weenies*; charla en GDC 2009).
- Lynch, K. (1960). *The Image of the City*. MIT Press.
- Hodent, C. (2017). *The Gamer's Brain: How Neuroscience and UX Can Impact Video Game Design*. CRC Press.
- Norman, D. (2013). *The Design of Everyday Things* (edición revisada). Basic Books.
- Swink, S. (2008). *Game Feel*. Morgan Kaufmann. Cook, D. (2007). *The Chemistry of Game Design*. Gamasutra/Lostgarden.
- Koster, R. (2004). *A Theory of Fun for Game Design*. Paraglyph.
- Lindgaard, G., Fernandes, G., Dudek, C. y Brown, J. (2006). Attention web designers: You have 50 milliseconds to make a good first impression! *Behaviour & Information Technology*, 25(2), 115–126.
- Gronier, G. (2016). Measuring the first impression: testing the validity of the 5 second test. *Journal of Usability Studies*, 12(1), 8–25.
- Nielsen, J. (2006). *Progressive Disclosure*. Nielsen Norman Group. Nielsen, J. (2000). *Why You Only Need to Test with 5 Users*. Nielsen Norman Group.
- Teo, L., John, B. E. y Blackmon, M. H. (2012). *CogTool-Explorer*. CHI 2012, 2479–2488.
