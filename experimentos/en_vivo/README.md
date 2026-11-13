# Pronóstico en vivo (SEIN, por área)

Cada mañana el COES publica la demanda por área del día anterior en el anexo diario del IEOD (`AnexoA_DDMM.xlsx`,
hoja `DEMANDA_AREAS`), hacia las 09:45. Es la misma fuente y la misma definición que la capa silver: el anexo del
22 de octubre de 2026 coincide periodo a periodo con ella, y el empalme del 23 no tiene salto. Con eso, la tubería
de `tetouan_power_forecast.en_vivo` pronostica el día de hoy y lo deja registrado antes de que exista su real.

## Qué es en vivo y qué no

| | ¿En vivo? | Por qué |
|---|---|---|
| **24 h** | Sí | Con los datos hasta el fin de ayer (D), se pronostica desde cada uno de los 48 orígenes de D el periodo 24 h después: el perfil completo de hoy (D+1). Se registra con el sello UTC de la corrida y su real llega mañana. |
| **1 h** | No | Cada origen necesita la demanda de una hora antes del objetivo, y esa demanda llega al día siguiente, en el mismo anexo que trae el real. El 1 h de ayer se emite igual para seguirlo, siempre como **reconstruido**. |

Cada fila del registro lleva un `tipo`, calculado con su sello de emisión:

- `ex_ante_estricto`: al emitirse, el periodo objetivo todavía no empezaba.
- `en_vivo`: el periodo ya había empezado, pero su día no había terminado, así que el COES no podía haber publicado
  su real. (Es una cota conservadora: lo emitido entre el fin del día y la publicación también sería en vivo.)
- `reconstruido`: se emitió después. Es el relleno inicial (del 23 de octubre al día anterior a la primera corrida),
  todo el 1 h y cualquier corrida atrasada. Usa solo los datos hasta su origen, pero no se registró antes del real.

Como el anexo llega hacia las 10:00, en el perfil de hoy las medias horas de la madrugada son `en_vivo` y las del
resto del día `ex_ante_estricto`. La evaluación separa los dos grupos del reconstruido.

## Cómo correrlo

```bash
experimentos/en_vivo/entorno.sh RUTA/chronos2ftcal.tar   # una vez: venv y pesos en ~/.cache/tpf-vivo
experimentos/en_vivo/diario.sh                           # ingesta → pronóstico → evaluación
experimentos/en_vivo/diario.sh relleno                   # lo mismo, sin emitir el día de hoy
experimentos/en_vivo/diario.sh verificar                 # compara la inferencia local con la guardada de Colab
```

`diario.sh` usa `TETOUAN_DATA` (por defecto, `../tetouan-power-forecast/data` junto al repo) y el Python de
`~/.cache/tpf-vivo/venv` (o `TPF_VIVO_PYTHON`). Es idempotente: si el anexo de ayer ya entró y el perfil de hoy ya
se emitió, no pide nada al COES, no carga el modelo y no agrega filas. Mide su duración y la deja en
`corridas.jsonl` y en `diario.log`.

Códigos de salida: `0` listo; `75` el COES todavía no publica el anexo de ayer, u otra corrida está en curso
(reintentar más tarde); `3` un anexo no pasa las validaciones (no se emite nada: hay que mirarlo); `1` otro error.

### Programarlo (no está instalado: lo decide el dueño)

Con cron, cada 30 minutos de 09:00 a 17:30 en hora de Lima. Las corridas antes de la publicación salen con 75 y
cuestan tres listados del portal (unos 30 kB); después de la primera que funciona, el resto del día no hace nada:

```cron
CRON_TZ=America/Lima
*/30 9-17 * * * /RUTA/AL/REPO/experimentos/en_vivo/diario.sh >> /RUTA/A/DATOS/reportes/sein/en_vivo/cron.log 2>&1
```

O con un timer de systemd del usuario (`systemctl --user enable --now tpf-vivo.timer`):

```ini
# ~/.config/systemd/user/tpf-vivo.service
[Service]
Type=oneshot
ExecStart=/RUTA/AL/REPO/experimentos/en_vivo/diario.sh
SuccessExitStatus=75

# ~/.config/systemd/user/tpf-vivo.timer
[Timer]
OnCalendar=*-*-* 09..17:00,30:00 America/Lima
Persistent=true

[Install]
WantedBy=timers.target
```

Para subir las capas al Drive después de cada corrida (mismas rutas que en el disco):

```bash
d="$TETOUAN_DATA"; r=gdrive:datalake/tetouan-power-forecast
rclone copy "$d/coes/bronze/ieod_diario" "$r/coes/bronze/ieod_diario"
rclone copyto "$d/coes/silver/demanda_areas_en_vivo.parquet" "$r/coes/silver/demanda_areas_en_vivo.parquet"
rclone copy "$d/reportes/sein/en_vivo" "$r/reportes/sein/en_vivo" --exclude ".corrida.lock"
```

