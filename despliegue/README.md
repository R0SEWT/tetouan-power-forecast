# Despliegue de Curva

**Publicada en Azure App Service: <https://curva-sein.azurewebsites.net>** (ver [Azure App Service](#azure-app-service-publicada)).

La app (la API FastAPI, que sirve también la web en su mismo origen) no lleva los datos: viven en un **dataset** del
Hub de Hugging Face, y la app los baja al arrancar. El mismo arranque sirve para Azure App Service (código + Oryx) y
para un **Space Docker** de Hugging Face (el `Dockerfile`; el resto de este documento, desde
[Hugging Face Spaces](#hugging-face-spaces-estado-21-de-noviembre-de-2026)).

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
| `WEBSITES_CONTAINER_START_TIME_LIMIT` | `900` | 15 min para arrancar (por defecto 230 s): extraer el entorno, bajar datos y cargar modelos. |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Que Oryx instale `requirements.txt`. |
| Comprobación de salud | `/salud` | App Service la pide cada minuto. |
| Logs del contenedor | `filesystem` | Para leerlos con `--logs` o en el portal. |
| `PORT` | (lo pone App Service: 8000) | El arranque lo lee; no hace falta fijarlo. |

Todo va en ASCII y el script lo **lee de vuelta** después de aplicarlo: si algo no quedó (por ejemplo, una tilde
dañada en el comando de inicio), se detiene y dice qué. Solo escribe lo que difiere: cada cambio de configuración
reinicia la app, y en B1 un reinicio así no cabe en memoria (ver «Mediciones»).

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
- **La B1 alcanza, pero justa.** Arranca y sirve todo sin errores ni avisos, y lo ya calculado responde en menos de
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
- **Recomendación: B2 al menos para la exposición** (29.93 USD/mes, ~1 USD por día): `python
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
