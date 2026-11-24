# Revisión de literatura, hechos del dataset y baseline peruano (COES) para el proyecto `tetouan-power-forecast`

**Destinatarios:** equipo del proyecto CRISP-DM (UPC) y profesor del curso.
**Alcance:** este informe reúne la evidencia necesaria antes de diseñar los experimentos de modelado (LightGBM, modelos fundacionales, AutoGluon). Todavía no se diseñan los experimentos.
**Convención numérica:** punto decimal y coma para separar miles (p. ej., 52,416 filas; 1.76 %). Salvo que se indique otra cosa, las unidades de consumo de Tetouan son kW (ver la sección 4.1 sobre la incertidumbre de unidades).
**Nota de uso:** el informe resume trabajos publicados de terceros (propiedad intelectual ajena), datos públicos de UCI, COES y REE, y cálculos propios.

---

## 1. Resumen

- **La afirmación "la mayoría de trabajos reporta R² ≈ 98 % regresando el consumo del mismo instante a partir del clima" no se sostiene tal cual.** Revisamos 43 trabajos que, según la evidencia, usan UCI 849 (41 de predicción o regresión y 2 de otro tipo; en el n.º 6 el uso del archivo de UCI es dudoso), más 2 con uso no confirmado que dejamos fuera de la tabla. **No es un censo:** identificamos al menos otros 7 trabajos que usan Tetouan y que no revisamos (sección 2.2). De los 41, **9 se clasifican como regresión del mismo instante**: 6 con texto completo leído (n.º 2, 3, 4, 5, 7, 8); el n.º 1 solo de segunda mano; y los n.º 6 y 9 por inferencia (en el n.º 6 la sección de Tetouan no describe ningún protocolo; en el n.º 9 la tarea está subespecificada). De esos 9, solo **3 reportan un R² auténtico ≥ 0.97** (Abdillahi & Etem 0.9812; Eghaghe 98.06 %; Rose et al. 0.976). Otros 2 reportan cifras cercanas al 98 % que no son R²: una r de Pearson etiquetada como R² y una "accuracy" de matriz de confusión.
- **Los R² de 0.976 a ≈ 0.998 aparecen con igual o mayor frecuencia en pronósticos a un paso (10 min o 1 h) con rezagos del consumo:** hay 7 trabajos así, más uno (n.º 15) cuyo R² usa una fórmula no estándar. El 0.9996 de JAIT (n.º 34) pertenece a la categoría de tarea no determinable y se calcula sobre una suma de zonas suavizada. En la configuración a un paso, la persistencia ya logra R² altos: el extractor calculó una persistencia a t+1 de R² 0.992 para la Zona 1 en la partición de Singh & Tewari (cálculo no reverificado).
- **Un R² ≈ 0.98 se consigue con una línea base trivial incluso a 60 minutos.** En nuestra partición, la "persistencia + delta diario" da **R² 0.981 a t+6** en test. Un R² alto, por sí solo, no indica capacidad predictiva.
- **Solo 4 de los 41 trabajos reportan una línea base ingenua (persistencia).** En los trabajos de mismo instante, la partición aleatoria explica buena parte del R². En nuestras pruebas, un RandomForest **solo con calendario** da R² 0.994 con partición aleatoria y 0.126 con partición cronológica. KNN con clima y calendario da 0.984 frente a 0.41.
- **Las otras zonas del mismo instante producen el mismo efecto que el calendario.** En la reproducción del extractor de Abdillahi & Etem, KNN con clima y las Zonas 2 y 3 del mismo instante da R² 0.9839 con partición aleatoria y 0.396 con partición cronológica. En AVITEC (n.º 8) la Tabla 2 normaliza las tres zonas juntas y no nombra el objetivo; en JUTIF (n.º 7) la línea base sin selección de variables podría incluir las zonas.
- **No encontramos ningún trabajo que evalúe la Zona 1 a resolución de 10 min con horizonte t+6.** El más cercano es Bunke & Hrudzynskyi (2026): Zona 1, medias horarias, 1 h adelante, partición cronológica 70/15/15. Allí la persistencia da MAPE 6.03 % y Ridge 2.33 %; un naive estacional de 24 h calculado por el extractor (RMSE 1,448, R² 0.942) supera a sus LSTM, GRU y LSTM-Attention.
- **Existe un baseline ingenuo mucho más fuerte que la persistencia y debe entrar en el paper.** Para la Zona 1 a t+6, la "persistencia + delta diario", ŷ = y(t) + [y(t−138) − y(t−144)], da **MAE 567 kW (MAPE 1.99 %, R² 0.981) en test** y **MAE 671 en el año completo**. La persistencia da 1,821 en test. No está claro que el primer modelo del equipo (MAE CV 997 ± 353) le gane; hay que compararlos en los mismos folds y con una prueba de significancia.
- **El dataset tiene peculiaridades que afectan la validación y el test:** un traspaso de carga de la Zona 1 a la Zona 2 el 24 y 25 de octubre de 2017 (todo el test queda después; la validación lo atraviesa); un salto de la Zona 3 entre el 8 y el 18 de noviembre; un reescalado entero por mes sin documentar; viento bimodal poco plausible; falta el 31 de diciembre; y Ramadán cambia el perfil nocturno. El test cubre solo noviembre y diciembre e incluye tres feriados marroquíes (6 y 18 de noviembre, 1 de diciembre).
- **Baseline peruano real (COES, SEIN, 30 min), calculado con datos públicos:** el pronóstico del día previo (PDO) tiene un MAPE de **1.50 % en 2025** y de 1.76 % en 2017. La persistencia a 1 h da 2.34 % (2025) y 2.75 % (2017). La referencia "persistencia + ΔPDO" da **1.03 %**, pero usa un producto del operador que Tetouan no tiene. No hallamos un MAPE oficial publicado por el COES.
- **Las cifras peruanas y las de Tetouan no se comparan en MAPE bruto.** El SEIN tiene unos 7,000 MW de media y la Zona 1, unos 32 MW. Lo comparable es el skill frente a la persistencia en el mismo horizonte, definido con MAE (sección 5.4).

---

## 2. Literatura sobre UCI 849

### 2.1 Método de verificación

Para cada trabajo, un agente extrajo la información y luego dos verificadores independientes intentaron refutar tres elementos: el tipo de tarea, la partición y las entradas. En la columna "Verificación":
- **"2/2 no refutan"**: ningún verificador pudo refutar la clasificación.
- **"disputado (k/2)"**: k verificadores la refutaron.
- **"sin verificación adversarial"**: no hubo verificadores.
- **"Texto: no"**: no se accedió al texto completo; se trabajó con el resumen, los metadatos, las figuras o las citas de otros trabajos.

Abreviaturas: "?" = no declarado o poco claro; MI = mismo instante; t+1 = un paso adelante en la resolución indicada. La columna **"Escala / unidad"** indica en qué escala están las métricas reportadas: muchas no están en kW y no se pueden comparar directamente.

### 2.2 Tabla (43 trabajos revisados; no es un censo)

**A. Regresión del mismo instante (9).** Clasificación: 6 con texto leído (n.º 2, 3, 4, 5, 7, 8); n.º 1 de segunda mano; n.º 6 y 9 inferidos.

| # | Autor (año), tipo | Tarea / horizonte | Consumo pasado | Clima contemp. | Otras zonas | Partición | Métricas Zona 1 (u objetivo reportado) | Escala / unidad | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Salam & El Hibaoui (2018), conf. IRSEC (origen del dataset) | MI, 10 min y horario | No | Sí | ? | Aleatoria 75/25 (solo de segunda mano, vía FELDL) | RF RMSE 3,174.7 (de segunda mano, con atribución en conflicto con 2,336.9). Cifras horarias también en conflicto (≈ 21,109.7 frente a 14,700.9). Sin MAE, MAPE ni R²; el "R² ≈ 98 %" que otros trabajos le atribuyen **no aparece en este paper** | kW presumible; horario probablemente suma de 6 lecturas | Texto: no; 2/2 no refutan |
| 2 | Abdillahi & Etem (2025), revista AJEAS | MI, 10 min | No | Sí | ? | 80/20; aleatoria **inferida** por reproducción. Estandariza y recorta outliers al 1–99 % **antes** de la partición | Stacking MAE 632.0, RMSE 774.58 (error de copia; el texto dice ≈ 937), R² 0.9812; KNN R² 0.9784. Sus estadísticas descriptivas no corresponden al CSV (p. ej., Zona 1 de 200 a 18,500 kW) | kW (las RMSE encajan con la escala real) | Texto: sí; 2/2 |
| 3 | Eghaghe (2024), tesis MSc NCI | MI, 10 min | No | Sí | No | StratifiedShuffleSplit 20 % (aleatoria explícita) | XGBoost MAE 706.0, RMSE 993.3, R² 98.06 % | kW | Texto: sí; 2/2 |
| 4 | arXiv 2609.34120 (2026), preprint probabilístico | MI, horario | No | Sí | No | El texto dice "cronológica"; la Fig. 4 sugiere filas barajadas → poco clara | NGBoost MAE 1,682.57, RMSE 2,241.14, CRPS 1,178.65, PICP 0.95 | kW (media horaria probable) | Texto: sí; 2/2 |
| 5 | Rose et al. (2023), Atlantis ICACECS | MI; objetivo = suma de 3 zonas | No | Sí | No | 70/30, orden no declarado | Sin Zona 1. Fine Tree en test: R² 0.976, RMSE 2.68e3 | Suma de zonas, unidad no declarada | Texto: sí; 2/2 |
| 6 | Satan et al. (2025), Energy Informatics | MI inferido (temperatura → carga + perfil típico); la sección de Tetouan no describe protocolo | No (solo vía perfiles) | Sí | ? | No declarada para Tetouan | Mediana RMSE ≈ 5,168 (zona y unidad no especificadas). No reporta R² para Tetouan; su Ec. 4 de R² tiene las predicciones en el denominador (no estándar). **Nunca cita UCI**; pudo usar la variante de Salam & El Hibaoui 2021 | "MWh" declarado, inconsistente con el dataset | Texto: sí; 2/2 |
| 7 | JUTIF 6(3) (2025), ALO/Jaya + KNN | MI, 10 min | No | Sí | No (aparente); la línea base KNN sin selección podría incluir las zonas | 90/10, orden no declarado; escalado sobre todo el dataset | JA+KNN RMSE 856.17, MAPE 1.80 %, "R²" 0.9853 (la Ec. 4 es una r de Pearson) | kW | Texto: sí; 2/2 |
| 8 | Wahyusari, Sunardi & Fadlil (2025), AVITEC | MI, 10 min; objetivo sin nombrar | No | Sí | ? (la Tabla 2 normaliza las tres zonas junto con el clima) | 90/10, 80/20 y 50/50; probablemente aleatoria (random_state=42); normaliza antes de partir | Zona no declarada: KNN RMSE 1,314.1, MAPE 4.58 % | kW; MAPE como fracción | Texto: sí; 2/2 |
| 9 | Zhao, Hu, Yan et al. (2024), Cluster Computing (BOKNN; se leyó el preprint) | MI inferido; el verificador la considera "estrictamente subespecificada; MI es la lectura mejor apoyada" | No | Sí | ? | 75/25 u 80/20, orden no declarado | Zona no declarada: MAE 531, RMSE 1,282, "accuracy" 98.13 % (no es R²). Filas imposibles: MAE > RMSE en ANN | No declarada (presumiblemente kW) | Texto: sí; 2/2 |

