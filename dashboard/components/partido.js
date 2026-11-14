/**
 * components/partido.js
 * OMNIMORPH — Página del partido activo.
 * Fuente: ../data/partido/partido.json (scripts/export_dashboard_data.py).
 * Todo el texto de los datos se inserta con textContent, nunca como HTML.
 */
(function () {
  'use strict';

  var TODOS_TABS = ['ficha', 'fichero', 'comparativa', 'goles', 'eventos', 'muller'];
  var TABS = ['ficha', 'fichero'];
  var PERIODOS_TODOS = [['primer_tiempo', '1T'], ['segundo_tiempo', '2T'], ['tiempo_completo', 'Total']];
  var CLASES_EQ_DEFAULT = ['bra', 'ger'];
  var CLASES_EQ_UNIFORME = ['partido-a', 'partido-b'];
  var EQUIPOS = [];

  var FOTO_MINEIRAO = 'https://commons.wikimedia.org/wiki/File:Est%C3%A1dio_Governador_Magalh%C3%A3es_Pinto_-_Belo_Horizonte_-_20240626170354.jpg';

  var D = null;
  var metricaActiva = 'tiros_totales';
  var golActivo = 0;
  var dibujado = {};
  var eventosEnlazados = false;

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
    if (v == null || v === '' || isNaN(Number(v))) return '—';
    return Number(v).toLocaleString('es-MX', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function vaciar(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  var NOMBRES_NO_DISPONIBLE = {
    xg_goles_esperados: 'Goles esperados (xG)',
    xa_asistencias_esperadas: 'Asistencias esperadas (xA)',
    distancia_recorrida_km: 'Distancia recorrida por jugador y por equipo',
    velocidad_maxima_kmh_y_sprints: 'Velocidad máxima y número de sprints',
    mapas_de_calor_y_tracking_25fps: 'Mapas de calor y seguimiento de jugadores',
    redes_de_pases_matriz_jugador_a_jugador: 'Red de pases entre jugadores',
    ppda_intensidad_presion: 'Intensidad de la presión (PPDA)',
    coordenadas_shotmap_de_todos_los_remates: 'Mapa con la posición de todos los remates (solo hay la de los goles)',
    corte_1t_2t_de_recuperaciones_por_equipo: 'Recuperaciones por equipo en cada tiempo',
    temperatura_humedad_viento: 'Temperatura, humedad y viento'
  };

  /** Envuelve un diagrama en un enlace que lo abre a tamaño completo en otra pestaña. */
  function enlaceAmpliar(img) {
    return el('a', { href: img.getAttribute('src'), target: '_blank', rel: 'noopener',
      class: 'figure__ampliar', 'aria-label': 'Abrir en grande: ' + img.getAttribute('alt') }, img);
  }

  /** Uniforme del partido en texto (camiseta, pantaloneta, medias), de campo y de portero. */
  function bloqueUniforme(detalle) {
    if (!detalle) return null;
    var filas = [];
    [['campo', 'Jugadores de campo'], ['portero', 'Portero']].forEach(function (par) {
      var u = detalle[par[0]];
      if (!u) return;
      if (u.estado === 'no_disponible' || !u.camiseta) {
        filas.push(el('p', null, el('strong', { text: par[1] + '. ' }), 'Sin foto verificada del partido: no se describe.'));
        return;
      }
      var partes = [['Camiseta', u.camiseta], ['Pantaloneta', u.pantaloneta], ['Medias', u.medias]]
        .filter(function (p) { return p[1]; })
        .map(function (p) { return p[0] + ': ' + p[1]; });
      filas.push(el('p', null, el('strong', { text: par[1] + (u.marca ? ' · ' + u.marca : '') + '. ' }),
        partes.join(' ')));
    });
    if (!filas.length) return null;
    return el('details', { class: 'window uniforme' },
      el('summary', { text: 'Uniforme del partido' }),
      el('div', { class: 'detail' }, filas));
  }

  /** Quita del texto las marcas de fuente pensadas para analistas, no para el club. */
  function sinMarcasFuente(texto) {
    return String(texto || '')
      .replace(/\s*\((?:FIFA Timeline pos|pos(?:ición)? FIFA)[^)]*\)/gi, '')
      .replace(/\s*\((?:ESPN\/TM|ESPN|TM|FIFA|Opta|FotMob)\)/g, '')
      .replace(/\s*\[estimacion_tactica\]\s*/g, ' ')
      .trim();
  }

  /** Relato de la jugada sin el marcador al inicio («2-0 Acción…»): ya está en su columna. */
  function textoJugada(texto) {
    return sinMarcasFuente(texto).replace(/^\d+\s*[-–]\s*\d+\s+/, '');
  }

  function metricasDefinidas() {
    var ncd = (D && D.estadisticas && D.estadisticas.notas_calidad_datos) || null;
    var xgEstimado = Boolean(ncd && ncd.xg);
    return [
      ['posesion_pct', 'Posesión (%)', 1, ncd && ncd.posesion_por_tiempo ? 'por tiempo sin confirmar' : ''],
      ['tiros_totales', 'Tiros totales', 0, ''],
      ['tiros_a_puerta', 'Tiros a puerta', 0, ncd && ncd.tiros_a_puerta_alemania_por_tiempo ? EQUIPOS[1][1] + ' por tiempo: derivado' : ''],
      ['tiros_dentro_area', 'Tiros dentro del área', 0, ''],
      ['tiros_fuera_area', 'Tiros fuera del área', 0, ''],
      ['xg_esperado', xgEstimado ? 'xG (estimado)' : 'xG', 2, xgEstimado ? 'estimado, no oficial' : ''],
      ['precision_pases_pct', 'Precisión de pases (%)', 1, ''],
      ['corners', 'Córners', 0, ''],
      ['faltas_cometidas', 'Faltas cometidas', 0, ''],
      ['fueras_de_juego', 'Fueras de juego', 0, ''],
      ['atajadas_portero', 'Atajadas', 0, ''],
      ['recuperaciones', 'Recuperaciones', 0, ''],
    ];
  }

  function tienePorTiempo() {
    var rc = D && D.estadisticas && D.estadisticas.resumen_comparativo;
    if (!rc || !rc.primer_tiempo || !rc.segundo_tiempo) return false;
    return metricasDefinidas().some(function (m) {
      var c = m[0];
      return rc.primer_tiempo[c] && EQUIPOS.some(function (e) { return rc.primer_tiempo[c][e[0]] != null; });
    });
  }

  function periodosActivos() {
    return tienePorTiempo() ? PERIODOS_TODOS : [['tiempo_completo', 'Total']];
  }

  // ── Datos ────────────────────────────────────────────────────────────────
  fetch('../data/partido/partido.json')
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) { D = data; if (D.pendiente) enPreparacion(); else iniciar(); })
    .catch(function () {
      $('data-error').hidden = false;
      $('tabs').hidden = true;
      window.OmniTransicion.falla('No pudimos cargar los datos del partido');
    });

  // Partido activo sin datos verificados todavía: no se muestran pestañas ni cifras.
  function enPreparacion() {
    document.title = 'MATEO — ' + D.titulo;
    $('hub-titulo').textContent = D.titulo;
    $('subtitle').textContent = D.competicion;
    if (D.etiqueta) $('hub-chip').textContent = D.etiqueta;
    $('hub-calidad').hidden = true;
    $('hub-pendiente').hidden = false;
    $('tabs').hidden = true;
  }

  function pintarAvisoCalidad() {
    var aviso = $('hub-calidad');
    var avisoTexto = $('hub-calidad-texto');
    if (!aviso || !avisoTexto) return;
    vaciar(avisoTexto);
    if (D.validado === false) {
      aviso.hidden = false;
      var linkFuentes = el('a', {
        href: '#fuentes-partido',
        style: 'text-decoration: underline;',
        text: 'Ver fuentes consultadas'
      });
      linkFuentes.addEventListener('click', function (e) {
        e.preventDefault();
        mostrar('ficha');
        var det = $('fuentes-partido');
        if (det) {
          det.open = true;
          det.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
      avisoTexto.appendChild(document.createTextNode(
        'Datos públicos recopilados por IA con sus fuentes, pendientes de validación por el equipo de análisis. '
      ));
      avisoTexto.appendChild(linkFuentes);
      avisoTexto.appendChild(document.createTextNode('.'));
    } else if (D.estadisticas && D.estadisticas.notas_calidad_datos) {
      aviso.hidden = false;
      avisoTexto.appendChild(document.createTextNode(
        'Los desgloses por tiempo y la posesión total no tienen confirmación oficial, y el xG es estimado. ' +
        'Los tiros a puerta de ' + EQUIPOS[1][1] + ' por tiempo son derivados. '
      ));
      avisoTexto.appendChild(el('a', {
        href: '../data/partido/PROCEDENCIA.md',
        style: 'text-decoration: underline;',
        text: 'Ver procedencia y correcciones'
      }));
      avisoTexto.appendChild(document.createTextNode('.'));
    } else {
      aviso.hidden = true;
    }
  }

  function iniciar() {
    var info = D.partido;
    var orden = (D.equipos_orden && D.equipos_orden.length) ? D.equipos_orden : Object.keys(D.equipos);
    var tieneUniforme = D.colores_uniforme && orden.length >= 2 &&
      (D.colores_uniforme[orden[0]] || D.colores_uniforme[orden[1]]);
    var clasesEq = tieneUniforme ? CLASES_EQ_UNIFORME : CLASES_EQ_DEFAULT;
    EQUIPOS = orden.map(function (k, i) {
      return [k, D.equipos[k].pais, clasesEq[i] || 'bra', D.equipos[k].codigo];
    });

    if (D.colores && orden.length >= 2) {
      var root = document.documentElement.style;
      if (D.colores[orden[0]]) root.setProperty('--color-team-a', D.colores[orden[0]]);
      if (D.colores[orden[1]]) root.setProperty('--color-team-b', D.colores[orden[1]]);
    }
    if (tieneUniforme) {
      var root2 = document.documentElement.style;
      if (D.colores_uniforme[orden[0]]) root2.setProperty('--color-partido-a', D.colores_uniforme[orden[0]]);
      if (D.colores_uniforme[orden[1]]) root2.setProperty('--color-partido-b', D.colores_uniforme[orden[1]]);
    }

    var clavesMarcador = Object.keys(D.equipos);
    var nombresMarcador = clavesMarcador.map(function (k) { return D.equipos[k].pais; });
    var codigosMarcador = clavesMarcador.map(function (k) { return D.equipos[k].codigo; });
    // Punto de la etiqueta superior («CRC vs SKN»): mitad y mitad con los colores del uniforme,
    // en el mismo orden que el marcador. Sin uniforme, queda el color del análisis de video.
    var punto = document.querySelector('.chip--team-a .chip__dot');
    var cu = D.colores_uniforme || {};
    if (punto && cu[clavesMarcador[0]] && cu[clavesMarcador[1]]) {
      punto.style.background = 'linear-gradient(90deg, ' + cu[clavesMarcador[0]] + ' 50%, ' +
        cu[clavesMarcador[1]] + ' 50%)';
    }
    var titulo = nombresMarcador[0] + ' ' + String(info.resultado.marcador_final).replace('-', '–') + ' ' + nombresMarcador[1];
    $('hub-titulo').textContent = titulo;
    document.title = 'MATEO — ' + titulo;
    $('hub-chip').textContent = codigosMarcador.join(' vs ') + ' · ' + String(info.fecha).slice(0, 4);
    $('subtitle').textContent = info.fase + ' · ' + info.competicion + ' · ' + info.fecha +
      ' · ' + info.estadio + ', ' + info.ciudad;

    pintarAvisoCalidad();

    TABS = ['ficha', 'fichero'];
    if (D.estadisticas && D.estadisticas.resumen_comparativo) {
      TABS.push('comparativa');
      $('tab-comparativa').textContent = tienePorTiempo() ? 'Comparativa 1T / 2T' : 'Comparativa';
    }
    if (D.goles && D.goles.length > 0) {
      TABS.push('goles');
      $('tab-goles').textContent = D.goles.length === 1 ? 'El gol' : 'Los ' + D.goles.length + ' goles';
    }
    if (D.eventos && D.eventos.length) {
      TABS.push('eventos');
      $('tab-eventos').textContent = 'Eventos (' + D.eventos.length + ')';
    }
    if (D.gol_muller) {
      TABS.push('muller');
      var apellido = D.gol_muller.metadatos_jugada.anotador.nombre.split(' ').pop();
      $('tab-muller').textContent = 'Gol de ' + apellido;
    }

    TODOS_TABS.forEach(function (id) {
      var visible = TABS.indexOf(id) >= 0;
      $('tab-' + id).hidden = !visible;
      if (!visible) $('panel-' + id).hidden = true;
    });

    if (!eventosEnlazados) {
      eventosEnlazados = true;
      TABS.forEach(function (id) {
        $('tab-' + id).addEventListener('click', function () { mostrar(id); });
        $('tab-' + id).addEventListener('keydown', function (e) {
          var i = TABS.indexOf(id);
          if (e.key === 'ArrowRight') mostrar(TABS[(i + 1) % TABS.length], true);
          if (e.key === 'ArrowLeft') mostrar(TABS[(i + TABS.length - 1) % TABS.length], true);
        });
      });
      window.addEventListener('hashchange', function () { mostrar(desdeHash(), false, true); });
    }
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

  var RENDER = { ficha: renderFicha, fichero: renderFichero, comparativa: renderComparativa, goles: renderGoles, eventos: renderEventos, muller: renderMuller };

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
    var esMineirao = info.id === 'WC2014_SF_BRA_GER';
    var esEstadioNacionalCR = info.id === 'CONCACAF_WCQ2026_R2_CRC_SKN';
    if (esMineirao) {
      host.appendChild(el('figure', { class: 'estadio' },
        el('div', { class: 'estadio__foto' },
          el('img', { src: '../assets/estadio/mineirao.jpg', alt: 'Fachada de concreto del estadio ' + info.estadio }),
          el('div', { class: 'estadio__nombre' },
            el('strong', { text: 'Mineirão' }),
            el('span', { text: info.ciudad }))),
        el('figcaption', { class: 'estadio__credito' }, 'Foto de 2024: ',
          el('a', { href: FOTO_MINEIRAO, target: '_blank', rel: 'noopener', text: 'Rodrigo Rocatto' }), ', ',
          el('a', { href: 'https://creativecommons.org/licenses/by-sa/4.0/', target: '_blank', rel: 'noopener', text: 'CC BY-SA 4.0' }),
          ', recortada')));
    } else if (esEstadioNacionalCR) {
      host.appendChild(el('figure', { class: 'estadio' },
        el('div', { class: 'estadio__foto' },
          el('img', { src: '../assets/estadio/estadio_nacional_cr.jpg', alt: 'Vista panorámica del ' + info.estadio }),
          el('div', { class: 'estadio__nombre' },
            el('strong', { text: info.estadio }),
            el('span', { text: info.ciudad + ' · Parque Metropolitano La Sabana' }))),
        el('figcaption', { class: 'estadio__credito',
          text: 'Estadio Nacional de Costa Rica (La Sabana, San José) · Capacidad: 35 175 espectadores · Recreación editorial Omnimorph' })));
    }

    var statClima = (clima && clima.temperatura_c != null)
      ? stat('Clima', clima.temperatura_c + ' °C',
          clima.cielo + ' · humedad ' + clima.humedad_pct + '% · viento ' + clima.viento_kmh + ' km/h')
      : (clima && clima.resumen)
        ? stat('Clima', clima.resumen, clima.cielo + ' · temperatura sin dato oficial')
        : stat('Clima', '—', 'Sin dato en fuentes públicas');

    host.appendChild(el('div', { class: 'stat-row' },
      stat('Marcador final', info.resultado.marcador_final, 'Descanso ' + info.resultado.primer_tiempo),
      stat('Asistencia', info.asistencia != null ? num(info.asistencia, 0) : '—', esMineirao ? 'Mineirão' : info.estadio),
      statClima,
      stat('Árbitro', arb.principal, arb.pais, true)));
    host.appendChild(el('p', { class: 'caption',
      text: 'Asistentes: ' + arb.asistente_1 + ' y ' + arb.asistente_2 + ' · Cuarto árbitro: ' + arb.cuarto_arbitro }));

    if (info.contexto_previo) {
      host.appendChild(el('p', { class: 'caption', text: info.contexto_previo }));
    }

    var split = el('div', { class: 'split' });
    EQUIPOS.forEach(function (e) {
      var eq = D.equipos[e[0]];
      var col = el('div');
      col.appendChild(el('div', { class: 'team-head' },
        el('div', { class: 'team-head__name' }, el('span', { class: 'swatch swatch--' + e[2] }), eq.pais),
        el('span', { class: 'team-head__meta',
          text: 'Entrenador: ' + eq.entrenador + ' · Esquema: ' + eq.esquema_inicial + ' · Capitán: ' + eq.capitan })));
      (eq.bajas_previas || []).forEach(function (b) {
        col.appendChild(el('div', { class: 'absence' },
          el('span', { class: 'absence__name', text: 'Baja: ' + b.nombre }),
          el('span', { class: 'absence__reason', text: b.motivo })));
      });
      var uniforme = bloqueUniforme(eq.uniforme_detalle);
      if (uniforme) col.appendChild(uniforme);
      split.appendChild(col);
    });
    host.appendChild(split);

    // Contexto competitivo (Costa Rica: formato de la ronda, grupo, ranking)
    if (info.contexto_competitivo) {
      var cc = info.contexto_competitivo;
      var textoCtx = '';
      if (cc.formato_segunda_ronda) textoCtx += cc.formato_segunda_ronda + ' ';
      if (cc.otro_resultado_jornada_1_grupo_b) textoCtx += cc.otro_resultado_jornada_1_grupo_b;
      if (textoCtx.trim()) {
        host.appendChild(el('p', { class: 'caption', text: textoCtx.trim() }));
      }
    }

    // Datos no disponibles (para que el club vea qué NO se inventó)
    if (info.datos_no_disponibles && info.datos_no_disponibles.campos && info.datos_no_disponibles.campos.length) {
      var noDispLista = el('div', { class: 'detail' });
      noDispLista.appendChild(el('p', {
        text: 'Ninguna fuente pública los publicó para este partido. Por eso no se muestran ni se estiman.' }));
      noDispLista.appendChild(el('ul', null,
        info.datos_no_disponibles.campos.map(function (c) {
          var t = NOMBRES_NO_DISPONIBLE[c] || c.replace(/_/g, ' ');
          return el('li', { text: t.charAt(0).toUpperCase() + t.slice(1) });
        })));
      host.appendChild(el('details', { class: 'window' },
        el('summary', { text: 'Datos no disponibles (' + info.datos_no_disponibles.campos.length + ')' }),
        noDispLista));
    }

    // Discrepancias entre fuentes ya resueltas
    if (info.discrepancias_resueltas && info.discrepancias_resueltas.length) {
      var discLista = el('div', { class: 'detail' });
      info.discrepancias_resueltas.forEach(function (d) {
        var txt = d.tema ? (d.tema + ': ' + (d.valor_adoptado || '') + (d.motivo ? ' — ' + d.motivo : '')) : String(d);
        discLista.appendChild(el('p', { text: txt }));
      });
      host.appendChild(el('details', { class: 'window' },
        el('summary', { text: 'Discrepancias entre fuentes resueltas (' + info.discrepancias_resueltas.length + ')' }),
        discLista));
    }

    // Diagramas de Fer: esquemas_tacticos y uniformes_y_zonas
    ['esquemas_tacticos.svg', 'uniformes_y_zonas.svg'].forEach(function (nombre) {
      var img = el('img', {
        src: '../data/partido/' + nombre,
        alt: nombre.replace(/_/g, ' ').replace('.svg', '') + ' — equipo de análisis',
        class: 'figure__img'
      });
      // La leyenda va dentro de la figura: si el SVG no existe (Brasil), se van juntas.
      var fig = el('div', { class: 'figure' }, enlaceAmpliar(img),
        el('p', { class: 'caption', text: 'Diagrama: equipo de análisis (Fer) · Tócalo para verlo en grande' }));
      img.onerror = function () { fig.remove(); };
      host.appendChild(fig);
    });

    if (D.procedencia && D.procedencia.fuentes && D.procedencia.fuentes.length) {
      var fuentesLista = el('div', { class: 'detail' });
      D.procedencia.fuentes.forEach(function (f) {
        var obj = typeof f === 'string' ? { id: '', nombre: f, url: f, datos: '' } : f;
        var p = el('p', null);
        if (obj.id) p.appendChild(el('strong', { text: obj.id + ' · ' }));
        p.appendChild(el('a', {
          href: obj.url,
          target: '_blank',
          rel: 'noopener',
          style: 'text-decoration: underline;',
          text: obj.nombre || obj.url
        }));
        if (obj.datos) p.appendChild(document.createTextNode(' — ' + obj.datos));
        fuentesLista.appendChild(p);
      });
      host.appendChild(el('details', { class: 'window', id: 'fuentes-partido' },
        el('summary', { text: 'Fuentes públicas consultadas (' + D.procedencia.fuentes.length + ')' }),
        fuentesLista));
    }
  }

  function renderFichero() {
    window.OmniFichero.render($('panel-fichero'), D, el);
  }

  // ── Comparativa ──────────────────────────────────────────────────────────
  function metricaPorClave(clave) {
    return metricasDefinidas().filter(function (m) { return m[0] === clave; })[0];
  }

  function valor(clave, periodo, equipo) {
    var rc = D.estadisticas && D.estadisticas.resumen_comparativo;
    if (!rc || !rc[periodo] || !rc[periodo][clave]) return null;
    return rc[periodo][clave][equipo];
  }

  function metricaDisponible(clave) {
    return periodosActivos().some(function (p) {
      return EQUIPOS.some(function (e) { return valor(clave, p[0], e[0]) != null; });
    });
  }

  // Etiquetas en español para las métricas adicionales de Fer
  var ETIQUETAS_ADICIONALES = {
    'tiros_al_poste': 'Tiros al poste',
    'grandes_ocasiones': 'Grandes ocasiones',
    'grandes_ocasiones_falladas': 'Grandes ocasiones falladas',
    'toques_area_rival': 'Toques en el área rival',
    'pases_precisos_campo_propio': 'Pases precisos campo propio',
    'pases_precisos_campo_rival': 'Pases precisos campo rival',
    'balones_largos_precisos': 'Balones largos precisos',
    'balones_largos_pct': 'Precisión balones largos (%)',
    'centros_precisos': 'Centros precisos',
    'centros_pct': 'Precisión centros (%)',
    'saques_de_banda': 'Saques de banda',
    'entradas_tackles': 'Entradas (tackles)',
    'intercepciones': 'Intercepciones',
    'bloqueos_defensivos': 'Bloqueos defensivos',
    'despejes': 'Despejes',
    'duelos_ganados': 'Duelos ganados',
    'duelos_suelo_ganados': 'Duelos en tierra ganados',
    'duelos_suelo_pct': 'Precisión duelos en tierra (%)',
    'duelos_aereos_ganados': 'Duelos aéreos ganados',
    'duelos_aereos_pct': 'Precisión duelos aéreos (%)',
    'regates_exitosos': 'Regates exitosos',
    'regates_pct': 'Precisión regates (%)',
  };

  function tablaAdicional() {
    var ma = D.estadisticas && D.estadisticas.metricas_adicionales;
    if (!ma) return null;
    // Periodos presentes en metricas_adicionales
    var periodos = PERIODOS_TODOS.filter(function (p) { return ma[p[0]] != null; });
    if (!periodos.length) return null;
    // Claves de métricas (tomar del primer periodo disponible)
    var claves = Object.keys(ma[periodos[0][0]] || {});
    if (!claves.length) return null;

    var nCols = String(periodos.length);
    var thead = el('thead', null,
      el('tr', null, el('th', { rowspan: '2', text: 'Métrica adicional' }),
        EQUIPOS.map(function (e) {
          return el('th', { class: 'group group--' + e[2], colspan: nCols, text: e[1] });
        })),
      el('tr', null, periodos.concat(periodos).map(function (p, i) {
        return el('th', { class: 'num' + (i % periodos.length === 0 ? ' group' : ''), text: p[1] });
      })));
    var tbody = el('tbody');
    claves.forEach(function (clave) {
      var etiqueta = ETIQUETAS_ADICIONALES[clave] || clave.replace(/_/g, ' ');
      var fila = el('tr', null, el('td', null, etiqueta));
      EQUIPOS.forEach(function (e) {
        periodos.forEach(function (p, i) {
          var v = ma[p[0]] && ma[p[0]][clave] ? ma[p[0]][clave][e[0]] : null;
          fila.appendChild(el('td', { class: 'num' + (i === 0 ? ' group' : ''), text: v != null ? String(v) : '—' }));
        });
      });
      tbody.appendChild(fila);
    });
    return el('div', { class: 'table-wrap' }, el('table', { class: 'tbl' }, thead, tbody));
  }

  function renderComparativa() {
    var host = $('panel-comparativa');
    vaciar(host);
    var listaMetricas = metricasDefinidas();
    var disponibles = listaMetricas.filter(function (m) { return metricaDisponible(m[0]); });
    if (disponibles.length && !metricaDisponible(metricaActiva)) {
      metricaActiva = disponibles[0][0];
    }
    var pills = el('div', { class: 'pillbar', role: 'group', 'aria-label': 'Métrica' });
    disponibles.forEach(function (m) {
      var b = el('button', { class: 'btn btn--outline btn-xs', type: 'button', 'data-metrica': m[0],
        'aria-pressed': m[0] === metricaActiva ? 'true' : 'false', text: m[1] });
      b.addEventListener('click', function () { metricaActiva = m[0]; marcarPills(); dibujarGrafico(); });
      pills.appendChild(b);
    });
    host.appendChild(pills);
    host.appendChild(el('div', { class: 'legend', 'aria-label': 'Leyenda' },
      EQUIPOS.map(function (e) {
        return el('span', { class: 'legend__item' }, el('span', { class: 'swatch swatch--' + e[2] }), e[1]);
      })));
    // Nota de colores de uniforme (solo cuando están activos)
    if (D.colores_uniforme) {
      host.appendChild(el('p', { class: 'caption',
        text: 'Colores del uniforme real del partido (distintos a los del análisis de video).' }));
    }
    host.appendChild(el('div', { class: 'chart', id: 'chart' }));
    host.appendChild(el('div', { class: 'section-label', text: 'Todas las métricas' }));
    host.appendChild(tablaCompleta());
    var tabAdic = tablaAdicional();
    if (tabAdic) {
      host.appendChild(el('div', { class: 'section-label', text: 'Métricas adicionales (FotMob / Opta)' }));
      host.appendChild(tabAdic);
    }
    dibujarGrafico();
  }

  function marcarPills() {
    document.querySelectorAll('#panel-comparativa [data-metrica]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-metrica') === metricaActiva ? 'true' : 'false');
      b.className = 'btn btn-xs ' + (b.getAttribute('data-metrica') === metricaActiva ? 'btn--primary' : 'btn--outline');
    });
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
    var porTiempo = tienePorTiempo();
    var series = porTiempo ? [['1T', 'primer_tiempo'], ['2T', 'segundo_tiempo']] : [['Total', 'tiempo_completo']];
    var maxV = 0;
    series.forEach(function (s) {
      EQUIPOS.forEach(function (e) {
        var v = valor(m[0], s[1], e[0]);
        if (v != null) maxV = Math.max(maxV, Number(v));
      });
    });
    var techo = techoGrafico(maxV);
    var y = function (v) { return MT + (H - MT - MB) * (1 - v / techo); };

    var descEtiqueta = porTiempo ? 'en el primer y segundo tiempo' : 'en el total del partido';
    var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, role: 'img',
      'aria-label': m[1] + ' de ' + EQUIPOS[0][1] + ' y ' + EQUIPOS[1][1] + ' ' + descEtiqueta });
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
        var valNum = val != null ? Number(val) : 0;
        var x = cx + (j === 0 ? -barra - 1 : 1);
        var alto = Math.max(H - MB - y(valNum), 0);
        var r = svg('rect', { class: 'bar bar--' + e[2], x: x, y: H - MB - alto, width: barra, height: alto,
          rx: 3, tabindex: 0, 'data-tip': e[1] + ' · ' + ser[0] + ': ' + num(val, m[2]) + ' ' + m[1].toLowerCase(),
          'aria-label': e[1] + ', ' + ser[0] + ', ' + m[1] + ': ' + num(val, m[2]) });
        s.appendChild(r);
        s.appendChild(svg('text', { class: 'chart__value', x: x + barra / 2, y: H - MB - alto - 6,
          'text-anchor': 'middle', text: num(val, m[2]) }));
        s.appendChild(svg('text', { x: x + barra / 2, y: H - MB + 14, 'text-anchor': 'middle', text: (e[3] || e[2]).toUpperCase() }));
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
    var per = periodosActivos();
    var nCols = String(per.length);
    var thead = el('thead', null,
      el('tr', null, el('th', { rowspan: '2', text: 'Métrica' }),
        EQUIPOS.map(function (e) {
          return el('th', { class: 'group group--' + e[2], colspan: nCols, text: e[1] });
        })),
      el('tr', null, per.concat(per).map(function (p, i) {
        return el('th', { class: 'num' + (i % per.length === 0 ? ' group' : ''), text: p[1] });
      })));
    var tbody = el('tbody');
    metricasDefinidas().forEach(function (m) {
      var fila = el('tr', null, el('td', null, m[1], m[3] ? el('span', { class: 'note', text: m[3] }) : null));
      EQUIPOS.forEach(function (e) {
        per.forEach(function (p, i) {
          fila.appendChild(el('td', { class: 'num' + (i === 0 ? ' group' : ''), text: num(valor(m[0], p[0], e[0]), m[2]) }));
        });
      });
      tbody.appendChild(fila);
    });
    return el('div', { class: 'table-wrap' }, el('table', { class: 'tbl' }, thead, tbody));
  }

  // ── Goles ────────────────────────────────────────────────────────────────

  /** Convierte segundos desde el inicio del partido a mm:ss. */
  function segAMinutos(s) {
    if (s == null) return null;
    var m = Math.floor(s / 60), sec = s % 60;
    return m + "'" + (sec > 0 ? String(sec).padStart(2, '0') + '"' : '');
  }

  /**
   * Mini-cancha con el punto del remate en coordenadas IFES/Opta (0–100).
   * Convención (ANALISIS_PARTIDO.md de Fer): x va de la portería propia (0) a la rival (100);
   * y va de la banda derecha (0) a la izquierda (100) mirando hacia la portería rival.
   * Se dibuja atacando hacia la derecha, así que la banda izquierda queda arriba.
   */
  function miniCancha(coordenadas, equipo) {
    if (!coordenadas || coordenadas.x == null || coordenadas.y == null) return null;
    var LARGO = 105, ANCHO = 68;                 // medidas de referencia en metros
    var W = 240, H = 156, PAD = 8;
    var iw = W - 2 * PAD, ih = H - 2 * PAD;
    var mx = function (m) { return PAD + (m / LARGO) * iw; };
    var my = function (m) { return PAD + (m / ANCHO) * ih; };
    var ns = 'http://www.w3.org/2000/svg';
    var s = document.createElementNS(ns, 'svg');
    s.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    s.setAttribute('class', 'mini-cancha');
    s.setAttribute('role', 'img');
    s.setAttribute('aria-label', 'Lugar del remate' + (equipo ? ' de ' + equipo : '') +
      ': ' + Math.round(LARGO * (1 - coordenadas.x / 100)) + ' m de la línea de gol rival');
    function forma(tag, attrs) {
      var n = document.createElementNS(ns, tag);
      Object.keys(attrs).forEach(function (k) { n.setAttribute(k, String(attrs[k])); });
      s.appendChild(n);
      return n;
    }
    forma('rect', { x: 0, y: 0, width: W, height: H, 'class': 'mini-cancha__bg' });
    forma('rect', { x: PAD, y: PAD, width: iw, height: ih, 'class': 'mini-cancha__linea' });
    forma('line', { x1: mx(LARGO / 2), y1: PAD, x2: mx(LARGO / 2), y2: H - PAD, 'class': 'mini-cancha__linea' });
    forma('circle', { cx: mx(LARGO / 2), cy: my(ANCHO / 2), r: (9.15 / LARGO) * iw, 'class': 'mini-cancha__linea' });
    // Áreas grande y chica, y portería, en los dos extremos
    [[0, 1], [LARGO, -1]].forEach(function (lado) {
      var x0 = lado[0], dir = lado[1];
      var area = function (fondo, ancho) {
        var xa = dir > 0 ? x0 : x0 - fondo;
        forma('rect', { x: mx(xa), y: my((ANCHO - ancho) / 2), width: mx(fondo) - PAD,
          height: my(ancho) - PAD, 'class': 'mini-cancha__linea' });
      };
      area(16.5, 40.3);
      area(5.5, 18.3);
      var xp = dir > 0 ? x0 - 1.5 : x0;
      forma('rect', { x: mx(xp), y: my((ANCHO - 7.32) / 2), width: mx(1.5) - PAD,
        height: my(7.32) - PAD, 'class': 'mini-cancha__porteria' });
    });
    // Punto del remate
    var px = mx(LARGO * coordenadas.x / 100);
    var py = my(ANCHO * (1 - coordenadas.y / 100));
    forma('circle', { cx: Math.round(px), cy: Math.round(py), r: 5, 'class': 'mini-cancha__punto' });
    return s;
  }

  function renderGoles() {
    var host = $('panel-goles');
    vaciar(host);
    var hayCoordenadas = D.goles.some(function (g) { return g.coordenadas_campo_cm != null; });
    if (hayCoordenadas) {
      host.appendChild(el('div', { class: 'figure' }, el('img', { src: '../data/partido/mapa_8_goles.svg',
        alt: 'Mapa de la cancha con la posición de remate de los ' + D.goles.length + ' goles' })));
      host.appendChild(el('p', { class: 'caption',
        text: 'El tamaño de cada punto indica el xG estimado. Las coordenadas están normalizadas: ' + EQUIPOS[1][1] + ' siempre ataca hacia la izquierda, también en el 2T.' }));
    }

    // Columnas opcionales: solo si al menos un gol tiene dato
    var hayXg = D.goles.some(function (g) { return g.xg != null; });
    var hayDist = D.goles.some(function (g) { return g.distancia_porteria_m != null; });

    var tbody = el('tbody');
    D.goles.forEach(function (g, i) {
      var jugadaLimpia = g.jugada ? textoJugada(g.jugada) : '';
      var jugadaCorta = jugadaLimpia ? (jugadaLimpia.length > 60 ? jugadaLimpia.slice(0, 58) + '…' : jugadaLimpia)
                       : (g.tipo_jugada || '—');
      var cols = [
        el('td', { class: 'num', text: g.minuto + "'" }),
        el('td', { class: 'num', text: g.marcador_momento }),
        el('td', { text: g.anotador ? g.anotador.nombre : '—' }),
        el('td', { class: 'soft', text: g.asistente && g.asistente.nombre ? g.asistente.nombre : '—' }),
        el('td', { class: 'soft goles__jugada', text: jugadaCorta })
      ];
      if (hayXg) cols.push(el('td', { class: 'num', text: num(g.xg, 2) }));
      if (hayDist) cols.push(el('td', { class: 'num', text: num(g.distancia_porteria_m, 1) }));
      var fila = el.apply(null, ['tr', { 'data-row': String(i), tabindex: 0, 'aria-selected': i === golActivo ? 'true' : 'false' }].concat(cols));
      var elegir = function () { golActivo = i; marcarGol(); };
      fila.addEventListener('click', elegir);
      fila.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); elegir(); } });
      tbody.appendChild(fila);
    });
    var thCols = [
      el('th', { text: 'Min' }), el('th', { class: 'num', text: 'Marcador' }),
      el('th', { text: 'Anotador' }), el('th', { text: 'Asistente' }), el('th', { text: 'Jugada' })
    ];
    if (hayXg) thCols.push(el('th', { class: 'num', text: 'xG est.' }));
    if (hayDist) thCols.push(el('th', { class: 'num', text: 'Dist. (m)' }));
    host.appendChild(el('div', { class: 'table-wrap' }, el('table', { class: 'tbl', id: 'tabla-goles' },
      el.apply(null, ['thead', null, el.apply(null, ['tr', null].concat(thCols))]),
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
    // Encabezado del gol
    var tiempoOficial = segAMinutos(g.segundo_oficial);
    var encab = g.minuto + "'" + (tiempoOficial ? ' (' + tiempoOficial + ' reloj)' : '') +
      ' · ' + (g.anotador ? g.anotador.nombre : '—') + ' (' + g.marcador_momento + ')';
    box.appendChild(el('p', null, el('strong', { text: encab })));
    // Zona y pie de remate
    if (g.zona_remate || g.pie_remate) {
      var detRemate = [g.pie_remate, g.zona_remate].filter(Boolean).join(' · ');
      box.appendChild(el('p', null, el('strong', { text: 'Remate. ' }), detRemate));
    }
    // Mini-cancha con coordenadas FIFA
    var cancha = miniCancha(g.coordenadas_fifa, g.equipo_anotador);
    if (cancha) {
      box.appendChild(cancha);
      box.appendChild(el('p', { class: 'caption mini-cancha__leyenda',
        text: (g.equipo_anotador || 'El equipo que anota') + ' ataca hacia la derecha → · Posición oficial FIFA/Opta' }));
    }
    // Jugada completa (relato de Fer)
    if (g.jugada) box.appendChild(el('p', null, el('strong', { text: 'Jugada. ' }), textoJugada(g.jugada)));
    else if (g.narracion) box.appendChild(el('p', null, el('strong', { text: 'Relato. ' }), g.narracion));
    // Análisis táctico (si existe)
    if (g.nota_tactica) box.appendChild(el('p', null, el('strong', { text: 'Análisis táctico. ' }), g.nota_tactica));
  }

  // ── Gol destacado (opcional, ej. Müller) ─────────────────────────────────
  function renderMuller() {
    var host = $('panel-muller');
    vaciar(host);
    if (!D.gol_muller) return;
    var jugada = D.gol_muller.metadatos_jugada;
    var ventanas = D.gol_muller.ventanas_tacticas;
    var met = ventanas[ventanas.length - 1].metricas;
    host.appendChild(el('p', { class: 'caption',
      text: jugada.minuto_oficial + "' · " + jugada.anotador.nombre + ' · ' + jugada.tipo_jugada + ' · Reloj ' + jugada.reloj_partido }));
    host.appendChild(el('div', { class: 'figure' }, el('img', { src: '../data/partido/radar_gol_muller.svg',
      alt: 'Radar cenital de la jugada del gol de ' + jugada.anotador.nombre })));
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

  // ── Eventos ──────────────────────────────────────────────────────────────
  var ICONOS_EVENTO = {
    'inicio': '⏱', 'descanso': '⏱', 'final': '⏱',
    'gol': '⚽', 'tarjeta_amarilla': '🟨', 'tarjeta_roja': '🟥',
    'cambio': '🔄', 'sustitucion': '🔄', 'poste': '🥅', 'atajada': '🧤',
    'ocasion_clara': '💥', 'atencion_medica': '➕', 'remate_bloqueado': '⛔'
  };
  var NOMBRES_EVENTO = {
    'inicio': 'Inicio', 'descanso': 'Descanso', 'final': 'Final', 'gol': 'Gol',
    'tarjeta_amarilla': 'Tarjeta amarilla', 'tarjeta_roja': 'Tarjeta roja',
    'cambio': 'Cambio', 'sustitucion': 'Cambio', 'poste': 'Poste o travesaño',
    'atajada': 'Atajada', 'ocasion_clara': 'Ocasión clara',
    'atencion_medica': 'Atención médica', 'remate_bloqueado': 'Remate bloqueado'
  };

  function claseEquipoEvento(nombreEquipo) {
    if (!nombreEquipo || !EQUIPOS.length) return '';
    var nombre = nombreEquipo.toLowerCase();
    for (var i = 0; i < EQUIPOS.length; i++) {
      if (EQUIPOS[i][1].toLowerCase().indexOf(nombre) >= 0 || nombre.indexOf(EQUIPOS[i][1].toLowerCase()) >= 0) {
        return EQUIPOS[i][2]; // clase CSS del equipo
      }
    }
    return '';
  }

  function renderEventos() {
    var host = $('panel-eventos');
    vaciar(host);

    // Diagrama de Fer: timeline_partido.svg
    var imgTimeline = el('img', {
      src: '../data/partido/timeline_partido.svg',
      alt: 'Línea de tiempo del partido (diagrama del equipo de análisis)',
      class: 'figure__img'
    });
    var figTimeline = el('div', { class: 'figure' }, enlaceAmpliar(imgTimeline),
      el('p', { class: 'caption', text: 'Diagrama: equipo de análisis (Fer) · Tócalo para verlo en grande' }));
    imgTimeline.onerror = function () { figTimeline.remove(); };
    host.appendChild(figTimeline);

    host.appendChild(el('div', { class: 'section-label', text: 'Cronología — ' + D.eventos.length + ' eventos' }));

    var lista = el('div', { class: 'eventos-lista' });
    D.eventos.forEach(function (ev) {
      var icono = ICONOS_EVENTO[ev.tipo] || '•';
      var claseEq = claseEquipoEvento(ev.equipo);
      var jugadorTexto = ev.jugador || '';
      if (ev.jugador_secundario) jugadorTexto += ' → ' + ev.jugador_secundario;

      var fila = el('div', { class: 'evento-fila' },
        el('span', { class: 'evento-fila__min', text: ev.minuto }),
        el('span', { class: 'evento-fila__icono', 'aria-hidden': 'true', text: icono }),
        el('span', { class: 'evento-fila__tipo', text: NOMBRES_EVENTO[ev.tipo] || ev.tipo.replace(/_/g, ' ') }),
        claseEq ? el('span', { class: 'swatch swatch--' + claseEq, 'aria-hidden': 'true' }) : null,
        jugadorTexto ? el('span', { class: 'evento-fila__jugador', text: jugadorTexto }) : null,
        el('span', { class: 'evento-fila__desc', text: sinMarcasFuente(ev.descripcion) })
      );
      lista.appendChild(fila);
    });
    host.appendChild(lista);
  }
})();
