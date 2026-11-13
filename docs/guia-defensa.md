# Guía de defensa individual (DD1)

Grupo 3 · Metodología para Data Science · UPC 2026-2

> **De dónde salen las cifras.** Del borrador del paper (`paper/paper.md`, versión del 13 de noviembre) y de la
> auditoría metodológica (`docs/auditoria-metodologica.md`). Cada respuesta dice la sección y la tabla. Lo que
> todavía no existe está marcado como **[PENDIENTE]**.
>
> **Qué se sabe de la DD1.** El sílabo no trae una rúbrica propia: dice que cada equipo debe «defender la solución
> metodológica completa», desde el negocio hasta la entrega. No se sabe si las preguntas serán individuales sobre
> cualquier parte (`course-meto-data-science/docs/tb1-final-requisitos.md`, sección (d); pendiente del Aula). Por
> eso **cada integrante debe poder responder cualquier pregunta**, no solo las de su parte de la exposición.

## Cómo usar esta guía

1. Aprenderse la **hoja de cifras** (15 cifras). Es lo único que hay que memorizar.
2. Leer la lista de **cosas que NO hay que afirmar**. Equivocarse ahí es peor que no saber una cifra.
3. Leer las **26 preguntas**. No hay que memorizar las respuestas: basta con la idea y la cifra.

**Cómo responder cualquier pregunta:** la idea en una frase → la cifra que la respalda → el límite, si lo hay.

**Si no sabes la respuesta:** «No tengo la cifra exacta en la cabeza; está en la sección [X] del paper. Lo que sí
puedo decir es que…». **Nunca inventar una cifra.**

---

## Hoja 1: cifras que hay que saberse

| # | Cifra | Qué es | Fuente |
|---|---|---|---|
| 1 | **51.7 / 57.9 / 29.1 %** | Cuánto menos error que la mejor referencia tuvo el modelo a 1 h en 2026 (Norte / Centro / Sur) | §5.4, tabla «El modelo fijo frente a las referencias» |
| 2 | **34.5 / 42.2 / 11.9 %** | Lo mismo, a 24 h. La mejora fue mayor que en 2025 en 5 de los 6 casos (todos menos el Sur a 24 h) | §5.4, misma tabla y texto que la sigue |
| 3 | **ICEN 3.98** | Agosto de 2026: el valor más alto desde 1997-98 | §3, «Por qué ahora» |
| 4 | **Hasta +17 %** | Crecimiento de la demanda del Norte sobre 2025 (en julio; el rango del año es de 4 a 17 %) | §3 y §4.2 |
| 5 | **+27 %** | Crecimiento de la demanda media del SEIN, de 5,496 MW (2016) a 6,982 MW (2025). Por eso el objetivo en razón | §4.2, «Crecimiento» |
| 6 | **2016-2024 / 2025 / 2026** | Entrenamiento / validación (elegir) / prueba (una sola vez). Por área a 1 h: 154,791 / 17,518 / 13,920 periodos | §4.3, «Partición con hueco» |
| 7 | **613.4 frente a 738.5 kW** | Error del modelo en razón frente al modelo en nivel (Tetuán, Zona 1; la mejor referencia, 1,159.6 kW) | §4.3, «El objetivo en razón» |
| 8 | **43.2 frente a 42.9 %** | Random Forest frente a XGBoost en 2025: empate. Ridge, 26.4 % | §5.3, tabla «Algoritmos y elección» |
| 9 | **108 de 108** | Meses-área de 2023 a 2025 en que el modelo le gana a la mejor referencia | §5.3, «Estable en el tiempo» |
| 10 | **248.0 frente a 1.10 MW** | Importancia de la demanda y el calendario frente a la del clima (Centro, 2025) | §5.3 y §6.2 |
| 11 | **Alrededor de 1 %** | Lo que cambian el error las exógenas y el reentrenamiento (de 0.09 a 1.48 MW) | §6.4, punto 2 |
| 12 | **+1.35 MW** | Lo que el clima empeoró el pronóstico a 24 h en el Centro en 2026 (IC 0.10 a 2.97) | §5.4, tabla «Ablación de exógenas en 2026» |
| 13 | **3 hipótesis no se cumplieron** | La 1b, la 3 y la 4 | §5.4, tabla «Las hipótesis, una por una» |
| 14 | **18 kW frente a más de 1,200 kW** | Lo que movió cambiar de algoritmo frente a cambiar el objetivo (del Entregable 7 a la versión en razón) | §7, lección 1 |
| 15 | **Tetuán 41-56 % · Ceuta 2.31 frente a 4.62 %** | Tetuán: menos error que la mejor referencia en la prueba. Ceuta: MAPE sin haber visto un verano frente a la mejor regla simple | §5.1, tabla de la prueba; §5.2, tabla de MAPE |
| 16 | **55 → 48 MW (1 h) · 86 → 75 (24 h) · Sur 24 h: 57 → 52** | La combinación final (Chronos-2 ajustado con calendario + híbrido XGBoost + Simons) frente al Random Forest, 2025 (54.6 → 48.2; 86.1 → 75.2; 56.7 → 51.8). En 2026: 54.1 → 48.8, 78.1 → 71.9 y 48.3 → 44.6; la diferencia excluye el cero en los 12 casos (2026, Centro 24 h: −6.2 MW, IC −8.7 a −3.8). Zero-shot solo, Simons: 49.7 a 1 h (gana) y 92.9 a 24 h (pierde) | §5.5, tabla de MAE y tabla de diferencias |

