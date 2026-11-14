// Accesibilidad y estructura: axe-core por estado, recorrido de foco, tamaño de los objetivos,
// desborde horizontal, cromo fijo que tapa contenido y afirmaciones no respaldadas.
import AxeBuilder from '@axe-core/playwright';
import { nuevaPagina, URL_AREA, WEB } from './comun.mjs';
import { version } from './versiones.mjs';

const ETIQUETAS_WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

export async function abrirEstado(navegador, nombreVersion, estado, vista, tema) {
  const { contexto, pagina } = await nuevaPagina(navegador, vista, tema);
  const v = version(nombreVersion);
  await pagina.goto((v.url && v.url(estado)) || (estado === 'inicio' ? `${WEB}/` : URL_AREA));
  await pagina.waitForLoadState('networkidle');
  await version(nombreVersion).estados[estado](pagina);
  await pagina.waitForLoadState('networkidle').catch(() => {});
  await pagina.waitForTimeout(700);
  return { contexto, pagina };
}

export async function medirAxe(navegador, nombreVersion) {
  const estados = Object.keys(version(nombreVersion).estados);
  const porRegla = {};
  const corridas = [];
  let infracciones = 0;
  let nodos = 0;
  let buenasPracticas = 0;
  for (const estado of estados) {
    for (const vista of ['movil', 'escritorio']) {
      for (const tema of ['dark', 'light']) {
        const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, estado, vista, tema);
        const wcag = await new AxeBuilder({ page: pagina }).withTags(ETIQUETAS_WCAG).analyze();
        const bp = await new AxeBuilder({ page: pagina }).withTags(['best-practice']).analyze();
        await contexto.close();
        let n = 0;
        wcag.violations.forEach((v) => {
          n += v.nodes.length;
          porRegla[v.id] = porRegla[v.id] || { impacto: v.impact, nodos: 0, estados: new Set() };
          porRegla[v.id].nodos += v.nodes.length;
          porRegla[v.id].estados.add(`${estado}/${vista}/${tema}`);
        });
        infracciones += wcag.violations.length;
        nodos += n;
        buenasPracticas += bp.violations.reduce((s, v) => s + v.nodes.length, 0);
        corridas.push({ estado, vista, tema, reglas: wcag.violations.map((v) => v.id), nodos: n });
      }
    }
  }
  const reglas = Object.fromEntries(Object.entries(porRegla).map(([k, v]) => [k, { impacto: v.impacto, nodos: v.nodos, estados: v.estados.size }]));
  return { pantallas: corridas.length, infracciones, nodos, buenas_practicas_nodos: buenasPracticas, reglas, corridas };
}

// Recorre la página con Tab: cuántos elementos reciben foco, cuántos quedan tapados por el cromo fijo
// (WCAG 2.4.11) o sin indicador visible (2.4.7), y cuántas pulsaciones hasta controles clave.
export async function medirFoco(navegador, nombreVersion, vista) {
  const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, 'area', vista, 'dark');
  const objetivos = version(nombreVersion).foco || { horizonte: /24 horas/, diagnostico: /Diagn[oó]stico/ };
  await pagina.evaluate(() => { document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); });
  const vistos = [];
  let hastaHorizonte = null;
  let hastaDiagnostico = null;
  for (let i = 1; i <= 90; i += 1) {
    await pagina.keyboard.press('Tab');
    const info = await pagina.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      const indicador = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || (s.boxShadow && s.boxShadow !== 'none');
      const cx = Math.min(innerWidth - 1, Math.max(0, r.left + r.width / 2));
      const cy = Math.min(innerHeight - 1, Math.max(0, r.top + r.height / 2));
      const arriba = document.elementFromPoint(cx, cy);
      const dentro = r.bottom > 0 && r.top < innerHeight;
      const tapado = !dentro || !arriba || !(arriba === el || el.contains(arriba));
      const nombre = (el.getAttribute('aria-label') || el.textContent || el.value || el.id || el.tagName).replace(/\s+/g, ' ').trim().slice(0, 50);
      const clave = el.id || nombre + el.tagName;
      // Si cae en una lista de pestañas, cuántas flechas faltan hasta «Diagnóstico»
      let flechas = null;
      if (el.getAttribute('role') === 'tab') {
        const tabs = [...el.closest('[role=tablist]').querySelectorAll('[role=tab]')];
        const d = tabs.findIndex((t) => /Diagn/.test(t.textContent));
        if (d >= 0) flechas = (d - tabs.indexOf(el) + tabs.length) % tabs.length;
      }
      return { nombre, clave, tapado, indicador, tag: el.tagName, flechas };
    });
    if (!info) continue;
    if (vistos.length && info.clave === vistos[0].clave) break; // dio la vuelta
    vistos.push(info);
    const texto = `${info.nombre} ${info.clave}`;
    if (hastaHorizonte == null && objetivos.horizonte.test(texto)) hastaHorizonte = i;
    if (hastaDiagnostico == null && info.flechas != null) hastaDiagnostico = i + info.flechas;
    else if (hastaDiagnostico == null && objetivos.diagnostico.test(texto)) hastaDiagnostico = i;
  }
  await contexto.close();
  return {
    enfocables: vistos.length,
    tapados: vistos.filter((v) => v.tapado).length,
    tapados_ejemplos: vistos.filter((v) => v.tapado).slice(0, 6).map((v) => v.nombre),
    sin_indicador: vistos.filter((v) => !v.indicador).length,
    sin_indicador_ejemplos: vistos.filter((v) => !v.indicador).slice(0, 6).map((v) => `${v.tag} ${v.nombre}`),
    tabs_hasta_horizonte: hastaHorizonte,
    tabs_hasta_diagnostico: hastaDiagnostico,
  };
}

