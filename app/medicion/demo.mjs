// El recorrido de la demo de la exposición (docs/demo/README.md): capturas, cronómetro y video.
//   node demo.mjs --cronometro   # el recorrido con un expositor simulado (140 palabras por minuto), sin grabar
//   node demo.mjs --capturas     # docs/demo/capturas/*.png: 1920×1080 en claro, R1-R3 y tres en el celular
//   node demo.mjs --video        # docs/demo/recorrido-demo.mp4 y corrida-diaria.mp4 (1920×1080, sin audio)
// La app debe estar levantada (app/levantar.sh). Variables: TPF_WEB (por defecto http://localhost:8080) y TPF_API
// (http://localhost:8000); con la API en otro puerto, las peticiones de la web a :8000 se desvían a TPF_API.
//
// La pantalla es la de Chrome con zoom del 150 % en una pantalla de 1920×1080: 1280×720 px de página, capturados a
// 1920×1080. Así el texto se sigue leyendo cuando Collaborate reduce la pantalla compartida a 1280×720 o menos.
import { copyFileSync, mkdirSync, mkdtempSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { API, WEB, abrirNavegador, vigilarRed } from './comun.mjs';

const args = process.argv.slice(2);
const DOCS = fileURLToPath(new URL('../../docs/demo/', import.meta.url));
const CAPTURAS = join(DOCS, 'capturas');
// La web busca la API en su mismo origen (o en :8000 si está en :8080): se le dice dónde está, sea cual sea el puerto.
const PAGINA = `${WEB}/?api=${API.replace(/\/+$/, '')}`;
const DESVIO = /^https?:\/\/(localhost|127\.0\.0\.1):8000\/?$/.test(API) ? null : API.replace(/\/+$/, '');

// El día de repaso y su respaldo. Fijos: no dependen del día en que se exponga.
export const DIA = { fecha: '2026-08-27', hora: '19:00', pico: ['vie 28', '15:00'] };
export const RESPALDO = { fecha: '2026-03-10', hora: '19:00' };
const RESPALDO_PICO = { fecha: '2026-03-11', hora: '14:30' }; // lo que deja tocar su pico
const ruta = (d) => `#/ahora/centro?fecha=${d.fecha}&hora=${d.hora}`;

// Lo que dice el expositor, en el orden en que lo hace. Las cifras de «hoy» cambian cada día: se leen de la pantalla.
export const PASOS = [
  {
    id: 'paso1', titulo: 'Hoy, en vivo', ruta: '#/ahora/centro', guion: [
      ['decir', 'Esta es Curva: corre nuestros modelos sobre la demanda que publica el COES. Lo real llega hasta ayer, '
        + 'porque el COES publica cada día a la mañana siguiente; desde la línea punteada todo es pronóstico, emitido '
        + 'hoy antes de conocer el real.'],
      // El recuadro de «lo que dijimos»: su título cambia si ese día no hay dato nuevo («Lo que se dijo un día antes»)
      ['bajar', '#ahAyerTit'],
      ['decir', 'Aquí, lo que dijimos para ayer a esta hora y lo que pasó.'],
    ],
  },
  {
    id: 'paso2', titulo: 'Un día de El Niño', ruta: ruta(DIA), guion: [
      ['decir', 'Ahora, un día de la prueba: el 27 de agosto de 2026, el mes en que el ICEN llegó a 3.98. El modelo no '
        + 'vio 2026 al entrenarse. Un día antes pronosticó 4,810 megavatios para las 19:00; fue 4,772, dentro del '
        + 'rango.'],
      ['tocarHora', DIA.pico],
      // Tras tocar el gráfico, el primer clic en un enlace se pierde (fallo de la app): un clic en el título lo evita.
      ['clic', 'text=/¿Acertamos/'],
      ['decir', 'Toco el pico: para las 15:00 del día siguiente dijo 5,007 y fue 5,027.'],
    ],
  },
  {
    id: 'paso3', titulo: '¿Y si hace más calor?', guion: [
      ['clic', 'role=link[name="¿Y si hace más calor?"]'],
      ['decir', '¿Y si mañana hace dos grados más? Lo calcula el XGBoost, el único modelo que usa el clima.'],
      ['clic', '[data-temp="2"]'],
      ['bajar', '#fraseEscenario'],
      ['decir', 'El pico sube 8 megavatios, 0.2 %: casi nada. Y en 2026 el clima empeoró el pronóstico a 24 horas: no '
        + 'conviene apoyarse en él en un evento extraordinario.'],
    ],
  },
  {
    id: 'paso4', titulo: 'Confianza', guion: [
      ['clic', 'role=link[name="Confianza"]'],
      ['decir', 'Aquí la app dice cuánto acertó: en 2026 le ganó a la referencia los diez meses, con 71.9 megavatios de '
        + 'error a 24 horas, 47 % menos, y su rango del 90 % cubrió el 91 %.'],
      ['decir', 'Y lo honesto: en vivo, desde el 13 de noviembre, el rango del 80 % cubre el 70 %: queda corto y lo '
        + 'mostramos en rojo. Es seguimiento en curso, no un resultado.'],
    ],
  },
  {
    id: 'paso5', titulo: 'Cierre', guion: [
      ['decir', 'El diseño lo medimos con instrumentos sintéticos; falta probarlo con personas.'],
    ],
  },
];

// Solo si sobran 30 segundos o si la profesora pregunta por el mantenimiento.
export const EXTRA = {
  id: 'extra', titulo: 'La corrida diaria (solo si preguntan)', ruta: ruta(DIA), guion: [
    ['clic', 'role=link[name="Detalle"]'],
    ['clic', '[data-ir="envivo"]'],
    ['decir', 'Esto corre solo cada mañana. Cuando el COES publica el anexo del día anterior, hacia las 9:45, la corrida '
      + 'lo baja, lo valida, pronostica el día y lo registra con su hora de emisión, antes de que exista el real.'],
    ['decir', 'Si el anexo no pasa las validaciones, no emite nada. Corren tres modelos en paralelo y todo se copia al '
      + 'Drive.'],
  ],
};

// Un expositor que lee con calma: 140 palabras por minuto; una cifra se dice en unas tres palabras.
const PALABRAS_POR_SEGUNDO = 140 / 60;
export function segundosDeHabla(texto) {
  const palabras = texto.split(/\s+/).filter(Boolean).reduce((n, p) => n + (/\d/.test(p) ? 3 : 1), 0);
  return palabras / PALABRAS_POR_SEGUNDO + 0.4;
}

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

async function nuevaPagina(navegador, { movil = false, cursor = false } = {}) {
  const contexto = await navegador.newContext(movil
    ? { viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }
    : { viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
  await contexto.addInitScript(() => { try { localStorage.setItem('tpf-tema', 'light'); } catch { /* nada */ } });
  if (cursor) await contexto.addInitScript(CURSOR);
  if (DESVIO) {
    await contexto.route(/^http:\/\/(localhost|127\.0\.0\.1):8000\//,
      (r) => r.continue({ url: r.request().url().replace(/^http:\/\/[^/]+/, DESVIO) }));
  }
  const pagina = await contexto.newPage();
  await pagina.emulateMedia({ colorScheme: 'light' });
  return { contexto, pagina, quieta: vigilarRed(pagina) };
}

// En el video, un puntero visible y un rótulo discreto con el paso (headless no dibuja el puntero).
const CURSOR = () => {
  const poner = () => {
    if (document.getElementById('demo-puntero')) return;
    const p = document.createElement('div');
    p.id = 'demo-puntero';
    p.style.cssText = 'position:fixed;left:-40px;top:-40px;width:22px;height:22px;margin:-11px 0 0 -11px;'
      + 'border-radius:50%;background:rgba(220,38,38,.35);border:2px solid #dc2626;z-index:2147483647;'
      + 'pointer-events:none;transition:transform .12s';
    const r = document.createElement('div');
    r.id = 'demo-rotulo';
    r.style.cssText = 'position:fixed;left:12px;bottom:12px;padding:4px 10px;border-radius:6px;'
      + 'background:rgba(15,23,42,.72);color:#fff;font:600 13px system-ui,sans-serif;z-index:2147483646;'
      + 'pointer-events:none';
    r.textContent = window.__rotulo || '';
    document.body.append(p, r);
    addEventListener('mousemove', (e) => { p.style.left = `${e.clientX}px`; p.style.top = `${e.clientY}px`; }, true);
    addEventListener('mousedown', () => { p.style.transform = 'scale(.6)'; }, true);
    addEventListener('mouseup', () => { p.style.transform = ''; }, true);
  };
  if (document.body) poner(); else addEventListener('DOMContentLoaded', poner);
};

async function rotular(pagina, texto) {
  await pagina.evaluate((t) => {
    window.__rotulo = t;
    const r = document.getElementById('demo-rotulo');
    if (r) r.textContent = t;
  }, texto).catch(() => {});
}

async function mover(pagina, x, y, suave) {
  if (suave) await pagina.mouse.move(x, y, { steps: 18 });
  else await pagina.mouse.move(x, y);
}

async function clic(pagina, selector, suave) {
  const objetivo = pagina.locator(selector).filter({ visible: true }).first();
  await objetivo.scrollIntoViewIfNeeded();
  const caja = await objetivo.boundingBox();
  await mover(pagina, caja.x + caja.width / 2, caja.y + caja.height / 2, suave);
  if (suave) await espera(250);
  await objetivo.click();
}

// Toca el gráfico de «Ahora» en la hora de una etiqueta del eje (la primera `hora` después de `dia`).
async function tocarHora(pagina, [dia, hora], suave) {
  const punto = await pagina.evaluate(([d, h]) => {
    const textos = [...document.querySelectorAll('#vistaAhora svg text')].filter((t) => t.getClientRects().length);
    const i = textos.findIndex((t) => t.textContent.trim() === d);
    const t = textos.slice(i + 1).find((x) => x.textContent.trim() === h);
    const svg = t.closest('svg').getBoundingClientRect();
    const r = t.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: svg.y + svg.height * 0.45 };
  }, [dia, hora]);
  await mover(pagina, punto.x, punto.y, suave);
  if (suave) await espera(250);
  await pagina.mouse.click(punto.x, punto.y);
}

async function bajar(pagina, selector, suave) {
  await pagina.locator(selector).filter({ visible: true }).first()
    .evaluate((el, s) => el.scrollIntoView({ block: 'center', behavior: s ? 'smooth' : 'instant' }), suave);
  await espera(suave ? 700 : 150);
  if (suave) await mover(pagina, 1255, 360, true); // el puntero a un margen, para que no tape el texto
}

// Recorre los pasos: cada acción se mide; cada frase espera lo que tarda en decirse.
async function recorrer(pagina, quieta, pasos, { hablar = true, suave = true, alPaso } = {}) {
  const tiempos = [];
  const t0 = Date.now();
  for (const [n, paso] of pasos.entries()) {
    const inicio = Date.now();
    await rotular(pagina, `${n + 1}/${pasos.length} · ${paso.titulo}`);
    let accion = 0;
    let habla = 0;
    if (paso.ruta) {
      const a = Date.now();
      await pagina.goto(`${PAGINA}${paso.ruta}`);
      await quieta();
      await pagina.evaluate(() => scrollTo(0, 0)); // como abrir la pestaña del paso
      await rotular(pagina, `${n + 1}/${pasos.length} · ${paso.titulo}`);
      accion += Date.now() - a;
    }
    for (const [tipo, valor] of paso.guion) {
      if (tipo === 'decir') {
        const s = segundosDeHabla(valor);
        habla += s * 1000;
        if (hablar) await espera(s * 1000);
        continue;
      }
      const a = Date.now();
      if (tipo === 'clic') await clic(pagina, valor, suave);
      else if (tipo === 'tocarHora') await tocarHora(pagina, valor, suave);
      else if (tipo === 'bajar') await bajar(pagina, valor, suave);
      await quieta();
      await rotular(pagina, `${n + 1}/${pasos.length} · ${paso.titulo}`);
      accion += Date.now() - a;
    }
    if (alPaso) await alPaso(paso);
    const r1 = (x) => Math.round(x * 10) / 10;
    tiempos.push({ paso: paso.id, titulo: paso.titulo, inicio: inicio / 1000,
      segundos: r1((Date.now() - inicio) / 1000), habla_s: r1(habla / 1000), acciones_s: r1(accion / 1000) });
  }
  return { tiempos, total: Math.round(Date.now() - t0) / 1000 };
}

const mmss = (s) => {
  const r = Math.round(s);
  return `${Math.floor(r / 60)}:${String(r % 60).padStart(2, '0')}`;
};

function imprimir({ tiempos, total }) {
  let acumulado = 0;
  for (const t of tiempos) {
    console.log(`${mmss(acumulado)}–${mmss(acumulado + t.segundos)}  ${t.titulo.padEnd(38)} ${t.segundos.toFixed(1)} s`
      + `  (habla ${t.habla_s.toFixed(1)} s, acciones ${t.acciones_s.toFixed(1)} s)`);
    acumulado += t.segundos;
  }
  console.log(`Total: ${mmss(total)} (${total.toFixed(1)} s)`);
}

// Graba con el screencast de Chrome: cuadros de 1920×1080 solo cuando la pantalla cambia, con su hora.
async function grabar(pagina, quieta, pasos, salida) {
  const dir = mkdtempSync(join(tmpdir(), 'tpf-demo-'));
  const cdp = await pagina.context().newCDPSession(pagina);
  const cuadros = [];
  cdp.on('Page.screencastFrame', async ({ data, metadata, sessionId }) => {
    const archivo = join(dir, `${String(cuadros.length).padStart(5, '0')}.jpg`);
    writeFileSync(archivo, Buffer.from(data, 'base64'));
    cuadros.push({ archivo, t: metadata.timestamp });
    await cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
  });
  await pagina.goto(`${PAGINA}${pasos[0].ruta}`);
  await quieta();
  await espera(800);
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1920, maxHeight: 1080 });
  const inicio = Date.now() / 1000;
  const medida = await recorrer(pagina, quieta, pasos, { hablar: true, suave: true });
  await espera(1500);
  const fin = Date.now() / 1000;
  await cdp.send('Page.stopScreencast');
  // A 30 cuadros por segundo: cada cuadro de salida repite el último que mostró la pantalla hasta ese instante.
  const t0 = Math.min(inicio, cuadros[0].t);
  const salidaDir = join(dir, 'salida');
  mkdirSync(salidaDir);
  let j = 0;
  for (let k = 0; k <= Math.ceil((fin - t0) * 30); k += 1) {
    const t = t0 + k / 30;
    while (j + 1 < cuadros.length && cuadros[j + 1].t <= t) j += 1;
    symlinkSync(cuadros[j].archivo, join(salidaDir, `${String(k).padStart(6, '0')}.jpg`));
  }
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', '30', '-i', join(salidaDir, '%06d.jpg'),
    '-vf', 'scale=1920:1080:flags=lanczos,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '24',
    '-tune', 'stillimage', '-movflags', '+faststart', '-an', salida]);
  // En qué segundo del video empieza cada paso
  for (const paso of medida.tiempos) {
    paso.en_el_video = mmss(paso.inicio - t0);
    delete paso.inicio;
  }
  medida.video_s = Math.round((fin - t0) * 10) / 10;
  rmSync(dir, { recursive: true, force: true });
  return medida;
}

