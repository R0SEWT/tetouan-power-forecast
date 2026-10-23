# Estado del arte: trabajos que usan el dataset UCI 849 "Power Consumption of Tetouan City"

Corte de la búsqueda: 22 de octubre de 2026. Dataset: Salam y El Hibaoui (2018), UCI 849
(doi:10.24432/C5B034), artículo de origen doi:10.1109/IRSEC.2018.8703007.

## Resumen

Identifiqué unas 70 obras (2018-2026) que usan el dataset, casi siempre como banco de pruebas para arquitecturas
nuevas. Dominan tres diseños: un paso de 10 min, donde la persistencia ya da un MAPE de 1.2-1.7 % y un R² de 0.99;
regresiones con el calendario y el clima del mismo instante, que no pronostican; y horizontes de 4-72 h con
métricas normalizadas. De las 30 obras de la tabla principal, solo 2 se comparan con la persistencia y ninguna con
ayer o la semana pasada; al hacerlo con los datos, varios modelos publicados no superan a una ingenua. Solo Wei
(2023) pronostica cada zona a 60 min con partición cronológica. Nadie menciona la transferencia del 25 de octubre
ni el Ramadán, y solo una obra nota, sin interpretarlo, que el viento toma dos valores. Cinco obras asignan
Z1 = Quads, Z2 = Smir y Z3 = Boussafou sin citar ninguna fuente primaria.

## 1. Cómo se armó el corpus

- **Fuentes.** (a) Las 114 obras que citan a Salam y El Hibaoui (2018) en OpenAlex. (b) Las 133 obras de OpenAlex
  con "Tetouan", "Tétouan" o "Tetuan" en el título o el resumen junto a *consumption*, *load*, *electricity* o
  *demand*. (c) Una búsqueda en el texto completo indexado por OpenAlex de "Boussafou", "Quads Smir" y "Amendis",
  palabras que solo aparecen cuando el trabajo describe este dataset.
- **Criterio de inclusión.** La obra usa el dataset si lo dice el título, el resumen o el texto completo. Las que
  solo citan el paper original quedan como "uso no confirmado".
- **Acceso.** Leí 30 textos completos: 22 de la tabla principal y 8 de la secundaria. Salieron de MDPI, Nature,
  arXiv, Research Square, repositorios institucionales (Glasgow, White Rose), revistas de acceso abierto
  (ETASR, JAIT, SJI, JISIS, DergiPark, Frontiers) y las páginas HTML de Springer e IEEE. ScienceDirect y Wiley
  bloquearon el acceso automático; las obras de Elsevier y Wiley, aunque sean de acceso abierto, se trabajaron
  con el resumen, salvo la de *Energy Reports*, que tiene preprint en arXiv. Cada fila de las tablas indica si
  salió del texto completo o solo del resumen.
- **Referencias ingenuas propias.** Para poner en contexto las cifras publicadas calculé la persistencia y las
  referencias de ayer y de la semana pasada sobre el CSV de UCI. Es un cálculo liviano; los resultados están en
  la sección 3.1.

## 2. Tabla comparativa

**Convenciones.** Z1, Z2, Z3 = zonas; "Total" = suma de las tres. "Fuga" se refiere a usar información que no
está disponible en el momento del pronóstico: el consumo simultáneo de otras zonas, el clima del instante
objetivo o el calendario combinado con una partición aleatoria. "Mismo instante" significa que el modelo
estima el consumo de t con variables de t y sin rezagos, así que no pronostica nada. Acceso: **TC** = texto
completo leído; **R** = solo resumen.

### 2.1 Tabla principal: obras con el diseño experimental extraíble

