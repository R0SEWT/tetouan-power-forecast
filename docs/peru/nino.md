# Datos abiertos de El Niño (ENSO y El Niño Costero) y su uso en un caso predictivo del sector eléctrico peruano

*Insumo para el TB1 de Metodología para Data Science (UPC). Verificado el 23 de octubre de 2026. Las cifras salen de descargas y scripts reproducibles, detallados abajo. Conviene validarlas con un especialista (ENFEN/IGP, COES u Osinergmin) antes de citarlas en el short paper.*

---

## 0. Resumen ejecutivo

- **Los índices son buenos, pequeños y abiertos.** El ICEN oficial (IGP/ENFEN), el ONI y el RONI (NOAA CPC), y el Niño 1+2 OISST pesan menos de 150 KB cada uno, no tienen huecos y se bajan sin registro.
  - El ICEN (1950-01 a 2026-08, 920 meses) se reproduce casi exacto desde ERSSTv5: RMSE de 0,025 °C entre 2006 y 2025.
  - Correlaciones: con el Niño 1+2 OISST trimestral, r = 0,97; con el ONI, r = 0,69. Miden fenómenos distintos.
- **Su principal limitación es el rezago.** El ICEN definitivo del mes *m* se publica hacia el día 10–20 de *m+2*. El ICENtmp de *m* sale hacia el día 11 de *m+1* y luego se revisa: en agosto de 2026 pasó de 3,73 a 3,98. Para predecir hay que usar ICEN(t−2) o la TSM semanal de Niño 1+2, que tiene unos 9 días de rezago.
- **Hubo cambios de versión que conviene documentar:**
  - En diciembre de 2024 ENFEN cambió la metodología del ICEN. El nuevo método da en promedio +0,22 frente al anterior, con un máximo de 0,72, sobre todo antes de 1981.
  - Entre marzo y octubre de 2026 NOAA rehízo toda la serie del ONI con ERSSTv6. La diferencia llega a 0,44 en la década de 1950 y a 0,12 en la de 2020.
  - El archivo de Niño mensual ERSSTv5 de CPC quedó congelado en junio de 2026.
  - En 2026 ENFEN pasó a usar el RONI para el Niño 3.4.
- **2017 y 2023-24 se ven con claridad:**
  - 2017: ICEN de 1,31 (moderado) con un ONI neutro de 0,32. Es el caso típico de "Niño Costero".
  - 2023-24: ICEN de 2,92 (fuerte), unos 5 meses antes del pico del ONI (1,99).
  - **2026 está en curso y es extraordinario:** ICEN de 3,98 en agosto, el mayor desde 1997-98 (4,08); anomalía semanal de Niño 1+2 de +5,3 °C. ENFEN prevé que se mantenga extraordinario hasta enero de 2027, con récords de temperatura del aire en la costa.
- **Los datos de estaciones de SENAMHI no son una fuente abierta práctica.** La descarga histórica pide registro, login y captcha, y el conjunto horario en datosabiertos.gob.pe bloquea las descargas automáticas. El reanálisis ERA5 (vía Open-Meteo, CC BY 4.0) es la alternativa abierta. NASA POWER no sirve para Lima: su celda tiene 1 195 m de altitud.
- **Evidencia sobre la electricidad:** es sólida para la parte física y para daños puntuales; para demanda y costos marginales es escasa o viene de prensa. No encontré un estudio revisado por pares que cuantifique el efecto de El Niño sobre la demanda del SEIN o de Lima. Eso es un vacío que el TB1 puede atacar.
- **Problema más factible:** pronosticar la demanda eléctrica (SEIN o un área) con temperatura ERA5 e ICEN/Niño 1+2 rezagados, o clasificar días o meses de demanda anómala. El efecto de El Niño debe entrar a través de la temperatura de la costa, no como un indicador binario.

---

## 1. Tabla de fuentes

Columnas: **Res./cobertura** = resolución y cobertura; **Rezago** = rezago de publicación medido; **Abierta** = si califica como fuente abierta (sí, no o parcial).

