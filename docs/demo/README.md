# Kit de la demo: Curva en 3 minutos

Para quien hace la demo de la exposición final (TB1) **sin haber corrido nunca el proyecto**. La exposición es
**virtual, por Class Collaborate** (previsto: jueves 3 de diciembre, 19:00), con los cinco integrantes con cámara y
audio. Dura 20 minutos y después vienen unos 10 minutos de preguntas de la profesora. La demo va de **15:40 a 18:40**
del guion ([`docs/guion-exposicion.md`](../guion-exposicion.md)) y se hace **compartiendo pantalla**.

| Quién | Qué hace en la demo |
|---|---|
| **Expositor 5** | Levanta la app en su laptop, comparte pantalla y dice las frases. |
| **Expositor 3 (respaldo)** | Tiene descargados el PDF de capturas y el video. Si se cae la conexión del Expositor 5, comparte él y dice las mismas frases. |
| **Expositor 2** | Lleva el tiempo y avisa por el chat del grupo. |

Lo medido: el recorrido completo dura **2:13** con un expositor simulado que lee a 140 palabras por minuto (cifras
en [`cronometro.json`](cronometro.json)). Quedan 47 segundos de margen para los nervios y el retraso de Collaborate.

## Qué hay en esta carpeta

| Archivo | Para qué |
|---|---|
| [`demo.sh`](demo.sh) | El comando del día: revisa lo necesario, levanta la app, comprueba las cifras y abre el navegador |
| [`verificar.py`](verificar.py) | Lo usa `demo.sh`: compara lo que muestra la app con lo que dice este guion |
| [`plan-b-capturas.pdf`](plan-b-capturas.pdf) | Plan B: una página por paso, en orden (8 páginas, 1920×1080) |
| [`recorrido-demo.mp4`](recorrido-demo.mp4) | Plan B: el recorrido completo en video, 2:15, sin audio, 1920×1080, 4.9 MB |
| [`corrida-diaria.mp4`](corrida-diaria.mp4) | Para las preguntas: la corrida diaria en 30 segundos, 1.4 MB |
| [`capturas/`](capturas/) | Las capturas sueltas, para las diapositivas y el paper (lista al final) |

## La víspera (una sola vez, con internet)