async function capturas(navegador, carpeta) {
  const archivo = (nombre) => join(carpeta, `${nombre}.png`);
  const foto = (pagina, nombre) => pagina.screenshot({ path: archivo(nombre) });
  const { contexto, pagina, quieta } = await nuevaPagina(navegador);
  const ir = async (r) => {
    await pagina.goto(`${PAGINA}${r}`);
    await quieta();
    await pagina.evaluate(() => scrollTo(0, 0));
    await espera(400);
  };

  await ir('#/ahora/centro');
  await foto(pagina, 'paso1-hoy');
  await bajar(pagina, '#ahAyerTit', false);
  await foto(pagina, 'paso1b-lo-que-dijimos');

  await ir(ruta(DIA));
  await foto(pagina, 'paso2-repaso-27-08-2026');
  await tocarHora(pagina, DIA.pico, false);
  await quieta(); await espera(400);
  await clic(pagina, 'text=/¿Acertamos/', false);
  await foto(pagina, 'paso2b-pico-28-08-2026');
  await clic(pagina, 'role=link[name="¿Y si hace más calor?"]', false);
  await quieta();
  await clic(pagina, '[data-temp="2"]', false);
  await quieta(); await espera(400);
  await bajar(pagina, '#fraseEscenario', false);
  await foto(pagina, 'paso3-y-si-2c');
  await clic(pagina, 'role=link[name="Confianza"]', false);
  await quieta(); await espera(400);
  await foto(pagina, 'paso4-confianza');
  await bajar(pagina, 'h2:has-text("El seguimiento en vivo")', false);
  await foto(pagina, 'paso4b-confianza-en-vivo');
  await clic(pagina, '[data-cf-horizonte="1h"]', false);
  await quieta(); await espera(400);
  await pagina.evaluate(() => scrollTo(0, 0));
  await foto(pagina, 'paso4c-confianza-1h');

  await ir(ruta(DIA));
  await clic(pagina, 'role=link[name="Detalle"]', false);
  await quieta();
  await clic(pagina, '[data-ir="envivo"]', false);
  await quieta(); await espera(400);
  await foto(pagina, 'extra-corrida-diaria');
  await clic(pagina, '[data-ir="diagnostico"]', false);
  await quieta(); await espera(400);
  await foto(pagina, 'R2b-diagnostico');

  // Las del paper (figura 13 y diapositivas de respaldo R1-R3): el día de repaso, que no cambia con la fecha.
  await ir(ruta(DIA));
  await foto(pagina, 'R1-ahora');
  await clic(pagina, 'role=link[name="¿Y si hace más calor?"]', false);
  await quieta();
  await clic(pagina, '[data-temp="2"]', false);
  await quieta(); await espera(400);
  await bajar(pagina, '#fraseEscenario', false);
  await foto(pagina, 'R2-escenarios-2c');
  copyFileSync(archivo('paso4-confianza'), archivo('R3-confianza-en-vivo'));

  await ir(ruta(RESPALDO));
  await foto(pagina, 'respaldo-repaso-10-03-2026');
  // Tocar su pico deja la app en el 11/03 a las 14:30 (no es una etiqueta del eje: se abre por su enlace)
  await ir(ruta(RESPALDO_PICO));
  await foto(pagina, 'respaldo-pico-11-03-2026');
  await clic(pagina, 'role=link[name="¿Y si hace más calor?"]', false);
  await quieta();
  await clic(pagina, '[data-temp="2"]', false);
  await quieta(); await espera(400);
  await bajar(pagina, '#fraseEscenario', false);
  await foto(pagina, 'respaldo-y-si-11-03-2026');
  await contexto.close();

  // El paso 1 un día sin dato nuevo: el reloj de la API se pasa al día siguiente del último pronóstico, a las 19:00
  // (la hora de la exposición), como si esa mañana el COES no hubiera publicado.
  const ultimo = (await (await fetch(`${API}/en-vivo/centro`)).json()).ultimo;
  if (ultimo) {
    const manana = new Date(`${ultimo.fecha}T12:00:00Z`);
    manana.setUTCDate(manana.getUTCDate() + 1);
    const reloj = `${manana.toISOString().slice(0, 10)}T19:00`;
    const sinDato = await nuevaPagina(navegador);
    await sinDato.contexto.route(/\/ahora\/centro(\?(?!.*origen=)[^#]*)?$/, (r) => {
      const url = new URL(r.request().url());
      url.searchParams.set('ahora', reloj);
      return r.fallback({ url: url.toString() });
    });
    await sinDato.pagina.clock.setFixedTime(new Date(`${reloj}:00-05:00`));
    await sinDato.pagina.goto(`${PAGINA}#/ahora/centro`);
    await sinDato.quieta(); await espera(400);
    await sinDato.pagina.screenshot({ path: archivo('paso1-sin-dato-nuevo') });
    await sinDato.contexto.close();
  }

  const movil = await nuevaPagina(navegador, { movil: true });
  for (const [nombre, r] of [['movil-hoy', '#/ahora/centro'], ['movil-repaso', ruta(DIA)],
    ['movil-confianza', '#/confianza/centro']]) {
    await movil.pagina.goto(`${PAGINA}${r}`);
    await movil.quieta(); await espera(400);
    await movil.pagina.screenshot({ path: archivo(nombre) });
  }
  await movil.contexto.close();

  // El plan B en un PDF: una página por paso, en el orden del recorrido.
  return ['paso1-hoy', 'paso1b-lo-que-dijimos', 'paso2-repaso-27-08-2026', 'paso2b-pico-28-08-2026',
    'paso3-y-si-2c', 'paso4-confianza', 'paso4b-confianza-en-vivo', 'extra-corrida-diaria'];
}

async function pdf(navegador, orden, carpeta, destino) {
  const dir = mkdtempSync(join(tmpdir(), 'tpf-plan-b-'));
  const html = join(dir, 'plan-b.html');
  writeFileSync(html, `<!doctype html><meta charset="utf-8"><style>@page{size:1920px 1080px;margin:0}body{margin:0}
    img{display:block;width:1920px;height:1080px;break-after:page}</style>`
    + orden.map((n) => `<img src="${pathToFileURL(join(carpeta, `${n}.png`)).href}">`).join(''));
  const hoja = await navegador.newPage();
  await hoja.goto(pathToFileURL(html).href, { waitUntil: 'load' });
  await hoja.pdf({ path: destino, width: '1920px', height: '1080px', printBackground: true });
  await hoja.close();
  rmSync(dir, { recursive: true, force: true });
}

// Todo se genera en una carpeta temporal y se copia a docs/demo solo si la generación terminó: un corte a medias no
// deja capturas o videos de dos corridas mezclados.
function publicar(origen, destino) {
  mkdirSync(destino, { recursive: true });
  for (const nombre of readdirSync(origen)) copyFileSync(join(origen, nombre), join(destino, nombre));
}

const navegador = await abrirNavegador();
try {
  if (args.includes('--capturas')) {
    const tmp = mkdtempSync(join(tmpdir(), 'tpf-capturas-'));
    const orden = await capturas(navegador, tmp);
    await pdf(navegador, orden, tmp, join(tmp, 'plan-b-capturas.pdf'));
    copyFileSync(join(tmp, 'plan-b-capturas.pdf'), join(DOCS, 'plan-b-capturas.pdf'));
    rmSync(join(tmp, 'plan-b-capturas.pdf'));
    publicar(tmp, CAPTURAS);
    rmSync(tmp, { recursive: true, force: true });
    console.log(`Capturas en ${CAPTURAS} y el PDF del plan B en ${join(DOCS, 'plan-b-capturas.pdf')}`);
  }
  if (args.includes('--video')) {
    try {
      execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' });
    } catch {
      throw new Error('--video necesita ffmpeg en el PATH (en Ubuntu: sudo apt install ffmpeg).');
    }
    const { contexto, pagina, quieta } = await nuevaPagina(navegador, { cursor: true });
    const tmp = mkdtempSync(join(tmpdir(), 'tpf-videos-'));
    const medida = await grabar(pagina, quieta, PASOS, join(tmp, 'recorrido-demo.mp4'));
    imprimir(medida);
    const extra = await grabar(pagina, quieta, [EXTRA], join(tmp, 'corrida-diaria.mp4'));
    imprimir(extra);
    writeFileSync(join(tmp, 'cronometro.json'), `${JSON.stringify({
      medido: new Date().toISOString(), palabras_por_minuto: 140, recorrido: medida, extra,
    }, null, 2)}\n`);
    publicar(tmp, DOCS);
    rmSync(tmp, { recursive: true, force: true });
    await contexto.close();
  }
  if (args.includes('--cronometro')) {
    const { contexto, pagina, quieta } = await nuevaPagina(navegador);
    imprimir(await recorrer(pagina, quieta, PASOS));
    await contexto.close();
  }
} finally {
  await navegador.close();
}