**B. Pronóstico a un paso con rezagos (13)**

| # | Autor (año), tipo | Tarea / horizonte | Consumo pasado | Clima contemp. | Otras zonas | Partición | Métricas Zona 1 (u objetivo reportado) | Escala / unidad | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 10 | Sci. Rep. 15:6447 (2025), clustering difuso + ML | t+1 (10 min), 3 rezagos | Sí | Sí | ? | Cronológica 70/30 (inferida de la Fig. 7) | Sin Zona 1. Zona 3: MLP+FCM RMSE 355.42, R² 0.9889. Al nivel de la persistencia de Z3 a t+1 en la partición de Singh & Tewari (R² 0.9895; cálculo del extractor, particiones distintas) | kW | Texto: sí; 2/2 |
| 11 | Singh & Tewari (2026), Cureus J. Comput. Sci. | t+1 (10 min) | Sí | Sí (solo el meta-learner) | No | Cronológica 80/20 | RMSE 1,433.77, MAPE 3.69 %, R² 0.9457 (Zona 1 **sin Chronos**: la "generalización" a Z1 y Z3 no lo usa). Persistencia t+1 en las mismas filas (cálculo del extractor, no reverificado): RMSE 549.94, MAPE 1.27 %, R² 0.992 → el pipeline de Z1 es ≈ 2.6 veces peor; en Z3 también (678.06 frente a 339.19). En Z2, Chronos solo pierde contra la persistencia (477.89 frente a 461.44). Persistencia a **t+6** en la misma partición, Z1: R² 0.826 | "kWh" (son kW) | Texto + código; 2/2 |
| 12 | Eng. Proc. 144:4 (2026), LSTM-XGBoost (citado como "Sadik et al.") | Un paso (inferido) + corrector de residuo con clima del instante objetivo | Sí | Sí | ? | Cronológica 80/20 | Híbrido RMSE 651.51, MAPE 1.678 %, R² 0.9889 | "kWh" (son kW) | Texto: sí; 2/2 |
| 13 | Bunke & Hrudzynskyi (2026), Visnyk SNU | Media de la hora siguiente (1 paso horario ≈ ventana t+1..t+6) | Sí | No | No | Cronológica 70/15/15 | Persistencia MAE 1,748.22 / MAPE 6.027 % / R² 0.8525; Ridge 667.09 / 2.328 % / 0.9776; HGB 650.76 / 2.218 %. Naive estacional 24 h (cálculo del extractor, no en el paper): RMSE 1,448, MAPE 3.31 %, R² 0.942, **mejor que LSTM (1,776), GRU (1,603) y LSTM-Attention (1,480)** | "W" en el texto; escala del dataset | Texto: sí; 2/2 |
| 14 | Kshetrimayum, Singh & Hoque (2024), IJDSA (se leyó el preprint) | 1 h adelante; objetivo = suma de 3 zonas | Sí | No | No | CV expansiva, 4 folds | Sin Zona 1. Total: persistencia MAPE 6.60 %, R² 0.837; P-ConvLSTM MAPE 2.49 %, R² 0.976 | kW, media horaria de la suma | Texto + código; 2/2 |
| 15 | Chang & Ke (2024), IEEE Access | Probablemente t+1 horario (inferido; los autores lo llaman "day-ahead"); objetivos = sumas de zonas | Sí (univariado) | No | No | No declarada | Sin Zona 1 sola. Z1+Z2: RMSE 8,346, MAPE 1.87 %, "R²" 0.985. **R² con fórmula no estándar:** su Ec. (15) define SS_Res como la dispersión de las predicciones, no de los residuos | Sumas horarias de 6 lecturas de 10 min (≈ ×6), etiquetadas "kW" | Texto: sí; 2/2 |
| 16 | da Silva & Meneses (2023), Energy Reports (se leyó la versión arXiv) | t+1 (10 min, inferido), univariado, ventana de 90 | Sí | No | No | CV temporal + holdout de diciembre | Sin Zona 1 (serie ≈ suma de zonas, inferido). BLSTM RMSE 646.2, MAPE 0.8 %, R² 99.8 %. Persistencia t+1 en diciembre (cálculo del extractor): MAPE 1.21 % | kW (suma) | Texto: sí; 2/2 |
| 17 | BAJEST 4(2) (2025), DL, un autor | t+1 (10 min), entrada univariada (inferida de los parámetros) | Sí | Probablemente no | ? | Cronológica, ratio no declarado | Sin Zona 1; híbrido MSE 0.425 | Escalada, escalador no declarado | Texto: sí; 2/2 |
| 18 | Martínez & Acuña (2025), SCCC | t+1 (10 min), NARX/NARMAX directo | Sí | ? | ? | Cronológica (sin CV) | Sin cifras visibles | — | Texto: no (fragmentos); sin verificación adversarial |
| 19 | Sarwoko, Vianita & Wibowo (2025), ETASR | t+1 (10 min), ventana de 12; objetivo = suma | Sí | No | ? (solo pasado) | Cronológica, último 20 %. Escalador y clustering ajustados **sobre todo el dataset** | Sin Zona 1. LSTM+KMeans RMSE 721.70, MAE 493.72, R² 0.9974 | kW (suma, tras invertir la escala) | Texto: sí; 2/2 |
| 20 | SJI 13(2) (2026), CNN-LSTM-Transformer | t+1 (10 min), ventana de 24 | Sí | ? | ? | Cronológica 80/20; normaliza y suaviza **antes** de partir | Escenario S4: MAE 257, RMSE 423, MAPE 0.82 %. Problemas: sus "líneas base" provienen de otros estudios (consumo de gasolina y de hogares); filas imposibles (MAE > RMSE; una fila idéntica en las tres zonas); lista variables que no existen en UCI 849 (presión atmosférica, radiación solar) | "kWh" (son kW) | Texto: sí; sin verificación adversarial |
| 21 | Od et al. (2026), preprint arXiv (QRC) | 1 h adelante, Zona 1 horaria | Sí | No | ? | Cronológica 70/10/20 | RMSE 3,359, MAPE 9.81 %, R² 0.695. Cálculos del extractor en el mismo test: persistencia horaria RMSE 2,362, MAPE 6.05 %, R² 0.850; naive estacional 24 h RMSE 1,452, MAPE 3.34 %, R² 0.943. El QRC queda **por debajo de ambas líneas base triviales** | "kWh" (son kW, media horaria) | Texto: sí; sin verificación adversarial |
| 22 | FedTrees (2022), arXiv 2210.00060 (versión de revista: FedraTrees, EAAI 2023) | 1 h adelante; objetivo = suma | Sí | ? | No | 80/20, orden no declarado | Sin Zona 1. Configuración federada (Tablas 5 y 6): persistencia MAPE 6.64 %, FedAvg 3.43 %, FedTrees 3.69 %. (El LGBM centralizado de 2.69 % es de otra tabla, la 2, sin persistencia.) **Advertencia:** la persistencia tiene un MAE 4.7 veces mayor pero un MAPE solo 1.9 veces mayor; no se sabe si el MAPE se calculó sobre datos escalados | MinMax [0, 1] | Texto: sí; 2/2 |

**C. Multi-paso (3)**

