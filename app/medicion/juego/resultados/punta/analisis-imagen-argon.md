# Playtest sintético: punta (imagen-argon)

Capturas de 2026-11-14 02:11 (Lima). Sesiones válidas: 44; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

## Primera apertura

| Medida | entrada-1030 | entrada-1900 | entrada-hoy |
|---|---|---|---|
| Dice qué es | 90 % (80–100) | 100 % | 100 % |
| Sabe qué momento muestra | 100 % | 100 % | 100 % |
| Lee la cifra del momento | 100 % | 100 % | 100 % |
| Lee cifra, pronóstico y rango | 100 % | 100 % | 100 % |
| Lo primero que mira es la cifra o la respuesta | 50 % (40–60) | 67 % (50–80) | 40 % |
| Primer clic acertado (media de 4 tareas) | 100 % | 94 % (94–95) | 68 % (65–70) |
| …t1 | 100 % | 100 % | 100 % |
| …t2 | 100 % | 100 % | 100 % |
| …t3 | 100 % | 100 % | 30 % (20–40) |
| …t4 | 100 % | 78 % (75–80) | 40 % |
| Dudas por sesión | 4.1 (4.0–4.2) | 4.4 (4.0–4.8) | 5.1 (5.0–5.2) |
| Marcadores de confusión en la voz alta | 0.7 (0.4–1.0) | 0.8 (0.6–1.0) | 0.9 (0.8–1.0) |
| Términos no entendidos por sesión | 3.7 (3.2–4.2) | 3.6 (3.4–3.8) | 3.5 (3.4–3.6) |
| Volvería mañana (sí o tal vez) | 80 % | 78 % (75–80) | 80 % |

