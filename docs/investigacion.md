# Investigación: qué zona es cuál y cómo pronostica la industria

Punto de partida de la [comprensión del negocio](negocio.md). Responde tres preguntas: qué son las tres
zonas del dataset, qué tan difícil es pronosticar cada una, y cómo aborda este problema la industria
eléctrica.

Las tablas se generan con `uv run python -m tetouan_power_forecast.perfiles`, sobre el silver del
[medallón](datos.md). Las funciones están en `src/tetouan_power_forecast/perfiles.py`.

## 1. Qué dicen las fuentes sobre las zonas

- UCI describe los datos solo como el consumo de "tres redes de distribución" de Tetuán. No nombra las
  zonas y no da unidades.
- La descripción del dataset que circula en Kaggle y en los repositorios que lo usan agrega que los datos
  vienen del SCADA de **Amendis**, el operador de distribución, y que la red se alimenta de **tres
  subestaciones: Quads, Smir y Boussafou**. No dice qué subestación es cada zona.
- El único mapeo que circula (Zona 1 = Quads, Zona 2 = Boussafou, Zona 3 = Smir) viene de un artículo
  de divulgación sin respaldo. Los papers que usan los nombres no son de acceso abierto. Uno que sí lo es
  (Hybrid LSTM-XGBoost, MDPI) solo numera las zonas.

**Conclusión:** no hay una fuente primaria accesible que identifique las zonas. La identificación tiene
que salir del comportamiento de los datos.

## 2. Lo que dicen los datos: la firma de carga

Las empresas eléctricas distinguen qué tipo de demanda tiene una zona por la forma de su curva de carga:
cuándo sube y baja durante el día, si cae el fin de semana, cuánto responde al calor y cómo cambia en
los días especiales.

| | Zona 1 | Zona 2 | Zona 3 |
|---|---:|---:|---:|
| Parte de la demanda de la ciudad (%) | 45.41 | 29.54 | 25.04 |
| Factor de carga (media / máximo) | 0.62 | 0.56 | 0.37 |
| Domingo de día / laborable (9-17 h) | 0.91 | 0.81 | 1.01 |
| Julio / promedio anual | 1.11 | 1.15 | 1.58 |
| Mes más alto / mes más bajo | 1.26 | 1.40 | 2.55 |
| Sensibilidad al calor en verano (%/°C) | 0.95 | 3.03 | 6.94 |
| Ramadán de día / mes previo (9-16 h) | 0.98 | 0.93 | 0.99 |
| Ramadán de madrugada / mes previo (0-4 h) | 1.44 | 1.41 | 1.45 |

Feriados de 2017 en día laborable (consumo del feriado / mismo día de semana sin feriado):

| | Zona 1 | Zona 2 | Zona 3 |
|---|---:|---:|---:|
| 11-ene · Manifiesto de la Independencia | 0.97 | 0.92 | 0.96 |
| 1-may · Día del Trabajo | 0.91 | 0.92 | 0.97 |
| 26-jun · Eid al-Fitr | 0.88 | 0.80 | 0.99 |
| 27-jun · Eid al-Fitr | 0.82 | 0.77 | 0.94 |
| 14-ago · Oued Ed-Dahab | 0.95 | 0.97 | 1.03 |
| 21-ago · Día de la Juventud | 1.02 | 1.03 | 1.18 |
| 1-sep · Eid al-Adha | 0.83 | 0.73 | 0.77 |
| 6-nov · Marcha Verde | 0.94 | 0.95 | 0.91 |
| 1-dic · Mawlid | 0.93 | 0.88 | 0.86 |

### Lectura

- **Zona 3: costera y de veraneo.** Tiene el factor de carga más bajo, es la que más responde al calor y
  más sube en julio. Es la única cuyo consumo no baja el domingo, y sube 18 % en el feriado del 21 de
  agosto, cuando en otras zonas no cambia. En diciembre consume menos de la mitad que en julio. Es el comportamiento de una
  zona con población estacional, coherente con **Smir**, la franja costera turística al norte de Tetuán.
- **Zona 2: ritmo laboral.** Es la que más cae el domingo de día (−19 %) y en los feriados (−27 % en
  Eid al-Adha), y la única que baja de día en Ramadán, cuando se acorta la jornada. Su demanda sigue la
  actividad de comercio, administración o industria. No pude verificar el carácter de Boussafou, así
  que el nombre queda abierto.
- **Zona 1: la red urbana mixta.** Concentra casi la mitad de la demanda, es la más estable (factor de
  carga más alto) y combina rasgos residenciales y laborales.