// Medidas de estructura en la vista del área.
export async function medirEstructura(navegador, nombreVersion, vista, fichaPronostico) {
  const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, 'area', vista, 'dark');
  const r = await pagina.evaluate((ficha) => {
    const interactivos = [...document.querySelectorAll('a[href], button, input, select, textarea, [role=tab], [tabindex]:not([tabindex="-1"])')]
      .filter((el) => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden');
    const tam = interactivos.map((el) => {
      const b = el.getBoundingClientRect();
      // Los input range miden su pista: cuenta la altura del control completo
      return { min: Math.min(b.width, b.height), nombre: (el.getAttribute('aria-label') || el.textContent || el.tagName).trim().slice(0, 30) };
    });
    // Cromo fijo o pegajoso que ocupa la ventana
    let cromo = 0;
    document.querySelectorAll('body *').forEach((el) => {
      const s = getComputedStyle(el);
      if ((s.position === 'fixed' || s.position === 'sticky') && el.getClientRects().length) {
        const b = el.getBoundingClientRect();
        const visible = Math.max(0, Math.min(innerHeight, b.bottom) - Math.max(0, b.top));
        if (b.width > innerWidth * 0.5) cromo += visible;
      }
    });
    // ¿Se ve el número pronosticado sin desplazarse?
    let respuesta = false;
    const re = new RegExp(`(?<![\\d,.])${ficha.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![\\d])`);
    const caminante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let nodo;
    while ((nodo = caminante.nextNode())) {
      if (!re.test(nodo.textContent)) continue;
      const el = nodo.parentElement;
      if (!el || el.closest('[hidden]')) continue;
      const b = el.getBoundingClientRect();
      if (!b.width || b.bottom < 0 || b.top > innerHeight) continue;
      const arriba = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      if (arriba && (arriba === el || el.contains(arriba) || arriba.contains(el))) { respuesta = true; break; }
    }
    const hRespuesta = (() => {
      const tam = [];
      const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        const el = n.parentElement;
        if (re.test(n.textContent) && el && !el.closest('[hidden]') && el.getClientRects().length && !el.closest('svg')) tam.push(parseFloat(getComputedStyle(el).fontSize));
      }
      return tam.length ? Math.max(...tam) : null;
    })();
    return {
      interactivos: tam.length,
      menores_24px: tam.filter((t) => t.min < 24).length,
      menores_44px: tam.filter((t) => t.min < 44).length,
      ejemplos_menores_24: tam.filter((t) => t.min < 24).slice(0, 5).map((t) => t.nombre),
      cromo_fijo_pct: Math.round((100 * cromo) / innerHeight),
      respuesta_sin_desplazar: respuesta,
      tamano_fuente_respuesta_px: hRespuesta,
      alto_pagina_px: document.scrollingElement.scrollHeight,
    };
  }, fichaPronostico);
  await contexto.close();
  return r;
}

export async function medirDesborde(navegador, nombreVersion) {
  const salida = {};
  for (const ancho of [320, 375]) {
    const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, 'area', 'movil', 'dark');
    await pagina.setViewportSize({ width: ancho, height: 740 });
    await pagina.waitForTimeout(400);
    salida[`${ancho}px`] = await pagina.evaluate(() => Math.max(0, document.scrollingElement.scrollWidth - innerWidth));
    await contexto.close();
  }
  return salida;
}

// Afirmaciones que el proyecto no respalda (por ahora: la comparación con la Programación Diaria del COES).
export async function medirAfirmaciones(navegador, nombreVersion) {
  let total = 0;
  const donde = [];
  for (const estado of Object.keys(version(nombreVersion).estados)) {
    const { contexto, pagina } = await abrirEstado(navegador, nombreVersion, estado, 'escritorio', 'dark');
    const texto = await pagina.evaluate(() => document.body.innerText);
    const n = (texto.match(/Programaci[oó]n (Diaria|COES)/gi) || []).length;
    if (n) donde.push(`${estado}: ${n}`);
    total += n;
    await contexto.close();
  }
  return { programacion_diaria_visible: total, donde };
}
