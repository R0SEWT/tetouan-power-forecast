// Qué se mide en cada pantalla: la URL, cuándo está lista y las áreas de interés (AOI) que tiene que comunicar.
// El orden de las AOI es la prioridad de atribución: un píxel cuenta para la primera AOI que lo cubre (como myPage).
// modo 'texto' = caja ajustada al texto renderizado (un título display:block no diluye su lift); 'caja' = el elemento.
import { API, WEB } from '../comun.mjs';

// La web busca la API en :8000; si el arnés corre en otros puertos (la app del dueño puede estar abierta), se pasa ?api=.
const Q = /^https?:\/\/localhost:8000\/?$/.test(API) ? '' : `?api=${API}`;
export const URL_RAIZ = `${WEB}/${Q}`;
const CASO = 'centro?fecha=2026-03-10&hora=19:00';

const AOI_AHORA = [
  // La cifra de ahora: la primera tarjeta de cifras hasta el PR 2; desde el PR 3, la de la respuesta a la pregunta del día
  { n: 'cifra_ahora', s: ':is(#ahCifras .kpi:nth-child(1), #ahRespuesta .r-ahora) :is(.k,.n)' },
  { n: 'pico_24h', s: '#ahCifras :is(.kpi.dest, .kpi-pico) :is(.k,.n)' }, // .dest hasta el PR 2, .kpi-pico desde entonces
  // El punto de «ahora»: línea, punto y pastilla (hasta el PR 6 el punto era el círculo que sigue a la pastilla);
  // desde el PR 7 también el halo y el valor que lo acompañan
  { n: 'linea_ahora', s: '#ahLienzo :is(.g-ahora,.g-pastilla,.g-pastilla-texto,.g-pastilla-texto + .g-punto,.g-ahora-halo,.g-ahora-punto,.g-ahora-valor,.g-ahora-valor-texto)', modo: 'caja' },
  { n: 'estado_datos', s: '#estadoDatos', modo: 'caja' },
  { n: 'dijimos_ayer', s: '#ahAyerTit, #ahAyer .dijimos, #ahAyer .veredicto', modo: 'caja' },
  { n: 'titulo', s: '#principal' },
  { n: 'que_es', s: '.cab-marca', modo: 'caja' },
  { n: 'modo', s: '#ahModo' },
  { n: 'otras_cifras', s: '#ahCifras .kpi:not(:nth-child(1)):not(.dest):not(.kpi-pico) :is(.k,.n)' },
  { n: 'rotulos', s: '#ahLienzo .g-rotulo' }, // «Real (COES)» y «Pronóstico» sobre sus líneas (PR 7)
  { n: 'grafico', s: '#ahLienzo svg', modo: 'caja' },
  // El selector de área: la elegida y cada una de las otras por separado (PR 12); lo que queda del control, «areas»
  { n: 'area_elegida', s: '#ahAreas > [aria-current="page"]', modo: 'caja' },
  { n: 'area_otra_1', s: '#ahAreas > a:nth-child(1 of :not([aria-current="page"]))', modo: 'caja' },
  { n: 'area_otra_2', s: '#ahAreas > a:nth-child(2 of :not([aria-current="page"]))', modo: 'caja' },
  { n: 'areas', s: '#ahAreas', modo: 'caja' },
  { n: 'cuando', s: '.cuando', modo: 'caja' },
  { n: 'regimen', s: '#chipRegimen', modo: 'caja' },
  { n: 'respuesta', s: '#ahRespuesta .r-frase' }, // la frase que responde la pregunta del día (PR 3)
];

const LISTO_AHORA = ':is(#ahRespuesta .r-ahora, #ahCifras .kpi)';

export const PANTALLAS = {
  // La primera apertura: la URL raíz, sin parámetros (en vivo, a la hora del reloj de Lima).
  // Lista cuando se ve la cifra de ahora: la primera tarjeta hasta el PR 2, la respuesta desde el PR 3
  inicio: { url: () => URL_RAIZ, listo: LISTO_AHORA, aoi: AOI_AHORA },
  // «Ahora» en repaso, el caso fijo de las tareas: reproducible día tras día.
  ahora: { url: () => `${URL_RAIZ}#/ahora/${CASO}`, listo: LISTO_AHORA, aoi: AOI_AHORA },
  // El mismo día en repaso a media mañana: el pronóstico del día ya está y el pico, por llegar (desde el PR 7)
  ahora_dia: { url: () => `${URL_RAIZ}#/ahora/centro?fecha=2026-03-10&hora=10:30`, listo: LISTO_AHORA, aoi: AOI_AHORA },
  confianza: {
    url: () => `${URL_RAIZ}#/confianza/centro`,
    listo: '#cfStats .stat',
    esperar: () => /\S/.test(document.querySelector('#cfTitular')?.textContent || '') && !/Calculando/.test(document.querySelector('#cfTitular').textContent) && !document.querySelector('#cfMes .cargando-bloque'),
    aoi: [
      { n: 'titular', s: '#cfTitular' },
      // El aviso en vivo antes que la cobertura: desde el PR 10 va dentro de la tarjeta de cobertura (.aviso-vivo)
      { n: 'aviso_vivo', s: '#cfLead b:nth-of-type(3), #cfVivoTit, #cfVivo .veredicto, #vistaConfianza .aviso-vivo', modo: 'caja' },
      // La tarjeta de cobertura de la fila de cifras (la única con veredicto) o, desde el PR 10, la de junto al titular
      { n: 'cobertura', s: '#cfStats .stat:has(> .estado-meta), #cfCobVista, #cfCobTit, #cfCob svg', modo: 'caja' },
      { n: 'mes_a_mes', s: '#cfMesTit, #cfMes svg', modo: 'caja' },
      { n: 'cifras', s: '#cfStats .stat:not(:has(> .estado-meta)) :is(.k,.n)' },
      { n: 'lead', s: '#cfLead' },
      { n: 'estado_datos', s: '#estadoDatos', modo: 'caja' },
      { n: 'que_es', s: '.cab-marca', modo: 'caja' },
      { n: 'selectores', s: '.conf-cab', modo: 'caja' },
    ],
  },
  detalle: {
    url: () => `${URL_RAIZ}#/area/${CASO}&horizonte=24h&variante=M3`,
    listo: '#respValor',
    esperar: () => /\d/.test(document.querySelector('#respValor')?.textContent || ''),
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
