# Datos abiertos de electricidad en el Perú para el TB1: inventario verificado y calidad

Fecha de verificación: 23-oct-2026 (hora de Lima). Todo lo que figura como "verificado" se comprobó en el sitio con
peticiones reales o con muestras descargadas y analizadas con scripts de Python. Lo demás está marcado como tal.

Los scripts de verificación están en [`experimentos/peru/verificacion/energia/`](../../experimentos/peru/verificacion/energia/).
Las muestras descargadas no se versionan.

> Los datos del COES y los artículos de prensa citados son de terceros. Los consumos por cliente (Distriluz,
> Electro Puno) traen campos personales anonimizados a medias: el proyecto no los usa.

---

## 0. Resumen

1. **La mejor fuente con diferencia es el COES**, y es la única con datos subhorarios de demanda. Tiene:
   - la demanda del SEIN cada **30 min** desde al menos el año 2000, casi en tiempo real;
   - la demanda **por barra/subestación** de las 31 distribuidoras, cada **30 min**, desde **jun-2014**;
   - la demanda **por área** (Norte, Centro, Sur), cada 30 min, dentro del IEOD diario desde oct-2011.

   Cubre el Niño Costero de 2017, el de 2023 y el episodio de 2026.
2. **La demanda del SEIN es la serie más limpia**: 207 072 registros (2015–2026), sin huecos ni duplicados.
   - **Benchmark oficial incorporado:** la "Programación Diaria" del COES, con un MAPE del 1,5–1,9 %.
   - **Desfase de nivel:** está ~1–1,5 % por encima de las cifras oficiales (IEOD, Estadística Anual).
3. **La demanda por barras es el análogo directo de Tetuán** (subestaciones, 30 min, 12 años), pero viene sucia:
   - los faltantes se codifican como 0;
   - el signo de los flujos de línea cambió entre 2017 y 2023;
   - la topología cambia con los años;
   - Edelnor, Enel y Pluz aparecen con tres códigos distintos.
4. **En datosabiertos.gob.pe no hay demanda subhoraria.** Lo más útil de ese portal:
   - **SAIDI/SAIFI** mensual por sistema eléctrico, 2004–2026 (Osinergmin, ODC-By), limpio y con señal clara de El Niño;
   - facturación mensual (2022 en adelante).
5. **Riesgo de cumplimiento:** el COES no aparece en Kaggle, UCI, datosabiertos.gob.pe ni Google Dataset Search, y
   no publica una licencia. Si el enunciado exige esos catálogos al pie de la letra, el plan B que cumple es el
   SAIDI/SAIFI.
6. **Recomendación:** pronóstico a **1 h de la demanda por subestación de Luz del Sur** (datos del COES por barras),
   con el SEIN como serie de control y el SAIDI como plan B. Ver §4.

---

## 1. Tabla de fuentes

Leyenda de la columna "¿Abierta?": ✅ cumple el enunciado; ⚠️ es pública y sin registro, pero no está en los
catálogos que nombra el enunciado; ❌ no sirve.

