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

let FECHA_MIN = '2025-01-01'; // cada modelo puede traer su primer día en /modelos
let FECHA_MAX = '2026-10-31'; // con el modelo real, /resumen trae el último día con datos
const ESCENARIO_BASE = Object.freeze({ delta_temp_c: 0, nino: 'observado', falla: 'observada' });

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

const INFO_AREA = {
  norte: { letra: 'N', fg: '#000', desc: 'Costa norte: Piura, Chiclayo y Trujillo. Lluvias con El Niño y carga minera e industrial.' },
  centro: { letra: 'C', fg: '#fff', desc: 'Lima y el centro: Electroandes, minería e industria. El calor del verano pesa en Lima.' },
  sur: { letra: 'S', fg: '#000', desc: 'Dominada por la minería: Cerro Verde, Las Bambas y Southern. Responde poco al clima.' },
};

const NOMBRE_REF = {
  persistencia: '«el último dato»',
  ayer: '«ayer a la misma hora»',
  semana_pasada: '«la semana pasada a la misma hora»',
};
const TITULO_REF = { persistencia: 'Último dato', ayer: 'Ayer, misma hora', semana_pasada: 'Semana pasada, misma hora' };
const ESTADO_NINO = { neutro: 'neutro', debil: 'débil', moderado: 'moderado', fuerte: 'fuerte', extraordinario: 'extraordinario' };
const REGIMEN = {
  neutro: 'Neutro', debil: 'Niño débil', moderado: 'Niño moderado', fuerte: 'Niño fuerte',
  extraordinario: 'Niño extraordinario', falla_en_curso: 'Falla en curso', red_golpeada: 'Red golpeada',
};
const VARIANTE = {
  M0: 'M0 · demanda y calendario', M1: 'M1 · + clima', M2: 'M2 · + El Niño', M3: 'M3 · + fallas',
  M4: 'M4 · + SAIDI', M3_sin_clima: 'M3 sin clima', M3_sin_nino: 'M3 sin El Niño', M3_sin_fallas: 'M3 sin fallas',
  hibrido: 'Híbrido · XGBoost + Simons', ajustado: 'Chronos-2 ajustado', combinado: 'Combinado',
};
const POLITICA = { fijo: 'Sin reentrenar', semanal: 'Reentreno semanal', alerta_enfen: 'Reentreno con alerta ENFEN' };
const VARIABLE = {
  demanda_reciente: 'Demanda reciente', calendario: 'Calendario', clima: 'Clima', nino: 'El Niño', fallas: 'Fallas', saidi: 'SAIDI',
  fundacional: 'Pronóstico del modelo fundacional', ajustado: 'Chronos-2 ajustado', hibrido: 'Híbrido (XGBoost + Simons)',
};
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
  modelos: [],
  modelo: null,
  tab: 'operacion',
  escenario: { ...ESCENARIO_BASE },
  sensVar: 'temperatura',
  serie: null,
  pron: null,
  pico: null,
  diag: new Map(),
  seguimiento: new Map(),
  turnos: { serie: 0, pron: 0, esc: 0, sens: 0, diag: 0, pico: 0, seg: 0, vivo: 0 },
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
  return `${p.d} ${MESES_CORTOS[p.m - 1]} ${p.y}`;
}

function fechaDiaMes(iso) {
  const p = partesFecha(iso);
  return `${DIAS[p.dow]} ${p.d} de ${MESES[p.m - 1]}`;
}

function fechaLarga(iso) {
  const p = partesFecha(iso);
  return `${DIAS[p.dow]} ${p.d} de ${MESES[p.m - 1]} de ${p.y}`;
}

// «10/03/2026»: el control de fecha sigue el idioma del navegador; esto, siempre el formato peruano
function fechaNumerica(iso) {
  const p = partesFecha(iso);
  return `${String(p.d).padStart(2, '0')}/${String(p.m).padStart(2, '0')}/${p.y}`;
}

// «19:30 del martes 10 de marzo», para un inicio de periodo AAAA-MM-DDTHH:MM
const cuandoTxt = (fechaHora) => `${horaDe(fechaHora)} del ${fechaDiaMes(fechaHora)}`;
const mesLargo = (aaaamm) => MESES[Number(aaaamm.slice(5, 7)) - 1] || aaaamm;
const mesCorto = (aaaamm) => MESES_CORTOS[Number(aaaamm.slice(5, 7)) - 1] || aaaamm;
// «Combinado (recomendado)» → «combinado», para usarlo dentro de una frase
const nombreCorto = (m) => (m ? m.nombre.replace(/\s*\(.*\)\s*$/, '').toLowerCase() : 'modelo');

function sumarDias(iso, dias) {
  const p = partesFecha(iso);
  return new Date(Date.UTC(p.y, p.m - 1, p.d + dias)).toISOString().slice(0, 10);
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

// El parámetro `modelo` solo viaja si el backend ofrece más de uno (un backend anterior no lo conoce).
const hayVariosModelos = () => S.modelos.length > 1;
const modeloPorId = (id) => S.modelos.find((m) => m.id === id) || null;
const modeloActual = () => modeloPorId(S.modelo);
const esFecha = (x) => /^\d{4}-\d{2}-\d{2}$/.test(x || '');
const enRango = (m, fecha) => !m || !fecha
  || ((!esFecha(m.fecha_min) || fecha >= m.fecha_min) && (!esFecha(m.fecha_max) || fecha <= m.fecha_max));
// El modelo que responde: el elegido o, en un día sin sus pronósticos precalculados, su respaldo (el base).
function modeloEfectivo() {
  const m = modeloActual();
  if (m && m.respaldo && !enRango(m, S.fecha)) return modeloPorId(m.respaldo) || m;
  return m;
}
// Un modelo puede no distinguir variantes (el híbrido usa solo la demanda) y tener su propio rango de fechas.
const usaSoloDemanda = (m) => Boolean(m && Array.isArray(m.variantes) && !m.variantes.includes('M3'));
const soloDemanda = () => usaSoloDemanda(modeloEfectivo());
function aplicarModelo() {
  const m = modeloActual();
  const r = m && m.respaldo ? modeloPorId(m.respaldo) : null;
  // Con respaldo, el selector de fecha abarca los dos rangos: fuera del rango del modelo responde el respaldo
  const minimos = [m, r].filter((x) => x && esFecha(x.fecha_min)).map((x) => x.fecha_min).sort();
  const maximos = [m, r].filter((x) => x && esFecha(x.fecha_max)).map((x) => x.fecha_max).sort();
  FECHA_MIN = minimos[0] || '2025-01-01';
  if (maximos.length) FECHA_MAX = maximos[maximos.length - 1];
  if (soloDemanda()) S.variante = 'M0';
  if (S.fecha) S.fecha = acotarFecha(S.fecha) || S.fecha;
  const ayuda = $('#ayudaModelo');
  if (ayuda) {
    ayuda.textContent = (m && m.descripcion) || '';
    ayuda.hidden = !(m && m.descripcion);
  }
  $$('[data-variante]').forEach((b) => { b.disabled = soloDemanda() && b.dataset.variante !== 'M0'; });
  const ayudaVar = $('#ayudaVariante');
  if (ayudaVar) {
    ayudaVar.textContent = soloDemanda()
      ? 'Este modelo usa solo la demanda: no distingue clima ni El Niño.'
      : '«Con clima y El Niño» también usa las fallas en curso de la red.';
  }
}
const conModelo = (obj) => {
  const m = modeloEfectivo();
  return hayVariosModelos() && m ? { ...obj, modelo: m.id } : obj;
};
// Los escenarios y la sensibilidad necesitan un modelo que use el clima: si el elegido no lo usa, el base.
function modeloConClima() {
  if (!soloDemanda()) return modeloEfectivo();
  return S.modelos.find((m) => !usaSoloDemanda(m)) || modeloEfectivo();
}
const conModeloClima = (obj) => {
  const m = modeloConClima();
  // Si el elegido usa solo la demanda (también cuando responde su respaldo), los escenarios van con clima
  const variante = usaSoloDemanda(m) ? 'M0' : (usaSoloDemanda(modeloActual()) ? 'M3' : S.variante);
  return hayVariosModelos() && m ? { ...obj, variante, modelo: m.id } : { ...obj, variante };
};

// index.html pide los datos de arranque antes de que baje este archivo; cada respuesta se usa una sola vez.
const PRECARGA = window.PRECARGA instanceof Map ? window.PRECARGA : new Map();
// La serie que pidió index.html sirve si es del mismo día y horizonte, de la misma variante (o el modelo no la usa)
// y del mismo modelo; un enlace sin modelo se precargó sin él y luego se revisa cuál respondió.
function seriePrecargada(q) {
  for (const ruta of PRECARGA.keys()) {
    const [camino, consulta] = ruta.split('?');
    if (camino !== `/series/${encodeURIComponent(S.area)}`) continue;
    const p = new URLSearchParams(consulta);
    if (p.get('fecha') !== q.get('fecha') || p.get('horizonte') !== q.get('horizonte')) continue;
    if (p.get('variante') !== q.get('variante') && !soloDemanda()) continue;
    if (p.has('modelo') && p.get('modelo') !== q.get('modelo')) continue;
    return ruta;
  }
  return null;
}

async function api(ruta, cuerpo) {
  const opciones = cuerpo
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) }
    : undefined;
  const precargada = cuerpo ? null : PRECARGA.get(ruta);
  PRECARGA.delete(ruta);
  let r;
  try {
    r = (precargada && await precargada) || await fetch(API + ruta, opciones);
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
    b.innerHTML = '<strong>No pudimos conectar con el servidor de datos.</strong> Puede ser la conexión o que el servicio '
      + 'esté detenido. Lo que se ve puede no estar al día. <button class="btn" type="button" id="btnReintentar">Reintentar</button>';
    $('#btnReintentar').addEventListener('click', () => {
      b.hidden = true;
      iniciar();
    });
  } else {
    b.innerHTML = `<strong>No pudimos traer estos datos.</strong> ${esc(textoError(err))}`;
  }
  b.hidden = false;
}

// El detalle del servidor ya viene en español llano; una validación de parámetros no, y se traduce.
function textoError(err) {
  if (err.estado === 0) return 'Sin conexión con el servidor de datos.';
  if (err.estado === 422 && /should|field|pattern|valid/i.test(err.message)) return 'La fecha o la hora no son válidas.';
  if (err.estado === 404 && /not found/i.test(err.message)) return 'Esta versión del servidor todavía no ofrece esta información.';
  return err.message;
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
  if (panel) panel.innerHTML = `<p class="vacio" role="alert">No pudimos calcularlo. ${esc(textoError(err))}</p>`;
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
      let fila = `<div class="fila"><span>${esc(s.nombre)}</span><span>${v == null ? 'sin dato' : esc(formatoY(v))}</span></div>`;
      if (s.banda && s.banda.nombre) fila += `<div class="fila"><span>${esc(s.banda.nombre)}</span><span>${esc(formatoY(s.banda.inf[i]))}–${esc(formatoY(s.banda.sup[i]))}</span></div>`;
      return fila;
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

function itemBanda(clase, texto) {
  return `<li><svg width="26" height="12" viewBox="0 0 26 12" aria-hidden="true"><rect x="1" y="1" width="24" height="10" rx="2" class="${clase}"/><line x1="1" y1="6" x2="25" y2="6" class="linea ln-pronostico"/></svg>${esc(texto)}</li>`;
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
  $('meta[name="theme-color"]').setAttribute('content', claro ? '#f4f6f8' : '#0b0f14');
}

// ---- El Niño costero ------------------------------------------------------------------

// «El Niño costero: extraordinario · ICEN 3.38 (jul-2026)»: con el mes y el año del último ICEN publicado
function pintarRegimen() {
  const r = S.resumen && S.resumen.regimen_nino;
  const chip = $('#chipRegimen');
  if (!r) {
    chip.hidden = true; // sin dato no se queda en «cargando»
    return;
  }
  const [y, m] = r.mes.split('-').map(Number);
  const estado = ESTADO_NINO[r.estado] || r.estado;
  $('#chipRegimenTxt').textContent = `El Niño costero: ${estado} · ICEN ${r.icen.toFixed(2)} (${MESES_CORTOS[m - 1]}-${y})`;
  chip.title = `Último ICEN publicado: ${r.icen} en ${MESES[m - 1]} de ${y}, régimen ${estado} según ENFEN. El ICEN sale con meses de rezago.`;
  chip.hidden = false;
}

// ---- Detalle del área -------------------------------------------------------------------

function escribirRuta() {
  const q = new URLSearchParams({
    fecha: S.fecha, hora: idxAHora(S.idx), horizonte: S.horizonte, variante: S.variante,
  });
  if (hayVariosModelos() && S.modelo) q.set('modelo', S.modelo);
  const destino = `#/area/${encodeURIComponent(S.area)}?${q}`;
  if (location.hash !== destino) history.replaceState(null, '', destino);
  pintarEstado({ modo: 'repaso', texto: `Repaso · ${fechaNumerica(S.fecha)}, ${idxAHora(S.idx)}`,
    corto: `Repaso ${fechaNumerica(S.fecha).replace(/\/20(\d\d)$/, '/$1')} ${idxAHora(S.idx)}`,
    titulo: `Detalle de un día del historial: ${fechaLarga(S.fecha)}, ${idxAHora(S.idx)}` });
  actualizarNav();
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
  const conReal = S.serie && S.serie.real.some((v) => v != null);
  if (pico != null) lista.push({ txt: conReal ? 'Máximo real del día' : 'Máximo pronosticado', idx: pico });
  $('#momentos').innerHTML = lista.map((mo) => (
    `<button type="button" class="moment-btn" data-idx="${mo.idx}" aria-pressed="${mo.idx === S.idx}">${esc(mo.txt)} <span class="mono">${idxAHora(mo.idx)}</span></button>`
  )).join('');
}

function sincronizarControles() {
  $('#inFecha').value = S.fecha;
  $('#inFecha').min = FECHA_MIN;
  $('#inFecha').max = FECHA_MAX;
  $('#fechaLarga').textContent = `${fechaLarga(S.fecha)} (${fechaNumerica(S.fecha)})`;
  $('#inModelo').value = S.modelo || '';
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
  const llega = $('#vistaArea').hidden; // desde el inicio (o al abrir la app): la sección en vivo se vuelve a pedir
  S.area = id;
  S.fecha = acotarFecha(q.get('fecha')) || S.fecha || acotarFecha(ahora.fecha);
  S.idx = horaAIdx(q.get('hora')) ?? (S.fecha === ahora.fecha ? ahora.idx : S.idx);
  if (['1h', '24h'].includes(q.get('horizonte'))) S.horizonte = q.get('horizonte');
  if (['M0', 'M3'].includes(q.get('variante'))) S.variante = q.get('variante');
  if (q.get('modelo') && S.modelos.some((m) => m.id === q.get('modelo')) && q.get('modelo') !== S.modelo) {
    S.modelo = q.get('modelo');
    cargarResumen();
  }
  aplicarModelo();
  if (cambioDeArea) {
    S.serie = null;
    S.pron = null;
    S.pico = null;
    S.escenario = { ...ESCENARIO_BASE };
  }

  const info = INFO_AREA[id] || { letra: area.nombre[0], fg: '#000', desc: '' };
  const badge = $('#areaBadge');
  badge.textContent = info.letra;
  $('#areaNombre').textContent = `${area.nombre}: detalle del pronóstico`;
  document.title = `${area.nombre}, detalle · Curva`;

  mostrarVista('detalle');
  if (cambioDeArea || llega) window.scrollTo(0, 0);

  sincronizarControles();
  escribirRuta();
  cargarSerie();
  cargarPronostico();
  cargarPico();
  pintarTab();
  if (cambioDeArea || llega) cargarEnVivo();
  actualizarNav();
  const seccion = q.get('seccion');
  if (['escenarios', 'diagnostico', 'envivo', 'curva'].includes(seccion)) {
    requestAnimationFrame(() => irASeccion(seccion));
  }
}

function recargar() {
  aplicarModelo(); // un día sin pronósticos precalculados del modelo elegido pasa a su respaldo
  escribirRuta();
  sincronizarControles();
  cargarSerie();
  cargarPronostico();
  cargarPico();
  if (S.tab === 'escenarios') pintarEscenarios();
  if (S.tab === 'diagnostico') pintarDiagnostico(); // «mes a mes» sigue al horizonte y al modelo
}

let esperaHora = null;
function elegirHora(i) {
  S.idx = i;
  sincronizarControles();
  escribirRuta();
  pintarRespuesta();
  pintarCurva();
  pintarTablaDia();
  clearTimeout(esperaHora);
  invalidarPico();
  esperaHora = setTimeout(() => {
    cargarPronostico();
    cargarPico();
    if (S.tab === 'escenarios') pintarEscenarios();
  }, 250);
}

// Mientras llega la serie nueva, lo que se ve es de la elección anterior: se marca como desactualizado.
function marcarCargando(cargando) {
  const resp = $('#respuesta');
  resp.setAttribute('aria-busy', String(cargando));
  resp.classList.toggle('desactualizada', cargando && Boolean(S.serie));
  $('#graficoDia').setAttribute('aria-busy', String(cargando));
  $('#graficoDia').classList.toggle('cargando', cargando);
  $('#respEstado').textContent = cargando ? (S.serie ? 'Actualizando…' : 'Calculando…') : '';
}

async function cargarSerie() {
  const turno = ++S.turnos.serie;
  marcarCargando(true);
  try {
    const q = new URLSearchParams(conModelo({ fecha: S.fecha, horizonte: S.horizonte, variante: S.variante }));
    const precargada = seriePrecargada(q);
    let datos = precargada ? await api(precargada).catch(() => null) : null;
    if (datos && q.has('modelo') && datos.modelo !== q.get('modelo')) datos = null; // respondió otro modelo
    if (!datos) datos = await api(`/series/${encodeURIComponent(S.area)}?${q}`);
    if (turno !== S.turnos.serie) return;
    S.serie = datos;
    limpiarError();
    marcarCargando(false);
    pintarRespuesta();
    pintarConfianza();
    pintarCurva();
    pintarMomentos();
    pintarTablaDia();
  } catch (err) {
    if (turno !== S.turnos.serie) return;
    S.serie = null;
    marcarCargando(false);
    $('#respTitulo').textContent = 'No se pudo calcular el pronóstico';
    $('#respVeredicto').textContent = textoError(err);
    manejarError(err, $('#graficoDia'));
  }
}

const horizonteTxt = () => (S.horizonte === '1h' ? '1 hora' : '24 horas');
const nombreModelo = () => {
  const m = modeloEfectivo();
  return m ? m.nombre : (S.salud ? S.salud.modelo : 'modelo');
};

// Si respondió otro modelo que el elegido (un día sin sus pronósticos precalculados), se dice en la respuesta.
function pintarAvisoModelo() {
  const aviso = $('#respAviso');
  const elegido = modeloActual();
  const respondio = S.serie && S.serie.modelo ? modeloPorId(S.serie.modelo) : modeloEfectivo();
  if (!elegido || !respondio || respondio.id === elegido.id) {
    aviso.hidden = true;
    return;
  }
  const rango = esFecha(elegido.fecha_min) && esFecha(elegido.fecha_max)
    ? ` (los hay del ${fechaCorta(elegido.fecha_min)} al ${fechaCorta(elegido.fecha_max)})` : '';
  aviso.textContent = `Para el ${fechaLarga(S.fecha)} no hay pronósticos precalculados del modelo ${nombreCorto(elegido)}${rango}: se muestra el modelo ${respondio.nombre}.`;
  aviso.hidden = false;
}

// La ficha del número: de qué piezas sale y con qué pesos (el combinado), o qué modelo es (los demás).
function pintarFichaNumero() {
  const s = S.serie;
  if (!s) return;
  const i = S.idx;
  const m = (s.modelo && modeloPorId(s.modelo)) || modeloEfectivo();
  const area = S.areas.find((a) => a.id === S.area);
  const piezas = Array.isArray(s.componentes) && s.componentes.length ? s.componentes : null;
  const resumen = $('#respFichaResumen');
  const cuerpo = $('#respFichaCuerpo');
  if (!piezas) {
    resumen.textContent = '· un solo modelo, sin mezcla';
    const datos = usaSoloDemanda(m) ? 'Usa solo la demanda y el calendario.'
      : (S.variante === 'M3' ? 'Aquí usa la demanda, el calendario, el clima, El Niño y las fallas en curso.' : 'Aquí usa solo la demanda y el calendario.');
    cuerpo.innerHTML = `<p><strong>${esc(m ? m.nombre : nombreModelo())}.</strong> ${esc((m && m.descripcion) || '')} ${esc(datos)}</p>`
      + '<p class="muted small">El número es el pronóstico directo del modelo para esa media hora, emitido con la anticipación elegida.</p>';
    return;
  }
  const corto = (c) => c.nombre.replace(/\s*\(.*\)\s*$/, '');
  resumen.textContent = `· ${piezas.map((c) => `${nf0.format(100 * c.peso)} % ${corto(c)}`).join(' + ')}`;
  let html = `<p>${esc(m ? m.nombre : 'Combinado')}, ${esc(area ? area.nombre : '')} a ${horizonteTxt()}, para las ${idxAHora(i)}:</p>`;
  const faltan = piezas.filter((c) => c.valores[i] == null);
  if (faltan.length) {
    html += `<p>En esta media hora falta el pronóstico de ${esc(faltan.map((c) => c.nombre).join(' y '))}: el número usa la referencia simple.</p>`;
  } else {
    const suma = piezas.reduce((t, c) => t + c.peso * c.valores[i], 0);
    html += '<div class="tabla-scroll ficha-tabla" tabindex="0" role="region" aria-label="Cómo se arma el número"><table class="tabla">'
      + '<caption class="visually-hidden">Cómo se arma el número: pronóstico de cada pieza por su peso</caption>'
      + '<thead><tr><th scope="col">Pieza</th><th scope="col" class="num">Pronóstico</th><th scope="col" class="num">Peso</th><th scope="col" class="num">Aporte</th></tr></thead><tbody>'
      + piezas.map((c) => `<tr><th scope="row">${esc(c.nombre)}</th><td class="num mono">${mw(c.valores[i])} MW</td>`
        + `<td class="num mono">× ${c.peso.toFixed(2)}</td><td class="num mono">${nf1.format(c.peso * c.valores[i])}</td></tr>`).join('')
      + `</tbody><tfoot><tr><th scope="row" colspan="3">Suma</th><td class="num mono">${mw(suma)} MW</td></tr></tfoot></table></div>`;
    html += `<p class="small">${piezas.map((c) => `${esc(corto(c))} × ${c.peso.toFixed(2)}`).join(' + ')} = <strong class="num">${mw(suma)} MW</strong>: `
      + `el número de arriba (${mw(s.pronostico[i])} MW). Puede diferir en 1 MW por el redondeo.</p>`;
  }
  const origenPesos = m && m.composicion ? m.composicion : 'Los pesos se fijaron por área y horizonte con la validación de 2025.';
  html += `<p class="muted small">${esc(origenPesos)} Chronos-2 se ajustó y el híbrido se entrenó con datos hasta 2024; sus pronósticos se calcularon aparte con GPU y la app los lee guardados.</p>`;
  cuerpo.innerHTML = html;
}

// La respuesta: el pronóstico para la hora elegida, emitido con la anticipación elegida.
function pintarRespuesta() {
  const s = S.serie;
  if (!s) return;
  const i = S.idx;
  const v = s.pronostico[i];
  const real = s.real[i];
  const iv = s.intervalo;
  const area = S.areas.find((a) => a.id === S.area);
  const emision = S.horizonte === '1h'
    ? `${idxAHora((i + 46) % 48)}${i < 2 ? ` del ${fechaDiaMes(sumarDias(S.fecha, -1))}` : ''}`
    : `${idxAHora(i)} del ${fechaDiaMes(sumarDias(S.fecha, -1))}`;
  $('#respKicker').textContent = `${area ? area.nombre : ''} · a ${horizonteTxt()}`;
  $('#respTitulo').textContent = `Para las ${idxAHora(i)} del ${fechaLarga(S.fecha)}`;
  $('#respEmision').textContent = `Emitido a las ${emision} · ${nombreModelo()}, ${soloDemanda() ? 'sin clima ni El Niño' : (S.variante === 'M3' ? 'con clima y El Niño' : 'solo con la demanda')}`;
  $('#respValor').textContent = mw(v);
  pintarAvisoModelo();
  pintarFichaNumero();
  $('#respRango').textContent = iv ? `${mw(iv.inferior[i])} – ${mw(iv.superior[i])} MW` : 'no disponible';
  $('#respMarca').innerHTML = '';
  if (real == null) {
    $('#respReal').textContent = 'sin dato';
    $('#respError').textContent = '—';
  } else {
    const dentro = iv && real >= iv.inferior[i] && real <= iv.superior[i];
    $('#respReal').innerHTML = `<span class="num">${mw(real)} MW</span>`;
    if (iv) $('#respMarca').innerHTML = `<span class="marca ${dentro ? 'dentro' : 'fuera'}">la real cayó ${dentro ? 'dentro' : 'fuera'}</span>`;
    $('#respError').innerHTML = `<span class="num">${mw(Math.abs(v - real))} MW</span> <span class="muted">(${pct((100 * Math.abs(v - real)) / real)})</span>`;
  }
  const maeModelo = mae(s.real, s.pronostico);
  const maeRef = mae(s.real, s.referencia);
  $('#respDia').innerHTML = maeModelo == null ? 'sin datos reales' : `<span class="num">${nf1.format(maeModelo)} MW</span>`;
  const ver = $('#respVeredicto');
  ver.className = 'resp-veredicto';
  if (maeModelo == null || maeRef == null) {
    ver.textContent = 'Este día no tiene datos reales: todavía no se puede medir el error.';
    return;
  }
  const mejora = (100 * (maeRef - maeModelo)) / maeRef;
  const ref = NOMBRE_REF[s.referencia_nombre] || 'la referencia simple';
  if (Math.abs(maeRef - maeModelo) < 0.5) {
    ver.textContent = `Este día se equivocó lo mismo que la referencia simple, ${ref}.`;
  } else if (mejora > 0) {
    ver.classList.add('bueno');
    ver.textContent = `Este día se equivocó ${nf0.format(mejora)} % menos que la referencia simple, ${ref} (${nf1.format(maeRef)} MW).`;
  } else {
    ver.classList.add('malo');
    ver.textContent = `Este día se equivocó ${nf0.format(-mejora)} % más que la referencia simple, ${ref} (${nf1.format(maeRef)} MW).`;
  }
}

// Qué tan bueno es: el error del día frente a la referencia, la cobertura del rango y la prueba de 2026.
function pintarConfianza() {
  const s = S.serie;
  if (!s) return;
  const maeModelo = mae(s.real, s.pronostico);
  const maeRef = mae(s.real, s.referencia);
  const ref = TITULO_REF[s.referencia_nombre] || 'Referencia simple';
  const barras = $('#barrasConfianza');
  if (maeModelo != null && maeRef != null) {
    const tope = Math.max(maeModelo, maeRef) || 1;
    const fila = (nombre, valor, clase) => `<div class="barra-fila"><span class="barra-nombre">${esc(nombre)}</span>`
      + `<span class="barra-pista"><span class="barra ${clase}" style="width:${((100 * valor) / tope).toFixed(1)}%"></span></span>`
      + `<span class="barra-valor num">${nf1.format(valor)} MW</span></div>`;
    barras.innerHTML = '<p class="muted small">Error medio de este día (menos es mejor)</p>'
      + fila('Modelo', maeModelo, 'barra-modelo-h') + fila(`Referencia: ${ref.toLowerCase()}`, maeRef, 'barra-referencia-h');
  } else {
    barras.innerHTML = '<p class="muted small">Este día no tiene datos reales para medir el error.</p>';
  }
  const items = [];
  if (s.intervalo) {
    let dentro = 0;
    let n = 0;
    s.real.forEach((r, i) => {
      if (r == null) return;
      n += 1;
      if (r >= s.intervalo.inferior[i] && r <= s.intervalo.superior[i]) dentro += 1;
    });
    if (n) items.push(`<li><strong>Rango probable:</strong> la demanda real cayó dentro en <span class="num">${dentro}</span> de <span class="num">${n}</span> medias horas del día (se espera alrededor de 9 de cada 10).</li>`);
  }
  const met = S.resumen && S.resumen.metricas_prueba[S.area];
  if (met) items.push(`<li><strong>En toda la prueba de 2026</strong> (a 24 h, ${usaSoloDemanda(modeloActual()) ? 'solo con la demanda' : 'con clima y El Niño'}): error medio <span class="num">${nf1.format(met.mae_mw)} MW</span> (<span class="num">${pct(met.mape_pct)}</span>). Mes a mes, en «Diagnóstico».</li>`);
  items.push('<li><strong>Referencia simple:</strong> la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora). Es la vara mínima que el modelo debe superar.</li>');
  $('#listaConfianza').innerHTML = items.join('');
}

function pintarCurva() {
  const s = S.serie;
  const el = $('#graficoDia');
  if (!s) return;
  const nombreRef = TITULO_REF[s.referencia_nombre] || 'Referencia';
  const banda = s.intervalo ? { inf: s.intervalo.inferior, sup: s.intervalo.superior, clase: 'banda-pronostico', nombre: 'Rango probable' } : null;
  const series = [
    { clase: 'ln-referencia', valores: s.referencia, nombre: `Referencia: ${nombreRef.toLowerCase()}` },
    { clase: 'ln-pronostico', valores: s.pronostico, nombre: 'Modelo', banda },
    { clase: 'ln-real', valores: s.real, nombre: 'Real', puente: true },
  ];
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
    alto: 240,
    alPulsar: elegirHora,
    aria: `Curva del ${fechaLarga(S.fecha)}: demanda real, pronóstico a ${horizonteTxt()} con su rango probable y la referencia simple (${nombreRef.toLowerCase()}).${resumen}`,
  });
  $('#subCurva').textContent = `${fechaCorta(S.fecha)} · a ${horizonteTxt()}`;

  let leyenda = itemLinea('ln-real', 'Real') + itemLinea('ln-pronostico', 'Modelo');
  if (banda) leyenda += itemBanda('banda-pronostico', 'Rango probable');
  leyenda += itemLinea('ln-referencia', `Referencia: ${nombreRef.toLowerCase()}`);
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