| # | Referencia | Año · revista | Zona | Horizonte | Partición | ¿Fuga? | Métricas y mejor resultado | ¿Ref. ingenua? | Acceso |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Salam y El Hibaoui | 2018 · IRSEC (congreso IEEE) | Las tres | 10 min y/o 1 h, un paso | No consta | Probable "mismo instante" (así describe Wei, 2023, a la literatura previa) | Random forest, el mejor; sin cifras en el resumen | No consta | R |
| 2 | Salam y El Hibaoui | 2021 · *Math. Comput. Simul.* | No consta | No consta | No consta | No determinable | Satan et al. (2025) le atribuyen una mediana de RMSE de 5,876 | No consta | R |
| 3 | da Silva y Meneses | 2023 · *Energy Reports* | Una serie univariante "Tetouan-Zones"; no dice cuál | 10 min, un paso (ventana de 90) | Cronológica: TimeSeriesSplit de 10 pliegues (ene-nov) y diciembre como *holdout* | No | BLSTM: MAPE 0.8 %, NRMSE 0.012, R² 0.998 (media de 10 modelos); LSTM: MAPE 1.1 % | No | TC del preprint de arXiv |
| 4 | Wang et al. | 2023 · *Electronics* | Z3; Z1, Z2 y el clima como entradas | Varios pasos: 4-20 h (con 48 h de entrada) y 24-72 h (con 8 h) | Cronológica 70/10/20 | No aparente (ventanas pasadas) | MSE y MAE normalizados; a 4 h, MSE 0.062 y MAE 0.199 | No | TC |
| 5 | Al-Jamimi et al. | 2023 · *Electronics* | Las tres como salidas simultáneas | Ninguno: mismo instante, agregado a 1 h | 80/20; no dice si es cronológica | **Sí**: año, mes, día, hora, minuto y clima del mismo instante | R² 0.97-0.98; RMSE 790-1,170 kW | No (compara con regresión lineal, ridge y SVR) | TC |
| 6 | Al-Quraan et al. (FedraTrees) | 2023 · *Eng. Appl. Artif. Intell.* | Total | 1 h, un paso (datos horarios) | 80/20; no dice si es cronológica | Leve: el clima de la hora objetivo | MAPE 3.43 % (FedAvg) y 3.69 % (FedraTrees) | **Sí**: persistencia, con MAPE 6.64 % | TC (manuscrito aceptado y preprint) |
| 7 | Wei | 2023 · ICECCME (congreso IEEE) | Cada zona por separado | 10, 60 y 120 min (modelos directos, retardo 1, 6 y 12) | Cronológica: entrena con enero y prueba de febrero a diciembre | No: solo rezagos | A 60 min, MAE de 1,866, 1,281 y 2,013 kW (Z1, Z2, Z3) | No | TC (manuscrito aceptado) |
| 8 | Rose et al. | 2023 · Atlantis Highlights (actas) | Total | Ninguno: mismo instante | 70/30; no dice el orden | **Sí**: fecha, hora y clima | Fine Tree: RMSE de prueba 2.68×10³, R² 0.976; la tabla de la variante bayesiana es inconsistente | No | TC |
| 9 | Zhang et al. (AMTCN) | 2024 · *Electronics* | Z1 (descarta las otras dos) | Varios pasos: 6, 12 y 24 (1-4 h) | Cronológica 3:1:1 y *walk-forward* | No (lo declara) | MSE, MAE, RRSE y CORR normalizados; a 24 pasos, MSE 0.080 | No | TC |
| 10 | Kshetrimayum et al. (PConvLSTM) | 2024 · *Int. J. Data Sci. Anal.* | Una serie "load"; por la magnitud de los errores, probablemente el total | 1 h, un paso (ventana de 24 h) | Origen móvil, 4 pliegues | No | MAPE 2.49 %, MAE 1,737, R² 0.976 | **Sí**: persistencia, con MAPE 6.60 % | TC del preprint |
| 11 | Chang y Ke | 2024 · *IEEE Access* | Sumas de zonas (4 combinaciones) | "Día siguiente" con datos horarios y ventana de 24; no precisa si es un paso o 24 | No se indica | No (univariante) | MAPE mínimo 1.87 %, R² 0.978-0.985; RMSE de 8,346 "kW" sobre sumas horarias de valores de 10 min | No | TC (HTML) |
| 12 | Alsalem | 2025 · *Scientific Reports* | Z3 | 10 min, un paso (3 rezagos) | 70/30; no dice el orden | Leve: el clima del instante objetivo; no queda claro si entran las otras zonas | MLP con FCM: RMSE 355, MAE 246, R² 0.989 | No | TC |
| 13 | Satan et al. | 2025 · *Energy Informatics* | No consta | Perfil del día siguiente (método pensado para Astana) | No se describe para Tetuán | No determinable | "Mediana de RMSE" de 5,168, en "MWh", frente a 5,876 de Salam y El Hibaoui (2021) | No | TC (Tetuán solo como comparación) |
| 14 | Qi et al. (SFPFMformer) | 2025 · *Mathematics* | Z1, solo diciembre | Varios pasos: 4 h y 24 h | Cronológica 80/20 dentro de diciembre; prueba del 24 al 30 | No | A 4 h, MAPE 2.63 % y RMSE 1,129; a 24 h, MAPE 2.97 % | No | TC |
| 15 | Sarwoko et al. | 2025 · ETASR | Total | 10 min, un paso (ventana de 12) | Cronológica: prueba en el último 20 % | No (salvo un escalado sobre todo el conjunto) | LSTM con K-means: RMSE 721.7, MAE 493.7, R² 0.997 | No | TC |
| 16 | Rizki et al. (MP-RWKV) | 2025 · *Eng. Proc.* (actas MDPI) | Z3; Z1, Z2 y el clima como entradas | Varios pasos; las filas 24-120 se rotulan como horas | No se indica | No (ventanas pasadas) | MSE y MAE normalizados; las líneas base son idénticas a la tabla 5 de Wang et al. (2023) | No | TC |
| 17 | Abdillahi y Etem | 2025 · AJEAS | Cada zona | No se declara | 80/20 tras normalizar; no dice el orden | No determinable | Stacking: R² 0.981, 0.981 y 0.991; los descriptivos no coinciden con el dataset | No | TC |
| 18 | Talib et al. | 2025 · JISIS | Cada zona | 10 min | Secuencial | Posible: las 29 variables incluyen el consumo de las tres zonas | MAE 0.159 y R² 0.956, normalizados | No | TC (lectura parcial) |
| 19 | Sadik et al. | 2026 · *Eng. Proc.* (actas MDPI) | Z2 como caso principal; también Z1 y Z3 | No se declara; la ventana de 144 pasos sugiere un paso de 10 min | Cronológica 80/20 | Leve: el residuo se corrige con clima y calendario | MAPE 1.68 % (Z1), 2.41 % (Z2) y 6.65 % (Z3); R² 0.93-0.99 | No | TC |
| 20 | Rizki et al. (RWKV-CVM) | 2026 · *Electricity* | Las tres en conjunto | 4, 8, 24, 48 y 72 h (entrada de 48 h) | Cronológica 70/10/20, sin ventanas que crucen los cortes | No (lo verifica) | MSE normalizado; ventajas pequeñas y no en todos los horizontes | No (sí re-ejecuta DLinear, iTransformer y RWKV-TS) | TC |
| 21 | Tibermacine et al. | 2026 · *Front. Energy Res.* | Las tres zonas, como clientes federados | 1 h, un paso (ventana de 24 h) | Cronológica 70/15/15 | No | R² 0.91-0.95; MAE y RMSE normalizados | No | TC |
| 22 | Neupane et al. | 2026 · arXiv (preprint) | Cada zona | Ninguno: mismo instante, datos horarios | Cronológica 80/20 | **Sí**: hora, día, mes y clima, sin rezagos | NGBoost: MAE de 1,683, 1,400 y 1,266 kW | No | TC |
| 23 | Roshif et al. | 2026 · *Sci. J. Informatics* | Cada zona; escenarios que entrenan con varias zonas | 10 min, un paso (ventana de 24) | Cronológica 80/20 | No aparente | Z1: MAE 257 y MAPE 0.82 %; su LSTM de base tiene un MAPE de 11.85 % | No | TC |
| 24 | Almesmari et al. | 2026 · JAIT | Total | 10 min y horario | Cronológica | **Sospecha**: un MAPE de 0.30 % a 10 min, unas cuatro veces menor que la persistencia | ExtraTrees: MAE ≈ 202, R² 0.9996, MAPE 0.30 % | No | TC |
| 25 | Islam et al. | 2025 · *Quality & Quantity* | Las tres, por nombre, y su promedio | 10 min y 1 h | No consta | Usa rezagos | Dice mejorar el MAPE y el R² frente al "enfoque tradicional" | No consta | R |
| 26 | Fan et al. | 2025 · *Cognitive Computation* | Tetuán; por la magnitud de los errores, probablemente el total | No consta | Por temporada y tipo de día | No consta | En días de descanso, MAPE 1.03 % y MAE 733 kW | No consta | R |
| 27 | Biswas et al. | 2026 · *Results in Engineering* | Zonas por nombre ("Boussafou"), el total y la media | 10 min y 1 h | No consta | Clima y calendario | TSMixer: MAPE 5.66 % (Boussafou, 10 min); TiDE: 1.92 % (combinado, 10 min); RF: 1.04 % (horario) | No consta | R |
| 28 | Bensalah y Haïr | 2024 · IRASET (congreso IEEE) | No consta | No consta | Entrenamiento y validación | No determinable | MAE, RMSE, MAPE y R², sin cifras en el resumen | No consta | R |
| 29 | Boriratrit y Chatthaworn | 2023 · ICACI (congreso IEEE) | No consta | No consta | No consta | Posible: descomposición CEEMDAN | R² de hasta 0.9999 | No consta | R |
| 30 | Santhi y Meiliana | 2025 · ISRITI (congreso IEEE) | No consta | No consta | No consta | No determinable | LSTM con atención: MAPE 0.68 y MAE 428 | No consta | R |

Notas a la tabla:

- **3.** La versión publicada en *Energy Reports* no fue accesible. Los datos salen del preprint de los mismos
  autores (arXiv:2305.16546), que describe el mismo diseño.
- **6.** La "Zona" combina la suma de las tres con una variable: el consumo agregado de la hora anterior.
- **13.** No describe cómo aplicó su método a Tetuán: compara su RMSE con el que reporta otro artículo.
- **16.** Las cifras de Informer, Autoformer, Transformer, Reformer y LSTM coinciden dígito a dígito con la
  tabla 5 de Wang et al. (2023), donde las filas 24-120 son pasos de 10 minutos (4-20 h), no horas.
- **17.** Los descriptivos del artículo (Zona 1 de 200 a 18,500 kW, media ≈ 8,200; viento de 0 a 9.8 m/s) no
  coinciden con el dataset: la Zona 1 tiene una media de 32,345 kW y el viento llega como máximo a 6.48. Además,
  habla de unas 52,560 observaciones (son 52,416), elimina como atípicos los valores fuera de los percentiles 1 y
  99 (lo que borra parte de los picos reales), normaliza antes de partir y presenta el R² como "accuracy" (§3-4,
  pp. 7-8).
- **24.** El objetivo es la suma de las tres zonas, y la tabla de variables lista las zonas junto a las
  predictoras. No se puede descartar una fuga.
- **29.** Si la descomposición se aplicó a toda la serie antes de partir los datos, hay fuga. Solo con el
  resumen no se puede confirmar.

### 2.2 Otras obras que usan el dataset (tabla secundaria)

Usan el dataset según el resumen, el título o el texto completo, pero no se pudo extraer el diseño completo, o
su tarea no es pronosticar el consumo.

