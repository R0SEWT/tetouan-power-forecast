'use strict';

/* ==========================================================================
   Curva · «Confianza»: el error al frente, con su meta, sus días fallidos y su contexto.
   Se carga al abrir la pantalla (cargarPantalla, en app.js) y usa las utilidades y el estado de app.js.
   ========================================================================== */

function mostrarConfianza(area, q) {
  C.area = area;
  if (['1h', '24h'].includes(q.get('horizonte'))) C.horizonte = q.get('horizonte');
  C.mes = /^\d{4}-\d{2}$/.test(q.get('mes') || '') ? q.get('mes') : (A.fecha && A.fecha.startsWith('2026') ? A.fecha.slice(0, 7) : C.mes);
  C.ir = q.get('seccion') === 'nino' ? '#cfNinoTit' : null; // el chip de El Niño de «Ahora» lleva a su sección
  const llega = $('#vistaConfianza').hidden;
  mostrarVista('confianza');
  document.title = `${nombreArea(area)} · Confianza · ${TITULO_CURVA}`;
  if (llega) window.scrollTo(0, 0);
  $('#cfAreas').innerHTML = (S.areas.length ? S.areas : AREAS_RESPALDO).map((a) => `<a href="#/confianza/${encodeURIComponent(a.id)}?horizonte=${C.horizonte}"${a.id === area ? ' aria-current="page"' : ''}>${esc(a.nombre)}</a>`).join('');
  $$('[data-cf-horizonte]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.cfHorizonte === C.horizonte)));
  cargarConfianza();
}

async function cargarConfianza() {
  const turno = ++C.turno;
  const { area, horizonte } = C;
  const m = hayVariosModelos() && S.modelo ? S.modelo : null;
  $('#cfTitular').textContent = 'Calculando la confianza…';
  $('#vistaConfianza').classList.add('desactualizada');
  const q = new URLSearchParams({ horizonte, variante: 'M3' });
  if (m) q.set('modelo', m);
  const diagClave = `${S.modelo || ''}|${area}`;
  const [conf, vivo, diag] = await Promise.allSettled([
    api(`/confianza/${encodeURIComponent(area)}?${q}`), // sin caché aquí: su parte en vivo crece cada mañana (el backend cachea el historial)
    api(`/en-vivo/${encodeURIComponent(area)}`),
    S.diag.has(diagClave) ? Promise.resolve(S.diag.get(diagClave)) : api(`/diagnostico/${encodeURIComponent(area)}${m ? `?modelo=${encodeURIComponent(m)}` : ''}`),
  ]);
  if (turno !== C.turno) return;
  $('#vistaConfianza').classList.remove('desactualizada');
  if (conf.status === 'rejected') {
    // Nada de la selección anterior queda a la vista: se vacían todas las secciones
    C.datos = null;
    if (conf.reason.estado === 0) mostrarError(conf.reason);
    $('#cfTitular').textContent = 'No pudimos calcular la confianza de esta área';
    $('#cfLead').textContent = textoError(conf.reason);
    $('#cfStats').innerHTML = '';
    $('#cfCobVista').innerHTML = '';
    ['#cfMes', '#cfCob', '#cfVivo', '#cfDia', '#cfSesgo', '#cfNino'].forEach((s) => { $(s).innerHTML = '<p class="vacio">Sin datos por ahora.</p>'; });
    $('#cfMundo').innerHTML = '';
    return;
  }
  limpiarError();
  if (diag.status === 'fulfilled') S.diag.set(diagClave, diag.value);
  C.datos = { conf: conf.value, vivo: vivo.status === 'fulfilled' ? vivo.value : null, diag: diag.status === 'fulfilled' ? diag.value : null };
  const u = C.datos.vivo && C.datos.vivo.ultimo;
  if (u) {
    const fin = finTxt(u.datos_hasta);
    pintarEstado({ modo: 'vivo', texto: `Datos del COES al ${fin.corto}`, corto: ['COES', fin.corto.replace(', ', ' ')], titulo: `Datos reales del COES hasta el ${fin.largo}` });
  } else {
    pintarEstado({ modo: 'repaso', texto: 'Prueba de 2026', titulo: 'El error medido en la prueba de 2026' });
  }
  pintarConfianzaPantalla();
  if (C.ir) {
    const sec = $(C.ir).closest('section');
    C.ir = null;
    // Debajo de la cabecera fija, no tapado por ella
    const cabecera = document.querySelector('header');
    const arriba = sec.getBoundingClientRect().top + window.scrollY - (cabecera ? cabecera.getBoundingClientRect().height : 0) - 12;
    window.scrollTo({ top: Math.max(0, arriba), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    sec.setAttribute('tabindex', '-1');
    sec.focus({ preventScroll: true });
  }
}

function pintarConfianzaPantalla() {
  const { conf, vivo, diag } = C.datos;
  const seg = conf.seguimiento;
  const area = nombreArea(C.area);
  const h = C.horizonte === '1h' ? '1 hora' : '24 horas';
  const nombreRef = NOMBRE_REF[seg.referencia_nombre] || 'la referencia';
  const n = seg.meses.length;
  const ganados = seg.meses.filter((x) => x.mae_modelo < x.mae_referencia).length;
  const t = seg.total;
  const mejora = (100 * (t.mae_referencia - t.mae_modelo)) / t.mae_referencia;
  const meta = seg.meta_cobertura_pct;
  const bajos = seg.meses.filter((x) => x.cobertura_pct < meta - 2);
  const vCob = veredictoCobertura(t.cobertura_pct, meta);
  const rVivo = vivo && vivo.resumen ? (vivo.resumen.find((x) => x.horizonte === '24h' && x.grupo === 'en_vivo') || vivo.resumen.find((x) => x.horizonte === '24h')) : null;
  $('#cfTitular').textContent = ganados === n
    ? `En 2026 se equivocó menos que la referencia los ${n} meses.`
    : `En 2026 le ganó a la referencia en ${ganados} de ${n} meses.`;
  let lead = `${esc(area)}, a ${h}: error medio de <b>${nf1.format(t.mae_modelo)} MW</b> (megavatios; ${nf1.format(conf.mape_pct)} % de la demanda), ${nf0.format(Math.abs(mejora))} % ${mejora >= 0 ? 'menos' : 'más'} que repetir ${esc(nombreRef)}. `
    + `El rango del ${nf0.format(meta)} % cubrió el <b>${nf1.format(t.cobertura_pct)} %</b> en el año${bajos.length ? `, pero quedó corto en ${esc(bajos.map((x) => mesLargo(x.mes)).join(', '))}` : ''}. `;
  if (rVivo) {
    const vv = veredictoCobertura(rVivo.cobertura_pct, vivo.nivel_rango_pct);
    lead += `En vivo, desde el ${esc(fechaDiaMes(rVivo.desde))}, el rango del ${vivo.nivel_rango_pct} % cubrió el <b>${nf1.format(rVivo.cobertura_pct)} %</b>: ${esc(vv.texto)}. `;
  }
  lead += 'Todo se mide contra la demanda real que publica el COES, el operador del sistema eléctrico, con pronósticos que el modelo no vio al entrenar; 2026 sí se usó para elegir el modelo.';
  $('#cfLead').innerHTML = lead;

  const ac = conf.acierto;
  $('#cfStats').innerHTML = [
    `<div class="stat"><p class="k">Error medio 2026</p><p class="n">${nf1.format(t.mae_modelo)}<small> MW</small></p><p class="d">${nf1.format(conf.mape_pct)} % de la demanda (MAPE)</p></div>`,
    `<div class="stat"><p class="k">Frente a la referencia</p><p class="n">${mejora >= 0 ? '−' : '+'}${nf0.format(Math.abs(mejora))}<small> %</small></p><p class="d">${nf1.format(t.mae_referencia)} MW la referencia</p></div>`,
    ac ? `<div class="stat"><p class="k">Hora del pico (±1 h)</p><p class="n">${nf1.format(ac.pct_hora)}<small> %</small></p><p class="d">de ${nf0.format(ac.dias)} días; referencia ${nf1.format(ac.pct_hora_referencia)} %</p></div>`
      : `<div class="stat"><p class="k">Medias horas medidas</p><p class="n">${nf0.format(t.periodos)}</p><p class="d">de 2026</p></div>`,
    statNino(diag),
  ].join('');

  pintarMesAMes(seg, conf);
  pintarCoberturaVista(t.cobertura_pct, meta, vCob, rVivo, vivo);
  pintarCoberturaConf(seg, rVivo, vivo);
  pintarVivoConf(vivo, conf);
  pintarDiaADia(conf);
  pintarSesgoConf(conf);
  pintarNinoConf(diag);
  pintarMundo(conf);
  $('#cfPie').textContent = `Modelo: ${(modeloPorId(conf.modelo) || { nombre: conf.modelo }).nombre}. Prueba de 2026: del 1 de enero al ${fechaCorta((S.resumen && S.resumen.fechas_corte.prueba_hasta) || '2026-10-15')}, con todas las medias horas que tienen dato real. El registro en vivo usa otro modelo (${(vivo && vivo.modelo) || 'Chronos-2 ajustado'}): sus cifras van aparte.`;
}

// La cobertura del rango, junto al titular: la de la prueba de 2026 y la del registro en vivo, una al lado de la otra.
// Si en vivo el rango queda corto, el aviso va con el veredicto de la prueba, no debajo de un «Cumple lo que promete»
// que lo contradice
function pintarCoberturaVista(cubrio, meta, vCob, rVivo, vivo) {
  const vv = rVivo ? veredictoCobertura(rVivo.cobertura_pct, vivo.nivel_rango_pct) : null;
  const fila = (clase, titulo, pct, nivel, v, extra) => `<div class="cob-fila${clase}"><p class="k">${titulo}</p>`
    + `<p class="n">${nf1.format(pct)}<small> %</small></p><p class="d">rango del ${nf0.format(nivel)} %</p>`
    + `<p class="estado-meta ${v.clase}">${ICONO[v.clase]}${esc(capital(v.texto))}${extra}</p></div>`;
  let html = '<p class="cob-tit">¿El rango cumple lo que promete?</p>'
    + fila('', 'Prueba de 2026', cubrio, meta, vCob, '');
  if (vv) {
    const debe = vivo.nivel_rango_pct % 10 === 0 ? `: cubre ${nf0.format(rVivo.cobertura_pct / 10)} de cada 10, no ${vivo.nivel_rango_pct / 10}` : '';
    html += fila(vv.clase === 'bien' ? '' : ` aviso-vivo ${vv.clase}`, `En vivo, desde el ${esc(fechaCorta(rVivo.desde).replace(/ \d{4}$/, ''))}`, rVivo.cobertura_pct, vivo.nivel_rango_pct, vv, vv.clase === 'bien' ? '' : debe);
  }
  $('#cfCobVista').innerHTML = html;
}

function statNino(diag) {
  const regs = diag && diag.mae_por_regimen;
  if (!regs || !regs.length) return '';
  const peor = regs.reduce((a, b) => (b.modelo > a.modelo ? b : a));
  const gana = regs.filter((r) => r.modelo < r.referencia).length;
  return `<div class="stat"><p class="k">Con El Niño, donde más yerra</p><p class="n">${nf1.format(peor.modelo)}<small> MW</small></p>`
    + `<p class="d">${esc(REGIMEN[peor.regimen] || peor.regimen)} · le gana a la referencia en ${gana === regs.length ? `las ${regs.length}` : `${gana} de ${regs.length}`} fases</p></div>`;
}

function pintarMesAMes(seg, conf) {
  const cont = $('#cfMes');
  const meses = seg.meses;
  const ganados = meses.filter((x) => x.mae_modelo < x.mae_referencia).length;
  const peor = meses.reduce((a, b) => (b.mae_modelo > a.mae_modelo ? b : a));
  const hasta = S.resumen && S.resumen.fechas_corte.prueba_hasta;
  const ultimo = meses[meses.length - 1].mes;
  const parcial = hasta && hasta.slice(0, 7) === ultimo && Number(hasta.slice(8, 10)) < 28 ? ` ${capital(mesLargo(ultimo))} llega hasta el día ${Number(hasta.slice(8, 10))}.` : '';
  cont.innerHTML = `<p class="sub">Error medio absoluto en MW (menos es mejor), a ${C.horizonte === '1h' ? '1 hora' : '24 horas'}. Solo pronósticos que el modelo no vio al entrenar.</p>`
    + `<div class="leyenda"><span class="it"><span class="mk pron"></span>Pronóstico</span><span class="it"><span class="mk ref" style="border-top-style:solid"></span>Referencia (${esc((TITULO_REF[seg.referencia_nombre] || '').toLowerCase())})</span></div>`
    + '<div id="cfMesG" class="chart lienzo" style="min-height:220px"></div>'
    + `<p class="sub">Le ganó a la referencia en <b>${ganados} de ${meses.length}</b> meses. Peor mes: ${esc(mesLargo(peor.mes))} (${nf1.format(peor.mae_modelo)} MW).${esc(parcial)}</p>`
    + `<details class="datos"><summary>Ver la tabla mes a mes</summary><div class="tabla-scroll" tabindex="0" role="region" aria-label="Error mes a mes"><table class="t"><caption class="visually-hidden">Error medio y cobertura por mes de 2026</caption><thead><tr><th scope="col">Mes</th><th scope="col">Pronóstico (MW)</th><th scope="col">Referencia (MW)</th><th scope="col">¿Le ganó?</th><th scope="col">Cobertura</th><th scope="col">Medias horas</th></tr></thead><tbody>`
    + meses.map((x) => `<tr><th scope="row">${esc(capital(mesLargo(x.mes)))}</th><td>${nf1.format(x.mae_modelo)}</td><td>${nf1.format(x.mae_referencia)}</td><td>${x.mae_modelo < x.mae_referencia ? 'sí' : 'no'}</td><td>${nf1.format(x.cobertura_pct)} %</td><td>${nf0.format(x.periodos)}</td></tr>`).join('')
    + `<tr><th scope="row">2026</th><td><b>${nf1.format(seg.total.mae_modelo)}</b></td><td><b>${nf1.format(seg.total.mae_referencia)}</b></td><td></td><td><b>${nf1.format(seg.total.cobertura_pct)} %</b></td><td>${nf0.format(seg.total.periodos)}</td></tr></tbody></table></div></details>`;
  barrasMeses($('#cfMesG'), meses);
  void conf;
}

function barrasMeses(el, meses) {
  el._dibujar = () => barrasMeses(el, meses);
  const W = Math.max(280, el.clientWidth || 600);
  const H = W < 560 ? 200 : 230;
  const m = { l: 44, r: 8, t: 14, b: 28 };
  const tope = Math.max(...meses.map((x) => Math.max(x.mae_referencia, x.mae_modelo))) * 1.1;
  const y = (v) => m.t + (1 - v / tope) * (H - m.t - m.b);
  const bw = (W - m.l - m.r) / meses.length;
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Error medio por mes de 2026, modelo frente a la referencia">`;
  marcas(0, tope, 4).forEach((v) => {
    s += `<line class="${v === 0 ? 'g-eje' : 'g-rejilla'}" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${mw(v)}</text>`;
  });
  s += `<text class="g-texto" x="${m.l - 6}" y="10" text-anchor="end">MW</text>`;
  meses.forEach((x, j) => {
    const cx = m.l + j * bw + bw / 2;
    const w = Math.min(14, (bw - 10) / 2);
    s += `<rect class="g-barra-modelo" x="${(cx - w - 1).toFixed(1)}" y="${y(x.mae_modelo).toFixed(1)}" width="${w.toFixed(1)}" height="${(y(0) - y(x.mae_modelo)).toFixed(1)}" rx="3"/>`;
    s += `<rect class="g-barra-ref" x="${(cx + 1).toFixed(1)}" y="${y(x.mae_referencia).toFixed(1)}" width="${w.toFixed(1)}" height="${(y(0) - y(x.mae_referencia)).toFixed(1)}" rx="3"/>`;
    s += `<text class="g-texto" x="${cx.toFixed(1)}" y="${H - m.b + 16}" text-anchor="middle">${esc(mesCorto(x.mes))}</text>`;
  });
  el.innerHTML = `${s}</svg>`;
}

function pintarCoberturaConf(seg, rVivo, vivo) {
  const cont = $('#cfCob');
  const meta = seg.meta_cobertura_pct;
  const t = seg.total.cobertura_pct;
  const v = veredictoCobertura(t, meta);
  const fuera = seg.meses.filter((x) => Math.abs(x.cobertura_pct - meta) > 5);
  const cortos = seg.meses.filter((x) => x.cobertura_pct < meta - 2).map((x) => mesLargo(x.mes));
  const anchos = seg.meses.filter((x) => x.cobertura_pct > meta + 5).map((x) => mesLargo(x.mes));
  cont.innerHTML = `<p class="sub">Parte de las medias horas en que lo real cayó dentro del rango del ${nf0.format(meta)} %. Banda verde: de ${nf0.format(meta - 5)} a ${nf0.format(meta + 5)} %.</p>`
    + '<div id="cfCobG" class="chart lienzo" style="min-height:200px"></div>'
    + `<div class="veredicto ${v.clase}">${ICONO[v.clase]}<span>En el año cubrió el ${nf1.format(t)} %: ${esc(v.texto)}${v.porque ? `; ${esc(v.porque)}` : ''}.${cortos.length ? ` Quedó corto en ${esc(cortos.join(', '))}.` : ''}${anchos.length ? ` Fue más ancho de lo necesario en ${esc(anchos.join(', '))}.` : ''}</span></div>`
    + avisoVivoCob(rVivo, vivo)
    + `<p class="nota-pie">Puntos destacados: ${fuera.length ? 'meses a más de 5 puntos de la meta' : 'ninguno: todos los meses quedan a 5 puntos de la meta o menos'}.</p>`;
  lineaCobertura($('#cfCobG'), seg.meses, meta);
}

// En la tarjeta de cobertura, el registro en vivo al lado del veredicto de la prueba (si allí el rango queda corto)
function avisoVivoCob(rVivo, vivo) {
  const vv = rVivo ? veredictoCobertura(rVivo.cobertura_pct, vivo.nivel_rango_pct) : null;
  if (!vv || vv.clase === 'bien') return '';
  return `<div class="veredicto ${vv.clase} aviso-vivo" style="margin-top:8px">${ICONO[vv.clase]}<span>En vivo, desde el ${esc(fechaDiaMes(rVivo.desde))}, el rango del ${vivo.nivel_rango_pct} % cubrió el ${nf1.format(rVivo.cobertura_pct)} %: ${esc(vv.texto)}. Más abajo, en «El seguimiento en vivo».</span></div>`;
}

function lineaCobertura(el, meses, meta) {
  el._dibujar = () => lineaCobertura(el, meses, meta);
  const W = Math.max(240, el.clientWidth || 320);
  const H = 200;
  const m = { l: 38, r: 8, t: 10, b: 26 };
  const lo = Math.min(meta - 10, ...meses.map((x) => x.cobertura_pct)) - 1;
  const hi = Math.min(100, Math.max(meta + 10, ...meses.map((x) => x.cobertura_pct)) + 1);
  const y = (v) => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const x = (j) => m.l + (j + 0.5) * ((W - m.l - m.r) / meses.length);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Cobertura del rango por mes frente a la meta del ${meta} %">`;
  s += `<rect class="g-meta-zona" x="${m.l}" y="${y(meta + 5).toFixed(1)}" width="${W - m.l - m.r}" height="${(y(meta - 5) - y(meta + 5)).toFixed(1)}"/>`;
  marcas(lo, hi, 4).forEach((v) => {
    s += `<line class="g-rejilla" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${nf0.format(v)} %</text>`;
  });
  s += `<line class="g-meta" x1="${m.l}" x2="${W - m.r}" y1="${y(meta).toFixed(1)}" y2="${y(meta).toFixed(1)}"/>`;
  s += `<text class="g-texto fuerte" x="${W - m.r}" y="${(y(meta) - 5).toFixed(1)}" text-anchor="end">meta ${nf0.format(meta)} %</text>`;
  s += `<path class="g-linea-pron" d="${meses.map((k, j) => `${j ? 'L' : 'M'}${x(j).toFixed(1)},${y(k.cobertura_pct).toFixed(1)}`).join('')}"/>`;
  meses.forEach((k, j) => {
    const fuera = Math.abs(k.cobertura_pct - meta) > 5;
    s += `<circle class="${fuera ? 'g-punto-ojo' : 'g-punto'}" cx="${x(j).toFixed(1)}" cy="${y(k.cobertura_pct).toFixed(1)}" r="${fuera ? 5 : 3.5}"/>`;
    s += `<text class="g-texto" x="${x(j).toFixed(1)}" y="${H - m.b + 15}" text-anchor="middle">${esc(mesCorto(k.mes).charAt(0).toUpperCase())}</text>`;
  });
  el.innerHTML = `${s}</svg>`;
}

function tarjetaDia(k) {
  const sobre = k.error_pct > 0;
  const causa = k.causa_probable
    ? `<span class="causa">Causa probable, según el calendario: ${esc(k.causa_probable)}.</span>`
    : '<span class="causa sin">Causa: sin registrar (el calendario no la explica).</span>';
  return `<li class="dia"><div class="f"><span>${esc(capital(DIAS[partesFecha(k.fecha).dow]))} ${partesFecha(k.fecha).d} ${esc(MESES_CORTOS[partesFecha(k.fecha).m - 1])}</span>`
    + `<span class="e ${sobre ? 'sobre' : 'bajo'}">${sobre ? 'Sobrestimó' : 'Subestimó'} ${nf1.format(Math.abs(k.error_pct))} %</span></div>`
    + `<p>Pico real ${mw(k.pico_real)} MW a las ${esc(k.hora_real)}; se pronosticó ${mw(k.pico_pronostico)} MW a las ${esc(k.hora_pronostico)}.</p>${causa}</li>`;
}

function pintarVivoConf(vivo, conf) {
  const cont = $('#cfVivo');
  if (!vivo || !vivo.resumen || !vivo.resumen.length) {
    cont.innerHTML = '<p class="sub">Todavía no hay pronósticos en vivo verificados para esta área.</p>';
    return;
  }
  const g = (grupo, h) => vivo.resumen.find((r) => r.grupo === grupo && r.horizonte === h);
  const caja = (titulo, r, nota) => {
    if (!r) return `<div class="vivo-tipo"><span class="muted">${esc(titulo)}</span><b>—</b><span class="muted">${esc(nota)}</span></div>`;
    const v = veredictoCobertura(r.cobertura_pct, vivo.nivel_rango_pct);
    return `<div class="vivo-tipo"><span class="muted">${esc(titulo)} · ${plural(r.dias, 'día', 'días')}</span><b>${nf1.format(r.mae_modelo)} MW</b>`
      + `<span>frente a ${nf1.format(r.mae_referencia)} MW de repetir ${esc(REF_CORTA[r.referencia_nombre] || r.referencia_nombre)}</span>`
      + `<p class="estado-meta ${v.clase}" style="margin-top:6px">${ICONO[v.clase]}Rango del ${vivo.nivel_rango_pct} %: cubrió ${nf1.format(r.cobertura_pct)} %, ${esc(v.texto)}</p></div>`;
  };
  const vivo24 = g('en_vivo', '24h');
  const recon24 = g('reconstruido', '24h');
  const principal = vivo24 || recon24;
  const v = principal ? veredictoCobertura(principal.cobertura_pct, vivo.nivel_rango_pct) : null;
  const malos = (conf.dias_en_vivo || []).filter((k) => Math.abs(k.error_pct) > conf.umbral_pico_pct);
  const inicio = [recon24 && recon24.desde, vivo24 && vivo24.desde, vivo.primer_dia_en_vivo].filter(Boolean).sort()[0];
  let html = `<p class="sub">Desde el ${esc(fechaDiaMes(inicio || ''))}, ${esc(vivo.modelo || 'el modelo')}${/Chronos/.test(vivo.modelo || '') ? ', un modelo fundacional de series de tiempo,' : ''} pronostica cada día con la demanda del día anterior que publica el COES. `
    + `Lleva ${plural(vivo.dias_reconstruidos, 'día reconstruido', 'días reconstruidos')} (calculados después de conocerse el real, con los datos que habría tenido: no cuentan como en vivo) y ${plural(vivo.dias_en_vivo, 'día en vivo', 'días en vivo')}${vivo.primer_dia_en_vivo ? `, desde el ${esc(fechaDiaMes(vivo.primer_dia_en_vivo))}` : ''}: emitidos antes de su real, cada uno se verifica a la mañana siguiente.</p>`;
  html += `<div class="vivo-tipos">${caja('En vivo a 24 h', vivo24, 'Todavía ningún día con su real')}${caja('Reconstruido a 24 h', recon24, 'Sin días reconstruidos')}${caja('A 1 hora, siempre reconstruido', g('reconstruido', '1h'), 'Sin datos')}</div>`;
  if (v && v.clase !== 'bien') {
    html += `<div class="veredicto ${v.clase}" style="margin-top:12px">${ICONO[v.clase]}<span>El rango del ${vivo.nivel_rango_pct} % ${esc(v.texto)}. Entre el ${esc(fechaDiaMes(principal.desde))} y el ${esc(fechaDiaMes(principal.hasta))} cubrió el ${nf1.format(principal.cobertura_pct)} % de las medias horas a 24 h, cuando debería cubrir ${vivo.nivel_rango_pct / 10} de cada 10. Elia, en Bélgica, tiene el mismo problema con su banda del 80 %: cubrió entre 74 % y 79 % en 2024-2026.</span></div>`;
  }
  html += malos.length
    ? `<h3 class="sub" style="margin-top:16px"><b>${plural(malos.length, 'día pasó', 'días pasaron')} el ${nf0.format(conf.umbral_pico_pct)} % en el pico con el registro en vivo</b></h3><ul class="dias">${malos.map(tarjetaDia).join('')}</ul>`
    : `<p class="sub" style="margin-top:12px">Ningún día del registro en vivo pasó el ${nf0.format(conf.umbral_pico_pct)} % en el pico.</p>`;
  html += `<p class="enlaces"><a class="btn-enlace" href="${rutaDetalle(C.area, null, 'envivo')}">Ver el error de cada día en vivo</a></p>`;
  cont.innerHTML = html;
}

function pintarDiaADia(conf) {
  const cont = $('#cfDia');
  const dias = conf.dias;
  if (!dias.length) {
    cont.innerHTML = '<p class="sub">No hay días completos con real para medir el pico.</p>';
    return;
  }
  const u = conf.umbral_pico_pct;
  const meses = [...new Set(dias.map((k) => k.fecha.slice(0, 7)))];
  if (!meses.includes(C.mes)) C.mes = meses[meses.length - 1];
  const malos = dias.filter((k) => Math.abs(k.error_pct) > u);
  const sub = malos.filter((k) => k.error_pct < 0).length;
  const delMes = dias.filter((k) => k.fecha.startsWith(C.mes));
  const malosMes = delMes.filter((k) => Math.abs(k.error_pct) > u);
  const subMes = malosMes.filter((k) => k.error_pct < 0).length;
  cont.innerHTML = `<p class="sub">El pico pronosticado a 24 h frente al pico real de cada día. Arriba, sobrestimó; abajo, subestimó (lo más costoso: obliga a arrancar generación cara de urgencia). Líneas en ±${nf0.format(u)} %, como en el informe de PJM.</p>`
    + `<p class="sub">En todo 2026, <b>${malos.length} de ${dias.length} días</b> pasaron el ${nf0.format(u)} %: ${sub} subestimaciones y ${malos.length - sub} sobrestimaciones.</p>`
    + `<div class="meses-seg" role="group" aria-label="Mes">${meses.map((mes) => {
      const nm = dias.filter((k) => k.fecha.startsWith(mes) && Math.abs(k.error_pct) > u).length;
      return `<button type="button" data-cf-mes="${mes}" aria-pressed="${mes === C.mes}" aria-label="${esc(capital(mesLargo(mes)))}: ${plural(nm, 'día', 'días')} sobre el ${nf0.format(u)} %">${esc(capital(mesCorto(mes)))}${nm ? `<span class="n" aria-hidden="true">${nm}</span>` : ''}</button>`;
    }).join('')}</div>`
    + '<div id="cfDiaG" class="chart lienzo" style="min-height:200px"></div>'
    + `<p class="leyenda-dias"><span><i style="background:var(--crit)"></i>Subestimó más de ${nf0.format(u)} %</span><span><i style="background:var(--warn-mark)"></i>Sobrestimó más de ${nf0.format(u)} %</span><span><i style="background:var(--surface-3)"></i>Fin de semana</span></p>`
    + `<h3 class="sub" style="margin-top:16px"><b>${capital(mesLargo(C.mes))}: ${malosMes.length ? `${plural(malosMes.length, 'día pasó', 'días pasaron')} el ${nf0.format(u)} % en el pico${subMes ? ` (${subMes} subestimaciones)` : ''}` : `ningún día pasó el ${nf0.format(u)} % en el pico`}</b></h3>`
    + (malosMes.length ? `<ul class="dias">${malosMes.map(tarjetaDia).join('')}</ul>` : '')
    + `<details class="datos"><summary>Ver los ${malos.length} días de 2026 sobre el ${nf0.format(u)} %</summary><div class="tabla-scroll" tabindex="0" role="region" aria-label="Días con el error del pico sobre el umbral"><table class="t"><caption class="visually-hidden">Días de 2026 con el error del pico sobre el ${u} %</caption><thead><tr><th scope="col">Día</th><th scope="col">Pico real</th><th scope="col">Pronosticado</th><th scope="col">Error</th><th scope="col">Causa probable</th></tr></thead><tbody>`
    + malos.map((k) => `<tr><th scope="row">${esc(fechaNumerica(k.fecha))}</th><td>${mw(k.pico_real)} · ${esc(k.hora_real)}</td><td>${mw(k.pico_pronostico)} · ${esc(k.hora_pronostico)}</td><td>${k.error_pct > 0 ? '+' : '−'}${nf1.format(Math.abs(k.error_pct))} %</td><td style="text-align:left">${esc(k.causa_probable || 'sin registrar')}</td></tr>`).join('')
    + '</tbody></table></div></details>';
  barrasDias($('#cfDiaG'), delMes, u);
}

function barrasDias(el, dias, u) {
  el._dibujar = () => barrasDias(el, dias, u);
  const W = Math.max(280, el.clientWidth || 600);
  const movil = W < 560;
  const H = movil ? 190 : 220;
  const m = { l: 40, r: 8, t: 12, b: 26 };
  const lim = Math.max(6, Math.ceil(Math.max(...dias.map((k) => Math.abs(k.error_pct))) + 0.5));
  const y = (v) => m.t + (1 - (v + lim) / (2 * lim)) * (H - m.t - m.b);
  const bw = (W - m.l - m.r) / Math.max(dias.length, 1);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Error del pico de cada día de ${mesLargo(C.mes)}, en porcentaje">`;
  dias.forEach((k, j) => {
    const dow = partesFecha(k.fecha).dow;
    if (dow === 0 || dow === 6) s += `<rect class="g-fin-semana" x="${(m.l + j * bw).toFixed(1)}" y="${m.t}" width="${bw.toFixed(1)}" height="${H - m.t - m.b}"/>`;
  });
  [-lim, -u, 0, u, lim].forEach((v) => {
    s += `<line class="${v === 0 ? 'g-eje' : Math.abs(v) === u ? 'g-umbral' : 'g-rejilla'}" x1="${m.l}" x2="${W - m.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}"/>`;
    s += `<text class="g-texto" x="${m.l - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end">${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v)} %</text>`;
  });
  dias.forEach((k, j) => {
    const fuera = Math.abs(k.error_pct) > u;
    const x0 = m.l + j * bw + Math.max(1, bw * 0.18);
    const w = Math.max(3, bw * 0.64);
    const y1 = y(Math.max(0, k.error_pct));
    const y2 = y(Math.min(0, k.error_pct));
    s += `<rect class="g-dia${fuera ? (k.error_pct > 0 ? ' sobre' : ' bajo') : ''}" x="${x0.toFixed(1)}" y="${y1.toFixed(1)}" width="${w.toFixed(1)}" height="${Math.max(1, y2 - y1).toFixed(1)}" rx="2"><title>${esc(fechaNumerica(k.fecha))}: ${k.error_pct > 0 ? '+' : ''}${nf1.format(k.error_pct)} %</title></rect>`;
    const d = partesFecha(k.fecha).d;
    if (!movil || d % 5 === 0 || d === 1) s += `<text class="g-texto" x="${(m.l + j * bw + bw / 2).toFixed(1)}" y="${H - m.b + 15}" text-anchor="middle">${d}</text>`;
  });
  el.innerHTML = `${s}</svg>`;
}

function pintarSesgoConf(conf) {
  const sg = conf.sesgo;
  const sub = sg.subestima_pct;
  const equilibrado = Math.abs(sub - 50) <= 5;
  $('#cfSesgo').innerHTML = '<p class="sub">Subestimar cuesta más: obliga a arrancar generación cara de urgencia. Lo ideal es quedar cerca de la mitad.</p>'
    + `<div class="medidor" role="img" aria-label="Subestimó en ${nf1.format(sub)} % de las medias horas; la zona equilibrada va de 45 a 55 %"><span class="zona"></span><span class="aguja" style="left:${Math.max(0, Math.min(100, sub))}%"></span></div>`
    + '<div class="medidor-eje"><span>Siempre sobrestima</span><span>50 %</span><span>Siempre subestima</span></div>'
    + `<p class="sub"><b>Subestimó en ${nf1.format(sub)} %</b> de las ${nf0.format(sg.periodos)} medias horas de 2026 (todas, no una muestra), con un sesgo medio de ${sg.sesgo_mw >= 0 ? '+' : '−'}${nf1.format(Math.abs(sg.sesgo_mw))} MW (pronóstico − real). ${equilibrado ? 'Está en la zona equilibrada (45–55 %).' : 'Está fuera de la zona equilibrada (45–55 %).'}</p>`;
}

function pintarNinoConf(diag) {
  const cont = $('#cfNino');
  if (!diag || !diag.mae_por_regimen || !diag.mae_por_regimen.length) {
    cont.innerHTML = '<p class="sub">El error por fase de El Niño no está disponible para este modelo.</p>';
    return;
  }
  const regs = diag.mae_por_regimen;
  const tope = Math.max(...regs.map((r) => Math.max(r.modelo, r.referencia)));
  const peor = regs.reduce((a, b) => (b.modelo > a.modelo ? b : a));
  const gana = regs.filter((r) => r.modelo < r.referencia).length;
  cont.innerHTML = '<p class="sub">Error medio a 24 h en 2026 según la fase de El Niño costero del mes pronosticado.</p>'
    + regs.map((r) => `<div class="barra-cmp"><span>${esc(REGIMEN[r.regimen] || r.regimen)}</span><span class="pista"><i class="i-pron" style="width:${((100 * r.modelo) / tope).toFixed(1)}%"></i></span><b>${nf1.format(r.modelo)} MW</b></div>`).join('')
    + `<p class="sub">Donde más se equivoca: <b>${esc(REGIMEN[peor.regimen] || peor.regimen)}</b> (${nf1.format(peor.modelo)} MW). ${gana === regs.length ? `Le gana a la referencia en las ${regs.length} fases.` : `Le gana a la referencia en ${gana} de ${regs.length} fases.`}</p>`;
}

// Cifras citables de otros operadores, cada una con su fuente. No es una comparación de igual a igual.
const MUNDO = [
  { quien: 'REE (España peninsular)', que: 'Pronóstico diario, publicado el día anterior: suma de errores absolutos horarios entre la demanda del año. Lo audita el regulador (CNMC).', periodo: '2024', valor: '1.60 %', fuente: 'https://www.cnmc.es/sites/default/files/6336322.pdf', nombre: 'CNMC, RAP/DE/012/25' },
  { quien: 'REE (España peninsular)', que: 'El mismo indicador, auditado por la CNMC', periodo: '2025', valor: '1.69 %', fuente: 'https://www.cnmc.es/sites/default/files/6915601.pdf', nombre: 'CNMC, RAP/DE/016/26' },
  { quien: 'Elia (Bélgica, unos 9 GW de demanda media)', que: 'Pronóstico del día siguiente (18:00), error ponderado (WAPE). Su banda P10–P90 (80 %) cubrió 75.5 %. Cálculo propio con sus datos abiertos.', periodo: '2025', valor: '3.04 %', fuente: 'https://opendata.elia.be/explore/dataset/ods001/', nombre: 'Elia, datos abiertos ods001' },
  { quien: 'PJM (Estados Unidos)', que: 'Día siguiente, error medio horario (MAPE); publica cada mes los días que pasaron el 3 % en el pico, con su causa.', periodo: 'ene-2026', valor: '1.73 %', fuente: 'https://www.pjm.com/-/media/DotCom/committees-groups/committees/oc/2026/20260205/20260205-item-07---system-operations-report.pdf', nombre: 'PJM, informe de operación, feb-2026' },
  { quien: 'ISO-NE (Nueva Inglaterra)', que: 'Día siguiente (10:00), todas las horas (MAPE), contra una meta de 2.0 % con semáforo: ese tramo no la cumplió.', periodo: 'ene–may 2025', valor: '2.49 %', fuente: 'https://www.iso-ne.com/static-assets/documents/100024/june-2025-coo-report.pdf', nombre: 'ISO-NE, informe COO, jun-2025' },
  { quien: 'NESO (Gran Bretaña, unos 26 GW)', que: 'Día siguiente, cada 30 min (MAPE). Cálculo propio con su archivo de desempeño.', periodo: '2025', valor: '2.69 %', fuente: 'https://www.neso.energy/data-portal/day-ahead-half-hourly-demand-forecast-performance', nombre: 'NESO, portal de datos' },
];

function pintarMundo(conf) {
  const area = nombreArea(C.area);
  const hasta = S.resumen && S.resumen.fechas_corte.prueba_hasta;
  const filas = MUNDO.map((f) => `<tr><td>${esc(f.quien)}</td><td>${esc(f.que)} <a href="${f.fuente}" rel="noopener" target="_blank">${esc(f.nombre)}</a></td><td>${esc(f.periodo)}</td><td class="n">${esc(f.valor)}</td></tr>`).join('');
  const nuestro = `<tr class="nuestro"><td><b>Este modelo · ${esc(area)}</b></td><td>${C.horizonte === '1h' ? '1 hora' : '24 horas'} exactas, cada 30 min, sin clima pronosticado. WAPE (como REE y Elia) y MAPE (como PJM, ISO-NE y NESO).</td><td>2026 (ene–${hasta ? esc(fechaCorta(hasta).replace(/ \d{4}$/, '')) : 'oct'})</td><td class="n">WAPE ${nf2(conf.wape_pct)} %<br>MAPE ${nf2(conf.mape_pct)} %</td></tr>`;
  $('#cfMundo').innerHTML = `<div class="veredicto ojo">${ICONO.info}<span>No es una comparación de igual a igual: cambian la métrica, el horizonte y el tamaño del sistema (un área del SEIN es mucho más chica y ruidosa que un país), y 2026 ya se usó para elegir el modelo. Sirve para saber en qué orden de magnitud se mueven los operadores que publican su error.</span></div>`
    + `<div class="tabla-scroll" tabindex="0" role="region" aria-label="Error de otros operadores" style="max-height:none;margin-top:12px"><table class="cmp"><caption class="visually-hidden">Error del pronóstico que publican otros operadores y el de este modelo</caption><thead><tr><th scope="col">Quién</th><th scope="col">Qué se mide y fuente</th><th scope="col">Periodo</th><th scope="col" style="text-align:right">Error</th></tr></thead><tbody>${filas}${nuestro}</tbody></table></div>`
    + '<p class="nota-pie">Fuentes consultadas el 13 de noviembre de 2026. No encontramos que el COES publique el error de su pronóstico ni de su programa.</p>';
}

const nf2 = (x) => new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(x);

// ---- La pantalla: su HTML y sus eventos ---------------------------------------------------------------------

const HTML_CONFIANZA = `
  <div class="conf-cab">
    <nav class="seg" id="cfAreas" aria-label="Área"></nav>
    <div class="seg" role="group" aria-label="Con cuánta anticipación">
      <button type="button" data-cf-horizonte="1h" aria-pressed="false">A 1 hora</button>
      <button type="button" data-cf-horizonte="24h" aria-pressed="true">A 24 horas</button>
    </div>
  </div>
  <h1 id="cfTitular" class="titular" tabindex="-1">Calculando la confianza…</h1>
  <aside id="cfCobVista" class="cob-vista" aria-label="Cobertura del rango"></aside>
  <p id="cfLead" class="lead"></p>
  <section id="cfStats" class="stats" aria-label="Cifras de 2026"></section>
  <div class="grid-conf">
    <section class="card c8" aria-labelledby="cfMesTit">
      <div class="card-h"><h2 id="cfMesTit">Error mes a mes en 2026</h2></div>
      <div class="card-b" id="cfMes"><p class="cargando-bloque">Calculando…</p></div>
    </section>
    <section class="card c4" aria-labelledby="cfCobTit">
      <div class="card-h"><h2 id="cfCobTit">¿El rango cumple lo que promete?</h2></div>
      <div class="card-b" id="cfCob"><p class="cargando-bloque">Calculando…</p></div>
    </section>
    <section class="card c12" aria-labelledby="cfVivoTit" id="cfVivoCard">
      <div class="card-h"><h2 id="cfVivoTit">El seguimiento en vivo</h2></div>
      <div class="card-b" id="cfVivo"><p class="cargando-bloque">Cargando el registro en vivo…</p></div>
    </section>
    <section class="card c12" aria-labelledby="cfDiaTit">
      <div class="card-h"><h2 id="cfDiaTit">Día a día: el error del pico</h2></div>
      <div class="card-b" id="cfDia"><p class="cargando-bloque">Calculando…</p></div>
    </section>
    <section class="card c6" aria-labelledby="cfSesgoTit">
      <div class="card-h"><h2 id="cfSesgoTit">¿Hacia dónde se equivoca?</h2></div>
      <div class="card-b" id="cfSesgo"></div>
    </section>
    <section class="card c6" aria-labelledby="cfNinoTit">
      <div class="card-h"><h2 id="cfNinoTit">Con El Niño</h2></div>
      <div class="card-b" id="cfNino"><p class="cargando-bloque">Calculando…</p></div>
    </section>
    <section class="card c12 mundo" aria-labelledby="cfMundoTit">
      <div class="card-h"><h2 id="cfMundoTit">Para poner la cifra en contexto</h2></div>
      <div class="card-b" id="cfMundo"></div>
    </section>
  </div>
  <p class="pie-nota" id="cfPie"></p>`;

function conectarConfianza() {
  $$('[data-cf-horizonte]').forEach((b) => b.addEventListener('click', () => {
    if (C.horizonte === b.dataset.cfHorizonte) return;
    C.horizonte = b.dataset.cfHorizonte;
    history.replaceState(null, '', `#/confianza/${encodeURIComponent(C.area)}?horizonte=${C.horizonte}`);
    mostrarConfianza(C.area, new URLSearchParams({ horizonte: C.horizonte }));
  }));
  $('#cfDia').addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-cf-mes]');
    if (!b || !C.datos) return;
    C.mes = b.dataset.cfMes;
    pintarDiaADia(C.datos.conf);
    const elegido = $(`[data-cf-mes="${C.mes}"]`);
    if (elegido) elegido.focus();
  });
}

// La llama cargarPantalla (app.js) cuando llegaron este código y sus estilos
function iniciarConfianza() {
  $('#vistaConfianza').innerHTML = HTML_CONFIANZA;
  conectarConfianza();
}
