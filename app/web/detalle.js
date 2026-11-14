'use strict';

/* ==========================================================================
   Curva · «Detalle»: el detalle del área, sus escenarios, el diagnóstico y el registro en vivo.
   Se carga al abrir la pantalla (cargarPantalla, en app.js) y usa las utilidades y el estado de app.js.
   ========================================================================== */

const INFO_AREA = {
  norte: { letra: 'N', fg: '#000', desc: 'Costa norte: Piura, Chiclayo y Trujillo. Lluvias con El Niño y carga minera e industrial.' },
  centro: { letra: 'C', fg: '#fff', desc: 'Lima y el centro: Electroandes, minería e industria. El calor del verano pesa en Lima.' },
  sur: { letra: 'S', fg: '#000', desc: 'Dominada por la minería: Cerro Verde, Las Bambas y Southern. Responde poco al clima.' },
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

const MOMENTOS = [
  { txt: 'Madrugada', idx: 6 }, { txt: 'Mañana', idx: 18 }, { txt: 'Mediodía', idx: 25 },
  { txt: 'Tarde', idx: 32 }, { txt: 'Noche', idx: 40 },
];
const TEMPERATURAS = [-2, 0, 2, 4];

const origen = () => `${S.fecha}T${idxAHora(S.idx)}`;

// «19:30 del martes 10 de marzo», para un inicio de periodo AAAA-MM-DDTHH:MM
const cuandoTxt = (fechaHora) => `${horaDe(fechaHora)} del ${fechaDiaMes(fechaHora)}`;

// «Combinado (recomendado)» → «combinado», para usarlo dentro de una frase
const nombreCorto = (m) => (m ? m.nombre.replace(/\s*\(.*\)\s*$/, '').toLowerCase() : 'modelo');

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

function itemLinea(clase, texto) {
  return `<li><svg width="26" height="10" viewBox="0 0 26 10" aria-hidden="true"><line x1="1" y1="5" x2="25" y2="5" class="linea ${clase}"/></svg>${esc(texto)}</li>`;
}

function itemBanda(clase, texto) {
  return `<li><svg width="26" height="12" viewBox="0 0 26 12" aria-hidden="true"><rect x="1" y="1" width="24" height="10" rx="2" class="${clase}"/><line x1="1" y1="6" x2="25" y2="6" class="linea ln-pronostico"/></svg>${esc(texto)}</li>`;
}

const ITEM_HUECO = '<li><svg width="18" height="12" viewBox="0 0 18 12" aria-hidden="true"><rect x="0.5" y="0.5" width="17" height="11" fill="none" class="hueco-rect"/><line x1="3" y1="11" x2="9" y2="1" class="hueco-trama"/><line x1="9" y1="11" x2="15" y2="1" class="hueco-trama"/></svg>Sin datos</li>';
const ITEM_PRELIMINAR = '<li><svg width="18" height="12" viewBox="0 0 18 12" aria-hidden="true"><rect x="0" y="7" width="18" height="5" class="prelim-rect"/></svg>Preliminar</li>';

// ---- Detalle del área -------------------------------------------------------------------

function escribirRuta() {
  const q = new URLSearchParams({
    fecha: S.fecha, hora: idxAHora(S.idx), horizonte: S.horizonte, variante: S.variante,
  });
  if (hayVariosModelos() && S.modelo) q.set('modelo', S.modelo);
  const destino = `#/area/${encodeURIComponent(S.area)}?${q}`;
  if (location.hash !== destino) history.replaceState(null, '', destino);
  pintarEstado({ modo: 'repaso', texto: `Repaso · ${fechaNumerica(S.fecha)}, ${idxAHora(S.idx)}`,
    corto: ['Repaso', `${fechaNumerica(S.fecha).replace(/\/20(\d\d)$/, '/$1')} ${idxAHora(S.idx)}`],
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
  if (pico != null) lista.push({ txt: conReal ? 'Pico real del día' : 'Pico pronosticado', idx: pico });
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
  document.title = `${area.nombre}, detalle · ${TITULO_CURVA}`;

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
    html += `<p>En esta media hora falta el pronóstico de ${esc(faltan.map((c) => c.nombre).join(' y '))}: el número usa la referencia.</p>`;
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
  const ref = NOMBRE_REF[s.referencia_nombre] || 'la referencia';
  if (Math.abs(maeRef - maeModelo) < 0.5) {
    ver.textContent = `Este día se equivocó lo mismo que la referencia, ${ref}.`;
  } else if (mejora > 0) {
    ver.classList.add('bueno');
    ver.textContent = `Este día se equivocó ${nf0.format(mejora)} % menos que la referencia, ${ref} (${nf1.format(maeRef)} MW).`;
  } else {
    ver.classList.add('malo');
    ver.textContent = `Este día se equivocó ${nf0.format(-mejora)} % más que la referencia, ${ref} (${nf1.format(maeRef)} MW).`;
  }
}

// Qué tan bueno es: el error del día frente a la referencia, la cobertura del rango y la prueba de 2026.
function pintarConfianza() {
  const s = S.serie;
  if (!s) return;
  const maeModelo = mae(s.real, s.pronostico);
  const maeRef = mae(s.real, s.referencia);
  const ref = TITULO_REF[s.referencia_nombre] || 'Regla simple';
  const barras = $('#barrasConfianza');
  if (maeModelo != null && maeRef != null) {
    const tope = Math.max(maeModelo, maeRef) || 1;
    const fila = (nombre, valor, clase) => `<div class="barra-fila"><span class="barra-nombre">${esc(nombre)}</span>`
      + `<span class="barra-pista"><span class="barra ${clase}" style="width:${((100 * valor) / tope).toFixed(1)}%"></span></span>`
      + `<span class="barra-valor num">${nf1.format(valor)} MW</span></div>`;
    barras.innerHTML = '<p class="muted small">Error medio de este día (menos es mejor)</p>'
      + fila('Pronóstico', maeModelo, 'barra-modelo-h') + fila(`Referencia (${ref.toLowerCase()})`, maeRef, 'barra-referencia-h');
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
    if (n) items.push(`<li><strong>Rango del 90 %:</strong> la demanda real cayó dentro en <span class="num">${dentro}</span> de <span class="num">${n}</span> medias horas del día (se espera alrededor de 9 de cada 10).</li>`);
  }
  const met = S.resumen && S.resumen.metricas_prueba[S.area];
  if (met) items.push(`<li><strong>En toda la prueba de 2026</strong> (a 24 h, ${usaSoloDemanda(modeloActual()) ? 'solo con la demanda' : 'con clima y El Niño'}): error medio <span class="num">${nf1.format(met.mae_mw)} MW</span> (<span class="num">${pct(met.mape_pct)}</span>). Mes a mes, en «Diagnóstico».</li>`);
  items.push('<li><strong>Referencia:</strong> la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora). Es la vara mínima que el modelo debe superar.</li>');
  $('#listaConfianza').innerHTML = items.join('');
}

function pintarCurva() {
  const s = S.serie;
  const el = $('#graficoDia');
  if (!s) return;
  const nombreRef = TITULO_REF[s.referencia_nombre] || 'Referencia';
  const banda = s.intervalo ? { inf: s.intervalo.inferior, sup: s.intervalo.superior, clase: 'banda-pronostico', nombre: 'Rango del 90 %' } : null;
  const series = [
    { clase: 'ln-referencia', valores: s.referencia, nombre: `Referencia (${nombreRef.toLowerCase()})` },
    { clase: 'ln-pronostico', valores: s.pronostico, nombre: 'Pronóstico', banda },
    { clase: 'ln-real', valores: s.real, nombre: 'Real', puente: true },
  ];
  const pico = indicePico();
  const resumen = pico != null && s.real[pico] != null
    ? ` El pico real fue ${mw(s.real[pico])} MW a las ${idxAHora(pico)}.`
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
    aria: `Curva del ${fechaLarga(S.fecha)}: demanda real, pronóstico a ${horizonteTxt()} con su rango del 90 % y la referencia (${nombreRef.toLowerCase()}).${resumen}`,
  });
  $('#subCurva').textContent = `${fechaCorta(S.fecha)} · a ${horizonteTxt()}`;

  let leyenda = itemLinea('ln-real', 'Real') + itemLinea('ln-pronostico', 'Pronóstico');
  if (banda) leyenda += itemBanda('banda-pronostico', 'Rango del 90 %');
  leyenda += itemLinea('ln-referencia', `Referencia (${nombreRef.toLowerCase()})`);
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
    + '<thead><tr><th scope="col">Hora</th><th scope="col" class="num">Pronóstico</th><th scope="col" class="num">Rango del 90 %</th><th scope="col" class="num">Real</th><th scope="col" class="num">Referencia</th></tr></thead>'
    + `<tbody>${filas}</tbody></table></div>`;
}

// ---- Pico y mayor subida de las próximas 24 h -------------------------------------------------

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
  html += `<div><dt>Pico</dt><dd><span class="pico-valor num">${mw(pico.valor)} MW</span> a las ${esc(cuandoTxt(pico.fecha_hora))}`
    + `<span class="pico-nota">Rango del 90 %: <span class="num">${mw(pico.inferior)} – ${mw(pico.superior)} MW</span></span></dd></div>`;
  if (rampa) {
    html += `<div><dt>Mayor subida en una hora</dt><dd><span class="pico-valor num">+${mw(rampa.subida_mw)} MW</span> de las ${esc(horaDe(rampa.desde))} a las ${esc(cuandoTxt(rampa.hasta))}`
      + `<span class="pico-nota"><span class="marca ${rampa.fuerte ? 'fuera' : 'dentro'}">${rampa.fuerte ? 'rampa fuerte' : 'subida habitual'}</span></span></dd></div>`;
  } else {
    html += '<div><dt>Mayor subida en una hora</dt><dd>La demanda pronosticada no sube en ninguna hora de la ventana.</dd></div>';
  }
  html += '</dl>';
  if (acierto) {
    html += `<p class="pico-acierto">¿Acierta la hora? En 2026, la hora del pico pronosticado de cada día cayó a ±1 h de la del pico real en <strong class="num">${nf1.format(acierto.pct_hora)} %</strong> de los días`
      + ` (${nf0.format(acierto.dias)}); la referencia, en ${nf1.format(acierto.pct_hora_referencia)} %. El valor del pico se equivocó en promedio <span class="num">${mw(acierto.mae_pico_mw)} MW</span> (la referencia, ${mw(acierto.mae_pico_referencia_mw)} MW).</p>`;
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
  <li><strong>Rango del 90 %:</strong> la banda donde debería caer la demanda 9 de cada 10 veces.</li>
  <li><strong>Referencia:</strong> la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora) en la validación de 2025.</li>
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
    html += '<table class="tabla"><thead><tr><th scope="col">Hora</th><th scope="col" class="num">Pronóstico</th><th scope="col" class="num">Rango del 90 %</th><th scope="col" class="num">Real</th></tr></thead><tbody>';
    html += p.fecha_hora.map((fh, j) => (
      `<tr><td class="mono">${horaDe(fh)}</td><td class="num mono">${mw(p.pronostico[j])}</td>`
      + `<td class="num mono">${mw(p.intervalo.inferior[j])}–${mw(p.intervalo.superior[j])}</td>`
      + `<td class="num mono">${p.real[j] == null ? 'sin dato' : mw(p.real[j])}</td></tr>`
    )).join('');
    html += '</tbody></table>';
  } else {
    html += '<div id="graficoOperacion" class="chart"></div>';
    html += `<ul class="legend">${itemLinea('ln-real', 'Real')}${itemLinea('ln-pronostico', 'Pronóstico')}${itemBanda('banda-pronostico', 'Rango del 90 %')}${itemLinea('ln-referencia', 'Referencia (la mejor regla simple)')}</ul>`;
  }
  html += NOTAS_OPERACION;
  panel.innerHTML = html;
  if (S.horizonte === '24h') {
    graficoLineas($('#graficoOperacion'), {
      n: p.fecha_hora.length,
      series: [
        { clase: 'ln-referencia', valores: p.referencia, nombre: 'Referencia (la mejor regla simple)' },
        { clase: 'ln-pronostico', valores: p.pronostico, nombre: 'Pronóstico', banda: { inf: p.intervalo.inferior, sup: p.intervalo.superior, clase: 'banda-pronostico', nombre: 'Rango del 90 %' } },
        { clase: 'ln-real', valores: p.real, nombre: 'Real', puente: true },
      ],
      etiquetaX: (j) => (j % 12 === 11 ? horaDe(p.fecha_hora[j]) : null),
      etiquetaPunto: (j) => `${fechaCorta(p.fecha_hora[j])} ${horaDe(p.fecha_hora[j])}`,
      alto: 200,
      aria: `Pronóstico de las próximas 24 horas desde las ${idxAHora(S.idx)}, con su rango del 90 %. ${p.frase}`,
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
      <ul class="legend"><li><svg width="18" height="11" aria-hidden="true"><rect width="18" height="11" rx="3" class="barra-modelo"/></svg>Pronóstico</li><li><svg width="18" height="11" aria-hidden="true"><rect x="0.75" y="0.75" width="16.5" height="9.5" rx="3" class="barra-referencia"/></svg>Referencia</li></ul>
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
  })), { aria: 'Error del modelo y de la referencia según la fase de El Niño.' });

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
  const nombreRef = (TITULO_REF[sel.referencia_nombre] || 'Regla simple').toLowerCase();
  const leyenda = modelos.map((m, k) => itemLinea(clases[k] || 'ln-modelo-3', m.nombre)).join('') + itemLinea('ln-referencia', `Referencia (${nombreRef})`);
  const meta = sel.meta_cobertura_pct;

  // Lecturas: la conclusión de cada gráfico, calculada
  const ganados = sel.meses.filter((m) => m.mae_modelo < m.mae_referencia).length;
  const peor = sel.meses.reduce((a, b) => (b.mae_modelo > a.mae_modelo ? b : a));
  const totales = modelos.map((m, k) => `${nombreCorto(m)} ${nf1.format(res[k].total.mae_modelo)} MW`).join('; ');
  const lecMae = `Todo 2026, a ${horizonteTxt()}: ${totales}; la referencia, ${nf1.format(sel.total.mae_referencia)} MW. `
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
      { clase: 'ln-referencia', valores: sel.meses.map((m) => m.mae_referencia), nombre: `Referencia (${nombreRef})` },
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
      + (gana === regs.length ? `Le gana a la referencia en las ${regs.length} fases.` : `Le gana a la referencia en ${gana} de ${regs.length} fases.`);
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

