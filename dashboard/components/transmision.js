/**
 * dashboard/components/transmision.js
 * OMNIMORPH — Controlador de la página Transmisión.
 * IIFE con 'use strict'. Lee transmision.json y maneja video + gráficos.
 */
(function () {
  'use strict';

  var L = window.TransmisionLogica;

  // ── Estado ────────────────────────────────────────────────────────────────
  var estado = {
    datos:        null,
    reproduciendo: false,
    vozActiva:    true,
    frameAnterior: -1,
    fraseActual:  '',
  };

  // ── Referencias DOM ───────────────────────────────────────────────────────
  var video       = document.getElementById('tv-video');
  var voz         = document.getElementById('tv-voz');
  var tv          = document.getElementById('tv');
  var marcadorEl  = document.getElementById('tv-marcador');
  var relojEl     = document.getElementById('tv-reloj');
  var localEl     = document.getElementById('tv-local-codigo');
  var scoreEl     = document.getElementById('tv-score');
  var visitaEl    = document.getElementById('tv-visita-codigo');
  var protagonistaEl = document.getElementById('tv-protagonista');
  var trazosEl    = document.getElementById('tv-trazos');
  var radarEl     = document.getElementById('tv-radar');
  var fichaEl     = document.getElementById('tv-ficha');
  var mateoEl     = document.getElementById('tv-mateo');
  var fichaMovilEl  = document.getElementById('tv-ficha-movil');
  var mateoMovilEl  = document.getElementById('tv-mateo-movil');
  var inicioBtn   = document.getElementById('tv-inicio');
  var pausaBtn    = document.getElementById('tv-pausa');
  var vozToggleBtn = document.getElementById('tv-voz-toggle');
  var repetirBtn  = document.getElementById('tv-repetir');
  var dataErrorEl = document.getElementById('data-error');

  // ── Escala ────────────────────────────────────────────────────────────────
  function actualizarEscala() {
    if (!estado.datos) return;
    var esc = L.escala(tv.clientWidth, estado.datos.video.ancho);
    tv.style.setProperty('--tv-escala', esc);
  }

  window.addEventListener('resize', actualizarEscala);

  // ── Inicialización ────────────────────────────────────────────────────────
  fetch('../data/transmision.json')
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (datos) {
      estado.datos = datos;
      var p = datos.partido;

      // Marcador inicial
      localEl.textContent  = p.local.codigo;
      visitaEl.textContent = p.visita.codigo;
      localEl.style.color  = p.local.color;
      visitaEl.style.color = p.visita.color;
      scoreEl.textContent  = p.marcador[0] + '-' + p.marcador[1];
      relojEl.textContent  = L.reloj(0, p.reloj_inicio_s);

      // Ficha (pre-construir, se muestra en paso 5)
      construirFicha(datos.ficha, p);

      // Voz
      voz.src = datos.narracion.audio;

      // Video
      if (!datos.video.src) {
        mostrarError('No se encontró el video del partido en dashboard/media/');
        return;
      }
      video.src = datos.video.src;

      video.addEventListener('loadeddata', function () {
        inicioBtn.disabled = false;
        inicioBtn.textContent = 'Ver transmisión';
        pausaBtn.disabled  = false;
        repetirBtn.disabled = false;
        actualizarEscala();
        requestAnimationFrame(bucle);
      });

      video.addEventListener('error', function () {
        mostrarError('No se encontró el video del partido en dashboard/media/');
      });
    })
    .catch(function () {
      mostrarError(null);
    });

  function mostrarError(msg) {
    if (dataErrorEl) {
      if (msg) {
        var span = dataErrorEl.querySelector('span:last-child');
        if (span) span.textContent = msg;
      }
      dataErrorEl.hidden = false;
    }
  }

  // ── Botón inicio ──────────────────────────────────────────────────────────
  inicioBtn.addEventListener('click', function () {
    inicioBtn.hidden = true;
    video.play();
    if (estado.vozActiva) voz.play();
    estado.reproduciendo = true;
  });

  // ── Pausa ─────────────────────────────────────────────────────────────────
  pausaBtn.addEventListener('click', function () {
    if (video.paused) {
      video.play();
      if (estado.vozActiva && !voz.paused) voz.play();
      else if (estado.vozActiva) voz.play();
      pausaBtn.textContent = 'Pausa';
    } else {
      video.pause();
      voz.pause();
      pausaBtn.textContent = 'Reanudar';
    }
  });

  // ── Repetir ───────────────────────────────────────────────────────────────
  repetirBtn.addEventListener('click', function () {
    video.currentTime = 0;
    voz.currentTime   = 0;
    video.play();
    if (estado.vozActiva) voz.play();
    pausaBtn.textContent = 'Pausa';
  });

  // ── Barra espaciadora = pausa ─────────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.code === 'Space' && e.target === document.body) {
      e.preventDefault();
      pausaBtn.click();
    }
  });

  // ── Toggle voz ───────────────────────────────────────────────────────────
  vozToggleBtn.addEventListener('click', function () {
    estado.vozActiva = !estado.vozActiva;
    voz.muted = !estado.vozActiva;
    video.volume = estado.vozActiva ? 0.25 : 1.0;
    vozToggleBtn.setAttribute('aria-pressed', String(estado.vozActiva));
    vozToggleBtn.textContent = 'Voz de MATEO: ' + (estado.vozActiva ? 'sí' : 'no');
    if (!estado.vozActiva) {
      mateoEl.hidden = true;
    }
  });

  // ── Bucle de animación ────────────────────────────────────────────────────
  function bucle() {
    requestAnimationFrame(bucle);
    if (!estado.datos || video.paused) return;

    var d  = estado.datos;
    var t  = video.currentTime;
    var p  = d.partido;

    // Sincronizar reloj y marcador
    relojEl.textContent = L.reloj(t, p.reloj_inicio_s);

    // Volumen del video según estado de voz
    if (estado.vozActiva) {
      video.volume = 0.25;
    } else {
      video.volume = 1.0;
    }

    // Reajuste de voz
    var aj = L.ajusteVoz(video.currentTime, voz.currentTime);
    if (aj !== null) voz.currentTime = aj;

    // Cuadro actual
    var fps = d.video.fps;
    var n   = d.video.n_frames;
    var f   = L.indiceCuadro(t, fps, n);

    // Visibilidad de gráficos
    var vis = L.graficosVisibles(t, d.jugadas);
    var j   = vis.indice >= 0 ? d.jugadas[vis.indice] : null;

    // ③ Protagonista
    if (vis.protagonista && j && j.protagonista !== null) {
      var jugadorData = d.jugadores[String(j.protagonista)];
      if (jugadorData) {
        protagonistaEl.textContent = jugadorData.etiqueta;
        protagonistaEl.style.borderLeftColor = jugadorData.team === 1
          ? p.local.color : jugadorData.team === 0 ? p.visita.color : 'transparent';
        protagonistaEl.hidden = false;
      }
    } else {
      protagonistaEl.hidden = true;
    }

    // ⑥ Estela + triángulo
    var cuadroActual = d.cuadros[f] || [];
    if (vis.protagonista && j && j.protagonista !== null) {
      var caja = L.cajaDe(cuadroActual, j.protagonista);
      if (caja) {
        dibujarTrazos(d.cuadros, j.protagonista, f, caja);
      } else {
        limpiarTrazos();
      }
    } else {
      limpiarTrazos();
    }

    // ④ Radar
    if (vis.radar && d.cancha[f]) {
      dibujarRadar(d.cancha[f], p);
      radarEl.hidden = false;
    } else {
      radarEl.hidden = true;
    }

    // ⑤ Ficha (alineaciones)
    fichaEl.hidden = !vis.ficha;
    if (fichaMovilEl) fichaMovilEl.hidden = !vis.ficha;

    // ⑦ MATEO
    var frase = L.fraseEn(t, d.jugadas);
    if (frase !== estado.fraseActual) {
      estado.fraseActual = frase;
      actualizarMateo(frase);
    }
    mateoEl.hidden = !(frase && estado.vozActiva);
    if (mateoMovilEl) mateoMovilEl.hidden = !(frase && estado.vozActiva);
  }

  // ── ⑥ Estela y triángulo ─────────────────────────────────────────────────
  var SVG_NS = 'http://www.w3.org/2000/svg';

  function limpiarTrazos() {
    while (trazosEl.firstChild) trazosEl.removeChild(trazosEl.firstChild);
  }

  function _cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function dibujarTrazos(cuadros, id, f, caja) {
    limpiarTrazos();
    var puntos = L.estela(cuadros, id, f, 15);
    if (puntos.length >= 2) {
      var poly = document.createElementNS(SVG_NS, 'polyline');
      poly.setAttribute('points', puntos.map(function (p) { return p[0] + ',' + p[1]; }).join(' '));
      poly.setAttribute('fill', 'none');
      poly.setAttribute('stroke', _cssVar('--color-ok') || '#1FC8B0');
      poly.setAttribute('stroke-width', '3');
      poly.setAttribute('stroke-linejoin', 'round');
      poly.setAttribute('stroke-linecap', 'round');
      trazosEl.appendChild(poly);
    }
    // Triángulo 10 px arriba de y1, centrado en x
    var cx = (caja[1] + caja[3]) / 2;
    var ty = caja[2] - 10;
    var tamanio = 8;
    var pts = [
      cx + ',' + (ty - tamanio),
      (cx - tamanio) + ',' + (ty + tamanio / 2),
      (cx + tamanio) + ',' + (ty + tamanio / 2),
    ].join(' ');
    var tri = document.createElementNS(SVG_NS, 'polygon');
    tri.setAttribute('points', pts);
    tri.setAttribute('fill', _cssVar('--color-ball') || '#A3E635');
    trazosEl.appendChild(tri);
  }

  // ── ④ Mini radar ─────────────────────────────────────────────────────────
  function dibujarRadar(entradaCancha, partido) {
    var svgEl = radarEl.querySelector('.tv-radar__svg');
    while (svgEl.firstChild) svgEl.removeChild(svgEl.firstChild);

    var VW = 1200, VH = 700;
    var colorPitch      = _cssVar('--color-pitch')       || '#0E1A16';
    var colorLines      = _cssVar('--color-pitch-lines') || '#2A4A3E';
    var colorTextSoft   = _cssVar('--color-text-soft')   || '#A1A1AE';
    var colorBall       = _cssVar('--color-ball')        || '#A3E635';

    // Fondo
    var rect = document.createElementNS(SVG_NS, 'rect');
    rect.setAttribute('width', VW); rect.setAttribute('height', VH);
    rect.setAttribute('fill', colorPitch);
    svgEl.appendChild(rect);

    // Líneas de cancha
    var lineas = [
      // Borde
      { x1: 10, y1: 10, x2: VW - 10, y2: 10 },
      { x1: VW - 10, y1: 10, x2: VW - 10, y2: VH - 10 },
      { x1: VW - 10, y1: VH - 10, x2: 10, y2: VH - 10 },
      { x1: 10, y1: VH - 10, x2: 10, y2: 10 },
      // Línea media
      { x1: VW / 2, y1: 10, x2: VW / 2, y2: VH - 10 },
    ];
    lineas.forEach(function (l) {
      var ln = document.createElementNS(SVG_NS, 'line');
      ln.setAttribute('x1', l.x1); ln.setAttribute('y1', l.y1);
      ln.setAttribute('x2', l.x2); ln.setAttribute('y2', l.y2);
      ln.setAttribute('stroke', colorLines); ln.setAttribute('stroke-width', '2');
      svgEl.appendChild(ln);
    });

    // Círculo central (radio 91.5)
    var cc = document.createElementNS(SVG_NS, 'circle');
    cc.setAttribute('cx', VW / 2); cc.setAttribute('cy', VH / 2);
    cc.setAttribute('r', '91.5');
    cc.setAttribute('fill', 'none'); cc.setAttribute('stroke', colorLines);
    cc.setAttribute('stroke-width', '2');
    svgEl.appendChild(cc);

    // Áreas 165×403 centradas en cada portería
    [[10, (VH - 403) / 2], [VW - 10 - 165, (VH - 403) / 2]].forEach(function (pos) {
      var ar = document.createElementNS(SVG_NS, 'rect');
      ar.setAttribute('x', pos[0]); ar.setAttribute('y', pos[1]);
      ar.setAttribute('width', '165'); ar.setAttribute('height', '403');
      ar.setAttribute('fill', 'none'); ar.setAttribute('stroke', colorLines);
      ar.setAttribute('stroke-width', '2');
      svgEl.appendChild(ar);
    });

    // Jugadores y balón
    var pts = L.puntosRadar(entradaCancha);
    pts.jugadores.forEach(function (jug) {
      var color = jug.team === 1 ? partido.local.color
                : jug.team === 0 ? partido.visita.color
                : colorTextSoft;
      // Escalar coordenadas (cancha 1200×700 dm → viewBox 1200×700)
      var cx = jug.x; var cy = jug.y;
      var circ = document.createElementNS(SVG_NS, 'circle');
      circ.setAttribute('cx', cx); circ.setAttribute('cy', cy);
      circ.setAttribute('r', '12');
      circ.setAttribute('fill', color);
      svgEl.appendChild(circ);
    });

    if (pts.balon) {
      var bal = document.createElementNS(SVG_NS, 'circle');
      bal.setAttribute('cx', pts.balon.x); bal.setAttribute('cy', pts.balon.y);
      bal.setAttribute('r', '8');
      bal.setAttribute('fill', colorBall);
      svgEl.appendChild(bal);
    }
  }

  // ── ⑤ Ficha ──────────────────────────────────────────────────────────────
  function _rellenarFicha(el, ficha, partido) {
    if (!el || !ficha) return;
    while (el.firstChild) el.removeChild(el.firstChild);

    var titulo = document.createElement('div');
    titulo.className = 'tv-ficha__titulo';
    titulo.textContent = 'Alineaciones';
    el.appendChild(titulo);

    var filas = L.filasFicha(ficha, partido);
    filas.forEach(function (fila) {
      var div = document.createElement('div');
      div.className = 'tv-ficha__fila';

      var cod = document.createElement('span');
      cod.className = 'tv-ficha__codigo';
      cod.textContent = fila.codigo;
      cod.style.color = fila.color;

      var esq = document.createElement('span');
      esq.className = 'tv-ficha__esquema';
      esq.textContent = fila.texto;

      div.appendChild(cod);
      div.appendChild(esq);
      el.appendChild(div);
    });

    var pie = document.createElement('div');
    pie.className = 'tv-ficha__pie';
    pie.textContent = ficha.estadio + ' · '
      + ficha.asistencia.toLocaleString('es-MX') + ' aficionados';
    el.appendChild(pie);
  }

  function construirFicha(ficha, partido) {
    _rellenarFicha(fichaEl, ficha, partido);
    _rellenarFicha(fichaMovilEl, ficha, partido);
  }

  // ── ⑦ Franja MATEO ───────────────────────────────────────────────────────
  function _rellenarMateo(el, frase) {
    while (el.firstChild) el.removeChild(el.firstChild);
    if (!frase) return;
    var prefijo = document.createElement('span');
    prefijo.className = 'tv-mateo__prefijo';
    prefijo.textContent = 'MATEO';
    var texto = document.createTextNode(' ' + frase);
    el.appendChild(prefijo);
    el.appendChild(texto);
  }

  function actualizarMateo(frase) {
    _rellenarMateo(mateoEl, frase);
    if (mateoMovilEl) _rellenarMateo(mateoMovilEl, frase);
  }

})();