| # | Autor (año), tipo | Tarea / horizonte | Consumo pasado | Clima contemp. | Otras zonas | Partición | Métricas Zona 1 | Escala / unidad | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 23 | RWKV-CVM (2026), Electricity MDPI | Directo, 4–72 h (promedio de los pasos 1..H) | Sí | No | No (solo pasado) | Cronológica 70/10/20 | MSE promediado sobre horizontes: 0.02585 | z-score (no kW) | Texto: sí; sin verificación adversarial |
| 24 | Electronics 15:5213 (2026), APRC-LSTM | Día siguiente, 1–24 h (medias horarias) | Sí | No | No | Cronológica, 4 orígenes expansivos | NMAE (MAE/pico): APRC 1.316 % frente a persistencia del día previo 1.813 % | NMAE (% del pico de train) | Texto: sí; 2/2 |
| 25 | AsymDF (2026), IEEE Access | 48 h a 15 días (30 min) | Sí | No | No | Cronológica ≈ 70/10/20 | Sin Zona 1; zonas agregadas MSE 0.0887 | z-score | Texto: sí; sin verificación adversarial |

**D. Mixtos (3)**

| # | Autor (año), tipo | Tarea / horizonte | Consumo pasado | Clima contemp. | Otras zonas | Partición | Métricas Zona 1 | Escala / unidad | Verificación |
|---|---|---|---|---|---|---|---|---|---|
| 26 | Islam et al. (2025), Quality & Quantity | Un paso con rezagos reales en test + recursivo a 1–2 días con clima observado (oráculo) | Sí | Sí | ? | Cronológica 75/15/10 | Solo leído en gráfico (aprox.): 10 min, 1D: MAPE ≈ 10.5 %, R² ≈ 64 %; horario, 1D: MAPE ≈ 9.0 %, R² ≈ 72 % | % (MAPE, R²) | Texto: no; sin verificación adversarial |
| 27 | Guha et al. (2025), IEEE Access | VAR + residuo a un paso; horizonte no definido | Sí | No (clima endógeno en el VAR) | No | Cronológica (inferida) | VAR+RF: NRMSE 0.6977, MAPE 14.10 %, R² 0.5128, MAE 3,956.22 | NRMSE sobre datos MinMax; MAE en kW | Texto: sí; sin verificación adversarial |
| 28 | Zhao (2024), J. Electrotechnology (Clausius) | Diario: SARIMA multi-paso + RF con rezagos de 1 y 7 días | Sí | ? | No | Cronológica (inferida) | Zona 1 diaria: MAE SARIMA 944.903; combinado 562.767 | kW, media diaria | Texto: sí; 2/2 |

**E. Tarea no determinable o no declarada (13)**

| # | Autor (año), tipo | Lo que se sabe | Partición | Métricas | Escala / unidad | Verificación |
|---|---|---|---|---|---|---|
| 29 | Biswas, Ahmed Mahdi & Das Gupta (2026), Results in Engineering | Pronóstico con Darts y rezagos de carga; horizonte "n = ?"; Quads a 10 min y horario | Cronológica 80/20 | Solo de gráficos (aprox.): Quads RF MAPE ≈ 7 % (10 min), ≈ 1.3–1.6 % (horario) | Ejes en "MW" (son kW) | Texto: no; **disputado (1/2 refuta** el "clima contemporáneo = sí") |
| 30 | Boriratrit & Chatthaworn (2023), ICACI | CEEMDAN-LM-LSTM | ? | R² "hasta 0.9999" sin zona ni horizonte | ? | Texto: no; 2/2 |
| 31 | Bensalah & Hair (2024), IRASET | SARIMA univariado → pronóstico; horizonte desconocido | Probablemente cronológica | RMSE 2,134.62 / MAPE 5.33 % **solo de fuente secundaria, sin verificar** | kW presumible | Texto: no; 2/2 |
| 32 | JISIS 15(3) (2025), CNN modificada | Probablemente MI (inferido de la arquitectura) | Dice "secuencial"; la Fig. 9 sugiere barajada | Sin zona: MAE 0.1594, R² 0.9561 | z-score | Texto: sí; 2/2 |
| 33 | Eid (2026), Fusion: Practice & Applications | Probablemente MI (calendario + clima en SHAP) | Cronológica (80 % train) | Sin zona: "R²" 0.990. **No se cuenta como R² auténtico:** R² > r² en todos los modelos, lo que es imposible | MinMax [0, 1] | Texto: sí; 2/2 |
| 34 | JAIT 17(6) (2026), EHHO | "Nowcast" con medias móviles de carga; objetivo = suma suavizada | Cronológica | Total: MAPE 0.30 %, R² 0.9996 | kW (suma suavizada) | Texto: sí; 2/2 |
| 35 | Cao & Li (2026), J. Power Technologies | ESN: "future value", horizonte no declarado; suavizado gaussiano de todo el PN antes de modelar | No descrita | Zona 1 (Quads): MSE 0.0016 (RG-ESN) frente a 0.0037 | Normalizada, método no declarado | Texto: sí; **disputado (1/2 refuta**: lo considera pronóstico, no "poco claro") |
| 36 | ISSA-BiTCN-LSTM (2025), Cognitive Computation | Desconocido | ? | Días de descanso: RMSE 925.11, MAE 732.63, MAPE 1.034 % (probablemente carga total) | kW | Texto: no; 2/2 |
| 38 | Meshak Immanuvel et al. (2025), ICEES | Desconocido ("regresión") | ? | Sin cifras | — | Texto: no; 2/2 |
| 39 | Santhi & Meiliana (2025), ISRITI | Probablemente t+1 (no declarado) | ? | MAE 428.12, MAPE 0.68 % (probablemente total) | kW presumible | Texto: no; 2/2 |
| 40 | ICSIST (2026), Autoformer + conformal | Probablemente multi-horizonte (no declarado) | ? | Zona 1: RMSE 1,089.73, MAE 860.09, MAPE 3.17 %, PICP 0.891 | No declarada (prob. kW) | Texto: no; 2/2 |
| 41 | Ari & Burukanli (2025), ISAS | Desconocido. Híbrido RF→LSTM: el RF solo da R² 0.5754 y el LSTM solo 0.6743, frente a 0.9813 del híbrido; el salto sugiere fuga por meta-features del RF calculadas en la misma muestra (no verificable) | ? | MAPE 2.29 %, R² 98.13 % (zona no declarada) | % | Texto: no; 2/2 |
| 42 | Hambali, Wreford & Olasupo (2024), capítulo CRC | "Weekly intervals", ambiguo | ? | Sin cifras | — | Texto: no; 2/2 |

**F. No son pronóstico (2)**

| # | Trabajo | Qué hace | Verificación |
|---|---|---|---|
| 43 | Kahil, Jellouli & Fihri (2025), Statistics | Detección de anomalías (DBSCAN + EVT); "99 % accuracy" sobre benchmarks etiquetados | Texto: no; 2/2 |
| 44 | Ma (2023), preprint arXiv | Entropía de transferencia clima → consumo con rezagos de 1–24 h, en 5 días de octubre | Texto: sí; sin verificación adversarial |

**Fuera de la tabla (uso del dataset no confirmado):**
- **DTGA**, Cognitive Computation (2025), doi 10.1007/s12559-025-10402-8. Es probable que use Tetouan (tres zonas y cita a Salam & El Hibaoui), pero no está confirmado. Reporta R² de 0.9918, 0.9924 y 0.9934 sin indicar horizonte ni partición.
- **n.º 37, Asal (2025), ICHORA.** El resumen solo menciona "three distinct zones" y no nombra Tetouan ni UCI; el verificador indica que el uso de UCI 849 no está confirmado. Tarea desconocida (probable MI, sin verificar); sin cifras. Conservamos su número para no renumerar la tabla.

**Identificados, no revisados** (aparecen citados en el paquete de evidencia; no se extrajeron ni verificaron):
- **FELDL**, "IoT-Enabled Electric Load Prediction via Federated Label Distribution Learning" (doi 10.1002/itl2.70177): usa Tetouan con partición aleatoria 75/25 "following [20]" (Salam & El Hibaoui). Sería otro caso de mismo instante con partición aleatoria.
- **Salam & El Hibaoui (2021)**, Math. Comput. Simul. 190:97-109 ("Deep Inception Residual Network" + LSTM): RMSE mediana 5,876 según Satan et al.; RMSE 5,708 según la Tabla 1 de BOKNN.
- **Sadhana (2025)**, doi 10.1007/s12046-025-02761-7.
- **ICECCME (2023)**, doi 10.1109/ICECCME57830.2023.10252535.
- **EPSR (2022)**: afirma que el MLP fue el mejor modelo en Salam & El Hibaoui 2018, en conflicto con su resumen.
- **Priyadarshini et al. (2022)**: ensemble con "R² close to 99 %" (citado en la tesis de Eghaghe).
- **Wang et al.**: ensemble LSTM-Informer, "prior best result" según RWKV-CVM (Zona 3, otra normalización).

### 2.3 Veredicto sobre la afirmación "la mayoría reporta R² ≈ 98 % regresando el consumo del mismo instante a partir del clima"

