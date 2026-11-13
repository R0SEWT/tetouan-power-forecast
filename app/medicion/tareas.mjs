// Las cuatro tareas clave con un oráculo independiente de la interfaz: qué cifras tiene que ver
// la persona (calculadas aquí desde la API) para dar la tarea por cumplida.
// Se mide: si se cumple (y qué falta), acciones (clics, pulsaciones, desplazamientos),
// segundos del robot (incluye la latencia de la API) y segundos estimados para una persona (KLM).
import { api, CASO, fmt0, fmt1, mediana, nuevaPagina, textoVisible, URL_AREA, vigilarRed, WEB } from './comun.mjs';
import { version } from './versiones.mjs';

// Keystroke-Level Model (Card, Moran y Newell, 1980; valores de Kieras, 2001).
const KLM = { M: 1.35, P: 1.1, B: 0.2, K: 0.28, H: 0.4, S: 1.0 }; // S: un gesto de desplazamiento y volver a ubicarse (supuesto)

const REGIMEN = {
  neutro: 'Neutro', debil: 'Niño débil', moderado: 'Niño moderado', fuerte: 'Niño fuerte',
  extraordinario: 'Niño extraordinario', falla_en_curso: 'Falla en curso', red_golpeada: 'Red golpeada',
};

function maeDe(real, otro) {
  let s = 0;
  let n = 0;
  real.forEach((r, i) => {
    if (r != null && otro[i] != null) { s += Math.abs(r - otro[i]); n += 1; }
  });
  return n ? s / n : null;
}

// Grupos de fichas: cada grupo se cumple si se vio cualquiera de sus alternativas.
export async function oraculos() {
  const { area, fecha, idx } = CASO;
  const serie = await api(`/series/${area}?fecha=${fecha}&horizonte=24h&variante=M3`);
  const previo = new Date(`${fecha}T00:00:00Z`);
  previo.setUTCDate(previo.getUTCDate() - 1);
  const origenPrevio = `${previo.toISOString().slice(0, 10)}T${CASO.hora}`;
  const p = await api('/pronostico', { area, origen: origenPrevio, horizonte: '24h', variante: 'M3' });
  const u = p.pronostico.length - 1;
  const maeM = maeDe(serie.real, serie.pronostico);
  const maeR = maeDe(serie.real, serie.referencia);
  const base = await api('/pronostico', { area, origen: `${fecha}T${CASO.hora}`, horizonte: '24h', variante: 'M3' });
  const esc = await api('/pronostico', {
    area, origen: `${fecha}T${CASO.hora}`, horizonte: '24h', variante: 'M3', escenario: { delta_temp_c: 2 },
  });
  const pico = base.pronostico.indexOf(Math.max(...base.pronostico));
  const cambio = esc.pronostico[pico] - base.pronostico[pico];
  const diag = await api(`/diagnostico/${area}`);
  const peor = diag.mae_por_regimen.reduce((a, b) => (b.modelo > a.modelo ? b : a));
  return {
    t1: {
      nombre: 'Pronóstico de un área, horizonte y fecha, con intervalo y real',
      grupos: {
        pronostico: [fmt0(serie.pronostico[idx])],
        'intervalo inferior': [fmt0(p.intervalo.inferior[u])],
        'intervalo superior': [fmt0(p.intervalo.superior[u])],
        real: [fmt0(serie.real[idx])],
      },
    },
    t2: {
      nombre: '¿Se puede confiar? Error reciente frente a la referencia',
      grupos: {
        'error del modelo': [fmt1(maeM), `${fmt0(maeM)} MW`],
        'comparación con la referencia': [fmt1(maeR), `${fmt0(maeR - maeM)} MW`, `${fmt0(Math.abs(maeR - maeM))} MW menos`],
      },
    },
    t3: {
      nombre: 'Efecto de +2 °C en el pronóstico a 24 h',
      grupos: { 'cambio del escenario': [`${fmt0(Math.abs(cambio))} MW`, fmt0(esc.pronostico[pico])] },
    },
    t4: {
      nombre: 'Diagnóstico: régimen de El Niño con más error',
      grupos: { régimen: [REGIMEN[peor.regimen] || peor.regimen], error: [fmt1(peor.modelo)] },
    },
  };
}

const escapar = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const patron = (ficha) => new RegExp(`(?<![\\d,.])${escapar(ficha)}(?![\\d])`);

function anotarVistos(texto, grupos, vistos) {
  for (const [g, alts] of Object.entries(grupos)) {
    if (!vistos.has(g) && alts.some((a) => patron(a).test(texto))) vistos.add(g);
  }
}

