# El producto final: qué falta para que la app sea una herramienta de operación

Lluvia de ideas y priorización para cerrar el TB1 con un producto, no solo con un modelo. Parte de lo que ya existe
(la app rediseñada del PR #31, el notebook 04 del PR #32 y el selector de modelo en preparación) y de cómo son los
productos de pronóstico de corto plazo que usan los operadores. Fecha: 13 de noviembre de 2026.

**En corto.** Para la entrega, cinco cosas en un día de trabajo: el modelo combinado por defecto con su ficha a la
vista, el seguimiento del error y de la cobertura en 2026, el pico y la rampa de las próximas 24 h, los intervalos de
la combinación y una demo pública que no dependa de la suerte. Lo demás (datos al día, comparación con el COES,
sesiones con personas) queda para la siguiente iteración, y hay una lista de lo que no conviene hacer.

## 1. La visión en una frase

> Una pantalla que le dice al operador del COES cuánta demanda viene en cada área en la próxima hora y mañana a esta
> hora, con su margen, cuándo desconfiar del número y qué modelo lo dio, y que cualquiera puede rehacer desde el repo.

## 2. Usuarios y trabajos por hacer

| Usuario | Cuando… | quiere… | para… |
|---|---|---|---|
| **Coordinador de tiempo real del COES** | falta una hora para la subida de la noche | cuánto pedirá cada área, con su rango, y si viene una rampa fuerte | decidir si arranca una unidad rápida, mueve reserva o prepara una maniobra entre áreas |
| **Programador del día siguiente** | arma el programa de mañana | el perfil de 24 h por área con su banda, el pico y la hora del pico | comprometer unidades y reserva sin quedarse corto (subestimar cuesta más) |
| **Analista de estudios del COES** | revisa cada semana cómo va el pronóstico | el error en el tiempo frente a la referencia simple y si el rango sigue cubriendo lo que dice | decidir si sigue con el modelo, lo reentrena o cambia de modelo |
| **Evaluadora académica** | tiene 3 minutos de demo en un proyector | qué pronostica, qué tan bien, qué ganó el modelo nuevo y por qué creerle | calificar el despliegue (fase 6 de CRISP-DM) y la honestidad de las cifras |
| **El equipo** | tiene que levantar la demo el día de la exposición | un comando que la levante y otro que confirme que responde | no improvisar frente al jurado |

## 3. Qué muestran los productos reales

Revisión de lo que publican operadores y proveedores en 2025 y 2026 (consultado el 13 de noviembre de 2026).

| Producto | Qué muestra | Fuente |
|---|---|---|
| **COES**, portal de demanda | La demanda ejecutada, la programación diaria (y su reprogramación) y semanal, y un **pronóstico automático de tiempo real con su rango mínimo y máximo**; exporta los datos | [COES, Demanda](https://www.coes.org.pe/Portal/portalinformacion/demanda) |
| **CAISO**, *Today's Outlook* | En un mismo gráfico: demanda real, pronóstico de una hora antes, pronóstico del día anterior y la demanda de ayer; arriba, **el pico previsto de hoy y el de mañana** y la capacidad disponible de las próximas horas; aparte, la demanda neta (sin solar ni eólica) | [CAISO, Today's Outlook](https://www.caiso.com/todays-outlook) |
| **Red Eléctrica (REE)** | Curvas de previsión, programada y real, actualizadas cada pocos minutos; desde diciembre de 2025, una cuarta curva, «Programada total», que suma el autoconsumo | [REE, nota del 11-dic-2025](https://www.ree.es/sites/default/files/2025-12/11122025_autoconsumo_1.pdf), [REE, demanda en tiempo real](https://www.ree.es/en/node/1240) |
| **ENTSO-E**, plataforma de transparencia | Pronóstico de carga total del día siguiente (art. 6.1.B), de la semana con mínimo y máximo por día (6.1.C) y del año; el operador debe actualizarlo si cambia 10 % o más | [ENTSO-E, 6.1.C](https://transparencyplatform.zendesk.com/hc/en-us/articles/16648042895252-Week-ahead-Total-Load-Forecast-per-Day-6-1-C), [Detailed Data Descriptions v3r4](https://eepublicdownloads.entsoe.eu/clean-documents/Transparency/MoP_Ref2_DDD_v3r4.pdf) |
| **AEMO** (Australia) | Pronóstico de demanda cada 30 min por región con **tres valores: POE10, POE50 y POE90** (probabilidad de ser excedido), para el predespacho y el corto plazo; está pasando a comunicar «sobres» de incertidumbre | [AEMO, datos de demanda operativa](https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/operational-demand-data), [ESIG, A. Akman](https://www.esig.energy/attachment/serve/session-4-embracing-uncertainty-in-operational-forecasting-andrew-akman-2) |
| **NESO** (Gran Bretaña) | **Publica cada mes el error** de su pronóstico de demanda del día siguiente, con métricas acordadas con el regulador; en 2025 incorporó un modelo probabilístico a 48 h y se comprometió a publicar pronósticos probabilísticos | [NESO, estrategia de pronóstico (2026)](https://www.neso.energy/document/370386/download), [NESO, pronóstico a 2 días](https://www.neso.energy/data-portal/2-day-ahead-demand-forecast) |
| **Proveedores** (Amperon, Enverus) | Pronósticos por conjunto de escenarios del clima con **percentiles P5 a P95**, **alertas de pico coincidente** y el error en las horas pico (no solo el del día) | [Amperon, 2025](https://www.solarpowerworldonline.com/2025/09/new-tool-from-amperon-can-predict-electricity-demand-up-to-7-months-ahead/), [Amperon, Europa](https://www.sustainabilityhq.com/amperon-expands-weather-informed-grid-demand-mid-term-forecast-to-europe-transforming-seasonal-energy-market-planning/), [Enverus, 2025](https://www.enverus.com/blog/enverus-forecasting-solutions-delivering-precision-and-innovation/) |

Lo que se repite y sirve aquí:

1. **Pronóstico, real y una vara en la misma curva.** Todos lo hacen. La app ya lo hace con la referencia simple.
2. **Una banda, no solo un número.** El propio COES dibuja un mínimo y un máximo; AEMO da tres valores; los
   proveedores, percentiles. La app ya muestra el rango del 90 %; falta comprobar que cubre lo que dice.
3. **El pico de hoy y el de mañana, arriba de todo.** CAISO lo pone antes que cualquier gráfico. La app no lo tiene.
4. **El error se sigue en el tiempo y se publica.** NESO lo reporta cada mes. La app muestra el error de 2026 como una
   sola cifra y por régimen de El Niño, pero no su evolución.
5. **Alertas de pico.** Los proveedores las venden. Para un operador, «viene una rampa fuerte a las 18:00» vale más
   que otra cifra de MAE.
6. **Varias versiones del pronóstico.** REE y ENTSO-E muestran la previsión y la programación lado a lado. Aquí el
   equivalente es comparar modelos (base, híbrido y combinado) y, más adelante, contra la Programación Diaria del COES.

**Contexto que la app puede usar.** El ENFEN mantiene la alerta de El Niño Costero y, en su comunicado 19-2026, prevé
magnitud extraordinaria en Niño 1+2 hasta febrero de 2027
([Gestión, nov-2026](https://gestion.pe/peru/el-nino-mantendra-intensidad-hasta-febrero-de-2027-que-regiones-tendran-mas-lluvias-noticia/)).
El producto sigue siendo relevante después de la exposición.

### Dónde está la app hoy

| Ya tiene | Le falta |
|---|---|
| Pronóstico a 1 h y 24 h por área, con rango del 90 %, lo real y la referencia simple | El pico y la rampa de las próximas 24 h |
| «¿Qué tan bueno es?» del día y el error de 2026 | El error y la cobertura **en el tiempo** |
| Escenarios de temperatura y diagnóstico por fase de El Niño | La versión del modelo y la fecha de corte de los datos, a la vista |
| Selector con base, híbrido y combinado (rama `feature/app-hibrido`) | El combinado como modelo por defecto y de dónde sale su número |
| Medición de usabilidad y accesibilidad (axe en 0) | Sesiones con personas; datos más allá del 23 de octubre de 2026 |

## 4. Lluvia de ideas

29 ideas en cinco grupos. Esfuerzo: **S** ≤ 2 h, **M** ≤ 1 día, **L** más de un día o depende de GPU, de terceros o
de que pase el tiempo. Impacto: **alto** si cambia lo que decide el operador o lo que ve la evaluadora; **medio** si
mejora la confianza o la calidad; **bajo** si es pulido.

### Modelo

| ID | Idea | Impacto | Esfuerzo |
|---|---|---|---|
| M1 | El **combinado como modelo por defecto**, con respaldo al base fuera del rango precalculado | alto | S |
| M2 | **Intervalos por *bootstrap* de días** de la combinación frente al Random Forest, en 2025 y 2026 (el paper los da por pendientes), con una comprobación por bloques de semanas | alto | S |
| M3 | Medir la **cobertura del rango del 90 %** de cada modelo en 2026 y recalibrarlo si se aleja (hoy sale de los cuantiles del error de 2025: es conformal partido) | medio | S |
| M4 | Banda con los **cuantiles propios de Chronos-2** (P10, P50, P90) en vez de un ancho fijo relativo, evaluada con pérdida *pinball* y cobertura | medio | M |
| M5 | **«Número para la reserva»**: el P90 a 24 h como lectura aparte, porque subestimar cuesta más que sobrestimar | medio | S |
| M6 | Contexto largo (8,192 periodos) para los fundacionales | bajo | L |
| M7 | **Prueba ciega hacia adelante**: congelar hoy la versión (tag y sha256 de los artefactos) y evaluarla con lo que venga de noviembre de 2026 en adelante; sería la primera cifra limpia del modelo | alto | L |

### Datos

| ID | Idea | Impacto | Esfuerzo |
|---|---|---|---|
| D1 | **Ingesta diaria del IEOD** para que la app llegue hasta ayer («modo hoy»), no solo al 23 de octubre | alto | L |
| D2 | Pronóstico fundacional diario en la 4060 o en Colab que alimente D1 | medio | L |
| D3 | **Comparar con el pronóstico automático de tiempo real y la Programación Diaria del COES**, en igualdad de origen, horizonte y perímetro | alto | L |
| D4 | Estado de alerta del ENFEN y fase de El Niño junto al pronóstico | bajo | S |
| D5 | **Fecha de corte y procedencia** a la vista: IEOD hasta el 23-oct-2026, entrenamiento hasta 2024 o 2025 según el modelo | medio | S |

### App y experiencia

| ID | Idea | Impacto | Esfuerzo |
|---|---|---|---|
| A1 | **Pico y rampa de las próximas 24 h** por área, con su rango, en el inicio | alto | S–M |
| A2 | **Seguimiento del error**: MAE móvil de 7 días del modelo frente a la mejor referencia, y cobertura móvil del rango, en 2026 | alto | M |
| A3 | Comparar modelos en el mismo día: tres curvas y lo real, con el MAE de 2026 de cada uno | medio | M |
| A4 | **«De dónde sale este número»**: los dos componentes del combinado y su peso | medio | S |
| A5 | **Días destacados** de la prueba con URL fija (el mayor pico del Norte, el peor día del modelo, un feriado, el mes del ICEN más alto) | medio | S |
| A6 | **Sesiones con 3 a 5 personas**: pensar en voz alta, tiempo por tarea y SUS | alto | M |
| A7 | Red lenta: pedir la serie en paralelo con los datos base cuando la URL ya trae un área | bajo | S |

### Operación

| ID | Idea | Impacto | Esfuerzo |
|---|---|---|---|
| O1 | **Demo pública con Tailscale Funnel** desde la máquina con GPU, con una verificación antes de exponer; aplica desde el PR #35 y solo con lo publicable o con acceso protegido (ver criterio 5) | alto | S |
| O2 | **Respaldo sin red**: capturas de los días destacados y un video de 60 a 90 s | medio | S |
| O3 | **Versión en `/salud`**: commit, sha256 corto de los artefactos, fin del entrenamiento y fecha de corte | medio | S |
| O4 | Prueba de humo de los notebooks en CI: papermill con datos sintéticos pequeños; jupytext para revisar sus diferencias | medio | M |
| O5 | Imagen reproducible de la demo: Dockerfile con uv y artefactos que se bajan con un comando | medio | M |
| O6 | Reporte de deriva de las entradas y aviso por correo cuando el error se dispara | bajo | M |

### Comunicación para la exposición

| ID | Idea | Impacto | Esfuerzo |
|---|---|---|---|
| C1 | **Guion de demo de 3 minutos** sobre los días destacados, ensayado con cronómetro | alto | S |
| C2 | Diapositiva «del Random Forest al combinado»: 54.6 → 48.2 MW a 1 h y 86.1 → 75.3 a 24 h en el Centro, con la cifra de 2026 (fuera del entrenamiento, pero ya inspeccionada) y su intervalo | alto | S |
| C3 | Ficha del modelo de una página: datos, entrenamiento, métricas de 2025 y 2026, límites y licencias | medio | S |
| C4 | QR a la demo y una diapositiva de «qué no hace» | bajo | S |

## 5. Matriz de impacto y esfuerzo

| | **Esfuerzo S** (≤ 2 h) | **Esfuerzo M** (≤ 1 día) | **Esfuerzo L** (> 1 día) |
|---|---|---|---|
| **Impacto alto** | M1, M2, A1, O1, C1, C2 | A2, A6 | M7, D1, D3 |
| **Impacto medio** | M3, M5, D5, A4, A5, O2, O3, C3 | M4, A3, O4, O5 | D2 |
| **Impacto bajo** | D4, A7, C4 | O6 | M6 |

Lectura: la fila de arriba a la izquierda va a la entrega; A2 entra porque es lo que más se parece a lo que publican
los operadores y los datos ya existen; las de impacto alto y esfuerzo L son la siguiente iteración; las de impacto
bajo solo si sobra tiempo.

## 6. Selección priorizada

### Para la entrega (≤ 1 día de trabajo)

Requisito previo: fusionar el PR #31, la rama del selector de modelo y el PR #32, en ese orden. Las cinco suman unas
8 a 9 horas; si falta tiempo, se recorta primero la 3.

| # | Qué | Ideas | Horas |
|---|---|---|---|
| 1 | El combinado por defecto, con su ficha a la vista | M1, A4, O3, D5 | 2 |
| 2 | Seguimiento del error y de la cobertura en 2026 | A2, M3 | 2.5 |
| 3 | Pico y rampa de las próximas 24 h | A1 | 2 |
| 4 | Intervalos de la combinación frente al Random Forest | M2, C2 | 1 |
| 5 | Demo pública a prueba de caídas | O1, O2, A5, C1 | 1.5 |

### Criterios de aceptación de las cinco

**1. El combinado por defecto, con su ficha a la vista.**

- Al abrir un área sin el parámetro `modelo`, la app muestra el combinado en toda fecha del rango precalculado; fuera
  de ese rango muestra el base **y lo dice en texto**. Una prueba de pytest cubre los dos casos.
- `/salud` devuelve el modelo, el commit, el sha256 corto de los artefactos, el fin del entrenamiento y la fecha de
  corte de los datos; la app los muestra a un toque de la respuesta.
- En el caso fijo del arnés (Centro, martes 10 de marzo de 2026, 19:00, a 24 h), la app muestra el pronóstico de
  Chronos-2 ajustado, el del híbrido y el peso (0.85 y 0.15), y la suma ponderada coincide con el número mostrado
  con una diferencia de 1 MW o menos.
- `node medir.mjs --rapido` de `app/medicion` sigue dando axe en 0 y T1 a T4 no suman acciones frente a la
  iteración 2.

**2. Seguimiento del error y de la cobertura en 2026.**

- Por área y horizonte, un gráfico con el MAE móvil de 7 días del modelo elegido y de la mejor referencia, de enero a
  octubre de 2026, solo con pronósticos fuera de muestra.
- El MAE total de 2026 que muestra la app para el combinado coincide con la tabla 5.5 del paper (Centro: 48.8 MW a
  1 h y 71.9 a 24 h) con una diferencia de 0.5 MW o menos; si no, el texto explica la diferencia de filas.
- La cobertura del rango del 90 % en 2026, total y móvil de 30 días, con la línea del 90 % de referencia. Si la total
  queda bajo 85 %, la app dice que el rango es más angosto de lo que debería («el rango cubrió N %: se queda corto»);
  si pasa de 95 %, que es más ancho de lo necesario («cubrió N %: exagera el margen»).
- Una frase con la conclusión del gráfico, del tipo «En N de las M semanas el modelo quedó por debajo de la
  referencia», calculada, no escrita a mano.

**3. Pico y rampa de las próximas 24 h.**

- En el inicio, por área: la hora y los MW del máximo de las próximas 24 h con su rango, y la mayor subida en una hora
  (MW/h) con la hora en que ocurre.
- «Rampa fuerte» se marca con texto, no solo con color, cuando la subida supera el percentil 95 de las subidas horarias
  del área en 2016–2024 (solo datos de entrenamiento).
- Un script calcula sobre 2026, a 24 h y por área: el porcentaje de días en que la hora del pico pronosticada cae a
  ±1 h de la real y el error medio del pico diario en MW frente a la mejor referencia. Las seis cifras quedan en
  `reportes/` y la app las muestra junto a la tarjeta.
- La tarjeta no agrega acciones a T1 en el arnés.

**4. Intervalos de la combinación frente al Random Forest.**

- Doce intervalos al 95 % (tres áreas, dos horizontes, 2025 y 2026) de la diferencia de MAE entre la combinación y el
  Random Forest, por *bootstrap* de días con la misma semilla y el mismo número de remuestreos que el notebook 04.
- **Límite declarado:** remuestrear días como si fueran independientes ignora que el error de un día se parece al del
  siguiente, y los intervalos pueden salir más angostos de lo que son. Como comprobación, se repiten con *bootstrap*
  por bloques de una semana; si alguna conclusión cambia de signo o deja de distinguirse de cero, se reporta así.
- La tabla queda en el notebook 04 y en la sección 5.5 del paper, y desaparece la frase «Sus intervalos los calculará
  el notebook 04».
- La diapositiva C2 cita la cifra de 2026 con su intervalo como «fuera del entrenamiento, pero ya inspeccionada» (2026
  se usó en el notebook 03) y marca la de 2025 como dentro de muestra. «Limpia» se reserva para la prueba congelada
  hacia adelante (M7).

**5. Demo pública a prueba de caídas.**

Dos condiciones antes de exponer nada:

- **Qué se expone es decisión del dueño del repo.** Con el pronosticador real, `/series/{area}` entrega la demanda
  real de las capas del COES sin autenticación, y el COES no publica licencia. La demo pública debe servir solo lo ya
  publicable (por ejemplo, pronósticos y errores, sin la serie real) o ir protegida (solo dentro de la red de
  Tailscale o con contraseña). Mientras no se decida, la demo va por la red de Tailscale, no por Funnel.
- **Funnel sobre el puerto 8000 sirve la app solo desde el PR #35**, en el que el backend entrega `app/web`
  comprimido en el mismo origen (sin otro puerto ni CORS extra). Antes de ese PR, la URL pública mostraría solo la API.

Con eso resuelto:

- Una URL HTTPS abre la app desde un celular con datos móviles, fuera de la red de Tailscale; el número aparece en
  2 s o menos (mediana de 5 cargas).
- Un script de verificación consulta `/salud`, `/modelos` (existe desde el PR #31) y una serie de cada modelo, sale
  con código 0 en menos de 30 s y se corre 30 minutos antes de la exposición.
- Entre 4 y 6 días destacados con URL fija; el guion de 3 minutos se ensaya dos veces y dura 3:00 o menos.
- El respaldo (capturas de los días destacados y video de 60 a 90 s) abre sin internet desde la laptop de la
  exposición.
- La URL pública se apaga al terminar: cualquiera que la tenga puede entrar.

### Siguiente iteración

En este orden:

1. **Sesiones con 3 a 5 personas** (A6): estudiantes de ingeniería eléctrica como operadores y la profesora como
   evaluadora; las cuatro tareas del arnés, tiempo por tarea y SUS. Es el pendiente principal del rediseño.
2. **Datos al día y prueba ciega hacia adelante** (D1, D2, M7): congelar la versión de la entrega y pronosticar cada
   día con el IEOD nuevo. Con El Niño extraordinario hasta febrero de 2027, es la prueba que el paper no pudo hacer.
3. **Comparación con el COES** (D3): contra el pronóstico automático de tiempo real (que el portal exporta) y la
   Programación Diaria, cuidando que el perímetro y el origen sean los mismos. Es la vara que un lector del COES pide
   primero.
4. **Banda probabilística propia** (M4, M3): cuantiles de Chronos-2 y recalibración adaptativa (ACI) si la cobertura
   se aleja; evaluar con *pinball* y cobertura.
5. **Comparar modelos en el mismo día** (A3) y el «número para la reserva» (M5).
6. **Reproducibilidad** (O4, O5): prueba de humo de los notebooks en CI y una imagen de la demo.
7. Contexto largo de los fundacionales (M6), estado del ENFEN (D4), red lenta (A7) y aviso por correo (O6), cuando
   haya datos nuevos que vigilar.

### No hacer, y por qué

| Qué | Por qué |
|---|---|
| Reentrenar automáticamente cada semana en la app | En 2026 reentrenar cambió el error alrededor de 1 %; suma piezas que pueden fallar a cambio de casi nada |
| Usar el clima pronosticado como entrada a 24 h | En 2026 el clima **empeoró** el pronóstico a 24 h en el Norte y el Centro, y la temperatura tampoco ayudó a Chronos-2 |
| Generar el pronóstico fundacional en vivo en la app | Pide GPU; la app es una repetición de 2025 y 2026 y los pronósticos ya están calculados |
| Explicar el combinado variable por variable (SHAP) | Chronos-2 no tiene una atribución comparable a la del XGBoost; una explicación a medias engaña. Se muestran los componentes y sus pesos (A4) |
| Mostrar TimesFM 3.0 u otro modelo de licencia no comercial | Su licencia no permite el uso operativo que la app simula |
| Migrar a Streamlit | Se perdería la medición del PR #31 (axe en 0, tareas medidas); el paper ya declara la decisión y su riesgo |
| Subir la app a un servicio en la nube | No hace falta GPU para servirla, pero habría que subir capas derivadas del COES, que no publica licencia; la demo corre en la máquina propia |
| Agregar MLflow, DVC o un servidor de modelos | El medallón ya guarda la procedencia con sha256 y los modelos se rehacen con un comando; un segundo sistema al final del ciclo cuesta más de lo que aporta |
| Pronosticar el SEIN total y reconciliarlo con las áreas | Fuera del alcance del OE3 y del tiempo que queda |

## 7. Herramientas evaluadas

| Necesidad | Herramienta | Veredicto | Por qué |
|---|---|---|---|
| Demo pública | [Tailscale Funnel](https://tailscale.com/kb/1223/tailscale-funnel) | **Adoptar**, con condiciones | La demo ya corre detrás de Tailscale; Funnel da HTTPS público a un puerto local sin abrir puertos. Sirve la app desde el PR #35 (web y API en el mismo origen). Acceso para cualquiera con la URL y límite de ancho de banda no configurable: solo durante la exposición y solo con lo publicable o protegido (criterio 5) |
| Hospedaje gratuito | Hugging Face Spaces (Docker) | Descartar | En 2026 hay reportes de que el CPU gratuito para Docker pide plan pagado o se queda sin cuota ([foro de HF](https://discuss.huggingface.co/t/cpu-basic-quota-limit-with-only-one-space/180646); no confirmado oficialmente), se duerme sin uso y obligaría a subir capas del COES |
| Servir el modelo | BentoML, LitServe | Descartar | La app lee pronósticos precalculados; FastAPI alcanza |
| Intervalos | [MAPIE](https://mapie.readthedocs.io/en/stable/generated/mapie.regression.TimeSeriesRegressor.html) 1.6 (EnbPI, ACI) | Probar | Para la siguiente iteración (M3, M4). En la entrega basta el rango por cuantiles del error de 2025, que ya es conformal partido |
| Evaluar la banda | [scoringrules](https://github.com/frazane/scoringrules) 0.12, utilsforecast | Probar | *Pinball*, CRPS y cobertura, junto con M4 |
| Seguimiento y deriva | [Evidently](https://github.com/evidentlyai/evidently) 0.7 | Probar | Solo cuando haya datos nuevos (D1). Hoy el seguimiento es MAE móvil y cobertura, que salen con pandas |
| Seguimiento y deriva | NannyML | Descartar | Estima el desempeño sin lo real, y aquí lo real llega a los 30 minutos; sin cambios desde julio de 2025 |
| CI de notebooks | papermill (ya se usa) | Probar | Prueba de humo con parámetros y datos sintéticos (O4) |
| CI de notebooks | nbmake, nbval | Descartar | nbmake sin versión desde diciembre de 2024; nbval compara salidas, frágil con cifras que cambian |
| Revisar notebooks | [jupytext](https://github.com/mwouts/jupytext) | Probar | Un `.py` pareado hace legibles las diferencias en los PR |
| Versionar datos y modelos | DVC, MLflow | Descartar | Ver «No hacer» |

## 8. Riesgos

| Riesgo | Qué puede pasar | Cómo se maneja |
|---|---|---|
| **Licencia de Simons (OpenMDW-1.1)** | Licencia permisiva para pesos, datos y código, publicada por la Linux Foundation en mayo de 2026; la OSI todavía la revisa ([lista license-review, ago-2026](https://lists.opensource.org/pipermail/license-review_lists.opensource.org/2026-August/006125.html)) | Citar la licencia y el aviso en la ficha (C3) y confirmar el texto en la ficha del modelo antes de cualquier uso fuera del curso |
| **Licencia de Chronos-2 (Apache-2.0)** | Permisiva; si se redistribuye el modelo ajustado, hay que acompañarlo de la licencia y el aviso, y señalar que se modificó | Mencionarlo en la ficha y en el notebook 04 |
| **Otros fundacionales** | TimesFM 3.0 es de uso no comercial (según el paper; por confirmar en su ficha) | Fuera de la app (ver «No hacer») |
| **Dependencia de GPU** | Sin los pronósticos precalculados, el híbrido y el combinado no tienen qué servir; rehacerlos pide una L4 o una A100 (unas 195 series por segundo en una L4; el ajuste fino, 26 minutos en una A100) | La app vuelve al base y lo dice (criterio 1); los archivos precalculados quedan respaldados en el Drive con su sha256 |
| **Datos del COES** | No publican licencia; el IEOD validado llega con días de rezago; un cambio en el portal rompe la ingesta; las capas llegan al 23 de octubre de 2026; una demo pública con el pronosticador real los entrega por `/series/{area}` | Citar al COES, no subir datos crudos al repo, mostrar la fecha de corte (D5), no exponer la serie real sin que el dueño del repo lo decida (criterio 5) y dejar la ingesta diaria para la siguiente iteración |
| **Cifras que se leen de más** | Los pesos de la combinación se fijaron en 2025 y 2026 ya se había usado; el *bootstrap* de días puede dar intervalos angostos | En la app y en la exposición, la cifra principal es la de 2026, presentada como fuera del entrenamiento pero ya inspeccionada, con su intervalo y la comprobación por semanas (criterio 4) |
| **La demo falla en vivo** | Sin red, la máquina apagada o Funnel caído | Verificación 30 minutos antes y respaldo sin red (criterio 5) |
| **URL pública** | Cualquiera con el enlace puede entrar y extraer lo que la API entregue | Solo lo publicable o acceso protegido, según decida el dueño del repo; se apaga al terminar |
| **Usabilidad sin personas** | Todo lo medido es sintético | Declararlo en la exposición; sesiones en la siguiente iteración (A6) |
| **Orden de fusión** | Esta lista asume el PR #31, el selector de modelo y el PR #32 ya fusionados, y el PR #35 para la demo pública | Fusionar en ese orden antes de empezar |
