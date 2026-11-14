// Las pantallas del playtest sintético: la URL, cuándo está lista, qué AOI de atencion/pantallas.mjs usa para nombrar
// las zonas, cuántas ventanas se capturan y, si hace falta, la acción que la deja en su estado (p. ej. +2 °C).
import { WEB } from '../comun.mjs';

const CASO = 'centro?fecha=2026-03-10';
const DETALLE = `${WEB}/#/area/${CASO}&hora=19:00&horizonte=24h&variante=M3`;
export const LISTO_AHORA = ':is(#ahRespuesta .r-ahora, #ahCifras .kpi)';
const esperarConfianza = () => !/Calculando/.test(document.querySelector('#cfTitular')?.textContent || 'Calculando')
  && !document.querySelector('#cfMes .cargando-bloque');
const esperarDetalle = () => /\d/.test(document.querySelector('#respValor')?.textContent || '');

// Las pantallas del playtest. `vistas`: cuántas ventanas se capturan como máximo; `desde`: 'arriba' (la página al
// abrir) o 'actual' (donde la deja la app, p. ej. tras saltar a una sección).
export const PANTALLAS = {
  hoy: { url: () => `${WEB}/`, listo: LISTO_AHORA, aoi: 'inicio', vistas: 3, desde: 'arriba' },
  'repaso-1030': { url: () => `${WEB}/#/ahora/${CASO}&hora=10:30`, listo: LISTO_AHORA, aoi: 'ahora', vistas: 3, desde: 'arriba' },
  'repaso-1900': { url: () => `${WEB}/#/ahora/${CASO}&hora=19:00`, listo: LISTO_AHORA, aoi: 'ahora', vistas: 3, desde: 'arriba' },
  confianza: { url: () => `${WEB}/#/confianza/centro`, listo: '#cfStats .stat', esperar: esperarConfianza, aoi: 'confianza', vistas: 3, desde: 'arriba' },
  escenarios: { url: () => `${DETALLE}&seccion=escenarios`, listo: '#respValor', esperar: esperarDetalle, aoi: 'detalle', vistas: 2, desde: 'actual' },
  'escenario-2c': {
    url: () => `${DETALLE}&seccion=escenarios`,
    listo: '#respValor',
    esperar: esperarDetalle,
    aoi: 'detalle',
    vistas: 2,
    desde: 'actual',
    accion: async (p) => {
      const b = p.getByRole('button', { name: '+2 °C' }).first();
      await b.scrollIntoViewIfNeeded();
      await b.click();
    },
  },
};