| Referencia | Año · revista | Uso | Acceso |
|---|---|---|---|
| Nassreddine et al. | 2025 · *Smart Energy Syst. Res.* | SVR y LSTM con selección de variables por MLR; 1 h y pico/valle del día siguiente; 80/20. Describe que el viento toma dos valores (§4.2, p. 7) | TC (lectura parcial) |
| Cao y Li | 2026 · *J. Power Technologies* | Red de estado de eco con selección de variables por recurrencia; tres zonas en verano; usa los nombres de las subestaciones (índice de texto completo) | R |
| Ni et al. | 2026 · *Electr. Power Syst. Res.* | PWTC-iPAPT, comparado con iTransformer; MSE, MAE y MAPE | R |
| Li et al. | 2026 · *IEEE Trans. Sustain. Comput.* | TSD-Net con datos de Shanghái, Australia y Tetuán | R |
| Iqbal et al. | 2025 · *Int. J. Energy Res.* | SALF, con predicciones a nivel de minuto; nombra a Boussafou (índice de texto completo) | R |
| Xi et al. | 2025 · *Internet Technol. Lett.* | Aprendizaje federado; nombra a Quads y Smir (índice de texto completo) | R |
| Muna et al. | 2026 · *Results in Engineering* | LSTM con 9 datasets, entre ellos Tetuán; partición 80-90 % | R |
| Benhayoun-Sadafiyine y Lakouismi | 2025 · ICTMOD; 2026 · *Procedia CS* | MLR, SVM, XGBoost, ARIMA y SARIMA; XGBoost, el mejor (RMSE, MAE, R²) | R |
| Hambali et al. | 2024 · capítulo, CRC Press | Comparación de algoritmos; el título y la descripción replican los del artículo original | R |
| Mohammd | 2025 · BAJEST | CNN, LSTM, BiLSTM e híbrido | R |
| Nandan y Musti | 2023 · capítulo, IGI Global | *Gradient boosting* a 10 minutos | R |
| Dos Santos | 2026 · Zenodo | RF, GB, LR y SVR con tres datasets | R |
| AlAssaf y Khan | 2026 · *J. Inf. Knowl. Manag.* | *Boosting* con rezagos y clima, dentro de un marco operativo | R |
| Prameswari et al. | 2026 · (DOAJ) | SVR multiobjetivo con PSO; RMSE de 34,769.5 en Z1 horario | R |
| Wahyusari; Wahyusari et al. | 2024 · SNAST; 2025 · AVITEC; 2025 · JUTIF | KNN, SVR, RF y CatBoost; particiones 90:10, 80:20 y 50:50 sin orden declarado | R y TC (AVITEC) |
| Bunke y Grudzynskyi | 2026 · *Visnyk SNU* | Datos horarios; Ridge y HistGB con RMSE ≈ 900, R² > 0.977 y MAPE ≈ 2.2 % | R |
| Eid | 2025 · *Fusion Pract. Appl.* | Optimización *greylag goose* (solo el título) | Metadatos |
| Mewada y Sundar | 2025 · ISNCC | CNN-RNN con R² 0.997 | R |
| Djenga et al. | 2026 · *Procedia CS* | ELM inspirada en computación cuántica con tres datasets | R |
| Od et al.; Pathak et al. | 2026 · arXiv | Computación de reservorio cuántica | TC |
| Landers | 2026 · arXiv | Riesgo de un predictor congelado ante la deriva de las covariables | TC |
| Zhao et al. | 2024 · *Cluster Computing* | KNN con optimización bayesiana; 75 % de entrenamiento; enfoque de clasificación | TC del preprint |
| Fan et al. | 2025 · *Physica Scripta* | ISSA-TCN con "tres ciudades"; los mismos autores usan Tetuán en Fan et al. (2025, *Cognitive Computation*) | R (uso probable) |
| Khashei et al. | 2023 · *Energy Reports* | Clasificación del consumo con aprendizaje profundo discreto | R |
| Kahil et al.; Hrimech y Mahmud; Tan et al. | 2025 · *Statistics*; 2024 · LNEE; 2024 · IMCEC | Detección de anomalías | R / metadatos |
| Dixit et al. | 2025 · *Stat* | Intervalos de predicción con transferencia (Bayes empírico) | R |
| Ma | 2023 · arXiv | Rezagos clima → consumo con entropía de transferencia; nombra las tres redes | TC |
| Pramesti et al. | 2026 · TESEA | Proceso de Ornstein-Uhlenbeck estacional por subestación, con nombres; 90 % de entrenamiento | TC |
| Parhusip et al. | 2026 · JITET | Reglas de asociación (Apriori) | R |
| Chakrabarty | 2026 · Figshare | Subconjunto del total, sin filas del mismo día, para regresión gaussiana no estacionaria | R |
| M. A. et al.; Kommineni et al.; Siranjeevi | 2025 · ICEES; 2024 · ICSPCRE; 2025 · ICECST | El resumen habla de "Zone 1, 2 y 3", pero no nombra Tetuán | R (uso probable) |

**Uso no confirmado.** Citan el artículo original, pero ni el resumen ni el índice de texto completo confirman
que usen el dataset: Zhou et al. (2024, *Expert Syst. Appl.*, 13 citas), Ji et al. (2025, *Knowl.-Based Syst.*),
Lucas y Portillo (2024, *Neural Networks*), Hu et al. (2026, *Sci. Rep.*), Fang et al. (2026), Bai et al. (2025),
Guha et al. (2025, *IEEE Access*), Olawuyi et al. (2023), Vyshnevskyy y Zhuravchak (2024a, 2024b), Arı y
Burukanlı (2025), Manohar et al. (2025), Rawat y Premraj (2023) y Tan et al. (2023).

## 3. Errores frecuentes y qué tan comparables son los resultados

### 3.1 Referencias ingenuas calculadas sobre el CSV de UCI

| Referencia (partición) | Z1 | Z2 | Z3 | Total |
|---|---:|---:|---:|---:|
| Persistencia 10 min, último 20 % · MAPE | 1.27 % | 1.34 % | 1.72 % | 1.23 % |
| Persistencia 10 min, último 20 % · R² | 0.992 | 0.993 | 0.989 | 0.993 |
| Persistencia 1 h (t+6), último 20 % · MAPE | 6.31 % | 6.74 % | 8.01 % | 6.46 % |
| Persistencia 1 h (t+6), último 20 % · R² | 0.83 | 0.85 | 0.80 | 0.82 |
| Persistencia 60 min, feb-dic · MAE (kW) | 2,180 | 1,440 | 1,401 | — |
| Medias horarias, último 20 %, persistencia · MAPE | 6.05 % | 6.49 % | 7.54 % | 6.22 % |
| Medias horarias, último 20 %, ayer · MAPE | 3.34 % | 5.25 % | 5.35 % | 3.30 % |
| Medias horarias, último 20 %, ayer · MAE (kW) | 968 | 1,156 | 645 | 2,067 |
| Prueba del proyecto (nov-dic, t+6), la mejor ingenua · MAPE | 2.94 % | 4.32 % | 6.00 % | — |

A 10 minutos, la persistencia ya alcanza un R² de 0.99. Un R² de 0.98-0.99 a ese horizonte no prueba nada.

### 3.2 Errores frecuentes, con ejemplos

1. **Estimar el consumo del mismo instante y llamarlo pronóstico.** El modelo estima el consumo de t con el clima
   y el calendario de t. Ejemplos: Al-Jamimi et al. (2023), con año, mes, día, hora y minuto como variables;
   Rose et al. (2023); Neupane et al. (2026); Abdillahi y Etem (2025), aparentemente; y, según la descripción de
   Wei (2023, §III.B, p. 5), la literatura previa a su trabajo. Islam et al. (2025) presentan como novedad usar
   rezagos del consumo, lo que sugiere que muchos trabajos anteriores no los usaban. Cuando se compara contra
   una ingenua, estos modelos pierden: el NGBoost de Neupane et al. tiene un MAE de 1,683, 1,400 y 1,266 kW por
   zona, y "ayer" obtiene 968, 1,156 y 645 kW en el mismo tramo.
2. **Calendario anual con partición aleatoria o sin orden declarado.** Con un solo año, el mes, el día y el día
   del año identifican la época, y una partición aleatoria permite interpolar entre vecinos. Ejemplos:
   Al-Jamimi et al. (2023, 80/20), Rose et al. (2023, 70/30), Alsalem (2025, 70/30), Al-Quraan et al. (2023,
   80/20, con mes y día), Abdillahi y Etem (2025, 80/20) y Wahyusari et al. (2025, 90:10, 80:20 y 50:50).
   Ninguna obra discute que, con un año, el calendario funciona como identificador de época.
3. **Clima o consumo del instante objetivo como predictores.** Alsalem (2025) usa el clima en t junto con los
   rezagos t-1 a t-3; Al-Quraan et al. (2023), el clima de la hora que pronostican; Sadik et al. (2026), el clima y
   el calendario para corregir el residuo. Todos suponen un pronóstico perfecto del clima que el dataset no tiene.
   En Talib et al. (2025), las 29 variables incluyen el consumo de las tres zonas. En Almesmari et al. (2026), el
   objetivo es la suma de las zonas y la tabla de variables las lista junto a las predictoras. Las otras zonas
   llevan mucha información: una regresión lineal sobre una partición aleatoria explica el 81 % de la varianza
   de Z1 solo con Z2 y Z3 del mismo instante (R² 0.81), y el 58 % de la de Z3 con Z1 y Z2. Wang et al. (2023) y
   Rizki et al. (2025, 2026) también usan las otras zonas, pero solo en ventanas pasadas, que es lo correcto.
