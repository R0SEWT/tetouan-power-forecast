# Playtest sintético: punta (texto)

Capturas de 2026-11-14 02:11 (Lima). Sesiones válidas: 10; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

## Primera apertura

| Medida | entrada-1900 | entrada-hoy |
|---|---|---|
| Dice qué es | 100 % | 80 % |
| Sabe qué momento muestra | 100 % | 60 % |
| Lee la cifra del momento | 100 % | 100 % |
| Lee cifra, pronóstico y rango | 100 % | 100 % |
| Lo primero que mira es la cifra o la respuesta | 0 % | 0 % |
| Primer clic acertado (media de 4 tareas) | 75 % | 60 % |
| …t1 | 100 % | 100 % |
| …t2 | 100 % | 100 % |
| …t3 | 100 % | 0 % |
| …t4 | 0 % | 40 % |
| Dudas por sesión | 2.8 (2.8–2.8) | 3.0 (3.0–3.0) |
| Marcadores de confusión en la voz alta | 1.2 (1.2–1.2) | 1.6 (1.6–1.6) |
| Términos no entendidos por sesión | 4.2 (4.2–4.2) | 2.8 (2.8–2.8) |
| Volvería mañana (sí o tal vez) | 80 % | 80 % |

**Embudo, entrada-1900:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 5/5 → acierta el primer clic en 3 de 4 tareas 5/5 → volvería mañana (sí o tal vez) 4/5.
Términos más citados: Simons (componente del modelo) (100 %), Chronos-2 / modelo fundacional (80 %), IEOD (80 %), modelo / híbrido / XGBoost (80 %), COES (40 %), CSV (20 %).
Dudas por zona: chip de El Niño (5), respuesta a la pregunta (5), no ubicada (1), respuesta a la pregunta (1), #ahCsv (1), marca (1).
Mira primero: marca (4), no ubicada (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (60 %), la cifra de ahora (40 %), los datos para descargar (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

**Embudo, entrada-hoy:** abre la pantalla 5/5 → dice qué es 4/5 → lee la cifra del momento 4/5 → sabe qué momento muestra 3/5 → acierta el primer clic en 3 de 4 tareas 2/5 → volvería mañana (sí o tal vez) 2/5.
Términos más citados: Chronos-2 / modelo fundacional (80 %), IEOD (80 %), COES (40 %), CSV (20 %), MW / megavatios (20 %), SEIN (20 %).
Dudas por zona: párrafo de modo (5), «Lo que dijimos ayer» (4), «De dónde sale» (pie) (2), chip de El Niño (2), cifra de ahora (1), marca (1).
Mira primero: marca (4), no ubicada (1).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (40 %), los datos para descargar (20 %), la cifra de ahora (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 5/5 → lee lo pronosticado, el rango y lo real (repaso 19:00) 5/5
- **t2**: primer clic desde hoy 0/0 → lee el error y la comparación (Confianza) 0/0
- **t3**: primer clic desde el repaso de las 19:00 0/0 → toca +2 °C 0/0 → lee el cambio 0/0
- **t4**: primer clic desde hoy 0/0 → lee el régimen con más error (Confianza) 0/0

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| repaso-1900 | t4 primer clic | no sabe qué tocar | — | 4 | 100 % | 5 | Solo veo un texto informativo que dice 'El Niño costero: extraordinario', pero no es un botón ni hay ningún enlace visible sobre errores según El Niño. |
| hoy | t3 primer clic | no sabe qué tocar | — | 4 | 100 % | 5 | No existe ningún control, botón ni mención a la temperatura (+2 °C) ni a análisis contrafácticos en toda la pantalla. |
| hoy | t4 primer clic | no sabe qué tocar | — | 4 | 40 % | 2 | Aunque aparece el texto 'El Niño costero (calentamiento del mar frente a la costa): extraordinario', es solo una etiqueta estática no interactiva. No hay ningún |
| hoy | momento | confunde el momento | dia_pasado | 3 | 40 % | 2 | Habla de un día pasado. Aunque tiene botones y textos que dicen 'Hoy', muestra datos del 12 de noviembre de 2026 a las 23:30 (y 24:00), y advierte … |
| repaso-1900 | duda | duda | chip de El Niño | 1 | 100 % | 5 | No sé si es un dato que puedo cambiar o solo un texto informativo, ni cómo influye en el pronóstico o el gráfico. |
| repaso-1900 | duda | duda | respuesta a la pregunta | 1 | 100 % | 5 | Esa fórmula con nombres raros de inteligencia artificial me marea; no sé de dónde salen esos modelos ni esos pesos. |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| hoy | duda | duda | párrafo de modo | 1 | 100 % | 5 | Me confunde si la pantalla me está mostrando datos de hoy en vivo o de ayer, porque arriba dice «Hoy» y «Último dato real · 23:30», pero aquí … |
| hoy | t4 primer clic | acierta dudando | Confianza | 2 | 40 % | 2 | Iría a «Confianza» a ver si allí desglosan el margen de error según eventos climáticos. En esta pantalla solo aparece la etiqueta informativa «El Niño costero.. |
| repaso-1900 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| repaso-1900 | palabra | palabra | IEOD | 1 | 80 % | 4 | IEOD |
| repaso-1900 | palabra | palabra | modelo / híbrido / XGBoost | 1 | 80 % | 4 | modelo / híbrido / XGBoost |
| hoy | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| hoy | palabra | palabra | IEOD | 1 | 80 % | 4 | IEOD |
| hoy | duda | duda | «Lo que dijimos ayer» | 1 | 80 % | 4 | Me suena contradictorio que diga «en vivo» y al mismo tiempo «reconstruido despues de conocerse el real». No me queda claro si fue una predicción real previa o  |
| hoy | qué es | no entiende qué es | primera impresión | 3 | 20 % | 1 | Parece una página de noticias o del Estado sobre cuánta electricidad se consume en el Perú, para ver si alcanza la energía. |
| hoy | t4 primer clic | toca algo que no es control | El Niño costero (calentamiento del mar f | 3 | 20 % | 1 | Tocaría ese texto porque menciona directamente a El Niño costero a ver si despliega las situaciones y el error del pronóstico, aunque parece texto estático y no |
| repaso-1900 | palabra | palabra | COES | 1 | 40 % | 2 | COES |
| hoy | duda | duda | «De dónde sale» (pie) | 1 | 40 % | 2 | No sé qué es «Chronos-2» ni qué significa «modelo fundacional de series de tiempo». Como periodista de datos no sé cómo explicárselo a los lectores de forma sen |
| hoy | palabra | palabra | COES | 1 | 40 % | 2 | COES |