---

## Hoja 2: cosas que NO hay que afirmar

Según la auditoría metodológica. La columna de la derecha dice el hallazgo.

| # | No decir | Decir en cambio | Auditoría |
|---|---|---|---|
| 1 | «Las fallas no ayudan» o «las fallas no tienen efecto» | «La variable de fallas, tal como se pudo construir con el registro público, no distingue la operación normal de una falla (está activa el 91 % del tiempo), así que su efecto no es interpretable» | G2 |
| 2 | «Nos comparamos con el pronóstico oficial (la Programación Diaria) del COES» | «No nos comparamos con el pronóstico oficial; nos medimos contra referencias ingenuas». Ojo: la ficha técnica y la pestaña «Operación» de la app todavía lo mencionan | G3 |
| 3 | «La variable más importante es la media de 24 horas» | «`media_24h` es la escala para volver a MW, no una variable que el modelo vea. Lo que más pesa es la demanda actual» | G1 |
| 4 | «Las hipótesis se escribieron antes de ver los datos de 2026» | «Se escribieron después de explorar los datos de 2026 y antes de evaluar ningún modelo en ellos» | D3 |
| 5 | «El clima empeora el pronóstico» (a secas) | «En 2026, a 24 h, con temperaturas fuera de lo visto y un pronóstico simulado, el clima empeoró el error en el Norte y el Centro (+0.42 y +1.35 MW, menos del 2 % del error). Es un efecto chico, medido dentro de un solo año» | D4 |
| 6 | «Usamos datos del SENAMHI» o «pronósticos reales de ENFEN» | «La temperatura observada se aproxima con ERA5, un reanálisis con unos cinco días de rezago. El pronóstico a 24 h es simulado: la temperatura observada más un error de 1.5 °C» | D1 |
| 7 | «Random Forest es mejor que XGBoost», «la app corre el modelo elegido» o «la mejora fue 52, 58 y 29 %» | «Empataron (0.3 puntos, sin intervalo). El elegido, Random Forest, da 51.7, 57.9 y 29.1 %; el XGBoost global, 52.4, 58.4 y 29.2 %, y es el que corre la app» | D2, M10 |
| 8 | «Probamos de enero a octubre de 2026» | «Del 1 de enero al 17 de octubre a 1 h (al 16 a 24 h): lo recorta el rezago del clima» | D8 |
| 9 | «El origen móvil es una prueba ciega» | «El origen móvil mide estabilidad: sus hiperparámetros se eligieron con datos hasta 2024» | D6 |
| 10 | «La prueba de 2026 se corrió sin cambiar el código» | «Sin cambiar los cálculos ni las elecciones. Se cayó tres veces y se retomó desde una caché de predicciones» | D7 |
| 11 | «Mejoramos 73-75 % frente al estado del arte» (sin aclarar) o citar el MAPE de 1.42 % del total de Tetuán | «Frente a la persistencia, entre 55 y 75 %; frente a la mejor de tres referencias, entre 41 y 56 %. Las dos van juntas». El 1.42 % está por verificar: no citarlo | D13 |
| 12 | «Ceuta demuestra que el error baja 20 %» como cifra firme | «Ceuta apoya la dirección del resultado, no su tamaño: se corrió sin ajuste de hiperparámetros, con una semilla y sin intervalos» | D12 |
| 13 | «Los intervalos muestran que funcionará en el próximo Niño» | «Los intervalos miden la incertidumbre dentro de 2026: un solo año y un solo evento» | D5 |
| 14 | «Las horas de mayor demanda de 2026 o los días fuera de rango son reglas que el operador puede usar» | «Son cortes definidos con los propios datos de 2026, para describir dónde falla el modelo» | D10 |
| 15 | «Usamos el SAIDI, los feriados regionales y los comunicados de ENFEN», o «la app reentrena en vivo» | «M4 (SAIDI) no se corrió; los feriados son los nacionales; la alerta sale de los cambios de categoría del ICEN publicado. La adaptación de la app sale de la tabla del notebook 03» | D14, §13 |
| 16 | «Los modelos fundacionales pasaron una prueba limpia (o intacta) en 2026», «reemplazan a nuestro modelo» o citar las diferencias de 2025 de la combinación como si no fueran optimistas | «Es una extensión posterior a la prueba: 2026 no entra en ningún ajuste ni elección (ajuste fino hasta 2024; pesos y variantes elegidos con 2025), pero ya se había inspeccionado en el notebook 03; una prueba intacta sería el periodo posterior al 22 de octubre de 2026. Las cifras de 2025 de la combinación son optimistas porque los pesos se eligieron ahí. No está en la app ni fue parte de las hipótesis» | §6.4, punto 11; D16 |

