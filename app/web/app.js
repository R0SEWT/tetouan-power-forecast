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
// Qué es Curva, también en la pestaña
const TITULO_CURVA = 'Curva, pronóstico de la demanda eléctrica del Perú';
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

const ZONA_AREA = { norte: 'el norte del país', centro: 'Lima y el centro del país', sur: 'el sur del país' };

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

const CORTE = {
  entrenamiento_hasta: 'Entrenamiento hasta', validacion_hasta: 'Validación hasta', prueba_hasta: 'Prueba hasta',
  demanda: 'Demanda (COES)', clima: 'Clima (ERA5)', icen: 'ICEN (IGP y ENFEN)', nino12: 'Niño 1+2 (NOAA)',
  fallas: 'Fallas (COES)', saidi: 'SAIDI (Osinergmin)',
};

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

const mesLargo = (aaaamm) => MESES[Number(aaaamm.slice(5, 7)) - 1] || aaaamm;
const mesCorto = (aaaamm) => MESES_CORTOS[Number(aaaamm.slice(5, 7)) - 1] || aaaamm;

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

// index.html pide los datos de arranque antes de que baje este archivo; cada respuesta se usa una sola vez.
const PRECARGA = window.PRECARGA instanceof Map ? window.PRECARGA : new Map();

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

function redibujarGraficos() {
  $$('.chart').forEach((el) => {
    if (el._dibujar && el.offsetParent !== null) el._dibujar();
  });
}

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
  $('#chipRegimenTxt').textContent = `El Niño costero (calentamiento del mar frente a la costa): ${estado}`;
  chip.title = `Último ICEN publicado: ${r.icen} en ${MESES[m - 1]} de ${y}, régimen ${estado} según ENFEN. El ICEN sale con meses de rezago.`;
  chip.hidden = false;
}

const nombreModelo = () => {
  const m = modeloEfectivo();
  return m ? m.nombre : (S.salud ? S.salud.modelo : 'modelo');
};

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
    <section><h3>Qué hace</h3><p>Pronostica la demanda eléctrica de las áreas Norte, Centro y Sur del SEIN cada 30 minutos, a 1 hora y a 24 horas, con su rango del 90 %. La compara con la referencia: la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora).</p></section>
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

