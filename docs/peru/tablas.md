# Tablas de referencia: áreas del COES, empresas, subestaciones, ciudades, feriados y cuarentena

Fecha: 24-oct-2026. Las tablas están en
[`src/tetouan_power_forecast/tablas/`](../../src/tetouan_power_forecast/tablas/) y se leen con
[`tablas.py`](../../src/tetouan_power_forecast/tablas.py):

```python
from tetouan_power_forecast import tablas
deptos = tablas.cargar("departamentos_area")   # DataFrame
tablas.validar()                                # ValueError si alguna regla falla
tablas.normalizar("Pluz Energía Perú S.A.A..")  # 'PLUZ ENERGIA PERU SAA', para cruzar nombres
```

- Todas son CSV en UTF-8, con la cabecera en minúsculas, y cada fila lleva su `fuente`.
- `confianza` vale `alta` (dos o más fuentes coinciden), `media` (una fuente o una inferencia
  de la topología) o `baja` (inferencia débil; revisar antes de usarla para algo fino).
- Se armaron a partir de las muestras locales (eventos del COES de 2017 y 2023; anexos del IEOD
  del 02-mar-2017, 15-mar-2023 y 22-oct-2026; SAIDI/SAIFI de Osinergmin) y de fuentes web.
  Las muestras son de terceros y no se versionan; los CSV sí, porque son referencia propia.
- El anexo del 15-mar-2023 (1,4 MB) se bajó para esta tarea, para contrastar la agrupación de
  usuarios libres de 2026 (ver §3).

| Tabla | Filas | Cobertura |
|---|---|---|
| `departamentos_area` | 25 | 25 de 25 departamentos (19 alta, 5 media, 1 baja) |
| `subarea_area` | 7 | las 7 subáreas de `DEMANDA_AREAS` |
| `empresa_area` | 277 | 180 empresas; 98,4 % de los eventos y todos los usuarios libres salvo uno |
| `sin_asignar` | 7 | empresas que no se pudieron asignar, con el motivo |
| `subestacion_departamento_area` | 501 | 98,4 % de los eventos con al menos un extremo asignado; 94,1 % con todos |
| `ciudades_era5` | 6 | Norte 3, Centro 1, Sur 2 |
| `feriados_pe_2015_2026` | 258 | 161 feriados nacionales, 36 regionales, 61 días no laborables |
| `cuarentena_pe_2020` | 5 | de la cuarentena estricta (16-mar-2020) a la Fase 4 (fin de 2020) |

---

## 1. `departamentos_area`: departamento → área operativa

**Qué es.** El área operativa del COES (Norte, Centro, Sur) de cada uno de los 25 departamentos,
Callao incluido.

**De dónde salió.** El COES no publica una lista de departamentos por área. Se reconstruyó con
tres fuentes que coinciden:

