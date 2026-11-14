// Cómo llega cada versión de la interfaz a cada estado y cómo recorre cada tarea.
// Las métricas y los oráculos son los mismos para todas; solo cambia el camino.
// Una ruta es una lista de pasos; cada paso cuenta como acciones del usuario:
//   { clic: (p) => locator }                 1 clic (o toque)
//   { escribir: (p) => locator, texto }      M + H + n pulsaciones
//   { teclas: (p) => locator, tecla, veces } n pulsaciones (con el foco ya puesto por el paso anterior)
//   { revisar: true }                        mira la pantalla (acumula lo visto), sin costo

import { WEB } from './comun.mjs';

const tabBase = (nombre) => (p) => p.locator(`.sheet-tab[data-tab=${nombre}]`);

export const VERSIONES = {
  base: {
    estados: {
      inicio: async () => {},
      area: async () => {},
      operacion: async (p) => { await tabBase('operacion')(p).click(); },
      escenarios: async (p) => { await tabBase('escenarios')(p).click(); },
      sensibilidad: async (p) => {
        await p.getByRole('button', { name: '1 hora' }).click();
        await tabBase('escenarios')(p).click();
      },
      diagnostico: async (p) => { await tabBase('diagnostico')(p).click(); },
      ficha: async (p) => { await p.locator('#btnFicha').click(); },
    },
    tareas: {
      // Desde el inicio: Centro, 10 de marzo de 2026, 19:00, a 24 h.
      t1: [
        { clic: (p) => p.getByRole('link', { name: /Centro/ }) },
        { escribir: (p) => p.locator('#inFecha'), texto: '2026-03-10' },
        { clic: (p) => p.getByRole('button', { name: /Noche/ }) },
        { clic: (p) => p.locator('#inHora'), foco: true },
        { teclas: (p) => p.locator('#inHora'), tecla: 'ArrowLeft', veces: 2 },
        { clic: (p) => p.getByRole('button', { name: '24 horas' }) },
        { revisar: true },
        { clic: tabBase('operacion') },
      ],
      t2: [{ revisar: true }],
      t3: [
        { clic: tabBase('escenarios') },
        { clic: (p) => p.getByRole('button', { name: '+2 °C' }) },
      ],
      t4: [{ clic: tabBase('diagnostico') }],
    },
  },
};

// Iteración 1: las pestañas de detalle están en la página y la respuesta trae el rango.
const tab = (nombre) => (p) => p.getByRole('tab', { name: nombre });
VERSIONES.it1 = {
  estados: {
    inicio: async () => {},
    area: async () => {},
    operacion: async (p) => { await tab('Próximas horas')(p).click(); },
    escenarios: async (p) => { await tab('¿Y si…?')(p).click(); },
    sensibilidad: async (p) => {
      await p.getByRole('button', { name: '1 hora' }).click();
      await tab('¿Y si…?')(p).click();
    },
    diagnostico: async (p) => { await tab('Diagnóstico')(p).click(); },
    ficha: async (p) => { await p.locator('#btnFicha').click(); },
  },
  tareas: {
    t1: VERSIONES.base.tareas.t1.slice(0, -1), // igual, sin abrir la hoja: el rango ya está junto al número
    t2: [{ revisar: true }],
    t3: [
      { clic: tab('¿Y si…?') },
      { clic: (p) => p.getByRole('button', { name: '+2 °C' }) },
    ],
    t4: [{ clic: tab('Diagnóstico') }],
  },
};

// Iteración 2: una barra de secciones pegajosa lleva a «¿Y si…?» y «Diagnóstico» con un toque.
const seccion = (nombre) => (p) => p.getByRole('navigation', { name: 'Secciones de esta área' }).getByRole('button', { name: nombre });
VERSIONES.it2 = {
  estados: {
    ...VERSIONES.it1.estados,
    escenarios: async (p) => { await seccion('¿Y si…?')(p).click(); },
    sensibilidad: async (p) => {
      await p.getByRole('button', { name: '1 hora' }).click();
      await seccion('¿Y si…?')(p).click();
    },
    diagnostico: async (p) => { await seccion('Diagnóstico')(p).click(); },
  },
  tareas: {
    t1: VERSIONES.it1.tareas.t1,
    t2: [{ revisar: true }],
    t3: [
      { clic: seccion('¿Y si…?') },
      { clic: (p) => p.getByRole('button', { name: '+2 °C' }) },
    ],
    t4: [{ clic: seccion('Diagnóstico') }],
  },
};

