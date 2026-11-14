# Plan: las líneas de trabajo y los PR, en orden

Sale de la línea base ([`linea-base.md`](linea-base.md)), de la primera apertura ([`onboarding.md`](onboarding.md)), de
la crítica externa (verificada contra el código, §3) y de los pendientes de la iteración 8 (§4). Sigue el método de
myPage ([`metodo.md`](metodo.md)): **un cambio pequeño por PR, una medición clave con su umbral fijado aquí, antes y
después con el mismo arnés, lo probado y revertido con cifras, capturas y máscaras de atención antes/después**. Si un
cambio no mueve su medición o empeora una guarda, se revierte y se anota. El orden lo pone el dolor del dueño: *«cuando
abro la app como que me pierdo»*.

**Guardas de todos los PR** (no pueden empeorar; las mide `app/medicion/medir.mjs --rapido` y `atencion/medir.sh`):
T1–T4 cumplidas con las cifras de la API; KLM de las cuatro tareas ≤ 17.8 s (escritorio) y 18.8 s (móvil); axe 0
infracciones; 0 objetivos táctiles de menos de 44 px; 0 px de desborde horizontal; 0 colores fuera del sistema; peso de
«Ahora» ≤ 76 KB; las cifras del caso iguales a las de la API. La atención se compara en repaso (`ahora`, reproducible)
o con capturas de `inicio` hechas en la misma media hora.

## 1. Los PR

| # | PR | Línea | Medición clave: base → umbral | Decisión del dueño |
|---|---|---|---|---|
| 1 | **Qué es Curva**, dicho en la cabecera y el título en las cuatro vistas | L1 Orientación | Prueba de 5 s, «¿Qué es esto?»: responde en 1 de 4 vistas (al límite, 5.2 %) → 4 de 4 | — |
| 2 | **Una cifra del presente al frente**: «Ahora» como cifra destacada, el pico de hoy sin opacarla (y marcado si ya pasó), sin tarjeta vacía en vivo | L2 Jerarquía | Atención a 3 s en la cifra de ahora, escritorio: 1.2 % → ≥ 5 %; «¿cuánta demanda hay ahora?»: 0 de 4 vistas → ≥ 3 de 4; tarjetas vacías: 1 → 0 | — |
| 3 | **La pregunta del día** (concepto B) | L1 Orientación | Prueba de 5 s: 4 / 3 de 6 (escritorio / móvil) → ≥ 5 de 6 en las cuatro vistas; cifras a la vista: 56 / 33 → ≤ 12 | — |
| 4 | **Palabras**: cada término explicado donde aparece y un nombre por concepto | L1 Orientación | Términos a la vista sin definir en la pantalla: 9 / 7 → 0 en «Ahora» y «Confianza»; conceptos con más de un nombre entre pantallas: 5 → 0 | — |
| 5 | **Tocar o arrastrar el gráfico de «Ahora» fija la hora** | L3 Tiempo | T1 (otra hora del mismo día): 15 acciones, 7.1 s KLM → ≤ 3 acciones, ≤ 4 s | — |
| 6 | **Selector propio de fecha y hora**, dd/mm/aaaa y 24 h, con atajos (ayer, hace una semana) | L3 Tiempo | Formato visto en un Chrome en inglés: `03/10/2026` y `07:00 PM` → `10/03/2026` y `19:00`; pulsaciones de T1: 13 → ≤ 4 | — |
| 7 | **El gráfico se lee de un vistazo**: «ahora» como hito, banda visible en claro, rótulo de la rampa con conector | L2 Jerarquía | Atención a 3 s en el punto de «ahora»: 0.0 % / 0.1 % → ≥ 3 % y lift ≥ 2 (escritorio / proyector); contraste banda/fondo en claro: 1.22:1 → ≥ 1.6:1 sin bajar el de la línea (3.41:1) | — |
| 8 | **Apertura guiada de tres pasos sobre el gráfico** (concepto A; necesita el 5) | L1 Orientación | Primer clic sintético: 3 de 6 → ≥ 5 de 6; cifras a la vista en el paso 1: ≤ 5; 0 % de reaperturas tras saltarlo | Sí: si la primera visita se marca en el navegador |
| 9 | **«Lo que dijimos ayer» en el recorrido de lectura** | L2 Jerarquía | Atención a 3 s, escritorio: 0.7 % (lift 0.16) → ≥ 3 %; en tablet y móvil: fuera de la vista → visible sin desplazarse | — |
| 10 | **Confianza honesta de un vistazo**: el aviso en vivo junto al veredicto de cobertura, selectores con menos peso | L4 Confianza | Atención a 3 s en el aviso en vivo: 0.2 % → ≥ 3 % y a la vista sin desplazarse; selectores: 21 % → ≤ 10 % (escritorio) | — |
| 11 | **Un solo rango, recalibrado**: el 80 % en vivo y el 90 % del repaso pasan a un nivel, calibrado con el registro en vivo | L4 Confianza | Cobertura en vivo (23-oct → 12-nov) del rango publicado: 73.2 % Centro, 74.3 % Norte para un 80 % nominal → dentro de ±3 puntos del nominal en las tres áreas, en un tramo que no se usó para calibrar | Sí: qué nivel publicar (80 o 90 %) |
| 12 | **Tarjetas de área con identidad y cuota de la demanda** en vez de las insignias N/C/S | L2 Jerarquía | El área elegida se lleva más atención que cada una de las otras (hoy Norte 9.4 % > Centro 7.2 %); «¿de qué zona habla?»: 1 de 4 vistas → ≥ 3 de 4 | — |
| 13 | **«Detalle» se funde en «Ahora» y «Confianza»** (escenarios, diagnóstico y modelo se mudan; lo duplicado se va) | L5 Consistencia | Jaccard de tamaños de letra Detalle~Ahora: 0.44 → ≥ 0.7 (o pantalla retirada); controles a la vista: 19 / 29 (escritorio / proyector) → ≤ 15; T3 ≤ 2 acciones | **Sí: fusionar o retirar** |
| 14 | **Partir `app.js`**: «Confianza» y lo que quede de «Detalle» se cargan al abrirlos | L6 Rendimiento | Peso de «Ahora»: 76 KB → ≤ 50 KB; hasta ver el número en red lenta: 829 ms → ≤ 706 ms | — |
| 15 | **Niveles Ciudadano y Operador** (concepto C), con estados vacíos que enseñan | L1 Orientación | En Ciudadano: controles a la vista 12 / 10 → ≤ 6; prueba de 5 s ≥ 5 de 6; en Operador, KLM de T1–T4 ≤ base | **Sí: público objetivo** |
| 16 | **El repositorio presenta «Curva»**: README con la captura principal y el contexto académico al pie, poda de capturas, `LICENSE` y `Dockerfile` | L7 Repositorio | README: 0 imágenes y el título de curso → captura de «Ahora» en la primera pantalla; capturas sin referencia en `docs/img/app-hcd`: 10 de 40 → 0; `docker run` responde `/salud` | **Sí: licencia** |