- **Las tres comparten un efecto que el calendario gregoriano no captura:** en Ramadán, el consumo de
  madrugada sube entre 41 y 45 %. El Ramadán cae en fechas distintas cada año, así que ni el mes ni el
  día del año lo representan.

### Un cambio estructural: la transferencia de carga del 25 de octubre

El 25 de octubre de 2017, cerca del mediodía, la Zona 1 cae y la Zona 2 sube en espejo frente al mismo
momento del día anterior: a las 18 h, −4,903 y +4,858 kW. La suma de las dos casi no cambia. Consumo medio de
las dos semanas anteriores (11-24 de octubre) y las dos posteriores (26 de octubre-8 de noviembre):

| | antes (kW) | después (kW) | cambio (%) |
|---|---:|---:|---:|
| Zona 1 | 33,623.8 | 29,419.3 | -12.5 |
| Zona 2 | 21,109.2 | 23,489.6 | 11.3 |
| Zona 3 | 13,291.6 | 12,410.0 | -6.6 |
| Zona 1 + Zona 2 | 54,733.0 | 52,908.9 | -3.3 |

Es una **transferencia de carga entre subestaciones**: parte de los clientes de la Zona 1 pasaron a la
Zona 2. La baja de la suma (−3.3 %) coincide con la baja estacional que también tiene la Zona 3. Tres
consecuencias:

- La decisión que el proyecto busca apoyar (transferir carga entre subestaciones) ocurre en la realidad y
  queda registrada en los datos.
- La prueba (desde el 6 de noviembre) y el final de la validación caen después del cambio. La subida de la
  Zona 2 en noviembre y diciembre no es estacional: es la transferencia.
- Las firmas de carga de las Zonas 1 y 2 se calculan, sobre todo, con datos anteriores al cambio.

### Hipótesis de trabajo

| Zona | Identidad probable | Confianza |
|---|---|---|
| Zona 3 | Smir, zona costera turística | Media-alta: varias señales independientes coinciden |
| Zona 2 | Zona de actividad laboral | Media: el patrón es claro, el nombre no |
| Zona 1 | Red urbana principal | Media: la de mayor peso y comportamiento más mixto |

Conviene validar esta lectura con la profesora o con alguien que conozca la red de Tetuán antes de usar
los nombres en el paper. Mientras tanto, se habla de "Zona 1, 2 y 3" y se describe su comportamiento.

## 3. Qué tan difícil es cada zona: las referencias ingenuas

Toda evaluación de un pronóstico de carga se compara contra referencias ingenuas: reglas que no
aprenden nada. Para un horizonte de una hora (t+6) hay tres habituales:

- **persistencia:** en una hora se consumirá lo mismo que ahora (t);
- **ayer:** se consumirá lo mismo que a esa hora de ayer (t+6−144);
- **semana pasada:** lo mismo que a esa hora hace una semana (t+6−1008).

MAPE (%) de cada referencia en la partición cronológica del gold (sin las filas de hueco):

| | persistencia | ayer | semana_pasada |
|---|---:|---:|---:|
| Zona 1 · validacion | 6.25 | 3.64 | 4.56 |
| Zona 1 · prueba | 6.29 | 3.44 | 2.94 |
| Zona 2 · validacion | 6.45 | 6.49 | 5.50 |
| Zona 2 · prueba | 6.78 | 5.15 | 4.32 |
| Zona 3 · validacion | 7.51 | 4.63 | 6.62 |
| Zona 3 · prueba | 8.08 | 6.00 | 11.13 |

- **La persistencia es la más débil en todas las zonas.** Ganarle no demuestra que el modelo sirva.
- **La mejor referencia cambia por zona.** En la Zona 2 gana "semana pasada", lo que confirma su ciclo
  semanal laboral. En la Zona 3, "semana pasada" falla en la prueba porque el consumo cae semana a semana
  al salir de la temporada.
- **La prueba (noviembre y diciembre) cae en temporadas distintas para cada zona.** Es temporada alta
  para la Zona 2 y baja para la Zona 3. El verano de la Zona 3, donde está el riesgo, queda en el
  entrenamiento y solo se puede evaluar con validación de origen móvil.

## 4. Cómo lo aborda la industria

1. **Se pronostica cada subestación y también el total.** La competencia de referencia del área,
   GEFCom2012, pedía pronosticar 20 zonas de una empresa eléctrica estadounidense y su suma
   (Hong, Pinson y Fan, 2014). A nivel de subestación se aceptan errores mayores que a nivel sistema: el
   JRC de la Comisión Europea pone como meta un MAPE menor a 20 % para pronósticos de subestación o
   transformador. Un meta-análisis de errores de pronóstico de corto plazo no encontró diferencias
   significativas entre subestación y sistema.
