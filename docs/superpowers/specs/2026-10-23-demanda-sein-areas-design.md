# Demanda eléctrica por área del SEIN ante eventos extraordinarios: diseño del proyecto

Fecha: 2026-10-24 (v2, con la revisión de la v1 del 23-oct). Estado: borrador para revisión del grupo.

## 1. Objetivo

Pronosticar la demanda eléctrica de las tres áreas operativas del Sistema Eléctrico Interconectado Nacional (SEIN),
**Norte, Centro y Sur**, cada 30 minutos y con datos públicos del COES, a dos horizontes:

- **1 hora (t+2):** el pronóstico operativo, para la coordinación en tiempo real.
- **24 horas (t+48):** la programación del día siguiente. Es comparable con la Programación Diaria del COES y es
  donde un pronóstico de clima o de El Niño puede cambiar la decisión.

Y medir cómo se adapta el pronóstico cuando el sistema vive un **evento extraordinario**, es decir, cuando la
demanda se sale de lo que el modelo vio al entrenar. Hay dos formas de adaptarse: **sumar variables exógenas**
(clima, El Niño, fallas) y **reentrenar más seguido**. Se comparan las dos.

> ¿Qué tan bien se pronostica la demanda de cada área durante un evento extraordinario, y qué ayuda más: la
> información exógena o reentrenar a tiempo?

**Hipótesis, escrita antes de ver los resultados:**
- **A 1 h** la ganancia de las exógenas será pequeña, porque la demanda reciente y su media de 24 h ya absorben el
  nivel.
- **A 24 h** la ganancia puede ser mayor, sobre todo en el Centro (Lima) y en la costa norte.
- **"Sin efecto" es un resultado válido** y se reporta igual, con su intervalo.

**Las áreas viven realidades distintas**, y no todo es clima:

- **Norte:** lluvias e inundaciones con El Niño (marzo de 2017 y de 2023), con carga minera e industrial
  (Yanacocha, Cementos Pacasmayo).
- **Centro:** en 2017, Lima era ~47 % del área (1,585 de 3,350 MW en el IEOD); el resto es Electroandes, minería e
  industria. El calor de los veranos con Niño debería pesar en la parte de Lima.
- **Sur:** dominado por la minería (Cerro Verde, Las Bambas, Southern). Su variabilidad es más industrial que
  climática, así que las exógenas climáticas deberían pesar poco ahí.

El notebook 01 mide la cuota de los usuarios libres de cada área con la hoja `DEMANDA_UL` y reescribe estas
afirmaciones con cifras.

**Por qué ahora:** El Niño Costero de 2026 es extraordinario. El ICEN llegó a 3.98 en agosto, el mayor desde
1997-98, y ENFEN prevé esa magnitud hasta enero de 2027. Además, no encontramos estudios revisados por pares que
midan el efecto de El Niño sobre la demanda de Lima o del SEIN ([`docs/peru/nino.md`](../../peru/nino.md), §3.1).

## 2. Negocio

| | 1 hora | 24 horas |
|---|---|---|
| **Quién decide** | Coordinación de la operación en tiempo real del COES | Programación de la operación del COES (el programa diario) |
| **Qué decide** | Redespacho, reserva rotante, arranque de unidades rápidas y maniobras entre áreas | Qué unidades se programan para mañana, con qué reserva, y la compra de combustible para las térmicas |
| **Costo de subestimar** | Reserva insuficiente: arrancar diésel caro de urgencia o, en el extremo, cortar carga | Programar poca generación: desvíos caros en tiempo real |
| **Costo de sobrestimar** | Reserva ociosa y arranques innecesarios | Unidades comprometidas de más |
| **Por qué por área** | Los enlaces de transmisión entre áreas tienen límite: un desvío en el Norte no siempre se cubre desde el Centro | Igual. Además, El Niño golpea distinto a cada área |

**Subestimar cuesta más que sobrestimar.** Por eso, además del MAE, se reporta la subestimación en las horas de
mayor demanda (§8.5).