Fuera de la numeración, porque no es un PR de interfaz:

- **L8 Personas** (antes del 3 y después del 8): cinco personas que no conocen Curva, una prueba de 5 segundos con la
  pantalla de entrada y tres tareas de primer clic (T1, T2 y T4), antes y después. Es lo que valida o desmiente todo lo
  sintético de este plan.
- **Renombrar el paquete y el repositorio** (`tetouan_power_forecast` → algo de Curva o del SEIN): decisión del dueño;
  si se hace, va en un PR propio sin otros cambios, con `ruff` y `pytest` verdes y los enlaces de Colab actualizados.

### Por qué este orden

1. **Orientación primero (1–4).** Son los más baratos y atacan lo que la línea base marca peor: nadie sabe qué es ni
   dónde mirar. El 1 y el 2 son cambios de pocas líneas; el 3 es el primer concepto de primera apertura, el que menos
   arriesga (sin recorrido ni niveles); el 4 completa la prueba de 5 s y es requisito de los conceptos A y C.
2. **Después, el tiempo (5–6).** Fijar la hora es la acción más frecuente y hoy cuesta 15 acciones con controles que
   hablan en formato estadounidense. El 5 además es la mecánica que enseña el concepto A.
3. **El gráfico y la rendición de cuentas (7–9).** Con el hito de «ahora» y la banda visibles, la apertura guiada (8)
   tiene algo que señalar.
