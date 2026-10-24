'use strict';

/* ==========================================================================
   Demanda del SEIN por área: frontend sin framework.
   Habla con el backend FastAPI según el contrato de app/backend/contrato.py.
   Gráficos en SVG propio, sin librerías.
   ========================================================================== */

// ---- Configuración ---------------------------------------------------------

// El backend se busca en el puerto 8000 del mismo host. Se puede cambiar con ?api=URL.
const API = (() => {
  const desdeUrl = new URLSearchParams(location.search).get('api');
  if (desdeUrl) return desdeUrl.replace(/\/+$/, '');
  if (location.protocol === 'file:' || !location.hostname) return 'http://localhost:8000';
  return `${location.protocol}//${location.hostname}:8000`;
})();

const FECHA_MIN = '2025-01-01';
const FECHA_MAX = '2026-10-31';
const ESCENARIO_BASE = Object.freeze({ delta_temp_c: 0, nino: 'observado', falla: 'observada' });

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const DIAS_CORTOS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];

const INFO_AREA = {
  norte: { letra: 'N', fg: '#000', desc: 'Costa norte: Piura, Chiclayo y Trujillo. Lluvias con El Niño y carga minera e industrial.' },
  centro: { letra: 'C', fg: '#fff', desc: 'Lima y el centro: Electroandes, minería e industria. El calor del verano pesa en Lima.' },
  sur: { letra: 'S', fg: '#000', desc: 'Dominada por la minería: Cerro Verde, Las Bambas y Southern. Responde poco al clima.' },
};

const NOMBRE_REF = {
  persistencia: 'la persistencia (el último dato)',
  ayer: '«ayer a la misma hora»',
  semana_pasada: '«la semana pasada a la misma hora»',
};
const TITULO_REF = { persistencia: 'Persistencia', ayer: 'Ayer, misma hora', semana_pasada: 'Semana pasada' };
const ESTADO_NINO = { neutro: 'neutro', debil: 'débil', moderado: 'moderado', fuerte: 'fuerte', extraordinario: 'extraordinario' };
const REGIMEN = {
  neutro: 'Neutro', debil: 'Niño débil', moderado: 'Niño moderado', fuerte: 'Niño fuerte',
  extraordinario: 'Niño extraordinario', falla_en_curso: 'Falla en curso', red_golpeada: 'Red golpeada',
};
const VARIANTE = {
  M0: 'M0 · demanda y calendario', M1: 'M1 · + clima', M2: 'M2 · + El Niño', M3: 'M3 · + fallas',
  M4: 'M4 · + SAIDI', M3_sin_clima: 'M3 sin clima', M3_sin_nino: 'M3 sin El Niño', M3_sin_fallas: 'M3 sin fallas',
};
const POLITICA = { fijo: 'Fijo', semanal: 'Semanal', alerta_enfen: 'Alerta ENFEN' };
const VARIABLE = { demanda_reciente: 'Demanda reciente', clima: 'Clima', nino: 'El Niño', fallas: 'Fallas', saidi: 'SAIDI' };
const CORTE = {
  entrenamiento_hasta: 'Entrenamiento hasta', validacion_hasta: 'Validación hasta', prueba_hasta: 'Prueba hasta',
  demanda: 'Demanda (COES)', clima: 'Clima (ERA5)', icen: 'ICEN (IGP y ENFEN)', nino12: 'Niño 1+2 (NOAA)',
  fallas: 'Fallas (COES)', saidi: 'SAIDI (Osinergmin)',
};
const MOMENTOS = [
  { txt: 'Madrugada', idx: 6 }, { txt: 'Mañana', idx: 18 }, { txt: 'Mediodía', idx: 25 },
  { txt: 'Tarde', idx: 32 }, { txt: 'Noche', idx: 40 },
];
const TEMPERATURAS = [-2, 0, 2, 4];

// ---- Estado ------------------------------------------------------------------

const S = {
  salud: null,
  areas: [],
  resumen: null,
  area: null,
  fecha: null,
  idx: 30,
  horizonte: '1h',
  variante: 'M3',
  tab: 'operacion',
  hojaAbierta: false,
  escenario: { ...ESCENARIO_BASE },
  sensVar: 'temperatura',
  serie: null,
  pron: null,
  diag: new Map(),
  turnos: { serie: 0, pron: 0, esc: 0, sens: 0, diag: 0 },
};

// ---- Utilidades ----------------------------------------------------------------

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// Coma de miles y punto decimal, como se escribe en Perú.
const nf0 = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const mw = (x) => (x == null || Number.isNaN(x) ? '—' : nf0.format(x));
const pct = (x) => `${nf1.format(x)} %`;

const idxAHora = (i) => `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 ? '30' : '00'}`;
const horaDe = (fechaHora) => fechaHora.slice(11, 16);
const origen = () => `${S.fecha}T${idxAHora(S.idx)}`;

function horaAIdx(texto) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(texto || '');
  if (!m) return null;
  const i = Number(m[1]) * 2 + (Number(m[2]) >= 30 ? 1 : 0);
  return i >= 0 && i < 48 ? i : null;
}

function partesFecha(iso) {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return { y, m, d, dow: new Date(Date.UTC(y, m - 1, d)).getUTCDay() };
}

function fechaCorta(iso) {
  const p = partesFecha(iso);
  return `${DIAS_CORTOS[p.dow]} ${p.d} ${MESES_CORTOS[p.m - 1]} ${p.y}`;
}

function fechaLarga(iso) {
  const p = partesFecha(iso);
  return `${DIAS[p.dow]} ${p.d} de ${MESES[p.m - 1]} de ${p.y}`;
}

function acotarFecha(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return null;
  if (iso < FECHA_MIN) return FECHA_MIN;
  return iso > FECHA_MAX ? FECHA_MAX : iso;
}

function ahoraEnLima() {
  try {
    const fecha = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima' }).format(new Date());
    const hora = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'America/Lima', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).format(new Date());
    return { fecha, idx: horaAIdx(hora) ?? 30 };
  } catch {
    return { fecha: new Date().toISOString().slice(0, 10), idx: 30 };
  }
}

function mae(real, otro) {
  let suma = 0;
  let n = 0;
  real.forEach((r, i) => {
    if (r != null && otro[i] != null) {
      suma += Math.abs(r - otro[i]);
      n += 1;
    }
  });
  return n ? suma / n : null;
}

function guardar(clave, valor) {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    /* sin almacenamiento: no pasa nada */
  }
}

function leer(clave) {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
}

// ---- API -------------------------------------------------------------------------

class ErrorApi extends Error {
  constructor(estado, mensaje) {
    super(mensaje);
    this.estado = estado;
  }
}

function mensajeDe(datos, estado) {
  const d = datos && datos.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((e) => e.msg || JSON.stringify(e)).join(' · ');
  return `Error ${estado}`;
}

async function api(ruta, cuerpo) {
  const opciones = cuerpo
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) }
    : undefined;
  let r;
  try {
    r = await fetch(API + ruta, opciones);
  } catch {
    throw new ErrorApi(0, 'sin conexión');
  }
  let datos = null;
  try {
    datos = await r.json();
  } catch {
    /* respuesta sin cuerpo JSON */
  }
  if (!r.ok) throw new ErrorApi(r.status, mensajeDe(datos, r.status));
  return datos;
}

function mostrarError(err) {
  const b = $('#bannerError');
  if (err.estado === 0) {
    b.innerHTML = `<strong>No hay conexión con el backend</strong> en <code>${esc(API)}</code>. `
      + 'Levántalo desde la raíz del repo con <code>uv run uvicorn app.backend.main:app --reload</code>.'
      + '<br><button class="btn" type="button" id="btnReintentar">Reintentar</button>';
    $('#btnReintentar').addEventListener('click', () => {
      b.hidden = true;
      iniciar();
    });
  } else {
    b.innerHTML = `<strong>El backend respondió con un error (${err.estado}).</strong> ${esc(err.message)}`;
  }
  b.hidden = false;
}

function limpiarError() {
  $('#bannerError').hidden = true;
}

// Los errores de conexión van al aviso general; los demás, al panel que los pidió.
function manejarError(err, panel) {
  if (err.estado === 0) {
    mostrarError(err);
    return;
  }
  if (panel) panel.innerHTML = `<p class="vacio">${esc(err.message)}</p>`;
}

// ---- Gráficos en SVG ------------------------------------------------------------------

