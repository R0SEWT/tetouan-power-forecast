'use strict';

/* ==========================================================================
   Curva · lo de «Ahora» que nadie necesita al abrir: la ficha técnica, la tabla del gráfico y el CSV.
   Se carga al pedirlo (conExtra, en app.js) y usa las utilidades y el estado de app.js.
   ========================================================================== */

// ---- Ficha técnica -------------------------------------------------------------------------

function pintarFicha() {
  const r = S.resumen;
  const s = S.salud;
  const prueba = s && s.modelo === 'prueba';
  const cortes = r
    ? Object.entries(r.fechas_corte).map(([k, v]) => `<tr><td>${esc(CORTE[k] || k)}</td><td class="num mono">${esc(v)}</td></tr>`).join('')
    : '';
  let nino = '';
  if (r) {
    const [y, m] = r.regimen_nino.mes.split('-').map(Number);
    nino = `El último ICEN publicado es ${r.regimen_nino.icen.toFixed(2)}, de ${MESES[m - 1]} de ${y}: régimen ${ESTADO_NINO[r.regimen_nino.estado] || r.regimen_nino.estado} según ENFEN. `;
  }
  $('#fichaCuerpo').innerHTML = `
    <section><h3>Qué hace</h3><p>Pronostica la demanda eléctrica de las áreas Norte, Centro y Sur del SEIN cada 30 minutos, a 1 hora y a 24 horas, con su rango del 90 %. La compara con la referencia: la mejor de tres reglas sin modelo (el último dato, ayer o la semana pasada a la misma hora).</p></section>
    <section><h3>Modelo</h3><p>Modelo <span class="mono">${esc(s ? nombreModelo() : '—')}</span>, datos <span class="mono">${esc(s ? s.version_datos : '—')}</span>.${prueba ? ' Es el modelo de prueba: persistencia, ciclo diario y ruido sobre series sintéticas. Sirve para probar la app; sus números no son resultados.' : ''}</p></section>
    <section><h3>El Niño Costero</h3><p>${esc(nino)}Cada variable entra con su rezago real de publicación.</p></section>
    <section><h3>Fechas de corte</h3><table class="tabla"><tbody>${cortes}</tbody></table></section>
    <section><h3>Fuentes y licencias</h3><ul>
      <li>COES: demanda por área (IEOD) y eventos. Sin licencia publicada.</li>
      <li>ERA5 de Copernicus, vía Open-Meteo: temperatura. CC BY 4.0.</li>
      <li>IGP y ENFEN: ICEN.</li>
      <li>NOAA: Niño 1+2. Dominio público.</li>
      <li>Osinergmin: SAIDI. ODC-By.</li>
    </ul></section>
    <section><h3>Supuesto de colaboración</h3><p>Se simula que el COES recibe en tiempo real los datos y los pronósticos de clima y de El Niño de ENFEN (SENAMHI, IGP e IMARPE). Por eso hay escenarios a 24 h.</p></section>
    <section><h3>Por qué no hay escenarios a 1 h</h3><p>A 1 h la demanda reciente ya contiene el clima del momento. En su lugar se muestra la sensibilidad del modelo.</p></section>
    <section><h3>Lo que no cubre</h3><ul>
      <li>La demanda por subestación o por distribuidora.</li>
      <li>Los costos marginales.</li>
      <li>Pronósticos de clima reales: se simulan.</li>
    </ul></section>`;
}

function pintarTablaAhora(d) {
  const filas = d.fecha_hora.map((fh, i) => {
    const real = i <= d.i_origen ? d.real[i] : (A.despues && d.real_despues ? d.real_despues[i] : null);
    return `<tr${i === d.i_ahora ? ' class="fila-elegida"' : ''}><th scope="row">${esc(diaCorto(fh))} ${esc(horaDe(fh))}</th>`
      + `<td>${real == null ? '—' : mw(real)}</td><td>${mw(d.pronostico[i])}</td><td>${mw(d.inferior[i])}–${mw(d.superior[i])}</td>`
      + `<td>${d.referencia[i] == null ? '—' : mw(d.referencia[i])}</td></tr>`;
  }).join('');
  $('#ahTabla').innerHTML = '<div class="tabla-scroll" tabindex="0" role="region" aria-label="Datos del gráfico"><table class="t">'
    + `<caption class="visually-hidden">Demanda del ${esc(nombreArea(A.area))} en MW: real, pronóstico a 24 h, rango del ${d.nivel_rango_pct} % y referencia</caption>`
    + `<thead><tr><th scope="col">Hora</th><th scope="col">Real</th><th scope="col">Pronóstico</th><th scope="col">Rango ${d.nivel_rango_pct} %</th><th scope="col">Referencia</th></tr></thead>`
    + `<tbody>${filas}</tbody></table></div>`;
}

function descargarCsvAhora() {
  const d = A.datos.get(A.area);
  if (!d) return;
  const filas = [['inicio_periodo', 'pronostico_mw', `rango_${d.nivel_rango_pct}_inferior_mw`, `rango_${d.nivel_rango_pct}_superior_mw`, 'error_mw']];
  d.fecha_hora.forEach((fh, i) => {
    const real = i <= d.i_origen ? d.real[i] : (d.real_despues ? d.real_despues[i] : null);
    filas.push([fh, d.pronostico[i], d.inferior[i], d.superior[i], real == null ? '' : (d.pronostico[i] - real).toFixed(1)]);
  });
  const cabeza = `# Curva · ${nombreArea(A.area)} · ${d.modelo_nombre} · último dato real hasta ${d.datos_hasta} (hora de Lima)\n`
    + '# pronostico_mw: pronóstico directo a 24 h, emitido 24 h antes de cada periodo; error_mw = pronóstico − real\n';
  const blob = new Blob([cabeza + filas.map((f) => f.join(',')).join('\n')], { type: 'text/csv;charset=utf-8' });
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(blob);
  enlace.download = `curva-${A.area}-${d.origen.replace(':', '')}.csv`;
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
}