1. **El repo y uv.** Si no los tienes: instala [uv](https://docs.astral.sh/uv/)
   (`curl -LsSf https://astral.sh/uv/install.sh | sh`) y clona el repo:
   `git clone https://github.com/R0SEWT/tetouan-power-forecast && cd tetouan-power-forecast`. En Windows, usa Git
   Bash o WSL (no lo probamos en Windows).
2. **Los datos.** La app necesita la carpeta `data` del proyecto (unos 240 MB de lo que usa la app), que no está en el
   repo. Pídesela al dueño (está en su Drive, `datalake/tetouan-power-forecast`) y déjala junto al repo, en
   `../tetouan-power-forecast/data`; o di dónde está con `TETOUAN_DATA=/ruta/a/data`. Con rclone y acceso a ese
   Drive, `docs/demo/demo.sh --descargar` la baja sola.
3. **El ensayo.** `docs/demo/demo.sh --verificar`. La primera vez instala las dependencias (unos minutos). Tiene que
   terminar en «Ensayo: todo listo.» (o «listo, con avisos»: léelos; el más común es que todavía no hay pronóstico
   de hoy). Si dice FALTA o FALLA, el mensaje dice qué hacer.
4. **Collaborate.** Entren a la sala de prueba y comprueben que **el Expositor 5 y el Expositor 3 pueden compartir
   pantalla** (hace falta el rol de presentador; si no lo tienen, pedirlo a la profesora al entrar). Compartan la
   ventana de Chrome y pidan a otro que diga si lee la leyenda del gráfico.
5. **El respaldo.** El Expositor 3 descarga `plan-b-capturas.pdf` y `recorrido-demo.mp4` y ensaya las frases.
6. **En vivo.** El registro en vivo solo se actualiza en la máquina donde corre la corrida diaria (la del dueño) y en
   su copia del Drive. Si la demo se hace desde otra laptop, el día de la exposición hay que traer la copia del día
   (`demo.sh --descargar`); si no, el paso 1 se verá con días de atraso (ver «Si no hay dato nuevo»).

## Lista de verificación: 30 minutos antes (18:30)

- [ ] Laptop enchufada, «No molestar» activado, notificaciones y otras apps cerradas.
- [ ] Internet estable (cable si se puede); el celular listo para compartir datos si se cae el wifi.
- [ ] En una terminal, desde la carpeta del repo: `docs/demo/demo.sh`. Todo en OK. Anota la cifra que imprime
      «Para leer en «Confianza» (paso 4)»: es la cobertura en vivo del día.
- [ ] Se abrieron dos pestañas: paso 1 (`#/ahora/centro`) y paso 2 (`#/ahora/centro?fecha=2026-08-27&hora=19:00`).
      Si no, ábrelas con las URL que imprimió `demo.sh` (si la API quedó en otro puerto, la URL lleva `?api=`).
- [ ] **Zoom de Chrome al 150 %** en las dos pestañas (Ctrl y + tres veces desde 100 %; Ctrl y 0 vuelve a 100 %). En una
      pantalla más chica, el que haga que la cabecera de Curva y Norte/Centro/Sur entren en una fila y el gráfico se
      vea completo sin bajar (110 o 125 %). Así el texto se lee aunque Collaborate achique la pantalla compartida.
- [ ] Modo claro (el botón de la luna, arriba a la derecha, muestra la luna).
- [ ] Otras pestañas cerradas y barra de marcadores oculta (Ctrl+Shift+B).
- [ ] La cabecera del paso 1 dice «Hoy · datos del COES al [ayer], 24:00». Si dice un día anterior: «Si no hay dato
      nuevo», abajo.
- [ ] La presentación abierta en otra ventana, lista en la diapositiva 11.
- [ ] Expositor 3: PDF y video abiertos (el video en una pestaña de Chrome, pausado en 0:00).
- [ ] Expositor 2: cronómetro listo; avisa si a las 17:50 no empezó el paso 4.

## El recorrido

Se comparte **la ventana de Chrome** (no una pestaña sola), para que se vea el cambio de pestaña del paso 2. Los
tiempos son los medidos; en la exposición, el paso 1 empieza a las 15:40.

| Paso | Tiempo (exposición) | Dónde | Qué hacer |
|---|---|---|---|
| 1. Hoy, en vivo | 0:00–0:25 (15:40–16:05) | Pestaña 1: `http://localhost:8080/#/ahora/centro` | Al final, bajar con la rueda hasta «Lo que dijimos para ayer a esta hora» |
| 2. Un día de El Niño | 0:25–1:01 (16:05–16:41) | Pestaña 2: `http://localhost:8080/#/ahora/centro?fecha=2026-08-27&hora=19:00` | Tocar en el gráfico el punto del pico («Pico 5,007 · 15:00», a la derecha). Después, un clic en el título «¿Acertamos…?» |
| 3. ¿Y si hace más calor? | 1:01–1:29 (16:41–17:09) | Desde el paso 2 | Clic en el enlace azul «¿Y si hace más calor?»; luego en «+2 °C»; bajar un poco hasta la frase «Si hiciera 2 °C más…» |
| 4. Confianza | 1:29–2:08 (17:09–17:48) | Clic en «Confianza», en la cabecera | Leer el titular y la tarjeta roja «En vivo, desde el 13 nov» |
| 5. Cierre | 2:08–2:13 (17:48–17:53) | — | Volver a la presentación |

**Qué decir, paso por paso** (no hay que memorizarlo: la idea y la cifra bastan):

1. **Hoy, en vivo.** «Esta es Curva: corre nuestros modelos sobre la demanda que publica el COES. Lo real llega hasta
   ayer, porque el COES publica cada día a la mañana siguiente; desde la línea punteada todo es pronóstico, emitido hoy
   antes de conocer el real. [bajar] Aquí, lo que dijimos para ayer a esta hora y lo que pasó.»
2. **Un día de El Niño.** «Ahora, un día de la prueba: el 27 de agosto de 2026, el mes en que el ICEN llegó a 3.98. El
   modelo no vio 2026 al entrenarse. Un día antes pronosticó 4,810 megavatios para las 19:00; fue 4,772, dentro del
   rango. [tocar el pico] Toco el pico: para las 15:00 del día siguiente dijo 5,007 y fue 5,027.»
3. **¿Y si hace más calor?** «¿Y si mañana hace dos grados más? Lo calcula el XGBoost, el único modelo que usa el
   clima. [+2 °C] El pico sube 8 megavatios, 0.2 %: casi nada. Y en 2026 el clima empeoró el pronóstico a 24 horas: no
   conviene apoyarse en él en un evento extraordinario.»
4. **Confianza.** «Aquí la app dice cuánto acertó: en 2026 le ganó a la referencia los diez meses, con 71.9
   megavatios de error a 24 horas, 47 % menos, y su rango del 90 % cubrió el 91 %. Y lo honesto: en vivo, desde el 13
   de noviembre, el rango del 80 % cubre el [cifra roja de la pantalla] %: queda corto y lo mostramos en rojo. Es
   seguimiento en curso, no un resultado.» (El 20 de noviembre la cifra roja era 70.2 %; cambia cada mañana.)
5. **Cierre.** «El diseño lo medimos con instrumentos sintéticos; falta probarlo con personas.» **Pase:** «[Expositor
   1] cierra.»

**Paso extra, 30 segundos** (la corrida diaria): solo si al terminar el paso 4 el reloj marca 17:50 o menos; si no,
se guarda para las preguntas. Clic en «Detalle» (cabecera) y en el botón «En vivo». «Esto corre solo cada mañana.
Cuando el COES publica el anexo del día anterior, hacia las 9:45, la corrida lo baja, lo valida, pronostica el día y lo
registra con su hora de emisión, antes de que exista el real. Si el anexo no pasa las validaciones, no emite nada.
Corren tres modelos en paralelo y todo se copia al Drive.»

**Cuidado con tres cosas:**

- **El clic después de tocar el gráfico.** Tras tocar el gráfico, la app pierde el siguiente clic en un enlace (un
  fallo conocido). Por eso el paso 2 termina con un clic en el título. Si «¿Y si hace más calor?» no responde, haz clic
  otra vez.
- **Toca justo el pico.** Si el toque cae media hora antes o después, las cifras cambian un poco: di las de la
  pantalla. Lo mismo con «+2 °C»: la frase de la app dice cuánto sube.
- **El día elegido es bueno a propósito.** Si preguntan: «Lo elegimos para mostrar; cómo le fue en todo 2026 está en
  «Confianza»: le ganó a la referencia los diez meses.»

### Por qué estos días

- **27 de agosto de 2026, 19:00 (el principal).** Agosto es el mes del ICEN de 3.98, el más alto desde 1997-98 (la
  cifra de la diapositiva 3). Es un jueves normal y la demanda del Centro iba 6 % sobre el mismo día de 2025. Ese día
  el combinado se equivocó 40.7 MW frente a 77.0 de «la semana pasada» (47 % menos) y el rango cubrió las 48 medias
  horas. El chip «El Niño costero: extraordinario» muestra el último ICEN publicado, no el de ese día: no lo uses para
  decir en qué fase estaba el 27 de agosto (en agosto sí era extraordinario).
- **10 de marzo de 2026, 19:00 (el respaldo):** `http://localhost:8080/#/ahora/centro?fecha=2026-03-10&hora=19:00`.
  Es el caso de las mediciones de diseño (paper, §5.6) y el mejor día del Centro en 2026; en marzo empezó El Niño
  según el ENFEN. Cifras: dijimos 4,767 (4,588–4,929), fue 4,784; el pico del 11 a las 14:30, dijimos 4,977 y fue
  4,961; desde ahí, +2 °C sube el pico 20 MW (0.4 %). Úsalo si el principal muestra algo raro.

### Si no hay dato nuevo el día de la exposición

El COES publica la demanda de cada día a la mañana siguiente (hacia las 09:45) y la corrida reintenta cada 30 minutos
hasta las 17:30. Si ese día no publicó, o la laptop no tiene la copia del día, la cabecera dice un día anterior y la
pantalla dice «el pronóstico sale hacia las 10:00 … Mientras, abajo, lo que se pronosticó» (ver
[`capturas/paso1-sin-dato-nuevo.png`](capturas/paso1-sin-dato-nuevo.png)). No se arregla en vivo: el paso 1 se hace
igual y se dice: «Hoy el COES todavía no publicó la demanda de ayer: la app lo dice y muestra lo último que se
pronosticó. Por eso decimos "en vivo con un día de retraso", no "tiempo real".» El resto del recorrido no depende de la
fecha.

**No decir:** «tiempo real», «el combinado corre en vivo» (en vivo corre Chronos-2 ajustado), «validado con usuarios»
ni «El Niño empezó en noviembre» (lista completa en el guion, «Lo que no hay que decir en la demo»).

## Plan B

**La regla:** si en 20 segundos la app no carga, sale un error, o aparece el chip «Datos de prueba: series
sintéticas», no se arregla en vivo.

| Qué falla | Qué se hace |
|---|---|
| La app no arranca o falla, pero el Expositor 5 sigue conectado | Dice: «Para no perder tiempo, les muestro las capturas del mismo recorrido». Comparte `plan-b-capturas.pdf` (página por paso) y dice las mismas frases. |
| Se cae la conexión o la laptop del Expositor 5 | El Expositor 3 dice «Sigo yo», comparte el PDF (o el video) y dice las frases desde el paso en que se cortó. |
| Falla internet, pero no la app | La app corre en la laptop y no necesita internet; lo que se cae es Collaborate: pasa al Expositor 3. |
| La pantalla compartida se ve chica o borrosa | Subir el zoom de Chrome (Ctrl y +). Compartir la ventana de Chrome, no toda la pantalla. Si alguien cambió la resolución o conectó otro monitor, Ctrl y 0 y volver a subir hasta que la cabecera entre en una fila. |
| `demo.sh` dice FALLA en las cifras | Si dice «prueba» o falta el combinado: plan B con el PDF. Si solo cambió «¿Y si…?», se dice la cifra de la pantalla. |
| Los puertos 8000 u 8080 están ocupados | `demo.sh` usa otros sin cerrar nada y lo avisa; usa las URL que imprime (llevan `?api=`). |

- **El PDF** ([`plan-b-capturas.pdf`](plan-b-capturas.pdf)) es lo más seguro: lo avanza quien habla. Páginas: 1 hoy,
  2 «lo que dijimos», 3 el 27 de agosto, 4 el pico, 5 «+2 °C», 6 «Confianza», 7 el seguimiento en vivo, 8 la corrida
  diaria (extra). En Collaborate se puede compartir la ventana del lector de PDF o, si la sala lo permite, subirlo con
  «Compartir archivos».
- **El video** ([`recorrido-demo.mp4`](recorrido-demo.mp4), 2:15, sin audio) se abre en una pestaña de Chrome
  (arrastrar el archivo a la ventana) y se comparte esa ventana; quien habla dice las frases encima. Cada paso lleva
  abajo a la izquierda un rótulo («2/5 · Un día de El Niño»). Comienzos: paso 1, 0:00; paso 2, 0:26; paso 3, 1:01;
  paso 4, 1:29; paso 5, 2:08. En el video, «hoy» es el 20 de noviembre de 2026: dilo así.
- Al final del plan B: «Si desean, en las preguntas la mostramos en vivo».

## Preguntas probables de la profesora (1 minuto de lectura)

En el avance preguntó por el mantenimiento. Respuestas cortas; si da el tiempo, mostrar el paso extra (Detalle → En
vivo) o [`corrida-diaria.mp4`](corrida-diaria.mp4).

- **¿Qué pasa cuando llegan datos nuevos?** Llegan solos cada día: la corrida diaria baja el anexo del COES, lo valida,
  pronostica el día y lo registra con su hora de emisión antes de que exista el real; al día siguiente lo compara con
  el real. No hay que tocar código.
- **¿Y si el COES cambia el archivo o las columnas?** El lector busca la hoja `DEMANDA_AREAS` y las columnas por su
  nombre (SEIN, NORTE, CENTRO, SUR), no por su posición. Si falta una, si el día no trae las 48 medias horas, si las
  áreas no suman el SEIN (±1 MW) o si el empalme salta más de lo visto en dos años, la corrida **no emite nada** y
  termina con un código de error que queda en el registro, para revisarlo a mano. Preferimos no pronosticar a
  pronosticar con datos malos. Si el COES corrige un anexo, se baja la versión nueva aparte y lo ya emitido no cambia.
- **¿Cada cuánto se reentrena?** Hoy, a mano: el XGBoost de la app se reentrena con un comando (unos 4 minutos en una
  laptop) y Chronos-2 se ajustó una vez, con datos hasta 2024 y GPU. Medimos qué pasa si se reentrena cada semana: a 1
  hora baja el error alrededor de 1 %, y por eso lo recomendamos (paper, §5.4), pero no está automatizado.
- **¿Qué tan automatizado está?** La corrida en vivo, del todo: un cron cada 30 minutos de 9:00 a 17:30, hora de Lima.
  La primera que encuentra el anexo trabaja (poco más de un minuto) y las demás no hacen nada. Corren tres modelos en
  paralelo (el base, uno con un rango recalibrado y uno corregido por el calor) y todo se copia al Drive. Cada fila
  guarda el sha256 de los pesos y del anexo. Lo que falta: el reentrenamiento automático, una alerta (hoy solo queda el
  código de salida en el registro) y el combinado en vivo (faltan los pesos de Simons en esa máquina).
- **¿Y si el COES no publica un día?** La corrida reintenta; si falta un día, la serie se detiene ahí y no se inventa
  (no interpola). La app lo dice en la pantalla.
- **¿Cómo saben que el código no se rompe?** La regla de información y la app tienen pruebas automáticas (pytest) que
  corren en GitHub en cada cambio, junto con ruff.

Fuentes: [`experimentos/en_vivo/README.md`](../../experimentos/en_vivo/README.md) y la guía de defensa, preguntas 13,
24 y 29.

## Las capturas

Todas en modo claro, a 1920×1080: la página de Chrome con zoom del 150 % (1280×720 de página). Se comprobó que se leen
reducidas a 1280×720, como las muestra Collaborate; al 100 % de zoom, la letra chica queda en unos 7 px y no se lee.

| Archivo | Qué es |
|---|---|
| `paso1-hoy.png`, `paso1b-lo-que-dijimos.png` | Paso 1 (del 20 de noviembre: «hoy» cambia cada día) |
| `paso1-sin-dato-nuevo.png` | El paso 1 un día en que el COES no publicó (reloj simulado) |
| `paso2-repaso-27-08-2026.png`, `paso2b-pico-28-08-2026.png` | Paso 2 |
| `paso3-y-si-2c.png` | Paso 3 |
| `paso4-confianza.png`, `paso4b-confianza-en-vivo.png`, `paso4c-confianza-1h.png` | Paso 4 (a 24 h, el seguimiento en vivo y a 1 h: 48.8 MW) |
| `extra-corrida-diaria.png` | El paso extra |
| `respaldo-repaso-10-03-2026.png`, `respaldo-pico-11-03-2026.png`, `respaldo-y-si-11-03-2026.png` | El día de respaldo: el repaso, su pico y «+2 °C» desde el pico |
| `R1-ahora.png`, `R2-escenarios-2c.png`, `R2b-diagnostico.png`, `R3-confianza-en-vivo.png` | Las diapositivas de respaldo R1-R3 del guion y la figura 13 pendiente del informe técnico (§6.1: «Detalle», escenarios y diagnóstico) |
| `movil-hoy.png`, `movil-repaso.png`, `movil-confianza.png` | En el celular (375×812, a 750×1624), para la diapositiva del diseño |

**Regenerarlas** (con la app levantada, Node y, para el video, ffmpeg; por ejemplo, la víspera, para que «hoy» sea
reciente):

```bash
cd app/medicion && npm ci
node demo.mjs --capturas     # capturas y PDF del plan B
node demo.mjs --video        # los dos videos y cronometro.json (unos 4 minutos)
node demo.mjs --cronometro   # solo el cronómetro
# Con la app en otros puertos: TPF_WEB=http://localhost:8081 TPF_API=http://localhost:8001 node demo.mjs --capturas
```

Si cambian las cifras (otros modelos), hay que cambiar las frases de `app/medicion/demo.mjs`, las de este README y las
esperadas de `verificar.py`.

## Notas para el dueño (no hace falta leerlas para la demo)

Encontradas al verificar el kit el 20 de noviembre, con los modelos de Colab; no se tocaron la app ni el paper:

- **Fallo de la app:** tras tocar o arrastrar el gráfico de «Ahora», el primer clic en un enlace se pierde: el `blur`
  del lienzo vuelve a pintar la cabecera y reemplaza el enlace entre el `mousedown` y el `click`.
- **«¿Y si…?» cambió con los modelos de Colab:** +2 °C sube el pico 4 MW el 10/03 a las 19:00 (antes, 15 MW). La cifra
  T3 de `docs/app-hcd.md` (15 MW, 4,934) y su recorrido de demo quedaron viejos.
- **«Confianza» a 1 h** muestra en las tarjetas del pico, de El Niño y del seguimiento en vivo las cifras de 24 h, sin
  decirlo.
- **«Confianza» dice «2026 sí se usó para elegir el modelo»**; el paper y el guion dicen que se eligió con 2025 y que
  2026 queda fuera de la selección. Las dos cosas pueden ser ciertas (el combinado abre por defecto por ser el de menor
  error en 2026), pero conviene alinear la frase.
- **Sin dato nuevo, a las 19:00** la pantalla dice «el pronóstico sale hacia las 10:00»; a esa hora sería más claro
  decir que el COES se atrasó.
- **El rango del combinado:** la app muestra un rango del 90 % calibrado con los errores de 2025 (91.1 % en 2026); la
  guía de defensa (pregunta 24) dice que es el 10-90 de Chronos-2 (80 %) y el short paper (§5.3) da 77-81 % para el
  intervalo 10-90 de la combinación. Son intervalos distintos.
- **README, «Resultados clave»:** «En vivo, desde el 23 de octubre … 73.2 %» es el tramo reconstruido; en vivo, desde
  el 13 de noviembre, era 70.2 % en el Centro al 19 de noviembre.
- **Referencias de 2026:** la app da 128.6 y 135.4 MW en el Centro (13,824 medias horas, hasta el 15 de octubre); el
  paper, 128.5 y 135.3 (filas del Random Forest, hasta el 17 y el 16). No es un error, pero se nota si alguien compara.
- **El XGBoost de la app con clima a 24 h** (M3) empeora 3.5 MW en el Norte y 5.4 en el Centro frente a M0 en 2026,
  más que la ablación del Random Forest del paper (+0.42 y +1.35). No sale en la demo; no se buscó la causa.