| Fuente | Variable | Res./cobertura | Rezago | Acceso | Licencia | Abierta | Verificado (23-oct-2026) |
|---|---|---|---|---|---|---|---|
| **ICEN oficial** (ENFEN 2024, publicado por el IGP) | Media móvil de 3 meses de la anomalía de TSM en Niño 1+2 (ERSSTv5, climatologías móviles al estilo del ONI) | Mensual, 1950-01 a 2026-08 (920 valores) | Definitivo del mes *m*: entre los días ~10 y 20 de *m+2* (en 7 de 8 snapshots, el último valor era *M−2*) | `http://met.igp.gob.pe/datos/ICEN.txt` (TXT, 16 KB). En minúsculas da 404. | Sin licencia explícita; información pública estatal, sin registro | **Sí de facto.** No está en datosabiertos.gob.pe ni en Google Dataset Search. | Sí; Last-Modified: 19-oct-2026 |
| ICEN tradicional 81-10 / 91-20 e ICENr (no oficiales) | Mismo cálculo con climatología fija; el ICENr resta la tendencia de calentamiento | Mensual, 1950 a 2026-08 (ICENr hasta 2026-06) | Igual que el ICEN | `.../datos/ICEN_81_10.txt`, `ICEN_91_20.txt`, `ICENr.txt` (16 KB c/u) | Igual | Sí | Sí |
| Índices E y C (Takahashi et al. 2011, IGP) | Modos de TSM del Pacífico este (E) y central (C), por componentes principales | Mensual, 1854 a 2026-09 | ~1 mes | `.../datos/ecindex_ersstv5.txt` (79 KB) | Igual | Sí | Sí |
| Lista de eventos y umbrales | Eventos Niño/Niña Costeros 1950–2026 con magnitud; umbrales de la NT ENFEN 01-2024 | Por evento | Al cierre del evento | `.../datos/lista_eventos_ICEN.html`; Nota Técnica ENFEN 01-2024 (PDF, 1 MB) | Igual | Sí | Sí. La tabla HTML tiene 13 errores (ver §2.1). |
| **Comunicados oficiales ENFEN** y estado de alerta | Estado (No activo, Vigilancia o Alerta, de Niño o Niña Costero), magnitud esperada y pronósticos | Quincenal, 2016 a 2026 (171 comunicados en el sitemap) | 0 días (es el producto operativo) | `enfen.imarpe.gob.pe/download/<slug>/?wpdmdl=<id>`; PDF de 0,3–0,8 MB c/u. La línea "Estado del sistema de alerta: …" se puede extraer con pdftotext. | Sin licencia explícita | **Parcial:** no hay una serie consolidada y hay que construirla | Sí: 3 comunicados leídos (2017, 2023, 2026); lista vía `wpdmpro-sitemap.xml` |
| Informes técnicos ENFEN | Tablas de ICEN e ICENtmp, RONI, ONI, caudales por pentadas, embalses y anomalías de temperatura del aire | Quincenal | 0 días | PDF de **~17 MB c/u**: bajarlos solo en Colab | Igual | Parcial (solo PDF) | Sí: bajé 1 (N°16-2026) |
| **ONI** (NOAA CPC) | Media de 3 meses de la anomalía en Niño 3.4, ERSST**v6** desde 2026, bases centradas | Trimestral móvil, DJF 1950 a JAS 2026 | ~3–5 días tras cerrar el último mes del trimestre: JAS estaba disponible el 3 de octubre | `cpc.ncep.noaa.gov/data/indices/oni.ascii.txt` (23 KB) | Dominio público (gobierno de EE.UU.) | **Sí.** Está en Google Dataset Search vía HDX (CC0) y espejos en Kaggle. | Sí |
| RONI (CPC) | ONI relativo: anomalía de Niño 3.4 menos la anomalía tropical. ENFEN lo usa desde 2026. | Trimestral móvil, 1950 a JAS 2026 | Igual que el ONI | `.../indices/RONI.ascii.txt` (15 KB) | Dominio público | Sí | Sí |
| **Niño 1+2 y 3.4, OISST v2.1** (CPC) | TSM absoluta y anomalía (base 1991-2020) | Mensual 1982-01 a 2026-09; semanal desde 1981-09 hasta 2026-10-14 (2 355 semanas, sin huecos) | Mensual ~5 días; semanal ~9 días | `.../indices/sstoi.indices` (39 KB); `.../indices/wksst9120.for` (149 KB) | Dominio público | Sí | Sí |
| Niño mensual ERSSTv5 (CPC) | TSM y anomalía de Niño 1+2, 3, 4 y 3.4 | Mensual, 1950 a **2026-06 (congelado)** | Sin actualizar desde el 5-ago-2026; ya no figura en el índice de CPC | `.../indices/ersst5.nino.mth.91-20.ascii` (67 KB) | Dominio público | Sí, pero obsoleto | Sí. NCEI sigue publicando ERSSTv5 en netCDF (septiembre de 2026, publicado el 3-oct). |
| **SENAMHI**: estaciones históricas (mapa de descarga) | Temperatura y precipitación diarias por estación | 293 estaciones. Ejemplo: Piura "Miraflores", 1971–2013 | Las series históricas terminan antes de la actualidad (Miraflores, en 2013) | `senamhi.gob.pe/mapas/descarga-datos/...` → **"Ingreso": correo, contraseña y captcha; requiere registro** | No indicada | **No** (registro) | Sí: no me registré ni la usé |
| SENAMHI en datosabiertos.gob.pe: "Variables meteorológicas de estaciones automáticas de intercambio internacional" (GBON/RBON) | Temperatura, humedad relativa y precipitación horarias validadas | Horaria; estaciones y periodo no indicados en la ficha | Última modificación: 2025-09-08 | CSV en `datosabiertos.gob.pe/sites/default/files/...`. **Las descargas automáticas reciben HTTP 418 (WAF)**; hay que bajarlo desde el navegador. | ODC-BY | Sí (portal oficial) | Ficha leída; CSV **no** descargado |
| SENAMHI en datosabiertos.gob.pe: "Datos hidrometeorológicos de libre acceso" | Solo enlaces a las páginas de SENAMHI | — | — | HTML | "License Not Specified" | No (redirige al mapa con login) | Sí |
| PISCO (grilla de SENAMHI) | Precipitación y temperatura diarias en grilla | ~0,1° | — | IRI Data Library: **ahora redirige a login** | — | No en la práctica | Sí (302 a `/auth/login`) |
| **Open-Meteo ERA5** (y ERA5-Land) | Tmax, Tmin, Tmedia, temperatura aparente y precipitación diarias u horarias | ERA5 0,25°, desde 1940; ERA5-Land 0,1°, desde 1950 (**sin precipitación**) | ~5 días: el 23-oct ya había datos hasta el 15-oct | API `archive-api.open-meteo.com/v1/archive` (CSV, ~130 KB por ciudad y década) | **Datos de la API bajo CC BY 4.0** (atribución y enlace); ERA5 © Copernicus | Sí | Sí. La API devolvió 503 ("overloaded") durante ~10 minutos; funcionó al reintentar. |
| NASA POWER (MERRA-2) | T2M, Tmax, Tmin, precipitación corregida y humedad relativa diarias | 0,5° × 0,625°, desde 1981 | No verificado | API `power.larc.nasa.gov/api/temporal/daily/point` (CSV de 144 KB por ciudad), sin clave | Datos NASA de libre uso (no verifiqué los términos exactos) | Sí | Sí. **Celda de Lima a 1 195 m de altitud: no sirve para Lima.** |
| IMARPE | TSM y anomalías en 10 estaciones costeras (de Tumbes a Ilo) | Boletines semanales | Semanal | PDF en `repositorio.imarpe.gob.pe` (un PDF por semana) | No indicada | **No** como serie (habría que extraerla de PDFs). No encontré el índice LABCOS como dato descargable. | Parcial (búsqueda web) |

