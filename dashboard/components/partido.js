/**
 * components/partido.js
 * OMNIMORPH — Página del partido Brasil 1-7 Alemania.
 * Fuente: ../data/partido/partido.json (scripts/export_dashboard_data.py).
 * Todo el texto de los datos se inserta con textContent, nunca como HTML.
 */
(function () {
  'use strict';

  var TABS = ['ficha', 'fichero', 'comparativa', 'goles', 'muller'];
  var PERIODOS = [['primer_tiempo', '1T'], ['segundo_tiempo', '2T'], ['tiempo_completo', 'Total']];
  var EQUIPOS = [['brasil', 'Brasil', 'bra'], ['alemania', 'Alemania', 'ger']];

  // [clave, etiqueta, decimales, nota]
  var METRICAS = [
    ['posesion_pct', 'Posesión (%)', 1, 'por tiempo sin confirmar'],
    ['tiros_totales', 'Tiros totales', 0, ''],
    ['tiros_a_puerta', 'Tiros a puerta', 0, 'Alemania por tiempo: derivado'],
    ['tiros_dentro_area', 'Tiros dentro del área', 0, ''],
    ['tiros_fuera_area', 'Tiros fuera del área', 0, ''],
    ['xg_esperado', 'xG (estimado)', 2, 'estimado, no oficial'],
    ['precision_pases_pct', 'Precisión de pases (%)', 1, ''],
    ['corners', 'Córners', 0, ''],
    ['faltas_cometidas', 'Faltas cometidas', 0, ''],
    ['fueras_de_juego', 'Fueras de juego', 0, ''],
    ['atajadas_portero', 'Atajadas', 0, ''],
    ['recuperaciones', 'Recuperaciones', 0, ''],
  ];

  var FOTO_ESTADIO = 'https://commons.wikimedia.org/wiki/File:Est%C3%A1dio_Governador_Magalh%C3%A3es_Pinto_-_Belo_Horizonte_-_20240626170354.jpg';

  var D = null;
  var metricaActiva = 'tiros_totales';
  var golActivo = 0;
  var dibujado = {};

  function $(id) { return document.getElementById(id); }

  /** Crea un elemento: attrs {class, text, ...atributos}; children = nodos o textos. */
  function el(tag, attrs) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k];
      else if (k === 'class') node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (function agregar(hijos) {
      hijos.forEach(function (c) {
        if (c == null) return;
        if (Array.isArray(c)) { agregar(c); return; }
        node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      });
    })(Array.prototype.slice.call(arguments, 2));
    return node;
  }

  function svg(tag, attrs) {
    var node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    return node;
  }

  function num(v, dec) {
    return Number(v).toLocaleString('es-MX', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function vaciar(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  // ── Datos ────────────────────────────────────────────────────────────────
  fetch('../data/partido/partido.json')
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) { D = data; iniciar(); })
    .catch(function () {
      $('data-error').hidden = false;
      $('tabs').hidden = true;
      window.OmniTransicion.falla('No pudimos cargar los datos del partido');
    });

  function iniciar() {
    var info = D.partido;
    $('subtitle').textContent = info.fase + ' · ' + info.competicion + ' · ' + info.fecha +
      ' · ' + info.estadio + ', ' + info.ciudad;

    TABS.forEach(function (id) {
      $('tab-' + id).addEventListener('click', function () { mostrar(id); });
      $('tab-' + id).addEventListener('keydown', function (e) {
        var i = TABS.indexOf(id);
        if (e.key === 'ArrowRight') mostrar(TABS[(i + 1) % TABS.length], true);
        if (e.key === 'ArrowLeft') mostrar(TABS[(i + TABS.length - 1) % TABS.length], true);
      });
    });
    window.addEventListener('hashchange', function () { mostrar(desdeHash(), false, true); });
    mostrar(desdeHash(), false, true);
  }

  function desdeHash() {
    var h = location.hash.replace('#', '');
    return TABS.indexOf(h) >= 0 ? h : TABS[0];
  }

  function mostrar(id, enfocar, sinHash) {
    TABS.forEach(function (t) {
      var activa = t === id;
      $('tab-' + t).setAttribute('aria-selected', activa ? 'true' : 'false');
      $('tab-' + t).tabIndex = activa ? 0 : -1;
      $('panel-' + t).hidden = !activa;
    });
    if (enfocar) $('tab-' + id).focus();
    if (!sinHash && location.hash !== '#' + id) history.replaceState(null, '', '#' + id);
    if (!dibujado[id]) { dibujado[id] = true; RENDER[id](); }
  }

  var RENDER = { ficha: renderFicha, fichero: renderFichero, comparativa: renderComparativa, goles: renderGoles, muller: renderMuller };

  // ── Ficha previa ─────────────────────────────────────────────────────────
  function stat(label, valor, hint, esTexto) {
    return el('div', { class: 'stat' },
      el('span', { class: 'stat__label', text: label }),
      el('span', { class: 'stat__value' + (esTexto ? ' stat__value--text' : ''), text: valor }),
      hint ? el('span', { class: 'stat__hint', text: hint }) : null);
  }

  function renderFicha() {
    var info = D.partido, clima = info.condiciones_climaticas, arb = info.arbitro;
    var host = $('panel-ficha');
    vaciar(host);
    host.appendChild(el('figure', { class: 'estadio' },
      el('div', { class: 'estadio__foto' },
        el('img', { src: '../assets/estadio/mineirao.jpg', alt: 'Fachada de concreto del estadio Mineirão' }),
        el('div', { class: 'estadio__nombre' },
          el('strong', { text: 'Mineirão' }),
          el('span', { text: info.ciudad }))),
      el('figcaption', { class: 'estadio__credito' }, 'Foto de 2024: ',
        el('a', { href: FOTO_ESTADIO, target: '_blank', rel: 'noopener', text: 'Rodrigo Rocatto' }), ', ',
        el('a', { href: 'https://creativecommons.org/licenses/by-sa/4.0/', target: '_blank', rel: 'noopener', text: 'CC BY-SA 4.0' }),
        ', recortada')));
    host.appendChild(el('div', { class: 'stat-row' },
      stat('Marcador final', info.resultado.marcador_final, 'Descanso ' + info.resultado.primer_tiempo),
      stat('Asistencia', num(info.asistencia, 0), 'Mineirão'),
      stat('Clima', clima.temperatura_c + ' °C',
        clima.cielo + ' · humedad ' + clima.humedad_pct + '% · viento ' + clima.viento_kmh + ' km/h'),
      stat('Árbitro', arb.principal, arb.pais, true)));
    host.appendChild(el('p', { class: 'caption',
      text: 'Asistentes: ' + arb.asistente_1 + ' y ' + arb.asistente_2 + ' · Cuarto árbitro: ' + arb.cuarto_arbitro }));

    var split = el('div', { class: 'split' });
    EQUIPOS.forEach(function (e) {
      var eq = D.equipos[e[0]];
      var col = el('div');
      col.appendChild(el('div', { class: 'team-head' },
        el('div', { class: 'team-head__name' }, el('span', { class: 'swatch swatch--' + e[2] }), eq.pais),
        el('span', { class: 'team-head__meta',
          text: 'Entrenador: ' + eq.entrenador + ' · Esquema: ' + eq.esquema_inicial + ' · Capitán: ' + eq.capitan })));
      eq.bajas_previas.forEach(function (b) {
        col.appendChild(el('div', { class: 'absence' },
          el('span', { class: 'absence__name', text: 'Baja: ' + b.nombre }),
          el('span', { class: 'absence__reason', text: b.motivo })));
      });
      split.appendChild(col);
    });
    host.appendChild(split);
  }

  function renderFichero() {
    window.OmniFichero.render($('panel-fichero'), D, el);
  }

  // ── Comparativa 1T / 2T ──────────────────────────────────────────────────
  function metricaPorClave(clave) {
    return METRICAS.filter(function (m) { return m[0] === clave; })[0];
  }

  function renderComparativa() {
    var host = $('panel-comparativa');
    vaciar(host);
    var pills = el('div', { class: 'pillbar', role: 'group', 'aria-label': 'Métrica' });
    METRICAS.forEach(function (m) {
      var b = el('button', { class: 'btn btn--outline btn-xs', type: 'button', 'data-metrica': m[0],
        'aria-pressed': m[0] === metricaActiva ? 'true' : 'false', text: m[1] });
      b.addEventListener('click', function () { metricaActiva = m[0]; marcarPills(); dibujarGrafico(); });
      pills.appendChild(b);
    });
    host.appendChild(pills);
    host.appendChild(el('div', { class: 'legend', 'aria-label': 'Leyenda' },
      el('span', { class: 'legend__item' }, el('span', { class: 'swatch swatch--bra' }), 'Brasil'),
      el('span', { class: 'legend__item' }, el('span', { class: 'swatch swatch--ger' }), 'Alemania')));
    host.appendChild(el('div', { class: 'chart', id: 'chart' }));
    host.appendChild(el('div', { class: 'section-label', text: 'Todas las métricas' }));
    host.appendChild(tablaCompleta());
    dibujarGrafico();
  }

  function marcarPills() {
    document.querySelectorAll('#panel-comparativa [data-metrica]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-metrica') === metricaActiva ? 'true' : 'false');
      b.className = 'btn btn-xs ' + (b.getAttribute('data-metrica') === metricaActiva ? 'btn--primary' : 'btn--outline');
    });
  }

  function valor(clave, periodo, equipo) {
    return D.estadisticas.resumen_comparativo[periodo][clave][equipo];
  }

  function techoGrafico(max) {
    if (max <= 0) return 1;
    var exp = Math.pow(10, Math.floor(Math.log(max) / Math.LN10));
    var f = max / exp;
    var paso = f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10;
    return paso * exp;
  }

  function dibujarGrafico() {
    marcarPills();
    var m = metricaPorClave(metricaActiva);
    var host = $('chart');
    vaciar(host);

    var W = 640, H = 300, ML = 44, MR = 12, MT = 28, MB = 34;
    var series = [['1T', 'primer_tiempo'], ['2T', 'segundo_tiempo']];
    var maxV = 0;
    series.forEach(function (s) { EQUIPOS.forEach(function (e) { maxV = Math.max(maxV, valor(m[0], s[1], e[0])); }); });
    var techo = techoGrafico(maxV);
    var y = function (v) { return MT + (H - MT - MB) * (1 - v / techo); };

    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img',
      'aria-label': m[1] + ' de Brasil y Alemania en el primer y segundo tiempo' });
    for (var t = 0; t <= 4; t++) {
      var v = techo * t / 4;
      s.appendChild(svg('line', { class: 'chart__grid', x1: ML, x2: W - MR, y1: y(v), y2: y(v) }));
      s.appendChild(svg('text', { x: ML - 8, y: y(v) + 4, 'text-anchor': 'end', text: num(v, techo < 5 ? 1 : 0) }));
    }
    var ancho = (W - ML - MR) / series.length;
    var barra = Math.min(56, ancho / 3);
    series.forEach(function (ser, i) {
      var cx = ML + ancho * i + ancho / 2;
      EQUIPOS.forEach(function (e, j) {
        var val = valor(m[0], ser[1], e[0]);
        var x = cx + (j === 0 ? -barra - 1 : 1);
        var alto = Math.max(H - MB - y(val), 0);
        var r = svg('rect', { class: 'bar bar--' + e[2], x: x, y: H - MB - alto, width: barra, height: alto,
          rx: 3, tabindex: 0, 'data-tip': e[1] + ' · ' + ser[0] + ': ' + num(val, m[2]) + ' ' + m[1].toLowerCase(),
          'aria-label': e[1] + ', ' + ser[0] + ', ' + m[1] + ': ' + num(val, m[2]) });
        s.appendChild(r);
        s.appendChild(svg('text', { class: 'chart__value', x: x + barra / 2, y: H - MB - alto - 6,
          'text-anchor': 'middle', text: num(val, m[2]) }));
        s.appendChild(svg('text', { x: x + barra / 2, y: H - MB + 14, 'text-anchor': 'middle', text: e[2].toUpperCase() }));
      });
      s.appendChild(svg('text', { x: cx, y: H - 6, 'text-anchor': 'middle', text: ser[0] }));
    });
    host.appendChild(s);
    if (m[3]) host.appendChild(el('p', { class: 'chart__note', text: 'Nota: ' + m[3] + '.' }));
    activarTooltip(host);
  }

  function activarTooltip(host) {
    var tip = $('tip');
    function poner(e) {
      var t = e.target.getAttribute && e.target.getAttribute('data-tip');
      if (!t) { tip.hidden = true; return; }
      tip.textContent = t;
      tip.hidden = false;
      var rect = e.target.getBoundingClientRect();
      var x = e.clientX != null && e.type.indexOf('pointer') === 0 ? e.clientX + 14 : rect.right + 8;
      var yy = e.clientY != null && e.type.indexOf('pointer') === 0 ? e.clientY - 34 : rect.top;
      tip.style.left = Math.min(x, window.innerWidth - tip.offsetWidth - 8) + 'px';
      tip.style.top = Math.max(yy, 8) + 'px';
    }
    host.addEventListener('pointermove', poner);
    host.addEventListener('pointerleave', function () { tip.hidden = true; });
    host.addEventListener('focusin', poner);
    host.addEventListener('focusout', function () { tip.hidden = true; });
  }

  function tablaCompleta() {
    var thead = el('thead', null,
      el('tr', null, el('th', { rowspan: '2', text: 'Métrica' }),
        el('th', { class: 'group group--bra', colspan: '3', text: 'Brasil' }),
        el('th', { class: 'group group--ger', colspan: '3', text: 'Alemania' })),
      el('tr', null, PERIODOS.concat(PERIODOS).map(function (p, i) {
        return el('th', { class: 'num' + (i % 3 === 0 ? ' group' : ''), text: p[1] });
      })));
    var tbody = el('tbody');
    METRICAS.forEach(function (m) {
      var fila = el('tr', null, el('td', null, m[1], m[3] ? el('span', { class: 'note', text: m[3] }) : null));
      EQUIPOS.forEach(function (e) {
        PERIODOS.forEach(function (p, i) {
          fila.appendChild(el('td', { class: 'num' + (i === 0 ? ' group' : ''), text: num(valor(m[0], p[0], e[0]), m[2]) }));
        });
      });
      tbody.appendChild(fila);
    });
    return el('div', { class: 'table-wrap' }, el('table', { class: 'tbl' }, thead, tbody));
  }

  // ── Los 8 goles ──────────────────────────────────────────────────────────
  function renderGoles() {
    var host = $('panel-goles');
    vaciar(host);
    host.appendChild(el('div', { class: 'figure' }, el('img', { src: '../data/partido/mapa_8_goles.svg',
      alt: 'Mapa de la cancha con la posición de remate de los 8 goles' })));
    host.appendChild(el('p', { class: 'caption',
      text: 'El tamaño de cada punto indica el xG estimado. Las coordenadas están normalizadas: Alemania siempre ataca hacia la izquierda, también en el 2T.' }));

    var tbody = el('tbody');
    D.goles.forEach(function (g, i) {
      var fila = el('tr', { 'data-row': String(i), tabindex: 0, 'aria-selected': i === golActivo ? 'true' : 'false' },
        el('td', { class: 'num', text: g.minuto + "'" }),
        el('td', { class: 'num', text: g.marcador_momento }),
        el('td', { text: g.anotador.nombre }),
        el('td', { class: 'soft', text: g.asistente.nombre }),
        el('td', { class: 'soft', text: g.tipo_jugada }),
        el('td', { class: 'num', text: num(g.xg, 2) }),
        el('td', { class: 'num', text: num(g.distancia_porteria_m, 1) }));
      var elegir = function () { golActivo = i; marcarGol(); };
      fila.addEventListener('click', elegir);
      fila.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); elegir(); } });
      tbody.appendChild(fila);
    });
    host.appendChild(el('div', { class: 'table-wrap' }, el('table', { class: 'tbl', id: 'tabla-goles' },
      el('thead', null, el('tr', null, el('th', { text: 'Min' }), el('th', { class: 'num', text: 'Marcador' }),
        el('th', { text: 'Anotador' }), el('th', { text: 'Asistente' }), el('th', { text: 'Jugada' }),
        el('th', { class: 'num', text: 'xG est.' }), el('th', { class: 'num', text: 'Dist. (m)' }))),
      tbody)));
    host.appendChild(el('div', { class: 'detail', id: 'detalle-gol', 'aria-live': 'polite' }));
    marcarGol();
  }

  function marcarGol() {
    document.querySelectorAll('#tabla-goles tr[data-row]').forEach(function (r) {
      r.setAttribute('aria-selected', Number(r.getAttribute('data-row')) === golActivo ? 'true' : 'false');
    });
    var g = D.goles[golActivo], box = $('detalle-gol');
    vaciar(box);
    box.appendChild(el('p', null, el('strong', { text: g.minuto + "' · " + g.anotador.nombre + ' (' + g.marcador_momento + ')' })));
    box.appendChild(el('p', null, el('strong', { text: 'Análisis táctico. ' }), g.nota_tactica));
    box.appendChild(el('p', null, el('strong', { text: 'Relato. ' }), g.narracion));
  }

  // ── Gol de Müller ────────────────────────────────────────────────────────
  function renderMuller() {
    var host = $('panel-muller');
    vaciar(host);
    var jugada = D.gol_muller.metadatos_jugada;
    var ventanas = D.gol_muller.ventanas_tacticas;
    var met = ventanas[ventanas.length - 1].metricas;
    host.appendChild(el('p', { class: 'caption',
      text: jugada.minuto_oficial + "' · " + jugada.anotador.nombre + ' · ' + jugada.tipo_jugada + ' · Reloj ' + jugada.reloj_partido }));
    host.appendChild(el('div', { class: 'figure' }, el('img', { src: '../data/partido/radar_gol_muller.svg',
      alt: 'Radar cenital de la pantalla de Klose y Höwedes y el remate de Müller' })));
    host.appendChild(el('div', { class: 'stat-row' },
      stat('Distancia', num(met.distancia_remate_m, 1) + ' m'),
      stat('xG (estimado)', num(met.xg, 2)),
      stat('Separación de marca', num(met.separacion_marca_radio_m, 1) + ' m', 'sin fuente independiente'),
      stat('Velocidad del remate', num(met.velocidad_remate_kmh, 1) + ' km/h', 'sin fuente independiente')));
    host.appendChild(el('div', { class: 'detail' },
      el('p', null, el('strong', { text: 'Hasta el gol. ' }), D.gol_muller.estadisticas_acumuladas_minuto_11.resumen_tramo_inicial)));
    ventanas.forEach(function (v) {
      host.appendChild(el('details', { class: 'window' },
        el('summary', { text: 'Ventana ' + v.ventana_id + ' · ' + v.t0 + '–' + v.t1 + ' s · ' + v.fase }),
        el('div', { class: 'detail' }, el('p', { text: v.texto_tactico }), el('p', { text: v.texto_narracion }))));
    });
  }
})();