**Supuesto de colaboración entre instituciones.** Se simula que el COES y ENFEN colaboran: el operador recibe en
tiempo real los datos y los pronósticos de clima y de El Niño de ENFEN, que incluye a SENAMHI, IGP e IMARPE.

- **En el histórico:** se usa el dato observado como si fuera el pronóstico recibido, degradado con un error de
  pronóstico realista (§6).
- **Es un supuesto del paper,** no un dato del COES. Le da sentido a los escenarios del tipo "¿y si mañana hace más
  calor?".

## 3. Lo ya decidido (no se reabre aquí)

- **Caso:** demanda del COES por área (Norte, Centro, Sur). La profesora aprobó el cambio de caso y que **el COES
  cuenta como fuente abierta**.
- **Por qué áreas y no subestaciones.** La investigación recomendaba la demanda por subestación de Luz del Sur
  ([`docs/peru/energia.md`](../../peru/energia.md), §4), pero esa serie solo cubre Lima Sur y no responde la
  pregunta por realidades regionales. Las áreas sí, y además suman exacto al SEIN en el IEOD. Las subáreas no se usan
  porque cambian entre años (siete en 2017, una en 2026). **Plan B:** el SEIN del portal del COES (§12).
- **El Niño, el clima, las fallas del COES y el SAIDI de Osinergmin son exógenas,** no lo que se predice.
- **Regla de información:** cada variable entra solo con lo que se sabía en el momento de predecir, con su rezago
  de publicación real (§6).
- **Se reutiliza la metodología de Tetuán:**
  - medallón con auditoría;
  - objetivo en razón con la media de 24 h (`ModeloRazon`);
  - modelo global;
  - referencias ingenuas;
  - origen móvil;
  - bootstrap por días.

  Tetuán y Ceuta quedan como **antecedente metodológico**: muestran que el objetivo en razón aguanta niveles que el
  modelo no vio.
- **App propia,** no Streamlit, aunque la rúbrica lo nombre. Riesgo aceptado en el criterio VI. Igual tiene que
  **ejecutar el modelo** ([spec de la app](2026-10-23-app-design.md)).
- **Infraestructura:**
  - lo pesado se baja y se procesa en Colab Pro, con GPU cuando haga falta;
  - el bronze vive en el Drive;
  - el silver y el gold, en el Drive y en un dataset **privado** de Hugging Face del grupo;
  - la demo final corre en la 4060, detrás de Tailscale;
  - nada pesado en local.

## 4. Alcance

Dentro:

- **Medallón del COES:**
  - el IEOD diario de 2016 a 2026, completo en el bronze;
  - el SEIN del portal y la Programación Diaria;
  - los eventos relevantes.
- **Exógenas:** ERA5 horario por área, ICEN, Niño 1+2, feriados, cuarentena y SAIDI por área.
- **Modelado a 1 h y a 24 h:**
  - Ridge, Random Forest y Gradient Boosting, con búsqueda de hiperparámetros y validación cruzada temporal;
  - global frente a local.
- **Ablación de exógenas** (§8.3) y **experimento de adaptación** (§8.4).
- **Evaluación:** validación en 2025, prueba fuera de distribución en 2026 y errores por régimen.
- **App con backend que ejecuta el modelo, short paper y exposición.**

Fuera:

- la demanda por subestación de las 31 distribuidoras;
- los costos marginales;
- la generación hidroeléctrica como objetivo;
- los pronósticos de clima reales (se simulan, §2);
- el estado de alerta de ENFEN armado desde los PDF, salvo que haga falta para la variante "reentrenar cuando cambia
  la alerta" (§8.4). En ese caso se arma en Colab.

## 5. Datos

Detalle y calidad en [`docs/peru/energia.md`](../../peru/energia.md) y [`docs/peru/nino.md`](../../peru/nino.md).