| # | Fuente | Variable | Resolución | Cobertura y retraso (verificado) | Nivel geográfico | Acceso y tamaño | Licencia | ¿Abierta? | Niño 2017 / 2023 |
|---|---|---|---|---|---|---|---|---|---|
| A | **COES, Demanda del SEIN** (Portal de Información) | Ejecutado, Prog. Diaria y Prog. Semanal (MW) | **30 min** | 2000→hoy. En 2000 y 2005 falta la Prog. Semanal; desde 2010 está completa. 1995: vacío. El 23-oct a las 22:15 había datos hasta las 22:00, o sea ~30 min de retraso (preliminar) | SEIN nacional | `POST /Portal/portalinformacion/Demanda` (JSON, 24 KB/día) o `GET .../ExportarDemanda?fechaInicial=dd/mm/aaaa&fechaFinal=` (xlsx de **0,63 MB/año**; acepta un año por petición) | No publicada; sin registro | ⚠️ | ✅ / ✅ |
| B | COES, Pronóstico automático de tiempo real | Ejecutado, RDO, pronóstico TR e intervalo mín./máx. | 30 min | Ventana reciente; el histórico no se verificó | SEIN | `GET .../ObtenerPronosticoTiempoReal`, `ExportarPronosticoTiempoReal` | Ídem | ⚠️ | ? |
| C | **COES, Demanda de los agentes por barras** (Distribuidores `tipo=2`, Usuarios libres `tipo=4`) | MW por punto de medición (transformador o línea), con empresa, equipo, kV y subestación | **30 min** | Desde **jun-2014**: el 1-may-2014 está vacío y el 1-jun-2014 tiene datos. Hay huecos sueltos (31-dic-2014 vacío). Llega hasta el día anterior (20-oct-2026 completo). También ofrece demanda prevista diaria (`lectcodi=110`) y semanal (`102`) | **Subestación o barra**, 31 distribuidoras (Luz del Sur: 87–101 puntos, 43–47 SE) | `POST /Portal/demandabarras/consulta/grilla` (JSON, ~48 KB/día/empresa) o `exportar` + `descargar` (xlsx, **~0,75 MB/mes** para Luz del Sur). Máximo 31 días por consulta | Ídem | ⚠️ | ✅ / ✅ |
| D | **COES, IEOD** (Informe de Evaluación de la Operación Diaria) | Hoja `DEMANDA_AREAS` (SEIN, Norte, Centro, Sur y subáreas). Además: generación por área y recurso, CMg, demanda de usuarios libres, flujos, eventos y, en 2026, `TEMP_AMB` y `DESV_DEMANDA_PRONOS` | 30 min | Oct-2011→D+1 (el 22-oct-2026 se publicó el 23-oct) | **Área operativa** (3) | Navegador de archivos: `POST /Portal/browser/vistadatos`, descarga en `GET /Portal/browser/download?url=`. Un Anexo xlsx de **1,0–1,3 MB por día** (~400 MB/año) | Ídem | ⚠️ | ✅ / ✅ |
| E | COES, Generación por tipo de recurso | MW por combustible o tecnología (hídrica, gas, solar, eólica, diésel…) | SCADA **30 min**; medidores **15 min** | SCADA desde ≤2005; medidores desde ≤2012 con **retraso mensual** (30-sep-2026 disponible, 15-oct-2026 vacío) | SEIN | `POST /Portal/portalinformacion/Generacion` con `indicador=0` (SCADA) o `1` (medidores): 280–460 KB/día | Ídem | ⚠️ | ✅ / ✅ |
| F | COES, Costos marginales | CMg nodal (energía, congestión y total) | 30 min | Tiempo real: **desde ~oct-2020** (1-jul-2020 vacío, 1-oct-2020 con datos), con huecos. Revisados: carpetas 2018–2026. Del IEOD (hoja CMgCP, sistema): desde 2011 | ~120 barras de >138 kV, o todas | `GET .../costosmarginales/ExportarMasivo?fechaInicio=&fechaFin=&defecto=S` (máximo 31 días; ~1,2 MB/semana) | Ídem | ⚠️ | 2017 solo vía IEOD / ✅ |
| G | COES, Eventos relevantes | Registro de eventos: empresa, ubicación, familia, equipo, inicio, fin y texto | Evento | Al menos 2017→2026 (2017: 1 769 eventos; 2023: 1 981) | Instalación | `GET /Portal/eventos/relevantes/ExportarEvento?FechaInicio=&FechaFin=&IdTipoEvento=0&Version=N&IdTipoEmpresa=0&IdEmpresa=0&IdFamilia=0&IndInterrupcion=-1` (~110 KB/año) | Ídem | ⚠️ | ✅ / ✅ |
| H | COES, Estadística Anual | Producción, máxima demanda, demanda, fallas… | Mensual o anual; algunos gráficos de carga | Carpetas de al menos 2014–2025 (2025 publicada el 03-feb-2026) | SEIN o área | Excel por capítulo: Cap. 05 "Demanda" 10,7 MB; Cap. 07 "Fallas" 0,47 MB. En 2017, archivos por cuadro de ~20 KB | Ídem | ⚠️ | ✅ / ✅ |
| I | **Osinergmin, SAIDI/SAIFI** (PNDA) | SAIDI y SAIFI mensuales, total y por origen (generación, transmisión, distribución) | Mensual | **2004-09 → 2026-03**. Corte del 07-may-2026, o sea ~5 semanas de retraso | **Sistema eléctrico** (322) de 24 empresas | CSV de **6,5 MB** más diccionario | **ODC-By** (Open Data Commons Attribution) | ✅ | ✅ / ✅ |
| J | Osinergmin, Facturación ("Reporte del consumo de energía eléctrica, kWh-mes") (PNDA) | Nº de suministros y consumo promedio por empresa × sistema × tarifa × uso | Mensual | 2024-01 → 2026-04 (43 MB) y 2022-01 → 2025-01 (282 MB) | Sistema eléctrico | CSV con `;` | ODC-By | ✅ | ❌ / ✅ |
| K | Distriluz (Hidrandina, Electronorte, Enosa), Electro Puno, Electro Ucayali, ADINELSA, SEAL (PNDA) | Consumo mensual **por cliente** (anonimizado a medias) | Mensual | Desde dic-2022 | Suministro, con ubigeo | ~190 MB por mes (Hidrandina) | ODC-By (Hidrandina); "no especificada" (Electro Puno) | ✅ (con riesgo de PII) | ❌ / ✅ |
| L | EGEMSA, Generación de la C.H. Machupicchu (PNDA) | Potencia activa y reactiva por grupo (4) | 30 min | 2011→2026 (modificado el 17-sep-2026) | Una central | Un CSV por año (2,9 MB en 2017) | ODC-By | ✅ | ✅ / ✅ |
| M | Osinergmin, otros (PNDA) | Pliegos tarifarios, suministros, subestaciones de distribución, instalaciones de MT y BT | Inventarios | — | — | — | ODC-By | ✅ | no son series |
| N | MINEM, Anuario estadístico e indicadores mensuales | Producción y demanda | Mensual o anual | **No verificado**: minem.gob.pe agotó el tiempo dos veces. En la PNDA solo está "MINEM Capacidad Instalada" | Región | — | — | ? | ? |
| O | Kaggle | — | — | **No se encontró ningún dataset peruano**. Solo se buscó por web: la API pública devolvió HTML y pide sesión | — | — | — | — | — |
| P | Google Dataset Search | — | — | Para "Peru electricity load", "COES SINAC", "demanda SEIN Peru" y "Peru SAIDI" solo salen agregadores (Ember, CEIC, TheGlobalEconomy, Statista). **El COES no está indexado** | País | — | — | — | — |
| Q | Luz del Sur y Pluz (sitios propios) | — | — | No se encontraron datasets abiertos; solo avisos HTML de cortes programados (según la prensa) | — | — | — | ❌ | — |