const REF_CORTA = { persistencia: 'último dato', ayer: 'ayer', semana_pasada: 'semana pasada' };
const plural = (n, uno, varios) => `${nf0.format(n)} ${n === 1 ? uno : varios}`;

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
  // La versión corta, en dos líneas (qué y hasta cuándo)
  const corta = (Array.isArray(corto) ? corto : [corto || texto]).map((t) => `<span>${esc(t)}</span>`).join(' ');
  $('#estadoTxt').innerHTML = `<span class="larga">${esc(texto)}</span><span class="corta">${corta}</span>`;
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
  document.title = `${nombreArea(area)} · Ahora · ${TITULO_CURVA}`;
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
  const pedido = api(`/ahora/${encodeURIComponent(A.area)}${consulta}`);
  // Las otras dos áreas bajan después del número (para cambiar de área al instante): en una red lenta no le quitan
  // ancho de banda a lo primero que se lee
  const otras = ORDEN_AREAS.filter((a) => a !== A.area);
  pedido.catch(() => {}).then(() => otras.forEach((a) => {
    if (turno !== A.turno) return;
    api(`/ahora/${encodeURIComponent(a)}${consulta}`).then((d) => {
      if (turno !== A.turno) return;
      A.datos.set(a, d);
      pintarAreasAhora();
    }).catch(() => {});
  }));
  let d;
  try {
    d = await pedido;
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
        pintarEstado({ modo: 'repaso', texto: `Sin conexión · copia del ${txt}`, corto: ['Copia del', txt], titulo: 'Sin conexión: última copia guardada' });
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
  const preg = preguntaDelDia(d);
  A.sinAviso = Boolean(preg.sinAviso);
  // Arriba de la pregunta, de qué zona habla: el nombre del área y qué parte del país es
  $('#principal').innerHTML = `<span class="pregunta-area">${esc(nombreArea(A.area))} · ${esc(ZONA_AREA[A.area] || 'Perú')}</span>${esc(preg.q)}`;
  $('#ahRespuesta').innerHTML = preg.html;
  $('#ahModo').innerHTML = vivo
    ? `Lo real llega con un día de retraso: el COES, el operador del sistema eléctrico, publica cada mañana la demanda del día anterior. Lo demás es pronóstico, emitido ${emitidoTxt(d.emitido_en || d.ahora)}.`
    : `<b>Repaso de un día del historial.</b> Así se veía a las ${esc(horaDe(d.origen))}: lo real (del COES, el operador del sistema eléctrico) llega hasta esa hora y lo que sigue es lo que ya se había pronosticado.`;
  pintarEstado(vivo
    ? { modo: 'vivo', texto: `Hoy · datos del COES al ${fin.corto}`, corto: ['COES', fin.corto.replace(', ', ' ')], titulo: `Pronóstico de hoy. Datos reales del COES hasta el ${fin.largo}; el resto es pronóstico.` }
    : { modo: 'repaso', texto: `Repaso · ${fechaNumerica(d.origen)}, ${horaDe(d.origen)}`, corto: ['Repaso', `${fechaNumerica(d.origen).replace(/\/20(\d\d)$/, '/$1')} ${horaDe(d.origen)}`], titulo: `Repaso del ${fechaLarga(d.origen)}, ${horaDe(d.origen)}` });

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
  // Si la respuesta ya explica que el pronóstico del día no llegó, el aviso no lo repite con otra hora
  const avisos = (d.avisos || []).filter((t) => !(A.sinAviso && /^Todavía no llega la demanda/.test(t)));
  $('#ahAviso').innerHTML = avisos.map((t) => `${ICONO.ojo}<span>${esc(t)}</span>`).join('');
  $('#ahAviso').hidden = !avisos.length;

  pintarAreasAhora();
  pintarCifras(d);
  $('#ahTodasTit').textContent = vivo ? 'Todas las cifras de hoy' : 'Todas las cifras de ese día';
  $('#ahGrafTitulo').textContent = vivo ? 'Ayer y hoy' : 'Ese día y las 24 h siguientes';
  $('#ahGrafSub').textContent = vivo
    ? `${nombreArea(A.area)}. A la izquierda, lo real de ayer y lo que se había pronosticado; desde la línea punteada no hay dato real todavía. «Ahora» marca la hora de Lima.`
    : `${nombreArea(A.area)}. A la izquierda de «Ahora», lo real y lo que se pronosticó un día antes; a la derecha, lo que ya estaba pronosticado a las ${horaDe(d.origen)}.`;
  $('#ahLeyRango').textContent = `Rango del ${d.nivel_rango_pct} % (cae ahí ${d.nivel_rango_pct / 10} de cada 10 veces)`;
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

function pintarAreasAhora() {
  const lista = S.areas.length ? S.areas : AREAS_RESPALDO;
  const repaso = A.fecha ? { fecha: A.fecha, hora: A.hora } : null;
  $('#ahAreas').innerHTML = lista.map((a) => `<a href="${rutaAhora(a.id, repaso, { modelo: A.modelo })}"${a.id === A.area ? ' aria-current="page"' : ''}>${esc(a.nombre)}</a>`).join('');
}

const cambioPct = (a, b) => Math.round((100 * Math.abs(a - b)) / b);
const emitidoTxt = (fh) => {
  const dia = fh.slice(0, 10);
  const cuando = dia === hoyLima() ? 'hoy' : dia === sumarDias(hoyLima(), -1) ? 'ayer' : `el ${esc(fechaDiaMes(fh))}`;
  return `${cuando} a las ${esc(horaDe(fh))}`;
};

// La pregunta del día: el pico si está por llegar; si no, el resto del día; en un repaso, si se acertó
function preguntaDelDia(d) {
  const vivo = d.modo === 'en_vivo';
  const c = d.cifra_ahora;
  const real = c.fuente === 'real';
  const cifra = (k, sw, sub) => `<div class="r-ahora"><p class="k"><span class="sw ${sw}" aria-hidden="true"></span>${k}</p>`
    + `<p class="n">${mw(c.valor)}<small>MW</small></p><p class="d">${sub}</p></div>`;
  if (!vivo) {
    const ay = d.ayer && d.ayer.fecha_hora === c.fecha_hora ? d.ayer : null;
    const dia = d.origen.slice(0, 10);
    const escenario = dia >= FECHA_MIN && dia <= FECHA_MAX
      ? ` <a class="kpi-enlace" href="${rutaDetalle(A.area, { fecha: dia, hora: horaDe(d.origen) }, 'escenarios')}">¿Y si hace más calor?</a>` : '';
    let frase = real ? `Fueron <b>${mw(c.valor)} MW</b>, dato del COES.` : `Se pronosticaban <b>${mw(c.valor)} MW</b>, entre ${mw(c.inferior)} y ${mw(c.superior)}.`;
    if (ay && real) {
      frase = `Un día antes se pronosticó <b>${mw(ay.pronostico)} MW</b>, con un rango de ${mw(ay.inferior)} a ${mw(ay.superior)}: `
        + `lo real cayó ${ay.dentro ? 'dentro' : 'fuera'}.`;
    }
    return {
      q: `¿Acertamos el ${fechaLarga(d.origen)} a las ${horaDe(d.origen)}?`,
      html: cifra(`${real ? 'Fue' : 'Pronóstico'} · ${esc(horaDe(c.fecha_hora))}`, real ? 'real' : 'pron', `${real ? 'Dato del COES' : 'Pronóstico'}, en megavatios (MW)`)
        + `<p class="r-frase">${frase}${escenario}</p>`,
    };
  }
  if (real) {
    return {
      q: '¿Cuánta electricidad se usará hoy?',
      html: cifra(`Último dato real · ${esc(horaDe(c.fecha_hora))}`, 'real', 'Dato del COES, en megavatios (MW)')
        + '<p class="r-frase">El pronóstico de hoy sale hacia las 10:00, cuando el COES publique la demanda de ayer. Mientras, abajo, el último que se emitió.</p>',
      sinAviso: true,
    };
  }
  const ahora = cifra(`Ahora · ${esc(horaDe(c.fecha_hora))}`, 'pron', 'Pronóstico en megavatios (MW); el real llega mañana');
  const p = d.pico;
  if (p.fecha_hora > d.ahora) {
    return {
      q: '¿A qué hora se usará más electricidad hoy?',
      html: `${ahora}<p class="r-frase">A las ${esc(horaDe(p.fecha_hora))}, con unos <b>${mw(p.valor)} MW</b>: ${cambioPct(p.valor, c.valor)} % más que ahora.</p>`,
    };
  }
  const hoy = d.ahora.slice(0, 10);
  const resto = [];
  for (let i = d.i_ahora + 1; i < d.fecha_hora.length && d.fecha_hora[i].startsWith(hoy); i += 1) resto.push(i);
  if (!resto.length) {
    return {
      q: '¿Cuánta electricidad se usa ahora?',
      html: `${ahora}<p class="r-frase">El pronóstico de mañana se publica hacia las 10:00, cuando el COES dé la demanda de hoy.</p>`,
    };
  }
  const hora = Number(horaDe(d.ahora).slice(0, 2));
  const q = `¿Cuánta electricidad se usará ${hora >= 18 ? 'esta noche' : 'el resto del día'}?`;
  const iMax = resto.reduce((a, i) => (d.pronostico[i] > d.pronostico[a] ? i : a), resto[0]);
  if (d.pronostico[iMax] > c.valor * 1.01) {
    return { q, html: `${ahora}<p class="r-frase">Subirá hasta unos <b>${mw(d.pronostico[iMax])} MW</b> a las ${esc(horaDe(d.fecha_hora[iMax]))}: ${cambioPct(d.pronostico[iMax], c.valor)} % más que ahora.</p>` };
  }
  const iFin = resto[resto.length - 1];
  const v = d.pronostico[iFin];
  const pct = cambioPct(v, c.valor);
  // Una subida menor que el 1 % (las mayores ya se dijeron arriba) no se cuenta como bajada
  return {
    q,
    html: `${ahora}<p class="r-frase">${v >= c.valor || pct < 1 ? `Se mantendrá cerca de <b>${mw(v)} MW</b> hasta las ${esc(horaDe(d.fecha_hora[iFin]))}.` : `Irá bajando: unos <b>${mw(v)} MW</b> a las ${esc(horaDe(d.fecha_hora[iFin]))}, ${pct} % menos que ahora.`}</p>`,
  };
}

function kpiHtml({ clase = '', sw = 'pron', k, n, d, unidad = 'MW' }) {
  return `<div class="kpi ${clase}"><p class="k">${sw ? `<span class="sw ${sw}" aria-hidden="true"></span>` : ''}${k}</p>`
    + `<p class="n">${n}${unidad ? `<small>${unidad}</small>` : ''}</p><p class="d">${d}</p></div>`;
}

function pintarCifras(d) {
  const vivo = d.modo === 'en_vivo';
  const c = d.cifra_ahora;
  const html = [];
  // Todas las cifras, a un toque; sin tarjetas vacías
  const dijimos = d.ayer && d.ayer.fecha_hora === c.fecha_hora ? `. Se pronosticó ${mw(d.ayer.pronostico)} (${rangoTxt(d.ayer.inferior, d.ayer.superior)}): ${d.ayer.dentro ? 'dentro' : 'fuera'} del rango` : '';
  html.push(kpiHtml({
    sw: c.fuente === 'real' ? 'real' : 'pron',
    k: `Ahora · ${esc(horaDe(c.fecha_hora))}`,
    n: mw(c.valor),
    d: c.fuente === 'real' ? `Dato del COES${dijimos}` : `Pronóstico, rango ${rangoTxt(c.inferior, c.superior)} · el real llega mañana`,
  }));
  const u = d.en_1h;
  if (u) {
    html.push(kpiHtml({
      k: `En 1 hora · ${esc(horaDe(u.fecha_hora))}`,
      n: mw(u.valor),
      d: `Rango ${rangoTxt(u.inferior, u.superior)}${u.fuente === 'pronostico_1h' ? ' · a 1 h' : ''}`,
    }));
  }
  const p = d.pico;
  const yaPaso = vivo && p.fecha_hora < d.ahora;
  html.push(kpiHtml({
    clase: `kpi-pico${yaPaso ? ' kpi-pasado' : ''}`,
    k: `Pico${yaPaso ? ' <span class="kpi-paso">ya pasó</span>' : ''}`,
    n: mw(p.valor),
    d: `${yaPaso ? `Fue a las ${esc(horaDe(p.fecha_hora))}, según el pronóstico` : `${esc(fechaDiaMes(p.fecha_hora))}, ${esc(horaDe(p.fecha_hora))}`} · Rango del ${d.nivel_rango_pct} %: ${rangoTxt(p.inferior, p.superior)}`,
  }));
  if (d.manana) {
    html.push(kpiHtml({
      k: 'Mañana a esta hora',
      n: mw(d.manana.valor),
      d: `${firmado(d.manana.valor - c.valor)} MW frente a ahora`,
    }));
  }
  const r = d.rampa;
  if (r) {
    html.push(kpiHtml({
      sw: null,
      k: 'Mayor subida en 1 hora',
      n: `+${mw(r.subida_mw)}`,
      d: `${esc(horaDe(r.desde))}–${esc(horaDe(r.hasta))} ${esc(diaCorto(r.hasta))} · `
        + (r.fuerte ? `<span class="marca-estado fuerte">${ICONO.ojo}rampa fuerte</span>` : 'habitual')
        + (r.umbral_mw != null ? ` (umbral ${mw(r.umbral_mw)})` : ''),
    }));
  }
  $('#ahCifras').innerHTML = html.join('');
  const nombres = ['ahora', d.en_1h && 'en 1 hora', vivo ? 'el pico de hoy' : 'el pico', d.manana && 'mañana a esta hora', d.rampa && 'la mayor subida'].filter(Boolean);
  $('#ahTodasQue').textContent = `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}`;
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
  // Arriba de cada tramo, qué es: lo real (del COES) a la izquierda y el pronóstico desde el último dato real
  const resto = movil ? '' : (vivo ? ': el real todavía no se publica' : ' de las próximas 24 horas');
  s += `<text class="g-rotulo pron" x="${(x(io) + 8).toFixed(1)}" y="${m.t - 8}">Pronóstico<tspan class="g-rotulo-resto">${esc(resto)}</tspan></text>`;
  // …y hasta cuándo hay dato real, si cabe
  const hasta = vivo ? finTxt(d.datos_hasta).corto : horaDe(d.origen);
  const reales = [`Real (COES) hasta ${vivo ? 'el' : 'las'} ${hasta}`, 'Real (COES)', 'Real'].find((t) => movil ? t === 'Real' : t.length * 7.4 + 30 < x(io) - m.l);
  if (io > 0 && reales) s += `<text class="g-rotulo real" x="${(m.l + 14).toFixed(1)}" y="${m.t - 8}">${esc(reales)}</text>`;
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
  // La banda del rango: plena en lo que viene; más tenue en lo que ya pasó, donde manda lo real
  const banda = (a, b) => {
    let t = '';
    for (let i = a; i <= b; i += 1) t += `${i > a ? 'L' : 'M'}${p(i, d.superior[i])}`;
    for (let i = b; i >= a; i -= 1) t += `L${p(i, d.inferior[i])}`;
    return `${t}Z`;
  };
  if (io > 0) s += `<path class="g-banda pasada" d="${banda(0, io)}"/>`;
  s += `<path class="g-banda" d="${banda(io, N)}"/>`;
  if (A.ref) s += `<path class="ln-referencia" d="${linea(d.referencia, 0, N)}"/>`;
  const real = linea(d.real, 0, io);
  if (real) s += `<path class="g-real-relleno" d="${real}L${x(io).toFixed(1)},${H - m.b}L${x(0).toFixed(1)},${H - m.b}Z"/>`;
  s += `<path class="ln-pronostico fina" d="${linea(d.pronostico, 0, io)}"/>`;
  if (real) s += `<path class="ln-real" d="${real}"/>`;
  s += `<path class="ln-pronostico" d="${linea(d.pronostico, io, N)}"/>`;
  if (despues) s += `<path class="ln-despues" d="${linea(d.real_despues.map((v, i) => (i === io ? d.real[io] : v)), io, N)}"/>`;
  // Lo que ya ocupa un rótulo (cajas x0, y0, x1, y1): el que llega después busca otro lugar o no se dibuja
  const ocupado = [];
  const cajaTexto = (tx, ty, texto, ancla, px = 6.8) => {
    const w = texto.length * px;
    const x0 = ancla === 'end' ? tx - w : ancla === 'middle' ? tx - w / 2 : tx;
    return [x0 - 3, ty - 13, x0 + w + 3, ty + 4];
  };
  const libre = (c) => c[0] >= m.l - 2 && c[2] <= W - m.r + 2 && c[1] >= m.t - 24 && c[3] <= H - m.b
    && !ocupado.some((o) => c[0] < o[2] && c[2] > o[0] && c[1] < o[3] && c[3] > o[1]);
  // El hito de «ahora»: su valor en una pastilla junto al punto (arriba; si no cabe, abajo)
  const vAhora = d.real[ia] != null ? d.real[ia] : d.pronostico[ia];
  const textoAhora = `${mw(vAhora)} MW`;
  const anchoValor = textoAhora.length * 8.6 + 18;
  // A la izquierda del punto (sobre lo real); si no cabe, a la derecha. Pegada al halo: se lee como parte del punto
  const izqValor = x(ia) - 16 - anchoValor >= m.l + 4;
  const vx = izqValor ? x(ia) - 16 - anchoValor : x(ia) + 16;
  const vy = Math.min(Math.max(y(vAhora) - 14, m.t - 18), H - m.b - 30);
  if (!movil) ocupado.push([vx - 4, vy - 4, vx + anchoValor + 4, vy + 32]);
  ocupado.push([x(ia) - 14, y(vAhora) - 14, x(ia) + 14, y(vAhora) + 14],
    [x(ia) - 3, m.t - 22, x(ia) + 3, H - m.b]); // ningún rótulo cruza la línea de «ahora»
  if (ia !== io) ocupado.push(cajaTexto(x(io) - 6, H - m.b - 8, 'Último dato real', 'end'));
  ocupado.push(cajaTexto(x(io) + 8, m.t - 8, movil ? 'Pronóstico' : 'Pronóstico: el real todavía no se publica', 'start', 7.2),
    cajaTexto(m.l + 14, m.t - 8, 'Real (COES) hasta el 00/00, 24:00', 'start', 7.4));
  const r = d.rampa;
  const ir = r ? d.fecha_hora.indexOf(r.desde) : -1;
  let rotuloRampa = '';
  if (ir >= 0 && ir + 2 <= N) {
    const tramo = `M${p(ir, d.pronostico[ir])}L${p(ir + 1, d.pronostico[ir + 1])}L${p(ir + 2, d.pronostico[ir + 2])}`;
    s += `<path class="g-rampa-fondo" d="${tramo}"/><path class="g-rampa${r.fuerte ? ' fuerte' : ''}" d="${tramo}"/>`;
    if (!movil) {
      // El rótulo, apartado del tramo y unido a él con un conector: se lee qué subida es sin tapar la curva
      const texto = `+${mw(r.subida_mw)} MW en 1 h${r.fuerte ? ' · rampa fuerte' : ''}`;
      const mx = x(ir + 1);
      const my = y(d.pronostico[ir + 1]);
      const opciones = [[-30, -26, 'end'], [30, 30, 'start'], [-30, 30, 'end'], [-12, 4, 'end']];
      for (const [dx, dy, ancla] of opciones) {
        const c = cajaTexto(mx + dx, my + dy, texto, ancla, 6.4);
        if (!libre(c)) continue;
        ocupado.push(c);
        const cx = ancla === 'end' ? c[2] - 1 : c[0] + 1;
        const cy = dy < 0 ? c[3] - 2 : c[1] + 2;
        const fin = (k) => (dy < 0 ? -k : k);
        if (Math.abs(dx) > 12) rotuloRampa += `<line class="g-conector" x1="${cx.toFixed(1)}" y1="${cy.toFixed(1)}" x2="${(mx + (dx < 0 ? -3 : 3)).toFixed(1)}" y2="${(my + fin(3)).toFixed(1)}"/>`;
        rotuloRampa += `<text class="g-texto medio g-rotulo-rampa" x="${(mx + dx).toFixed(1)}" y="${(my + dy).toFixed(1)}" text-anchor="${ancla}">${texto}</text>`;
        break;
      }
    }
  }
  if (Math.abs(ia - io) > 1) {
    s += `<line class="g-corte" x1="${x(io).toFixed(1)}" x2="${x(io).toFixed(1)}" y1="${m.t - 22}" y2="${H - m.b}"/>`;
    if (!movil) s += `<text class="g-texto medio" x="${(x(io) - 6).toFixed(1)}" y="${H - m.b - 8}" text-anchor="end">Último dato real</text>`;
  }
  const anotar = (i, v, texto) => {
    const izq = x(i) + 12 + texto.length * 6.8 > W - 2; // si el rótulo no cabe a la derecha, va a la izquierda
    const tx = x(i) + (izq ? -9 : 9);
    const punto = `<circle class="g-punto" cx="${x(i).toFixed(1)}" cy="${y(v).toFixed(1)}" r="5"/>`;
    // Arriba del punto; si pisa otro rótulo, abajo; si tampoco cabe, queda el punto solo
    const ancla = izq ? 'end' : 'start';
    const ty = [y(v) - 10, y(v) + 20, y(v) - 26].find((t) => libre(cajaTexto(tx, t, texto, ancla)));
    if (ty == null) return punto;
    ocupado.push(cajaTexto(tx, ty, texto, ancla));
    return `${punto}<text class="g-texto fuerte" x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" text-anchor="${ancla}">${esc(texto)}</text>`;
  };
  const ip = d.fecha_hora.indexOf(d.pico.fecha_hora);
  if (ip >= 0) s += anotar(ip, d.pico.valor, movil ? `Pico ${mw(d.pico.valor)}` : `Pico ${mw(d.pico.valor)} · ${horaDe(d.pico.fecha_hora)}`);
  const im = d.manana ? d.fecha_hora.indexOf(d.manana.fecha_hora) : -1;
  if (!movil && im >= 0 && Math.abs(im - ip) > 10) s += anotar(im, d.manana.valor, `Mañana ${horaDe(d.manana.fecha_hora)}: ${mw(d.manana.valor)}`);
  s += rotuloRampa;
  // El hito de «ahora»: la línea, un halo alrededor del punto, su valor y la pastilla con la hora en el eje
  s += `<line class="g-ahora" x1="${x(ia).toFixed(1)}" x2="${x(ia).toFixed(1)}" y1="${m.t - 22}" y2="${H - m.b}"/>`;
  const anchoPastilla = 84;
  const gx = Math.min(Math.max(x(ia) - anchoPastilla / 2, m.l), W - m.r - anchoPastilla);
  s += `<rect class="g-pastilla" x="${gx.toFixed(1)}" y="${H - m.b + 4}" width="${anchoPastilla}" height="22" rx="11"/>`;
  s += `<text class="g-pastilla-texto" x="${(gx + anchoPastilla / 2).toFixed(1)}" y="${H - m.b + 19}" text-anchor="middle">${vivo ? 'Ahora' : 'A las'} ${esc(horaDe(d.ahora))}</text>`;
  const esReal = d.real[ia] != null;
  s += `<circle class="g-ahora-halo${esReal ? ' real' : ''}" cx="${x(ia).toFixed(1)}" cy="${y(vAhora).toFixed(1)}" r="12"/>`;
  s += `<circle class="g-punto g-ahora-punto${esReal ? ' real' : ''}" cx="${x(ia).toFixed(1)}" cy="${y(vAhora).toFixed(1)}" r="6"/>`;
  if (!movil) {
    s += `<rect class="g-ahora-valor${esReal ? ' real' : ''}" x="${vx.toFixed(1)}" y="${vy.toFixed(1)}" width="${anchoValor.toFixed(1)}" height="28" rx="7"/>`;
    s += `<text class="g-ahora-valor-texto" x="${(vx + anchoValor / 2).toFixed(1)}" y="${(vy + 20).toFixed(1)}" text-anchor="middle">${textoAhora}</text>`;
  }
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
  const ref = NOMBRE_REF[d.referencia_nombre] || 'la referencia';
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
    + `<dl class="pares"><dt>Error</dt><dd>${firmado(dif)} MW (${nf1.format(porc)} %)</dd><dt>Rango del ${d.nivel_rango_pct} %</dt><dd>${mw(y.inferior)} – ${mw(y.superior)} MW</dd></dl>`
    + `<div class="veredicto ${y.dentro ? 'bien' : 'ojo'}">${y.dentro ? ICONO.bien : ICONO.ojo}<span>Lo real cayó ${y.dentro ? 'dentro' : 'fuera'} del rango. ${Math.abs(dif) < 0.5 ? 'Acertó.' : `${dif > 0 ? 'Sobrestimó' : 'Subestimó'} por ${mw(Math.abs(dif))} MW.`}</span></div>`
    + `<p class="nota-pie"><span class="etiqueta-fuente">${fuente}</span></p>`;
}

function barrasCmp(modelo, referencia) {
  const tope = Math.max(modelo, referencia || 0) || 1;
  const fila = (nombre, v, clase) => `<div class="barra-cmp"><span>${nombre}</span><span class="pista"><i class="${clase}" style="width:${((100 * v) / tope).toFixed(1)}%"></i></span><b>${nf1.format(v)} MW</b></div>`;
  return fila('Pronóstico', modelo, 'i-pron') + (referencia != null ? fila('Referencia', referencia, 'i-ref') : '');
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
  const nombreRef = NOMBRE_REF[d.referencia_nombre] || 'la referencia';
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
    html = `<p class="sub">${esc(d.modelo_nombre)}: un modelo fundacional de series de tiempo, ajustado a la demanda del SEIN (Sistema Eléctrico Interconectado Nacional) con datos hasta 2024 y con los feriados de Perú. Cada mañana, con la demanda de ayer que publica el COES, pronostica las 48 medias horas de hoy. Queda registrado con su hora de emisión antes de conocerse el real y no se reescribe.</p>`;
  } else if (y && y.componentes && y.componentes.length) {
    const suma = y.componentes.reduce((t, c) => t + c.peso * (c.valores[0] || 0), 0);
    html = `<p class="sub">Lo calcula el modelo <b>${esc(d.modelo_nombre.replace(/\s*\(.*\)\s*$/, '').toLowerCase())}</b>, el de menor error en 2026. Lo que se dijo para las ${esc(horaDe(y.fecha_hora))}:</p>`
      + `<div class="formula">${y.componentes.map((c) => `${mw(c.valores[0])} × ${c.peso.toFixed(2)} <span class="muted">(${esc(c.nombre)})</span>`).join('<br>+ ')}<br>= <b>${mw(suma)} MW</b></div>`
      + '<p class="nota-pie">Pesos fijados con la validación de 2025 y aplicados tal cual a 2026. Usa solo la demanda y el calendario; no usa el clima. Chronos-2 es un modelo fundacional de series de tiempo, ajustado a esta demanda.</p>';
  } else {
    const m = modeloPorId(d.modelo);
    html = `<p class="sub">Lo calcula el modelo <b>${esc(d.modelo_nombre)}</b>. ${esc((m && m.descripcion) || '')}</p>`;
  }
  html += '<p class="enlaces">'
    + (repaso && repaso.fecha >= FECHA_MIN && repaso.fecha <= FECHA_MAX ? `<a class="btn-enlace" href="${rutaDetalle(A.area, repaso, 'escenarios')}">¿Y si hace más calor? →</a>` : '')
    + `<a class="btn-enlace" href="${rutaDetalle(A.area, repaso, 'diagnostico')}">Diagnóstico completo</a>`
    + `<a class="btn-enlace" href="${rutaDetalle(A.area, repaso)}">${repaso && repaso.fecha <= FECHA_MAX ? 'Otro modelo u horizonte' : 'Explorar el historial con otro modelo'}</a>`
    + '<button type="button" class="btn-enlace" data-accion="ficha">Ficha técnica: modelo y datos</button></p>';
  cont.innerHTML = html;
}