4. **Confianza (10–11).** El 10 es de interfaz y rápido; el 11 toca el modelo del registro en vivo y necesita la
   decisión del nivel del rango.
5. **Identidad, consistencia y peso (12–14).** El 13 espera la decisión sobre «Detalle»; el 14 conviene después del 13,
   porque partir el script depende de qué queda de esa pantalla.
6. **Lo que necesita decisiones (15–16).** El README (16) no depende de nada y puede adelantarse si hace falta para una
   entrega.

## 2. Las líneas de trabajo

El repositorio **no usa beads** (no hay `.beads/`; `bd` está instalado en la máquina, pero no se inicializó aquí sin
pedirlo). Las líneas quedan en este plan, en el mismo formato de los epics de myPage, listas para `bd create` si el
dueño lo adopta.

### L1 · Orientación y primera apertura (PR 1, 3, 4, 8, 15)

- **Estado:** abierta; es la prioridad del dueño.
- **Instrumento:** `atencion/medir.sh` en `inicio` (la URL raíz) y `ahora`: prueba de 5 s y de primer clic sintéticas,
  términos sin definir, controles y cifras a la vista.
- **Hallazgos (base):** 12 controles y 56 cifras a la vista en escritorio; prueba de 5 s 4 / 3 / 3 / 3 de 6
  (escritorio, proyector, tablet, móvil); 11 términos a la vista sin definir (9 sin explicación en la pantalla);
  primer clic sintético 3 de 6 en las cuatro vistas.
- **Próximos pasos:** PR 1 → 3 → 4; sesiones con personas (L8); PR 8 tras el 5; PR 15 si el dueño quiere dos niveles.

### L2 · Jerarquía y atención en «Ahora» (PR 2, 7, 9, 12)

- **Hallazgos (base, escritorio, 3 s):** tarjetas de área 18.7 % (lift 1.9), cifra de ahora 1.2 %, pico 2.2 %, punto
  de «ahora» 0.0 %, «lo que dijimos ayer» 0.7 % (lift 0.16), gráfico 6.7 % (lift 0.32). El pico a 40 px opaca a la
  cifra de ahora a 28 px, y en vivo a las 22:30 habla de un pico que ya pasó.
- **Próximos pasos:** PR 2 → 7 → 9 → 12.

### L3 · Interacción con el tiempo (PR 5, 6)

- **Hallazgos:** el gráfico de «Ahora» solo muestra un tooltip (`pointermove`, flechas); fijar la hora exige escribir
  en `#ahFecha` y `#ahHora` (13 pulsaciones). Los controles nativos siguen el idioma del navegador, no el de la página:
  `03/10/2026` y `07:00 PM` con `lang="es"` y locale `es-PE`.

### L4 · Confianza (PR 10, 11)

- **Hallazgos:** el titular funciona (28–30 % de la atención, lift 9); el aviso de que el rango del 80 % cubrió 73.2 %
  en vivo se lleva 0.2 % y solo su cifra está a la vista, mientras la tarjeta de cobertura dice «Cumple lo que promete»
  (91.1 %, rango del 90 %, 2026). Los selectores de área y horizonte se llevan 21 % (lift 4.2).

### L5 · Consistencia del sistema (PR 4, 13)

- **Hallazgos:** «Detalle» usa 12 tamaños de letra (5 que no usa ninguna otra pantalla: 10, 12.5, 13.5, 22 y 52 px);
  Jaccard de tamaños con «Ahora» 0.44, frente a 0.73 entre «Ahora» y «Confianza». Cinco conceptos con más de un
  nombre entre pantallas (Pronóstico/Modelo, Rango del N %/Rango probable, Pico/Máximo, Referencia, Error medio/MAE).
  Colores fuera del sistema: 0 en las 32 capturas (se conserva).

### L6 · Rendimiento (PR 14)

- **Hallazgos (iteración 8):** peso de «Ahora» 48 → 76 KB; hasta ver el número en red lenta 706 → 829 ms; `app.js`
  pesa 174 KB (49 KB comprimido) y trae el código de las tres pantallas.

### L7 · El repositorio como producto (PR 16 y el renombre)

