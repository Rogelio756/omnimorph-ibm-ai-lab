/**
 * components/metodo.js
 * OMNIMORPH — Página Método: principios, flujo, niveles de confianza, límites y gobernanza.
 * Fuente: ../data/metodo.json (scripts/export_dashboard_data.py → export_metodo()).
 *
 * Regla de esta página: ninguna cifra se escribe a mano. Todas salen de los monitores
 * de la última corrida del pipeline. El texto se inserta con textContent, nunca como HTML.
 */
(function () {
  'use strict';

  var host = document.getElementById('metodo');
  if (!host) return;

  function el(tag, attrs) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === 'text') node.textContent = attrs[k];
      else if (k === 'class') node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (function agregar(hijos) {
      hijos.forEach(function (c) {
        if (c == null || c === false) return;
        if (Array.isArray(c)) { agregar(c); return; }
        node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      });
    })(Array.prototype.slice.call(arguments, 2));
    return node;
  }

  function num(v, dec) {
    if (v == null || v === '' || isNaN(Number(v))) return '—';
    return Number(v).toLocaleString('es-MX', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  }

  function chip(estado, texto) {
    var ok = estado === 'PASS';
    var c = el('span', { class: 'chip ' + (ok ? 'chip--ok' : 'chip--alert') },
      el('span', { class: 'chip__dot' }), texto + ' · ' + (estado || '—'));
    c.style.alignSelf = 'flex-start';   // dentro de .stat (columna flex) no se estira
    c.style.marginTop = 'var(--space-2)';
    return c;
  }

  function stat(label, valor, hint, esTexto, extra) {
    return el('div', { class: 'stat' },
      el('span', { class: 'stat__label', text: label }),
      el('span', { class: 'stat__value' + (esTexto ? ' stat__value--text' : ''), text: valor }),
      hint ? el('span', { class: 'stat__hint', text: hint }) : null,
      extra || null);
  }

  function seccion(titulo) {
    return el('div', { class: 'section-label', text: titulo });
  }

  function parrafos(titulo, textos) {
    return el('div', { class: 'detail' },
      titulo ? el('strong', { text: titulo }) : null,
      textos.map(function (t) { return el('p', { text: t }); }));
  }

  function limite(nombre, texto) {
    return el('div', { class: 'absence' },
      el('span', { class: 'absence__name', text: nombre }),
      el('span', { class: 'absence__reason', text: texto }));
  }

  function tabla(cabecera, filas) {
    var thead = el('thead', {}, el('tr', {}, cabecera.map(function (h) { return el('th', { text: h }); })));
    var tbody = el('tbody', {}, filas.map(function (f) {
      return el('tr', {}, f.map(function (c, i) {
        return el('td', {}, i === 0 ? el('strong', { text: c }) : c);
      }));
    }));
    return el('div', { class: 'table-wrap' }, el('table', { class: 'tbl' }, thead, tbody));
  }

  /** Estado agregado de un grupo de monitores (p. ej. M2.0–M2.5). */
  function estadoGrupo(mon, prefijo) {
    var claves = Object.keys(mon).filter(function (k) { return k.indexOf(prefijo) === 0; });
    if (!claves.length) return null;
    return claves.every(function (k) { return mon[k] === 'PASS'; }) ? 'PASS' : 'FAIL';
  }

  // ── Diagrama de flujo en SVG (horizontal en escritorio, vertical en móvil) ──
  var NS = 'http://www.w3.org/2000/svg';
  function s(tag, attrs, texto) {
    var n = document.createElementNS(NS, tag);
    Object.keys(attrs).forEach(function (k) { if (attrs[k] !== '') n.setAttribute(k, attrs[k]); });
    if (texto != null) n.textContent = texto;
    return n;
  }

  function caja(g, e, x, y, w, h) {
    g.appendChild(s('rect', { x: x, y: y, width: w, height: h, rx: 10,
      class: 'caja' + (e.ibm ? ' caja--ibm' : '') + (e.humano ? ' caja--humano' : '') }));
    g.appendChild(s('text', { x: x + 14, y: y + 28, class: 'titulo' }, e.t));
    e.d.forEach(function (linea, i) { g.appendChild(s('text', { x: x + 14, y: y + 52 + i * 18, class: 'dato' }, linea)); });
    if (e.m) {
      var ok = e.m[1] === 'PASS' || e.m[1] === 'VALIDADOS';
      var pendiente = e.humano && !ok;
      g.appendChild(s('text', { x: x + 14, y: y + h - 14, class: ok || pendiente ? 'monitor-ok' : 'monitor-fail',
        style: pendiente ? 'fill: var(--color-warn)' : '' }, '● ' + e.m[0] + ' · ' + (e.m[1] || '—')));
    }
  }

  function flecha(g, d, humano) {
    g.appendChild(s('path', { d: d, class: 'flecha' + (humano ? ' flecha--humano' : '') }));
  }

  function punta(g, x, y, dir, humano) {
    var p = dir === 'der' ? [x, y, x - 8, y - 5, x - 8, y + 5] :
            dir === 'abajo' ? [x, y, x - 5, y - 8, x + 5, y - 8] : [x, y, x - 5, y + 8, x + 5, y + 8];
    g.appendChild(s('polygon', { points: p.join(' '), class: 'punta' + (humano ? ' punta--humano' : '') }));
  }

  function diagrama(etapas, datos, vertical) {
    var svg, g = s('g', {});
    if (!vertical) {
      var W = 180, H = 124, paso = 208, y = 16;
      svg = s('svg', { viewBox: '0 0 1236 290', class: 'diagrama__horizontal', 'aria-hidden': 'true' });
      etapas.forEach(function (e, i) {
        var x = 8 + i * paso;
        caja(g, e, x, y, W, H);
        if (i < etapas.length - 1) {
          flecha(g, 'M' + (x + W) + ' ' + (y + H / 2) + ' H' + (x + paso - 2));
          punta(g, x + paso, y + H / 2, 'der');
        }
      });
      var xd = 8 + 3 * paso, yd = 172, wd = 2 * W + 28;
      caja(g, datos, xd, yd, wd, 100);
      var xt = 8 + 5 * paso + W / 2;
      flecha(g, 'M' + (xd + wd) + ' ' + (yd + 50) + ' H' + xt + ' V' + (y + H + 10), true);
      punta(g, xt, y + H + 2, 'arriba', true);
    } else {
      var Wv = 380, Hv = 112, pasoV = 140, x0 = 20;
      var alto = 20 + (etapas.length + 1) * pasoV;
      svg = s('svg', { viewBox: '0 0 420 ' + alto, class: 'diagrama__vertical', 'aria-hidden': 'true' });
      etapas.forEach(function (e, i) {
        var yv = 20 + i * pasoV;
        caja(g, e, x0, yv, Wv, Hv);
        if (i < etapas.length - 1) {
          flecha(g, 'M' + (x0 + Wv / 2) + ' ' + (yv + Hv) + ' V' + (yv + pasoV - 2));
          punta(g, x0 + Wv / 2, yv + pasoV, 'abajo');
        }
      });
      var ydv = 20 + etapas.length * pasoV;
      caja(g, datos, x0, ydv, Wv, Hv);
      var yTab = 20 + (etapas.length - 1) * pasoV + Hv;
      flecha(g, 'M' + (x0 + Wv / 2) + ' ' + ydv + ' V' + (yTab + 10), true);
      punta(g, x0 + Wv / 2, yTab + 2, 'arriba', true);
    }
    svg.appendChild(g);
    return svg;
  }

  function render(D) {
    var P = D.partido, C = D.corrida, m1 = D.m1, m2 = D.m2, m3 = D.m3, m4 = D.m4, dor = D.dorsales;
    var mon = C.monitores || {};
    var validado = P.datos_validados === true;
    var hayDorsales = dor && dor.jugadores > 0;

    document.getElementById('metodo-subtitulo').textContent =
      P.titulo + ' · clip de ' + num(P.duracion_s, 0) + ' s · corrida del ' +
      (C.fecha ? new Date(C.fecha).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) : '—');

    var chipHost = document.getElementById('metodo-chip');
    chipHost.classList.add(C.todos_pass ? 'chip--ok' : 'chip--alert');
    document.getElementById('metodo-chip-texto').textContent =
      num(C.n_pass) + '/' + num(C.n_total) + ' monitores PASS';

    if (!D.coincide_partido) document.getElementById('metodo-otra-corrida').hidden = false;

    // 0 · Ficha técnica del MVP ----------------------------------------------
    host.appendChild(seccion('Ficha técnica del MVP'));
    host.appendChild(tabla(['Campo', 'Detalle'], [
      ['Producto', 'MATEO, el MVP de Omnimorph: análisis táctico de video de fútbol con IA y narración en español'],
      ['Partido', P.titulo + ' · ' + P.competicion],
      ['Clip analizado', num(P.duracion_s, 0) + ' s · ' + num(m1.frames) + ' cuadros a ' + num(P.fps, 2) + ' fps · transmisión de TV'],
      ['Percepción', 'Seis modelos de roboflow/sports: líneas del campo, jugadores y balón (YOLOv8), seguimiento (ByteTrack), clasificación por equipo y radar'],
      ['Motor táctico', 'Homografía suavizada (EMA) · unión de rastros con el algoritmo húngaro · trayectorias Savitzky-Golay · ventanas de ' +
        num(m2.ventana_s, 1) + ' s'],
      ['Modelo de lenguaje', (m3.modelo || '—') + ' en IBM watsonx.ai, para el narrador y el chat'],
      ['Voz', 'Síntesis local (' + (m4.motor_tts || '—') + '), sincronizada con el video'],
      ['Interfaz', 'Web estática (HTML, CSS y JavaScript) con un servidor local en Python'],
      ['Gobernanza', num(C.n_total) + ' monitores en cada corrida y registro de cada llamada a Granite'],
      ['Ejecución', 'Local. IBM watsonx.ai es el único servicio externo'],
      ['Datos del partido', num(P.n_fuentes) + ' fuentes públicas · ' + (validado ? 'validados por el equipo de análisis' : 'pendientes de validación')],
      ['Última corrida', (C.fecha ? new Date(C.fecha).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) : '—') +
        ' · ' + num(C.n_pass) + '/' + num(C.n_total) + ' monitores PASS en ' + num(C.duracion_s, 1) + ' s']
    ]));

    // 0b · Diagrama de flujo -------------------------------------------------
    host.appendChild(seccion('Diagrama de flujo'));
    var etapas = [
      { t: 'Video', d: ['Transmisión de TV', num(m1.frames) + ' cuadros · ' + num(P.fps, 2) + ' fps'], m: null },
      { t: 'Percepción', d: ['6 modelos · YOLOv8, ByteTrack', num(m1.filas_jugadores) + ' posiciones'], m: ['M1', mon.M1] },
      { t: 'Motor táctico', d: [num(m2.ids_crudos) + ' → ' + num(m2.ids_cosidos) + ' rastros', num(m2.n_ventanas) + ' ventanas de ' + num(m2.ventana_s, 1) + ' s'],
        m: ['M2.0–M2.5', estadoGrupo(mon, 'M2.')] },
      { t: 'Narrador Granite', d: [(m3.modelo || '—').replace('ibm/', ''), num(m3.llamadas) + ' textos · ' + num(m3.latencia_ms_media, 0) + ' ms'],
        m: ['M3', mon.M3], ibm: true },
      { t: 'Voz', d: ['Síntesis local', num(m4.clips) + ' audios · ' + num(m4.desfase_ms_max, 1) + ' ms'], m: ['M4', mon.M4] },
      { t: 'Tablero', d: ['MATEO · Partido · Método', 'Operaciones'], m: [num(C.n_pass) + '/' + num(C.n_total), C.todos_pass ? 'PASS' : 'FAIL'] }
    ];
    var datosPartido = { t: 'Datos del partido', d: [num(P.n_fuentes) + ' fuentes públicas', 'validación humana'],
      m: ['Datos', validado ? 'VALIDADOS' : 'POR VALIDAR'], humano: true };
    host.appendChild(el('div', { class: 'diagrama', role: 'img',
        'aria-label': 'Flujo: ' + etapas.map(function (e) { return e.t; }).join(' → ') +
          '. Los datos del partido llegan al tablero tras validación humana.' },
      diagrama(etapas, datosPartido, false), diagrama(etapas, datosPartido, true)));
    host.appendChild(el('p', { class: 'caption' }, 'Las cifras salen de la última corrida. ',
      el('a', { href: 'operaciones.html', style: 'text-decoration: underline;',
        text: 'Ver cada monitor y el consumo del chat en Operaciones →' })));

    // 1 · Principios ---------------------------------------------------------
    host.appendChild(seccion('Principios de investigación'));
    host.appendChild(el('div', { class: 'stat-row' },
      stat('Principio 1', 'Ningún dato sin fuente', 'Cada cifra del partido cita de dónde sale', true),
      stat('Principio 2', 'La IA se marca', 'Lo que estima un modelo aparece «por validar»', true),
      stat('Principio 3', 'Valida una persona', 'Un analista confirma antes de que sea oficial', true),
      stat('Principio 4', 'Solo IBM Granite', 'Cada llamada al modelo queda auditada', true)));
    host.appendChild(parrafos(null, [
      'Separamos tres cosas que suelen mezclarse: lo que mide la visión por computadora en el video, ' +
      'lo que dicen las fuentes públicas del partido y lo que redacta la IA. Cada una tiene su nivel de confianza ' +
      'y la página lo dice en el lugar donde aparece el dato.',
      'Si un dato no está en ninguna fuente, se muestra «—». No lo completamos con promedios ni con estimaciones.'
    ]));

    // 3 · Niveles de confianza -----------------------------------------------
    var porValidar = [];
    if (!validado && P.datos_validados != null) {
      porValidar.push('Ficha, alineaciones, estadísticas y goles del partido (' + num(P.n_fuentes) + ' fuentes públicas)');
    }
    if (hayDorsales && !dor.validado) {
      porValidar.push(num(dor.jugadores) + ' jugadores identificados a mano en ' + num(dor.rastros) + ' rastros del clip');
    }
    host.appendChild(seccion('Niveles de confianza'));
    host.appendChild(tabla(['Nivel', 'Qué significa', 'En este partido'], [
      ['Verificado', 'Un analista lo confirmó contra fuentes citadas.',
        validado ? 'Ficha, alineaciones, estadísticas y goles del partido.'
                 : 'Todavía nada. Los datos del partido esperan la revisión del equipo de análisis.'],
      ['Por validar', 'Lo reunió una IA o se identificó a mano. Se muestra con la etiqueta «por validar».',
        porValidar.length ? porValidar.join(' · ') : 'Nada pendiente.'],
      ['No disponible', 'No está en las fuentes o el sistema no lo calcula. Se muestra «—».',
        'Velocidad por jugador · métricas que no calculamos, como xG o PPDA · datos marcados sin fuente.']
    ]));

    // 4 · Límites conocidos --------------------------------------------------
    host.appendChild(seccion('Límites conocidos'));
    host.appendChild(el('p', { class: 'caption',
      text: 'Los decimos aquí porque un sistema que explica dónde falla es más útil que uno que promete todo.' }));
    host.appendChild(limite('Velocidades ocultas',
      'La cámara de TV se mueve y la calibración que convierte la imagen en metros salta de un cuadro a otro. ' +
      'Eso produce velocidades irreales, así que no las mostramos. Las posiciones usan la misma calibración: ' +
      'son más estables, pero aproximadas. El ' + num(m1.homografia_calculada_pct, 0) + ' % de calibración del ' +
      'monitor M1 significa que se pudo calcular en cada cuadro, no que sea exacta.'));
    if (hayDorsales) {
      host.appendChild(limite('Dorsales identificados a mano',
        'El modelo automático de dorsales no lee los números en una transmisión de TV. ' + num(dor.jugadores) +
        ' jugadores se identificaron a mano en ' + num(dor.rastros) + ' rastros, comparando el video con la alineación' +
        (dor.validado ? ', y ya están validados.' : '. Siguen por validar.')));
    }
    host.appendChild(limite('Rastros partidos',
      'El seguimiento pierde a un jugador cuando sale de cuadro o se cruza con otro. Después de unir tramos quedan ' +
      num(m2.ids_cosidos) + ' identificadores para unas 25 personas en el campo, así que un mismo jugador puede ' +
      'aparecer con dos números.' +
      (hayDorsales && dor.rastros > dor.jugadores
        ? ' Los tramos que el equipo identificó a mano ya se muestran unidos en MATEO.' : '')));
    host.appendChild(limite('Un clip, no el partido',
      'El análisis de video cubre ' + num(P.duracion_s, 0) + ' s. Las cifras del clip no describen el partido completo; ' +
      'las del partido vienen de fuentes públicas.'));
    host.appendChild(limite('La narración interpreta cifras',
      'Granite resume los números de cada ventana. El monitor M3 comprueba que el equipo que nombra coincida con los ' +
      'datos, pero no juzga la calidad táctica del texto. La lectura final es del analista.'));

    // 5 · Gobernanza ---------------------------------------------------------
    host.appendChild(seccion('Gobernanza y tecnología IBM'));
    host.appendChild(el('div', { class: 'stat-row' },
      stat('Modelo', m3.modelo || '—', 'IBM watsonx.ai', true),
      stat('Llamadas auditadas', num(m3.pass) + '/' + num(m3.llamadas), num(m3.offline) + ' sin conexión'),
      stat('Latencia media', num(m3.latencia_ms_media, 0) + ' ms', 'máxima ' + num(m3.latencia_ms_max, 0) + ' ms'),
      stat('Costo de la corrida', num(m3.costo_ru, 2) + ' RU', 'unidades de recurso de watsonx')));
    host.appendChild(parrafos('Qué revisa el monitor M3 en cada llamada', [
      '1. Que el modelo sea un IBM Granite autorizado.',
      '2. Que la respuesta tenga el formato esperado.',
      '3. Que la narración no pase de ' + num(m3.max_palabras) + ' palabras, para que quepa en su ventana de audio.',
      '4. Que el equipo que la narración da como dominante coincida con los datos de esa ventana.'
    ]));
    host.appendChild(parrafos('Trazabilidad', [
      'Cada llamada queda registrada con su modelo, latencia, tokens, costo y resultado. Si algo falla, hay registro.',
      'Las credenciales se leen de un archivo local fuera del código y nunca se publican.',
      'La herramienta táctica también se integró y probó como herramienta de IBM watsonx Orchestrate durante el desarrollo.'
    ]));

    // 6 · Lo que no afirmamos ------------------------------------------------
    host.appendChild(seccion('Lo que no afirmamos'));
    host.appendChild(parrafos(null, [
      'No es tiempo real: se analiza un clip ya grabado, y la corrida tarda ' + num(C.duracion_s, 0) + ' s.',
      'No damos un porcentaje global de precisión: todavía no tenemos una referencia etiquetada a mano para medirla.',
      'No calculamos xG, PPDA ni pases entre líneas.',
      'Solo lo probamos con planos amplios de transmisión de TV.',
      'La IA no ve el video: Granite solo lee las cifras que le entrega el motor.'
    ]));
  }

  fetch('../data/metodo.json')
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(function (e) {
      console.error('[metodo] ', e);
      document.getElementById('data-error').hidden = false;
    });
})();
