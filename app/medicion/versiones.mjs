// Cómo llega cada versión de la interfaz a cada estado y cómo recorre cada tarea.
// Las métricas y los oráculos son los mismos para todas; solo cambia el camino.
// Una ruta es una lista de pasos; cada paso cuenta como acciones del usuario:
//   { clic: (p) => locator }                 1 clic (o toque)
//   { escribir: (p) => locator, texto }      M + H + n pulsaciones
//   { teclas: (p) => locator, tecla, veces } n pulsaciones (con el foco ya puesto por el paso anterior)
//   { revisar: true }                        mira la pantalla (acumula lo visto), sin costo

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

export function version(nombre) {
  const v = VERSIONES[nombre];
  if (!v) throw new Error(`Versión desconocida: ${nombre}. Hay: ${Object.keys(VERSIONES).join(', ')}`);
  return v;
}