### Hallazgos de acceso

- **El portal del COES no tiene API documentada**, pero sus endpoints son estables y no piden registro.
  - Se encontraron leyendo el JavaScript de cada página: `demanda.js`, `consulta.js`, `costomarginal.js`, `evento.js`, `web.js`.
  - `robots.txt` responde 404.
  - No se encontraron términos de uso ni licencia en el portal.
- **datosabiertos.gob.pe** es un DKAN/Drupal sin API tipo CKAN (`/api/3/action/...` lleva a un 404).
  - Bloquea el user agent de `curl` (código 418); con el de un navegador responde bien.
  - Los archivos aceptan `Range`, lo que permitió muestrear los CSV grandes sin bajarlos completos.
- **El navegador de archivos del COES (IEOD, Estadística) cambia las convenciones de nombre según el año.** Esto rompe
  cualquier scraper ingenuo:
  - meses: `03_MARZO` (2017), `03_Marzo` (2023), `10_Octubre` (2026), `12 DICIEMBRE` (2011);
  - días: `Dia 01` y `Día 02` conviven en el mismo mes de 2017; en 2023 son solo `01`;
  - anexos: `Anexo_0203.xlsx` (2017), `Anexo1_Resumen_1503.xlsx` (2023), `AnexoA_2210.xlsx` (2026).

---

## 2. Calidad sobre muestras reales

### 2.1 Demanda del SEIN, 30 min (fuente A). Muestra: 2015-01-01 → 2026-10-23, doce exportaciones anuales (7,5 MB)

Script: `q_sein.py`. Salida: `out/q_sein.txt` y `out/sein_30min_2015_2026.csv`.

| Prueba | Resultado |
|---|---|
| Registros esperados y presentes | **207 072 / 207 072**; 0 marcas de tiempo faltantes; **0 duplicados** |
| Formato | Las 12 exportaciones tienen las mismas 4 columnas (`FECHA`, `EJECUTADO`, `PROG. DIARIA`, `PROG. SEMANAL`); 0 fechas sin parsear |
| Nulos, ceros, negativos | 4 NaN, que son los periodos de hoy aún no transcurridos (22:30–24:00); 0 ceros; 0 negativos |
| Marca de tiempo | **Fin de periodo**: 00:30 … 23:30, y 24:00 se publica como 00:00 del día siguiente. Hora local de Lima (UTC−5, sin horario de verano). El portal no declara zona horaria; que los datos de "hoy" llegaran hasta las 22:00 a las 22:15 de Lima es coherente con hora local |
| Saltos | 3 437 saltos de más del 5 % entre periodos consecutivos y 68 de más del 10 %. Hay 5 puntos con \|z robusto\| > 6 (mediana móvil más MAD), todos el 26-ago-2025 |
| Atípicos | **Son eventos reales, no errores de dato.** En cada uno, la Prog. Diaria sigue normal mientras el ejecutado cae: <br>• 26-ago-2025 01:30: −29,6 % (de 6 520 a 4 588 MW durante unas 3 h); <br>• 9-jul-2017 23:00: −24 % (de 5 317 a 4 031 MW, hasta el día siguiente); <br>• 3-jul-2024 23:30: −18,6 %; <br>• 27-oct-2018 17:30: −18 %. <br>Hay que marcarlos (como en la auditoría de Tetuán), no borrarlos. Se pueden cruzar con la fuente G |
| COVID | Semanas desde el 22-mar-2020: entre −25 % y −33 % frente a 2019 |
| Desfase frente al IEOD (post-operación) | El portal queda **por encima**: <br>• 2-mar-2017: +60 MW de media (+1,05 %, rango 0,56–1,51 %); <br>• 22-oct-2026: +96 MW (+1,26 %, rango 0,97–1,46 %). <br>En el IEOD, Norte + Centro + Sur = SEIN exacto (diferencia de 0,0 MW) |
| Frente a la Estadística Anual 2017 (Cuadro 2.1) | Energía mensual: el portal está **+0,68 % a +1,58 %** por encima. Anual: 49 570 GWh frente a 48 993 GWh (**+1,18 %**). Máxima demanda en horas punta: entre +0,5 % y +1,7 % |
| Frente a cifras publicadas | Máxima de 2024 en punta: portal 7 889 MW; SNMPE (vía Gestión) 7 794 MW (+1,2 %). Feb-2024: 7 889 MW frente a 7 762 MW de la Prospectiva de Osinergmin (+1,6 %) |
| Energía de un día con cuatro fuentes (2-mar-2017) | Portal 142 130 MWh; IEOD 140 686 MWh; generación SCADA 139 953 MWh; generación por medidores de 15 min 139 485 MWh |