---

## Las 26 preguntas más probables

### A. Negocio y CRISP-DM

**1. ¿Cuál es el problema de negocio y quién usaría su pronóstico?**

El COES, que opera el SEIN, necesita anticipar la demanda de cada área a una hora, para la operación en tiempo real
(redespacho, reserva, arranque de unidades rápidas), y a 24 horas, para el programa del día siguiente. Lo necesita
por área porque los enlaces entre el Norte, el Centro y el Sur tienen límite. Y subestimar cuesta más que
sobrestimar: obliga a arrancar generación cara de urgencia o a cortar carga.

*Respaldo:* el Centro es el 60 % del sistema, el Sur el 25 % y el Norte el 15 % (§4.2). Tabla de negocio de §4.1.

**2. ¿Cómo aplicaron CRISP-DM? ¿Dónde se ve que es un ciclo?**

Las seis fases están en el paper, de §4.1 a §4.6, para los tres casos. El mejor ejemplo del ciclo es nuestro
Entregable 7: los modelos en nivel le ganaban a la persistencia, pero perdían contra «ayer a la misma hora». La
evaluación nos devolvió a la preparación (tres referencias, objetivo en razón, sin calendario anual, con hueco), y
con los mismos dos algoritmos el error bajó a cerca de la mitad del de «ayer».

*Respaldo:* Entregable 7: Random Forest 1,795 kW y XGBoost 1,958 kW frente a 1,007 kW de «ayer»; en razón, XGBoost
526 kW y Random Forest 544 kW. Cambiar de algoritmo movió 18 kW; cambiar el objetivo, más de 1,200 (§7, lección 1).
*Ojo:* la profesora tiene la versión sin corregir del Entregable 7 (auditoría, D15). Se presenta como lección
aprendida, no se esconde.

**3. ¿Cuál era el criterio de éxito? ¿Se cumplió?**

Lo fijamos antes de modelar: en cada área y horizonte, el error del modelo tenía que quedar por debajo del de la mejor
de tres referencias ingenuas, en el origen móvil y en la prueba; también en las horas de mayor demanda, y reportando
dónde falla. No pusimos una meta fija de mejora. Se cumplió: en 2026 gana en las seis combinaciones de área y
horizonte, y de 2023 a 2025 gana en todos los meses.

*Respaldo:* 51.7 / 57.9 / 29.1 % a 1 h y 34.5 / 42.2 / 11.9 % a 24 h (§5.4); 108 de 108 meses-área (§5.3). Dónde
falla: el Sur a 24 h en octubre de 2026, −4.1 % (§5.4). Criterios: §4.1.

**4. ¿Por qué tres casos? ¿Para qué Tetuán si el tema es el Perú?**

Tetuán es el dataset abierto de la UCI con el que empezamos el proyecto (el del Entregable 7), y ahí diseñamos el método
con un solo año de datos. Ceuta sirve para comprobar que la elección generaliza a otro sistema y a veranos que el
modelo no vio. El SEIN es el caso central y el más difícil: un nivel de demanda nunca visto durante El Niño de 2026.
Es una sola metodología, puesta a prueba tres veces con dificultad creciente.

*Respaldo:* Tetuán, 52,416 registros de 2017; Ceuta, 391,975 intervalos de 2019 a 2026; SEIN, 189,504 periodos de
2016 a 2026 (tabla de §4.2).

### B. Datos y preparación

**5. ¿Qué hallazgo del análisis exploratorio cambió su modelado?**

