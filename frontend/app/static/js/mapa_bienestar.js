// Mapa de Bienestar: calor de estudiantes que pasa a puntos al acercarse, y colegios.
(function () {
  const AREA = {
    'Realista': '#eb6834', 'Investigador': '#2a78d6', 'Artístico': '#e87ba4',
    'Social': '#1baf7a', 'Emprendedor': '#eda100', 'Convencional': '#4a3aa7',
  };
  const PERFILES = Object.keys(AREA);
  const GRADOS = ['9°', '10°', '11°'];
  const SECTORES = ['Oficial', 'Privado'];
  const ESTRATOS = ['1', '2', '3', '4', '5', '6'];
  const ZOOM_PUNTOS = 13.5;

  const $ = (id) => document.getElementById(id);
  const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const titulo = (m) => m ? m.charAt(0) + m.slice(1).toLowerCase().replace('medellin', 'medellín').replace('itagui', 'itagüí') : '';

  const filtros = { perfil: new Set(), grado: new Set(), sector: new Set(), estrato: new Set(), municipio: '' };
  let datos = { estudiantes: [], colegios: [] };
  let mapa;
  let listo = false;

  // ── Panel ────────────────────────────────────────
  function chips(id, valores, clave, color) {
    const cont = $(id);
    cont.innerHTML = valores.map((v) => `<button type="button" class="mb-chip" aria-pressed="false" data-v="${esc(v)}">${color ? `<i style="background:${color(v)}"></i>` : ''}${esc(v)}</button>`).join('');
    cont.addEventListener('click', (e) => {
      const b = e.target.closest('.mb-chip');
      if (!b) return;
      const v = b.dataset.v;
      if (filtros[clave].has(v)) filtros[clave].delete(v); else filtros[clave].add(v);
      b.setAttribute('aria-pressed', filtros[clave].has(v));
      aplicar();
    });
  }

  function pasa(e) {
    return (!filtros.perfil.size || filtros.perfil.has(e.perfil))
      && (!filtros.grado.size || filtros.grado.has(e.grado))
      && (!filtros.sector.size || filtros.sector.has(e.sector))
      && (!filtros.estrato.size || filtros.estrato.has(String(e.estrato)))
      && (!filtros.municipio || filtros.municipio === e.municipio);
  }

  function geojsonEstudiantes() {
    return {
      type: 'FeatureCollection',
      features: datos.estudiantes.filter(pasa).map((e, i) => ({
        type: 'Feature', id: i, geometry: { type: 'Point', coordinates: [e.lon, e.lat] }, properties: e,
      })),
    };
  }

  function geojsonColegios() {
    return {
      type: 'FeatureCollection',
      features: datos.colegios.filter((c) => !filtros.municipio || c.municipio === filtros.municipio)
        .filter((c) => !filtros.sector.size || filtros.sector.has(c.sector))
        .map((c) => ({
          type: 'Feature', geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
          properties: Object.assign({}, c, { perfiles: JSON.stringify(c.perfiles), cobertura_v: c.cobertura == null ? -1 : c.cobertura }),
        })),
    };
  }

  // ── Capas ────────────────────────────────────────
  function colorColegio(modo) {
    if (modo === 'dominante') {
      return ['match', ['coalesce', ['get', 'dominante'], ''], ...PERFILES.flatMap((p) => [p, AREA[p]]), '#c9c6d2'];
    }
    if (modo === 'cobertura') {
      return ['case', ['<', ['get', 'cobertura_v'], 0], '#d9d7e0',
        ['interpolate', ['linear'], ['get', 'cobertura_v'], 0, '#fde2c4', 0.1, '#f7a457', 0.3, '#e8730a', 0.6, '#9a4300']];
    }
    return ['case', ['>', ['get', 'evaluados'], 0], '#1c1b22', '#ffffff'];
  }

  function leyenda(modo) {
    const l = $('leyendaColegios');
    if (modo === 'dominante') {
      l.innerHTML = PERFILES.map((p) => `<span><i style="background:${AREA[p]}"></i>${p}</span>`).join('') + '<span><i style="background:#c9c6d2"></i>Sin evaluados</span>';
    } else if (modo === 'cobertura') {
      l.innerHTML = '<span class="mb-rampa"></span><span class="mb-rampa-txt"><em>0 %</em><em>30 %</em><em>60 % o más</em></span><span><i style="background:#d9d7e0"></i>Sin dato de matrícula</span>';
    } else {
      l.innerHTML = '<span><i style="background:#1c1b22"></i>Con estudiantes evaluados</span><span><i style="background:#fff;border:1px solid #1c1b22"></i>Sin ninguno todavía</span>';
    }
  }

  function crearCapas() {
    mapa.addSource('estudiantes', { type: 'geojson', data: geojsonEstudiantes() });
    mapa.addSource('colegios', { type: 'geojson', data: geojsonColegios() });
    mapa.addSource('lineas', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });

    mapa.addLayer({
      id: 'calor', type: 'heatmap', source: 'estudiantes', maxzoom: ZOOM_PUNTOS + 1.5,
      paint: {
        'heatmap-weight': 1,
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 10, 1.2, 15, 3],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 18, 13, 26, 15, 34],
        'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(240,127,6,0)', 0.15, 'rgba(253,226,196,0.75)', 0.4, '#f7a457', 0.7, '#e8730a', 1, '#7a3500'],
        'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], ZOOM_PUNTOS - 0.5, 0.9, ZOOM_PUNTOS + 1.5, 0],
      },
    });
    mapa.addLayer({
      id: 'calor-colegios', type: 'heatmap', source: 'colegios', layout: { visibility: 'none' },
      paint: {
        'heatmap-weight': ['interpolate', ['linear'], ['get', 'evaluados'], 0, 0, 1, 0.4, 5, 1],
        'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 10, 1.2, 15, 2.5],
        'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 10, 22, 15, 50],
        'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'],
          0, 'rgba(42,120,214,0)', 0.2, 'rgba(190,215,245,0.7)', 0.5, '#5b9be0', 0.8, '#2a78d6', 1, '#123f78'],
        'heatmap-opacity': 0.85,
      },
    });
    mapa.addLayer({ id: 'lineas', type: 'line', source: 'lineas', paint: { 'line-color': '#1c1b22', 'line-opacity': 0.35, 'line-width': 1 } });
    mapa.addLayer({
      id: 'puntos', type: 'circle', source: 'estudiantes', minzoom: ZOOM_PUNTOS - 1,
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], ZOOM_PUNTOS - 1, 2, 17, 6],
        'circle-color': ['match', ['get', 'perfil'], ...PERFILES.flatMap((p) => [p, AREA[p]]), '#8a8698'],
        'circle-stroke-color': '#ffffff', 'circle-stroke-width': 0.8,
        'circle-opacity': ['interpolate', ['linear'], ['zoom'], ZOOM_PUNTOS - 1, 0, ZOOM_PUNTOS, 1],
        'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], ZOOM_PUNTOS - 1, 0, ZOOM_PUNTOS, 1],
      },
    });
    mapa.addLayer({
      id: 'colegios', type: 'circle', source: 'colegios',
      paint: {
        // Pequeños de lejos para no tapar el calor; crecen con el zoom y con los evaluados.
        'circle-radius': ['interpolate', ['linear'], ['zoom'],
          10, ['interpolate', ['linear'], ['sqrt', ['get', 'evaluados']], 0, 1.6, 3, 3.5, 8, 6],
          15, ['interpolate', ['linear'], ['sqrt', ['get', 'evaluados']], 0, 4, 3, 8, 8, 14]],
        'circle-color': colorColegio('evaluados'),
        'circle-stroke-color': ['case', ['>', ['get', 'evaluados'], 0], '#1c1b22', '#8a8698'],
        'circle-stroke-width': ['interpolate', ['linear'], ['zoom'], 10, 0.6, 15, 1.2], 'circle-opacity': 0.92,
      },
    });
    leyenda('evaluados');

    mapa.on('click', 'puntos', (e) => {
      const p = e.features[0].properties;
      new maplibregl.Popup({ closeButton: true, maxWidth: '260px' }).setLngLat(e.lngLat).setHTML(`
        <div class="mb-pop"><strong style="color:${AREA[p.perfil] || '#1c1b22'}">${esc(p.perfil)}</strong>
        <span>${esc(p.grado || 'Grado sin dato')} · ${esc(p.sector || '')}</span>
        <span>${esc(p.colegio || 'Colegio sin dato')}</span>
        <span>Estrato ${esc(p.estrato || 'sin dato')} · ${esc(titulo(p.municipio))}</span>
        ${p.distancia_km !== 'null' && p.distancia_km != null ? `<span>A ${String(p.distancia_km).replace('.', ',')} km de su colegio</span>` : ''}
        ${p.simulado === true || p.simulado === 'true' ? '<em>Dato simulado</em>' : ''}</div>`).addTo(mapa);
    });
    mapa.on('click', 'colegios', (e) => {
      const c = e.features[0].properties;
      const perfiles = JSON.parse(c.perfiles || '{}');
      const total = Object.values(perfiles).reduce((a, b) => a + b, 0);
      const barra = total ? `<div class="mb-barra">${PERFILES.filter((p) => perfiles[p]).map((p) => `<i title="${p}: ${perfiles[p]}" style="flex:${perfiles[p]};background:${AREA[p]}"></i>`).join('')}</div>` : '';
      const cobertura = c.cobertura_v >= 0 ? `${(c.cobertura_v * 100).toFixed(1).replace('.', ',')} % de cobertura` : 'Sin dato de matrícula';
      new maplibregl.Popup({ closeButton: true, maxWidth: '280px' }).setLngLat(e.lngLat).setHTML(`
        <div class="mb-pop"><strong>${esc(c.nombre)}</strong>
        <span>${esc(c.sector)} · ${esc(titulo(c.municipio))}${c.comuna && c.comuna !== 'null' ? ' · ' + esc(c.comuna) : ''}</span>
        <span>${c.evaluados} evaluados${c.matricula && c.matricula !== 'null' ? ` de ${c.matricula} en 9° a 11°` : ''}</span>
        <span>${cobertura}</span>${barra}</div>`).addTo(mapa);
      lineasDe(c.codigo, e.lngLat);
    });
    ['puntos', 'colegios'].forEach((id) => {
      mapa.on('mouseenter', id, () => { mapa.getCanvas().style.cursor = 'pointer'; });
      mapa.on('mouseleave', id, () => { mapa.getCanvas().style.cursor = ''; });
    });
    listo = true;
  }

  function lineasDe(codigo, lngLat) {
    const destino = [lngLat.lng, lngLat.lat];
    const features = datos.estudiantes.filter((e) => e.colegio_codigo === codigo && pasa(e))
      .map((e) => ({ type: 'Feature', geometry: { type: 'LineString', coordinates: [[e.lon, e.lat], destino] } }));
    mapa.getSource('lineas').setData({ type: 'FeatureCollection', features });
  }

  function aplicar() {
    if (!listo) return;
    mapa.getSource('estudiantes').setData(geojsonEstudiantes());
    mapa.getSource('colegios').setData(geojsonColegios());
    mapa.getSource('lineas').setData({ type: 'FeatureCollection', features: [] });
    const visibles = datos.estudiantes.filter(pasa).length;
    const colegios = datos.colegios.filter((c) => (!filtros.municipio || c.municipio === filtros.municipio) && c.evaluados > 0).length;
    $('resumenMapa').textContent = `${visibles} estudiantes en el mapa · ${colegios} colegios con evaluados`;
  }

  async function cargar() {
    const simulados = $('incluirSimulados').checked ? '1' : '0';
    $('avisoSimulados').hidden = simulados !== '1';
    try {
      const r = await fetch(`${window.MB_URL}?simulados=${simulados}`);
      if (!r.ok) throw new Error(r.status);
      datos = await r.json();
    } catch (e) {
      $('resumenMapa').textContent = 'No se pudieron cargar los datos del mapa.';
      return;
    }
    const municipios = [...new Set(datos.colegios.map((c) => c.municipio))].sort();
    const sel = $('filtroMunicipio');
    const actual = sel.value;
    sel.innerHTML = '<option value="">Todo el Valle de Aburrá</option>' + municipios.map((m) => `<option value="${esc(m)}">${esc(titulo(m))}</option>`).join('');
    sel.value = actual;
    aplicar();
  }

  // ── Arranque ─────────────────────────────────────
  chips('filtroPerfil', PERFILES, 'perfil', (p) => AREA[p]);
  chips('filtroGrado', GRADOS, 'grado');
  chips('filtroSector', SECTORES, 'sector');
  chips('filtroEstrato', ESTRATOS, 'estrato');
  $('filtroMunicipio').addEventListener('change', (e) => {
    filtros.municipio = e.target.value;
    aplicar();
    const cs = datos.colegios.filter((c) => !filtros.municipio || c.municipio === filtros.municipio);
    if (cs.length) {
      const b = new maplibregl.LngLatBounds();
      cs.forEach((c) => b.extend([c.lon, c.lat]));
      mapa.fitBounds(b, { padding: 60, maxZoom: 14, duration: 600 });
    }
  });
  document.querySelectorAll('input[name="modoColegio"]').forEach((r) => r.addEventListener('change', (e) => {
    if (!listo) return;
    mapa.setPaintProperty('colegios', 'circle-color', colorColegio(e.target.value));
    leyenda(e.target.value);
  }));
  const capas = { capaCalor: ['calor'], capaPuntos: ['puntos', 'lineas'], capaColegios: ['colegios'], capaCalorColegios: ['calor-colegios'] };
  Object.entries(capas).forEach(([id, ids]) => $(id).addEventListener('change', (e) => {
    if (!listo) return;
    ids.forEach((c) => mapa.setLayoutProperty(c, 'visibility', e.target.checked ? 'visible' : 'none'));
  }));
  $('capaSatelite').addEventListener('change', (e) => MapaBase.satelite(mapa, e.target.checked));
  try { $('incluirSimulados').checked = localStorage.getItem('ea_simulados') === '1'; } catch (e) { /* sin almacenamiento */ }
  $('incluirSimulados').addEventListener('change', (e) => {
    try { localStorage.setItem('ea_simulados', e.target.checked ? '1' : '0'); } catch (err) { /* sin almacenamiento */ }
    cargar();
  });
  $('plegarPanel').addEventListener('click', () => {
    const panel = $('panelMapa');
    const abierto = !panel.classList.toggle('plegado');
    $('plegarPanel').setAttribute('aria-expanded', abierto);
    setTimeout(() => mapa.resize(), 220);
  });
  $('ayudaMapa').addEventListener('click', () => {
    const f = $('formulasMapa');
    if (!f.childElementCount && window.katex) {
      [String.raw`\hat f(x) = \sum_{i=1}^{n} \exp\!\left(-\frac{\lVert x - x_i \rVert^2}{2h^2}\right)`,
       String.raw`\text{cobertura}_s = \frac{\text{evaluados}_s}{m_{9,s} + m_{10,s} + m_{11,s}}`].forEach((tex) => {
        const d = document.createElement('div');
        katex.render(tex, d, { displayMode: true, throwOnError: false });
        f.appendChild(d);
      });
    }
    $('dialogoMapa').showModal();
  });
  $('dialogoMapa').addEventListener('click', (e) => { if (e.target === e.currentTarget) e.currentTarget.close(); });

  mapa = MapaBase.crear('mapaBienestar', { zoom: 11 });
  mapa.on('load', () => { crearCapas(); cargar(); });
})();
