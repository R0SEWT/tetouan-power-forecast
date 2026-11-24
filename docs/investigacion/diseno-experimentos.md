# Plan de experimentos: Tetuán, Ceuta y SEIN

Versión 2, 23 de noviembre de 2026. Revisa la versión 1 (copia en `diseno-experimentos.prev.md`) con una crítica de rigor que encontró fugas de diseño, hipótesis ya medidas, dependencias en ciclo y un Nivel 1 que no cabía antes de TB1. Une el análisis de brechas, los cuatro diseños propuestos, el veredicto de tres jueces (rigor, novedad e impacto, factibilidad) y esa crítica. Está escrito para el equipo y, más adelante, para los revisores del paper.

Convenciones:
- Las rutas del repo son relativas a `/home/cip-exodia/Code/exprimental/tetouan-power-forecast` (rama develop, HEAD `ebdea94`).
- "Scratchpad" significa `/home/cip-exodia/Code/exprimental/tetouan-research/scripts/design/`. Es un directorio temporal: copien a un lugar durable los scripts ancla (`deltas_nb02.py`, `ceuta_baselines.py`, `pdo_windows.py`, `oper_anchor.py`, `gaps.py`, `audit2/irsec_*.py`) antes de que se borre. `tetouan-research/scripts/pr03_replica.py` ya está en un lugar durable.
- Las cifras nuevas (deltas de Tetuán y Ceuta, ventanas del PDO, lectura de figuras de IRSEC, cuantiles y rampas del PDO) son cálculos propios no revisados por terceros. Hay que verificarlas antes de citarlas.
- Este plan usa resultados no publicados del equipo y trabajos de terceros.

### Cambios principales respecto a la versión 1

1. **Fugas corregidas antes de correr nada.** Las referencias estacionales usan S = ⌈H/S_d⌉·S_d, y el arnés verifica con un `assert` que todo rezago sea ≥ 0 (B2 y B6 filtraban el futuro a origen fijo). P5 (PDO por área) sale de X1. Tetuán se reajusta solo con `entrenamiento` para la validación.
2. **Tetuán es entero reanálisis/exploratorio.** No tiene ventana confirmatoria: la arquitectura se eligió mirando los folds Mar–Dic y el test.
3. **Hipótesis ya medidas fuera de las familias confirmatorias:** H1a, H1b, H3a (retirada), H8b (salvo en vivo), la parte de γ de H12a, H6a (réplica), y la parte ya corrida de H9b (`ftcal2` perdió).
4. **Origen de igual información frente al PDO** (08:00 de D−1). El de 16:00 pasa a ser cota optimista. La vista pública usa `prediction_length = 96`.
5. **Orden sin ciclos:** `prereg-v1` se fija antes de X1, `prereg-v2` espera solo a X12-SEIN y la dependencia queda X1 → X3 → X4 → H3c.
6. **Nivel 1 dividido:** 1a (antes de TB1: referencias sobre predicciones guardadas, DM con bootstrap circular, PDO-CPU exploratorio, colectores, textos) y 1b (después).
7. **Referencias nuevas:** semana pasada ajustada por nivel (B9), media de k semanas con ajuste de nivel (B10), B7 sin feriado, comparadores reentrenados en toda tabla de FM y la búsqueda de un pronóstico del operador para Ceuta.
8. **Lo que faltaba:** `fallas_en_curso` degenerada, cuarentena, días sin IEOD, N+C+S ≠ SEIN, viento de Tetuán, Ramadán, la etiqueta "24 h" en vivo, el XGB apilado y SHAP, y el vintage del portal (X21 y ajustes en X5, X10, X11 y X15).
9. **Afirmaciones corregidas:** FM sobre UCI 849 ya existe (Singh & Tewari 2026, Chronos en Z2 a t+1). R0 no fue "a ciegas". Se citan bien Toto-2 313m, TabPFN-TS y la celda de nb03.
10. **Cómputo:** X17 pasa a ~80 A100-h, X13 queda sujeto a un piloto cronometrado y TabPFN-TS sale de X16.

---

## 0. Resumen

La historia actual del paper ("mejoramos un 40–58 % sobre la mejor de tres ingenuas") no resiste una referencia fuerte. Frente a la persistencia más el delta diario, el modelo de Tetuán gana un 18.5 % en Z1 y un 12.3 % en Z2, y pierde un 9.4 % en Z3. En validación, una media fija de dos deltas le gana en las tres zonas. En Ceuta, V4 sin verano pierde contra el delta semanal en 5 de 5 veranos. En el SEIN nadie ha comparado contra el PDO del COES (MAPE 1.50 % en 2025), y una cota gruesa sugiere que el repo podría no ganarle.

La historia que proponemos es otra: un protocolo de evaluación orientado a la operación, aplicado a tres sistemas de escala muy distinta, que dice con pruebas pareadas cuánto valor queda sobre referencias fuertes y sobre el operador, y dónde. Tetuán aporta evidencia de reanálisis (no confirmatoria). La única evidencia confirmatoria del paper sale de la ventana prospectiva del SEIN (X5).

Preguntas que el plan responde:
1. ¿Cuánto skill queda sobre la referencia trivial más fuerte (deltas, semana ajustada por nivel, Ridge, mismo tipo de día, PDO), con las mismas filas, pruebas que respetan la dependencia y control de multiplicidad?
2. ¿Le gana algún modelo al PDO en su propia estructura (SEIN total, día siguiente) **con igual información** (origen 08:00 de D−1), y qué pasa en la cota optimista (16:00) y en la vista pública? Si no, ¿lo mejora como capa de corrección?
3. ¿El objetivo en razón aporta por sí mismo, una vez separado de la normalización de variables, y se sostiene en Tetuán y Ceuta?
4. ¿Cuánto del R² ≈ 0.98 de la literatura sobre UCI 849 es producto del protocolo (partición aleatoria, regresión del mismo instante) y no de capacidad de pronóstico?
5. ¿Se sostienen las conclusiones sobre clima y modelos fundacionales cuando se usan pronósticos reales archivados, una ventana prospectiva no explorada y controles de contaminación?

---

## 1. Punto de partida

### 1.1 Lo ya hecho

| Acto | Resultado actual | Fuente |
|---|---|---|
| Tetuán (OE1) | HGB global, objetivo `y(t+6)/media_24h`. Test (6-nov a 30-dic-2017): MAE 462.5 / 429.4 / 429.1 kW (Z1/Z2/Z3). Mejora frente a la mejor de 3: 44.8 / 55.9 / 40.7 %. Con reentrenamiento semanal: 446.3 / 415.0 / 415.5 | `notebooks/02_modelado_evaluacion.ipynb`, celda 25 |
| Tetuán, referencia fuerte | Delta diario en test: 567.5 / 489.9 / 392.1. Media fija de deltas: 480.7 / 413.2 / 368.2 en test y 566.9 / 412.7 / 351.4 en validación (modelo en validación: 590.1 / 472.7 / 373.1) | scratchpad `deltas_nb02.py` |
| Tetuán, rolling y variantes | `experimentos/historico/rolling.py` ya corre V0–V4 en folds mensuales Mar–Dic (V2 frente a V4: mismo conjunto de variables, pero distinto objetivo **y** distinta normalización, /m24). Z3 pierde contra B2 en marzo, mayo, junio y julio. La elección razón + global de `docs/historico.md` §1 se hizo mirando esos folds y el MAPE del test | `rolling.py`, CSV en Drive `reportes/historico/`; scratchpad `deltas_nb02.py` |
| Tetuán, lo que está guardado | nb02 guarda `predicciones_prueba_zona*.csv` y tablas agregadas (`origen_movil.csv`). **No** guarda predicciones de validación ni por fila del rolling. `modelo_final.joblib` se ajustó con `tramo("desarrollo")` = entrenamiento + validación (celdas 5 y 39) | nb02 |
| Tetuán, datos | Denominadores enteros mensuales 13–929 (informe §4.2). Quiebre Z1→Z2 el 25-oct hacia las 11 h con `cuota.py` (`historico.md` §4). Z3 pierde en Ramadán (631.1 frente a 587.8) | informe, `historico.md` |
| Ceuta (OE2) | V4 sin verano 2.31 % de MAPE; delta semanal 2.06 % (gana en los 5 veranos 2022-26); V4 con 1 año 1.93 %, con 3 años 1.81 % | `experimentos/ceuta/validacion.py`; scratchpad `ceuta_baselines.py` |
| SEIN validación 2025 | RF por área elegido (43.20 % frente a 42.88–42.93 % de XGB); rolling 2023-25: 108/108 área-meses contra la mejor de 3. nb02_sein celda 40 guarda las predicciones de validación 2025 y un `origen_movil.csv` **agregado** | `notebooks/02_sein*` |
| SEIN test 2026 | 1 h: 51.7 / 57.9 / 29.1 % (N/C/S). 24 h: 34.5 / 42.2 / 11.9 %; Centro 24 h MAE 78.15 MW. Exógenas y reentrenamiento mueven ~1 %. Política C (reentrenamiento semanal) en `prueba_2026/predicciones_{h}_{a}.csv` | nb03, celda 9 (mejoras), celda 11 (ablación), celda 26 (política C) |
| Fundacionales (SEIN) | Chronos-2 ft+feriado (ftcal) 40.0 / 41.6 %; combinación con XGB+Simons 40.7 / 42.3 %; Centro 24 h 2026: 71.9 MW. `chronos2ftcal2` (sábado, domingo, víspera, puente) **perdió**: 78.2 frente a 75.6 MW (Centro, 24 h, 2025). La receta de ftcal (lr 1e-6, 3000 pasos, feriado) se eligió en 2025 entre a/b/c/ftcal/ftcal2 | nb04; `chronos2_variantes.py:50-60` |
| En vivo (desde 13-nov) | Centro "24 h": MAE 90.7, sesgo −68.3 MW, cobertura del 80 % en 66.7 %. ACI con γ = 0.2 (elegido en 2025) da 79–81 % en 2025/2026 y 82–86 % en vivo. El registro ya guarda ftcal, +rango y +calor con sha256. **El "24 h" se emite hacia las 10:00 del propio día objetivo** con el anexo del día anterior: no es un pronóstico de día siguiente | `src/tetouan_power_forecast/en_vivo.py:1-20`, `:540-557`; PR #53/#55 |
| Clima (SEIN) | +calor en el 10 % de días más cálidos de Centro: error de pico 106 → 74 MW en 2025 (−32 [−43, −19]); 2026: −16 [−26, −1] | PR #55 |
| PDO del COES (SEIN total) | MAPE 1.50 %, MAE 105.0 MW (2025); 1.51 %, 111.3 MW (2026-01-01 a 10-17, ventana de test); sesgo +23.3 MW (+40–58 MW de 12 a 16 h). Con la ventana 2026-01-01 a 11-22 (n = 15,685), MAE 110.5 | scratchpad `pdo_windows.py`, `oper_anchor.py`; CSV `/home/cip-exodia/Code/exprimental/tetouan-research/data/out/coes_demand_30min.csv` |
| Referencia 1 h SEIN total | `y(t−2)+Δsemana`: 1.22 %, MAE 85.0; con ΔPDO: 1.03 % (techo del operador) | scratchpad `pdo_windows.py` |
| Réplica PR-03 (R0) | Réplica simplificada (sin carga industrial ni feriados): MAPE 2.2–2.5 % (4.3 % en 2020). Ya se conoce: no es una predicción | `informe.md:306`; `tetouan-research/scripts/pr03_replica.py` |
| UCI 849, literatura | Z1 = Quads confirmado; Z2 = Boussafou y Z3 = Smir inferidos de figuras. Serie "horaria" de IRSEC = suma de 6 lecturas. IRSEC 2018 apunta a partición cronológica (test desde ≈2017-10-03 17:00). Wei (2023) ya hizo Z1, 10 min, t+6. Singh & Tewari (2026) ya usaron Chronos en Z2 a t+1 con partición cronológica. Aleatoria frente a cronológica, RF solo calendario: R² 0.994 frente a 0.126 | scratchpad `audit2/irsec_*.py`; `docs/estado-del-arte.md:53`; `informe.md:58` |

### 1.2 Huecos (resumen del análisis de brechas y de la crítica)