El principal: la demanda del SEIN creció 27 % en nueve años, así que un modelo que aprende el nivel queda viejo
rápido; de ahí sale el objetivo en razón. Además, el pico se movió de la noche hacia el mediodía, por eso las horas
de mayor demanda se definen por área y por año. Y El Niño tuvo efectos de signo distinto en 2017, 2023 y 2026, lo que
anticipaba que el ICEN difícilmente ayudaría como variable.

*Respaldo:* 5,496 → 6,982 MW; pico entre las 18 y las 23 h el 87 % de los días en 2016 y entre 25 y 33 % desde 2023;
Norte −6 a −7 % (2017), +2 a 6 % (2023), +4 a 17 % (2026) (§4.2, «Qué se encontró en el SEIN»).

**6. ¿Qué problemas de calidad, sesgos o limitaciones tienen los datos?**

En el SEIN faltan pocos días y en 2026 la suma de las áreas se aparta del total hasta 47.6 MW, lo que no afecta
porque modelamos las áreas, no el total. La demanda «en tiempo real» la tomamos del IEOD, que el COES valida al día
siguiente: es un sustituto del SCADA que el operador sí tiene en vivo. La variable de fallas está activa casi todo el
tiempo y no sirve como señal. En Tetuán, la unidad (kW) y la identidad de las zonas no tienen fuente primaria, y la
temperatura del dataset no coincide con fuentes externas.

*Respaldo:* falta un día de 2017 y dos por año de 2018 a 2020; 47.6 MW en 2026; fallas activas en el 91 % de los
periodos de 2025; correlación de 0.83 entre la temperatura de Tetuán y ERA5 (§4.2, calidad y sesgos).

**7. ¿Por qué predicen una razón y no directamente los megavatios?**

Porque los modelos de árboles no extrapolan: no pueden predecir un valor más alto que el máximo que vieron al
entrenar. Si les pedimos la razón entre la demanda futura y la media de las últimas 24 horas, solo tienen que acertar
la forma del día, y el nivel nuevo lo trae la media. Lo comprobamos en los tres casos.

*Respaldo:* Tetuán, Zona 1: nivel 738.5 kW, cambio respecto de t 793.6 kW, razón 613.4 kW, mejor referencia
1,159.6 kW (§4.3). Ceuta: la razón le gana al nivel en los 25 pares de verano e historia (§5.2). SEIN 2026: gana con
la demanda del Norte hasta 17 % sobre 2025 (§5.4).

**8. ¿Cómo evitaron la fuga de información?**

Con la regla de información: cada variable entra solo con lo que se sabía en el momento de emitir el pronóstico, con
su rezago real de publicación. La demanda entra con rezagos hacia atrás, la temperatura es la última hora ya
publicada y el ICEN es el de dos o tres meses atrás, según su fecha de publicación. Todo lo calcula una sola función,
usada por los notebooks y la app, con pruebas automáticas; la auditoría revisó el código y esa parte se sostiene.

*Respaldo:* ICEN de m−2 desde el día 20 y de m−3 antes; Niño 1+2 con 9 días de rezago (tabla de la regla de
información, §4.3; auditoría, §1, «Lo que se sostiene»). *Si preguntan por la temperatura a 24 h:* es la observada
más un error de 1.5 °C; es un supuesto declarado, y optimista, del pronóstico que recibiría el COES, no una fuga
escondida (§4.3 y §6.4, punto 3).

**9. ¿Cómo hicieron las particiones? ¿Por qué no al azar?**

Por fechas, porque en series de tiempo partir al azar mete el futuro en el entrenamiento. En el SEIN entrenamos con
2016-2024, elegimos el modelo con 2025 y probamos en 2026 una sola vez. Entre tramos dejamos un hueco de H pasos (2
a una hora, 48 a 24 horas) para que ningún objetivo del entrenamiento caiga en el tramo siguiente; las filas de 2026
se apartan en la primera celda del notebook de modelado y se comprueba en el código.

*Respaldo:* 154,791 / 17,518 / 13,920 periodos por área a 1 h (§4.3); en Tetuán, 70/15/15 cronológica (§4.2); la
comprobación con `assert`, en la auditoría, §2.

**10. ¿Cómo aseguran que el trabajo es reproducible?**

Los datos van en capas (bronze, silver y gold) con la huella sha256 y la fecha de descarga de cada archivo. Las
variables las calcula una sola función con pruebas automáticas, usada por los notebooks y la app, y usamos semilla
fija; el Random Forest corre en CPU porque la versión en GPU no daba lo mismo dos veces. Ninguna cifra del paper se
calculó a mano: todas salen de un notebook ejecutado.