**Descargado en total:** ~27 MB. 17 MB corresponden a un solo informe técnico de ENFEN; el resto son archivos de menos de 1 MB.

---

## 2. Calidad de los datos (resultados con cifras)

Scripts en [`experimentos/peru/verificacion/nino/`](../../experimentos/peru/verificacion/nino/): `indices_qc.py`, `oni_rev.py`, `clima_qc.py`, `lag_util.py` y `anom_2026.py`. Las descargas no se versionan.

### 2.1 Huecos y consistencia

- **ICEN oficial:** 920 meses (1950-01 a 2026-08), 0 huecos, 0 NaN y 0 duplicados.
- **ICEN tradicional:** solo falta 1950-01, por el borde de la media móvil.
- **ONI:** 920 trimestres, sin huecos. **OISST semanal:** 2 355 semanas con paso exacto de 7 días.
- **La tabla HTML de la lista de eventos del IGP no coincide con `ICEN.txt` en 13 meses:**
  - 1951-04 tiene el signo cambiado (−0,26 en el HTML, +0,26 en el TXT).
  - Todo 1954 conserva valores del método de 2012. Ejemplo: 1954-01 vale −1,23 en el HTML y −0,75 en el TXT.
  - **Usar siempre el TXT.**

### 2.2 Revisiones del ICEN: temporal frente a definitivo y cambios de método

Comparé 7 snapshots de `ICEN.txt` en la Wayback Machine (2017-03 a 2025-03) con el archivo actual y con el Informe Técnico ENFEN N°16-2026.

**Los valores definitivos no se revisan de un mes a otro.** Entre snapshots del mismo método la diferencia es exactamente 0,00: tres snapshots de 2017 y tres de 2023-2024.

**Cambia la versión del dato o del método:**

| Cambio | Efecto medido |
|---|---|
| ERSST v3b → v5 (entre nov-2017 y ene-2023) | Diferencia máxima de 0,55 y media de 0,10. Enero de 2017 pasó de 0,60 a 0,92 y marzo de 2017, de 1,11 a 1,42. |
| Método 2012 → 2024 (NT ENFEN 01-2024: climatologías móviles de 30 años, nuevos umbrales por percentiles) | Sesgo medio de +0,22 y diferencia máxima de 0,72; r = 0,970. Por periodo: 1950-80, +0,50; 1981-2005, +0,06; 2006-2024, −0,03 (máximo 0,27). |
| Temporal → definitivo (ICENtmp con pronóstico NMME) | Agosto de 2026: **ICENtmp = 3,73** (informe del 11-sep-2026) frente al **ICEN definitivo = 3,98** (archivo del 19-oct). Diferencia de **+0,25**; el temporal subestimó. Es un solo caso, con un evento en rápido crecimiento. |
| Mismo mes, otros índices | ONItmp de agosto de 2026 = 2,35 frente al ONI JAS de 2,16 (−0,19); RONItmp = 1,79 frente a 1,69 (−0,10). |

**Para el modelo:** usa la versión vigente (ENFEN 2024) y fija la fecha de descarga, para que el dataset sea reproducible. Documenta que los valores anteriores a 2025 publicados con el método de 2012 difieren.

### 2.3 Revisión del ONI (NOAA cambió a ERSSTv6 en 2026)

Comparé el snapshot de marzo de 2026 con el archivo actual:

