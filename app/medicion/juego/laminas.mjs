// Playtest sintético, paso 4: las capturas de los documentos, con los tropiezos señalados y numerados.
//
//   TPF_WEB=http://localhost:8190 TPF_API=http://localhost:8130 node app/medicion/juego/laminas.mjs punta
//
// Lee marcas.json ({ pantalla: [{ n, texto | selector, vista }] }) y deja docs/auditoria/juego/<etiqueta>-<pantalla>.jpg:
// la ventana de esa vista con un recuadro rojo y su número sobre cada elemento señalado.
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { abrirNavegador, nuevaPagina, vigilarRed } from '../comun.mjs';
import { PANTALLAS } from './pantallas.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const etiqueta = process.argv[2];
if (!etiqueta) {
  console.error('Uso: node laminas.mjs <etiqueta>');
  process.exit(1);
}
const DESTINO = join(AQUI, '..', '..', '..', 'docs', 'auditoria', 'juego');
const VISTA = { alto: 768, solape: 100 };
const marcas = JSON.parse(readFileSync(join(AQUI, 'marcas.json'), 'utf8'));
mkdirSync(DESTINO, { recursive: true });

const navegador = await abrirNavegador();
for (const [nombre, lista] of Object.entries(marcas)) {
  const def = PANTALLAS[nombre];
  const { contexto, pagina } = await nuevaPagina(navegador, 'escritorio', 'light');
  const quieto = vigilarRed(pagina);
  await pagina.goto(def.url());
  await pagina.locator(def.listo).first().waitFor({ timeout: 30000 });
  if (def.esperar) await pagina.waitForFunction(def.esperar, null, { timeout: 30000 });
  await quieto(600);
  if (def.accion) {
    await def.accion(pagina);
    await quieto(600);
  }
  await pagina.waitForTimeout(700);
  if (def.desde === 'arriba') await pagina.evaluate(() => window.scrollTo(0, 0));
  const vista = Math.max(...lista.map((m) => m.vista || 1));
  if (vista > 1) await pagina.evaluate((dy) => window.scrollBy(0, dy), (vista - 1) * (VISTA.alto - VISTA.solape));
  await pagina.waitForTimeout(250);
  const faltan = await pagina.evaluate((ms) => {
    const perdidas = [];
    const buscar = (m) => {
      if (m.selector) return document.querySelector(m.selector);
      let mejor = null;
      for (const el of document.querySelectorAll('body *')) {
        if (!el.textContent.includes(m.texto) || el.closest('[hidden]')) continue;
        const r = el.getBoundingClientRect();
        if (!r.width || !r.height || r.bottom < 0 || r.top > innerHeight) continue;
        if (!mejor || el.textContent.length < mejor.textContent.length) mejor = el;
      }
      return mejor;
    };
    for (const m of ms) {
      const el = buscar(m);
      if (!el) { perdidas.push(m.n); continue; }
      const r = el.getBoundingClientRect();
      const caja = document.createElement('div');
      caja.style.cssText = `position:fixed;left:${r.left - 4}px;top:${r.top - 4}px;width:${r.width + 8}px;`
        + `height:${r.height + 8}px;border:3px solid #d1242f;border-radius:8px;z-index:99999;pointer-events:none`;
      const num = document.createElement('div');
      num.textContent = m.n;
      num.style.cssText = `position:fixed;left:${Math.max(2, r.left - 16)}px;top:${Math.max(2, r.top - 16)}px;`
        + 'width:26px;height:26px;border-radius:13px;background:#d1242f;color:#fff;font:700 15px/26px sans-serif;'
        + 'text-align:center;z-index:100000;pointer-events:none';
      document.body.append(caja, num);
    }
    return perdidas;
  }, lista);
  const archivo = join(DESTINO, `${etiqueta}-${nombre}.jpg`);
  await pagina.screenshot({ path: archivo, type: 'jpeg', quality: 78 });
  console.log(`${archivo}${faltan.length ? ` (sin ubicar: ${faltan.join(', ')})` : ''}`);
  await contexto.close();
}
await navegador.close();