**Qué R² contamos.** Contamos como "R² auténtico" el coeficiente de determinación 1 − SS_res/SS_tot reportado sobre test, tal como lo da cada paper (no lo recalculamos). Excluimos:
- n.º 7 (JUTIF): la Ec. 4 es una r de Pearson.
- n.º 9 (BOKNN): es una "accuracy" de matriz de confusión.
- n.º 15 (Chang & Ke): la Ec. (15) define SS_Res como la dispersión de las predicciones.
- n.º 6 (Satan): su Ec. 4 pone las predicciones en el denominador (no reporta R² para Tetouan, pero su definición tampoco sería válida).
- n.º 33 (Eid): R² > r² en todos los modelos, lo que es matemáticamente imposible.

**Nota de cautela:** tres trabajos reportan exactamente 98.13 %: el n.º 2 en el resumen (0.9812 en su tabla), el n.º 9 ("accuracy") y el n.º 41 (R²). Puede ser casualidad, pero conviene no citar esa cifra sin la fuente primaria.

**Conteos sobre los 41 trabajos de predicción o regresión de la tabla:**

| Categoría | N | Con R² ≥ ~0.97 reportado |
|---|---|---|
| Mismo instante (6 con texto leído; n.º 1 de segunda mano; n.º 6 y 9 inferidos) | 9 | 3 auténticos (n.º 2, 3, 5) + 2 que no son R² (n.º 7: r de Pearson; n.º 9: "accuracy") |
| Un paso con rezagos | 13 | 7 (n.º 10, 11 [Z2], 12, 13, 14, 16, 19) + n.º 15 con fórmula no estándar |
| Multi-paso | 3 | 0 (reportan MSE estandarizado o NMAE) |
| Mixto | 3 | 0 (R² de 0.51 a 0.72) |
| No determinable | 13 | 3 (n.º 30, 34, 41) + n.º 33 con R² imposible + n.º 32 con 0.956 |

**Qué se sostiene:**
- Existe un grupo de trabajos de mismo instante que llega a R² ≈ 0.98. Al menos uno usa partición aleatoria explícita (Eghaghe). En Abdillahi & Etem la partición aleatoria se infirió y se confirmó por reproducción: KNN con clima y calendario da R² 0.9842 con partición aleatoria y 0.4098 con partición cronológica.
- El trabajo que dio origen al dataset (Salam & El Hibaoui 2018) también es de mismo instante. Su partición aleatoria solo está atestiguada de segunda mano, y **no reporta R²**: el "R² ≈ 98 %" que otros trabajos le atribuyen no procede de él.
- Las réplicas propias muestran el mecanismo. Un RandomForest **solo con calendario** (sin clima ni rezagos) logra R² 0.994 con partición aleatoria y 0.126 con partición cronológica. Con clima solamente, 0.577 frente a −0.211.
- **La fuga por otras zonas tiene el mismo efecto.** En la reproducción del extractor de Abdillahi & Etem, KNN con clima y las Zonas 2 y 3 del mismo instante da R² 0.9839 con partición aleatoria y 0.396 con partición cronológica. En AVITEC (n.º 8) la Tabla 2 normaliza las tres zonas junto con el clima y no se nombra el objetivo; en JUTIF (n.º 7) no se sabe qué columnas usa la línea base KNN sin selección de variables. Varios trabajos de mismo instante dejan "otras zonas" como "?".

**Qué no se sostiene:**
- "**La mayoría**": solo 9 de 41 trabajos (≈ 22 %) se clasifican como mismo instante, y 3 de ellos por inferencia o de segunda mano. Aun sumando los de la categoría E que probablemente lo son (n.º 32, 33, 38), se llega a 12 de 41 (≈ 29 %), menos de un tercio.
- "**R² ≈ 98 % a partir del clima**": dentro del grupo de mismo instante, solo 3 trabajos reportan un R² auténtico cercano a 0.98, y 4 de los 9 no reportan R². Además, el R² alto viene sobre todo del **calendario** o de **otras zonas del mismo instante** combinados con la **partición aleatoria**, no del clima. Con clima solamente, aun barajando, KNN da R² 0.45 y RF 0.58.
- El R² ≥ 0.976 aparece con **mayor frecuencia en pronósticos a un paso** (7 trabajos con R² estándar) que en los de mismo instante. A t+1 (10 min) la persistencia ya logra R² ≈ 0.99 (cálculo del extractor en la partición de Singh & Tewari, no reverificado), y a t+6 nuestra "persistencia + delta diario" logra 0.981.

**Excepciones relevantes** (trabajos con evaluación honesta o con cifras modestas):
- Bunke & Hrudzynskyi: cronológica y con persistencia.
- Kshetrimayum et al.: CV expansiva y con persistencia.
- Electronics 15:5213: varios orígenes, persistencia y bootstrap.
- Od et al.: R² 0.695 a 1 h, por debajo de la persistencia y del naive estacional según los cálculos del extractor.
- Guha et al.: R² 0.51.
- Islam et al.: R² 0.64–0.72 a 1 día.
- RWKV-CVM y AsymDF: multi-paso con datos estrictamente pasados.

**Verificado frente a no accesible:**
- Texto completo leído: 30 de los 45 trabajos considerados (los 43 de la tabla más DTGA y el n.º 37).
- Texto no accesible: 15. Son los n.º 1, 18, 26, 29, 30, 31, 36, 37, 38, 39, 40, 41, 42, 43 y DTGA (conferencias IEEE de acceso cerrado, Springer, Elsevier y Taylor & Francis).
- Para los no accesibles, las clasificaciones son "poco claro" o se basan en el resumen, los fragmentos y las citas. No deben usarse como evidencia ni a favor ni en contra de la afirmación.
- Solo 4 trabajos reportan una línea base ingenua dentro del propio paper (n.º 13, 14, 22, 24).

---

## 3. Qué implica para el paper del equipo

1. **Comparabilidad.** Ningún número de la tabla es directamente comparable con "Zona 1, 10 min, t+6, partición cronológica 70/15/15". Las referencias más cercanas, que deben citarse con sus diferencias explícitas, son:
   - **Bunke & Hrudzynskyi (2026):** Zona 1, media horaria, 1 h adelante, 70/15/15. Su objetivo es la media de los próximos 6 valores, no el valor puntual en t+6, y es más suave. Un naive estacional de 24 h (cálculo del extractor) supera a sus modelos recurrentes.
   - **Od et al. (2026):** Zona 1 horaria, 1 h; queda por debajo de la persistencia y del naive estacional.
   - **RWKV-CVM (2026):** Zona 1 a 10 min, partición cronológica. Su H = 24 promedia los pasos 1..24, que incluyen t+6, pero reporta MSE estandarizado.
   - **Biswas et al. (2026):** Quads (Zona 1) a 10 min y horario, partición cronológica; horizonte no declarado y cifras solo leídas de gráficos.
   - **ICSIST (2026):** Zona 1, MAPE 3.17 %, pero con horizonte no declarado.
   - **Singh & Tewari (2026):** Zona 1 a t+1 (10 min); su pipeline de Zona 1 es ≈ 2.6 veces peor que la persistencia.
   - **SJI (2026):** Zona 1 a t+1, pero con **peso bajo**: líneas base copiadas de otros estudios, filas imposibles, variables inexistentes en UCI 849 y normalización antes de la partición.
2. **La persistencia sola no basta como referencia.** Con t+6 se pasa de 1,821 a 567 kW de MAE en test usando solo un rezago diario (ver la sección 4.4). Un modelo "2.3 veces mejor que la persistencia" podría no superar a esta línea base trivial. La literatura lo confirma: en Bunke & Hrudzynskyi, un naive estacional de 24 h (RMSE 1,448, R² 0.942) supera a LSTM, GRU y LSTM-Attention; en Od et al., el QRC queda por debajo de la persistencia y del naive de 24 h; en Singh & Tewari, los pipelines de Zonas 1 y 3 son peores que la persistencia. Recomendamos reportar el skill frente a la persistencia **y** frente a la "persistencia + delta diario".
3. **Cómo redactarlo sin exagerar.** Evitar "la mayoría de trabajos reportan R² de 98 % con modelos de mismo instante" y "somos los primeros en…". Texto sugerido:

   > «En la literatura sobre el conjunto UCI 849 coexisten tareas distintas bajo el nombre de "predicción". Una parte de los trabajos estima el consumo del mismo instante a partir de variables meteorológicas y de calendario medidas en ese instante, en varios casos con particiones aleatorias de registros de 10 minutos, y reporta R² cercanos a 0.98 (p. ej., Eghaghe, 2024; Abdillahi y Etem, 2025). Otra parte pronostica un paso adelante (10 min o 1 h) usando rezagos del consumo, configuración en la que la persistencia ya alcanza R² elevados. De los 41 trabajos revisados, solo cuatro reportan una línea base ingenua. Un R² alto no basta como evidencia: en nuestra partición, una línea base trivial (la persistencia más el cambio observado el día anterior) alcanza R² 0.981 a 60 minutos. Por ello no comparamos nuestras cifras con esos valores; reportamos el desempeño frente a líneas base de persistencia y estacionales evaluadas sobre la misma partición cronológica, a un horizonte de 60 minutos.»

   Si se quiere mencionar la novedad: «No encontramos trabajos que evalúen la Zona 1 a resolución de 10 minutos con un horizonte de 60 minutos y partición cronológica». Así se describe el resultado de esta búsqueda, sin afirmar que no existen; además, la revisión no es un censo (hay trabajos identificados y no revisados).
