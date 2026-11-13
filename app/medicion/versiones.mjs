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

// La versión rediseñada usa nombres accesibles estables; se agrega aquí cuando existe.
export function version(nombre) {
  const v = VERSIONES[nombre];
  if (!v) throw new Error(`Versión desconocida: ${nombre}. Hay: ${Object.keys(VERSIONES).join(', ')}`);
  return v;
}