// ---- En vivo: lo que registra cada día la tubería con el anexo del COES ---------------------------------------

const TIPO_DIA = { en_vivo: 'En vivo', reconstruido: 'Reconstruido' };

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
  const linea = (r) => `error medio <span class="num">${nf1.format(r.mae_modelo)} MW</span>; la referencia (${esc(REF_CORTA[r.referencia_nombre] || r.referencia_nombre)}), <span class="num">${nf1.format(r.mae_referencia)} MW</span>; el rango del 80 % cubrió el <span class="num">${nf0.format(r.cobertura_pct)} %</span> (promete 80 %)`;
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
    <ul class="legend" aria-label="Leyenda">${itemLinea('ln-pronostico', 'Pronóstico')}${itemBanda('banda-pronostico', 'Rango del 80 % (8 de cada 10)')}${hayReal ? itemLinea('ln-real', 'Real') : ''}</ul>
    ${hayReal ? '' : '<p class="muted small">El real de este día llega mañana, con el anexo del COES.</p>'}
    <h3 class="diag-sub">Lo ya verificado contra el real</h3>
    <ul class="lista-confianza">${items.join('')}</ul>
    ${a24.length ? `<details class="tabla-datos"><summary>Ver el error de cada día a 24 h</summary>
      <div class="tabla-scroll" tabindex="0" role="region" aria-label="Error de cada día a 24 h"><table class="tabla">
        <caption class="visually-hidden">Error medio en MW del modelo y de la referencia, y cobertura del rango del 80 %, por día pronosticado a 24 h</caption>
        <thead><tr><th scope="col">Día</th><th scope="col">Tipo</th><th scope="col" class="num">Pronóstico</th><th scope="col" class="num">Referencia</th><th scope="col" class="num">Cobertura</th></tr></thead>
        <tbody>${filas}</tbody></table></div>
      <p class="muted small">Error medio del día en MW. Referencia (la mejor en el acumulado de cada tipo): ${esc(refsTabla)}.</p>
    </details>` : ''}
    <p class="muted small">Modelo: ${esc(d.modelo || '—')}${d.version_pesos ? ` · pesos <span class="mono">${esc(d.version_pesos.slice(0, 12))}</span>` : ''}. Datos del IEOD del COES.</p>`;

  const resumenGrafico = hayReal
    ? ` El error medio del día fue ${nf1.format(mae(u.real, u.pronostico))} MW.`
    : ' El real todavía no se publica.';
  graficoLineas($('#gEnVivo'), {
    n: u.fecha_hora.length,
    series: [
      { clase: 'ln-pronostico', valores: u.pronostico, nombre: 'Pronóstico', banda: { inf: u.inferior, sup: u.superior, clase: 'banda-pronostico', nombre: 'Rango del 80 %' } },
      { clase: 'ln-real', valores: u.real, nombre: 'Real', puente: true },
    ],
    marcador: idxEmision != null ? { i: idxEmision, txt: `Emitido ${horaDe(u.emitido_lima)}` } : null,
    etiquetaX: (i) => (i % 12 === 0 ? idxAHora(i) : null),
    etiquetaPunto: (i) => horaDe(u.fecha_hora[i]),
    alto: 220,
    aria: `Pronóstico en vivo a 24 h del ${fechaLarga(u.fecha)} con su rango 10–90 %.${resumenGrafico}`,
  });
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

// ---- La pantalla: su HTML, sus eventos y el selector de modelo ----------------------------------------------

const HTML_DETALLE = `
  <div class="area-header">
    <a href="#/" class="btn-back" id="detVolver" aria-label="Volver a «Ahora»">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
    </a>
    <span id="areaBadge" class="area-badge" aria-hidden="true"></span>
    <div>
      <h1 id="areaNombre">Área</h1>
      <p id="areaDesc" class="muted">Elige la anticipación, los datos y el modelo; prueba escenarios y mira el diagnóstico completo.</p>
    </div>
  </div>

  <nav class="nav-secciones" aria-label="Secciones de esta área">
    <button type="button" data-ir="respuesta">Pronóstico</button>
    <button type="button" data-ir="curva">Curva</button>
    <button type="button" data-ir="escenarios">¿Y si…?</button>
    <button type="button" data-ir="diagnostico">Diagnóstico</button>
    <button type="button" data-ir="envivo">En vivo</button>
  </nav>

  <div class="area-grid">
    <div class="col-principal">
      <!-- La respuesta: el número, su rango, lo real y qué tan bueno fue -->
      <section id="respuesta" class="respuesta" aria-labelledby="respTitulo" aria-busy="true" tabindex="-1">
        <div class="resp-cabeza">
          <p class="resp-kicker" id="respKicker">Pronóstico</p>
          <span id="respEstado" class="resp-estado" role="status"></span>
        </div>
        <h2 id="respTitulo" class="resp-titulo">Calculando el pronóstico…</h2>
        <p id="respEmision" class="resp-emision muted"></p>
        <p id="respAviso" class="resp-aviso" hidden></p>
        <p class="resp-valor"><span id="respValor" class="num">—</span> <span class="unidad">MW</span></p>
        <p class="resp-rango">
          <span class="resp-rango-txt">Rango del 90 %</span>
          <span id="respRango" class="num">—</span>
          <span id="respMarca"></span>
          <span class="muted small resp-rango-ayuda">9 de cada 10 veces la demanda cae aquí</span>
        </p>
        <dl class="resp-datos">
          <div><dt>Real</dt><dd id="respReal">—</dd></div>
          <div><dt>Error</dt><dd id="respError">—</dd></div>
          <div><dt>Error medio del día</dt><dd id="respDia">—</dd></div>
        </dl>
        <p id="respVeredicto" class="resp-veredicto" aria-live="polite"></p>
        <details id="respFicha" class="resp-ficha">
          <summary><span class="resp-ficha-titulo">¿De dónde sale este número?</span> <span id="respFichaResumen" class="muted"></span></summary>
          <div id="respFichaCuerpo" class="resp-ficha-cuerpo"></div>
        </details>
      </section>

      <section class="panel controles" aria-labelledby="tituloControles">
        <h2 id="tituloControles" class="visually-hidden">Qué pronóstico ver</h2>
        <div class="control-row">
          <div class="field field-grow">
            <span class="field-label" id="lblHorizonte">Con cuánta anticipación</span>
            <div class="segmented" role="group" aria-labelledby="lblHorizonte">
              <button type="button" data-horizonte="1h" aria-pressed="true">1 hora</button>
              <button type="button" data-horizonte="24h" aria-pressed="false">24 horas</button>
            </div>
          </div>
          <div class="field field-grow">
            <span class="field-label" id="lblVariante">Datos que usa</span>
            <div class="segmented" role="group" aria-labelledby="lblVariante" aria-describedby="ayudaVariante">
              <button type="button" data-variante="M0" aria-pressed="false">Solo demanda</button>
              <button type="button" data-variante="M3" aria-pressed="true">Con clima y El Niño</button>
            </div>
          </div>
        </div>
        <p id="ayudaVariante" class="field-help">«Con clima y El Niño» también usa las fallas en curso de la red.</p>
        <div class="control-row">
          <label class="field field-grow">
            <span class="field-label">Día</span>
            <input type="date" id="inFecha" min="2025-01-01" max="2026-10-31" required aria-describedby="fechaLarga fechaAviso">
            <span id="fechaLarga" class="field-help"></span>
          </label>
          <div class="field">
            <span class="field-label" id="lblHora">Hora</span>
            <output id="outHora" class="time-pill" for="inHora" aria-labelledby="lblHora">15:00</output>
          </div>
        </div>
        <p id="fechaAviso" class="field-aviso" hidden></p>
        <div>
          <input type="range" id="inHora" min="0" max="47" step="1" value="30" aria-label="Hora del pronóstico" aria-valuetext="15:00">
          <div class="slider-ticks" aria-hidden="true"><span>00:00</span><span>06:00</span><span>12:00</span><span>18:00</span><span>23:30</span></div>
        </div>
        <div id="momentos" class="moment-chips" role="group" aria-label="Ir a un momento del día"></div>

        <label class="field" id="campoModelo">
          <span class="field-label">Qué modelo usa</span>
          <select id="inModelo" aria-describedby="ayudaModelo"></select>
        </label>
        <p id="ayudaModelo" class="field-help" hidden></p>
      </section>

      <section id="pico" class="panel pico" aria-labelledby="tituloPico" aria-busy="true">
        <h2 id="tituloPico">Pico y mayor subida de las próximas 24 h</h2>
        <div id="picoCuerpo"><p class="cargando-txt">Calculando…</p></div>
      </section>

      <section id="confianza" class="panel confianza" aria-labelledby="tituloConfianza">
        <h2 id="tituloConfianza">¿Qué tan bueno es?</h2>
        <div id="barrasConfianza" class="barras-confianza"></div>
        <ul id="listaConfianza" class="lista-confianza"></ul>
      </section>

      <!-- En vivo: lo que registra cada día la tubería con el anexo del COES (GET /en-vivo/{area}) -->
      <section id="envivo" class="panel envivo" aria-labelledby="tituloEnVivo" aria-busy="true" tabindex="-1">
        <h2 id="tituloEnVivo">En vivo</h2>
        <div id="envivoCuerpo"><p class="cargando-txt">Cargando el pronóstico en vivo…</p></div>
      </section>
    </div>

    <div class="col-detalle">
      <section id="curva" class="panel" aria-labelledby="tituloCurva" tabindex="-1">
        <div class="panel-head">
          <h2 id="tituloCurva">La curva del día</h2>
          <span id="subCurva" class="muted small"></span>
        </div>
        <div id="graficoDia" class="chart" aria-busy="true"></div>
        <ul id="leyendaDia" class="legend" aria-label="Leyenda"></ul>
        <p id="notaDatos" class="muted small" hidden></p>
        <p class="muted small">Cada punto del modelo se emitió con la anticipación elegida. Toca la curva para elegir la hora.</p>
        <details id="tablaDia" class="tabla-datos">
          <summary>Ver los datos del día en una tabla</summary>
          <div id="tablaDiaCuerpo"></div>
        </details>
      </section>

      <section id="detalle" class="panel detalle" aria-label="Más detalle" tabindex="-1">
        <div class="sheet-tabs" role="tablist" aria-label="Más detalle">
          <button type="button" role="tab" class="sheet-tab" id="tab-operacion" aria-controls="panel-operacion" aria-selected="true" data-tab="operacion">Próximas horas</button>
          <button type="button" role="tab" class="sheet-tab" id="tab-escenarios" aria-controls="panel-escenarios" aria-selected="false" tabindex="-1" data-tab="escenarios">¿Y si…?</button>
          <button type="button" role="tab" class="sheet-tab" id="tab-diagnostico" aria-controls="panel-diagnostico" aria-selected="false" tabindex="-1" data-tab="diagnostico">Diagnóstico</button>
        </div>
        <div role="tabpanel" id="panel-operacion" class="tab-panel" aria-labelledby="tab-operacion" tabindex="0"></div>
        <div role="tabpanel" id="panel-escenarios" class="tab-panel" aria-labelledby="tab-escenarios" tabindex="0" hidden></div>
        <div role="tabpanel" id="panel-diagnostico" class="tab-panel" aria-labelledby="tab-diagnostico" tabindex="0" hidden></div>
      </section>
    </div>
  </div>`;

function pintarSelectorModelo() {
  $('#inModelo').innerHTML = S.modelos.map((m) => `<option value="${esc(m.id)}">${esc(m.nombre)}</option>`).join('');
  $('#campoModelo').classList.toggle('unico', S.modelos.length === 1);
}

function conectarDetalle() {
  $('.nav-secciones').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-ir]');
    if (!b) return;
    irASeccion(b.dataset.ir);
    if (b.dataset.ir === 'envivo') cargarEnVivo(); // por si la tubería emitió algo desde que se abrió el área
  });
  $('#tablaDia').addEventListener('toggle', pintarTablaDia);

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
}

// La llama cargarPantalla (app.js) cuando llegaron este código y sus estilos
function iniciarDetalle() {
  $('#vistaArea').innerHTML = HTML_DETALLE;
  conectarDetalle();
  if (S.modelos.length) pintarSelectorModelo(); // si no, lo pinta cargarBase al terminar
}
