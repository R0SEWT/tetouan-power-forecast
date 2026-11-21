# Curva en Hugging Face Spaces

La app (la API FastAPI, que sirve también la web en su mismo origen) corre en un **Space Docker** de Hugging Face.
Los datos no van en la imagen ni en el repo del Space: viven en un **dataset** del Hub, y el contenedor los baja al
arrancar. Los dos repos son **privados** hasta que el dueño decida otra cosa.

```text
dataset USUARIO/curva-datos (privado, 68 MB) ──descarga al arrancar──▶ Space USUARIO/curva (Docker, CPU básico)
        ▲                                                                   │  python -m despliegue.arranque
        └── actualizar_hf.py: el registro en vivo de cada mañana            └▶ uvicorn en :7860 → /salud, la web
```

## Estado (21 de noviembre de 2026)

- **Dataset publicado:** [`rosewt/curva-datos`](https://huggingface.co/datasets/rosewt/curva-datos), privado, 68.1 MB
  (24 archivos; los sha256 del Hub coinciden con `MANIFIESTO.json`). Se probó desde la laptop la descarga del registro
  en vivo con el token (2.5 s) y que sin token no se puede leer.
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

[overview]: https://huggingface.co/docs/hub/spaces-overview
[docker]: https://huggingface.co/docs/hub/spaces-sdks-docker
[config]: https://huggingface.co/docs/hub/spaces-config-reference
[pricing]: https://huggingface.co/pricing
[foro-docker]: https://discuss.huggingface.co/t/docker-sdk-now-marked-as-paid-when-creating-a-new-space/177580
[foro-cupo]: https://discuss.huggingface.co/t/future-of-free-docker-spaces-quota-for-older-accounts/180780
[gcp]: https://docs.cloud.google.com/free/docs/free-cloud-features
