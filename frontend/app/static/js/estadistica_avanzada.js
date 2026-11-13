// Estadística avanzada: pinta las tarjetas de hallazgos y las vuelve a pedir cada minuto.
(function () {
  const AREA = {
    'Realista': '#eb6834', 'Investigador': '#2a78d6', 'Artístico': '#e87ba4',
    'Social': '#1baf7a', 'Emprendedor': '#eda100', 'Convencional': '#4a3aa7', 'Otros': '#b9b6c3',
  };
  const SERIES = ['#f07f06', '#2a78d6', '#6f6b80'];
  const REFRESCO_MS = 60000;
  const graficas = {};
  let ultimo = null;
  let datosTarjetas = {};

  const $ = (id) => document.getElementById(id);
  const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const porc = (v) => (v * 100).toFixed(0) + ' %';
  const sinTema = { temaUSB: false };

  function opcionesBase(extra) {
    return Object.assign({ responsive: true, maintainAspectRatio: false, animation: { duration: 300 } }, extra);
  }

  function crearGrafica(canvas, g) {
    if (!g) return null;
    const ctx = canvas.getContext('2d');
    if (g.tipo === 'proporciones') {
      return new Chart(ctx, {
        type: 'bar',
        data: { labels: g.areas, datasets: [{ label: 'Proporción', data: g.valores.map((v) => v * 100), backgroundColor: g.areas.map((a) => AREA[a]), borderRadius: 4, maxBarThickness: 22 }] },
        options: opcionesBase({
          indexAxis: 'y',
          plugins: Object.assign({ legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.raw.toFixed(1)} % (IC 95 %: ${(g.bajo[c.dataIndex] * 100).toFixed(1)} – ${(g.alto[c.dataIndex] * 100).toFixed(1)} %)` } } }, sinTema),
          scales: { x: { min: 0, max: Math.min(100, Math.ceil(Math.max(...g.alto) * 10) * 10), ticks: { callback: (v) => v + ' %' }, grid: { color: '#ecebf0' } }, y: { grid: { display: false } } },
        }),
        plugins: [{
          id: 'intervalos',
          afterDatasetsDraw(chart) {
            const { ctx: c, scales: { x, y } } = chart;
            c.save(); c.strokeStyle = '#1c1b22'; c.lineWidth = 1.5;
            g.areas.forEach((_, i) => {
              const yy = y.getPixelForValue(i), x1 = x.getPixelForValue(g.bajo[i] * 100), x2 = x.getPixelForValue(g.alto[i] * 100);
              c.beginPath(); c.moveTo(x1, yy); c.lineTo(x2, yy); c.moveTo(x1, yy - 5); c.lineTo(x1, yy + 5); c.moveTo(x2, yy - 5); c.lineTo(x2, yy + 5); c.stroke();
            });
            c.restore();
          },
        }],
      });
    }
    if (g.tipo === 'correlaciones') {
      return new Chart(ctx, {
        type: 'bar',
        data: { labels: g.areas, datasets: [{ label: 'ρ de Spearman', data: g.valores, backgroundColor: g.areas.map((a, i) => g.significativo[i] ? AREA[a] : AREA[a] + '55'), borderRadius: 4, maxBarThickness: 22 }] },
        options: opcionesBase({
          indexAxis: 'y',
          plugins: Object.assign({ legend: { display: false }, tooltip: { callbacks: { label: (c) => `ρ = ${c.raw.toFixed(2)}${g.significativo[c.dataIndex] ? ' (significativa)' : ''}` } } }, sinTema),
          scales: { x: { min: -1, max: 1, grid: { color: '#ecebf0' } }, y: { grid: { display: false } } },
        }),
      });
    }
    if (g.tipo === 'barras') {
      const desde = g.marca_desde ? g.marca_desde - 1 : Infinity;
      return new Chart(ctx, {
        type: 'bar',
        data: { labels: g.etiquetas, datasets: [{ label: g.eje_y || '', data: g.valores, backgroundColor: g.etiquetas.map((_, i) => i >= desde ? '#f07f06' : '#d9d7e0'), borderRadius: 4, maxBarThickness: 36 }] },
        options: opcionesBase({
          plugins: Object.assign({ legend: { display: false } }, sinTema),
          scales: { x: { title: { display: !!g.eje_x, text: g.eje_x }, grid: { display: false } }, y: { beginAtZero: true, title: { display: !!g.eje_y, text: g.eje_y }, grid: { color: '#ecebf0' } } },
        }),
      });
    }
    if (g.tipo === 'apiladas') {
      return new Chart(ctx, {
        type: 'bar',
        data: {
          labels: g.grupos.map((n, i) => `${n} (${g.totales[i]})`),
          datasets: g.areas.map((a, j) => ({ label: a, data: g.valores.map((fila) => fila[j] * 100), backgroundColor: AREA[a], borderWidth: { right: 1 }, borderColor: '#fff', borderSkipped: false })),
        },
        options: opcionesBase({
          indexAxis: 'y',
          plugins: Object.assign({ legend: { position: 'bottom' }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.raw.toFixed(0)} %` } } }, sinTema),
          scales: { x: { stacked: true, max: 100, ticks: { callback: (v) => v + ' %' }, grid: { display: false } }, y: { stacked: true, grid: { display: false } } },
        }),
      });
    }
    if (g.tipo === 'agrupadas') {
      return new Chart(ctx, {
        type: 'bar',
        data: { labels: g.areas, datasets: g.series.map((s, i) => ({ label: s.nombre, data: s.valores, backgroundColor: SERIES[i % SERIES.length], borderRadius: 3, maxBarThickness: 14 })) },
        options: opcionesBase({
          plugins: Object.assign({ legend: { position: 'bottom' }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.raw.toFixed(1)} %` } } }, sinTema),
          scales: { x: { grid: { display: false } }, y: { beginAtZero: true, max: 100, title: { display: true, text: g.eje_y }, grid: { color: '#ecebf0' } } },
        }),
      });
    }
    if (g.tipo === 'pareto') {
      return new Chart(ctx, {
        type: 'bar',
        data: {
          labels: g.etiquetas.map((t) => t.length > 22 ? t.slice(0, 21) + '…' : t),
          datasets: [
            { type: 'bar', label: 'Encuestas', data: g.valores, backgroundColor: '#f07f06', borderRadius: 3, yAxisID: 'y', order: 2 },
            { type: 'line', label: '% acumulado', data: g.acumulado.map((v) => v * 100), borderColor: '#1c1b22', backgroundColor: '#1c1b22', pointRadius: 2, yAxisID: 'y2', order: 1 },
          ],
        },
        options: opcionesBase({
          plugins: Object.assign({ legend: { position: 'bottom' }, tooltip: { callbacks: { title: (it) => g.etiquetas[it[0].dataIndex] } } }, sinTema),
          scales: {
            x: { ticks: { maxRotation: 60, minRotation: 45, font: { size: 10 } }, grid: { display: false } },
            y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#ecebf0' } },
            y2: { position: 'right', min: 0, max: 100, ticks: { callback: (v) => v + ' %' }, grid: { display: false } },
          },
        }),
      });
    }
    if (g.tipo === 'ecdf') {
      return new Chart(ctx, {
        type: 'line',
        data: { datasets: g.series.map((s, i) => ({ label: s.nombre, data: s.puntos.map((p) => ({ x: p.x, y: p.f * 100 })), stepped: true, borderColor: SERIES[i], backgroundColor: SERIES[i], pointRadius: 0, borderWidth: 2 })) },
        options: opcionesBase({
          parsing: false,
          plugins: Object.assign({ legend: { position: 'bottom' } }, sinTema),
          scales: { x: { type: 'linear', min: 0, title: { display: true, text: g.eje_x }, grid: { display: false } }, y: { min: 0, max: 100, ticks: { callback: (v) => v + ' %' }, grid: { color: '#ecebf0' } } },
        }),
      });
    }
    return null;
  }

  function htmlTarjeta(t) {
    const progreso = t.estado === 'faltan_datos'
      ? `<div class="ea-progreso" role="progressbar" aria-valuemin="0" aria-valuemax="${t.minimo}" aria-valuenow="${t.n}"><span style="width:${Math.min(100, t.n / t.minimo * 100)}%"></span></div>` : '';
    const lista = t.lista && t.lista.length
      ? `<ul class="ea-lista">${t.lista.map((c) => `<li><span>${esc(c.nombre)}</span><span>${esc(c.sector)} · ${c.matricula} en 9° a 11°</span></li>`).join('')}</ul>` : '';
    return `
      <article class="card ea-tarjeta ea-${t.estado}" data-id="${t.id}">
        <header class="ea-tarjeta-cabeza">
          <p class="ea-pregunta">${esc(t.pregunta)}</p>
          <button type="button" class="ea-ayuda" data-metodo="${t.id}" aria-label="Cómo se calculó: ${esc(t.pregunta)}">?</button>
        </header>
        <h2 class="ea-conclusion">${esc(t.conclusion)}</h2>
        ${progreso}
        ${t.grafica ? `<div class="ea-grafica ea-g-${t.grafica.tipo}"><canvas aria-label="${esc(t.conclusion)}"></canvas></div>` : ''}
        ${t.detalle ? `<p class="ea-detalle">${esc(t.detalle)}</p>` : ''}
        ${lista}
        <footer class="ea-pie">${t.estado === 'faltan_datos' ? `n = ${t.n} de ${t.minimo}` : `n = ${t.n_total ?? t.n}`}${t.estado === 'sin_evidencia' ? ' · sin diferencia clara' : ''}</footer>
      </article>`;
  }

  function pintar(datos) {
    Object.values(graficas).forEach((g) => g && g.destroy());
    datosTarjetas = {};
    const cont = $('tarjetas');
    cont.innerHTML = datos.tarjetas.map(htmlTarjeta).join('');
    cont.setAttribute('aria-busy', 'false');
    datos.tarjetas.forEach((t) => {
      datosTarjetas[t.id] = t;
      const canvas = cont.querySelector(`[data-id="${t.id}"] canvas`);
      if (canvas) graficas[t.id] = crearGrafica(canvas, t.grafica);
    });
  }

  function hace(fecha) {
    const s = Math.round((Date.now() - fecha) / 1000);
    if (s < 60) return 'hace un momento';
    const m = Math.round(s / 60);
    return m === 1 ? 'hace 1 minuto' : `hace ${m} minutos`;
  }

  function estado() {
    if (!ultimo) return;
    $('estadoDatos').textContent = `${ultimo.datos.con_dos_pruebas} estudiantes con las dos pruebas · actualizado ${hace(ultimo.hora)}`;
  }

  async function cargar() {
    const simulados = $('incluirSimulados').checked ? '1' : '0';
    try {
      const r = await fetch(`${window.EA_URL}?simulados=${simulados}`);
      if (!r.ok) throw new Error(r.status);
      const datos = await r.json();
      const firma = JSON.stringify(datos.tarjetas.map((t) => [t.id, t.n, t.conclusion]));
      if (!ultimo || ultimo.firma !== firma || ultimo.simulados !== simulados) pintar(datos);
      ultimo = { datos, firma, simulados, hora: Date.now() };
      $('avisoSimulados').hidden = simulados !== '1';
      estado();
    } catch (e) {
      $('estadoDatos').textContent = 'No se pudieron cargar los datos. Se reintenta en un minuto.';
    }
  }

  function abrirMetodo(id) {
    const t = datosTarjetas[id];
    if (!t) return;
    const m = t.metodo || {};
    $('metodoTitulo').textContent = t.pregunta;
    $('metodoPasos').innerHTML = (m.pasos || []).map((p) => `<li>${esc(p)}</li>`).join('');
    const formulas = $('metodoFormulas');
    formulas.innerHTML = '';
    (m.formulas || []).forEach((f) => {
      const div = document.createElement('div');
      try { katex.render(f, div, { displayMode: true, throwOnError: false }); } catch (e) { div.textContent = f; }
      formulas.appendChild(div);
    });
    $('metodoSupuestos').textContent = m.supuestos || '';
    $('metodoResultado').textContent = m.resultado || 'Todavía no hay datos suficientes para calcularlo.';
    $('dialogoMetodo').showModal();
  }

  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-metodo]');
    if (b) abrirMetodo(b.dataset.metodo);
  });
  $('dialogoMetodo').addEventListener('click', (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });
  try { $('incluirSimulados').checked = localStorage.getItem('ea_simulados') === '1'; } catch (e) { /* sin almacenamiento */ }
  $('incluirSimulados').addEventListener('change', (e) => {
    try { localStorage.setItem('ea_simulados', e.target.checked ? '1' : '0'); } catch (err) { /* sin almacenamiento */ }
    cargar();
  });

  cargar();
  setInterval(cargar, REFRESCO_MS);
  setInterval(estado, 15000);
})();