**Conclusión:** el "Ejecutado" del portal tiene un sesgo de nivel estable de ~1–1,5 % frente a las cifras oficiales.
Probablemente es un perímetro distinto, pero no está confirmado. Para modelar sirve igual, siempre que no se mezclen
fuentes en una misma serie. Las revisiones posteriores del dato preliminar no se pudieron medir (§5).

**Resumen anual** (MW; energía en GWh, calculada como la suma por 0,5 h):

| Año | Media | Máximo | Momento del máximo | Energía |
|---|---|---|---|---|
| 2015 | 5 113 | 6 377 | 25-nov 19:30 | 44 784 |
| 2017 | 5 659 | 6 751 | 09-feb 15:00 | 49 570 |
| 2020 | 5 663 | 7 375 | 25-feb 15:30 | 49 746 |
| 2023 | 6 763 | 7 999 | 07-mar 14:30 | 59 240 |
| 2025 | 7 075 | 8 505 | 22-dic 15:00 | 61 979 |
| 2026 (a oct) | 7 441 | 8 767 | 26-feb 15:00 | 52 847 |

**Deriva de concepto:** el pico diario se ha ido del atardecer al mediodía. El porcentaje de días cuyo máximo cae
entre las 18 y las 23 h fue:

- 98,4 % en 2015, 72,4 % en 2020, 47,7 % en 2021, 27,7 % en 2023 y 29,4 % en 2026;
- solo enero a marzo: 96,7 % en 2015 y 17,8 % en 2026.

Lo mismo se ve en el máximo anual: a las 19:00 en 2015 y 2016, y a las 14:00–15:00 desde 2017. Para la validación,
esto implica no entrenar con 2015 y evaluar con 2026 como si fueran la misma distribución.

**Referencias ingenuas y benchmark del COES** (MAPE %, del script):

| Año | Prog. Diaria del COES (día anterior) | Prog. Semanal | Persistencia a 1 h | Ayer, misma hora | Semana pasada |
|---|---|---|---|---|---|
| 2015 | 1,69 | 2,27 | 3,01 | 4,55 | 2,63 |
| 2017 | 1,76 | 2,42 | 2,75 | 4,35 | 2,64 |
| 2020 | 1,91 | 3,15 | 2,68 | 3,96 | 3,62 |
| 2023 | 1,72 | 2,11 | 2,36 | 3,71 | 2,64 |
| 2025 | 1,50 | 1,95 | 2,34 | 3,78 | 2,50 |
| 2026 | 1,51 | 2,01 | 2,37 | 3,73 | 2,41 |

La Programación Diaria del COES le gana a la persistencia a 1 h aunque se emite el día anterior. Es un benchmark
exigente y muy bueno para el paper.

**Niños Costeros (semanas frente al mismo periodo del año anterior):**

- **2017:** del 19-mar al 16-abr, entre −0,9 % y −3,3 %, cuando la tendencia era de +2,3 %/año. Eso deja la demanda
  ~3–5 % por debajo de la tendencia (huaicos e inundaciones).
- **2023** (ciclón Yaku y calor): de marzo a abril, entre **+6,2 % y +13,6 %**, por encima de la tendencia.
- Los dos eventos tienen signos opuestos, lo que es interesante para el cruce con ENSO.

### 2.2 Demanda por barras de Luz del Sur (fuente C). Muestras: mar-2017 y mar-2023, más cortes de un día en 2015, 2020, 2025 y 2026