2. **El horizonte depende de la decisión.** Una hora adelante sirve para operar la red: anticipar
   sobrecargas y preparar maniobras. Ahí la carga reciente pesa más que el clima. La compra de energía se
   decide con un día de anticipación y se apoya en pronósticos del clima, que este dataset no tiene.
3. **Se compara contra referencias ingenuas fuertes**, no solo contra la persistencia. La referencia
   clásica con modelo es el *vanilla benchmark* de Tao Hong, usado en GEFCom2012: una regresión lineal
   con tendencia, calendario, temperatura y sus interacciones.
4. **Se evalúa con origen móvil a lo largo del año**, y los errores se reportan por temporada, por hora
   (sobre todo en las horas pico) y aparte para los días especiales. En países musulmanes, los feriados
   del calendario hijri y el Ramadán se modelan como efectos propios. Según el país, el Ramadán sube o
   baja la carga: en Jordania baja porque se acorta la jornada y en Indonesia sube de noche.
5. **Cada vez más, se dan intervalos y no solo un valor.** El pronóstico probabilístico (cuantiles,
   evaluados con *pinball loss*) ganó terreno con GEFCom2014, que fue íntegramente probabilística
   (Hong y Fan, 2016).

## 5. Qué implica para el proyecto

- **Tres zonas, un mismo pipeline, papeles distintos:** la Zona 1 es el caso principal, la Zona 3 la
  prueba de estrés (picos de verano y niveles que el modelo no vio) y la Zona 2 el contraste (ciclo
  semanal laboral).
- **El criterio de éxito se mide contra la mejor de las tres referencias ingenuas de cada zona**, no solo
  contra la persistencia.
- **La evaluación usa origen móvil** y reporta los errores por temporada, en hora pico, en feriados y en
  Ramadán, y por separado antes y después de la transferencia de carga del 25 de octubre.
- **Variables candidatas para la preparación:** indicador de Ramadán, indicador de feriado y el rezago
  de la semana pasada.
- **Opcional, como diferencial:** intervalos de predicción por cuantiles en la app.

## Fuentes

- Salam, A. y El Hibaoui, A. (2018). *Power Consumption of Tetouan City* [dataset]. UCI Machine Learning
  Repository. <https://archive.ics.uci.edu/dataset/849/power+consumption+of+tetouan+city>
- Descripción del dataset con el origen en Amendis y las tres subestaciones:
  <https://www.kaggle.com/datasets/fedesoriano/electric-power-consumption> (replicada en
  <https://github.com/Merci93/Tetouan_Power_Consumption-SQL_Aanalysis>)
- Mapeo de zonas no confirmado: <https://medium.com/@mehranwaheed/project-overview-98fe6424f3b9>
- *Forecasting Energy Consumption Using a Hybrid LSTM-XGBoost Model* (MDPI):
  <https://www.mdpi.com/2673-4591/144/1/4>
- Habib et al. (2025). *Forecasting Tetouan energy demand employing shift approach in
  machine-learning*. Quality & Quantity, 59.
  <https://www.researchgate.net/publication/387440487_Forecasting_Tetouan_energy_demand_employing_shift_approach_in_machine-learning_complementing_econometric_insights>
- Hong, T., Pinson, P. y Fan, S. (2014). Global Energy Forecasting Competition 2012. *International
  Journal of Forecasting*, 30(2), 357-363. <https://ideas.repec.org/a/eee/intfor/v30y2014i2p357-363.html>
- Hong, T. y Fan, S. (2016). Probabilistic electric load forecasting: A tutorial review. *International
  Journal of Forecasting*, 32(3), 914-938. <https://ideas.repec.org/a/eee/intfor/v32y2016i3p914-938.html>
- Meta-regresión de errores de pronóstico de carga de corto plazo: <https://arxiv.org/pdf/2305.18550>
- JRC, Comisión Europea, metas de precisión por nivel de la red: <https://ses.jrc.ec.europa.eu/node/52843>
- *Vanilla benchmark* de Tao Hong, descrito en <https://arxiv.org/pdf/2305.05575>
- Ramadán y carga eléctrica: Jordania <https://jordantimes.com/node/281923>; Indonesia
  <https://en.tempo.co/amp/1204406/ramadan-electricity-consumption-increases-5-percent-pln-says>;
  calendario hijri en Turquía
  <https://scholar.its.ac.id/en/publications/hybrid-dynamic-harmonic-regression-with-calendar-variation-for-tu/>
