# Protocolo de reanálisis para TB1

El protocolo fija los cálculos nuevos sobre ventanas que el equipo ya exploró. Las
cifras preliminares de Tetuán frente a los deltas y el resultado de Ceuta frente al
delta semanal ya se conocen. Esta versión organiza su reproducción. El experimento
prospectivo del SEIN tendrá su propio preregistro, con otra pregunta y otra muestra.

## Ventanas y comparadores

| Serie | Evaluación | Comparadores |
| --- | --- | --- |
| Tetuán a 60 min | 7.841 orígenes guardados por zona, del 6 de noviembre al 30 de diciembre de 2017 | Gradient Boosting global y semanal guardados, persistencia, mejor de las tres referencias históricas, delta diario, delta semanal, promedio simple de deltas, semana ajustada por nivel y promedio de cuatro semanas ajustadas |
| Ceuta a 60 min | Orígenes de julio y agosto de 2022–26. El verano 2021 se reserva para selección si se ajusta una referencia. V4 se ajusta cada año con enero a junio, dejando un hueco de una hora en los objetivos de entrenamiento | V4 sin verano, delta semanal y referencias ajustadas por nivel, con persistencia y la referencia histórica como contexto |

Se reportan todos los comparadores especificados. La mejor histórica es el menor MAE
entre persistencia, ayer y semana pasada sobre las filas de reporte. Se conserva como
reproducción de la regla histórica. El delta diario y el promedio de deltas son las
comparaciones destacadas de Tetuán y el delta semanal es la de Ceuta. Si se selecciona
una referencia ajustada, se usan solo datos anteriores a la ventana de reporte.

La reproducción de Ceuta aplica los cortes al reloj UTC del silver, como la
corrida original. El corte con el calendario civil de Ceuta es una sensibilidad
de auditoría.

## Emparejamiento y métricas

- Cada pronóstico se identifica por serie, fecha de origen y fecha objetivo. Para las
  predicciones rodantes de TB1, el objetivo queda 60 minutos después del origen.
  Se comprueba el real guardado contra la serie de demanda y se rechazan duplicados
  de la clave. Los rezagos se buscan por fecha, sin saltar huecos.
- Para un origen `t`, objetivo `t+h` y periodo estacional `P`, el rezago es
  `S = techo(h/P) × P`. El delta es `y[t] + y[t+h−S] − y[t−S]`. El ajuste de nivel
  multiplica el valor de la semana análoga por el cociente entre la media móvil
  de 24 h en el origen y la media móvil en el origen desplazado por el rezago.
  Las medias se calculan con ventanas completas y terminan en el instante indicado.
- Todos los métodos se puntúan en una intersección por zona o verano. Se publica
  cuántas filas entraron y cuántas se perdieron, más el número de reales no positivos.
  El MAPE usa únicamente reales positivos y el MAE conserva todos los reales finitos.
- Para Tetuán se reportan MAE, MAPE y skill de MAE `1 − MAE_modelo / MAE_referencia`.
  Para Ceuta se reportan MAPE y MAE por verano y la media aritmética de las métricas
  de los cinco veranos. También se incluye el número de filas por verano para
  distinguir esa media de un promedio ponderado por volumen.
- Predicciones guardadas tienen preferencia. Si falta V4 de Ceuta por fila, se permite
  reproducir su receta original con el corte y las variables históricos, marcando
  que se regeneró. La auditoría distinguirá valores de clima observado y huecos
  rellenados de insumos disponibles en el momento de emitir.

## Presentación

TB1 usa tablas descriptivas. El contraste de Tetuán tiene nueve pares previstos
(tres zonas por delta diario, semanal y promedio) y el de Ceuta tiene cinco pares
por verano frente al delta semanal. Se someten a calibración del remuestreo por
bloques y, si se publican pruebas formales, se controla multiplicidad dentro de cada
familia. Ambas son familias de reanálisis. Cualquier cambio de ventana, métrica,
comparador o población se registra con fecha y motivo.
