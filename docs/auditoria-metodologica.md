# Auditoría metodológica del proyecto

Fecha: 12 de noviembre de 2026. Alcance: la metodología de los tres casos (Tetuán, Ceuta y el SEIN) tal como
quedó en la rama `develop` (commit `447bbc1`), con foco en el caso central del SEIN. Se revisaron el código
de `src/`, los notebooks ejecutados (`01_sein_datos_preparacion`, `02_sein_modelado_evaluacion`,
`03_sein_prueba_2026`, `01_datos_preparacion`, `02_modelado_evaluacion` y `entregables/Entregable6_MDS_Grupo03`),
las tablas de resultados de 2025 (`reportes/sein/modelado/*.csv`, corrida del 4-nov en la L4) y de 2026
(`reportes/sein/prueba_2026/*.csv`), la spec (`docs/superpowers/specs/2026-10-23-demanda-sein-areas-design.md`,
PR #11), `docs/` y el historial de git. **No se reejecutó nada y no se cambió ningún notebook, código ni
resultado.** Las celdas se citan por su índice dentro del `.ipynb` (de 0 en adelante, contando las de texto).

## Resumen

Ningún hallazgo obliga a rehacer una corrida. La disciplina temporal (regla de información, particiones con
hueco, elección en 2025, prueba de 2026 corrida una sola vez) está implementada en `src/` y cubierta por tests,
y las cifras de los notebooks se corresponden con las tablas guardadas. Lo que hay son **tres hallazgos graves de
redacción** (uno de ellos, G1, ya resuelto en el PR #30 el 12-nov), que cambian afirmaciones que el paper no
debe hacer tal como están en los notebooks o en los docs;
**quince puntos que hay que declarar** en la sección de limitaciones; y **once menores**.

| Clase | Cuántos | Qué implican |
|---|---|---|
| **Grave (de redacción o de alcance)** | 3 (G1 ya resuelto) | Cambian una afirmación o un objetivo del paper. No piden rehacer corridas |
| **A declarar** | 15 | Van a la sección de limitaciones o amenazas a la validez, o cambian cómo se presenta un resultado |
| **Menor** | 11 | Se anotan; no cambian conclusiones |

Los tres graves, en una línea cada uno:

- **G1.** La importancia por permutación incluye la columna de escala `media_24h`, que no es una variable del
  modelo: al permutarla se rompe la reconstrucción a MW y sale como "la más importante" (207 MW en el Centro).
  El paper no debe presentarla como variable. **Resuelto** en el PR #30 (`fix/importancia-sin-escala`, commit
  `c687feb`, sin fusionar a `develop` al 12-nov): los notebooks 02 del SEIN y de Tetuán y la app quitan la fila; el
  grupo "demanda y calendario" baja de 455.3 a 248.0 MW en el Centro y ninguna conclusión cambia.
- **G2.** `fallas_en_curso` no mide fallas: es mayor que cero en el 91 % de los periodos de 2025 y su media por
  periodo creció de 0.47 en 2016 a 1.8 en 2026 por cómo se registran los eventos. Las conclusiones del tipo
  "las fallas no ayudan" no están respaldadas: la variable **no se pudo evaluar**. La variante con exógenas que
  el paper debe presentar es M2 (clima y El Niño), que también se corrió en 2025 y 2026.
- **G3.** La comparación con la Programación Diaria del COES (spec §8.2.1) y el SEIN modelado directo a 24 h no se
  hicieron. El objetivo específico 3 y el texto de la introducción de `docs/paper/estructura.md` todavía dicen
  "y cómo queda frente al pronóstico oficial del COES": hay que quitarlo. **En el borrador del paper ya está
  hecho:** el OE3 no lo menciona, §6.4 lo lista como "lo que no se hizo" y §7 lo declara como trabajo futuro. Lo
  mismo con G2: la tabla de ablación de 2026 del paper lleva la columna M2 − M0 y el texto lee "las exógenas"
  sobre M2.

## Tabla de hallazgos

| ID | Tema | Clase | Hallazgo |
|---|---|---|---|
| G1 | Importancia de variables | Grave · **resuelto (PR #30)** | La escala `media_24h` aparecía como variable más importante (artefacto); los notebooks ya la excluyen |
| G2 | Ablación de exógenas | Grave | `fallas_en_curso` es una variable degenerada; "sin efecto de las fallas" no está respaldado |
| G3 | Alcance | Grave | No hay comparación con la Programación Diaria del COES; el OE3 la menciona |
| D1 | Supuesto COES-ENFEN | A declarar | A 1 h el "observado" es ERA5 (reanálisis con ~5 días de rezago); a 24 h el pronóstico simulado es la observada futura más N(0, 1.5 °C) por día; la spec prometía dos niveles (1 y 2 °C) |
| D2 | Selección de modelo | A declarar | Empate RF/XGBoost (0.3 puntos, sin intervalo); búsqueda solo en el Centro a 1 h y presupuesto desigual; la app sirve el XGBoost global, no el "elegido" |
| D3 | Hipótesis previas | A declarar | Se escribieron antes de correr el modelo en 2026, no antes de mirar los datos de 2026 (el crecimiento del Norte ya se conocía) |
| D4 | Intervalos | A declarar | 66 intervalos al 95 % en 2026 sin corrección por comparaciones múltiples; los efectos "distinguibles" van de 0.09 a 1.48 MW (menos del 2 % del error) |
| D5 | Bootstrap por días | A declarar | Bloques de un día: a 24 h los errores de días vecinos siguen correlacionados; un solo año y un solo evento |
| D6 | Origen móvil | A declarar | Los hiperparámetros se eligieron con CV sobre 2016-2024 y se usan para evaluar 2023-2025 (fuga leve de hiperparámetros, no de datos) |
| D7 | Corrida 2026 con caché | A declarar | La caché se agregó a mitad de la corrida; la clave no incluye un hash de datos ni de código; el determinismo se afirma, no se demuestra |
| D8 | Periodo de prueba | A declarar | La prueba efectiva va del 1-ene al 17-oct-2026 (1 h) y al 16-oct (24 h), no "enero a octubre": la recorta la disponibilidad del clima |
| D9 | Regla de información de la demanda y de las fallas | A declarar | El IEOD validado ex post sustituye al SCADA; el retraso de publicación de los eventos del COES no se midió; los eventos sin fecha de fin se descartan |
| D10 | Regímenes ex post | A declarar | Las horas de mayor demanda de 2026 y los días "fuera de lo visto" se definen con los datos de 2026 |
| D11 | CPU/GPU | A declarar | Random Forest en CPU porque cuML no es reproducible; XGBoost entrena en GPU y se guarda en CPU (`portable`); una sola semilla |
| D12 | Ceuta | A declarar | Experimento sin ajuste de hiperparámetros, una semilla, sin intervalos; otro sistema |
| D13 | Tetuán | A declarar | Unidad (kW) e identidad de las zonas sin fuente primaria; la temperatura del dataset no coincide con ERA5; el modelo pierde en el Ramadán de la Zona 3 (−7.4 %) y su ventaja baja tras la transferencia (51 → 39 % en la Zona 1) |
| D14 | Variables no usadas | A declarar | Feriados con `holidays.PE` (nacionales), no la tabla curada de `docs/peru/tablas.md`; M4 (SAIDI) no se corrió; la alerta de ENFEN sale de cruces del ICEN, no de los comunicados |
| D15 | Entregable 7 | A declarar (lección) | El grupo entregó la versión en nivel, que pierde contra "ayer"; la corregida (en razón) está en el repo |
| D16 | Modelos fundacionales (extensión del 13-nov) | A declarar | Se hizo después de la prueba de 2026: elegido con 2025, 2026 solo confirma; los pesos de la combinación final son de 2025 (dentro de muestra) y sin intervalos; posible contaminación del preentrenamiento; licencias distintas; el "XGBoost base" de esa comparación no es el del notebook 03 |
| M1 | Tetuán, Ridge | Menor | `alpha` = 0.001 queda en el borde de la grilla |
| M2 | Auditoría del silver | Menor | En 2026, N + C + S − SEIN llega a 47.6 MW ("a revisar antes de la prueba") y no se revisó; no afecta a los modelos por área |
| M3 | Variables a 24 h | Menor | `Area_ayer` duplica `Area_t` a 24 h (ayer = persistencia) |
| M4 | App | Menor | Los intervalos de la app usan los errores de 2025 del Random Forest sobre predicciones del XGBoost |
| M5 | Semillas | Menor | Una sola semilla en Random Forest, XGBoost, el bootstrap y el ruido del pronóstico |
| M6 | Salidas | Menor | Los "0.0 min" del notebook 03 vienen de la caché (ya explicado en sus conclusiones) |
| M7 | Tetuán, notebook 02 | Menor | Las conclusiones siguen vacías ("Se completan con los resultados de la corrida") |
| M8 | Ruido del pronóstico | Menor | `error_pronostico_diario` depende del rango de fechas del dataset: la app puede ver otra realización del ruido |
| M9 | Cuarentena | Menor | Solo la fase estricta (16-mar a 1-jul-2020), no las fases de la tabla |
| M10 | README | Menor | Las cifras "52, 58 y 29 %" del README son del XGBoost global; el modelo elegido da 51.7, 57.9 y 29.1 |
| M11 | Presupuesto de búsqueda | Menor | 15 combinaciones para Random Forest (de 243 posibles) frente a 30 para XGBoost; en Tetuán, 8 frente a 20 |

## Hallazgos en detalle

### 1. Regla de información y fugas

**Qué se revisó.** `src/tetouan_power_forecast/variables_sein.py` (`dataset_area`, `_temperatura_conocida`,
`_temperatura_interpolada`, `error_pronostico_diario`, `particion`, `filas_comunes`), `exogenas.py`
(`icen_disponible`, `nino12_disponible`, `saidi_disponible`, `fallas_en_curso`), `modelado_sein.py`
(`bloques`, `predecir_por_bloques`) y los tests `tests/test_variables_sein.py`, `test_exogenas.py` y
`test_modelado_sein.py`.

**Lo que se sostiene.**

- Todas las variables de demanda se calculan en t con rezagos hacia atrás (`y.shift(r)`), y el objetivo es
  `y.shift(-horizonte)`; "ayer" y "semana pasada" se toman a la hora de t+H restando el horizonte
  (`y.shift(48 − H)`, `y.shift(336 − H)`). Verificado en el código (`variables_sein.py`, `dataset_area`) y en
  `test_referencias_y_objetivo_a_1_h`.
- La temperatura en t es la última hora ya publicada (`_temperatura_conocida`, con `ffill` y sin interpolar) y
  queda vacía pasado el archivo de clima (`test_la_temperatura_en_t_es_la_ultima_hora_ya_publicada`,
  `test_pasado_el_archivo_de_clima_la_temperatura_queda_vacia_y_la_fila_sale`). El notebook 01 del SEIN lo
  verificó además en una muestra de 200 periodos (celda 25).
- El ICEN entra con su rezago de publicación (el de m−2 desde el día 20, el de m−3 antes); el Niño 1+2, con 9 días;
  el SAIDI, con el de m−2 desde el día 7 (`exogenas.py`, tests `test_icen_entra_segun_su_publicacion`,
  `test_nino12_semanal_con_columnas_pegadas_y_rezago`, `test_saidi_entra_segun_su_publicacion`).
- La climatología de la anomalía de temperatura se cierra en el fin del entrenamiento (`FIN_CLIMATOLOGIA =
  2025-01-01`) y, en el origen móvil, antes del primer mes evaluado (`fin_climatologia=DESDE_MOVIL`, notebook 02,
  celda 25).
- En el reentrenamiento por bloques, cada bloque se entrena solo con lo anterior al hueco
  (`predecir_por_bloques`; `test_cada_bloque_se_entrena_solo_con_lo_anterior_al_hueco`) y los bloques cubren la
  evaluación sin solapes (`test_los_bloques_cubren_la_evaluacion_sin_huecos_ni_solapes`).
- La política "alerta de ENFEN" usa la categoría del ICEN **ya publicado** en t (`categoria_icen(icen_disponible(...))`,
  notebooks 02 y 03), no el definitivo del mes.

**D9 (a declarar).** Tres puntos que la spec ya reconoce y que el paper tiene que decir:

- La demanda "en t" sale del IEOD, que el COES valida y publica al día siguiente. Es el sustituto del SCADA que el
  operador sí tiene en tiempo real (spec §6). No es una fuga, pero sí un supuesto.
- Las fallas en curso se arman con el registro de eventos del COES, que es ex post. Cuánto tarda un evento en
  aparecer en el registro no se midió (spec §6: "falta medir con cuánto retraso se publican").
- `fallas_en_curso` descarta los eventos sin fecha de fin (`dropna(subset=["inicio", "final"])`,
  `exogenas.py`): los eventos todavía abiertos al cierre de los datos no cuentan, así que en los últimos días de la
  serie la variable queda sesgada hacia abajo. Como la variable es degenerada (G2), el efecto práctico es nulo.

**D10 (a declarar).** Dos cortes de la evaluación se definen con la propia prueba: las "horas de mayor demanda"
de 2026 son las cuatro horas con más demanda media de cada área **en 2026** (`horas_mayor_demanda`, notebook 03,
celda 18), y los días con "temperatura fuera de lo visto" se marcan comparando 2026 con el máximo del mismo mes
de 2016-2025 (`dias_fuera_de_rango`, misma celda). Son estratificaciones ex post, válidas para describir dónde
falla el modelo, pero no son reglas que el operador pueda aplicar antes de tiempo. Lo mismo vale para la "mejor
referencia", que se elige en la propia prueba (notebook 03, celda 7): es la vara más exigente, no una elección
anticipada.

### 2. Particiones y huecos

**Lo que se sostiene.** `particion(fechas, horizonte)` deja H pasos de hueco antes de cada corte (filas cuyo
objetivo cae en la partición siguiente), y `filas_comunes` deja las mismas filas para M0 a M3
(`test_particion_con_hueco`, `test_variantes_y_filas_comunes`). El notebook 02 aparta la prueba en su primera
celda y lo comprueba con dos `assert` (celda 5: ninguna fila de prueba y ninguna fecha de 2026). El tramo
"desarrollo" (entrenamiento + validación) incluye el hueco anterior a 2025, cuyos objetivos caen en la
validación, y no el anterior a 2026 (`tramo`, `test_el_tramo_de_desarrollo_junta_entrenamiento_y_validacion`).
Conteos por área: 154,791 / 17,518 / 13,920 filas a 1 h y 154,423 / 17,472 / 13,871 a 24 h, con 4 y 96 filas de
hueco (notebook 01 del SEIN, celda 24).

**D8 (a declarar).** La prueba termina el **17 de octubre a las 23:30 a 1 h** y el **16 de octubre a las 23:00
a 24 h** (notebook 03, celda 5), aunque la demanda llega al 23 de octubre: `filas_comunes` exige filas completas
para M0 a M3, y la temperatura de ERA5 llega con unos cinco días de rezago. Eso tiene dos consecuencias que el
paper debe decir: (1) el periodo de prueba es "del 1 de enero al 17 de octubre de 2026 a 1 h y al 16 de octubre a
24 h" y (2) M0, que no usa el
clima, también se evalúa solo donde el clima existe (por diseño, para comparar variantes sobre las mismas filas).

**M2 (menor).** La auditoría del silver (notebook 01 del SEIN, celda 6) reporta que en 2026 la suma Norte +
Centro + Sur se aparta del SEIN hasta 47.6 MW (en 2019, hasta 5.66 MW; el resto, 0.00), y el texto dice "a
revisar en la auditoría antes de la prueba". No consta que se haya revisado. No afecta a los modelos, que
pronostican las áreas y no usan la columna SEIN; conviene anotarlo como calidad del dato en la fase 2.

### 3. Referencias ingenuas

**Lo que se sostiene.** Tres referencias (persistencia, ayer y semana pasada a la hora de t+H) y comparación
contra la **mejor de las tres** en cada área, horizonte y tramo (`mejor_referencia`,
`test_la_mejor_referencia_es_la_de_menor_mae`). A 24 h, "ayer" coincide con la persistencia
(`test_a_24_h_ayer_es_la_persistencia`). En 2025 y en 2026 la mejor a 1 h fue la persistencia en las tres áreas; a
24 h, "semana pasada" en el Norte y el Centro y la persistencia en el Sur (notebook 02, celda 7; notebook 03,
celda 7). La elección de la mejor en la propia prueba hace la vara más exigente (D10).

**M3 (menor).** A 24 h, `Area_ayer = y / m24` es la misma columna que `Area_t` (`dataset_area`,
`variables_sein.py`). Es inocuo para los árboles, pero son 26 variables en M0 y una está repetida.

### 4. Origen móvil

**Lo que se sostiene.** `plegados_mensuales` entrena con todo lo anterior al mes menos el horizonte
(`test_plegados_mensuales_dejan_una_hora_y_omiten_meses_cortos`), y el origen móvil del SEIN usa datasets propios
con la climatología cerrada antes de enero de 2023 (notebook 02, celda 25). El modelo le gana a la mejor
referencia del mes en los 108 meses-área de 2023 a 2025 (notebook 02, celda 25: "M0: le gana a la mejor
referencia en 108 de 108 meses-área"); en Tetuán, en los 24 meses-zona de marzo a octubre (notebook 02 de
Tetuán, celda 21).

**D6 (a declarar).** Los hiperparámetros del origen móvil son los elegidos con validación cruzada sobre el
entrenamiento 2016-2024 (notebook 02, celda 9). Para evaluar enero de 2023 se usan, entonces, hiperparámetros
elegidos con datos de 2023 y 2024. Es una fuga de hiperparámetros, no de datos ni de pesos: afecta poco a un
Random Forest, pero el paper debe decir que el origen móvil mide estabilidad, no que es una prueba ciega. En
Tetuán pasa lo mismo con los meses de marzo a septiembre de 2017.

### 5. Bootstrap por días e intervalos

**Lo que se sostiene.** `bootstrap_diferencia_mae` remuestrea **días enteros** y calcula la diferencia pareada
de errores absolutos (modelo − referencia) sobre los mismos periodos, con 2,000 réplicas y semilla fija
(`evaluacion.py`; `test_bootstrap_por_dias`). Es la forma correcta de comparar dos pronósticos sobre el mismo
periodo.

**D5 (a declarar).** El bloque es un día. A 1 h alcanza; a 24 h, el pronóstico de un periodo y el del mismo periodo
del día siguiente comparten casi toda la información, así que los errores de días vecinos siguen correlacionados y
los intervalos a 24 h pueden salir angostos. Además, todos los intervalos de 2026 miden la variabilidad **dentro de
un solo año y un solo evento**: no dicen nada de otro Niño ni de otro año. El paper debe presentar los intervalos
como "incertidumbre dentro de 2026".

**D4 (a declarar).** En 2026 se calcularon 30 intervalos de ablación (5 contrastes × 3 áreas × 2 horizontes) y
36 de adaptación (6 × 3 × 2), todos al 95 % y sin corrección por comparaciones múltiples
(`ablacion.csv`, `efectos_adaptacion.csv`). Con 66 intervalos se esperan tres "distinguibles" por azar. Los
efectos que sí se distinguen son chicos: el mayor es el de todas las exógenas juntas a 24 h en el Centro, +1.48 MW
(IC 0.24 a 3.03), y el mayor de un solo grupo, el clima, +1.35 (IC 0.10 a 2.97), sobre un MAE de 78 MW (menos del
2 %); el de reentrenar sin exógenas a 1 h va de −0.09 (Sur) a −0.43 MW (Centro). La lectura
honesta es "efectos de alrededor del 1 % del error, algunos distinguibles de cero dentro de 2026", no "el clima
empeora el pronóstico" a secas.

### 6. Selección de modelos en 2025 frente a la prueba de 2026 (y el empate)

**Lo que se sostiene.** Todo se eligió en 2025: el algoritmo (celda 15 del notebook 02), los hiperparámetros
(celda 9, `TimeSeriesSplit(5, gap=H)` solo sobre el entrenamiento; para el global, `CVPorFecha`), las variantes y
las políticas. El notebook 03 fija `ELEGIDO`, `ALTERNATIVO` e `HIPERPARAMETROS` en su celda 3 y los compara con
`modelo_final.json` del notebook 02 con dos `assert` ("Modelo e hiperparámetros verificados contra el notebook
02", salida de la celda 3). La prueba se corrió una vez (commit `49a263b`, 6-nov), con lo fijado en `cadf68e`
(5-nov). La regla de elección (mayor mejora media frente a la mejor referencia, promediada entre áreas) estaba
escrita antes de ver las cifras (notebook 02, celda 14 de texto).

**D2 (a declarar).**

- **El empate.** Random Forest por área 43.20 %, Gradient Boosting por área 42.93 %, Gradient Boosting global
  42.88 % (notebook 02, celda 15). La diferencia es de 0.3 puntos y no tiene intervalo: la decide el Sur (25.1
  frente a 22.9 %), mientras XGBoost gana en el Centro (56.7 frente a 55.5 %) y el Norte. En la validación cruzada
  de la búsqueda, XGBoost tuvo menor error (50.34 frente a 51.79 MW, `busqueda.csv`). En 2026 el XGBoost global
  queda apenas por encima a 1 h (52.4, 58.4 y 29.2 % frente a 51.7, 57.9 y 29.1 %) y apenas por debajo a 24 h
  (`frente_referencias.csv`). El paper debe decir "empate" y reportar los dos.
- **Búsqueda acotada.** Los hiperparámetros se buscaron solo en el **Centro a 1 h con M0** y se reutilizaron en las
  otras áreas, a 24 h y en M1-M3 (spec §7, notebook 02, celda 9). Es una decisión de cómputo declarada; el paper
  debe repetirla.
- **Presupuesto desigual (M11).** 15 combinaciones para Random Forest (9.1 min, de 243 posibles), 30 para
  XGBoost (3.0 min) y 13 para Ridge (`busqueda.csv`). En Tetuán, 8, 20 y 13. La comparación entre familias no
  está igualada en esfuerzo.
- **El modelo desplegado no es el elegido.** La app sirve el XGBoost global porque pesa decenas de MB en vez de
  1 GB y predice en milisegundos (`app/backend/pronosticador_real.py`, docstring). El paper debe decir qué modelo
  corre en la app y por qué.
- **M10.** El README cita "52, 58 y 29 %" (XGBoost global); el elegido da 51.7, 57.9 y 29.1. Elegir una sola
  convención para el paper (propongo las del elegido, con el XGBoost en la misma tabla).

**M1 (menor, Tetuán).** El Ridge de Tetuán eligió `alpha = 0.001`, el valor más chico de la grilla
(`reportes/modelado/busqueda.csv`). Como Ridge no fue el elegido, no cambia nada, pero en una defensa conviene
saberlo.

### 7. Ablación de exógenas

**Lo que se sostiene.** Dos cadenas (acumulativa M0 → M3 y quitando un grupo desde M3) sobre las mismas filas,
cada diferencia con su intervalo pareado (notebook 02, celda 19; notebook 03, celda 11). Las importancias por
permutación se midieron en la validación, por área y por grupo (notebook 02, celda 33).

**G2 (grave de redacción): `fallas_en_curso`.** El notebook 01 del SEIN (celda 18 y hallazgos) muestra que la
media de eventos en curso por periodo pasó de 0.47 en 2016 a 1.67 en 2025 y 1.80 en 2026, y que en 2025 hay al
menos uno en curso en el 91 % de los periodos (15,935 de 17,518; notebook 02, conclusiones). La variable refleja
cómo se registran los eventos, no si la red está fallando. El propio notebook 02 lo dice en "Qué revisar antes de
2026": "tal como está, la variable no separa la operación normal de una falla. Hay que restringir qué cuenta como
falla o sacarla de M3". El notebook 03 la mantuvo "para comparar con la validación" y agregó M2 (sin fallas) en
las políticas fija y semanal (celda 13). Consecuencias para el paper:

- No afirmar que "las fallas no ayudan". Lo correcto: "la variable de fallas, tal como se pudo construir con el
  registro público, no distingue la operación normal de una falla, y por eso su efecto no es interpretable".
- Presentar **M2** como la variante "con exógenas" (clima y El Niño) y M3 como variante secundaria. Las tablas de
  2026 tienen M2 en fijo y semanal (`adaptacion.csv`; contraste "Reentrenar sin fallas (semanal M2 − fijo M2)" en
  `efectos_adaptacion.csv`).
- En la importancia por grupo, "fallas" vale −0.01 MW en el Centro y 0.00 en las otras áreas
  (`importancias_por_grupo.csv`): no aporta ni daña.

**G1 (grave de redacción): la escala en la importancia.** `ModeloRazon` separa la columna `media_24h` del resto
y la usa para multiplicar la predicción (`modelos.py`, `_separar`); el estimador no la ve. Pero
`permutation_importance` recibe todas las columnas (notebook 02, celda 33: `cols = columnas_variante(d, "M3")`,
que incluye la escala), así que al permutar `media_24h` se rompe la reconstrucción a MW y el MAE se dispara: 207.3
MW en el Centro, 46.6 en el Norte y 65.8 en el Sur (`importancias.csv`), por encima de `Area_t` (119.5, 23.0 y
22.7). El grupo "M0 (demanda y calendario)" de `importancias_por_grupo.csv` (455.3 MW en el Centro) incluye ese
artefacto. En Tetuán pasa lo mismo (`media_24h` = 1,541 kW en la Zona 1, notebook 02 de Tetuán, celda 33). El
notebook de Tetuán lo advierte ("`media_24h` es la escala que lleva la razón a kW"); el del SEIN no. **Propuesta:**
en el paper, quitar la fila `media_24h` de la tabla y de la figura de importancias, decirlo en una nota, y no
sumar el grupo M0 (la cifra incluye la escala). Las variables que sí importan quedan claras sin ella: `Area_t`,
`Area_media_1h`, el calendario diario (`MinuteOfDay`, `Time_Cos`, `Obj_Cos`) y `Area_semana_pasada`; el clima suma
1.10 MW en el Centro y 0.18-0.23 en las otras áreas.

**Estado (12-nov): resuelto en el PR #30** (`fix/importancia-sin-escala`, commit `c687feb`, todavía sin fusionar a
`develop`). Los notebooks 02 del SEIN y de Tetuán hacen `importancias.drop(index="media_24h")` después de calcular
(los valores de las demás variables no cambian) y la app lo replica en `GRUPOS_IMPORTANCIA`. Con la fila fuera, el
grupo "demanda y calendario" queda en 49.46 / 247.97 / 43.37 MW (Norte / Centro / Sur) en vez de 96.11 / 455.29 /
109.19; clima (0.18 / 1.10 / 0.23), El Niño (0.02 / 0.04 / 0.02) y fallas (0.00 / −0.01 / 0.00) no cambian, y la
conclusión 5 del notebook ahora dice "1.1 MW frente a 248 MW". En Tetuán, `Zona_t` pasa a primera (4,100.8 /
2,920.4 / 1,827.9 kW), seguida de `Zona_lag_24h` y `Zona_lag_1w`. Verificado en las salidas de la celda 33 de los
dos notebooks en esa rama. Las tablas nuevas están en el Drive (`reportes/sein/modelado/importancias.csv` e
`importancias_por_grupo.csv`; las anteriores, en `respaldo/`).

**Lectura de la ablación con esta corrección.** A 1 h: en 2025, M1 − M0 en el Centro −0.25 MW (IC −0.47 a −0.01)
y nada en el Norte ni el Sur; en 2026, −0.46 (IC −0.71 a −0.20) en el Centro y nada en las otras. A 24 h: en 2025
el clima mejora el Centro −0.61 MW (IC −1.15 a −0.07); en 2026 lo empeora +1.35 (IC 0.10 a 2.97) y al Norte +0.42
(IC 0.16 a 0.68). El Niño nunca mejora y en 2026 empeora el Sur a 24 h (+0.83, IC 0.46 a 1.23). Todo esto es de
`ablacion.csv` de las dos corridas. Son efectos de menos del 2 % del error (D4).

### 8. El supuesto de colaboración COES-ENFEN

**Cómo está implementado** (`variables_sein.py`):

- A 1 h, `temp` es la temperatura horaria de ERA5 (Open-Meteo) de la última hora publicada, media simple de las
  ciudades del área (Norte: Piura, Chiclayo y Trujillo; Centro: Lima; Sur: Arequipa y Tacna). `temp_objetivo`
  a 1 h es la misma `temp`.
- A 24 h, `temp_objetivo` es la temperatura **observada** de t+H, interpolada entre horas, más un error
  gaussiano con σ = 1.5 °C sorteado **una vez por día de emisión y por área**, con la misma semilla en
  entrenamiento, validación y prueba (`ERROR_PRONOSTICO_TEMP_C = 1.5`, `error_pronostico_diario`).

**D1 (a declarar).**

1. ERA5 es un reanálisis: una grilla de 0.25°, suavizada, que se publica con unos cinco días de rezago. No es la
   estación de SENAMHI que el operador tendría en tiempo real. El paper debe decir "la temperatura observada se
   aproxima con ERA5" y no "con datos de SENAMHI".
2. El pronóstico simulado a 24 h es **optimista**: parte del valor que efectivamente ocurrió, con un error sin
   sesgo e independiente entre días. Un pronóstico real tiene sesgos y errores correlacionados, y durante un
   evento extraordinario suele ser peor. Eso tiene una lectura favorable al proyecto que conviene decir
   explícitamente: si **aun con un pronóstico optimista** el clima empeora el pronóstico de demanda a 24 h en
   2026, con un pronóstico real difícilmente ayudaría.
3. La spec (§6 y §13.2) decía que se probarían dos niveles de error, σ = 1 y 2 °C. Se implementó uno solo, 1.5 °C,
   y no hay análisis de sensibilidad al nivel. Declararlo.
4. El error se sortea por día de emisión, pero el pronóstico de cada periodo se "emite" en t (cada 30 minutos):
   el supuesto es que el COES recibe un pronóstico diario y lo usa para todos los orígenes del día. Es razonable;
   hay que decirlo.
5. **M8.** `error_pronostico_diario` numera los días únicos del dataset y sortea con semilla 0: si la app o un
   experimento arma el dataset con otro rango de fechas, la realización del ruido de un día cambia. No afecta a
   los notebooks (mismo rango en 02 y 03), pero la app no ve exactamente el mismo `temp_objetivo` que el
   notebook 03.

### 9. CPU/GPU y reproducibilidad

**Lo que consta.** Antes de la corrida se midieron cinco implementaciones con el dataset real del Centro a 1 h
(tabla en el notebook 02, texto de la celda 8): el Random Forest de cuML en GPU ajusta en 3.4 s pero **no es
reproducible** (hasta 29 MW de diferencia entre dos ajustes con la misma semilla) y al pasarlo a scikit-learn su
MAE sube de 54.70 a 55.56 MW; el Random Forest vía XGBoost (`num_parallel_tree`) es reproducible pero tarda de
74 a 119 s. Se quedó el de scikit-learn en CPU (17.6 s, determinista con `random_state`). XGBoost entrena en GPU
(`device="cuda"`, `tree_method="hist"`), es determinista y pasa a CPU al guardarse (`portable`,
`test_portable_deja_xgboost_en_la_cpu_sin_tocar_el_original`). Esto es correcto y conviene contarlo en una
línea del paper como decisión de reproducibilidad.

**D11 (a declarar).** Dos matices: (1) "determinista" vale dentro del mismo hardware; un modelo XGBoost entrenado
en GPU y evaluado en CPU puede diferir en los últimos decimales (el README dice que la app reproduce el error del
notebook 03 a 1 h; no lo verifiqué); (2) hay **una sola semilla** (0) para Random Forest, XGBoost, el bootstrap
y el ruido del pronóstico (M5). Con 2,000 réplicas el bootstrap no depende de la semilla, pero la variabilidad
entre semillas del Random Forest no se midió.

### 10. La corrida de 2026 retomada con caché

**Lo que consta.** La corrida se cayó tres veces (la laptop que la mantenía viva se suspendió). El commit
`e556404` (6-nov, 14:56) agregó `con_cache`: cada bloque (política, horizonte y variante) se guarda como `.npz`
apenas termina y se lee si existe (notebook 03, celda 5). El diff de ese commit solo envuelve las llamadas
existentes en `con_cache` y no toca ningún cálculo. La corrida final (commit `49a263b`, 18:42) arrancó con "19
bloques ya calculados" (salida de la celda 5) y calculó en esa sesión los bloques de 24 h de reentrenamiento
semanal (17.0 min), alerta (20.6) y semanal + alerta (52.3); los demás dicen "0.0 min" porque salieron de la caché
(M6). Con capas sintéticas, la segunda corrida dio tablas idénticas (mensaje del commit).

**D7 (a declarar).**

- Las conclusiones del notebook 03 dicen "sin cambiar código ni elecciones". Lo preciso es "sin cambiar los
  cálculos ni las elecciones": el código sí cambió (se agregó la caché) a mitad de la corrida.
- La clave de la caché es solo el nombre del bloque; no incluye un hash del gold, del silver ni del código. Si las
  capas del Drive hubieran cambiado entre una sesión y otra (por ejemplo, por una recarga del IEOD), los bloques
  mezclarían datos. No hay evidencia de que haya pasado (los conteos de filas coinciden entre sesiones y el
  notebook 03 cargó 13,920 filas de prueba en la sesión final), pero tampoco hay una comprobación que lo descarte.
- El determinismo que justifica mezclar bloques de distintas sesiones es el de `random_state=0` en Random Forest
  (con `n_jobs=-1`, scikit-learn sigue siendo determinista) y de XGBoost en `hist`. Es cierto, pero se afirma, no
  se demuestra en la corrida real.

**Propuesta.** Una frase en la fase de evaluación del paper: "la corrida de 2026 se interrumpió tres veces y se
retomó desde una caché de predicciones por bloque; los cálculos son deterministas con semilla fija y no se cambió
ninguna elección". Si hubiera tiempo (no es prioridad): agregar al nombre de cada bloque el sha256 del gold y
volver a correr dos bloques al azar para confirmar que coinciden con la caché.

### 11. Hipótesis "escritas antes de ver la prueba"

**Lo que consta.** Las seis hipótesis están en la §12 del notebook 02 (celda 34, commit `8c4e084`, 5-nov 00:47),
el notebook 03 se escribió después (`8fa27ee`, 5-nov 21:02) y evalúa esas hipótesis con reglas cerradas en código
(celda 22: por ejemplo, "1b" es `25 < mejora_norte < 49`). La corrida de 2026 es del 6-nov (`49a263b`, 18:42).
Resultado (`hipotesis.csv`): 1a sí, 1b no (la mejora del Norte subió a 51.7 % en vez de bajar), 1c sí, 2 sí,
3 no (el clima sí ayuda algo a 1 h en el Centro), 4 no (el clima empeora a 24 h en el Centro), 5 sí.

**D3 (a declarar).** Las hipótesis citan "el Norte, donde la demanda crece entre 10 y 17 % sobre el año anterior"
(esa cifra viene de la spec de octubre; el EDA del notebook 01, celda de hallazgos, midió después entre 4 y 17 %
según el mes, que es la que usa el paper):
el nivel de 2026 ya se conocía por la investigación (spec §1, README) y por el EDA del notebook 01 del SEIN, que
mira la serie completa hasta octubre de 2026 (celdas 8 y 16). Lo que no se había visto era **cómo se comportaba el
modelo** en 2026. El paper debe decir exactamente eso: "las hipótesis se escribieron después de explorar los datos
de 2026 y antes de evaluar ningún modelo en ellos". También conviene decir que dos de las tres hipótesis que
fallaron, fallaron en la dirección favorable al modelo (1b) o en contra de las exógenas (4), y presentarlo como
resultado, no como excusa.

### 12. Tetuán, Ceuta y el Entregable 7

**Tetuán (D13).**

- **Lo que se sostiene.** Partición cronológica 70/15/15 con hueco de 6 pasos (notebook 02 de Tetuán, celda 5:
  35,714 / 7,835 / 7,841 filas), búsqueda con `TimeSeriesSplit(5, gap=6)` solo en el entrenamiento (celda 11),
  elección en la validación por la mejora media (celda 17: Gradient Boosting global 49.0 %, Ridge y Gradient
  Boosting por zona 48.2 %, Random Forest 46.9 %), origen móvil de marzo a octubre (24 de 24 meses-zona, celda 21),
  prueba una vez con intervalo por bootstrap (celda 24: Zona 1 −375.6 kW, IC −474.2 a −285.8; Zona 2 −544.1,
  IC −727.2 a −394.1; Zona 3 −294.0, IC −441.6 a −168.9). En la prueba el modelo queda 44.8, 55.9 y 40.7 % por
  debajo de la mejor referencia (`reportes/modelado/prueba.csv`).
- **A declarar.** (1) La unidad (kW) y la identidad de las zonas no tienen fuente primaria (`docs/datos.md`,
  `docs/estado-del-arte.md` §4). (2) La temperatura del dataset no coincide con ninguna fuente externa
  (correlación 0.83 con ERA5; `docs/historico.md` §7). (3) En el Ramadán, en la Zona 3, el modelo **pierde** contra
  la mejor referencia (631 frente a 588 kW, −7.4 %; notebook 02, celda 27). (4) Tras la transferencia del 25 de
  octubre, la ventaja en la Zona 1 baja de 51.2 a 39.2 % (celda 29). (5) Ridge empata casi con los árboles en la
  validación (48.2 frente a 49.0 %): el mérito está en las variables en razón, no en el algoritmo. (6) La
  comparación con el estado del arte (Tabla 1 de `docs/paper/estructura.md`) es contra la persistencia, porque es
  lo único que los demás trabajos reportan; contra la mejor referencia la mejora es menor (41-56 %, no 73-75 %:
  44.8, 55.9 y 40.7 % en `prueba.csv`).
  Las dos cifras tienen que ir juntas. (7) La fila "Total (suma de las zonas), MAPE 1.42 frente a 6.48 %" de esa
  tabla sale de los archivos de predicciones del Drive y no la pude verificar en local: marcarla como "por
  verificar" hasta recalcularla.
- **M7.** Las conclusiones del notebook 02 de Tetuán siguen vacías. No es un problema metodológico, pero sí de
  entrega (criterio IV de la rúbrica).

**Ceuta (D12).** La validación externa (`docs/historico.md` §8) usa `HistGradientBoostingRegressor` con 300
iteraciones y tasa 0.05, **sin ajuste de hiperparámetros, con una sola semilla y sin intervalos**, sobre un
sistema distinto (sin veraneo como el de la Zona 3, con feriados españoles). Sus cifras (razón sin verano 2.31 %
de MAPE frente a 4.62 % de la mejor ingenua y 2.87 % del modelo en nivel) sostienen la **dirección** del
resultado, no su tamaño. El paper debe presentarla como evidencia de apoyo. El CSV `resultados_validacion.csv`
está en el Drive, no en local.

**Entregable 7 (D15).** La versión entregada al curso (4 de noviembre) evaluaba en nivel y contra la
persistencia: los dos modelos le ganaban a la persistencia pero perdían contra "ayer" (Random Forest 1,795 kW y
XGBoost 1,958 frente a 1,007 kW de "ayer"). La versión corregida (`entregables/Entregable6_MDS_Grupo03.ipynb`,
celda 93) pasa al objetivo en razón, agrega las tres referencias, el hueco y el MAPE, y los dos modelos quedan
cerca de la mitad del error de "ayer" (XGBoost 526 kW, Random Forest 544). Es el mejor ejemplo de CRISP-DM como
ciclo que tiene el grupo y va en "lecciones aprendidas", con la fecha y lo que cambió. Riesgo a manejar en la
defensa: la profesora tiene la versión sin corregir.

### 13. La app

**Lo que consta.** Ejecuta el XGBoost global entrenado con 2016-2025 sobre las capas del SEIN
(`app/backend/pronosticador_real.py`): pronóstico a 1 h y 24 h, escenarios, sensibilidad y diagnóstico sobre la
prueba de 2026. La adaptación (fijo frente a semanal) no se reentrena en vivo: muestra la tabla del notebook 03.
**M4:** los intervalos del 90 % usan los errores fuera de muestra de 2025 del Random Forest (notebook 02) sobre
predicciones del XGBoost. Declarar en la fase de implementación: "la app corre el XGBoost global, empatado con el
elegido; sus intervalos son empíricos, de los errores de 2025".

### 14. Otros menores

- **D14.** Los notebooks del SEIN usan `holidays.PE` (feriados nacionales; 160 fechas, notebook 01, celda 3) y no
  la tabla curada `feriados_pe_2015_2026` (258 filas con regionales y no laborables) descrita en
  `docs/peru/tablas.md`. M4 (SAIDI por área) no se corrió (spec §12, primero en el orden de recorte). La alerta de
  ENFEN se arma con los cruces de categoría del ICEN publicado, no con los comunicados en PDF (spec §8.4, opción
  declarada). El paper debe describir lo que se usó, no lo que la spec planeó.
- **M9.** `Cuarentena` es un indicador de la fase estricta (16-mar a 1-jul-2020), no las cinco fases de
  `cuarentena_pe_2020`.

### 15. Extensión del 13-nov: modelos fundacionales (D16)

**Lo que consta.** Rama `feature/modelos-fundacionales` (worktree `tpf-fm`, aún sin commit ni PR): `fm_bench.py`
(ocho modelos de Hugging Face en zero-shot, contexto de 2,048 periodos, orígenes de 2025-01-01 a 2026-10-23, pasos 2
y 48, mediana como punto, 336 huecos del silver interpolados), `chronos2_variantes.py` (covariables con la regla de
información del proyecto: temperatura conocida, pronóstico simulado con error de 1.5 °C por día y feriados),
`ajuste_fino.py` (Chronos-2 ajustado solo con datos hasta 2024-12-31) y `apilar.py` (híbrido: XGBoost global en
razón con `pred`, `ancho` y `otro` del fundacional divididos por `media_24h`, entrenado con orígenes de 2016-03 a
2024, validado en 2025; el "XGBoost base" se entrena sobre las mismas filas). Salidas en
`data/reportes/sein/fundacionales/`. El notebook 04 está en preparación.

**Verificado en local** (sobre las filas de `prueba_2026/predicciones_*.csv` y el silver de la demanda): los MAE de
2026 de todos los modelos coinciden fila a fila con los de la tabla del paper; los de 2025 a 1 h también; los de los
híbridos a 24 h coinciden con `resumen_chronos2_simons.json`. Los intervalos de 2026 del híbrido con Simons frente
al Random Forest se reproducen con `bootstrap_diferencia_mae`. **No verificado:** los intervalos de 2025 (las
predicciones de validación del Random Forest están en el Drive), el costo en GPU y las licencias.

**A declarar (D16).** (1) Es una extensión posterior a la prueba: 2026 ya se había usado en el notebook 03, así que
sus cifras confirman, no prueban; el paper lo dice en §4.4, §5.5 y §6.4. (2) No se puede descartar que series
parecidas estén en el preentrenamiento (el corpus de Chronos-2 no es público completo; ver `docs/historico.md`,
§6). (3) Las licencias difieren por modelo (Simons OpenMDW-1.1, Chronos-2 Apache-2.0, TimesFM 3.0 no comercial,
según las fichas; por confirmar). (4) El "XGBoost global base" de la comparación (53.6 / 19.6 / 24.7 MW en 2025 a
1 h) no es el XGBoost del notebook 03 (53.5 / 19.6 / 24.7 en 2025; distinta ventana para 2026): comparar dentro de
la tabla. (5) En el Sur a 24 h en 2026, la ventaja del zero-shot no se distingue de cero (−1.44 MW, IC −3.24 a
0.30) y el híbrido empeora (+1.54, IC 0.29 a 2.80). (6) La variante `chronos2ftcal` (ajuste fino hasta 2024 con
tasa 1e-6 y el feriado como covariable futura) resultó la mejor de cuatro variantes elegidas con 2025 y entró al
paper como "Chronos-2 ajustado con calendario" (2026: 19.2 / 50.3 / 21.1 y 28.2 / 72.5 / 44.6 MW, verificados fila
a fila; Δ frente al Random Forest en el Norte a 24 h −0.77, IC −1.65 a 0.12, reproducido; cobertura 10-90 de 74 a
77 %, reproducida). (7) **La combinación final** (Chronos-2 ajustado con calendario + híbrido XGBoost + Simons,
con pesos por horizonte y área fijados en 2025: 0.35 / 0.45 / 0.65 a 1 h y 0.70 / 0.85 / 0.95 a 24 h) se reprodujo
en 2026 fila a fila (18.8 / 48.8 / 20.9 y 27.9 / 71.9 / 44.6) y en 2025 a 1 h; **sus cifras de 2025 son dentro de
muestra** (los pesos se eligieron ahí) y sus intervalos no existen todavía (los calculará el notebook 04): el paper
lo dice en §5.5, §6.4 y §7, y la guía de defensa prohíbe dar un intervalo. (8) Faltan las corridas con contexto de
8,192.

## Lo que se verificó y se sostiene (para la defensa)

1. Ninguna variable usa información posterior a t: rezagos hacia atrás, temperatura de la última hora publicada,
   ICEN, Niño 1+2 y SAIDI con su rezago de publicación, calendario del periodo objetivo (conocido). Tests:
   `test_variables_sein.py`, `test_exogenas.py`.
2. Partición cronológica con hueco de H pasos antes de cada corte; la prueba se aparta en la primera celda del
   notebook 02 y se comprueba con `assert`.
3. Búsqueda de hiperparámetros con validación cruzada temporal (5 pliegues, hueco de H) solo en el entrenamiento;
   validación de 2025 para elegir; prueba de 2026 una sola vez, con el modelo y los hiperparámetros verificados
   contra lo guardado por el notebook 02.
4. Referencia exigente: la mejor de tres referencias ingenuas, elegida en el propio tramo.
5. Intervalos por bootstrap pareado de días (2,000 réplicas) para toda diferencia que se reporta.
6. Reentrenamiento por bloques con ventana creciente y hueco antes de cada bloque; hiperparámetros congelados.
7. Hipótesis escritas y commiteadas (5-nov) antes de la corrida de 2026 (6-nov), evaluadas con reglas en código.
8. Reproducibilidad: semilla fija, Random Forest en CPU por ser el único reproducible, XGBoost determinista,
   procedencia (sha256) de las capas, caché por bloque.
9. En Tetuán, el mismo protocolo con 70/15/15, origen móvil y prueba única.

## Qué llevar a la sección de limitaciones del paper

Una lista corta, en el orden en que conviene decirlas:

1. Un solo año y un solo evento en la prueba (D5); intervalos "dentro de 2026".
2. Efectos de exógenas y reentrenamiento de alrededor del 1 % del error, con 66 intervalos sin corrección (D4).
3. El supuesto COES-ENFEN: ERA5 como observado; pronóstico a 24 h simulado y optimista, con un solo nivel de error
   (D1).
4. `fallas_en_curso` no evaluable; M2 como variante con exógenas (G2).
5. Empate entre Random Forest y XGBoost; búsqueda solo en el Centro a 1 h; la app corre el XGBoost (D2).
6. Las hipótesis se escribieron tras explorar los datos de 2026 y antes de evaluar modelos en ellos (D3).
7. La prueba va del 1 de enero al 17 de octubre de 2026 a 1 h y al 16 de octubre a 24 h (D8); el IEOD sustituye
   al SCADA (D9).
8. Sin comparación con la Programación Diaria del COES (G3).
9. En Tetuán, unidad e identidad de zonas sin fuente primaria; Ramadán en la Zona 3; transferencia (D13).
10. Ceuta como evidencia de apoyo, sin ajuste ni intervalos (D12).
11. La corrida de 2026 se retomó desde caché (D7).

## Qué haría falta rehacer, si hubiera tiempo (en orden)

Ninguno es necesario para el paper; están ordenados por lo que aportarían.

1. **Importancias sin la escala** (G1): **hecho** en el PR #30 (la fila se quita después de calcular; los demás
   valores no cambian). Falta fusionarlo a `develop`.
2. **Sensibilidad al error del pronóstico de temperatura** (D1): M1 a 24 h en 2026 con σ = 1 y 2 °C, con el modelo
   fijo (dos bloques, unos 10 minutos cada uno en Colab). Diría si el daño del clima a 24 h depende del supuesto.
3. **Una definición útil de falla** (G2): solo eventos con interrupción de carga o con MW indisponibles, por área
   con `empresa_area`. Es la única que exigiría rehacer M3 en 2025 y 2026 (unas 3 horas).
4. **Hash del gold en la clave de la caché** y recálculo de dos bloques (D7).
5. **Comparación con la Programación Diaria** (G3): bajar el portal del COES y evaluar "día siguiente". Es lo que la
   spec dejó como opcional y lo que más pediría un lector del COES.
