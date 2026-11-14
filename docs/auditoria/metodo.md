# Auditoría de atención: el método (de myPage a Curva)

La primera pasada de diseño centrado en las personas ([`docs/app-hcd.md`](../app-hcd.md)) tomó de
[R0SEWT/myPage](https://github.com/R0SEWT/myPage) el ciclo de medición (base → cambio mínimo → re-medición → tabla
antes/después), pero dejó fuera la medición de **atención**. Esta carpeta la porta, la valida y la extiende a lo que
el dueño señala como el dolor principal: *«cuando abro la app como que me pierdo»*.

| Documento | Qué tiene |
|---|---|
| [`metodo.md`](metodo.md) | Este: cómo lo hace myPage, qué se portó, qué se agregó y cuánto vale la medición |
| [`linea-base.md`](linea-base.md) | La app de `develop` medida con el arnés: atención por AOI, primera apertura y métricas baratas |
| [`onboarding.md`](onboarding.md) | La primera apertura: diseño de niveles de videojuegos traducido a Curva, tres conceptos y cómo medirlos |
| [`plan.md`](plan.md) | Las líneas de trabajo y los PR, en orden, cada uno con su medición clave y su umbral |
| [`bocetos/primera-apertura.html`](bocetos/primera-apertura.html) | Bocetos estáticos de los tres conceptos de primera apertura |

## 1. Cómo lo hace myPage

