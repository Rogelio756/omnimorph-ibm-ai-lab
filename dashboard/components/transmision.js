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
  var radarMovilEl  = document.getElementById('tv-radar-movil');
  var escenarioEl   = document.getElementById('tv-escenario');
  var panelesToggleBtn = document.getElementById('tv-paneles-toggle');
  var panelEls = {
    local:  document.getElementById('tv-panel-local'),
    visita: document.getElementById('tv-panel-visita'),
  };
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

      // Radar: última posición válida por cuadro, leyenda y copia para móvil
      estado.ultimo = L.ultimoValido(datos.cancha || []);
      prepararRadar(p);

      // Paneles laterales (estilo transmisión de F1)
      construirPaneles(datos.paneles, p);

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

  // ── Modo TV / Modo estadísticas ─────────────────────────────────────────
  var CLAVE_PANELES = 'omnimorph.transmision.paneles';
  function aplicarPaneles(activos) {
    escenarioEl.classList.toggle('tv-escenario--sin-paneles', !activos);
    panelesToggleBtn.setAttribute('aria-pressed', String(activos));
    panelesToggleBtn.textContent = activos ? 'Ocultar estadísticas' : 'Mostrar estadísticas';
    actualizarEscala();
  }
  var panelesGuardado = null;
  try { panelesGuardado = localStorage.getItem(CLAVE_PANELES); } catch (e) { /* sin almacenamiento */ }
  aplicarPaneles(panelesGuardado !== '0');
  panelesToggleBtn.addEventListener('click', function () {
    var activos = panelesToggleBtn.getAttribute('aria-pressed') !== 'true';
    aplicarPaneles(activos);
    try { localStorage.setItem(CLAVE_PANELES, activos ? '1' : '0'); } catch (e) { /* sin almacenamiento */ }
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

    // ④ Radar (fijo después de las alineaciones)
    if (vis.radar) {
      var prot = vis.protagonista && j ? j.protagonista : null;
      dibujarRadar(f, prot, p);
    }
    radarEl.hidden = !vis.radar;
    if (radarMovilEl) radarMovilEl.hidden = !vis.radar;

    // ⑤ Ficha (alineaciones, solo al inicio)
    fichaEl.hidden = !vis.ficha;
    if (fichaMovilEl) fichaMovilEl.hidden = !vis.ficha;

    // Paneles laterales
    actualizarPaneles(t, vis.protagonista && j ? j.protagonista : null);

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

  // ── ④ Radar ──────────────────────────────────────────────────────────────
  // La cancha es fija en el HTML; aquí solo se dibujan los puntos.
  var radares = [];

  function prepararRadar(partido) {
    radares = [radarEl];
    if (radarMovilEl) {
      var copia = radarEl.cloneNode(true);
      copia.removeAttribute('id');
      copia.hidden = false;
      copia.classList.add('tv-radar--movil');
      radarMovilEl.appendChild(copia);
      radares.push(copia);
    }
    radares.forEach(function (r) {
      [['local', partido.local], ['visita', partido.visita]].forEach(function (par) {
        var el = r.querySelector('[data-lado="' + par[0] + '"]');
        if (el) {
          el.textContent = par[1].codigo;
          el.style.setProperty('--tv-equipo-color', par[1].color);
        }
      });
    });
  }

  function dibujarRadar(f, protagonista, partido) {
    var d  = estado.datos;
    var lv = estado.ultimo ? estado.ultimo[f] : -1;
    var enEspera = lv >= 0 && lv !== f;
    var html = '';

    if (lv >= 0) {
      var pts = L.puntosRadar(d.cancha[lv]);
      var colorRef  = _cssVar('--color-text-soft') || '#9CA3AF';
      var colorBall = _cssVar('--color-ball')      || '#A3E635';
      pts.jugadores.forEach(function (jug) {
        var color = jug.team === 1 ? partido.local.color
                  : jug.team === 0 ? partido.visita.color
                  : colorRef;
        var r = jug.team === 2 ? 18 : 26;
        if (protagonista !== null && jug.id === protagonista) {
          html += '<circle cx="' + jug.x + '" cy="' + jug.y + '" r="42" fill="none" stroke="' +
                  colorBall + '" stroke-width="5"/>';
        }
        html += '<circle cx="' + jug.x + '" cy="' + jug.y + '" r="' + r + '" fill="' + color +
                '" stroke="#111" stroke-width="3"/>';
      });
      // En toma cerrada no se sabe dónde está el balón: no se dibuja
      if (!enEspera && pts.balon) {
        html += '<circle cx="' + pts.balon.x + '" cy="' + pts.balon.y + '" r="16" fill="' +
                colorBall + '" stroke="#111" stroke-width="3"/>';
      }
    }

    radares.forEach(function (r) {
      var g = r.querySelector('.tv-radar__puntos');
      if (g) g.innerHTML = html;
      var esp = r.querySelector('.tv-radar__espera');
      if (esp) esp.hidden = !enEspera;
    });
  }

  // ── Paneles laterales (lenguaje de aficionado) ───────────────────────────
  function _el(tag, clase, texto) {
    var e = document.createElement(tag);
    if (clase) e.className = clase;
    if (texto != null) e.textContent = texto;
    return e;
  }

  function _barra(clase) {
    var b = _el('div', 'tv-panel__barra ' + (clase || ''));
    b.appendChild(_el('span', 'tv-panel__relleno'));
    return b;
  }

  function _cifra(valor, etiqueta) {
    var c = _el('div', 'tv-panel__cifra');
    c.appendChild(_el('span', 'tv-panel__num', valor));
    c.appendChild(_el('span', 'tv-panel__etq', etiqueta));
    return c;
  }

  function construirPaneles(paneles, partido) {
    if (!paneles) {
      escenarioEl.classList.add('tv-escenario--sin-paneles');
      panelesToggleBtn.hidden = true;
      return;
    }
    ['visita', 'local'].forEach(function (lado) {
      var eq = paneles[lado];
      var el = panelEls[lado];
      if (!el || !eq) return;
      el.style.setProperty('--tv-equipo-color', partido[lado].color);
      while (el.firstChild) el.removeChild(el.firstChild);

      // Encabezado
      var cab = _el('header', 'tv-panel__cab');
      cab.appendChild(_el('span', 'tv-panel__nombre', eq.nombre));
      cab.appendChild(_el('span', 'tv-panel__sub',
        [eq.esquema, eq.entrenador].filter(Boolean).join(' · ')));
      el.appendChild(cab);

      // Ahora (cambia con el video)
      var ahora = _el('section', 'tv-panel__bloque');
      ahora.appendChild(_el('h3', 'tv-panel__titulo', 'Ahora mismo'));
      ahora.appendChild(_el('p', 'tv-panel__estado', ''));
      ahora.appendChild(_el('p', 'tv-panel__frase tv-panel__frase--pos', ''));
      ahora.appendChild(_barra('tv-panel__barra--cancha'));
      ahora.appendChild(_el('p', 'tv-panel__frase tv-panel__frase--rival', ''));
      ahora.appendChild(_barra('tv-panel__barra--rival'));
      ahora.appendChild(_el('p', 'tv-panel__jugada', ''));
      el.appendChild(ahora);

      // El partido (fijo)
      var pp = eq.partido || {};
      var part = _el('section', 'tv-panel__bloque');
      part.appendChild(_el('h3', 'tv-panel__titulo', 'En el partido'));
      var cifras = _el('div', 'tv-panel__cifras');
      if (pp.goles != null) cifras.appendChild(_cifra(String(pp.goles), pp.goles === 1 ? 'gol' : 'goles'));
      if (pp.tiros_totales != null) cifras.appendChild(_cifra(String(pp.tiros_totales), 'tiros'));
      if (pp.tiros_a_puerta != null) cifras.appendChild(_cifra(String(pp.tiros_a_puerta), 'a puerta'));
      part.appendChild(cifras);
      if (pp.posesion_pct != null) {
        part.appendChild(_el('p', 'tv-panel__frase', 'Tuvo el balón el ' + pp.posesion_pct + ' % del tiempo'));
        var bp = _barra();
        bp.firstChild.style.width = Math.max(0, Math.min(100, pp.posesion_pct)) + '%';
        part.appendChild(bp);
      }
      if (eq.goles && eq.goles.length) {
        var ul = _el('ul', 'tv-panel__goles');
        eq.goles.forEach(function (g) {
          var li = _el('li');
          li.appendChild(_el('span', 'tv-panel__minuto', g.minuto + '′'));
          li.appendChild(document.createTextNode(' ' + g.nombre));
          ul.appendChild(li);
        });
        part.appendChild(ul);
      }
      part.appendChild(_el('p', 'tv-panel__fuente', 'Partido completo · fuentes públicas'));
      el.appendChild(part);

      // ¿Sabías que…? (rota por jugada)
      var cur = _el('section', 'tv-panel__bloque tv-panel__bloque--curioso');
      cur.appendChild(_el('h3', 'tv-panel__titulo', '¿Sabías que…?'));
      cur.appendChild(_el('p', 'tv-panel__curioso', ''));
      cur.appendChild(_el('span', 'tv-panel__origen', ''));
      el.appendChild(cur);
    });
    estado.panelClave = '';
    actualizarPaneles(0, null);
  }

  function actualizarPaneles(t, protagonista) {
    var d = estado.datos;
    var pn = d && d.paneles;
    if (!pn) return;
    var i = L.jugadaEn(t, pn.tramos);
    var clave = i + '|' + protagonista;
    if (clave === estado.panelClave) return;
    estado.panelClave = clave;
    var tr = i >= 0 ? pn.tramos[i] : null;

    ['visita', 'local'].forEach(function (lado) {
      var eq = pn[lado], el = panelEls[lado];
      if (!el || !eq || !el.firstChild) return;
      var m = tr && tr.equipos ? tr.equipos[eq.codigo] : null;

      var est = el.querySelector('.tv-panel__estado');
      est.textContent = !tr ? '' : tr.territorio === eq.codigo ? 'Está adelantado'
                      : tr.territorio === 'repartido' ? 'Juego parejo' : 'Está en su mitad';
      est.classList.toggle('tv-panel__estado--fuerte', !!tr && tr.territorio === eq.codigo);

      var pos = m && m.posicion_m != null ? Math.round(m.posicion_m) : null;
      var riv = m && m.pct_campo_rival != null ? Math.round(m.pct_campo_rival) : null;
      el.querySelector('.tv-panel__frase--pos').textContent =
        pos == null ? '' : 'Juega a ' + pos + ' m de su portería';
      el.querySelector('.tv-panel__barra--cancha .tv-panel__relleno').style.width =
        (pos == null ? 0 : Math.min(100, pos / 105 * 100)) + '%';
      el.querySelector('.tv-panel__frase--rival').textContent =
        riv == null ? '' : riv + ' % de sus jugadores en campo rival';
      el.querySelector('.tv-panel__barra--rival .tv-panel__relleno').style.width =
        (riv == null ? 0 : riv) + '%';

      var jug = protagonista != null ? d.jugadores[String(protagonista)] : null;
      var jugEl = el.querySelector('.tv-panel__jugada');
      var tiene = jug && jug.team === d.partido[lado].team && jug.etiqueta.indexOf('Jugador') !== 0;
      jugEl.textContent = tiene ? 'En la jugada: ' + jug.etiqueta.replace(' · ', ' ') : '';
      jugEl.hidden = !tiene;

      var dc = L.datoCurioso(eq.curiosos, i);
      el.querySelector('.tv-panel__curioso').textContent = dc ? dc.texto : '';
      el.querySelector('.tv-panel__origen').textContent =
        !dc ? '' : dc.origen === 'granite' ? 'Escrito por IBM Granite' : 'Dato del partido';
    });
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