4. **Cifras de terceros.** Citar las cifras de los trabajos no leídos (n.º 1, 18, 26, 29–31, 36–42, 43 y DTGA) solo con la nota "según el resumen o fuentes secundarias". En particular, la RMSE de Salam & El Hibaoui (3,174.7 frente a 2,336.9) no debe citarse sin el PDF original, ni atribuirle un R² ≈ 98 %.

---

## 4. Hechos del dataset relevantes

### 4.1 Procedencia y unidades

| Hecho | Soporte | Confianza |
|---|---|---|
| La página de UCI **no da unidades** para ninguna variable | Página de UCI | Alta |
| El resumen del paper original dice que los datos SCADA van cada 10 min del 1 de enero al 31 de diciembre de 2017. **La confianza "Alta" se refiere a lo que dice el resumen, no al archivo:** el CSV termina el 30 de diciembre a las 23:50 (ver 4.2) | Resumen de IRSEC 2018 (texto cerrado) | Alta (sobre el resumen) |
| El operador es Amendis; las subestaciones son Quads, Smir y Boussafou (63 kV → 20 kV) | Solo la ficha de Kaggle | Media |
| Zona 1 = Quads, 2 = Smir, 3 = Boussafou | Solo un README de GitHub | **Baja** |
| La unidad es kW (potencia media) | Fuente secundaria (arXiv 2305.16546) + plausibilidad: la suma de medias es ≈ 71.2 MW, ≈ 1,130 kWh por habitante al año. **Pero** el reescalado entero por mes (4.2) pone en duda que sean kW crudos: podrían ser kW reescalados mes a mes | Media |
| "general diffuse flows" y "diffuse flows" no tienen unidades documentadas. DF > GDF en el 14 % de las filas con GDF > 100, lo que contradice la lectura "global frente a difusa". La ficha de Kaggle define "diffuse flow" con un texto copiado sobre fuentes hidrotermales | Cálculo propio + Kaggle | Alta |

### 4.2 Peculiaridades (cálculos propios sobre el CSV)

- **Cobertura:** 52,416 filas a paso exacto de 10 min, del 2017-01-01 00:00 al **2017-12-30 23:50**. Falta el 31 de diciembre. No hay duplicados ni huecos, y todos los días tienen 144 filas, incluidos los de cambio de hora.
- **Reescalado mensual sin documentar:** dentro de cada mes, todos los valores de cada zona son un entero dividido por un denominador propio del mes. En la Zona 1: enero 79, febrero 59, marzo 47, abril 929, mayo 61, junio 151, julio 301, agosto 901, septiembre 113, octubre 457, noviembre 13, diciembre 263. No conocemos la interpretación; afecta a la confianza en las unidades (4.1).
- **Viento poco plausible:** es bimodal. El 57.6 % de las filas está por debajo de 0.2 y el 38.6 % por encima de 4, y la serie se queda semanas en un régimen (p. ej., del 21 de julio al 16 de agosto ≈ 4.91 constante). La temperatura y la humedad parecen mediciones reales.
- **Traspaso de carga de la Zona 1 a la Zona 2 el 24 y 25 de octubre de 2017:** la Zona 1 baja unos 3 MW, la Zona 2 sube lo mismo y la suma Z1+Z2 se mantiene (55,319 → 55,224). **Todo el test (desde el 2017-11-06 09:30) queda después**, y la validación (desde el 2017-09-12 19:10) lo atraviesa. Consecuencias:
  - Si el modelo usa rezagos de la Zona 2, su relación con la Zona 1 cambia después del 25 de octubre; las variables de otras zonas pueden "romperse" justo en el test.
  - Como la validación atraviesa el corte, la selección de hiperparámetros mezcla dos regímenes.
- **Zona 3:** sube en verano (Z3/Z1 = 0.78 en julio frente a 0.38 en diciembre), cae entre el 28 de agosto y el 1 de septiembre, y da un salto temporal de +20–26 % entre el 8 y el 18 de noviembre (dentro del test). Esto importa porque los rezagos de la Zona 3 son variables del modelo.

### 4.3 Calendario de 2017 y cambio de hora (Marruecos)

- **Horario de verano** (IANA tzdata y timeanddate): empieza el 26 de marzo, se suspende por Ramadán del 21 de mayo al 2 de julio y termina el 29 de octubre.
- **Las marcas de tiempo no muestran saltos de DST.** El centroide solar y la rampa vespertina no se desplazan unos 60 min, lo que es compatible con un reloj fijo de aproximadamente UTC+1 (inferido). La rampa matutina tampoco se mueve, así que la conclusión **no es concluyente**.
- **Ramadán** (≈ 27 de mayo al 25 de junio): la carga de madrugada de la Zona 1 sube de ≈ 26.7k a 38.5k (01 h) y de ≈ 25.4k a 39.9k (02 h).
- **Feriados con efecto medido en la Zona 1** (relativo a ±3 semanas, mismo día de la semana):
  - Aid al-Fitr: 26 de junio −12 % y 27 de junio −18 %.
  - Aid al-Adha: **1 de septiembre**, −16.5 %. Yabiladi y los datos apuntan al 1; timeanddate da el 2.
  - 1 de mayo: −9 %.
  - 6 de noviembre (Marcha Verde): −7.5 %.
  - 1 de diciembre (Mawlid): −7 %.
- **Feriados dentro del test** (que empieza el 6 de noviembre a las 09:30): 6 de noviembre (parcialmente), **18 de noviembre** (Día de la Independencia, dentro del salto de la Zona 3; efecto no medido) y 1 de diciembre. La Navidad no es feriado en Marruecos.

### 4.4 Líneas base ingenuas para la Zona 1 a t+6 (cálculo propio, misma partición 70/15/15)

| Línea base | MAE año | MAE val | MAE test | MAPE test |
|---|---|---|---|---|
| Persistencia y(t) | 2,181 | 2,079 | 1,821 | 6.28 % (R² 0.829) |
| Mismo instante de ayer, y(t−138) | 1,301 | 1,158 | 985 | 3.44 % |
| Mismo instante de la semana anterior, y(t−1002) | 1,469 | 1,438 | 841 | 2.95 % |
| **y(t) + [y(t−138) − y(t−144)]** | **671** | **629** | **567** | **1.99 % (R² 0.981)** |
| y(t) + [y(t−1002) − y(t−1008)] | 759 | 693 | 560 | 1.97 % |

- La persistencia reproduce el MAE de test que reportó el equipo (1,821). En validación sale 2,079 frente a 2,073; la pequeña diferencia probablemente viene del borde de la partición.
- La persistencia a t+6 en la partición de Singh & Tewari (80/20 sin las primeras 1,008 filas) da R² 0.826 (cálculo del extractor), coherente con nuestro 0.829.
- Por mes, el MAE de la persistencia va de 1,803 (diciembre) a 2,433 (agosto; noviembre 1,842), y el del delta diario de 528 (diciembre) a 763 (junio).
- A resolución horaria (medias), la persistencia a 1 h da MAE 2,100, MAPE 6.56 % y R² 0.844, y la misma hora de ayer MAE 1,262 y MAPE 4.02 %. **El paquete no indica el periodo de estas cifras horarias (parece el año completo)**, así que no se comparan con el 6.28 % del test a 10 min. Para el último 20 % de los datos, Od et al. (cálculo del extractor) dan una persistencia horaria de 6.05 %.
- **Alcance del test:** cubre solo noviembre y diciembre (una sola estación, después de la ruptura del 24–25 de octubre, con el salto de la Zona 3 y tres feriados). Recomendamos reportar el error **por mes** y **con y sin las ventanas anómalas** (traspaso Z1→Z2, salto de Z3, feriados).
- **Atención:** el primer modelo del equipo (MAE CV 997 ± 353) se evaluó en otros folds, con mucha varianza. El delta diario da 671 en el año completo. Hay que compararlos en los mismos folds, con una prueba de significancia (sección 6), antes de afirmar que el modelo supera a las líneas base.

---

## 5. Baseline real en Perú (COES, SEIN)

### 5.1 Cómo pronostica el COES (normativa leída en texto completo)

- **PR-03, "Pronóstico de la Demanda a Corto Plazo del SEIN"** (Res. Osinergmin 005-2011-OS/CD). Define dos pronósticos:
  - **PSO** (programa semanal): al menos 168 periodos **horarios**, publicado como máximo el jueves a las 18:00, para el periodo de sábado a viernes. En los datos del portal, el PSO se repite en pares de medias horas (resolución horaria), así que al medirlo a 30 min arrastra un error intrahorario.
  - **PDO** (programa diario): 48 medias horas, publicado hasta las 16:00 del día D−1 (PR-01) para el día D. La anticipación depende del hito desde el que se mida:
    - desde la **publicación del PDO** (16:00 de D−1): unas **8 a 32 h**;
    - desde el **envío de las previsiones de los agentes** (08:00 de D−1): unas **16 a 40 h**.
- **Método oficial (Anexo A del PR-03):** días similares, determinista.
  - Toma los últimos 5 días del mismo tipo (sábado, domingo y lunes por separado; martes a viernes juntos).
  - Depura los valores que difieren más de 5 % de la mediana.
  - Arma un perfil por unidad.
  - Aplica una tendencia lineal por mínimos cuadrados.
  - Suma la demanda industrial (≥ 10 MW) declarada por los Usuarios Libres.
  - Trata los feriados con factores de proporción.
  - El PR-03 permite reemplazar el método por otro con menores desviaciones.
