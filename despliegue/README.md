# Despliegue de Curva

**Publicada en dos lugares de la suscripción «Azure for Students»:**

- **<https://curva.rosewt.dev>**: la web desde Netlify y la API en Azure Container Apps, que se apaga sola (ver
  [Netlify](#netlify-curvarosewtdev-la-web-en-el-cdn-la-api-en-container-apps)). La web aparece al instante; si el
  servidor dormía, avisa «Despertando el servidor» y los datos llegan en ~25 s.
- **Azure Container Apps, se apaga sola: <https://curva.jollyocean-4175cf43.brazilsouth.azurecontainerapps.io>** (ver
  [Azure Container Apps](#azure-container-apps-se-apaga-sola)). Cero réplicas cuando nadie la usa; la primera visita
  la prende en ~21-23 s.
- **Azure App Service (B1, siempre prendida): <https://curva-sein.azurewebsites.net>** (ver
  [Azure App Service](#azure-app-service-publicada)). Queda como está hasta que el dueño decida.

La app (la API FastAPI, que sirve también la web en su mismo origen) no lleva los datos: viven en un **dataset** del
Hub de Hugging Face, y la app los baja al arrancar. El mismo arranque sirve para la imagen del `Dockerfile` (Container
Apps, y un **Space Docker** de Hugging Face: ver
[Hugging Face Spaces](#hugging-face-spaces-estado-21-de-noviembre-de-2026)) y para App Service (código + Oryx).

## Azure Container Apps (se apaga sola)

**URL pública: <https://curva.jollyocean-4175cf43.brazilsouth.azurecontainerapps.io>** (la salud en `/salud`). La misma
app y el mismo dataset público que App Service, en un contenedor que **baja a cero réplicas cuando nadie la usa**:
apagada no cobra nada, y la primera visita la prende en 21-23 s. Pública, como la de App Service; con dominio propio,
en <https://curva.rosewt.dev> (ver [Netlify](#netlify-curvarosewtdev-la-web-en-el-cdn-la-api-en-container-apps)).

```text
push a feature/despliegue-aca ──GitHub Actions (~1.5 min)──▶ ghcr.io/r0sewt/curva:sha-<commit>  (público, 331 MB)
                                                                   │ Container Apps la baja al prender una réplica
dataset rosewt/curva-datos ──descarga al arrancar (7 s)──▶ app curva (1 vCPU, 2 GiB, 0 o 1 réplica) ──▶ /salud, la web
```

### Qué se creó

| Recurso | Nombre | Detalle |
|---|---|---|
| Grupo de recursos | `curva-aca-rg` | Brazil South (la región permitida más cercana a Lima). Etiquetas `proyecto=curva`, `curso=upc-mds` (también en el entorno y la app). |
| Entorno de Container Apps | `curva-aca-env` | Modo **Express** (ver abajo), con **solo** el perfil Consumption; **sin Log Analytics** (ver abajo); sin red virtual propia. |
| Container App | `curva` | 1 vCPU y 2 GiB, **de 0 a 1 réplica**, regla de escala HTTP, ingreso externo solo HTTPS al puerto 7860. |
| Imagen | `ghcr.io/r0sewt/curva` | Paquete **público** de GitHub: Container Apps la baja sin credenciales. 331 MB comprimida (14 capas), 908 MB en disco. Etiquetas `sha-<commit>` y `latest`. |

- **La imagen se construye en GitHub, no en la laptop:** [`.github/workflows/imagen.yml`](../.github/workflows/imagen.yml)
  construye el `Dockerfile` en cada push a `feature/despliegue-aca` (y a mano desde Actions → «Imagen» → «Run
  workflow»; no en cada PR) y la publica con la etiqueta del commit y `latest`. El resumen del job trae el tamaño.
  El paquete quedó público al publicarse (se comprobó bajando el manifiesto y una capa sin credenciales), así que no
  hay ningún token guardado en Azure. Si algún día deja de serlo, el script lo detecta antes de tocar la app.
- **Modo Express.** El CLI (extensión `containerapp` 1.3.0b4) creó el entorno en modo Express sin que se le pidiera;
  el script ahora lo pide explícito (`--environment-mode Express`) y lo verifica. Según Microsoft ([preguntas
  frecuentes de Express](https://learn.microsoft.com/azure/container-apps/express-faq)) se cobra con las mismas
  tarifas Consumption y las mismas cuotas gratis, sin cargo por el entorno ni por bajar la imagen. Es lo que hace tan
  corto el arranque en frío (el contenedor arranca ~1 s después del pedido). A cambio, **no admite dominios propios**
  (ver «Dominio propio»), ni HTTP/2, ni división de tráfico entre revisiones: cada cambio reemplaza la revisión, que
  siempre se llama `curva--latest`.
- **Logs: ninguno guardado.** El entorno se creó con `--logs-destination none`. Log Analytics cobra por cada GB que
  guarda (4.60 USD/GB en Brazil South, API de precios) y cada arranque escribe unas líneas: con «ninguno» ese cargo
  no existe. Los logs del contenedor se leen **en vivo** mientras hay una réplica prendida (`--logs`, o en el portal:
  la app → «Log stream») y se pierden al apagarse. Si hiciera falta guardarlos: `az containerapp env update -n
  curva-aca-env -g curva-aca-rg --logs-destination log-analytics --logs-workspace-id ... --logs-workspace-key ...
  --subscription "Azure for Students"` (con un espacio de trabajo de Log Analytics, que cobra). El flujo de eventos
  del sistema (`az containerapp logs show --type system`) no funciona en este entorno sin destino (responde 400); los
  arranques y reinicios se ven en `--estado`.

### Configuración (la aplica y la verifica el script)

| Qué | Valor | Por qué |
|---|---|---|
| CPU y memoria | 1 vCPU, 2 GiB | La app ocupa 1.17-1.24 GB en uso (métrica `WorkingSetBytes`): sobra ~40 %. |
| Réplicas | mínimo 0, máximo 1 | Se apaga sola; con una sola réplica, el registro en vivo y lo ya calculado viven en un solo lugar. |
| Escala | regla HTTP (10 pedidos simultáneos por réplica); baja a cero tras 300 s sin pedidos | Lo de por defecto de Container Apps. |
| Ingreso | externo, puerto 7860, transporte HTTP/1.1, sin HTTP plano (`allowInsecure: false`) | El puerto del `Dockerfile`. |
| Sonda de arranque | TCP al 7860 cada 1 s, hasta 240 fallas (4 min) | La que pone Container Apps por defecto. uvicorn abre el puerto recién con los modelos cargados. |
| Sondas de vida y de disponibilidad | TCP al 7860 (cada 30 s y cada 10 s) | No `/salud`: con la única CPU ocupada en un cálculo largo, `/salud` puede tardar, pero el puerto acepta conexiones. |
| `TPF_HF_DATASET`, `TPF_PRONOSTICADOR` | `rosewt/curva-datos`, `real` | De dónde bajan los datos y qué modelo se sirve. Sin `HF_TOKEN`: el dataset es público. |
| `TPF_CALENTAR` | `0` | Ver «Arranque en frío»: el puerto abre a los ~20 s en vez de ~30. |
| `TPF_RECARGA_MIN`, `PORT`, `MALLOC_ARENA_MAX` | `15`, `7860`, `2` | Relee el registro en vivo cada 15 min (eso no mantiene la app prendida), el puerto y menos memoria fragmentada. |

La especificación entera va en un solo PUT a la API de Container Apps (`az rest`, versión `2025-07-01`), en ASCII, y
solo si lo que hay en Azure es distinto; después se **lee de vuelta** campo por campo. Dos cosas que devuelve Azure
distinto de lo que uno manda, y que el script ya contempla: con transporte «auto» guarda «Http» (por eso se pide
«http»), y la espera de 300 s antes de bajar a cero (el valor por defecto) vuelve vacía.

### Comandos

Desde la raíz del repo, con `az login` hecho (la cuenta UPC entre las del CLI; **no** hace falta que sea la suscripción
por defecto: todo pasa `--subscription "Azure for Students"`, y el script se niega a usar otra cuenta o suscripción).

```bash
python despliegue/publicar_aca.py --dry-run                # los comandos que correría, sin tocar Azure
python despliegue/publicar_aca.py                          # crear lo que falte + configurar + verificar (idempotente)
python despliegue/publicar_aca.py --imagen sha-abc1234     # pasar a la imagen de otro commit (+ prueba de humo)
python despliegue/publicar_aca.py --estado                 # URL, imagen, réplicas prendidas, reinicios, revisión
python despliegue/publicar_aca.py --logs                   # las últimas 60 líneas del contenedor (si está prendido)
python despliegue/publicar_aca.py --metricas 24            # réplicas, pedidos, memoria y costo de las últimas 24 h
python despliegue/publicar_aca.py --apagar                 # la detiene: la URL responde 502 y nada la despierta
python despliegue/publicar_aca.py --prender                # la vuelve a prender (+ prueba de humo)
python despliegue/publicar_aca.py --borrar                 # borra curva-aca-rg entero (pide escribir el nombre)
python despliegue/humo.py https://curva.jollyocean-4175cf43.brazilsouth.azurecontainerapps.io   # prueba de humo
```

- **Actualizar a una imagen nueva:** push del commit a `feature/despliegue-aca`, esperar el workflow «Imagen» (~1.5
  min) y `python despliegue/publicar_aca.py --imagen sha-<7 primeros caracteres del commit>`. El script comprueba que
  la etiqueta exista en ghcr.io, crea la revisión nueva, la prende (prueba de humo) y confirma que la que tiene el
  tráfico es la nueva. `--imagen latest` se fija al digest de ese momento: con una etiqueta que se mueve, cada
  arranque en frío bajaría la imagen que fuera la última, distinta de la que se probó. Sin `--imagen`, el script
  **conserva** la imagen que tiene la app. Los datos no se redespliegan: la app los relee del dataset cada 15 min.
- **Apagar sin borrar:** no hace falta, porque sin visitas ya está en cero y no cobra. `--apagar` sirve para que nadie
  pueda prenderla: la detiene (la API de Container Apps, `POST .../stop`) y la URL responde 502 «Failed to resolve
  route». `--prender` la vuelve a prender (sigue apagándose sola sin visitas) y corre la prueba de humo; la
  configuración y la dirección no cambian. Probado: detenerla tardó 10 s; prenderla y pasar la prueba de humo, 48 s.
- **Fijar una réplica prendida para un evento (no aplicado; lo decide el dueño):** `python despliegue/publicar_aca.py
  --minimo 1` el día antes, y `--minimo 0` cuando termine. Con una réplica siempre prendida no hay arranque en frío,
  pero **cobra todo el tiempo** aunque nadie entre (ver «Costo»). El script conserva el mínimo que tenga la app si no
  se le pasa `--minimo`, así que un `--imagen` durante el evento no la vuelve a cero. Lo mismo sin el script:
  `az containerapp update -n curva -g curva-aca-rg --min-replicas 1 --subscription "Azure for Students"`.
- **Borrar todo** (no se puede deshacer; la dirección queda libre): `python despliegue/publicar_aca.py --borrar`, o
  `az group delete -n curva-aca-rg --subscription "Azure for Students"`. El script solo borra un grupo con las
  etiquetas del proyecto y sin recursos ajenos a Container Apps, y nunca `curva-rg` (App Service) ni
  `aire-distribuido-rg`. La imagen en ghcr.io queda (se borra desde el paquete en GitHub, si se quiere).

### Dominio propio: no en Container Apps, sí con Netlify

El modo Express **no admite dominios propios**: `az containerapp hostname add` respondió
`ExpressCustomDomainsNotSupported`. El dueño eligió no cambiar el modo y servir `curva.rosewt.dev` desde un sitio de
Netlify que le pasa la API a esta app (ver [Netlify](#netlify-curvarosewtdev-la-web-en-el-cdn-la-api-en-container-apps)).
Los dos registros que se habían creado para validar el dominio en Azure (CNAME `curva` y TXT `asuid.curva`) se
borraron. Si algún día se pasa el entorno a WorkloadProfiles (`MODO` en el script; `az containerapp env update
--environment-mode workloadprofiles`, 15-30 min), el script conserva los dominios vinculados al cambiar la imagen o el
mínimo; el arranque en frío habría que volver a medirlo.

### Mediciones (21 de noviembre de 2026)

Desde una conexión de casa en Lima, con la app en cero réplicas antes de cada arranque en frío (comprobado con la
lista de réplicas y la métrica `Replicas`). El reloj arranca con el primer pedido; a la vez se abrió la web en un
navegador y se midió cuándo llegó «Ahora» (la cifra en MW) con los tiempos del propio navegador.

| Arranque en frío (pedido → respuesta) | `/salud` 200 | La web muestra «Ahora» | Todos los pedidos de la web | Errores |
|---|---|---|---|---|
| 1. Con calentamiento antes de abrir el puerto (la configuración inicial) | 32.8 s | — | — | **503 «App port is not ready» a los 31.3 s**, en `/salud` y en la web |
| 2. Configuración final | **21.2 s** | 21.7 s | 23.4 s | ninguno |
| 3. Configuración final | **23.0 s** | 23.5 s | 25.2 s | ninguno |
| 4. Configuración final | **23.0 s** | 23.5 s | 25.2 s | ninguno |

- **De qué se compone** (logs del contenedor): el contenedor arranca ~1 s después del pedido (la imagen ya está en
  el nodo), baja los datos del dataset en 7-8 s y carga los modelos en ~12 s; uvicorn abre el puerto a los ~20 s.
  Con el calentamiento previo (10 pedidos, 10 s) abría a los ~31 s.
- **Por qué se quitó el calentamiento:** mientras la réplica arranca, Container Apps retiene el primer pedido, pero
  a los ~30 s se rinde y responde 503 `{"error":"App port is not ready"}`. Con el calentamiento la app abría el
  puerto 0.4 s tarde y el primer visitante veía ese texto en vez de la web. Sin calentar, lo que se saltea se calcula
  cuando la web lo pide: en esta CPU, el primer «Confianza» tardó 2.7 s y el primer «Detalle» 3.1 s (en la B1 de App
  Service, 18.8 y 19.6 s).
- **Con la app prendida** (latencia por pedido): conexión TCP 104 ms; un pedido con conexión nueva 320-440 ms; con la
  conexión abierta, como el navegador, 106-236 ms. Prueba de humo (16 pedidos, conexión nueva en cada uno): mediana
  413 ms, máximo 724 ms. En el navegador, los pedidos de la web tardan 124-267 ms. Un «Confianza» que nadie pidió
  aún (1 h, híbrido o combinado) tarda 1.5-2.8 s.
- **Memoria:** la métrica `WorkingSetBytes` llegó a **1.28 GB (1.19 GiB) de los 2 GiB (60 %)**, con 1.17-1.24 GB
  en uso normal. CPU en reposo: 2-4 milésimas de vCPU (menos del 0.01 que Container Apps cuenta como «en reposo»).
- **Vuelve a cero sola:** ~5 min después del último pedido (último pedido 17:26:4x, cero réplicas 17:31:48; la
  métrica `Replicas` lo confirma en cada prueba). Entre las 18:58 y las 21:29 (hora UTC) estuvo en cero, sin cobrar.
- **Visitas que la mantienen prendida:** cualquier pedido reinicia los 5 min. Durante las pruebas hubo visitas a `/`
  y `/salud` que no eran de las mediciones, cada pocos minutos; con un visitante así de seguido la app no llega a
  apagarse.

### Costo

Precios públicos del plan Consumption en Brazil South (API de precios de Azure, 21/11/2026; los mismos en modo
Express): vCPU activo 0.000024 USD/s, en reposo 0.000003; memoria 0.000003 USD/GiB-s (activo o en reposo); 0.40 USD
por millón de pedidos. Gratis cada mes por suscripción: 180 000 vCPU-s, 360 000 GiB-s y 2 millones de pedidos. Con
1 vCPU y 2 GiB, **una réplica activa cuesta 0.000030 USD/s = 0.108 USD por hora**; en reposo, 0.0324 USD por hora.

| Escenario | Consumo al mes | Costo al mes |
|---|---|---|
| **Se apaga sola, uso bajo** (cada visita la prende ~20 s + uso + 5 min hasta apagarse: ~10.5 min por visita de 5 min) | hasta ~285 visitas separadas (~9 por día) entran en lo gratis | **0 USD**; ~0.019 USD por visita de más (20 visitas por día: ~5.9 USD) |
| Lo que consumieron estas pruebas (64 min de réplica en 5.5 h, 151 pedidos; `--metricas 5.5`) | 3 840 vCPU-s, 7 680 GiB-s | 0 USD (dentro de lo gratis) |
| **Prendida siempre** (`--minimo 1`, 730 h) en reposo casi todo el tiempo | 2 628 000 vCPU-s en reposo, 5 256 000 GiB-s | **~22 USD** |
| Prendida siempre y siempre activa (el peor caso) | 2 628 000 vCPU-s activos | ~73 USD |
| Una semana de exposición con `--minimo 1` (8 h activas por día, el resto en reposo) | | ~8-10 USD (menos lo gratis que quede del mes) |
| Comparación: App Service B1 (`curva-rg`, sigue prendida) | | 14.60 USD fijos |

**Otros cargos (revisado en la documentación de Microsoft):** el entorno no cobra (Express y Consumption no tienen
cargo fijo; la tarifa de gestión de 0.10 USD/h es solo para perfiles dedicados, mantenimiento planificado o
puntos de conexión privados, que no se usan); no hay Log Analytics (4.60 USD/GB si se activara); sin red virtual
propia ni IP pública aparte; bajar la imagen no cobra (ghcr.io es gratis para paquetes públicos y Express no cobra
las descargas); la salida de datos a internet es gratis hasta 100 GB al mes (una visita completa son ~0.3 MB) y las
sondas de salud no cuentan como pedidos.


### Presupuesto y cómo ver el consumo

**Alerta de presupuesto** (creada el 22/11/2026, con la API de Cost Management): `mensual-5usd`, a nivel de toda la
suscripción «Azure for Students», **5 USD por mes**, de noviembre de 2026 a diciembre de 2027. Avisa por correo a la
cuenta UPC de la suscripción (la de `az account show --subscription "Azure for Students" --query user.name`) cuando el
gasto **real** llega al **50 %** y al **100 %** y cuando el **pronosticado** llega al **100 %**. Es solo un aviso: no
apaga nada. Abarca todo lo que cobra en la suscripción, también la B1 de App Service (14.60 USD al mes: si sigue
prendida, los avisos llegarán) y los recursos de otros cursos. Ya existía otro presupuesto, `credito-estudiante`
(100 USD por año), que no se tocó.

```bash
S="Azure for Students"; SUB=$(az account show --subscription "$S" --query id -o tsv)
B="https://management.azure.com/subscriptions/$SUB/providers/Microsoft.Consumption/budgets"
az rest --method get --url "$B/mensual-5usd?api-version=2023-05-01" --subscription "$S" \
  --query "properties.{monto:amount,gastado:currentSpend.amount,pronostico:forecastSpend.amount}"
# Cambiar el monto (p. ej. a 10 USD): leer, editar y volver a escribir el mismo presupuesto
az rest --method get --url "$B/mensual-5usd?api-version=2023-05-01" --subscription "$S" > /tmp/presupuesto.json
#   editar "amount" en /tmp/presupuesto.json (y, si se quiere, los umbrales en "notifications")
az rest --method put --url "$B/mensual-5usd?api-version=2023-05-01" --subscription "$S" --body @/tmp/presupuesto.json
az rest --method delete --url "$B/mensual-5usd?api-version=2023-05-01" --subscription "$S"   # borrarlo
```

También en el portal: Cost Management → Budgets. **Para ver el consumo del mes por grupo de recursos** (los datos
llegan con 8-24 h de atraso):

```bash
echo '{"type":"ActualCost","timeframe":"MonthToDate","dataset":{"granularity":"None",
  "aggregation":{"total":{"name":"Cost","function":"Sum"}},
  "grouping":[{"type":"Dimension","name":"ResourceGroupName"}]}}' > /tmp/consulta.json
az rest --method post --url "https://management.azure.com/subscriptions/$SUB/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
  --subscription "$S" --body @/tmp/consulta.json --query properties.rows
```

El 22/11/2026 daba, en lo que va de noviembre: `curva-rg` (App Service) 0.28 USD, `curva-aca-rg` (Container Apps)
0.003 USD (103 vCPU-s y 206 GiB-s), y los grupos de otros cursos. `python despliegue/publicar_aca.py --metricas 24`
estima el de Container Apps al momento, desde las métricas.

## Netlify: `curva.rosewt.dev` (la web en el CDN, la API en Container Apps)

**URL pública: <https://curva.rosewt.dev>** (también <https://curva-rosewt.netlify.app>). El dueño eligió esta
opción: el entorno de Container Apps sigue en modo Express, que no admite dominios propios, y el dominio lo sirve un
sitio de Netlify de su cuenta personal (la misma que administra la zona `rosewt.dev`).

```text
navegador ──▶ curva.rosewt.dev (Netlify, CDN) ──▶ la web estática (app/web): carga al instante aunque el servidor duerma
                    │ _redirects: solo las rutas de la API, «proxy» (200)
                    └──────────────▶ curva.jollyocean-…azurecontainerapps.io (Container Apps, 0 o 1 réplica)
```

- **La web no espera al servidor para aparecer.** El HTML, los scripts y los estilos salen del CDN de Netlify; solo
  `/salud`, `/modelos`, `/areas`, `/resumen`, `/pronostico`, `/sensibilidad` y `/series`, `/diagnostico`,
  `/seguimiento`, `/pico`, `/en-vivo`, `/ahora` y `/confianza` (con su área) van a Container Apps. La web ya llamaba a
  la API en su mismo origen, así que no cambió nada en cómo la busca. Un test comprueba que las reglas cubren todas
  las rutas del backend: una ruta nueva sin regla daría 404 en este dominio.
- **Límite del proxy: 26 s.** «Proxy rewrite requests will time out after 26 seconds» ([Netlify, Rewrites and
  proxies → Limitations](https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/)). El arranque en frío
  medido es de 21-23 s hasta que la API responde: entra, con 3-5 s de margen. Si un arranque tarda más, el proxy
  responde con error y la web reintenta (abajo).
- **El aviso al despertar** (`app/web/app.js`, `pedirDespertando`): si un pedido a la API tarda más de 4 s (el proxy
  lo retiene mientras el servidor arranca) o vuelve con 502, 503 o 504, arriba aparece «Despertando el servidor, unos
  segundos…» (`role="status"`); los 502/503/504 se reintentan con espera creciente (1, 2, 4, 8, 8… s) hasta ~60 s
  antes de mostrar el error. Sin conexión, el error con «Reintentar» sale enseguida, como antes. Con el servidor
  prendido, el cálculo más lento tarda ~3 s, así que no aparece. El gráfico de «Ahora» tiene nombre y valores ARIA
  mientras carga (axe lo marcaba con el aviso visible).
- **Medido con el arnés** (`app/medicion`, `node medir.mjs --version it8 --solo tareas,axe --rapido`, contra la app
  local): tareas T1-T4 cumplidas en escritorio y móvil, **axe 0 infracciones en 40 pantallas**
  ([`resultados/netlify-despertar.json`](../app/medicion/resultados/netlify-despertar.json)). Con el servidor simulado
  dormido 15 s (la API responde 503), el aviso aparece a los 0.2 s, se va a los 15.5 s junto con los datos, sin error
  y con axe 0 mientras se ve.
- **Verificado a través del proxy:** las respuestas son idénticas byte a byte a las de Container Apps directo (los
  parámetros de la URL pasan), el `POST /pronostico` funciona y la prueba de humo pasa (`python despliegue/humo.py
  https://curva.rosewt.dev`).

**Visitas con la app dormida** (Chrome sin caché, desde Lima, con la app en cero réplicas comprobado con la métrica
`Replicas`; el reloj arranca al pedir la página):

| Primera visita a `https://curva.rosewt.dev` con la app en cero réplicas | Página | Aparece el aviso | Se ve «Ahora» (la cifra en MW) | Se va el aviso | Errores |
|---|---|---|---|---|---|
| 1 (22:30 UTC) | 1.3 s | 5.3 s | **23.3 s** | 25.1 s | ninguno; las 9 llamadas a la API, 200 |
| 2 (03:00 UTC) | 0.6 s | 4.6 s | **22.8 s** | 24.6 s | ninguno; las 9 llamadas a la API, 200 |
| Con la app ya despierta (después de cada una) | 1.0 s | — | 1.1 s | — | ninguno |

El proxy de Netlify retuvo las llamadas mientras el servidor arrancaba y no devolvió ningún error: la página apareció
enseguida, el aviso salió a los 4 s de espera y se fue cuando llegaron todos los datos. axe contra el sitio publicado
(«Ahora» y «Confianza», escritorio y móvil): 0 infracciones. Netlify agrega a los sitios de cuentas gratis su script
`hud` (el botón «Powered by Netlify» abajo a la derecha, igual que en `uni.rosewt.dev`), que tapa una esquina del
contenido.

### Caché en la CDN y `robots.txt` (para que las visitas automáticas no despierten al servidor)

Si alguien mantuviera la app despierta todo el mes (un monitor o un robot que pide datos cada pocos minutos), se
cobraría la tarifa activa: ~73 USD al mes. Dos defensas:

- **Las respuestas de datos se guardan en la CDN de Netlify.** Netlify **no** guarda lo que viene de un proxy salvo que
  el origen lo pida con cabeceras de caché: «responses coming from Netlify Functions, Edge Functions, Netlify Server,
  and proxies are not cached by default» ([Netlify, Caching overview](https://docs.netlify.com/build/caching/caching-overview/)).
  El backend (`app/backend/main.py`, `cache_de_datos`) agrega a cada respuesta **200 de un GET de la API**:

  | Cabecera | Valor | Para qué |
  |---|---|---|
  | `Cache-Control` | `public, max-age=60` | El navegador la reusa 1 min. |
  | `Netlify-CDN-Cache-Control` | `public, s-maxage=1800` | La CDN de Netlify la guarda 30 min (solo Netlify lee esta cabecera). |

  La clave de la caché es la URL completa con sus parámetros: `/confianza/norte?horizonte=1h` y `?horizonte=24h` son
  entradas distintas (bien), pero un parámetro inventado (`?x=123`) también hace una entrada nueva y llega al servidor.
  Se probó `Netlify-Vary: query=<los parámetros de la API>` para que los ignorara y en un proxy no cambia nada (la
  misma URL con y sin `?q=…`, por la misma conexión, falló las dos veces), así que se quitó. Los errores de la API y
  los `POST` llevan `Cache-Control: no-store`. Los 502/503/504 de la plataforma («App port
  is not ready») o del proxy no traen cabeceras de caché, y sin ellas Netlify no guarda nada de un proxy: el aviso de
  «Despertando el servidor» y los reintentos siguen igual (verificado: un 404 pedido dos veces llega dos veces al
  origen, `fwd=miss` sin `stored`). `/salud` también se guarda porque la web la pide al arrancar; si se guardara solo
  lo demás, cada visita despertaría al servidor por ella. Con 30 min en la CDN y 15 min de recarga del registro, lo
  que se ve puede tener hasta ~45 min de atraso (los datos cambian una vez al día). Cada publicación del sitio de
  Netlify borra esta caché; para borrarla sin publicar: `netlify api purgeCache --data '{"body": {"site_id":
  "1e12ea46-b8c6-4245-9ef1-06fd67209b14"}}'`. La cabecera `cache-status` dice si respondió la caché (`hit`) o el
  servidor (`fwd=miss`).

  **Medido con la app dormida** (Chrome nuevo en cada visita; pedidos que llegaron a Azure según la métrica
  `Requests`):

  | Visita a `https://curva.rosewt.dev` | Aciertos de la caché | Pedidos que llegaron a Azure | La app | «Ahora» con datos |
  |---|---|---|---|---|
  | 1. 05:07 UTC, caché vacía (recién publicado) | 0 de 8 | 8 | se despertó | 22.8 s (con el aviso) |
  | 2. 05:14, con la app ya de vuelta en cero | **8 de 8** | **0** | **siguió en cero** | **0.6 s** |
  | 3. 05:15, otro navegador nuevo | 0 de 8 | 8 | se despertó | 22.9 s (con el aviso) |

  **Cada nodo de la CDN tiene su propia caché.** La visita 2 cayó en el nodo que había atendido la 1 y no tocó Azure;
  la 3 cayó en otro nodo, vacío. Netlify comparte la caché entre nodos (`durable`) solo para sus Functions, no para un
  proxy. Por eso la CDN guarda 30 min (lo más que se acordó, en vez de 15): cada nodo pide los datos a lo sumo una
  vez cada 30 min. Un visitante automático todavía puede despertar al servidor, pero muchas menos veces.
- **`robots.txt`** ([`app/web/robots.txt`](../app/web/robots.txt), servido en <https://curva.rosewt.dev/robots.txt>)
  deja la portada y bloquea las 13 rutas de datos: `/salud`, `/modelos`, `/areas`, `/resumen`, `/pronostico`,
  `/sensibilidad` y `/series/`, `/diagnostico/`, `/seguimiento/`, `/pico/`, `/en-vivo/`, `/ahora/`, `/confianza/`.
  Los buscadores que ejecutan la web para indexarla no piden esas rutas, y la página igual se indexa. Un test
  comprueba que están todas las rutas de la API y que no bloquea archivos de la web (`/confianza.js` no cae en
  `/confianza/`). Los robots que no ejecutan JavaScript solo bajan la página, que sale del CDN y no toca Azure.

### DNS y certificado

- **Se borraron** los dos registros que se habían creado para el dominio propio en Container Apps (por su id, nada
  más): CNAME `curva.rosewt.dev` → `curva.jollyocean-4175cf43.brazilsouth.azurecontainerapps.io` y TXT
  `asuid.curva.rosewt.dev`.
- **Se asignó** `curva.rosewt.dev` al sitio `curva-rosewt` (`custom_domain`); Netlify creó solo su registro
  (`NETLIFY curva.rosewt.dev → curva-rosewt.netlify.app`). El certificado es el comodín `*.rosewt.dev` de Let's
  Encrypt que la cuenta ya tenía en Netlify DNS: válido desde el primer momento.
- **`https://rosewt.dev` y `https://uni.rosewt.dev` no cambiaron:** el mismo HTML byte a byte (sha256) y el mismo
  `ETag` antes y después; la zona quedó con los mismos 25 registros de antes más el de `curva`.

### Comandos

```bash
bash despliegue/publicar_netlify.sh --dry-run                 # arma la carpeta y muestra las reglas, sin publicar
bash despliegue/publicar_netlify.sh "mensaje"                 # publica en producción y prueba la web y /salud
CURVA_SIN_DESPERTAR=1 bash despliegue/publicar_netlify.sh     # prueba solo la web (no prende el servidor)
```

Requiere la CLI de Netlify con la sesión de la cuenta personal (`netlify status`), o `npx`, que la descarga. Lo que se
hizo una vez (no hace falta repetirlo):

```bash
netlify api createSiteInTeam --data '{"account_slug": "r0sewt", "body": {"name": "curva-rosewt"}}'
netlify api updateSite --data '{"site_id": "1e12ea46-b8c6-4245-9ef1-06fd67209b14", "body": {"custom_domain": "curva.rosewt.dev"}}'
```

- **Si cambia la dirección de Container Apps** (por ejemplo, si se borra y se vuelve a crear el entorno), hay que
  cambiar `origen` en el script y volver a publicar.
- **Costo:** el plan gratuito de Netlify da 300 créditos al mes **compartidos con los demás sitios de la cuenta**
  (`rosewt.dev`, `uni.rosewt.dev`, ...): cada publicación en producción gasta 15, cada GB servido 20 y cada 10 000
  pedidos 2 ([precios de Netlify](https://www.netlify.com/pricing/)). Una visita completa son ~0.3 MB: el uso normal
  no se nota, pero ~20 publicaciones en un mes agotarían los créditos de toda la cuenta. Publicar solo cuando cambie
  la web (los datos no pasan por aquí).
- **Deshacer:** quitar el dominio del sitio (`netlify api updateSite --data '{"site_id": "1e12ea46-b8c6-4245-9ef1-06fd67209b14", "body": {"custom_domain": null}}'`,
  o en el panel: el sitio → Domain management) y, si se quiere, borrar el sitio (`netlify sites:delete
  1e12ea46-b8c6-4245-9ef1-06fd67209b14`). Comprobar después que el registro `NETLIFY curva.rosewt.dev` ya no está en
  la zona (app.netlify.com → Domains → rosewt.dev); los demás registros no se tocan. La app de Container Apps sigue
  en su dirección `azurecontainerapps.io`.

## Azure App Service (publicada)

**URL pública: <https://curva-sein.azurewebsites.net>** (la salud en `/salud`). Es pública a propósito: el dueño lo
decidió, y el dataset `rosewt/curva-datos` también es público, así que no hay token ni secreto que guardar.

```text
dataset rosewt/curva-datos (público, 68 MB) ──descarga al arrancar (14 s)──▶ Web App curva-sein (Python 3.13, plan B1)
        ▲                                                                     │  python despliegue/arranque.py
        └── actualizar_hf.py: el registro en vivo de cada mañana              └▶ uvicorn en $PORT → /salud, la web
```

### Qué se creó y cuánto cuesta

| Recurso | Nombre | Detalle |
|---|---|---|
| Suscripción | «Azure for Students» | La de la cuenta UPC del dueño (crédito de 100 USD, sin tarjeta). El script se niega a usar otra. |
| Grupo de recursos | `curva-rg` | Brazil South. Etiquetas `proyecto=curva`, `curso=upc-mds` (también en el plan y la app). |
| Plan de App Service | `curva-plan` | **B1 Linux**: 1 vCPU, 1.75 GB de RAM, 10 GB de disco, 1 instancia. |
| Web App | `curva-sein` | Python 3.13 (la versión del `Dockerfile`), «Always On», solo HTTPS, TLS 1.2, sin FTP. |

- **Costo: 0.020 USD por hora = 14.60 USD al mes** (B1 Linux en Brazil South, 730 h; API pública de precios de Azure,
  21/11/2026). Se cobra **el plan**, esté la app prendida o detenida, hasta que se baje a F1 o se borre. Los 100 USD del
  crédito alcanzan para ~6.8 meses de B1 sola; menos con otros recursos en la suscripción (hoy hay una VM de otro
  curso). En East US 2 costaría 12.41 USD/mes; una B2 (3.5 GB) en Brazil South, 29.93.
- **Región: Brazil South**, la más cercana a Lima entre las cinco que permite la política de la suscripción
  («Allowed resource deployment regions»: `brazilsouth`, `mexicocentral`, `eastus2`, `canadacentral`,
  `southcentralus`). Conexión TCP medida desde Lima (mínimo de 5): Brazil South 104 ms, East US 2 131, South Central US
  137, Canada Central 152 y Mexico Central 155.
- **Método: despliegue de código, compilado por App Service (Oryx).** El script sube un zip de ~0.2 MB (el código y un
  `requirements.txt` sacado de `uv.lock`); Oryx instala las dependencias en Azure. No se construye ninguna imagen y la
  laptop no baja nada pesado. Se descartó la imagen en ghcr.io: suma un workflow, la visibilidad del paquete y, si es
  privado, una credencial de GitHub guardada en Azure; y Azure Container Registry cuesta aparte.
- **Sin NCCL:** XGBoost para Linux depende de NCCL (cientos de MB, solo para varias GPU). El `requirements.txt` pide
  `xgboost-cpu`, la misma versión (3.4.1) compilada sin CUDA: el módulo se llama igual y la API respondió **idéntico**
  con una y otra en 462 pedidos (tres áreas, tres modelos, dos horizontes, variantes, escenarios, sensibilidad, «Ahora»
  y «Confianza»).

### Configuración (la aplica y la verifica el script)

| Qué | Valor | Por qué |
|---|---|---|
| Comando de inicio | `python despliegue/arranque.py` | El mismo arranque del `Dockerfile`, corrido como archivo (pone `src/` en el path). |
| `TPF_HF_DATASET` | `rosewt/curva-datos` | De dónde baja los datos. |
| `TPF_PRONOSTICADOR` | `real` | El modelo entrenado (si los datos no bajan, el arranque cae a los de prueba y lo avisa). |
| `TPF_CACHE`, `HF_HOME` | `/tmp/curva-datos`, `/tmp/hf` | Disco local: cada arranque baja el paquete limpio, sin basura en el `/home` persistente. |
| `TPF_RECARGA_MIN` | `15` | Relee el registro en vivo del dataset cada 15 min. |
| `MALLOC_ARENA_MAX` | `2` | Menos memoria fragmentada en una máquina justa. |
| `WEBSITES_CONTAINER_START_TIME_LIMIT` | `1800` | 30 min para arrancar, el máximo (por defecto 230 s). Con 900 s, un arranque lento en otra máquina se pasó y Azure lo reinició. |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Que Oryx instale `requirements.txt`. |
| Comprobación de salud | `/salud` | App Service la pide cada minuto. |
| Logs del contenedor | `filesystem` | Para leerlos con `--logs` o en el portal. |
| `PORT` | (lo pone App Service: 8000) | El arranque lo lee; no hace falta fijarlo. |

Todo va en ASCII y el script lo **lee de vuelta** después de aplicarlo: si algo no quedó (por ejemplo, una tilde
dañada en el comando de inicio), se detiene y dice qué. Solo escribe lo que difiere: cada cambio de configuración
reinicia la app, y en B1 un reinicio así no cabe en memoria (ver «Mediciones»). Si en B1 hay algo que cambiar, primero
detiene la app y al final la vuelve a prender.

### Comandos

Desde la raíz del repo, con `az login` hecho (la cuenta UPC tiene que estar entre las del CLI; **no** hace falta que
sea la suscripción por defecto: todo pasa `--subscription "Azure for Students"`).

```bash
python despliegue/publicar_azure.py --dry-run       # los comandos que correría, sin tocar Azure
python despliegue/publicar_azure.py                 # crear lo que falte + configurar + desplegar + prueba de humo
python despliegue/publicar_azure.py --solo-config   # solo reaplicar y verificar la configuración
python despliegue/publicar_azure.py --logs          # las últimas 60 líneas del log de la app y de la plataforma
python despliegue/publicar_azure.py --reiniciar     # detener y prender + prueba de humo (en B1, no «restart»)
python despliegue/humo.py https://curva-sein.azurewebsites.net                 # prueba de humo, desde cualquier lado
python despliegue/humo.py https://curva-sein.azurewebsites.net --esperar 900   # tras un reinicio
```

- **Actualizar el código:** `python despliegue/publicar_azure.py` otra vez (es idempotente: no recrea nada). **En B1 la
  app queda 10-13 min sin servicio:** el script la detiene, Oryx compila (~5 min) y la prende con el código nuevo
  (6.5-9 min hasta responder con todo calculado). Es a propósito: en B1 no caben a la vez la app vieja y la nueva, y
  el primer despliegue «en caliente» dejó la máquina sin memoria; Azure movió la app a otra y estuvo ~10 min caída
  igual. Desde B2 se puede desplegar sin detenerla con `--en-caliente`. Los datos no se redespliegan: se actualizan en el dataset
  (`actualizar_hf.py`) y la app los relee sola cada 15 min.
- **Ver logs:** `--logs` arriba, o en el portal: la Web App → «Log stream». **`az webapp log tail` y `az webapp deploy`
  no funcionan en la laptop del dueño:** piden el token de Kudu en el tenant de la suscripción por defecto del CLI (la
  del trabajo) y Kudu responde 403. El script pide ese token con `--subscription` y habla con Kudu directo.
- **Reiniciar:** `python despliegue/publicar_azure.py --reiniciar` (detiene, prende y corre la prueba de humo; ~9 min).
  **No usar `az webapp restart` ni el botón «Restart» del portal en B1:** arrancan la copia nueva con la vieja viva, no
  caben las dos y la app quedó lenta 4 min y caída 13 min (se probó; ver «Mediciones»).
- **Apagar sin borrar (deja de cobrar):** detener la app no basta, porque se cobra el plan. Hay que bajarlo a F1
  (gratis; F1 no admite «Always On»). **No se probó** bajar a F1 (subir a B2 y volver a B1 sí):

  ```bash
  S="Azure for Students"
  az webapp stop -n curva-sein -g curva-rg --subscription "$S"
  az webapp config set -n curva-sein -g curva-rg --always-on false --subscription "$S"
  az appservice plan update -n curva-plan -g curva-rg --sku F1 --subscription "$S"
  ```

  Para volver: `python despliegue/publicar_azure.py --solo-config --sku B1` (sube el plan, reactiva «Always On» y lo
  verifica) y `az webapp start -n curva-sein -g curva-rg --subscription "$S"`. Si F1 falla, lo seguro es borrar.
- **Borrar todo** (no se puede deshacer; la URL `curva-sein` queda libre para cualquiera):
  `az group delete -n curva-rg --subscription "Azure for Students"`.
- **Subir a B2** (probado: la app vuelve sola en ~3 min): `python despliegue/publicar_azure.py --solo-config --sku B2`;
  volver con `--sku B1`. B2 cuesta 0.041 USD/h (29.93 USD/mes).

### Mediciones (21 de noviembre de 2026)

Desde una conexión de casa en Lima. En la laptop del dueño, como referencia, la app arranca en 8 s y su proceso ocupa
1.05 GB al abrir el puerto y 1.18 GB tras el calentamiento.

| Qué | B1 (lo publicado) | B2 (prueba de 5 min) | Laptop |
|---|---|---|---|
| Compilación de Oryx (`uv pip install` + comprimir el entorno) | 5-6 min | — | — |
| **Arranque en frío:** prender → `/salud` responde (todo calculado) | **6.5-9 min** (medido 4 veces) | ~3.3 min | 8 s |
| ・ de eso, cargar los modelos | 2.5-4 min | 58 s | 7 s |
| ・ de eso, calentar los 10 pedidos de la web | 140-240 s | 75 s | 5 s |
| «Confianza» de una combinación que nadie pidió aún (1 h, híbrido) | 18.8 s | 6.3 s | 0.9 s |
| «Detalle» del híbrido (diagnóstico, primera vez) | 19.6 s | 1.3 s | 0.3 s |
| Memoria de la máquina (métrica `MemoryPercentage` del plan) | 85-92 % de 1.75 GB | 60 % de 3.5 GB | — |
| Memoria de la app (métrica `MemoryWorkingSet`) | 0.6-0.72 GB | — | 1.05-1.18 GB (RSS) |
| Sin servicio al actualizar el código con el script | 10-13 min | (en caliente: ~0) | — |

- **Latencia desde Lima:** conexión TCP 104 ms (la más baja de las regiones permitidas). Un pedido con conexión nueva
  (TCP + TLS + respuesta) tarda ~340-440 ms y, con la conexión ya abierta (como hace el navegador), ~120-180 ms los
  pedidos chicos. La prueba de humo (16 pedidos, conexión nueva en cada uno) justo después de arrancar: mediana 615-763 ms,
  máximo 0.9-1.9 s. En el navegador, la página carga en 0.9 s y cada pantalla («Ahora», «Confianza», «Detalle») pide
  sus datos en 0.2-1.2 s, sin el aviso de datos de prueba.
- **La B1 arranca y sirve, pero no sobra nada.** Arranca y sirve todo sin errores ni avisos, y lo ya calculado responde en menos de
  1 s. Pero la máquina queda al 85-92 % de memoria y lo que se calcula por primera vez tarda 10-60 veces más que en la
  laptop; en B2, con el doble de memoria y de núcleos, entre 3 y 15 veces menos que en B1. Esa diferencia es mayor que
  el doble de CPU: buena parte es memoria (el sistema libera páginas mientras pandas arma tablas). **Qué se ve:** el
  primer visitante después de un arranque ya no espera (el calentamiento corre antes de abrir el puerto), pero quien
  abre por primera vez un modelo, horizonte o «Detalle» distinto de los de por defecto espera 20-40 s; después queda
  guardado hasta el próximo reinicio.
- **Riesgo de la B1: los reinicios solapados.** `az webapp restart`, el botón «Restart» del portal y los cambios de
  configuración arrancan la copia nueva mientras la vieja sigue viva, y en B1 no caben las dos. Se probó dos veces:
  la app respondió lenta 4 min y luego estuvo **13 min caída** hasta que Azure la movió a otra máquina; lo mismo pasó
  con un despliegue en caliente. `WEBSITE_DISABLE_OVERLAPPED_RECYCLING=1` no lo evita en Linux (se probó). Por eso el
  script despliega y reinicia deteniendo y prendiendo, y no reescribe la configuración que ya está bien. Los reinicios
  que decida Azure (mantenimiento) no se pueden evitar: en B1 pueden dejarla ~15 min fuera.
- **Y sin reiniciar también:** a las 10:50 (hora UTC) el sistema mató la app por falta de memoria (código de salida 137)
  sin que nadie la reiniciara, con la app en reposo y Kudu activo (se estaban leyendo los logs con `--logs`). Azure la
  volvió a arrancar sola, ~8 min sin servicio. En B1 la app vive al borde de la memoria.
- **Recomendación: B2, como mínimo para la exposición** (29.93 USD/mes, ~1 USD por día): `python
  despliegue/publicar_azure.py --solo-config --sku B2` el día antes y `--sku B1` después (cada cambio de plan mueve la
  app de máquina, ~3-9 min sin servicio). Con B2 caben las dos copias, los reinicios no la tumban y se puede desplegar
  con `--en-caliente`. Si el crédito alcanza, dejarla en B2.

## Hugging Face Spaces: estado (21 de noviembre de 2026)

```text
dataset USUARIO/curva-datos (68 MB) ──descarga al arrancar──▶ Space USUARIO/curva (Docker, CPU básico)
        ▲                                                         │  python -m despliegue.arranque
        └── actualizar_hf.py: el registro en vivo de cada mañana  └▶ uvicorn en :7860 → /salud, la web
```


- **Dataset publicado:** [`rosewt/curva-datos`](https://huggingface.co/datasets/rosewt/curva-datos), 68.1 MB
  (24 archivos; los sha256 del Hub coinciden con `MANIFIESTO.json`). Se creó privado y el dueño lo hizo **público**:
  ya no hace falta `HF_TOKEN` para leerlo (lo que sigue sobre el token aplica solo si vuelve a ser privado).
- **Space sin crear:** Hugging Face respondió `402 Payment Required` al crear `rosewt/curva`: «Static Spaces are free
  for everyone, but hosting Gradio and Docker Spaces on free cpu-basic requires a PRO subscription». Es un bloqueo del
  plan de la cuenta, no del código. Cuando el dueño decida (PRO, 9 USD/mes, o el plan B de abajo), el paso que falta es
  un solo comando: el de «Publicar» (el dataset ya subido no se vuelve a subir).

| Archivo | Qué hace |
|---|---|
| [`paquete.py`](paquete.py) | Arma el paquete de datos mínimo y su `MANIFIESTO.json` (sha256 de cada archivo). |
| [`arranque.py`](arranque.py) | El `CMD` del contenedor: baja el dataset, lo verifica y levanta la API. Recarga el registro en vivo cada 15 min. |
| [`publicar_hf.py`](publicar_hf.py) | Crea (si faltan) el dataset y el Space, sube datos y código, configura y espera a «Running». |
| [`actualizar_hf.py`](actualizar_hf.py) | Sube al dataset solo el registro en vivo que cambió (para después de la corrida diaria). |
| [`cuenta.py`](cuenta.py) | Lee el token solo de `HF_TOKEN` y se niega a publicar con cuentas de trabajo del CIP. |
| [`../Dockerfile`](../Dockerfile) | La imagen: Python 3.13, las versiones exactas de `uv.lock`, usuario con uid 1000, puerto 7860. |

## Cuánto pesa

Se midió qué archivos lee de verdad la app: con la carpeta de datos completa (**675 MB**), la API levantada con el
modelo real bajo `strace -e openat` y los 193 pedidos de todos los endpoints (tres áreas, tres modelos, dos horizontes,
todas las variantes, escenarios, sensibilidad, «Ahora» en vivo y en repaso, «Confianza» y la web). Abrió 21 archivos:

| Qué | Archivos | Originales | En el paquete |
|---|---|---|---|
| Modelos de la app (XGBoost, uno por horizonte y variante) | 6 `.joblib` + `metadatos.json` | 131.1 MB | comprimidos con xz |
| Híbrido y combinado (XGBoost sobre Simons, pesos) | 2 `.joblib` + `combinado.json` | 35.6 MB | comprimidos con xz |
| Pronósticos fundacionales precalculados (Simons, Chronos-2 ajustado) | 2 `.parquet` | 7.9 MB | tal cual |
| Capas silver: demanda por área del COES y exógenas | 5 `.parquet` | 10.3 MB | tal cual |
| Tabla de adaptación del notebook 03 | 1 `.csv` | 0.005 MB | tal cual |
| Registro en vivo (pronósticos, seguimiento, resumen) | 3 `.parquet` | 1.5 MB | tal cual |
| **Total** | **21** | **186.5 MB** | **68.1 MB** |

No van los pesos de Chronos-2 (los usa solo la corrida diaria, no la app), el bronze, la demanda en vivo
(`demanda_areas_en_vivo.parquet`: la app no la lee, el real de los días en vivo viene en `seguimiento.parquet`) ni los
demás reportes. Con el paquete, la app responde **idéntico** a la carpeta completa: los 193 pedidos dan los mismos
JSON. En memoria ocupa unos 1.25 GB; arranca en unos 15 s en una laptop una vez bajados los datos.

La imagen la construye Hugging Face en sus servidores (no se baja nada a la laptop). Subir el paquete la primera vez
gasta unos 70 MB de datos; cada actualización diaria, 1–2 MB (y nada si no cambió).

## Qué queda público y qué no

- **Por defecto, nada.** El dataset y el Space se crean privados: solo el dueño (con su sesión de Hugging Face o su
  token) ve la app, el código del Space y los datos. Un Space privado responde 404 a cualquier otra persona.
- **La app muestra la demanda real por área que publica el COES** (la capa silver y el registro en vivo), además de
  los pronósticos. Hacer público el Space (`--publico`) la deja a la vista de cualquiera, junto con el código. **Es una
  decisión del dueño**; este despliegue no la toma. El dataset puede seguir privado aunque el Space sea público.
- Para mostrar la app sin datos del COES, el Space puede correr sin dataset (`--sin-datos`): usa los datos de prueba
  sintéticos y lo dice en la web.
- El token con que el Space lee el dataset privado va como **secreto** del Space (no se ve en la configuración ni
  pasa a los duplicados). Lo ideal es un token de **solo lectura** (`HF_TOKEN_LECTURA`); si no se da, se usa el de
  escritura, y el script lo advierte. La variable `TPF_HF_DATASET` (el nombre del dataset) es visible si el Space es
  público.

## Publicar: los comandos

Desde la raíz del repo, con la carpeta de datos en `../tetouan-power-forecast/data` (o `TETOUAN_DATA`, o `--datos`):

```bash
# 1. Un token de tu cuenta PERSONAL con permiso de escritura: https://huggingface.co/settings/tokens
#    (New token → Write). Nunca el de una cuenta de trabajo: el script se niega con cip-itlicenses y cipotato*.
export HF_TOKEN=hf_...                 # en fish: set -x HF_TOKEN hf_...

# 2. (Recomendado) Otro token, de solo lectura, para que el Space lea el dataset privado
export HF_TOKEN_LECTURA=hf_...

# 3. Ensayo sin red: arma el paquete y muestra qué haría
uv run --no-project --with "huggingface_hub>=1.33,<2" python despliegue/publicar_hf.py USUARIO --dry-run

# 4. Publicar: dataset y Space privados, y espera a que el Space responda en /salud
uv run --no-project --with "huggingface_hub>=1.33,<2" python despliegue/publicar_hf.py USUARIO
```

Es idempotente: correrlo de nuevo solo sube lo que cambió (el paquete se arma en `~/.cache/curva-hf/paquete` y no se
recomprime si los originales no cambiaron); si solo cambiaron los datos, reinicia el Space para que los baje. No toca la
visibilidad de lo que ya existe salvo que se pida. Otras opciones: `--publico` / `--privado` (Space),
`--dataset-publico`, `--sin-datos`, `--solo-datos`, `--rotar-token` (vuelve a poner el secreto), `--no-esperar`;
`--help` las lista.

La app queda en `https://huggingface.co/spaces/USUARIO/curva` (con la sesión del dueño iniciada, por ser privada) y su
API en `https://USUARIO-curva.hf.space` (un Space privado pide el token: `curl -H "Authorization: Bearer $HF_TOKEN"
https://USUARIO-curva.hf.space/salud`).

## Actualización diaria

La corrida diaria en vivo (`experimentos/en_vivo/diario.sh`, en el cron) reescribe el registro en
`reportes/sein/en_vivo/`. `actualizar_hf.py` sube al dataset solo los archivos de ese registro que cambiaron desde la
última subida (guarda sus sha256 en `~/.cache/curva-hf/`; si nada cambió, no usa la red). El Space vuelve a pedirlos
cada 15 minutos (`TPF_RECARGA_MIN`) y la API los relee sin reiniciar: la corrida de las 10:00 se ve en la app antes de
las 10:20. `--reiniciar` además reinicia el Space (si se apagó la recarga con `TPF_RECARGA_MIN=0`).

**No está instalado en el cron.** Para sumarlo después de la copia al Drive, en la misma línea del cron (con el
Python de `~/.cache/tpf-vivo/venv`, que ya trae `huggingface_hub`; el token se lee de donde lo tengas guardado, aquí
de una variable universal de fish):

```cron
*/30 9-17 * * * /home/rody/Code/lab/courses/tpf-vivo/experimentos/en_vivo/diario.sh >> /home/rody/Code/lab/courses/tetouan-power-forecast/data/reportes/sein/en_vivo/cron.log 2>&1 && { /home/rody/.cache/tpf-vivo/subir_drive.sh >> /home/rody/Code/lab/courses/tetouan-power-forecast/data/reportes/sein/en_vivo/cron.log 2>&1; HF_TOKEN="$(fish -c 'echo -n $HF_ROSEWT')" /home/rody/.cache/tpf-vivo/venv/bin/python /home/rody/Code/lab/courses/tpf-vivo/despliegue/actualizar_hf.py rosewt >> /home/rody/Code/lab/courses/tetouan-power-forecast/data/reportes/sein/en_vivo/cron.log 2>&1; }
```

(El script tiene que estar en `tpf-vivo`, así que esto va después de fusionar este cambio y actualizar esa copia.)
Escribe una línea por corrida en el log (`INFO hf: ...` o `ERROR hf: ...`), como la copia al Drive.

## Ver los logs, apagar, reiniciar

- **Logs:** en la página del Space, «Logs» (o `https://huggingface.co/spaces/USUARIO/curva?logs=container`; los del
  build, `?logs=build`). Desde Python:

  ```bash
  uv run --no-project --with "huggingface_hub>=1.33,<2" python -c "import os; from huggingface_hub import HfApi; \
    print(''.join(HfApi(token=os.environ['HF_TOKEN']).fetch_space_logs('USUARIO/curva')))"   # build=True: el build
  ```

  Al arrancar se ve `Datos listos en /home/user/datos, bajados desde el dataset USUARIO/curva-datos`; la recarga cada
  15 min solo escribe si falla. Si los datos no bajan, la web muestra un aviso arriba y `/salud` trae el motivo.
- **Apagar:** «Settings» → «Pause Space» (no consume nada y nadie lo puede despertar salvo el dueño), o
  `HfApi(token=...).pause_space("USUARIO/curva")`. Volver a prenderlo: `restart_space`. Borrarlo: «Settings» → «Delete».
- **Reiniciar** (vuelve a bajar todo el dataset): `HfApi(token=...).restart_space("USUARIO/curva")`.

## Límites del plan gratuito y plan B

Lo que dice la documentación oficial (revisada el 21 de noviembre de 2026):

- **Crear un Space Docker o Gradio pide plan de pago.** «Static Spaces are free for everyone. Gradio and Docker Spaces
  run on compute and require a paid plan to create: PRO for personal accounts» ([Spaces Overview][overview]). PRO
  cuesta 9 USD al mes ([pricing][pricing]). Según el foro, el cambio llegó en julio de 2026 ([foro][foro-docker]) y
  algunas cuentas antiguas conservan cupo para 2 Spaces Docker en CPU básico ([foro][foro-cupo]). Con la cuenta
  `rosewt` se comprobó: la API respondió `402 Payment Required` al crear el Space.
- **El hardware CPU básico no cobra por hora**: 2 vCPU, 16 GB de RAM y 50 GB de disco no persistente
  ([Spaces Overview][overview]). A la app le sobran (usa ~1.25 GB).
- **Se duerme sin uso**: «On free hardware, your Space will "go to sleep" and stop executing after a period of time if
  unused» ([Spaces Overview][overview]); la documentación ya no dice cuánto (antes eran 48 h). Al despertar vuelve a
  bajar el dataset (unos segundos dentro de Hugging Face) y a cargar los modelos.
- **Disco no persistente**: lo escrito se pierde al reiniciar ([Docker Spaces][docker]); por eso los datos viven en el
  dataset y se bajan en cada arranque.
- **Puerto y usuario**: el puerto por defecto es 7860 (`app_port`) y el contenedor corre con el uid 1000
  ([Docker Spaces][docker]); el arranque puede tardar hasta 30 min por defecto (`startup_duration_timeout`,
  [referencia][config]).
- Los **datasets** sí siguen sin costo en cuentas gratuitas (privados, con su cuota de almacenamiento).

### Si Spaces no deja crear el Space

`publicar_hf.py` lo detecta y se detiene con un mensaje claro **después de subir el dataset**, que queda listo. Con el
dataset en el Hub, la misma imagen corre en cualquier lugar con Docker: lee `PORT`, `TPF_HF_DATASET` y `HF_TOKEN`.

1. **PRO (9 USD/mes)** o añadir facturación a la cuenta, que es lo que pide la interfaz para desbloquear los Spaces
   Docker; luego se vuelve a correr `publicar_hf.py` tal cual. Es el camino sin cambios.
2. **Google Cloud Run** (sin costo dentro de la capa gratuita: 2 millones de pedidos, 180 000 vCPU-s y 360 000 GB-s
   al mes; pide una cuenta de facturación, [Google Cloud Free Tier][gcp]). Escala a cero cuando no hay visitas (cada
   arranque en frío baja el dataset y carga los modelos, unos 30–60 s). Con la imagen construida en Cloud Build (no en
   la laptop): `gcloud run deploy curva --source . --memory 2Gi --set-env-vars TPF_HF_DATASET=USUARIO/curva-datos
   --set-secrets HF_TOKEN=...`.
3. **Una VM gratuita con 2 GB de RAM o más** (por ejemplo Oracle Cloud Always Free) con `docker run -p 80:7860 -e
   TPF_HF_DATASET=... -e HF_TOKEN=... curva`. No sirven los planes gratuitos de 512 MB (Render, Koyeb): la app ocupa
   ~1.25 GB.
4. **Sin publicar en internet**: la laptop con `app/levantar.sh` y un túnel (Tailscale Funnel o Cloudflare Tunnel).
   Gratis, pero cada visita gasta los datos móviles del dueño y depende de que la laptop esté prendida.

## Probar sin red

El mismo arranque que en el Space, con una carpeta local en lugar del dataset (es lo que se probó antes de publicar):

```bash
python -m despliegue.paquete ../tetouan-power-forecast/data /tmp/curva-paquete     # 68 MB, ~1 min la primera vez
TPF_HF_DATASET=/tmp/curva-paquete TPF_CACHE=/tmp/curva-cache PORT=7860 \
  PYTHONPATH=src:. uv run --no-sync --with fastapi --with uvicorn --with xgboost --with holidays \
  python -m despliegue.arranque                                                      # http://localhost:7860/
TPF_HF_DATASET=/no/existe PORT=7860 ... python -m despliegue.arranque                # cae a datos de prueba, con aviso
```

`docker build --check .` valida el `Dockerfile` sin bajar capas. `pytest tests/test_despliegue.py` cubre el paquete,
el arranque (descarga simulada, fallas, recarga del registro en vivo) y los scripts en `--dry-run`, sin red.

## Variables del contenedor

| Variable | Por defecto | Qué hace |
|---|---|---|
| `PORT` | `7860` | Puerto de uvicorn. |
| `TPF_HF_DATASET` | — | Dataset con el paquete (`USUARIO/curva-datos`) o una carpeta local. Sin ella: `TETOUAN_DATA` montada o datos de prueba. |
| `HF_TOKEN` | — | Secreto: lee el dataset privado. Solo se usa el de la variable, nunca uno guardado en disco. |
| `TPF_CACHE` | `~/datos` | Dónde se bajan los datos (pasa a ser `TETOUAN_DATA`). |
| `TPF_RECARGA_MIN` | `15` | Minutos entre recargas del registro en vivo; `0` las apaga. |
| `TPF_SI_FALLA` | `prueba` | Si el modelo real no carga, arranca con el de prueba y lo avisa (lo pone el arranque). |
| `TPF_CALENTAR` | `1` | Al abrir el puerto, pide el resumen, «Ahora», «Confianza» y el diagnóstico de las tres áreas para que el primer visitante no espere sus cálculos; `0` lo apaga. |

[overview]: https://huggingface.co/docs/hub/spaces-overview
[docker]: https://huggingface.co/docs/hub/spaces-sdks-docker
[config]: https://huggingface.co/docs/hub/spaces-config-reference
[pricing]: https://huggingface.co/pricing
[foro-docker]: https://discuss.huggingface.co/t/docker-sdk-now-marked-as-paid-when-creating-a-new-space/177580
[foro-cupo]: https://discuss.huggingface.co/t/future-of-free-docker-spaces-quota-for-older-accounts/180780
[gcp]: https://docs.cloud.google.com/free/docs/free-cloud-features