// Iteración 4: el combinado por defecto, la ficha del número, el pico y el seguimiento mes a mes. Las tareas
// siguen los mismos caminos que en la iteración 2 (el pico va en su propio panel y la ficha, plegada).
VERSIONES.it4 = VERSIONES.it2;

// Iteración 7: la sección «En vivo» (GET /en-vivo/{area}) al final de la vista del área, con su botón en la barra de
// secciones. Los demás estados y las tareas no cambian; se agrega el estado con la sección a la vista.
VERSIONES.it7 = {
  estados: {
    ...VERSIONES.it2.estados,
    envivo: async (p) => {
      await seccion('En vivo')(p).click();
      await p.locator('#envivo[aria-busy="false"]').waitFor();
    },
  },
  tareas: VERSIONES.it2.tareas,
};

// Iteración 8: «Ahora» y «Confianza» son las pantallas de entrada. El caso se abre en «Ahora», en repaso (el
// 10 de marzo de 2026 a las 19:00); el detalle anterior queda en «Detalle». Cada versión puede decir desde qué enlace
// arranca cada estado (`url`) y cada tarea (`inicio`); si no lo dice, se usan los de siempre (comun.mjs).
const URL_AHORA = `${WEB}/#/ahora/centro?fecha=2026-03-10&hora=19:00`;
const URL_DETALLE = `${WEB}/#/area/centro?fecha=2026-03-10&hora=19:00&horizonte=24h&variante=M3`;
const navegar = (nombre) => (p) => p.getByRole('navigation', { name: 'Pantallas' }).getByRole('link', { name: nombre });
// Desde el PR 14 «Confianza» baja al abrirla: su titular no existe hasta que llega
const confianzaLista = async (p) => p.waitForFunction(() => {
  const t = document.querySelector('#cfTitular');
  return Boolean(t) && !/Calculando/.test(t.textContent);
});
VERSIONES.it8 = {
  url: (estado) => ({
    inicio: `${WEB}/`,
    area: URL_AHORA,
    despues: URL_AHORA,
    confianza: URL_AHORA,
    confianza_1h: URL_AHORA,
    sin_api: URL_AHORA,
    detalle: URL_DETALLE,
    escenarios: URL_DETALLE,
    diagnostico: URL_DETALLE,
    ficha: URL_AHORA,
  })[estado],
  inicio: (tarea) => (tarea === 't1' ? `${WEB}/` : URL_AHORA),
  // Recorrido de foco: en «Ahora» no hay selector de horizonte; los controles clave son el día y «Confianza»
  foco: { horizonte: /ahFecha/, diagnostico: /Confianza/ },
  estados: {
    inicio: async () => {},
    area: async () => {},
    despues: async (p) => { await p.getByLabel('Mostrar lo que pasó después').check(); },
    confianza: async (p) => { await navegar('Confianza')(p).click(); await confianzaLista(p); },
    confianza_1h: async (p) => {
      await navegar('Confianza')(p).click();
      await confianzaLista(p);
      await p.getByRole('button', { name: 'A 1 hora' }).click();
      await confianzaLista(p);
    },
    sin_api: async (p) => {
      await p.route(/:8000\//, (r) => r.abort());
      await p.reload();
      await p.waitForTimeout(800);
    },
    detalle: async () => {},
    escenarios: async (p) => { await seccion('¿Y si…?')(p).click(); },
    diagnostico: async (p) => { await seccion('Diagnóstico')(p).click(); },
    ficha: async (p) => { await p.getByRole('button', { name: 'Ficha técnica: modelo y datos' }).click(); },
  },
  tareas: {
    // Desde la entrada («Ahora», en vivo): escribir el día y la hora. Lo que se dijo, su rango y lo real quedan a la vista.
    t1: [
      { escribir: (p) => p.locator('#ahFecha'), texto: '2026-03-10' },
      { escribir: (p) => p.locator('#ahHora'), texto: '19:00' },
      { revisar: true },
    ],
    // El error del día completo se ve al pedir lo que pasó después: la pantalla no muestra el futuro sin pedirlo.
    t2: [{ clic: (p) => p.getByLabel('Mostrar lo que pasó después') }],
    t3: [
      { clic: (p) => p.getByRole('link', { name: '¿Y si hace más calor?' }) },
      { clic: (p) => p.getByRole('button', { name: '+2 °C' }) },
    ],
    t4: [{ clic: navegar('Confianza') }],
  },
};

// PR 5: tocar el gráfico de «Ahora» fija la hora. La posición de una hora sale de la escala del propio gráfico.
const enElGrafico = (hora) => async (p) => p.evaluate((h) => {
  const el = document.querySelector('#ahLienzo');
  const g = el._g;
  const dia = g.d.origen.slice(0, 10);
  const i = g.d.fecha_hora.findIndex((f) => f === `${dia}T${h}`);
  return { x: g.x(i), y: g.m.t + 40 };
}, hora);
const tocarHora = (hora) => ({ clic: (p) => p.locator('#ahLienzo'), posicion: enElGrafico(hora) });
const URL_AHORA_1030 = `${WEB}/#/ahora/centro?fecha=2026-03-10&hora=10:30`;
VERSIONES.pr05 = {
  ...VERSIONES.it8,
  // T1 completa: el día se escribe (es el PR 6) y la hora se toca en el gráfico
  tareas: {
    ...VERSIONES.it8.tareas,
    t1: [
      { escribir: (p) => p.locator('#ahFecha'), texto: '2026-03-10' },
      tocarHora('19:00'),
      { revisar: true },
    ],
  },
};
// T1 en el mismo día: el caso abierto a las 10:30 y la tarea pide las 19:00 (lo que mide el PR 5)
VERSIONES['it8-hora'] = {
  ...VERSIONES.it8,
  inicio: (tarea) => (tarea === 't1' ? URL_AHORA_1030 : VERSIONES.it8.inicio(tarea)),
  tareas: { ...VERSIONES.it8.tareas, t1: [{ escribir: (p) => p.locator('#ahHora'), texto: '19:00' }, { revisar: true }] },
};
VERSIONES['pr05-hora'] = {
  ...VERSIONES.pr05,
  inicio: VERSIONES['it8-hora'].inicio,
  tareas: { ...VERSIONES.pr05.tareas, t1: [tocarHora('19:00'), { revisar: true }] },
};

// PR 6: el día se escribe como se dice en el campo propio (10/03: sin año, el último que pasó); la hora, en el gráfico
VERSIONES.pr06 = {
  ...VERSIONES.pr05,
  tareas: {
    ...VERSIONES.pr05.tareas,
    t1: [{ escribir: (p) => p.locator('#ahFecha'), texto: '1003' }, tocarHora('19:00'), { revisar: true }],
  },
};
// …y con todo escrito (día y hora) en los campos propios, sin tocar el gráfico
VERSIONES['pr06-campos'] = {
  ...VERSIONES.pr05,
  tareas: {
    ...VERSIONES.pr05.tareas,
    t1: [
      { escribir: (p) => p.locator('#ahFecha'), texto: '1003' },
      { escribir: (p) => p.locator('#ahHora'), texto: '19' },
      { revisar: true },
    ],
  },
};

export function version(nombre) {
  const v = VERSIONES[nombre];
  if (!v) throw new Error(`Versión desconocida: ${nombre}. Hay: ${Object.keys(VERSIONES).join(', ')}`);
  return v;
}