- **Se revisó toda la serie.** Diferencia máxima por década: 1950s, 0,44; 1980s, 0,24; 2010s, 0,19; 2020s, 0,12.
- Ejemplos: el pico de NDJ 2015 bajó de 2,75 a 2,59, y el de NDJ 2023, de 2,06 a 1,99.
- La página de CPC ya rotula el ONI como "ERSSTv6 (centered base periods)". El archivo de Niño mensual ERSSTv5 quedó congelado en 2026-06.
- **Implicación:** las copias en Kaggle o HDX pueden ser de la versión anterior. Hay que bajar el ONI directo de CPC y anotar la fecha.

### 2.4 Coherencia entre índices (1982-2025, mensual)

| | ICEN | ONI | Niño 1+2 OISST (3 meses) | Niño 3.4 OISST (3 meses) |
|---|---|---|---|---|
| ICEN | 1 | 0,69 | 0,97 | 0,67 |
| ONI | 0,69 | 1 | 0,67 | 0,98 |

- **ICEN reconstruido** como media de 3 meses de la anomalía de Niño 1+2 ERSSTv5 (CPC, 91-20): coincide con el oficial en 2006-2025 con RMSE de 0,025 y diferencia máxima de 0,17. Con OISST, el RMSE es de 0,21 y la diferencia máxima de 0,71, porque es otro producto de TSM.
- **Acuerdo de fases** (n = 527 meses):
  - Meses cálidos: 130 con ICEN > 0,5 y 141 con ONI ≥ 0,5; **coinciden solo 92**.
  - Meses fríos: 126 con ICEN y 140 con ONI; coinciden solo 58.
  - **ICEN y ONI no son intercambiables.** Para la costa (Lima, Piura) manda el ICEN; para la sierra centro-sur y la Amazonía (hidrología del Mantaro y del sur) manda el ONI, el RONI o el índice C (ver §3.2).

### 2.5 Eventos 2017, 2023-24 y 2026

| Mes | ICEN | ONI | Niño 1+2 OISST (mes) |
|---|---|---|---|
| 2017-01 | 0,89 | −0,08 | 1,07 |
| 2017-02 | 1,29 | 0,08 | 1,14 |
| 2017-03 | **1,31** | 0,27 | 1,83 |
| 2017-04 | 0,92 | 0,32 | 0,77 |
| 2023-03 | 1,53 | −0,11 | 1,52 |
| 2023-07 | **2,92** | 1,00 | 3,21 |
| 2023-12 | 1,67 | **1,99** | 1,41 |
| 2026-08 | **3,98** | 2,16 | 4,08 (septiembre: 4,69) |

- **2017** es un Niño Costero claro: ICEN moderado (enero a abril) con un ONI neutro, de 0,32 como máximo.
  - Pico semanal de Niño 1+2: +2,3 °C el 15-mar-2017. El Niño 3.4 semanal no pasó de +0,5.
  - El ICEN de 1,31 está apenas sobre el umbral de "moderado" (1,3); con el método de 2012 valía 1,42.
- **2023-24:** "fuerte" de marzo de 2023 a febrero de 2024. El pico del ICEN (julio de 2023) adelantó en ~5 meses al pico del ONI (diciembre de 2023). Pico semanal: +3,5 °C (19-jul-2023).
- **2026 (en curso):** "extraordinario" desde marzo de 2026.
  - ICEN de 3,98 en agosto, frente a 4,08 en 1997-98 y 4,32 en 1982-83. Anomalía semanal de +5,3 °C el 30-sep-2026.
  - El Comunicado Oficial ENFEN N°18-2026 (16-oct-2026) prevé magnitud extraordinaria hasta enero de 2027 y fuerte hasta el otoño de 2027.
  - El Informe Técnico ENFEN N°16-2026 reporta anomalías de la temperatura máxima del aire en septiembre de +6,3 °C en la costa centro y +4,8 °C en la costa norte, con récords de temperatura mínima.

### 2.6 Rezago de publicación y uso como predictor

| Índice | Disponible para predecir el mes *t* |
|---|---|
| ICEN definitivo | **ICEN(t−2)** como máximo (publicado entre el día ~10 y 20 de *t*) |
| ICENtmp | ICENtmp(t−1), con revisión posterior (+0,25 en el caso medido) |
| ONI o RONI | ONI(t−2): el trimestre centrado en *t−2* sale ~3 días después de cerrar *t−1* |
| Niño 1+2 OISST mensual | Valor de *t−1*, unos 5 días después de cerrar el mes |
| Niño 1+2 OISST semanal | Semana anterior (~9 días de rezago) |
| ERA5 (Open-Meteo) | Hasta *t* − 5 días |

**Utilidad medida en 2015-2024** (anomalía mensual de la temperatura media ERA5 frente a cada predictor):

| Ciudad | ICEN(t) | ICEN(t−2) | Niño 1+2 OISST(t−1) |
|---|---|---|---|
| Lima | 0,91 | 0,79 | 0,82 |
| Piura | 0,88 | 0,81 | 0,85 |
| Chiclayo | 0,91 | 0,80 | 0,85 |
| Tumbes | 0,77 | 0,79 | 0,81 |

- Solo verano (diciembre a marzo, n = 40): r de 0,65 a 0,77.
- El ICEN es muy persistente: autocorrelación de 0,96 a 1 mes, 0,87 a 2 meses y 0,76 a 3 meses. Por eso el rezago cuesta poco en información.