4. **Horizontes triviales de 10 minutos.** Es el diseño más común: da Silva y Meneses (2023), Alsalem (2025),
   Sarwoko et al. (2025), Roshif et al. (2026), Almesmari et al. (2026), Talib et al. (2025) y, aparentemente,
   Sadik et al. (2026). Algunos ganan a la persistencia por poco: el BLSTM de da Silva y Meneses llega a un MAPE
   de 0.8 %, frente a 1.2-1.8 % de la persistencia en diciembre, y Sarwoko et al. bajan el RMSE de 1,187 a 722.
   Otros probablemente pierden. Si el horizonte de Sadik et al. es de 10 minutos, sus MAPE (1.68 %, 2.41 % y
   6.65 %) superan a la persistencia (1.27 %, 1.34 % y 1.72 %). El TSMixer de Biswas et al. (2026), con 5.66 % a
   10 minutos en una zona, triplica el error de la persistencia, si es un pronóstico de un paso.
5. **Sin referencia ingenua, o solo la más débil.** Solo Al-Quraan et al. (2023) y Kshetrimayum et al. (2024) se
   comparan contra la persistencia, y nadie contra ayer o la semana pasada. La comparación cambia la lectura:
   - FedraTrees baja el MAPE de la persistencia de 6.64 % a 3.69 %, pero "ayer", con medias horarias del total
     en el último 20 %, da 3.30 %. Si su prueba es ese tramo, no le gana a la referencia diaria.
   - El SFPFMformer de Qi et al. (2025) reporta un MAPE de 2.63 % a 4 h y de 2.97 % a 24 h. En su misma semana de
     prueba (24-30 de diciembre, Zona 1), "semana pasada" da 2.05 %.
   - Wei (2023), a 60 minutos, mejora a la persistencia en Z1 (MAE −14 %) y Z2 (−11 %), pero empeora en Z3
     (+44 %). Entrenó solo con enero, así que su modelo no vio los niveles de verano de la zona costera.
6. **R² inflados.** El R² sube con la varianza estacional de la prueba, así que un R² alto no dice nada si no se
   compara con el de una ingenua. Ejemplos: R² de 0.9996 (Almesmari et al., 2026), 0.9999 (Boriratrit y
   Chatthaworn, 2023), 0.998 (da Silva y Meneses, 2023) y 0.989 (Alsalem, 2025), contra 0.989-0.993 de la
   persistencia a 10 minutos.
7. **Métricas solo normalizadas.** Wang et al. (2023), Zhang et al. (2024), Rizki et al. (2025, 2026), Tibermacine
   et al. (2026) y Talib et al. (2025) reportan MSE o MAE sobre datos escalados. No se pueden pasar a kW ni a
   porcentaje, ni compararse entre artículos.
8. **Reproducibilidad e integridad.** MP-RWKV (Rizki et al., 2025) copia las líneas base de otro artículo y rotula
   pasos de 10 minutos como horas. Abdillahi y Etem (2025) reportan descriptivos que no coinciden con el dataset.
   Rose et al. (2023) tienen una fila de la tabla de resultados que no cuadra. Chang y Ke (2024) suman valores de
   10 minutos y reportan el resultado en "kW". Las unidades no coinciden entre artículos: kW (Wang, da Silva, Wei,
   Rizki 2026, Neupane), kWh (Sadik, Nassreddine, Pramesti, Almesmari) y MWh (Satan).

### 3.3 Qué resultados son comparables con los del proyecto

El proyecto pronostica cada zona a una hora (t+6) con información de t, partición cronológica 70/15/15 con hueco,
origen móvil y prueba en noviembre y diciembre, contra la mejor de tres ingenuas.

- **Comparables en diseño, con matices.**
  - Wei (2023): por zona, 60 minutos, cronológica, MAE en kW. Su prueba va de febrero a diciembre y solo entrena
    con enero, así que la comparación tiene que ser contra la mejora sobre la persistencia, no en valores
    absolutos.
  - Tibermacine et al. (2026): por zona, 1 h, cronológica 70/15/15, casi la misma partición del proyecto. Solo
    reporta métricas normalizadas.
  - Zhang et al. (2024): Z1 a 1-4 h, cronológica. Métricas normalizadas.
- **Parcialmente comparables.** Kshetrimayum et al. (2024) y Al-Quraan et al. (2023): una hora y contra la
  persistencia, pero para el total y con medias horarias. Su mejora relativa (−62 % y −44 % de MAPE frente a la
  persistencia) da una idea del orden de magnitud. Qi et al. (2025): Zona 1, cronológica, pero solo diciembre y a
  4 y 24 horas.
- **No comparables.** Las obras a 10 minutos (filas 3, 12, 15, 18, 19, 23 y 24), las que estiman el mismo
  instante (5, 8, 22 y probablemente 17), las de 4 a 72 horas con métricas normalizadas (4, 16 y 20), los
  perfiles del día siguiente (11 y 13) y las que solo tienen resumen.

Recomendación para el paper: reportar el MAE en kW y la mejora relativa frente a cada ingenua (*skill*), por zona.
Es la única forma de que el resultado se pueda comparar con Wei (2023) y con los trabajos que reportan la
persistencia.

### 3.4 ¿Alguien vio la transferencia de octubre, la anomalía del viento o el Ramadán?

- **La transferencia del 25 de octubre: nadie la menciona.** Rizki et al. (2026, §4.1) notan el movimiento
  conjunto de las zonas y que la Zona 1 parece anticipar a la Zona 3; Landers (2026) usa el dataset para estudiar
  la deriva de un predictor congelado. Ninguno identifica el cambio de nivel ni la transferencia entre Z1 y Z2.
  Las obras con partición cronológica y prueba en el último 20 % (desde fines de octubre) evalúan, sin saberlo,
  después del cambio.
- **El viento con dos estados: solo una descripción.** Nassreddine et al. (2025, §4.2, p. 7) anotan que el viento
  solo toma dos valores, sin interpretarlo como un problema del sensor. Las demás obras lo usan como variable
  continua. Wang et al. (2023, tabla 3) le asignan una correlación de 0.28 con la Zona 3, y Wei (2023, tabla II)
  anota que su unidad no está clara. Abdillahi y Etem (2025) reportan un rango de 0 a 9.8 m/s que no existe en los
  datos. Según el CSV de UCI, el 61.2 % de las observaciones está por debajo de 1, el 38.6 % por encima de 4.5 y
  solo el 0.21 % en medio.
- **El Ramadán y los feriados: nadie.** Ningún texto completo revisado menciona el Ramadán, los feriados
  marroquíes ni el calendario hijri. Almesmari et al. (2026) usan feriados, pero solo para su dataset de Panamá.

## 4. Identidad de las zonas

**No hay una fuente primaria accesible.** La ficha de UCI solo habla de "tres redes de distribución". El resumen
del artículo original no nombra las subestaciones. El otro trabajo accesible de los autores del dataset (Salam et
al., 2021, IJECE) no usa estos datos ni nombra las subestaciones ni a Amendis. El texto completo del artículo
original (IRSEC 2018) y el de Salam y El Hibaoui (2021) siguen sin revisar. Los nombres Quads, Smir y Boussafou vienen de la descripción
del dataset en Kaggle (fedesoriano), que se replica en el README de un repositorio de GitHub. Esa descripción
menciona el SCADA de Amendis y los 63 kV y 20 kV, y lista las tres estaciones en el orden "Quads, Smir y
Boussafou", pero no dice qué columna corresponde a cada una.

**Obras que asignan los nombres a las zonas.** Las cinco dan la misma asignación: Z1 = Quads, Z2 = Smir y
Z3 = Boussafou. Ninguna cita una fuente para hacerlo.

| Obra | Dónde | Lo que dice |
|---|---|---|
| Zhang et al. (2024), *Electronics* 13(20), 4080 | §4.1, p. 9 | Cita textual: "The three zones correspond to Quads, Smir, and Boussafou, respectively." También atribuye los datos al SCADA de Amendis. |
| Rizki et al. (2026), *Electricity* 7(2), 58 | §4.1, p. 8 | Pone los nombres con el número de zona entre paréntesis (Quads, Zona 1; Smir, Zona 2; Boussafou, Zona 3) y da los rangos en kW de cada zona. |
| Tibermacine et al. (2026), *Front. Energy Res.* 14 | §3.2, p. 6, y tabla 3, p. 15 | La misma asignación, presentada como tres zonas de distribución con perfiles distintos. |
| Neupane et al. (2026), arXiv:2609.34120 | §III, p. 3 | La misma asignación, como tres estaciones de suministro; atribuye los datos al SCADA de Amendis. |
| Abdillahi y Etem (2025), AJEAS 3(2) | Tabla 2 ("Data description"), p. 7 | Describe las columnas de las zonas 1, 2 y 3 como el consumo de Quads, Smir y Boussafou. En el párrafo anterior de la misma página lista los nombres en otro orden (Boussafou, Quads, Smir) y cita como respaldo la ficha de UCI, que no nombra zonas. Sus descriptivos no coinciden con el dataset. |