// Busca en el DOM un nodo de texto visible por estilo con la ficha, lo lleva a la vista y
// devuelve cuántos gestos de desplazamiento haría falta (0.8 de la altura del contenedor por gesto).
async function desplazarHasta(pagina, ficha) {
  return pagina.evaluate((fuente) => {
    const re = new RegExp(fuente);
    const caminante = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let nodo;
    while ((nodo = caminante.nextNode())) {
      if (!re.test(nodo.textContent)) continue;
      const el = nodo.parentElement;
      if (!el || el.closest('[hidden]') || !el.getClientRects().length) continue;
      let c = el.parentElement;
      while (c && c !== document.body) {
        const s = getComputedStyle(c);
        if (/(auto|scroll)/.test(s.overflowY) && c.scrollHeight > c.clientHeight + 2) break;
        c = c.parentElement;
      }
      const contenedor = c && c !== document.body ? c : document.scrollingElement;
      const antes = contenedor.scrollTop;
      el.scrollIntoView({ block: 'center', behavior: 'instant' });
      const delta = Math.abs(contenedor.scrollTop - antes);
      const alto = contenedor === document.scrollingElement ? innerHeight : contenedor.clientHeight;
      return delta < 4 ? 0 : Math.ceil(delta / (0.8 * alto));
    }
    return null;
  }, patron(ficha).source);
}

// Mira la pantalla y, si falta algo que está en la página, se desplaza hasta verlo (contando gestos).
async function revisar(pagina, grupos, vistos, cuenta, esperar) {
  await esperar();
  anotarVistos(await textoVisible(pagina), grupos, vistos);
  for (const [g, alts] of Object.entries(grupos)) {
    if (vistos.has(g)) continue;
    for (const a of alts) {
      const gestos = await desplazarHasta(pagina, a);
      if (gestos == null) continue;
      await pagina.waitForTimeout(200);
      const antes = vistos.size;
      anotarVistos(await textoVisible(pagina), grupos, vistos);
      if (vistos.has(g) || vistos.size > antes) cuenta.desplazamientos += Math.max(1, gestos);
      if (vistos.has(g)) break;
    }
  }
}

async function correrRuta(pagina, ruta, grupos, vistos, cuenta, esperar) {
  for (const paso of ruta) {
    if (paso.revisar) {
      await revisar(pagina, grupos, vistos, cuenta, esperar);
      continue;
    }
    if (paso.clic) {
      const loc = paso.clic(pagina).first();
      if (paso.foco) await loc.focus();
      else await loc.click();
      cuenta.clics += 1;
    } else if (paso.escribir) {
      await paso.escribir(pagina).first().fill(paso.texto);
      cuenta.escrituras += 1;
      cuenta.pulsaciones += paso.texto.replace(/-/g, '').length;
    } else if (paso.teclas) {
      for (let i = 0; i < paso.veces; i += 1) await paso.teclas(pagina).first().press(paso.tecla);
      cuenta.pulsaciones += paso.veces;
    }
    await esperar();
  }
  await revisar(pagina, grupos, vistos, cuenta, esperar);
}

export async function medirTarea(navegador, nombreVersion, clave, oraculo, vista) {
  const { contexto, pagina } = await nuevaPagina(navegador, vista);
  const esperar = vigilarRed(pagina);
  const ruta = version(nombreVersion).tareas[clave];
  const inicio = clave === 't1' ? `${WEB}/` : URL_AREA;
  await pagina.goto(inicio);
  await esperar(500);
  const vistos = new Set();
  const cuenta = { clics: 0, escrituras: 0, pulsaciones: 0, desplazamientos: 0 };
  const t0 = Date.now();
  await correrRuta(pagina, ruta, oraculo.grupos, vistos, cuenta, esperar);
  const segundos = (Date.now() - t0) / 1000;
  await contexto.close();
  const faltan = Object.keys(oraculo.grupos).filter((g) => !vistos.has(g));
  const klm = cuenta.clics * (KLM.M + KLM.P + KLM.B)
    + cuenta.escrituras * (KLM.M + KLM.H)
    + cuenta.pulsaciones * KLM.K
    + cuenta.desplazamientos * KLM.S;
  return {
    cumplida: faltan.length === 0,
    vistos: Object.keys(oraculo.grupos).length - faltan.length,
    total: Object.keys(oraculo.grupos).length,
    faltan,
    acciones: cuenta.clics + cuenta.escrituras + cuenta.pulsaciones + cuenta.desplazamientos,
    ...cuenta,
    segundos_robot: Number(segundos.toFixed(2)),
    segundos_klm: Number(klm.toFixed(1)),
  };
}

export async function medirTareas(navegador, nombreVersion, repeticiones = 3) {
  const o = await oraculos();
  const salida = {};
  for (const clave of Object.keys(o)) {
    salida[clave] = { nombre: o[clave].nombre, fichas: o[clave].grupos };
    for (const vista of ['escritorio', 'movil']) {
      const corridas = [];
      for (let i = 0; i < repeticiones; i += 1) corridas.push(await medirTarea(navegador, nombreVersion, clave, o[clave], vista));
      const r = corridas[0];
      r.segundos_robot = mediana(corridas.map((c) => c.segundos_robot));
      salida[clave][vista] = r;
    }
  }
  return salida;
}