| Fuente | Qué aporta | Resolución, cobertura y publicación | Acceso | Calidad y cuidados |
|---|---|---|---|---|
| **COES, IEOD** (anexo diario) | `DEMANDA_AREAS` (SEIN, Norte, Centro, Sur); también `DEMANDA_UL` (usuarios libres), `G_AREAS` (generación por área y recurso), `EVENTOS` (con MW indisponibles e interrupción), `DESV_DEMANDA_PRONOS` y `TEMP_AMB`, cuando existen | 30 min, de oct-2011 a D+1 | Un xlsx por día (1.0-1.3 MB, ~400 MB/año). **El bronze guarda el xlsx completo** en el Drive y registra las hojas de cada archivo | Norte + Centro + Sur = SEIN exacto en el IEOD. Las hojas y los nombres cambian por año: en 2017 no hay `EVENTOS` ni `TEMP_AMB`. Hay variantes de formato (§9) |
| COES, SEIN del portal | Ejecutado, Programación Diaria y Semanal | 30 min, del 2000 a casi hoy | Un xlsx por año (~0.63 MB) | 2015-2026 sin huecos ni duplicados. Queda **+1-1.5 % sobre el IEOD**: no se mezcla con él. Es el plan B (§12) |
| COES, eventos relevantes | Fallas: empresa, ubicación, inicio y fin | Por evento; verificado de 2017 a 2026 | Un xlsx por año (~110 KB) | Texto libre. **2016 por verificar.** En 2023 los eventos duran más que en 2017 (mediana de 62 frente a 26 min) y hay registros de meses o años: los de más de 2 días no cuentan como falla en curso |
| Open-Meteo, ERA5 | Temperatura horaria por ciudad | Horaria, desde 1940; ~5 días de rezago | API, CC BY 4.0 | Completa. La lluvia de ERA5 en Lima no sirve |
| IGP y ENFEN, ICEN | Régimen de El Niño Costero | Mensual, 1950 a 2026-08; el definitivo del mes m sale entre los días ~10 y 20 de m+2 | TXT de 16 KB | Sin huecos. Cambió de método en dic-2024: se usa una sola versión, fijada en la procedencia |
| NOAA CPC, Niño 1+2 (OISST) | Temperatura del mar frente al norte | Semanal, de 1981 a hoy; ~9 días de rezago | TXT de 149 KB, dominio público | Sin huecos |
| Osinergmin, SAIDI y SAIFI | Duración y frecuencia de los cortes por sistema eléctrico | Mensual, de 2004 a 2026-03; ~5 semanas de rezago | datosabiertos.gob.pe, ODC-By | Limpio. **No viene por área:** se agrega con la tabla `empresa → área` |
| Feriados | Calendario | Diario, 2016-2026 | Paquete `holidays` (PE) para los nacionales; a mano, los no laborables decretados y los regionales relevantes | Los no laborables compensables aplican sobre todo al sector público: su efecto es parcial |
| Tablas de asignación | `empresa → área` y `subestación → departamento → área` | Estáticas | Armadas a mano y revisadas, con su fuente | Las transmisoras (REP, CTM, ISA) cruzan áreas: lo que no se asigne queda como indicador del SEIN |

**Por qué empezar en 2016:**
- La demanda por área existe en el IEOD desde 2011, pero en 2015 el anexo es un `.xls` sin la hoja
  `DEMANDA_AREAS`. El punto de control (§9) leyó bien de 2016 a 2026: 48 periodos por día y Norte + Centro + Sur =
  SEIN exacto.
- El pico diario cambió de lugar: en 2015 el 98 % de los días tenía el máximo entre las 18 y las 23 h, y en 2026
  solo el 29 %. Empezar en 2016 deja fuera el año más antiguo de esa deriva.
- Empezar en 2016 deja dentro del entrenamiento dos eventos: El Niño Costero de 2017 y el de 2023 con el ciclón Yaku.

## 6. Variables y regla de información

