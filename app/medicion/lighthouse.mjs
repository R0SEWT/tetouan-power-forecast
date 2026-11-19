// Lighthouse (rendimiento, accesibilidad, buenas prácticas) en móvil y escritorio, mediana de n corridas.
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import { mediana, URL_AREA, WEB } from './comun.mjs';

const CATEGORIAS = ['performance', 'accessibility', 'best-practices'];

async function correr(url, factor) {
  const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless=new', '--no-sandbox'] });
  try {
    const config = factor === 'escritorio'
      ? { extends: 'lighthouse:default', settings: { formFactor: 'desktop', screenEmulation: { mobile: false, width: 1350, height: 940, deviceScaleFactor: 1, disabled: false }, throttling: { rttMs: 40, throughputKbps: 10240, cpuSlowdownMultiplier: 1 }, onlyCategories: CATEGORIAS } }
      : { extends: 'lighthouse:default', settings: { onlyCategories: CATEGORIAS } };
    const r = await lighthouse(url, { port: chrome.port, output: 'json', logLevel: 'error' }, config);
    const lhr = r.lhr;
    const a = lhr.audits;
    return {
      rendimiento: Math.round(100 * lhr.categories.performance.score),
      accesibilidad: Math.round(100 * lhr.categories.accessibility.score),
      buenas_practicas: Math.round(100 * lhr.categories['best-practices'].score),
      fcp_ms: Math.round(a['first-contentful-paint'].numericValue),
      lcp_ms: Math.round(a['largest-contentful-paint'].numericValue),
      tbt_ms: Math.round(a['total-blocking-time'].numericValue),
      cls: Number(a['cumulative-layout-shift'].numericValue.toFixed(3)),
      kb: Math.round(a['total-byte-weight'].numericValue / 1024),
      fallas_accesibilidad: lhr.categories.accessibility.auditRefs
        .filter((ref) => ref.weight > 0 && a[ref.id].score !== null && a[ref.id].score < 1).map((ref) => ref.id),
      fallas_buenas_practicas: lhr.categories['best-practices'].auditRefs
        .filter((ref) => ref.weight > 0 && a[ref.id].score !== null && a[ref.id].score < 1).map((ref) => ref.id),
    };
  } finally {
    await chrome.kill();
  }
}

export async function medirLighthouse(repeticiones = 3) {
  const salida = {};
  for (const [pagina, url] of [['inicio', `${WEB}/`], ['area', URL_AREA]]) {
    for (const factor of ['movil', 'escritorio']) {
      const corridas = [];
      for (let i = 0; i < repeticiones; i += 1) corridas.push(await correr(url, factor));
      const med = {};
      for (const k of ['rendimiento', 'accesibilidad', 'buenas_practicas', 'fcp_ms', 'lcp_ms', 'tbt_ms', 'cls', 'kb']) med[k] = mediana(corridas.map((c) => c[k]));
      med.rendimiento_rango = [Math.min(...corridas.map((c) => c.rendimiento)), Math.max(...corridas.map((c) => c.rendimiento))];
      med.fallas_accesibilidad = corridas[0].fallas_accesibilidad;
      med.fallas_buenas_practicas = corridas[0].fallas_buenas_practicas;
      salida[`${pagina}_${factor}`] = med;
    }
  }
  return salida;
}
