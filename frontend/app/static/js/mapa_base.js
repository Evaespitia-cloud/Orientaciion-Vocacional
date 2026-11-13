// Mapa base común: MapLibre con el mapa de OpenFreeMap (datos de OpenStreetMap)
// y las imágenes satelitales de Esri como alternativa. Lo usan el formulario de
// dirección del estudiante y el mapa de Bienestar.
window.MapaBase = (function () {
  const ESTILO = 'https://tiles.openfreemap.org/styles/positron';
  const CENTRO_VALLE = [-75.5812, 6.2442];
  const LIMITES_VALLE = [[-75.95, 5.85], [-75.05, 6.65]];
  const SATELITE = {
    type: 'raster',
    tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
    tileSize: 256,
    maxzoom: 19,
    attribution: 'Imágenes © Esri, Maxar, Earthstar Geographics',
  };

  function primeraCapaDeTexto(mapa) {
    const capa = mapa.getStyle().layers.find((l) => l.type === 'symbol');
    return capa ? capa.id : undefined;
  }

  function crear(contenedor, opciones = {}) {
    const mapa = new maplibregl.Map({
      container: contenedor,
      style: ESTILO,
      center: opciones.centro || CENTRO_VALLE,
      zoom: opciones.zoom ?? 11,
      maxBounds: LIMITES_VALLE,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
    });
    mapa.touchZoomRotate.disableRotation();
    mapa.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    mapa.on('load', () => {
      mapa.addSource('satelite', SATELITE);
      mapa.addLayer({ id: 'satelite', type: 'raster', source: 'satelite', layout: { visibility: 'none' } },
        primeraCapaDeTexto(mapa));
    });
    return mapa;
  }

  function satelite(mapa, activo) {
    if (mapa.getLayer('satelite')) {
      mapa.setLayoutProperty('satelite', 'visibility', activo ? 'visible' : 'none');
    }
  }

  return { crear, satelite, CENTRO_VALLE };
})();
