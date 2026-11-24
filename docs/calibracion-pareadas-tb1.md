# Piloto de calibración de las pruebas pareadas de TB1

Para ventanas de 55 y 62 días se simuló una diferencia de pérdidas con media
nula y dependencia AR(1). Se fijaron cuatro niveles de autocorrelación (0, 0,3,
0,6 y 0,8), innovaciones normales y t de 5 grados de libertad, 2.000
simulaciones por escenario y 1.999 réplicas del bootstrap circular centrado
por prueba. El criterio previo fue una tasa de rechazo entre el 3 y el 7 %
con nivel nominal del 5 %.

| Longitud del bloque | Tasa mínima | Mediana | Máxima | Escenarios dentro del criterio |
| ---: | ---: | ---: | ---: | ---: |
| 1 día | 4,7 % | 24,8 % | 56,3 % | 4/16 |
| 3 días | 5,6 % | 15,1 % | 37,6 % | 3/16 |
| 7 días | 8,4 % | 12,8 % | 27,7 % | 0/16 |
| 14 días | 12,6 % | 16,5 % | 28,2 % | 0/16 |

El procedimiento evaluado es la prueba bilateral sobre la media diaria con
réplicas centradas y sin studentizar. Los resultados muestran problemas de
tamaño incluso cuando se remuestrean semanas. TB1 mantiene los efectos
descriptivos. Para justificar una prueba formal hay que contrastar otros
procedimientos con una familia de nulos que además refleje la dependencia
observada en las pérdidas reales. Este piloto no mide potencia ni valida una
prueba prospectiva del SEIN.

El piloto se reproduce con este comando.

```bash
python -m experimentos.historico.calibrar_pareadas --salida /ruta/privada/calibracion_nulo.csv
```
