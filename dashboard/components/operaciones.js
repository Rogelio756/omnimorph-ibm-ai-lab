/**
 * components/operaciones.js
 * OMNIMORPH — Página Operaciones.
 *  - Monitores: ../data/metodo.json → monitores_detalle (estático, funciona sin servidor).
 *  - Terminal del chat: GET /api/operaciones/chat cada 5 s (solo con dashboard/serve.py).
 *  - Servicios IBM: GET /api/operaciones/ibm (IAM + watsonx.ai sin generar texto, 0 RU).
 * Todo el texto de los datos se inserta con textContent, nunca como HTML.
 */
(function () {
  'use strict';

  var POLL_CHAT_MS = 5000;
  var POLL_IBM_MS = 60000;

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
        if (c == null || c === false) return;
        if (Array.isArray(c)) { agregar(c); return; }
        node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
      });
    })(Array.prototype.slice.call(arguments, 2));
    return node;
  }

  function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }

  function num(v, dec) {
    if (v == null || v === '' || isNaN(Number(v))) return '—';
    return Number(v).toLocaleString('es-MX', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  }

  function hora(ts) {
    var d = ts ? new Date(typeof ts === 'number' ? ts * 1000 : ts) : new Date();
    return d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  }

  function chip(tipo, texto) {
    return el('span', { class: 'chip chip--' + tipo }, el('span', { class: 'chip__dot' }), texto);
  }

  function stat(label, valor, hint) {
    return el('div', { class: 'stat' },
      el('span', { class: 'stat__label', text: label }),
      el('span', { class: 'stat__value', text: valor }),
      hint ? el('span', { class: 'stat__hint', text: hint }) : null);
  }

  // ── Monitores ────────────────────────────────────────────────────────────
  function valorCheck(c) {
    var o = c.observado, l = c.limite;
    if (typeof o === 'boolean') return o ? 'sí' : 'no';
    var dec = (typeof o === 'number' && o % 1 !== 0) ? (Math.abs(o) < 10 ? 2 : 1) : 0;
    var v = num(o, dec);
    if (l == null) return v;
    switch (c.unidad) {
      case 'de': return v + ' de ' + num(l);
      case 'máx.': return v + ' / máx. ' + num(l, l % 1 ? 1 : 0);
      case 'mín.': return v + ' (mín. ' + num(l) + ')';
      case '% mín.': return v + ' % (mín. ' + num(l) + ' %)';
      default: return v + ' (debe ser ' + num(l) + ')';
    }
  }

  function tarjetaMonitor(m) {
    var ok = m.estado === 'PASS';
    var tarjeta = el('article', { class: 'monitor', 'aria-label': m.id + ' ' + m.nombre },
      el('div', { class: 'monitor__cab' },
        el('span', { class: 'monitor__id', text: m.id }),
        chip(ok ? 'ok' : 'alert', m.estado || '—')),
      el('div', { class: 'monitor__nombre', text: m.nombre }));
    m.checks.forEach(function (c) {
      var fila = el('div', { class: 'monitor__check' + (c.pass ? '' : ' monitor__check--fail') },
        el('span', { class: 'monitor__check-desc', text: c.descripcion }),
        el('span', { class: 'monitor__check-val', text: valorCheck(c) }));
      if ((c.unidad === 'máx.' || c.unidad === 'de') && typeof c.observado === 'number' && c.limite) {
        var pct = Math.max(2, Math.min(100, c.observado / c.limite * 100));
        var barra = el('div', { class: 'monitor__barra', role: 'presentation' }, el('span'));
        barra.firstChild.style.width = pct.toFixed(1) + '%';
        fila.appendChild(barra);
      }
      tarjeta.appendChild(fila);
    });
    return tarjeta;
  }

  function renderMonitores(D) {
    var C = D.corrida || {};
    $('monitores-titulo').textContent = 'Monitores de la última corrida · ' +
      (C.fecha ? new Date(C.fecha).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }) : '—') +
      ' · ' + num(C.n_pass) + '/' + num(C.n_total) + ' PASS en ' + num(C.duracion_s, 1) + ' s' +
      (D.coincide_partido === false ? ' · ¡corrida de otro partido!' : '');
    var host = $('monitores');
    vaciar(host);
    (D.monitores_detalle || []).forEach(function (m) { host.appendChild(tarjetaMonitor(m)); });

    var m3 = D.m3 || {};
    var nar = $('narrador');
    vaciar(nar);
    nar.appendChild(stat('Modelo', (m3.modelo || '—').replace('ibm/', ''), 'IBM watsonx.ai'));
    nar.appendChild(stat('Narraciones', num(m3.pass) + '/' + num(m3.llamadas), num(m3.offline) + ' sin conexión'));
    nar.appendChild(stat('Latencia media', num(m3.latencia_ms_media, 0) + ' ms', 'máxima ' + num(m3.latencia_ms_max, 0) + ' ms'));
    nar.appendChild(stat('Costo de la corrida', num(m3.costo_ru, 2) + ' RU', 'estimado por tokens'));

    var chipHost = $('op-chip');
    chipHost.className = 'chip ' + (C.todos_pass ? 'chip--ok' : 'chip--alert');
    $('op-chip-texto').textContent = num(C.n_pass) + '/' + num(C.n_total) + ' monitores PASS';
  }

  // ── Terminal ─────────────────────────────────────────────────────────────
  var term = $('terminal');
  var vistas = {};          // timestamp → ya impreso
  var lineasIBM = 0;

  function escribir(clase, partes) {
    var abajo = term.scrollHeight - term.scrollTop - term.clientHeight < 24;
    var linea = el('div', { class: 'terminal__linea terminal__linea--' + clase }, partes);
    term.appendChild(linea);
    while (term.childNodes.length > 200) term.removeChild(term.firstChild);
    if (abajo) term.scrollTop = term.scrollHeight;
  }

  function pad(s, n) { s = String(s); while (s.length < n) s += ' '; return s; }

  function lineaChat(e) {
    var h = hora(e.timestamp) + '  ';
    var estado = e.bloqueada ? 'BLOQUEADA' : (e.error ? 'ERROR' : (e.status || '—'));
    var clase = (e.bloqueada || e.error) ? 'alerta' : (e.origen === 'regla' ? 'regla' : 'granite');
    var cuerpo;
    if (e.origen === 'regla') {
      cuerpo = pad('regla', 9) + pad('0 RU · sin llamada al modelo', 52) + estado;
    } else {
      cuerpo = pad('granite', 9) +
        pad('in ' + num(e.tokens_in) + ' · out ' + num(e.tokens_out) + ' tok', 24) +
        pad(num(e.latency_ms, 0) + ' ms (1.er token ' + num(e.primer_token_ms, 0) + ' ms)', 30) +
        pad(num(e.ru, 3) + ' RU', 11) + estado;
    }
    escribir(clase, [h + cuerpo]);
    if (e.pregunta) escribir(clase, [el('span', { class: 'terminal__pregunta', text: '          └ «' + e.pregunta + '»' })]);
  }

  function renderTotales(t) {
    var host = $('totales');
    vaciar(host);
    var h = t.hoy, H = t.historico;
    host.appendChild(stat('Preguntas hoy', num(h.preguntas),
      num(h.a_granite) + ' a Granite · ' + num(h.por_regla) + ' por regla · histórico ' + num(H.preguntas)));
    host.appendChild(stat('Tokens hoy', num(h.tokens_in + h.tokens_out),
      'entrada ' + num(h.tokens_in) + ' · salida ' + num(h.tokens_out)));
    host.appendChild(stat('RU hoy', num(h.ru, 2), 'histórico ' + num(H.ru, 2) + ' RU'));
    host.appendChild(stat('Latencia media hoy', h.latencia_ms_media != null ? num(h.latencia_ms_media, 0) + ' ms' : '—',
      num(h.bloqueadas) + ' bloqueadas · ' + num(h.errores) + ' errores'));
  }

  function estadoTerminal(ok, texto) {
    $('term-punto').style.backgroundColor = ok ? 'var(--color-ok)' : 'var(--color-alert)';
    $('term-estado').textContent = texto;
  }

  function sondearChat() {
    if (document.hidden) return;
    fetch('/api/operaciones/chat', { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (d) {
        d.entradas.forEach(function (e) {
          var k = e.timestamp + '|' + e.pregunta;
          if (vistas[k]) return;
          vistas[k] = true;
          lineaChat(e);
        });
        renderTotales(d);
        estadoTerminal(true, 'en vivo · chat_audit.jsonl · actualiza cada ' + POLL_CHAT_MS / 1000 + ' s');
        servidor(true);
      })
      .catch(function () {
        estadoTerminal(false, 'sin servidor local: ejecuta python dashboard/serve.py');
        servidor(false);
      });
  }

  // ── Servicios ────────────────────────────────────────────────────────────
  var ultimoIBM = null;
  var servidorOk = null;

  function servidor(ok) {
    if (servidorOk === ok) return;
    servidorOk = ok;
    renderServicios();
  }

  function renderServicios() {
    var host = $('servicios');
    vaciar(host);
    host.appendChild(chip(servidorOk ? 'ok' : 'alert', 'Servidor local' + (servidorOk ? '' : ' · apagado')));
    var s = ultimoIBM;
    if (s) {
      host.appendChild(chip(s.iam.ok ? 'ok' : 'alert',
        'IBM Cloud IAM · ' + (s.iam.ok ? num(s.iam.ms, 0) + ' ms' : (s.iam.motivo || 'sin respuesta'))));
      host.appendChild(chip(s.watsonx.ok ? 'ok' : 'alert',
        'watsonx.ai ' + (s.watsonx.region ? s.watsonx.region.split('.')[0] : '') + ' · ' +
        (s.watsonx.ok ? 'Granite disponible · ' + num(s.watsonx.ms, 0) + ' ms' : (s.watsonx.motivo || 'sin respuesta'))));
      var ce = s.chat.estado;
      host.appendChild(chip(ce === 'listo' ? 'ok' : ce === 'cargando' ? 'warn' : 'alert',
        'Chat Granite · ' + ce + (s.chat.motivo ? ' (' + s.chat.motivo + ')' : '')));
      host.appendChild(chip('warn', 'watsonx Orchestrate · probado en desarrollo'));
    } else if (servidorOk === false) {
      host.appendChild(chip('warn', 'IBM: sin comprobar (necesita el servidor local)'));
    }
    var boton = el('button', { class: 'btn btn--outline btn-sm', type: 'button', text: 'Comprobar ahora' });
    boton.addEventListener('click', function () { sondearIBM(true); });
    host.appendChild(boton);
    host.appendChild(el('span', { class: 'servicios__hora',
      text: s ? 'comprobado ' + hora(s.comprobado) + ' · 0 RU' : '' }));
  }

  function sondearIBM(forzar) {
    fetch('/api/operaciones/ibm' + (forzar ? '?forzar=1' : ''), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (s) {
        var nueva = !ultimoIBM || ultimoIBM.comprobado !== s.comprobado;
        ultimoIBM = s;
        servidorOk = true;
        renderServicios();
        if (nueva) {
          escribir(s.iam.ok && s.watsonx.ok ? 'info' : 'alerta', [hora(s.comprobado) + '  ' + pad('ibm', 9) +
            'IAM ' + (s.iam.ok ? 'ok ' + num(s.iam.ms, 0) + ' ms' : 'falla (' + (s.iam.motivo || '—') + ')') +
            ' · watsonx.ai ' + (s.watsonx.ok ? 'ok ' + num(s.watsonx.ms, 0) + ' ms · ' + s.watsonx.modelo + ' disponible'
                                             : 'falla (' + (s.watsonx.motivo || '—') + ')') +
            ' · 0 RU']);
          lineasIBM++;
        }
      })
      .catch(function () { servidor(false); });
  }

  // ── Arranque ─────────────────────────────────────────────────────────────
  fetch('../data/metodo.json')
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(renderMonitores)
    .catch(function (e) { console.error('[operaciones]', e); $('data-error').hidden = false; });

  renderServicios();
  sondearIBM(false);
  sondearChat();
  setInterval(sondearChat, POLL_CHAT_MS);
  setInterval(function () { if (!document.hidden) sondearIBM(false); }, POLL_IBM_MS);
  document.addEventListener('visibilitychange', function () { if (!document.hidden) sondearChat(); });
})();
