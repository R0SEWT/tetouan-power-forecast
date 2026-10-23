# Comprensión del negocio

Fase 1 de CRISP-DM. La evidencia detrás de cada decisión está en la [investigación](investigacion.md)
y la procedencia de los datos, en [datos](datos.md).

## 1. Contexto

Tetuán, en el norte de Marruecos, recibe la electricidad a través de **Amendis**, el operador que
gestiona por delegación la distribución de agua y electricidad de la ciudad desde 2002. Amendis compra
la energía a la ONEE (Office National de l'Électricité et de l'Eau Potable) en alta tensión (63 kV), la
baja a media tensión (20 kV) en **tres subestaciones** y desde ahí la reparte a sus clientes. Su sistema
SCADA registra el consumo de cada subestación cada 10 minutos: de ahí sale el dataset de 2017.

## 2. El problema

Cada subestación tiene una capacidad. Si la demanda la supera, los transformadores se sobrecargan,
envejecen más rápido y pueden saltar las protecciones, y con ellas el suministro de una parte de la
ciudad. El centro de control ve el consumo en tiempo real, pero solo cuando ya ocurrió. Para actuar
antes del pico tiene que saber, con margen, cuánto va a demandar cada subestación.

El riesgo no es igual en todo el año ni en toda la ciudad. Las tres zonas tienen su pico al anochecer
(19-22 h). En verano, la zona costera consume en julio 58 % más que su promedio anual.

## 3. La decisión que apoya el pronóstico

| | |
|---|---|
| **Quién decide** | El centro de control de Amendis |
| **Qué decide** | Si hace falta transferir carga entre subestaciones o preparar una maniobra antes de un pico |
| **Cuándo** | Cada 10 minutos, mirando una hora hacia adelante |
| **Con qué información** | El consumo y el clima medidos hasta ese momento, y el calendario |
| **Costo de equivocarse** | Subestimar un pico deja al operador sin margen para maniobrar. Sobreestimarlo provoca maniobras innecesarias, que también cuestan, pero menos. |