### 2.7 Series diarias de clima (ERA5 vía Open-Meteo y NASA POWER, 2015-2024)

- **Completitud:** ERA5 trae 3 653 días por ciudad (Lima, Piura, Tumbes, Chiclayo) sin NaN ni casos de Tmin > Tmax. **ERA5-Land no trae precipitación** (100 % NaN), como dice la documentación.
- **Ciclo estacional de Tmax:**
  - Lima con ERA5: 26,8 °C en febrero y 21,1 °C en agosto; amplitud de 5,7 °C, plausible.
  - Lima con NASA POWER: 24,2 y 22,2 °C; amplitud de 1,9 °C, porque la celda mezcla sierra (1 195 m). Sesgo de la temperatura media ERA5 − POWER: +2,6 °C en Lima y +2,1 °C en Chiclayo.
  - **POWER no se recomienda para la costa.**
- **La precipitación de ERA5 en Lima es sospechosa:** 137 mm al año, frente a una ciudad hiperárida con normales del orden de 10–20 mm (verificar con las normales de SENAMHI). No conviene usar la precipitación de ERA5 para Lima.
- **La señal de El Niño se ve con claridad:**
  - Lluvia de febrero y marzo de 2017 con ERA5: Piura 846 mm (climatología de 188), Tumbes 1 178 (403) y Chiclayo 452 (111).
  - Marzo de 2017 en Piura: 631 mm, frente a un promedio de marzo de 139.
  - Marzo de 2023 (ciclón Yaku) en Piura: 206 mm.
  - No tengo datos de estación para comparar: el reanálisis suele subestimar la lluvia convectiva extrema.
- **Días de calor en Lima** (Tmax ≥ 27,1 °C, el percentil 90) entre enero y marzo:

| Año | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|---|---|---|---|---|
| Días | 16 | **64** | **58** | 0 | 27 | 24 | 5 | 2 | **54** | **79** |

  Los veranos con Niño (2016, 2017, 2023, 2024) suman entre 54 y 79 días calurosos; los de La Niña (2018, 2021, 2022), entre 0 y 5.
- **2026 en vivo:** la anomalía de Tmax en Lima fue de +4,2 °C en septiembre y de +4,8 °C en octubre (días 1 a 15). El máximo mensual de 2015-2024 fue +2,9 °C, así que 2026 está fuera del rango de entrenamiento. Un modelo entrenado en 2015-2024 tendrá que **extrapolar**.
- **Advertencia metodológica:** en las celdas costeras, la temperatura a 2 m de ERA5 se ancla a la TSM que el reanálisis asimila. Parte de la correlación de 0,9 con el ICEN es estructural. Conviene validarla con datos de estación (SENAMHI GBON) si se consiguen.

---

## 3. Evidencia del efecto de El Niño sobre la electricidad en el Perú

Leyenda: **[V]** fuente primaria o revisada por pares que leí; **[P]** documento oficial que leí; **[M]** solo prensa o fuente secundaria, sin verificar contra la fuente primaria.

### 3.1 Demanda

- **[P] El pico anual del SEIN cae en verano.** El informe "Prospectiva del sector eléctrico" del MINEM (DGE), de noviembre de 2024, con datos del COES, indica que la máxima demanda de febrero de 2024 seguía siendo la más alta del año. Ese verano siguió al Niño 2023-24 (ICEN de 0,88 en febrero de 2024). El informe **no** atribuye el pico a El Niño.
- **[V, propio] Los veranos con Niño son mucho más calurosos en Lima** (§2.7). Es el mecanismo plausible: más refrigeración en Lima y en la costa norte. Pero **no encontré un estudio peruano revisado por pares que cuantifique la elasticidad de la demanda a la temperatura en Lima o en la costa norte.**
  - El único estudio peruano hallado es sobre Huancayo (IOP Conf. Ser. 2022, doi:10.1088/1755-1315/1008/1/012001). Es una ciudad andina fría donde domina la calefacción, así que no se extrapola a la costa.
  - **Es un vacío de literatura que el TB1 puede atacar.**
- **[M]** Una nota de prensa atribuye parte del crecimiento de la demanda no minera al uso de aire acondicionado en hogares y comercios. No tiene cifras.

### 3.2 Oferta: hidroelectricidad, lluvias en el norte y sequía en el sur

Esta parte física está bien respaldada:

- **[V]** Lavado-Casimiro et al. (2013), *Adv. Geosci.* 33, doi:10.5194/adgeo-33-33-2013. Analizan 20 cuencas entre 1968 y 2006. En años de Niño fuerte el caudal **sube con fuerza en el centro-norte de la vertiente del Pacífico y baja en la mayoría de las demás estaciones**.
- **[V]** Rau et al. (2016), *Int. J. Climatol.*, doi:10.1002/joc.4693. Con 145 estaciones de 1964 a 2011: con Niños extremos aumenta la lluvia en la parte baja del norte; con Niños del Pacífico central disminuye en las partes altas de la vertiente del Pacífico.
- **[V, citado por IGP/ENFEN]** Sulca et al. (2017), *Int. J. Climatol.*, doi:10.1002/joc.5185. El "sabor" de El Niño importa: el tipo del Pacífico este (E) pega en la costa y el central (C) en la sierra y la Amazonía.
  - **Implicación:** para la hidroelectricidad del centro y sur (Mantaro, sur andino) el predictor adecuado es el ONI, el RONI o el índice C, no el ICEN.
