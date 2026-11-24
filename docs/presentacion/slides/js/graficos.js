// Gráficos del deck con D3 (v7, vendorizado en js/d3.v7.min.js para que el deck funcione sin red).
//
// Cada gráfico es un <div data-grafico="nombre"> en index.qmd. Los datos salen de window.DATOS (datos.js, que
// escribe datos.py desde las tablas de los notebooks), nunca de cifras escritas aquí. Los colores y las fuentes los
// pone custom.scss con clases (s-ref, s-rf, s-xgb, s-comb, …): aquí no hay un solo color.
//
// Ciclo de vida, atado a reveal.js:
//   entrar()  la diapositiva aparece: se anima desde cero, en menos de un segundo y medio
//   paso(n)   n = el mayor data-paso de los fragmentos visibles de la diapositiva
//   salir()   la diapositiva se va: se detienen las transiciones
//   final()   ?print-pdf: el estado completo, sin animar
(function () {
  "use strict";

  // ------------------------------------------------------------------ formato, como en el informe
  const MENOS = "−";
  const dec = (x, d = 1) => d3.format(`,.${d}f`)(x).replace("-", MENOS);
  const miles = (x) => d3.format(",.0f")(x);
  const pct = (x, d = 1) => `${dec(x, d)} %`;
  const AREAS = ["Norte", "Centro", "Sur"];
  const HORIZONTE = { "1h": "A 1 hora", "24h": "A 24 horas" };
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const DUR = 900;

  function lienzo(el, ancho, alto, clase, etiqueta) {
    return d3.select(el).append("svg")
      .attr("viewBox", `0 0 ${ancho} ${alto}`)
      .attr("class", `g ${clase}`)
      .attr("role", "img")
      .attr("aria-label", etiqueta || "");
  }
  const animar = (sel, si, dur = DUR, retraso = 0) =>
    (si ? sel.transition().duration(dur).delay(retraso).ease(d3.easeCubicOut) : sel);

  // Una línea que se dibuja de izquierda a derecha
  function trazar(path, si, dur = 1100, retraso = 0) {
    path.interrupt();
    if (!si) { path.attr("stroke-dasharray", null).attr("stroke-dashoffset", null); return; }
    const L = path.node().getTotalLength();
    path.attr("stroke-dasharray", `${L} ${L}`).attr("stroke-dashoffset", L)
      .transition().delay(retraso).duration(dur).ease(d3.easeCubicInOut).attr("stroke-dashoffset", 0)
      .on("end", () => path.attr("stroke-dasharray", null));
  }

  function leyenda(svg, x, y, items, paso = 230) {
    const g = svg.append("g").attr("class", "g-ley").attr("transform", `translate(${x},${y})`);
    const it = g.selectAll("g").data(items).join("g")
      .attr("transform", (d, i) => `translate(${d.x !== undefined ? d.x : i * paso},0)`);
    it.each(function (d) {
      const s = d3.select(this);
      if (d.tipo === "linea") {
        s.append("line").attr("class", d.clase).attr("x1", 0).attr("x2", 30).attr("y1", -6).attr("y2", -6);
      } else if (d.tipo === "aro") {
        s.append("circle").attr("class", `p-vacio ${d.clase}`).attr("cx", 9).attr("cy", -6).attr("r", 7);
      } else if (d.tipo === "punto") {
        s.append("circle").attr("class", d.clase).attr("cx", 9).attr("cy", -6).attr("r", 8);
      } else {
        s.append("rect").attr("class", d.clase).attr("y", -15).attr("width", 18).attr("height", 18).attr("rx", 3);
      }
      s.append("text").attr("x", d.tipo === "linea" ? 40 : 28).text(d.texto);
    });
    return it;
  }

  // ------------------------------------------------------------------ (1) un día del Centro, como lo muestra Curva
  // El combinado a 24 horas: el pronóstico que se emitió un día antes, su rango del 90 % y lo que pasó. La
  // semana pasada a la misma hora va como referencia. Se dibuja primero el pronóstico y después lo real, en el
  // orden en que se conocieron.
  function dia(el) {
    const D = window.DATOS.dia;
    const P = D.puntos;
    const ancho = 1180, alto = 470, m = { t: 30, r: 330, b: 50, l: 78 };
    const svg = lienzo(el, ancho, alto, "g-dia", "Pronóstico frente a lo real de un día del Centro");
    const x = d3.scalePoint(P.map((p) => p.h), [m.l, ancho - m.r]);
    const ys = P.flatMap((p) => [p.bajo, p.alto, p.real, p.semana]);
    const y = d3.scaleLinear([d3.min(ys) * 0.985, d3.max(ys) * 1.01], [alto - m.b, m.t]).nice();
    svg.append("g").attr("class", "g-eje").attr("transform", `translate(0,${alto - m.b})`)
      .call(d3.axisBottom(x).tickValues(P.map((p) => p.h).filter((h) => h.endsWith(":00") && +h.slice(0, 2) % 3 === 0))
        .tickSizeOuter(0));
    svg.append("g").attr("class", "g-eje g-rejilla").attr("transform", `translate(${m.l},0)`)
      .call(d3.axisLeft(y).ticks(5).tickFormat(miles).tickSize(-(ancho - m.l - m.r)));
    svg.append("text").attr("class", "g-et").attr("x", m.l - 64).attr("y", m.t - 10).text("MW");

    const banda = svg.append("path").attr("class", "d-banda")
      .attr("d", d3.area().x((p) => x(p.h)).y0((p) => y(p.bajo)).y1((p) => y(p.alto))(P));
    const linea = (campo) => d3.line().x((p) => x(p.h)).y((p) => y(p[campo]))(P);
    const semana = svg.append("path").attr("class", "d-semana").attr("d", linea("semana"));
    const pred = svg.append("path").attr("class", "d-pred").attr("d", linea("pred"));
    const real = svg.append("path").attr("class", "d-real").attr("d", linea("real"));

    // La hora del recorrido de la demo: lo que dijimos y lo que fue
    const H = D.destacado;
    const marca = svg.append("g");
    marca.append("line").attr("class", "d-marca").attr("x1", x(H.h)).attr("x2", x(H.h)).attr("y1", m.t).attr("y2", alto - m.b);
    marca.append("circle").attr("class", "d-punto-pred").attr("cx", x(H.h)).attr("cy", y(H.pred)).attr("r", 8);
    marca.append("circle").attr("class", "d-punto-real").attr("cx", x(H.h)).attr("cy", y(H.real)).attr("r", 8);
    const caja = marca.append("g").attr("transform", `translate(${ancho - m.r + 26},${m.t + 6})`);
    caja.append("text").attr("class", "g-titulo").attr("y", 0).text(`A las ${H.h}`);
    caja.append("text").attr("class", "g-et").attr("y", 34).text("un día antes dijimos");
    caja.append("text").attr("class", "g-valor t-rf").attr("y", 66).text(`${miles(H.pred)} MW`);
    caja.append("text").attr("class", "g-et").attr("y", 94).text(`rango del ${D.nivel} %: ${miles(H.bajo)} a ${miles(H.alto)}`);
    caja.append("text").attr("class", "g-et").attr("y", 134).text("y fue");
    caja.append("text").attr("class", "g-valor").attr("y", 166).text(`${miles(H.real)} MW`);
    caja.append("text").attr("class", "g-et").attr("y", 214).text("error medio del día:");
    caja.append("text").attr("class", "g-et").attr("y", 240)
      .call((t) => {
        t.append("tspan").attr("class", "t-rf").attr("font-weight", 700).text(`${dec(D.mae)} MW`);
        t.append("tspan").text(" el modelo");
      });
    caja.append("text").attr("class", "g-et").attr("y", 266)
      .call((t) => {
        t.append("tspan").attr("class", "t-ref").attr("font-weight", 700).text(`${dec(D.mae_semana)} MW`);
        t.append("tspan").text(" la semana pasada");
      });

    const ley = leyenda(svg, m.l, alto - 6, [
      { tipo: "linea", clase: "d-real", texto: "lo que pasó", x: 0 },
      { tipo: "linea", clase: "d-pred", texto: "pronóstico de un día antes", x: 170 },
      { tipo: "caja", clase: "d-banda", texto: `rango del ${D.nivel} %`, x: 460 },
      { tipo: "linea", clase: "d-semana", texto: "la semana pasada", x: 640 },
    ]);
    ley.attr("opacity", 1);
    svg.select(".g-ley").attr("transform", `translate(${m.l},${alto - 2})`);
    svg.select(".g-eje").raise();

    function mostrar(si) {
      banda.interrupt().attr("opacity", si ? 0 : 1);
      animar(banda, si, 700).attr("opacity", 1);
      trazar(pred, si, 1000);
      semana.interrupt().attr("opacity", si ? 0 : 1);
      animar(semana, si, 500, 900).attr("opacity", 1);
      trazar(real, si, 1100, 600);
      marca.interrupt().attr("opacity", si ? 0 : 1);
      animar(marca, si, 400, 1500).attr("opacity", 1);
    }
    return { entrar() { mostrar(true); }, final() { mostrar(false); }, salir() { svg.selectAll("*").interrupt(); } };
  }

  // ------------------------------------------------------------------ (2) la prueba de 2026 por área y horizonte
  // Cada celda: la mejor de las tres reglas simples (= 100) y los modelos, a la misma escala relativa. Sobre la
  // regla, su MAE en MW; sobre cada modelo, cuánto menos error tiene. Pasos: 0 la regla y el Random Forest,
  // 1 + XGBoost, 2 + el combinado (la extensión de la diapositiva de los fundacionales).
  function prueba(el) {
    const D = window.DATOS.prueba;
    const ancho = 1180, alto = 500, izq = 150, arriba = 92, filaH = 196;
    const colW = (ancho - izq) / 3;
    const svg = lienzo(el, ancho, alto, "g-prueba", "Error de 2026 por área y horizonte frente a la mejor referencia");
    const series = [
      { k: "ref", clase: "s-ref", paso: 0 },
      { k: "rf", clase: "s-rf", paso: 0 },
      { k: "xgb", clase: "s-xgb", paso: 1 },
      { k: "comb", clase: "s-comb", paso: 2 },
    ];
    const bw = 54, gap = 28, grupo = series.length * bw + (series.length - 1) * gap;
    const hmax = 118;
    const ley = leyenda(svg, izq + 10, 30, [
      { clase: "s-ref", texto: "mejor de las tres reglas simples", x: 0 },
      { clase: "s-rf", texto: "Random Forest (elegido)", x: 330 },
      { clase: "s-xgb", texto: "XGBoost global", x: 590 },
      { clase: "s-comb", texto: "combinado (extensión)", x: 770 },
    ]);
    AREAS.forEach((a, j) => svg.append("text").attr("class", "g-titulo").attr("text-anchor", "middle")
      .attr("x", izq + colW * j + colW / 2).attr("y", arriba - 18).text(a));
    const barras = [];
    const textos = [];
    ["1h", "24h"].forEach((h, i) => {
      const y0 = arriba + i * filaH + 140; // base de las barras
      svg.append("text").attr("class", "g-titulo").attr("x", 0).attr("y", y0 - 60).text(HORIZONTE[h]);
      AREAS.forEach((a, j) => {
        const d = D.find((c) => c.horizonte === h && c.area === a);
        const x0 = izq + colW * j + (colW - grupo) / 2;
        const g = svg.append("g");
        g.append("line").attr("class", "b-cero").attr("x1", x0 - 10).attr("x2", x0 + grupo + 10).attr("y1", y0).attr("y2", y0);
        series.forEach((s, k) => {
          const rel = d[s.k] / d.ref;
          const xb = x0 + k * (bw + gap);
          const r = g.append("rect").attr("class", s.clase).attr("x", xb).attr("width", bw).attr("rx", 3)
            .datum({ paso: s.paso, y: y0 - hmax * rel, h: hmax * rel, base: y0 });
          barras.push(r);
          const etiqueta = s.k === "ref" ? `${dec(d.ref)} MW` : MENOS + pct(d[`mejora_${s.k}`]);
          const t = g.append("text").attr("text-anchor", "middle").attr("x", xb + bw / 2).attr("y", y0 - hmax * rel - 9)
            .attr("class", s.k === "ref" ? "g-num t-ref" : s.k === "rf" ? "g-valor t-rf" : s.k === "comb" ? "g-et t-comb" : "g-et")
            .style("font-size", s.k === "rf" ? "20px" : s.k === "ref" ? "15px" : "16px")
            .style("font-weight", s.k === "comb" ? 700 : null)
            .text(etiqueta).datum({ paso: s.paso });
          textos.push(t);
        });
        g.append("text").attr("class", "g-et g-suave").attr("x", x0 + bw / 2).attr("y", y0 + 22)
          .attr("text-anchor", "middle").style("font-size", "15px").text(d.referencia.toLowerCase());
      });
    });
    let actual = -1;
    function mostrar(n, si) {
      barras.forEach((r) => {
        const d = r.datum();
        const ver = d.paso <= n;
        if (!ver) { r.interrupt().attr("y", d.base).attr("height", 0); return; }
        if (si && d.paso > actual) r.interrupt().attr("y", d.base).attr("height", 0);
        animar(r, si && d.paso > actual, 800).attr("y", d.y).attr("height", d.h);
      });
      textos.forEach((t) => {
        const ver = t.datum().paso <= n;
        if (!ver) { t.interrupt().attr("opacity", 0); return; }  // lo que todavía no toca, se oculta de inmediato
        if (si && t.datum().paso > actual) t.interrupt().attr("opacity", 0);
        animar(t, si && t.datum().paso > actual, 300, 600).attr("opacity", 1);
      });
      ley.attr("opacity", (d, i) => (series[i].paso <= n ? 1 : 0.25));
      actual = n;
    }
    return {
      entrar() { actual = -1; mostrar(0, true); },
      paso(n) { if (n !== actual) mostrar(n, true); },
      final() { actual = -1; mostrar(2, false); },
      salir() { svg.selectAll("*").interrupt(); },
    };
  }

  // ------------------------------------------------------------------ (3) mes a mes en 2026
  // Seis paneles (área × horizonte): el MAE mensual del modelo fijo y el de la mejor referencia. Pasos: 1 el Norte a
  // 1 hora (la mejora sube con El Niño), 2 el Sur a 24 horas (el único mes que pierde).
  function mensual(el) {
    const D = window.DATOS.mensual;
    const ancho = 1180, alto = 500, izq = 128, arriba = 70, gx = 26, gy = 46;
    const pw = (ancho - izq - 2 * gx) / 3, ph = (alto - arriba - gy - 36) / 2;
    const m = { t: 10, r: 8, b: 26, l: 56 };
    const svg = lienzo(el, ancho, alto, "g-mensual", "Error mes a mes de 2026 frente a la mejor referencia");
    leyenda(svg, izq, 26, [
      { tipo: "linea", clase: "m-modelo", texto: "Random Forest, fijo desde 2025", x: 0 },
      { tipo: "linea", clase: "m-ref", texto: "mejor de las tres reglas simples", x: 360 },
    ]);
    const paneles = D.paneles.map((p) => {
      const i = p.horizonte === "1h" ? 0 : 1, j = AREAS.indexOf(p.area);
      const x0 = izq + j * (pw + gx), y0 = arriba + i * (ph + gy);
      const g = svg.append("g").attr("transform", `translate(${x0},${y0})`);
      if (i === 0) g.append("text").attr("class", "g-titulo").attr("x", m.l).attr("y", -2).text(p.area);
      if (j === 0) svg.append("text").attr("class", "g-titulo").attr("x", 0).attr("y", y0 + ph / 2).text(HORIZONTE[p.horizonte]);
      const meses = p.meses.map((d) => ({ ...d, n: +d.mes.slice(5, 7) }));
      const x = d3.scaleLinear([1, meses.length], [m.l + 8, pw - m.r - 8]);
      const y = d3.scaleLinear([0, d3.max(meses, (d) => Math.max(d.modelo, d.ref)) * 1.12], [ph - m.b, m.t + 12]).nice();
      g.append("g").attr("class", "g-eje g-rejilla").attr("transform", `translate(${m.l},0)`)
        .call(d3.axisLeft(y).ticks(3).tickSize(-(pw - m.l - m.r)).tickFormat((v) => miles(v)));
      g.append("g").attr("class", "g-eje").attr("transform", `translate(0,${ph - m.b})`)
        .call(d3.axisBottom(x).tickValues(meses.map((d) => d.n)).tickFormat((n) => MESES[n - 1].slice(0, 1).toUpperCase())
          .tickSizeOuter(0));
      const linea = (campo) => d3.line().x((d) => x(d.n)).y((d) => y(d[campo]));
      const ref = g.append("path").attr("class", "m-ref").attr("d", linea("ref")(meses));
      const mod = g.append("path").attr("class", "m-modelo").attr("d", linea("modelo")(meses));
      const puntos = g.selectAll("circle").data(meses).join("circle").attr("class", "s-rf")
        .attr("cx", (d) => x(d.n)).attr("cy", (d) => y(d.modelo)).attr("r", 4.5);
      const notas = g.append("g").attr("opacity", 0);
      return { p, g, ref, mod, puntos, notas, x, y, meses, i, j };
    });

    // Las dos lecturas que pide el guion
    const norte = paneles.find((q) => q.p.horizonte === "1h" && q.p.area === "Norte");
    const sur = paneles.find((q) => q.p.horizonte === "24h" && q.p.area === "Sur");
    const icen = window.DATOS.mensual.icen;
    {
      const ene = norte.meses[0], sep = norte.meses.find((d) => d.n === 9);
      norte.notas.append("text").attr("class", "g-valor t-rf").attr("x", norte.x(ene.n)).attr("y", norte.y(ene.modelo) - 12)
        .style("font-size", "19px").text(pct(ene.mejora));
      norte.notas.append("text").attr("class", "g-valor t-rf").attr("text-anchor", "middle").attr("x", norte.x(sep.n))
        .attr("y", norte.y(sep.modelo) - 12).style("font-size", "19px").text(pct(sep.mejora));
      const ic0 = icen[0], icn = icen[icen.length - 1];
      norte.notas.append("text").attr("class", "g-et").attr("x", norte.x(1)).attr("y", norte.y.range()[1] - 2)
        .style("font-size", "15px")
        .text(`menos error · ICEN ${dec(ic0.icen, 2)} en ${MESES[+ic0.mes.slice(5) - 1]} → ${dec(icn.icen, 2)} en ${MESES[+icn.mes.slice(5) - 1]}`);
    }
    {
      const oct = sur.meses.find((d) => d.mejora < 0);
      sur.notas.append("circle").attr("class", "m-marca").attr("cx", sur.x(oct.n)).attr("cy", sur.y(oct.modelo)).attr("r", 14);
      sur.notas.append("text").attr("class", "g-valor t-ref").attr("text-anchor", "end").attr("x", sur.x(oct.n) - 20)
        .attr("y", sur.y(oct.modelo) - 18).style("font-size", "19px")
        .text(`${MESES[oct.n - 1]}: ${pct(oct.mejora)}`);
    }

    let actual = -1;
    function mostrar(n, si, dibujar) {
      paneles.forEach((q) => {
        const foco = n === 1 ? q === norte : n === 2 ? q === sur : true;
        animar(q.g.interrupt(), si, 400).attr("opacity", foco ? 1 : 0.22);
        animar(q.notas.interrupt(), si, 400, 200).attr("opacity", (n === 1 && q === norte) || (n === 2 && q === sur) ? 1 : 0);
        if (dibujar) {
          trazar(q.ref, si, 1000, 100 * q.j);
          trazar(q.mod, si, 1000, 100 * q.j + 200);
          q.puntos.interrupt().attr("opacity", si ? 0 : 1);
          animar(q.puntos, si, 300, 1000 + 100 * q.j).attr("opacity", 1);
        }
      });
      actual = n;
    }
    return {
      entrar() { mostrar(0, true, true); },
      paso(n) { if (n !== actual) mostrar(n, true, false); },
      final() {
        mostrar(0, false, true);
        norte.notas.attr("opacity", 1);
        sur.notas.attr("opacity", 1);
      },
      salir() { svg.selectAll("*").interrupt(); },
    };
  }

  // ------------------------------------------------------------------ (4) Tetuán y Ceuta frente a las referencias fuertes
  // Tetuán (MAE en kW, prueba de 2017): el modelo frente a la mejor de las tres reglas (paso 0) y frente al promedio
  // de los deltas diario y semanal (paso 1). Ceuta (MAPE de cada verano): el modelo sin verano frente al delta
  // semanal (paso 2). Más a la izquierda, menos error.
  function reanalisis(el) {
    const R = window.DATOS.reanalisis;
    const ancho = 1180, alto = 450;
    const svg = lienzo(el, ancho, alto, "g-reanalisis", "Tetuán y Ceuta frente a las referencias fuertes");

    // Tetuán
    const T = { x0: 110, x1: 560, y0: 90, fila: 98 };
    const gt = svg.append("g");
    gt.append("text").attr("class", "g-titulo").attr("x", 0).attr("y", 26).text("Tetuán · MAE de la prueba de 2017");
    const xt = d3.scaleLinear([300, d3.max(R.tetuan, (z) => z.historica) * 1.04], [T.x0, T.x1]).nice();
    gt.append("g").attr("class", "g-eje g-rejilla").attr("transform", `translate(0,${T.y0 + 3 * T.fila - 40})`)
      .call(d3.axisBottom(xt).ticks(5).tickFormat(miles).tickSize(-(3 * T.fila - 20)));
    const filasT = R.tetuan.map((z, i) => {
      const y = T.y0 + i * T.fila;
      const g = gt.append("g");
      g.append("text").attr("class", "g-titulo").attr("x", 0).attr("y", y + 7).text(z.zona);
      const lineaH = g.append("line").attr("class", "r-linea").attr("y1", y).attr("y2", y)
        .attr("x1", xt(z.modelo)).attr("x2", xt(z.historica));
      const lineaD = g.append("line").attr("class", "r-linea").attr("y1", y + 0).attr("y2", y + 0)
        .attr("x1", xt(Math.min(z.modelo, z.deltas))).attr("x2", xt(Math.max(z.modelo, z.deltas))).attr("opacity", 0);
      const hist = g.append("circle").attr("class", "r-hueco s-ref").attr("cx", xt(z.historica)).attr("cy", y).attr("r", 10);
      g.append("text").attr("class", "g-et g-suave").attr("x", xt(z.historica)).attr("y", y - 20).attr("text-anchor", "middle")
        .style("font-size", "15px").text(z.nombre_historica);
      const deltas = g.append("circle").attr("class", "s-ref").attr("cx", xt(z.deltas)).attr("cy", y).attr("r", 10).attr("opacity", 0);
      const modelo = g.append("circle").attr("class", "s-rf").attr("cx", xt(z.modelo)).attr("cy", y).attr("r", 10)
        .style("stroke", "#FFFFFF").style("stroke-width", 2);
      const tH = g.append("text").attr("class", "g-valor t-rf").attr("x", xt(z.historica) + 22).attr("y", y + 8)
        .style("font-size", "20px").text(`${MENOS}${pct(z.frente_historica)}`);
      const gana = z.frente_deltas > 0;
      const tD = g.append("text").attr("class", `g-valor ${gana ? "t-rf" : "t-ref"}`).attr("x", T.x1 + 16).attr("y", y + 8)
        .style("font-size", "20px").attr("opacity", 0)
        .text(`${gana ? "gana" : "pierde"} por ${pct(Math.abs(z.frente_deltas))}`);
      return { lineaH, lineaD, hist, deltas, modelo, tH, tD };
    });
    const leyT = leyenda(svg, 0, alto - 12, [
      { tipo: "punto", clase: "s-rf", texto: "el modelo", x: 0 },
      { tipo: "aro", clase: "s-ref", texto: "mejor de las tres reglas", x: 130 },
      { tipo: "punto", clase: "s-ref", texto: "promedio de los deltas", x: 400 },
    ]);
    gt.append("text").attr("class", "g-et g-suave").attr("x", T.x1).attr("y", T.y0 + 3 * T.fila + 8)
      .attr("text-anchor", "end").style("font-size", "15px").text("kW · más a la izquierda, menos error");

    // Ceuta
    const C = { x0: 880, x1: 1160, y0: 90, fila: 58 };
    const gc = svg.append("g").attr("opacity", 0);
    gc.append("text").attr("class", "g-titulo").attr("x", 800).attr("y", 26).text("Ceuta · MAPE del verano (%)");
    const vals = R.ceuta.flatMap((c) => [c.modelo, c.delta]);
    const xc = d3.scaleLinear([d3.min(vals) * 0.9, d3.max(vals) * 1.04], [C.x0, C.x1]).nice();
    gc.append("g").attr("class", "g-eje g-rejilla").attr("transform", `translate(0,${C.y0 + 5 * C.fila - 30})`)
      .call(d3.axisBottom(xc).ticks(4).tickFormat((v) => dec(v, 1)).tickSize(-(5 * C.fila - 10)));
    R.ceuta.forEach((c, i) => {
      const y = C.y0 + i * C.fila;
      gc.append("text").attr("class", "g-titulo").attr("x", 800).attr("y", y + 7).text(c.verano);
      gc.append("line").attr("class", "r-linea").attr("y1", y).attr("y2", y).attr("x1", xc(c.delta)).attr("x2", xc(c.modelo));
      gc.append("circle").attr("class", "s-ref").attr("cx", xc(c.delta)).attr("cy", y).attr("r", 10);
      gc.append("circle").attr("class", "s-rf").attr("cx", xc(c.modelo)).attr("cy", y).attr("r", 10);
    });
    gc.append("text").attr("class", "g-et").attr("x", 800).attr("y", alto - 12)
      .call((t) => {
        t.append("tspan").attr("class", "t-ref").attr("font-weight", 700).text("delta semanal");
        t.append("tspan").text(` gana ${R.ceuta_gana_delta} de ${R.ceuta.length} veranos`);
      });

    let actual = -1;
    function mostrar(n, si) {
      filasT.forEach((f, i) => {
        animar(f.lineaH.interrupt(), si, 400).attr("opacity", n >= 1 ? 0 : 1);
        animar(f.tH.interrupt(), si, 400).attr("opacity", n >= 1 ? 0 : 1);
        animar(f.hist.interrupt(), si, 400).attr("opacity", n >= 1 ? 0.35 : 1);
        animar(f.lineaD.interrupt(), si, 500, 150 * i).attr("opacity", n >= 1 ? 1 : 0);
        animar(f.deltas.interrupt(), si, 500, 150 * i).attr("opacity", n >= 1 ? 1 : 0);
        animar(f.tD.interrupt(), si, 500, 150 * i + 200).attr("opacity", n >= 1 ? 1 : 0);
      });
      leyT.filter((d, i) => i === 2).attr("opacity", n >= 1 ? 1 : 0.25);
      animar(gc.interrupt(), si, 600).attr("opacity", n >= 2 ? 1 : 0);
      actual = n;
    }
    return {
      entrar() {
        actual = -1;
        filasT.forEach((f, i) => {
          f.modelo.interrupt().attr("cx", f.hist.attr("cx"));
          animar(f.modelo, true, 900, 150 * i).attr("cx", xt(R.tetuan[i].modelo));
        });
        mostrar(0, true);
      },
      paso(n) { if (n !== actual) mostrar(n, true); },
      final() { mostrar(2, false); },
      salir() { svg.selectAll("*").interrupt(); },
    };
  }

  // ------------------------------------------------------------------ (5) peso frente a rendimiento
  // El MAE del Centro en 2026 frente al peso en disco de cada modelo (escala logarítmica), a 1 y a 24 horas. La
  // línea punteada es el Random Forest elegido: por debajo, mejor que él. Círculo vacío: peso estimado (parámetros ×
  // 4 bytes). Pasos: 0 los árboles, 1 los ocho fundacionales sin entrenar, 2 el ajustado, el híbrido y el combinado.
  function peso(el) {
    const D = window.DATOS.peso;
    const ancho = 1180, alto = 430, gx = 64, abajo = 88;
    const pw = (ancho - gx) / 2;
    const m = { t: 34, r: 122, l: 58 };
    const svg = lienzo(el, ancho, alto, "g-peso", "Peso de los modelos frente a su error en el Centro");
    const PASO = { arbol: 0, zeroshot: 1, ajustado: 2, hibrido: 2, combinado: 2 };
    const CLASE = { arbol: "s-rf", zeroshot: "s-gris", ajustado: "s-comb", hibrido: "s-comb", combinado: "s-comb" };
    // Dónde va cada etiqueta para que no se pisen (solo diseño: los valores vienen de DATOS)
    const LADO = {
      "1h": { "XGBoost global": "der-arriba", "Random Forest por área": "izq-abajo", "Chronos-2": "izq",
        "Timestral": "izq", "t0-gamma": "izq", "Simons": "der-abajo", "Toto 2.0": "der-arriba",
        "TimesFM 3.0": "der", "TimesFM 2.5": "der", "TiRex-2": "der", "Chronos-2 ajustado": "izq",
        "Híbrido XGBoost + Simons": "izq", "Combinado": "der" },
      "24h": { "XGBoost global": "der-arriba", "Random Forest por área": "izq-arriba", "Chronos-2": "izq",
        "Timestral": "izq-arriba", "t0-gamma": "der-arriba", "Simons": "der-abajo", "Toto 2.0": "der",
        "TimesFM 3.0": "der", "TimesFM 2.5": "der", "TiRex-2": "der", "Chronos-2 ajustado": "izq",
        "Híbrido XGBoost + Simons": "izq", "Combinado": "der-abajo" },
    };
    const capas = [];
    ["1h", "24h"].forEach((h, i) => {
      const g = svg.append("g").attr("transform", `translate(${i * (pw + gx)},0)`);
      const campo = `mae_${h}`;
      const x = d3.scaleLog([10, 2600], [m.l, pw - m.r]);
      const ext = d3.extent(D, (d) => d[campo]);
      const y = d3.scaleLinear([ext[0] - (ext[1] - ext[0]) * 0.05, ext[1] + (ext[1] - ext[0]) * 0.05],
        [alto - abajo, m.t]).nice();
      g.append("g").attr("class", "g-eje g-rejilla").attr("transform", `translate(${m.l},0)`)
        .call(d3.axisLeft(y).ticks(5).tickSize(-(pw - m.l - m.r)));
      g.append("g").attr("class", "g-eje").attr("transform", `translate(0,${alto - abajo})`)
        .call(d3.axisBottom(x).tickValues([20, 100, 1000, 2000])
          .tickFormat((v) => (v >= 1000 ? `${v / 1000} GB` : `${v} MB`)).tickSizeOuter(0));
      g.append("text").attr("class", "g-titulo").attr("x", m.l).attr("y", m.t - 12).text(`${HORIZONTE[h]} · MAE (MW)`);
      g.append("text").attr("class", "g-et g-suave").attr("x", pw - m.r).attr("y", alto - abajo + 46)
        .attr("text-anchor", "end").style("font-size", "15px").text("peso en disco (escala logarítmica)");
      const rf = D.find((d) => d.tipo === "arbol" && d.nombre.startsWith("Random Forest"));
      g.append("line").attr("class", "p-linea-rf").attr("x1", m.l).attr("x2", pw - m.r)
        .attr("y1", y(rf[campo])).attr("y2", y(rf[campo]));
      const puntos = g.selectAll("g.pt").data(D).join("g").attr("class", "pt")
        .attr("transform", (d) => `translate(${x(d.mb)},${y(d[campo])})`);
      puntos.append("circle").attr("r", (d) => (d.tipo === "combinado" ? 11 : 9))
        .attr("class", (d) => `${CLASE[d.tipo]} ${d.estimado ? "p-vacio" : "p-lleno"}`);
      puntos.append("text")
        .attr("class", (d) => (d.tipo === "combinado" || d.tipo === "ajustado" ? "p-et-fuerte" : "p-et"))
        .each(function (d) {
          const lado = LADO[h][d.nombre] || "der";
          const t = d3.select(this);
          const dy = lado.includes("arriba") ? -12 : lado.includes("abajo") ? 21 : 5;
          if (lado.startsWith("izq")) t.attr("x", -14).attr("text-anchor", "end");
          else t.attr("x", 14);
          t.attr("y", dy).text(`${d.nombre}  ${dec(d[campo])}`);
        });
      capas.push(puntos);
    });
    const ley = leyenda(svg, m.l, alto - 8, [
      { tipo: "punto", clase: "s-rf", texto: "árboles (el proyecto)", x: 0 },
      { tipo: "punto", clase: "s-gris", texto: "sin entrenar", x: 210 },
      { tipo: "punto", clase: "s-comb", texto: "ajustado, híbrido y combinado", x: 360 },
      { tipo: "aro", clase: "s-gris", texto: "peso estimado", x: 650 },
      { tipo: "linea", clase: "p-linea-rf", texto: "Random Forest elegido", x: 815 },
    ]);
    let actual = -1;
    function mostrar(n, si) {
      capas.forEach((puntos) => {
        puntos.each(function (d, k) {
          const nuevo = PASO[d.tipo] > actual;
          const sel = d3.select(this);
          if (PASO[d.tipo] > n) { sel.interrupt().attr("opacity", 0); return; }
          if (si && nuevo) sel.interrupt().attr("opacity", 0);
          animar(sel, si && nuevo, 500, nuevo ? 70 * (k % 8) : 0).attr("opacity", 1);
        });
      });
      ley.attr("opacity", (d, k) => ([0, 1, 2, 1, 0][k] <= n ? 1 : 0.25));
      actual = n;
    }
    return {
      entrar() { actual = -1; mostrar(0, true); },
      paso(n) { if (n !== actual) mostrar(n, true); },
      final() { actual = -1; mostrar(2, false); },
      salir() { svg.selectAll("*").interrupt(); },
    };
  }

  // ------------------------------------------------------------------ barras horizontales sencillas
  // data-serie="validacion" (mejora media de 2025 por algoritmo) o "adaptacion" (el error del Centro a 1 hora y
  // lo que lo mueven el clima y reentrenar, a la misma escala).
  function barras(el) {
    const B = window.DATOS.barras[el.dataset.serie];
    const ancho = +(el.dataset.ancho || 560), fila = 64, alto = B.length * fila + 6;
    const etq = +(el.dataset.etiqueta || 210), valor = 120;
    const svg = lienzo(el, ancho, alto, "g-barras", el.dataset.serie);
    const x = d3.scaleLinear([0, d3.max(B, (d) => d.valor)], [0, ancho - etq - valor]);
    const g = svg.selectAll("g").data(B).join("g").attr("transform", (d, i) => `translate(0,${i * fila + 8})`);
    g.append("text").attr("class", "g-et").attr("x", 0).attr("y", 24).style("font-size", "20px").text((d) => d.etiqueta);
    g.append("rect").attr("class", "b-pista").attr("x", etq).attr("width", ancho - etq - valor).attr("height", 34).attr("rx", 5);
    const r = g.append("rect").attr("class", (d) => d.clase).attr("x", etq).attr("height", 34).attr("rx", 5).attr("width", 0);
    const COLOR = { "b-tinta": "", "b-rf": "t-rf", "b-xgb": "t-rf", "b-gris": "t-gris" };
    g.append("text").attr("class", (d) => `g-valor ${COLOR[d.clase] || ""}`)
      .attr("x", ancho - valor + 12).attr("y", 26).style("font-size", "22px").text((d) => d.texto);
    // Una barra de menos de 3 px no se vería: se dibuja de 3 px y el número dice el valor
    const w = (d) => Math.max(3, x(d.valor));
    return {
      entrar() { r.interrupt().attr("width", 0); animar(r, true, 800).delay((d, i) => 120 * i).attr("width", w); },
      final() { r.attr("width", w); },
      salir() { r.interrupt(); },
    };
  }

  // ------------------------------------------------------------------ enlace con reveal.js
  const GRAFICOS = { dia, prueba, mensual, reanalisis, peso, barras };
  const instancias = [];

  function pasoVisible(diapositiva) {
    return d3.max(Array.from(diapositiva.querySelectorAll(".fragment.visible[data-paso]")), (f) => +f.dataset.paso) || 0;
  }

  function alCambiar(actual, anterior) {
    instancias.forEach(({ el, g }) => {
      if (anterior && anterior.contains(el) && g.salir) g.salir();
    });
    instancias.forEach(({ el, g }) => {
      if (actual && actual.contains(el)) {
        if (g.entrar) g.entrar();
        if (g.paso) g.paso(pasoVisible(actual));
      }
    });
  }

  function alFragmento(ev) {
    const diapositiva = ev.fragment && ev.fragment.closest("section");
    if (!diapositiva) return;
    instancias.forEach(({ el, g }) => {
      if (diapositiva.contains(el) && g.paso) g.paso(pasoVisible(diapositiva));
    });
  }

  function iniciar() {
    document.querySelectorAll("[data-grafico]").forEach((el) => {
      const f = GRAFICOS[el.dataset.grafico];
      if (!f) { console.warn("gráfico desconocido:", el.dataset.grafico); return; }
      instancias.push({ el, g: f(el) });
    });
    if (/print-pdf/.test(window.location.search)) {
      instancias.forEach(({ g }) => g.final && g.final());
      return;
    }
    Reveal.on("slidechanged", (ev) => alCambiar(ev.currentSlide, ev.previousSlide));
    Reveal.on("fragmentshown", alFragmento);
    Reveal.on("fragmenthidden", alFragmento);
    alCambiar(Reveal.getCurrentSlide(), null);
  }

  function cuandoReveal() {
    if (!window.Reveal) { setTimeout(cuandoReveal, 50); return; }
    if (Reveal.isReady && Reveal.isReady()) iniciar();
    else Reveal.on("ready", iniciar);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", cuandoReveal);
  else cuandoReveal();
})();
