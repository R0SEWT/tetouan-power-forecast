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

const LISTA = [
  ['inicio', 'movil', 'dark'],
  ['area', 'movil', 'dark'],
  ['area', 'escritorio', 'dark'],
  ['area', 'escritorio', 'light'],
  ['operacion', 'movil', 'dark'],
  ['escenarios', 'escritorio', 'dark'],
  ['diagnostico', 'escritorio', 'dark'],
];

const navegador = await abrirNavegador();
for (const [estado, vista, tema] of LISTA) {
  const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, estado, vista, tema);
  const nombre = `${etiqueta}-${estado}-${vista}${tema === 'light' ? '-claro' : ''}.jpg`;
  await pagina.screenshot({ path: new URL(nombre, destino).pathname, type: 'jpeg', quality: 72 });
  console.log(nombre);
  await contexto.close();
}
await navegador.close();