- **[P] ENFEN, Comunicado Oficial N°18-2026:**
  - Prevé caudales sobre lo normal desde noviembre en los ríos Tumbes, Chira, Piura, La Leche y Jequetepeque, y desde diciembre en el Rímac y el Chillón.
  - Prevé caudales bajo lo normal en el Ucayali, Huallaga, Apurímac y Vilcanota, y en el sur andino (Arequipa, Moquegua, Tacna).
  - Embalses al 58 % de la capacidad nacional (al 10-sep estaban al 67,7 %, según el Informe Técnico N°16).
- **[V]** Foucher et al. (2023), *HESS* 27:3191, doi:10.5194/hess-27-3191-2023: hipersedimentación del embalse de Poechos ligada a ENSO, con aportes de hasta 90 % del bosque seco durante el Niño Costero de 2016-17.
  - Esto afecta la vida útil de embalses de uso múltiple. No verifiqué la capacidad de las centrales asociadas a Poechos.
- **[V]** Castillo et al. (2018), *IOP Conf. Ser.* 154:012002: el Niño de 2017 elevó los caudales del Chira y el Piura y llenó Poechos. Los autores proponen aprovechar la complementariedad hidro-eólica en el norte.
- **[M] 2023: menor hidroelectricidad y costos marginales altos.**
  - *Gestión* (22-sep-2023), citando al MINEM: la generación hidráulica cayó ~8 % entre enero y julio de 2023, y la térmica a gas subió ~27 %.
  - El mismo artículo cita a un gerente de Celepsa: costos marginales por encima de US$ 200/MWh, frente a ~35 un año antes. También menciona un informe de Osinergmin (N°711-2022-GRT) con un escenario seco de US$ 100/MWh.
  - **Matiz:** la caída empezó a fines de 2022, en plena La Niña. Influyeron también la sequía del sur y la indisponibilidad de gas, de modo que **no es atribuible solo a El Niño**.
  - Según resultados de búsqueda, el INEI reportó para julio de 2023 una caída de la hidroelectricidad de −18,3 % interanual. No pude abrir el PDF del INEI por un error de certificado.

### 3.3 Daños e interrupciones

- **[P, fabricante] Niño Costero 2017:** la central de Callahuanca (82–84 MW, cuenca del Rímac) sufrió daños severos por huaicos a inicios de 2017 y se detuvo por completo (ANDRITZ Hydronews). Prensa del sector [M] reporta que también pararon Huampaní, Moyopampa y Matucana, y una rehabilitación de unos US$ 40–45 millones.
- **[V]** Yglesias-González et al. (2023), *PLOS ONE*, doi:10.1371/journal.pone.0290767 (con K. Takahashi). Cifras del Niño Costero de 2017:
  - 1,9 millones de afectados y 169 muertos;
  - reconstrucción pública de US$ 7 712 millones (~3,5 % del PBI).
  - **La tabla de reconstrucción no tiene una línea de electricidad** (las redes son en gran parte concesionadas). Los daños eléctricos de 2017 **no** están en la cifra oficial de reconstrucción.
- **[M/P]** Una tesis de la UNI (2019) describe daños a instalaciones de transmisión en Piura en 2017 y sobrecarga de la subestación Piura Oeste. Hay resoluciones de Osinergmin contra Enosa en 2017, pero no son específicas del Niño.
- **Ciclón Yaku (marzo de 2023):**
  - [P] Reporte de SENAMHI en SINIA: ciclón "de características tropicales no organizado"; lluvias en Tumbes, Piura y Lambayeque.
  - [M] Prensa citando al COEN: 58 muertos.
  - **No encontré cifras de cortes eléctricos de Yaku** (Osinergmin o Enosa).
- **[V]** Peng et al. (2024), *Sci. Adv.*, doi:10.1126/sciadv.adk8646: el Niño Costero de 2023 fue predecible con 1 mes de anticipación. Respalda usar la TSM de Niño 1+2 como señal temprana.
- **[V]** French et al. (2020), *IJDRR*, doi:10.1016/j.ijdrr.2020.101539: causas institucionales de los desastres del Niño en el Perú. Es contexto, no trae datos eléctricos.

---

## 4. Problemas predictivos posibles, de más a menos factible

Todos requieren cruzar con datos eléctricos (COES, Osinergmin, MINEM), que inventaría la otra investigación.

