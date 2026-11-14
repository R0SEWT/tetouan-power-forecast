# Plan de juego: RITE en la serie de PR y el protocolo con personas

Sale de [`juego.md`](juego.md): la investigación sobre cómo valida la industria del videojuego, las medidas M1–M12 y la
línea base del playtest sintético. No reemplaza a [`plan.md`](plan.md) (los PR 1–16 y sus umbrales): le agrega un
ciclo de validación por PR, las mejoras que sugiere el playtest y el protocolo para repetirlo con personas.

## 1. El ciclo RITE en la serie de PR

RITE (Medlock et al., 2002) corrige **entre una sesión y la siguiente** apenas un problema es claro, en lugar de juntar
todo para un informe final. En la serie de PR queda así:

```
   ┌────────────────────────────────────────────────────────────────────────────────────┐
   │ 1. Playtest de la punta: las sesiones que toca el PR (5 personas × 3 repeticiones)  │
   │ 2. El tropiezo de mayor puntaje (frecuencia × severidad) que el PR puede arreglar   │
   │ 3. El cambio mínimo que lo ataca, con su medida y su umbral fijados antes           │
   │ 4. Volver a jugar las mismas sesiones + las guardas de plan.md                      │
   │ 5. ¿La medida supera el ruido y ninguna guarda empeora? Sí → PR. No → revertir y    │
   │    anotar «probado y descartado» con cifras                                          │
   └────────────────────────────────────────────────────────────────────────────────────┘
        cada 2–3 PR: una ronda de 5 personas (§3) sobre la punta, con el mismo guion
```

- **Qué se juega en cada PR.** Solo las sesiones de las pantallas que toca: un cambio en «Ahora» juega
  `entrada-hoy`, `entrada-1030` y `entrada-1900` (45 sesiones, unos 20 minutos con 4 en paralelo); uno en «Confianza»,
  `confianza` (15 sesiones, unos 7 minutos). El resto se juega al cierre de la serie.
- **Cuándo cuenta una diferencia.** Si los rangos entre repeticiones no se solapan (`analizar.py antes después`).
  Las sesiones de «Detalle» (`escenarios`, `escenario-2c`), donde los PR 1–4 solo cambiaron palabras, sirven de
  control parcial: su primer clic y su lectura no se movieron (100 % en las dos versiones) y sus términos no entendidos
  bajaron poco (−0.3 y −0.4 por sesión), como se esperaba del PR 4.
- **Qué va en el PR.** Además de lo que pide [`plan.md`](plan.md): la tabla antes/después de la medida del playtest,
  el tropiezo atacado con su evidencia textual y el embudo afectado. Lo descartado, con cifras, como en myPage.
- **Lo que el playtest no decide.** Si alguien volvería mañana (M11) o si entiende de verdad una cifra: eso lo decide la
  ronda con personas. Si el playtest y las personas discrepan, mandan las personas y se anota la discrepancia para
  calibrar el instrumento.
- **Dónde encaja con los PR de [`plan.md`](plan.md).** Antes del PR 5: la primera ronda con personas (L8), con la
  punta actual (la de los PR 1–4) y este guion. Después del PR 8 (apertura guiada): la segunda.

## 2. Las mejoras que sugieren el playtest y la investigación

Ocho, en el orden en que conviene atacarlas (puntaje del tropiezo, costo y dependencia). Cada una con su medida del
playtest (base = la punta, [`juego.md`](juego.md) §5) y su umbral, fijado aquí antes de probar. Donde coincide con un PR
de [`plan.md`](plan.md), se dice; las demás son nuevas y se proponen para esa tabla (este PR no la toca).

