# Auditoría inicial de datos y modelos

Hallazgos verificados al preparar el reanálisis de TB1 y el futuro ensayo del corrector.
Las capas, los modelos y sus resultados se conservan con sus fechas originales.

| Control | Evidencia observada | Implicación |
| --- | --- | --- |
| Ceuta, reloj y valores válidos | El silver UTC contiene 391.975 fechas únicas y cuatro demandas no positivas. Ninguna cae en las ventanas emparejadas de julio y agosto de 2022–26. Al cambiar los cortes del verano a hora civil de Ceuta, el MAPE medio resulta 2,29 % para V4 y 2,06 % para el delta semanal. | El MAPE de TB1 conserva las 8.928 filas por verano y el corte histórico en UTC. El delta semanal también gana los cinco veranos con cortes civiles. |
| Tetuán, reloj sin zona declarada | Los 52.416 sellos son únicos y consecutivos cada 10 minutos. Al contrastar los cambios de hora de `Africa/Casablanca` con la mediana del centroide diario de irradiancia difusa de 06:00 a 21:59 (diez días a cada lado), los saltos son −5,6, +10,7, +0,6 y +7,5 minutos, en orden cronológico. | La rejilla y la irradiancia son compatibles con un reloj de desfase fijo, sin identificar su desfase exacto. El reanálisis conserva el reloj del archivo y deja la atribución de horarios civiles como sensibilidad. |
| SEIN, suma de áreas | En 2024 y 2025 la suma de Norte, Centro y Sur coincide con SEIN a 0,01 MW de tolerancia. En 2026 hay 48 discrepancias, del 6 de marzo a las 00:30 al 7 de marzo a las 00:00, con un máximo de 47,5961 MW. | Tratarlo como un solo día operativo y publicar la sensibilidad con ese día excluido si se usa suma de áreas. Mantener el SEIN directo en la evaluación de totales. |
| SEIN, variable de fallas | Al aplicar `fallas_en_curso` al año operativo 2025, la variable es positiva en 15.938 de 17.520 medias horas (90,97 %). | La ablación mide esta codificación. Evaluar otras definiciones requerirá procedencia temporal de los eventos. |
| Emisión real | El registro local contiene 4.752 filas rodantes de 24 h desde el 13 de noviembre de 2026. Cero se emitieron antes del comienzo de su día objetivo. Algunas filas sí preceden al inicio de su media hora. | Reportar el seguimiento del mismo día y formalizar por separado una prueba de día siguiente con los 48 intervalos emitidos a tiempo. |
| Identidad del modelo | El elegido de la evaluación principal es RF M0. El notebook 05 explica los artefactos del XGBoost global. El registro diario de 24 h contiene `chronos2ftcal`, `+calor` y `+rango`. | Vincular cada explicación o resultado con su artefacto y su corte. |
| Disponibilidad en las reconstrucciones | La interpolación de la demanda completa en `en_vivo.emitir` puede usar un valor posterior al origen si hay un hueco. Con la secuencia 100, hueco, 160, el hueco toma 130; con datos cortados antes de 160 toma 100. `verificar_regla_de_informacion` comprueba temperatura en una muestra, sin verificar esa imputación. | Probar la invariancia ante cambios de datos posteriores al origen y registrar la disponibilidad real antes de usar una reconstrucción como prueba estricta. El ejemplo muestra un mecanismo posible. Su frecuencia e impacto no se han medido. |
| Revisiones de modelos fundacionales | Varios adaptadores cargan identificadores de repositorios de modelos sin fijar una revisión en la llamada. | Identificar la revisión exacta y el corpus declarado antes de la auditoría de contaminación. Una revisión sin corpus trazable queda como desconocida. |

Las fuentes locales son `bronze/uci849_tetouan.csv`, `ceuta/silver/ceuta.parquet`,
`coes/silver/demanda_areas.parquet`, `exogenas/silver/eventos_coes.parquet`,
`reportes/sein/en_vivo/pronosticos.parquet`, notebook 05 y adaptadores de
`experimentos/fundacionales/`. Continúan pendientes el desfase exacto de UCI 849,
la sensibilidad completa de datos y el inventario de versiones y corpus.
