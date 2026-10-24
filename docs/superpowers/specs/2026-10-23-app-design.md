# App del pronóstico de demanda por área del SEIN: diseño

Fecha: 2026-10-23. Estado: borrador para revisión del grupo.
Acompaña a la [spec del proyecto](2026-10-23-demanda-sein-areas-design.md).

## 1. Objetivo

Una app HTML sencilla, como pide el enunciado del TB1 ("inputs del usuario, predicción del modelo y gráficos
explicativos"), que se use desde el celular y que se pueda mostrar en la exposición de la semana 15. Tiene que
responder tres preguntas:

1. **¿Cuánta demanda viene en la próxima hora en cada área?** El pronóstico frente a lo que pasó y frente a la mejor
   referencia ingenua.
2. **¿Qué pasa si…?** Más calor, El Niño encendido o apagado, una falla en curso: cómo cambia el pronóstico.
3. **¿Cuándo falla el modelo?** El error por régimen (normal, El Niño, red golpeada, fallas) y cuánto ayudan las
   variables exógenas.

## 2. Lo ya decidido (no se reabre aquí)

- **Diseño y UX tomados de Wachi** (`R0SEWT/wachi`, `web/`) **y del visor de concurrente** (`R0SEWT/concurrente`,
  `tp/app/`). No se copia el código: se toma el lenguaje visual y los patrones (§4).
- **PWA estática:** HTML, CSS y JavaScript sin framework, como Wachi. Sin backend en este corte: los datos vienen
  **precalculados** por el notebook 02 en archivos JSON.
- **Español, en lenguaje llano:** MW y "horas" en vez de jerga, como el texto de beneficio de Wachi ("pasa N cuadras
  menos junto a robos registrados").

## 3. Usuarios y escenario de uso

| Quién | Qué necesita |
|---|---|
| Profesora y jurado (exposición) | Ver en 2 minutos el problema, el modelo y su evidencia; tocar la app en vivo |
| Operador de un área (usuario figurado) | Mirar la próxima hora de su área, saber si el sistema está en un régimen raro y cuánto confiar en el pronóstico |
| El grupo | Explorar errores y escenarios mientras escribe el paper |

## 4. Lenguaje visual (de Wachi y del visor)

| Patrón | De dónde sale | Cómo se usa aquí |
|---|---|---|
| **Pensada para el celular**, con modo oscuro por defecto ("pantalla discreta") y modo claro | Wachi: `body.mode-light`, tokens en `:root` | Los mismos tokens: `--bg-app`, `--bg-surface`, `--text-main`, `--text-muted` y radios de 8, 14 y 20 px |
| **Tipografía:** Plus Jakarta Sans para el texto y JetBrains Mono para las cifras | Los dos | Los MW y los porcentajes siempre en mono, con cifras tabulares |
| **Paleta de Bang Wong**, legible para daltónicos | El visor | Norte `#E69F00`, Centro `#0072B2`, Sur `#009E73`; el pronóstico en `#56B4E9`, la referencia en `#CC79A7`; el dato real en el color del texto |
| **Dos tarjetas que se comparan** | Wachi: Rápida frente a Tranquila | Pronóstico frente a mejor referencia, con la diferencia en una frase: "el modelo se equivocó 42 MW menos que 'ayer a la misma hora'" |
| **Barra superior con chips** (guía, ficha técnica, leyenda) | El visor: `hud-top`, `chip-btn` | Igual, más un chip con el régimen de El Niño |
| **Hoja inferior con pestañas** | El visor: "Consejo en la calle" frente a "Diagnóstico ODS 11" | Pestañas "Operación" y "Diagnóstico" |
| **Botones de momentos del día, laborable frente a fin de semana, reproducir 24 h** | El visor: `moment-btn`, `toggle-btn`, `play-btn` | Para recorrer el día elegido |
| **"Sin datos" es un indicador, no un valor** | Wachi, ADR 010: tramos con pocos datos punteados | Los huecos del COES y los periodos con dato preliminar se pintan punteados y se explican en la ficha técnica |
| **Paneles colapsables y botón para restaurarlos** | El visor | En el celular, para ver el mapa o el gráfico completo |

## 5. Pantallas

1. **Inicio:**
   - mapa del Perú con las tres áreas, cada una con su color;
   - un chip de régimen arriba ("El Niño Costero extraordinario · ICEN 3.98, agosto");
   - tres botones rápidos, uno por área.

   Al tocar un área se abre su detalle.
2. **Detalle del área, pestaña Operación:**
   - selector de fecha (dentro de la prueba de 2026) y de hora;
   - las dos tarjetas: el pronóstico frente a la mejor referencia, en MW y con el error de ese momento;
   - la curva del día: real, pronóstico y referencia, con los huecos punteados;
   - botones de momentos del día y reproducción de 24 h.
3. **¿Y si…?** Dentro del detalle:
   - controles de la temperatura (−2, 0, +2 y +4 °C sobre la observada), de El Niño (observado o neutro) y de la
     falla en curso (observada o ninguna);
   - la curva y las tarjetas se actualizan, con una frase del cambio en la hora de mayor demanda.

   Son los "inputs del usuario" del enunciado.
4. **Detalle del área, pestaña Diagnóstico:**
   - MAE por régimen, frente a la mejor referencia;
   - la ablación M0 a M4 con su intervalo (cuánto ayudan las exógenas);
   - las 10 variables más importantes;
   - real contra predicho y la distribución de los residuos, que son el equivalente en regresión de la matriz de
     confusión que menciona el enunciado.
5. **Ficha técnica (modal):**
   - fuentes, licencias y atribuciones (COES, ERA5 de Copernicus vía Open-Meteo con CC BY 4.0, IGP/ENFEN, NOAA,
     Osinergmin con ODC-By);
   - fechas de corte de cada fuente y rezagos;
   - qué no cubre el modelo;
   - enlace al repo y al paper.

## 6. Datos que consume (contrato)

El notebook 02 escribe los archivos en `app/data/`. La app no calcula nada que no esté en ellos.

| Archivo | Contenido | Tamaño objetivo |
|---|---|---|
| `resumen.json` | Fechas de corte, régimen de El Niño por mes, métricas de la prueba por área, nombre del modelo, versión de los datos | < 20 KB |
| `prueba_<area>.json` | Para cada periodo de 30 min de 2026: real, pronóstico, mejor referencia y marca de hueco o dato preliminar | < 600 KB por área (arreglos en columnas, no objetos) |
| `escenarios.json` | 12 días representativos por área (normales, con Niño, con falla, feriados) × 48 periodos × la grilla de temperatura, El Niño y falla | < 300 KB |
| `diagnostico.json` | MAE por régimen, ablación con intervalos, importancias, muestra de real contra predicho y residuos | < 100 KB |
| `areas.geojson` | Departamentos simplificados (Natural Earth admin-1, dominio público) con su área del COES | < 150 KB |

Con datos precalculados, la app no necesita servidor ni sufre problemas de CORS con el COES. Para pronósticos en
vivo hay dos caminos, que **quedan fuera de este corte**: exportar el modelo a ONNX y correrlo en el navegador, o un
backend como el de Wachi (FastAPI en un host propio detrás de Tailscale Funnel).

## 7. Estructura

```
app/
  index.html, app.js, style.css   sin framework; los gráficos en SVG propio o con una librería chica fijada por versión
  sw.js, manifest.json, icons/    PWA instalable que funciona sin conexión con los datos ya cargados
  data/                           lo genera el notebook 02 (§6)
```

El mapa es un SVG dibujado desde el GeoJSON: sin teselas ni servidor de mapas, así funciona sin conexión y pesa
poco.

## 8. Calidad

- **Celular primero:** se prueba a 375 px de ancho, sin desplazamiento horizontal.
- **Accesibilidad:**
  - contraste AA;
  - `aria-label` en los botones de ícono;
  - la paleta de Wong;
  - el color nunca es la única señal: la referencia va punteada y el pronóstico, continuo.
- **Peso:** menos de 2 MB en la primera carga, y los datos de un área se cargan solo al abrirla.
- **Verificación:**
  - abrir en un celular real y en el panel del navegador;
  - una prueba que valide los JSON contra el contrato de §6 en el CI.

## 9. Despliegue

Netlify, como Wachi, en un subdominio de `rosewt.dev` (§10, decisión 1). La app es estática, así que también sirve
GitHub Pages desde el repo, sin cuentas nuevas.

## 10. Decisiones abiertas

1. **Dónde publicarla:** un subdominio de `rosewt.dev` en Netlify o GitHub Pages.
2. **Librería de gráficos:** SVG propio, que pesa menos y da más control, o una chica como uPlot, que es más rápida
   de armar.
3. **Los días representativos** de `escenarios.json`: elegirlos a mano o por regla (por ejemplo, el día de mayor
   error de cada régimen).
4. **Nombre de la app** para la exposición.
