// Qué se mide en cada pantalla: la URL, cuándo está lista y las áreas de interés (AOI) que tiene que comunicar.
// El orden de las AOI es la prioridad de atribución: un píxel cuenta para la primera AOI que lo cubre (como myPage).
// modo 'texto' = caja ajustada al texto renderizado (un título display:block no diluye su lift); 'caja' = el elemento.
import { API, WEB } from '../comun.mjs';

// La web busca la API en :8000; si el arnés corre en otros puertos (la app del dueño puede estar abierta), se pasa ?api=.
const Q = /^https?:\/\/localhost:8000\/?$/.test(API) ? '' : `?api=${API}`;
export const URL_RAIZ = `${WEB}/${Q}`;
const CASO = 'centro?fecha=2026-03-10&hora=19:00';

const AOI_AHORA = [
  { n: 'cifra_ahora', s: '#ahCifras .kpi:nth-child(1) :is(.k,.n)' },
  { n: 'pico_24h', s: '#ahCifras .kpi.dest :is(.k,.n)' },
  { n: 'linea_ahora', s: '#ahLienzo :is(.g-ahora,.g-pastilla,.g-pastilla-texto)', modo: 'caja' },
  { n: 'estado_datos', s: '#estadoDatos', modo: 'caja' },
  { n: 'dijimos_ayer', s: '#ahAyerTit, #ahAyer .dijimos, #ahAyer .veredicto', modo: 'caja' },
  { n: 'titulo', s: '#principal' },
  { n: 'que_es', s: '.cab-marca', modo: 'caja' },
  { n: 'modo', s: '#ahModo' },
  { n: 'otras_cifras', s: '#ahCifras .kpi:not(:nth-child(1)):not(.dest) :is(.k,.n)' },
  { n: 'grafico', s: '#ahLienzo svg', modo: 'caja' },
  { n: 'areas', s: '#ahAreas', modo: 'caja' },
  { n: 'cuando', s: '.cuando', modo: 'caja' },
  { n: 'regimen', s: '#chipRegimen', modo: 'caja' },
];

export const PANTALLAS = {
  // La primera apertura: la URL raíz, sin parámetros (en vivo, a la hora del reloj de Lima).
  inicio: { url: () => URL_RAIZ, listo: '#ahCifras .kpi', aoi: AOI_AHORA },
  // «Ahora» en repaso, el caso fijo de las tareas: reproducible día tras día.
  ahora: { url: () => `${URL_RAIZ}#/ahora/${CASO}`, listo: '#ahCifras .kpi', aoi: AOI_AHORA },
  confianza: {
    url: () => `${URL_RAIZ}#/confianza/centro`,
    listo: '#cfStats .stat',
    esperar: () => !/Calculando/.test(document.querySelector('#cfTitular').textContent) && !document.querySelector('#cfMes .cargando-bloque'),
    aoi: [
      { n: 'titular', s: '#cfTitular' },
      { n: 'cobertura', s: '#cfStats .stat:nth-child(3), #cfCobTit, #cfCob svg', modo: 'caja' },
      { n: 'aviso_vivo', s: '#cfLead b:nth-of-type(3), #cfVivoTit, #cfVivo .veredicto', modo: 'caja' },
      { n: 'mes_a_mes', s: '#cfMesTit, #cfMes svg', modo: 'caja' },
      { n: 'cifras', s: '#cfStats .stat:not(:nth-child(3)) :is(.k,.n)' },
      { n: 'lead', s: '#cfLead' },
      { n: 'estado_datos', s: '#estadoDatos', modo: 'caja' },
      { n: 'que_es', s: '.cab-marca', modo: 'caja' },
      { n: 'selectores', s: '.conf-cab', modo: 'caja' },
    ],
  },
  detalle: {
    url: () => `${URL_RAIZ}#/area/${CASO}&horizonte=24h&variante=M3`,
    listo: '#respValor',
    esperar: () => /\d/.test(document.querySelector('#respValor').textContent),
    aoi: [
      { n: 'cifra', s: '#respValor, #respTitulo' },
      { n: 'rango', s: '.resp-rango' },
      { n: 'real_y_error', s: '.resp-datos', modo: 'caja' },
      { n: 'curva', s: '#graficoDia svg', modo: 'caja' },
      { n: 'pico', s: '#tituloPico, #picoCuerpo', modo: 'caja' },
      { n: 'titulo', s: '#areaNombre, #areaDesc' },
      { n: 'secciones', s: '.nav-secciones', modo: 'caja' },
      { n: 'panel_controles', s: '.panel.controles', modo: 'caja' },
      { n: 'estado_datos', s: '#estadoDatos', modo: 'caja' },
      { n: 'que_es', s: '.cab-marca', modo: 'caja' },
    ],
  },
};

export const VISTAS = {
  escritorio: { width: 1366, height: 768 },
  proyector: { width: 1920, height: 1080 },
  tablet: { width: 1024, height: 768, isMobile: true, hasTouch: true },
  movil: { width: 375, height: 812, isMobile: true, hasTouch: true },
};
export const TEMAS = ['light', 'dark'];