Todo se mide en t: el momento en que se emite el pronóstico de t+H, con H = 2 o 48.

| Grupo | Variables | ¿Disponible en t? |
|---|---|---|
| **Demanda del área** | Rezagos t, t−1, t−2 y t−4; mismo momento de ayer y de la semana pasada respecto de t+H; media y desviación de la última hora; todo dividido por la media de 24 h del área | **Para el operador, sí** (SCADA en tiempo real). El público solo la ve al día siguiente en el IEOD. El proyecto toma la vista del operador y usa el IEOD (dato validado) como sustituto del dato en tiempo real, que no es público. Se declara |
| Nivel reciente | Media de 24 h sobre la de 7 días | Igual que la demanda |
| Calendario | Hora, minuto del día, día de la semana; seno y coseno diario y semanal; feriado y no laborable de la fecha de t+H | Sí: se conoce de antemano |
| Clima, a 1 h | Temperatura del área en t (la **última hora ya publicada**: a las 00:30 vale la de las 00:00, no se interpola con la de la 01:00); media de 24 h; anomalía frente a la climatología de 2016-2024 por hora y mes, que queda fija en los reentrenamientos | **No en sentido estricto:** ERA5 llega con ~5 días. Se usa como sustituto del dato observado que tendría el operador (supuesto de colaboración, §2) |
| Clima, a 24 h | Temperatura del área pronosticada para t+H: la observada (interpolada entre horas) más **un error por día de emisión y por área**, con media cero, porque el COES recibiría un pronóstico al día. Dos niveles, σ = 1 y 2 °C, con la fuente en la verificación de la temperatura a 2 m a 24 h del ECMWF. La misma semilla en entrenamiento, validación y prueba | Sí, bajo el supuesto de colaboración |
| El Niño | ICEN definitivo **según su fecha de publicación**: el del mes m−2 si el día es ≥ 20 y el de m−3 si no; Niño 1+2 de la última semana publicada (~9 días) | Sí, con su rezago |
| Fallas | Eventos del COES en curso en t. Un evento cuenta desde su inicio hasta su final, pero **como mucho 2 días**: no se descartan por su duración, que no se conoce al predecir. Por área cuando exista la tabla `empresa → área`; hasta entonces, el total del SEIN. Si el anexo trae `EVENTOS` con MW indisponibles o interrupción, se prueba "falla con interrupción" | Sí: se registran durante la operación (falta medir con cuánto retraso se publican) |
| SAIDI del área | El último SAIDI publicado como "estrés de la red": el de m−2 desde el día 7 de cada mes, el de m−3 antes | Sí, con su rezago. **En la evaluación** se usa además el SAIDI del mismo mes (ex post) para marcar los meses con la red golpeada (§8.5) |
| Contexto | Cuarentena por fases con inicio y fin (estricta del 16-mar-2020; reactivación por fases durante 2020), según los decretos | Sí |

El calendario anual (mes, día del año) no entra en las variantes M. Se prueba aparte: M0 con y sin calendario
anual, antes de la ablación. En Tetuán, con un solo año, funcionó como identificador de época; aquí hay doce años.

**Ciudades de ERA5 por área** (media simple, porque ponderar por demanda exigiría datos por departamento):

| Área | Ciudades | Nota |
|---|---|---|
| Norte | Piura, Chiclayo y Trujillo | Costeras |
| Centro | Lima | Electroandes y la minería del Centro no responden al clima de Lima |
| Sur | Arequipa y Tacna | **No** Cusco: está a 3,400 m y no muestra demanda por calor |

Los departamentos de cada área se confirman con el documento de áreas operativas del COES.

## 7. Modelado

- **Series:** las tres áreas. El SEIN se reporta como la suma de las áreas y, a 24 h, también se modela directo
  para compararlo con la Programación Diaria.
- **Objetivo:** la demanda de t+H dividida por la media de 24 h del área (`ModeloRazon`). Las métricas se calculan
  siempre en MW.