Scripts: `q_barras.py` y `q_barras_neg.py`. Salida: `out/q_barras.txt`.

| Prueba | Mar-2017 | Mar-2023 |
|---|---|---|
| Filas (30 min) | 1 488 de 1 488; 0 huecos; 0 duplicados; 0 NaN | ídem |
| Puntos y subestaciones | 89 / 43 | 101 / 47 |
| Celdas en cero | **7,0 %** | **13,6 %** |
| Puntos siempre en cero | 4 (equipos retirados que siguen como columna) | 7 |
| **Faltante codificado como 0** | 24-mar-2017 14:30: **61 de 89 puntos = 0** y el total cae a 577 MW, cuando antes y después ronda los 2 340 MW | 0 instantes con más del 50 % de puntos en cero |
| **Negativos** | **13 372 celdas** en 11 puntos. Son flujos de línea, p. ej. L-659 Santa Anita–Huachipa: media −41 MW, 100 % negativos | **0**. Las mismas líneas ahora valen ~0 (92,8–98,9 % de ceros). **Cambió la convención de signo** |
| Tramos planos de 2 h o más (sin contar ceros) | 0,64 % | 0,50 % |
| Saltos de más del 50 % en 30 min (puntos con media > 5 MW) | 245 en 66 puntos | 99 en 27 puntos (transferencias de carga entre SE) |
| Subestaciones con media > 20 MW | 25 | 28 |

- **Estabilidad de la topología (Luz del Sur):**
  - puntos: 87 (2015), 89 (2017), 101 (2023), 101 (2026);
  - **78 puntos y 42 subestaciones aparecen en los cuatro cortes**: base suficiente para un modelo global.
- **Cambio de razón social en Lima Norte.** Tres códigos de empresa distintos:
  - `14` EDELNOR: 105 puntos en 2015;
  - `12099` ENEL: 106 puntos en 2020, con **0 IDs en común con 2015** (solo coinciden 30 nombres de subestación);
  - `15264` PLUZ: 137 puntos en 2025, que conserva los 106 IDs de Enel.

  La serie de Lima Norte solo se puede unir por nombre de subestación, y a mano. Por eso conviene empezar con Luz del
  Sur (código `13` sin cambios).
- **Agregación:** sumar todos los puntos cuenta dos veces. Hay transformadores de 220 kV que alimentan 60 kV, además de
  los flujos de línea. Antes de agregar hay que elegir un conjunto que no se solape, por ejemplo los puntos de 10 y
  22,9 kV de cada subestación.

### 2.3 Costos marginales nodales en tiempo real (fuente F). Muestras: 1–7 mar 2023, 10-jun-2026 y 12-ago-2026

Script: `q_cmg.py`. Salida: `out/q_cmg.txt`.

- **Semana de 2023:**
  - 38 018 filas y 113 barras;
  - por barra, la mediana es de **325 de 336** periodos;
  - **17 instantes sin ninguna barra** (las 00:00 de cada día y 12 al azar);
  - **1 300 filas duplicadas** (nodo, hora) en 4 nodos con valores distintos (p. ej. CHAVARR220: 103,36 y 102,89);
  - 789 componentes de congestión negativos.
- **2026:** el 10-jun tiene **36 de 48** instantes y el 12-ago solo **2 de 48**. La exportación en tiempo real no sirve
  como serie continua: hay que usar los "Revisados" o el IEOD.
- **Nivel:** la media de la barra Santa Rosa 220 fue 132 (mar-2023), 123 (10-jun-2026) y 815 (12-ago-2026, con solo 2
  instantes).
  - Las unidades serían S/./MWh por analogía con la hoja CMgCP del IEOD; la exportación no las declara.
  - La subida de junio a agosto de 2026 va en el sentido que reporta la prensa (CMg de más de 100 USD/MWh en jul–ago
    de 2026, ver §3), pero con 2 instantes no es comparable.

### 2.4 SAIDI/SAIFI de Osinergmin (fuente I). Archivo completo, 6,5 MB

Script: `q_saidi.py`. Salida: `out/q_saidi.txt`.

- **Volumen:** 54 191 filas de 2004-09 a 2026-03 (259 meses), con 322 sistemas y 24 empresas. Hay 148–231 sistemas
  por mes, con escalones en 2010 y 2013–2014.
- **Integridad:**
  - 0 duplicados (mes, sistema) y 0 NaN;
  - 10,6 % de ceros;
  - SAIDI máximo de 685,9;
  - **SAIDI = GEN + TRA + DIS exacto** en todas las filas.
- **Un solo `FECHA_CORTE`:** es una foto que se sobrescribe, sin historial de revisiones.
- **Renombre retroactivo:** "PLUZ ENERGIA PERU S.A.A.." (con doble punto) tiene historia desde 2004, con 17 sistemas.
  Aquí, a diferencia del COES, la serie viene ya unida.
