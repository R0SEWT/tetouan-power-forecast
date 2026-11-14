// Capturas para el documento de diseño: docs/img/app-hcd/<etiqueta>-<estado>-<vista>.jpg
//   node capturas.mjs --version base --etiqueta base
import { mkdirSync } from 'node:fs';
import { abrirNavegador } from './comun.mjs';
import { abrirEstado } from './accesibilidad.mjs';

const args = process.argv.slice(2);
const opcion = (nombre, defecto) => { const i = args.indexOf(`--${nombre}`); return i >= 0 ? args[i + 1] : defecto; };
const nombreVersion = opcion('version', 'base');
const etiqueta = opcion('etiqueta', nombreVersion);
const destino = new URL('../../docs/img/app-hcd/', import.meta.url);
mkdirSync(destino, { recursive: true });

const LISTAS = {
  it8: [
    ['inicio', 'escritorio', 'light'],
    ['inicio', 'movil', 'light'],
    ['area', 'escritorio', 'light'],
    ['area', 'escritorio', 'dark'],
    ['area', 'movil', 'light'],
    ['area', 'movil', 'dark'],
    ['area', 'proyector', 'light'],
    ['despues', 'escritorio', 'light'],
    ['confianza', 'escritorio', 'light'],
    ['confianza', 'escritorio', 'dark'],
    ['confianza', 'movil', 'light'],
    ['detalle', 'escritorio', 'light'],
    ['sin_api', 'movil', 'light'],
  ],
};
const LISTA_BASE = [
  ['inicio', 'movil', 'dark'],
  ['area', 'movil', 'dark'],
  ['area', 'escritorio', 'dark'],
  ['area', 'escritorio', 'light'],
  ['operacion', 'movil', 'dark'],
  ['escenarios', 'escritorio', 'dark'],
  ['diagnostico', 'escritorio', 'dark'],
];

const LISTA = LISTAS[nombreVersion] || LISTA_BASE;
const completa = args.includes('--completa');
const navegador = await abrirNavegador();
for (const [estado, vista, tema] of LISTA) {
  const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, estado, vista === 'proyector' ? 'escritorio' : vista, tema);
  if (vista === 'escritorio' && nombreVersion === 'it8') { await pagina.setViewportSize({ width: 1440, height: 900 }); await pagina.waitForTimeout(500); }
  const nombre = `${etiqueta}-${estado}-${vista}${tema === 'light' ? '-claro' : ''}.jpg`;
  await pagina.screenshot({ path: new URL(nombre, destino).pathname, type: 'jpeg', quality: 72, fullPage: completa });
  console.log(nombre);
  await contexto.close();
}
await navegador.close();
