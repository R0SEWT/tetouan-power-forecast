# Playtest sintético: r0 (imagen)

Capturas de 2026-11-14 04:41 (Lima). Sesiones válidas: 50; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

## Primera apertura

| Medida | entrada-1030 | entrada-1900 | entrada-hoy |
|---|---|---|---|
| Dice qué es | 100 % | 100 % | 100 % |
| Sabe qué momento muestra | 100 % | 100 % | 100 % |
| Lee la cifra del momento | 100 % | 100 % | 100 % |
| Lee cifra, pronóstico y rango | 100 % | 100 % | 100 % |
| Lo primero que mira es la cifra o la respuesta | 0 % | 0 % | 0 % |
| Primer clic acertado (media de 4 tareas) | 75 % | 75 % | 50 % |
| …t1 | 100 % | 100 % | 100 % |
| …t2 | 100 % | 100 % | 100 % |
| …t3 | 100 % | 100 % | 0 % |
| …t4 | 0 % | 0 % | 0 % |
| Dudas por sesión | 3.4 (3.4–3.4) | 3.0 (3.0–3.0) | 2.9 (2.4–3.4) |
| Marcadores de confusión en la voz alta | 1.3 (1.2–1.4) | 0.7 (0.6–0.8) | 0.6 (0.6–0.6) |
| Términos no entendidos por sesión | 4.2 (4.0–4.4) | 3.9 (3.8–4.0) | 2.8 (2.6–3.0) |
| Volvería mañana (sí o tal vez) | 90 % (80–100) | 80 % | 80 % |