- **Hallazgos:** el README abre con `tetouan-power-forecast` y «Trabajo grupal (TB1) del curso…», sin ninguna imagen;
  `docs/img/app-hcd` tiene 40 capturas (3.8 MB), 10 sin referencia; no hay `LICENSE` ni `Dockerfile`; el paquete se
  llama `tetouan_power_forecast` y `pyproject.toml` describe «el consumo eléctrico de la Zona 1 de Tetuán».

### L8 · Validación con personas

- **Estado:** pendiente desde la primera pasada. Todo lo de este plan es sintético.

## 3. La crítica externa, verificada contra el código

| Punto de la crítica | ¿Se confirma? | Evidencia | PR |
|---|---|---|---|
| Clic o arrastre en el gráfico de «Ahora» para fijar la hora | Sí, no existe | `app.js`: `#ahLienzo` solo escucha `pointermove`, `pointerleave`, `focus`, `blur` y flechas (tooltip); el de «Detalle» sí tiene `alPulsar` | 5 |
| Selector de fecha y hora propio, formato peruano y 24 h | Sí | `<input type="date">` y `<input type="time" step="1800">`; en la captura del arnés (Chrome en inglés, página `es`, locale `es-PE`): `03/10/2026` y `07:00 PM` | 6 |
| El «Pico» a 40 px opaca a «Ahora» a 28 px; tarjeta vacía sin «mañana a esta hora» | Sí | `.kpi.dest .n { font-size: 40px }` frente a `.kpi .n { 28px }`; atención a 3 s: pico 2.2 %, ahora 1.2 %; en vivo, «Mañana a esta hora: —» | 2 |
| Insignias N/C/S genéricas en vez de identidad y cuota | Sí | `INFO_AREA` solo da una letra; las tarjetas no dicen qué parte del SEIN es cada área; la más mirada es Norte (9.4 %), no la elegida | 12 |
| Rótulo de la rampa sin conector; banda del rango casi invisible en claro | Sí | El texto «+325 MW en 1 h» se dibuja a 10 px del tramo, sin línea; banda `rgba(42,120,214,.16)` sobre el fondo del futuro: **1.22:1** en claro (1.36:1 en oscuro) | 7 |
| «Detalle» con estilos antiguos que duplica «Ahora»/«Confianza» | Sí | Variables de la «versión anterior» en `style.css`; 12 tamaños de letra, 5 propios; repite cifra, rango, real, error, curva, pico y «¿qué tan bueno es?»; propio: escenarios, diagnóstico, modelo, horizonte y la sección en vivo | 13 (dueño) |
| README de trabajo de curso, sin imágenes | Sí | Título `tetouan-power-forecast`, «Trabajo grupal (TB1)…», 0 imágenes | 16 |
| 41 capturas intermedias en `docs/img/app-hcd` | Casi: son **40** (3.8 MB), 10 sin referencia | conteo en `develop` | 16 |
| Paquete `tetouan_power_forecast` para un producto del SEIN | Sí | `src/tetouan_power_forecast`, `pyproject.toml` | renombre (dueño) |
| Falta `LICENSE` y `Dockerfile` | Sí | no existen en la raíz | 16 (licencia: dueño) |

## 4. Pendientes conocidos que entran al plan

| Pendiente | De dónde | PR |
|---|---|---|
| Unificar el rango del 80 % en vivo con el del 90 % del repaso y recalibrarlo (cubrió 73.2 % en Centro y 74.3 % en Norte) | `docs/app-hcd.md`, iteración 8 | 11 |
| Partir `app.js` (el peso de «Ahora» subió de 48 a 76 KB) | iteración 8 | 14 |
| Modo operador/público (no se llevó del prototipo) | iteración 8 | 15 |
| Las tareas T2–T4 del arnés empiezan en el caso en repaso, no en la primera apertura | esta auditoría | 1–4 (agregar al arnés una variante desde la raíz) |
| Sesiones con personas | primera pasada | L8 |

## 5. Plantilla de cada PR (como en myPage)

```markdown
## Auditoría
<la medición clave: tabla base → este PR, con el umbral; y las guardas que no se movieron>
<lo probado y revertido, con cifras>
## Cambios
## Antes / después (capturas)   ← app/medicion/capturas.mjs
## Máscaras de atención         ← atencion/comparar.py base <pr> --salida docs/auditoria/<pr>/
## Literatura
## Checks                       ← ruff, pytest, medir.mjs --rapido, atencion/medir.sh
```
