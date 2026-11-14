# Playtest sintético: r2 (imagen)

Capturas de 2026-11-14 04:48 (Lima). Sesiones válidas: 14; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

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
| Marcadores de confusión en la voz alta | 1.0 (1.0–1.0) | 1.8 (1.8–1.8) | 0.4 (0.4–0.4) |
| Términos no entendidos por sesión | 4.2 (4.2–4.2) | 4.2 (4.2–4.2) | 3.2 (3.2–3.2) |
| Volvería mañana (sí o tal vez) | 80 % | 75 % | 80 % |

**Embudo, entrada-1030:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 5/5 → acierta el primer clic en 3 de 4 tareas 5/5 → volvería mañana (sí o tal vez) 4/5.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (80 %), modelo / híbrido / XGBoost (80 %), IEOD (60 %), COES (40 %), CSV (20 %).
Dudas por zona: controles de fecha y hora (3), #ahOrigenTit (2), respuesta a la pregunta (1), #ahGrafTitulo (1), respuesta a la pregunta (1), #ahDespues (1).
Mira primero: línea de «ahora» (5).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (40 %), los datos para descargar (20 %), la cifra de ahora (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

**Embudo, entrada-1900:** abre la pantalla 4/4 → dice qué es 4/4 → lee la cifra del momento 4/4 → sabe qué momento muestra 4/4 → acierta el primer clic en 3 de 4 tareas 4/4 → volvería mañana (sí o tal vez) 3/4.
Términos más citados: Chronos-2 / modelo fundacional (100 %), Simons (componente del modelo) (100 %), modelo / híbrido / XGBoost (75 %), IEOD (50 %), COES (25 %), CSV (25 %).
Dudas por zona: respuesta a la pregunta (3), controles de fecha y hora (2), respuesta a la pregunta (1), #ahGrafTitulo (1), «Lo que dijimos ayer» (1), navegación (Ahora · Confianza · Detalle) (1).
Mira primero: línea de «ahora» (4).
Le importó: los datos para descargar (25 %), rendición de cuentas (acertó, cuánto se equivoca) (25 %), la cifra de ahora (25 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

**Embudo, entrada-hoy:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 1/5 → acierta el primer clic en 3 de 4 tareas 1/5 → volvería mañana (sí o tal vez) 1/5.
Términos más citados: Chronos-2 / modelo fundacional (80 %), IEOD (80 %), COES (40 %), SEIN (40 %), CSV (20 %), MW / megavatios (20 %).
Dudas por zona: título (5), «Lo que dijimos ayer» (4), respuesta a la pregunta (1), «De dónde sale» (pie) (1), «¿Qué tan bueno es?» (1), marca (1).
Mira primero: línea de «ahora» (4), título (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (60 %), la cifra de ahora (40 %), el pico y la hora de más consumo (40 %), nada (20 %), los datos para descargar (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 4/4 → lee lo pronosticado, el rango y lo real (repaso 19:00) 4/4
- **t2**: primer clic desde hoy 0/0 → lee el error y la comparación (Confianza) 0/0
- **t3**: primer clic desde el repaso de las 19:00 0/0 → toca +2 °C 0/0 → lee el cambio 0/0
- **t4**: primer clic desde hoy 0/0 → lee el régimen con más error (Confianza) 0/0

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| hoy | momento | confunde el momento | dia_pasado | 3 | 80 % | 4 | Habla de un día pasado. Aunque arriba dice hoy sábado 14, dice clarito «Último dato real · jue 12, 23:30» (jueves 12 a las 23:30) y el pronóstico … |
| repaso-1030 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| repaso-1900 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 100 % | 4 | Chronos-2 / modelo fundacional |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 4 | Simons (componente del modelo) |
| hoy | duda | duda | título | 1 | 100 % | 5 | El título grande me pregunta por hoy sábado 14, pero abajo dice jueves 12 y viernes 13; me confunde no saber de qué día me están mostrando los … |
| repaso-1030 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| repaso-1030 | palabra | palabra | modelo / híbrido / XGBoost | 1 | 80 % | 4 | modelo / híbrido / XGBoost |
| hoy | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| hoy | palabra | palabra | IEOD | 1 | 80 % | 4 | IEOD |
| hoy | duda | duda | «Lo que dijimos ayer» | 1 | 80 % | 4 | Me confunde la mezcla de «en vivo» con «reconstruido después de conocerse el real». Como periodista me hace dudar de si fue un pronóstico que se emitió antes … |
| repaso-1900 | duda | duda | respuesta a la pregunta | 1 | 75 % | 3 | Ponen una operación matemática con nombres rarísimos como Chronos y XGBoost que parecen de universidad o de ingenieros. |
| repaso-1900 | palabra | palabra | modelo / híbrido / XGBoost | 1 | 75 % | 3 | modelo / híbrido / XGBoost |
| repaso-1030 | duda | duda | controles de fecha y hora | 1 | 60 % | 3 | Al inicio dudé si estaba viendo datos de hoy en vivo o un registro pasado, hasta que leí «Repaso de un día del historial». |
| repaso-1030 | palabra | palabra | IEOD | 1 | 60 % | 3 | IEOD |
| repaso-1900 | palabra | palabra | IEOD | 1 | 50 % | 2 | IEOD |
| repaso-1900 | duda | duda | controles de fecha y hora | 1 | 50 % | 2 | En el gráfico la línea de datos reales dice llegar hasta las 19:30, pero el titular y el corte consultado dicen 19:00, generando duda sobre cuál es la … |
| repaso-1030 | palabra | palabra | COES | 1 | 40 % | 2 | COES |
| repaso-1030 | duda | duda | #ahOrigenTit | 1 | 40 % | 2 | La fórmula muestra 'Chronos-2 ajustado' y 'Híbrido (XGBoost + Simons)'. En la carrera vemos sistemas de potencia y curvas de carga, pero no nos enseñan qué son  |
| hoy | palabra | palabra | COES | 1 | 40 % | 2 | COES |
| hoy | palabra | palabra | SEIN | 1 | 40 % | 2 | SEIN |