| # | Problema | Tipo y objetivo | Horizonte | ¿Basta la resolución mensual de los índices? | Datos eléctricos a cruzar | Factibilidad y riesgos |
|---|---|---|---|---|---|---|
| **1** | **Pronóstico de la demanda (SEIN o área Centro/Lima) con covariables climáticas** | Regresión de la energía diaria (MWh) o de la demanda máxima diaria (MW), o del total mensual | Día siguiente a 7 días (diaria); 1–3 meses (mensual) | **Para la diaria, no:** hacen falta la temperatura diaria ERA5 (o un pronóstico) y los feriados. **Para la mensual, sí:** ICEN(t−2) o Niño 1+2(t−1). | Demanda diaria y cada 30 min del COES (idealmente por área: Norte, Centro, Sur) | **Alta.** El clima entra a través de la temperatura; la señal de Niño en la temperatura de Lima es fuerte (r ≈ 0,9). Riesgos: tendencia y crecimiento, COVID 2020 y el cambio de régimen de 2026 (extrapolación). |
| **2** | **Clasificar días o meses de demanda anómala** (por ejemplo, residuo sobre el percentil 90, o día de máxima demanda del mes) | Clasificación binaria | Diaria o mensual | Igual que el #1 | Igual que el #1 | **Alta.** Es una buena alternativa si la regresión queda débil; la métrica F1 o AUC es fácil de explicar en la app. Desbalance de clases manejable. |
| **3** | **Impacto en la generación hidroeléctrica** (total del SEIN o por cuenca o central: Mantaro, Rímac, norte) | Regresión de la producción hidro mensual (GWh) o de su anomalía | 1–6 meses | **Sí** (mensual). Usar el **ICEN para las centrales del norte y la costa y el ONI, RONI o índice C para el centro y sur andino**, más la lluvia (ERA5; PISCO si se consigue). | Producción por central y mes (COES); caudales y embalses (ANA, informes de ENFEN en PDF) | **Media.** La operación de embalses, los mantenimientos y las nuevas centrales confunden la señal. Solo hay ~4 eventos cálidos fuertes desde 2015 (poca muestra). |
| 4 | Régimen de costo marginal alto | Clasificación de meses con CMg sobre un umbral | 1–3 meses | Sí (mensual) | CMg por barra (COES), hidro y despacho térmico, disponibilidad de gas | **Media-baja.** El precio del gas, la congestión de transmisión y las fallas de Camisea pesan más que El Niño (2022-23 ocurrió en La Niña). |
| 5 | Riesgo de interrupciones en la costa norte (Enosa, Electronorte, Electronoroeste) | Clasificación de días o semanas con interrupción mayor, o regresión de SAIDI/SAIFI mensual | Días o semanas | **No:** el ICEN mensual es muy grueso. Se necesita lluvia diaria (ERA5, que subestima los extremos) o alertas de SENAMHI. | Interrupciones por evento o indicadores de calidad de Osinergmin (verificar si son abiertos y a qué resolución) | **Baja.** Pocos eventos, datos de interrupciones posiblemente no abiertos y lluvia extrema mal capturada por el reanálisis. |

**Recomendación para el TB1:** combinar el #1 con el #2 sobre el área Centro (Lima) o el SEIN. Con datos diarios del COES (2015-2026) y ERA5 diario de Lima:

- **Variables predictoras:** temperatura máxima, temperatura aparente, rezagos de la demanda, calendario y feriados, y como variables de régimen el ICEN(t−2) y el Niño 1+2 semanal.
- **Pregunta de negocio (CRISP-DM):** ¿cuánto sube la demanda en veranos con Niño Costero? El verano 2026-27 extraordinario sirve de motivación y de prueba fuera de muestra, presentada con cautela: es extrapolación.

---

## 5. Cómo bajar lo pesado en Colab (no lo hice aquí)

- **Serie histórica de estados de alerta de ENFEN (2016–2026):** se arma desde los 171 comunicados en PDF (~70–100 MB en total). Pasos:
  1. Leer los slugs que empiezan por `comunicado-oficial` en `https://enfen.imarpe.gob.pe/wpdmpro-sitemap.xml`.
  2. Para cada slug, abrir `https://enfen.imarpe.gob.pe/download/<slug>/` y extraer `?wpdmdl=<id>` con una expresión regular.
  3. Bajar el PDF y pasarlo por `pdftotext`. Extraer `Estado del sistema de alerta:\s*(.+)` y la fecha (ejemplo: "13 de abril de 2023").
  4. Convertirlo a una serie mensual: estado vigente a fin de mes.
  - Nota: en 2026 la línea es solo "Alerta de El Niño Costero" (sin el prefijo "Estado del sistema de alerta").
- **Informes técnicos de ENFEN** (~17 MB c/u): solo si se quieren las tablas de ICENtmp, caudales o embalses. La Tabla 3 trae el ICEN, el RONI, el ONI y sus valores temporales.
- **ERA5 horario de Lima y Piura, 2015–2026** (Open-Meteo, ~2–5 MB): `hourly=temperature_2m,apparent_temperature,relative_humidity_2m`. Si responde 503, reintentar.
- **SENAMHI GBON horario:** bajarlo desde el navegador (datosabiertos.gob.pe bloquea curl con HTTP 418). Revisar qué estaciones costeras incluye y su cobertura.

---

## 6. Lo que no pude verificar

- **Datos de estaciones de SENAMHI.**
  - No bajé el CSV horario GBON de datosabiertos (el WAF bloquea la descarga automática; no intenté sortearlo). Desconozco sus estaciones, periodo y tamaño.
  - La descarga histórica de estaciones exige registro, login y captcha: no me registré.
  - PISCO en IRI ahora pide login.