*Respaldo:* §4.3, «Reproducibilidad»; §7, lección 6. *Límite:* una sola semilla, y la corrida de 2026 se retomó tres
veces desde una caché (§6.4, punto 7; auditoría, D7 y D11).

### C. Modelado y evaluación

**11. ¿Qué algoritmos probaron y por qué esos?**

Tres familias, todas con el objetivo en razón. Ridge, una regresión lineal regularizada: si las variables en razón
ya dicen casi todo, debería bastar. Random Forest, que capta combinaciones como hora por día de la semana, y XGBoost,
que suele ser el más preciso en datos tabulares; además, un XGBoost global para las tres áreas juntas.

*Respaldo:* en 2025, Ridge 26.4 %, Random Forest 43.2 %, XGBoost por área 42.9 %, XGBoost global 42.9 % (§5.3). En
Tetuán, Ridge quedó a un punto de los árboles (48.2 frente a 49.0 %): ahí la ganancia estaba en las variables, no en
el algoritmo (§5.1).

**12. ¿Cómo buscaron los hiperparámetros? ¿Hicieron validación cruzada?**

Sí: validación cruzada temporal con 5 pliegues y un hueco de H pasos, solo sobre el entrenamiento, minimizando el
error en MW. Ridge en grilla; Random Forest y XGBoost con búsqueda aleatoria. Para acotar el cómputo buscamos en el
Centro a una hora y reutilizamos esos hiperparámetros en las otras áreas y a 24 horas.

*Respaldo:* Ridge, 13 combinaciones, MAE de 72.80 MW; Random Forest, 15 y 51.79 MW; XGBoost, 30 y 50.34 MW (§4.4,
tabla de búsqueda). *Límite:* presupuestos distintos y búsqueda solo en el Centro (§6.4, punto 5; auditoría, D2).

**13. ¿Por qué eligieron Random Forest si XGBoost ganaba en el Centro y el Norte? ¿Y por qué la app usa XGBoost?**

Porque la regla de elección se escribió antes de ver las cifras: la mayor mejora promedio de las tres áreas frente a
la mejor referencia. Con esa regla ganó Random Forest por 0.3 puntos, que decide el Sur; en la práctica es un empate
y reportamos los dos. La app usa el XGBoost global porque empató en 2025 y en 2026 y pesa decenas de MB en vez de
1 GB. Ninguna conclusión depende de cuál se elija.

*Respaldo:* 43.2 frente a 42.9 % (§5.3); en 2026 a 1 h, Random Forest 51.7 / 57.9 / 29.1 % y XGBoost global 52.4 /
58.4 / 29.2 % (§5.4); §4.6 y §6.4, punto 5.

**14. ¿Qué variables pesan más en el modelo?**

Medimos la importancia por permutación en la validación de 2025: cuánto sube el error al desordenar una variable.
Manda la demanda reciente (la demanda actual del área y la media de la última hora) y después el calendario diario;
el clima, El Niño y las fallas casi no pesan. La columna de escala (`media_24h`) no se cuenta, porque no es una
variable que el modelo vea: solo sirve para volver a MW.

*Respaldo:* Centro: demanda y calendario 248.0 MW; demanda actual 119.5; media de la última hora 55.3; clima 1.10;
El Niño 0.04; fallas −0.01 (§5.3 y §6.2; auditoría, G1).

**15. ¿Por qué compararse con referencias ingenuas? ¿No basta con un buen R²?**

No basta: la demanda está tan autocorrelacionada que hasta copiar el valor actual da un R² cercano a 1. Lo que importa
es si el modelo le gana a lo que el operador ya podría hacer sin modelo. Por eso usamos la mejor de tres reglas (lo
mismo que ahora, que ayer y que la semana pasada a esa hora), elegida en cada área, horizonte y tramo: es una vara más
exigente que la persistencia sola.

*Respaldo:* a 10 minutos, la persistencia da un R² de 0.99 en Tetuán (§3); el Entregable 7 le ganaba a la
persistencia pero perdía contra «ayer» (§7, lección 1); las referencias, en §4.5.

**16. ¿Cómo quedan frente a los trabajos publicados? ¿En qué referencias se apoyan?**

