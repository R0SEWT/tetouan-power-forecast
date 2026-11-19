// Color de los gráficos: contraste no textual de cada serie contra el fondo (WCAG 1.4.11, 3:1)
// y separación entre series con visión de color simulada (Machado, Oliveira y Fernandes, 2009).
import { abrirEstado } from './accesibilidad.mjs';

const MACHADO = {
  protan: [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
  deutan: [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
  tritan: [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
};

const lin = (c) => { const v = c / 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
const gam = (v) => { const c = v <= 0.0031308 ? 12.92 * v : 1.055 * v ** (1 / 2.4) - 0.055; return Math.round(255 * Math.min(1, Math.max(0, c))); };
const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
export const contraste = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

function simular(rgb, m) {
  const l = rgb.map(lin);
  return m.map((fila) => gam(fila[0] * l[0] + fila[1] * l[1] + fila[2] * l[2]));
}

function lab([r, g, b]) {
  const [R, G, B] = [r, g, b].map(lin);
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
  const X = (0.4124 * R + 0.3576 * G + 0.1805 * B) / 0.95047;
  const Y = 0.2126 * R + 0.7152 * G + 0.0722 * B;
  const Z = (0.0193 * R + 0.1192 * G + 0.9505 * B) / 1.08883;
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
}
const dE = (a, b) => { const [p, q] = [lab(a), lab(b)]; return Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]); };

const rgbDe = (txt) => (txt.match(/\d+(\.\d+)?/g) || []).slice(0, 3).map(Number);

export async function medirColor(navegador, nombreVersion) {
  const salida = {};
  for (const tema of ['dark', 'light']) {
    const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, 'area', 'escritorio', tema);
    const crudo = await pagina.evaluate(() => {
      const fondoDe = (el) => {
        let e = el;
        while (e) {
          const c = getComputedStyle(e).backgroundColor;
          if (c && !/rgba\(.*, 0\)|transparent/.test(c)) return c;
          e = e.parentElement;
        }
        return getComputedStyle(document.body).backgroundColor;
      };
      const series = {};
      for (const clase of ['ln-real', 'ln-pronostico', 'ln-referencia']) {
        const el = document.querySelector(`.chart svg path.${clase}`);
        if (el) series[clase] = { trazo: getComputedStyle(el).stroke, fondo: fondoDe(el.closest('.chart')) };
      }
      return series;
    });
    await contexto.close();
    const series = Object.fromEntries(Object.entries(crudo).map(([k, v]) => [k, { trazo: rgbDe(v.trazo), fondo: rgbDe(v.fondo) }]));
    const contrastes = Object.fromEntries(Object.entries(series).map(([k, v]) => [k, Number(contraste(v.trazo, v.fondo).toFixed(2))]));
    const nombres = Object.keys(series);
    const separacion = {};
    for (const [tipo, m] of Object.entries({ normal: null, ...MACHADO })) {
      let minimo = Infinity;
      for (let i = 0; i < nombres.length; i += 1) {
        for (let j = i + 1; j < nombres.length; j += 1) {
          const a = series[nombres[i]].trazo;
          const b = series[nombres[j]].trazo;
          minimo = Math.min(minimo, m ? dE(simular(a, m), simular(b, m)) : dE(a, b));
        }
      }
      separacion[tipo] = Number(minimo.toFixed(1));
    }
    salida[tema] = {
      contraste_series: contrastes,
      series_bajo_3a1: Object.values(contrastes).filter((c) => c < 3).length,
      deltaE_min_entre_series: separacion,
    };
  }
  return salida;
}
