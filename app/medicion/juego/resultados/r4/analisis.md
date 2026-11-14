# Playtest sintético: r4 (imagen)

Capturas de 2026-11-14 04:52 (Lima). Sesiones válidas: 12; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

## Primera apertura

| Medida | entrada-1030 | entrada-1900 | entrada-hoy |
|---|---|---|---|
| Dice qué es | 100 % | 100 % | 100 % |
| Sabe qué momento muestra | 100 % | 100 % | 20 % |
| Lee la cifra del momento | 100 % | 100 % | 100 % |
| Lee cifra, pronóstico y rango | 100 % | 100 % | 100 % |
| Lo primero que mira es la cifra o la respuesta | 0 % | 0 % | 0 % |
| Primer clic acertado (media de 4 tareas) | 100 % | 100 % | 100 % |
| …t1 | 100 % | 100 % | 100 % |
| …t2 | 100 % | 100 % | 100 % |
| …t3 | 100 % | 100 % | 100 % |
| …t4 | 100 % | 100 % | 100 % |
| Dudas por sesión | 2.6 (2.6–2.6) | 3.0 (3.0–3.0) | 2.6 (2.6–2.6) |
| Marcadores de confusión en la voz alta | 0.4 (0.4–0.4) | 1.5 (1.5–1.5) | 0.6 (0.6–0.6) |
| Términos no entendidos por sesión | 4.2 (4.2–4.2) | 5.0 (5.0–5.0) | 2.2 (2.2–2.2) |
| Volvería mañana (sí o tal vez) | 80 % | 50 % | 80 % |

**Embudo, entrada-1030:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 5/5 → acierta el primer clic en 3 de 4 tareas 5/5 → volvería mañana (sí o tal vez) 4/5.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (80 %), IEOD (80 %), modelo / híbrido / XGBoost (80 %), COES (40 %), CSV (20 %).
Dudas por zona: controles de fecha y hora (3), respuesta a la pregunta (2), «De dónde sale» (pie) (2), respuesta a la pregunta (1), #ahGrafSub (1), leyenda del gráfico (1).
Mira primero: línea de «ahora» (4), controles de fecha y hora (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (40 %), la cifra de ahora (40 %), los datos para descargar (20 %), el pico y la hora de más consumo (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

**Embudo, entrada-1900:** abre la pantalla 2/2 → dice qué es 2/2 → lee la cifra del momento 2/2 → sabe qué momento muestra 2/2 → acierta el primer clic en 3 de 4 tareas 2/2 → volvería mañana (sí o tal vez) 1/2.
Términos más citados: Chronos-2 / modelo fundacional (100 %), IEOD (100 %), Simons (componente del modelo) (100 %), COES (50 %), CSV (50 %), MW / megavatios (50 %).
Dudas por zona: línea de «ahora» (1), respuesta a la pregunta (1), respuesta a la pregunta (1), #ahGrafTitulo (1), controles de fecha y hora (1), «De dónde sale» (pie) (1).
Mira primero: línea de «ahora» (2).
Le importó: los datos para descargar (50 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

**Embudo, entrada-hoy:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 1/5 → acierta el primer clic en 3 de 4 tareas 1/5 → volvería mañana (sí o tal vez) 1/5.
Términos más citados: Chronos-2 / modelo fundacional (80 %), COES (40 %), SEIN (40 %), CSV (20 %), MW / megavatios (20 %), sesgo / subestima (20 %).
Dudas por zona: título (4), #ahAcierto (3), «¿Qué tan bueno es?» (2), respuesta a la pregunta (1), respuesta a la pregunta (1), controles de fecha y hora (1).
Mira primero: línea de «ahora» (4), título (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (40 %), los datos para descargar (20 %), el pico y la hora de más consumo (20 %), la cifra de ahora (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 2/2 → lee lo pronosticado, el rango y lo real (repaso 19:00) 2/2
- **t2**: primer clic desde hoy 0/0 → lee el error y la comparación (Confianza) 0/0
- **t3**: primer clic desde el repaso de las 19:00 0/0 → toca +2 °C 0/0 → lee el cambio 0/0
- **t4**: primer clic desde hoy 0/0 → lee el régimen con más error (Confianza) 0/0

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| hoy | momento | confunde el momento | dia_pasado | 3 | 80 % | 4 | Habla de un día pasado. Aunque el título arriba pregunta por 'hoy, sábado 14', el último dato real que muestra es del jueves 12 a las 23:30 (4,456 … |
| repaso-1030 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| repaso-1900 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 100 % | 2 | Chronos-2 / modelo fundacional |
| repaso-1900 | palabra | palabra | IEOD | 1 | 100 % | 2 | IEOD |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 2 | Simons (componente del modelo) |
| repaso-1030 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| repaso-1030 | palabra | palabra | IEOD | 1 | 80 % | 4 | IEOD |
| repaso-1030 | palabra | palabra | modelo / híbrido / XGBoost | 1 | 80 % | 4 | modelo / híbrido / XGBoost |
| hoy | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| hoy | duda | duda | título | 1 | 80 % | 4 | El titular me habla de hoy sábado 14, pero el texto aclara que el pronóstico de hoy recién sale a las 10:00 y lo que se muestra abajo … |
| repaso-1030 | duda | duda | controles de fecha y hora | 1 | 60 % | 3 | La pantalla indica que la hora consultada es las 10:30, pero en el gráfico aparece una línea con la etiqueta 'Real (COES) hasta las 11:00', lo que confunde … |
| hoy | duda | duda | #ahAcierto | 1 | 60 % | 3 | No entiendo bien a qué se refiere con que el pronóstico se 'reconstruyó después'; si ya sabían el dato real, me hace dudar de si es un pronóstico … |
| repaso-1900 | duda | duda | línea de «ahora» | 1 | 50 % | 1 | No sé qué es MW ni qué significa esa cantidad tan grande; en mi casa solo conozco los kWh de mi recibo de luz. |
| repaso-1900 | duda | duda | respuesta a la pregunta | 1 | 50 % | 1 | No sé qué empresa o entidad es el COES ni qué cosa son megavatios. |
| repaso-1900 | duda | duda | respuesta a la pregunta | 1 | 50 % | 1 | Parece una fórmula matemática de universidad con palabras en inglés y números raros que no entiendo nada. |
| repaso-1900 | duda | duda | #ahGrafTitulo | 1 | 50 % | 1 | El gráfico tiene muchas curvas y líneas de colores que se cruzan y me marean, no sé cuál línea debo mirar. |
| repaso-1900 | palabra | palabra | COES | 1 | 50 % | 1 | COES |
| repaso-1900 | palabra | palabra | CSV | 1 | 50 % | 1 | CSV |
| repaso-1900 | palabra | palabra | MW / megavatios | 1 | 50 % | 1 | MW / megavatios |
| repaso-1900 | palabra | palabra | modelo / híbrido / XGBoost | 1 | 50 % | 1 | modelo / híbrido / XGBoost |