Revisamos unos 70 trabajos sobre el dataset de Tetuán: casi ninguno se compara con referencias ingenuas, y varios
pronostican a 10 minutos o usan información del instante que pronostican. Contra la persistencia, que es lo único que
reportan, nuestra mejora supera a la de los trabajos comparables; contra la mejor de tres referencias es menor, y esa
es la medida honesta. En lo metodológico nos apoyamos en CRISP-DM (Chapman et al., 2000) y en la literatura sobre
cómo evaluar pronósticos sin fugas (Tashman, 2000; Bergmeir et al., 2018; Hewamalage et al., 2023).

*Respaldo:* §3, «El vacío»; §5.1, tabla «Frente al estado del arte»: en la prueba, −75 / −73 / −55 % frente a la
persistencia; Al-Quraan et al. (2023), −48 %; Kshetrimayum et al. (2024), −62 %; Wei (2023) perdió en la Zona 3
(+44 %) porque no vio el verano. Bibliografía: §8. *Ojo:* no citar la fila «Total» (MAPE de 1.42 %), que está por
verificar (auditoría, D13).

### D. Exógenas, El Niño de 2026 y adaptación

**17. ¿Por qué el clima y El Niño casi no aportan?**

A una hora, la demanda de la última media hora ya contiene el clima del momento: si hace calor, ya se nota en la
demanda. Y la razón con la media de 24 horas ya absorbe el nivel. El Niño, además, tuvo efectos de signo distinto en
cada episodio y el ICEN llega con meses de rezago. Sobre las fallas no podemos concluir nada: la variable no distingue
la operación normal de una falla.

*Respaldo:* 2025, a 1 h: ninguna variante se aleja de M0 más de 0.32 MW, menos del 0.6 % del error; importancia del
clima 1.10 MW frente a 248.0 MW en el Centro (§5.3). 2026, a 1 h: el clima mejora el Centro −0.46 MW sobre 54 MW
(§5.4). Fallas: §4.4 y auditoría, G2.

**18. Si el clima influye en la demanda, ¿por qué empeora el pronóstico a 24 horas en 2026?**

Porque 2026 tuvo temperaturas por encima de todo lo visto entre 2016 y 2025, y los árboles no extrapolan: ante una
temperatura nueva responden como con la más alta que conocen. Además, el pronóstico de temperatura es simulado, con
error; era el riesgo que declaramos en la hipótesis 4. El efecto es chico, menos del 2 % del error y medido en un
solo año; pero si aun con un pronóstico optimista el clima empeora, con uno real difícilmente ayudaría.

*Respaldo:* clima a 24 h: Norte +0.42 MW (IC 0.16 a 0.68) y Centro +1.35 MW (IC 0.10 a 2.97), sobre un error de
78 MW en el Centro; días por encima de lo visto: 105 en el Norte, 91 en el Centro y 4 en el Sur (§5.4). Lectura
favorable: §6.4, punto 3.

**19. ¿Cómo saben que el modelo aguantó El Niño de 2026 y no fue suerte?**

El modelo, los hiperparámetros y las variantes se fijaron en 2025, y la prueba se corrió una sola vez sin tocar el
modelo. Cada diferencia va con un intervalo del 95 % por bootstrap de días: remuestreamos días enteros 2,000 veces, y
todos los intervalos frente a la referencia quedan lejos del cero. Además, la mejora no se degradó a medida que El
Niño se intensificó, y los días con temperaturas nunca vistas no fueron peores a una hora.

*Respaldo:* Norte a 1 h: diferencia de −21.6 MW (IC −22.1 a −21.1) (§5.4, tabla); mejora del Norte de 42.9 % en
enero a 61.6 % en septiembre; días fuera de lo visto, 54.8 % de mejora frente a 50.0 % dentro (§5.4); 2,000
réplicas (§4.5). *Límite:* los intervalos miden la incertidumbre dentro de 2026, no de otro Niño (§6.4, punto 1).

**20. ¿Sirve reentrenar cada semana?**

Un poco. A una hora, reentrenar cada semana bajó el error en las tres áreas en 2026, incluso en el Norte, donde en
2025 no se distinguía de cero, pero es alrededor del 1 %. A 24 horas, sin exógenas, no se distingue de no reentrenar;
con clima y El Niño (variante M2) ayuda algo y compensa parte del daño del clima, pero el M2 reentrenado no llega al
nivel del modelo fijo sin exógenas. Reentrenar solo cuando cambia la alerta de ENFEN fue peor que hacerlo cada
semana en el Centro y el Sur.

*Respaldo:* 2026 a 1 h, sin exógenas: −0.14 / −0.43 / −0.09 MW; M2 a 24 h, semanal frente a fijo: −0.16 / −0.72 /
−0.66 MW, y aun así 29.2 / 78.8 / 48.5 MW frente a 29.0 / 78.1 / 48.3 del fijo sin exógenas; alerta en lugar de
semanal a 1 h: +0.20 MW en el Centro y +0.09 en el Sur; 41 reentrenamientos semanales y 4 por alerta (§5.4, tabla
«Experimento de adaptación en 2026» y texto que la sigue; §7).