Esta decisión ocurre en la realidad y deja huella en los datos: el 25 de octubre de 2017, cerca del
mediodía, parte de la carga de la Zona 1 pasó a la Zona 2. La Zona 1 bajó 12.5 % y la Zona 2 subió 11.3 %,
mientras la suma de ambas casi no cambió
([investigación](investigacion.md#un-cambio-estructural-la-transferencia-de-carga-del-25-de-octubre)).

**Fuera de alcance:** la compra de energía a la ONEE. Se decide con un día de anticipación, para toda la
ciudad y con pronósticos del clima, y este dataset no los tiene.

## 4. Por qué una hora

- **Diez minutos no alcanzan para reaccionar.** Además, en ese intervalo el consumo casi no cambia y el
  problema se reduce a copiar el valor actual.
- **Un día es otra decisión:** la compra de energía, con otro horizonte y otros datos.
- **Una hora deja margen para una maniobra operativa antes del pico.** Es el horizonte de muy corto plazo
  con el que la industria opera la red.

## 5. Las tres zonas y su papel

La fuente no dice qué subestación es cada zona. Se identifican por su comportamiento
([investigación, §2](investigacion.md#2-lo-que-dicen-los-datos-la-firma-de-carga)) y cada una cumple un
papel distinto en el proyecto.

| Zona | Qué la caracteriza | Papel | Pregunta que responde |
|---|---|---|---|
| **Zona 1** | 45 % de la demanda de la ciudad; la más estable | **Caso principal**: ajuste completo del modelo, importancia de variables y app | ¿Cuánto mejora el pronóstico donde está la mayor parte de la demanda? |
| **Zona 3** | Costera y de veraneo: picos de verano, se vacía en invierno | **Prueba de estrés** | ¿Aguanta el modelo niveles que no vio y una estacionalidad turística? |
| **Zona 2** | Ritmo laboral: cae los domingos y feriados | **Contraste** | ¿Sirve el mismo pipeline cuando domina el ciclo semanal? |

Las tres se modelan por separado con el mismo pipeline. Las otras dos zonas entran como predictoras a
través de sus rezagos.

## 6. Objetivos

- **De negocio:** que el centro de control anticipe con una hora el consumo de cada subestación, para
  actuar antes de los picos.
- **De data science:** un modelo de regresión por zona que estime el consumo en t+6 (una hora) con la
  información disponible en t y que sea mejor que las referencias ingenuas.

## 7. Información disponible al momento de predecir

Si la predicción se hace al cierre del periodo t:

| Información | ¿Disponible en t? |
|---|---|
| Consumo de las tres zonas hasta t | Sí |
| Clima observado hasta t | Sí |
| Calendario del periodo a predecir (hora, día, feriado, Ramadán) | Sí, se conoce de antemano |
| Clima en t+6 | No: el dataset no trae pronósticos del clima |
| Consumo en t+6 | No: es lo que se predice |

## 8. Criterios de éxito

**De data science.**

1. El MAE (kW) del modelo es menor que el de la **mejor de las tres referencias ingenuas** de la zona:
   persistencia (lo mismo que ahora), ayer a la misma hora y la semana pasada a la misma hora. Se exige
   en la validación de origen móvil y en la prueba final.
2. El MAPE (%) se reporta para comparar zonas de distinto tamaño.

**De negocio.**

3. En las horas pico (19-22 h) el modelo también le gana a la mejor referencia, porque ahí está el
   riesgo de sobrecarga.
4. Se reporta qué parte de los periodos pico se subestima en más de 5 %, porque ese es el error caro.

**Meta propuesta, a confirmar por el grupo:** en la Zona 1, al menos 20 % menos MAE que la mejor
referencia ingenua.

Hoy, la mejor referencia ingenua en la prueba tiene un MAPE de 2.9 % en la Zona 1 (semana pasada), 4.3 %
en la Zona 2 (semana pasada) y 6.0 % en la Zona 3 (ayer). La persistencia es la más débil en las tres
([investigación, §3](investigacion.md#3-qué-tan-difícil-es-cada-zona-las-referencias-ingenuas)).

**Cómo se evalúa.**

- Partición cronológica 70/15/15. La prueba (noviembre y diciembre) no se toca hasta el final.
- Validación de origen móvil sobre entrenamiento y validación, con un hueco de una hora entre el
  entrenamiento y cada bloque evaluado.
- Errores desagregados por mes, por hora, en días laborables y fines de semana, en feriados y en
  Ramadán, y antes y después de la transferencia de carga del 25 de octubre.

## 9. Supuestos, restricciones y riesgos

| Tipo | Qué | Cómo se maneja |
|---|---|---|
| Supuesto | Los consumos están en kW (lo dicen fuentes secundarias, no UCI) | Se declara en el paper |
| Supuesto | La identidad de las zonas no está confirmada | Se describen por su comportamiento, sin afirmar nombres |
| Restricción | Un solo año de datos: el verano y el ciclo anual se ven una vez | Validación de origen móvil y errores por temporada |
| Restricción | No hay pronósticos del clima | Solo se usa el clima observado hasta t |
| Restricción | No se conoce la capacidad de cada subestación | El error en hora pico y la subestimación de picos hacen de proxy del riesgo de sobrecarga |
| Riesgo | Los modelos de árboles no extrapolan a niveles que no vieron (el verano de la Zona 3) | Modelar el cambio respecto al consumo actual, no el nivel |
| Riesgo | Ramadán y los feriados del calendario hijri cambian de fecha cada año | Variables propias y evaluación aparte |
| Riesgo | Fuga de información del futuro | Solo variables conocidas en t, partición cronológica y hueco de una hora en la validación |
| Riesgo | Cambios en la red: la transferencia de carga del 25 de octubre deja a la prueba después de un cambio de nivel en las Zonas 1 y 2 | Errores reportados antes y después del cambio; preferir variables que se ajusten rápido (rezagos recientes) a las que fijan niveles |

## 10. Hipótesis para la comprensión de los datos

| | Hipótesis | Dónde se contrasta |
|---|---|---|
| H1 | El consumo sigue un ciclo diario con pico al anochecer | Notebook 01, comportamiento temporal |
| H2 | Las zonas difieren en su ciclo semanal: la zona laboral cae los fines de semana | Notebook 01, las tres zonas |
| H3 | El calor eleva el consumo en verano, sobre todo en la zona costera | Notebook 01, clima y consumo |
| H4 | Ramadán y los feriados cambian el perfil, y el calendario gregoriano no lo captura | Notebook 01, días especiales |
| H5 | La mejor referencia ingenua no es la misma en todas las zonas | Notebook 01, referencias ingenuas |

## 11. Plan

| Fase CRISP-DM | Entregable | Estado |
|---|---|---|
| 1. Negocio | Este documento y la [investigación](investigacion.md) | Hecho |
| 2. Datos | Notebook 01 y [datos](datos.md) | Hecho |
| 3. Preparación | Notebook 01 y el gold del [medallón](datos.md#capas) para las tres zonas | Hecha para la Zona 1; faltan Ramadán, feriados y el rezago semanal |
| 4. Modelado | Notebook 02 | Pendiente |
| 5. Evaluación | Notebook 02 | Pendiente |
| 6. Despliegue | App en Streamlit | Pendiente |

El cierre del TB1 es en la semana 15: short paper, app y exposición de 20 minutos.
