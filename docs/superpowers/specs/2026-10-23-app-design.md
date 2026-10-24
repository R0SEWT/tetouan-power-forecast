# App del pronóstico de demanda por área del SEIN: diseño

Fecha: 2026-10-24 (v2, con la revisión de la v1 del 23-oct). Estado: borrador para revisión del grupo.
Acompaña a la [spec del proyecto](2026-10-23-demanda-sein-areas-design.md).

## 1. Objetivo

Una app propia, usable desde el celular, que **ejecuta el modelo** y responde tres preguntas:

1. **¿Cuánta demanda viene en cada área?** El pronóstico a 1 h y a 24 h, frente a lo que pasó y a la mejor referencia.
2. **¿Qué pasa si mañana…?** Más calor, El Niño encendido o apagado, una falla: escenarios a 24 h, bajo el supuesto
   de colaboración entre el COES y ENFEN (§2 de la spec del proyecto).
3. **¿Cuándo falla el modelo y qué lo arregla?** Error por régimen, aporte de las exógenas y efecto de reentrenar.

## 2. Lo ya decidido (no se reabre aquí)

- **No es Streamlit.** La rúbrica lo nombra (criterio VI); el riesgo está aceptado a cambio de una app bien hecha.
  Lo que la rúbrica sí pide, y esta app cumple: ingresar datos o elegir escenarios, **ejecutar el modelo**, mostrar
  la predicción y gráficos de apoyo, con una interfaz clara y estable.
- **Backend FastAPI que carga el modelo y calcula las variables al vuelo.** Frontend estático, sin framework, como
  Wachi.
  - **Demo final:** en la 4060, detrás de Tailscale Funnel, con el mismo mecanismo que Wachi.
  - **Desarrollo:** en local, con datos de prueba.
- **Diseño y UX de Wachi** (`R0SEWT/wachi`, `web/`) **y del visor de concurrente** (`R0SEWT/concurrente`, `tp/app/`).
  Se toma el lenguaje visual y los patrones (§4), no el código.
- **Español llano:** MW y frases, no jerga.
- **La desarrollan agentes,** así que el contrato de la API (§6) y sus pruebas son la fuente de verdad.

## 3. Usuarios

| Quién | Qué necesita |
|---|---|
| Profesora y jurado | Ver en 2 minutos el problema, el modelo y su evidencia, y tocar la app en vivo |
| Operador de un área (figurado) | La próxima hora y el día siguiente de su área, si el sistema está en un régimen raro y cuánto confiar |
| Analista de ENFEN o del COES (figurado) | Probar escenarios de clima o de El Niño para mañana |

## 4. Lenguaje visual

| Patrón | De dónde sale | Cómo se usa aquí |
|---|---|---|
| **Pensada para el celular**, con modo oscuro por defecto y modo claro | Wachi: `body.mode-light`, tokens en `:root` | Los mismos tokens (`--bg-app`, `--bg-surface`, `--text-main`, `--text-muted`) y radios de 8, 14 y 20 px |
| **Plus Jakarta Sans** para el texto y **JetBrains Mono** para las cifras | Los dos | Los MW y los porcentajes siempre en mono, con cifras tabulares |
| **Paleta de Bang Wong** | El visor | Norte `#E69F00`, Centro `#0072B2`, Sur `#009E73`; pronóstico `#D55E00`, que no compite con el azul del Centro; referencia `#CC79A7`, punteada; el real, en el color del texto |
| **Dos tarjetas que se comparan** | Wachi: Rápida frente a Tranquila | Pronóstico frente a mejor referencia, con la diferencia en una frase ("se equivocó 42 MW menos que 'ayer a la misma hora'") |
| **Barra superior con chips** | El visor: `hud-top`, `chip-btn` | Guía, ficha técnica, leyenda y un chip con el régimen de El Niño |
| **Hoja inferior con pestañas** | El visor | "Operación", "Escenarios" y "Diagnóstico" |
| **Momentos del día, laborable o fin de semana, reproducir 24 h, deslizador de hora** | El visor: `moment-btn`, `toggle-btn`, `play-btn`, `input type=range` | Para recorrer el día |
| **"Sin datos" es un indicador** | Wachi, ADR 010 | Huecos y datos estimados del COES punteados y explicados |
| **Paneles colapsables** | El visor | Para ver el gráfico o el mapa completo |

## 5. Pantallas

1. **Inicio:**
   - mapa del Perú con las tres áreas, rotulado "aproximado", porque las áreas del COES no siguen exactamente los
     límites departamentales;
   - chip de régimen ("El Niño Costero extraordinario · ICEN 3.98, agosto");
   - tres botones rápidos, uno por área.