## Qué hace cada paso

1. **Ingesta.** Baja los anexos que falten desde el último día de la serie hasta ayer: pocas peticiones (listado
   del año, del mes y del día, y la descarga de ~1.2 MB), espaciadas 3 s y con los reintentos de `coes._pedir`. Los
   lee con `coes.leer_demanda_areas`, el lector que armó la silver, y valida: los 48 periodos, sin vacíos, Norte +
   Centro + Sur = SEIN (±1 MW), que el día empiece justo después del último dato y que el cambio de 30 minutos en el
   empalme caiga dentro de lo visto a esa hora en los dos últimos años. Si algo falla, no agrega ni emite nada.
   Guarda el Excel tal cual en `coes/bronze/ieod_diario/AAAA-MM-DD/` y lo agrega a
   `coes/silver/demanda_areas_en_vivo.parquet`; la silver histórica no se toca. Cuando entra un día nuevo vuelve a
   mirar los listados de los dos anteriores: si el COES corrigió un anexo (cambian su tamaño u observaciones), baja
   la versión nueva, la guarda aparte con su sha256 y corrige el real; lo ya emitido no cambia.
2. **Pronóstico.** Chronos-2 ajustado con feriados (`chronos2ftcal`), en CPU, con la inferencia de
   `experimentos/fundacionales/chronos2_variantes.py`: 2048 periodos de contexto, el feriado de Perú como covariable
   pasada y futura (el rango de años sale de las fechas) y los cuantiles 10, 50 y 90 %. Emite lo que falte en el
   registro: el 24 h del día siguiente al último dato y el 1 h del último día. Cada fila guarda el modelo, el sha256
   de los pesos, `emitido_en`, `datos_hasta`, el sha256 del anexo usado y el commit del código.
   `verificar` reproduce los pronósticos guardados de Colab (`reportes/sein/fundacionales/chronos2ftcal_c2048.parquet`)
   con una diferencia máxima de 0.0005 MW.
3. **Evaluación.** Cruza el registro con el real que ya llegó: `seguimiento.parquet` (error de cada periodo, si cayó
   dentro del rango y las referencias) y `resumen.parquet` (MAE, sesgo y cobertura por día y acumulados, por tipo,
   frente a la mejor referencia ingenua en esas mismas filas: ayer o la semana pasada a 24 h; también el último dato
   a 1 h). Se rehacen en cada corrida.

La app lo muestra en `GET /en-vivo/{area}` y en la sección «En vivo» de la vista de cada área.

| Archivo (dentro de `TETOUAN_DATA`) | Qué es |
|---|---|
| `coes/bronze/ieod_diario/AAAA-MM-DD/AnexoA_DDMM.xlsx` | El anexo tal cual; una corrección del COES va aparte con su sha256 en el nombre |
| `coes/bronze/ieod_diario/procedencia.jsonl` | Una línea por descarga: ruta, sha256, firma del listado, hora y salto del empalme |
| `coes/silver/demanda_areas_en_vivo.parquet` | La demanda cada 30 minutos desde el 23 de octubre de 2026, con el sha256 de su anexo |
| `reportes/sein/en_vivo/pronosticos.parquet` | El registro, que solo crece |
| `reportes/sein/en_vivo/seguimiento.parquet`, `resumen.parquet` | La evaluación |
| `reportes/sein/en_vivo/corridas.jsonl`, `diario.log` | Una línea por corrida y su detalle |

## El combinado, después

El combinado de la app (`peso · Chronos-2 ajustado + (1 − peso) · híbrido`) necesita los pesos de Simons-297M
(1.19 GB), que todavía no están en esta máquina. Para sumarlo basta una clase con `nombre`, `version` y
`pronosticar(demanda, origenes)` que devuelva el mismo formato que `ChronosAjustado` (una fila por origen y área con
`pred_2`, `q10_2`, `q90_2`, `pred_48`, `q10_48` y `q90_48`, como los parquet de `experimentos/fundacionales`):
Simons en el mismo formato, el XGBoost híbrido con `_variables_fundacionales` de `app/backend/pronosticador_hibrido.py`
y la mezcla con `combinado.json`. El registro lo separa por `modelo` y `version_pesos`, así que convive con lo ya
emitido; su primer tramo también sería reconstruido.

## Lo que falta o no está verificado

- La hora de publicación del anexo se midió un solo día; los fines de semana largos y feriados pueden atrasarla (el
  del sábado 31 de octubre figura publicado el lunes 2). Si un día falta, la ingesta se detiene ahí: la serie no
  puede tener huecos y no se interpola.
- No se compara el SEIN del anexo con el total del tiempo real del portal (debería quedar 50 a 130 MW por debajo).
- Los días no laborables que decreta el gobierno sobre la marcha no están en `holidays`.
- No hay alerta si el portal deja de responder: solo el código de salida y el log.