**Embudo, entrada-1030:** abre la pantalla 10/10 → dice qué es 10/10 → lee la cifra del momento 10/10 → sabe qué momento muestra 10/10 → acierta el primer clic en 3 de 4 tareas 10/10 → volvería mañana (sí o tal vez) 9/10.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (80 %), IEOD (70 %), modelo / híbrido / XGBoost (70 %), COES (30 %), CSV (20 %).
Dudas por zona: chip de El Niño (9), respuesta a la pregunta (6), «De dónde sale» (pie) (4), controles de fecha y hora (3), #ahGrafTitulo (2), navegación (Ahora · Confianza · Detalle) (2).
Mira primero: línea de «ahora» (9), controles de fecha y hora (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (30 %), los datos para descargar (20 %), la cifra de ahora (20 %).
Acuerdo entre repeticiones: {'comprende': 1.0, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

**Embudo, entrada-1900:** abre la pantalla 10/10 → dice qué es 10/10 → lee la cifra del momento 10/10 → sabe qué momento muestra 10/10 → acierta el primer clic en 3 de 4 tareas 10/10 → volvería mañana (sí o tal vez) 8/10.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (80 %), IEOD (70 %), modelo / híbrido / XGBoost (70 %), COES (40 %), MW / megavatios (20 %).
Dudas por zona: chip de El Niño (8), respuesta a la pregunta (7), controles de fecha y hora (4), respuesta a la pregunta (2), #ahPie (2), #ahDespues (2).
Mira primero: línea de «ahora» (9), controles de fecha y hora (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (60 %), nada (20 %), los datos para descargar (20 %), la cifra de ahora (10 %).
Acuerdo entre repeticiones: {'comprende': 1.0, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

**Embudo, entrada-hoy:** abre la pantalla 10/10 → dice qué es 10/10 → lee la cifra del momento 10/10 → sabe qué momento muestra 10/10 → acierta el primer clic en 3 de 4 tareas 0/10 → volvería mañana (sí o tal vez) 0/10.
Términos más citados: Chronos-2 / modelo fundacional (80 %), IEOD (70 %), COES (40 %), SEIN (40 %), CSV (20 %), MW / megavatios (20 %).
Dudas por zona: «Lo que dijimos ayer» (7), controles de fecha y hora (6), chip de El Niño (3), #ahLeyRango (2), «De dónde sale» (pie) (2), línea de «ahora» (1).
Mira primero: línea de «ahora» (8), título (2).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (50 %), el pico y la hora de más consumo (30 %), la cifra de ahora (20 %), los datos para descargar (20 %), nada (10 %).
Acuerdo entre repeticiones: {'comprende': 1.0, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

## Pasos siguientes

| Pantalla | Medida | Valor | Dudas / sesión | Términos / sesión |
|---|---|---|---|---|
| escenario-2c | t3_lectura_ok | 100 % | 2.2 (2.2–2.2) | 3.0 (3.0–3.0) |
| escenarios | t3_clic_ok | 100 % | 2.1 (2.0–2.2) | 3.0 (3.0–3.0) |

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 10/10 → lee lo pronosticado, el rango y lo real (repaso 19:00) 10/10
- **t2**: primer clic desde hoy 0/0 → lee el error y la comparación (Confianza) 0/0
- **t3**: primer clic desde el repaso de las 19:00 10/10 → toca +2 °C 10/10 → lee el cambio 10/10
- **t4**: primer clic desde hoy 0/0 → lee el régimen con más error (Confianza) 0/0

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| hoy | t3 primer clic | no sabe qué tocar | — | 4 | 100 % | 5 | No hay ningún botón, menú ni barra para ingresar temperatura o simular calor en toda la pantalla; no sé dónde se haría. |
| repaso-1030 | t4 primer clic | toca algo que no es control | El Niño costero (calentamiento del mar f | 3 | 100 % | 5 | Es el único lugar de la pantalla donde se menciona a El Niño; probaría tocar esa etiqueta para ver si muestra el desglose del error según la condición … |
| hoy | t4 primer clic | toca algo que no es control | El Niño costero (calentamiento del mar f | 3 | 100 % | 5 | Es el único lugar donde se menciona El Niño; tocaría esa etiqueta para ver si me permite filtrar por otros escenarios o ver el error bajo ese fenómeno, … |
| repaso-1900 | t4 primer clic | toca algo que no es control | El Niño costero (calentamiento del mar f | 3 | 80 % | 5 | Es el único lugar de toda la pantalla donde se menciona a El Niño, así que probaría si esa pastilla gris se puede cliquear para ver otros escenarios, … |
| repaso-1030 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| escenario-2c | duda | duda | panel de controles de «Detalle» | 1 | 100 % | 5 | En la barra izquierda dice que el modelo elegido es «Combinado (recomendado)» y que no distingue clima ni El Niño, pero esta alerta dice que el escenario lo … |
| escenarios | duda | duda | panel de controles de «Detalle» | 1 | 100 % | 5 | No entiendo qué es modelo combinado ni XGBoost, y me hace dudar si al tocar la temperatura va a cambiar algo o si tengo que configurar otra cosa. |
| repaso-1030 | duda | duda | chip de El Niño | 1 | 90 % | 5 | No sé si es un botón o filtro que puedo presionar para cambiar la condición climática, o si es solo una etiqueta de texto informativo. |
| repaso-1900 | t4 primer clic | no sabe qué tocar | — | 4 | 20 % | 2 | No veo ninguna opción ni botón que muestre los errores según las situaciones de El Niño; solo hay una etiqueta fija que dice «El Niño costero (calentamiento del |
| repaso-1030 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| repaso-1900 | duda | duda | chip de El Niño | 1 | 80 % | 5 | No me queda claro si esa pastilla es un botón que se puede tocar para cambiar de escenario o si es solo un texto informativo. |
| repaso-1900 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| hoy | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| escenario-2c | duda | duda | panel de escenarios | 1 | 80 % | 5 | Aparecen dos datos de cambio distintos: 15 MW más a las 11:00 (en la hora pico) y +25 MW a las 15:30 (el mayor cambio absoluto), así que … |
| escenario-2c | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| escenario-2c | palabra | palabra | modelo / híbrido / XGBoost | 1 | 80 % | 4 | modelo / híbrido / XGBoost |
| escenarios | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| escenarios | palabra | palabra | modelo / híbrido / XGBoost | 1 | 80 % | 4 | modelo / híbrido / XGBoost |
| repaso-1030 | palabra | palabra | IEOD | 1 | 70 % | 4 | IEOD |