// El estado de «Confianza»: la pantalla se carga aparte, pero la cabecera y las rutas lo leen
const C = { area: 'centro', horizonte: '24h', mes: null, turno: 0, datos: null };

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

// ---- Pantallas que se cargan al abrirlas ---------------------------------------------------------------------

// «Confianza» y «Detalle» traen su código, su HTML y sus estilos al abrirlas por primera vez: «Ahora» no los paga.
// Se piden antes, sin costo, cuando el puntero o el foco llegan a un enlace hacia ellas.
const VISTA_DE = { confianza: '#vistaConfianza', detalle: '#vistaArea' };
const RECURSOS = new Map(); // un archivo que llegó no se vuelve a pedir (su código ya corrió); uno que falló, sí
function cargarRecurso(url) {
  if (!RECURSOS.has(url)) {
    RECURSOS.set(url, new Promise((ok, mal) => {
      const css = url.endsWith('.css');
      const el = document.createElement(css ? 'link' : 'script');
      if (css) {
        el.rel = 'stylesheet';
        el.href = url;
      } else el.src = url;
      el.onload = ok;
      el.onerror = () => {
        RECURSOS.delete(url);
        el.remove();
        mal(new ErrorApi(0, 'sin conexión'));
      };
      document.head.append(el);
    }));
  }
  return RECURSOS.get(url);
}
const PANTALLAS = {}; // nombre → promesa de la pantalla lista: código, estilos y HTML
const LISTAS = new Set();
function cargarPantalla(nombre) {
  if (!PANTALLAS[nombre]) {
    // El HTML se pinta cuando ya están el código y los estilos: nunca se ve sin estilo
    PANTALLAS[nombre] = Promise.all([cargarRecurso(`${nombre}.css`), cargarRecurso(`${nombre}.js`)]).then(() => {
      if (nombre === 'detalle') iniciarDetalle();
      else iniciarConfianza();
      LISTAS.add(nombre);
    }).catch((err) => {
      PANTALLAS[nombre] = null;
      throw err;
    });
  }
  return PANTALLAS[nombre];
}
const pantallaDeEnlace = (a) => {
  const m = a && /^#\/(confianza|area)\//.exec(a.getAttribute('href') || '');
  return m ? (m[1] === 'area' ? 'detalle' : 'confianza') : null;
};
function precargarPantalla(ev) {
  const nombre = pantallaDeEnlace(ev.target.closest && ev.target.closest('a[href^="#/"]'));
  if (nombre) cargarPantalla(nombre).catch(() => {});
}
// Una pantalla que todavía no se ve (al entrar por un enlace directo): un aviso en su lugar mientras baja
function esqueletoPantalla(nombre) {
  mostrarVista(nombre);
  $(VISTA_DE[nombre]).innerHTML = '<p class="cargando-bloque">Cargando la pantalla…</p>';
}
// Los datos de «Confianza» bajan junto con su código, no después: en una red lenta serían dos esperas en serie
function precargarConfianza(area, q) {
  const horizonte = ['1h', '24h'].includes(q.get('horizonte')) ? q.get('horizonte') : C.horizonte;
  const m = hayVariosModelos() && S.modelo ? S.modelo : null;
  const p = new URLSearchParams({ horizonte, variante: 'M3' });
  if (m) p.set('modelo', m);
  const a = encodeURIComponent(area);
  const rutas = [`/confianza/${a}?${p}`, `/en-vivo/${a}`];
  if (!S.diag.has(`${S.modelo || ''}|${area}`)) rutas.push(`/diagnostico/${a}${m ? `?modelo=${encodeURIComponent(m)}` : ''}`);
  rutas.forEach((ruta) => {
    if (PRECARGA.has(ruta)) return;
    const pedido = fetch(API + ruta).catch(() => null);
    PRECARGA.set(ruta, pedido);
    setTimeout(() => { if (PRECARGA.get(ruta) === pedido) PRECARGA.delete(ruta); }, 20000); // nada viejo
  });
}