- **Señal de El Niño.** Mediana del SAIDI mensual en Enosa + Electronorte + Hidrandina:

  | Mes | 2017 | 2023 | Otros años (2014–2025) |
  |---|---|---|---|
  | Febrero | 4,83 | 3,24 | — |
  | Marzo | **7,06**, máximo de la tabla | **4,60** | 1,6–3,8 |
  | Abril | 3,44 | 2,73 | — |

### 2.5 Eventos del COES (fuente G). Años 2017 y 2023

Script: `q_eventos.py`. Salida: `out/q_eventos.txt`.

| | 2017 | 2023 |
|---|---|---|
| Eventos | 1 769 | 1 981 |
| Duplicados | 11 | 2 |
| Fechas vacías o duración negativa | 0 | 0 |
| Mes con más eventos | **Marzo (258)** | Dic. 227, Feb. 223, Mar. 219 |
| Duración mediana | 26 min | 62 min (cambio de práctica de registro, no verificado) |
| Descripciones con "MW" de carga | 0 | 14 |

No hay un campo estructurado de carga interrumpida.

### 2.6 Facturación de Osinergmin (fuente J). Solo se muestrearon los primeros y últimos 100 KB

- El esquema es estable.
- Ejemplo de dato inconsistente: ELOR, tarifa BT5D, rango "de 31 a 100 kWh", con 2 suministros y un consumo
  **promedio de 4 483 kWh**.
- Los campos de texto vienen rellenos con espacios hasta 150 caracteres.

---

## 3. Problemáticas que estos datos sostienen, ordenadas por factibilidad e impacto

| # | Problema | Objetivo (y) | Horizonte | Evaluación | Datos | Factibilidad | Impacto | Niño 2017 / 2023 |
|---|---|---|---|---|---|---|---|---|
| **1** | **Pronóstico de la demanda por subestación de Lima Sur** (modelo global) | MW de la SE en t+2 (30 min), relativo a su media de 24 h | 1 h (2 pasos) | MAE, MAPE y skill frente a persistencia, ayer y semana pasada; origen móvil mensual; métricas aparte en las ventanas Niño | C (+ A como contexto) | **Alta**: 2015→2026, ~105 MB en Colab | **Alta** | ✅ / ✅ |
| 2 | Pronóstico de la demanda del SEIN o por área | MW del SEIN, o de Norte, Centro y Sur | 1 h a 24 h | Ídem, más el **benchmark de la Prog. Diaria del COES (MAPE 1,5 %)** | A (limpio); D (áreas, ~400 MB/año) | Muy alta (A) / media (D) | Alta | ✅ / ✅ |
| 3 | Clasificar si el pico del día será diurno o en horas punta (18–23 h), o detectar días top-5 % | Binaria por día | D-1 | F1, AUC, Brier; validación temporal (la clase pasa del 98 % al 29 %) | A | Muy alta | Media-alta (punta = potencia y tarifa) | ✅ / ✅ |
| 4 | SAIDI alto el mes próximo por sistema eléctrico (panel) | SAIDI > p75 propio del sistema (binaria), o log SAIDI (regresión) | 1 mes | AUC y F1 por año retenido | I (+ ENSO del otro estudio) | **Alta**, y **cumple el enunciado** | Alta (calidad de suministro, El Niño en el norte) | ✅ / ✅ |
| 5 | CMg alto o pronóstico de CMg | CMg total en una barra de referencia (regresión), o CMg > umbral | D-1 o 1 h | MAE; precisión y recall de los picos | F (revisados), E | Media-baja (huecos, duplicados, unidades, armado) | Alta en 2026 | 2017 solo vía IEOD / ✅ |
| 6 | Eventos o fallas por día o semana | Nº de eventos > umbral, o ≥1 evento en una zona | Día o semana | AUC y PR-AUC | G | Media (texto libre, sin carga estructurada) | Media | ✅ / ✅ |
| 7 | Consumo facturado por sistema o tarifa | kWh promedio mensual | 1 mes | MAPE | J | Media (archivos grandes; desde 2022) | Media | ❌ / ✅ |
| 8 | Generación de la C.H. Machupicchu | MW de la central | 30 min a 1 día | MAE | L | Alta y cumple el enunciado | Baja-media (la manda el despacho) | ✅ / ✅ |

### Relevancia para el Perú, según fuentes

