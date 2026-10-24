# El paper: objetivos y estructura en tres actos

Borrador para el grupo. El paper cuenta **una sola metodología puesta a prueba tres veces**, cada vez en una situación
más difícil para el modelo: poco histórico (Tetuán), otro sistema y varios años (Ceuta) y un evento extraordinario por
área (el SEIN con El Niño de 2026). Perú es el caso central y se lleva la mayor parte de los resultados; Tetuán y Ceuta
son los dos primeros objetivos específicos, no un apéndice.

## Hilo conductor

Un pronóstico de demanda de muy corto plazo falla cuando la demanda llega a niveles que el modelo no vio al entrenar.
En Tetuán eso pasa porque hay un solo año de datos; en el SEIN, porque El Niño de 2026 empuja la demanda del Norte muy
por encima de lo normal. La misma respuesta metodológica (pronosticar la razón con la media de las últimas 24 horas,
con un modelo global y contra referencias ingenuas) se evalúa en los tres casos.

Título tentativo: *Pronóstico de demanda eléctrica de muy corto plazo ante niveles no vistos: de Tetuán a El Niño de
2026 en el SEIN*.

## Objetivo general

Desarrollar y validar una metodología de pronóstico de la demanda eléctrica a muy corto plazo que se sostenga cuando
la demanda se sale de lo que el modelo vio, y medir qué ayuda más a adaptarla durante un evento extraordinario.

## Objetivos específicos

| | OE1. Tetuán | OE2. Ceuta | OE3. SEIN (Perú) |
|---|---|---|---|
| **Objetivo** | Diseñar un pronóstico a 1 h que no dependa de aprender el nivel, con un solo año de datos, y situarlo frente al estado del arte del dataset | Verificar que la elección generaliza a un sistema vecino con varios años, sobre todo a niveles no vistos | Medir, por área y durante El Niño extraordinario de 2026, qué tan bien se pronostica la demanda y qué ayuda más: información exógena o reentrenar |
| **Datos** | UCI 849: 2017, cada 10 min, tres zonas | Red Eléctrica: demanda de Ceuta, mayo de 2019 a octubre de 2026, cada 10 min | COES (IEOD): Norte, Centro y Sur, 2016 a 2026, cada 30 min; ERA5, ICEN, Niño 1+2, fallas del COES, SAIDI |
| **Lo que se pone a prueba** | Niveles no vistos dentro del año (el verano, la transferencia de carga del 25 de octubre) | Veranos no vistos en siete años distintos | Un nivel no visto en el sistema nacional, distinto en cada área |
| **Criterio de éxito** | Le gana a la mejor referencia ingenua en todas las zonas y meses; al menos 20 % menos MAE que ella en la prueba | El objetivo en razón le gana al objetivo en nivel, y entrenar sin haber visto un verano sigue por debajo de la mejor ingenua | M0 le gana a la mejor ingenua en las tres áreas en 2025; en 2026, la diferencia entre variantes con su intervalo al 95 %. "Sin efecto" también es un resultado |
| **Estado** | Hecho: le gana en 24 de 24 meses-zona y en la prueba queda 41-56 % por debajo de la mejor ingenua | Hecho: gana en los 25 pares de verano e historia; sin verano, 2.31 % de MAPE contra 4.62 % de la mejor ingenua | Validación 2025 hecha (M0 gana en los 6 casos; las exógenas no ayudan, como se previó). Faltan la prueba de 2026, el experimento de adaptación y la comparación con la Programación Diaria del COES |

Las hipótesis del OE3 están escritas antes de ver la prueba, en la [spec](../superpowers/specs/2026-10-23-demanda-sein-areas-design.md) (§1).

### Texto para la introducción (borrador)

> El objetivo general es desarrollar y validar una metodología de pronóstico de la demanda eléctrica a muy corto plazo
> que se sostenga cuando la demanda se sale de lo que el modelo vio al entrenar. Se evalúa en tres casos de dificultad
> creciente. Primero, con el consumo de Tetuán, que tiene un solo año de datos, se diseña un pronóstico a una hora que
> no depende de aprender el nivel y se compara con los trabajos publicados sobre el mismo dataset (OE1). Segundo, se
> verifica que la elección generaliza a Ceuta, un sistema vecino con siete años de datos, en particular a veranos que
> el modelo no vio (OE2). Tercero, se lleva la metodología a la demanda de las tres áreas operativas del SEIN y se mide,
> durante El Niño Costero extraordinario de 2026, qué ayuda más a adaptar el pronóstico: sumar información exógena
> (clima, El Niño, fallas) o reentrenar con más frecuencia, y cómo queda frente al pronóstico oficial del COES (OE3).

## Estructura del paper

La extensión depende de la plantilla del curso (a confirmar). El reparto se da en proporción, no en páginas.

