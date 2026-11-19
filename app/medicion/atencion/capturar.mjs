// Captura cada pantalla × viewport × tema y recoge lo que necesita la auditoría de atención:
// la captura de la ventana (lo que se ve sin desplazarse), las cajas de las AOI, los elementos fijos que tapan,
// los controles y textos visibles, y las métricas baratas (desborde, caracteres por línea, colores fuera del
// sistema, escala tipográfica).
//
//   node atencion/capturar.mjs --etiqueta base [--pantallas inicio,ahora] [--vistas movil] [--temas light]
//
// Escribe resultados/tmp/atencion/<etiqueta>/<pantalla>-<vista>-<tema>.png y .../capturas.json.
// Requiere la app levantada (ver app/levantar.sh); TPF_WEB y TPF_API como en el resto del arnés.
import { mkdirSync, writeFileSync } from 'node:fs';
import { abrirNavegador } from '../comun.mjs';
import { PANTALLAS, TEMAS, VISTAS } from './pantallas.mjs';

const args = process.argv.slice(2);
const opcion = (nombre, defecto) => { const i = args.indexOf(`--${nombre}`); return i >= 0 ? args[i + 1] : defecto; };
const etiqueta = opcion('etiqueta', 'base');
const lista = (nombre, todos) => (opcion(nombre, null) ? opcion(nombre).split(',') : todos);
const pantallas = lista('pantallas', Object.keys(PANTALLAS));
const vistas = lista('vistas', Object.keys(VISTAS));
const temas = lista('temas', TEMAS);
const destino = new URL(`../resultados/tmp/atencion/${etiqueta}/`, import.meta.url);
mkdirSync(destino, { recursive: true });