**21. ¿De verdad escribieron las hipótesis antes? ¿Cuáles fallaron?**

Se escribieron al cierre de la evaluación de 2025: después de explorar los datos de 2026 (ya sabíamos que el Norte
crecía), pero antes de evaluar ningún modelo en ellos, y se evaluaron con reglas fijadas en código. Tres no se
cumplieron: en la 1b esperábamos que la mejora del Norte bajara y subió; en la 3, que las exógenas no movieran nada a
una hora, y el clima ayudó algo en el Centro; en la 4, que el clima ayudara a 24 horas en el Centro, y lo empeoró.
Las reportamos tal como quedaron escritas.

*Respaldo:* 1b: Norte 51.7 % frente a 49 % en 2025; 3: Centro −0.53 MW (IC −0.78 a −0.27); 4: +1.35 MW (IC 0.10 a
2.97) (§5.4, tabla «Las hipótesis, una por una»). Hipótesis registradas el 5 de noviembre y prueba corrida el 6
(auditoría, §11).

### E. Límites, lo que haríamos distinto, la app y los modelos fundacionales

**22. ¿Cuáles son las principales limitaciones?**

Primero, un solo año y un solo evento en la prueba: los intervalos no dicen nada de otro Niño. Segundo, los efectos
de las exógenas y del reentrenamiento son de alrededor de 1 % y calculamos 66 intervalos sin corrección, así que
alguno «distinguible» puede ser azar. Tercero, el supuesto de colaboración COES-ENFEN es optimista: la temperatura
«observada» es ERA5 y el pronóstico a 24 horas es simulado. Cuarto, no nos comparamos con el pronóstico oficial del
COES, y el Sur a 24 horas es el punto débil.

*Respaldo:* 66 intervalos, efectos de 0.09 a 1.48 MW (§6.4, punto 2); Sur a 24 h: 11.9 % de mejora en 2026 y R² de
0.33 en 2025 (§5.3 y §5.4); la lista completa, en §6.4.

**23. ¿Qué harían distinto o con más tiempo?**

Probaríamos la sensibilidad al error del pronóstico de temperatura, con 1 y 2 °C, para saber si el daño del clima a
24 horas depende de ese supuesto. Construiríamos una variable de fallas útil, contando solo eventos con interrupción
de carga o potencia indisponible, por área. Y nos compararíamos con la Programación Diaria del COES, que es lo que
más pediría un operador; también buscaríamos hiperparámetros por área y con el mismo presupuesto para cada algoritmo.

*Respaldo:* auditoría, «Qué haría falta rehacer», puntos 2, 3 y 5; §6.4, puntos 3, 4, 5 y 8 (se probó un solo nivel
de error, 1.5 °C, cuando el plan preveía 1 y 2 °C).

**24. La rúbrica nombra Streamlit. ¿Por qué una app propia? ¿Ejecuta el modelo?**

Sí ejecuta el modelo: el backend carga el XGBoost global entrenado con 2016-2025, calcula las variables con la misma
función de los notebooks y responde pronósticos a 1 y 24 horas por área. Tiene lo que pide el enunciado: entradas del
usuario (área, fecha, hora, horizonte y escenario), la predicción y gráficos explicativos (real contra predicho,
residuos, error por régimen, ablación e importancia). Elegimos una app propia asumiendo ese riesgo, con la condición
de que corra el modelo y no muestre resultados precalculados; la única tabla precalculada es la de reentrenamiento,
porque no se puede reentrenar en vivo.

*Respaldo:* §4.6 y §6.3; rúbrica, criterio VI (`tb1-final-requisitos.md`, sección (b)). *Ojo:* los intervalos de la
app salen de los errores de 2025 del Random Forest (auditoría, M4). Decir «intervalos empíricos, de los errores de
2025».

**25. ¿Cómo queda su modelo frente a los modelos fundacionales, como TimesFM o Chronos-2?**