| # | Mejora | Tropiezo / idea | Medida: base → umbral | Relación con `plan.md` |
|---|---|---|---|---|
| J1 | **«¿Y si hace más calor?» también en vivo**: el enlace en la respuesta de hoy, hacia los escenarios del último día con modelo (o, cuando exista, un escenario sobre el pronóstico vivo) | Tropiezo 1 (sev. 4, 15 de 15) | Primer clic de T3 desde hoy: 0 % → ≥ 80 %, con «no sabe» ≤ 10 %. Ensayo: 0 → 100 % | Nueva; cabe antes del PR 5 (es una línea) |
| J2 | **El chip de El Niño deja de mentir**: o es un enlace a «Confianza» que dice a dónde lleva («¿cuándo se equivoca más? →»), o deja de verse como pastilla | Tropiezo 2 (sev. 3, 15 de 15) | Falsas affordances en T4: 15 de 15 → 0; primer clic de T4 desde las tres entradas: 0 % → ≥ 80 %. Ensayo (como enlace): 0 → 100 % | Nueva; junto con J1 |
| J3 | **De madrugada, decir qué hora es de verdad**: entre la medianoche y la publicación del día, «Ahora» no marca una hora de hace un día; el gráfico se titula con sus fechas, y «emitido» y «reconstruido» se explican una vez | Tropiezo 3 | Sesiones de madrugada que dudan en «Lo que dijimos ayer» o en el párrafo de modo: 12 de 15 → ≤ 3; «sabe qué momento muestra» (que hoy depende de cómo lea «Hoy») 100 % con imagen y en solo texto | Completa el PR 2 (que ya agregó el aviso de «todavía no llega») |
| J4 | **Fecha dd/mm/aaaa y hora de 24 h** | Tropiezo 4; lo que más piden cambiar | Sesiones que dudan en los controles de fecha y hora: 11 de 15 (hoy) y 10 de 15 (19:00) → ≤ 2; «que_cambiarias» que mencionen la fecha → 0 | **Es el PR 6**: el playtest le agrega la medida |
| J5 | **«Detalle» con un solo modelo a la vista en los escenarios**: el panel dice qué modelo calcula el escenario, o los escenarios se mudan a «Ahora» con su propio modelo; una sola cifra de cambio | Tropiezo 5 (15 de 15 sesiones) | Sesiones que dudan en el panel de controles: 15 de 15 en `escenarios` y en `escenario-2c` → ≤ 3 | Entra en el **PR 13** (fundir «Detalle»), decisión del dueño |
| J6 | **Los nombres del modelo fuera del camino**: «Chronos-2», «Simons», «IEOD» pasan a una ficha técnica plegada; en la primera pantalla, «el pronóstico» | Jerga persistente pese al PR 4 | Términos no entendidos por sesión en las entradas: 3.1–3.4 → ≤ 2; «Chronos-2» citado: 12 de 15 → ≤ 3 | Sigue al PR 4 (que las definió: definir no bastó) |
| J7 | **«Confianza» sin referencias que nadie conoce**: PJM y Elia, con una frase de quiénes son o en una nota; MAE/MAPE/WAPE como «error medio en MW» y «en %» | Severidad 1, pero 15 de 15 | Términos en «Confianza»: 3.4 → ≤ 2; PJM/Elia citados: 15 de 15 → ≤ 3 | Junto con el **PR 10** (confianza de un vistazo) |
| J8 | **Lo que hace volver, a la vista**: «Lo que dijimos ayer» en el recorrido (bucle de un día) y el CSV con la demanda real | Lo que les importó: la rendición de cuentas (60 %); lo que pidieron Diego y Luis | Con personas (M11): de cinco, cuántos dicen para qué la abrirían mañana; en el playtest, solo como pista: «le importó la rendición de cuentas» ≥ 60 % en las tres entradas | **PR 9** («Lo que dijimos ayer» en el recorrido); el CSV, nuevo |

**Las tres primeras que haría:** J1 y J2 juntas (los dos tropiezos más graves, una línea cada uno, y el ensayo ya
mostró que el instrumento las ve) y J4 (el PR 6, que es lo que todos los perfiles piden). J3 va después, porque toca
el modo en vivo y conviene medirlo de madrugada y de día.

**Lo que no se propone** (sería maquillaje, [`juego.md`](juego.md) §1.6): rachas de días, insignias, celebraciones
cuando el pronóstico acierta o recordatorios para volver. Para Rosa, que quiere saber si «la luz va a alcanzar», la
respuesta no es un juego sino el nivel Ciudadano del concepto C ([`onboarding.md`](onboarding.md)), decisión del dueño.

## 3. El protocolo de 30 minutos con cinco personas

