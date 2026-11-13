// "Comparte tu carta": vista previa, nombre opcional, compartir con el menú del celular,
// descargar la imagen o copiar el enlace público (que nunca lleva el nombre).
(function () {
  const dialogo = document.getElementById('dialogoCarta');
  if (!dialogo) return;
  const $ = (id) => document.getElementById(id);
  const imagen = $('ccImagen'), nombre = $('ccNombre'), estado = $('ccEstado');
  const descargar = $('ccDescargar'), compartir = $('ccCompartir');
  let enlace = null;
  let blob = null;

  function urlPng() {
    return `${dialogo.dataset.png}?nombre=${nombre.checked ? '1' : '0'}&v=${Date.now()}`;
  }

  async function cargarImagen() {
    imagen.removeAttribute('src');
    imagen.classList.add('cargando');
    try {
      const r = await fetch(urlPng());
      if (!r.ok) throw new Error(r.status);
      blob = await r.blob();
      const url = URL.createObjectURL(blob);
      imagen.src = url;
      descargar.href = url;
      const archivo = new File([blob], 'mi-perfil-vocacional.png', { type: 'image/png' });
      compartir.hidden = !(navigator.canShare && navigator.canShare({ files: [archivo] }));
    } catch (e) {
      estado.textContent = 'No se pudo preparar la carta. Intenta de nuevo.';
    } finally {
      imagen.classList.remove('cargando');
    }
  }

  async function obtenerEnlace() {
    if (enlace) return enlace;
    const r = await fetch(dialogo.dataset.enlace);
    if (!r.ok) throw new Error(r.status);
    enlace = (await r.json()).url;
    return enlace;
  }

  document.querySelectorAll('[data-abrir-carta]').forEach((b) => b.addEventListener('click', () => {
    dialogo.showModal();
    if (!blob) cargarImagen();
  }));
  dialogo.addEventListener('click', (e) => { if (e.target === dialogo) dialogo.close(); });
  nombre.addEventListener('change', cargarImagen);

  compartir.addEventListener('click', async () => {
    try {
      const url = await obtenerEnlace();
      const archivo = new File([blob], 'mi-perfil-vocacional.png', { type: 'image/png' });
      await navigator.share({ files: [archivo], title: 'Mi perfil vocacional', text: `Mi perfil vocacional es ${dialogo.dataset.perfil}. Descubre el tuyo: ${url}` });
    } catch (e) {
      if (e && e.name !== 'AbortError') estado.textContent = 'No se pudo abrir el menú para compartir; descarga la imagen.';
    }
  });

  $('ccCopiar').addEventListener('click', async () => {
    try {
      const url = await obtenerEnlace();
      await navigator.clipboard.writeText(url);
      estado.textContent = 'Enlace copiado. Pégalo en WhatsApp o donde quieras.';
    } catch (e) {
      estado.textContent = 'No se pudo copiar el enlace.';
    }
  });
})();