Salvo la primera fila, que es una cita textual, las demás son paráfrasis; el texto exacto está en la página o
sección indicada.

**Obras que nombran las subestaciones sin asignarlas:** Wang et al. (2023, §4.1, p. 7), Chang y Ke (2024, §III.A,
que también describe el SCADA y la transformación de 63 a 20 kV y admite que no hay información sobre el tipo de
carga de cada zona),
Rizki et al. (2025, §4.1.1, p. 9), Roshif et al. (2026, p. 5), Pramesti et al. (2026, §3.3, p. 7) y Ma (2023,
§6, p. 7). Otras listan los nombres en otro orden (Quads, Boussafou, Smir): Al-Jamimi et al. (2023, §3, p. 8),
Al-Quraan et al. (2023, §4, p. 5) e Islam et al. (2025, resumen). Biswas et al. (2026) reportan resultados para
"Boussafou" sin que el resumen diga qué columna es.

**Lectura.** La asignación de la literatura sigue el orden en que la descripción de Kaggle lista los nombres, y
no está respaldada. Además, choca con dos cosas: con el mapeo que circula en el artículo de Medium que cita el
proyecto (Z2 = Boussafou, Z3 = Smir), y con la firma de carga de los datos, donde la Zona 3 se comporta como una
zona costera y estacional, coherente con Smir. Conviene seguir hablando de Zona 1, 2 y 3 y declarar la
asignación de la literatura como no verificada.

**Amendis y unidades.** Mencionan a Amendis Zhang et al. (2024), Neupane et al. (2026), Almesmari et al. (2026) y
Pramesti et al. (2026); el índice de texto completo lo muestra también en Hrimech y Mahmud (2024). Usan kW Wang et
al. (2023), da Silva y Meneses (2023), Wei (2023), Rizki et al. (2026) y Neupane et al. (2026), siempre sin citar
una fuente primaria. Chang y Ke (2024) describen las zonas en MW, lo que es coherente con kW. Otros usan kWh
(Sadik et al., 2026; Nassreddine et al., 2025; Pramesti et al., 2026; Almesmari et al., 2026) o MWh (Satan et al.,
2025).

## 5. Posicionamiento propuesto

Para la sección de trabajos relacionados:

> El dataset de Tetuán (Salam y El Hibaoui, 2018) se volvió un banco de pruebas habitual: identificamos más de
> sesenta trabajos entre 2018 y 2026. La mayoría lo usa para proponer arquitecturas nuevas (LSTM, variantes de
> Transformer, híbridos optimizados con metaheurísticas) con tres diseños dominantes. Uno pronostica un paso de
> 10 minutos, donde la persistencia ya alcanza un R² de 0.99 (da Silva y Meneses, 2023; Alsalem, 2025). Otro
> estima el consumo con el clima y el calendario del mismo instante, a menudo con particiones que no se declaran
> cronológicas (Al-Jamimi et al., 2023). El tercero pronostica entre 4 y 72 horas con métricas normalizadas
> (Wang et al., 2023; Rizki et al., 2026). Casi ninguno se compara contra referencias ingenuas: solo Al-Quraan et
> al. (2023) y Kshetrimayum et al. (2024) usan la persistencia, y ninguno el mismo momento de ayer o de la semana
> pasada. El antecedente más cercano a nuestro diseño es Wei (2023), que pronostica cada zona a 60 minutos con
> partición cronológica.
>
> Este trabajo no propone una arquitectura: propone un protocolo de evaluación orientado a la operación. Cada zona
> se pronostica una hora adelante solo con la información disponible en t, con partición cronológica con hueco y
> validación de origen móvil, y el criterio de éxito es superar a la mejor de tres referencias ingenuas
> (persistencia, ayer y semana pasada), reportando el error en kW. Además, documentamos características del
> dataset que la literatura revisada no menciona: una transferencia de carga de la Zona 1 a la Zona 2 el 25 de
> octubre de 2017, que deja la prueba después de un cambio de nivel; una velocidad del viento que solo toma dos
> estados; un aumento del consumo de madrugada en Ramadán, que el calendario gregoriano no captura; y el hecho de
> que, con un solo año, el calendario anual funciona como un identificador de época. Tampoco asumimos la
> identidad de las zonas: la asignación que circula en la literatura no tiene una fuente primaria.

## 6. Limitaciones de esta revisión

- 8 de las 30 obras de la tabla principal se leyeron solo por el resumen. Entre ellas están el artículo original
  (IRSEC 2018) y el de 2021 de los mismos autores (*Math. Comput. Simul.*), que son de acceso cerrado y podrían
  nombrar las zonas. **Pendiente:** revisarlos cuando estén disponibles por la biblioteca y actualizar la
  sección 4.
- Las versiones publicadas de *Energy Reports* (da Silva y Meneses), *Int. J. Data Sci. Anal.* (Kshetrimayum et
  al.) y *Cluster Computing* (Zhao et al.) se revisaron a través de sus preprints.
- Las comparaciones con las referencias ingenuas suponen el horizonte y la partición que cada artículo describe.
  Cuando no los declara, la comparación se marca como condicional.
- La búsqueda depende de la cobertura de OpenAlex. Puede haber obras en repositorios regionales que no aparezcan.

## 7. Bibliografía

Marcas: **[TC]** texto completo leído; **[R]** solo resumen; **[M]** solo metadatos (uso no confirmado). Todos
los DOI se comprobaron contra el registro de DOI (handle.net) el 22-oct-2026; cuando no hay DOI se indica.
Autores, volumen y páginas vienen de OpenAlex y Crossref; las diferencias con el PDF se señalan.

### Dataset y fuentes del dataset

- Salam, A., & El Hibaoui, A. (2018). *Power consumption of Tetouan city* [Dataset]. UCI Machine Learning
  Repository. https://doi.org/10.24432/C5B034 — Verificado: el DOI redirige a la ficha de UCI.
- fedesoriano. (s. f.). *Electric power consumption* [Descripción del dataset]. Kaggle.
  https://www.kaggle.com/datasets/fedesoriano/electric-power-consumption — **No verificado directamente.** El
  texto se verificó en su réplica de GitHub.
- Merci93. (s. f.). *Tetouan_Power_Consumption-SQL_Aanalysis* [README]. GitHub.
  https://github.com/Merci93/Tetouan_Power_Consumption-SQL_Aanalysis — Verificado.
- Waheed, M. (s. f.). *Project overview* [Entrada de blog]. Medium.
  https://medium.com/@mehranwaheed/project-overview-98fe6424f3b9 — **No verificado.** Lo cita la documentación
  del proyecto.

### Obras revisadas

- Abdillahi, M. A., & Etem, T. (2025). Stacked ensemble machine learning model of energy consumption prediction.
  *Alfa Mühendislik ve Uygulamalı Bilimler Dergisi (AJEAS), 3*(2), 1–14. https://doi.org/10.70988/ajeas.1694578 [TC]
- Al-Jamimi, H. A., BinMakhashen, G. M., Worku, M. Y., & Hassan, M. A. E. (2023). Advancements in household load
  forecasting: Deep learning model with hyperparameter optimization. *Electronics, 12*(24), 4909.
  https://doi.org/10.3390/electronics12244909 [TC]
- Al-Quraan, M. M., Khan, A. R., Centeno, A., Zoha, A., Imran, M. A., & Mohjazi, L. (2023). FedraTrees: A novel
  computation-communication efficient federated learning framework investigated in smart grids. *Engineering
  Applications of Artificial Intelligence, 124*, 106654. https://doi.org/10.1016/j.engappai.2023.106654 [TC,
  manuscrito aceptado]
- Al-Quraan, M. M., Khan, A., Centeno, A., Zoha, A., Imran, M. A., & Mohjazi, L. (2022). *FedTrees: A novel
  computation-communication efficient federated learning framework investigated in smart grids* [Preprint].
  arXiv. https://doi.org/10.48550/arXiv.2210.00060 [TC]
- AlAssaf, R. A., & Khan, I. R. (2026). Machine learning-based short-term electricity forecasting within an
  operational and governance framework. *Journal of Information & Knowledge Management, 25*(9).
  https://doi.org/10.1142/S0219649226500437 [R]
- Almesmari, A. R., Al-Betar, M. A., & Makhadmeh, S. N. (2026). Advancing electricity load forecasting using a
  novel enhanced Harris Hawks optimization. *Journal of Advances in Information Technology, 17*(6), 1096–1112.
  https://doi.org/10.12720/jait.17.6.1096-1112 [TC]