Lo sintético encuentra candidatos; esto los confirma o los descarta. Mismo guion, mismas tareas y mismos códigos que el
playtest sintético, para que la comparación sea directa («¿el tropiezo que vio el evaluador lo vio también una
persona?»).

**Quiénes.** Cinco personas que no conocen Curva, una por perfil del playtest: alguien sin formación técnica, un
estudiante de ingeniería, alguien que opere o planifique la red, alguien que escriba o comunique con datos y un
docente. Personas nuevas en cada ronda para la primera apertura (los jugadores «de un solo uso» de Schell).

**Qué se necesita.** Una laptop con la app de la punta a 1366×768 (o el celular de la persona si ese es su uso), la
URL raíz abierta en otra pestaña oculta, el repaso del 10-mar-2026 a las 19:00 en otra; un moderador y un anotador;
la hoja de registro ([`juego/hoja-de-registro.csv`](juego/hoja-de-registro.csv)); un cronómetro; papel para la curva
de interés.

**Datos personales.** Al mínimo: un código (P1–P5) y el perfil, sin nombre, correo ni grabación de la cara. Si se
graba la pantalla, se avisa antes y se borra al pasar las notas a la hoja.

| Minuto | Bloque | Qué hace el moderador | Qué se anota |
|---|---|---|---|
| 0–2 | Bienvenida | «Probamos la aplicación, no a ti. No hay respuestas malas. Piensa en voz alta; yo no voy a ayudarte, pero al final te explico todo.» Consentimiento verbal | Código, perfil, dispositivo |
| 2–4 | **Prueba de 5 segundos** | Muestra la URL raíz 5 s y la oculta. «¿Qué era? ¿Para qué sirve? ¿Qué cifra recuerdas?» | M1 (dice qué es) y lo que recuerda, textual |
| 4–7 | **Primer clic** (sin ejecutar) | Vuelve a mostrar la pantalla. Para cada consigna de `tareas.json` (T1, T2, T4 desde la raíz; T3 desde el repaso): «¿Dónde tocarías primero?» Solo señala | Texto del elemento, acierto/aceptable/equivocado/no es control/no sabe, segundos hasta señalar (M5, M6) |
| 7–21 | **Tareas en voz alta** | Ahora sí hace las cuatro tareas, 3 min como máximo cada una. Si en 60 s no avanza: «¿qué buscas?»; si sigue, se anota bloqueo y se le muestra el camino. No se corrige ni se elogia | Pasos, dudas (dónde, qué), palabras, lectura copiada y si es correcta, completó sin ayuda, segundos (M3, M8, M9, M10) |
| 21–24 | **Lecturas** | En el repaso de las 19:00: «¿Cuánto se pronosticó y cuánto fue? ¿Qué quiere decir el rango?» | M2, M3 y si entiende «8 de cada 10 veces» |
| 24–27 | **Curva de interés** | «Dibuja una línea: arriba cuando te interesó, abajo cuando te perdiste» (Schell) | Foto del papel; los dos puntos más bajos |
| 27–30 | **Cierre** | «¿La abrirías mañana? ¿Para qué? ¿Qué cambiarías primero?» Facilidad de cada tarea de 1 a 7. Explicación y gracias | M11, citas breves |

**Después de cada sesión (RITE).** Moderador y anotador revisan la hoja en 10 minutos: los tropiezos de severidad 3–4
con un arreglo evidente se corrigen antes de la siguiente sesión, y se anota en qué sesión entró cada cambio. Al final
de la ronda, la hoja se codifica con las mismas categorías de `analizar.py` y se compara con el playtest sintético de
la misma versión: tropiezos confirmados, nuevos y los que solo vio el evaluador.

**La hoja de registro** tiene una fila por bloque y tarea: `sesion, participante, perfil, dispositivo, ronda, version,
bloque, tarea, paso, pantalla, primer_clic_texto, resultado_clic, segundos_al_primer_clic, lectura_copiada,
lectura_correcta, completo_sin_ayuda, segundos_tarea, facilidad_1a7, duda_donde, duda_que, palabras_no_entendidas,
tipo_tropiezo, severidad_1a4, cita_breve, notas`. Los valores de `resultado_clic`, `tipo_tropiezo` y `severidad` son
los de [`juego.md`](juego.md) §3.