- **Referencias débiles.** `REFERENCIAS` (`variables.py:23`, `variables_sein.py:29`) solo tiene persistencia, ayer y semana pasada. Ningún delta, Ridge ni PDO.
- **Sin prueba pareada** contra la referencia fuerte. Bloques de 1 día también a 24 h; 66 IC sin corrección de multiplicidad.
- **Fuga de diseño.** En Tetuán la arquitectura se eligió mirando los folds Mar–Dic y el test. En el SEIN, 2026 se exploró antes del test. Los hiperparámetros se ajustaron en todo el entrenamiento y se reusaron en el rolling. La receta de ftcal se eligió en 2025.
- **Regla de información incompleta.** ERA5 interpolado hacia adelante en Ceuta (`ceuta.py:173-178`), ERA5 tratado como tiempo real, temperatura "pronosticada" simulada como verdad + N(0, 1.5 °C) con la misma semilla para todas las áreas, calendario de Ceuta en UTC, convención de feriados inconsistente.
- **Sin comparación con el PDO** (auditoría G3, issue #9).
- **Calibración.** Tetuán y Ceuta sin intervalos; SEIN con intervalos parcialmente dentro de la muestra (`apilar.py:261-266`) y errores del RF aplicados al XGB en la app.
- **Rupturas.** Traspaso Z1→Z2 del 25-oct dentro de validación; salto de Z3 del 8 al 18-nov dentro del test; lunes feriado como peor error de 2026 (776 MW el 29-jun).
- **Contaminación de FM** no auditada (Simons, Timestral y otros); ningún control limpio corrido.
- **Variables del SEIN dudosas.** `fallas_en_curso` está degenerada (activa el 91 % de 2025, entre 0.47 y 1.80 por periodo), así que "las fallas no ayudan" no está probado. La cuarentena no usa la tabla curada `cuarentena_pe_2020` (5 fases) ni corta la segunda ola de 2021. Hay 7 días sin IEOD que hacen perder unos 56 días de filas de entrenamiento; el portal los cubre a nivel SEIN. En 2026 hay 48 periodos con N+C+S ≠ SEIN (hasta 47.6 MW), sin diagnóstico. El XGB apilado reusa hiperparámetros de nb02 (posiblemente ajustados en 2025), y el SHAP se calcula sobre un modelo que no es el elegido ni el servido. M4 (SAIDI) no se ha evaluado.
- **Variables de Tetuán dudosas.** Viento bimodal e implausible usado como variable; clima con importancia ≈0; Ramadán con fechas aproximadas.
- **Ceuta.** Falta el 15-ago (nacional). El 2-sep y el 17-sep (Melilla) caen fuera de la ventana de test, que termina el 1-sep. Hay 4 valores no positivos que afectan el MAPE, y la selección en 2020 (COVID) es atípica.
- **Etiqueta "24 h" en vivo.** Se emite hacia las 10:00 del día objetivo; las hipótesis (b) y (c) de `prereg-v1` la heredaban sin aclararlo.
- **Vintage del portal.** El Ejecutado reciente puede ser preliminar.
- **Datos.** Las predicciones guardadas y las capas silver/gold están solo en Drive, y el token de rclone está vencido (PR #55).

---

## 2. Decisiones transversales

Estas reglas valen para todos los experimentos. Se escriben en `docs/preregistro-evaluacion.md` y se commitean, con el tag `prereg-v1`, **antes de correr X1** (ver 2.8 y 5.1).

### 2.1 Referencias oficiales

Se implementan en un `referencias.py` común y se agregan a `REFERENCIAS` sin quitar las existentes.

**Regla de rezago estacional.** Para un horizonte H (pasos desde el último dato disponible en la vista), toda referencia estacional usa S = ⌈H/S_d⌉·S_d (diaria) o S = ⌈H/S_w⌉·S_w (semanal). Así ningún término y(t+H−S) cae después del último dato disponible. El arnés de X0 lleva un `assert` de que todo rezago es ≥ 0 respecto del último dato disponible **en la vista** (I-op, I-pub, rodante). Este error afectaba a B2, B6 y "B4 a origen fijo" en v1 (H = 17..64 con S_d = 48).

| Código | Referencia | Definición |
|---|---|---|
| B0 | Persistencia | ŷ(t+H) = y(t) |
| B1 | Mejor de 3 (legado) | La regla actual; solo para continuidad, va al apéndice |
| B2 | Delta diario | ŷ(t+H) = y(t) + [y(t+H−S) − y(t−S)], S = ⌈H/S_d⌉·S_d. **A 24 h rodante (H = S_d) degenera** en 2y(t) − y(t−S_d), una extrapolación lineal: se excluye a 24 h rodante (se reporta solo en el apéndice, rotulada así) |
| B3 | Delta semanal | Igual con S = ⌈H/S_w⌉·S_w |
| B4 | Media de deltas | 0.5·B2 + 0.5·B3, sin nada ajustado (donde B2 está excluida, B4 = B3) |
| B5 | Mezcla convexa | Pesos ≥0 que suman 1, ajustados **dentro de cada fold** con datos de entrenamiento |
| B6 | Ridge sobre rezagos | Rezagos {0, 1, 2, S_d', S_d'−H, S_w', S_w'−H} con S_d' = ⌈H/S_d⌉·S_d y S_w' = ⌈H/S_w⌉·S_w (todos ≥ 0); alpha en rejilla log 1e-6 a 1e4, CV temporal interna con hueco H, **dentro de cada fold** |
| B7 | Mismo tipo de día | Media de los últimos 3 días del mismo tipo a la misma hora; feriado → domingo. En Tetuán también **B7-sf** (sin feriados), porque la lista de feriados es aproximada (`variables.py:18-21`) |
| B8 | MSTL+AutoETS | Opcional, después de TB1; configuración fijada antes de correr |
| B9 | Semana pasada ajustada por nivel | ŷ(t+H) = y(t+H−S_w')·m24(t)/m24(t−S_w'). Contraparte natural del objetivo en razón; candidata fuerte a 24 h, donde B2 degenera |
| B10 | Media de k semanas ajustada por nivel | Media de y(t+H−j·S_w')·m24(t)/m24(t−j·S_w') para j = 1..k, con k = 4 fijado ex ante. Robusta a un feriado aislado en la semana de referencia |
| C-RT | Comparador reentrenado | Mismo modelo con reentrenamiento periódico: política C semanal del SEIN (`prueba_2026/predicciones_{h}_{a}.csv`, nb03 celda 26) y HGB semanal de Tetuán (446.3 / 415.0 / 415.5, nb02 celda 25). Obligatorio en **toda** tabla de FM |
| P1 | PDO (SEIN total) | Columna "Programación Diaria" del portal; usable solo si el objetivo está en D y el origen es ≥16:00 de D−1 |
| P2 | PSO | Programa semanal; comparación también horaria |
| P3 | Techo del operador a 1 h | y(t−2) + [PDO(t) − PDO(t−2)] |
| P4 | Réplica PR-03 R0/R1 | Ver X3 |
| P5 | PDO asignado por área | PDO_SEIN(t) · s_a(t) · (IEOD/portal), con s_a = cuota del área en la misma media hora de los últimos 7 días cerrados. **Solo en X4** (origen fijo ≥16:00 de D−1). No entra en X1 |
| P6 | Pronóstico del operador en Ceuta | Solo si REE publica series "prevista/programada" para Ceuta (no verificado: las respuestas descargadas en `downloads/ceuta_ree_summers/*.jsonl` solo traen `dem` y generación). Sería el análogo del PDO en el acto 2 |

Resoluciones: Tetuán y Ceuta a 10 min (S_d = 144, S_w = 1008, H = 6); SEIN a 30 min (S_d = 48, S_w = 336, H = 2 y 48 rodante; H = 17..64 a origen fijo I-op; H = 49..96 a origen fijo I-pub); REData horario (S_d = 24, S_w = 168, H = 1).

Reglas:
- La "referencia más fuerte" se elige **ex ante en la ventana de selección** y se congela. Se reporta junto a la elección ex post en el test, que favorece a la referencia.
- **Skill doble**: 1 − MAE/MAE_B0 y 1 − MAE/MAE_fuerte, siempre en las mismas filas y horizontes.
- **Criterio de éxito.** La regla "mejor de 3" de `docs/negocio.md` §8 se fijó antes de modelar (`short-paper.qmd:93-98`). Cambiarla después de ver los resultados está justificado, pero es una decisión **posterior** y se declara así. El paper reporta **ambos** criterios (mejor de 3 y referencia más fuerte) y dice cuándo y por qué cambió el principal.

### 2.2 Protocolo de evaluación común

- **Mismas filas** para todos los modelos y referencias de una comparación (intersección válida).
- **Etiqueta obligatoria** en cada resultado: *confirmatorio* (ventana no vista al registrar), *reanálisis de ventana explorada* o *exploratorio*.
- **Ya medido no es hipótesis.** Un número que ya se calculó (aunque sea en un script del scratchpad) se reporta como *reanálisis* con su fuente y queda fuera de las familias confirmatorias de Holm. Se le puede dar un IC y un p dentro de su propia familia de reanálisis.
- **Ventanas por acto:**

| Acto | Selección | Reporte | Estado |
|---|---|---|---|
| Tetuán | CV anidada **dentro de cada fold externo** del rolling mensual Mar–Oct (la selección usa solo meses anteriores al fold) | Error del fold externo únicamente, nunca el de selección; validación 13-sep a 6-nov y test 6-nov a 30-dic como reanálisis | **Todo Tetuán es reanálisis o exploratorio.** `historico.md` §1 eligió razón + global mirando los folds Mar–Dic y el MAPE del test, así que no queda ninguna ventana confirmatoria |
| Ceuta | Verano 2021 (2020 solo como sensibilidad: atípico por COVID) | Veranos 2022-26 | 2022-26 ya mirado: reanálisis |
| SEIN | 2025 (y un segundo año: corte ≤2023 evaluado en 2024) | 2026-01-01 a 10-17/22 | 2026 explorado (auditoría D3, D16): reanálisis |
| SEIN prospectivo | — | Solo datos posteriores al hash de congelamiento (X5) | Única ventana confirmatoria y libre de contaminación de FM |

- **Métrica primaria:**
  - Tetuán: MAE, reportado como skill (adimensional) porque la unidad kW no está documentada; MAPE como apoyo.
  - Ceuta: MAPE, sin los 4 valores no positivos (se reporta cuántas filas se excluyen) y con MAE como control.
  - SEIN por área: MAE en MW.
  - SEIN total frente al PDO: MAPE sobre el Ejecutado del portal; MAE como secundaria.
- **Métricas secundarias:** RMSE, sesgo, MAE en hora pico (definida con años de entrenamiento), subestimación >5 % en pico, cuantiles q95/q97.5/q99 de |error|, error de rampa a 30 min y 2 h, acierto de la hora del pico (±1 h). Las métricas de reserva se reportan en MW y MW·h; **no se convierte a dinero** sin un precio oficial citado.
- **Unidades y zonas de Tetuán:** kW "declarado por los autores, sin documentar"; correspondencia Z2 = Boussafou, Z3 = Smir "inferida de figuras".
- **Entregable frente a criterio de éxito.** "Una tabla" o "una figura" es un entregable de trabajo, no un criterio. Cada experimento separa **Entregable** de **Criterio de decisión** (qué resultado cambia qué afirmación del paper).

### 2.3 Pruebas estadísticas

- **Diebold-Mariano** con corrección de Harvey-Leybourne-Newbold, sobre diferencias de pérdida **agregadas por día**, con varianza HAC (Bartlett, ancho por la regla de Andrews, al menos H−1 pasos).
- **Bootstrap circular por bloques** con 10,000 réplicas: bloques de 1 día a t+6 y a 1 h; de 7 días a 24 h y a origen fijo diario. Bootstrap estacionario (Politis-White) como sensibilidad (después de TB1).
- **Holm** dentro de familias declaradas de antemano en el preregistro (por ejemplo, Tetuán: 3 zonas × 3 referencias fuertes = 9 pruebas, familia de reanálisis). Benjamini-Yekutieli como dato adicional.
- **Model Confidence Set** (Hansen, α = 0.10, estadístico Tmax) para cualquier selección entre varios modelos. Como el MCS entrega un conjunto y no una elección, se preregistra una **regla de desempate**: dentro del MCS se elige el modelo más simple según un orden fijado de antemano (referencias < Ridge < HGB/RF < XGB/LightGBM < FM sin ajuste < FM ajustado < combinación); con empate de complejidad, el de menor costo de inferencia.
- **Equivalencia.** Las hipótesis de "empata" o "queda a ±x %" se prueban con TOST, con el margen declarado en el preregistro (por ejemplo, ±10 % del MAE de B4 en H13a; ±0.10 pts de MAPE frente al PDO en X4).
- **Tendencias.** Las hipótesis de "mejora hasta k" se prueban con un contraste de tendencia declarado (pendiente de MAE frente a log2(k) con IC por bootstrap de bloques, más una prueba de Jonckheere-Terpstra sobre los cortes).
- **Efecto mínimo detectable (MDE)** con 80 % de potencia para cada ventana, **calculado para el procedimiento que se va a usar** (DM a n fijo en ventanas cerradas; secuencias anytime-valid en la ventana prospectiva, que tienen menos potencia) y publicado en métodos. Un "no distinguible" se interpreta siempre frente a su MDE.
- **Tamaño empírico de las pruebas.** Un solo par placebo no estima un tamaño. Se usan muchos pares de pérdida esperada igual: (i) inversión aleatoria de signo de diferencias reales de pérdida, centradas; (ii) subventanas disjuntas del mismo modelo frente a sí mismo desplazado; (iii) pares de modelos estocásticos (RF con semillas distintas, o modelos con bagging o submuestreo activado). El HGB de Tetuán y Ceuta es **determinista** (`early_stopping=False`, `rolling.py:109-111`), y LightGBM sin bagging también: sus semillas no varían nada y no sirven como placebo. La prueba "delta contra sí mismo con origen permutado" se descarta por degenerada.
- **Cobertura de intervalos:** Kupiec y Christoffersen necesitan indicadores Bernoulli. La fracción diaria de fallos no lo es. Indicador primario: **un horizonte fijo por día** (declarado: la media hora de las 19:00 en el SEIN, t+6 de las 20:00 en Tetuán) → serie Bernoulli diaria. Como complemento, el conteo diario de fallos sobre los 48 horizontes, con un modelo beta-binomial con sobredispersión.
- **Ventana prospectiva:** secuencias de confianza válidas en cualquier momento (anytime-valid), porque los resultados se mirarán de forma continua. Su MDE y la fecha de parada estimada se calculan por simulación con esas secuencias (no con DM a n fijo) y se publican.

### 2.4 Regla de información

- Toda variable debe tener marca temporal de fuente ≤ origen. `verificar_regla_de_informacion` se extiende a **todas** las variables y filas (hoy cubre solo temperatura en 200 filas).
- **Rezagos ≥ 0.** Toda referencia y variable de rezago pasa por el `assert` de 2.1 respecto del último dato disponible en la vista.
- **Control positivo** como prueba unitaria del arnés: meter y(t+6) sin ruido en una variable debe bajar el MAE de Tetuán más de un 80 % y ser detectado por el verificador. **Control negativo**: objetivo permutado dentro de los días de entrenamiento debe quedar peor que la persistencia.
- **PDO:** el PDO de D se publica a las 16:00 de D−1. Es usable solo si el objetivo cae en D y el origen es ≥16:00 de D−1. Desde un origen entre 00:00 y 16:00 de D, el objetivo t+48 cae en D+1 y su PDO aún no existe. Los RDO posteriores al origen no se usan nunca. Se codifica como `assert`.
- **Asimetría de información frente al PDO.** El PDO se arma con declaraciones de agentes de las 08:00 de D−1 (informe: 16–40 h de anticipación). Un modelo con IEOD/SCADA hasta las 16:00 tiene más información que el programa. Por eso, el origen de 08:00 de D−1 es la **comparación de igual información** (la única que puede sostener "le gana al PDO"), y el de 16:00 es una **cota optimista**.
- **Vistas a origen fijo.** I-op: datos hasta el origen (IEOD como sustituto del SCADA); objetivo D a 17–64 pasos desde las 16:00 (33–80 desde las 08:00). I-pub: datos hasta las 24:00 de D−2; objetivo D a 49–96 pasos de la última observación → `prediction_length = 96`.
- **Clima:** ERA5 con forward-fill y rezago de 1 h (no interpolación hacia adelante); variante con rezago ≥5 días (latencia real). Pronósticos GFS con la regla de edición vigente y DEMORA de 8 h (`temperatura_pronosticada.py`).
- **Calendario** en hora local (Europe/Madrid en Ceuta, America/Lima en el SEIN). Una sola convención inicio/fin de periodo para feriados (`variables_sein.py:117-119` frente a `en_vivo.py:445-455`).
- **Hiperparámetros** siempre con búsqueda anidada dentro de cada fold, nunca ajustados en todo el entrenamiento y reusados en el rolling. Los modelos que se evalúan en validación se ajustan **solo con `entrenamiento`**, nunca con `desarrollo`.
- **Revisiones de datos** (ICEN con el método de dic-2024, IEOD corregible, Ejecutado del portal posiblemente preliminar, eventos descargados hoy): se declaran como amenaza a la validez. El CSV del portal del 22-nov se congela con sha256 y se vuelve a comparar con lo que publique el portal más adelante (X5).
- **Etiqueta del "24 h" en vivo.** El pronóstico en vivo se emite hacia las 10:00 del día objetivo. Se rotula "24 h rodante, emitido el mismo día", **no** "día siguiente".

### 2.5 Rupturas y regímenes

- **Definiciones fijadas antes de evaluar y solo con datos de entrenamiento:** horas pico (top-4 por área, 2016-24), días cálidos (deciles mensuales de temperatura 2016-24), categoría ICEN disponible en el momento de emisión.
- **Tetuán:**
  - Ventanas: 24-26 oct (traspaso Z1→Z2), Z3 del 8 al 18-nov, feriados 6-nov, 18-nov y 1-dic, Ramadán (fechas aproximadas, con ±1 día de sensibilidad).
  - Como varias se encontraron mirando el test, se reportan **solo como análisis de sensibilidad** (con y sin cada ventana), no como hipótesis confirmatorias.
  - La validación cruza el quiebre del 25-oct: la selección se reporta por régimen y la nueva selección se hace con CV anidada por fold externo.
- **SEIN:**
  - El Niño Costero (2017, 2023, 2026) se reporta como **tabla descriptiva** del error del PDO y del modelo por evento. Con tres eventos no hay inferencia; 2017 además está confundido por huaicos y salidas de líneas.
  - Ventanas de evento fijadas con los comunicados del ENFEN, no con los datos.
  - Cuarentena 2020 con la tabla curada `cuarentena_pe_2020` (5 fases) y corte de la segunda ola de 2021 (X21).
  - Lunes feriado y decretos no laborables: X9.

### 2.6 Contaminación del preentrenamiento

- Tabla de estado del corpus por modelo y serie (UCI 849, UCI 321, "spain", COES, Ceuta) en el paper.
- **Controles limpios** en todo panel de FM:
  - Toto-2 313m: ya es el checkpoint base (sin datos públicos según el proveedor). El que no es limpio es el 2.5B-FT. Se cuenta **una** vez.
  - TabPFN-TS-3 en modo **LOCAL** (solo sintéticos). Desde v1.3.0 el modelo por defecto es TabPFN-3.5: hay que fijar el checkpoint `tabpfn-v3-regressor-v3_20260506_timeseries.ckpt` y las versiones de paquete. TabPFN-TS descarta las covariables solo pasadas, así que el clima entra como pronóstico (covariable futura).
  - ChakraTS-OS-10M **no** sirve de control limpio (corpus no auditable, licencia no comercial con acceso restringido).
  - TabPFN en modo CLIENT, la API de ChakraTS y PDM no se usan, porque envían datos al proveedor (política del CIP).
- **Qué no dicen los controles.** Toto-2 313m y TabPFN-TS-3 son más débiles (TabPFN-TS-3 ocupa el puesto 22 de 42 en fev) y no aceptan covariables pasadas. La distancia entre un control limpio y un FM mezcla capacidad con posible fuga, así que no sirve como prueba de contaminación. Solo indica cuánto se pierde con un modelo verificablemente limpio.
- La única ventana libre de contaminación es la prospectiva posterior a la fecha de publicación de cada checkpoint (X5).
- Prueba formal de contaminación, validada con controles positivos y negativos: X16 (Nivel 3). Sin ella, el paper dice "no auditable" y muestra los controles limpios.

### 2.7 Semillas

- Las semillas solo se usan en modelos estocásticos: RF, FM ajustados y GBM con submuestreo o bagging activado. En HGB con `early_stopping=False` y en LightGBM sin bagging no varían nada, y no se reporta "rango entre semillas" para ellos.
- 3 semillas por defecto; 5 en la configuración titular. Se reporta el rango entre semillas.
- La robustez se mide también como **varianza de selección** (cortes de ajuste distintos, años de evaluación distintos), no solo de semilla (hoy 0.19 MW en ftcal).

### 2.8 Registro previo de hipótesis

- **Archivo:** `docs/preregistro-evaluacion.md`, con cada hipótesis, su etiqueta (confirmatoria, reanálisis, exploratoria), métrica primaria, prueba, familia de Holm, α, dirección esperada, margen de equivalencia, MDE y regla de parada.
- **Commit y tag `prereg-v1` antes de correr X1** (paso 2 de 5.1). El SHA se escribe en cada CSV de resultados. El MDE, si se calcula después, entra como enmienda fechada (`prereg-v1.1`), calculada solo con series de referencias y antes de cualquier comparación modelo-referencia en una ventana confirmatoria.
- **Registro en etapas** para la prueba en vivo:
  - `prereg-v1`, antes del primer objetivo evaluado: modelos que **ya existen** (RF M0, XGB global, ftcal, ftcal+rango, ftcal+calor, combinación), referencias, la comprobación de la columna del PDO y la etiqueta "24 h rodante, emitido el mismo día".
  - `prereg-v2`, cuando X4, X7 y **X12-SEIN** estén congelados (no hace falta X12 de Tetuán y Ceuta): modelo de X4 en vista I-pub, capa de corrección del PDO y método de intervalos.
  - Cada ventana confirmatoria empieza **estrictamente después** de su hash. Lo que va del 23-oct al hash correspondiente queda como "explorado parcial".
- Opcional: registro externo con marca de tiempo (OSF) o commit firmado con hash compartido.
- Toda desviación del preregistro se reporta, incluido el cambio de criterio de éxito de 2.1.

---

## 3. Experimentos por niveles

Resumen de la estructura:

| Nivel | ID | Experimento | Cuándo |
|---|---|---|---|
| 1a | X0-min | Referencias en `REFERENCIAS`, `assert` de rezagos, DM con bootstrap circular, `prereg-v1` | Antes de TB1 |
| 1a | X1-min | Escalera de referencias sobre predicciones **ya guardadas** | Antes de TB1 |
| 1a | X4-CPU | PDO frente a Δsemana y suma de áreas existente (exploratorio) | Antes de TB1 |
| 1a | X5-col | Colectores prospectivos y congelamiento del CSV del portal | Hoy |
| 1a | T | Corrección de textos (sección 6.2) | Antes de TB1 |
| 1b | X0 | Arnés completo: Holm, MCS, bootstrap estacionario, placebo con muchos pares, MDE | Después de TB1 |
| 1b | X1 | Escalera completa: rolling de Tetuán y SEIN 2023-25 reentrenados | Después de TB1 |
| 1b | X2 | Tetuán: reanálisis pareado con validación reajustada solo en `entrenamiento` | Test antes de TB1 (en X1-min); validación después |
| 1b | X3 | Réplica PR-03: R0 congelado, R1 nuevo, versión por área | Después de TB1 |
| 1b | X4 | Cara a cara con el PDO (08:00 igual información, 16:00 cota, I-pub) | Después de TB1 |
| 1b | X5 | Prueba en vivo preregistrada | Continuo |
| 1b | X6 | Aleatoria frente a cronológica y ventana de IRSEC | Después de TB1 |
| 2 | X7 | El modelo como corrector del PDO | |
| 2 | X8 | Clima real frente a simulado | |
| 2 | X9 | Feriados y lunes después de feriado | |
| 2 | X10 | Objetivo y normalización (2×2), con rolling anidado | |
| 2 | X11 | Ceuta y Melilla: costo de no haber visto un verano | |
| 2 | X12 | Calibración de intervalos fuera de muestra | |
| 2 | X13 | FM en Tetuán y Ceuta con controles limpios | |
| 2 | X14 | Varianza de selección y búsqueda justa en el SEIN | |
| 2 | X15 | Forense de UCI 849 | |
| 2 | X21 | Saneamiento de variables y datos del SEIN (nuevo) | |
| 3 | X16 | Prueba de contaminación de FM validada | |
| 3 | X17 | Ajuste fino: escalado de datos, LoRA y otros FM | |
| 3 | X18 | Ajuste fino entre sistemas | |
| 3 | X19 | Metaauditoría codificada de UCI 849 | |
| 3 | X20 | Intradía y reprogramación (RDO), condicionado | |

En la sección 3.4 está lo descartado y por qué.

### 3.0 Nivel 1a: lo mínimo antes de TB1

Lo que limita antes de TB1 es el tiempo de las personas, no la GPU: son unos 10 días de un equipo que además prepara la exposición, la demo y el paper. El Nivel 1a es todo lo que entra, y todo es CPU.

1. **X5-col (hoy).** Colectores de solo añadido para el PDO al publicarse, el pronóstico de tiempo real del COES y el Ejecutado del portal (ver X5). Congelar el CSV del portal del 22-nov con sha256.
2. **`prereg-v1`.** Definiciones de 2.1 (con la regla S = ⌈H/S_d⌉·S_d), protocolo de 2.2, pruebas de 2.3, familias de Holm y etiquetas. Tag antes del paso 4.
3. **X0-min.** Agregar B2, B3, B4, B9 y B10 a `REFERENCIAS`. `assert` de rezagos ≥ 0. Una función de DM-HLN sobre pérdidas diarias con bootstrap circular por bloques (extender `evaluacion.bootstrap_diferencia_mae`).
4. **X1-min.** Recalcular la escalera con predicciones **ya guardadas**, sin reentrenar: Tetuán test (`predicciones_prueba_zona*.csv` y HGB semanal), SEIN validación 2025 (nb02_sein celda 40), nb03 2026 (incluida la política C) y nb04. Todo rotulado reanálisis.
5. **X4-CPU.** PDO frente a Δsemana (con la regla de rezago) y suma de las áreas existentes, en el SEIN total, rotulado *exploratorio*.
6. **T.** Corrección de textos (6.2).

Todo lo demás va después de TB1.

### 3.1 Nivel 1b: imprescindible para que el paper sea defendible

#### X0. Arnés común, MDE y preregistro

- **Pregunta.** ¿Las pruebas pareadas mantienen su tamaño nominal en estas series autocorrelacionadas, y cuál es el efecto mínimo detectable de cada ventana con el procedimiento que se va a usar?
- **Hipótesis.**
  - H0a: DM-HLN sobre diferencias diarias tiene tamaño empírico de 3–7 % a α = 0.05 en cada ventana; el DM por periodo sin agregar rechaza de más (>20 %).
  - H0b: MDE al 80 % de potencia aproximado de 6–9 % del MAE en el test de Tetuán, ~3 % en el rolling Mar–Dic, ~1.5–2 % en el SEIN 2026 a 1 h y ~4–6 % a 24 h con bloques de 7 días. Por tanto, efectos de 0.09–1.48 MW a 24 h quedan en su mayoría bajo el MDE. Para la ventana prospectiva, MDE de las secuencias anytime-valid (mayor que el de DM a n fijo).
  - H0c: el arnés reproduce las cifras ancla (tolerancia 0.1 kW o 0.01 pts): Tetuán B2 567.5 / 489.9 / 392.1; B4 480.7 / 413.2 / 368.2; Ceuta B3 2.06 %; SEIN total `y(t−2)+Δsemana` 2025 MAE 85.0 MW; nb02 462.5 / 429.4 / 429.1; ftcal Centro 24 h 2025 75.6 MW; PDO 2026 en la ventana de test 111.3 MW (y 110.5 en 2026-01-01 a 11-22, n = 15,685, como segunda ventana rotulada).
- **Datos.** UCI 849 local; series de error del SEIN en Drive; CSV del portal congelado.
- **Protocolo.**
  1. Paso 0: bajar de Drive (desde Colab si rclone sigue roto) `reportes/modelado/predicciones_prueba_zona*.csv`, `reportes/historico/*`, `reportes/sein/modelado/*`, `prueba_2026/*` y `fundacionales/*`, con su sha256. Responsable y fecha: por asignar (ver 7.3); bloquea X1-min.
  2. Nivel 1a: ver 3.0.
  3. Después de TB1: Holm, MCS con regla de desempate, TOST, bootstrap estacionario; estudio de tamaño con muchos pares placebo (2.3) y nulos ARMA/GARCH ajustados a las series de diferencias (5,000 series por ventana; desplazamientos de 1–15 % del MAE para la potencia); MDE de la ventana prospectiva por simulación de las secuencias anytime-valid.
  4. Controles positivo y negativo de fuga (2.4) como pruebas unitarias, junto con el `assert` de rezagos.
- **Modelos.** Ninguno nuevo.
- **Referencias.** Se implementan aquí.
- **Métricas y pruebas.** Tamaño y potencia empíricos por (prueba, ventana, bloque); tabla de MDE; pruebas unitarias.
- **Entregable.** Tabla de MDE para métodos; pruebas unitarias en CI.
- **Criterio de decisión.** Una configuración de prueba con tamaño fuera de 3–7 % se descarta antes de cualquier comparación real. `prereg-v1` existe antes de X1.
- **Cómputo.** CPU: ~2 CPU-h en 1a y ~6 CPU-h para el estudio completo. Laptop o Colab gratuito.
- **Código que reutiliza.** `src/tetouan_power_forecast/evaluacion.py:36` (`bootstrap_diferencia_mae`), `experimentos/temperatura/evaluar.py:161` y `experimentos/sesgo/remedios.py:252` (bloques semanales), `variables.py:23`, `variables_sein.py:29`, `pipeline_sein.verificar_regla_de_informacion`, scripts ancla del scratchpad.
- **Dependencias.** `prereg-v1` (que se escribe en paralelo). Bloquea todo lo demás.
- **Riesgos.** Acceso a Drive (token vencido). Los ajustes ARMA pueden subestimar la dependencia en colas; el bootstrap estacionario sirve de contraste.

#### X1. Escalera de referencias fuertes en los tres actos

- **Pregunta.** ¿Cuánto de cada mejora titular queda frente a B2–B10 y C-RT (y P1–P3 en el SEIN total)?
- **Ya medido (reanálisis, fuera de las familias confirmatorias).**
  - Tetuán: Z3 pierde contra B2 en marzo, mayo, junio y julio (`deltas_nb02.py`). Antes H1a.
  - Ceuta: V4 sin verano pierde contra B3 en 5 de 5 veranos (`ceuta_baselines.py`). Antes H1b.
- **Hipótesis.**
  - H1c (SEIN por área, 2026, reanálisis): a 1 h, el skill del RF M0 frente a `y(t−H)+Δsemana` cae a ~15–35 % en Norte y Centro y a ≤15 % en Sur; a 24 h rodante, el IC del skill de Sur frente a la referencia más fuerte (B3, B9 o B10; B2 excluida a 24 h) incluye 0.
  - H1d (SEIN, rolling 2023-25 reentrenado): "108/108 área-meses" baja a ≤95/108 frente a la referencia más fuerte.
  - H1e (nueva): a 24 h rodante, B9 o B10 es la referencia más fuerte en al menos 2 de 3 áreas en la ventana de selección 2025.
- **Datos.** UCI 849; veranos de Ceuta (scratchpad `downloads/ceuta_ree_summers/`, licencia académica, no commitear); predicciones de nb02, nb02_sein, nb03, nb04 (Drive); CSV del portal.
- **Protocolo.**
  - Nivel 1a (X1-min): mismas filas que cada resultado guardado, sin reentrenar.
  - Nivel 1b: lo que no está guardado se **reentrena**. El rolling de Tetuán se rehace con el arnés de X10 (no hay predicciones por fila del rolling) y el rolling SEIN 2023-25 se rehace para H1d (`origen_movil.csv` solo tiene agregados).
  - B5 y B6 se ajustan dentro de cada fold. La referencia más fuerte se elige en la ventana de selección. Reporte por hora pico, tipo de día y mes. B8 (MSTL-ETS) queda para después.
  - P4 (por área) y P5 **no** entran en X1: P4 sale de X3 y P5 de X4.
  - El "24 h" en vivo se rotula según 2.4.
  - Sensibilidad: excluir los 48 periodos de 2026 con N+C+S ≠ SEIN (diagnóstico en X21).
- **Modelos.** Los ya elegidos: HGB global de nb02 y HGB semanal; V0/V4 de Ceuta; RF M0, XGB global, política C, ftcal y combinación del SEIN.
- **Referencias.** B0–B10 (B2 excluida a 24 h rodante; B7 y B7-sf en Tetuán), C-RT, P1–P3.
- **Métricas y pruebas.** MAE, MAPE, skill doble; DM-HLN y bootstrap (bloque según horizonte); Holm por acto × horizonte; MCS con desempate para la elección RF frente a XGB; prueba de signo para los conteos de meses.
- **Entregable.** Una sola ruta de código que produce la tabla de los tres actos y reproduce las cifras ancla de X0.
- **Criterio de decisión.** Toda frase titular del paper se reescribe con skill doble y p ajustados, salga lo que salga. Si H1d se cumple, "108/108" sale del resumen.
- **Cómputo.** CPU: X1-min <2 h (Tetuán y Ceuta en laptop; SEIN en Colab CPU leyendo Drive). Nivel 1b: rolling SEIN 2023-25 reentrenado ~10–20 CPU-h (estimación, no medición); rolling de Tetuán incluido en X10. +6 CPU-h si se agrega B8.
- **Código que reutiliza.** Scratchpad `deltas_nb02.py`, `ceuta_baselines.py`, `pdo_windows.py`; `modelado_sein.py:149` (`mejor_referencia`); `fundacionales.py:47` (`mae_mejor_referencia`) y `:97` (`comparar`); `evaluacion.py:52` (`plegados_mensuales`); `experimentos/ceuta/validacion.py:36`.
- **Dependencias.** X0, `prereg-v1`.
- **Riesgos.** Que las predicciones de Drive no estén completas.

#### X2. Tetuán: reanálisis pareado del modelo de nb02

- **Pregunta.** ¿El HGB global en razón le gana a B2, B3, B4 y B9 en las filas exactas de nb02, con una significancia que el paper pueda declarar?
- **Etiqueta.** *Reanálisis de ventana explorada*: las cifras puntuales ya se conocen y la arquitectura se eligió mirando los folds Mar–Dic y el test. Lo que se prueba es la significancia. Ningún resultado de Tetuán es confirmatorio.
- **Hipótesis** (familia de reanálisis de Holm: 3 zonas × {B2, B3, B4}).
  - Frente a B2: Z1 −18.5 % y Z2 −12.3 % rechazan con p_Holm < 0.05; Z3 +9.4 % (peor) probablemente no significativo, se reporta el signo.
  - Frente a B4: Z1 −3.8 % no significativo; Z3 +16.5 % (peor) significativo.
  - En validación, el modelo reajustado solo con `entrenamiento` no le gana a B4 en ninguna zona.
- **Datos.**
  - Test: `predicciones_prueba_zona{1,2,3}.csv` (Drive), comprobando MAE 462.49 / 429.44 / 429.05 (±0.1 kW).
  - Validación: **no hay predicciones guardadas** y `modelo_final.joblib` se ajustó con entrenamiento + validación (nb02 celdas 5 y 39), así que no sirve. Se reajusta con los hiperparámetros de `busqueda.csv` **solo con `entrenamiento`** y se predice la validación.
- **Protocolo.** Validación: 7,835 filas (13-sep 01:20 a 6-nov 11:00); test: 7,841 filas (6-nov 12:10 a 30-dic 22:50). Comparador reentrenado (HGB semanal) en la misma tabla. Estratos descriptivos (fuera de la familia de Holm): pico 19–22 h, laborable/fin de semana, feriados, Ramadán, Z3 8–18 nov, después del 25-oct.
- **Modelos.** HGB de nb02 (test); HGB reajustado en `entrenamiento` (validación); HGB semanal; Ridge reajustado solo en `entrenamiento`.
- **Referencias.** B0–B10, B7-sf.
- **Métricas y pruebas.** MAE, RMSE, MAPE, R², skill doble; DM-HLN diario, bootstrap de 1 día; Holm sobre 9 pruebas.
- **Entregable.** Tabla de Tetuán con DM e IC.
- **Criterio de decisión.** "41–56 % bajo la mejor referencia" (`short-paper.qmd:74-80`, `paper.md:389-432`) se reemplaza por skill frente al delta con p ajustados e IC. "Vara exigente" (`qmd:423`) se retira salvo que Z1 y Z2 rechacen.
- **Cómputo.** CPU, <1 h (test en 1a, validación en 1b).
- **Código que reutiliza.** nb02 celdas 5, 25, 29, 31, 39, 40; `evaluacion.subestimacion_pico`, `mae_por_grupo`; scratchpad `deltas_nb02.py`.
- **Dependencias.** X0; acceso a Drive (`busqueda.csv`).
- **Riesgos.** Determinismo entre versiones de librerías al reajustar.

#### X3. Réplica del PR-03 (Anexo A) como referencia explícita

- **Pregunta.** ¿Cuánto del 1.50 % del PDO explica el método de días similares por sí solo, y cuánto le gana el repo al método oficial por área, donde no existe PDO?
- **Ya medido.** R0 simplificado (sin Usuarios Libres ni feriados) ya da 2.2–2.5 % en 2025 (4.3 % en 2020) (`informe.md:306`, `tetouan-research/scripts/pr03_replica.py`). La antigua H3a se **retira**: no es una predicción.
- **Hipótesis.**
  - H3b: R1 (factores de feriado estimados con años previos) reduce la brecha R0 − PDO en feriados y en el MAPE anual.
  - H3c: por área, el mejor modelo a origen fijo de X4 le gana a R1 en MAE en ≥25 % en Norte y Centro y en ≥10 % en Sur, en 2025 y 2026.
- **Regla de congelamiento.** R0 es `pr03_replica.py` **tal cual**, congelado por sha256: se implementó después de conocer la cifra, así que no se retoca. R1 y la versión por área se implementan desde el texto normativo y se congelan **antes** de calcular su error, idealmente por alguien que no vio las cifras de R0. No hay cláusula de "revisar hasta que dé el rango".
- **Datos.** CSV del portal; silver IEOD por área (Drive); `tablas/feriados_pe_2015_2026`.
- **Protocolo.** `src/tetouan_power_forecast/pr03.py` (en una rama nueva) que envuelve R0 y agrega R1 y la versión por área. Últimos 5 días completos del mismo tipo disponibles en el origen (sábado, domingo y lunes por separado; martes a viernes juntos); descarte de valores a más de 5 % de la mediana por media hora; tendencia lineal por MCO sobre medias diarias. Vistas de información: igual información (08:00 de D−1), operador (16:00 de D−1) y pública (IEOD hasta 24:00 de D−2). R2 (Usuarios Libres ejecutados como oráculo) **se aplaza** hasta que exista un lector de la hoja DEMANDA_UL en `coes.py`, y se rotulará como cota superior, no como réplica.
- **Modelos.** R0, R1 deterministas.
- **Referencias.** PDO, PSO, naive de 7 días, Δsemana a origen fijo (S = ⌈H/S_w⌉·S_w).
- **Métricas y pruebas.** MAPE y MAE por año, hora, tipo de día y feriado; descomposición PDO − R0 − R1; DM-HAC (rezago 7 sobre la pérdida diaria), bootstrap de 7 días, Holm sobre áreas × variantes.
- **Entregable.** Tabla de la réplica y descomposición de la brecha con el PDO.
- **Criterio de decisión.** H3c con IC que excluye 0 tras Holm en ≥5 de 6 combinaciones área × año → el paper puede decir que el modelo supera al método oficial por área.
- **Cómputo.** CPU, <1 h.
- **Código que reutiliza.** `pr03_replica.py`; `coes.py`; `tablas/feriados_pe_2015_2026`; `docs/peru/tablas.md` §2 y §8.3; informe §5.1 y §5.3; scratchpad `oper_anchor.py`.
- **Dependencias.** X0, X1. H3c depende de X4.
- **Riesgos.** La lectura del PR-03 (texto de 2011) no está validada por un especialista y puede haber una versión vigente distinta: confirmar la versión y declararla. La agrupación de Usuarios Libres de Sur en 2026 está mal.

#### X4. Cara a cara con el PDO en su estructura

- **Pregunta.** Con la misma información que tuvo el PDO (origen 08:00 de D−1), ¿el mejor modelo del repo iguala o supera al PDO en el SEIN total? ¿Y en la cota optimista (16:00) y en la vista pública?
- **Hipótesis** (signo esperado negativo, registrado de antemano).
  - H4a (I-op, 08:00, igual información): suma de áreas con ftcal reajustado: MAPE 2025 de 1.60–2.00 % frente a 1.50 % del PDO. No le gana.
  - H4a' (I-op, 16:00, cota optimista): MAPE 2025 de 1.55–1.90 %.
  - H4b: modelo SEIN directo sobre el Ejecutado del portal a ±0.15 pts de la suma de áreas.
  - H4c (I-pub, ftcal-96): MAPE 1.9–2.4 %, peor que el PDO en ≥15 %.
  - H4d (tabla lateral a 1 h): P3 (1.03 % en 2025) le gana a todo modelo de 1 h por suma de áreas.
  - Margen de equivalencia (TOST): ±0.10 pts de MAPE. "Competitivo" solo si el extremo superior del IC de ΔMAPE < +0.10 en 2025 y 2026. "Le gana" solo con el origen de **08:00** y con IC que excluye 0 en 2025, 2026 y la ventana prospectiva.
- **Datos.** CSV del portal congelado (Ejecutado, PDO, PSO, 2017-01-01 a 2026-11-22); silver IEOD por área; GFS Previous Runs desde 2021-03.
- **Protocolo.**
  - Orígenes diarios a las 08:00 de D−1 (igual información, principal), 12:00 y 16:00 (cota optimista); objetivo las 48 medias horas de D.
  - Vista I-op (IEOD como sustituto del SCADA hasta el origen; pasos 33–80 desde las 08:00 y 17–64 desde las 16:00). Vista I-pub (IEOD hasta 24:00 de D−2; pasos 49–96, `prediction_length = 96`).
  - Referencias estacionales con S = ⌈H/S_d⌉·S_d (pasa el `assert` de X0).
  - Perímetro: evaluación sobre el Ejecutado del portal; las áreas IEOD se llevan al portal con una razón mes × media hora estimada con datos ≤2024.
  - P5 (PDO por área) solo aquí, en orígenes ≥16:00 de D−1.
  - Fase CPU (1a): PDO, PSO, Δsemana y suma de predicciones existentes en las mismas filas, rotulado *exploratorio*. Fase CPU (1b): RF/XGB directos con la anticipación como variable, en las tres vistas.
  - Fase GPU: refactor de `ajuste_fino.py` (`prediction_length` 48 → 80 para I-op desde las 08:00 y 96 para I-pub; aserción de corte como parámetro; rutas `/content` a configuración). ftcal-80 y ftcal-96 con corte ≤2024 y ≤2023 (segundo año de selección, evaluado en 2024); 3 semillas.
  - **El modelo de X4 en vista I-pub es el que entra a `prereg-v2`** como variable primaria (es lo único que se puede correr en vivo a día siguiente, porque el anexo llega a las 09:45 de D+1). La "combinación" actual es un modelo rodante de 48 pasos, no uno a origen fijo, y no sirve para esa comparación.
  - Métricas operativas (de OP7) como secundarias: cuantiles de |error|, rampas, error y hora del pico, en MW.
  - Tabla descriptiva de El Niño 2017, 2023 y 2026 (PDO frente a modelo).
  - El veredicto final queda condicionado a la comprobación de la columna del PDO con las instantáneas de X5.
- **Modelos.** RF/XGB directos, ftcal-80, ftcal-96, Chronos-2 y Simons sin ajuste.
- **Referencias.** P1, P2, P4 (R0, R1), P5, naive de 7 días, Δsemana y B4 a origen fijo (con S corregido), B9, C-RT.
- **Métricas y pruebas.** MAPE (primaria), MAE, sesgo por hora y por anticipación (8–16, 16–24, 24–32, 32–48 h); percentiles del MAPE diario frente a los del PDO (p50/p90/p99 = 1.25 / 2.40 / 4.56 % en 2025); DM-HLN diario, bootstrap de 7 días, TOST; Holm sobre modelos × orígenes × vistas.
- **Entregable.** Tabla y figura de error por hora y anticipación frente al PDO; `programacion_diaria` lleno en `app/backend/contrato.py:131` y `pronosticador_real.py:379`.
- **Criterio de decisión.** Cierra G3 y el issue #9. El párrafo "competitivo en orden de magnitud" (`short-paper.qmd:345-350`) y la limitación de `qmd:410-411` se reescriben según el resultado de TOST con origen de 08:00. Si solo se gana a las 16:00, el paper dice "con más información que el programa".
- **Cómputo.** CPU ~5 CPU-h; GPU ~7 A100-h (2 largos × 2 cortes × 3 semillas a ~26–30 min, más inferencia) + ~1 L4-h.
- **Código que reutiliza.** `experimentos/fundacionales/ajuste_fino.py:37-38`, `fm_bench.py` (reanudación), `chronos2_variantes.py`, `modelado_sein.py`, `temperatura_pronosticada.py`, spec §8.2.1 (rama `origin/feature/spec-peru`), scratchpad `pdo_windows.py`, `oper_anchor.py`.
- **Dependencias.** X0, X1, X3 (R0/R1); X8 para la variante con temperatura real (sin ella, se corre sin clima); X5 para la ventana prospectiva y la comprobación del PDO.
- **Riesgos.** La columna "Programación Diaria" podría no ser siempre el PDO original (confianza media). Diferencia de perímetro portal/IEOD (+1–1.5 %). 2026 ya explorado.

#### X5. Archivo prospectivo y prueba en vivo preregistrada

- **Pregunta.** Sobre datos que nadie vio y posteriores a la publicación de todos los checkpoints, ¿se sostienen las conclusiones frente a referencias fuertes y frente a los productos del COES?
- **Hipótesis** (se registran en dos etapas; ver 2.8).
  - `prereg-v1`. Todas sobre el "24 h rodante, emitido el mismo día" (no día siguiente):
    - (a) cobertura del 80 % de ftcal+rango con ACI (γ = 0.2 congelado) en 75–85 %;
    - (b) la combinación le gana a B3 y a B9 en Centro;
    - (c) sesgo de Centro dentro de ±30 MW tras la recalibración elegida;
    - (d) la columna "Programación Diaria" obtenida después coincide con la instantánea del PDO tomada entre las 16:00 y las 18:00 de D−1 en ≥95 % de los días (vale para los días futuros; para 2017–2026 hay que **suponer** que la política del portal no cambió, y se declara);
    - (e) la ganancia de los FM sobre el RF queda a ±30 % de la de 2025;
    - (h) en el 10 % de días más cálidos de Centro, +calor baja el error del pico (la única prueba confirmatoria de lo que PR #55 ya midió en 2025-26).
  - `prereg-v2`: (f) la capa de corrección de X7 (vista I-pub) tiene MAE ≥5 % menor que la instantánea del PDO; (g) el modelo de X4 en I-pub no le gana al PDO.
  - Variable primaria de v2: razón de MAE **modelo de X4 en I-pub**/PDO en el SEIN total a día siguiente.
- **Datos.** Portal del COES en vivo, IEOD diario, Open-Meteo.
- **Protocolo.**
  1. **Hoy, sin dependencias:** extender `en_vivo.py` con colectores de solo añadido (sha256 y `emitido_en` en UTC). El registro ya guarda ftcal, +rango y +calor con sha256 (`en_vivo.py:540-557`); lo nuevo es:
     - el pronóstico automático de tiempo real del COES con su banda, cada 30 min (no tiene historial público: cada día no archivado se pierde);
     - el Ejecutado del portal cada 30 min (para medir latencia y vintage);
     - el PDO al publicarse (sondeo de 15:00 a 18:00 de D−1), el PSO y cada RDO;
     - la corrida GFS del día.

     Además: congelar el CSV del portal del 22-nov con sha256 y volver a descargarlo cada mes para medir revisiones del Ejecutado.
  2. Calcular el MDE de las **secuencias anytime-valid** (por simulación con las diferencias diarias de pérdida de 2025) **antes** de registrar, fijar con él la fecha de parada y publicarla. Con bloques de 7 días, un efecto de 5 % frente al PDO (f) probablemente exige varios meses: decir en el preregistro si la fecha cae antes de TB2.
  3. Congelar modelos (pesos por sha256), métodos de intervalo, γ y pesos de combinación en el commit de preregistro.
  4. Solo cuentan los pronósticos `ex_ante_estricto` emitidos después del hash.
  5. Inferencia con secuencias de confianza anytime-valid sobre diferencias diarias de pérdida; DM de horizonte fijo al final como dato adicional.
  6. Operación: VM o timer de systemd en la nube como respaldo, alerta si el portal deja de responder, respaldo diario. Renovar el token de rclone.
- **Modelos.** RF M0, XGB global, ftcal, ftcal+rango, ftcal+calor, combinación (requiere los pesos de Simons, 1.19 GB, en la máquina en vivo); luego el modelo de X4 en I-pub y la capa de X7.
- **Referencias.** Instantánea del PDO, RDO, PSO, pronóstico de tiempo real del COES, R0/R1, B3, B4, B9, controles limpios.
- **Métricas y pruebas.** MAE, MAPE, sesgo por hora, CRPS, pinball, PICP; secuencias de confianza; Kupiec y Christoffersen con el indicador de un horizonte por día (2.3); Holm solo dentro de la familia registrada.
- **Entregable.** Archivo del pronóstico de tiempo real del COES y de instantáneas del PDO, con las condiciones de uso del portal verificadas antes de publicarlo.
- **Criterio de decisión.** Todas las pruebas registradas se reportan tal como salgan. Es la única evidencia confirmatoria del paper.
- **Cómputo.** VM de CPU (~4 vCPU, 16 GB) durante toda la ventana; ~1 L4-h por mes si la combinación necesita GPU.
- **Código que reutiliza.** `en_vivo.py:99-101`, `:212` (clase Portal), `:540-557`, `:973-1020`; `experimentos/en_vivo/{diario.sh, entorno.sh, README.md}`; `experimentos/sesgo/remedios.py:497-508`; `app/backend/en_vivo.py`.
- **Dependencias.** Colectores: ninguna. `prereg-v1`: X0-min. `prereg-v2`: X4, X7, X12-SEIN.
- **Riesgos.** Endpoint de tiempo real no documentado; caídas de la máquina; ventana corta con poca potencia (por eso el MDE y la inferencia anytime-valid); condiciones de uso del portal.

#### X6. Partición aleatoria frente a cronológica y ventana de IRSEC

- **Pregunta.** ¿Cuánto del R² que reporta la literatura sobre UCI 849 viene del protocolo, y los errores publicados de IRSEC 2018 corresponden a un test cronológico desde ≈2017-10-03 17:00?
- **Hipótesis.**
  - H6a (**réplica**, no hipótesis nueva): RF solo con calendario, mismo instante: R² ≥ 0.99 con partición aleatoria frente a ≤ 0.20 cronológica (informe: 0.994 frente a 0.126).
  - H6b: para t+6 con rezagos, la partición aleatoria infla poco el R² (≤0.01) pero abarata el MAE ≥10 %; el k-fold purgado con embargo de 1 día elimina ≥90 % de la inflación.
  - H6c: B2 alcanza R² ≥ 0.95 a t+6 en toda zona y partición, así que el R² no sirve para ordenar métodos.
  - H6d: RF con las variables de la Fig. 4 de IRSEC, entrenado hasta 2017-10-03 17:00, da MAE de Z1 a ±10 % de 2,663.5 y RMSE a ±10 % de 3,174.7; la partición aleatoria 75/25 da MAE ≤1,200.
- **Datos.** UCI 849 (52,416 filas); figuras y tablas primarias de IRSEC ya leídas (scratchpad `downloads/audit3_s2figs/`, material con derechos de terceros: solo citar, no redistribuir). No hace falta el PDF de IRSEC.
- **Protocolo.** Factorial reducido: tarea {mismo instante, t+6 con rezagos} × entradas {calendario, calendario+clima, +otras zonas en t, rezagos propios} × partición {aleatoria 75/25, aleatoria por días, k-fold purgado, cronológica de nb02, ventana de IRSEC} × {RF, Ridge}; 3 semillas solo para RF (Ridge es determinista). Factorial completo (más tareas, KNN, XGB, 5 semillas) después. Escaladores ajustados solo en entrenamiento, más una variante de control positivo con el escalador ajustado en todo el dataset. Sensibilidad de ±2 días en la ventana de IRSEC (diferencia de filas del 31-dic).
- **Modelos.** RF, Ridge (luego KNN, XGB).
- **Referencias.** B0, B2, B3, B4, B9 en las mismas filas de test de cada celda.
- **Métricas y pruebas.** R², MAE, MAPE, skill frente a B2; inflación = métrica(aleatoria) − métrica(cronológica) con IC bootstrap sobre semillas × bloques diarios.
- **Entregable.** Figura de "escalera de inflación del R²" y tabla, base del paper corto sobre UCI 849.
- **Criterio de decisión.** Si H6d se cumple, el paper reclasifica IRSEC como cronológica; si no, la deja como "no determinada". Si H6c se cumple, el paper deja de usar R² para ordenar métodos.
- **Cómputo.** CPU: ~3 CPU-h la versión reducida, ~10 CPU-h la completa.
- **Código que reutiliza.** Scratchpad `audit2/irsec_window.py`, `irsec_match.py`, `irsec_r2.py`, `irsec_hourly.py`; `docs/estado-del-arte.md:39,168-178`; informe §3–§4.
- **Dependencias.** X0.
- **Riesgos.** Bajo. La ventana de IRSEC tiene incertidumbre de ±1 día.

### 3.2 Nivel 2: fortalece el paper

#### X7. El modelo como corrector del PDO

- **Pregunta.** Aunque el modelo no le gane al PDO solo, ¿una combinación PDO+modelo o un modelo del error del PDO reduce el error del programa publicado?
- **Hipótesis** (Holm sobre H7a–c).
  - Nulo ya medido: el desesgo ingenuo por media hora no ayuda (105.0 → 105.0 MW en 2025; en 2026, en la ventana de test hasta el 17-oct, se recalcula con `oper_anchor.py`; la cifra 110.5 → 112.9 es de 2026-01-01 a 11-22, n = 15,685, y se reporta rotulada así).
  - H7a: combinación w_b·PDO + (1−w_b)·modelo, con w por bloque horario elegido en 2024, reduce el MAE 5–12 % frente al PDO en 2025 y 2026.
  - H7b: XGB sobre el error del PDO (hora, día, feriado, GFS vigente, errores del PDO observados hasta el último dato de la vista —16:00 de D−1 en I-op, 24:00 de D−2 en I-pub—, discrepancia modelo−PDO, PDO−PSO) reduce el MAE ≥8 %, sobre todo el sesgo de +40–58 MW de 12 a 16 h.
  - H7c: Chronos-2 reajustado con el PDO como covariable futura le gana a H7a y H7b por ≥2 pts relativos.
  - H7d (métricas operativas): la combinación baja el q97.5 de |error| ≥8 %, el error de rampa a 30 min ≥15 % y el MAE del pico diario ≥10 %.
- **Datos.** Portal (PDO, PSO, Ejecutado desde 2017); IEOD por área; GFS archivado.
- **Protocolo.** Pronósticos del modelo estrictamente fuera de muestra: RF/XGB reentrenados por año (CPU, primero); Chronos-2 con cortes anuales ≤2021…≤2025 (GPU, segundo y opcional). Capa de combinación entrenada en 2022-23, hiperparámetros en 2024, evaluación en 2025, reporte en 2026 y en vivo (X5, `prereg-v2`, vista I-pub). Vistas I-op (08:00 y 16:00) e I-pub y razón de perímetro de X4. Regla de disponibilidad del PDO y de rezagos como `assert`. La columna del PDO de 2026 es provisional hasta la comprobación de X5; si difiere, se recalcula contra las instantáneas. Reservas en MW: proxies R_q (cuantil q de |e| por estación × bloque horario) y R_σ (k·σ), declarados como **no** equivalentes al algoritmo del PR-22. Sin conversión a dinero salvo precio oficial citado.
- **Modelos.** Combinación lineal por bloque; XGB del error; Chronos-2 ft con covariable PDO.
- **Referencias.** PDO, PDO desesgado, modelo de X4 solo, promedio simple, remedios de `experimentos/sesgo/remedios.py` aplicados al PDO.
- **Métricas y pruebas.** MAE, MAPE, sesgo por hora, percentiles del MAPE diario, cuantiles de |error|, rampas, pico; DM-HLN, bootstrap de 7 días, Holm.
- **Entregable.** Tabla PDO + modelo en MW.
- **Criterio de decisión.** H7a o H7b con IC que excluye 0 en 2025 y 2026 y mismo signo en la ventana prospectiva → la afirmación operativa del paper es "el modelo aporta como corrector del programa del operador".
- **Cómputo.** CPU ~5 CPU-h; GPU ~7 A100-h (parte opcional).
- **Código que reutiliza.** `experimentos/fundacionales/apilar.py`, `fundacionales.py:61-89` (pesos y combinación), `chronos2_variantes.py`, `experimentos/sesgo/remedios.py`, `ajuste_fino.py`, `experimentos/sein/pico_2026.py`, `modelado_sein.subestimacion_sobre_p90`, scratchpad `oper_anchor.py`.
- **Dependencias.** X4; X8 para temperatura real; X5 para la comprobación del PDO y la ventana prospectiva.
- **Riesgos.** Errores de PDO y modelo muy correlacionados (ganancias pequeñas). Revisiones de la columna del PDO.

#### X8. Clima real frente a simulado

- **Pregunta.** Con el pronóstico de temperatura que realmente existía en el origen, ¿ayuda el clima a 24 h, sobre todo en días cálidos? ¿La simulación ERA5 + N(0, 1.5 °C) es un sustituto válido?
- **Ya medido (reanálisis).** +calor en Centro, 10 % de días más cálidos: error de pico 106 → 74 MW en 2025 (−32 [−43, −19]) y −16 [−26, −1] en 2026 (PR #55). Antes H8b; su versión confirmatoria es la hipótesis (h) de X5 en vivo.
- **Hipótesis.**
  - H8a: con GFS real, el efecto medio M1−M0 a 24 h queda dentro de ±1 MW (TOST).
  - H8c: `chronos_cdd` baja el error del pico en días cálidos ≥10 MW sin subir el MAE global más de 1 MW.
  - H8d: el orden de las variantes de covariable bajo la simulación no se traslada al GFS real (τ de Kendall < 0.5).
  - H8e: a 1 h, reemplazar ERA5(t) por una disponibilidad realista (METAR en tiempo real o ERA5 con 5 días de rezago) cambia el MAE ≤0.3 MW.
- **Datos.** Open-Meteo Previous Runs (`gfs_seamless` desde 2021-03; ECMWF IFS opcional, con inicio de archivo por verificar); ERA5; METAR de Iowa Mesonet (SPJC, SPUR, SPHI, SPRU, SPQU, SPTN); IEOD.
- **Protocolo.** **Ventana de entrenamiento común** 2021-03 a 2024-12 para todos los brazos (quita la confusión entre largo de entrenamiento y realismo del pronóstico). Brazos: C0 sin clima; C1 simulado con σ ∈ {0, 1, 1.5, 2} × 10 semillas, error independiente por área; C2 GFS real; C3 bootstrap por bloques de residuos GFS−ERA5 (por mes × anticipación × área, ajustados en 2021-03 a 2024) aplicado a 2016-24 como sensibilidad; C4 observaciones METAR. Días cálidos definidos con umbrales de años de entrenamiento. Selección en 2025; reporte en 2026 y en vivo. Terminar `chronos_cdd` en una VM con checkpointing, no en Colab.
- **Modelos.** RF y XGB M0/M1, Chronos-2 cov1 (rehecho), `chronos_cdd`, modelos de X4 con temperatura.
- **Referencias.** C0 de cada modelo; corrección +calor; ERA5 observado como oráculo (cota).
- **Métricas y pruebas.** Primaria (ya fijada en `experimentos/temperatura/README`): error absoluto del pico diario en Centro a 24 h en el 10 % y 20 % de días más cálidos. Guardas: MAE global, sesgo, días normales. Bootstrap de bloques semanales, DM, Holm sobre modelos × áreas; τ de Kendall.
- **Entregable.** Figura de pico en días cálidos con GFS real.
- **Criterio de decisión.** H8c con IC que excluye 0 en 2025 y 2026 y guarda de MAE global ≤ +1 MW. Desde ya, "el clima no ayuda" se reescribe como "el clima simulado no ayuda en promedio"; después, con la cifra real.
- **Cómputo.** GPU ~6 A100-h + ~10 L4-h; CPU ~10 CPU-h.
- **Código que reutiliza.** `experimentos/temperatura/{descarga.py, comun.py, fuente.py, chronos_cdd.py, evaluar.py, apilar_temperatura.py, correccion.py}`; `temperatura_pronosticada.py`; `variables_sein.py:32,139-145`; `modelado_sein.py:126-129`; `chronos2_variantes.py:164`; `app/backend/pronosticador_real.py:16-18`.
- **Dependencias.** X0. Alimenta a X4 y X7.
- **Riesgos.** Pocos años con GFS. Huecos en METAR. Licencia de Open-Meteo no comercial (vale para el curso, no para operación).

#### X9. Feriados y lunes después de feriado

- **Pregunta.** ¿Cómo se comportan el modelo y el PDO en feriados y puentes, y qué agrega a ftcal un calendario con decretos y "lunes tras domingo o feriado"?
- **Ya medido.** `chronos2ftcal2` (sábado, domingo, víspera, puente) ya corrió y **perdió**: 78.2 frente a 75.6 MW (Centro, 24 h, 2025; nb04, `chronos2_variantes.py:50-60`). Se cita como resultado negativo.
- **Hipótesis.**
  - H9a: el MAPE del PDO en feriados es al menos el doble que en días laborables.
  - H9b (solo el delta nuevo): agregar a ftcal los decretos no laborables y "lunes tras domingo o feriado" baja el MAE en feriados y días adyacentes ≥15 % frente a ftcal, sin empeorar días normales más de 0.5 MW.
  - H9c: los lunes feriado explican ≥15 % del ΔMAE a 24 h frente a B7.
- **Datos.** `tablas/feriados_pe_2015_2026` (258 filas) más decretos (APEC 2016 y 2024, Panamericanos 2019); IEOD; portal.
- **Protocolo.** Variables de calendario relativas al feriado declaradas de antemano. Unificar la convención inicio/fin de periodo.
  - Muestra confirmatoria con **ventana expansiva por año** (entrenar hasta el año k−1 y evaluar en k, de 2019 a 2025; ~100 feriados), no leave-one-year-out (usaría años futuros para predecir el pasado).
  - H9b se mide **con el mismo modelo** que la muestra confirmatoria: ftcal-calendario con los cortes expansivos compartidos con X14 (≤2022 → 2023, ≤2023 → 2024, ≤2024 → 2025), 3 semillas. RF/XGB con la ventana expansiva completa 2019 → 2025.
  - 2026 y en vivo como apoyo. MDE por tipo de feriado.
- **Modelos.** ftcal con el calendario nuevo, ftcal, ftcal2, RF, XGB.
- **Referencias.** PDO, R1, B7 con feriado y B7 sin feriado.
- **Métricas y pruebas.** MAE, MAPE y error de pico en el subconjunto de feriados (día, antes y después); bootstrap por día y DM; guarda en días normales.
- **Entregable.** Tabla de feriados frente al PDO.
- **Criterio de decisión.** IC de la mejora en feriados que excluye 0 en la ventana expansiva y en 2026, con la guarda cumplida → el calendario nuevo entra al modelo servido.
- **Cómputo.** ~5 A100-h (corridas compartidas con X14) + ~4 CPU-h.
- **Código que reutiliza.** `tablas.py`, `chronos2_variantes.py` (cov3), `ajuste_fino.py`, `variables_sein.py:117-119`, `en_vivo.py:445`, nb05 celda 31.
- **Dependencias.** X3 (R1), X4, X14 (cortes).
- **Riesgos.** Muestra pequeña. Tabla curada no validada por un experto (`docs/peru/tablas.md` §8).

#### X10. Objetivo y normalización (2×2), con rolling anidado

- **Pregunta.** ¿La ganancia viene del objetivo en razón a la media de 24 h, de dividir las variables por m24, o de los cambios de variables que los acompañan? ¿Un objetivo residual sobre B4 rinde mejor?
- **Lo que ya existe.** `experimentos/historico/rolling.py` ya corre V0–V4 en folds mensuales (`historico.md` §1). Ojo: V2 frente a V4 **no** aísla el objetivo, porque V4 además divide los rezagos por m24 (`rolling.py:72-85`). Leer primero los CSV de Drive `reportes/historico/` antes de rediseñar.
- **Hipótesis** (Tetuán: exploratorias o de reanálisis; Ceuta: reanálisis).
  - H10a: con aprendiz fijo, en el 2×2 objetivo {nivel, razón} × variables {crudas, /m24}, el efecto principal del objetivo reduce el MAE 8–20 % en Tetuán y Ceuta, y la interacción es menor que el efecto principal.
  - H10b: el efecto se mantiene con Ridge (≥50 % del efecto con HGB).
  - H10c: el objetivo residual sobre B4 iguala o supera a la razón en ≥1 de 2 sistemas. Si se cumple, la recomendación es *post hoc* y debe reconfirmarse en la ventana prospectiva o en Ceuta.
  - H10d: con búsqueda anidada, el MAE del rolling del **HGB anidado** sube 2–6 % frente al **HGB no anidado** de nb02 (mismo aprendiz).
  - H10e: Ridge con rejilla de alpha sin borde empata al HGB global dentro de ±3 % (TOST).
- **Datos.** UCI 849; silver de Ceuta. El SEIN queda como extensión opcional del Nivel 3.
- **Protocolo.**
  - Factorial: objetivo {nivel, razón m24, residual sobre B4} × variables {crudas, /m24} × información {F0: rezagos y calendario diario/semanal; F1: F0 + desvío móvil, temperatura media 24 h, m24/m7d} × aprendiz {HGB, LightGBM, Ridge}.
  - Sensibilidad de clima en la celda elegida: V4 sin viento (bimodal e implausible) y V4 sin clima (importancia ≈0).
  - Folds: Tetuán mensual en expansión Mar–Oct (Nov–Dic en un bloque aparte rotulado "contaminado por diseño", sin selección); Ceuta veranos 2021-26 con historia de 1 año (2020 aparte).
  - Selección: Optuna con 30 ensayos por celda, **anidada dentro de cada fold externo** (CV interna con hueco H solo en el entrenamiento de ese fold). Se reporta solo el error del fold externo.
  - Semillas solo donde hay aleatoriedad (LightGBM con bagging; Optuna con 3 semillas de muestreo). HGB y Ridge son deterministas.
  - Curvas de desempeño según ensayos para mostrar la meseta. Modelo mixto y contrastes primarios (razón frente a nivel, /m24 frente a crudas, residual frente a razón) fijados en el preregistro; se reportan todas las celdas.
- **Modelos.** HGB, LightGBM, Ridge; más el HGB por zona y global y el apilado [B2, B3, HGB] como candidatos del MCS en Tetuán.
- **Referencias.** Escalera de X1 por fold (B9 y B10 incluidas).
- **Métricas y pruebas.** log-MAE en modelo lineal mixto (efectos aleatorios fold × serie); efectos en % con IC bootstrap por bloques de fold; Holm sobre los contrastes primarios; MCS por zona-mes con la regla de desempate; conteo de victorias frente a B2 con prueba de signo.
- **Entregable.** Figura de tamaño de efecto del objetivo y de la normalización por sistema × aprendiz, con IC.
- **Criterio de decisión.** Apoya o refuta la afirmación de `paper.md:444` y `historico.md` §1-§2. La selección de Tetuán pasa a ser el modelo elegido por la regla de desempate dentro del MCS del rolling anidado, no 49.0 frente a 48.2 %.
- **Cómputo.** CPU ~80–120 vCPU-h (VM de 64 vCPU unas horas; sube por el factor de normalización). XGB/LightGBM en GPU opcional.
- **Código que reutiliza.** `modelos.py:12` (ModeloDelta), `:37` (ModeloRazon), `:64` (CVPorFecha); `experimentos/historico/rolling.py:38,72-85,109,112-123`; `evaluacion.py:52`; `experimentos/ceuta/validacion.py`.
- **Dependencias.** X0, X1.
- **Riesgos.** Caminos que se bifurcan: mitigado al registrar el análisis y reportar todo. Folds cortos: el MCS puede retener muchos modelos; la regla de desempate decide y se reporta el conjunto.

#### X11. Ceuta y Melilla: costo de no haber visto un verano

- **Pregunta.** ¿Cuánto cuesta no haber visto un verano, separado de tener más datos y de la antigüedad de los datos, y le gana V4 al delta semanal en muchas temporadas?
- **Hipótesis** (reanálisis: 2022-26 ya se miró).
  - H11a: con historia de igual largo e igual antigüedad, el costo de exposición al verano de V4 (12 meses que terminan el 30-jun con Jul–Ago enmascarados, frente a los **mismos** 12 meses con dos meses no estivales enmascarados: 10 frente a 10 meses) es ≤ +10 % de MAPE, más o menos la mitad del +20 % confundido que se reporta (`historico.md:522-525`).
  - H11b: en el 2×2 de X10 aplicado a Ceuta, el efecto del objetivo (con normalización fija) explica ≥50 % de la brecha V0→V4.
  - H11c: V4 con ≥1 año le gana a B3 y a B9 en ≥75 % de las temporadas, con p_Holm agrupado < 0.05; V4 sin verano no le gana.
  - H11d: las correcciones de calendario local, feriados y ERA5 sin interpolar cambian el MAPE de V4 ≤0.1 pts.
- **Datos.** REE de 5 min 2019-2026 llevado a 10 min; REData horario 2011-2018; Melilla (MELILLAAU) **opcional** si el endpoint existe; ERA5. Licencia académica, sin redistribución; no commitear descargas. Comprobar si REE publica series "prevista/programada" para Ceuta (P6).
- **Protocolo.**
  - Brazos: (i) 12 meses al 30-jun con Jul–Ago enmascarados; (ii) los mismos 12 meses con dos meses no estivales enmascarados (por ejemplo, Mar–Abr, elegidos de antemano); (iii) 12 meses completos; (iv) 2 y 3 años. Se descarta el brazo "Jul–Dic del año previo frente a Ene–Jun", que mezcla haber visto el verano con 6 meses de antigüedad.
  - Reportar las filas que se pierden por la regla de `rolling(1008)` después de cada hueco de enmascarado, por brazo.
  - Test del 1-jul al 1-sep en hora local. Feriados de Ceuta dentro de la ventana: 5-ago, **15-ago (nacional)** y Aid al-Adha, de los calendarios oficiales (BOCCE/BOME). El 2-sep y el 17-sep (Melilla) caen fuera de la ventana: se mencionan, no se modelan. Los inferidos se marcan como no validados.
  - Los 4 valores no positivos se excluyen del MAPE (con conteo) y se reporta MAE.
  - V0–V5, el 2×2 y el objetivo residual de X10. La serie horaria 2011-18 (H = 1) y la de 10 min (H = 6) son **estratos separados** del metaanálisis, no se agrupan. Selección en 2021; 2020 aparte. Espejo invernal solo si sobra tiempo.
- **Modelos.** HGB/LightGBM con V0–V5 y el 2×2.
- **Referencias.** Escalera de X1 (sobre todo B3 y B9); P6 si existe.
- **Métricas y pruebas.** MAPE y MAE por temporada; DM con bloques de 1 día dentro de cada temporada; metaanálisis de efectos aleatorios de los contrastes; prueba de signo entre temporadas.
- **Entregable.** Forest plot del costo de no ver un verano y tasa de victorias de V4 frente a B3 con IC.
- **Criterio de decisión.** Las frases de `paper.md` §5.2 quedan sostenidas o se retiran.
- **Cómputo.** CPU ~20–40 vCPU-h. Descarga REE con límite de tasa: lanzarla en la primera semana, de noche.
- **Código que reutiliza.** `ceuta.py` (bronze, clima, silver; reemplazar `:173-178`), `experimentos/ceuta/validacion.py:32-47,84` (corregir el promedio 2021+ frente a 2022-26), `comparar_2017.py`, scratchpad `ceuta_bajar_veranos.py`, `ceuta_baselines.py`, `rolling.py:109`.
- **Dependencias.** X0, X1, X10 (2×2 y objetivo residual).
- **Riesgos.** Endpoint de REE no documentado. La estacionalidad de verano de Ceuta es débil (julio/promedio 1.02); no extrapolar a Z3 de Tetuán (1.58).

#### X12. Calibración de intervalos fuera de muestra

- **Pregunta.** ¿Puede cada modelo dar intervalos de 50/80/90 % calibrados fuera de muestra, incluido el cambio de nivel de 2026 y la ventana en vivo, y a qué costo en ancho?
- **Ya medido (reanálisis).** PR #53 eligió γ = 0.2 en 2025; cobertura 79–81 % (2025/2026) y 82–86 % en vivo. La rejilla de γ **no** se vuelve a elegir mirando 2026: γ = 0.2 queda congelado.
- **Hipótesis.**
  - H12a: conformal dividido calibrado en 2025 subcubre en 2026 ≥3 pts a 24 h (reanálisis); ACI con γ = 0.2 congelado se mantiene a ±2 pts con ancho +10–20 % (el ancho es lo nuevo).
  - H12b: los cuantiles nativos de ftcal (cobertura 10–90 ≈75 %) fallan Kupiec; ACI pasa Kupiec y falla Christoffersen a 24 h (fallos agrupados en días cálidos y lunes feriados).
  - H12c: la combinación recalibrada con CQR baja el CRPS ≥3 % frente a sus cuantiles promediados.
  - H12d: en Tetuán t+6, los intervalos conformes alrededor del HGB son más angostos que los de B2 a igual cobertura (PINAW −15 % o más).
- **Datos.** Paneles fuera de muestra de X1, X10, X11, nb03/nb04 y el registro en vivo.
- **Protocolo.** Residuos de calibración siempre fuera de muestra (corrige `apilar.py:261-266` y el uso de errores del RF sobre el XGB en la app). Conformal dividido (absoluto y relativo, por hora), CQR, ACI por lado, cuantiles nativos de FM. Método elegido en ventanas anteriores (SEIN 2025, Tetuán Mar–Oct, Ceuta 2021). **X12-SEIN** primero (ya tiene predicciones fuera de muestra) y basta para `prereg-v2`; Tetuán y Ceuta cuando lleguen X10 y X11. Kupiec y Christoffersen con el indicador de un horizonte por día (2.3), más el conteo beta-binomial.
- **Modelos.** Todos los modelos puntuales, FM y combinación.
- **Referencias.** Cuantiles empíricos de los residuos de B2 y B9; cuantiles nativos; intervalos actuales de la app.
- **Métricas y pruebas.** PICP, PINAW, Winkler, CRPS (de la rejilla de cuantiles), pinball q10/q50/q90; Kupiec y Christoffersen; cobertura condicional por hora, feriado, decil cálido y régimen; DM sobre CRPS con bloques de 7 días; MDE de la prueba de cobertura para la ventana en vivo.
- **Entregable.** Diagramas de fiabilidad, CRPS y pruebas de cobertura.
- **Criterio de decisión.** Todo intervalo del paper y de la app es fuera de muestra, pasa Kupiec al 80 % y 90 % (o se reporta el fallo) y viene con CRPS. El método elegido entra congelado en X5.
- **Cómputo.** CPU ~20 CPU-h; <2 L4-h si hay que reinferir cuantiles.
- **Código que reutiliza.** `experimentos/sesgo/remedios.py` (ACI, `:387` `bootstrap_cobertura`), `fundacionales.py:52,61-72`, `experimentos/fundacionales/apilar.py`, `app/backend/pronosticador_hibrido.py`.
- **Dependencias.** X12-SEIN: X0, X1. X12 de Tetuán y Ceuta: X10 y X11.
- **Riesgos.** El conformal supone intercambiabilidad, que se rompe con el cambio de régimen; eso es justamente lo que se mide.

#### X13. FM en Tetuán y Ceuta con controles limpios

- **Pregunta.** ¿Los FM actuales, sin ajuste, le ganan a B4 y al HGB en un sistema chico de un año a 10 min, y en los veranos de Ceuta sin haberlos visto?
- **Hipótesis** (Tetuán: exploratorias; Ceuta 2022-26: reanálisis).
  - H13a: el mejor FM sin ajuste en Tetuán a t+6 es **equivalente** a B4 con margen ±10 % del MAE (TOST).
  - H13d: en Ceuta, los FM sin ajuste igualan a V4 con 1 año (MAPE ≈1.9 %, TOST ±0.2 pts) sin entrenar con ningún verano.
  - Descriptivo (no hipótesis, n = 3): pérdida de los FM univariados contra B4 en los 3 feriados del test y cuánto la reducen las covariables de calendario (feriado, Ramadán).
  - Descriptivo: distancia de los controles limpios al mejor FM. Mezcla capacidad con posible fuga (2.6), así que no se interpreta como evidencia de contaminación.
- **Datos.** UCI 849; silver de Ceuta.
- **Protocolo.**
  - Generalizar primero `fm_bench.py` (quitar AREAS, H = 48 y `/content` fijos; parametrizar resolución y pasos).
  - **Piloto cronometrado** de 100 orígenes por modelo (en particular TabPFN-TS-3 con contexto largo; ETT_1D tardó 648 s por 280 pronósticos con contextos cortos) **antes** de presupuestar y fijar cuántos orígenes entran.
  - Panel: los adaptadores existentes más TabPFN-TS-3 LOCAL (checkpoint fijado, clima como covariable futura). Sin Timer-S1.
  - Contexto y variante de covariables elegidos en el rolling Mar–Sep (no en la validación que cruza el quiebre) y congelados.
  - Horizonte principal t+6 (t+1, t+36 y t+144 como contexto bibliográfico). Todos los orígenes del test y orígenes del rolling cada tercero (o los que permita el piloto). Feriados, Ramadán, Z3 8–18 nov y post-quiebre por separado.
  - Ceuta: veranos 2021-26 (2020 aparte). Desde **cada origen** de julio y agosto, el contexto llega hasta t (como V4 en inferencia). El corte del 30-jun es solo para los modelos que entrenan; los FM no entrenan.
  - Familia de Holm y MDE declarados.
- **Modelos.** Chronos-2, Simons-297M, Timestral-209M, TimesFM 2.5, TiRex-2, Toto-2 313m (control limpio, cuenta una vez), TimeH2O-v1 (restringido, no comercial), ChakraTS-OS-10M (local; **no** como control limpio), TabPFN-TS-3 LOCAL (control limpio).
- **Referencias.** Escalera de X1; HGB de nb02 **y HGB semanal** (C-RT); V4 de Ceuta.
- **Métricas y pruebas.** MAE, MAPE, skill doble, pinball, CRPS, cobertura 10–90; DM con bloques de 1 día, TOST y Holm; MCS por zona con desempate.
- **Entregable.** Tabla de FM en Tetuán y Ceuta.
- **Criterio de decisión.** La novedad que el paper puede declarar es **"FM a t+6 sobre UCI 849 contra referencias delta, con pruebas pareadas y controles limpios"**, no "primeros FM sobre UCI 849": Singh & Tewari (2026, Cureus J. Comput. Sci.) ya usaron Chronos en Z2 a t+1 con partición cronológica (`informe.md:58`), y Wei (2023) ya hizo "Z1, 10 min, t+6".
- **Cómputo.** ~35 L4-h + A100 **según el piloto** (reserva provisional ~30 A100-h; v1 no la respaldaba).
- **Código que reutiliza.** `experimentos/fundacionales/{adaptadores.py, fm_bench.py, chronos2_variantes.py, cola.sh, instalar.sh}`; `fundacionales.py:37,97`; `variables.py:18-21` (FERIADOS, RAMADAN).
- **Dependencias.** X0, X1, X15 (fechas de feriados, Ramadán y reloj).
- **Riesgos.** Conflictos de instalación (venvs separados). Costo de TabPFN. Un solo test de una estación. Licencias no comerciales (TimeH2O, ChakraTS-OS, TabPFN-3.x): solo curso y paper. Cláusula de ingresos de Timestral: verificarla si el trabajo se asocia al empleador.

#### X14. Varianza de selección y búsqueda justa en el SEIN

- **Pregunta.** ¿La ventaja de ftcal sobre el RF se sostiene con otros cortes de ajuste y años de evaluación, o es un efecto de 2025? ¿Cambia la elección RF frente a XGB con búsqueda igual y anidada por área y horizonte?
- **Hipótesis.**
  - H14a: ftcal le gana al RF M0 a 24 h en Centro en los 3 años de evaluación (2023, 2024, 2025) con IC que excluye 0.
  - H14b: la dispersión de ΔMAE(ftcal − RF del mismo año) entre cortes es ≥5 veces la dispersión entre semillas (0.19 MW). Se usa ΔMAE frente al RF del **mismo año** porque cada corte se evalúa en un año distinto y el corte queda confundido con la dificultad del año.
  - H14c: RF, XGB y LightGBM con 30 ensayos anidados por área y horizonte comparten el MCS al 90 % en ≥80 % de las celdas año × área × horizonte.
- **Datos.** Gold del SEIN 2016-2026.
- **Protocolo.**
  - La receta de ftcal (lr 1e-6, 3000 pasos, feriado) se eligió en 2025, así que evaluarla en 2023 y 2024 usa una decisión tomada con datos posteriores. **Brazo principal:** se vuelve a elegir la receta entre las variantes a/b/c/ftcal/ftcal2 solo con el corte 2022 (evaluado en 2023), igual que X17, y se congela. **Brazo secundario:** la receta de 2025, rotulada "elegida con datos posteriores".
  - Chronos-2 (ajuste completo) con cortes ≤2022, ≤2023, ≤2024 × 3 semillas, cada uno evaluado en el año siguiente; aserción de corte parametrizada.
  - Tabulares RF/XGB(GPU)/LightGBM con búsqueda anidada de 30 ensayos por área y horizonte, un solo arnés de Optuna compartido con X10.
  - Comparador reentrenado (política C) en la tabla. 2026 rotulado "explorado". Modelo de descomposición de varianza (corte, semilla, modelo) fijado de antemano.
- **Modelos.** Chronos-2 ftcal (las dos recetas), RF, XGB, LightGBM, política C.
- **Referencias.** Escalera de X1 por año.
- **Métricas y pruebas.** MAE, skill frente a la más fuerte; MCS por año con desempate; τ de Kendall del ranking entre años; regret de elegir con el año previo; descomposición de varianza.
- **Entregable.** Figura de estabilidad del ranking (modelos × años con pertenencia al MCS) y tabla de descomposición de varianza.
- **Criterio de decisión.** Reemplazan las conclusiones de una sola partición de nb02_sein y nb04. Si H14a falla con la receta reelegida en 2022, el paper no dice que ftcal le gana al RF en general.
- **Cómputo.** ~13 A100-h (Chronos, incluida la reelección de receta) + ~20 L4-h (XGB/LightGBM) + ~100 vCPU-h (RF).
- **Código que reutiliza.** `ajuste_fino.py`, `fm_bench.py`, `cola.sh`; `modelado_sein.py:63-116,188-234`; `fundacionales.py:61`; `chronos2_variantes.py`; nb02_sein celdas 8-15 y 26-28.
- **Dependencias.** X0, X1.
- **Riesgos.** Que la selección cambie el modelo "elegido": se reporta y se mantiene nb03 como prueba única de registro.

#### X15. Forense de UCI 849

- **Pregunta.** ¿Qué propiedades del dataset (reloj, reescalado entero mensual, traspaso del 25-oct, salto de Z3, feriados y Ramadán) cambian las conclusiones modelo frente a referencia?
- **Ya existe.** Denominadores enteros 13–929 (informe §4.2). Quiebre del 25-oct hacia las 11 h con `cuota.py` (`historico.md` §4). Lo nuevo es la prueba de invariancia de las métricas relativas al denominador, `ruptures` con IC y el reloj.
- **Hipótesis.**
  - H15a (reloj): el centroide diario de la irradiancia difusa sigue al mediodía solar de Tetuán (35.57 N, 5.37 O). Regla registrada: salto ≥45 min en los cambios de hora de 2017 → hora civil local; <15 min → desfase fijo (se reporta el desfase respecto a UTC).
  - H15b: sin las ventanas anómalas, la pérdida de Z3 frente a B2 pasa de −9.4 % a ±3 % (solo sensibilidad, porque las ventanas se vieron en el test).
  - H15c: objetivo S12 (Z1+Z2) con cuota de Z1 a 24 h, o reentrenamiento disparado por un detector `ruptures` causal, baja ≥10 % el MAE post-quiebre de Z1/Z2 en validación (604/518) y le gana a B2 tras el quiebre (599/479).
  - H15d: los datos apoyan el Aid al-Adha solo el 1-sep; recodificarlo cambia el MAE de feriado de Z1 <2 %.
  - H15e (Ramadán, sensibilidad): Z3 pierde en Ramadán (631.1 frente a 587.8); desplazar las fechas ±1 día y agregar una variable de horario de Ramadán (iftar) cambia esa brecha; se reporta el tamaño, sin p confirmatorio.
- **Datos.** Solo UCI 849.
- **Protocolo.** (a) Prueba de que las métricas relativas no dependen del denominador entero. (b) Centroide de irradiancia frente a ecuaciones de mediodía solar de NOAA. (c) `ruptures` (PELT, penalización BIC) con IC por bootstrap, contrastado con la fecha ya obtenida por `cuota.py`. (d) Sensibilidad con y sin cada ventana. (e) Variantes con régimen entrenadas hasta el 13-sep y elegidas en la validación previa al quiebre (13-sep a 24-oct), con el tramo posterior como pseudotest. (f) Ramadán con fechas ±1 día.
- **Modelos.** HGB global en razón; S12 y cuota; reentrenamiento por detector.
- **Referencias.** X1 (sobre todo B2, B4 y B9).
- **Métricas y pruebas.** MAE y skill por ventana; diferencia de MAE con bloques de 1 día; IC de fecha de quiebre; IC del desfase del reloj.
- **Entregable.** Tabla tipo "datasheet" de rarezas con evidencia y tamaño de efecto, y tabla de "conclusiones robustas o no a las ventanas anómalas".
- **Criterio de decisión.** Si H15a indica hora civil o un desfase, las variables de calendario y la hora pico de Tetuán se recalculan antes de X10 y X13.
- **Cómputo.** CPU <5 h.
- **Código que reutiliza.** `experimentos/historico/{cuota.py, quiebre.py, rolling.py}`; `variables.py:18-21`; `evaluacion.py:29`; `docs/historico.md` §4; nb02 celda 31; informe §4.2.
- **Dependencias.** X0, X1.
- **Riesgos.** Bajo. Zonas, feriados y Ramadán siguen siendo inferidos de los datos.

#### X21. Saneamiento de variables y datos del SEIN (nuevo)

- **Pregunta.** ¿Qué conclusiones del paper cambian al corregir las variables degeneradas y los huecos de datos del SEIN?
- **Hipótesis y tareas.**
  - H21a (fallas): `fallas_en_curso` está activa el 91 % de 2025 (0.47 a 1.80 por periodo), así que no discrimina. Con una definición útil (fallas nuevas en las últimas k horas, ponderadas por MW interrumpidos, con k y umbral fijados en 2016-24), M3 − M2 a 24 h en Centro cambia de signo o su IC se mueve más de 1 MW. Mientras tanto, "las fallas no ayudan" sale del paper o se reescribe como "la variable de fallas usada está degenerada". M4 (SAIDI) se evalúa igual si hay datos.
  - Cuarentena: reemplazar el indicador actual por la tabla curada `cuarentena_pe_2020` (5 fases) y cortar la segunda ola de 2021; reportar el cambio en el MAE de 2020-21 y en la selección.
  - 7 días sin IEOD: marcarlos con una variable indicadora e imputar el total con el portal a nivel SEIN (cuotas por área de los 7 días cerrados previos), para no perder ~56 días de filas por las ventanas de rezago. Sensibilidad: con y sin imputación.
  - N+C+S ≠ SEIN en 2026 (48 periodos, hasta 47.6 MW): diagnosticar si hay un cambio en la definición de las áreas en el año de test (fecha, áreas afectadas, magnitud) y decidir antes de X4 si se corrige o se excluye.
  - XGB apilado: rehacer sus hiperparámetros dentro de cada corte (sin reusar los de nb02, posiblemente ajustados en 2025). SHAP (TreeSHAP) sobre el modelo **elegido** (RF M0) y, si es posible, sobre el servido; el SHAP actual sobre XGB M3 se rotula como "modelo no elegido".
- **Datos.** Gold del SEIN; eventos de fallas; tabla `cuarentena_pe_2020`; portal.
- **Entregable.** Nota de saneamiento con cada cambio, su efecto en el MAE y la decisión tomada.
- **Criterio de decisión.** Si H21a cambia el signo del efecto de fallas, la afirmación del paper se reescribe.
- **Cómputo.** CPU ~8 CPU-h (la nueva corrida de M3 cuesta ~3 h).
- **Código que reutiliza.** `exogenas.py:243` (`fallas_en_curso`), `variables_sein.py:17,37,152`, `tablas.py:48,184`, `modelado_sein.py`, nb05.
- **Dependencias.** X0. Alimenta a X1 (sensibilidad N+C+S), X4 y X14.
- **Riesgos.** Definición de "falla útil" con grados de libertad: se fija en el preregistro antes de evaluar.

### 3.3 Nivel 3: ambicioso, mucha GPU o mucho tiempo humano

#### X16. Prueba de contaminación de FM validada con controles

- **Pregunta.** ¿Se puede detectar fuga del preentrenamiento solo por el comportamiento del pronóstico, y los resultados del SEIN 2025-26 de FM con corpus no auditable (Simons, Timestral, ChakraTS-OS) están afectados?
- **Hipótesis.**
  - H16a (validez con un experimento natural): TiRex-2 tiene dos checkpoints descontaminados que difieren en la inclusión de UCI 321 (según la crítica, el descontaminado para fev la incluye y el descontaminado para GIFT-Eval la excluye; **verificar en las fichas de los modelos** antes de registrar). Es el mismo modelo con o sin la serie: el que la vio muestra un skill relativo ≥5 % mejor en UCI 321 que el que no la vio, y no en series que ninguno vio.
  - H16a' (control positivo secundario): en la serie "spain" 2015-18, que en TiRex-2 entra por `lotsa_data` y por `chronos_datasets_extra/spanish_energy_and_weather`. El control negativo ENTSO-E España 2019-24 es **el mismo sistema**, así que una mejora en él puede ser generalización dentro de la distribución y no fuga. Se declara y no se usa como negativo limpio.
  - H16c: la ganancia de cada FM no auditable frente al comparador reentrenado y a Toto-2 313m cambia <2 pts entre antes y después de su fecha de publicación.
- **Datos.** UCI 321 (`autogluon/chronos_datasets`); "spain" de GiftEvalPretrain (scratchpad `downloads/gifteval_spain`); ENTSO-E España (token gratuito de la API ENTSO-E Transparency); `downloads/fev_entsoe`; registro en vivo de X5.
- **Protocolo.** Tres pruebas. (1) Sustitutos: K = 20 copias con permutación de bloques semanales dentro del mismo mes y hora del año, comprobando que conservan la alineación de feriados. (2) Eventos canario fijados de antemano (traspaso del 25-oct-2017, salto de Z3, artefacto entre áreas del 4-ago-2026, lunes feriado 29-jun-2026). (3) Diferencias en diferencias por fecha de publicación, con la ventana prospectiva de X5 y con `last_modified` de HF tratado como cota superior de la fecha de corte del corpus. Sonda de perturbación del contexto (jitter mínimo) como cuarta prueba. Regla de marcado registrada antes. El AUC del detector se define **sobre ventanas o sustitutos** (positivos: ventanas de UCI 321 vistas por un checkpoint; negativos: las mismas ventanas para el checkpoint que no las vio, y sustitutos), no sobre modelos. Si AUC <0.7, la prueba se declara no informativa y un nulo no se lee como limpieza. Potencia y MDE de la parte (3) declarados. TabPFN-TS **no** entra en X16 (con K = 20 sustitutos su costo explota).
- **Modelos.** Panel de X13 sin TabPFN-TS; Toto-2 313m como control.
- **Referencias.** Controles limpios; C-RT; RF/XGB (no contaminables).
- **Métricas y pruebas.** Cociente MAE_sustituto/MAE_original frente a los controles con IC bootstrap; AUC del detector; DiD con bloques de 7 días; prueba de permutación para eventos; Holm por familia de modelos.
- **Entregable.** Lista de modelos marcados y no marcados con su evidencia.
- **Criterio de decisión.** El paper reemplaza "no se puede auditar" por un resultado solo si AUC ≥0.7. Si se marca Simons, la combinación se recalcula sin Simons.
- **Cómputo.** ~40 A100-h + ~30 L4-h.
- **Código que reutiliza.** `fm_bench.py`, `adaptadores.py`, scratchpad `inspect_arrow.py`, `inspect_fev_entsoe.py`, `en_vivo.py` (`pronosticos.parquet`).
- **Dependencias.** X0, X5 (datos posteriores a la publicación), X13.
- **Riesgos.** Poca potencia (los FM normalizan y no memorizan secuencias exactas). Las fechas de publicación no son fechas de corte del corpus.

#### X17. Ajuste fino: escalado de datos, LoRA y otros FM

- **Pregunta.** ¿Cuánto histórico necesita el ajuste fino, LoRA iguala al ajuste completo y otro FM ajustado iguala o supera a ftcal?
- **Hipótesis.**
  - H17a: el MAE de Chronos-2 ajustado a 24 h en Centro mejora con la ventana k ∈ {0.5, 1, 2, 4, todo} años hasta k = 4 (pendiente negativa de MAE frente a log2(k) en k ≤ 4, con IC por bootstrap de bloques que excluye 0, y Jonckheere-Terpstra); entre 4 años y todo, |ΔMAE| ≤1 MW (TOST).
  - H17b: LoRA (r ∈ {8, 32}) queda a ≤1.5 MW del ajuste completo en los 3 cortes (TOST).
  - H17c: TimesFM 2.5 con LoRA r = 16 queda a ±3 % de ftcal (TOST).
  - H17d: reajustar con datos hasta 2025 mejora el MAE de la ventana prospectiva ≥2 % frente a ftcal.
- **Datos.** Silver IEOD por área 2016-2026.
- **Protocolo.** Factores: modo (completo, LoRA r 8/32), k y corte (2022, 2023, 2024; evaluado en el año siguiente). Hiperparámetros (lr, pasos) elegidos solo con el corte 2022 y congelados (la misma reelección de X14). 3 semillas. Simons **solo** si una corrida piloto reproduce su receta de entrenamiento; si diverge, se reporta "no reproducible" sin ajustarlo sobre años de evaluación.
- **Modelos.** Chronos-2 (completo y LoRA), TimesFM 2.5 LoRA, Simons (condicional).
- **Referencias.** ftcal de nb04; RF M0; política C; combinación; escalera de X1.
- **Métricas y pruebas.** Curva MAE(k) con IC de 7 días; DM frente a RF y ftcal con Holm por corte; ANOVA de efectos aleatorios sobre ΔMAE; MCS por corte con desempate.
- **Entregable.** Curva MAE(k) con IC.
- **Criterio de decisión.** Responde "¿cuánto histórico basta?" (`historico.md`); si H17b se cumple, LoRA pasa a ser el ajuste por defecto.
- **Cómputo.** 3 modos × 5 k × 3 cortes × 3 semillas = 135 ajustes × ~26 min ≈ 58 A100-h solo de ajuste, más la inferencia de un año por corrida y TimesFM: **~80 A100-h** (+ ~8 H100-h si el piloto de Simons funciona).
- **Código que reutiliza.** `ajuste_fino.py`, `chronos2_variantes.py`, `fundacionales.py`, `apilar.py`.
- **Dependencias.** X0, X14 (comparte cortes y la receta reelegida; X14 es el subconjunto barato).
- **Riesgos.** Receta de Simons inmadura. Costos estimados, no medidos.

#### X18. Ajuste fino entre sistemas

- **Pregunta.** ¿Ajustar con varios sistemas eléctricos ayuda al sistema chico (Tetuán, un año) y a la isla (Ceuta) más que el ajuste local?
- **Hipótesis.**
  - H18a: en Tetuán a t+6, ajuste agrupado < ajuste local < sin ajuste en MAE, con ≥5 % entre escalones en Z1 y Z2.
  - H18b: en Ceuta, el ajuste agrupado le gana a V4 con 1 año y a B3 en ≥4 de 5 veranos.
- **Datos.** UCI 849; Ceuta 2019-2026 (más REData horario); Melilla si está disponible.
- **Protocolo.** Variantes: sin ajuste, local, agrupado (identificador de sistema como covariable). **Regla de corte por fecha calendario:** todas las series del ajuste se cortan en la misma fecha que el objetivo (Ceuta y Tetuán se correlacionan 0.73 hora a hora). Como Ceuta empieza en 2019, para Tetuán 2017 solo se usa Ceuta horaria anterior a la fecha de corte o se declara la variante como relajada y no válida para afirmaciones. Hiperparámetros congelados de X17. 3 semillas. Sin selección de checkpoints en el test.
- **Modelos.** Chronos-2 completo y LoRA r = 32.
- **Referencias.** Escalera de X1; HGB de nb02 y HGB semanal; V4; resultados sin ajuste de X13.
- **Métricas y pruebas.** MAE y MAPE por sistema; DM entre escalones consecutivos con Holm por sistema; bootstrap estratificado por verano en Ceuta.
- **Entregable.** Tabla por sistema y escalón.
- **Criterio de decisión.** Cierra el pendiente de "preentrenamiento con Ceuta" (`historico.md:54, 470-471`) con una respuesta válida.
- **Cómputo.** ~15–20 A100-h.
- **Código que reutiliza.** `ajuste_fino.py` (generalizado a varios sistemas), `comparar_2017.py`, `ceuta.bronze_ceuta`.
- **Dependencias.** X13, X17.
- **Riesgos.** Perfiles muy distintos (Ramadán +11 % en Ceuta frente a +43–49 % en Tetuán): agrupar puede perjudicar a Tetuán. Las hipótesis son falsables en ambos sentidos.

#### X19. Metaauditoría codificada de UCI 849

- **Pregunta.** ¿Cuántos resultados publicados sobre UCI 849 son pronósticos, con qué partición y escala, y cómo se comparan con una referencia trivial del mismo protocolo?
- **Hipótesis.**
  - H19a: de los trabajos con protocolo determinable (unión de `docs/estado-del-arte.md` e informe, sin duplicados), ≥60 % son regresión del mismo instante o partición aleatoria; de los de pronóstico, ≥70 % no reportan referencia ingenua o reportan un error peor que la referencia del mismo protocolo.
  - H19b: la escala de suma horaria reproduce el MAE horario de IRSEC (15,442) a ±15 %.
  - H19c: el MAE a t+6 de Wei (2023) sobre Feb–Dic es ≥2 veces el de B2 en la misma ventana.
- **Datos.** Textos y figuras de los trabajos (material de terceros: citar, no redistribuir); UCI 849.
- **Protocolo.** Libro de códigos (tarea, partición, resolución y escala, zona, rezagos, referencia, riesgos de fuga, nivel de evidencia). Dos codificadores independientes; precodificación con IA declarada y **ciega para los codificadores al menos en un subconjunto de calibración**; κ de Cohen. Reproducciones por clase de protocolo con su referencia trivial (las de X6 son el núcleo). Hiperparámetros del paper cuando están declarados; si no, por defecto de sklearn, declarado antes.
- **Modelos.** RF, MLP, LR, SVR, DT, SARIMA.
- **Referencias.** Referencia trivial por protocolo.
- **Métricas y pruebas.** Métrica reproducida frente a reportada; diagrama de dispersión "escalera de protocolos"; κ; IC binomial exacto.
- **Entregable.** Tabla clasificada completa con niveles de evidencia y una hoja de protocolos recomendados para UCI 849.
- **Criterio de decisión.** H19a con IC binomial que excluye el umbral → afirmación central del paper corto; si no, el paper corto se limita a la escalera de X6.
- **Cómputo.** CPU <10 h; ~2 personas × 3 días de codificación.
- **Código que reutiliza.** Scratchpad `audit2/*`; `docs/estado-del-arte.md`; `informe.md` §3–§4; `src/tetouan_power_forecast/datos.py`.
- **Dependencias.** X6, X15. **Acceso institucional UPC a IEEE Xplore** para subir niveles de evidencia (IRSEC 2018, ICEES, ICSIST, ICACI, IRASET, ISAS, ISRITI, SCCC, ICHORA); después, Elsevier con token institucional, Wiley TDM y Springer TDM. Sin acceso, los trabajos quedan en "solo resumen" o "solo figuras", y se declara.
- **Riesgos.** Tiempo humano en plena entrega de TB1 (por eso es Nivel 3). Anclaje de los codificadores en la precodificación automática.

#### X20. Intradía y reprogramación (RDO), condicionado

- **Pregunta.** ¿Un modelo intradía (cada 30 min, 1 a 8 h) mejora al techo del operador a 1 h y anticipa las salidas de tolerancia del PR-06?
- **Hipótesis.**
  - H20a: a 1 h en el SEIN, Chronos-2 o XGB con el PDO como covariable futura y el Ejecutado reciente le gana a P3 (1.03 %, MAE 71.8) ≥8 % en 2025 y 2026.
  - H20b y H20c (alertas y pronóstico tras un RDO) **solo** si se cumplen las condiciones de abajo.
- **Condiciones de entrada.** (1) X5 mide durante 7 días que el Ejecutado del portal se publica en tiempo real y con qué latencia; (2) se localiza el archivo de RDO 2024-25; (3) se conoce la tolerancia τ del PR-06 (Anexo 1). Si (2) o (3) fallan, solo se corre H20a.
- **Datos.** Portal, archivo de RDO (por localizar), GFS archivado.
- **Protocolo.** Origen cada 30 min, H = 2..16; entrenamiento ≤2024, selección 2025, reporte 2026 y en vivo. Referencias con S = ⌈H/S_d⌉·S_d. Alerta P(|γ̂| > τ en las próximas 4 medias horas) > p*, con p* elegido en 2025.
- **Modelos.** Chronos-2 ft con covariable PDO (`prediction_length = 16`), XGB intradía.
- **Referencias.** P3, `y(t−H)+Δsemana`, persistencia, PDO; pronóstico de tiempo real del COES solo en la ventana prospectiva.
- **Métricas y pruebas.** MAE por horizonte con DM-HAC; anticipación, recall, precisión y falsas alarmas por semana con bootstrap por eventos; Holm.
- **Entregable.** Tabla de MAE por horizonte frente a P3.
- **Criterio de decisión.** H20a con IC que excluye 0 en 2025 y 2026.
- **Cómputo.** ~2 A100-h + ~1 L4-h.
- **Código que reutiliza.** `en_vivo.py`, `chronos2_variantes.py`, `fm_bench.py`, informe §5.1 y §5.3, scratchpad `oper_anchor.py`.
- **Dependencias.** X5, X7.
- **Riesgos.** τ, ruta del RDO y latencia desconocidas; revisiones del Ejecutado en tiempo real.

### 3.4 Descartado o absorbido, y por qué

| Propuesta | Decisión | Motivo |
|---|---|---|
| Zoológico de modelos profundos (NHITS, TFT, PatchTST…; ~500 A100-h) | Descartado | Lo más caro y menos novedoso; la comparación GBM frente a profundos ya está en la literatura; sin valor operativo para Perú. La búsqueda GBM anidada de X10/X14 basta para no comparar contra un rival débil |
| AutoGluon best_quality (~150 A100-h) | Descartado | Responde "¿ayudan los ensambles?" (ya se sabe); entorno de torch en conflicto; lo valioso (combinación con el PDO) está en X7 |
| Escalado de tamaño de modelo y contexto (Toto-2 4m–2.5B, Timer-S1, ci-proto; ~120 H100-h) | Descartado | Curvas ya publicadas por los proveedores; datos 2025-26 ya explorados; ninguna afirmación del paper depende de esto |
| Panel de 14 FM × 4 contextos × 3 covariables en Tetuán | Reemplazado por X13 | Multiplicidad sin MDE; misma novedad a ~3 veces el costo |
| FM en Ceuta con contexto de 391k | Reemplazado por X11 y X13 | Caro y frágil, con estacionalidad débil |
| Validación cruzada sin control positivo de contaminación (perturbaciones) | Reemplazado por X16 | Un nulo no sería interpretable |
| Ventana en vivo "virgen" desde el 23-oct con congelamiento posterior | Rechazado | La ventana se vería durante el desarrollo; X5 empieza después del hash |
| Congelar el 25-nov o el 30-nov modelos que aún no existen | Rechazado | Ciclo de dependencias; X5 registra en dos etapas |
| Cláusula de "revisar la réplica PR-03 hasta que dé 2.2–2.5 %" | Rechazada | Ajusta la referencia a un número objetivo |
| H3a ("R0 = 2.2–2.5 %") | Retirada (v2) | Ya medido por `pr03_replica.py`; no es una predicción |
| H1a, H1b, H8b, γ de H12a, H6a | Reetiquetadas como reanálisis o réplica (v2) | Números ya conocidos |
| P5 en X1 (24 h rodante) | Retirado (v2) | El PDO de D+1 no existe para orígenes antes de las 16:00 de D |
| Leave-one-year-out en X9 | Reemplazado por ventana expansiva (v2) | Usa años futuros para predecir el pasado |
| Brazo "Jul–Dic previo frente a Ene–Jun" en X11 | Reemplazado (v2) | Mezcla exposición al verano con antigüedad de los datos |
| H13b, H13c, H16b como hipótesis | Degradados a descriptivos o retirados (v2) | n = 3; controles más débiles mezclan capacidad con fuga; banda de 2 modelos no definida |
| TabPFN-TS en X16 | Excluido (v2) | Costo con K = 20 sustitutos |
| Diferencias en diferencias con 3 eventos de El Niño como prueba confirmatoria | Degradado a tabla descriptiva (en X4 y X7) | n = 3, 2017 confundido por choque de oferta y un solo año de IEOD |
| Reserva en dinero (PR-22) | Degradado a métricas en MW dentro de X4/X7 | Ni el algoritmo ni el precio son públicos |
| Catálogo de ablaciones de fuga | Absorbido | Controles en X0; σ y GFS en X8; ERA5 en X11; feriados en X9 |
| Rolling anidado de Tetuán por separado | Absorbido en X10 | Evita duplicar la búsqueda |
| Fase B del SEIN con 194k ajustes | Reducida dentro de X14 (30 ensayos) | Cambio esperado de MAE modesto |
| Regímenes por separado | Repartido | Tetuán en X15, feriados en X9, El Niño como tabla, días cálidos en X8 |

Si el equipo quiere usar más GPU de la que pide este plan, el mejor uso es ampliar X16, X17 y X13 (más semillas, más cortes, más orígenes), no las propuestas descartadas.

---

## 4. Plan de cómputo

Estimaciones propias a partir de mediciones del repo (L4: 1.5–13 ms por pronóstico, nb04 celda 28; ajuste fino de Chronos-2: ~26–30 min en A100; TabPFN-TS en ETT_1D: ~2.3 s por pronóstico con contexto corto). Son supuestos, no mediciones de este plan.

| Nivel | Experimentos | CPU (vCPU-h) | L4 (h) | A100 80 GB (h) | H100 (h) | Otros |
|---|---|---|---|---|---|---|
| 1a | X0-min, X1-min, X4-CPU, X5-col, textos | ~5–8 | 0 | 0 | 0 | Colab gratuito; colectores en la máquina en vivo |
| 1b | X0, X1, X2, X3, X4, X5, X6 | ~30–45 | ~2 (+1 por mes de X5) | ~7 | 0 | VM de CPU continua para X5 |
| 2 | X7–X15, X21 | ~280–340 | ~67 | ~31 + X13 según piloto (reserva ~30) | 0 | Descarga REE con límite de tasa |
| 3 | X16–X20 | ~20 | ~31 | ~140 | ~8 (condicional) | ~2 personas × 3 días (X19) |
| **Subtotal** | | **~335–415** | **~100** | **~210** | **~8** | |
| **Con 25 % de contingencia** (caídas, reintentos) | | **~420–520** | **~125** | **~260** | **~10** | |

Detalle de A100-h: Nivel 1b = X4 (7). Nivel 2 = X7 (7, opcional) + X8 (6) + X9 (5) + X14 (13) + X13 (reserva de ~30 hasta el piloto). Nivel 3 = X16 (40) + X17 (80) + X18 (15–20) + X20 (2).

Notas:
- **Lo que limita es el tiempo de las personas, no la GPU.** Antes de TB1 solo cabe el Nivel 1a, sin GPU. Que haya GPU de sobra no cambia el orden: cambia cuánto se amplía X13, X16 y X17 después.
- Los diseños descartados pedían ~1,380 A100-h + ~230 H100-h; este plan necesita alrededor de una sexta parte.
- Imágenes separadas solo para lo que se usa: `fm-main` (torch y el `instalar.sh` del repo con `--no-deps`), un venv aparte para TabPFN-TS con el checkpoint fijado y otro para `statsforecast` si se agrega B8.
- La reanudación por bloques de `fm_bench.py` se mantiene en todo y las escrituras son atómicas (`.tmp` → rename).

**Opciones de infraestructura** (precios: consultar la tarifa vigente; costo = horas × tarifa):

| Opción | Uso recomendado | Ventajas | Cuidados |
|---|---|---|---|
| Colab gratis / Pro / Pro+ | Nivel 1a y 1b, lectura de Drive, inferencia chica en L4 | Acceso directo a Drive; ya se usa | Sesiones que se caen (PR #27, `chronos_cdd`): siempre con checkpointing; unidades de cómputo limitadas |
| VM de CPU en la nube (64–96 vCPU, spot) | X10, X11, X14 (RF), X6 completo, rolling SEIN de X1 | Barato para el grueso tabular | Bajar los datos de Drive a un bucket privado con sha256 |
| Nubes de GPU especializadas (Lambda, RunPod, Vast.ai u otras) | X13, X16, X17, X18 en A100/H100 | Por lo general más baratas que las grandes nubes (supuesto a verificar) | Disponibilidad variable; spot puede interrumpirse |
| AWS / GCP / Azure bajo demanda | Respaldo; X5 (VM siempre encendida) | Estables; posibles créditos educativos | Por lo general más caras (supuesto a verificar) |
| Máquina en vivo actual | X5 (colectores e inferencia en CPU) | Ya existe; inferencia de Chronos en CPU reproduce Colab | Depende del cron del dueño y de un token de rclone vencido: hace falta respaldo en la nube |

---

## 5. Secuencia y dependencias

Fechas fijas del curso (de `docs/demo/README.md:4` y del análisis de brechas):
- **TB1:** jueves 3-dic-2026, 19:00, virtual.
- **Entrega de la semana 15:** fecha sin confirmar en el Aula Virtual (spec §12: entre fines de noviembre y la primera semana de diciembre). Confirmarla.
- **DD1 y TB2:** sin fecha en el repo.

No se fijan otras fechas; el orden importa más que el calendario.

### 5.1 Antes de TB1 (Nivel 1a, solo CPU, ~5–8 CPU-h)

1. **Hoy:** colectores de X5 y congelamiento del CSV del portal con sha256. En paralelo: paso 0 de X0 (bajar predicciones de Drive desde Colab; responsable y fecha por asignar).
2. **`prereg-v1` commiteado y con tag**: definiciones de referencias (con la regla de rezago), pruebas, familias, etiquetas y las hipótesis de X5 (v1).
3. X0-min: referencias en `REFERENCIAS`, `assert` de rezagos, DM con bootstrap circular.
4. X1-min sobre predicciones guardadas (Tetuán test, SEIN validación 2025, nb03 2026 con política C, nb04).
5. X4-CPU exploratorio (PDO frente a Δsemana y suma de áreas existente).
6. Corrección de textos (sección 6.2) con lo que sobreviva.

### 5.2 Después de TB1

- **Bloque A (en paralelo, sobre todo CPU):** X0 completo, X1 completo (rolling SEIN 2023-25 reentrenado), X2 validación, X3 (R1 y por área), X6, X21, X15, X10, X11 (lanzar la descarga REE el primer día), X8 (incluye terminar `chronos_cdd`), X12-SEIN.
- **Bloque B:** X4 fase GPU (después de X3 y, si se quiere clima, X8); X14 (reelección de receta en 2022 y cortes, que X9 reutiliza); X9; X7 (necesita X4 y X8).
- **Congelamiento** de X4 (I-pub), X7 y X12-SEIN → `prereg-v2`; desde su hash corre la parte confirmatoria de X5.
- **Bloque C (cuando haya GPU y tiempo):** X13 (piloto primero) → X18; X14 → X17 → X18; X16 cuando X5 tenga suficientes datos posteriores a la publicación de cada modelo (el MDE dice cuántos); X12 de Tetuán y Ceuta tras X10 y X11; X19 si llega el acceso a IEEE Xplore; X20 si se cumplen sus condiciones.
- **Cierre de X5** en la fecha de parada que fije su MDE anytime-valid.

### 5.3 Dependencias

| Experimento | Depende de |
|---|---|
| X5 colectores | Nada |
| `prereg-v1` | Nada (se escribe con X0-min) |
| X0 | `prereg-v1` (en paralelo) |
| X1 | X0, `prereg-v1` |
| X2 | X0 (y Drive) |
| X3 | X0, X1 |
| X4 | X0, X1, X3; X8 opcional; X21 (decisión sobre N+C+S) |
| H3c | X4 |
| X6 | X0 |
| X7 | X4, X8 |
| X8 | X0 |
| X9 | X3, X4, X14 |
| X10 | X0, X1 |
| X11 | X0, X1, X10 |
| X12-SEIN | X0, X1 |
| X12 Tetuán y Ceuta | X10, X11 |
| X13 | X0, X1, X15 |
| X14 | X0, X1 |
| X15 | X0, X1 |
| X21 | X0 |
| `prereg-v2` | X4, X7, X12-SEIN |
| X5 confirmatorio | `prereg-v1` (v1); `prereg-v2` (v2) |
| X16 | X5, X13 |
| X17 | X0, X14 |
| X18 | X13, X17 |
| X19 | X6, X15 (y acceso IEEE) |
| X20 | X5, X7 |

Ruta crítica hacia la evidencia confirmatoria: `prereg-v1` → X0 → X1 → X3 → X4 → X7 (+ X12-SEIN) → `prereg-v2` → X5.

---

## 6. Qué cambia en el paper

### 6.1 Tablas y figuras nuevas

| Tabla o figura | Sale de | Reemplaza o se agrega a |
|---|---|---|
| Escalera de referencias por acto y horizonte, con skill doble, p de Holm y etiqueta (reanálisis o confirmatorio) | X1 | Tabla de "41–56 %" (`short-paper.qmd:74-80`); columnas nuevas en `tbl-validacion`, `tbl-prueba`, `tbl-fundacionales` |
| Tetuán: modelo frente a B2/B3/B4/B9 con DM e IC (reanálisis) | X2 | `paper.md:389-432` |
| Conteo de zona-meses y área-meses ganados frente a la referencia más fuerte | X1, X10 | "24/24" y "108/108" |
| Tabla de MDE y tamaño empírico de las pruebas | X0 | Sección de métodos (nueva) |
| Cara a cara con el PDO (08:00 igual información, 16:00 cota, I-pub) y figura de error por hora y anticipación | X4 | Párrafo internacional (`qmd:345-350`) y limitación (`qmd:410-411`) |
| Réplica PR-03 y descomposición de la brecha con el PDO | X3 | Nueva |
| PDO + modelo: MAE, sesgo, cuantiles de error en MW | X7 | Nueva; titular operativo si se cumple |
| Tabla descriptiva de El Niño 2017/2023/2026 | X4, X7 | Discusión de El Niño |
| Escalera de inflación del R² | X6 | Argumento de `docs/estado-del-arte.md` |
| Efecto del objetivo y de la normalización (2×2) por sistema × aprendiz | X10 | Afirmación de `paper.md:444` |
| Forest plot de Ceuta y Melilla | X11 | `paper.md` §5.2, `:50`, `:444-446` |
| Pico en días cálidos con GFS real | X8 | Conclusión "el clima no ayuda" |
| Feriados frente al PDO (con el resultado negativo de ftcal2) | X9 | Lista de fallas (criterio de éxito 4, `qmd:93-98`) |
| Diagramas de fiabilidad, CRPS y pruebas de cobertura | X12 | Intervalos de la app y §5.7 |
| Estabilidad del ranking entre años | X14 | Selección de una sola partición en nb02_sein y nb04 |
| FM en Tetuán y Ceuta, con comparador reentrenado | X13 | Nueva |
| Datasheet de rarezas de UCI 849 | X15 | Sección de datos |
| Nota de saneamiento (fallas, cuarentena, días sin IEOD, N+C+S, SHAP) | X21 | Afirmación "las fallas no ayudan" y sección de explicabilidad |
| Resultado prospectivo | X5 | Sección confirmatoria (TB2 o versión posterior) |
| Contaminación de FM | X16 | Frase "no se puede auditar" |

### 6.2 Afirmaciones actuales que hay que corregir

Se pueden corregir ya, antes de tener resultados nuevos:

- **"41–56 %" y "vara exigente"** (`short-paper.qmd:74-80`, `:423`; `paper.md:389-432`; `README.md:90`, `:189`; `docs/historico.md:24-28`, `:517`): reescribir con skill doble (X1, X2). Cifras honestas hoy: ~12–19 % en Z1/Z2 frente al delta diario, pérdida en Z3. Todo Tetuán se rotula reanálisis.
- **Ceuta** (`paper.md:50`, `:444`): V4 sin verano pierde contra el delta semanal en 5 de 5 veranos.
- **Criterio de éxito "vencer a la mejor de tres"** (`docs/negocio.md` §8): reportar ambos criterios (mejor de 3 y referencia más fuerte) y declarar que el cambio de criterio principal es posterior a ver los resultados.
- **Conteo de trabajos con referencia ingenua** (`paper.md:84-87`): son 4 de 41 (incluye Bunke y Electronics 15:5213, que usa "ayer"), no "ninguno con ayer".
- **Novedad.** "Z1, 10 min, t+6" ya lo hizo Wei (2023). "FM sobre UCI 849" ya lo hicieron Singh & Tewari (2026, Chronos en Z2 a t+1, cronológica). La novedad defendible es "t+6 contra referencias delta con pruebas pareadas" y "FM a t+6 contra referencias delta, con pruebas pareadas y controles limpios" (X13). Si se cita a Wei, aclarar su mezcla de escalas (suma horaria frente a media).
- **"24 h" en vivo:** se emite hacia las 10:00 del día objetivo; decirlo y no llamarlo "día siguiente".
- **"Las fallas no ayudan":** la variable `fallas_en_curso` está degenerada (activa el 91 % de 2025). Retirar la frase o reescribirla como limitación hasta X21.
- **Al-Quraan −48 %** (`paper.md:423`): no citar (3.43 % es FedAvg y el MAPE quizá se calculó sobre datos escalados).
- **ICSIST 3.17 %:** solo con la salvedad de que su Tabla II dice 8.82 %.
- **IRSEC 2018:** partición "cronológica, inferida de figuras", no "aleatoria 75/25"; RMSE 3,174.7 es Z1 y 2,336.9 es Smir.
- **Unidades y zonas:** "kW declarado por los autores, sin documentar"; reescalado mensual entero sin documentar; Z2 = Boussafou y Z3 = Smir "inferido de figuras".
- **Clima:** "el clima no ayuda" → "el clima simulado no ayuda en promedio" (hasta X8).
- **Fuga de diseño:** declarar que la arquitectura de Tetuán se eligió mirando los folds Mar–Dic y el test, que la receta de ftcal se eligió en 2025 y que 2026 se exploró antes del test.
- **Fuente de cifras:** las mejoras del test 2026 salen de nb03 celda 9 (la 11 es la ablación).
- **Inconsistencias internas:**
  - `paper.md:609-610` invierte los MAE de t0-gamma y Toto-2 (50.7 y 51.8) respecto a `:1283-1285`, y TiRex-2 es peor que TimesFM 2.5 (59.5 frente a 57.0).
  - `paper.md` §5.8 (líneas 795, 818, 969, 1047): los PR #53 y #55 ya están fusionados.
  - `paper.md:427`: la fila "Total MAPE 1.42 % (por verificar)".
  - `experimentos/ceuta/validacion.py:84` y nb00b celda 13 promedian 2021+, mientras los documentos reportan 2022-26.
  - El modelo seleccionado (RF M0) no es el que se explica (SHAP sobre XGB M3) ni el que se sirve (Chronos-2 ft y combinación).

---

## 7. Riesgos y preguntas abiertas

### 7.1 Riesgos principales

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Predicciones y capas silver/gold solo en Drive; token de rclone vencido | Bloquea X1-min, X2 y todo reanálisis | Bajar todo desde Colab como paso 0 (con responsable y fecha) y copiarlo a un bucket privado con sha256; renovar el token |
| Predicciones de validación y del rolling no guardadas | X2 y H1d exigen reentrenar | Reajustar solo con `entrenamiento` con `busqueda.csv`; rehacer el rolling con el arnés de X10 |
| La columna "Programación Diaria" del portal podría no ser el PDO original | X4 y X7 favorecen o castigan al PDO de más | Instantáneas de X5; veredicto condicionado; declarar |
| Asimetría de información frente al PDO | "Le gana" inflado | Origen 08:00 como comparación principal; 16:00 como cota |
| Perímetro portal/IEOD (+1–1.5 %); 48 periodos con N+C+S ≠ SEIN en 2026 | Sesgo en MAE | MAPE como primaria frente al PDO; diagnóstico en X21; sensibilidad excluyendo esos periodos |
| Revisiones del Ejecutado del portal | Comparaciones con datos preliminares | CSV del 22-nov congelado con sha256; nueva descarga mensual en X5 |
| Ventana prospectiva corta | Poca potencia | MDE anytime-valid antes de registrar; fecha de parada publicada; no sobreinterpretar nulos |
| Caminos que se bifurcan (factoriales, paneles grandes) | Falsos positivos | Preregistro, familias de Holm declaradas, reporte de todas las celdas, MCS con regla de desempate |
| Endpoints no documentados (REE de 5 min, tiempo real del COES) | Pérdida de datos | Archivado diario, alertas, respaldo |
| Licencias no comerciales (TimesFM 3.0, TimeH2O, TabPFN-3.x, Moirai 2.0, ChakraTS-OS) y cláusula de Timestral | Uso operativo no permitido | Solo curso y paper; verificar Timestral si el trabajo se asocia al empleador |
| APIs que envían datos al proveedor | Incumplir la política del CIP | TabPFN-TS solo en LOCAL; no usar ChakraTS API ni PDM |
| Tiempo humano en la semana de TB1 | Nivel 1 incompleto | Nivel 1a acotado a referencias, DM, PDO-CPU, colectores y textos; el resto después |

### 7.2 Lo no validado con especialistas

Si la validación con un especialista del SEIN, con el COES, con la profesora o con alguien que conozca la red de Tetuán no llega a ocurrir, el plan no depende de ella. Estas son las alternativas, de más a menos fuerte:

1. **Validar con datos públicos** lo que se pueda contrastar:
   - Vigencia de la columna del PDO: instantáneas archivadas en X5 frente a la columna del portal.
   - Lectura del PR-03: R0 (`pr03_replica.py`) **no** se implementó a ciegas, porque la cifra 2.2–2.5 % se conocía; su distancia al PDO es solo evidencia indirecta. R1 y la versión por área, implementadas desde el texto por alguien que no vio las cifras y congeladas antes de calcular, sí sirven como contraste más limpio.
   - Feriados de Perú: contrastar la tabla curada con los decretos publicados en El Peruano y con caídas de demanda en el IEOD.
   - Feriados de Ceuta y Melilla: boletines oficiales (BOCCE, BOME).
   - Zonas de Tetuán: figuras primarias de IRSEC y de Islam et al. (2025).
   - Reloj y cambio de hora: X15 con la irradiancia.
   - Fechas de El Niño: comunicados oficiales del ENFEN.
   - Composición de los checkpoints de TiRex-2 (UCI 321): fichas de los modelos.
2. **Consultar documentos normativos** en sus versiones vigentes: procedimientos técnicos PR-03, PR-06 y PR-22 en el portal del COES; informes de Osinergmin sobre reserva secundaria; Anexo 1 del PR-06 para la tolerancia τ. Registrar qué versión se leyó y su fecha.
3. **Consultas por escrito de bajo costo**, que no requieren ir en persona: correo al área de programación o de atención de información del COES con 2 o 3 preguntas cerradas (versión vigente del PR-03, si la columna del portal es el PDO original, dónde se publican los RDO); consulta a un docente de sistemas de potencia de la universidad. Si no hay respuesta, se pasa al punto 4.
4. **Declararlo como limitación** en el paper, con una lista explícita de lo inferido y no validado: correspondencia de zonas, unidades, feriados y Ramadán de Tetuán, feriados de Ceuta y Melilla, lectura del PR-03/PR-06/PR-22, tolerancia τ, proxies de reserva, vigencia de la columna del PDO, tabla curada de feriados del Perú, uso de IEOD como sustituto del SCADA.

### 7.3 Preguntas abiertas

- ¿Quién baja las predicciones de Drive desde Colab (paso 0) y cuándo? Bloquea X1-min y X2.
- ¿Cuál es la fecha exacta de la entrega de la semana 15, y existe TB2 con fecha? Define si la fecha de parada de X5 cae antes de TB2.
- ¿Qué versión del PR-03 está vigente? ¿Dónde se publica el archivo de RDO? ¿Cuál es la τ del PR-06?
- ¿El portal publica el Ejecutado en tiempo real y con qué latencia? (X5 lo mide.)
- ¿REE publica previsión o programa para Ceuta (P6)? ¿Existe un endpoint de 5 min para Melilla?
- ¿Desde cuándo tiene archivo ECMWF IFS en Open-Meteo Previous Runs?
- ¿El Aid al-Adha de 2017 en Tetuán fue el 1-sep o el 1 y 2? ¿Los timestamps de UCI 849 están en hora civil o con desfase fijo? ¿Fechas exactas de Ramadán 2017 en Tetuán?
- ¿Qué incluye el corpus de Simons (36.92 % de fuentes privadas)? Sin respuesta del proveedor, solo X16 puede dar evidencia.
- ¿Qué checkpoint de TiRex-2 incluye UCI 321? (Verificar antes de registrar H16a.)

### 7.4 Accesos ("si necesitas otra API")

- **No hace falta el PDF de IRSEC 2018** para el Nivel 1: X6 trabaja con las figuras y tablas primarias ya leídas con Semantic Scholar.
- **Prioridad 1:** acceso institucional UPC a IEEE Xplore (proxy o API key). Sube el nivel de evidencia de X19 y confirma la partición de IRSEC.
- **Prioridad 2:** token gratuito de la API ENTSO-E Transparency (control secundario de X16).
- Después: Elsevier con token institucional, Wiley TDM, Springer TDM, CORE.
- **Llave de Semantic Scholar:** se pegó en texto plano en la conversación. No se usó en esta revisión. No debe ir al repo ni a notebooks; usar variable de entorno o secreto de Colab, y **rotarla**. Lo mismo para cualquier token futuro. Respetar su límite de 1 solicitud por segundo.

### 7.5 Datos sensibles y política

- `short-paper.qmd:7-31` contiene nombres, códigos y correos de estudiantes (PII). Ningún experimento lo necesita; minimicen cuánto se comparte al circular borradores.
- Este plan resume trabajos de terceros y resultados no publicados del equipo.
- Las cifras nuevas citadas aquí deben revisarlas especialistas antes de que entren al paper o a la exposición.

---

Validar con especialistas antes de ejecutar o citar.