- **Plazos para los agentes:** envían su previsión a 30 min del día siguiente antes de las 08:00, y la semanal el martes antes de las 08:00.
- **Reprogramación (PR-06, Res. 012-2021-OS/CD):** el parámetro de demanda γ se calcula cada 30 min. Si sale de tolerancia más de 3 medias horas seguidas, se elabora un RDO en un máximo de 120 min. Los Usuarios Libres con variaciones mayores a 75 MW deben actualizar su proyección.
- **PR-05:** el IEOD diario incluye las "Desviaciones de la demanda respecto a su pronóstico".
- **PR-22:** dimensiona la reserva secundaria con los errores medio horarios del PDO. El informe de Osinergmin 075-2026-GRT solo los muestra en gráficos.
- **Herramientas** (Memorias COES): modelo de despacho "Yupana" ("Yupana Continuo" para acelerar los RDO) y una aplicación en Python para el pronóstico de demanda.
- **Pronóstico automático de tiempo real:** el portal lo muestra con banda mínima y máxima, pero **solo para el día en curso, sin historial**.

### 5.2 Cifras oficiales de error

**No encontramos un MAPE oficial publicado** del pronóstico de demanda ni en las Memorias 2023–2025 ni en los Informes de Evaluación.

Literatura peruana (solo resúmenes o fragmentos):
- Gonzales Chávez (TECNIA 2014, UNI): ARIMA con sucesos externos < 1 % frente a "≈ 2 % con técnicas determinísticas", para la demanda diaria total. Confianza media; solo resumen.
- Tesis Curo Martínez (2022): MAPE 0.993 % diario. Solo fragmento de búsqueda; confianza baja.
- Tesis UNI con razonamiento inductivo difuso: dice superar al método del COES. Solo fragmento; confianza baja.

### 5.3 Errores calculados con datos públicos descargados

**Acceso:** `POST https://www.coes.org.pe/Portal/portalinformacion/Demanda` con `fechaInicial` y `fechaFinal` (dd/mm/yyyy). Devuelve JSON con Ejecutado, Programación Diaria y Programación Semanal cada 30 min. Lo encontramos en `demanda.js`. Para descarga manual existe `ExportarDemanda?fechaInicial=..&fechaFinal=..` (Excel).

Se descargaron 173,664 medias horas (2017 a noviembre de 2026) en un análisis y 85,728 (2022 a 2026-11-21) en otro.

**Método:** MAPE = media(|ŷ−y|/y). Las líneas base son rezagos de la demanda ejecutada: t−1 = 30 min, t−2 = 1 h, t−48 = 24 h, t−336 = 7 días.

| Periodo | PDO (día previo) | PSO | Persistencia 30 min | Persistencia 1 h | Naive 24 h | Naive 7 d |
|---|---|---|---|---|---|---|
| 2017 (media ≈ 5,659 MW) | 1.76 % (MAE 98.2 MW) | 2.42 % | 1.57 % | 2.75 % | 4.33 % | 2.64 % |
| Nov–dic 2017 (mismos meses que el test de Tetouan) | 1.75 % | 2.30 % | — | 2.74 % | 4.44 % | 2.52 % |
| 2023–2025 (media 6,917 MW) | 1.58 % (MAE 108.1, RMSE 142.9, sesgo +24.7 MW) | 1.98 % | — | 2.35 % | 3.70 % | 2.52 % |
| 2025 (media ≈ 7,075 MW) | 1.50 % (MAE 105.0, sesgo +23.3 MW) | 1.95 % (sesgo +47.4) | 1.38 % (MAE 96.9) | 2.34 % (MAE 164.0) | 3.75–3.78 %* | 2.50 % (MAE 173.9) |
| Nov–dic 2025 | 1.51 % | — | — | 2.37 % | — | — |

\*Dos análisis independientes difieren levemente, sin causa determinada.

**Datos adicionales:**
- **MAPE del PDO por año:** 2017 1.76; 2018 1.66; 2019 1.59; 2020 1.91; 2021 1.54; 2022 1.57; 2023 1.72; 2024 1.53; 2025 1.50; 2026 (hasta el 21 de noviembre) 1.49 %.
- **MAPE de la media diaria del PDO en 2025:** 1.13 %. Peor día: **2025-10-09, con 7.3 %** de APE diario.
- **Referencias híbridas a 1 h (2025):**
  - y(t−2) + PDO(t) − PDO(t−2) = **1.03 %** (MAE 71.8 MW). En noviembre y diciembre de 2025, 1.02 %. **No es un baseline equivalente a los de Tetouan:** usa un producto del operador (declaraciones industriales de los Usuarios Libres y ajuste experto) que Tetouan no tiene.
  - y(t−2) + Δsemana = 1.22 % (MAE 85.0 MW). Esta sí es análoga al delta semanal de Tetouan.
- **Réplica simplificada del PR-03** (sin carga industrial ni feriados): 2.2–2.5 % (4.3 % en 2020). Queda peor que el PDO real, lo que sugiere que las cargas declaradas y el ajuste experto aportan.
- **Distribución del error del PDO en 2025:**
  - APE mediano 1.18 %.
  - MAPE diario: p50 1.25 %, p90 2.40 %, p99 4.56 %.
  - Por hora: 1.26–1.72 %.
  - Sesgo de +40 a +58 MW entre las 12 y las 16 h.
- **Eventos en la serie ejecutada:** por ejemplo, el 2025-08-26 a la 01:30 la demanda cayó ≈ 1,932 MW en 30 min. La causa no está verificada.

**Advertencias:**
- No está confirmado que la columna "Programación Diaria" sea siempre el PDO original. El 2026-11-22 sus valores difieren de los del RDO, lo que apunta a que sí lo es (confianza media).
- El PR-03 citado es de 2011; puede haber versiones posteriores.
- El MAPE del PSO medido a 30 min incluye el error de usar un valor horario para dos medias horas.

### 5.4 Comparación y escala

- **Escala:** el SEIN tiene una media de ≈ 7,000 MW (2025) y la Zona 1 de Tetouan, ≈ 32 MW (media de 32,345 kW). La relación es del orden de 200 veces (cálculo aritmético de este informe). Una de las síntesis recibidas dice "unas 50 veces", lo que no cuadra con estas medias. Por agregación, la persistencia a 1 h del SEIN (2.3–2.75 %) es mucho mejor que la de la Zona 1 (6.28 %). **Los MAPE no son comparables entre sí.**
- **Medida comparable, definida una sola vez:** skill = 1 − MAE_modelo / MAE_persistencia, con la persistencia al **mismo horizonte**, sobre los **mismos datos**. Valores calculados con las cifras del paquete:

| Serie y horizonte | Referencia | Datos | Skill |
|---|---|---|---|
| Tetouan Z1, t+6 | Persistencia + delta diario | Test (567 / 1,821) | 0.69 |
| Tetouan Z1, t+6 | Persistencia + delta diario | Validación (629 / 2,079) | 0.70 |
| Tetouan Z1, t+6 | Persistencia + delta diario | Año completo (671 / 2,181) | 0.69 |
| Tetouan Z1, t+6 | Persistencia + delta semanal | Test (560 / 1,821) | 0.69 |
| Tetouan Z1, t+6 | Mismo instante de ayer | Test (985 / 1,821) | 0.46 |
| Tetouan Z1, t+6 | Modelo del equipo | Folds de CV | **Pendiente:** hace falta la MAE de la persistencia en los mismos folds (el cociente de MAPE 3.05/6.88 en CV no es la misma medida) |
| SEIN 2025, 1 h | y(t−2) + Δsemana | Año 2025 (85.0 / 164.0) | 0.48 |
| SEIN 2025, 1 h | Persistencia + ΔPDO (usa producto del operador) | Año 2025 (71.8 / 164.0) | 0.56 |
| SEIN 2025, 1 h | PDO del día previo (mezcla horizontes; solo ilustrativo) | Año 2025 (105.0 / 164.0) | 0.36 |
| SEIN 2025, 1 h | Naive semanal t−336 | Año 2025 (173.9 / 164.0) | −0.06 |

- La comparación más limpia entre países es la del delta semanal (Tetouan 0.69 frente a SEIN 0.48): mismo tipo de referencia trivial y mismo horizonte de 1 h, en series con distinta agregación y distinta forma diaria.

### 5.5 Contexto internacional

**Operadores nacionales:**
- **REE (España, 2025):** "demanda prevista" 1.37 % (5 min) y 1.25 % (horario); "Programada" 0.97 %. **El horizonte de ambas series no está documentado** (probablemente se actualizan dentro del día), así que no deben leerse como day-ahead. Persistencia a 1 h 4.09 % (5 min) y 3.92 % (horario). Naive 24 h 6.99 %. Media ≈ 29,030 MW. Cálculo propio sobre la API.
- **TSO alemanes, day-ahead (2016–2019):** MAE 3.14 % de la carga media, con sesgo.
- **PJM:** el 1.9 % horario que se suele citar es un *backcast* con el clima real, no un pronóstico operativo.
- **CAISO:** gráfico 2013–2018 en un eje de 0–2.5 %, sin valores exactos.
- **ERCOT:** ≈ 2.0 % day-ahead en agosto, solo según un fragmento de búsqueda; confianza baja.
- XM, CEN y CENACE: no se hallaron cifras.

**Benchmark KIT 2026** (horario, 1–96 h, nMAE). Su "Baseline" **no es persistencia**: es "la misma hora del último día del mismo tipo" (laborable, sábado o domingo/feriado).