1. **Barras de transferencia por área.** Osinergmin (2023), *Principales indicadores de la
   operación del SEIN, I trimestre 2023*, Tabla 1, elaborada con el informe mensual del COES.
   [PDF](https://cdn.www.gob.pe/uploads/document/file/5272219/4738468-principales-indicadores-de-la-operacion-del-sein-i-trimestre-2023.pdf)
   - Área Norte: Trujillo, Piura, Cajamarca Norte, Chimbote, Chiclayo, Guadalupe, Huallanca,
     Zorritos, Carhuaquero, Talara, La Niña.
   - Área Centro: San Juan, Chavarría, Santa Rosa, Electroandes, Independencia, Cajamarquilla,
     Vizcarra, Zapallal, Huánuco - Tingo María, Paramonga Nueva, Pomacocha, Marcona, Pucallpa -
     Aguaytía, Campo Armiño, Huayucachi, Desierto, Ica, Huacho, Huancavelica, Cantera, Carabayllo.
   - Área Sur: SPCC, Ampliación Cerro Verde, Arequipa, Tintaya, Cusco - Abancay, Callalli, Tacna,
     Juliaca, Azángaro, Puno, Quencoro - Combapata, Ilo, Moquegua, Ayaviri.
2. **Las fronteras entre áreas**, en la hoja `INTERCONEXIONES` del IEOD:
   - Centro - Norte: Kiman Ayllu (L-2269 y L-2270), Chimbote 1 (L-2215 y L-2216) y Chimbote Nueva
     (L-5006), los tres años.
   - Centro - Sur: Cotaruse (L-2051 y L-2052) y San José (L-5036) en 2017; Campo Armiño (L-2051 y
     L-2052) y Poroma (L-5033 y L-5034) en 2023 y 2026.
3. **La agrupación de usuarios libres por área** en la hoja `DEMANDA_UL` (2017 y 2023).

**Ambigüedades.**

- **Áncash** (norte, `media`). Chimbote, Huallanca y Huaraz son Norte, pero Vizcarra (Antamina),
  Conococha y Huallanca Nueva se alimentan desde el Centro, y Huarmey cuelga de Paramonga Nueva por
  66 kV. La tabla de subestaciones resuelve cada caso; a nivel de departamento manda el Norte.
- **Ica** (centro, `alta`). Es Centro sin duda: sus barras están en el Área Centro, y en el IEOD
  `SUR = SUR ESTE + SUR OESTE` exacto en todas las medias horas, sin la subárea Sur Medio.
- **Apurímac** (sur, `alta`). Cotaruse está justo en la frontera: en 2017 la medición Centro-Sur
  se hacía en Cotaruse y desde 2023 en Campo Armiño. Los dos criterios dejan a Apurímac en el Sur.
- **Huánuco y Ucayali** (centro, `alta`). Tienen barra propia en el Área Centro.
- **Ayacucho y Madre de Dios** (`media`). No tienen barra propia. Ayacucho se alimenta desde
  Huancavelica (Mollepata) y Nazca (Puquio), ambos del Centro; Madre de Dios, desde San Gabán (Sur).
- **San Martín y Amazonas** (norte, `media`). Moyobamba y Tarapoto cuelgan de Cáclic, en el
  Norte; Tocache, en cambio, cuelga de Tingo María, en el Centro.
- **Loreto** (norte, `baja`). Iquitos y casi todo Loreto son sistemas aislados, fuera del SEIN.
- **Excepciones locales** que la tabla de subestaciones corrige: Caravelí (Bella Unión, Arequipa)
  se alimenta desde Marcona (Centro), y en 2017 la S.E. Ocoña (Arequipa) quedaba del lado Centro.

## 2. `subarea_area`: subáreas del IEOD

`DEMANDA_AREAS` trae siete subáreas en 2017 y 2023, y solo Electroandes en 2026. Las sumas se
comprobaron en los dos anexos: `SEIN = NORTE + CENTRO + SUR` y `SUR = SUR ESTE + SUR OESTE`, exactos.

| Subárea | Área | Departamentos | Nota |
|---|---|---|---|
| Norte Medio | norte | Áncash, La Libertad (`baja`) | 17-85 MW: es un saldo de flujos, no la demanda de esos departamentos |
| Lima | centro | Lima, Callao | |
| Electroandes | centro | Junín, Pasco | barra del Área Centro en Osinergmin (2023) |
| Sur Medio | centro | Ica (`media`) | no entra en el Sur; trae valores negativos (saldo de flujos) |
| Sur Este | sur | Cusco, Puno, Apurímac, Madre de Dios | |
| Sur Oeste | sur | Arequipa, Moquegua, Tacna | contiene a Arequipa |
| Arequipa | sur | Arequipa | subconjunto de Sur Oeste; no suma aparte |

Norte Medio y Sur Medio no sirven como demanda por departamento: son saldos.

## 3. `empresa_area` y `sin_asignar`: empresa → área

**Qué es.** Una fila por nombre de empresa tal como aparece en alguna fuente (`empresa_original`),
con su empresa canónica (`empresa_coes`), tipo, área y departamento principal.

- El nombre original se conserva tal cual, salvo los espacios al borde y los saltos de línea, que
  pasan a ser un espacio.
- Para cruzar, compare `tablas.normalizar(nombre)` contra `normalizar(empresa_original)`.
- Las transmisoras que operan en más de un área llevan `area = sein` y `departamento_principal` vacío.

**Cobertura.**

- **Eventos del COES:** las 133 empresas distintas de 2017 y 2023. Se asignan 127; las otras 6
  van a `sin_asignar`. Por número de eventos, el 98,4 % tiene empresa asignada.
- **`DEMANDA_UL`:** todos los nombres de 2017 (44), 2023 (69) y 2026 (69), salvo Sobreandes (2026).
- **SAIDI de Osinergmin:** las 24 empresas.
- **Extras:** las generadoras de `TEMP_AMB` (2023 y 2026), y Edelnor y Pluz tal como aparecen en
  la demanda por barras del COES (códigos 14 y 15264).
- **Usuarios libres:** los rótulos de `DEMANDA_UL` por sitio (p. ej. `ARES-CALLALLI`,
  `MINSUR - PUCAMARCA`) tienen su propia fila, con el área y el departamento de ese sitio.

**Lo que la tabla fija:**

- Edelnor, Enel Distribución Perú y Pluz Energía Perú son la misma empresa (Lima Norte, Centro).
- Luz del Sur va en el Centro.
- Hidrandina, Electronorte y Electronoroeste (Enosa) van en el Norte.
- Electro Sur Este, Electro Puno, SEAL y Electrosur van en el Sur.

**Ambigüedades.**

- **`DEMANDA_UL` de 2026 agrupa mal a las mineras del Centro.** Su bloque "Área Sur" incluye a
  Chungar, El Brocal, Administradora Cerro, Óxidos de Pasco, San Ignacio de Morococha, Los
  Quenuales, Corona, Volcan y Nexa, todas de Pasco, Junín o la sierra de Lima.
  - En 2017 y 2023 esas mismas cargas estaban en el bloque Centro.
  - Las únicas interconexiones Centro-Sur son Campo Armiño y Poroma.
  - Se asignan al Centro; cuando el conflicto afecta a una fila, la `fuente` lo dice y la
    confianza baja a `media`.
  - **Consecuencia:** la cuota de usuarios libres por área no debe calcularse con la agrupación de
    2026 sin corregirla. Falta ver otro día de 2024-2026 para saber desde cuándo pasa.
- **Empresas multiárea.** Se asigna el área principal y la `fuente` explica el resto:
  - generadoras: Statkraft, Engie, Egesur (Aricota en el Sur e Independencia en el Centro),
    Sinersa, Electroperú, Enel Green Power y EGASA (C.T. Pisco);
  - usuarios libres: Buenaventura, Minsur, Ares y las cadenas comerciales y pesqueras.

  En los eventos donde la ubicación da un área única, la empresa coincide con ella en el 88 %; casi
  todos los desacuerdos son de estas empresas. **Regla recomendada para los eventos: primero la
  ubicación (§4) y, si no se resuelve, la empresa.**
- **Transmisoras `sein`.** Son diez: REP, Transmantaro, ISA Perú, ATN, ATN 1, Atlántica
  Transmisión Sur (antes ABY), Conenhua, Conelsur LT y Puerto Maldonado Transmisora (`baja`: su
  concesión va al Sur, pero sus eventos de 2023 están en Valle del Chira, Piura).
- **Para agregar el SAIDI por área**, la tabla por empresa no basta:
  - Electro Oriente tiene sistemas aislados en Loreto, fuera del SEIN;
  - Coelvisac tiene sistemas en Ica (Centro) y en Olmos (Norte);
  - Hidrandina tiene a Huarmey, que se alimenta desde el Centro;
  - ADINELSA tiene sistemas dispersos.

  Conviene una tabla `sistema_electrico → área` con los 323 sistemas del SAIDI (pendiente).
- **`sin_asignar`:**
  - Atria Energía y Eléctrica Santa Rosa (titulares de la C.H. Purmacana), Centrales Santa Rosa
    y Eléctrica Yanapampa: no se pudo verificar dónde están sus centrales;
  - Inversiones Shaqsha: solo aparece en la línea Cobriza I - Cobriza II;
  - Sobreandes: solo aparece en el bloque Sur de 2026;
  - el propio COES: es el operador, no un agente.

## 4. `subestacion_departamento_area`: instalación → departamento → área

**Qué es.** Las instalaciones que aparecen en la columna `Ubicación` de los eventos de 2017 y
2023, más las centrales de `TEMP_AMB`.

- Comprende subestaciones (`S.E.`) y centrales (`C.H.`, `C.T.`, `C.E.`, `C.S.`): las centrales
  explican el 36 % de las ubicaciones.
- En las líneas (`L. A - B`), cada extremo se trata como una subestación.
- `area` puede diferir del área del departamento cuando la instalación se alimenta desde otra área:
  - Vizcarra, Conococha, Huallanca Nueva, 09 de Octubre y Huarmey (Áncash) van en el Centro;
  - Tocache (San Martín) va en el Centro;
  - Bella Unión (Arequipa) va en el Centro.
- `kv` es la tensión máxima que mencionan las descripciones de los eventos de esa subestación;
  queda vacío en las centrales y donde no hay mención. Es indicativa, no un inventario.
- La columna `Equipo` trae códigos (L-2053, T35-121, G1), no nombres de subestación, así que no
  se usó.

**Cobertura** sobre los 3 750 eventos de las muestras:

| | 2017 | 2023 | Total |
|---|---|---|---|
| Con al menos un extremo asignado | 99,4 % | 97,5 % | 98,4 % |
| Con todos los extremos asignados | 94,3 % | 93,8 % | 94,1 % |
| Con un área única | | | 92,9 % |
| Interárea (extremos en áreas distintas) | | | 5,6 % |

- Las 16 centrales de `TEMP_AMB` (13 de 2026 y 3 más de 2023) están todas.
- **No asignadas:**
  - Machala, que está en Ecuador; la línea Zorritos - Machala se resuelve por Zorritos;
  - Purmacana, Santa Rosa I y II, y Yanapampa, de ubicación no verificada;
  - Bellavista (hay una en Puno y otra en San Martín) y Parque Industrial (en Junín y en
    Arequipa): ambiguas por el nombre;
  - Machahuay y Pías;
  - los rótulos `ÁREA CENTRO` y `_N (NO-DEF)`.
- **Confianza:** 450 filas `alta`, 39 `media` y 12 `baja`. Las `baja` son nodos intermedios cuyo
  departamento se infirió de las líneas (Pumiri, Chilota, Tucari, La Ramada, Pampa Honda, Santa
  Isabel, Huaricashash, Juanjuí, entre otros).
- **Eventos interárea:** casi todos son el enlace Mantaro - Cotaruse, la propia frontera
  Centro-Sur. Queda por decidir cómo contarlos (ver §8).

## 5. `ciudades_era5`: ciudades por área para la temperatura

| Ciudad | Área | Lat | Lon | Altitud (m) | Población 2017 | Peso |
|---|---|---|---|---|---|---|
| Piura | norte | −5,194 | −80,632 | 29 | 473 025 | 0,2431 |
| Chiclayo | norte | −6,771 | −79,841 | 27 | 552 508 | 0,2840 |
| Trujillo | norte | −8,112 | −79,029 | 34 | 919 899 | 0,4729 |
| Lima | centro | −12,046 | −77,043 | 154 | 9 562 280 | 1 |
| Arequipa | sur | −16,399 | −71,537 | 2 335 | 1 008 290 | 0,7789 |
| Tacna | sur | −18,014 | −70,253 | 562 | 286 240 | 0,2211 |

**Fuentes.**

- Coordenadas: las de Lima, Piura y Chiclayo vienen de la spec v2; las otras son de la Plaza de
  Armas de cada ciudad.
- Población de Lima Metropolitana (Lima y Callao): INEI (2018), *Perú: Perfil Sociodemográfico*,
  cap. 1, §1.1.6.
  [PDF](https://www.inei.gob.pe/media/MenuRecursivo/publicaciones_digitales/Est/Lib1539/cap01.pdf)
- Población de las demás ciudades: el anexo de ciudades del Perú por población de Wikipedia, que
  cita al INEI. El cuadro por ciudad del INEI está como imagen en el PDF.
  [es](https://es.wikipedia.org/wiki/Anexo:Ciudades_del_Per%C3%BA_por_poblaci%C3%B3n) ·
  [en](https://en.wikipedia.org/wiki/List_of_cities_in_Peru)
- Los pesos son la población urbana sobre el total del área y suman 1 por área.

**Decisiones y ambigüedades.**

- **Tacna en vez de Ilo.** Tacna tiene casi cinco veces la población de Ilo (59 572 según el
  anexo en inglés). La carga de Ilo es sobre todo industrial (la refinería de Southern) y no
  responde al clima; Ilo, con ese tamaño, pesaría menos de 0,06.
- **Tacna tiene dos cifras:** 286 240 (anexo en español) y 293 119 (anexo en inglés). El peso
  cambia en menos de 0,004.
- **Arequipa** está a 2 335 m: es la ciudad grande del Sur, pero su clima es templado. Su peso,
  0,78, refleja la población, no la sensibilidad térmica.
- **Huancayo: se recomienda no sumarla al Centro.**
  - Con pesos por población entraría con 0,046 frente a Lima: no movería el promedio.
  - La subárea Electroandes (180-280 MW) es carga minera de Yauli y Pasco, insensible al clima.
  - Huancayo está a ~3 260 m y no tiene demanda por calor.
  - Si el grupo quiere probar la sierra central, que sea una variable aparte (temperatura de
    Huancayo o de La Oroya) en una variante del modelo, no mezclada con Lima.
- Las coordenadas son del centro de la ciudad. La celda de ERA5 (0,25°) de las ciudades costeras
  puede incluir mar; conviene revisar la celda que devuelva la API.

## 6. `feriados_pe_2015_2026`: feriados y días no laborables

**Qué es.** Una fila por fecha, con `tipo` (`feriado` o `no_laborable`) y `ambito`:

- `nacional`: público y privado en todo el país;
- `sector_publico`: compensable en el sector público, opcional en el privado;
- `regional`: una provincia o un departamento, que se nombra entre paréntesis en `nombre`.

**De dónde salió.**

1. **Feriados nacionales:** el paquete `holidays` 0.107 (`holidays.PE`), revisado contra el art. 6
   del D. Leg. 713.
   - Se quitó el Domingo de Resurrección, que el paquete incluye pero la norma no.
   - Los feriados agregados después: Batalla de Junín y de Ayacucho (desde 2022), Día de la Fuerza
     Aérea (desde 2023) y Batalla de Arica (desde 2024, Ley 31788).
2. **Días no laborables decretados**, uno por fila con su decreto supremo: los de cada año para el
   sector público; Juntas del Banco Mundial y el FMI (2015); APEC 2016 y 2024; visita del papa
   (2018); Cumbre de las Américas (2018); Juegos Panamericanos (2019); 2 de enero y 27 de julio
   de 2026.
   - Fuentes: notas de El Peruano, Andina, RPP y LP Derecho que citan el decreto.
   - [2022](https://andina.pe/agencia/noticia-conoce-los-dias-declarados-no-laborables-durante-2022-887159.aspx) ·
     [2023-2024](https://andina.pe/agencia/noticia-gobierno-declara-dias-no-laborables-compensables-para-ano-2023-y-2024-923286.aspx) ·
     [APEC 2024](https://rpp.pe/politica/gobierno/apec-oficializan-el-14-15-y-16-de-noviembre-como-dias-no-laborables-para-sectores-publico-y-privado-noticia-1596979) ·
     [Panamericanos 2019](https://www.americatv.com.pe/noticias/actualidad/lima-2019-gobierno-decretara-dias-no-laborables-juegos-panamericanos-n376343) ·
     [visita del papa](https://panamericana.pe/nacionales/238731-decretan-feriado-trujillo-puerto-maldonado-visita-papa)
3. **Feriados regionales del Sur**, los únicos con norma verificada:
   - Cusco, 24 de junio (Decreto Ley 21860);
   - Arequipa, 15 de agosto (Ley 24875, art. 8; [Gestión](https://gestion.pe/peru/el-15-de-agosto-es-dia-no-laborable-para-sector-publico-y-privado-en-arequipa-feriados-noticia/));
   - Tacna, 28 de agosto (Ley 23849).

**Ambigüedades y huecos.**

- **No se encontraron días no laborables de 2016 para el sector público**; solo APEC. Puede que
  no los haya habido.
- **Números de norma no verificados:** la ley de la Batalla de Junín, la de la Fuerza Aérea y el
  decreto de la visita del papa (la `fuente` lo dice).
- **Elecciones:** se votan en domingo y no hubo días no laborables decretados. En 2026 solo hubo
  permisos para quien vota en otra ciudad (DS 003-2026-TR) y la jornada extendida al 13 de abril
  en las mesas que no se instalaron (DS 053-2026-PCM). Ninguno es un día no laborable general.
- **El efecto de los días `sector_publico` es parcial:** el privado solo descansa si hay acuerdo.
  Para el modelo conviene una variable aparte de la de feriado.
- **Fuera de la tabla:** el 24 de junio de San Juan en Loreto, San Martín, Ucayali, Huánuco y
  Madre de Dios (ordenanzas regionales) y otros aniversarios locales. Además, la regla
  (fecha, tipo, ámbito) única obliga a una sola fila regional por fecha.
- **2026:** completo hasta donde hay norma al 24-oct-2026; podría salir otro decreto para diciembre.

## 7. `cuarentena_pe_2020`: fases de 2020

Son cinco fases, sin solapes, con su decreto:

1. **Cuarentena estricta** (16-mar al 03-may): DS 044-2020-PCM y prórrogas.
2. **Cuarentena con Fase 1** (04-may al 04-jun): DS 080-2020-PCM.
3. **Cuarentena con Fase 2** (05-jun al 30-jun): DS 101-2020-PCM.
4. **Fin de la cuarentena nacional con Fase 3** (01-jul al 25-sep): DS 116-2020-PCM y
   DS 117-2020-PCM. Hubo cuarentena focalizada en siete departamentos, cinco de ellos del Centro o
   el Sur (Arequipa, Ica, Junín, Huánuco, Madre de Dios).
5. **Fase 4** (26-sep al 31-dic): DS 157-2020-PCM.

**Ambigüedades.**

- La Fase 1 se publicó un domingo (03-may) y cada sector arrancó cuando aprobó sus protocolos:
  el 04-may es una aproximación.
- La cuarentena focalizada de julio a septiembre fue por departamento y provincia; la tabla solo
  la describe. Si el modelo por área la necesita, habría que agregar los departamentos afectados.
- **No incluye la segunda ola de 2021** (cuarentena focalizada en Lima y otras regiones en
  febrero de 2021). Habría que agregarla si el entrenamiento cubre 2021; el decreto está por
  verificar.

## 8. Decisiones que debe tomar el grupo

1. **Eventos interárea (5,6 %).** Casi todos son Mantaro - Cotaruse. ¿Se cuentan en las dos áreas,
   en el SEIN o en el área receptora?
2. **Áncash.** ¿Se acepta que el departamento vaya en el Norte con las excepciones de Vizcarra,
   Conococha y Huarmey resueltas por subestación?
3. **`DEMANDA_UL` de 2026.** ¿Se corrige el bloque Sur con esta tabla antes de calcular la cuota
   de usuarios libres por área? Hace falta mirar otro día de 2024-2026.
4. **SAIDI por área.** ¿Se arma la tabla `sistema_electrico → área` (323 sistemas) o basta la de
   empresas, excluyendo los sistemas aislados de Electro Oriente?
5. **Ciudades del Sur.** Arequipa + Tacna (propuesta) o Arequipa + Ilo. Y Huancayo: no sumarla al
   Centro (recomendación).
6. **Segunda ola de 2021.** ¿Se agrega a la tabla de cuarentena?