| Sección | Contenido | Peso |
|---|---|---|
| 1. Introducción | El problema del operador; el vacío (la literatura de Tetuán casi no se compara con referencias ingenuas y no hay estudios del efecto de El Niño en la demanda del SEIN); el objetivo general y los tres específicos | Bajo |
| 2. Datos | Una tabla con los tres casos: fuente, periodo, resolución, series, partición. La regla de información del SEIN | Bajo |
| 3. Metodología | Común a los tres casos, siguiendo CRISP-DM: objetivo en razón, modelo global, referencias ingenuas, origen móvil, *bootstrap* por días. Lo propio del SEIN: exógenas por grupos (M0-M4), experimento de adaptación, comparación con la Programación Diaria | Medio |
| 4.1 Resultados: Tetuán (OE1) | La mejora frente a la mejor ingenua y la Tabla 1 contra el estado del arte | Bajo |
| 4.2 Resultados: Ceuta (OE2) | La Tabla 2, con y sin verano visto | Bajo |
| 4.3 Resultados: SEIN (OE3) | Validación 2025 y ablación; prueba 2026 por área y horizonte; adaptación; frente al COES | **Alto: la mitad o más de los resultados** |
| 5. Discusión y amenazas a la validez | Qué se sostiene en los tres casos y qué no; los límites de cada uno | Medio |
| 6. Conclusiones | Una por objetivo específico | Bajo |
| Declaración de uso de IA | Exigida por el curso y por la política del CIP | — |

## Tabla 1 (borrador): Tetuán frente al estado del arte

Pronóstico a una hora del consumo de Tetuán. La comparación justa es la **mejora frente a la persistencia**, porque
cada trabajo usa otro periodo de prueba y otra resolución.

| Trabajo | Serie | Entrenamiento y prueba | Error del modelo | Error de la persistencia | Mejora frente a la persistencia |
|---|---|---|---|---|---|
| Wei (2023) | Cada zona, cada 10 min | Entrena con enero; prueba de febrero a diciembre | MAE 1,866 · 1,281 · 2,013 kW | — | −14 % · −11 % · **+44 %** |
| Al-Quraan et al. (2023) | Total, medias horarias | 80/20, sin decir si es cronológica | MAPE 3.43 % | MAPE 6.64 % | −48 % |
| Kshetrimayum et al. (2024) | Total, medias horarias | Origen móvil, 4 pliegues | MAPE 2.49 % | MAPE 6.60 % | −62 % |
| **Este trabajo**, primer pliegue | Cada zona, cada 10 min | Entrena con enero y febrero; prueba en marzo | MAE 612 · 483 · 375 kW | MAE 2,279 · 1,372 · 1,419 kW | **−73 % · −65 % · −74 %** |
| **Este trabajo**, prueba | Cada zona, cada 10 min | Entrena hasta octubre; prueba en noviembre y diciembre | MAE 462 · 429 · 429 kW (MAPE 1.63 · 1.91 · 3.63 %) | MAE 1,821 · 1,567 · 951 kW | **−75 % · −73 % · −55 %** |
| **Este trabajo**, prueba | Total (suma de las zonas) | Igual | MAPE 1.42 % | MAPE 6.48 % | **−78 %** |

Notas para el pie de la tabla:

- Las cifras de este trabajo son del modelo global (Gradient Boosting) del notebook 02 de Tetuán.
- El primer pliegue es el que más se parece a Wei (2023): entrena con dos meses, frente a uno de él.
- Al-Quraan et al. y Kshetrimayum et al. trabajan con medias horarias del total, que son más suaves que los datos
  cada 10 minutos. Su persistencia (6.6 %) es casi igual a la nuestra para el total (6.48 %), así que la mejora
  relativa es comparable en orden de magnitud.
- Quedan fuera las obras a 10 minutos (ahí la persistencia ya da un MAPE de 1.2 a 1.7 %), las que estiman el mismo
  instante sin pronosticar y las que solo reportan métricas normalizadas ([estado del arte](../estado-del-arte.md),
  §3.3).

## Tabla 2 (borrador): Ceuta, julio y agosto

Media de los veranos 2022-2026, MAPE (%), con el clima solo de ERA5. "Nivel" es el modelo con el objetivo en nivel y calendario anual; "razón",
el objetivo en razón. Fuente: [`docs/historico.md`](../historico.md), sección 8.

| Mejor ingenua | Nivel, sin verano | Razón, sin verano | Nivel, 1 año | Razón, 1 año | Razón, 2 años | Razón, 3 años |
|---:|---:|---:|---:|---:|---:|---:|
| 4.62 | 2.87 | **2.31** | 2.10 | **1.93** | 1.84 | 1.81 |

## De dónde sale cada cifra

- **Tetuán:** `reportes/modelado/prueba.csv`, `origen_movil.csv` y `predicciones_prueba_zona{1,2,3}.csv`, que escribe
  el notebook `02_modelado_evaluacion.ipynb` (PR de modelado de Tetuán). El total suma las predicciones de las tres
  zonas.
- **Trabajos publicados:** [`docs/estado-del-arte.md`](../estado-del-arte.md), tabla 2.1 (filas 6, 7 y 10) y §3.2.
- **Ceuta:** [`docs/historico.md`](../historico.md), sección 8.
- **SEIN:** `reportes/sein/linea_base.csv` y el notebook 01 del SEIN, en el Drive.

## Pendiente

- La prueba de 2026, el experimento de adaptación y la Programación Diaria del COES (OE3).
- Repetir las tablas con las cifras finales si los notebooks se vuelven a correr.
- Copiar la Tabla 1 a las conclusiones del notebook 02 de Tetuán, que siguen vacías.
- Confirmar la plantilla y la extensión del short paper.