| Nivel | Baseline | Transformer | LightGBM | Chronos-2 |
|---|---|---|---|---|
| TSO (TransnetBW) | 5.49 % | 2.22 % | 2.87 % | 2.88 % |
| Alimentadores BT (FeederBW) | 33.5 % | 19.2 % | 21.1 % | 19.4 % |
| Clientes (Electricity-287 = UCI 321) | 10.35 % | 7.99 % | — | 7.92 % (no es zero-shot: el dataset está en su preentrenamiento) |

- La mejora del mejor modelo sobre el baseline es de 59.6 % (TSO), 42.3 % (alimentadores) y 23.3 % (clientes).
- **Chronos-2 falla en feriados y eventos especiales** a nivel TSO.

**Otros:**
- **Alimentadores BT (arXiv 2607.01966; 15 min, 4 días de horizonte, ≈ 36 viviendas por alimentador):** R² mediano de 0.57 con Chronos-2, 0.28 con Chronos-2 sin covariables y 0.19 con WeekNaive. Es pertinente para el eje de modelos fundacionales: sin covariables, Chronos-2 pierde buena parte de su ventaja.
- **Ley de escala** (Sevlian & Rajagopal): el error relativo baja con la agregación y se satura a partir de ≈ 2.2 MW de carga media. Va de 1–2 % en subestaciones y sistemas hasta 30 % en usuarios individuales. El error irreducible crece con el horizonte. **Consecuencia:** con unos 32 MW, la Zona 1 ya está en el régimen de saturación, así que su error relativo mayor que el del SEIN no se explica solo por el tamaño; también pesan la forma de la curva diaria y el horizonte.
- **EnergyBench (2026):** los modelos fundacionales con covariables quedan estadísticamente a la par de los TSO en carga day-ahead: +6 % y +4 % en conjunto; −1 a −11 % en BE, NL y DE-LU; +41–59 % en FR. Solo ≈ 18 días evaluados.
- **BuildingsBench:** edificios comerciales, NRMSE 13.31 % frente a 16.68 % de la persistencia; residenciales, 79.34 % frente a 77.88 % (no se supera a la persistencia).

---

## 6. Insumos para diseñar los experimentos (no es un diseño cerrado)

**Ejes candidatos que sugiere la evidencia:**

1. **Horizontes:**
   - t+1 (para comparar con el grupo más numeroso con horizonte declarado, 13 de 41 trabajos) y t+6 (objetivo del proyecto).
   - Opcionalmente t+36 y t+144.
   - Reportar el error en cada paso, y a t+6 también como media de t+1..t+6, para empalmar con Bunke & Hrudzynskyi y con RWKV-CVM.
2. **Resolución:** 10 min (nativa) frente a medias horarias. Las cifras disponibles no permiten medir aún cuánto cambia la dificultad: la persistencia horaria de 6.56 % no tiene periodo indicado (probablemente año completo), mientras que el 6.28 % a 10 min es de test, y Od et al. dan 6.05 % horaria sobre el último 20 %. Hay que calcular ambas resoluciones sobre el mismo periodo.
3. **Líneas base mínimas:**
   - Persistencia.
   - y(t−138) y y(t−1002) (naive estacional diario y semanal).
   - Delta diario y delta semanal.
   - Ridge sobre rezagos (fuerte en Bunke & Hrudzynskyi).
   - Skill (sección 5.4) frente a la persistencia **y** frente al delta diario.
4. **Entradas (ablación):**
   - Solo rezagos.
   - Rezagos + calendario.
   - + clima en t.
   - + clima "oráculo" en t+6, como cota superior.
   - + rezagos de las Zonas 2 y 3 (vigilando la ruptura del 24–25 de octubre).
   - + banderas de Ramadán y feriados.
   - + variable de DST u hora legal.
   - La entropía de transferencia de Ma (2023) sugiere probar clima con rezagos de 1 a 6 h.
5. **Particiones:**
   - Cronológica 70/15/15 (actual).
   - Origen rodante (CV expansiva por meses).
   - Métricas por mes y estación, y con y sin las ventanas anómalas (el test solo cubre noviembre y diciembre).
   - Partición aleatoria solo como **experimento de contraste** para reproducir el R² ≈ 0.98 de la literatura, con calendario y con otras zonas del mismo instante.
6. **Rupturas de régimen:** decidir cómo tratar el traspaso Z1→Z2 del 24 y 25 de octubre y el salto de Z3 del 8 al 18 de noviembre. Opciones: marcarlos, añadir una variable de régimen, o reportar con y sin esas ventanas. Considerar que la validación atraviesa el corte, lo que afecta a la selección de hiperparámetros.
7. **Higiene contra fugas de información:**
   - Escaladores, clustering y STL ajustados solo en train (Sarwoko et al. y Abdillahi & Etem los ajustan sobre todo el dataset).
   - Filtros causales. JAIT y SJI suavizan la serie completa sin aclarar si la ventana es causal; Cao & Li aplican suavizado gaussiano a todo el PN.
   - Ajuste de hiperparámetros solo en validación.
8. **Métricas y significancia:**
   - MAE y RMSE en kW, MAPE, R² (definido explícitamente como 1 − SS_res/SS_tot, no r de Pearson) y skill.
   - **Prueba de significancia** frente al delta diario en los mismos folds: Diebold-Mariano o bootstrap por bloques circulares (como Electronics 15:5213). El MAE CV del modelo (997 ± 353) tiene mucha varianza.
   - Opcionalmente probabilísticas: CRPS, pinball y PICP/PINAW a 90 %, con conformal cronológico. Así se pueden comparar con ICSIST (PICP 0.891) y arXiv 2609.34120.
9. **Modelos fundacionales:**
   - Evaluar aparte los feriados del test: 6 de noviembre (el test empieza ese día a las 09:30), 18 de noviembre (Independencia, dentro del salto de Z3) y 1 de diciembre (Mawlid). Chronos-2 falla en feriados a nivel TSO.
   - Comparar con y sin covariables (en alimentadores BT, Chronos-2 cae de R² 0.57 a 0.28 sin ellas).
   - Verificar si UCI 849 está en los datos de preentrenamiento de cada modelo (para UCI 321 sí lo está en Chronos-2).
10. **Línea Perú/COES:**
    - SEIN a 30 min con horizonte t+2 (1 h).
    - Referencias: persistencia (2.34 %), naive semanal (2.50 %), y(t−2) + Δsemana (1.22 %), PDO (1.50 %) y, como referencia del operador no replicable en Tetouan, persistencia + ΔPDO (1.03 %).
    - El mismo pipeline (p. ej., LightGBM) en ambas series, comparado por skill con MAE frente a la persistencia.
    - Opcional: empezar a archivar cada 30 min el pronóstico automático de tiempo real del COES, que no tiene historial público.
11. **Reproducción de la literatura (opcional):**
    - El montaje de Bunke & Hrudzynskyi (horario, 70/15/15), ya reproducido por el extractor en persistencia y naive de 24 h.
    - La partición de Singh & Tewari (80/20 sin las primeras 1,008 filas).
    - Un caso de mismo instante con partición aleatoria frente a cronológica.

---

## 7. Preguntas abiertas y aspectos no verificados

- Las **unidades** de las zonas (kW) y de GDF/DF no tienen fuente primaria, y el reescalado entero por mes pone en duda que sean kW crudos. Haría falta el PDF de IRSEC 2018 (acceso UPC/IEEE) o el trabajo de Salam & El Hibaoui de 2021.
- La correspondencia **Zona 1 = Quads** se apoya en una sola fuente de confianza baja.
- **Reescalado mensual:** no sabemos qué significa ni si introduce saltos en los bordes de mes. No se vieron saltos evidentes (z en ±2.7).
- **Reloj de las marcas de tiempo** (fijo ≈ UTC+1 o no): inconcluso.
- La **comparación en los mismos folds** entre el modelo del equipo (MAE CV 997) y el delta diario (MAE 671 en el año) está pendiente, con prueba de significancia.
- **Trabajos sin texto completo** (n.º 1, 18, 26, 29–31, 36–42, 43 y DTGA): horizonte, partición y entradas no verificados. Las cifras de Bensalah & Hair (RMSE 2,134.62, MAPE 5.33 %) y de Salam & El Hibaoui (RMSE 3,174.7) **no están verificadas**.
- **Trabajos identificados y no revisados** (FELDL, Salam & El Hibaoui 2021, Sadhana 2025, ICECCME 2023, EPSR 2022, Priyadarshini et al. 2022, Wang et al.): pendientes de extracción.
- **Uso de UCI 849 dudoso** en el n.º 6 (Satan et al.) y no confirmado en el n.º 37 (Asal) y DTGA.
- Los **cálculos de persistencia y naive estacional de los extractores** (Singh & Tewari, da Silva, Od et al., Bunke) no fueron re-ejecutados por los verificadores.
- **FedTrees:** no se sabe si el MAPE se calculó sobre datos escalados.
- **COES:**
  - ¿"Programación Diaria" es siempre el PDO original?
  - ¿Sigue vigente el PR-03 de 2011 o fue reemplazado?
  - ¿Cuál es la tolerancia actual de γ (Anexo 1 del PR-06)?
  - ¿Está documentado el método del pronóstico de tiempo real?
  - ¿La demanda "Ejecutada" reciente es preliminar?
  - ¿Cuál es la causa de los días con eventos (p. ej., 2025-08-26 y 2025-10-09)?