let contadorGraficos = 0;

function pasoBonito(rango, n) {
  const crudo = rango / n;
  const mag = 10 ** Math.floor(Math.log10(crudo));
  return [1, 2, 2.5, 5, 10].map((f) => f * mag).find((p) => p >= crudo) || 10 * mag;
}

function marcas(lo, hi, n = 4) {
  const paso = pasoBonito(hi - lo || 1, n);
  const t = [];
  for (let v = Math.ceil(lo / paso) * paso; v <= hi + 1e-9; v += paso) t.push(Number(v.toFixed(10)));
  return t;
}

function tramos(banderas) {
  const t = [];
  if (!banderas) return t;
  let ini = null;
  banderas.forEach((b, i) => {
    if (b && ini == null) ini = i;
    if (!b && ini != null) {
      t.push([ini, i - 1]);
      ini = null;
    }
  });
  if (ini != null) t.push([ini, banderas.length - 1]);
  return t;
}

const pt = (X, Y, i, v) => `${X(i).toFixed(1)},${Y(v).toFixed(1)}`;

function rutaLinea(valores, X, Y) {
  let d = '';
  valores.forEach((v, i) => {
    if (v == null) return;
    const antes = i > 0 && valores[i - 1] != null;
    const despues = i < valores.length - 1 && valores[i + 1] != null;
    d += `${antes ? 'L' : 'M'}${pt(X, Y, i, v)}`;
    if (!antes && !despues) d += 'h0.01'; // punto aislado entre huecos
  });
  return d;
}

// Une los datos vecinos de cada hueco con una línea punteada gris: no es un dato.
function rutaPuentes(valores, X, Y) {
  let d = '';
  let ultimo = null;
  valores.forEach((v, i) => {
    if (v == null) return;
    if (ultimo != null && i - ultimo > 1) d += `M${pt(X, Y, ultimo, valores[ultimo])}L${pt(X, Y, i, v)}`;
    ultimo = i;
  });
  return d;
}

function rutaBanda(inf, sup, X, Y) {
  const ida = sup.map((v, i) => `${i ? 'L' : 'M'}${pt(X, Y, i, v)}`).join('');
  const vuelta = inf.map((v, i) => [i, v]).reverse().map(([i, v]) => `L${pt(X, Y, i, v)}`).join('');
  return `${ida}${vuelta}Z`;
}

function anchoDe(el) {
  return Math.max(260, Math.round(el.clientWidth || 320));
}

/**
 * Gráfico de líneas sobre un eje x de índices.
 * o.series: [{ clase, valores, nombre, banda: { inf, sup, clase }, puente, puntos }]
 * Se dibujan en orden; el globo de ayuda las lista en orden inverso.
 */
function graficoLineas(el, o) {
  el._dibujar = () => graficoLineas(el, o);
  const W = anchoDe(el);
  const H = o.alto || 220;
  const m = { l: 46, r: 10, t: o.marcador ? 20 : 10, b: 24 };
  const formatoY = o.formatoY || mw;
  const valores = [];
  o.series.forEach((s) => {
    s.valores.forEach((v) => v != null && valores.push(v));
    if (s.banda) valores.push(...s.banda.inf, ...s.banda.sup);
  });
  if (!valores.length) {
    el.innerHTML = '<p class="vacio">Sin datos para graficar.</p>';
    return;
  }
  let lo = Math.min(...valores);
  let hi = Math.max(...valores);
  const margen = (hi - lo) * 0.08 || Math.max(Math.abs(hi) * 0.02, 1);
  lo -= margen;
  hi += margen;
  const n = o.n;
  const ancho = W - m.l - m.r;
  const alto = H - m.t - m.b;
  const paso = n > 1 ? ancho / (n - 1) : ancho;
  const X = (i) => m.l + (n > 1 ? i * paso : ancho / 2);
  const Y = (v) => m.t + ((hi - v) * alto) / (hi - lo);
  const id = `g${++contadorGraficos}`;
  const ticks = marcas(lo, hi).filter((t) => t >= lo && t <= hi);

  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(o.aria || '')}"${o.alPulsar ? ' style="cursor:pointer"' : ''}>`;
  svg += `<defs><pattern id="${id}-trama" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" class="hueco-trama"/></pattern></defs>`;
  svg += `<g class="rejilla">${ticks.map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t).toFixed(1)}" y2="${Y(t).toFixed(1)}"/>`).join('')}</g>`;
  svg += '<g class="eje">';
  svg += ticks.map((t) => `<text x="${m.l - 6}" y="${(Y(t) + 3).toFixed(1)}" text-anchor="end">${esc(formatoY(t))}</text>`).join('');
  for (let i = 0; i < n; i += 1) {
    const t = o.etiquetaX ? o.etiquetaX(i) : null;
    if (t == null) continue;
    const ancla = i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle';
    svg += `<text x="${X(i).toFixed(1)}" y="${H - 6}" text-anchor="${ancla}">${esc(t)}</text>`;
  }
  svg += '</g>';

  tramos(o.huecos).forEach(([a, b]) => {
    const x0 = Math.max(m.l, X(a) - paso / 2);
    const x1 = Math.min(W - m.r, X(b) + paso / 2);
    svg += `<rect x="${x0.toFixed(1)}" y="${m.t}" width="${(x1 - x0).toFixed(1)}" height="${alto}" fill="url(#${id}-trama)" class="hueco-rect"/>`;
    if (x1 - x0 > 46) svg += `<text class="etiqueta" x="${((x0 + x1) / 2).toFixed(1)}" y="${m.t + 12}" text-anchor="middle">sin datos</text>`;
  });
  tramos(o.preliminar).forEach(([a, b]) => {
    const x0 = Math.max(m.l, X(a) - paso / 2);
    const x1 = Math.min(W - m.r, X(b) + paso / 2);
    svg += `<rect x="${x0.toFixed(1)}" y="${m.t + alto - 5}" width="${(x1 - x0).toFixed(1)}" height="5" class="prelim-rect"/>`;
    if (x1 - x0 > 60) svg += `<text class="etiqueta" x="${((x0 + x1) / 2).toFixed(1)}" y="${m.t + alto - 9}" text-anchor="middle">preliminar</text>`;
  });

  o.series.forEach((s) => {
    if (s.banda) svg += `<path class="${s.banda.clase}" d="${rutaBanda(s.banda.inf, s.banda.sup, X, Y)}"/>`;
  });
  o.series.forEach((s) => {
    if (s.puente) svg += `<path class="linea ln-puente" d="${rutaPuentes(s.valores, X, Y)}"/>`;
    svg += `<path class="linea ${s.clase}" d="${rutaLinea(s.valores, X, Y)}"/>`;
    if (s.puntos) {
      svg += s.valores.map((v, i) => (v == null ? '' : `<circle class="pt-pronostico" cx="${X(i).toFixed(1)}" cy="${Y(v).toFixed(1)}" r="3"/>`)).join('');
    }
  });

  if (o.marcador && o.marcador.i != null) {
    const x = X(o.marcador.i);
    const ancla = x < m.l + 24 ? 'start' : x > W - m.r - 24 ? 'end' : 'middle';
    svg += `<g class="marcador"><line x1="${x.toFixed(1)}" x2="${x.toFixed(1)}" y1="${m.t - 4}" y2="${m.t + alto}"/>`
      + `<text x="${x.toFixed(1)}" y="${m.t - 8}" text-anchor="${ancla}">${esc(o.marcador.txt)}</text></g>`;
  }
  svg += `<line class="guia" x1="0" x2="0" y1="${m.t}" y2="${m.t + alto}" visibility="hidden"/>`;
  svg += '</svg>';
  el.innerHTML = `${svg}<div class="chart-tip" hidden></div>`;

  const svgEl = $('svg', el);
  const guia = $('.guia', svgEl);
  const globo = $('.chart-tip', el);
  const indice = (ev) => {
    const r = svgEl.getBoundingClientRect();
    const x = ((ev.clientX - r.left) * W) / r.width;
    return Math.max(0, Math.min(n - 1, Math.round((x - m.l) / paso)));
  };
  svgEl.addEventListener('pointermove', (ev) => {
    const i = indice(ev);
    const x = X(i);
    guia.setAttribute('x1', x);
    guia.setAttribute('x2', x);
    guia.setAttribute('visibility', 'visible');
    const filas = [...o.series].reverse().filter((s) => s.nombre).map((s) => {
      const v = s.valores[i];
      return `<div class="fila"><span>${esc(s.nombre)}</span><span>${v == null ? 'sin dato' : esc(formatoY(v))}</span></div>`;
    });
    globo.innerHTML = `<b>${esc(o.etiquetaPunto ? o.etiquetaPunto(i) : i)}</b>${filas.join('')}`;
    globo.hidden = false;
    const r = svgEl.getBoundingClientRect();
    const px = (x * r.width) / W;
    const g = globo.offsetWidth;
    globo.style.left = `${px + 12 + g > r.width ? Math.max(0, px - g - 12) : px + 12}px`;
  });
  svgEl.addEventListener('pointerleave', () => {
    guia.setAttribute('visibility', 'hidden');
    globo.hidden = true;
  });
  if (o.alPulsar) svgEl.addEventListener('click', (ev) => o.alPulsar(indice(ev)));
}

/** Barras horizontales con el rótulo arriba. filas: [{ etiqueta, barras: [{ valor, clase, texto }] }] */
function graficoBarras(el, filas, o = {}) {
  el._dibujar = () => graficoBarras(el, filas, o);
  if (!filas.length) {
    el.innerHTML = '<p class="vacio">Sin datos.</p>';
    return;
  }
  const W = anchoDe(el);
  const valores = filas.flatMap((f) => f.barras.map((b) => b.valor));
  const min = Math.min(0, ...valores);
  const max = Math.max(0, ...valores);
  const m = { l: 2, r: 92 };
  const X = (v) => m.l + ((v - min) * (W - m.l - m.r)) / (max - min || 1);
  let y = 2;
  let cuerpo = '';
  filas.forEach((f) => {
    cuerpo += `<text class="rotulo" x="${m.l}" y="${y + 13}">${esc(f.etiqueta)}</text>`;
    y += 20;
    f.barras.forEach((b) => {
      const x0 = X(Math.min(0, b.valor));
      const x1 = X(Math.max(0, b.valor));
      cuerpo += `<rect class="${b.clase}" x="${x0.toFixed(1)}" y="${y + 0.75}" width="${Math.max(1.5, x1 - x0).toFixed(1)}" height="11" rx="3"/>`;
      cuerpo += `<text class="valor" x="${(Math.max(x1, X(0)) + 6).toFixed(1)}" y="${y + 10}">${esc(b.texto)}</text>`;
      y += 16;
    });
    y += 8;
  });
  if (min < 0) cuerpo += `<line class="linea-ref" x1="${X(0)}" x2="${X(0)}" y1="16" y2="${y - 6}"/>`;
  el.innerHTML = `<svg viewBox="0 0 ${W} ${y}" width="${W}" height="${y}" role="img" aria-label="${esc(o.aria || '')}">${cuerpo}</svg>`;
}

/** Puntos con bigotes (intervalos). filas: [{ etiqueta, valor, inf, sup, hueco }] */
function graficoPuntos(el, filas, o = {}) {
  el._dibujar = () => graficoPuntos(el, filas, o);
  if (!filas.length) {
    el.innerHTML = '<p class="vacio">Sin datos.</p>';
    return;
  }
  const W = anchoDe(el);
  const extremos = filas.flatMap((f) => [f.inf ?? f.valor, f.sup ?? f.valor]);
  if (o.ref) extremos.push(o.ref.valor);
  let lo = Math.min(...extremos);
  let hi = Math.max(...extremos);
  const margen = (hi - lo) * 0.12 || 1;
  lo -= margen;
  hi += margen;
  const m = { l: 8, r: 8 };
  const X = (v) => m.l + ((v - lo) * (W - m.l - m.r)) / (hi - lo);
  let y = 4;
  let cuerpo = '';
  filas.forEach((f) => {
    const ic = f.inf != null ? ` (${nf1.format(f.inf)}–${nf1.format(f.sup)})` : '';
    cuerpo += `<text class="rotulo" x="${m.l}" y="${y + 12}">${esc(f.etiqueta)}</text>`;
    cuerpo += `<text class="valor" x="${W - m.r}" y="${y + 12}" text-anchor="end">${esc(`${nf1.format(f.valor)} MW${ic}`)}</text>`;
    const yc = y + 26;
    if (o.ref) {
      const xr = X(o.ref.valor).toFixed(1);
      cuerpo += `<line class="linea-ref" x1="${xr}" x2="${xr}" y1="${yc - 10}" y2="${yc + 10}"/>`;
    }
    if (f.inf != null) {
      cuerpo += `<line class="bigote" x1="${X(f.inf).toFixed(1)}" x2="${X(f.sup).toFixed(1)}" y1="${yc}" y2="${yc}"/>`;
      cuerpo += `<line class="bigote" x1="${X(f.inf).toFixed(1)}" x2="${X(f.inf).toFixed(1)}" y1="${yc - 4}" y2="${yc + 4}"/>`;
      cuerpo += `<line class="bigote" x1="${X(f.sup).toFixed(1)}" x2="${X(f.sup).toFixed(1)}" y1="${yc - 4}" y2="${yc + 4}"/>`;
    }
    cuerpo += `<circle class="punto${f.hueco ? ' vacio-pt' : ''}" cx="${X(f.valor).toFixed(1)}" cy="${yc}" r="5.5"/>`;
    y += 42;
  });
  let ejes = '';
  if (o.ref) {
    const x = X(o.ref.valor).toFixed(1);
    ejes += `<text class="eje" x="${x}" y="${y + 6}" text-anchor="middle">${esc(o.ref.txt)}</text>`;
  }
  const H = y + 18;
  el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(o.aria || '')}">${ejes}${cuerpo}</svg>`;
}