- Alsalem, K. O. (2025). A hybrid time series forecasting approach integrating fuzzy clustering and machine
  learning for enhanced power consumption prediction. *Scientific Reports, 15*, 6447.
  https://doi.org/10.1038/s41598-025-91123-8 [TC]
- Arı, D., & Burukanlı, M. (2025). Optimizing accuracy and reliability in power load forecasting using a
  data-driven RF and LSTM hybrid framework. En *International Symposium on Innovative Approaches in Smart
  Technologies (ISAS)* (pp. 1–8). IEEE. https://doi.org/10.1109/ISAS66241.2025.11101732 [M]
- Bai, N., Zhang, J., & Wu, Z. (2025). Multi-task graph attention net for electricity consumption prediction and
  anomaly detection. *Computers, 14*(9), 350. https://doi.org/10.3390/computers14090350 [M]
- Benhayoun-Sadafiyine, L., & Lakouismi, S. (2025). Context-aware forecasting for sustainable energy planning: A
  machine learning framework for emerging economies. En *IEEE International Conference on Technology Management,
  Operations and Decisions (ICTMOD)* (pp. 1–6). IEEE. https://doi.org/10.1109/ICTMOD66732.2025.11371868 [R]
- Benhayoun-Sadafiyine, L., & Lakouismi, S. (2026). Artificial intelligence for energy forecasting in emerging
  economies: A machine learning case study from Morocco. *Procedia Computer Science, 277*, 3390–3399.
  https://doi.org/10.1016/j.procs.2026.02.375 [R]
- Bensalah, M., & Haïr, A. (2024). Empowering smart cities: SARIMA forecasting of power consumption in Tetouan's
  urban grid. En *4th International Conference on Innovative Research in Applied Science, Engineering and
  Technology (IRASET)* (pp. 1–6). IEEE. https://doi.org/10.1109/IRASET60544.2024.10548574 [R]
- Biswas, N., Mahdi, M. A., & Das Gupta, M. (2026). Electricity demand forecasting for Tetouan, Morocco using
  Darts in machine-learning: A comparative study of forecasting models. *Results in Engineering, 30*, 110289.
  https://doi.org/10.1016/j.rineng.2026.110289 [R]
- Boriratrit, S., & Chatthaworn, R. (2023). Improvement of long short-term memory via CEEMDAN and logistic maps
  for the power consumption forecasting. En *International Conference on Advanced Computational Intelligence
  (ICACI)* (pp. 1–7). IEEE. https://doi.org/10.1109/ICACI58115.2023.10146172 [R]
- Bunke, O. S., & Grudzynskyi, Yu. (2026). [Evaluación comparativa de modelos de aprendizaje automático y
  profundo para el pronóstico de corto plazo del consumo eléctrico; título original en ucraniano]. *Visnyk of
  the Volodymyr Dahl East Ukrainian National University, 6*(304), 161–169.
  https://doi.org/10.33216/1998-7927-2026-304-6-161-169 [R]
- Cao, D., & Li, Q. (2026). Dynamic modeling of power consumption in Tetouan City using recurrence techniques.
  *Journal of Power Technologies*. https://papers.itc.pw.edu.pl/index.php/JPT/article/view/1985 [R; sin DOI;
  **volumen y páginas no verificados**; el sitio no respondió]
- Chakrabarty, D. (2026). *Training and test datasets used to perform non-parametric supervised learning with
  Gaussian Process…* [Dataset]. Figshare. https://doi.org/10.6084/m9.figshare.33408538 [R]
- Chang, Z.-H., & Ke, Y.-K. (2024). Cumulative load forecasting in microgrid clusters using enhanced-gated
  recurrent unit model. *IEEE Access, 12*, 197907–197916. https://doi.org/10.1109/ACCESS.2024.3521010 [TC]
- da Silva, D. G., & Meneses, A. A. de M. (2023a). Comparing long short-term memory (LSTM) and bidirectional LSTM
  deep neural networks for power consumption prediction. *Energy Reports, 10*, 3315–3334.
  https://doi.org/10.1016/j.egyr.2023.09.175 [TC del preprint; **versión publicada no consultada**]
- da Silva, D. G., & Meneses, A. A. de M. (2023b). *Preliminary studies: Comparing LSTM and BLSTM deep neural
  networks for power consumption prediction* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2305.16546 [TC]
- Dixit, A., Shen, W., Zhang, M., & Zhang, D. (2025). Prediction interval transfer learning for linear regression
  using an empirical Bayes approach. *Stat, 14*(1). https://doi.org/10.1002/sta4.70036 [R]
- Djenga, G. N., Kambale, W. V., Kambale, É. M., Selemani, J. L., Muhire, J.-P. M., Luo, K., Kasereka, S. K., &
  Kyandoghere, K. (2026). Multidomain time-series forecasting via quantum-inspired extreme learning machines: An
  efficiency-precision study. *Procedia Computer Science, 290*, 633–639. https://doi.org/10.1016/j.procs.2026.08.441 [R]
- Dos Santos, V. (2026). *Modeling and forecasting of energy consumption in urban environments: Exploring the
  potential of machine learning in energy consumption prediction*. Zenodo. https://doi.org/10.5281/zenodo.21114024 [R]
- Eid, M. M. (2025). Optimized time-series forecasting for electricity consumption in Tetouan: A machine learning
  approach with greylag goose optimization. *Fusion: Practice and Applications, 21*(2).
  https://doi.org/10.54216/FPA.210217 [M; solo el título]
- Fan, C., Li, G., Xiao, L., Yi, L., & Nie, S. (2025a). Short-term power load forecasting in city based on
  ISSA-BiTCN-LSTM. *Cognitive Computation, 17*(1). https://doi.org/10.1007/s12559-024-10401-1 [R]
- Fan, C., Li, G., Xiao, L., Yi, L., & Nie, S. (2025b). An ISSA-TCN short-term urban power load forecasting model
  with error factor. *Physica Scripta, 100*(4), 045222. https://doi.org/10.1088/1402-4896/adbb26 [R; uso de Tetuán
  **no confirmado**]
- Fang, X., Ma, T., Lu, K., Wang, F., & Lian, C. (2026). Multivariate time series forecasting with multi-view
  hierarchical patching and lag-coupled channel attention. *Frontiers in Applied Mathematics and Statistics, 12*.
  https://doi.org/10.3389/fams.2026.1825555 [M]
- Guha, S., Katyayanan, S., Mallya, G., & Panicker, R. O. (2025). Hybrid vector auto regression and tree-based
  ensembles for energy load forecasting: A case study. *IEEE Access, 13*, 151773–151787.
  https://doi.org/10.1109/ACCESS.2025.3603620 [M]
- Hambali, M. A., Wreford, A. I., & Olasupo, Y. A. (2024). Comparative analysis of machine learning algorithms for
  the power consumption prediction. En [libro editado] (pp. 13–36). CRC Press.
  https://doi.org/10.1201/9781003503057-2 [R; **título del libro no verificado**]
- Hrimech, A., & Mahmud, J. S. (2024). Anomaly detection in power consumption: A comprehensive multi-technique
  approach. En *Proceedings of International Conference on Recent Innovations in Computing* (Lecture Notes in
  Electrical Engineering, pp. 71–84). Springer. https://doi.org/10.1007/978-981-97-3442-9_5 [M]
- Hu, Z., Jia, Z., Wu, L., He, C., Fan, H., & Meng, J. (2026). TACDformer: An improved informer-based model for
  accurate multivariate long-term time series forecasting. *Scientific Reports, 16*.
  https://doi.org/10.1038/s41598-026-46529-3 [M]
- Iqbal, M. S., Adnan, M., Akbar, M. A., & Bermak, A. (2025). SALF: A self-adaptive learning framework for
  short-term load forecasting in smart grid. *International Journal of Energy Research, 2025*(1).
  https://doi.org/10.1155/er/6343205 [R]
- Islam, M. T., Turja, S. A., Islam, M. S., Rahman, M. M., & Habib, A. (2025). Forecasting Tetouan energy demand
  employing shift approach in machine-learning: Complementing econometric insights. *Quality & Quantity, 59*(2),
  1833–1860. https://doi.org/10.1007/s11135-024-02043-0 [R]
- Ji, Y., Zhu, Y., Lu, S., Yang, L., & Liew, A. W.-C. (2025). WTC-iPST: A deep learning framework for short-term
  electric load forecasting with multi-scale feature extraction. *Knowledge-Based Systems, 324*, 113907.
  https://doi.org/10.1016/j.knosys.2025.113907 [M]