- **Contexto internacional:** no se verificó el horizonte de la "demanda prevista" ni de la "programada" de REE, ni las cifras oficiales de ERCOT, CAISO (recientes), XM, CEN y CENACE.
- **Fechas religiosas de 2017:** inicio de Ramadán y Aid al-Adha (1 frente a 2 de septiembre), pendientes de un comunicado oficial del Ministerio de Habous. Los datos apoyan el 1.
- **Toto 2.0, TimeH2O, AutoGluon:** el paquete de evidencia no contiene información sobre ellos.

---

## 8. Fuentes

**Dataset y calendario**
- https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city
- https://archive.ics.uci.edu/static/public/849/power+consumption+of+tetouan+city.zip
- https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/IRSEC.2018.8703007?fields=title,abstract
- https://www.kaggle.com/datasets/fedesoriano/electric-power-consumption
- https://github.com/aNdr3W03/Electric-Predictive-Analytics
- https://arxiv.org/pdf/2305.16546v1
- https://www.timeanddate.com/time/change/morocco/casablanca?year=2017
- https://www.timeanddate.com/holidays/morocco/2017
- https://en.yabiladi.com/articles/details/56746/morocco-saudi-arabia-belgium-celebrate.html

**Literatura UCI 849**
- https://doi.org/10.1109/IRSEC.2018.8703007 · https://ieeexplore.ieee.org/rest/document/8703007/toc · https://ieeexplore.ieee.org/rest/document/8703007/figures · https://api.semanticscholar.org/graph/v1/paper/DOI:10.1109/IRSEC.2018.8703007/citations?fields=contexts
- https://dergipark.org.tr/en/download/article-file/4848479
- https://norma.ncirl.ie/8558/1/etinosaeghaghe.pdf
- https://link.springer.com/article/10.1007/s11135-024-02043-0 · https://ideas.repec.org/a/spr/qualqt/v59y2025i2d10.1007_s11135-024-02043-0.html
- https://www.nature.com/articles/s41598-025-91123-8
- https://doi.org/10.7759/s44389-026-00383-6 · https://github.com/khushvir11/Short-Term-Load-Forecasting
- https://doi.org/10.3390/engproc2026144004 · https://mdpi-res.com/d_attachment/engproc/engproc-144-00004/article_deploy/engproc-144-00004.pdf
- https://journals.snu.edu.ua/index.php/VisnikSNU/article/download/1218/1173
- https://www.researchsquare.com/article/rs-3186998/latest.pdf · https://github.com/nilakanta123/Short-Term-Load-Forecasting
- https://arxiv.org/abs/2609.34120
- https://doi.org/10.1016/j.rineng.2026.110289 · https://api.openalex.org/works/doi:10.1016/j.rineng.2026.110289
- https://doi.org/10.3390/electricity7020058 · https://github.com/Achrafchen/rwkv-cvm
- https://doi.org/10.3390/electronics15225213 · https://mdpi-res.com/d_attachment/electronics/electronics-15-05213/article_deploy/electronics-15-05213.pdf
- https://doi.org/10.1109/ACCESS.2024.3521010
- https://doi.org/10.1109/ACCESS.2025.3603620
- https://doi.org/10.1109/ACCESS.2026.3749060
- https://www.atlantis-press.com/article/125995751.pdf
- https://doi.org/10.1016/j.egyr.2023.09.175 · https://arxiv.org/pdf/2305.16546
- https://doi.org/10.1186/s42162-025-00481-0
- https://doi.org/10.1109/ICACI58115.2023.10146172
- https://doi.org/10.1109/IRASET60544.2024.10548574
- https://jutif.if.unsoed.ac.id/index.php/jurnal/article/download/4692/858
- https://doi.org/10.28989/avitec.v7i1.2722
- https://doi.org/10.56990/bajest/2025.040203
- https://doi.org/10.58346/jisis.2025.i3.032
- https://doi.org/10.54216/FPA.210217
- https://doi.org/10.1007/s12559-025-10402-8
- https://doi.org/10.1007/s12559-024-10401-1
- https://doi.org/10.1109/ICHORA65333.2025.11017058
- https://doi.org/10.1109/ICEES67011.2025.11213429
- https://doi.org/10.1109/ISRITI68345.2025.11393110
- https://doi.org/10.1109/ICSIST70215.2026.11706210
- https://doi.org/10.1109/ISAS66241.2025.11101732
- https://doi.org/10.1201/9781003503057-2
- https://papers.itc.pw.edu.pl/index.php/JPT/article/view/1985
- https://doi.org/10.1109/SCCC67219.2025.11420374
- https://www.researchsquare.com/article/rs-3741153/latest.pdf
- https://doi.org/10.1080/02331888.2025.2571861
- https://arxiv.org/abs/2301.06037 · https://github.com/majianthu/timelag
- https://etasr.com/index.php/ETASR/article/download/11938/5486
- https://journal.unnes.ac.id/journals/sji/article/download/44973/9495
- https://www.jait.us/articles/2026/JAIT-V17N6-1096.pdf
- http://www.clausiuspress.com/assets/default/article/2024/05/09/article_1715269797.pdf
- https://arxiv.org/pdf/2606.12806
- https://arxiv.org/pdf/2210.00060

**Identificados, no revisados**
- https://doi.org/10.1002/itl2.70177 (FELDL)
- https://doi.org/10.1007/s12046-025-02761-7 (Sadhana 2025)
- https://doi.org/10.1109/ICECCME57830.2023.10252535 (ICECCME 2023)

**COES / Perú**
- https://www.coes.org.pe/Portal/browser/download?url=Marco%20Normativo/Procedimientos/Tecnicos/03%20Pron%C3%B3stico%20de%20la%20Demanda%20a%20Corto%20Plazo%20del%20Sistema%20Interconectado%20Nacional.pdf
- https://cdn.www.gob.pe/uploads/document/file/834572/Osinergmin-005-2011-OS-CD.pdf.pdf
- https://www.coes.org.pe/Portal/browser/download?url=Marco%20Normativo/Procedimientos/Tecnicos/01%20Programaci%C3%B3n%20de%20la%20Operaci%C3%B3n%20de%20Corto%20Plazo.pdf
- https://busquedas.elperuano.pe/dispositivo/NL/1923902-1
- https://www.coes.org.pe/Portal/browser/download?url=Marco%20Normativo/Procedimientos/Tecnicos/05%20Evaluaci%C3%B3n%20del%20cumplimiento%20del%20programa%20diario%20de%20operaci%C3%B3n%20del%20SEIN.pdf
- https://cdn.www.gob.pe/uploads/document/file/9452252/7741164-informe-tecnico-075-2026-grt.pdf
- https://www.coes.org.pe/Portal/portalinformacion/demanda
- https://www.coes.org.pe/Portal/portalinformacion/ObtenerPronosticoTiempoReal
- https://www.coes.org.pe/Portal/Content/Scripts/PortalInformacion/demanda.js?v=1.5
- https://www.coes.org.pe/Portal/portalinformacion/ExportarDemanda?fechaInicial=01/01/2025&fechaFinal=02/01/2025
- https://www.coes.org.pe/Portal/browser/download?url=Publicaciones/Memorias%20Anuales/2025/COES_MEMORIA%202025.pdf
- https://alicia.concytec.gob.pe/vufind/Record/REVUNI_95b6e28915fd5213a8fe6752f977e15f/Details
- https://repositorioslatinoamericanos.uchile.cl/handle/2250/6235960
- https://cybertesis.uni.edu.pe/handle/20.500.14076/18474?locale=en
- https://github.com/sadelcarpio/mlops-webinar

**Contexto internacional**
- https://apidatos.ree.es/es/datos/demanda/demanda-tiempo-real
- https://arxiv.org/pdf/2302.11017
- https://www.pjm.com/-/media/committees-groups/subcommittees/las/2024/20240529/20240529-item-04--1-forecasted-vs-actual-loads-fall-winter-2023-2024.ashx
- https://www.caiso.com/documents/briefing-day-aheadloadforecastinganalysis-presentation-nov2018.pdf
- https://arxiv.org/pdf/2607.15705
- https://arxiv.org/pdf/2607.01966
- https://github.com/NREL/BuildingsBench
- https://arxiv.org/pdf/1404.0058
- https://arxiv.org/pdf/2611.07784
- https://www.ercot.com/gridinfo/load/forecast

**Artefactos locales (scripts y datos de este análisis)**
- Scripts: `/home/cip-exodia/Code/exprimental/tetouan-research/scripts/` (uci849_audit.py, uci849_baselines.py, uci849_dst.py, ajeas_repro.py, coes_err.py, ree_err.py, metrics.py, pr03_replica.py, entre otros).
- Serie COES: `/home/cip-exodia/Code/exprimental/tetouan-research/data/coes/coes_sein_demanda_30min_2022_2026.csv` y `/home/cip-exodia/Code/exprimental/tetouan-research/data/out/coes_demand_30min.csv`.
- CSV de UCI 849: `(se descarga de UCI; ver scripts)`.

---

**Las cifras del COES, la lectura del PR-03 y de los demás procedimientos, y las interpretaciones regulatorias del PDO deben validarse con un especialista en operación del SEIN**, como piden los propios análisis de origen.