/** Real contra predicho, con la diagonal de acierto. */
function graficoDispersion(el, real, predicho) {
  el._dibujar = () => graficoDispersion(el, real, predicho);
  const W = anchoDe(el);
  const H = Math.min(W, 300);
  const m = { l: 50, r: 10, t: 8, b: 36 };
  const todos = [...real, ...predicho];
  let lo = Math.min(...todos);
  let hi = Math.max(...todos);
  const margen = (hi - lo) * 0.05 || 1;
  lo -= margen;
  hi += margen;
  const X = (v) => m.l + ((v - lo) * (W - m.l - m.r)) / (hi - lo);
  const Y = (v) => m.t + ((hi - v) * (H - m.t - m.b)) / (hi - lo);
  const ticks = marcas(lo, hi, 3).filter((t) => t >= lo && t <= hi);
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Real contra predicho: ${real.length} medias horas de la prueba.">`;
  svg += `<g class="rejilla">${ticks.map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${Y(t).toFixed(1)}" y2="${Y(t).toFixed(1)}"/>`).join('')}</g>`;
  svg += '<g class="eje">';
  svg += ticks.map((t) => `<text x="${m.l - 6}" y="${(Y(t) + 3).toFixed(1)}" text-anchor="end">${mw(t)}</text>`).join('');
  svg += ticks.map((t) => `<text x="${X(t).toFixed(1)}" y="${H - 20}" text-anchor="middle">${mw(t)}</text>`).join('');
  svg += `<text x="${(m.l + W - m.r) / 2}" y="${H - 4}" text-anchor="middle">real (MW)</text>`;
  svg += `<text x="${m.l + 4}" y="${m.t + 10}">predicho (MW)</text></g>`;
  svg += `<line class="diagonal" x1="${X(lo)}" y1="${Y(lo)}" x2="${X(hi)}" y2="${Y(hi)}"/>`;
  svg += real.map((r, i) => `<circle class="punto-disp" cx="${X(r).toFixed(1)}" cy="${Y(predicho[i]).toFixed(1)}" r="2.6"/>`).join('');
  el.innerHTML = `${svg}</svg>`;
}

/** Histograma de los errores (predicho − real). */
function graficoHistograma(el, errores) {
  el._dibujar = () => graficoHistograma(el, errores);
  const W = anchoDe(el);
  const H = 150;
  const m = { l: 10, r: 10, t: 8, b: 34 };
  const tope = Math.max(...errores.map(Math.abs), 1);
  const nb = 15;
  const ancho = (2 * tope) / nb;
  const cuentas = new Array(nb).fill(0);
  errores.forEach((e) => {
    cuentas[Math.min(nb - 1, Math.floor((e + tope) / ancho))] += 1;
  });
  const maxC = Math.max(...cuentas);
  const X = (v) => m.l + ((v + tope) * (W - m.l - m.r)) / (2 * tope);
  const Y = (c) => m.t + ((maxC - c) * (H - m.t - m.b)) / maxC;
  let svg = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Distribución de los errores del modelo.">`;
  cuentas.forEach((c, k) => {
    const x0 = X(-tope + k * ancho) + 1;
    const x1 = X(-tope + (k + 1) * ancho) - 1;
    svg += `<rect class="barra-modelo" x="${x0.toFixed(1)}" y="${Y(c).toFixed(1)}" width="${Math.max(1, x1 - x0).toFixed(1)}" height="${(H - m.b - Y(c)).toFixed(1)}" rx="2"/>`;
  });
  svg += `<line class="linea-ref" x1="${X(0)}" x2="${X(0)}" y1="${m.t}" y2="${H - m.b}"/>`;
  svg += '<g class="eje">';
  svg += `<text x="${X(-tope)}" y="${H - 20}" text-anchor="start">−${mw(tope)}</text>`;
  svg += `<text x="${X(0)}" y="${H - 20}" text-anchor="middle">0</text>`;
  svg += `<text x="${X(tope)}" y="${H - 20}" text-anchor="end">+${mw(tope)}</text>`;
  svg += `<text x="${X(-tope)}" y="${H - 4}" text-anchor="start">← subestima</text>`;
  svg += `<text x="${X(tope)}" y="${H - 4}" text-anchor="end">sobreestima →</text>`;
  svg += '</g></svg>';
  el.innerHTML = svg;
}