function pintarTablaDia() {
  const det = $('#tablaDia');
  const s = S.serie;
  if (!det.open || !s) return;
  const iv = s.intervalo;
  const filas = s.fecha_hora.map((fh, i) => `<tr${i === S.idx ? ' class="fila-elegida"' : ''}><th scope="row" class="mono">${horaDe(fh)}</th>`
    + `<td class="num mono">${mw(s.pronostico[i])}</td>`
    + `<td class="num mono">${iv ? `${mw(iv.inferior[i])}–${mw(iv.superior[i])}` : '—'}</td>`
    + `<td class="num mono">${s.real[i] == null ? 'sin dato' : mw(s.real[i])}</td>`
    + `<td class="num mono">${mw(s.referencia[i])}</td></tr>`).join('');
  $('#tablaDiaCuerpo').innerHTML = `<div class="tabla-scroll" tabindex="0" role="region" aria-label="Datos del día"><table class="tabla">`
    + `<caption class="visually-hidden">Demanda del ${esc(fechaLarga(S.fecha))}, en MW, pronóstico a ${horizonteTxt()}</caption>`
    + '<thead><tr><th scope="col">Hora</th><th scope="col" class="num">Modelo</th><th scope="col" class="num">Rango probable</th><th scope="col" class="num">Real</th><th scope="col" class="num">Referencia</th></tr></thead>'
    + `<tbody>${filas}</tbody></table></div>`;
}

// ---- Máximo y mayor subida de las próximas 24 h -------------------------------------------------

// Lo que se ve es de la elección anterior: se descarta la respuesta en vuelo y se atenúa hasta la nueva.
function invalidarPico() {
  S.turnos.pico += 1;
  const panel = $('#pico');
  panel.setAttribute('aria-busy', 'true');
  panel.classList.toggle('desactualizada', Boolean(S.pico));
}

async function cargarPico() {
  invalidarPico();
  const turno = S.turnos.pico;
  const panel = $('#pico');
  const pedido = { area: S.area, fecha: S.fecha, idx: S.idx };
  try {
    const q = new URLSearchParams(conModelo({ origen: origen(), variante: S.variante }));
    const datos = await api(`/pico/${encodeURIComponent(pedido.area)}?${q}`);
    if (turno !== S.turnos.pico) return;
    S.pico = { ...datos, pedido }; // el origen viaja con la respuesta
    panel.hidden = false;
    pintarPico();
  } catch (err) {
    if (turno !== S.turnos.pico) return;
    if (err.estado === 404 && /not found/i.test(err.message)) panel.hidden = true; // un backend sin /pico
    else manejarError(err, $('#picoCuerpo'));
  } finally {
    if (turno === S.turnos.pico) {
      panel.setAttribute('aria-busy', 'false');
      panel.classList.remove('desactualizada');
    }
  }
}

function pintarPico() {
  const d = S.pico;
  if (!d) return;
  const area = S.areas.find((a) => a.id === S.area);
  const m = d.modelo ? modeloPorId(d.modelo) : null;
  const { pico, rampa, acierto } = d;
  const { fecha, idx } = d.pedido || { fecha: S.fecha, idx: S.idx };
  let html = `<p class="muted small">Si se emite a las ${idxAHora(idx)} del ${esc(fechaDiaMes(fecha))}: de las ${esc(cuandoTxt(d.desde))} a las ${esc(cuandoTxt(d.hasta))}, con el pronóstico a 24 h${m ? ` del modelo ${esc(nombreCorto(m))}` : ''}.</p>`;
  html += '<dl class="pico-datos">';
  html += `<div><dt>Máximo</dt><dd><span class="pico-valor num">${mw(pico.valor)} MW</span> a las ${esc(cuandoTxt(pico.fecha_hora))}`
    + `<span class="pico-nota">Rango probable: <span class="num">${mw(pico.inferior)} – ${mw(pico.superior)} MW</span></span></dd></div>`;
  if (rampa) {
    html += `<div><dt>Mayor subida en una hora</dt><dd><span class="pico-valor num">+${mw(rampa.subida_mw)} MW</span> de las ${esc(horaDe(rampa.desde))} a las ${esc(cuandoTxt(rampa.hasta))}`
      + `<span class="pico-nota"><span class="marca ${rampa.fuerte ? 'fuera' : 'dentro'}">${rampa.fuerte ? 'rampa fuerte' : 'subida habitual'}</span></span></dd></div>`;
  } else {
    html += '<div><dt>Mayor subida en una hora</dt><dd>La demanda pronosticada no sube en ninguna hora de la ventana.</dd></div>';
  }
  html += '</dl>';
  if (acierto) {
    html += `<p class="pico-acierto">¿Acierta la hora? En 2026, la hora del máximo pronosticado de cada día cayó a ±1 h de la del máximo real en <strong class="num">${nf1.format(acierto.pct_hora)} %</strong> de los días`
      + ` (${nf0.format(acierto.dias)}); la referencia simple, en ${nf1.format(acierto.pct_hora_referencia)} %. El valor del máximo se equivocó en promedio <span class="num">${mw(acierto.mae_pico_mw)} MW</span> (la referencia, ${mw(acierto.mae_pico_referencia_mw)} MW).</p>`;
  }
  const umbral = rampa && rampa.umbral_mw != null
    ? ` «Rampa fuerte» es subir más de ${mw(rampa.umbral_mw)} MW en una hora: la mayor subida del día solo pasó de ahí en el 5 % de los días de 2016 a 2024 en ${area ? `el ${esc(area.nombre)}` : 'el área'}.`
    : '';
  html += `<p class="muted small">Cada media hora de la ventana es el pronóstico a 24 h emitido 24 h antes, el mismo de la curva: a las ${idxAHora(idx)} ya estaban todos emitidos.${umbral}</p>`;
  $('#picoCuerpo').innerHTML = html;
}

// ---- Pestañas de detalle ------------------------------------------------------------------

function elegirTab(tab, foco = false) {
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
  pintarTab();
  requestAnimationFrame(redibujarGraficos);
}

function irASeccion(destino) {
  if (destino === 'escenarios' || destino === 'diagnostico') {
    elegirTab(destino);
    destino = 'detalle';
  }
  const el = document.getElementById(destino);
  if (!el) return;
  const reducido = matchMedia('(prefers-reduced-motion: reduce)').matches;
  el.scrollIntoView({ block: 'start', behavior: reducido ? 'auto' : 'smooth' });
  el.focus({ preventScroll: true });
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
    const p = await api('/pronostico', conModelo({
      area: S.area, origen: origen(), horizonte: S.horizonte, variante: S.variante, escenario: ESCENARIO_BASE,
    }));
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
  <li><strong>Referencia simple:</strong> la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora) en la validación de 2025.</li>
