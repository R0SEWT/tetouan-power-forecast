# Playtest sintético: develop (imagen)

Capturas de 2026-11-14 02:11 (Lima). Sesiones válidas: 90; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

## Primera apertura

| Medida | entrada-1030 | entrada-1900 | entrada-hoy |
|---|---|---|---|
| Dice qué es | 93 % (80–100) | 100 % | 93 % (80–100) |
| Sabe qué momento muestra | 100 % | 100 % | 100 % |
| Lee la cifra del momento | 100 % | 100 % | 100 % |
| Lee cifra, pronóstico y rango | 100 % | 100 % | 100 % |
| Lo primero que mira es la cifra o la respuesta | 0 % | 0 % | 0 % |
| Primer clic acertado (media de 4 tareas) | 75 % | 75 % | 50 % |
| …t1 | 100 % | 100 % | 100 % |
| …t2 | 100 % | 100 % | 100 % |
| …t3 | 100 % | 100 % | 0 % |
| …t4 | 0 % | 0 % | 0 % |
| Dudas por sesión | 3.4 (3.2–3.6) | 3.4 (3.2–3.6) | 3.7 (3.4–3.8) |
| Marcadores de confusión en la voz alta | 1.1 (0.8–1.4) | 1.3 (1.0–1.8) | 0.9 (0.6–1.0) |
| Términos no entendidos por sesión | 5.1 (5.0–5.2) | 5.4 (5.2–5.6) | 4.0 (4.0–4.0) |
| Volvería mañana (sí o tal vez) | 87 % (80–100) | 80 % | 80 % |