Fuentes: la metodología en el [issue #67](https://github.com/R0SEWT/myPage/issues/67), los PR
[#64](https://github.com/R0SEWT/myPage/pull/64)–[#80](https://github.com/R0SEWT/myPage/pull/80), el cierre en
[#81](https://github.com/R0SEWT/myPage/pull/81), el arnés `site/audit/` y `.beads/issues.jsonl`.

**El ciclo de cada PR (issue #67).** (1) Literatura HCD de los últimos cinco años sobre el problema concreto, citada en
el PR. (2) Medición de base sobre `main` antes de tocar nada. (3) Cambio mínimo que ataca la métrica que falla.
(4) Re-medición: si no mueve la métrica o la empeora, se revierte y se documenta; antes de creer una diferencia se
estima el ruido del instrumento. (5) PR con capturas antes/después **y máscaras de atención antes/después**, métricas y
literatura en `docs/audit/<pr>/`. (6) Registro en beads: un issue por hallazgo, cerrado con el resultado medido, y los
pendientes como `discovered-from`.

**El modelo de atención.** UEyes (Jiang et al., CHI 2023) publica miradas sobre 1,980 interfaces
(web, móvil, escritorio y afiches) como mapas de calor a 1, 3 y 7 s, con un split oficial de entrenamiento y prueba,
pero no los pesos de su modelo (UMSI++). myPage entrena el suyo:

| Paso | Script de myPage | Qué hace |
|---|---|---|
| Datos | `fetch_ueyes.py` | Lee por rangos HTTP solo imágenes y mapas de 1 y 3 s del zip de Zenodo (12.9 GB → ~1 GB) |
| Rasgos | `ueyes_feats.py` | DINOv2 ViT-S/14 congelado (`facebook/dinov2-small`): la imagen a ~448² px de área con su proporción, en múltiplos de 14; salidas de los bloques 8 y 12 sin el token CLS (768 canales por parche), guardadas en fp16 |
| Lector | `ueyes_train.py` | Cabeza conv 1×1 (768→96) · GELU · conv 3×3 (96→32) · GELU · conv 3×3 (32→1), más un prior de posición aprendido de 24×24; log-softmax sobre la rejilla; pérdida KLD − 2·CC; AdamW, 8 épocas (el sesgo solo, 6) |
| AOI | `aoi.mjs` | Playwright: captura de la ventana y cajas de las AOI por selector (afirmación, evidencia, CTA, chrome y un `FOCUS=` opcional). Texto con su **caja ajustada** (un `Range` sobre el contenido), imágenes y video con la del elemento |
| Lectura | `ueyes_audit.py` | Mapa a la resolución de la captura (bilineal), atribución **exclusiva por prioridad** (focus → afirmación → CTA → evidencia → chrome → fondo iluminado → resto) y, por AOI, **cuota** (masa de atención) y **lift** (cuota ÷ fracción del área: más de 1 = se mira más que lo que ocupa) |
| PR | `attention.sh` | Base y rama en dos puertos, las dos lecturas y láminas «ANTES · DESPUÉS» |

En el test oficial: **CC 0.690 / KLD 0.64**, contra 0.435 / 1.21 de un modelo de solo sesgo central. Ruido entre
corridas del mismo build: ±0.02 de cuota.

**Las otras métricas** (todas con un número, no una opinión): desborde por viewport (`scrollHeight − clientHeight` del
panel en `ovf.mjs` y `tablet.mjs`), contraste WCAG 2 y APCA contra el fondo renderizado (`contrast.mjs`), caracteres
por línea (`measure.mjs`), similitud con el sistema visual (`tokens.mjs`: Jaccard de familias y colores entre
pantallas; «colores fuera del sistema 4/4 → 0/5»; y UIClip, UIST 2024, como juez y como similitud con el deck), peso y
peticiones (`weight.mjs`), pulsaciones hasta el contenido (`tabs-to-content.mjs`, 9 → 2), gestos por pantalla
(`flick.mjs`), tamaño de objetivos 2.5.8 (`targets.mjs`), affordances falsas (`hover.mjs`) y fugas de idioma.

**Cómo es cada PR.** Un foco y una medición clave. El cuerpo tiene: la auditoría con una tabla antes/después de esa
medición (y de las que no deben empeorar), **lo probado y rechazado con cifras** (en #66, poner el cargo encima de la
fecha bajó su lift de 1.63 a 1.49 y se rechazó; en #81, dos columnas en tablet bajaron la atención a los cargos de
0.075 a 0.058 por solo 10 px menos de desborde y se revirtió; en #76, la variante «publicación primero» se midió pero
se dejó al autor porque es editorial), los cambios, capturas y máscaras antes/después, literatura y checks. Lo que es
decisión del autor no se toca: se registra.

**Beads.** Al cierre (#81), nueve epics, uno por línea de trabajo, con el mismo formato: **Estado**, **Instrumento**,
**Resultados** medidos, **Probado y descartado** (con cifras) y **Próximos pasos**; los hallazgos como issues hijos;
todo exportado a `.beads/issues.jsonl` con memorias.

**Límites que el propio myPage declara.** La saliencia de visión libre predice los primeros vistazos, no la búsqueda
dirigida por una tarea; los usuarios sintéticos detectan regresiones y deciden qué observar, pero no reemplazan
personas (Agnew et al., CHI 2024).

## 2. Qué se portó a Curva y qué se agregó

El arnés vive en [`app/medicion/atencion/`](../../app/medicion/atencion/):

| Archivo | Qué hace |
|---|---|
| `entrenar_colab.py` | Reproduce el entrenamiento de myPage **en Colab** (datos, rasgos con `transformers`, cabezas de 1, 3 y 7 s) y valida el port numpy contra torch |
| `saliencia.py` | El lector en **numpy** (sin torch): DINOv2-S y la cabeza, con el remuestreo idéntico al de `torch.nn.functional.interpolate` |
| `modelo/` | Las tres cabezas (`cabeza_ueyes_{1s,3s,7s}.npz`, 400 KB cada una) y `metricas.json` (test y validación) |
| `pantallas.mjs` | Pantallas, viewports, temas y AOI por selector, en orden de prioridad |
| `capturar.mjs` | Playwright: captura de la ventana, AOI, barras fijas que tapan, controles, textos, colores, tipografía y desbordes |
| `analizar.py` | Atención por AOI, métricas baratas, primera apertura (prueba de 5 s y de primer clic sintéticas), consistencia, mapas y láminas |
| `comparar.py` | Antes/después de un PR: tabla por AOI y máscaras lado a lado |
| `medir.sh` | Todo en un comando |

**Elección del modelo.** Se mantuvo el lector de myPage porque es el único de los disponibles entrenado con miradas
sobre interfaces (no sobre fotos) y con un número de validez publicado en un test oficial; un modelo de saliencia de
imágenes naturales o heurísticas de jerarquía no tendrían ese número. Lo que era pesado (descargar 1 GB, entrenar con
torch) se fue a Colab; en la laptop solo corre la inferencia, con numpy y los pesos de DINOv2-S que ya estaban en la
caché de Hugging Face.

| | myPage | Aquí |
|---|---|---|
| Test oficial UEyes, 3 s (CC / KLD) | 0.690 / 0.64 | **0.690 / 0.636** (sesgo central 0.435 / 1.208) |
| 7 s y 1 s | — | 0.718 / 0.428 y 0.563 / 1.115 (sesgo central 0.432 y 0.416) |
| Por tipo de interfaz, 3 s (CC) | web 0.648, móvil 0.753 | web 0.648, escritorio 0.655, móvil 0.753, afiche 0.704 |
| Port numpy contra torch (12 imágenes de prueba, a las rejillas de 1366×768, 1024×768 y 375×812) | — | pesos idénticos (diferencia 0), embedding de posición 1.7·10⁻⁷, **CC de los mapas ≥ 0.9997** |
| Descarga en la laptop | ~1 GB + torch | **400 KB × 3** (DINOv2-S, 85 MB, ya estaba en la caché; si falta se baja una vez) |
| Tiempo por captura | — | ~1.3 s en CPU |

Dos cambios respecto de myPage: Zenodo devuelve `429 Too Many Requests` con una petición por archivo, así que
`entrenar_colab.py` pide tramos contiguos de ~48 MB del zip (24 peticiones en lugar de ~8,000); y se entrenaron
también las cabezas de 1 y 7 s (la de 7 s sirve para la prueba de 5 segundos). UEyes se publica con licencia
CC BY 4.0 (Zenodo, [10.5281/zenodo.8010312](https://doi.org/10.5281/zenodo.8010312)); las cabezas derivadas se
versionan con esa atribución, y DINOv2 es Apache-2.0.

**AOI de Curva.** Por pantalla, en orden de prioridad (`pantallas.mjs`): en «Ahora», la cifra de ahora, el pico de
24 h, la línea y la pastilla de «ahora» en el gráfico, la cabecera con la fecha de los datos, «lo que dijimos ayer», el
título, la marca («qué es»), el párrafo de modo, las otras cifras, el gráfico, las tarjetas de área, los controles de
fecha y el chip de El Niño; en «Confianza», el titular-veredicto, la cobertura del rango, el aviso en vivo, el error mes
a mes, las cifras, el párrafo de entrada, la cabecera, la marca y los selectores; en «Detalle», la cifra, el rango,
real y error, la curva, el pico, el título, las secciones, el panel de controles, la cabecera y la marca. Después van
tres categorías genéricas: **barras fijas** (lo que tapan cuenta para ellas, no para la AOI de debajo), **controles** y
**texto**; lo demás es **resto**. Las cajas de texto son ajustadas, como en myPage desde #66.

**Pantallas y viewports.** `inicio` (la URL raíz, sin parámetros: en vivo y a la hora del reloj), `ahora` (el caso fijo
de las tareas, en repaso: Centro, 10-mar-2026, 19:00, reproducible), `confianza` y `detalle`; en escritorio
(1366×768), proyector (1920×1080), tablet (1024×768, táctil) y móvil (375×812, táctil); en claro y oscuro: 32 capturas.

**Lo agregado para la primera apertura** (pedido del dueño): controles y cifras a la vista sin desplazarse, palabras a
la vista, términos sin definir en la pantalla (lista en `analizar.py`), una **prueba de 5 segundos sintética** (seis
preguntas; se responde si la respuesta está a la vista con su texto **y** se lleva al menos el 5 % de la atención
predicha a 7 s; el umbral se fijó antes de medir) y una **prueba de primer clic sintética** por tarea (el control con
más «olor de información», palabras de la tarea en su etiqueta, como en CogTool-Explorer de Teo, John y Blackmon,
CHI 2012; a igualdad, el más mirado). Y las métricas baratas que myPage usa y el arnés no tenía: desborde horizontal por
viewport, pantallas de alto, caracteres por línea, colores fuera del sistema (contra los tokens de `:root` ya
resueltos), escala tipográfica y consistencia entre pantallas (Jaccard de tamaños de letra y de colores).

## 3. Cuánto vale la medición

- **Es atención sintética.** El lector predice dónde caen los primeros vistazos de alguien que mira libremente (CC 0.69
  con las miradas reales de UEyes: bueno, no perfecto). No sabe leer: no distingue una cifra importante de una
  irrelevante si se ven igual, ni predice la búsqueda de alguien con una tarea. Sirve para ver si lo importante está
  donde el ojo ya cae, no para afirmar que alguien lo entendió.
- **Las pruebas de 5 segundos y de primer clic son sintéticas**: reglas explícitas sobre lo que está a la vista, su
  texto y la atención predicha. Sirven para comparar versiones con la misma regla; no reemplazan la prueba con personas
  (Gronier, 2016, sobre la validez de la prueba de 5 s con personas).
- **«Inicio» depende del reloj**: en vivo, la pantalla cambia con la hora (a las 22:30 el pico del día ya pasó; a las
  09:00, no). La comparación entre versiones se hace con capturas del mismo momento, o en repaso (`ahora`).
- **Ruido**: dos corridas completas del mismo build (`base` y `base-r2`) se comparan en `linea-base.md`.
- Nada de esto se probó con personas. La primera línea de trabajo del plan incluye cinco sesiones cortas.

## 4. Cómo repetirlo

```bash
# La app (otros puertos si la del dueño está abierta en :8000/:8080)
PUERTO_API=8100 PUERTO_WEB=8180 UV_PROJECT_ENVIRONMENT=<venv> app/levantar.sh
# En otra terminal: captura + lector + métricas, y una lámina por pantalla y tema
export UV_PROJECT_ENVIRONMENT=<venv> TPF_WEB=http://localhost:8180 TPF_API=http://localhost:8100
LAMINAS=docs/auditoria/img app/medicion/atencion/medir.sh base
# Ruido: otra corrida del mismo build
COMPARAR=base app/medicion/atencion/medir.sh base-r2
# Un PR: la rama medida con otra etiqueta, y la comparación de su AOI clave
uv run --no-sync python app/medicion/atencion/comparar.py base pr1 --pantallas inicio --vistas escritorio,movil --salida docs/auditoria/pr1
# Reentrenar el lector (en Colab, nunca en la laptop): subir entrenar_colab.py y saliencia.py y lanzar desacoplado
colab new -s ueyes --gpu L4 && colab upload -s ueyes app/medicion/atencion/entrenar_colab.py /content/entrenar_colab.py
```

Resultados: `app/medicion/resultados/atencion/<etiqueta>.json` y `.md` (versionados); capturas y mapas en
`app/medicion/resultados/tmp/atencion/` (fuera de git).

## Referencias

- Jiang, Y. et al. (2023). *UEyes: Understanding Visual Saliency across User Interface Types*. CHI 2023. Datos: Zenodo 10.5281/zenodo.8010312 (CC BY 4.0).
- Oquab, M. et al. (2023). *DINOv2: Learning Robust Visual Features without Supervision*. arXiv:2304.07193.
- Teo, L., John, B. E. y Blackmon, M. H. (2012). *CogTool-Explorer: a model of goal-directed user exploration that considers information layout*. CHI 2012, 2479–2488.
- Pirolli, P. y Card, S. (1999). Information foraging. *Psychological Review*, 106(4), 643–675.
- Gronier, G. (2016). Measuring the first impression: testing the validity of the 5 second test. *Journal of Usability Studies*, 12(1), 8–25.
- Agnew, W. et al. (2024). *The Illusion of Artificial Inclusion*. CHI 2024.
- Wu, J. et al. (2024). *UIClip: A Data-driven Model for Assessing User Interface Design*. UIST 2024.