Son modelos preentrenados con millones de series de tiempo de distintos rubros, que pronostican una serie nueva sin
entrenarse con ella. Después de la prueba de 2026 comparamos ocho (Simons, Timestral, t0-gamma, Chronos-2, Toto,
TimesFM 2.5 y 3.0, TiRex) sin entrenar, con 43 días de contexto, sobre las mismas filas que nuestro modelo, en 2025
y 2026, a 1 y 24 horas y en las tres áreas. Solos, los mejores ganan a una hora en las tres áreas, pero a 24 horas
pierden en el Centro y el Norte: les falta el calendario. Entonces ajustamos Chronos-2 con nuestros datos hasta
2024 y el feriado como covariable, y lo combinamos con un híbrido (nuestro XGBoost en razón con el pronóstico de
un fundacional como variable). Esa combinación le gana a nuestro modelo en los doce casos: en el Centro, el error
baja de 55 a 48 MW a una hora y de 86 a 75 a 24 horas, y el Sur a 24 horas, el punto débil, de 57 a 52. ¿Por qué
funciona? El modelo preentrenado aporta el patrón reciente de la serie; el XGBoost, el calendario y el nivel. ¿Qué
cuesta? GPU para generar el pronóstico fundacional (y 26 minutos para ajustar Chronos-2); la app lo leería ya
calculado. La temperatura como covariable no lo ayuda, igual que a nuestro modelo. Lo proponemos como siguiente
versión, con tres cuidados: se eligió con un solo año y se confirmó en un año que ya habíamos usado, y los pesos de
la combinación se fijaron en 2025, así que sus cifras de 2025 son optimistas; las de 2026 quedan fuera del
entrenamiento y de la selección, pero sobre un año que ya habíamos inspeccionado.

*Respaldo:* §5.5, tabla de MAE (Centro, 2025): Random Forest 54.6 → combinación 48.2 MW a 1 h; 86.1 → 75.2 a 24 h;
Sur a 24 h 56.7 → 51.8. En 2026: 54.1 → 48.8, 78.1 → 71.9 y 48.3 → 44.6. Diferencias con el Random Forest en 2026
(tabla de §5.5): Centro −5.2 MW a 1 h (IC −5.8 a −4.6) y −6.2 a 24 h (IC −8.7 a −3.8); Sur a 24 h −3.7 (IC −5.5 a
−1.9); Norte a 24 h −1.1 (IC −1.8 a −0.3); ninguno cruza el cero. Mejora media frente a la mejor referencia: 35.2 →
40.7 % en 2025 y 37.9 → 42.3 % en 2026. Simons zero-shot a 1 h en el Centro, 49.7; con cuatro veces más contexto,
casi igual (91.5 frente a 92.9 a 24 h en 2025). Chronos-2 ajustado con calendario frente a Random Forest: gana con
intervalos que excluyen el cero salvo en el Norte a 24 h en 2026 (−0.77 MW, IC −1.65 a 0.12). Covariables de
temperatura: Chronos-2 zero-shot a 24 h en el Centro en 2026, 97.6 frente a 87.3 MW. *Límites:* §6.4, punto 11 (no
es prueba ciega; pesos de 2025 dentro de muestra; posible contaminación del preentrenamiento; licencias). *Robustez:* el ajuste fino repetido con tres semillas
cambia el MAE como mucho 0.2 MW, frente a −10.5 MW de ventaja en el Centro a 24 h; el código se revisó y no hay
fuga (solo ve datos hasta 2024; la única covariable futura es el feriado). *Ojo:* el
«XGBoost global base» de esa tabla no es el XGBoost del notebook 03 (§5.5). Detalle: notebook 04 (PR #32).

**26. ¿Los intervalos no son demasiado optimistas? Los errores de días seguidos están correlacionados.**

Es cierto que lo están, y por eso el bootstrap remuestrea días enteros y no periodos sueltos; aun así, a 24 horas
los días vecinos siguen correlacionados y el intervalo puede quedar algo angosto. Lo comprobamos remuestreando
semanas enteras y, aparte, meses enteros: los intervalos se ensanchan, pero la combinación sigue ganándole al
Random Forest en los doce casos, y lo mismo pasa con el resultado principal de 2026, cuyas diferencias con la
referencia están muy lejos del cero. Y el límite de fondo no cambia: todos miden la incertidumbre dentro de un solo
año.

*Respaldo:* por semanas, Centro a 24 h en 2026: −6.23 MW, IC −9.32 a −3.43 (por días, −8.67 a −3.81); por meses,
−9.19 a −2.93; Norte a 24 h en 2026, el caso más ajustado: −1.08, IC −1.91 a −0.36 (§5.5 del informe técnico, nota
sobre bloques; §6.1, punto 1, del short paper). Es una comprobación adicional, todavía fuera del notebook 04.
Resultado principal: Norte a 1 h, −21.6 MW, IC −22.1 a −21.1 (§5.4, tabla).