- Kahil, S., Jellouli, O., & Fihri, M. (2025). Hybrid clustering and extreme value theory for anomaly detection in
  electricity consumption: A case study on Tetouan's grid. *Statistics, 60*(2), 340–381.
  https://doi.org/10.1080/02331888.2025.2571861 [R]
- Khashei, M., Chahkoutahi, F., & Bakhtiarvand, N. (2023). A novel discrete deep learning-based intelligent
  methodology for energy consumption classification. *Energy Reports, 9*, 4861–4871.
  https://doi.org/10.1016/j.egyr.2023.04.006 [R]
- Kommineni, S., Muddana, S., & Senapati, R. (2024). Impact of temperature on power consumption: A machine
  learning approach. En *IEEE International Conference on Smart Power Control and Renewable Energy (ICSPCRE)*
  (pp. 1–6). IEEE. https://doi.org/10.1109/ICSPCRE62303.2024.10675226 [R; uso probable]
- Kshetrimayum, N., Singh, K. R., & Hoque, N. (2024). PConvLSTM: An effective parallel ConvLSTM-based model for
  short-term electricity load forecasting. *International Journal of Data Science and Analytics, 20*(3),
  2493–2510. https://doi.org/10.1007/s41060-024-00616-8 [TC del preprint en Research Square]
- Landers, J. R. (2026). *Jacobian-velocity bounds for deployment risk under covariate drift* [Preprint]. arXiv.
  https://doi.org/10.48550/arXiv.2605.04932 [TC]
- Li, Z., Wang, X., Gu, J., Cheng, H., Zhu, Y., Cao, K., & Wu, H. (2026). A novel two-stage forecasting framework
  with difference-based learning for power load forecasting. *IEEE Transactions on Sustainable Computing, 11*(5),
  476–488. https://doi.org/10.1109/TSUSC.2026.3720821 [R]
- Lucas, S., & Portillo, E. (2024). Methodology based on spiking neural networks for univariate time-series
  forecasting. *Neural Networks, 173*, 106171. https://doi.org/10.1016/j.neunet.2024.106171 [M]
- M. A., Nivedhitha, G., Karthikeyan, P., & Venkateshkumar, M. (2025). Forecasting of city power consumption for
  efficient energy management – smart city. En *International Conference on Electrical Energy Systems (ICEES)*
  (pp. 391–396). IEEE. https://doi.org/10.1109/ICEES67011.2025.11213429 [R; uso probable; **el nombre del primer
  autor está incompleto en la fuente**]
- Ma, J. (2023). *Identifying time lag in dynamical systems with copula entropy based transfer entropy*
  [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2301.06037 [TC]
- Manohar, V. J., Murthy, G., Royal, N. P., Binu, B., & Patil, T. (2025). Comprehensive analysis of energy demand
  prediction using advanced machine learning techniques. *E3S Web of Conferences, 616*, 02027.
  https://doi.org/10.1051/e3sconf/202561602027 [M]
- Mewada, H. K., & Sundar, L. S. (2025). Hybrid deep convolution network for fast and accurate power consumption
  forecasting. En *International Symposium on Networks, Computers and Communications (ISNCC)* (pp. 1–6). IEEE.
  https://doi.org/10.1109/ISNCC66965.2025.11250477 [R]
- Mohammd, N. (2025). An effective prediction of power consumption using deep learning models. *Bilad
  Alrafidain Journal for Engineering Science and Technology, 4*(2), 28–35. https://doi.org/10.56990/bajest/2025.040203 [R]
- Muna, M. F., Malik, A. I., & Syed, M. N. (2026). Dynamic characteristics of renewable energy generation and
  consumption using LSTM deep learning algorithm. *Results in Engineering, 30*, 109942.
  https://doi.org/10.1016/j.rineng.2026.109942 [R]
- Nandan, M., & Musti, K. S. S. (2023). Machine learning-based load forecast for energy markets. En [libro
  editado, serie *Practice, Progress, and Proficiency in Sustainability*] (pp. 147–169). IGI Global.
  https://doi.org/10.4018/978-1-6684-9130-0.ch007 [R; **título del libro no verificado**]
- Nassreddine, G., Hellany, A., Al-Khatib, O., Rammal, A., & Nassereddine, M. (2025). Feature selection technique
  using multiple linear regression for accurate electricity demand forecasting. *Smart Energy System Research,
  1*(1), 10003. https://doi.org/10.70322/sesr.2025.10003 [TC]
- Neupane, M., Dhungana, P., Khatri, P., Baskota, S., & Dhungana, H. (2026). *Probabilistic electrical power demand
  forecasting with uncertainty quantification* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2609.34120 [TC]
- Ni, J., Zhang, M., Wang, Z., & Lian, X. (2026). PWTC-iPAPT: A physics-aware deep learning framework for
  short-term electric load forecasting with multi-scale feature extraction. *Electric Power Systems Research,
  264*, 113886. https://doi.org/10.1016/j.epsr.2026.113886 [R]
- Od, M., Pathak, P., Innan, N., & Shafique, M. (2026). *Quantum reservoir computing for short-term power load
  forecasting in resource-constrained energy systems* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2606.12806 [TC]
- Olawuyi, A. A., Ajewole, T. O., Lawal, M. O., & Awofolaju, T. T. (2023). Enhancing load prediction accuracy using
  optimized support vector regression models. *Journal of Digital Food, Energy & Water Systems, 4*(2).
  https://doi.org/10.36615/digital_food_energy_water_systems.v4i2.2847 [M]
- Parhusip, J., Sriyanto, N. I., Pratama, T., Mavanudin, Z. C., & Augustin, D. S. (2026). Analisis pola konsumsi
  energi bangunan berdasarkan data sensor lingkungan berbasis algoritma Apriori. *Jurnal Informatika dan Teknik
  Elektro Terapan, 14*(1). https://doi.org/10.23960/jitet.v14i1.8524 [R]
- Pathak, P., Od, M., Innan, N., & Shafique, M. (2026). *Late breaking results: Hardware-efficient quantum reservoir
  computing via quantized readout* [Preprint]. arXiv. https://doi.org/10.48550/arXiv.2604.06075 [TC]
- Pramesti, G., Triyanto, Wiraya, A., Fitriana, L., & Pambudi, D. (2026). Signal processing of stochastic forecast:
  Seasonal electric power consumption in the scope of efficiency connected to renewable energy. *Transactions on
  Energy Systems and Engineering Applications, 7*(1), 1–14. https://doi.org/10.32397/tesea.vol7.n1.699 [TC; el PDF
  imprime "6(2): 699" y otro DOI que no resuelve; se usa el DOI registrado]
- Prameswari, M., Pandiya, R., & Putri, A. L. R. (2026). Hyperparameter optimization of multi-target support vector
  regression with sigmoid particle swarm optimization-based acceleration coefficients for electricity consumption
  prediction. https://doaj.org/article/3aa080bacd514347a202dc0fd2ae0338 [R; sin DOI; **revista no verificada**]
- Qi, C., Feng, Y., Wan, J., Mao, X., & Yuan, P. (2025). SFPFMformer: Short-term power load forecasting for proxy
  electricity purchase based on feature optimization and multiscale decomposition. *Mathematics, 13*(10), 1584.
  https://doi.org/10.3390/math13101584 [TC]
- Rawat, D. S., & Premraj, D. M. (2023). Predicting power consumption using tree-based model. En *Proceedings of the
  International Conference on Intelligent Computing, Communication and Information Security* (Algorithms for
  Intelligent Systems, pp. 195–211). Springer. https://doi.org/10.1007/978-981-99-1373-2_15 [M]
- Rizki, A., Touil, A., Echchatbi, A., & Ahlaqqach, M. (2025). A parallel processing architecture for long-term power
  load forecasting. *Engineering Proceedings, 97*(1), 26. https://doi.org/10.3390/engproc2025097026 [TC]
- Rizki, A., Echchatbi, A., & Yantour, H. (2026). RWKV-CVM: Gated cross-variate mixing for multivariate power load
  forecasting. *Electricity, 7*(2), 58. https://doi.org/10.3390/electricity7020058 [TC]
