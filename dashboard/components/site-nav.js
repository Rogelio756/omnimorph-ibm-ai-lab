/**
 * components/site-nav.js
 * OMNIMORPH — Navegación común. Rellena <nav id="site-nav"> con los enlaces del tablero.
 * En modo prueba añade «Tu opinión» al menú y muestra una franja de aviso bajo el menú.
 * Para añadir una página, agrégala a LINKS.
 */
(function () {
  'use strict';

  var LINKS = [
    ['Inicio', 'index.html'],
    ['MATEO', 'mateo.html'],
    ['Partido', 'partido.html'],
    ['Método', 'metodo.html'],
  ];

  var host = document.getElementById('site-nav');
  if (!host) return;

  var here = location.pathname.split('/').pop() || 'index.html';

  function pintarLinks(listaLinks) {
    listaLinks.forEach(function (link) {
      var a = document.createElement('a');
      a.className = 'site-nav__link';
      a.href = link[1];
      a.textContent = link[0];
      if (link[1] === here) a.setAttribute('aria-current', 'page');
      host.appendChild(a);
    });
  }

  pintarLinks(LINKS);

  // Consultar si hay prueba activa; si la hay, añadir «Tu opinión» y la franja
  fetch('/api/prueba/estado', { cache: 'no-store' })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (info) {
      if (!info || !info.activa) return;

      // Añadir enlace «Tu opinión» al menú
      var aOp = document.createElement('a');
      aOp.className = 'site-nav__link site-nav__link--opinion';
      aOp.href = 'opinion.html';
      aOp.textContent = 'Tu opinión';
      if ('opinion.html' === here) aOp.setAttribute('aria-current', 'page');
      host.appendChild(aOp);

      // Franja de aviso bajo el menú (o bajo el header si no hay nav parent)
      var fin = new Date(info.fin);
      var dia = fin.toLocaleDateString('es', { day: 'numeric', month: 'long' });
      var hora = fin.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });

      var franja = document.createElement('div');
      franja.className = 'prueba-franja';
      franja.setAttribute('role', 'note');
      franja.innerHTML =
        'Versi\u00f3n de prueba \u00b7 disponible hasta el ' + dia + ' a las ' + hora +
        ' \u00b7 <a class="prueba-franja__link" href="opinion.html"><strong>Danos tu opini\u00f3n</strong></a>';

      // Insertar justo después del elemento que contiene el nav, o al principio del body
      var padre = host.closest('header') || document.body;
      padre.insertAdjacentElement('afterend', franja);
    })
    .catch(function () { /* sin prueba o sin servidor: silencio */ });
})();