**Embudo, entrada-1030:** abre la pantalla 10/10 → dice qué es 9/10 → lee la cifra del momento 9/10 → sabe qué momento muestra 9/10 → acierta el primer clic en 3 de 4 tareas 9/10 → volvería mañana (sí o tal vez) 8/10.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (90 %), COES (30 %), modelo / híbrido / XGBoost (30 %), CSV (20 %), MW / megavatios (20 %).
Dudas por zona: controles de fecha y hora (11), chip de El Niño (8), navegación (Ahora · Confianza · Detalle) (5), gráfico (5), «De dónde sale» (pie) (5), respuesta a la pregunta (3).
Mira primero: controles de fecha y hora (5), cifra de ahora (5).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (70 %), los datos para descargar (40 %), la cifra de ahora (30 %), el pico y la hora de más consumo (10 %).
Acuerdo entre repeticiones: {'comprende': 0.8, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

**Embudo, entrada-1900:** abre la pantalla 9/9 → dice qué es 9/9 → lee la cifra del momento 9/9 → sabe qué momento muestra 9/9 → acierta el primer clic en 3 de 4 tareas 9/9 → volvería mañana (sí o tal vez) 7/9.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (89 %), modelo / híbrido / XGBoost (33 %), COES (22 %), CSV (22 %), MW / megavatios (22 %).
Dudas por zona: controles de fecha y hora (15), gráfico (5), «De dónde sale» (pie) (5), chip de El Niño (4), «Lo que dijimos ayer» (4), respuesta a la pregunta (3).
Mira primero: cifra de ahora (6), controles de fecha y hora (3).
Le importó: los datos para descargar (44 %), rendición de cuentas (acertó, cuánto se equivoca) (44 %), la cifra de ahora (11 %), el pico y la hora de más consumo (11 %).
Acuerdo entre repeticiones: {'comprende': 1.0, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

**Embudo, entrada-hoy:** abre la pantalla 10/10 → dice qué es 10/10 → lee la cifra del momento 10/10 → sabe qué momento muestra 10/10 → acierta el primer clic en 3 de 4 tareas 6/10 → volvería mañana (sí o tal vez) 6/10.
Términos más citados: Chronos-2 / modelo fundacional (80 %), IEOD (80 %), reconstruido / registro en vivo (40 %), COES (30 %), MW / megavatios (30 %), SEIN (30 %).
Dudas por zona: «Lo que dijimos ayer» (11), controles de fecha y hora (10), respuesta a la pregunta (8), leyenda del gráfico (7), gráfico (5), chip de El Niño (4).
Mira primero: título (6), cifra de ahora (4).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (50 %), el pico y la hora de más consumo (30 %), la cifra de ahora (20 %), los datos para descargar (20 %).
Acuerdo entre repeticiones: {'comprende': 1.0, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 0.4, 'clic_t4': 0.6}.

## Pasos siguientes

| Pantalla | Medida | Valor | Dudas / sesión | Términos / sesión |
|---|---|---|---|---|
| confianza | t2_ok | 100 % | 4.2 (4.2–4.2) | 4.2 (4.2–4.2) |
| confianza | t4_ok | 100 % | 4.2 (4.2–4.2) | 4.2 (4.2–4.2) |
| escenario-2c | t3_lectura_ok | 100 % | 4.2 (4.2–4.2) | 3.8 (3.8–3.8) |
| escenarios | t3_clic_ok | 100 % | 3.4 (3.4–3.4) | 3.6 (3.6–3.6) |

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 9/9 → lee lo pronosticado, el rango y lo real (repaso 19:00) 9/9
- **t2**: primer clic desde hoy 5/5 → lee el error y la comparación (Confianza) 5/5
- **t3**: primer clic desde el repaso de las 19:00 5/5 → toca +2 °C 5/5 → lee el cambio 5/5
- **t4**: primer clic desde hoy 2/5 → lee el régimen con más error (Confianza) 2/5

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| hoy | t3 primer clic | no sabe qué tocar | — | 4 | 70 % | 5 | En ninguna parte habla de temperatura en °C ni veo un simulador de calor; es más, abajo dice que el modelo solo usa la demanda pasada y los … |
| hoy | t4 primer clic | toca algo que no es control | El Niño costero (calentamiento del mar f | 3 | 60 % | 4 | Es el único elemento en toda la pantalla que menciona a El Niño costero, aunque parece una etiqueta informativa más que un botón; si no se pudiera clicar, … |
| confianza | duda | duda | en vivo | 1 | 100 % | 5 | Dice «con el registro en vivo» para el 1 y 2 de noviembre, cuando justo arriba dijo que en vivo solo lleva 1 día desde el viernes 13 … |
| confianza | palabra | palabra | PJM / Elia (referencias externas) | 1 | 100 % | 5 | PJM / Elia (referencias externas) |
| repaso-1030 | duda | duda | controles de fecha y hora | 1 | 100 % | 5 | En toda la página dice martes 10 de marzo y 10/03/2026, pero en el selector de fecha está al revés (mes/día/año, 03/10/2026), lo que confunde al querer elegir … |
| repaso-1030 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| repaso-1900 | duda | duda | controles de fecha y hora | 1 | 100 % | 5 | El título y la etiqueta de arriba dicen 10 de marzo de 2026 (10/03/2026), pero el selector de fecha muestra 03/10/2026 en formato mes/día/año, lo que hace dudar |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| hoy | duda | duda | controles de fecha y hora | 1 | 100 % | 5 | Arriba dice «datos del COES al 12/11, 24:00», pero en la cajita de fecha dice «11/12/2026». En Perú usamos día/mes/año, así que al principio pensé que era 11 … |
| escenario-2c | duda | duda | panel de escenarios | 1 | 100 % | 5 | Da dos cifras de cambio distintas (+15 MW en el pico de las 11:00 y +25 MW como mayor cambio a las 15:30), así que dudo cuál de … |
| escenario-2c | duda | duda | panel de controles de «Detalle» | 1 | 100 % | 5 | A la izquierda siguen seleccionados «Solo demanda» y «Combinado (recomendado)», por lo que confunde ver en la misma pantalla la columna izquierda con un modelo  |
| escenario-2c | palabra | palabra | modelo / híbrido / XGBoost | 1 | 100 % | 5 | modelo / híbrido / XGBoost |
| escenarios | duda | duda | panel de controles de «Detalle» | 1 | 100 % | 5 | Me confunde porque a la izquierda está marcado "Solo demanda" y "Combinado (recomendado)". No sé si tengo que cambiar esos controles primero o si al tocar "+2 ° |
| repaso-1030 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 90 % | 5 | Chronos-2 / modelo fundacional |
| hoy | duda | duda | «Lo que dijimos ayer» | 1 | 90 % | 5 | Arriba decía que el pronóstico fue «emitido ayer a las 10:34», pero aquí dice que fue emitido a las 23:30 (24 h antes). No me queda claro a … |
| repaso-1900 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 89 % | 4 | Chronos-2 / modelo fundacional |
| confianza | duda | duda | cifras de Confianza | 1 | 80 % | 4 | Me da el dato de donde más falla (Niño moderado, 80.6 MW), pero menciona «las 5 fases» y en toda esta página no aparece el desglose de cuáles … |
| confianza | duda | duda | error por día | 1 | 80 % | 4 | No sé qué es PJM ni qué informe es ese para entender por qué se usa ±3 % como referencia. |
| confianza | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| confianza | palabra | palabra | MAE / MAPE / WAPE | 1 | 80 % | 4 | MAE / MAPE / WAPE |
