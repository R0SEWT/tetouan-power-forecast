// Mide la app y guarda el resultado en resultados/<etiqueta>.json.
//
//   node medir.mjs --version base --etiqueta base           # todo
//   node medir.mjs --version nueva --etiqueta it1 --rapido  # sin Lighthouse y con menos repeticiones
//
// Requiere la app levantada (ver app/levantar.sh): backend en TPF_API (:8000) y web en TPF_WEB (:8080).
import { mkdirSync, writeFileSync } from 'node:fs';
import { abrirNavegador, API, CASO, fmt0 } from './comun.mjs';
import { medirAfirmaciones, medirAxe, medirDesborde, medirEstructura, medirFoco } from './accesibilidad.mjs';
import { medirColor } from './color.mjs';
import { medirLighthouse } from './lighthouse.mjs';
import { medirRendimiento } from './rendimiento.mjs';
import { medirTareas, oraculos } from './tareas.mjs';

const args = process.argv.slice(2);
const opcion = (nombre, defecto) => { const i = args.indexOf(`--${nombre}`); return i >= 0 ? args[i + 1] : defecto; };
const nombreVersion = opcion('version', 'base');
const etiqueta = opcion('etiqueta', nombreVersion);
const rapido = args.includes('--rapido');
const solo = opcion('solo', null);
const quiere = (k) => !solo || solo.split(',').includes(k);

const salud = await (await fetch(`${API}/salud`)).json();
const o = await oraculos();
const fichaPronostico = o.t1.grupos.pronostico[0];
console.log(`Midiendo «${nombreVersion}» (${etiqueta}) con el modelo ${salud.modelo}; respuesta esperada ${fichaPronostico} MW`);

const r = { etiqueta, version: nombreVersion, fecha: new Date().toISOString(), modelo: salud.modelo, caso: CASO };
const navegador = await abrirNavegador();
try {
  if (quiere('tareas')) { console.log('· tareas'); r.tareas = await medirTareas(navegador, nombreVersion, rapido ? 1 : 3); }
  if (quiere('rendimiento')) { console.log('· rendimiento'); r.rendimiento = await medirRendimiento(navegador, fichaPronostico, rapido ? 3 : 5, nombreVersion); }
  if (quiere('axe')) { console.log('· axe'); r.axe = await medirAxe(navegador, nombreVersion); }
  if (quiere('foco')) {
    console.log('· foco');
    r.foco = { movil: await medirFoco(navegador, nombreVersion, 'movil'), escritorio: await medirFoco(navegador, nombreVersion, 'escritorio') };
  }
  if (quiere('estructura')) {
    console.log('· estructura');
    r.estructura = {
      movil: await medirEstructura(navegador, nombreVersion, 'movil', fichaPronostico),
      escritorio: await medirEstructura(navegador, nombreVersion, 'escritorio', fichaPronostico),
      desborde_px: await medirDesborde(navegador, nombreVersion),
    };
  }
  if (quiere('color')) { console.log('· color'); r.color = await medirColor(navegador, nombreVersion); }
  if (quiere('afirmaciones')) { console.log('· afirmaciones'); r.afirmaciones = await medirAfirmaciones(navegador, nombreVersion); }
} finally {
  await navegador.close();
}
if (!rapido && quiere('lighthouse')) { console.log('· lighthouse'); r.lighthouse = await medirLighthouse(3); }

mkdirSync(new URL('./resultados/', import.meta.url), { recursive: true });
const ruta = new URL(`./resultados/${etiqueta}.json`, import.meta.url);
writeFileSync(ruta, `${JSON.stringify(r, null, 2)}\n`);
console.log(`Guardado en ${ruta.pathname}`);

// Resumen corto en la consola
if (r.tareas) {
  for (const [k, t] of Object.entries(r.tareas)) {
    for (const v of ['escritorio', 'movil']) {
      const x = t[v];
      console.log(`${k} ${v.padEnd(10)} ${x.cumplida ? 'cumplida' : `faltan: ${x.faltan.join(', ')}`} · ${x.acciones} acciones (${x.clics} clics, ${x.desplazamientos} despl.) · KLM ${x.segundos_klm} s · robot ${x.segundos_robot} s`);
    }
  }
}
if (r.axe) console.log(`axe: ${r.axe.infracciones} infracciones, ${r.axe.nodos} nodos en ${r.axe.pantallas} pantallas`, Object.keys(r.axe.reglas));
if (r.rendimiento) console.log(`peso ${r.rendimiento.kb} KB, ${r.rendimiento.peticiones} peticiones (${r.rendimiento.peticiones_a_terceros} a terceros); respuesta ${r.rendimiento.local.respuesta_ms} ms local, ${r.rendimiento.red_lenta.respuesta_ms} ms red lenta`);
if (r.foco) console.log('foco', JSON.stringify(r.foco));
if (r.estructura) console.log('estructura', JSON.stringify(r.estructura));
if (r.color) console.log('color', JSON.stringify(r.color));
if (r.afirmaciones) console.log('afirmaciones', JSON.stringify(r.afirmaciones));
if (r.lighthouse) for (const [k, v] of Object.entries(r.lighthouse)) console.log(`LH ${k}: rend ${v.rendimiento} acc ${v.accesibilidad} bp ${v.buenas_practicas} LCP ${v.lcp_ms} ms ${v.kb} KB`, v.fallas_accesibilidad, v.fallas_buenas_practicas);
void fmt0;
