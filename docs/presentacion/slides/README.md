# Deck (Quarto + reveal.js + D3)

`index.qmd` es la exposición final del TB1: portada, 13 diapositivas, el cierre para las preguntas y 8 de respaldo,
en 16:9 (1280×720). Sigue el guion (`docs/guion-exposicion.md`): 20 minutos repartidos entre los Expositores 1 a 5,
con la demo de 3 minutos (el recorrido medido dura 2:13). Cada diapositiva dice quién habla, abajo a la izquierda, y
sus notas traen el tiempo y qué decir, con las frases del guion.

| Tiempo | Diapositiva | Expositor |
|---|---|---|
| 0:00-3:00 | Portada · El problema · ¿Por qué ahora? | 1 |
| 3:00-6:30 | Tres casos · Lo que encontramos | 2 |
| 6:30-10:30 | Preparación · Modelado | 3 |
| 10:30-14:40 | Antes de 2026 · La prueba de 2026 · Mes a mes · ¿Qué ayuda a adaptarse? | 4 |
| 14:40-18:40 | Fundacionales · La demo | 5 |
| 18:40-20:00 | Conclusiones · Gracias | 1 |

La diapositiva 9 del guion («La prueba de 2026») se partió en dos, la prueba y el mes a mes, para que cada una
tenga un solo gráfico; entre las dos duran lo mismo (1:40).

## Ver y presentar

```bash
bash render.sh          # deja _site/index.html
bash render.sh --pdf    # y además _site/deck.pdf
```

`_site/index.html` es un solo archivo (`embed-resources: true`): D3, los datos, las capturas y las fuentes van
adentro, así que se abre con doble clic y funciona sin red. Por eso D3 está vendorizado en `js/d3.v7.min.js`.

| Tecla | Qué hace |
|---|---|
| `S` | Vista del orador: las notas, con el tiempo y quién habla |
| `M` | Menú con todas las diapositivas |
| `F` | Pantalla completa |

Los gráficos se animan al entrar a la diapositiva (menos de dos segundos) y algunos avanzan con cada clic: las
notas marcan cada `[clic]`. En el PDF salen completos, sin animar. El PDF es también el respaldo del Expositor 3
si se cae la conexión de quien comparte pantalla.

## Los nombres

`equipo.yml` es lo único que se completa a mano: el nombre de cada expositor (el chip de cada diapositiva) y los
integrantes de la portada. Está pendiente confirmar si el grupo es de cinco o de seis.

## De dónde salen los números

`datos.py` lee las tablas que ya escribieron los notebooks y escribe todo lo que el deck cita; no recalcula ningún
modelo. Se corre con la carpeta de datos (`TETOUAN_DATA`, `./data` o la del checkout principal):

```bash
TETOUAN_DATA=/ruta/a/los/datos uv run python docs/presentacion/slides/datos.py
```

- **El texto** lee `_deck.yml` con el shortcode `{{< meta deck.… >}}`.
- **Los gráficos de D3** leen `datos.js`.
- **Las tablas del respaldo** son `generado/*.md`, que el deck incluye.
- **La portada** es `img/portada.svg`: la demanda media mensual del SEIN de 2016 a 2026.

Los cuatro se versionan: el deck se renderiza sin los datos. Lo poco que solo está en el informe técnico va en
`DEL_INFORME`, con su sección, y donde una cifra calculada también está escrita en el informe, `datos.py` comprueba
que coincida (si no, falla en vez de publicar dos cifras distintas).

| Gráfico | Diapositiva | Tabla |
|---|---|---|
| Un día del Centro: pronóstico de un día antes, su rango del 90 % y lo real | La demo | `reportes/sein/fundacionales/combinacion_c2048.parquet` y la capa silver del COES (el rango, como la app: cuantiles 5 y 95 % del error de 2025) |
| Error de 2026 por área y horizonte: Random Forest, XGBoost, combinado y mejor referencia | La prueba de 2026 | `reportes/sein/prueba_2026/frente_referencias.csv` y `fundacionales/tablas/comparacion.csv` |
| Error mes a mes de 2026 frente a la referencia | Mes a mes | `reportes/sein/prueba_2026/mensual.csv` (y el ICEN de `exogenas/silver/icen.parquet`) |
| Tetuán y Ceuta frente a las referencias fuertes | Antes de 2026 | `reportes/tb1/reanalisis.csv` |
| Peso frente a rendimiento de los modelos | Fundacionales | `fundacionales/tablas/comparacion.csv`; el peso en disco, de la figura 16 del informe técnico (estimado para varios fundacionales: círculo vacío) |
| Barras de la validación de 2025 y de la adaptación | Modelado · ¿Qué ayuda a adaptarse? | §5.3 del informe; `prueba_2026/ablacion.csv` y `efectos_adaptacion.csv` |

## Dónde se diseña

- `custom.scss`: los tokens (los colores de la app Curva: tinta para lo real, azul para el modelo, naranja para la
  referencia; el XGBoost y el combinado se distinguen del Random Forest por la luminosidad, así que se leen con
  daltonismo), las fuentes (Inter, Inter Tight, IBM Plex Mono) y todas las piezas.
- `js/graficos.js`: los gráficos de D3. Cada uno es un `<div data-grafico="…">` en `index.qmd`; los fragmentos
  `.paso` con `data-paso` le dicen en qué paso está.

## Pendiente

- Completar `equipo.yml` y que cada expositor revise sus diapositivas y sus notas.
- Si el informe cambia antes de exponer, volver a correr `datos.py`: las comprobaciones dicen qué cifra se movió.
