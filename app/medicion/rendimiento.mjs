// Peso de la página, peticiones, terceros y tiempos hasta el primer gráfico y hasta la respuesta
// (el número pronosticado en pantalla), en red local y en una red lenta simulada.
import { mediana, nuevaPagina, rango, URL_AREA, WEB } from './comun.mjs';
import { version } from './versiones.mjs';

const RED_LENTA = { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 };

async function unaCarga(navegador, ficha, lenta, url = URL_AREA) {
  const { contexto, pagina } = await nuevaPagina(navegador, 'movil');
  const cdp = await contexto.newCDPSession(pagina);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  if (lenta) {
    await cdp.send('Network.emulateNetworkConditions', RED_LENTA);
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  }
  await pagina.addInitScript((f) => {
    window.__marcas = {};
    const re = new RegExp(`(?<![\\d,.])${f.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\d])`);
    const mirar = () => {
      const m = window.__marcas;
      if (!m.grafico && document.querySelector('svg path.ln-pronostico')) m.grafico = performance.now();
      if (!m.respuesta && document.body && re.test(document.body.innerText)) m.respuesta = performance.now();
    };
    new MutationObserver(mirar).observe(document, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['hidden'] });
  }, ficha);
  const peticiones = [];
  pagina.on('requestfinished', async (req) => {
    try {
      const s = await req.sizes();
      peticiones.push({ url: req.url(), tipo: req.resourceType(), bytes: s.responseBodySize + s.responseHeadersSize });
    } catch { /* nada */ }
  });
  await pagina.goto(url);
  await pagina.waitForFunction(() => window.__marcas && window.__marcas.grafico && window.__marcas.respuesta, null, { timeout: 60000 }).catch(() => {});
  await pagina.waitForLoadState('networkidle').catch(() => {});
  const marcas = await pagina.evaluate(() => window.__marcas);
  await contexto.close();
  const origen = new URL(WEB).host;
  const api = new URL(url).hostname;
  return {
    grafico_ms: marcas.grafico ? Math.round(marcas.grafico) : null,
    respuesta_ms: marcas.respuesta ? Math.round(marcas.respuesta) : null,
    peticiones: peticiones.length,
    bytes: peticiones.reduce((s, p) => s + p.bytes, 0),
    bytes_por_tipo: peticiones.reduce((o, p) => ({ ...o, [p.tipo]: (o[p.tipo] || 0) + p.bytes }), {}),
    terceros: peticiones.filter((p) => { const h = new URL(p.url).hostname; return h !== api && new URL(p.url).host !== origen; }).length,
  };
}

export async function medirRendimiento(navegador, ficha, repeticiones = 5, nombreVersion = null) {
  const v = nombreVersion ? version(nombreVersion) : {};
  const url = (v.url && v.url('area')) || URL_AREA;
  const salida = {};
  for (const [nombre, lenta] of [['local', false], ['red_lenta', true]]) {
    const corridas = [];
    for (let i = 0; i < repeticiones; i += 1) corridas.push(await unaCarga(navegador, ficha, lenta, url));
    salida[nombre] = {
      grafico_ms: mediana(corridas.map((c) => c.grafico_ms)),
      grafico_rango_ms: rango(corridas.map((c) => c.grafico_ms)),
      respuesta_ms: mediana(corridas.map((c) => c.respuesta_ms)),
      respuesta_rango_ms: rango(corridas.map((c) => c.respuesta_ms)),
    };
    if (!lenta) {
      const c = corridas[0];
      salida.peticiones = c.peticiones;
      salida.kb = Math.round(c.bytes / 1024);
      salida.kb_por_tipo = Object.fromEntries(Object.entries(c.bytes_por_tipo).map(([k, v]) => [k, Math.round(v / 1024)]));
      salida.peticiones_a_terceros = c.terceros;
    }
  }
  return salida;
}