- **Climatología real de Lima** (lluvia anual y Tmax de febrero de estación) para validar los sesgos de ERA5. Comparé solo entre reanálisis.
- **Serie histórica completa de estados de alerta de ENFEN:** solo confirmé el formato en 3 comunicados (2017, 2023, 2026) y los títulos de 2026 (Vigilancia el 15 de enero; Alerta desde el 30 de enero). No sé si existen comunicados de 2015 en el sitio: el sitemap empieza en 2016.
- **El rezago del ICEN tiene pocos puntos:** 8 snapshots de Wayback y un solo caso de ICENtmp frente a definitivo (agosto de 2026). No medí la revisión típica del ICENtmp en otros eventos.
- **Si CPC tiene un archivo de Niño 1+2 mensual con ERSSTv6:** no lo encontré. Tampoco sé qué hará ENFEN con el ICEN si NOAA deja de producir ERSSTv5 (la NT 01-2024 prevé actualizar la metodología en 2031).
- **Licencias explícitas** del IGP y ENFEN (no las publican) y términos exactos de NASA POWER.
- **IMARPE:** no hallé el índice LABCOS ni series de TSM costera descargables; solo boletines semanales en PDF.
- **Efecto de El Niño en la demanda eléctrica peruana:** no hallé estudios revisados por pares para Lima, la costa norte o el SEIN.
- **Cifras eléctricas de 2023 (MINEM e INEI):** solo vía prensa y resultados de búsqueda. El PDF del INEI falló por certificado, y las presentaciones de Osinergmin al Congreso (oct. y dic. de 2023) devuelven 404.
- **Daños e interrupciones eléctricas:** no encontré cifras oficiales de Osinergmin o MINEM para el Niño Costero de 2017 ni para el ciclón Yaku de 2023. Tampoco cifras del sector eléctrico para 1997-98 (el informe "Las lecciones de El Niño" de la CAF no estaba accesible en texto).
- **Si las centrales asociadas a Poechos y otras del norte se afectaron en 2017 o 2023:** sin fuente.
- **Copias de ONI en Google Dataset Search o Kaggle:** no verifiqué si ya reflejan la revisión ERSSTv6 de 2026.

---

### Fuentes principales (enlaces)

- ICEN e índices del IGP: http://met.igp.gob.pe/variabclim/indices.html, http://met.igp.gob.pe/datos/ICEN.txt
- Nota Técnica ENFEN 01-2024 (definición operacional): https://enfen.imarpe.gob.pe/download/nota-tecnica-enfen-01-2024-definicion-operacional-de-los-eventos-el-nino-costero-y-la-nina-costera-en-el-peru/?wpdmdl=1905
- Nota Técnica ENFEN 02-2026 (sistema de alerta): https://enfen.imarpe.gob.pe/download/nota-tecnica-enfen-02-2026-sistema-de-alerta-ante-el-nino-costero-y-la-nina-costera/?wpdmdl=1988
- Comunicado Oficial ENFEN N°18-2026: https://enfen.imarpe.gob.pe/download/comunicado-oficial-enfen-n-18-2026/?wpdmdl=2165
- Informe Técnico ENFEN N°16-2026: https://enfen.imarpe.gob.pe/download/informe-tecnico-enfen-ano-12-n16-al-11-de-setiembre-de-2026/?wpdmdl=2159
- NOAA CPC, índices: https://www.cpc.ncep.noaa.gov/data/indices/; cambio de base del ONI: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_change.shtml
- HDX, ONI (CC0): https://data.humdata.org/dataset/monthly-oceanic-nino-index-oni
- Open-Meteo, API histórica y licencia: https://open-meteo.com/en/docs/historical-weather-api, https://open-meteo.com/en/licence
- NASA POWER: https://power.larc.nasa.gov/
- SENAMHI en datosabiertos: https://www.datosabiertos.gob.pe/dataset/variables-meteorologicas-de-las-estaciones-autom%C3%A1ticas-de-intercambio-internacional-servicio
- MINEM, Prospectiva del sector eléctrico (nov. 2024): https://cdn.www.gob.pe/uploads/document/file/7580102/5180087-prospectiva-del-sector-electrico-para-el-mes-de-noviembre-2024.pdf
- ANDRITZ Hydronews, Callahuanca: https://www.andritz.com/hydro-en/hydronews/hn32/callahuanca-peru
- Gestión (22-sep-2023), costos de generación: https://gestion.pe/economia/costos-para-generacion-electrica-se-disparan-y-hay-riesgo-que-eleve-tarifas-a-largo-plazo-noticia/
- SENAMHI, reporte del ciclón Yaku (SINIA): https://sinia.minam.gob.pe/sites/default/files/sinia/archivos/public/docs/reporte_-_ciclon_yaku_f_f_.pdf
- Artículos: los DOI van citados en el texto. Los busqué y leí sus resúmenes vía la API de OpenAlex, y el texto completo de PLOS ONE vía Europe PMC (PMC10522041).

*Nota de uso: este informe resume investigación y prensa de terceros, que son propiedad intelectual ajena. No contiene datos personales.*