- **Algoritmos** (criterio V de la rúbrica): Ridge, Random Forest (con `max_samples` ≤ 0.3) y Gradient Boosting
  (`HistGradientBoostingRegressor`).
  - Hiperparámetros con `RandomizedSearchCV` y `TimeSeriesSplit(gap=H)`; para el modelo global, `CVPorFecha`.
  - **Cómputo acotado:**
    1. se elige el algoritmo y el modelo global o por área solo con **M0** y a 1 h;
    2. la ablación (§8.3) y el experimento de adaptación (§8.4) se corren con el ganador;
    3. el horizonte de 24 h reutiliza los hiperparámetros del de 1 h.
- **Importancia de variables:** por permutación, en la validación, por área y por grupo de variables.
- **Modelo final:** antes de la prueba se reentrena con entrenamiento + validación. Durante la prueba, la política
  de reentrenamiento es la que salga mejor en el experimento de adaptación (§8.4).

## 8. Evaluación

### 8.1 Partición

| Tramo | Fechas | Para qué |
|---|---|---|
| Entrenamiento | ene-2016 a dic-2024 | Ajuste y búsqueda de hiperparámetros. Incluye 2017, la cuarentena de 2020 y 2023 |
| Validación | ene-2025 a dic-2025 | Elegir el modelo, las exógenas y la política de reentrenamiento |
| **Prueba fuera de distribución** | ene-2026 a oct-2026 | El Niño extraordinario. Se toca una sola vez, al final |

Entre tramos queda un hueco de H pasos. **El modelo, las exógenas y la política de reentrenamiento se eligen en 2025.** En 2026 se corre todo, pero no se elige nada.

### 8.2 Referencias

| Horizonte | Referencias |
|---|---|
| 1 h | Persistencia (t), ayer a la misma hora (t+2−48) y semana pasada a la misma hora (t+2−336). Se compara contra la mejor de las tres en cada tramo |
| 24 h | Persistencia, que a este horizonte coincide con "ayer a la misma hora" (t+48−48 = t), y semana pasada (t+48−336). Para el SEIN, además, **la Programación Diaria del COES** (§8.2.1) |

#### 8.2.1 Comparación con la Programación Diaria del COES

Compararla con el modelo sobre la misma serie la sesgaría: la Programación Diaria se emite para el perímetro del
portal, que queda +1-1.5 % sobre el IEOD, y es un pronóstico de 10 a 34 h emitido una vez al día, no uno móvil a
t+48. Por eso:

- se evalúa la Programación Diaria contra el **Ejecutado del portal**, y el modelo contra el **IEOD**, y se comparan
  en términos relativos (MAPE);
- se agrega una evaluación **"día siguiente"**, con origen fijo a las 12:00 del día anterior y horizontes de 12 a
  36 h, para compararlos en igualdad;
- se reporta por hora del día dónde gana cada uno;
- en 2026 se usa también la hoja `DESV_DEMANDA_PRONOS` del IEOD, que compara la Programación Diaria con la ejecutada.

Falta bajar el SEIN del portal y la Programación Diaria (`ExportarDemanda`, un xlsx por año).

### 8.3 Ablación de exógenas

- **Acumulativa:** M0 (demanda y calendario), M1 (+ clima), M2 (+ El Niño), M3 (+ fallas) y M4 (+ SAIDI(m−2)).
- **Quitando un grupo a la vez desde M3** (sin clima, sin El Niño, sin fallas): mide lo que aporta cada grupo por
  su cuenta. En la cadena acumulativa, el aporte de El Niño después del clima es casi cero por construcción.

En cada variante se reporta el MAE, en general y por régimen (§8.5), a 1 h y a 24 h. El tamaño del efecto va con
su intervalo por bootstrap de días.

### 8.4 Experimento de adaptación ante eventos extraordinarios

En la validación de 2025 y en la prueba de 2026:

| | Sin exógenas (M0) | Con exógenas (M3) |
|---|---|---|
| **Modelo fijo** | A | B |
| **Reentrenado cada semana** | C | D |

Más una quinta variante: **reentrenar cuando ENFEN cambia el estado de alerta**, que es la colaboración del §2. No
puede adaptar antes que la semanal, porque dispara pocas veces. Se presenta como "casi la misma adaptación con muchos
menos reentrenamientos" (costo frente a beneficio) y como disparador extra sobre la semanal.

- La serie de alerta se arma con los cruces de umbral del ICEN, con su rezago de publicación; los comunicados en
  PDF quedan como mejora opcional.
- En todas las políticas: ventana creciente, hiperparámetros congelados (los elegidos en el entrenamiento) y un hueco
  de H pasos antes de cada reentrenamiento.

### 8.5 Regímenes y criterios

**Dónde se desagrega el error:**
- **El Niño,** según el ICEN y la clasificación de ENFEN (Nota Técnica 01-2024). Como 2026 es casi todo
  extraordinario, la comparación entre regímenes usa el origen móvil de 2023 a 2025 más la prueba.
- **Red golpeada:** el SAIDI del mismo mes sobre su percentil 90, ex post.
- **Fallas en curso.**
- **Feriados, laborables frente a fin de semana, y horas de mayor demanda.** Estas se definen por área y por año,
  porque el pico se movió al mediodía.
- **Cuarentena.**

Además, origen móvil mensual de 2023 a 2025 para el modelo elegido, M0 frente a M3.

**Criterios de éxito (a confirmar por el grupo):**
1. En cada área y en cada horizonte, el MAE del modelo elegido queda por debajo del de la mejor referencia, en el
   origen móvil y en la prueba.
2. En las horas de mayor demanda también le gana a la mejor referencia. Se reporta la fracción de esas horas que se
   subestima por encima del percentil 90 del error de la mejor referencia; un umbral fijo de 5 % sería ~0 para todos
   a 1 h.
3. Se reporta el tamaño del efecto de las exógenas y de la política de reentrenamiento, con su intervalo, contra la
   hipótesis escrita en el §1. No hay meta fija de mejora.
4. Se reporta honestamente dónde falla: por ejemplo, si 2026 obliga a extrapolar la temperatura. En Lima, la máxima
   de octubre va +4.8 °C, fuera del rango 2016-2024.

## 9. Ingesta del IEOD: lo que ya se sabe del formato

- **Las rutas cambian por año:** `03_MARZO` (2017), `03_Marzo` (2023), `10_Octubre` (2026); `Dia 01` y `Día 02`
  conviven en 2017; los anexos se llaman `Anexo_0203.xlsx` (2017), `Anexo1_Resumen_1503.xlsx` (2023) y
  `AnexoA_2210.xlsx` (2026).
- **En `DEMANDA_AREAS`:**
  - la hora viene como `datetime.time` en 2017 y como texto `'00:30'` en 2026;
  - las 24:00 vienen como `datetime(1900, 1, 1)` en 2017;
  - `'CENTRO '` lleva un espacio al final en 2017;
  - hay filas de `MÁXIMO`, `MÍNIMO`, `PROMEDIO` y `ENERGÍA` al pie;
  - la columna de importación o intercambios internacionales no entra en la suma.
- **La hoja se lee por su contenido** (`SEIN`, `NORTE`, `CENTRO`, `SUR`), no por su posición.
- **Las marcas de "datos estimados" o "sin datos"** se propagan al silver como indicador.
- **Punto de control antes de la descarga masiva:** un anexo por año (el 2 de marzo), leído con el mismo lector, con
  SEIN = N + C + S. **Resultado:** de 2016 a 2026, 48 periodos por día y desvío 0.0 MW. En 2015 el anexo es
  `Anexos_0203.xls` y no trae `DEMANDA_AREAS`. Desde 2018 hay varios anexos por día (`Anexo1`, `Anexo3_RSF`,
  `Anexo4_Hop`…) y desde 2025 uno solo (`AnexoA`); el lector busca el que tenga la hoja.

