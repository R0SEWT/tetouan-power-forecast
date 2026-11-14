// Playtest sintético, paso 1: las capturas que verá el evaluador externo, y lo que hace falta para codificar sus
// respuestas sin mirar la interfaz a mano.
//
// Por pantalla: la ventana al abrir (vista-1) y una o dos ventanas más abajo (vista-2, vista-3), como las vería
// alguien que se desplaza; el árbol de accesibilidad de la página (para la variante solo texto); y, por vista, los
// textos y controles visibles con su zona (la AOI de atencion/pantallas.mjs o el id más cercano), para ubicar las dudas
// y los primeros clics que cite el evaluador. Además, los oráculos (cifras calculadas desde la API, no desde la
// pantalla) con los que se califican las lecturas.
//
//   TPF_WEB=http://localhost:8190 TPF_API=http://localhost:8130 node app/medicion/juego/capturar.mjs punta
//
// Salida: app/medicion/juego/tmp/<etiqueta>/ (fuera de git): <pantalla>/vista-N.png, <pantalla>/aria.yaml y
// <pantalla>/textos.json; y app/medicion/juego/resultados/<etiqueta>/pantallas.json (versionado): el manifiesto con los
// oráculos y, por vista, los textos y controles visibles con su zona, que es lo que usa analizar.py.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { abrirNavegador, api, nuevaPagina, vigilarRed, WEB } from '../comun.mjs';
import { PANTALLAS as AOI_PANTALLAS } from '../atencion/pantallas.mjs';
import { PANTALLAS } from './pantallas.mjs';
import { oraculos } from '../tareas.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const etiqueta = process.argv[2];
if (!etiqueta) {
  console.error('Uso: node capturar.mjs <etiqueta>');
  process.exit(1);
}
const SALIDA = join(AQUI, 'tmp', etiqueta);
const RESULTADOS = join(AQUI, 'resultados', etiqueta);
const VISTA = { ancho: 1366, alto: 768, solape: 100 };

// Textos y controles visibles en la ventana, con la zona a la que pertenecen.
async function leerVista(pagina, aoi) {
  return pagina.evaluate((defs) => {
    const vw = innerWidth;
    const vh = innerHeight;
    const zonas = defs.map((d) => ({ n: d.n, els: [...document.querySelectorAll(d.s)] }));
    const zonaDe = (el) => {
      for (const z of zonas) if (z.els.some((e) => e === el || e.contains(el))) return z.n;
      const conId = el.closest('[id]');
      if (conId && conId !== document.body) return `#${conId.id}`;
      const hito = el.closest('header, nav, main, footer, section, aside');
      return hito ? hito.tagName.toLowerCase() : 'resto';
    };
    const visible = (el, r) => {
      if (!r.width || !r.height) return false;
      const cx = Math.min(vw - 1, Math.max(0, r.left + r.width / 2));
      const cy = r.top + r.height / 2;
      if (cy < 0 || cy > vh || r.right < 0 || r.left > vw) return false;
      const arriba = document.elementFromPoint(cx, cy);
      return Boolean(arriba && (arriba === el || el.contains(arriba) || arriba.contains(el)
        || (arriba.closest && arriba.closest('svg') && el.closest('svg') === arriba.closest('svg'))));
    };
    const textos = [];
    const caminante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let nodo;
    while ((nodo = caminante.nextNode())) {
      const t = nodo.textContent.replace(/\s+/g, ' ').trim();
      const el = nodo.parentElement;
      if (!t || !el || el.closest('[hidden]')) continue;
      const estilo = getComputedStyle(el);
      if (estilo.visibility === 'hidden' || estilo.display === 'none' || Number(estilo.opacity) === 0) continue;
      const rango = document.createRange();
      rango.selectNodeContents(nodo);
      const r = [...rango.getClientRects()].find((x) => visible(el, x));
      if (r) textos.push({ t, zona: zonaDe(el), x: Math.round(r.left), y: Math.round(r.top) });
    }
    const etiquetaDe = (el) => {
      const porId = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
      const implicita = el.labels && el.labels[0] ? el.labels[0].innerText : '';
      return (el.getAttribute('aria-label') || (porId && porId.textContent) || implicita || el.innerText || el.value
        || el.getAttribute('title') || el.getAttribute('placeholder') || '').replace(/\s+/g, ' ').trim();
    };
    const controles = [...document.querySelectorAll('a[href], button, input, select, summary, [role=tab], [role=button], [tabindex="0"]')]
      .filter((el) => !el.closest('[hidden]') && visible(el, el.getBoundingClientRect()))
      .map((el) => ({
        etiqueta: etiquetaDe(el),
        tipo: el.type ? `${el.tagName.toLowerCase()}:${el.type}` : el.tagName.toLowerCase(),
        valor: el.value && el.tagName === 'INPUT' ? el.value : undefined,
        zona: zonaDe(el),
      }));
    return { textos, controles };
  }, aoi);
}

