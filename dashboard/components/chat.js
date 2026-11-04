/**
 * components/chat.js
 * OMNIMORPH — Chatbot táctico. Habla con POST /api/chat de serve.py (Granite en watsonx.ai).
 * El texto del modelo se inserta SIEMPRE con textContent, nunca como HTML.
 */
(function () {
  'use strict';

  var MAX_PREGUNTAS = 30;
  var TIMEOUT_MS = 90000;
  var SUGERIDAS = [
    '¿Quién marcó cada gol y en qué minuto?',
    '¿Cómo cambió el partido del 1T al 2T?',
    'Compara el xG de ambos equipos en cada tiempo.',
    '¿Cómo se generó el gol de Müller?',
    '¿Qué bajas tuvo Brasil?',
  ];
  var ERRORES = {
    503: 'El chat no está disponible en este momento.',
    429: 'Demasiadas preguntas seguidas. Espera un minuto e inténtalo de nuevo.',
    502: 'Granite no pudo responder. Inténtalo de nuevo en unos segundos.',
    403: 'El chat solo responde a conexiones locales.',
  };

  var historial = [];
  var preguntas = 0;
  var listo = false;
  var ocupado = false;
  var maxPregunta = 500;

  function $(id) { return document.getElementById(id); }

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

  /** Texto del modelo → párrafos y listas con viñetas, solo con nodos de texto. */
  function renderTexto(destino, texto) {
    var lista = null;
    texto.split('\n').forEach(function (linea) {
      var item = linea.match(/^\s*[-•*]\s+(.*)$/);
      if (item) {
        if (!lista) { lista = el('ul'); destino.appendChild(lista); }
        lista.appendChild(el('li', { text: item[1] }));
        return;
      }
      lista = null;
      if (linea.trim()) destino.appendChild(el('p', { text: linea.trim() }));
    });
  }

  // ── Estado del servidor ──────────────────────────────────────────────────
  var CHIPS = {
    cargando: ['chip--warn', 'Conectando con Granite…'],
    listo: ['chip--ok', 'Granite listo'],
    no_disponible: ['chip--alert', 'Granite no disponible'],
    desactivado: ['chip--alert', 'Chat desactivado'],
  };

  function aplicarEstado(info) {
    var c = CHIPS[info.estado] || CHIPS.no_disponible;
    var chip = $('chip-estado');
    chip.className = 'chip ' + c[0];
    chip.lastChild.textContent = c[1];
    maxPregunta = info.max_pregunta || maxPregunta;
    $('pregunta').maxLength = maxPregunta;
    listo = info.estado === 'listo';
    var aviso = $('estado-aviso');
    // Rojo solo cuando algo falla; cargar es normal
    aviso.classList.toggle('notice--alert', info.estado !== 'cargando');
    if (info.estado === 'cargando') {
      aviso.hidden = false;
      aviso.lastElementChild.textContent = 'Conectando con Granite. Tarda unos segundos.';
    } else if (!listo) {
      aviso.hidden = false;
      aviso.lastElementChild.textContent = 'Revisa IBM_CLOUD_API_KEY, WATSONX_URL y WATSONX_SPACE_ID o WATSONX_PROJECT_ID en .env, ' +
        'y que el SDK ibm-watsonx-ai esté instalado. ' + (info.motivo ? '(' + info.motivo + ')' : '');
    } else {
      aviso.hidden = true;
    }
    actualizarControles();
    return info.estado;
  }

  function consultarEstado() {
    fetch('/api/chat/estado', { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (info) {
        if (aplicarEstado(info) === 'cargando') setTimeout(consultarEstado, 2000);
      })
      .catch(function () {
        aplicarEstado({ estado: 'no_disponible', motivo: 'servidor sin API: arranca dashboard/serve.py' });
      });
  }

  // ── Mensajes ─────────────────────────────────────────────────────────────
  function agregarMensaje(rol, cuerpo) {
    $('vacio').hidden = true;
    $('sugeridas').hidden = true;
    var msg = el('article', { class: 'msg msg--' + rol },
      el('span', { class: 'msg__who', text: rol === 'user' ? 'Tú' : 'MATEO' }), cuerpo);
    $('log').appendChild(msg);
    msg.scrollIntoView({ block: 'end', behavior: 'smooth' });
    return msg;
  }

  function mensajeUsuario(texto) {
    var cuerpo = el('div', { class: 'msg__body' });
    renderTexto(cuerpo, texto);
    return agregarMensaje('user', cuerpo);
  }

  function mensajeAsistente(r) {
    var cuerpo = el('div', { class: 'msg__body' });
    renderTexto(cuerpo, r.respuesta);

    if (r.atribucion_incorrecta && r.atribucion_incorrecta.length) {
      var ul = el('ul');
      r.atribucion_incorrecta.forEach(function (h) { ul.appendChild(el('li', { text: h })); });
      cuerpo.appendChild(el('div', { class: 'msg__flag', role: 'note' },
        el('strong', { text: 'Revisa estas cifras: no coinciden con los datos' }), ul));
    }
    if (r.numeros_sin_respaldo && r.numeros_sin_respaldo.length) {
      cuerpo.appendChild(el('div', { class: 'msg__flag', role: 'note' },
        el('strong', { text: 'Cifras que no aparecen en los datos' }),
        el('span', { text: r.numeros_sin_respaldo.join(', ') + '. Pueden ser cálculos válidos o errores del modelo.' })));
    }
    (r.avisos || []).forEach(function (a) { cuerpo.appendChild(el('span', { class: 'msg__note', text: a })); });
    cuerpo.appendChild(el('span', { class: 'msg__meta', text: r.origen === 'regla'
      ? 'Respuesta directa desde los datos, sin LLM'
      : r.modelo + ' · ' + Math.round(r.latency_ms) + ' ms · tokens ' + r.tokens_in + '/' + r.tokens_out + ' · ' +
        (r.bloqueada ? 'descartada por el verificador' : r.estado) }));
    return agregarMensaje('assistant', cuerpo);
  }

  // ── Envío ────────────────────────────────────────────────────────────────
  function actualizarControles() {
    var limite = preguntas >= MAX_PREGUNTAS;
    var activo = listo && !ocupado && !limite;
    $('pregunta').disabled = !activo;
    $('enviar').disabled = !activo;
    document.querySelectorAll('#sugeridas button').forEach(function (b) { b.disabled = !activo; });
    $('limite').hidden = !limite;
    $('nueva').hidden = preguntas === 0;
  }

  function enviar(texto) {
    texto = (texto || '').trim();
    if (!texto || !listo || ocupado || preguntas >= MAX_PREGUNTAS) return;
    ocupado = true;
    preguntas += 1;
    actualizarControles();
    $('pregunta').value = '';
    contar();
    mensajeUsuario(texto);

    var pendiente = agregarMensaje('assistant', el('div', { class: 'msg__body msg__body--pending', 'aria-live': 'polite', text: 'Pensando…' }));
    var avisoEspera = setTimeout(function () {
      pendiente.querySelector('.msg__body').textContent = 'Pensando… está tardando más de lo normal.';
    }, 6000);
    var control = new AbortController();
    var temporizador = setTimeout(function () { control.abort(); }, TIMEOUT_MS);

    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pregunta: texto, historial: historial.slice(-12) }),
      signal: control.signal,
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok) { var e = new Error(String(r.status)); e.estado = r.status; throw e; }
          return data;
        });
      })
      .then(function (data) {
        pendiente.remove();
        mensajeAsistente(data);
        // Una respuesta descartada no entra al historial: el modelo no debe apoyarse en ella
        if (!data.bloqueada) {
          historial.push({ role: 'user', content: texto }, { role: 'assistant', content: data.respuesta });
        }
      })
      .catch(function (err) {
        pendiente.remove();
        preguntas -= 1; // una pregunta que falló no cuenta
        var cuerpo = el('div', { class: 'msg__body', role: 'alert',
          text: ERRORES[err.estado] || 'No se pudo contactar con el servidor. Inténtalo de nuevo.' });
        agregarMensaje('error', cuerpo).classList.add('msg--assistant');
      })
      .then(function () {
        clearTimeout(temporizador);
        clearTimeout(avisoEspera);
        ocupado = false;
        actualizarControles();
        if (!$('pregunta').disabled) $('pregunta').focus();
      });
  }

  function nuevaConversacion() {
    historial = [];
    preguntas = 0;
    $('log').querySelectorAll('.msg').forEach(function (m) { m.remove(); });
    $('vacio').hidden = false;
    $('sugeridas').hidden = false;
    actualizarControles();
  }

  function contar() {
    $('contador').textContent = $('pregunta').value.length + ' / ' + maxPregunta;
  }

  function iniciar() {
    SUGERIDAS.forEach(function (s) {
      var b = el('button', { class: 'btn btn--outline btn-xs', type: 'button', text: s });
      b.addEventListener('click', function () { enviar(s); });
      $('sugeridas').appendChild(b);
    });
    $('form').addEventListener('submit', function (e) { e.preventDefault(); enviar($('pregunta').value); });
    $('pregunta').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); enviar($('pregunta').value); }
    });
    $('pregunta').addEventListener('input', contar);
    $('nueva').addEventListener('click', nuevaConversacion);
    actualizarControles();
    contar();
    consultarEstado();
  }

  iniciar();
})();