**Embudo, entrada-1030:** abre la pantalla 15/15 → dice qué es 14/15 → lee la cifra del momento 14/15 → sabe qué momento muestra 14/15 → acierta el primer clic en 3 de 4 tareas 14/15 → volvería mañana (sí o tal vez) 13/15.
Términos más citados: El Niño costero / ICEN (93 %), Simons (componente del modelo) (93 %), Chronos-2 / modelo fundacional (80 %), IEOD (67 %), COES (40 %), SEIN (40 %).
Dudas por zona: chip de El Niño (15), «De dónde sale» (pie) (9), tarjetas de cifras (6), controles de fecha y hora (6), marca (5), «Lo que dijimos ayer» (4).
Mira primero: título (14), selector de área (1).
Le importó: el pico y la hora de más consumo (40 %), rendición de cuentas (acertó, cuánto se equivoca) (40 %), la cifra de ahora (20 %), los datos para descargar (13 %), nada (7 %).
Acuerdo entre repeticiones: {'comprende': 0.8, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

**Embudo, entrada-1900:** abre la pantalla 15/15 → dice qué es 15/15 → lee la cifra del momento 15/15 → sabe qué momento muestra 15/15 → acierta el primer clic en 3 de 4 tareas 15/15 → volvería mañana (sí o tal vez) 12/15.
Términos más citados: Simons (componente del modelo) (100 %), El Niño costero / ICEN (93 %), Chronos-2 / modelo fundacional (80 %), IEOD (67 %), modelo / híbrido / XGBoost (53 %), COES (40 %).
Dudas por zona: chip de El Niño (14), «De dónde sale» (pie) (14), controles de fecha y hora (8), tarjetas de cifras (4), #ahPie (3), otras cifras (2).
Mira primero: título (14), selector de área (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (53 %), el pico y la hora de más consumo (27 %), los datos para descargar (27 %), la cifra de ahora (20 %).
Acuerdo entre repeticiones: {'comprende': 1.0, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

**Embudo, entrada-hoy:** abre la pantalla 15/15 → dice qué es 14/15 → lee la cifra del momento 14/15 → sabe qué momento muestra 14/15 → acierta el primer clic en 3 de 4 tareas 0/15 → volvería mañana (sí o tal vez) 0/15.
Términos más citados: El Niño costero / ICEN (100 %), Chronos-2 / modelo fundacional (80 %), IEOD (80 %), COES (40 %), SEIN (40 %), CSV (20 %).
Dudas por zona: chip de El Niño (13), «Lo que dijimos ayer» (11), selector de área (6), controles de fecha y hora (6), tarjetas de cifras (3), párrafo de modo (3).
Mira primero: título (14), selector de área (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (40 %), el pico y la hora de más consumo (33 %), los datos para descargar (27 %), la cifra de ahora (20 %), nada (7 %).
Acuerdo entre repeticiones: {'comprende': 0.8, 'lectura_cifra': 1.0, 'clic_t1': 1.0, 'clic_t2': 1.0, 'clic_t3': 1.0, 'clic_t4': 1.0}.

## Pasos siguientes

| Pantalla | Medida | Valor | Dudas / sesión | Términos / sesión |
|---|---|---|---|---|
| confianza | t2_ok | 100 % | 3.1 (2.8–3.6) | 3.7 (3.6–3.8) |
| confianza | t4_ok | 100 % | 3.1 (2.8–3.6) | 3.7 (3.6–3.8) |
| escenario-2c | t3_lectura_ok | 100 % | 2.7 (2.4–3.0) | 3.4 (3.4–3.4) |
| escenarios | t3_clic_ok | 100 % | 1.9 (1.8–2.0) | 3.2 (3.2–3.2) |

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 15/15 → lee lo pronosticado, el rango y lo real (repaso 19:00) 15/15
- **t2**: primer clic desde hoy 15/15 → lee el error y la comparación (Confianza) 15/15
- **t3**: primer clic desde el repaso de las 19:00 15/15 → toca +2 °C 15/15 → lee el cambio 15/15
- **t4**: primer clic desde hoy 0/15 → lee el régimen con más error (Confianza) 0/15

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| hoy | t3 primer clic | no sabe qué tocar | — | 4 | 100 % | 5 | No veo ninguna parte donde hable de temperatura, calor o grados centígrados en toda la pantalla, así que no sé qué tocar. |
| hoy | t4 primer clic | toca algo que no es control | El Niño costero: extraordinario · ICEN 3 | 3 | 100 % | 5 | Es el único elemento de la pantalla donde se menciona a El Niño. Probaría tocar esa etiqueta para ver si desglosa el error según eventos de El Niño, … |
| repaso-1900 | t4 primer clic | toca algo que no es control | El Niño costero: extraordinario · ICEN 3 | 3 | 80 % | 5 | Tocaría esa pastilla gris porque es el único sitio donde leo las palabras 'El Niño', aunque parece solo un texto y no sé si se puede presionar ni … |
| repaso-1030 | t4 primer clic | toca algo que no es control | El Niño costero: extraordinario · ICEN 3 | 3 | 67 % | 5 | Es el único elemento que menciona a El Niño en la pantalla, aunque parece una etiqueta informativa y no sé si permite filtrar o ver el error. |
| repaso-1030 | t4 primer clic | no sabe qué tocar | — | 4 | 33 % | 3 | No veo ninguna opción ni botón para evaluar el error según la fase de El Niño. La etiqueta superior parece meramente informativa y en la vista 2 se … |
| confianza | palabra | palabra | PJM / Elia (referencias externas) | 1 | 100 % | 5 | PJM / Elia (referencias externas) |
| repaso-1030 | duda | duda | chip de El Niño | 1 | 100 % | 5 | No entiendo qué es 'ICEN 3.38' ni por qué dice 'jul-2026' si la pantalla está mostrando datos del 10 de marzo de 2026. |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| hoy | palabra | palabra | El Niño costero / ICEN | 1 | 100 % | 5 | El Niño costero / ICEN |
| escenario-2c | duda | duda | panel de controles de «Detalle» | 1 | 100 % | 5 | A la izquierda tengo marcado «Solo demanda» y «Combinado (recomendado)», pero este aviso me dice que ese modelo no responde al clima y que el escenario lo calcu |
| escenarios | duda | duda | panel de controles de «Detalle» | 1 | 100 % | 5 | Me hace dudar si al presionar +2 °C el sistema hace el cálculo automáticamente o si antes tengo que cambiar de modelo en el panel izquierdo, donde dice … |
| repaso-1030 | palabra | palabra | El Niño costero / ICEN | 1 | 93 % | 5 | El Niño costero / ICEN |
| repaso-1030 | palabra | palabra | Simons (componente del modelo) | 1 | 93 % | 5 | Simons (componente del modelo) |
| repaso-1900 | duda | duda | chip de El Niño | 1 | 93 % | 5 | No conozco qué es el ICEN ni por qué indica julio de 2026 si la fecha mostrada es marzo de 2026, ni si es un botón o solo … |
| repaso-1900 | palabra | palabra | El Niño costero / ICEN | 1 | 93 % | 5 | El Niño costero / ICEN |
| hoy | duda | duda | chip de El Niño | 1 | 87 % | 5 | No sé qué significa ICEN 3.38 ni qué tiene que ver El Niño con la luz, ni por qué pone jul-2026 si la fecha dice noviembre. |
| escenario-2c | duda | duda | panel de escenarios | 1 | 87 % | 5 | Tengo dos cifras de cambio y dudo sobre cuál llevar al titular: si los 15 MW de las 11:00 (pico de demanda) o los 25 MW de las … |
| repaso-1900 | t4 primer clic | no sabe qué tocar | — | 4 | 20 % | 3 | Aquí me pierdo. Arriba veo una etiqueta gris que dice 'El Niño costero: extraordinario', pero no parece un botón y no veo nada que me diga en qué … |
| confianza | duda | duda | cobertura | 1 | 80 % | 5 | No entiendo qué tiene que ver Bélgica o quién es Elia si esto se supone que es sobre la luz en Lima. |
| confianza | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