async function capturar(navegador, nombre, def) {
  const dir = join(SALIDA, nombre);
  mkdirSync(dir, { recursive: true });
  const { contexto, pagina } = await nuevaPagina(navegador, 'escritorio', 'light');
  const quieto = vigilarRed(pagina);
  await pagina.goto(def.url());
  await pagina.locator(def.listo).first().waitFor({ timeout: 30000 });
  if (def.esperar) await pagina.waitForFunction(def.esperar, null, { timeout: 30000 });
  await quieto(600);
  if (def.accion) {
    await def.accion(pagina);
    await quieto(600);
    if (def.esperar) await pagina.waitForFunction(def.esperar, null, { timeout: 30000 });
  }
  await pagina.waitForTimeout(700); // la app salta a la sección en un requestAnimationFrame
  const aoi = (AOI_PANTALLAS[def.aoi]?.aoi || []).map(({ n, s }) => ({ n, s }));
  const alto = await pagina.evaluate(() => document.documentElement.scrollHeight);
  if (def.desde === 'arriba') await pagina.evaluate(() => window.scrollTo(0, 0));
  const y0 = await pagina.evaluate(() => scrollY);
  const vistas = [];
  for (let i = 0; i < def.vistas; i += 1) {
    const y = y0 + i * (VISTA.alto - VISTA.solape);
    if (i > 0 && y >= alto - VISTA.solape) break;
    await pagina.evaluate((yy) => window.scrollTo(0, yy), y);
    await pagina.waitForTimeout(250);
    const real = await pagina.evaluate(() => scrollY);
    if (i > 0 && real - vistas[vistas.length - 1].y < 200) break; // la página no da más (o casi nada más)
    const archivo = `vista-${i + 1}.png`;
    await pagina.screenshot({ path: join(dir, archivo) });
    vistas.push({ archivo, y: real, ...(await leerVista(pagina, aoi)) });
  }
  const aria = await pagina.locator('body').ariaSnapshot();
  writeFileSync(join(dir, 'aria.yaml'), aria);
  writeFileSync(join(dir, 'textos.json'), JSON.stringify(vistas, null, 1));
  await contexto.close();
  return { pantalla: nombre, alto, vistas: vistas.map((v) => ({ archivo: v.archivo, y: v.y })) };
}

// Los oráculos de las lecturas: las cifras que tiene que encontrar el evaluador, calculadas desde la API.
async function oraculosJuego() {
  const o = await oraculos();
  const conf = await api('/confianza/centro');
  const meses = [...conf.seguimiento.meses, conf.seguimiento.total];
  const num = (xs) => [...new Set(xs.filter((x) => x != null).map(Number))];
  // Lo que la entrada tiene que contar del momento que muestra: la cifra de ese momento y lo que se había
  // pronosticado para él un día antes, con su rango (lo mismo que T1 en el repaso de las 19:00)
  const lectura = async (consulta) => {
    const r = await api(`/ahora/centro${consulta}`);
    const a = r.ayer || {};
    return {
      momento: r.ahora,
      modo: r.modo,
      cifra: num([r.cifra_ahora?.valor, a.real]),
      pronostico: num([a.pronostico]),
      inferior: num([a.inferior]),
      superior: num([a.superior]),
      real: num([a.real]),
    };
  };
  return {
    lectura: {
      hoy: await lectura(''),
      'repaso-1030': await lectura('?origen=2026-03-10T10:30'),
      'repaso-1900': await lectura('?origen=2026-03-10T19:00'),
    },
    t1: o.t1.grupos,
    // T2 en «Confianza»: el error (MAE total o de un mes, MAPE o WAPE) y si es mejor que la referencia
    t2: {
      error: num([...meses.map((m) => m.mae_modelo), conf.mape_pct, conf.wape_pct]),
      referencia: num(meses.map((m) => m.mae_referencia)),
      mejor_que_referencia: conf.seguimiento.total.mae_modelo < conf.seguimiento.total.mae_referencia,
    },
    t3: o.t3.grupos,
    t4: o.t4.grupos,
  };
}

const navegador = await abrirNavegador();
const pantallas = [];
for (const [nombre, def] of Object.entries(PANTALLAS)) {
  pantallas.push(await capturar(navegador, nombre, def));
  console.log(`${nombre}: ${pantallas[pantallas.length - 1].vistas.length} vistas`);
}
await navegador.close();
const ahora = new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/Lima', dateStyle: 'short', timeStyle: 'short' }).format(new Date());
const manifiesto = { etiqueta, web: WEB, capturado_lima: ahora, viewport: `${VISTA.ancho}x${VISTA.alto}`, tema: 'light', pantallas, oraculos: await oraculosJuego() };
writeFileSync(join(SALIDA, 'manifiesto.json'), JSON.stringify(manifiesto, null, 1));
// La copia versionada: el manifiesto y, por vista, los textos y controles con su zona (sin coordenadas)
for (const p of manifiesto.pantallas) {
  const vistas = JSON.parse(readFileSync(join(SALIDA, p.pantalla, 'textos.json'), 'utf8'));
  p.vistas = vistas.map((v) => ({
    archivo: v.archivo,
    y: v.y,
    textos: v.textos.map(({ t, zona }) => ({ t, zona })),
    controles: v.controles,
  }));
}
mkdirSync(RESULTADOS, { recursive: true });
writeFileSync(join(RESULTADOS, 'pantallas.json'), JSON.stringify(manifiesto, null, 1));
console.log(`Listo: ${SALIDA} y ${RESULTADOS}/pantallas.json`);
