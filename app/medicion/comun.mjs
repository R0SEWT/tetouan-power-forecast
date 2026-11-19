// Utilidades compartidas por los scripts de medición.
// La app debe estar levantada: backend en API (por defecto :8000) y web en WEB (por defecto :8080).
import { chromium } from 'playwright';

export const WEB = process.env.TPF_WEB || 'http://localhost:8080';
export const API = process.env.TPF_API || 'http://localhost:8000';
// La web busca la API en el puerto 8000 de su mismo host. Si el arnés corre con la API en otro puerto (la app del
// dueño puede estar abierta en :8000), esas peticiones se desvían a TPF_API sin tocar la web ni sus enlaces; una
// ruta de la página (como la de «sin API», que corta :8000) manda sobre este desvío.
const DESVIO_API = /^https?:\/\/(localhost|127\.0\.0\.1):8000\/?$/.test(API) ? null : API.replace(/\/+$/, '');

// El caso de las tareas: Centro, martes 10 de marzo de 2026 (prueba, El Niño extraordinario), 19:00.
export const CASO = { area: 'centro', fecha: '2026-03-10', hora: '19:00', idx: 38, horizonte: '24h', variante: 'M3' };
export const URL_AREA = `${WEB}/#/area/${CASO.area}?fecha=${CASO.fecha}&hora=${CASO.hora}&horizonte=${CASO.horizonte}&variante=${CASO.variante}`;

export const VISTAS = {
  movil: { width: 375, height: 812, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  escritorio: { width: 1366, height: 768, isMobile: false, hasTouch: false, deviceScaleFactor: 1 },
};

export async function abrirNavegador() {
  try {
    return await chromium.launch({ channel: 'chrome' });
  } catch {
    return chromium.launch();
  }
}

export async function nuevaPagina(navegador, vista = 'escritorio', tema = 'dark') {
  const v = VISTAS[vista];
  const contexto = await navegador.newContext({
    viewport: { width: v.width, height: v.height },
    isMobile: v.isMobile,
    hasTouch: v.hasTouch,
    deviceScaleFactor: v.deviceScaleFactor,
    locale: 'es-PE',
    timezoneId: 'America/Lima',
    colorScheme: tema,
    reducedMotion: 'reduce', // desplazamientos instantáneos: lo que se mide no depende de una animación
  });
  await contexto.addInitScript((t) => {
    try { localStorage.setItem('tpf-tema', t === 'light' ? 'light' : 'dark'); } catch { /* nada */ }
  }, tema);
  if (DESVIO_API) {
    await contexto.route(/^http:\/\/(localhost|127\.0\.0\.1):8000\//, (r) => r.continue({ url: r.request().url().replace(/^http:\/\/[^/]+/, DESVIO_API) }));
  }
  const pagina = await contexto.newPage();
  return { contexto, pagina };
}

export async function api(ruta, cuerpo) {
  const r = await fetch(API + ruta, cuerpo
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) }
    : undefined);
  if (!r.ok) throw new Error(`${ruta}: ${r.status}`);
  return r.json();
}

// Texto que se ve dentro de la ventana: nodos de texto visibles cuyo rectángulo cae en el viewport
// y que no están tapados por otro elemento (se prueba el punto central de cada línea).
export async function textoVisible(pagina) {
  return pagina.evaluate(() => {
    const vw = innerWidth;
    const vh = innerHeight;
    const trozos = [];
    const caminante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let nodo;
    while ((nodo = caminante.nextNode())) {
      const t = nodo.textContent.replace(/\s+/g, ' ').trim();
      if (!t) continue;
      const el = nodo.parentElement;
      if (!el || el.closest('[hidden]')) continue;
      const estilo = getComputedStyle(el);
      if (estilo.visibility === 'hidden' || estilo.display === 'none' || Number(estilo.opacity) === 0) continue;
      const rango = document.createRange();
      rango.selectNodeContents(nodo);
      const rects = [...rango.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
      const visible = rects.some((r) => {
        const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2));
        const cy = r.top + r.height / 2;
        if (cy < 0 || cy > vh || r.right < 0 || r.left > vw) return false;
        const arriba = document.elementFromPoint(cx, cy);
        return arriba && (arriba === el || el.contains(arriba) || arriba.contains(el)
          || (arriba.closest && arriba.closest('svg') && el.closest('svg') === arriba.closest('svg')));
      });
      if (visible) trozos.push(t);
    }
    return trozos.join(' | ');
  });
}

export const fmt0 = (x) => new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(x);
export const fmt1 = (x) => new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(x);

export function mediana(xs) {
  const v = xs.filter((x) => x != null && !Number.isNaN(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

export function rango(xs) {
  const v = xs.filter((x) => x != null && !Number.isNaN(x));
  return v.length ? [Math.min(...v), Math.max(...v)] : [null, null];
}

// Espera a que no haya peticiones en vuelo durante `quieto` ms (la app pide datos tras cada cambio).
export function vigilarRed(pagina) {
  let enVuelo = 0;
  let ultimo = Date.now();
  const mas = () => { enVuelo += 1; ultimo = Date.now(); };
  const menos = () => { enVuelo = Math.max(0, enVuelo - 1); ultimo = Date.now(); };
  pagina.on('request', mas);
  pagina.on('requestfinished', menos);
  pagina.on('requestfailed', menos);
  return async (quieto = 350, tope = 20000) => {
    const t0 = Date.now();
    await new Promise((r) => setTimeout(r, 60));
    while (Date.now() - t0 < tope) {
      if (enVuelo === 0 && Date.now() - ultimo >= quieto) return;
      await new Promise((r) => setTimeout(r, 50));
    }
  };
}