function enrutar() {
  const r = leerRuta();
  const lista = S.areas.length ? S.areas : AREAS_RESPALDO;
  if (!lista.some((a) => a.id === r.area)) r.area = 'centro';
  guardar('tpf-area', r.area);
  const nombre = r.vista === 'confianza' ? 'confianza' : (r.vista === 'area' && S.areas.length ? 'detalle' : null);
  if (nombre && LISTAS.has(nombre)) {
    if (nombre === 'detalle') mostrarArea(r.area, r.q);
    else mostrarConfianza(r.area, r.q);
    return;
  }
  if (nombre) {
    // Mientras baja, la pantalla de la que se viene se atenúa y una línea avanza bajo la cabecera
    if (!$$('#app > main:not([hidden])').length) esqueletoPantalla(nombre);
    if (nombre === 'confianza') precargarConfianza(r.area, r.q);
    document.body.classList.add('cargando-pantalla');
    cargarPantalla(nombre).then(() => {
      document.body.classList.remove('cargando-pantalla');
      if (leerRuta().vista === r.vista) enrutar(); // con la ruta de ahora: pudo cambiar mientras bajaba
    }).catch((err) => {
      document.body.classList.remove('cargando-pantalla');
      if (leerRuta().vista !== r.vista) return;
      mostrarVista(nombre);
      $(VISTA_DE[nombre]).innerHTML = '<p class="vacio" role="alert">No pudimos cargar esta pantalla. Revisa la conexión y vuelve a intentarlo.</p>';
      mostrarError(err);
    });
    return;
  }
  if (r.raiz || r.vista === 'area') history.replaceState(null, '', rutaAhora(r.area));
  mostrarAhora(r.area, r.raiz ? new URLSearchParams() : r.q);
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
  if (LISTAS.has('detalle')) pintarSelectorModelo(); // si «Detalle» ya se cargó; si no, lo pinta al iniciarse
  aplicarModelo();
  $('#chipPrueba').hidden = salud.modelo !== 'prueba';
  pintarRegimen();
  pintarFicha();
}

async function iniciar() {
  const base = cargarBase();
  const ruta = leerRuta();
  const ahoraPrimero = ruta.vista === 'ahora';
  // Un enlace directo a «Confianza» o «Detalle»: su código baja junto con los datos de arranque, no después
  if (!ahoraPrimero) {
    const nombre = ruta.vista === 'area' ? 'detalle' : 'confianza';
    // Al reintentar tras un corte, una pantalla que ya está armada no se vacía: solo se vuelven a pedir sus datos
    if (!LISTAS.has(nombre)) {
      esqueletoPantalla(nombre);
      cargarPantalla(nombre).catch(() => {});
    }
  }
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
    if (S.vista === 'detalle' && LISTAS.has('detalle')) irASeccion('respuesta');
    else ((S.vista === 'confianza' && $('#cfTitular')) || $('#principal')).focus();
  });
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
  ['pointerover', 'focusin', 'touchstart'].forEach((t) => document.addEventListener(t, precargarPantalla, { passive: true }));
}

aplicarTema(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
conectarEventos();
iniciar();