2. **Operación** (por área):
   - fecha y hora (2025 o 2026) y horizonte (1 h o 24 h);
   - variante: sin o con exógenas;
   - las dos tarjetas;
   - la curva del día, con huecos punteados;
   - momentos del día y reproducción.

   El backend calcula el pronóstico con el modelo en cada cambio.
3. **Escenarios** (por área, solo a 24 h):
   - temperatura pronosticada para mañana (−2, 0, +2 y +4 °C sobre la recibida de ENFEN);
   - El Niño observado o neutro;
   - falla en curso, sí o no.

   El backend vuelve a ejecutar el modelo y muestra el cambio en la hora de mayor demanda. **A 1 h no hay escenarios:**
   la pestaña muestra la **sensibilidad del modelo** (cómo cambia la salida al mover una variable, con las demás
   fijas) y explica por qué no es un escenario: a 1 h la demanda reciente ya contiene el clima del momento.
4. **Diagnóstico** (por área). Se calcula con el origen móvil de 2023 a 2025 más la prueba, porque 2026 casi no
   tiene régimen normal:
   - MAE por régimen frente a la mejor referencia;
   - la ablación con sus intervalos;
   - el experimento de adaptación (fijo o reentrenado, sin o con exógenas);
   - importancia de variables;
   - real contra predicho y distribución de los residuos, el equivalente en regresión de la matriz de confusión.
5. **Ficha técnica:**
   - fuentes y licencias (COES, sin licencia publicada; ERA5 de Copernicus vía Open-Meteo con CC BY 4.0; IGP/ENFEN;
     NOAA; Osinergmin con ODC-By);
   - fechas de corte y rezagos;
   - el supuesto de colaboración;
   - lo que no cubre el modelo;
   - enlaces al repo y al paper.

## 6. API (contrato)

| Método y ruta | Entrada | Salida |
|---|---|---|
| `GET /health` | — | Estado, versión del modelo, fecha de corte de los datos |
| `GET /areas` | — | Áreas, colores, GeoJSON aproximado y régimen de El Niño vigente |
| `POST /pronostico` | `area`, `fecha` (día), `horizonte` (2 o 48), `variante` (`M0` o `M3`) | Por cada periodo de 30 min del día: real, pronóstico, mejor referencia, indicador de hueco o dato estimado, y el error del día frente a la referencia |
| `POST /escenario` | Lo de `/pronostico` con `horizonte = 48`, más `delta_temp` (°C), `nino` (`observado` o `neutro`) y `falla` (bool) | La curva del escenario, la base y la diferencia en la hora de mayor demanda |
| `POST /sensibilidad` | `area`, `fecha_hora`, `horizonte = 2` y la variable | La curva de dependencia parcial con su banda |
| `GET /diagnostico/{area}` | — | MAE por régimen, ablación, adaptación, importancias y una muestra de real contra predicho y residuos |

- **El backend carga al arrancar** el modelo final (joblib) y el gold de 2025-2026 (parquet), desde el Drive o desde
  el dataset privado de HF. Calcula las variables con el mismo código del paquete, así que no hay duplicación.
- **Pruebas:** `pytest` con el `TestClient` de FastAPI, con un modelo y datos de prueba pequeños, en el CI del repo.
  Los agentes que hagan el frontend trabajan contra este contrato.

## 7. Estructura

```
app/
  api/            FastAPI: main.py, rutas, carga del modelo; usa src/<paquete> para las variables
  web/            index.html, app.js, style.css, sw.js, manifest.json, iconos
  tests/          contrato de la API con datos de prueba
  deploy/         unidad systemd --user y script de despliegue a la 4060 (como Wachi)
```

Los gráficos van con una librería chica fijada por versión (uPlot o Chart.js). El mapa, en SVG propio desde el
GeoJSON (Natural Earth admin-1, dominio público).

## 8. Calidad

- **Celular primero:** a 375 px de ancho, sin desplazamiento horizontal.
- **Accesibilidad:**
  - contraste AA;
  - `aria-label` en los botones de ícono;
  - el color nunca es la única señal: la referencia va punteada y el pronóstico, continuo.
- **Rendimiento:** respuesta de `/pronostico` en menos de 1 s en la 4060; primera carga del frontend en menos de 1 MB.
- **Verificación:** las pruebas del contrato en el CI, y la app abierta en un celular real y en el navegador.

## 9. Decisiones abiertas

1. **Dónde sirve el frontend:** desde el mismo FastAPI en la 4060 (un solo despliegue) o en GitHub Pages llamando a
   la API.
2. **Librería de gráficos:** uPlot o Chart.js.
3. **Nombre de la app** para la exposición.
