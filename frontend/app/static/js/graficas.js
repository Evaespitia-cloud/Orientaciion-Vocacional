/* =====================================================
   Tema común de gráficas del panel (Chart.js 4)
   - Tipografía del sitio, textos en tinta y rejilla en línea fina.
   - Cada área RIASEC tiene SIEMPRE el mismo color, según su nombre (antes se
     asignaba por posición y un área cambiaba de color entre gráficas).
   - Otras categorías: paleta categórica validada para daltonismo, en orden fijo.
   - Barras delgadas con punta redondeada; donas con separación blanca.
   ===================================================== */
(function () {
  if (!window.Chart) return;

  var TINTA = '#1c1b22', TEXTO = '#6f6b80', REJILLA = '#ecebf0', SUPERFICIE = '#ffffff', ACENTO = '#f07f06';
  var AREA = {
    realista: '#eb6834', investigador: '#2a78d6', artistico: '#e87ba4',
    social: '#1baf7a', emprendedor: '#eda100', convencional: '#4a3aa7'
  };
  var CATEGORICA = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];

  function clave(txt) {
    return String(txt == null ? '' : txt).trim().toLowerCase()
      .normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function colorArea(txt) { return AREA[clave(txt)] || null; }
  function alfa(hex, a) {
    var h = hex.replace('#', '');
    return 'rgba(' + parseInt(h.slice(0, 2), 16) + ', ' + parseInt(h.slice(2, 4), 16) + ', ' + parseInt(h.slice(4, 6), 16) + ', ' + a + ')';
  }

  // ── Valores por defecto ─────────────────────────────
  var d = Chart.defaults;
  d.font.family = "'Inter', system-ui, sans-serif";
  d.font.size = 12;
  d.color = TEXTO;
  d.borderColor = REJILLA;
  d.plugins.legend.position = 'bottom';
  d.plugins.legend.labels.usePointStyle = true;
  d.plugins.legend.labels.pointStyle = 'circle';
  d.plugins.legend.labels.boxWidth = 8;
  d.plugins.legend.labels.boxHeight = 8;
  d.plugins.legend.labels.padding = 14;
  d.plugins.legend.labels.color = '#52505e';
  d.plugins.tooltip.backgroundColor = TINTA;
  d.plugins.tooltip.padding = 10;
  d.plugins.tooltip.cornerRadius = 8;
  d.plugins.tooltip.usePointStyle = true;
  d.plugins.tooltip.boxPadding = 4;
  d.elements.line.borderWidth = 2;
  d.elements.line.tension = 0.25;
  d.elements.point.radius = 3.5;
  d.elements.point.hoverRadius = 5.5;
  d.elements.point.hitRadius = 12;
  d.elements.point.borderWidth = 2;
  d.elements.arc.borderWidth = 2;
  d.elements.arc.borderColor = SUPERFICIE;
  d.elements.bar.borderRadius = 4;
  d.datasets.bar.maxBarThickness = 24;
  d.datasets.doughnut.cutout = '62%';
  d.scale.grid.color = REJILLA;
  d.scale.ticks.color = TEXTO;
  var radial = d.scales.radialLinear;
  radial.grid.color = REJILLA;
  radial.angleLines.color = REJILLA;
  radial.pointLabels.color = TINTA;
  radial.pointLabels.font = { size: 12, weight: '600' };
  radial.ticks.showLabelBackdrop = false;
  radial.ticks.color = '#a3a1ad';

  // ── Normalización de cada gráfica antes de dibujarla ──
  Chart.register({
    id: 'temaUSB',
    beforeUpdate: function (chart) {
      var tipo = chart.config.type;
      var labels = chart.data.labels || [];
      var etiquetasSonAreas = labels.length > 0 && labels.every(function (l) { return colorArea(l); });
      var series = chart.data.datasets || [];
      var apilada = false;
      // Se trabaja sobre la configuración original, no sobre chart.options (que son
      // proxies internos de Chart.js: reasignarlos rompe la resolución de opciones).
      var raw = chart.config.options || {};
      var esc = raw.scales || {};
      Object.keys(esc).forEach(function (id) { if (esc[id] && esc[id].stacked) apilada = true; });

      series.forEach(function (ds, i) {
        var t = ds.type || tipo;
        var deArea = colorArea(ds.label);

        if (t === 'line' || t === 'radar') {
          var c = deArea || (series.length === 1 ? ACENTO : CATEGORICA[i % CATEGORICA.length]);
          ds.borderColor = c;
          ds.pointBackgroundColor = c;
          ds.pointBorderColor = SUPERFICIE;
          ds.pointBorderWidth = 2;
          ds.borderWidth = 2;
          ds.borderDash = [];                       // nada de líneas punteadas
          ds.backgroundColor = (t === 'radar' || ds.fill) ? alfa(c, 0.10) : c;
          // Radar de una sola serie sobre las seis áreas: cada vértice con el color de su área
          if (t === 'radar' && series.length === 1 && etiquetasSonAreas) {
            ds.pointBackgroundColor = labels.map(colorArea);
          }
        } else if (t === 'bar') {
          if (deArea) ds.backgroundColor = deArea;
          else if (etiquetasSonAreas && series.length === 1) ds.backgroundColor = labels.map(colorArea);
          else if (series.length === 1) ds.backgroundColor = ACENTO;
          else ds.backgroundColor = CATEGORICA[i % CATEGORICA.length];
          ds.borderWidth = apilada ? { top: 2 } : 0;  // separación blanca entre segmentos apilados
          ds.borderColor = SUPERFICIE;
          ds.borderRadius = apilada ? 0 : 4;
          ds.borderSkipped = 'start';
          ds.maxBarThickness = 24;
        } else if (t === 'doughnut' || t === 'pie' || t === 'polarArea') {
          ds.backgroundColor = labels.map(function (l, j) {
            return colorArea(l) || CATEGORICA[j % CATEGORICA.length];
          });
          ds.borderColor = SUPERFICIE;
          ds.borderWidth = 2;
          ds.hoverOffset = 4;
        }
      });

      // Una torta se dibuja como dona: se lee mejor y deja espacio al total.
      if (tipo === 'pie') raw.cutout = '62%';

      // Ejes cartesianos: rejilla horizontal fina, sin rejilla vertical ni borde de eje.
      Object.keys(esc).forEach(function (id) {
        var e = esc[id];
        if (!e || e.type === 'radialLinear' || id === 'r') return;
        var esX = id === 'x' || e.axis === 'x' || (e.position === 'bottom' || e.position === 'top');
        e.grid = Object.assign({}, e.grid, esX ? { display: false } : { color: REJILLA });
        e.border = Object.assign({}, e.border, esX ? { color: '#d9d7e0' } : { display: false });
      });
    }
  });
})();