## 10. Reproducibilidad y estructura

- **Bronze:** el xlsx crudo de cada día en el Drive, con la procedencia (URL, fecha de descarga, sha256 y hojas
  presentes).
- **Silver:** la demanda por área (`coes/silver/demanda_areas.parquet`) y las exógenas (`exogenas/silver/*.parquet`),
  cada una con su marca de tiempo.
- **Gold:** una fila por periodo de 30 minutos desde 2015-12-24 (la semana de rezago que necesita el primer día de
  2016), con la demanda por área y las exógenas **ya con la regla de información aplicada**:
  - ICEN, Niño 1+2 y SAIDI según su publicación;
  - temperatura conocida en t;
  - fallas en curso;
  - feriados y cuarentena.

  Las razones y los rezagos no van en el gold: los calcula `variables_sein.py` en los notebooks y en la API, así hay
  una sola implementación.
- **Silver y gold, publicados en el Drive y en un dataset privado de Hugging Face del grupo,** con el mismo sha256.
  Falta `publicar_hf()`: el token va por los secretos de Colab y lo carga el usuario.
- **Artefactos para la app**, el punto de control entre la fase 3 y la 4:
  - `modelo_{area}_{horizonte}_{variante}.joblib`, para las tres áreas y el SEIN, a 1 h y 24 h, en M0 y M3;
  - `diagnostico_{area}.json` y `resumen.json`;
  - la versión (sha256) del gold con que se entrenaron.
- **Los notebooks 01 y 02 arrancan del silver,** así que se pueden correr sin repetir la descarga.
- **El COES no publica licencia:** se dice en el README y en el paper.

```
notebooks/
  00_medallon_coes.ipynb       Colab: punto de control, bronze y silver del IEOD; copia al Drive
  00c_exogenas.ipynb           Colab: bronze y silver de las exógenas
  (gold y publicación en HF: pendiente)
  01_datos_preparacion.ipynb   CRISP-DM 2 y 3
  02_modelado_evaluacion.ipynb CRISP-DM 4 y 5: algoritmos, global frente a local, ablación, adaptación, prueba 2026
src/<paquete>/
  medallon.py, metricas.py     se reutilizan
  coes.py                      nuevo: rutas del IEOD por año, descarga retomable y lectura por contenido
  exogenas.py                  nuevo: ERA5, ICEN, Niño 1+2, eventos, SAIDI, feriados y cuarentena, con su rezago
  variables.py, modelos.py,    se generalizan: resolución, horizonte y horas de mayor demanda como parámetros
  evaluacion.py                (hoy fijos en 10 min, 6 pasos y 19-22 h)
app/                           backend FastAPI y frontend (ver la spec de la app)
src/<paquete>/tablas/          departamentos, empresas y subestaciones → área, ciudades de ERA5, feriados y cuarentena,
                               versionadas con su fuente (data/ no se versiona)
docs/
  negocio.md, datos.md         se reescriben para el caso peruano
  peru/                        la investigación de datos
  antecedentes/                Tetuán y Ceuta
  superpowers/specs/
experimentos/                  historico/ y ceuta/ como antecedente; peru/verificacion/ como evidencia
```

## 11. Riesgos

| Riesgo | Mitigación |
|---|---|
| El IEOD cambia de formato y de rutas según el año | El punto de control del §9 antes de la descarga masiva |
| La asignación de eventos y del SAIDI a un área es ambigua | Tablas versionadas con su fuente. Lo que no se asigne queda como indicador del SEIN |
| La temperatura de 2026 está fuera del rango de entrenamiento | Es parte de la pregunta. Se reporta como prueba de extrapolación; el objetivo en razón y el reentrenamiento son las defensas |
| El supuesto de colaboración puede parecer optimista | El error de pronóstico simulado se hace explícito y se prueba con dos niveles de error |
| El dato preliminar se revisa después | La fecha de descarga queda en la procedencia, y no se mezcla el portal con el IEOD |
| Deriva: el pico pasó al mediodía | Validación en el año más reciente; horas de mayor demanda por área y por año |
| La rúbrica nombra Streamlit | Riesgo aceptado. La app igual ejecuta el modelo |