function redibujarGraficos() {
  $$('.chart').forEach((el) => {
    if (el._dibujar && el.offsetParent !== null) el._dibujar();
  });
}

function itemLinea(clase, texto) {
  return `<li><svg width="26" height="10" viewBox="0 0 26 10" aria-hidden="true"><line x1="1" y1="5" x2="25" y2="5" class="linea ${clase}"/></svg>${esc(texto)}</li>`;
}

const ITEM_HUECO = '<li><svg width="18" height="12" viewBox="0 0 18 12" aria-hidden="true"><rect x="0.5" y="0.5" width="17" height="11" fill="none" class="hueco-rect"/><line x1="3" y1="11" x2="9" y2="1" class="hueco-trama"/><line x1="9" y1="11" x2="15" y2="1" class="hueco-trama"/></svg>Sin datos</li>';
const ITEM_PRELIMINAR = '<li><svg width="18" height="12" viewBox="0 0 18 12" aria-hidden="true"><rect x="0" y="7" width="18" height="5" class="prelim-rect"/></svg>Preliminar</li>';

// ---- Tema ----------------------------------------------------------------------------

function aplicarTema(tema) {
  const claro = tema === 'light';
  document.documentElement.dataset.theme = claro ? 'light' : 'dark';
  $('#iconoLuna').hidden = claro;
  $('#iconoSol').hidden = !claro;
  $('#btnTema').setAttribute('aria-label', claro ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro');
  $('meta[name="theme-color"]').setAttribute('content', claro ? '#f4f6f9' : '#0e1117');
}

// ---- Inicio --------------------------------------------------------------------------

function pintarRegimen() {
  const r = S.resumen && S.resumen.regimen_nino;
  if (!r) return;
  const [y, m] = r.mes.split('-').map(Number);
  const estado = ESTADO_NINO[r.estado] || r.estado;
  const texto = r.estado === 'neutro'
    ? `El Niño Costero: neutro · ICEN ${r.icen.toFixed(2)}`
    : `El Niño ${estado} · ICEN ${r.icen.toFixed(2)} · ${MESES_CORTOS[m - 1]}`;
  $('#chipRegimenTxt').textContent = texto;
  $('#chipRegimen').setAttribute(
    'aria-label',
    `Régimen de El Niño Costero: ${estado}, ICEN ${r.icen} en ${MESES[m - 1]} de ${y}. Abre la ficha técnica.`,
  );
}

function pintarInicio() {
  if (!S.areas.length) return;
  $('#listaAreas').innerHTML = S.areas.map((a) => {
    const info = INFO_AREA[a.id] || { letra: a.nombre[0], fg: '#000', desc: '' };
    const met = S.resumen && S.resumen.metricas_prueba[a.id];
    const metrica = met
      ? `<span class="area-metric">Error medio en la prueba de 2026, a 24 h: <span class="num">${nf1.format(met.mae_mw)} MW</span> (<span class="num">${pct(met.mape_pct)}</span>). Mejor referencia: ${esc(NOMBRE_REF[met.mejor_referencia] || met.mejor_referencia)}.</span>`
      : '';
    return `<a class="area-btn" href="#/area/${encodeURIComponent(a.id)}" style="--area-color:${esc(a.color)};--area-fg:${info.fg}">`
      + `<span class="area-badge" aria-hidden="true">${esc(info.letra)}</span>`
      + `<span class="area-body"><span class="area-name">${esc(a.nombre)}</span><span class="area-desc">${esc(info.desc)}</span>${metrica}</span>`
      + '<svg class="area-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg></a>';
  }).join('');
}

function mostrarInicio() {
  $('#vistaInicio').hidden = false;
  $('#vistaArea').hidden = true;
  $('#hoja').hidden = true;
  $('#chipArea').hidden = true;
  $('#app').classList.remove('con-hoja');
  document.title = 'Demanda del SEIN por área';
  window.scrollTo(0, 0);
}

// ---- Detalle del área -------------------------------------------------------------------

function escribirRuta() {
  const q = new URLSearchParams({
    fecha: S.fecha, hora: idxAHora(S.idx), horizonte: S.horizonte, variante: S.variante,
  });
  const destino = `#/area/${encodeURIComponent(S.area)}?${q}`;
  if (location.hash !== destino) history.replaceState(null, '', destino);
}

function indicePico() {
  const s = S.serie;
  if (!s) return null;
  const base = s.real.some((v) => v != null) ? s.real : s.pronostico;
  let mejor = null;
  base.forEach((v, i) => {
    if (v != null && (mejor == null || v > base[mejor])) mejor = i;
  });
  return mejor;
}

function pintarMomentos() {
  const lista = [...MOMENTOS];
  const pico = indicePico();
  if (pico != null) lista.push({ txt: 'Pico del día', idx: pico });
  $('#momentos').innerHTML = lista.map((mo) => (
    `<button type="button" class="moment-btn" data-idx="${mo.idx}" aria-pressed="${mo.idx === S.idx}">${esc(mo.txt)} <span class="mono">${idxAHora(mo.idx)}</span></button>`
  )).join('');
}

function sincronizarControles() {
  $('#inFecha').value = S.fecha;
  $('#inHora').value = String(S.idx);
  $('#inHora').setAttribute('aria-valuetext', idxAHora(S.idx));
  $('#outHora').textContent = idxAHora(S.idx);
  $$('[data-horizonte]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.horizonte === S.horizonte)));
  $$('[data-variante]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.variante === S.variante)));
  pintarMomentos();
}

function mostrarArea(id, q) {
  const area = S.areas.find((a) => a.id === id);
  if (!area) {
    location.hash = '#/';
    return;
  }
  const ahora = ahoraEnLima();
  const cambioDeArea = S.area !== id;
  S.area = id;
  S.fecha = acotarFecha(q.get('fecha')) || S.fecha || acotarFecha(ahora.fecha);
  S.idx = horaAIdx(q.get('hora')) ?? (S.fecha === ahora.fecha ? ahora.idx : S.idx);
  if (['1h', '24h'].includes(q.get('horizonte'))) S.horizonte = q.get('horizonte');
  if (['M0', 'M3'].includes(q.get('variante'))) S.variante = q.get('variante');
  if (cambioDeArea) {
    S.serie = null;
    S.pron = null;
    S.escenario = { ...ESCENARIO_BASE };
  }

  const info = INFO_AREA[id] || { letra: area.nombre[0], fg: '#000', desc: '' };
  const badge = $('#areaBadge');
  badge.textContent = info.letra;
  badge.style.setProperty('--area-color', area.color);
  badge.style.setProperty('--area-fg', info.fg);
  $('#areaNombre').textContent = area.nombre;
  $('#areaDesc').textContent = info.desc;
  const chip = $('#chipArea');
  $('.dot', chip).style.background = area.color;
  $('span:last-child', chip).textContent = `Área ${area.nombre}`;
  chip.hidden = false;
  document.title = `${area.nombre} · Demanda del SEIN`;

  $('#vistaInicio').hidden = true;
  $('#vistaArea').hidden = false;
  $('#hoja').hidden = false;
  $('#app').classList.add('con-hoja');
  if (cambioDeArea) window.scrollTo(0, 0);

  sincronizarControles();
  escribirRuta();
  cargarSerie();
  cargarPronostico();
  pintarTab();
}

function recargar() {
  escribirRuta();
  sincronizarControles();
  cargarSerie();
  cargarPronostico();
  if (S.tab === 'escenarios') pintarEscenarios();
}

let esperaHora = null;
function elegirHora(i) {
  S.idx = i;
  sincronizarControles();
  escribirRuta();
  pintarTarjetas();
  pintarCurva();
  clearTimeout(esperaHora);
  esperaHora = setTimeout(() => {
    cargarPronostico();
    if (S.tab === 'escenarios') pintarEscenarios();
  }, 250);
}

async function cargarSerie() {
  const turno = ++S.turnos.serie;
  const el = $('#graficoDia');
  el.classList.add('cargando');
  try {
    const q = new URLSearchParams({ fecha: S.fecha, horizonte: S.horizonte, variante: S.variante });
    const datos = await api(`/series/${encodeURIComponent(S.area)}?${q}`);
    if (turno !== S.turnos.serie) return;
    S.serie = datos;
    limpiarError();
    pintarTarjetas();
    pintarCurva();
    pintarMomentos();
  } catch (err) {
    if (turno !== S.turnos.serie) return;
    S.serie = null;
    manejarError(err, el);
  } finally {
    if (turno === S.turnos.serie) el.classList.remove('cargando');
  }
}

function pintarTarjeta(card, datos) {
  $('[data-campo="sub"]', card).textContent = datos.sub;
  $('[data-campo="valor"]', card).innerHTML = `${mw(datos.valor)} <small>MW</small>`;
  $('[data-campo="error"]', card).innerHTML = datos.real == null
    ? 'Sin dato real a esa hora'
    : `Error a esa hora: <span class="num">${mw(Math.abs(datos.valor - datos.real))} MW</span>`;
  $('[data-campo="dia"]', card).innerHTML = datos.maeDia == null
    ? 'Sin datos reales en el día'
    : `Error medio del día: <span class="num">${nf1.format(datos.maeDia)} MW</span>`;
  card.classList.toggle('ganador', Boolean(datos.ganador));
  const previo = $('.badge-ganador', card);
  if (previo) previo.remove();
  if (datos.ganador) card.insertAdjacentHTML('beforeend', '<span class="badge-ganador">Menor error del día</span>');
}

function pintarTarjetas() {
  const s = S.serie;
  if (!s) return;
  const i = S.idx;
  const maeModelo = mae(s.real, s.pronostico);
  const maeRef = mae(s.real, s.referencia);
  const hay = maeModelo != null && maeRef != null;
  const nombreRef = s.referencia_nombre;
  const antes = S.horizonte === '1h' ? '1 h' : '24 h';
  $('[data-campo="titulo"]', $('#cardReferencia')).textContent = TITULO_REF[nombreRef] || 'Mejor referencia';
  pintarTarjeta($('#cardModelo'), {
    sub: `Para las ${idxAHora(i)}, emitido ${antes} antes · ${S.variante === 'M3' ? 'con exógenas' : 'solo demanda'}`,
    valor: s.pronostico[i],
    real: s.real[i],
    maeDia: maeModelo,
    ganador: hay && maeModelo < maeRef,
  });
  pintarTarjeta($('#cardReferencia'), {
    sub: `La mejor referencia ingenua a ${antes}`,
    valor: s.referencia[i],
    real: s.real[i],
    maeDia: maeRef,
    ganador: hay && maeRef < maeModelo,
  });

  const partes = [];
  if (s.real[i] != null) partes.push(`A las ${idxAHora(i)} la demanda real fue ${mw(s.real[i])} MW.`);
  if (hay) {
    const dif = maeModelo - maeRef;
    if (Math.abs(dif) < 0.5) {
      partes.push(`En el día, el modelo se equivocó lo mismo que ${NOMBRE_REF[nombreRef]}.`);
    } else {
      partes.push(`En el día, el modelo se equivocó ${mw(Math.abs(dif))} MW ${dif < 0 ? 'menos' : 'más'} que ${NOMBRE_REF[nombreRef]}.`);
    }
    if (s.programacion_diaria) {
      const maeProg = mae(s.real, s.programacion_diaria);
      if (maeProg != null) partes.push(`La Programación Diaria del COES se equivocó ${mw(maeProg)} MW en promedio.`);
    }
  } else {
    partes.push('Este día todavía no tiene datos reales: no se puede medir el error.');
  }
  $('#cmpFrase').textContent = partes.join(' ');
}

function pintarCurva() {
  const s = S.serie;
  const el = $('#graficoDia');
  if (!s) return;
  const nombreRef = TITULO_REF[s.referencia_nombre] || 'Referencia';
  const series = [{ clase: 'ln-referencia', valores: s.referencia, nombre: nombreRef }];
  if (s.programacion_diaria) series.push({ clase: 'ln-programacion', valores: s.programacion_diaria, nombre: 'Programación COES' });
  series.push({ clase: 'ln-pronostico', valores: s.pronostico, nombre: 'Modelo' });
  series.push({ clase: 'ln-real', valores: s.real, nombre: 'Real', puente: true });
  const pico = indicePico();
  const resumen = pico != null && s.real[pico] != null
    ? ` El máximo real fue ${mw(s.real[pico])} MW a las ${idxAHora(pico)}.`
    : '';
  graficoLineas(el, {
    n: s.fecha_hora.length,
    series,
    huecos: s.hueco,
    preliminar: s.preliminar,
    marcador: { i: S.idx, txt: idxAHora(S.idx) },
    etiquetaX: (i) => (i % 12 === 0 ? idxAHora(i) : null),
    etiquetaPunto: (i) => horaDe(s.fecha_hora[i]),
    alto: 230,
    alPulsar: elegirHora,
    aria: `Curva del ${fechaLarga(S.fecha)}: demanda real, pronóstico a ${S.horizonte === '1h' ? '1 hora' : '24 horas'} y ${nombreRef.toLowerCase()}.${resumen}`,
  });
  $('#subCurva').textContent = `${fechaCorta(S.fecha)} · a ${S.horizonte === '1h' ? '1 hora' : '24 horas'}`;

  let leyenda = itemLinea('ln-real', 'Real') + itemLinea('ln-pronostico', 'Modelo') + itemLinea('ln-referencia', nombreRef);
  if (s.programacion_diaria) leyenda += itemLinea('ln-programacion', 'Programación Diaria del COES');
  const hayHueco = s.hueco.some(Boolean);
  const hayPrelim = s.preliminar.some(Boolean);
  if (hayHueco) leyenda += ITEM_HUECO;
  if (hayPrelim) leyenda += ITEM_PRELIMINAR;
  $('#leyendaDia').innerHTML = leyenda;

  const notas = [];
  if (hayHueco) notas.push('Sin datos: el COES no publicó esos periodos. La línea gris punteada solo une los datos vecinos; no es un dato.');
  if (hayPrelim) notas.push('Preliminar: el COES aún no valida esos datos y pueden cambiar.');
  const nota = $('#notaDatos');
  nota.textContent = notas.join(' ');
  nota.hidden = !notas.length;
}

// ---- Hoja inferior ----------------------------------------------------------------------

function abrirHoja(abrir) {
  S.hojaAbierta = abrir;
  $('#hoja').classList.toggle('collapsed', !abrir);
  $('#hojaAsa').setAttribute('aria-expanded', String(abrir));
  $('#hojaAsaTxt').textContent = abrir ? 'Cerrar la hoja' : 'Abrir la hoja';
  if (abrir) requestAnimationFrame(redibujarGraficos);
}

function elegirTab(tab, foco = false) {
  if (tab === S.tab && S.hojaAbierta) {
    abrirHoja(false);
    return;
  }
  S.tab = tab;
  $$('.sheet-tab').forEach((b) => {
    const elegida = b.dataset.tab === tab;
    b.setAttribute('aria-selected', String(elegida));
    b.tabIndex = elegida ? 0 : -1;
    if (elegida && foco) b.focus();
  });
  $$('.tab-panel').forEach((p) => {
    p.hidden = p.id !== `panel-${tab}`;
  });
  abrirHoja(true);
  pintarTab();
}

function pintarTab() {
  if (S.tab === 'operacion') pintarOperacion();
  else if (S.tab === 'escenarios') pintarEscenarios();
  else pintarDiagnostico();
}

// Operación: lo que el modelo espera desde el origen elegido.
async function cargarPronostico() {
  const turno = ++S.turnos.pron;
  const panel = $('#panel-operacion');
  panel.classList.add('cargando');
  try {
    const p = await api('/pronostico', {
      area: S.area, origen: origen(), horizonte: S.horizonte, variante: S.variante, escenario: ESCENARIO_BASE,
    });
    if (turno !== S.turnos.pron) return;
    S.pron = p;
    pintarOperacion();
  } catch (err) {
    if (turno === S.turnos.pron) manejarError(err, panel);
  } finally {
    if (turno === S.turnos.pron) panel.classList.remove('cargando');
  }
}

const NOTAS_OPERACION = `<ul class="lista-notas">
  <li><strong>Rango probable:</strong> la banda donde debería caer la demanda 9 de cada 10 veces.</li>
  <li><strong>Mejor referencia:</strong> la mejor de las ingenuas (persistencia, ayer o la semana pasada a la misma hora) en la validación de 2025.</li>
  <li><strong>A 24 h</strong> también se compara con la Programación Diaria del COES.</li>
  <li><strong>Sin datos y preliminar:</strong> huecos del COES y datos aún no validados; se ven punteados en la curva.</li>
</ul>`;

function pintarOperacion() {
  const panel = $('#panel-operacion');
  const p = S.pron;
  if (!p) {
    panel.innerHTML = '<p class="cargando-txt">Calculando el pronóstico…</p>';
    return;
  }
  const ventana = S.horizonte === '1h' ? 'la próxima hora' : 'las próximas 24 horas';
  let html = `<h3>Desde las ${idxAHora(S.idx)} del ${esc(fechaCorta(S.fecha))}: ${ventana}</h3>`;
  html += `<p class="frase" aria-live="polite">${esc(p.frase)}</p>`;
  if (S.horizonte === '1h') {
    html += '<table class="tabla"><thead><tr><th scope="col">Hora</th><th scope="col" class="num">Modelo</th><th scope="col" class="num">Rango probable</th><th scope="col" class="num">Real</th></tr></thead><tbody>';
    html += p.fecha_hora.map((fh, j) => (
      `<tr><td class="mono">${horaDe(fh)}</td><td class="num mono">${mw(p.pronostico[j])}</td>`
      + `<td class="num mono">${mw(p.intervalo.inferior[j])}–${mw(p.intervalo.superior[j])}</td>`
      + `<td class="num mono">${p.real[j] == null ? 'sin dato' : mw(p.real[j])}</td></tr>`
    )).join('');
    html += '</tbody></table>';
  } else {
    html += '<div id="graficoOperacion" class="chart"></div>';
    html += `<ul class="legend">${itemLinea('ln-real', 'Real')}${itemLinea('ln-pronostico', 'Modelo y rango probable')}${itemLinea('ln-referencia', 'Mejor referencia')}</ul>`;
  }
  html += NOTAS_OPERACION;
  panel.innerHTML = html;
  if (S.horizonte === '24h') {
    graficoLineas($('#graficoOperacion'), {
      n: p.fecha_hora.length,
      series: [
        { clase: 'ln-referencia', valores: p.referencia, nombre: 'Referencia' },
        { clase: 'ln-pronostico', valores: p.pronostico, nombre: 'Modelo', banda: { inf: p.intervalo.inferior, sup: p.intervalo.superior, clase: 'banda-pronostico' } },
        { clase: 'ln-real', valores: p.real, nombre: 'Real', puente: true },
      ],
      etiquetaX: (j) => (j % 12 === 11 ? horaDe(p.fecha_hora[j]) : null),
      etiquetaPunto: (j) => `${fechaCorta(p.fecha_hora[j])} ${horaDe(p.fecha_hora[j])}`,
      alto: 200,
      aria: `Pronóstico de las próximas 24 horas desde las ${idxAHora(S.idx)}, con su rango probable. ${p.frase}`,
    });
  }
}

// Escenarios: a 24 h, controles que vuelven a ejecutar el modelo; a 1 h, la sensibilidad.
function grupoOpciones(id, titulo, botones) {
  return `<div class="grupo-opciones"><span class="field-label" id="${id}">${esc(titulo)}</span>`
    + `<div class="opciones" role="group" aria-labelledby="${id}">${botones.join('')}</div></div>`;
}

function opcion(atributo, valor, texto, elegido) {
  return `<button type="button" class="option-btn" data-${atributo}="${esc(valor)}" aria-pressed="${elegido}">${esc(texto)}</button>`;
}

function pintarEscenarios() {
  if (S.horizonte === '1h') {
    pintarSensibilidad();
    return;
  }
  const e = S.escenario;
  const panel = $('#panel-escenarios');
  let html = '<h3>¿Y si mañana…?</h3>';
  html += `<p class="muted small">Escenarios a 24 h desde las ${idxAHora(S.idx)} del ${esc(fechaCorta(S.fecha))}. Supuesto: el COES recibe de ENFEN los pronósticos de clima y de El Niño.</p>`;
  if (S.variante === 'M0') {
    html += '<div class="nota aviso">La variante «Solo demanda» no usa clima, El Niño ni fallas: los escenarios no la cambian. <button type="button" class="btn" data-accion="usar-m3">Usar «Con exógenas»</button></div>';
  }
  html += grupoOpciones('lblTemp', 'Temperatura frente a la pronosticada', TEMPERATURAS.map((t) => (
    opcion('temp', t, `${t > 0 ? '+' : t < 0 ? '−' : '±'}${Math.abs(t)} °C`, e.delta_temp_c === t))));
  html += grupoOpciones('lblNino', 'El Niño', [
    opcion('nino', 'observado', 'Como se observó', e.nino === 'observado'),
    opcion('nino', 'neutro', 'Neutro', e.nino === 'neutro'),
  ]);
  html += grupoOpciones('lblFalla', 'Falla en curso al emitir', [
    opcion('falla', 'observada', 'Como se observó', e.falla === 'observada'),
    opcion('falla', 'ninguna', 'Sin falla', e.falla === 'ninguna'),
  ]);
  html += '<p id="fraseEscenario" class="frase" aria-live="polite">Calculando…</p>';
  html += '<div id="graficoEscenario" class="chart"></div>';
  html += `<ul class="legend">${itemLinea('ln-real', 'Real')}${itemLinea('ln-pronostico', 'Escenario base')}${itemLinea('ln-escenario', 'Tu escenario y su rango')}</ul>`;
  panel.innerHTML = html;
  cargarEscenario();
}

const esBase = (e) => e.delta_temp_c === 0 && e.nino === 'observado' && e.falla === 'observada';

async function cargarEscenario() {
  const turno = ++S.turnos.esc;
  const pedido = { area: S.area, origen: origen(), horizonte: '24h', variante: S.variante };
  const base = esBase(S.escenario);
  try {
    const pedidos = [api('/pronostico', { ...pedido, escenario: ESCENARIO_BASE })];
    if (!base) pedidos.push(api('/pronostico', { ...pedido, escenario: S.escenario }));
    const [pb, pe] = await Promise.all(pedidos);
    if (turno !== S.turnos.esc || !$('#graficoEscenario')) return;
    const p = pe || pb;
    $('#fraseEscenario').textContent = base
      ? `Elige un cambio para compararlo con el escenario base. ${pb.frase}`
      : pe.frase;
    let pico = 0;
    pb.pronostico.forEach((v, j) => {
      if (v > pb.pronostico[pico]) pico = j;
    });
    const series = [{ clase: 'ln-pronostico', valores: pb.pronostico, nombre: 'Base' }];
    if (!base) {
      series.push({ clase: 'ln-escenario', valores: pe.pronostico, nombre: 'Escenario', banda: { inf: pe.intervalo.inferior, sup: pe.intervalo.superior, clase: 'banda-escenario' } });
    }
    series.push({ clase: 'ln-real', valores: p.real, nombre: 'Real', puente: true });
    graficoLineas($('#graficoEscenario'), {
      n: p.fecha_hora.length,
      series,
      marcador: { i: pico, txt: `pico ${horaDe(pb.fecha_hora[pico])}` },
      etiquetaX: (j) => (j % 12 === 11 ? horaDe(p.fecha_hora[j]) : null),
      etiquetaPunto: (j) => `${fechaCorta(p.fecha_hora[j])} ${horaDe(p.fecha_hora[j])}`,
      alto: 210,
      aria: `Escenario frente a la base en las próximas 24 horas. ${$('#fraseEscenario').textContent}`,
    });
  } catch (err) {
    if (turno === S.turnos.esc) manejarError(err, $('#graficoEscenario'));
  }
}

function pintarSensibilidad() {
  const panel = $('#panel-escenarios');
  const objetivo = idxAHora((S.idx + 2) % 48);
  panel.innerHTML = `
    <div class="nota"><strong>A 1 hora no hay escenarios.</strong> La demanda de la última media hora ya contiene el clima del momento: si hace más calor, ya se nota en la demanda reciente. Por eso aquí se muestra cómo responde el modelo, no un escenario. Para «¿y si mañana hace más calor?», usa el horizonte de 24 horas.
      <div style="margin-top:8px"><button type="button" class="btn" data-accion="ir-24h">Ver escenarios a 24 h</button></div></div>
    <h3>Sensibilidad del modelo a 1 h</h3>
    <p class="muted small">Cómo cambia el pronóstico de las ${objetivo} al mover una variable, con las demás fijas (dependencia parcial, variante con exógenas).</p>
    ${grupoOpciones('lblSens', 'Variable', [
      opcion('sens', 'temperatura', 'Temperatura', S.sensVar === 'temperatura'),
      opcion('sens', 'icen', 'ICEN (El Niño)', S.sensVar === 'icen'),
    ])}
    <p id="fraseSens" class="frase" aria-live="polite">Calculando…</p>
    <div id="graficoSens" class="chart"></div>`;
  cargarSensibilidad();
}

async function cargarSensibilidad() {
  const turno = ++S.turnos.sens;
  const variable = S.sensVar;
  try {
    const s = await api('/sensibilidad', { area: S.area, origen: origen(), variable });
    if (turno !== S.turnos.sens || !$('#graficoSens')) return;
    const temp = variable === 'temperatura';
    const fmtX = (v) => (temp ? `${nf1.format(v)} °C` : nf1.format(v));
    const lo = Math.min(...s.pronostico);
    const hi = Math.max(...s.pronostico);
    const rango = hi - lo;
    const nombre = temp ? 'la temperatura' : 'el ICEN';
    let frase = `Al mover ${nombre} de ${fmtX(s.valores[0])} a ${fmtX(s.valores[s.valores.length - 1])}, el pronóstico a 1 h cambia ${mw(rango)} MW (${pct((100 * rango) / lo)}).`;
    if ((100 * rango) / lo < 2) frase += ' Es poco: a 1 h manda la demanda reciente.';
    $('#fraseSens').textContent = frase;
    const centro = Math.floor(s.valores.length / 2);
    graficoLineas($('#graficoSens'), {
      n: s.valores.length,
      series: [{ clase: 'ln-pronostico', valores: s.pronostico, nombre: 'Pronóstico', puntos: true }],
      marcador: temp ? { i: centro, txt: 'observada' } : null,
      etiquetaX: (j) => (j % 3 === 0 || j === s.valores.length - 1 ? (temp ? `${Math.round(s.valores[j])}°` : nf1.format(s.valores[j])) : null),
      etiquetaPunto: (j) => fmtX(s.valores[j]),
      alto: 200,
      aria: frase,
    });
  } catch (err) {
    if (turno === S.turnos.sens) manejarError(err, $('#graficoSens'));
  }
}

// Diagnóstico: cuándo falla el modelo y qué lo arregla.
async function pintarDiagnostico() {
  const panel = $('#panel-diagnostico');
  const area = S.area;
  if (!S.diag.has(area)) {
    panel.innerHTML = '<p class="cargando-txt">Calculando el diagnóstico…</p>';
    const turno = ++S.turnos.diag;
    try {
      S.diag.set(area, await api(`/diagnostico/${encodeURIComponent(area)}`));
    } catch (err) {
      if (turno === S.turnos.diag) manejarError(err, panel);
      return;
    }
    if (turno !== S.turnos.diag || S.area !== area || S.tab !== 'diagnostico') return;
  }
  const d = S.diag.get(area);
  const prueba = S.salud && S.salud.modelo === 'prueba';
  panel.innerHTML = `
    <p class="muted small">Todo a 24 horas.${prueba ? ' <strong>Datos de prueba:</strong> los números son ilustrativos.' : ''}</p>
    <section class="diag-seccion">
      <h3>Error por régimen de El Niño</h3>
      <p class="muted small">MAE en MW de 2025 a 2026: 2026 casi no tiene régimen neutro.</p>
      <ul class="legend"><li><svg width="18" height="11" aria-hidden="true"><rect width="18" height="11" rx="3" class="barra-modelo"/></svg>Modelo</li><li><svg width="18" height="11" aria-hidden="true"><rect x="0.75" y="0.75" width="16.5" height="9.5" rx="3" class="barra-referencia"/></svg>Mejor referencia</li></ul>
      <div id="gRegimen" class="chart"></div>
    </section>
    <section class="diag-seccion">
      <h3>¿Cuánto aporta cada grupo de variables?</h3>
      <p class="muted small">Ablación en la prueba de 2026: MAE con su intervalo del 95 % (bootstrap por días). Menos es mejor; la línea punteada es M0.</p>
      <div id="gAblacion" class="chart"></div>
    </section>
    <section class="diag-seccion">
      <h3>¿Reentrenar o sumar exógenas?</h3>
      <p class="muted small">MAE en la prueba de 2026 según cada cuánto se reentrena. Punto lleno: con exógenas; vacío: sin exógenas.</p>
      <div id="gAdaptacion" class="chart"></div>
    </section>
    <section class="diag-seccion">
      <h3>Qué variables pesan más</h3>
      <p class="muted small">Cuántos MW sube el error al quitar cada grupo. Un valor negativo quiere decir que quitarlo mejora.</p>
      <div id="gImportancias" class="chart"></div>
    </section>
    <section class="diag-seccion">
      <h3>Real contra predicho</h3>
      <p class="muted small">Cada punto es media hora de la prueba. Sobre la diagonal, el modelo acierta.</p>
      <div id="gDispersion" class="chart"></div>
      <div id="gResiduos" class="chart"></div>
      <p id="txtResiduos" class="muted small"></p>
    </section>`;

  graficoBarras($('#gRegimen'), d.mae_por_regimen.map((r) => ({
    etiqueta: REGIMEN[r.regimen] || r.regimen.replaceAll('_', ' '),
    barras: [
      { valor: r.modelo, clase: 'barra-modelo', texto: `modelo ${nf1.format(r.modelo)}` },
      { valor: r.referencia, clase: 'barra-referencia', texto: `ref. ${nf1.format(r.referencia)}` },
    ],
  })), { aria: 'Error del modelo y de la mejor referencia por régimen de El Niño.' });

  const m0 = d.ablacion.find((a) => a.variante === 'M0');
  graficoPuntos($('#gAblacion'), d.ablacion.map((a) => ({
    etiqueta: VARIANTE[a.variante] || a.variante, valor: a.mae, inf: a.ic_inf, sup: a.ic_sup,
  })), { ref: m0 ? { valor: m0.mae, txt: 'M0' } : null, aria: 'Error de cada variante de la ablación con su intervalo.' });

  graficoPuntos($('#gAdaptacion'), d.adaptacion.map((a) => ({
    etiqueta: `${POLITICA[a.politica] || a.politica}, ${a.exogenas ? 'con' : 'sin'} exógenas`,
    valor: a.mae,
    hueco: !a.exogenas,
  })), { aria: 'Error según la política de reentrenamiento.' });

  graficoBarras($('#gImportancias'), d.importancias.map((x) => ({
    etiqueta: VARIABLE[x.variable] || x.variable.replaceAll('_', ' '),
    barras: [{
      valor: x.valor,
      clase: x.valor >= 0 ? 'barra-neutra' : 'barra-negativa',
      texto: `${x.valor >= 0 ? '+' : '−'}${nf1.format(Math.abs(x.valor))} MW`,
    }],
  })), { aria: 'Importancia de cada grupo de variables.' });

  const { real, predicho } = d.residuos;
  graficoDispersion($('#gDispersion'), real, predicho);
  const errores = predicho.map((p, i) => p - real[i]);
  graficoHistograma($('#gResiduos'), errores);
  const sub = errores.filter((e) => e < 0).length / errores.length;
  $('#txtResiduos').textContent = `El modelo subestimó la demanda en ${pct(100 * sub)} de las medias horas. Subestimar cuesta más: obliga a arrancar generación cara de urgencia.`;
}

// ---- Ficha técnica -------------------------------------------------------------------------

function pintarFicha() {
  const r = S.resumen;
  const s = S.salud;
  const prueba = s && s.modelo === 'prueba';
  const cortes = r
    ? Object.entries(r.fechas_corte).map(([k, v]) => `<tr><td>${esc(CORTE[k] || k)}</td><td class="num mono">${esc(v)}</td></tr>`).join('')
    : '';
  let nino = '';
  if (r) {
    const [y, m] = r.regimen_nino.mes.split('-').map(Number);
    nino = `El último ICEN publicado es ${r.regimen_nino.icen.toFixed(2)}, de ${MESES[m - 1]} de ${y}: régimen ${ESTADO_NINO[r.regimen_nino.estado] || r.regimen_nino.estado} según ENFEN. `;
  }
  $('#fichaCuerpo').innerHTML = `
    <section><h3>Qué hace</h3><p>Pronostica la demanda eléctrica de las áreas Norte, Centro y Sur del SEIN cada 30 minutos, a 1 hora y a 24 horas. La compara con la mejor referencia ingenua y, a 24 h, con la Programación Diaria del COES.</p></section>
    <section><h3>Modelo</h3><p>Modelo <span class="mono">${esc(s ? s.modelo : '—')}</span>, datos <span class="mono">${esc(s ? s.version_datos : '—')}</span>.${prueba ? ' Es el modelo de prueba: persistencia, ciclo diario y ruido sobre series sintéticas. Sirve para probar la app; sus números no son resultados.' : ''}</p></section>
    <section><h3>El Niño Costero</h3><p>${esc(nino)}Cada variable entra con su rezago real de publicación.</p></section>
    <section><h3>Fechas de corte</h3><table class="tabla"><tbody>${cortes}</tbody></table></section>
    <section><h3>Fuentes y licencias</h3><ul>
      <li>COES: demanda por área (IEOD), Programación Diaria y eventos. Sin licencia publicada.</li>
      <li>ERA5 de Copernicus, vía Open-Meteo: temperatura. CC BY 4.0.</li>
      <li>IGP y ENFEN: ICEN.</li>
      <li>NOAA: Niño 1+2. Dominio público.</li>
      <li>Osinergmin: SAIDI. ODC-By.</li>
    </ul></section>
    <section><h3>Supuesto de colaboración</h3><p>Se simula que el COES recibe en tiempo real los datos y los pronósticos de clima y de El Niño de ENFEN (SENAMHI, IGP e IMARPE). Por eso hay escenarios a 24 h.</p></section>
    <section><h3>Por qué no hay escenarios a 1 h</h3><p>A 1 h la demanda reciente ya contiene el clima del momento. En su lugar se muestra la sensibilidad del modelo.</p></section>
    <section><h3>Lo que no cubre</h3><ul>
      <li>La demanda por subestación o por distribuidora.</li>
      <li>Los costos marginales.</li>
      <li>Pronósticos de clima reales: se simulan.</li>
    </ul></section>`;
}

// ---- Rutas e inicio ------------------------------------------------------------------------

function leerRuta() {
  const h = location.hash.replace(/^#/, '') || '/';
  const [camino, consulta] = h.split('?');
  const partes = camino.split('/').filter(Boolean);
  const q = new URLSearchParams(consulta || '');
  if (partes[0] === 'area' && partes[1]) return { vista: 'area', area: decodeURIComponent(partes[1]), q };
  return { vista: 'inicio', q };
}

function enrutar() {
  const r = leerRuta();
  if (r.vista === 'area' && S.areas.length) mostrarArea(r.area, r.q);
  else mostrarInicio();
}

async function cargarBase() {
  const [salud, areas, resumen] = await Promise.all([api('/salud'), api('/areas'), api('/resumen')]);
  S.salud = salud;
  S.areas = areas;
  S.resumen = resumen;
  const prueba = salud.modelo === 'prueba';
  $('#chipPrueba').hidden = !prueba;
  $('#notaPruebaInicio').hidden = !prueba;
  pintarRegimen();
  pintarInicio();
  pintarFicha();
}

async function iniciar() {
  try {
    await cargarBase();
    limpiarError();
  } catch (err) {
    mostrarError(err);
    $('#listaAreas').innerHTML = '<p class="vacio">No se pudieron cargar las áreas.</p>';
  }
  enrutar();
}

function conectarEventos() {
  $('#btnTema').addEventListener('click', () => {
    const tema = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    aplicarTema(tema);
    guardar('tpf-tema', tema);
    redibujarGraficos();
  });

  const ficha = $('#dlgFicha');
  const abrirFicha = () => (typeof ficha.showModal === 'function' ? ficha.showModal() : ficha.setAttribute('open', ''));
  $('#btnFicha').addEventListener('click', abrirFicha);
  $('#chipRegimen').addEventListener('click', abrirFicha);
  $('#btnCerrarFicha').addEventListener('click', () => ficha.close());
  ficha.addEventListener('click', (ev) => {
    if (ev.target === ficha) ficha.close(); // clic en el fondo
  });

  $('#inFecha').addEventListener('change', (ev) => {
    const fecha = acotarFecha(ev.target.value);
    if (!fecha) return;
    S.fecha = fecha;
    recargar();
  });
  $('#inHora').addEventListener('input', (ev) => elegirHora(Number(ev.target.value)));
  $('#momentos').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-idx]');
    if (b) elegirHora(Number(b.dataset.idx));
  });
  $$('[data-horizonte]').forEach((b) => b.addEventListener('click', () => {
    if (S.horizonte === b.dataset.horizonte) return;
    S.horizonte = b.dataset.horizonte;
    recargar();
  }));
  $$('[data-variante]').forEach((b) => b.addEventListener('click', () => {
    if (S.variante === b.dataset.variante) return;
    S.variante = b.dataset.variante;
    recargar();
  }));

  $('#hojaAsa').addEventListener('click', () => abrirHoja(!S.hojaAbierta));
  $$('.sheet-tab').forEach((b) => b.addEventListener('click', () => elegirTab(b.dataset.tab)));
  $('.sheet-tabs').addEventListener('keydown', (ev) => {
    const tabs = $$('.sheet-tab');
    const actual = tabs.findIndex((t) => t.dataset.tab === S.tab);
    let siguiente = null;
    if (ev.key === 'ArrowRight') siguiente = (actual + 1) % tabs.length;
    if (ev.key === 'ArrowLeft') siguiente = (actual - 1 + tabs.length) % tabs.length;
    if (ev.key === 'Home') siguiente = 0;
    if (ev.key === 'End') siguiente = tabs.length - 1;
    if (siguiente == null) return;
    ev.preventDefault();
    elegirTab(tabs[siguiente].dataset.tab, true);
  });

  $('#panel-escenarios').addEventListener('click', (ev) => {
    const b = ev.target.closest('button');
    if (!b) return;
    const d = b.dataset;
    if (d.temp != null) S.escenario = { ...S.escenario, delta_temp_c: Number(d.temp) };
    else if (d.nino) S.escenario = { ...S.escenario, nino: d.nino };
    else if (d.falla) S.escenario = { ...S.escenario, falla: d.falla };
    else if (d.sens) S.sensVar = d.sens;
    else if (d.accion === 'usar-m3') {
      S.variante = 'M3';
      recargar();
      return;
    } else if (d.accion === 'ir-24h') {
      S.horizonte = '24h';
      recargar();
      return;
    } else return;
    pintarEscenarios();
  });

  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && S.hojaAbierta && !$('#dlgFicha').open) abrirHoja(false);
  });

  let esperaResize = null;
  window.addEventListener('resize', () => {
    clearTimeout(esperaResize);
    esperaResize = setTimeout(redibujarGraficos, 150);
  });
  window.addEventListener('hashchange', enrutar);
}

aplicarTema(leer('tpf-tema') === 'light' ? 'light' : 'dark');
conectarEventos();
iniciar();