- **Pronóstico de demanda (1 y 2).** El propio COES publica junto a la demanda un *"Pronóstico de Demanda Automático
  de Tiempo Real"* con intervalo, además de la *"Programación Diaria / Reprogramación Diaria"*. Ambos están verificados
  en el código del portal (`demanda.js`).
  - Las distribuidoras declaran demanda "prevista diaria" y "prevista semanal" por barra en la misma herramienta de
    la fuente C. Es decir, el pronóstico a corto plazo es un insumo operativo real del SEIN.
  - El COES también publicó un informe técnico, *"Mejora del Marco de Pronósticos de la Energía Renovable Variable en
    el Perú"*, enlazado desde su portada; no lo leí.
  - Gestión (21-sep-2026) reporta que la demanda *"ya está superando los 8,000 Mw en horas punta"*.
    [Gestión](https://gestion.pe/economia/aumenta-consumo-electrico-pero-tambien-costos-de-generacion-seguiran-subiendo-tarifas-noticia/)
  - Osinergmin publica una "Prospectiva del Sector Eléctrico" mensual con la máxima demanda del COES (p. ej. 7 762 MW
    en feb-2024).
    [Prospectiva marzo 2024](https://cdn.www.gob.pe/uploads/document/file/6158515/5180087-prospectiva-del-sector-electrico-para-el-mes-de-marzo-2024.pdf)
- **Horas punta (3).** La Estadística Anual del COES define la máxima demanda mensual en el *"periodo de Horas Punta del
  SEIN"*; está en la nota del Cuadro 2.1 de 2017, verificada. Los datos muestran que el pico real se ha ido al mediodía,
  un tema operativo y tarifario actual.
- **Calidad de suministro (4).** Osinergmin publica el SAIDI y el SAIFI por sistema como dataset abierto.
  - Los meses de los Niños Costeros (mar-2017 y mar-2023) tienen los SAIDI más altos del norte en la serie, según §2.4.
  - Hay notas de prensa de 2026 sobre refuerzos de Osinergmin en el 43 % de los sistemas eléctricos para reducir
    cortes. Solo las vi como resultado de búsqueda, no las leí.
    [ProActivo](https://proactivo.com.pe/osinergmin-refuerzan-43-de-sistemas-electricos-para-reducir-cortes-de-luz)
- **CMg (5).** Gestión reporta un CMg medio que pasó de ~35 USD/MWh en junio a más de 100 en julio de 2026, y de 105 a
  118 en agosto. El presidente del COES lo atribuye en parte a El Niño: menos lluvia y viento, más diésel.
  [Gestión](https://gestion.pe/economia/aumenta-consumo-electrico-pero-tambien-costos-de-generacion-seguiran-subiendo-tarifas-noticia/)

---

## 4. Recomendación para el TB1

**Dataset:** COES, Demanda de los agentes por barras, de **Luz del Sur** (código 13), 30 min, de ene-2015 a oct-2026.
La demanda del SEIN (fuente A) va como serie de contexto y control.

**Problema:** pronosticar con **1 h de anticipación** la demanda de cada **subestación** de Lima Sur, para anticipar
sobrecargas y maniobras de transferencia. Es la misma narrativa de negocio que Tetuán, ahora con datos peruanos.

### Por qué esta opción

- Reutiliza casi todo:
  - el medallón con auditoría (en bronce entran los Excel mensuales);
  - el objetivo relativo a la media de 24 h;
  - las tres referencias ingenuas;
  - el modelo global (20–40 SE en lugar de 3 zonas);
  - el origen móvil.
- Cubre 2017, 2023 y 2026 para el cruce con El Niño.
- La calidad sucia de la fuente C le da contenido real a la fase de *Data Understanding* de CRISP-DM:
  - ceros que en realidad son faltantes;
  - el cambio de signo;
  - las altas y bajas de puntos;
  - las transferencias entre subestaciones.
- El SEIN aporta un benchmark oficial (Prog. Diaria del COES) para una sección de comparación en el paper.

### Pasos

1. Seleccionar SE estables, con datos de 2015 a 2026, media > 20 MW y puntos de 10 y 22,9 kV, para no contar dos veces.
2. Tratar 0 como NaN cuando más de la mitad de los puntos estén en 0 en ese instante.
3. Truncar los flujos de línea a ≥0, o excluirlos.
4. Marcar los eventos con la fuente G y los atípicos del SEIN.

### Si el profesor exige un catálogo de los que nombra el enunciado

- **Plan B, que cumple:** SAIDI/SAIFI de Osinergmin en datosabiertos.gob.pe (problema 4: SAIDI alto el mes próximo
  por sistema eléctrico, con panel de 322 sistemas, 2004–2026 y ODC-By).
  - Es limpio y tiene señal de El Niño.
  - Pierde la reutilización del pronóstico subhorario.
- **Plan C:** SEIN más las 3 áreas del IEOD (Norte, Centro, Sur), la réplica exacta de las 3 zonas. Bajar ~400 MB por
  año y lidiar con tres formatos de nombre lo vuelve arriesgado para el 16-nov.
- **Pregunta para el profesor:** ¿la lista del enunciado es cerrada o son ejemplos? El COES es el operador oficial del
  sistema, sus datos son públicos y no piden registro, pero no publica una licencia explícita.

### Descarga en Colab (no ejecutado aquí más allá de las muestras)

```python
import requests, time, pandas as pd
B = "https://www.coes.org.pe/Portal"; s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0"
# A) SEIN 30 min: un xlsx por año (~0,63 MB), cabecera en la fila 4 -> pd.read_excel(f, header=3)
for y in range(2015, 2027):
    r = s.get(f"{B}/portalinformacion/ExportarDemanda",
              params={"fechaInicial": f"01/01/{y}", "fechaFinal": f"31/12/{y}"}, timeout=300)
    open(f"sein_{y}.xlsx", "wb").write(r.content); time.sleep(1)
# C) Barras de Luz del Sur (empresas=13), lectcodi=103 histórica; máximo 31 días por consulta (~0,75 MB/mes)
for ini in pd.date_range("2015-01-01", "2026-09-01", freq="MS"):
    fin = ini + pd.offsets.MonthEnd(0)
    name = s.post(f"{B}/demandabarras/consulta/exportar", data={"lectcodi": 103, "empresas": 13,
                  "fechaInicio": f"{ini:%Y-%m-%d}", "fechaFin": f"{fin:%Y-%m-%d}"}, timeout=300).json()
    if name in ("-1", "2", -1, 2): print("sin datos", ini); continue
    r = s.get(f"{B}/demandabarras/consulta/descargar", params={"file": name}, timeout=300)
    open(f"lds_{ini:%Y%m}.xlsx", "wb").write(r.content); time.sleep(1)
# Encabezados de barras: 5 filas (PUNTO DE MEDICIÓN, EMPRESA, EQUIPO, TENSION, SUBESTACIÓN); ver experimentos/peru/verificacion/energia/q_barras.py
```

Para el IEOD hay dos endpoints:

- **Listar una carpeta:** `POST {B}/browser/vistadatos` con `baseDirectory="Post Operación/Reportes/IEOD/"`,
  `url=<ruta>` e `indicador=S`. El parser está en `experimentos/peru/verificacion/energia/coes_browse.py` y `coes_files.py`.
- **Bajar un archivo:** `GET {B}/browser/download?url=<ruta del archivo>`.

---

## 5. Lo que no pude verificar

- **Licencia y términos de uso del COES:** no hay licencia ni términos visibles en el portal, y `robots.txt` da 404.
  No sé si el enunciado lo admite como "fuente abierta".
- **El COES en los catálogos del enunciado:** Google Dataset Search no devuelve nada para "COES SINAC" ni para "demanda
  SEIN Peru". En Kaggle solo se buscó por web, porque la API pide sesión, y no apareció ningún dataset peruano. No
  descarto que exista alguno subido por terceros.
- **Revisiones del "Ejecutado" preliminar:** haría falta una segunda foto en otra fecha. Tampoco sé la causa del desfase
  de ~1–1,5 % frente al IEOD y la Estadística.
- **Unidades del CMg** en `ExportarMasivo`: asumo S/./MWh.
- **Cobertura histórica de:**
  - la demanda prevista por barra (`lectcodi=110` y `102`);
  - el pronóstico de tiempo real del COES;
  - los usuarios libres (`tipo=4`).
- **Barras:** la fecha exacta de inicio (entre el 1-may y el 1-jun de 2014) y el inventario completo de días vacíos.
  Solo hice sondeos puntuales: encontré el 31-dic-2014 vacío.
- **IEOD:** solo abrí `DEMANDA_AREAS` de 2017 (7 subáreas) y de 2026 (solo Electroandes). El formato de 2023
  (`Anexo1_Resumen`) no lo abrí.
- **Estadística Anual, capítulo 05 "Demanda" (10,9 MB):** lo bajé al probar si el servidor acepta `Range` (no lo
  acepta) y no lo guardé. No sé si trae demanda de 30 min por área.
- **MINEM:** minem.gob.pe agotó el tiempo dos veces; anuario e indicadores sin verificar.
- **Osinergmin y distribuidoras:** del sitio de Osinergmin solo exploré los datasets de la PNDA. No navegué los sitios
  de Luz del Sur ni de Pluz.
- **Archivos grandes de la PNDA:** el CSV de facturación de 282 MB y los consumos por cliente solo los vi por cabecera.
- **Notas de prensa** (refuerzos de Osinergmin, BCRP "Demanda en el sector eléctrico 2023-2026"): solo las vi como
  resultado de búsqueda. La de Gestión del 21-sep-2026 sí la leí.
- **Zona horaria:** que sea hora de Lima se deduce de la coherencia con la hora actual; el portal no lo declara.
