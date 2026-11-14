# Playtest sintético: develop (texto)

Capturas de 2026-11-14 02:11 (Lima). Sesiones válidas: 10; fallidas: 0. Entre paréntesis, el rango entre repeticiones (cada una sobre las cinco personas): es el ruido del evaluador.

## Primera apertura

| Medida | entrada-1900 | entrada-hoy |
|---|---|---|
| Dice qué es | 100 % | 100 % |
| Sabe qué momento muestra | 100 % | 100 % |
| Lee la cifra del momento | 100 % | 100 % |
| Lee cifra, pronóstico y rango | 100 % | 100 % |
| Lo primero que mira es la cifra o la respuesta | 0 % | 0 % |
| Primer clic acertado (media de 4 tareas) | 75 % | 60 % |
| …t1 | 100 % | 100 % |
| …t2 | 100 % | 100 % |
| …t3 | 100 % | 0 % |
| …t4 | 0 % | 40 % |
| Dudas por sesión | 3.2 (3.2–3.2) | 3.2 (3.2–3.2) |
| Marcadores de confusión en la voz alta | 0.6 (0.6–0.6) | 1.0 (1.0–1.0) |
| Términos no entendidos por sesión | 5.2 (5.2–5.2) | 4.0 (4.0–4.0) |
| Volvería mañana (sí o tal vez) | 80 % | 80 % |

