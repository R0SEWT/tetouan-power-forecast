# Antecedente metodológico del paper: Tetuán y Ceuta

El caso central del paper es la demanda por área del SEIN ([spec](../superpowers/specs/2026-10-23-demanda-sein-areas-design.md)).
Tetuán y Ceuta entran como antecedente breve: un párrafo y una tabla contra el estado del arte. Este archivo tiene el
borrador de los dos y de dónde sale cada cifra.

## Párrafo (borrador)

> **Antecedente metodológico.** La metodología se desarrolló antes sobre el consumo eléctrico de Tetuán (UCI 849;
> Salam y El Hibaoui, 2018), que tiene un solo año (2017) de datos cada 10 minutos en tres zonas. Con un año, un modelo
> de árboles no extrapola a niveles que no vio, como el verano de la zona costera. Pronosticar la razón entre el
> consumo de una hora después y la media de las últimas 24 horas, con un modelo global de las tres zonas, resolvió ese
> problema: en la prueba de noviembre y diciembre, el error absoluto medio quedó entre 55 y 75 % por debajo de la
> persistencia y entre 41 y 56 % por debajo de la mejor referencia ingenua, y en el origen móvil mensual le ganó a la
> mejor referencia en los 24 meses-zona. La Tabla 1 lo sitúa frente a los trabajos publicados de diseño comparable: de
> unas 70 obras que usan el dataset, solo Wei (2023) pronostica cada zona a una hora con partición cronológica, y solo
> dos se comparan con la persistencia. Para comprobar que la elección no depende de Tetuán, se repitió en Ceuta, el
> sistema vecino, con los veranos de 2020 a 2026 de Red Eléctrica: el objetivo en razón le ganó al objetivo en nivel en
> todos los casos, y entrenar sin haber visto un verano subió el MAPE de julio y agosto solo de 1.94 a 2.33 %, la mitad
> que la mejor referencia ingenua (4.63 %). Esa propiedad, aguantar niveles que el modelo no vio, es la que el caso
> peruano pone a prueba a mayor escala con El Niño de 2026.

## Tabla 1 (borrador)

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

## De dónde sale cada cifra

- **Este trabajo:** `reportes/modelado/prueba.csv`, `origen_movil.csv` y `predicciones_prueba_zona{1,2,3}.csv`, que
  escribe el notebook `02_modelado_evaluacion.ipynb` (PR de modelado de Tetuán). El total suma las predicciones de las
  tres zonas.
- **Trabajos publicados:** [`docs/estado-del-arte.md`](../estado-del-arte.md), tabla 2.1 (filas 6, 7 y 10) y §3.2.
- **Ceuta:** [`docs/historico.md`](../historico.md), resumen y sección de la validación externa.

## Pendiente

- Repetir la tabla con las cifras finales si el notebook 02 de Tetuán se vuelve a correr.
- Copiar la tabla a las conclusiones del notebook 02 de Tetuán, que siguen vacías.