// Se ejecuta dentro de la página.
function recolectar(aoiConfig) {
  const vw = innerWidth;
  const vh = innerHeight;
  const R = (r) => [r.left, r.top, r.right, r.bottom].map((v) => Math.round(v));
  const visibleEstilo = (e) => {
    if (e.closest('[hidden]')) return false;
    // Lo que está dentro de un <details> cerrado (content-visibility: hidden) conserva sus cajas, pero no se pinta
    if (e.checkVisibility && !e.checkVisibility()) return false;
    const c = getComputedStyle(e);
    return c.display !== 'none' && c.visibility !== 'hidden' && Number(c.opacity) > 0;
  };
  const cajaTexto = (e) => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect(); };
  const encima = (e, r) => {
    const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2));
    const cy = r.top + r.height / 2;
    if (cy < 0 || cy >= vh || r.right <= 0 || r.left >= vw) return false;
    const a = document.elementFromPoint(cx, cy);
    return Boolean(a && (a === e || e.contains(a) || a.contains(e) || (a.closest('svg') && a.closest('svg') === e.closest('svg'))));
  };

  // Elementos fijos (barras): tapan lo que pasa por debajo.
  const fijos = [];
  for (const e of document.querySelectorAll('body *')) {
    if (getComputedStyle(e).position !== 'fixed' || !visibleEstilo(e)) continue;
    if (fijos.some((f) => f.el.contains(e))) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 2 || r.height < 2 || r.bottom <= 0 || r.top >= vh) continue;
    fijos.push({ el: e, caja: R(r), id: `${e.tagName.toLowerCase()}${e.id ? `#${e.id}` : ''}${e.className && typeof e.className === 'string' ? `.${e.className.split(' ')[0]}` : ''}` });
  }

  const aoi = {};
  for (const { n, s, modo } of aoiConfig) {
    const els = [...document.querySelectorAll(s)].filter(visibleEstilo);
    const cajas = [];
    const tapan = new Set();
    for (const e of els) {
      const usaCaja = modo === 'caja' || e instanceof SVGElement || e.querySelector('svg,img,canvas,video');
      let r = usaCaja ? e.getBoundingClientRect() : cajaTexto(e);
      if (e instanceof SVGGeometryElement) {
        // Una <line> vertical tiene caja geométrica de ancho 0: se suma el trazo pintado, al menos 1 px por lado.
        const t = Math.max(1, (parseFloat(getComputedStyle(e).strokeWidth) || 0) / 2);
        r = new DOMRect(r.left - t, r.top - t, r.width + 2 * t, r.height + 2 * t);
        if (r.width <= 1 || r.height <= 1) continue;
        cajas.push([Math.floor(r.left), Math.floor(r.top), Math.ceil(r.right), Math.ceil(r.bottom)]);
      } else {
        if (r.width <= 1 || r.height <= 1) continue;
        cajas.push(R(r));
      }
      fijos.forEach((f, i) => { if (!f.el.contains(e) && !e.contains(f.el)) tapan.add(i); });
    }
    aoi[n] = { cajas, tapan: [...tapan], existe: els.length > 0 };
  }

  const SEL_CONTROL = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [role=tab], [role=link], label:has(input[type=checkbox])';
  const etiquetaDe = (e) => {
    const lb = e.getAttribute('aria-labelledby');
    const t = e.getAttribute('aria-label')
      || (lb && lb.split(' ').map((id) => document.getElementById(id)?.textContent || '').join(' '))
      || (e.labels && e.labels.length ? [...e.labels].map((l) => l.textContent).join(' ') : '')
      || e.innerText || e.value || e.title || '';
    return t.replace(/\s+/g, ' ').trim().slice(0, 90);
  };
  const interactivos = [];
  for (const e of document.querySelectorAll(SEL_CONTROL)) {
    if (!visibleEstilo(e)) continue;
    if (e.matches('input[type=checkbox]') && e.closest('label')) continue; // cuenta la etiqueta, no la casilla
    const r = e.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) continue;
    const grupo = e.closest('[aria-label], nav, section')?.getAttribute('aria-label') || '';
    interactivos.push({ etiqueta: etiquetaDe(e), tag: e.tagName.toLowerCase(), tipo: e.type || e.getAttribute('role') || '', grupo, caja: R(r), visible: encima(e, r), id: e.id || '', actual: e.getAttribute('aria-current') || e.getAttribute('aria-pressed') || '' });
  }

  const textos = [];
  const caminante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let nodo;
  while ((nodo = caminante.nextNode())) {
    const t = nodo.textContent.replace(/\s+/g, ' ').trim();
    const el = nodo.parentElement;
    if (!t || !el || !visibleEstilo(el) || el.closest('script,style,title,dialog:not([open])')) continue;
    const rango = document.createRange();
    rango.selectNodeContents(nodo);
    const rects = [...rango.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
    if (!rects.length) continue;
    const c = getComputedStyle(el);
    const titulo = el.closest('[title], abbr[title]')?.getAttribute('title') || '';
    textos.push({ t, caja: R(rango.getBoundingClientRect()), visible: rects.some((r) => encima(el, r)), fs: parseFloat(c.fontSize), fw: Number(c.fontWeight), color: c.color, ayuda: titulo, svg: Boolean(el.closest('svg')) });
  }

  // Caracteres por línea de los bloques de texto corrido (los de dos líneas o más).
  const lineas = [];
  for (const e of document.querySelectorAll('p, li, dd, .d, .sub, .lead, figcaption, summary')) {
    if (!visibleEstilo(e) || e.querySelector('p, li, div')) continue;
    const texto = e.textContent.replace(/\s+/g, ' ').trim();
    if (texto.length < 40) continue;
    const r = document.createRange();
    r.selectNodeContents(e);
    const tops = new Set([...r.getClientRects()].filter((x) => x.width > 2).map((x) => Math.round(x.top / 4)));
    if (tops.size < 2) continue;
    const caja = e.getBoundingClientRect();
    lineas.push({ sel: `${e.tagName.toLowerCase()}${e.id ? `#${e.id}` : ''}.${String(e.className).split(' ')[0]}`, ch: Math.round(texto.length / tops.size), lineas: tops.size, visible: caja.top < vh && caja.bottom > 0, texto: texto.slice(0, 60) });
  }

  // Colores: los tokens del sistema (variables de :root ya resueltas) contra los colores que se usan.
  const nombres = new Set();
  for (const hoja of document.styleSheets) {
    let reglas = [];
    try { reglas = [...hoja.cssRules]; } catch { continue; }
    for (const regla of reglas) {
      if (!regla.selectorText || !/:root/.test(regla.selectorText)) continue;
      for (const p of regla.style) if (p.startsWith('--')) nombres.add(p);
    }
  }
  const centinela = document.createElement('div');
  centinela.style.color = 'rgb(1, 2, 3)';
  const sonda = document.createElement('span');
  centinela.appendChild(sonda);
  document.body.appendChild(centinela);
  const tokens = {};
  for (const n of nombres) {
    sonda.style.color = `var(${n})`;
    const v = getComputedStyle(sonda).color;
    if (v !== 'rgb(1, 2, 3)') tokens[n] = v;
  }
  centinela.remove();
  const usados = new Map();
  const anotar = (color, prop, e) => {
    if (!color || color === 'none' || color.startsWith('url') || /rgba\(\d+, \d+, \d+, 0\)/.test(color) || color === 'transparent') return;
    const k = `${color}|${prop}`;
    if (!usados.has(k)) usados.set(k, { color, prop, n: 0, ejemplo: `${e.tagName.toLowerCase()}${e.id ? `#${e.id}` : ''}.${String(e.className?.baseVal ?? e.className).split(' ')[0]}` });
    usados.get(k).n += 1;
  };
  const FORMAS = new Set(['path', 'rect', 'circle', 'polygon', 'ellipse', 'text', 'tspan']);
  for (const e of document.querySelectorAll('body *')) {
    if (!visibleEstilo(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    const c = getComputedStyle(e);
    if (e instanceof SVGElement) {
      const tag = e.tagName.toLowerCase();
      if (FORMAS.has(tag)) anotar(c.fill, 'fill', e);
      if (tag !== 'svg' && tag !== 'g' && c.stroke !== 'none' && parseFloat(c.strokeWidth) > 0) anotar(c.stroke, 'stroke', e);
      continue;
    }
    if ([...e.childNodes].some((x) => x.nodeType === 3 && x.textContent.trim())) anotar(c.color, 'color', e);
    anotar(c.backgroundColor, 'fondo', e);
    for (const lado of ['Top', 'Right', 'Bottom', 'Left']) {
      if (parseFloat(c[`border${lado}Width`]) > 0 && c[`border${lado}Style`] !== 'none') { anotar(c[`border${lado}Color`], 'borde', e); break; }
    }
  }

  const tamanos = {};
  const familias = new Set();
  for (const x of textos) tamanos[x.fs] = (tamanos[x.fs] || 0) + 1;
  for (const e of document.querySelectorAll('body *')) {
    if (visibleEstilo(e) && [...e.childNodes].some((x) => x.nodeType === 3 && x.textContent.trim())) familias.add(getComputedStyle(e).fontFamily.split(',')[0].replace(/"/g, '').trim());
  }

  const fuera = [];
  for (const e of document.querySelectorAll('body *')) {
    if (!visibleEstilo(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.width > 0 && r.right > vw + 1 && !e.closest('.chart, svg, .tabla-scroll, table')) fuera.push(`${e.tagName.toLowerCase()}.${String(e.className?.baseVal ?? e.className).split(' ')[0]} +${Math.round(r.right - vw)}px`);
  }

  return {
    vp: { ancho: vw, alto: vh },
    doc: { alto: document.documentElement.scrollHeight, ancho: document.documentElement.scrollWidth },
    fijos: fijos.map(({ caja, id }) => ({ caja, id })),
    aoi,
    interactivos,
    textos,
    lineas,
    colores: { tokens, usados: [...usados.values()] },
    tipografia: { tamanos, familias: [...familias] },
    desborde: { horizontal_px: Math.max(0, document.documentElement.scrollWidth - vw), elementos: fuera.slice(0, 12), n_elementos: fuera.length },
    modo: document.querySelector('#estadoDatos')?.textContent.trim() || '',
  };
}

const navegador = await abrirNavegador();
const salida = { etiqueta, fecha: new Date().toISOString(), capturas: [] };
try {
  for (const pantalla of pantallas) {
    const cfg = PANTALLAS[pantalla];
    for (const vista of vistas) {
      const v = VISTAS[vista];
      for (const tema of temas) {
        const contexto = await navegador.newContext({
          viewport: { width: v.width, height: v.height },
          isMobile: Boolean(v.isMobile),
          hasTouch: Boolean(v.hasTouch),
          deviceScaleFactor: 1,
          locale: 'es-PE',
          timezoneId: 'America/Lima',
          colorScheme: tema,
          reducedMotion: 'reduce',
        });
        await contexto.addInitScript((t) => { try { localStorage.setItem('tpf-tema', t); } catch { /* nada */ } }, tema);
        const p = await contexto.newPage();
        await p.goto(cfg.url());
        await p.waitForSelector(cfg.listo, { timeout: 30000 });
        await p.waitForLoadState('networkidle');
        if (cfg.esperar) await p.waitForFunction(cfg.esperar, null, { timeout: 30000 });
        await p.waitForTimeout(900);
        await p.mouse.move(0, v.height - 1); // sin cursor sobre el gráfico
        const datos = await p.evaluate(recolectar, cfg.aoi);
        const nombre = `${pantalla}-${vista}-${tema}`;
        await p.screenshot({ path: new URL(`${nombre}.png`, destino).pathname });
        salida.capturas.push({ nombre, pantalla, vista, tema, aoi_orden: cfg.aoi.map((a) => a.n), ...datos });
        console.log(`${nombre}: ${datos.interactivos.filter((x) => x.visible).length} controles a la vista, documento ${datos.doc.alto}px`);
        await contexto.close();
      }
    }
  }
} finally {
  await navegador.close();
}
writeFileSync(new URL('capturas.json', destino), JSON.stringify(salida));
console.log(`Guardado en ${destino.pathname}`);