**Embudo, entrada-1900:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 5/5 → acierta el primer clic en 3 de 4 tareas 5/5 → volvería mañana (sí o tal vez) 4/5.
Términos más citados: El Niño costero / ICEN (100 %), Simons (componente del modelo) (100 %), IEOD (80 %), Chronos-2 / modelo fundacional (60 %), modelo / híbrido / XGBoost (60 %), COES (40 %).
Dudas por zona: chip de El Niño (4), «Lo que dijimos ayer» (4), tarjetas de cifras (2), #ahOrigenTit (2), marca (1), título (1).
Mira primero: marca (4), no ubicada (1).
Le importó: la cifra de ahora (60 %), rendición de cuentas (acertó, cuánto se equivoca) (60 %), los datos para descargar (20 %), el pico y la hora de más consumo (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

**Embudo, entrada-hoy:** abre la pantalla 5/5 → dice qué es 5/5 → lee la cifra del momento 5/5 → sabe qué momento muestra 5/5 → acierta el primer clic en 3 de 4 tareas 2/5 → volvería mañana (sí o tal vez) 2/5.
Términos más citados: El Niño costero / ICEN (100 %), Chronos-2 / modelo fundacional (80 %), IEOD (80 %), COES (40 %), SEIN (40 %), CSV (20 %).
Dudas por zona: chip de El Niño (4), «De dónde sale» (pie) (3), «Lo que dijimos ayer» (3), marca (2), selector de área (1), «¿Qué tan bueno es?» (1).
Mira primero: marca (3), no ubicada (2).
Le importó: rendición de cuentas (acertó, cuánto se equivoca) (40 %), los datos para descargar (20 %), el pico y la hora de más consumo (20 %), la cifra de ahora (20 %).
Acuerdo entre repeticiones: {'comprende': None, 'lectura_cifra': None, 'clic_t1': None, 'clic_t2': None, 'clic_t3': None, 'clic_t4': None}.

## Embudos de las tareas (corridas sin tropezar en ningún paso)

- **t1**: primer clic desde hoy 5/5 → lee lo pronosticado, el rango y lo real (repaso 19:00) 5/5
- **t2**: primer clic desde hoy 0/0 → lee el error y la comparación (Confianza) 0/0
- **t3**: primer clic desde el repaso de las 19:00 0/0 → toca +2 °C 0/0 → lee el cambio 0/0
- **t4**: primer clic desde hoy 0/0 → lee el régimen con más error (Confianza) 0/0

## Tropiezos por puntaje (frecuencia × severidad; las dudas se agrupan por zona)

| Pantalla | Paso | Tipo | Objetivo | Sev. | Frec. | Personas | Evidencia |
|---|---|---|---|---|---|---|---|
| repaso-1900 | t4 primer clic | no sabe qué tocar | — | 4 | 100 % | 5 | No veo ningún botón ni sección sobre el desempeño del pronóstico según las fases de El Niño. El texto de El Niño es informativo y no clickeable, y … |
| hoy | t3 primer clic | no sabe qué tocar | — | 4 | 100 % | 5 | No existe ningún simulador, control de temperatura ni cálculo de sensibilidad térmica en ninguna parte de la página. |
| hoy | t4 primer clic | toca algo que no es control | El Niño costero: extraordinario · ICEN 3 | 3 | 40 % | 2 | Tocaría ese texto porque es el único sitio donde se menciona 'El Niño', a ver si me abre estadísticas de cómo afecta el pronóstico, aunque parece solo texto … |
| repaso-1900 | palabra | palabra | El Niño costero / ICEN | 1 | 100 % | 5 | El Niño costero / ICEN |
| repaso-1900 | palabra | palabra | Simons (componente del modelo) | 1 | 100 % | 5 | Simons (componente del modelo) |
| hoy | palabra | palabra | El Niño costero / ICEN | 1 | 100 % | 5 | El Niño costero / ICEN |
| hoy | t4 primer clic | no sabe qué tocar | — | 4 | 20 % | 1 | Aunque se menciona El Niño arriba, es un texto estático sin enlace y no hay ninguna opción ni gráfico que cruce las fallas del pronóstico con los escenarios … |
| hoy | t4 primer clic | acierta dudando | Confianza | 2 | 40 % | 2 | Tocaría «Confianza» para buscar si tienen una sección con el análisis de errores bajo condiciones de El Niño, ya que el aviso de El Niño de la cabecera … |
| repaso-1900 | duda | duda | chip de El Niño | 1 | 80 % | 4 | No entiendo qué significa ICEN 3.38 ni por qué pone julio de 2026 si la pantalla muestra el 10 de marzo de 2026. |
| repaso-1900 | duda | duda | «Lo que dijimos ayer» | 1 | 80 % | 4 | No sé qué son Chronos-2, XGBoost ni Simons; son términos de programación y algoritmos que no usamos en despacho de carga. |
| repaso-1900 | palabra | palabra | IEOD | 1 | 80 % | 4 | IEOD |
| hoy | duda | duda | chip de El Niño | 1 | 80 % | 4 | No entiendo qué significa ICEN 3.38 ni qué hace una fecha de julio de 2026 si estamos en noviembre, ni cómo se supone que eso afecta la demanda … |
| hoy | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 80 % | 4 | Chronos-2 / modelo fundacional |
| hoy | palabra | palabra | IEOD | 1 | 80 % | 4 | IEOD |
| repaso-1900 | palabra | palabra | Chronos-2 / modelo fundacional | 1 | 60 % | 3 | Chronos-2 / modelo fundacional |
| repaso-1900 | palabra | palabra | modelo / híbrido / XGBoost | 1 | 60 % | 3 | modelo / híbrido / XGBoost |
| hoy | duda | duda | «De dónde sale» (pie) | 1 | 60 % | 3 | Lenguaje muy técnico de inteligencia artificial que no le dice mucho a mis lectores sobre la validez del método. |
| hoy | duda | duda | «Lo que dijimos ayer» | 1 | 60 % | 3 | Me confunde que diga en vivo y a la vez reconstruido después de conocerse lo real; me hace dudar de si de verdad fue un pronóstico previo o … |
| repaso-1900 | duda | duda | tarjetas de cifras | 1 | 40 % | 2 | No sé qué es COES ni entiendo si 4,784 MW es mucha o poca electricidad. |
| repaso-1900 | palabra | palabra | COES | 1 | 40 % | 2 | COES |
