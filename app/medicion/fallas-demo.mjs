// Fallas que encontró el ensayo de la demo (PR #57): que no vuelvan.
//
//   node fallas-demo.mjs        # con la app levantada (TPF_WEB y TPF_API si no son :8080 y :8000)
//
// 1. Tras tocar, arrastrar o recorrer con el teclado el gráfico de «Ahora», un solo clic en «¿Y si hace más calor?»
//    tiene que abrir los escenarios (antes el blur del gráfico rehacía la respuesta y el clic se perdía).
// 2. «Confianza» a 1 h: el pico, El Niño y el registro en vivo, que solo se miden a 24 h, lo dicen.
// 3. «Confianza» no dice que 2026 se usó para elegir el modelo: quedó fuera del entrenamiento y de la elección, pero
//    ya se había revisado.
// Sale con 1 si algo falla.
import { abrirNavegador, nuevaPagina, WEB } from './comun.mjs';

const REPASO = `${WEB}/#/ahora/centro?fecha=2026-08-27&hora=19:00`; // el día de la demo
let fallas = 0;
const revisar = (ok, texto) => {
  if (!ok) fallas += 1;
  console.log(`  ${ok ? 'OK   ' : 'FALLA'}  ${texto}`);
};

const listo = (p, dia) => p.waitForFunction((d) => {
  const g = document.querySelector('#ahLienzo')?._g;
  return g && g.d.origen.startsWith(d) && document.querySelector('#ahRespuesta .r-ahora');
}, dia);
const puntoDe = (p, fh) => p.evaluate((f) => {
  const g = document.querySelector('#ahLienzo')._g;
  return { x: g.x(g.d.fecha_hora.indexOf(f)), y: g.m.t + 40 };
}, fh);
const enlaceCalor = (p) => p.locator('#ahRespuesta').getByRole('link', { name: '¿Y si hace más calor?', exact: true });

// Un solo clic en el enlace: ¿se abrieron los escenarios?
async function unClic(p) {
  await enlaceCalor(p).click();
  await p.waitForTimeout(800);
  return p.evaluate(() => location.hash.startsWith('#/area/')); // «Detalle» (la sección se quita del hash al llegar)
}

async function falla1(navegador) {
  console.log('1. Un clic después de usar el gráfico de «Ahora»');
  const casos = {
    'tocar el pico (el paso 2 de la demo)': async (p) => {
      await p.locator('#ahLienzo').click({ position: await puntoDe(p, '2026-08-28T15:00') });
      await listo(p, '2026-08-28');
    },
    'arrastrar y soltar lejos (arrepentirse)': async (p) => {
      const caja = await p.locator('#ahLienzo').boundingBox();
      const a = await puntoDe(p, '2026-08-28T09:00');
      const b = await puntoDe(p, '2026-08-28T15:00');
      await p.mouse.move(caja.x + a.x, caja.y + a.y);
      await p.mouse.down();
      await p.mouse.move(caja.x + b.x, caja.y + b.y, { steps: 8 });
      await p.mouse.move(caja.x + b.x, caja.y + caja.height + 200, { steps: 4 });
      await p.mouse.up();
    },
    'recorrer con las flechas, sin fijar': async (p) => {
      await p.locator('#ahLienzo').focus();
      await p.keyboard.press('ArrowRight');
      await p.keyboard.press('ArrowRight');
    },
  };
  for (const [nombre, accion] of Object.entries(casos)) {
    const { contexto, pagina } = await nuevaPagina(navegador, 'escritorio', 'light');
    await pagina.goto(REPASO);
    await listo(pagina, '2026-08-27');
    await accion(pagina);
    revisar(await unClic(pagina), `${nombre}: un clic en «¿Y si hace más calor?» abre los escenarios`);
    await contexto.close();
  }
  // Recorrer con las flechas cambia la cifra; salir del gráfico la deja como estaba
  const { contexto, pagina } = await nuevaPagina(navegador, 'escritorio', 'light');
  await pagina.goto(REPASO);
  await listo(pagina, '2026-08-27');
  const cifra = () => pagina.locator('#ahRespuesta .r-ahora .n').innerText();
  const antes = await cifra();
  await pagina.locator('#ahLienzo').focus();
  await pagina.keyboard.press('PageDown');
  const siguiendo = await cifra();
  await pagina.keyboard.press('Shift+Tab');
  const despues = await cifra();
  revisar(siguiendo !== antes && despues === antes, `las flechas cambian la cifra (${antes} → ${siguiendo}) y al salir vuelve (${despues})`);
  await contexto.close();
}

async function textoConfianza(navegador, horizonte) {
  const { contexto, pagina } = await nuevaPagina(navegador, 'escritorio', 'light');
  await pagina.goto(`${WEB}/#/confianza/centro?horizonte=${horizonte}`);
  await pagina.waitForFunction(() => {
    const t = document.querySelector('#cfTitular');
    return t && !/Calculando/.test(t.textContent) && document.querySelector('#cfStats .stat');
  });
  const t = await pagina.evaluate(() => Object.fromEntries(['#cfLead', '#cfStats', '#cfCobVista', '#cfCob', '#cfMundo']
    .map((s) => [s, document.querySelector(s).innerText.replace(/\s+/g, ' ')])));
  await contexto.close();
  return t;
}

async function falla2y3(navegador) {
  const h1 = await textoConfianza(navegador, '1h');
  const h24 = await textoConfianza(navegador, '24h');
  console.log('2. «Confianza» a 1 h dice qué cifras son de 24 h');
  revisar(/Hora del pico a 24 h/.test(h1['#cfStats']), 'el acierto de la hora del pico dice «a 24 h»');
  revisar(/Con El Niño, a 24 h/.test(h1['#cfStats']), 'el error con El Niño dice «a 24 h»');
  revisar(/En vivo, a 24 h/.test(h1['#cfLead']), 'el titular dice que el registro en vivo es a 24 h');
  revisar(/En vivo a 24 h/.test(h1['#cfCobVista']) && /En vivo a 24 h/.test(h1['#cfCob']), 'la cobertura en vivo dice «a 24 h»');
  revisar(/Hora del pico \(±1 h\)/.test(h24['#cfStats']) && !/a 24 h/.test(h24['#cfStats'] + h24['#cfCobVista']),
    'a 24 h no cambia nada');
  console.log('3. Qué papel tuvo 2026');
  const todo = [h1, h24].flatMap((t) => Object.values(t)).join(' ');
  revisar(!/se usó para elegir/.test(todo), 'no dice que 2026 se usó para elegir el modelo');
  revisar(/fuera del entrenamiento y de la elección del modelo/.test(h24['#cfLead']) && /ya lo habíamos revisado/.test(h24['#cfLead']),
    'dice que 2026 quedó fuera del entrenamiento y de la elección, pero ya revisado');
}

const navegador = await abrirNavegador();
try {
  await falla1(navegador);
  await falla2y3(navegador);
} finally {
  await navegador.close();
}
console.log(fallas ? `${fallas} comprobaciones fallaron` : 'Todo en orden');
process.exit(fallas ? 1 : 0);