</ul>`;

function pintarOperacion() {
  const panel = $('#panel-operacion');
  const p = S.pron;
  if (!p) {
    panel.innerHTML = '<p class="cargando-txt">Calculando el pronóstico…</p>';
    return;
  }
  const ventana = S.horizonte === '1h' ? 'la próxima hora' : 'las próximas 24 horas';
  let html = `<h3>Si se emite a las ${idxAHora(S.idx)} del ${esc(fechaCorta(S.fecha))}: ${ventana}</h3>`;
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
    html += `<ul class="legend">${itemLinea('ln-real', 'Real')}${itemLinea('ln-pronostico', 'Modelo')}${itemBanda('banda-pronostico', 'Rango probable')}${itemLinea('ln-referencia', 'Referencia simple')}</ul>`;
  }
  html += NOTAS_OPERACION;
  panel.innerHTML = html;
  if (S.horizonte === '24h') {
    graficoLineas($('#graficoOperacion'), {
      n: p.fecha_hora.length,
      series: [
        { clase: 'ln-referencia', valores: p.referencia, nombre: 'Referencia simple' },
        { clase: 'ln-pronostico', valores: p.pronostico, nombre: 'Modelo', banda: { inf: p.intervalo.inferior, sup: p.intervalo.superior, clase: 'banda-pronostico', nombre: 'Rango probable' } },
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
  let html = '<h3>¿Y si mañana hace más calor, o El Niño se calma?</h3>';
  html += `<p class="muted small">Cambia un supuesto y el modelo vuelve a calcular las próximas 24 h desde las ${idxAHora(S.idx)} del ${esc(fechaCorta(S.fecha))}. Supuesto del proyecto: el COES recibe de ENFEN los pronósticos de clima y de El Niño.</p>`;
  if (soloDemanda() && !usaSoloDemanda(modeloConClima())) {
    html += `<div class="nota aviso">El modelo ${esc(nombreCorto(modeloEfectivo()))} usa solo la demanda, así que el clima y El Niño no lo mueven. Estos escenarios los calcula el modelo ${esc(modeloConClima().nombre)}, con clima y El Niño.</div>`;
  } else if (soloDemanda()) {
    html += `<div class="nota aviso">${esc(nombreModelo())} usa solo la demanda: los escenarios de clima y de El Niño no lo cambian.</div>`;
  } else if (S.variante === 'M0' && !usaSoloDemanda(modeloActual())) {
    html += '<div class="nota aviso">«Solo demanda» no usa clima, El Niño ni fallas: los escenarios no la cambian. <button type="button" class="btn" data-accion="usar-m3">Usar «Con clima y El Niño»</button></div>';
  }
  html += grupoOpciones('lblTemp', 'Temperatura frente a la esperada', TEMPERATURAS.map((t) => (
    opcion('temp', t, `${t > 0 ? '+' : t < 0 ? '−' : '±'}${Math.abs(t)} °C`, e.delta_temp_c === t))));
  html += grupoOpciones('lblNino', 'El Niño', [
    opcion('nino', 'observado', 'Como se observó', e.nino === 'observado'),
    opcion('nino', 'neutro', 'Neutro', e.nino === 'neutro'),
  ]);
  html += grupoOpciones('lblFalla', 'Falla en la red al emitir', [
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
  const pedido = conModeloClima({ area: S.area, origen: origen(), horizonte: '24h' });
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
    <h3>¿Cuánto le importa al modelo la temperatura a 1 h?</h3>
    <p class="muted small">Cómo cambia el pronóstico de las ${objetivo} al mover una variable y dejar todo lo demás igual (usa los datos con clima y El Niño${soloDemanda() && !usaSoloDemanda(modeloConClima()) ? `: lo calcula el modelo ${esc(modeloConClima().nombre)}, porque el ${esc(nombreCorto(modeloEfectivo()))} usa solo la demanda` : ''}).</p>
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
    const { modelo } = conModeloClima({});
    const s = await api('/sensibilidad', modelo ? { area: S.area, origen: origen(), variable, modelo } : { area: S.area, origen: origen(), variable });
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
  const clave = `${S.modelo || ''}|${area}`; // el diagnóstico es de un modelo y un área
  if (!S.diag.has(clave)) {
    panel.innerHTML = '<p class="cargando-txt">Calculando el diagnóstico…</p>';
    const turno = ++S.turnos.diag;
    try {
      const q = hayVariosModelos() && S.modelo ? `?modelo=${encodeURIComponent(S.modelo)}` : '';
      S.diag.set(clave, await api(`/diagnostico/${encodeURIComponent(area)}${q}`));
    } catch (err) {
      if (turno === S.turnos.diag) manejarError(err, panel);
      return;
    }
    if (turno !== S.turnos.diag || S.area !== area || S.tab !== 'diagnostico' || clave !== `${S.modelo || ''}|${S.area}`) return;
  }
  const d = S.diag.get(clave);
  const prueba = S.salud && S.salud.modelo === 'prueba';
  panel.innerHTML = `
    <p class="muted small">El error medio va en MW (menos es mejor). «Mes a mes» sigue la anticipación elegida; lo demás es a 24 horas.${prueba ? ' <strong>Datos de prueba:</strong> los números son ilustrativos.' : ''}</p>
    <section class="diag-seccion">
      <h3>¿Con qué fase de El Niño se equivoca más?</h3>
      <p class="muted small">Error medio en la prueba de 2026 según la fase de El Niño.</p>
      <ul class="legend"><li><svg width="18" height="11" aria-hidden="true"><rect width="18" height="11" rx="3" class="barra-modelo"/></svg>Modelo</li><li><svg width="18" height="11" aria-hidden="true"><rect x="0.75" y="0.75" width="16.5" height="9.5" rx="3" class="barra-referencia"/></svg>Referencia simple</li></ul>
      <p id="lecRegimen" class="lectura"></p>
      <div id="gRegimen" class="chart"></div>
    </section>
    <section class="diag-seccion" aria-labelledby="tituloSeguimiento">
      <h3 id="tituloSeguimiento">Mes a mes en 2026: ¿sigue ganándole a la referencia?</h3>
      <p class="muted small">Error medio de cada mes de la prueba de 2026, a ${horizonteTxt()}, con pronósticos que los modelos no vieron al entrenar.</p>
      <div id="seguimientoCuerpo"></div>
    </section>
    <section class="diag-seccion">
      <h3>¿Cuánto aporta cada grupo de datos?</h3>
      <p class="muted small">Error en la prueba de 2026 al ir sumando datos al modelo, con su intervalo del 95 % (remuestreando días). La línea punteada es «solo demanda» (M0).</p>
      <p id="lecAblacion" class="lectura"></p>
      <div id="gAblacion" class="chart"></div>
    </section>
    <section class="diag-seccion">
      <h3>¿Conviene reentrenar seguido o sumar datos de clima?</h3>
      <p class="muted small">Error en la prueba de 2026 según cada cuánto se reentrena. Punto lleno: con clima y El Niño; vacío: solo demanda.</p>
      <p id="lecAdaptacion" class="lectura"></p>
      <div id="gAdaptacion" class="chart"></div>
    </section>
    <section class="diag-seccion">
      <h3>¿Qué datos pesan más?</h3>
      <p class="muted small">Cuántos MW sube el error al quitar cada grupo de datos. Un valor negativo quiere decir que quitarlo mejora.</p>
      <p id="lecImportancias" class="lectura"></p>
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
  })), { aria: 'Error del modelo y de la referencia simple según la fase de El Niño.' });

  const m0 = d.ablacion.find((a) => a.variante === 'M0');
  graficoPuntos($('#gAblacion'), d.ablacion.map((a) => ({
    etiqueta: VARIANTE[a.variante] || a.variante, valor: a.mae, inf: a.ic_inf, sup: a.ic_sup,
  })), { ref: m0 ? { valor: m0.mae, txt: 'M0' } : null, aria: 'Error de cada variante de la ablación con su intervalo.' });

  graficoPuntos($('#gAdaptacion'), d.adaptacion.map((a) => ({
    etiqueta: `${POLITICA[a.politica] || a.politica}, ${a.exogenas ? 'con clima y El Niño' : 'solo demanda'}`,
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

  pintarLecturas(d);
  cargarSeguimiento();

  const { real, predicho } = d.residuos;
  graficoDispersion($('#gDispersion'), real, predicho);
  const errores = predicho.map((p, i) => p - real[i]);
  graficoHistograma($('#gResiduos'), errores);
  const sub = errores.filter((e) => e < 0).length / errores.length;
  $('#txtResiduos').textContent = `El modelo subestimó la demanda en ${pct(100 * sub)} de las medias horas. Subestimar cuesta más: obliga a arrancar generación cara de urgencia.`;
}

// Mes a mes: el MAE de cada modelo frente a la referencia y la cobertura del rango del modelo elegido.
async function cargarSeguimiento() {
  const cont = $('#seguimientoCuerpo');
  if (!cont) return;
  const turno = ++S.turnos.seg;
  const { area, horizonte } = S;
  const elegido = modeloActual();
  // El elegido primero; los demás, para comparar
  const modelos = hayVariosModelos() ? [elegido, ...S.modelos.filter((m) => m !== elegido)].filter(Boolean) : [elegido || { id: null, nombre: nombreModelo() }];
  const pedir = (m) => {
    const variante = m === elegido ? S.variante : 'M3';
    const clave = `${m.id}|${area}|${horizonte}|${variante}`;
    if (!S.seguimiento.has(clave)) {
      const q = new URLSearchParams({ horizonte, variante });
      if (hayVariosModelos() && m.id) q.set('modelo', m.id);
      const promesa = api(`/seguimiento/${encodeURIComponent(area)}?${q}`);
      promesa.catch(() => S.seguimiento.delete(clave));
      S.seguimiento.set(clave, promesa);
    }
    return S.seguimiento.get(clave);
  };
  cont.innerHTML = '<p class="cargando-txt">Calculando el seguimiento…</p>';
  let resultados;
  try {
    resultados = await Promise.all(modelos.map(pedir));
  } catch (err) {
    if (turno === S.turnos.seg && $('#seguimientoCuerpo')) manejarError(err, $('#seguimientoCuerpo'));
    return;
  }
  if (turno !== S.turnos.seg || !$('#seguimientoCuerpo')) return;
  pintarSeguimiento(modelos, resultados);
}

function pintarSeguimiento(modelos, res) {
  const cont = $('#seguimientoCuerpo');
  const sel = res[0];
  const meses = sel.meses.map((m) => m.mes);
  const n = meses.length;
  const clases = ['ln-pronostico', 'ln-modelo-2', 'ln-modelo-3'];
  const porMes = (r, campo) => meses.map((mes) => {
    const fila = r.meses.find((x) => x.mes === mes);
    return fila ? fila[campo] : null;
  });
  const nombreRef = (TITULO_REF[sel.referencia_nombre] || 'Referencia simple').toLowerCase();
  const leyenda = modelos.map((m, k) => itemLinea(clases[k] || 'ln-modelo-3', m.nombre)).join('') + itemLinea('ln-referencia', `Referencia: ${nombreRef}`);
  const meta = sel.meta_cobertura_pct;

  // Lecturas: la conclusión de cada gráfico, calculada
  const ganados = sel.meses.filter((m) => m.mae_modelo < m.mae_referencia).length;
  const peor = sel.meses.reduce((a, b) => (b.mae_modelo > a.mae_modelo ? b : a));
  const totales = modelos.map((m, k) => `${nombreCorto(m)} ${nf1.format(res[k].total.mae_modelo)} MW`).join('; ');
  const lecMae = `Todo 2026, a ${horizonteTxt()}: ${totales}; la referencia simple, ${nf1.format(sel.total.mae_referencia)} MW. `
    + `El ${nombreCorto(modelos[0])} se equivocó menos que la referencia en ${ganados === n ? `los ${n} meses` : `${ganados} de ${n} meses`}; su peor mes fue ${mesLargo(peor.mes)} (${nf1.format(peor.mae_modelo)} MW).`;
  const periodos = [...new Set(res.map((r) => r.total.periodos))];
  const avisoFilas = periodos.length > 1
    ? ` Ojo: no se midieron en las mismas medias horas (${modelos.map((m, k) => `${nombreCorto(m)} ${nf0.format(res[k].total.periodos)}`).join(', ')}), así que la comparación no es exacta.`
    : ` Los ${modelos.length > 1 ? `${modelos.length} modelos se midieron en las mismas ${nf0.format(periodos[0])} medias horas` : `${nf0.format(periodos[0])} medias horas`}.`;
  const cubierto = sel.total.cobertura_pct;
  const dif = cubierto - meta;
  let veredicto = 'cumple lo que promete';
  if (dif < -5) veredicto = 'queda corto: el rango es más angosto de lo que debería';
  else if (dif < -2) veredicto = 'queda algo corto: el rango es un poco más angosto de lo que debería';
  else if (dif > 5) veredicto = 'es más ancho de lo necesario';
  else if (dif > 2) veredicto = 'cubre algo más de lo que promete: el rango es un poco más ancho de lo necesario';
  const bajos = sel.meses.filter((m) => m.cobertura_pct < meta - 5);
  const minimo = sel.meses.reduce((a, b) => (b.cobertura_pct < a.cobertura_pct ? b : a));
  const lecCob = `El rango probable del ${nombreCorto(modelos[0])} promete cubrir el ${nf0.format(meta)} % de las medias horas; en 2026 cubrió el ${nf1.format(cubierto)} %: ${veredicto}. `
    + (bajos.length
      ? `En ${bajos.length} de ${n} meses quedó por debajo del ${nf0.format(meta - 5)} %: ${bajos.map((m) => `${mesLargo(m.mes)} (${nf1.format(m.cobertura_pct)} %)`).join(', ')}.`
      : `Ningún mes bajó del ${nf0.format(meta - 5)} %; el más bajo fue ${mesLargo(minimo.mes)} (${nf1.format(minimo.cobertura_pct)} %).`);

  const filas = meses.map((mes, j) => `<tr><th scope="row">${esc(mesLargo(mes))}</th>`
    + res.map((r) => `<td class="num mono">${nf1.format(porMes(r, 'mae_modelo')[j] ?? NaN)}</td>`).join('')
    + `<td class="num mono">${nf1.format(sel.meses[j].mae_referencia)}</td><td class="num mono">${nf1.format(sel.meses[j].cobertura_pct)} %</td></tr>`).join('');
  const pie = '<tr><th scope="row">Todo 2026</th>' + res.map((r) => `<td class="num mono">${nf1.format(r.total.mae_modelo)}</td>`).join('')
    + `<td class="num mono">${nf1.format(sel.total.mae_referencia)}</td><td class="num mono">${nf1.format(sel.total.cobertura_pct)} %</td></tr>`;

  cont.innerHTML = `<p id="lecSeguimiento" class="lectura">${esc(lecMae + avisoFilas)}</p>
    <div id="gSeguimiento" class="chart"></div>
    <ul class="legend" aria-label="Leyenda">${leyenda}</ul>
    <h4 class="diag-sub">¿El rango probable cubre lo que promete?</h4>
    <p class="muted small">Qué parte de las medias horas de cada mes cayó dentro del rango probable del ${esc(nombreCorto(modelos[0]))}. La línea punteada es la meta (${nf0.format(meta)} %).</p>
    <p id="lecCobertura" class="lectura">${esc(lecCob)}</p>
    <div id="gCobertura" class="chart"></div>
    <details class="tabla-datos"><summary>Ver la tabla mes a mes</summary>
      <div class="tabla-scroll" tabindex="0" role="region" aria-label="Error y cobertura mes a mes"><table class="tabla">
        <caption class="visually-hidden">Error medio en MW de cada modelo y de la referencia, y cobertura del rango del ${esc(nombreCorto(modelos[0]))}, por mes de 2026, a ${horizonteTxt()}</caption>
        <thead><tr><th scope="col">Mes</th>${modelos.map((m) => `<th scope="col" class="num">${esc(m.nombre)}</th>`).join('')}<th scope="col" class="num">Referencia</th><th scope="col" class="num">Cobertura</th></tr></thead>
        <tbody>${filas}</tbody><tfoot>${pie}</tfoot></table></div>
    </details>`;

  const angosto = anchoDe($('#gSeguimiento')) < 400;
  const etiquetaMes = (j) => (!angosto || j % 2 === 0 || j === n - 1 ? mesCorto(meses[j]) : null);
  graficoLineas($('#gSeguimiento'), {
    n,
    series: [
      { clase: 'ln-referencia', valores: sel.meses.map((m) => m.mae_referencia), nombre: `Referencia: ${nombreRef}` },
      ...modelos.slice(1).map((m, k) => ({ clase: clases[k + 1] || 'ln-modelo-3', valores: porMes(res[k + 1], 'mae_modelo'), nombre: m.nombre })),
      { clase: 'ln-pronostico', valores: sel.meses.map((m) => m.mae_modelo), nombre: modelos[0].nombre, puntos: true },
    ],
    etiquetaX: etiquetaMes,
    etiquetaPunto: (j) => `${mesLargo(meses[j])} de ${meses[j].slice(0, 4)}`,
    formatoY: (v) => `${mw(v)}`,
    alto: 220,
    aria: `Error medio por mes de 2026, en MW. ${lecMae}`,
  });
  graficoLineas($('#gCobertura'), {
    n,
    series: [
      { clase: 'ln-meta', valores: meses.map(() => meta), nombre: 'Meta' },
      { clase: 'ln-pronostico', valores: sel.meses.map((m) => m.cobertura_pct), nombre: 'Cubrió', puntos: true },
    ],
    etiquetaX: etiquetaMes,
    etiquetaPunto: (j) => `${mesLargo(meses[j])} de ${meses[j].slice(0, 4)}`,
    formatoY: (v) => `${nf0.format(v)} %`,
    alto: 170,
    aria: `Cobertura del rango probable por mes de 2026. ${lecCob}`,
  });
}

// Una frase por gráfico: la conclusión, para quien no lee gráficos de error.
function pintarLecturas(d) {
  const nombreReg = (r) => REGIMEN[r] || r.replaceAll('_', ' ');
  const regs = d.mae_por_regimen;
  if (regs.length) {
    const peor = regs.reduce((a, b) => (b.modelo > a.modelo ? b : a));
    const gana = regs.filter((r) => r.modelo < r.referencia).length;
    $('#lecRegimen').textContent = `Donde más se equivoca: ${nombreReg(peor.regimen)} (${nf1.format(peor.modelo)} MW). `
      + (gana === regs.length ? `Le gana a la referencia simple en las ${regs.length} fases.` : `Le gana a la referencia simple en ${gana} de ${regs.length} fases.`);
  }
  const m0 = d.ablacion.find((a) => a.variante === 'M0');
  const m3 = d.ablacion.find((a) => a.variante === 'M3');
  const hib = d.ablacion.find((a) => a.variante === 'hibrido');
  const comb = d.ablacion.find((a) => a.variante === 'combinado');
  if (m0 && comb) {
    const solapan = comb.ic_inf <= m0.ic_sup && m0.ic_inf <= comb.ic_sup;
    $('#lecAblacion').textContent = `Combinado: ${nf1.format(comb.mae)} MW; el modelo base solo con la demanda (M0): ${nf1.format(m0.mae)} MW`
      + (hib ? `; el híbrido: ${nf1.format(hib.mae)} MW. ` : '. ')
      + (solapan ? 'Los intervalos del combinado y del base se superponen: la diferencia no es concluyente.'
        : `Combinar baja el error ${nf1.format(Math.abs(m0.mae - comb.mae))} MW frente al base.`);
  } else if (m0 && hib) {
    const solapan = hib.ic_inf <= m0.ic_sup && m0.ic_inf <= hib.ic_sup;
    const dif = m0.mae - hib.mae;
    $('#lecAblacion').textContent = `Híbrido: ${nf1.format(hib.mae)} MW; el modelo sin el pronóstico fundacional (M0): ${nf1.format(m0.mae)} MW. `
      + (solapan ? 'Los intervalos se superponen: la diferencia no es concluyente.'
        : `${dif > 0 ? 'Sumar el fundacional baja' : 'Sumar el fundacional sube'} el error ${nf1.format(Math.abs(dif))} MW.`);
  } else if (m0 && m3) {
    const solapan = m3.ic_inf <= m0.ic_sup && m0.ic_inf <= m3.ic_sup;
    const dif = m0.mae - m3.mae;
    $('#lecAblacion').textContent = `Con clima, El Niño y fallas (M3): ${nf1.format(m3.mae)} MW; solo demanda (M0): ${nf1.format(m0.mae)} MW. `
      + (solapan ? 'Los intervalos se superponen: la diferencia no es concluyente.'
        : `${dif > 0 ? 'Sumar esos datos baja' : 'Sumar esos datos sube'} el error ${nf1.format(Math.abs(dif))} MW.`);
  }
  if (!d.adaptacion.length) $('#lecAdaptacion').textContent = 'No se midió para este modelo: reentrenarlo pide volver a calcular los pronósticos fundacionales.';
  if (d.adaptacion.length) {
    const mejor = d.adaptacion.reduce((a, b) => (b.mae < a.mae ? b : a));
    const fijo = d.adaptacion.find((a) => a.politica === 'fijo' && !a.exogenas);
    $('#lecAdaptacion').textContent = `Lo mejor: ${(POLITICA[mejor.politica] || mejor.politica).toLowerCase()}, ${mejor.exogenas ? 'con clima y El Niño' : 'solo demanda'} (${nf1.format(mejor.mae)} MW)`
      + (fijo && fijo !== mejor ? `, frente a ${nf1.format(fijo.mae)} MW sin reentrenar y solo con la demanda.` : '.');
  }
  if (d.importancias.length) {
    const top = d.importancias.reduce((a, b) => (b.valor > a.valor ? b : a));
    const nombre = VARIABLE[top.variable] || top.variable.replaceAll('_', ' ');
    $('#lecImportancias').textContent = `Lo que más pesa: ${nombre.toLowerCase()} (el error sube ${nf1.format(top.valor)} MW si se quita).`;
  }
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
    <section><h3>Qué hace</h3><p>Pronostica la demanda eléctrica de las áreas Norte, Centro y Sur del SEIN cada 30 minutos, a 1 hora y a 24 horas, con su rango probable. La compara con la referencia simple: la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora).</p></section>
    <section><h3>Modelo</h3><p>Modelo <span class="mono">${esc(s ? nombreModelo() : '—')}</span>, datos <span class="mono">${esc(s ? s.version_datos : '—')}</span>.${prueba ? ' Es el modelo de prueba: persistencia, ciclo diario y ruido sobre series sintéticas. Sirve para probar la app; sus números no son resultados.' : ''}</p></section>
    <section><h3>El Niño Costero</h3><p>${esc(nino)}Cada variable entra con su rezago real de publicación.</p></section>
    <section><h3>Fechas de corte</h3><table class="tabla"><tbody>${cortes}</tbody></table></section>
    <section><h3>Fuentes y licencias</h3><ul>
      <li>COES: demanda por área (IEOD) y eventos. Sin licencia publicada.</li>
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

// ---- En vivo: lo que registra cada día la tubería con el anexo del COES ---------------------------------------

const TIPO_DIA = { en_vivo: 'En vivo', reconstruido: 'Reconstruido' };
const REF_CORTA = { persistencia: 'último dato', ayer: 'ayer', semana_pasada: 'semana pasada' };
const plural = (n, uno, varios) => `${nf0.format(n)} ${n === 1 ? uno : varios}`;

// Sin caché: la tubería agrega filas cada mañana, así que se vuelve a pedir al entrar al área y al ir a la sección.
async function cargarEnVivo() {
  const cont = $('#envivoCuerpo');
  const panel = $('#envivo');
  const turno = ++S.turnos.vivo;
  panel.setAttribute('aria-busy', 'true');
  let d;
  try {
    d = await api(`/en-vivo/${encodeURIComponent(S.area)}`);
  } catch (err) {
    if (turno !== S.turnos.vivo) return;
    panel.setAttribute('aria-busy', 'false');
    if (err.estado === 404) cont.innerHTML = '<p class="vacio">Esta versión del servidor todavía no ofrece el pronóstico en vivo.</p>';
    else manejarError(err, cont);
    return;
  }
  if (turno !== S.turnos.vivo) return;
  panel.setAttribute('aria-busy', 'false');
  pintarEnVivo(d);
}

function pintarEnVivo(d) {
  const cont = $('#envivoCuerpo');
  if (!d.ultimo) {
    cont.innerHTML = '<p class="vacio">Todavía no hay pronósticos en vivo de esta área: la tubería diaria no ha corrido con estos datos.</p>';
    return;
  }
  const u = d.ultimo;
  const cuenta = (t) => u.tipo.filter((x) => x === t).length;
  const exAnte = cuenta('ex_ante_estricto');
  const enVivo = cuenta('en_vivo');
  const reconstruido = u.tipo.length - exAnte - enVivo;
  const diaDatos = sumarDias(u.datos_hasta.slice(0, 10), -1); // datos_hasta es el fin del último periodo: las 24:00
  const hayReal = u.real.some((v) => v != null);

  let lectura = d.dias_en_vivo
    ? `Lleva ${plural(d.dias_en_vivo, 'día', 'días')} en vivo, desde el ${fechaDiaMes(d.primer_dia_en_vivo)}.`
    : 'Todavía no hay días en vivo: solo reconstruidos.';
  if (d.dias_reconstruidos) lectura += ` Antes, ${plural(d.dias_reconstruidos, 'día reconstruido', 'días reconstruidos')}: se calcularon después de conocerse el real, con los datos que el modelo habría tenido, y no cuentan como en vivo.`;

  let tipoTxt;
  if (reconstruido === u.tipo.length) tipoTxt = '<strong>Reconstruido:</strong> se calculó después de conocerse el real; no es un pronóstico en vivo.';
  else if (exAnte === u.tipo.length) tipoTxt = 'Se emitió antes de que empezara el día: las 48 medias horas son ex ante.';
  else tipoTxt = `De sus 48 medias horas, ${plural(exAnte, 'todavía no empezaba', 'todavía no empezaban')} al emitirse; las otras ${nf0.format(enVivo + reconstruido)} ya habían empezado, pero su real aún no estaba publicado.`;
  // La marca va en la media hora en que se emitió, si fue ese mismo día
  const idxEmision = u.emitido_lima.slice(0, 10) === u.fecha ? horaAIdx(horaDe(u.emitido_lima)) : null;

  const a24 = d.verificado.filter((v) => v.horizonte === '24h');
  const diaMes = (iso) => `${partesFecha(iso).d} ${MESES_CORTOS[partesFecha(iso).m - 1]}`;
  const filas = a24.map((v) => `<tr><th scope="row" class="mono">${esc(diaMes(v.fecha))}</th>`
    + `<td><span class="etiqueta-tipo ${v.tipo === 'en_vivo' ? 'tipo-vivo' : 'tipo-reconstruido'}">${esc(TIPO_DIA[v.tipo])}</span></td>`
    + `<td class="num mono">${nf1.format(v.mae_modelo)}</td>`
    + `<td class="num mono">${nf1.format(v.mae_referencia)}</td>`
    + `<td class="num mono">${nf0.format(v.cobertura_pct)} %</td></tr>`).join('');
  const refsTabla = [...new Map(a24.map((v) => [v.tipo, v.referencia_nombre])).entries()]
    .map(([tipo, ref]) => `${TIPO_DIA[tipo].toLowerCase()}, ${(TITULO_REF[ref] || ref).toLowerCase()}`).join('; ');

  const grupo = (g, h) => d.resumen.find((r) => r.grupo === g && r.horizonte === h);
  const linea = (r) => `error medio <span class="num">${nf1.format(r.mae_modelo)} MW</span>; la referencia simple (${esc(REF_CORTA[r.referencia_nombre] || r.referencia_nombre)}), <span class="num">${nf1.format(r.mae_referencia)} MW</span>; el rango 10–90 % cubrió el <span class="num">${nf0.format(r.cobertura_pct)} %</span> (promete 80 %)`;
  const items = [];
  const vivo = grupo('en_vivo', '24h');
  const exAnteR = grupo('ex_ante_estricto', '24h');
  const recon = grupo('reconstruido', '24h');
  const una = grupo('reconstruido', '1h');
  if (vivo) {
    let t = `<li><strong>En vivo a 24 h</strong> (${plural(vivo.dias, 'día', 'días')}, ${nf0.format(vivo.periodos)} medias horas): ${linea(vivo)}.`;
    if (exAnteR) t += ` Solo las ${nf0.format(exAnteR.periodos)} medias horas que todavía no empezaban al emitirse: <span class="num">${nf1.format(exAnteR.mae_modelo)} MW</span>.`;
    items.push(`${t}</li>`);
  } else {
    items.push('<li><strong>En vivo a 24 h:</strong> todavía ningún día con su real. Cada día se verifica cuando el COES publica su anexo, a la mañana siguiente.</li>');
  }
  if (recon) items.push(`<li><strong>Reconstruido a 24 h</strong> (del ${esc(fechaCorta(recon.desde))} al ${esc(fechaCorta(recon.hasta))}, ${plural(recon.dias, 'día', 'días')}): ${linea(recon)}. Es el primer tramo posterior a todo lo evaluado antes, pero no cuenta como en vivo.</li>`);
  if (una) items.push(`<li><strong>A 1 hora, siempre reconstruido</strong> (${plural(una.dias, 'día', 'días')}): ${linea(una)}. No puede emitirse en vivo: necesita la demanda de una hora antes, y el COES la publica al día siguiente junto con el real.</li>`);

  cont.innerHTML = `<p class="lectura">${esc(lectura)}</p>
    <p class="muted small">Cada mañana, cuando el COES publica la demanda del día anterior (hacia las 09:45), ${esc(d.modelo || 'el modelo')} pronostica a 24 h las 48 medias horas del día. El pronóstico queda guardado con su hora de emisión antes de conocerse el real y no se reescribe.</p>
    <h3 class="diag-sub">Pronóstico del ${esc(fechaLarga(u.fecha))}</h3>
    <p class="small">Emitido el ${esc(fechaDiaMes(u.emitido_lima))} a las ${esc(horaDe(u.emitido_lima))} (hora de Lima), con datos hasta el ${esc(fechaDiaMes(diaDatos))} a las 24:00. ${tipoTxt}</p>
    <div id="gEnVivo" class="chart"></div>
    <ul class="legend" aria-label="Leyenda">${itemLinea('ln-pronostico', 'Modelo')}${itemBanda('banda-pronostico', 'Rango 10–90 % (8 de cada 10)')}${hayReal ? itemLinea('ln-real', 'Real') : ''}</ul>
    ${hayReal ? '' : '<p class="muted small">El real de este día llega mañana, con el anexo del COES.</p>'}
    <h3 class="diag-sub">Lo ya verificado contra el real</h3>
    <ul class="lista-confianza">${items.join('')}</ul>
    ${a24.length ? `<details class="tabla-datos"><summary>Ver el error de cada día a 24 h</summary>
      <div class="tabla-scroll" tabindex="0" role="region" aria-label="Error de cada día a 24 h"><table class="tabla">
        <caption class="visually-hidden">Error medio en MW del modelo y de la referencia simple, y cobertura del rango 10–90 %, por día pronosticado a 24 h</caption>
        <thead><tr><th scope="col">Día</th><th scope="col">Tipo</th><th scope="col" class="num">Modelo</th><th scope="col" class="num">Referencia</th><th scope="col" class="num">Cobertura</th></tr></thead>
        <tbody>${filas}</tbody></table></div>
      <p class="muted small">Error medio del día en MW. Referencia simple (la mejor en el acumulado de cada tipo): ${esc(refsTabla)}.</p>
    </details>` : ''}
    <p class="muted small">Modelo: ${esc(d.modelo || '—')}${d.version_pesos ? ` · pesos <span class="mono">${esc(d.version_pesos.slice(0, 12))}</span>` : ''}. Datos del IEOD del COES.</p>`;

  const resumenGrafico = hayReal
    ? ` El error medio del día fue ${nf1.format(mae(u.real, u.pronostico))} MW.`
    : ' El real todavía no se publica.';
  graficoLineas($('#gEnVivo'), {
    n: u.fecha_hora.length,
    series: [
      { clase: 'ln-pronostico', valores: u.pronostico, nombre: 'Modelo', banda: { inf: u.inferior, sup: u.superior, clase: 'banda-pronostico', nombre: 'Rango 10–90 %' } },
      { clase: 'ln-real', valores: u.real, nombre: 'Real', puente: true },
    ],
    marcador: idxEmision != null ? { i: idxEmision, txt: `Emitido ${horaDe(u.emitido_lima)}` } : null,
    etiquetaX: (i) => (i % 12 === 0 ? idxAHora(i) : null),
    etiquetaPunto: (i) => horaDe(u.fecha_hora[i]),
    alto: 220,
    aria: `Pronóstico en vivo a 24 h del ${fechaLarga(u.fecha)} con su rango 10–90 %.${resumenGrafico}`,
  });
}

// ---- Producto: cabecera, vistas y navegación ---------------------------------------------------------------

const ORDEN_AREAS = ['norte', 'centro', 'sur'];
const AREAS_RESPALDO = [{ id: 'norte', nombre: 'Norte' }, { id: 'centro', nombre: 'Centro' }, { id: 'sur', nombre: 'Sur' }];
const ICONO = {
  bien: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg>',
  ojo: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3 2 21h20L12 3z"/><path d="M12 10v5"/><path d="M12 18h.01"/></svg>',
  mal: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></svg>',
  info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
};
const TIPO_TXT = {
  ex_ante_estricto: 'Emitido antes de que empezara la media hora',
  en_vivo: 'Emitido con la media hora ya empezada, antes de su real',
  reconstruido: 'Reconstruido: calculado después de conocerse el real',
};
const rangoTxt = (a, b) => `${mw(a)}\u00a0–\u00a0${mw(b)}`;
const firmado = (x) => `${x >= 0 ? '+' : '−'}${mw(Math.abs(x))}`;
const nombreArea = (id) => (S.areas.find((a) => a.id === id) || AREAS_RESPALDO.find((a) => a.id === id) || { nombre: id }).nombre;
const DIAS_CORTOS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const diaCorto = (fh) => `${DIAS_CORTOS[partesFecha(fh).dow]} ${partesFecha(fh).d}`;
const fechaNum = (iso) => fechaNumerica(iso).slice(0, 5); // «12/11»
const capital = (t) => t.charAt(0).toUpperCase() + t.slice(1);

// El fin de un periodo como se dice: «2026-11-13T00:00» es el jueves 12 a las 24:00.
function finTxt(fh) {
  if (horaDe(fh) === '00:00') {
    const ayer = sumarDias(fh.slice(0, 10), -1);
    return { corto: `${fechaNum(ayer)}, 24:00`, largo: `${fechaDiaMes(ayer)} a las 24:00` };
  }
  return { corto: `${fechaNum(fh)}, ${horaDe(fh)}`, largo: `${fechaDiaMes(fh)} a las ${horaDe(fh)}` };
}

function pintarEstado({ modo, texto, titulo, corto }) {
  const e = $('#estadoDatos');
  e.hidden = false;
  e.classList.toggle('repaso', modo === 'repaso');
  $('#estadoTxt').innerHTML = `<span class="larga">${esc(texto)}</span><span class="corta">${esc(corto || texto)}</span>`;
  e.title = titulo || texto;
  e.setAttribute('aria-label', titulo || texto);
}

function mostrarVista(nombre) {
  S.vista = nombre;
  $('#vistaAhora').hidden = nombre !== 'ahora';
  $('#vistaConfianza').hidden = nombre !== 'confianza';
  $('#vistaArea').hidden = nombre !== 'detalle';
  actualizarNav();
}

// Los enlaces de la cabecera llevan el área (y, si se repasa un día, ese momento) a la otra pantalla.
function actualizarNav() {
  const area = S.vista === 'detalle' ? S.area : S.vista === 'confianza' ? C.area : A.area;
  const a = area || 'centro';
  const repaso = S.vista === 'detalle' ? { fecha: S.fecha, hora: idxAHora(S.idx) } : (A.fecha ? { fecha: A.fecha, hora: A.hora } : null);
  $$('#navPantallas a').forEach((enlace) => {
    const v = enlace.dataset.nav;
    if (v === 'ahora') enlace.href = rutaAhora(a, repaso);
    if (v === 'confianza') enlace.href = `#/confianza/${encodeURIComponent(a)}`;
    if (v === 'detalle') enlace.href = rutaDetalle(a, repaso);
    if (v === S.vista) enlace.setAttribute('aria-current', 'page');
    else enlace.removeAttribute('aria-current');
  });
  const volver = $('#detVolver');
  if (volver) volver.href = rutaAhora(a, S.vista === 'detalle' ? repaso : null);
}

function rutaAhora(area, repaso = null, extra = {}) {
  const q = new URLSearchParams();
  if (repaso && repaso.fecha) {
    q.set('fecha', repaso.fecha);
    q.set('hora', repaso.hora || '19:00');
  }
  Object.entries(extra).forEach(([k, v]) => { if (v) q.set(k, v); });
  return `#/ahora/${encodeURIComponent(area)}${q.toString() ? `?${q}` : ''}`;
}

// El detalle abre en el mismo momento si es un día del historial del modelo; si no, en su último día.
function rutaDetalle(area, repaso = null, seccion = null) {
  const q = new URLSearchParams();
  if (repaso && repaso.fecha && repaso.fecha >= FECHA_MIN && repaso.fecha <= FECHA_MAX) {
    q.set('fecha', repaso.fecha);
    q.set('hora', repaso.hora);
    q.set('horizonte', '24h');
    q.set('variante', S.variante || 'M3');
  }
  if (hayVariosModelos() && S.modelo) q.set('modelo', S.modelo);
  if (seccion) q.set('seccion', seccion);
  return `#/area/${encodeURIComponent(area)}${q.toString() ? `?${q}` : ''}`;
}

const hoyLima = () => ahoraEnLima().fecha;
function horaValida(t) {
  const i = horaAIdx(t);
  return i == null ? null : idxAHora(i);
}

// ---- Ahora --------------------------------------------------------------------------------------------------

const A = { area: 'centro', fecha: null, hora: null, modelo: null, datos: new Map(), turno: 0, ref: true, despues: false,
  dias: null, extra: new Map() };

function consultaAhora() {
  const q = new URLSearchParams();
  if (A.fecha) q.set('origen', `${A.fecha}T${A.hora}`);
  if (A.modelo) q.set('modelo', A.modelo);
  return q.toString() ? `?${q}` : '';
}

function mostrarAhora(area, q) {
  const cambio = A.area !== area;
  A.area = area;
  const fecha = esFecha(q.get('fecha')) ? q.get('fecha') : null;
  A.fecha = fecha && fecha !== hoyLima() ? fecha : null;
  A.hora = A.fecha ? (horaValida(q.get('hora')) || idxAHora(ahoraEnLima().idx)) : null;
  A.modelo = q.get('modelo') && (!S.modelos.length || modeloPorId(q.get('modelo'))) ? q.get('modelo') : null;
  const llega = $('#vistaAhora').hidden;
  mostrarVista('ahora');
  document.title = `${nombreArea(area)} · Ahora · Curva`;
  if (llega || cambio) window.scrollTo(0, 0);
  cargarAhora();
}

function irAhora(repaso) {
  history.replaceState(null, '', rutaAhora(A.area, repaso, { modelo: A.modelo }));
  mostrarAhora(A.area, new URLSearchParams(location.hash.split('?')[1] || ''));
}

async function cargarAhora() {
  const turno = ++A.turno;
  const consulta = consultaAhora();
  const vista = $('#vistaAhora');
  vista.classList.toggle('desactualizada', A.datos.size > 0);
  $('#ahCifras').setAttribute('aria-busy', 'true');
  $('#ahLienzo').setAttribute('aria-busy', 'true');
  if (!A.datos.size) {
    $('#ahCifras').innerHTML = '<p class="cargando-bloque">Calculando el pronóstico…</p>';
    pintarAreasAhora();
  }
  const areas = [A.area, ...ORDEN_AREAS.filter((a) => a !== A.area)];
  const pedidos = areas.map((a) => api(`/ahora/${encodeURIComponent(a)}${consulta}`));
  pedidos.forEach((pr, k) => pr.then((d) => {
    if (turno !== A.turno || k === 0) return;
    A.datos.set(areas[k], d);
    pintarAreasAhora();
  }).catch(() => {}));
  let d;
  try {
    d = await pedidos[0];
  } catch (err) {
    if (turno !== A.turno) return;
    vista.classList.remove('desactualizada');
    $('#ahCifras').setAttribute('aria-busy', 'false');
    $('#ahLienzo').setAttribute('aria-busy', 'false');
    if (err.estado === 0) {
      mostrarError(err);
      const copia = leerCopiaAhora(consulta);
      if (copia) {
        A.datos.set(A.area, copia.d);
        pintarAhora();
        const cuando = new Date(copia.guardado);
        const txt = `${String(cuando.getDate()).padStart(2, '0')}/${String(cuando.getMonth() + 1).padStart(2, '0')}, ${String(cuando.getHours()).padStart(2, '0')}:${String(cuando.getMinutes()).padStart(2, '0')}`;
        $('#ahAviso').innerHTML = `${ICONO.ojo}<span>Sin conexión con el servidor de datos: se muestra la última copia guardada en este navegador, consultada el ${esc(txt)}.</span>`;
        $('#ahAviso').hidden = false;
        pintarEstado({ modo: 'repaso', texto: `Sin conexión · copia del ${txt}`, corto: `Copia del ${txt}`, titulo: 'Sin conexión: última copia guardada' });
        return;
      }
      pintarEstado({ modo: 'repaso', texto: 'Sin conexión con los datos', corto: 'Sin conexión' });
      A.sinDatos = true;
      pintarAreasAhora();
      $('#vistaAhora .grid-principal').hidden = !A.datos.has(A.area);
    }
    const motivo = err.estado === 422 && A.dias ? `No hay datos para repasar el ${fechaNumerica(A.fecha)}. ${textoDias(A.dias)}` : textoError(err);
    $('#ahAviso').innerHTML = `${ICONO.ojo}<span>${esc(motivo)}</span>`;
    $('#ahAviso').hidden = false;
    if (!A.datos.has(A.area)) $('#ahCifras').innerHTML = '<p class="vacio">No pudimos traer el pronóstico de esta área.</p>';
    return;
  }
  if (turno !== A.turno) return;
  limpiarError();
  A.sinDatos = false;
  $('#vistaAhora .grid-principal').hidden = false;
  A.datos.set(A.area, d);
  A.dias = d.dias_disponibles;
  if (!consulta) guardar(`tpf-copia|${A.area}`, JSON.stringify({ d, guardado: Date.now() })); // solo «hoy»: el repaso no cambia
  vista.classList.remove('desactualizada');
  $('#ahCifras').setAttribute('aria-busy', 'false');
  $('#ahLienzo').setAttribute('aria-busy', 'false');
  pintarAhora();
  cargarExtraAhora(d, turno);
}

function leerCopiaAhora(consulta) {
  try {
    if (consulta) return null;
    const c = JSON.parse(leer(`tpf-copia|${A.area}`) || 'null');
    return c && c.d && c.d.fecha_hora ? c : null;
  } catch {
    return null;
  }
}

function textoDias(tramos) {
  if (!tramos || !tramos.length) return '';
  return `Hay datos ${tramos.map(([a, b]) => `del ${fechaCorta(a)} al ${fechaCorta(b)}`).join(' y ')}, y el pronóstico de hoy.`;
}

function pintarAhora() {
  const d = A.datos.get(A.area);
  if (!d) return;
  const vivo = d.modo === 'en_vivo';
  const fin = finTxt(d.datos_hasta);
  const nombreModeloAhora = d.modelo_nombre.replace(/\s*\(.*\)\s*$/, '');
  $('#principal').textContent = vivo
    ? `${nombreArea(A.area)} · hoy, ${fechaDiaMes(d.ahora)}`
    : `${nombreArea(A.area)} · ${fechaLarga(d.origen)}`;
  $('#ahModo').innerHTML = vivo
    ? `<b>Son las ${esc(horaDe(d.ahora))}.</b> Lo real llega hasta el ${esc(fin.largo)}: el COES publica cada día la demanda del día anterior, hacia las 09:45. Todo lo que sigue es pronóstico, emitido hoy a las ${esc(horaDe(d.emitido_en || d.ahora))}.`
    : `<b>Repaso de un día del historial.</b> Así se veía a las ${esc(horaDe(d.origen))}: lo real llega hasta esa hora y lo que sigue es lo que el modelo ya había pronosticado.`;
  pintarEstado(vivo
    ? { modo: 'vivo', texto: `Hoy · datos del COES al ${fin.corto}`, corto: `COES ${fin.corto.replace(', ', ' ')}`, titulo: `Pronóstico de hoy. Datos reales del COES hasta el ${fin.largo}; el resto es pronóstico.` }
    : { modo: 'repaso', texto: `Repaso · ${fechaNumerica(d.origen)}, ${horaDe(d.origen)}`, corto: `Repaso ${fechaNumerica(d.origen).replace(/\/20(\d\d)$/, '/$1')} ${horaDe(d.origen)}`, titulo: `Repaso del ${fechaLarga(d.origen)}, ${horaDe(d.origen)}` });

  // Controles: «Hoy» o un día del historial, y la hora (solo al repasar)
  $('#ahHoy').setAttribute('aria-pressed', String(vivo));
  const fecha = $('#ahFecha');
  const tramos = d.dias_disponibles || [];
  if (tramos.length) fecha.min = tramos.map((t) => t[0]).sort()[0];
  fecha.max = hoyLima();
  fecha.value = vivo ? d.ahora.slice(0, 10) : d.origen.slice(0, 10);
  $('#ahFechaLarga').textContent = vivo ? 'Hoy' : `${fechaLarga(d.origen)} (${fechaNumerica(d.origen)})`;
  const hora = $('#ahHora');
  hora.value = horaDe(d.ahora);
  hora.closest('.campo').hidden = vivo;
  const avisos = [...(d.avisos || [])];
  $('#ahAviso').innerHTML = avisos.map((t) => `${ICONO.ojo}<span>${esc(t)}</span>`).join('');
  $('#ahAviso').hidden = !avisos.length;

  pintarAreasAhora();
  pintarCifras(d);
  $('#ahGrafTitulo').textContent = vivo ? 'Ayer y hoy' : 'Ese día y las 24 h siguientes';
  $('#ahGrafSub').textContent = vivo
    ? `${nombreArea(A.area)}. A la izquierda, lo real de ayer y lo que se había pronosticado; desde la línea punteada no hay dato real todavía. «Ahora» marca la hora de Lima.`
    : `${nombreArea(A.area)}. A la izquierda de «Ahora», lo real y lo que se pronosticó un día antes; a la derecha, lo que ya estaba pronosticado a las ${horaDe(d.origen)}.`;
  $('#ahLeyRango').textContent = `Rango del ${d.nivel_rango_pct} %`;
  $('#ahLeyRef').textContent = `Referencia (${(REF_CORTA[d.referencia_nombre] || 'simple')})`;
  $('#ahDespuesCampo').hidden = vivo;
  $('#ahDespues').checked = A.despues;
  pintarDiaCompleto(d);
  $('#ahRef').checked = A.ref;
  graficoAhora($('#ahLienzo'), d);
  $('#ahDesc').textContent = descripcionAhora(d);
  if ($('#ahTablaDet').open) pintarTablaAhora(d);
  pintarAyer(d);
  pintarBueno(d);
  pintarOrigen(d);
  $('#ahPie').textContent = `Curva es un pronóstico abierto hecho con los datos públicos del COES (IEOD); no sirve para operar el sistema eléctrico. ${vivo ? `Pronóstico en vivo de ${nombreModeloAhora}, emitido cada mañana con la demanda del día anterior.` : `Pronósticos del modelo ${nombreModeloAhora.toLowerCase()}.`} El CSV trae el pronóstico, su rango y su error, no la serie real del COES, que no tiene una licencia publicada.`;
  actualizarNav();
}

function sparkline(d) {
  const W = 96;
  const H = 30;
  const n = d.fecha_hora.length;
  const vals = [...d.pronostico, ...d.real.filter((v) => v != null)];
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const x = (i) => (i / (n - 1)) * W;
  const y = (v) => 2 + (1 - (v - lo) / (hi - lo || 1)) * (H - 4);
  const real = d.real.slice(0, d.i_origen + 1).map((v, i) => (v == null ? '' : `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`)).join('');
  const pron = d.pronostico.map((v, i) => (i < d.i_origen ? '' : `${i === d.i_origen ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`)).join('');
  return `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" aria-hidden="true" focusable="false">`
    + `<line x1="${x(d.i_ahora).toFixed(1)}" x2="${x(d.i_ahora).toFixed(1)}" y1="0" y2="${H}" class="g-eje"/>`
    + `<path d="${real}" class="sp-real"/><path d="${pron}" class="sp-pron"/></svg>`;
}

function pintarAreasAhora() {
  const lista = S.areas.length ? S.areas : AREAS_RESPALDO;
  const repaso = A.fecha ? { fecha: A.fecha, hora: A.hora } : null;
  $('#ahAreas').innerHTML = lista.map((a) => {
    const d = A.datos.get(a.id);
    const info = INFO_AREA[a.id] || { letra: a.nombre[0] };
    const actual = a.id === A.area;
    let cuerpo = `<span class="v">${A.sinDatos ? 'Sin datos por ahora' : 'Calculando…'}</span>`;
    if (d) {
      const vivo = d.modo === 'en_vivo';
      cuerpo = `<span class="v">Ahora <b>${mw(d.cifra_ahora.valor)}</b><span class="unidad"> MW${d.cifra_ahora.fuente === 'real' ? '' : ' (pron.)'}</span></span>`
        + `<span class="v pico-area">${vivo ? 'Pico de hoy' : 'Pico 24 h'}: <b>${mw(d.pico.valor)}</b> MW · ${esc(diaCorto(d.pico.fecha_hora))} ${esc(horaDe(d.pico.fecha_hora))}</span>`
        + sparkline(d);
    }
    return `<a class="area" href="${rutaAhora(a.id, repaso, { modelo: A.modelo })}"${actual ? ' aria-current="true"' : ''}>`
      + `<span class="nom"><em aria-hidden="true">${esc(info.letra)}</em>${esc(a.nombre)}</span>${cuerpo}</a>`;
  }).join('');
}

function kpiHtml({ clase = '', sw = 'pron', k, n, d, unidad = 'MW' }) {
  return `<div class="kpi ${clase}"><p class="k">${sw ? `<span class="sw ${sw}" aria-hidden="true"></span>` : ''}${k}</p>`
    + `<p class="n">${n}${unidad ? `<small>${unidad}</small>` : ''}</p><p class="d">${d}</p></div>`;
}

function pintarCifras(d) {
  const vivo = d.modo === 'en_vivo';
  const c = d.cifra_ahora;
  const html = [];
  const dijimos = d.ayer && d.ayer.fecha_hora === c.fecha_hora ? `. Se pronosticó ${mw(d.ayer.pronostico)} (${rangoTxt(d.ayer.inferior, d.ayer.superior)}): ${d.ayer.dentro ? 'dentro' : 'fuera'} del rango` : '';
  html.push(kpiHtml({
    sw: c.fuente === 'real' ? 'real' : 'pron',
    k: `Ahora · ${esc(horaDe(c.fecha_hora))}`,
    n: mw(c.valor),
    d: c.fuente === 'real' ? `Dato del COES${dijimos}` : `Pronóstico, rango ${rangoTxt(c.inferior, c.superior)} · el real llega mañana`,
  }));
  const u = d.en_1h;
  html.push(u ? kpiHtml({
    k: `En 1 hora · ${esc(horaDe(u.fecha_hora))}`,
    n: mw(u.valor),
    d: `Rango ${rangoTxt(u.inferior, u.superior)}${u.fuente === 'pronostico_1h' ? ' · a\u00a01\u00a0h' : ''}`,
  }) : kpiHtml({ clase: 'kpi-vacio', k: 'En 1 hora', n: '—', d: 'Sin pronóstico para esa hora', unidad: '' }));
  const p = d.pico;
  const yaPaso = vivo && p.fecha_hora < d.ahora;
  const dia = d.origen.slice(0, 10);
  const escenario = !vivo && dia >= FECHA_MIN && dia <= FECHA_MAX
    ? ` <a class="kpi-enlace" href="${rutaDetalle(A.area, { fecha: dia, hora: horaDe(d.origen) }, 'escenarios')}">¿Y si hace más calor?</a>` : '';
  html.push(kpiHtml({
    clase: 'dest',
    k: vivo ? 'Pico de hoy' : 'Pico de las próximas 24 h',
    n: mw(p.valor),
    d: `${esc(fechaDiaMes(p.fecha_hora))}, ${esc(horaDe(p.fecha_hora))} · rango ${rangoTxt(p.inferior, p.superior)}${yaPaso ? ' · según el pronóstico, ya pasó' : ''}${escenario}`,
  }));
  html.push(d.manana ? kpiHtml({
    k: 'Mañana a esta hora',
    n: mw(d.manana.valor),
    d: `${firmado(d.manana.valor - c.valor)} MW frente a ahora`,
  }) : kpiHtml({ clase: 'kpi-vacio', k: 'Mañana a esta hora', n: '—', unidad: '', d: d.modo === 'en_vivo' ? 'Se emite mañana hacia las 10:00, cuando el COES publique la demanda de hoy' : esc(d.manana_motivo || 'Todavía no se emite') }));
  const r = d.rampa;
  html.push(r ? kpiHtml({
    sw: null,
    k: 'Mayor subida en 1 hora',
    n: `+${mw(r.subida_mw)}`,
    d: `${esc(horaDe(r.desde))}–${esc(horaDe(r.hasta))} ${esc(diaCorto(r.hasta))} · `
      + (r.fuerte ? `<span class="marca-estado fuerte">${ICONO.ojo}rampa fuerte</span>` : 'habitual')
      + (r.umbral_mw != null ? ` (umbral ${mw(r.umbral_mw)})` : ''),
  }) : kpiHtml({ sw: null, clase: 'kpi-vacio', k: 'Mayor subida en 1 hora', n: '—', unidad: '', d: 'La demanda no sube en ninguna hora de la ventana' }));
  $('#ahCifras').innerHTML = html.join('');
}

// El gráfico principal: lo real hasta el último dato, el pronóstico fino (pasado) y grueso (futuro), su rango,
// la referencia, «ahora», y anotados sobre la curva el pico, la mayor subida y mañana a esta hora.
function graficoAhora(el, d) {
  el._dibujar = () => graficoAhora(el, d);
  const W = Math.max(280, Math.round(el.clientWidth || 600));
  const movil = W < 560;
  const H = movil ? 260 : (innerHeight < 800 ? 270 : (innerHeight < 900 ? 300 : 330));
  const m = { l: movil ? 42 : 52, r: movil ? 10 : 18, t: 32, b: 34 };
  const n = d.fecha_hora.length;
  const N = n - 1;
  const io = d.i_origen;
  const ia = d.i_ahora;
  const vivo = d.modo === 'en_vivo';
  const despues = !vivo && A.despues && d.real_despues;
  const vals = [];
  for (let i = 0; i < n; i += 1) {
    vals.push(d.inferior[i], d.superior[i]);
    if (d.real[i] != null) vals.push(d.real[i]);
    if (despues && d.real_despues[i] != null) vals.push(d.real_despues[i]);
    if (A.ref && d.referencia[i] != null) vals.push(d.referencia[i]);
  }
  let lo = Math.min(...vals);
  let hi = Math.max(...vals);
  const pad = (hi - lo) * 0.08 || 10;
  lo -= pad;
  hi += pad * 1.8;
  const x = (i) => m.l + (i / N) * (W - m.l - m.r);
  const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const p = (i, v) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`;
  const linea = (vals2, desde, hasta) => {
    let s = '';
    let abierto = false;
    for (let i = desde; i <= hasta; i += 1) {
      const v = vals2[i];
      if (v == null) { abierto = false; continue; }
      s += `${abierto ? 'L' : 'M'}${p(i, v)}`;
      abierto = true;
    }
    return s;
  };
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" aria-hidden="true" focusable="false">`;
  s += `<rect class="g-futuro" x="${x(io).toFixed(1)}" y="${m.t - 22}" width="${(x(N) - x(io)).toFixed(1)}" height="${H - m.b - m.t + 22}"/>`;
  const rotulo = movil ? 'Pronóstico' : (vivo ? 'Pronóstico: el real todavía no se publica' : 'Próximas 24 horas (pronóstico)');
  s += `<text class="g-texto medio" x="${(x(io) + 8).toFixed(1)}" y="${m.t - 8}">${esc(rotulo)}</text>`;
  marcas(lo, hi, movil ? 3 : 4).filter((t) => y(t) >= m.t - 2 && y(t) <= H - m.b + 1).forEach((t) => {
    s += `<line class="g-rejilla" x1="${m.l}" x2="${W - m.r}" y1="${y(t).toFixed(1)}" y2="${y(t).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 8}" y="${(y(t) + 4).toFixed(1)}" text-anchor="end">${mw(t)}</text>`;
  });
  s += `<text class="g-texto" x="${m.l - 8}" y="${m.t - 8}" text-anchor="end">MW</text>`;
  s += `<line class="g-eje" x1="${m.l}" x2="${W - m.r}" y1="${H - m.b}" y2="${H - m.b}"/>`;
  // Rótulos de hora cada 3, 6 o 12 h: los que quepan con al menos 48 px entre uno y otro
  const paso = [6, 12, 24].find((k) => (k * (W - m.l - m.r)) / N >= 48) || 24;
  for (let i = 0; i <= N; i += 1) {
    const fh = d.fecha_hora[i];
    const medianoche = horaDe(fh) === '00:00';
    if (medianoche && i > 0 && !(ia !== io && Math.abs(i - io) <= 1)) s += `<line class="g-eje" x1="${x(i).toFixed(1)}" x2="${x(i).toFixed(1)}" y1="${m.t}" y2="${H - m.b}"/>`;
    if (i % paso || Math.abs(x(i) - x(ia)) < 52) continue;
    s += `<line class="g-eje" x1="${x(i).toFixed(1)}" x2="${x(i).toFixed(1)}" y1="${H - m.b}" y2="${H - m.b + 4}"/>`;
    s += `<text class="g-texto" x="${x(i).toFixed(1)}" y="${H - m.b + 17}" text-anchor="middle">${esc(medianoche ? diaCorto(fh) : horaDe(fh))}</text>`;
  }
  const banda = d.superior.map((v, i) => `${i ? 'L' : 'M'}${p(i, v)}`).join('')
    + d.inferior.map((v, i) => [i, v]).reverse().map(([i, v]) => `L${p(i, v)}`).join('');
  s += `<path class="g-banda" d="${banda}Z"/>`;
  if (A.ref) s += `<path class="ln-referencia" d="${linea(d.referencia, 0, N)}"/>`;
  const real = linea(d.real, 0, io);
  if (real) s += `<path class="g-real-relleno" d="${real}L${x(io).toFixed(1)},${H - m.b}L${x(0).toFixed(1)},${H - m.b}Z"/>`;
  s += `<path class="ln-pronostico fina" d="${linea(d.pronostico, 0, io)}"/>`;
  if (real) s += `<path class="ln-real" d="${real}"/>`;
  s += `<path class="ln-pronostico" d="${linea(d.pronostico, io, N)}"/>`;
  if (despues) s += `<path class="ln-despues" d="${linea(d.real_despues.map((v, i) => (i === io ? d.real[io] : v)), io, N)}"/>`;
  const r = d.rampa;
  const ir = r ? d.fecha_hora.indexOf(r.desde) : -1;
  if (ir >= 0 && ir + 2 <= N) {
    const tramo = `M${p(ir, d.pronostico[ir])}L${p(ir + 1, d.pronostico[ir + 1])}L${p(ir + 2, d.pronostico[ir + 2])}`;
    s += `<path class="g-rampa-fondo" d="${tramo}"/><path class="g-rampa${r.fuerte ? ' fuerte' : ''}" d="${tramo}"/>`;
    if (!movil) {
      s += `<text class="g-texto medio" x="${(x(ir + 1) - 10).toFixed(1)}" y="${(y(d.pronostico[ir + 1]) + 4).toFixed(1)}" text-anchor="end">+${mw(r.subida_mw)} MW en 1 h${r.fuerte ? ' · rampa fuerte' : ''}</text>`;
    }
  }
  if (ia !== io) {
    s += `<line class="g-corte" x1="${x(io).toFixed(1)}" x2="${x(io).toFixed(1)}" y1="${m.t - 22}" y2="${H - m.b}"/>`;
    if (!movil) s += `<text class="g-texto medio" x="${(x(io) - 6).toFixed(1)}" y="${H - m.b - 8}" text-anchor="end">Último dato real</text>`;
  }
  s += `<line class="g-ahora" x1="${x(ia).toFixed(1)}" x2="${x(ia).toFixed(1)}" y1="${m.t - 22}" y2="${H - m.b}"/>`;
  const anchoPastilla = 76;
  const gx = Math.min(Math.max(x(ia) - anchoPastilla / 2, m.l), W - m.r - anchoPastilla);
  s += `<rect class="g-pastilla" x="${gx.toFixed(1)}" y="${H - m.b + 4}" width="${anchoPastilla}" height="20" rx="10"/>`;
  s += `<text class="g-pastilla-texto" x="${(gx + anchoPastilla / 2).toFixed(1)}" y="${H - m.b + 18}" text-anchor="middle">Ahora ${esc(horaDe(d.ahora))}</text>`;
  const vAhora = d.real[ia] != null ? d.real[ia] : d.pronostico[ia];
  s += `<circle class="g-punto${d.real[ia] != null ? ' real' : ''}" cx="${x(ia).toFixed(1)}" cy="${y(vAhora).toFixed(1)}" r="5"/>`;
  const anotar = (i, v, texto) => {
    const izq = x(i) + 12 + texto.length * 6.8 > W - 2; // si el rótulo no cabe a la derecha, va a la izquierda
    return `<circle class="g-punto" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="5"/>`
      + `<text class="g-texto fuerte" x="${(x(i) + (izq ? -9 : 9)).toFixed(1)}" y="${(y(v) - 10).toFixed(1)}" text-anchor="${izq ? 'end' : 'start'}">${esc(texto)}</text>`;
  };
  const ip = d.fecha_hora.indexOf(d.pico.fecha_hora);
  if (ip >= 0) s += anotar(ip, d.pico.valor, `Pico ${mw(d.pico.valor)} · ${horaDe(d.pico.fecha_hora)}`);
  const im = d.manana ? d.fecha_hora.indexOf(d.manana.fecha_hora) : -1;
  if (!movil && im >= 0 && Math.abs(im - ip) > 10) s += anotar(im, d.manana.valor, `Mañana ${horaDe(d.manana.fecha_hora)}: ${mw(d.manana.valor)}`);
  s += `<line class="g-cruz" x1="0" x2="0" y1="${m.t - 22}" y2="${H - m.b}" visibility="hidden"/>`;
  s += '<circle class="g-punto g-cursor" cx="0" cy="0" r="4" visibility="hidden"/>';
  s += '</svg>';
  el.innerHTML = `${s}<div class="tip" hidden></div>`;
  el._g = { x, y, N, m, W, d, despues };
  el.setAttribute('aria-label', `Gráfico de la demanda del ${nombreArea(A.area)}. Usa las flechas para recorrerlo.`);
}

function tipAhora(i) {
  const el = $('#ahLienzo');
  const g = el._g;
  if (!g) return;
  const d = g.d;
  const k = Math.max(0, Math.min(g.N, i));
  el._i = k;
  const cruz = $('.g-cruz', el);
  const cursor = $('.g-cursor', el);
  cruz.setAttribute('x1', g.x(k));
  cruz.setAttribute('x2', g.x(k));
  cruz.setAttribute('visibility', 'visible');
  cursor.setAttribute('cx', g.x(k));
  cursor.setAttribute('cy', g.y(d.pronostico[k]));
  cursor.setAttribute('visibility', 'visible');
  const fh = d.fecha_hora[k];
  const futuro = k > d.i_origen;
  const real = !futuro ? d.real[k] : (g.despues ? d.real_despues[k] : null);
  const error = real != null ? d.pronostico[k] - real : null;
  const emision = d.tipo ? TIPO_TXT[d.tipo[k]] || '' : `Emitido el ${fechaDiaMes(sumarDias(fh.slice(0, 10), -1))} a las ${horaDe(fh)} (24 h antes)`;
  const fila = (sw, nombre, valor) => `<tr><td>${sw ? `<span class="sw ${sw}"></span>` : ''}${esc(nombre)}</td><td>${valor}</td></tr>`;
  const tip = $('.tip', el);
  tip.innerHTML = `<b>${esc(capital(diaCorto(fh)))}, ${esc(horaDe(fh))}</b><div class="muted">${esc(emision)}</div><table>`
    + (real != null ? fila('real', futuro ? 'Real (lo que pasó después)' : 'Real', `${mw(real)} MW`) : '')
    + fila('pron', 'Pronóstico', `${mw(d.pronostico[k])} MW`)
    + fila('banda', `Rango del ${d.nivel_rango_pct} %`, `${mw(d.inferior[k])}–${mw(d.superior[k])}`)
    + (A.ref && d.referencia[k] != null ? fila('ref', 'Referencia', `${mw(d.referencia[k])} MW`) : '')
    + (error != null ? fila(null, 'Error', `${firmado(error)} MW`) : '')
    + '</table>';
  tip.hidden = false;
  const ancho = tip.offsetWidth || 190;
  let izq = g.x(k) + 14;
  if (izq + ancho > el.clientWidth) izq = Math.max(4, g.x(k) - ancho - 14);
  tip.style.left = `${izq}px`;
}

function ocultarTipAhora() {
  const el = $('#ahLienzo');
  if (!el._g) return;
  $('.tip', el).hidden = true;
  $('.g-cruz', el).setAttribute('visibility', 'hidden');
  $('.g-cursor', el).setAttribute('visibility', 'hidden');
}

function descripcionAhora(d) {
  const a = nombreArea(A.area);
  const ini = d.fecha_hora[0];
  const fin = d.fecha_hora[d.fecha_hora.length - 1];
  const c = d.cifra_ahora;
  let t = `Demanda del ${a} desde el ${fechaDiaMes(ini)} a las 00:00 hasta el ${fechaDiaMes(fin)} a las ${horaDe(fin)}. `;
  if (c.fuente === 'real') {
    const dentro = d.ayer && d.ayer.fecha_hora === c.fecha_hora ? (d.ayer.dentro ? ', dentro del rango que se pronosticó' : ', fuera del rango que se pronosticó') : '';
    t += `Ahora (${horaDe(c.fecha_hora)}) la demanda es ${mw(c.valor)} MW${dentro}. `;
  } else {
    t += `Lo real llega hasta el ${finTxt(d.datos_hasta).largo}. Ahora (${horaDe(c.fecha_hora)}) se pronostican ${mw(c.valor)} MW, entre ${mw(c.inferior)} y ${mw(c.superior)}. `;
  }
  t += `El pico ${d.modo === 'en_vivo' ? 'de hoy' : 'de las próximas 24 horas'} sería ${mw(d.pico.valor)} MW el ${fechaDiaMes(d.pico.fecha_hora)} a las ${horaDe(d.pico.fecha_hora)}`;
  if (d.rampa) t += `; la mayor subida, ${mw(d.rampa.subida_mw)} MW en una hora desde las ${horaDe(d.rampa.desde)}${d.rampa.fuerte ? ' (rampa fuerte)' : ''}`;
  return `${t}.`;
}

function pintarTablaAhora(d) {
  const filas = d.fecha_hora.map((fh, i) => {
    const real = i <= d.i_origen ? d.real[i] : (A.despues && d.real_despues ? d.real_despues[i] : null);
    return `<tr${i === d.i_ahora ? ' class="fila-elegida"' : ''}><th scope="row">${esc(diaCorto(fh))} ${esc(horaDe(fh))}</th>`
      + `<td>${real == null ? '—' : mw(real)}</td><td>${mw(d.pronostico[i])}</td><td>${mw(d.inferior[i])}–${mw(d.superior[i])}</td>`
      + `<td>${d.referencia[i] == null ? '—' : mw(d.referencia[i])}</td></tr>`;
  }).join('');
  $('#ahTabla').innerHTML = '<div class="tabla-scroll" tabindex="0" role="region" aria-label="Datos del gráfico"><table class="t">'
    + `<caption class="visually-hidden">Demanda del ${esc(nombreArea(A.area))} en MW: real, pronóstico a 24 h, rango del ${d.nivel_rango_pct} % y referencia</caption>`
    + `<thead><tr><th scope="col">Hora</th><th scope="col">Real</th><th scope="col">Pronóstico</th><th scope="col">Rango ${d.nivel_rango_pct} %</th><th scope="col">Referencia</th></tr></thead>`
    + `<tbody>${filas}</tbody></table></div>`;
}

function descargarCsvAhora() {
  const d = A.datos.get(A.area);
  if (!d) return;
  const filas = [['inicio_periodo', 'pronostico_mw', `rango_${d.nivel_rango_pct}_inferior_mw`, `rango_${d.nivel_rango_pct}_superior_mw`, 'error_mw']];
  d.fecha_hora.forEach((fh, i) => {
    const real = i <= d.i_origen ? d.real[i] : (d.real_despues ? d.real_despues[i] : null);
    filas.push([fh, d.pronostico[i], d.inferior[i], d.superior[i], real == null ? '' : (d.pronostico[i] - real).toFixed(1)]);
  });
  const cabeza = `# Curva · ${nombreArea(A.area)} · ${d.modelo_nombre} · último dato real hasta ${d.datos_hasta} (hora de Lima)\n`
    + '# pronostico_mw: pronóstico directo a 24 h, emitido 24 h antes de cada periodo; error_mw = pronóstico − real\n';
  const blob = new Blob([cabeza + filas.map((f) => f.join(',')).join('\n')], { type: 'text/csv;charset=utf-8' });
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(blob);
  enlace.download = `curva-${A.area}-${d.origen.replace(':', '')}.csv`;
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
}

// Al mostrar lo que pasó después, también cómo le fue en el día completo (en repaso ya pasó)
function pintarDiaCompleto(d) {
  const p = $('#ahDiaCompleto');
  const f = d.error_dia;
  p.hidden = !(d.modo === 'repaso' && A.despues && f);
  if (p.hidden) return;
  const ref = NOMBRE_REF[d.referencia_nombre] || 'la referencia simple';
  p.innerHTML = `El día completo: el modelo se equivocó <b>${nf1.format(f.mae_modelo)} MW</b> en promedio; repetir ${esc(ref)}, `
    + `<b>${f.mae_referencia == null ? '—' : `${nf1.format(f.mae_referencia)} MW`}</b>. ${frasesMejora(f.mae_modelo, f.mae_referencia, 'la referencia')}`;
}

function pintarAyer(d) {
  const y = d.ayer;
  const cont = $('#ahAyer');
  const hoy = y && y.fecha_hora.slice(0, 10) === d.ahora.slice(0, 10);
  $('#ahAyerTit').textContent = hoy || !y ? 'Lo que dijimos ayer para esta hora' : 'Lo que dijimos para ayer a esta hora';
  if (!y) {
    cont.innerHTML = '<p class="sub">Todavía no hay un pronóstico verificado contra el real para esta hora.</p>';
    return;
  }
  const dif = y.diferencia;
  const porc = (100 * Math.abs(dif)) / y.real;
  const fuente = y.fuente === 'historial'
    ? `Historial · modelo ${esc(d.modelo_nombre.replace(/\s*\(.*\)\s*$/, '').toLowerCase())}`
    : y.fuente === 'reconstruido'
      ? 'Registro en vivo · reconstruido: se calculó después de conocerse el real, con los datos que habría tenido'
      : 'Registro en vivo · emitido antes de conocerse el real';
  cont.innerHTML = `<p class="sub">Para las ${esc(horaDe(y.fecha_hora))} ${hoy ? 'de hoy' : `del ${esc(fechaDiaMes(y.fecha_hora))}`}, emitido el ${esc(fechaDiaMes(y.emitido))} a las ${esc(horaDe(y.emitido))} (24 h antes).</p>`
    + `<dl class="dijimos"><div><dt><span class="sw pron" aria-hidden="true"></span>Dijimos</dt><dd>${mw(y.pronostico)}<small>MW</small></dd></div>`
    + `<div><dt><span class="sw real" aria-hidden="true"></span>Fue</dt><dd>${mw(y.real)}<small>MW</small></dd></div></dl>`
    + `<dl class="pares"><dt>Diferencia</dt><dd>${firmado(dif)} MW (${nf1.format(porc)} %)</dd><dt>Rango del ${d.nivel_rango_pct} %</dt><dd>${mw(y.inferior)} – ${mw(y.superior)} MW</dd></dl>`
    + `<div class="veredicto ${y.dentro ? 'bien' : 'ojo'}">${y.dentro ? ICONO.bien : ICONO.ojo}<span>Lo real cayó ${y.dentro ? 'dentro' : 'fuera'} del rango. ${Math.abs(dif) < 0.5 ? 'Acertó.' : `${dif > 0 ? 'Sobrestimó' : 'Subestimó'} por ${mw(Math.abs(dif))} MW.`}</span></div>`
    + `<p class="nota-pie"><span class="etiqueta-fuente">${fuente}</span></p>`;
}

function barrasCmp(modelo, referencia) {
  const tope = Math.max(modelo, referencia || 0) || 1;
  const fila = (nombre, v, clase) => `<div class="barra-cmp"><span>${nombre}</span><span class="pista"><i class="${clase}" style="width:${((100 * v) / tope).toFixed(1)}%"></i></span><b>${nf1.format(v)} MW</b></div>`;
  return fila('Modelo', modelo, 'i-pron') + (referencia != null ? fila('Referencia', referencia, 'i-ref') : '');
}

function frasesMejora(modelo, referencia, nombreRef) {
  if (referencia == null || !referencia) return '';
  const mejora = (100 * (referencia - modelo)) / referencia;
  if (Math.abs(mejora) < 1) return `Se equivocó lo mismo que repetir ${nombreRef}.`;
  return `Se equivocó <b>${nf0.format(Math.abs(mejora))} % ${mejora > 0 ? 'menos' : 'más'}</b> que repetir ${nombreRef}.`;
}

// Cobertura del rango frente a lo que promete: el semáforo de ISO-NE aplicado a la meta del rango.
function veredictoCobertura(cubrio, meta) {
  const dif = cubrio - meta;
  if (Math.abs(dif) <= 2) return { clase: 'bien', texto: 'cumple lo que promete' };
  if (dif < -5) return { clase: 'mal', texto: 'queda corto', porque: 'el rango es más angosto de lo que debería' };
  if (dif < 0) return { clase: 'ojo', texto: 'queda algo corto' };
  if (dif > 5) return { clase: 'ojo', texto: 'es más ancho de lo necesario' };
  return { clase: 'ojo', texto: 'cubre algo más de lo que promete' };
}

function pintarBueno(d) {
  const cont = $('#ahBueno');
  const vivo = d.modo === 'en_vivo';
  const nombreRef = NOMBRE_REF[d.referencia_nombre] || 'la referencia simple';
  const bloques = [];
  const e = d.error_hasta_origen;
  if (e) {
    const titulo = vivo ? 'Ayer, el día completo' : `Ese día, hasta las ${horaDe(d.origen)}`;
    bloques.push(`<div class="bloque"><h3>${esc(titulo)}</h3>${barrasCmp(e.mae_modelo, e.mae_referencia)}<p class="sub">${frasesMejora(e.mae_modelo, e.mae_referencia, nombreRef)}</p></div>`);
  }
  if (!vivo && A.despues && d.error_dia) {
    const f = d.error_dia;
    bloques.push(`<div class="bloque"><h3>El día completo (ya pasó)</h3>${barrasCmp(f.mae_modelo, f.mae_referencia)}</div>`);
  } else if (!vivo && d.error_dia && bloques.length) {
    bloques[bloques.length - 1] = bloques[bloques.length - 1].replace(/<\/div>$/, '<p class="nota-pie">Marca «Mostrar lo que pasó después» para ver el error del día completo.</p></div>');
  }
  const extra = A.extra.get(`${A.area}|${d.modelo}`);
  if (extra && extra.tipo === 'seguimiento') {
    const t = extra.datos.total;
    const v = veredictoCobertura(t.cobertura_pct, extra.datos.meta_cobertura_pct);
    bloques.push(`<div class="bloque"><h3>En 2026, a 24 horas</h3>${barrasCmp(t.mae_modelo, t.mae_referencia)}`
      + `<p class="sub">${frasesMejora(t.mae_modelo, t.mae_referencia, NOMBRE_REF[extra.datos.referencia_nombre] || nombreRef)} Su rango del 90 % cubrió el <b>${nf1.format(t.cobertura_pct)} %</b> de las medias horas: ${esc(v.texto)}.</p></div>`);
  } else if (extra && extra.tipo === 'vivo') {
    const r = extra.datos.resumen.find((x) => x.horizonte === '24h' && x.grupo === 'en_vivo') || extra.datos.resumen.find((x) => x.horizonte === '24h');
    if (r) {
      const v = veredictoCobertura(r.cobertura_pct, extra.datos.nivel_rango_pct);
      bloques.push(`<div class="bloque"><h3>Desde el ${esc(fechaDiaMes(r.desde))}, ${r.grupo === 'en_vivo' ? 'en vivo' : 'reconstruido'}</h3>${barrasCmp(r.mae_modelo, r.mae_referencia)}`
        + `<div class="veredicto ${v.clase}">${ICONO[v.clase]}<span>Su rango del ${extra.datos.nivel_rango_pct} % cubrió el ${nf1.format(r.cobertura_pct)} % de las medias horas: ${esc(v.texto)}${v.porque ? `; ${esc(v.porque)}` : ''}.</span></div></div>`);
    }
  }
  bloques.push(`<p class="enlaces"><a class="btn-enlace" href="#/confianza/${encodeURIComponent(A.area)}">Ver la confianza mes a mes →</a></p>`);
  cont.innerHTML = bloques.join('');
}

async function cargarExtraAhora(d, turno) {
  const clave = `${A.area}|${d.modelo}`;
  if (A.extra.has(clave) && !d.modelo.startsWith('en_vivo:')) return;
  try {
    if (d.modelo.startsWith('en_vivo:')) {
      A.extra.set(clave, { tipo: 'vivo', datos: await api(`/en-vivo/${encodeURIComponent(A.area)}`) });
    } else {
      const q = new URLSearchParams({ horizonte: '24h', variante: 'M3' });
      if (hayVariosModelos()) q.set('modelo', d.modelo);
      A.extra.set(clave, { tipo: 'seguimiento', datos: await api(`/seguimiento/${encodeURIComponent(A.area)}?${q}`) });
    }
  } catch {
    return; // el bloque de 2026 es complementario: sin él, la tarjeta sigue con lo del día
  }
  if (turno === A.turno && A.datos.get(A.area) === d) pintarBueno(d);
}

function pintarOrigen(d) {
  const cont = $('#ahOrigen');
  const y = d.ayer;
  const repaso = A.fecha ? { fecha: A.fecha, hora: A.hora } : null;
  let html;
  if (d.modelo.startsWith('en_vivo:')) {
    html = `<p class="sub">${esc(d.modelo_nombre)}: un modelo fundacional de series de tiempo, ajustado a la demanda del SEIN con datos hasta 2024 y con los feriados de Perú. Cada mañana, con la demanda de ayer que publica el COES, pronostica las 48 medias horas de hoy. Queda registrado con su hora de emisión antes de conocerse el real y no se reescribe.</p>`;
  } else if (y && y.componentes && y.componentes.length) {
    const suma = y.componentes.reduce((t, c) => t + c.peso * (c.valores[0] || 0), 0);
    html = `<p class="sub">Modelo <b>${esc(d.modelo_nombre.replace(/\s*\(.*\)\s*$/, '').toLowerCase())}</b>: el de menor error en 2026. Lo que se dijo para las ${esc(horaDe(y.fecha_hora))}:</p>`
      + `<div class="formula">${y.componentes.map((c) => `${mw(c.valores[0])} × ${c.peso.toFixed(2)} <span class="muted">(${esc(c.nombre)})</span>`).join('<br>+ ')}<br>= <b>${mw(suma)} MW</b></div>`
      + '<p class="nota-pie">Pesos fijados con la validación de 2025 y aplicados tal cual a 2026. Usa solo la demanda y el calendario; no usa el clima.</p>';
  } else {
    const m = modeloPorId(d.modelo);
    html = `<p class="sub">Modelo <b>${esc(d.modelo_nombre)}</b>. ${esc((m && m.descripcion) || '')}</p>`;
  }
  html += '<p class="enlaces">'
    + (repaso && repaso.fecha >= FECHA_MIN && repaso.fecha <= FECHA_MAX ? `<a class="btn-enlace" href="${rutaDetalle(A.area, repaso, 'escenarios')}">¿Y si hace más calor? →</a>` : '')
    + `<a class="btn-enlace" href="${rutaDetalle(A.area, repaso, 'diagnostico')}">Diagnóstico completo</a>`
    + `<a class="btn-enlace" href="${rutaDetalle(A.area, repaso)}">${repaso && repaso.fecha <= FECHA_MAX ? 'Otro modelo u horizonte' : 'Explorar el historial con otro modelo'}</a>`
    + '<button type="button" class="btn-enlace" data-accion="ficha">Ficha técnica: modelo y datos</button></p>';
  cont.innerHTML = html;
}

// ---- Confianza ---------------------------------------------------------------------------------------------

const C = { area: 'centro', horizonte: '24h', mes: null, turno: 0, cache: new Map(), datos: null };

function mostrarConfianza(area, q) {
  C.area = area;
  if (['1h', '24h'].includes(q.get('horizonte'))) C.horizonte = q.get('horizonte');
  C.mes = /^\d{4}-\d{2}$/.test(q.get('mes') || '') ? q.get('mes') : (A.fecha && A.fecha.startsWith('2026') ? A.fecha.slice(0, 7) : C.mes);
  const llega = $('#vistaConfianza').hidden;
  mostrarVista('confianza');
  document.title = `${nombreArea(area)} · Confianza · Curva`;
  if (llega) window.scrollTo(0, 0);
  $('#cfAreas').innerHTML = (S.areas.length ? S.areas : AREAS_RESPALDO).map((a) => `<a href="#/confianza/${encodeURIComponent(a.id)}?horizonte=${C.horizonte}"${a.id === area ? ' aria-current="page"' : ''}>${esc(a.nombre)}</a>`).join('');
  $$('[data-cf-horizonte]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.cfHorizonte === C.horizonte)));
  cargarConfianza();
}

async function cargarConfianza() {
  const turno = ++C.turno;
  const { area, horizonte } = C;
  const m = hayVariosModelos() && S.modelo ? S.modelo : null;
  const clave = `${m}|${area}|${horizonte}`;
  $('#cfTitular').textContent = 'Calculando la confianza…';
  $('#vistaConfianza').classList.add('desactualizada');
  const q = new URLSearchParams({ horizonte, variante: 'M3' });
  if (m) q.set('modelo', m);
  const diagClave = `${S.modelo || ''}|${area}`;
  const [conf, vivo, diag] = await Promise.allSettled([
    C.cache.has(clave) ? Promise.resolve(C.cache.get(clave)) : api(`/confianza/${encodeURIComponent(area)}?${q}`),
    api(`/en-vivo/${encodeURIComponent(area)}`),
    S.diag.has(diagClave) ? Promise.resolve(S.diag.get(diagClave)) : api(`/diagnostico/${encodeURIComponent(area)}${m ? `?modelo=${encodeURIComponent(m)}` : ''}`),
  ]);
  if (turno !== C.turno) return;
  $('#vistaConfianza').classList.remove('desactualizada');
  if (conf.status === 'rejected') {
    if (conf.reason.estado === 0) mostrarError(conf.reason);
    $('#cfTitular').textContent = 'No pudimos calcular la confianza de esta área';
    $('#cfLead').textContent = textoError(conf.reason);
    ['#cfMes', '#cfCob', '#cfDia'].forEach((s) => { $(s).innerHTML = '<p class="vacio">Sin datos por ahora.</p>'; });
    return;
  }
  limpiarError();
  C.cache.set(clave, conf.value);
  if (diag.status === 'fulfilled') S.diag.set(diagClave, diag.value);
  C.datos = { conf: conf.value, vivo: vivo.status === 'fulfilled' ? vivo.value : null, diag: diag.status === 'fulfilled' ? diag.value : null };
  const u = C.datos.vivo && C.datos.vivo.ultimo;
  if (u) {
    const fin = finTxt(u.datos_hasta);
    pintarEstado({ modo: 'vivo', texto: `Datos del COES al ${fin.corto}`, corto: `COES ${fin.corto.replace(', ', ' ')}`, titulo: `Datos reales del COES hasta el ${fin.largo}` });
  } else {
    pintarEstado({ modo: 'repaso', texto: 'Prueba de 2026', titulo: 'El error medido en la prueba de 2026' });
  }
  pintarConfianzaPantalla();
}

function pintarConfianzaPantalla() {
  const { conf, vivo, diag } = C.datos;
  const seg = conf.seguimiento;
  const area = nombreArea(C.area);
  const h = C.horizonte === '1h' ? '1 hora' : '24 horas';
  const nombreRef = NOMBRE_REF[seg.referencia_nombre] || 'la referencia simple';
  const n = seg.meses.length;
  const ganados = seg.meses.filter((x) => x.mae_modelo < x.mae_referencia).length;
  const t = seg.total;
  const mejora = (100 * (t.mae_referencia - t.mae_modelo)) / t.mae_referencia;
  const meta = seg.meta_cobertura_pct;
  const bajos = seg.meses.filter((x) => x.cobertura_pct < meta - 2);
  const vCob = veredictoCobertura(t.cobertura_pct, meta);
  const rVivo = vivo && vivo.resumen ? (vivo.resumen.find((x) => x.horizonte === '24h' && x.grupo === 'en_vivo') || vivo.resumen.find((x) => x.horizonte === '24h')) : null;
  $('#cfTitular').textContent = ganados === n
    ? `En 2026 se equivocó menos que la referencia los ${n} meses.`
    : `En 2026 le ganó a la referencia en ${ganados} de ${n} meses.`;
  let lead = `${esc(area)}, a ${h}: error medio de <b>${nf1.format(t.mae_modelo)} MW</b> (${nf1.format(conf.mape_pct)} % de la demanda), ${nf0.format(Math.abs(mejora))} % ${mejora >= 0 ? 'menos' : 'más'} que repetir ${esc(nombreRef)}. `
    + `El rango del ${nf0.format(meta)} % cubrió el <b>${nf1.format(t.cobertura_pct)} %</b> en el año${bajos.length ? `, pero quedó corto en ${esc(bajos.map((x) => mesLargo(x.mes)).join(', '))}` : ''}. `;
  if (rVivo) {
    const vv = veredictoCobertura(rVivo.cobertura_pct, vivo.nivel_rango_pct);
    lead += `En vivo, desde el ${esc(fechaDiaMes(rVivo.desde))}, el rango del ${vivo.nivel_rango_pct} % cubrió el <b>${nf1.format(rVivo.cobertura_pct)} %</b>: ${esc(vv.texto)}. `;
  }
  lead += 'Todo se mide con pronósticos que el modelo no vio al entrenar; 2026 sí se usó para elegir el modelo.';
  $('#cfLead').innerHTML = lead;

  const ac = conf.acierto;
  $('#cfStats').innerHTML = [
    `<div class="stat"><p class="k">Error medio 2026</p><p class="n">${nf1.format(t.mae_modelo)}<small> MW</small></p><p class="d">${nf1.format(conf.mape_pct)} % de la demanda (MAPE)</p></div>`,
    `<div class="stat"><p class="k">Frente a la referencia</p><p class="n">${mejora >= 0 ? '−' : '+'}${nf0.format(Math.abs(mejora))}<small> %</small></p><p class="d">${nf1.format(t.mae_referencia)} MW la referencia</p></div>`,
    `<div class="stat"><p class="k">Cobertura del rango</p><p class="n">${nf1.format(t.cobertura_pct)}<small> %</small></p><p class="d">meta ${nf0.format(meta)} %</p><p class="estado-meta ${vCob.clase}">${ICONO[vCob.clase]}${esc(capital(vCob.texto))}</p></div>`,
    ac ? `<div class="stat"><p class="k">Hora del pico (±1 h)</p><p class="n">${nf1.format(ac.pct_hora)}<small> %</small></p><p class="d">de ${nf0.format(ac.dias)} días; referencia ${nf1.format(ac.pct_hora_referencia)} %</p></div>`
      : `<div class="stat"><p class="k">Medias horas medidas</p><p class="n">${nf0.format(t.periodos)}</p><p class="d">de 2026</p></div>`,
    statNino(diag),
  ].join('');

  pintarMesAMes(seg, conf);
  pintarCoberturaConf(seg);
  pintarVivoConf(vivo, conf);
  pintarDiaADia(conf);
  pintarSesgoConf(conf);
  pintarNinoConf(diag);
  pintarMundo(conf);
  $('#cfPie').textContent = `Modelo: ${(modeloPorId(conf.modelo) || { nombre: conf.modelo }).nombre}. Prueba de 2026: del 1 de enero al ${fechaCorta((S.resumen && S.resumen.fechas_corte.prueba_hasta) || '2026-10-15')}, con todas las medias horas que tienen dato real. El registro en vivo usa otro modelo (${(vivo && vivo.modelo) || 'Chronos-2 ajustado'}): sus cifras van aparte.`;
}

function statNino(diag) {
  const regs = diag && diag.mae_por_regimen;
  if (!regs || !regs.length) return '';
  const peor = regs.reduce((a, b) => (b.modelo > a.modelo ? b : a));
  const gana = regs.filter((r) => r.modelo < r.referencia).length;
  return `<div class="stat"><p class="k">Con El Niño, donde más yerra</p><p class="n">${nf1.format(peor.modelo)}<small> MW</small></p>`
    + `<p class="d">${esc(REGIMEN[peor.regimen] || peor.regimen)} · le gana a la referencia en ${gana === regs.length ? `las ${regs.length}` : `${gana} de ${regs.length}`} fases</p></div>`;
}

function pintarMesAMes(seg, conf) {
  const cont = $('#cfMes');
  const meses = seg.meses;
  const ganados = meses.filter((x) => x.mae_modelo < x.mae_referencia).length;
  const peor = meses.reduce((a, b) => (b.mae_modelo > a.mae_modelo ? b : a));
  const hasta = S.resumen && S.resumen.fechas_corte.prueba_hasta;
  const ultimo = meses[meses.length - 1].mes;
  const parcial = hasta && hasta.slice(0, 7) === ultimo && Number(hasta.slice(8, 10)) < 28 ? ` ${capital(mesLargo(ultimo))} llega hasta el día ${Number(hasta.slice(8, 10))}.` : '';
  cont.innerHTML = `<p class="sub">Error medio absoluto en MW (menos es mejor), a ${C.horizonte === '1h' ? '1 hora' : '24 horas'}. Solo pronósticos que el modelo no vio al entrenar.</p>`
    + `<div class="leyenda"><span class="it"><span class="mk pron"></span>Modelo</span><span class="it"><span class="mk ref" style="border-top-style:solid"></span>Referencia: ${esc((TITULO_REF[seg.referencia_nombre] || '').toLowerCase())}</span></div>`
    + '<div id="cfMesG" class="chart lienzo" style="min-height:220px"></div>'
    + `<p class="sub">Le ganó a la referencia en <b>${ganados} de ${meses.length}</b> meses. Peor mes: ${esc(mesLargo(peor.mes))} (${nf1.format(peor.mae_modelo)} MW).${esc(parcial)}</p>`
    + `<details class="datos"><summary>Ver la tabla mes a mes</summary><div class="tabla-scroll" tabindex="0" role="region" aria-label="Error mes a mes"><table class="t"><caption class="visually-hidden">Error medio y cobertura por mes de 2026</caption><thead><tr><th scope="col">Mes</th><th scope="col">Modelo (MW)</th><th scope="col">Referencia (MW)</th><th scope="col">¿Le ganó?</th><th scope="col">Cobertura</th><th scope="col">Medias horas</th></tr></thead><tbody>`
    + meses.map((x) => `<tr><th scope="row">${esc(capital(mesLargo(x.mes)))}</th><td>${nf1.format(x.mae_modelo)}</td><td>${nf1.format(x.mae_referencia)}</td><td>${x.mae_modelo < x.mae_referencia ? 'sí' : 'no'}</td><td>${nf1.format(x.cobertura_pct)} %</td><td>${nf0.format(x.periodos)}</td></tr>`).join('')
    + `<tr><th scope="row">2026</th><td><b>${nf1.format(seg.total.mae_modelo)}</b></td><td><b>${nf1.format(seg.total.mae_referencia)}</b></td><td></td><td><b>${nf1.format(seg.total.cobertura_pct)} %</b></td><td>${nf0.format(seg.total.periodos)}</td></tr></tbody></table></div></details>`;
  barrasMeses($('#cfMesG'), meses);
  void conf;
}

function barrasMeses(el, meses) {
  el._dibujar = () => barrasMeses(el, meses);
  const W = Math.max(280, el.clientWidth || 600);
  const H = W < 560 ? 200 : 230;
  const m = { l: 44, r: 8, t: 14, b: 28 };
  const tope = Math.max(...meses.map((x) => Math.max(x.mae_referencia, x.mae_modelo))) * 1.1;
  const y = (v) => m.t + (1 - v / tope) * (H - m.t - m.b);
  const bw = (W - m.l - m.r) / meses.length;
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Error medio por mes de 2026, modelo frente a la referencia">`;
  marcas(0, tope, 4).forEach((v) => {
    s += `<line class="${v === 0 ? 'g-eje' : 'g-rejilla'}" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${mw(v)}</text>`;
  });
  s += `<text class="g-texto" x="${m.l - 6}" y="10" text-anchor="end">MW</text>`;
  meses.forEach((x, j) => {
    const cx = m.l + j * bw + bw / 2;
    const w = Math.min(14, (bw - 10) / 2);
    s += `<rect class="g-barra-modelo" x="${(cx - w - 1).toFixed(1)}" y="${y(x.mae_modelo).toFixed(1)}" width="${w.toFixed(1)}" height="${(y(0) - y(x.mae_modelo)).toFixed(1)}" rx="3"/>`;
    s += `<rect class="g-barra-ref" x="${(cx + 1).toFixed(1)}" y="${y(x.mae_referencia).toFixed(1)}" width="${w.toFixed(1)}" height="${(y(0) - y(x.mae_referencia)).toFixed(1)}" rx="3"/>`;
    s += `<text class="g-texto" x="${cx.toFixed(1)}" y="${H - m.b + 16}" text-anchor="middle">${esc(mesCorto(x.mes))}</text>`;
  });
  el.innerHTML = `${s}</svg>`;
}

function pintarCoberturaConf(seg) {
  const cont = $('#cfCob');
  const meta = seg.meta_cobertura_pct;
  const t = seg.total.cobertura_pct;
  const v = veredictoCobertura(t, meta);
  const fuera = seg.meses.filter((x) => Math.abs(x.cobertura_pct - meta) > 5);
  const cortos = seg.meses.filter((x) => x.cobertura_pct < meta - 2).map((x) => mesLargo(x.mes));
  const anchos = seg.meses.filter((x) => x.cobertura_pct > meta + 5).map((x) => mesLargo(x.mes));
  cont.innerHTML = `<p class="sub">Parte de las medias horas en que lo real cayó dentro del rango del ${nf0.format(meta)} %. Banda verde: de ${nf0.format(meta - 5)} a ${nf0.format(meta + 5)} %.</p>`
    + '<div id="cfCobG" class="chart lienzo" style="min-height:200px"></div>'
    + `<div class="veredicto ${v.clase}">${ICONO[v.clase]}<span>En el año cubrió el ${nf1.format(t)} %: ${esc(v.texto)}${v.porque ? `; ${esc(v.porque)}` : ''}.${cortos.length ? ` Quedó corto en ${esc(cortos.join(', '))}.` : ''}${anchos.length ? ` Fue más ancho de lo necesario en ${esc(anchos.join(', '))}.` : ''}</span></div>`
    + `<p class="nota-pie">Puntos destacados: ${fuera.length ? 'meses a más de 5 puntos de la meta' : 'ninguno: todos los meses quedan a 5 puntos de la meta o menos'}.</p>`;
  lineaCobertura($('#cfCobG'), seg.meses, meta);
}

function lineaCobertura(el, meses, meta) {
  el._dibujar = () => lineaCobertura(el, meses, meta);
  const W = Math.max(240, el.clientWidth || 320);
  const H = 200;
  const m = { l: 38, r: 8, t: 10, b: 26 };
  const lo = Math.min(meta - 10, ...meses.map((x) => x.cobertura_pct)) - 1;
  const hi = Math.min(100, Math.max(meta + 10, ...meses.map((x) => x.cobertura_pct)) + 1);
  const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const x = (j) => m.l + (j + 0.5) * ((W - m.l - m.r) / meses.length);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Cobertura del rango por mes frente a la meta del ${meta} %">`;
  s += `<rect class="g-meta-zona" x="${m.l}" y="${y(meta + 5).toFixed(1)}" width="${W - m.l - m.r}" height="${(y(meta - 5) - y(meta + 5)).toFixed(1)}"/>`;
  marcas(lo, hi, 4).forEach((v) => {
    s += `<line class="g-rejilla" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${nf0.format(v)} %</text>`;
  });
  s += `<line class="g-meta" x1="${m.l}" x2="${W - m.r}" y1="${y(meta).toFixed(1)}" y2="${y(meta).toFixed(1)}"/>`;
  s += `<text class="g-texto fuerte" x="${W - m.r}" y="${(y(meta) - 5).toFixed(1)}" text-anchor="end">meta ${nf0.format(meta)} %</text>`;
  s += `<path class="g-linea-pron" d="${meses.map((k, j) => `${j ? 'L' : 'M'}${x(j).toFixed(1)},${y(k.cobertura_pct).toFixed(1)}`).join('')}"/>`;
  meses.forEach((k, j) => {
    const fuera = Math.abs(k.cobertura_pct - meta) > 5;
    s += `<circle class="${fuera ? 'g-punto-ojo' : 'g-punto'}" cx="${x(j).toFixed(1)}" cy="${y(k.cobertura_pct).toFixed(1)}" r="${fuera ? 5 : 3.5}"/>`;
    s += `<text class="g-texto" x="${x(j).toFixed(1)}" y="${H - m.b + 15}" text-anchor="middle">${esc(mesCorto(k.mes).charAt(0).toUpperCase())}</text>`;
  });
  el.innerHTML = `${s}</svg>`;
}

function tarjetaDia(k) {
  const sobre = k.error_pct > 0;
  const causa = k.causa_probable
    ? `<span class="causa">Causa probable, según el calendario: ${esc(k.causa_probable)}.</span>`
    : '<span class="causa sin">Causa: sin registrar (el calendario no la explica).</span>';
  return `<li class="dia"><div class="f"><span>${esc(capital(DIAS[partesFecha(k.fecha).dow]))} ${partesFecha(k.fecha).d} ${esc(MESES_CORTOS[partesFecha(k.fecha).m - 1])}</span>`
    + `<span class="e ${sobre ? 'sobre' : 'bajo'}">${sobre ? 'Sobrestimó' : 'Subestimó'} ${nf1.format(Math.abs(k.error_pct))} %</span></div>`
    + `<p>Pico real ${mw(k.pico_real)} MW a las ${esc(k.hora_real)}; se pronosticó ${mw(k.pico_pronostico)} MW a las ${esc(k.hora_pronostico)}.</p>${causa}</li>`;
}

function pintarVivoConf(vivo, conf) {
  const cont = $('#cfVivo');
  if (!vivo || !vivo.resumen || !vivo.resumen.length) {
    cont.innerHTML = '<p class="sub">Todavía no hay pronósticos en vivo verificados para esta área.</p>';
    return;
  }
  const g = (grupo, h) => vivo.resumen.find((r) => r.grupo === grupo && r.horizonte === h);
  const caja = (titulo, r, nota) => {
    if (!r) return `<div class="vivo-tipo"><span class="muted">${esc(titulo)}</span><b>—</b><span class="muted">${esc(nota)}</span></div>`;
    const v = veredictoCobertura(r.cobertura_pct, vivo.nivel_rango_pct);
    return `<div class="vivo-tipo"><span class="muted">${esc(titulo)} · ${plural(r.dias, 'día', 'días')}</span><b>${nf1.format(r.mae_modelo)} MW</b>`
      + `<span>frente a ${nf1.format(r.mae_referencia)} MW de repetir ${esc(REF_CORTA[r.referencia_nombre] || r.referencia_nombre)}</span>`
      + `<p class="estado-meta ${v.clase}" style="margin-top:6px">${ICONO[v.clase]}Rango del ${vivo.nivel_rango_pct} %: cubrió ${nf1.format(r.cobertura_pct)} %, ${esc(v.texto)}</p></div>`;
  };
  const vivo24 = g('en_vivo', '24h');
  const recon24 = g('reconstruido', '24h');
  const principal = vivo24 || recon24;
  const v = principal ? veredictoCobertura(principal.cobertura_pct, vivo.nivel_rango_pct) : null;
  const malos = (conf.dias_en_vivo || []).filter((k) => Math.abs(k.error_pct) > conf.umbral_pico_pct);
  const inicio = [recon24 && recon24.desde, vivo24 && vivo24.desde, vivo.primer_dia_en_vivo].filter(Boolean).sort()[0];
  let html = `<p class="sub">Desde el ${esc(fechaDiaMes(inicio || ''))}, ${esc(vivo.modelo || 'el modelo')} pronostica cada día con la demanda del día anterior que publica el COES. `
    + `Lleva ${plural(vivo.dias_reconstruidos, 'día reconstruido', 'días reconstruidos')} (calculados después de conocerse el real, con los datos que habría tenido: no cuentan como en vivo) y ${plural(vivo.dias_en_vivo, 'día en vivo', 'días en vivo')}${vivo.primer_dia_en_vivo ? `, desde el ${esc(fechaDiaMes(vivo.primer_dia_en_vivo))}` : ''}: emitidos antes de su real, cada uno se verifica a la mañana siguiente.</p>`;
  html += `<div class="vivo-tipos">${caja('En vivo a 24 h', vivo24, 'Todavía ningún día con su real')}${caja('Reconstruido a 24 h', recon24, 'Sin días reconstruidos')}${caja('A 1 hora, siempre reconstruido', g('reconstruido', '1h'), 'Sin datos')}</div>`;
  if (v && v.clase !== 'bien') {
    html += `<div class="veredicto ${v.clase}" style="margin-top:12px">${ICONO[v.clase]}<span>El rango del ${vivo.nivel_rango_pct} % ${esc(v.texto)}. Entre el ${esc(fechaDiaMes(principal.desde))} y el ${esc(fechaDiaMes(principal.hasta))} cubrió el ${nf1.format(principal.cobertura_pct)} % de las medias horas a 24 h, cuando debería cubrir ${vivo.nivel_rango_pct / 10} de cada 10. Elia, en Bélgica, tiene el mismo problema con su banda del 80 %: cubrió entre 74 % y 79 % en 2024-2026.</span></div>`;
  }
  html += malos.length
    ? `<h3 class="sub" style="margin-top:16px"><b>${plural(malos.length, 'día pasó', 'días pasaron')} el ${nf0.format(conf.umbral_pico_pct)} % en el pico con el registro en vivo</b></h3><ul class="dias">${malos.map(tarjetaDia).join('')}</ul>`
    : `<p class="sub" style="margin-top:12px">Ningún día del registro en vivo pasó el ${nf0.format(conf.umbral_pico_pct)} % en el pico.</p>`;
  html += `<p class="enlaces"><a class="btn-enlace" href="${rutaDetalle(C.area, null, 'envivo')}">Ver el error de cada día en vivo</a></p>`;
  cont.innerHTML = html;
}

function pintarDiaADia(conf) {
  const cont = $('#cfDia');
  const dias = conf.dias;
  if (!dias.length) {
    cont.innerHTML = '<p class="sub">No hay días completos con real para medir el pico.</p>';
    return;
  }
  const u = conf.umbral_pico_pct;
  const meses = [...new Set(dias.map((k) => k.fecha.slice(0, 7)))];
  if (!meses.includes(C.mes)) C.mes = meses[meses.length - 1];
  const malos = dias.filter((k) => Math.abs(k.error_pct) > u);
  const sub = malos.filter((k) => k.error_pct < 0).length;
  const delMes = dias.filter((k) => k.fecha.startsWith(C.mes));
  const malosMes = delMes.filter((k) => Math.abs(k.error_pct) > u);
  const subMes = malosMes.filter((k) => k.error_pct < 0).length;
  cont.innerHTML = `<p class="sub">El pico pronosticado a 24 h frente al pico real de cada día. Arriba, sobrestimó; abajo, subestimó (lo más costoso: obliga a arrancar generación cara de urgencia). Líneas en ±${nf0.format(u)} %, como en el informe de PJM.</p>`
    + `<p class="sub">En todo 2026, <b>${malos.length} de ${dias.length} días</b> pasaron el ${nf0.format(u)} %: ${sub} subestimaciones y ${malos.length - sub} sobrestimaciones.</p>`
    + `<div class="meses-seg" role="group" aria-label="Mes">${meses.map((mes) => {
      const nm = dias.filter((k) => k.fecha.startsWith(mes) && Math.abs(k.error_pct) > u).length;
      return `<button type="button" data-cf-mes="${mes}" aria-pressed="${mes === C.mes}" aria-label="${esc(capital(mesLargo(mes)))}: ${plural(nm, 'día', 'días')} sobre el ${nf0.format(u)} %">${esc(capital(mesCorto(mes)))}${nm ? `<span class="n" aria-hidden="true">${nm}</span>` : ''}</button>`;
    }).join('')}</div>`
    + '<div id="cfDiaG" class="chart lienzo" style="min-height:200px"></div>'
    + `<p class="leyenda-dias"><span><i style="background:var(--crit)"></i>Subestimó más de ${nf0.format(u)} %</span><span><i style="background:var(--warn-mark)"></i>Sobrestimó más de ${nf0.format(u)} %</span><span><i style="background:var(--surface-3)"></i>Fin de semana</span></p>`
    + `<h3 class="sub" style="margin-top:16px"><b>${capital(mesLargo(C.mes))}: ${malosMes.length ? `${plural(malosMes.length, 'día pasó', 'días pasaron')} el ${nf0.format(u)} % en el pico${subMes ? ` (${subMes} subestimaciones)` : ''}` : `ningún día pasó el ${nf0.format(u)} % en el pico`}</b></h3>`
    + (malosMes.length ? `<ul class="dias">${malosMes.map(tarjetaDia).join('')}</ul>` : '')
    + `<details class="datos"><summary>Ver los ${malos.length} días de 2026 sobre el ${nf0.format(u)} %</summary><div class="tabla-scroll" tabindex="0" role="region" aria-label="Días con el error del pico sobre el umbral"><table class="t"><caption class="visually-hidden">Días de 2026 con el error del pico sobre el ${u} %</caption><thead><tr><th scope="col">Día</th><th scope="col">Pico real</th><th scope="col">Pronosticado</th><th scope="col">Error</th><th scope="col">Causa probable</th></tr></thead><tbody>`
    + malos.map((k) => `<tr><th scope="row">${esc(fechaNumerica(k.fecha))}</th><td>${mw(k.pico_real)} · ${esc(k.hora_real)}</td><td>${mw(k.pico_pronostico)} · ${esc(k.hora_pronostico)}</td><td>${k.error_pct > 0 ? '+' : '−'}${nf1.format(Math.abs(k.error_pct))} %</td><td style="text-align:left">${esc(k.causa_probable || 'sin registrar')}</td></tr>`).join('')
    + '</tbody></table></div></details>';
  barrasDias($('#cfDiaG'), delMes, u);
}

function barrasDias(el, dias, u) {
  el._dibujar = () => barrasDias(el, dias, u);
  const W = Math.max(280, el.clientWidth || 600);
  const movil = W < 560;
  const H = movil ? 190 : 220;
  const m = { l: 40, r: 8, t: 12, b: 26 };
  const lim = Math.max(6, Math.ceil(Math.max(...dias.map((k) => Math.abs(k.error_pct))) + 0.5));
  const y = (v) => m.t + (1 - (v + lim) / (2 * lim)) * (H - m.t - m.b);
  const bw = (W - m.l - m.r) / Math.max(dias.length, 1);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Error del pico de cada día de ${mesLargo(C.mes)}, en porcentaje">`;
  dias.forEach((k, j) => {
    const dow = partesFecha(k.fecha).dow;
    if (dow === 0 || dow === 6) s += `<rect class="g-fin-semana" x="${(m.l + j * bw).toFixed(1)}" y="${m.t}" width="${bw.toFixed(1)}" height="${H - m.t - m.b}"/>`;
  });
  [-lim, -u, 0, u, lim].forEach((v) => {
    s += `<line class="${v === 0 ? 'g-eje' : Math.abs(v) === u ? 'g-umbral' : 'g-rejilla'}" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v)} %</text>`;
  });
  dias.forEach((k, j) => {
    const fuera = Math.abs(k.error_pct) > u;
    const x0 = m.l + j * bw + Math.max(1, bw * 0.18);
    const w = Math.max(3, bw * 0.64);
    const y1 = y(Math.max(0, k.error_pct));
    const y2 = y(Math.min(0, k.error_pct));
    s += `<rect class="g-dia${fuera ? (k.error_pct > 0 ? ' sobre' : ' bajo') : ''}" x="${x0.toFixed(1)}" y="${y1.toFixed(1)}" width="${w.toFixed(1)}" height="${Math.max(1, y2 - y1).toFixed(1)}" rx="2"><title>${esc(fechaNumerica(k.fecha))}: ${k.error_pct > 0 ? '+' : ''}${nf1.format(k.error_pct)} %</title></rect>`;
    const d = partesFecha(k.fecha).d;
    if (!movil || d % 5 === 0 || d === 1) s += `<text class="g-texto" x="${(m.l + j * bw + bw / 2).toFixed(1)}" y="${H - m.b + 15}" text-anchor="middle">${d}</text>`;
  });
  el.innerHTML = `${s}</svg>`;
}

function pintarSesgoConf(conf) {
  const sg = conf.sesgo;
  const sub = sg.subestima_pct;
  const equilibrado = Math.abs(sub - 50) <= 5;
  $('#cfSesgo').innerHTML = '<p class="sub">Subestimar cuesta más: obliga a arrancar generación cara de urgencia. Lo ideal es quedar cerca de la mitad.</p>'
    + `<div class="medidor" role="img" aria-label="Subestimó en ${nf1.format(sub)} % de las medias horas; la zona equilibrada va de 45 a 55 %"><span class="zona"></span><span class="aguja" style="left:${Math.max(0, Math.min(100, sub))}%"></span></div>`
    + '<div class="medidor-eje"><span>Siempre sobrestima</span><span>50 %</span><span>Siempre subestima</span></div>'
    + `<p class="sub"><b>Subestimó en ${nf1.format(sub)} %</b> de las ${nf0.format(sg.periodos)} medias horas de 2026 (todas, no una muestra), con un sesgo medio de ${sg.sesgo_mw >= 0 ? '+' : '−'}${nf1.format(Math.abs(sg.sesgo_mw))} MW (pronóstico − real). ${equilibrado ? 'Está en la zona equilibrada (45–55 %).' : 'Está fuera de la zona equilibrada (45–55 %).'}</p>`;
}

function pintarNinoConf(diag) {
  const cont = $('#cfNino');
  if (!diag || !diag.mae_por_regimen || !diag.mae_por_regimen.length) {
    cont.innerHTML = '<p class="sub">El error por fase de El Niño no está disponible para este modelo.</p>';
    return;
  }
  const regs = diag.mae_por_regimen;
  const tope = Math.max(...regs.map((r) => Math.max(r.modelo, r.referencia)));
  const peor = regs.reduce((a, b) => (b.modelo > a.modelo ? b : a));
  const gana = regs.filter((r) => r.modelo < r.referencia).length;
  cont.innerHTML = '<p class="sub">Error medio a 24 h en 2026 según la fase de El Niño costero del mes pronosticado.</p>'
    + regs.map((r) => `<div class="barra-cmp"><span>${esc(REGIMEN[r.regimen] || r.regimen)}</span><span class="pista"><i class="i-pron" style="width:${((100 * r.modelo) / tope).toFixed(1)}%"></i></span><b>${nf1.format(r.modelo)} MW</b></div>`).join('')
    + `<p class="sub">Donde más se equivoca: <b>${esc(REGIMEN[peor.regimen] || peor.regimen)}</b> (${nf1.format(peor.modelo)} MW). ${gana === regs.length ? `Le gana a la referencia en las ${regs.length} fases.` : `Le gana a la referencia en ${gana} de ${regs.length} fases.`}</p>`;
}

// Cifras citables de otros operadores, cada una con su fuente. No es una comparación de igual a igual.
const MUNDO = [
  { quien: 'REE (España peninsular)', que: 'Pronóstico diario, publicado el día anterior: suma de errores absolutos horarios entre la demanda del año. Lo audita el regulador (CNMC).', periodo: '2024', valor: '1.60 %', fuente: 'https://www.cnmc.es/sites/default/files/6336322.pdf', nombre: 'CNMC, RAP/DE/012/25' },
  { quien: 'REE (España peninsular)', que: 'El mismo indicador, auditado por la CNMC', periodo: '2025', valor: '1.69 %', fuente: 'https://www.cnmc.es/sites/default/files/6915601.pdf', nombre: 'CNMC, RAP/DE/016/26' },
  { quien: 'Elia (Bélgica, unos 9 GW de demanda media)', que: 'Pronóstico del día siguiente (18:00), error ponderado (WAPE). Su banda P10–P90 (80 %) cubrió 75.5 %. Cálculo propio con sus datos abiertos.', periodo: '2025', valor: '3.04 %', fuente: 'https://opendata.elia.be/explore/dataset/ods001/', nombre: 'Elia, datos abiertos ods001' },
  { quien: 'PJM (Estados Unidos)', que: 'Día siguiente, error medio horario (MAPE); publica cada mes los días que pasaron el 3 % en el pico, con su causa.', periodo: 'ene-2026', valor: '1.73 %', fuente: 'https://www.pjm.com/-/media/DotCom/committees-groups/committees/oc/2026/20260205/20260205-item-07---system-operations-report.pdf', nombre: 'PJM, informe de operación, feb-2026' },
  { quien: 'ISO-NE (Nueva Inglaterra)', que: 'Día siguiente (10:00), todas las horas (MAPE), contra una meta de 2.0 % con semáforo: ese tramo no la cumplió.', periodo: 'ene–may 2025', valor: '2.49 %', fuente: 'https://www.iso-ne.com/static-assets/documents/100024/june-2025-coo-report.pdf', nombre: 'ISO-NE, informe COO, jun-2025' },
  { quien: 'NESO (Gran Bretaña, unos 26 GW)', que: 'Día siguiente, cada 30 min (MAPE). Cálculo propio con su archivo de desempeño.', periodo: '2025', valor: '2.69 %', fuente: 'https://www.neso.energy/data-portal/day-ahead-half-hourly-demand-forecast-performance', nombre: 'NESO, portal de datos' },
];

function pintarMundo(conf) {
  const area = nombreArea(C.area);
  const hasta = S.resumen && S.resumen.fechas_corte.prueba_hasta;
  const filas = MUNDO.map((f) => `<tr><td>${esc(f.quien)}</td><td>${esc(f.que)} <a href="${f.fuente}" rel="noopener" target="_blank">${esc(f.nombre)}</a></td><td>${esc(f.periodo)}</td><td class="n">${esc(f.valor)}</td></tr>`).join('');
  const nuestro = `<tr class="nuestro"><td><b>Este modelo · ${esc(area)}</b></td><td>${C.horizonte === '1h' ? '1 hora' : '24 horas'} exactas, cada 30 min, sin clima pronosticado. WAPE (como REE y Elia) y MAPE (como PJM, ISO-NE y NESO).</td><td>2026 (ene–${hasta ? esc(fechaCorta(hasta).replace(/ \d{4}$/, '')) : 'oct'})</td><td class="n">WAPE ${nf2(conf.wape_pct)} %<br>MAPE ${nf2(conf.mape_pct)} %</td></tr>`;
  $('#cfMundo').innerHTML = `<div class="veredicto ojo">${ICONO.info}<span>No es una comparación de igual a igual: cambian la métrica, el horizonte y el tamaño del sistema (un área del SEIN es mucho más chica y ruidosa que un país), y 2026 ya se usó para elegir el modelo. Sirve para saber en qué orden de magnitud se mueven los operadores que publican su error.</span></div>`
    + `<div class="tabla-scroll" tabindex="0" role="region" aria-label="Error de otros operadores" style="max-height:none;margin-top:12px"><table class="cmp"><caption class="visually-hidden">Error del pronóstico que publican otros operadores y el de este modelo</caption><thead><tr><th scope="col">Quién</th><th scope="col">Qué se mide y fuente</th><th scope="col">Periodo</th><th scope="col" style="text-align:right">Error</th></tr></thead><tbody>${filas}${nuestro}</tbody></table></div>`
    + '<p class="nota-pie">Fuentes consultadas el 13 de noviembre de 2026. No encontramos que el COES publique el error de su pronóstico ni de su programa.</p>';
}

const nf2 = (x) => new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(x);

// ---- Rutas e inicio ------------------------------------------------------------------------

// #/ y #/ahora/{área}: «Ahora» (en vivo o, con fecha y hora, en repaso); #/confianza/{área}; #/area/{área}: el detalle.
function leerRuta() {
  const h = location.hash.replace(/^#/, '') || '/';
  const [camino, consulta] = h.split('?');
  const partes = camino.split('/').filter(Boolean);
  const q = new URLSearchParams(consulta || '');
  if (['ahora', 'confianza', 'area'].includes(partes[0]) && partes[1]) {
    return { vista: partes[0], area: decodeURIComponent(partes[1]), q };
  }
  return { vista: 'ahora', area: leer('tpf-area') || 'centro', q, raiz: true };
}

function enrutar() {
  const r = leerRuta();
  const lista = S.areas.length ? S.areas : AREAS_RESPALDO;
  if (!lista.some((a) => a.id === r.area)) r.area = 'centro';
  guardar('tpf-area', r.area);
  if (r.vista === 'area' && S.areas.length) mostrarArea(r.area, r.q);
  else if (r.vista === 'confianza') mostrarConfianza(r.area, r.q);
  else {
    if (r.raiz || r.vista === 'area') history.replaceState(null, '', rutaAhora(r.area));
    mostrarAhora(r.area, r.raiz ? new URLSearchParams() : r.q);
  }
}

// Las métricas de la ficha y de «¿qué tan bueno es?» son las del modelo elegido.
async function cargarResumen() {
  if (!hayVariosModelos() || !S.modelo) return;
  const pedido = S.modelo;
  let resumen;
  try {
    resumen = await api(`/resumen?modelo=${encodeURIComponent(pedido)}`);
  } catch {
    return; // se conserva el resumen anterior
  }
  if (pedido !== S.modelo) return; // mientras llegaba se eligió otro modelo
  S.resumen = resumen;
  pintarFicha();
  if (S.area && S.serie) pintarConfianza();
}

async function cargarBase() {
  // /modelos es opcional: un backend anterior no lo tiene y entonces el único modelo es el de /salud
  const [salud, areas, resumen, modelos] = await Promise.all([
    api('/salud'), api('/areas'), api('/resumen'), api('/modelos').catch(() => []),
  ]);
  S.salud = salud;
  S.areas = areas;
  S.resumen = resumen;
  const hasta = resumen.fechas_corte && resumen.fechas_corte.prueba_hasta;
  if (/^\d{4}-\d{2}-\d{2}$/.test(hasta || '')) FECHA_MAX = hasta;
  S.modelos = Array.isArray(modelos) ? modelos : [];
  if (!S.modelos.length) S.modelos = [{ id: salud.modelo, nombre: salud.modelo }];
  if (!S.modelos.some((m) => m.id === S.modelo)) S.modelo = S.modelos[0].id;
  $('#inModelo').innerHTML = S.modelos.map((m) => `<option value="${esc(m.id)}">${esc(m.nombre)}</option>`).join('');
  $('#campoModelo').classList.toggle('unico', S.modelos.length === 1);
  aplicarModelo();
  $('#chipPrueba').hidden = salud.modelo !== 'prueba';
  pintarRegimen();
  pintarFicha();
}

async function iniciar() {
  const base = cargarBase();
  const ahoraPrimero = leerRuta().vista === 'ahora';
  if (ahoraPrimero) enrutar(); // el número sale de /ahora: no espera a /salud, /areas, /resumen ni /modelos
  try {
    await base;
    limpiarError();
  } catch (err) {
    mostrarError(err);
    pintarRegimen();
  }
  if (!ahoraPrimero) enrutar();
  else if (S.vista === 'ahora' && A.datos.has(A.area)) pintarAhora(); // nombres, rangos de fechas y enlaces
}

function conectarEventos() {
  $('#saltar').addEventListener('click', (ev) => {
    ev.preventDefault(); // el hash es la ruta de la app
    if (S.vista === 'detalle') irASeccion('respuesta');
    else (S.vista === 'confianza' ? $('#cfTitular') : $('#principal')).focus();
  });
  $('.nav-secciones').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-ir]');
    if (!b) return;
    irASeccion(b.dataset.ir);
    if (b.dataset.ir === 'envivo') cargarEnVivo(); // por si la tubería emitió algo desde que se abrió el área
  });
  $('#tablaDia').addEventListener('toggle', pintarTablaDia);

  $('#btnTema').addEventListener('click', () => {
    const tema = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    aplicarTema(tema);
    guardar('tpf-tema', tema);
    redibujarGraficos();
  });

  const ficha = $('#dlgFicha');
  const abrirFicha = () => (typeof ficha.showModal === 'function' ? ficha.showModal() : ficha.setAttribute('open', ''));
  $('#btnFicha').addEventListener('click', abrirFicha);
  $('#btnCerrarFicha').addEventListener('click', () => ficha.close());
  ficha.addEventListener('click', (ev) => {
    if (ev.target === ficha) ficha.close(); // clic en el fondo
  });

  $('#inFecha').addEventListener('change', (ev) => {
    const pedida = ev.target.value;
    const fecha = acotarFecha(pedida);
    if (!fecha) return;
    const aviso = $('#fechaAviso');
    aviso.hidden = fecha === pedida;
    if (fecha !== pedida) aviso.textContent = `Solo hay datos del ${fechaCorta(FECHA_MIN)} al ${fechaCorta(FECHA_MAX)}: se muestra el ${fechaCorta(fecha)}.`;
    S.fecha = fecha;
    recargar();
  });
  $('#inModelo').addEventListener('change', (ev) => {
    S.modelo = ev.target.value;
    aplicarModelo();
    cargarResumen();
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

  // Ahora
  $('#ahHoy').addEventListener('click', () => irAhora(null));
  $('#ahFecha').addEventListener('change', (ev) => {
    const f = ev.target.value;
    if (!esFecha(f)) return;
    if (f >= hoyLima()) irAhora(null);
    else irAhora({ fecha: f, hora: A.hora || horaValida($('#ahHora').value) || idxAHora(ahoraEnLima().idx) });
  });
  $('#ahHora').addEventListener('change', (ev) => {
    const h = horaValida(ev.target.value);
    if (h && A.fecha) irAhora({ fecha: A.fecha, hora: h });
  });
  $('#ahRef').addEventListener('change', (ev) => {
    A.ref = ev.target.checked;
    const d = A.datos.get(A.area);
    if (d) graficoAhora($('#ahLienzo'), d);
  });
  $('#ahDespues').addEventListener('change', (ev) => {
    A.despues = ev.target.checked;
    const d = A.datos.get(A.area);
    if (!d) return;
    graficoAhora($('#ahLienzo'), d);
    pintarDiaCompleto(d);
    pintarBueno(d);
    if ($('#ahTablaDet').open) pintarTablaAhora(d);
  });
  $('#ahCsv').addEventListener('click', descargarCsvAhora);
  $('#ahOrigen').addEventListener('click', (ev) => {
    if (ev.target.closest('[data-accion="ficha"]')) $('#btnFicha').click();
  });
  $('#ahTablaDet').addEventListener('toggle', () => {
    const d = A.datos.get(A.area);
    if (d && $('#ahTablaDet').open) pintarTablaAhora(d);
  });
  const lienzo = $('#ahLienzo');
  const indiceLienzo = (ev) => {
    const g = lienzo._g;
    const r = lienzo.getBoundingClientRect();
    return Math.round(((ev.clientX - r.left - g.m.l) / (g.W - g.m.l - g.m.r)) * g.N);
  };
  lienzo.addEventListener('pointermove', (ev) => { if (lienzo._g) tipAhora(indiceLienzo(ev)); });
  lienzo.addEventListener('pointerleave', ocultarTipAhora);
  lienzo.addEventListener('focus', () => { if (lienzo._g) tipAhora(lienzo._g.d.i_ahora); });
  lienzo.addEventListener('blur', ocultarTipAhora);
  lienzo.addEventListener('keydown', (ev) => {
    if (!lienzo._g) return;
    const actual = lienzo._i ?? lienzo._g.d.i_ahora;
    const pasos = { ArrowRight: 1, ArrowLeft: -1, PageUp: -12, PageDown: 12 };
    let i = null;
    if (ev.key in pasos) i = actual + pasos[ev.key];
    if (ev.key === 'Home') i = 0;
    if (ev.key === 'End') i = lienzo._g.N;
    if (i == null) return;
    ev.preventDefault();
    tipAhora(i);
  });

  // Confianza
  $$('[data-cf-horizonte]').forEach((b) => b.addEventListener('click', () => {
    if (C.horizonte === b.dataset.cfHorizonte) return;
    C.horizonte = b.dataset.cfHorizonte;
    history.replaceState(null, '', `#/confianza/${encodeURIComponent(C.area)}?horizonte=${C.horizonte}`);
    mostrarConfianza(C.area, new URLSearchParams({ horizonte: C.horizonte }));
  }));
  $('#cfDia').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-cf-mes]');
    if (!b || !C.datos) return;
    C.mes = b.dataset.cfMes;
    pintarDiaADia(C.datos.conf);
    const elegido = $(`[data-cf-mes="${C.mes}"]`);
    if (elegido) elegido.focus();
  });

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (ev) => {
    if (leer('tpf-tema')) return; // la elección guardada manda
    aplicarTema(ev.matches ? 'dark' : 'light');
    redibujarGraficos();
  });

  let esperaResize = null;
  window.addEventListener('resize', () => {
    clearTimeout(esperaResize);
    esperaResize = setTimeout(redibujarGraficos, 150);
  });
  window.addEventListener('hashchange', enrutar);
}

aplicarTema(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
conectarEventos();
iniciar();
