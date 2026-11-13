// Tabla antes/después en Markdown a partir de resultados/<etiqueta>.json.
//   node tabla.mjs base it1 it2
import { readFileSync } from 'node:fs';

const etiquetas = process.argv.slice(2).length ? process.argv.slice(2) : ['base', 'it1', 'it2'];
const R = etiquetas.map((e) => JSON.parse(readFileSync(new URL(`./resultados/${e}.json`, import.meta.url))));

const t = (r, k, v) => r.tareas[k][v];
const sino = (b) => (b ? 'sí' : 'no');
const par = (a, b) => `${a} / ${b}`;
const minCvd = (r, tema) => Math.min(...['protan', 'deutan', 'tritan'].map((k) => r.color[tema].deltaE_min_entre_series[k]));
const minContraste = (r) => Math.min(...['dark', 'light'].flatMap((tm) => Object.values(r.color[tm].contraste_series)));
const klmTotal = (r, v) => Object.keys(r.tareas).reduce((s, k) => s + t(r, k, v).segundos_klm, 0).toFixed(1);

// [grupo, métrica, valor(r), objetivo (texto), cumple(valor del último, valor de la base)]
const FILAS = [
  ['Tareas', 'T1 pronóstico con rango y real: cifras vistas (escritorio / móvil)', (r) => par(`${t(r, 't1', 'escritorio').vistos}/${t(r, 't1', 'escritorio').total}`, `${t(r, 't1', 'movil').vistos}/${t(r, 't1', 'movil').total}`), '4/4', (r) => t(r, 't1', 'escritorio').cumplida && t(r, 't1', 'movil').cumplida],
  ['Tareas', 'T1 acciones (escritorio / móvil)', (r) => par(t(r, 't1', 'escritorio').acciones, t(r, 't1', 'movil').acciones), '≤ base', (r, b) => t(r, 't1', 'movil').acciones <= t(b, 't1', 'movil').acciones],
  ['Tareas', 'T2 ¿se puede confiar?: acciones (escritorio / móvil)', (r) => par(t(r, 't2', 'escritorio').acciones, t(r, 't2', 'movil').acciones), '≤ base', (r, b) => t(r, 't2', 'movil').acciones <= t(b, 't2', 'movil').acciones && t(r, 't2', 'escritorio').cumplida],
  ['Tareas', 'T3 efecto de +2 °C: acciones (escritorio / móvil)', (r) => par(t(r, 't3', 'escritorio').acciones, t(r, 't3', 'movil').acciones), '≤ base', (r, b) => t(r, 't3', 'movil').acciones <= t(b, 't3', 'movil').acciones && t(r, 't3', 'escritorio').acciones <= t(b, 't3', 'escritorio').acciones],
  ['Tareas', 'T4 diagnóstico: acciones (escritorio / móvil)', (r) => par(t(r, 't4', 'escritorio').acciones, t(r, 't4', 'movil').acciones), '≤ base', (r, b) => t(r, 't4', 'movil').acciones <= t(b, 't4', 'movil').acciones && t(r, 't4', 'escritorio').acciones <= t(b, 't4', 'escritorio').acciones],
  ['Tareas', 'Tiempo estimado (KLM) de las 4 tareas, s (escritorio / móvil)', (r) => par(klmTotal(r, 'escritorio'), klmTotal(r, 'movil')), '≤ base', (r, b) => Number(klmTotal(r, 'movil')) <= Number(klmTotal(b, 'movil'))],
  ['Jerarquía', 'Número pronosticado visible sin desplazarse (móvil / escritorio)', (r) => par(sino(r.estructura.movil.respuesta_sin_desplazar), sino(r.estructura.escritorio.respuesta_sin_desplazar)), 'sí / sí', (r) => r.estructura.movil.respuesta_sin_desplazar && r.estructura.escritorio.respuesta_sin_desplazar],
  ['Jerarquía', 'Tamaño del número pronosticado, px (móvil / escritorio)', (r) => par(r.estructura.movil.tamano_fuente_respuesta_px, r.estructura.escritorio.tamano_fuente_respuesta_px), '≥ 32 / 40', (r) => r.estructura.movil.tamano_fuente_respuesta_px >= 32],
  ['Jerarquía', 'Ventana ocupada por barras fijas, % (móvil / escritorio)', (r) => par(r.estructura.movil.cromo_fijo_pct, r.estructura.escritorio.cromo_fijo_pct), '≤ 10', (r) => r.estructura.movil.cromo_fijo_pct <= 10 && r.estructura.escritorio.cromo_fijo_pct <= 10],
  ['Accesibilidad', 'axe-core WCAG 2.2 AA: infracciones (nodos) en 28 pantallas', (r) => `${r.axe.infracciones} (${r.axe.nodos})`, '0', (r) => r.axe.nodos === 0],
  ['Accesibilidad', 'Lighthouse accesibilidad (área, móvil / escritorio)', (r) => par(r.lighthouse.area_movil.accesibilidad, r.lighthouse.area_escritorio.accesibilidad), '100', (r) => r.lighthouse.area_movil.accesibilidad === 100],
  ['Accesibilidad', 'Objetivos táctiles de menos de 44 px (móvil)', (r) => `${r.estructura.movil.menores_44px} de ${r.estructura.movil.interactivos}`, '0', (r) => r.estructura.movil.menores_44px === 0],
  ['Accesibilidad', 'Tabulaciones hasta el selector de horizonte / hasta «Diagnóstico»', (r) => par(r.foco.escritorio.tabs_hasta_horizonte, r.foco.escritorio.tabs_hasta_diagnostico), '< base', (r, b) => r.foco.escritorio.tabs_hasta_horizonte < b.foco.escritorio.tabs_hasta_horizonte],
  ['Accesibilidad', 'Elementos con foco sin indicador visible / tapados', (r) => par(r.foco.escritorio.sin_indicador, r.foco.escritorio.tapados), '0 / 0', (r) => r.foco.escritorio.sin_indicador === 0 && r.foco.escritorio.tapados === 0],
  ['Color', 'Contraste mínimo de las series contra el fondo (WCAG 1.4.11)', (r) => `${minContraste(r).toFixed(2)}:1`, '≥ 3:1', (r) => minContraste(r) >= 3],
  ['Color', 'ΔE mínimo entre series con daltonismo simulado (oscuro / claro)', (r) => par(minCvd(r, 'dark'), minCvd(r, 'light')), '≥ 20', (r) => minCvd(r, 'dark') >= 20 && minCvd(r, 'light') >= 20],
  ['Rendimiento', 'Peso de la vista del área, KB / peticiones', (r) => par(r.rendimiento.kb, r.rendimiento.peticiones), '≤ base', (r, b) => r.rendimiento.kb <= b.rendimiento.kb],
  ['Rendimiento', 'Peticiones a terceros', (r) => r.rendimiento.peticiones_a_terceros, '0', (r) => r.rendimiento.peticiones_a_terceros === 0],
  ['Rendimiento', 'Hasta ver el número, ms: red local / red lenta y CPU ×4 (mediana de 5)', (r) => par(r.rendimiento.local.respuesta_ms, r.rendimiento.red_lenta.respuesta_ms), '≤ base', (r, b) => r.rendimiento.red_lenta.respuesta_ms <= b.rendimiento.red_lenta.respuesta_ms],
  ['Rendimiento', 'Lighthouse rendimiento (área, móvil / escritorio)', (r) => par(r.lighthouse.area_movil.rendimiento, r.lighthouse.area_escritorio.rendimiento), '≥ base', (r, b) => r.lighthouse.area_movil.rendimiento >= b.lighthouse.area_movil.rendimiento && r.lighthouse.area_escritorio.rendimiento >= b.lighthouse.area_escritorio.rendimiento],
  ['Rendimiento', 'LCP móvil, ms / CLS escritorio (Lighthouse, área)', (r) => par(r.lighthouse.area_movil.lcp_ms, r.lighthouse.area_escritorio.cls), 'CLS ≤ 0.1', (r) => r.lighthouse.area_escritorio.cls <= 0.1],
  ['Rendimiento', 'Lighthouse buenas prácticas (área, móvil)', (r) => r.lighthouse.area_movil.buenas_practicas, '100', (r) => r.lighthouse.area_movil.buenas_practicas === 100],
  ['Honestidad', 'Menciones visibles a la Programación Diaria del COES', (r) => r.afirmaciones.programacion_diaria_visible, '0', (r) => r.afirmaciones.programacion_diaria_visible === 0],
];

const titulo = (e) => {
  const n = e.split('/').pop();
  if (n.startsWith('base')) return 'Base';
  const m = /^it(\d+)/.exec(n);
  return m ? `It. ${m[1]}` : n;
};
const cab = ['', 'Métrica', ...etiquetas.map(titulo), 'Objetivo', 'Cumple'];
console.log(`| ${cab.join(' | ')} |`);
console.log(`|${cab.map(() => '---').join('|')}|`);
let grupo = '';
for (const [g, nombre, valor, objetivo, cumple] of FILAS) {
  const ultimo = R[R.length - 1];
  let ok;
  try { ok = cumple(ultimo, R[0]) ? 'sí' : '**no**'; } catch { ok = '—'; }
  const vals = R.map((r) => { try { return String(valor(r)); } catch { return '—'; } });
  console.log(`| ${g === grupo ? '' : g} | ${nombre} | ${vals.join(' | ')} | ${objetivo} | ${ok} |`);
  grupo = g;
}
