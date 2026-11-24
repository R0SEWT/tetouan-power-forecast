# Conciliación de demanda del COES

Se alinearon el anexo de despacho del Programa Diario, la API de demanda programada,
el gráfico de demanda del portal y el IEOD. Las horas se tratan como fin de periodo en
Lima. La última fila del anexo, rotulada `23:59`, se empareja con la media hora que
termina a las `00:00` del día siguiente. Se mantuvieron el SHA-256 y la primera hora
de observación de cada insumo. Las descargas históricas sirven para verificar
contenido, con la fecha de captura actual.

## Resultados del cruce

Valores en MW de diferencia absoluta media. Cada comparación con cifra usa 48 pares.

| Día | API SEIN frente a Demanda YUPANA del anexo | API SEIN frente a Demanda COES del anexo | Programación Diaria del portal frente a Demanda COES | Ejecutado del portal frente a SEIN del IEOD |
| --- | ---: | ---: | ---: | ---: |
| 2025-06-15 | 0,0 | 48,3 | 104,1 | 81,4 |
| 2026-10-26 | 0,0 | 69,4 | 91,4 | 99,0 |
| 2026-11-22 | 0,0 | 29,5 | 95,2 | 88,0 |
| 2026-11-23 | 0,0 | 47,8 | 92,7 | — |
| 2026-11-24 | 0,0 | 43,3 | — | — |

Centro, Norte, Sur y Electroandes también coinciden sin tolerancia entre el anexo
y la API en las cinco fechas. El total de la API coincide valor por valor con
«Demanda YUPANA», una columna distinta de «Demanda COES». La «Programación
Diaria» del portal difiere de ambas columnas en todas las fechas comparables.
El Ejecutado del gráfico supera al SEIN del IEOD en los tres días cruzados.
Esa diferencia de nivel, por sí sola, no identifica su causa.

## Regla para probar en el piloto

- **Edición de referencia.** Usar el anexo de despacho del catálogo Programa Diario
  con la primera captura exitosa anterior al inicio del día objetivo. Guardar el
  hash utilizado. Las actualizaciones y RDO mantienen identidades separadas.
  Una captura retrospectiva permite estudiar el contenido, pero no certificar
  la edición que estaba disponible en el momento de emitir.
- **Perímetro.** Estudiar por separado las parejas Demanda COES y Demanda YUPANA
  con Ejecutado del portal e IEOD. Antes del preregistro prospectivo se debe
  documentar qué previsión y real representan un mismo perímetro. Los nombres
  de las columnas son insuficientes para decidirlo.
- **Edición de cierre del Ejecutado.** Probar la primera captura completa de 48
  periodos desde las 00:00 de D+2 en Lima. Si no hay captura completa antes de
  D+3, marcar el día como faltante. Es una regla candidata que debe verificarse
  con el archivo recurrente antes de fijarla. Las capturas posteriores permiten
  medir revisiones y quedan archivadas.

El cruce se reproduce con `python -m experimentos.en_vivo.conciliar_coes`. El
script produce una tabla por media hora y un resumen por fecha y pareja, con
conteos explícitos cuando faltan datos. Los archivos crudos y las salidas de
trabajo se mantienen fuera de Git.