- Rose, N., Osbourne, O., Williams, N., & Rizvi, S. S. H. (2023). A novel optimized variant of machine learning
  algorithm for accurate energy demand prediction for Tetouan City, Morocco. En *Proceedings of the International
  e-Conference on Advances in Computer Engineering and Communication Systems (ICACECS 2023)* (Atlantis Highlights
  in Computer Sciences, pp. 62–73). Atlantis Press. https://doi.org/10.2991/978-94-6463-314-6_7 [TC]
- Roshif, A. F. Z., Nurhayati, O. D., & Nugraheni, D. M. K. (2026). Hybrid CNN–LSTM–Transformer for electrical
  energy consumption forecasting: A multi-scenario evaluation. *Scientific Journal of Informatics, 13*(2),
  295–312. https://doi.org/10.15294/sji.v13i2.44973 [TC]
- Sadik, Y., Nejmi, A., Oumiguil, L., & Baite, M. (2026). Forecasting energy consumption using a hybrid LSTM-XGBoost
  model. *Engineering Proceedings, 144*(1), 4. https://doi.org/10.3390/engproc2026144004 [TC]
- Salam, A., & El Hibaoui, A. (2018). Comparison of machine learning algorithms for the power consumption
  prediction: Case study of Tetouan city. En *6th International Renewable and Sustainable Energy Conference
  (IRSEC)* (pp. 1–5). IEEE. https://doi.org/10.1109/IRSEC.2018.8703007 [R]
- Salam, A., El Hibaoui, A., & Saif, A. (2021). A comparison of activation functions in multilayer neural network
  for predicting the production and consumption of electricity power. *International Journal of Electrical and
  Computer Engineering (IJECE), 11*(1), 163–170. https://doi.org/10.11591/ijece.v11i1.pp163-170 [TC; no usa el
  dataset de Tetuán; OpenAlex lo fecha en 2020 y Crossref en febrero de 2021]
- Salam, A., & El Hibaoui, A. (2021). Energy consumption prediction model with deep inception residual network
  inspiration and LSTM. *Mathematics and Computers in Simulation, 190*, 97–109.
  https://doi.org/10.1016/j.matcom.2021.05.006 [R]
- Santhi, N. M. R. N., & Meiliana. (2025). Evaluation of GMM clustering augmentation and attention mechanism
  integration in LSTM for electricity consumption forecasting. En *International Seminar on Research of
  Information Technology and Intelligent Systems (ISRITI)* (pp. 606–611). IEEE.
  https://doi.org/10.1109/ISRITI68345.2025.11393110 [R]
- Sarwoko, E. A., Vianita, E., & Wibowo, A. (2025). Evaluating the integration of fuzzy and non-fuzzy clustering
  approaches into LSTM for the power consumption forecasting utilizing the case study dataset of Tetuan City.
  *Engineering, Technology & Applied Science Research, 15*(5), 26689–26696. https://doi.org/10.48084/etasr.11938 [TC]
- Satan, A., Zhakiyev, N., Nugumanova, A., & Friedrich, D. (2025). Hybrid feature-based neural network regression
  method for load profiles forecasting. *Energy Informatics, 8*, 19. https://doi.org/10.1186/s42162-025-00481-0 [TC]
- Siranjeevi, R. (2025). Hybrid machine learning models for power consumption prediction and analysis. En *2nd
  International Conference on Electronic Circuits and Signaling Technologies (ICECST)* (pp. 130–136). IEEE.
  https://doi.org/10.1109/ICECST66106.2025.11307517 [R; uso probable]
- Talib, Z., Abdul-Rahaim, L. A., & Aljuboury, A. S. (2025). Modified CNN learning model for Tetouan City energy
  consumption prediction. *Journal of Internet Services and Information Security, 15*(3), 465–479.
  https://doi.org/10.58346/JISIS.2025.I3.032 [TC]
- Tan, Y.-F., Zhao, G.-Z., Cheeng, T.-H., Ooi, C.-P., Tan, W.-H., & Cheong, S.-N. (2023). Supervised machine learning
  techniques for power consumption usage level prediction. En *International Conference on Software Engineering
  and Computer Science (CSECS)* (pp. 1–5). IEEE. https://doi.org/10.1109/CSECS60003.2023.10428312 [M]
- Tan, Y.-F., Zhao, G.-Z., Ooi, C.-P., & Tan, W.-H. (2024). Leveraging interquartile range and isolation forest for
  abnormal power consumption prediction. En *IEEE Advanced Information Management, Communicates, Electronic and
  Automation Control Conference (IMCEC)* (pp. 815–819). IEEE. https://doi.org/10.1109/IMCEC59810.2024.10575711 [M]
- Tibermacine, A., Naidji, I., Tibermacine, I. E., Sahraoui, S., Zouai, M., Rabehi, A., & Habib, M. (2026).
  Privacy-preserving load forecasting in smart grids using federated learning: A comparative analysis of
  aggregation strategies. *Frontiers in Energy Research, 14*, 1854654. https://doi.org/10.3389/fenrg.2026.1854654 [TC]
- Vyshnevskyy, O., & Zhuravchak, L. (2024a). Forecasting the electricity consumption using an ensemble of machine
  learning models. *Ukrainian Journal of Information Technology, 6*(2), 20–29. https://doi.org/10.23939/ujit2024.02.020 [M]
- Vyshnevskyy, O., & Zhuravchak, L. (2024b). Forecasting the electricity consumption for energy management software
  using an ensemble model. En *IEEE 19th International Conference on Computer Science and Information Technologies
  (CSIT)* (pp. 1–5). IEEE. https://doi.org/10.1109/CSIT65290.2024.10982553 [M]
- Wahyusari, R. (2024). Perbandingan k-nearest neighbors (KNN) dan support vector regression (SVR) untuk prediksi
  konsumsi energi listrik. *Prosiding SNAST*, G44–G50. https://doi.org/10.34151/prosidingsnast.v1i1.5034 [R]
- Wahyusari, R., Sunardi, S., & Fadlil, A. (2025a). Comparison of machine learning methods for predicting electrical
  energy consumption. *AVITEC, 7*(1), 11. https://doi.org/10.28989/avitec.v7i1.2722 [TC]
- Wahyusari, R., Sunardi, S., & Fadlil, A. (2025b). Comparative analysis of ant lion optimization and Jaya algorithm
  for feature selection in k-nearest neighbor (KNN) based electricity consumption prediction. *Jurnal Teknik
  Informatika (JUTIF), 6*(3), 1373–1388. https://doi.org/10.52436/1.jutif.2025.6.3.4692 [R]
- Wang, K., Zhang, J., Li, X., & Zhang, Y. (2023). Long-term power load forecasting using LSTM-Informer with ensemble
  learning. *Electronics, 12*(10), 2175. https://doi.org/10.3390/electronics12102175 [TC]
- Wei, H.-L. (2023). System identification-informed transparent and explainable machine learning with application
  to power consumption forecasting. En *International Conference on Electrical, Computer, Communications and
  Mechatronics Engineering (ICECCME)* (pp. 1–6). IEEE. https://doi.org/10.1109/ICECCME57830.2023.10252535 [TC,
  manuscrito aceptado; la paginación citada es la del manuscrito]
- Xi, B., Jin, H., Li, K., & Kui, F. (2025). IoT-enabled electric load prediction via federated label distribution
  learning. *Internet Technology Letters, 9*(1). https://doi.org/10.1002/itl2.70177 [M; el índice de texto completo
  confirma el uso]
- Zhang, W., Liu, J., Deng, W., Tang, S., Yang, F., Han, Y., Liu, M., & Wan, R. (2024). AMTCN: An attention-based
  multivariate temporal convolutional network for electricity consumption prediction. *Electronics, 13*(20), 4080.
  https://doi.org/10.3390/electronics13204080 [TC]
- Zhao, W., Hu, Y.-C., Yan, X., Liu, X., Ding, R., Dai, C., & Cao, Y. S. (2024). Enhanced K-NN with Bayesian
  optimization algorithm for predicting energy efficiency of smart grids in IoT. *Cluster Computing, 27*(9),
  12311–12322. https://doi.org/10.1007/s10586-024-04480-w [TC del preprint]
- Zhou, J., Wang, Q., Khajavi, H., & Rastgoo, A. (2024). Sensitivity analysis and comparative assessment of novel
  hybridized boosting method for forecasting the power consumption. *Expert Systems with Applications, 249*,
  123631. https://doi.org/10.1016/j.eswa.2024.123631 [M]

Nota: la obra de *Quality & Quantity* a veces se cita como "Habib et al. (2025)". Según OpenAlex y Crossref,
el primer autor es M. T. Islam y A. Habib es el último; la cita correcta es Islam et al. (2025).
