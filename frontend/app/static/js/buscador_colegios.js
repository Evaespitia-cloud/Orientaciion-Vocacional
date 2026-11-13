// Buscador de colegios con autocompletar (patrón combobox de WAI-ARIA).
// Uso: BuscadorColegios.iniciar(raiz), donde raiz contiene:
//   input[data-colegio-buscar], ul[data-colegio-lista], input[name=sede_codigo],
//   y opcionalmente select[data-colegio-sector] (oficial/privado) o
//   select[data-colegio-municipio] para filtrar la lista.
// Con un sector elegido la lista se despliega sin escribir nada; escribir la filtra.
window.BuscadorColegios = (function () {
  function escapar(t) {
    return String(t ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function iniciar(raiz, alElegir) {
    const entrada = raiz.querySelector('[data-colegio-buscar]');
    const lista = raiz.querySelector('[data-colegio-lista]');
    const codigo = raiz.querySelector('input[name="sede_codigo"]');
    const sector = raiz.querySelector('[data-colegio-sector]');
    const municipio = raiz.querySelector('[data-colegio-municipio]');
    const ayuda = raiz.querySelector('[data-colegio-ayuda]');
    let resultados = [];
    let total = 0;
    let activo = -1;
    let espera;

    function filtros() {
      return {
        sector: sector && sector.value ? sector.value : '',
        municipio: municipio && municipio.value ? municipio.value : '',
      };
    }

    function cerrar() {
      lista.hidden = true;
      entrada.setAttribute('aria-expanded', 'false');
      activo = -1;
    }

    function bloquear() {
      // Sin tipo de colegio elegido no hay lista que mostrar: primero se elige oficial o privado.
      if (!sector) return;
      const hay = !!sector.value;
      entrada.disabled = !hay;
      entrada.placeholder = hay ? 'Elige tu colegio de la lista o escribe para buscarlo'
                                : 'Primero elige el tipo de colegio';
      if (!hay) { entrada.value = ''; codigo.value = ''; cerrar(); }
      if (ayuda) ayuda.textContent = '';
    }

    function pintar() {
      if (!resultados.length) {
        lista.innerHTML = '<li class="bc-vacio">No aparece. Revisa el nombre o el tipo de colegio (oficial / privado).</li>';
      } else {
        lista.innerHTML = resultados.map((c, i) => `
          <li role="option" id="bc-op-${i}" class="bc-op${i === activo ? ' activo' : ''}" data-i="${i}" aria-selected="${i === activo}">
            <span class="bc-nombre">${escapar(c.nombre)}</span>
            <span class="bc-detalle">${escapar(c.sede_etiqueta ? c.sede_etiqueta + ' · ' : '')}${escapar(c.sector)} · ${escapar(c.municipio_nombre || c.municipio)}</span>
          </li>`).join('');
      }
      lista.hidden = false;
      entrada.setAttribute('aria-expanded', 'true');
      entrada.setAttribute('aria-activedescendant', activo >= 0 ? `bc-op-${activo}` : '');
      if (ayuda) {
        ayuda.textContent = total > resultados.length
          ? `Mostrando ${resultados.length} de ${total} colegios. Escribe para encontrar el tuyo.`
          : (resultados.length ? `${resultados.length} colegio(s).` : '');
      }
    }

    function elegir(i) {
      const c = resultados[i];
      if (!c) return;
      entrada.value = c.nombre_visible;
      codigo.value = c.codigo;
      cerrar();
      if (ayuda) ayuda.textContent = '';
      if (alElegir) alElegir(c);
    }

    async function buscar() {
      const q = entrada.value.trim();
      const f = filtros();
      codigo.value = '';
      // Con sector elegido la lista se abre sin escribir; sin sector hacen falta dos letras.
      if (q.length < 2 && !f.sector && !f.municipio) { cerrar(); return; }
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (f.sector) params.set('sector', f.sector);
      if (f.municipio) params.set('municipio', f.municipio);
      try {
        const r = await fetch('/api/colegios?' + params);
        const d = r.ok ? await r.json() : {};
        resultados = d.colegios || [];
        total = d.total || resultados.length;
      } catch (e) {
        resultados = [];
        total = 0;
      }
      activo = -1;
      pintar();
    }

    entrada.addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(buscar, 180); });
    entrada.addEventListener('keydown', (e) => {
      if (lista.hidden) {
        if (e.key === 'ArrowDown') { buscar(); e.preventDefault(); }
        return;
      }
      if (e.key === 'ArrowDown') { activo = Math.min(activo + 1, resultados.length - 1); pintar(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { activo = Math.max(activo - 1, 0); pintar(); e.preventDefault(); }
      else if (e.key === 'Enter' && activo >= 0) { elegir(activo); e.preventDefault(); }
      else if (e.key === 'Escape') { cerrar(); }
    });
    lista.addEventListener('mousedown', (e) => {
      const op = e.target.closest('[data-i]');
      if (op) { elegir(Number(op.dataset.i)); e.preventDefault(); }
    });
    entrada.addEventListener('focus', () => { if (!codigo.value) buscar(); });
    entrada.addEventListener('blur', () => setTimeout(cerrar, 120));
    if (sector) sector.addEventListener('change', () => { bloquear(); if (sector.value) buscar(); });
    if (municipio) municipio.addEventListener('change', () => { if (entrada.value.trim().length >= 2 || filtros().sector) buscar(); });
    bloquear();
  }

  return { iniciar };
})();