## 12. Plan: dependencias, puntos de control y recorte

Sin fechas por fase: el único plazo fijo es la **entrega de la semana 15**, con la fecha exacta a confirmar en el
aula virtual. Los beads la ubican entre fines de noviembre y la primera semana de diciembre.

**Fases, en orden de dependencia.** Se pueden empezar en paralelo:
- la generalización de `variables.py`, `modelos.py` y `evaluacion.py`;
- las tablas de asignación y los feriados;
- la base de la app con datos de prueba.

| Fase | Depende de | Entregable | Punto de control | Si falla |
|---|---|---|---|---|
| 0a. Rutas e inventario del IEOD | — | Un anexo por año leído (hecho: 2016-2026 bien, 2015 sin la hoja) | SEIN = N + C + S en los once años | Caer al SEIN del portal como serie única; las áreas pasan a ser un extra |
| 0b. Descarga masiva y exógenas | 0a | Bronze completo en el Drive; ERA5, ICEN, Niño 1+2, SAIDI, eventos | Archivos por mes contra el calendario | Usar solo los años completos y declararlo |
| 0c. Silver y gold | 0b y las tablas | Silver auditado en el Drive y en HF | Auditoría: huecos marcados y SEIN = N + C + S en todos los días | Acortar el origen móvil a los años buenos |
| 1. Comprensión y preparación | 0c | Notebook 01, con la cuota de usuarios libres por área (falta el lector de `DEMANDA_UL`) | Unión de silver y exógenas sin duplicados; pruebas de la regla de información; tabla de cuota de usuarios libres | — |
| 2. Modelado | 1 y la generalización | Notebook 02: algoritmos, global frente a local con M0 | M0 le gana a la mejor referencia en las tres áreas en la validación | Si no, el problema no es de exógenas: revisar el objetivo y los rezagos antes de la ablación |
| 3. Ablación y adaptación | 2 | M0-M4, la ablación que quita un grupo y las cinco variantes de adaptación | M3 frente a M0 en 2025, con su intervalo | Si cruza el cero ya en 2025, se ajusta la narrativa antes de redactar |
| 4. Prueba 2026 y app conectada | 3 | Resultados finales; el backend sirve el modelo final | Contrato de la API probado en el CI | La app muestra solo el modelo elegido |
| 5. Paper y exposición | 4 | Short paper y ensayo | — | — |

**Orden de recorte si no alcanza** (de primero a último):
1. M4 (el SAIDI queda solo para estratificar).
2. Random Forest.
3. La variante "reentrenar cuando cambia la alerta" (queda la semanal).
4. Global frente a local (se queda el que gane con M0).
5. El origen móvil se acorta a 2025.
6. Las fallas por área pasan al SEIN.
7. El horizonte de 24 h por área se reduce al SEIN.
8. Extras de la app (mapa, reproducción de 24 h).
9. Las áreas pasan al SEIN del portal.

El modelado (5 puntos) se protege antes que la app (2 puntos).

## 13. Decisiones abiertas

1. **Nombre del repo y del paquete.** Propuesta: renombrar el repo a `sein-power-forecast` (GitHub redirige el nombre
   viejo) y el paquete a `pronostico_demanda`, en el mismo PR que generaliza `variables.py`, `modelos.py` y
   `evaluacion.py`, porque ese PR ya toca todos los imports.
2. **El error simulado del pronóstico de temperatura a un día:** confirmar σ = 1 y 2 °C con la verificación del ECMWF.
3. **Confirmar los departamentos de cada área operativa** con el documento del COES.
4. **La fecha exacta de la entrega.**
