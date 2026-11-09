/**
 * components/chat-widget.js
 * OMNIMORPH — Burbuja flotante del chatbot.
 * Crea el marcado y controla abrir/cerrar; la conversación la lleva components/chat.js,
 * que debe cargarse después de este archivo porque busca estos elementos por id.
 */
(function () {
  'use strict';

  var MARCADO =
    '<section class="chat-widget__panel" id="chat-panel" role="dialog" aria-label="Chatbot táctico">' +
      '<header class="chat-widget__head">' +
        '<div class="chat-widget__title">' +
          '<h2>Chatbot táctico</h2>' +
          '<span class="chip chip--warn" id="chip-estado"><span class="chip__dot"></span>Conectando con Granite…</span>' +
        '</div>' +
        '<button class="btn btn--outline btn-xs" id="nueva" type="button" hidden>Nueva</button>' +
        '<button class="chat-widget__close" id="chat-cerrar" type="button" aria-label="Cerrar chat">' +
          '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
        '</button>' +
      '</header>' +
      '<div class="notice" role="note">' +
        '<span>Puede equivocarse. Responde solo con los datos del partido; contrasta en ' +
        '<a href="partido.html">Partido</a>.</span>' +
      '</div>' +
      '<div class="notice notice--alert" id="estado-aviso" hidden>' +
        '<span class="notice__tag">Estado</span><span></span>' +
      '</div>' +
      '<div class="chat__log" id="log" aria-label="Conversación" aria-live="polite">' +
        '<p class="chat__empty" id="vacio">Elige una pregunta o escribe la tuya.</p>' +
        '<div class="suggest" id="sugeridas" role="group" aria-label="Preguntas sugeridas"></div>' +
      '</div>' +
      '<p class="notice" id="limite" hidden>' +
        '<span class="notice__tag">Límite</span>' +
        '<span>Esta conversación llegó al límite de 30 preguntas. Empieza una nueva para continuar.</span>' +
      '</p>' +
      '<form class="composer" id="form" autocomplete="off">' +
        '<div class="composer__field">' +
          '<label class="composer__label" for="pregunta">Pregunta sobre el partido</label>' +
          '<textarea id="pregunta" rows="1" maxlength="500" disabled placeholder="Pregunta sobre el clip analizado"></textarea>' +
          '<span class="composer__count" id="contador">0 / 500</span>' +
        '</div>' +
        '<button class="btn btn--primary btn-xs" id="enviar" type="submit" disabled>Enviar</button>' +
      '</form>' +
    '</section>' +
    '<button class="chat-widget__bubble" id="chat-burbuja" type="button"' +
    ' aria-label="Abrir chatbot táctico" aria-expanded="false" aria-controls="chat-panel">' +
      '<svg class="chat-widget__icon-open" viewBox="0 0 24 24" aria-hidden="true">' +
        '<path d="M4 5h16v11H9l-5 4z"/>' +
      '</svg>' +
      '<svg class="chat-widget__icon-close" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
    '</button>';

  var raiz = document.createElement('div');
  raiz.className = 'chat-widget';
  raiz.innerHTML = MARCADO;
  document.body.appendChild(raiz);

  var burbuja = document.getElementById('chat-burbuja');

  function alternar(abrir) {
    raiz.classList.toggle('chat-widget--open', abrir);
    burbuja.setAttribute('aria-expanded', String(abrir));
    burbuja.setAttribute('aria-label', abrir ? 'Cerrar chatbot táctico' : 'Abrir chatbot táctico');
    if (abrir) {
      var campo = document.getElementById('pregunta');
      if (!campo.disabled) campo.focus();
    } else if (raiz.contains(document.activeElement)) {
      burbuja.focus();
    }
  }

  function abierto() {
    return raiz.classList.contains('chat-widget--open');
  }

  burbuja.addEventListener('click', function () { alternar(!abierto()); });
  document.getElementById('chat-cerrar').addEventListener('click', function () { alternar(false); });

  // Clic fuera del chat o tecla Escape: cierra
  document.addEventListener('pointerdown', function (e) {
    if (abierto() && !raiz.contains(e.target)) alternar(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && abierto()) alternar(false);
  });
})();
