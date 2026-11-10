/**
 * components/site-nav.js
 * OMNIMORPH — Navegación común. Rellena <nav id="site-nav"> con los enlaces del tablero.
 * Para añadir una página, agrégala a LINKS.
 */
(function () {
  'use strict';

  var LINKS = [
    ['Inicio', 'index.html'],
    ['MATEO', 'mateo.html'],
    ['Partido', 'partido.html'],
    ['Método', 'metodo.html'],
    ['Operaciones', 'operaciones.html'],
  ];

  var host = document.getElementById('site-nav');
  if (!host) return;

  var here = location.pathname.split('/').pop() || 'index.html';
  LINKS.forEach(function (link) {
    var a = document.createElement('a');
    a.className = 'site-nav__link';
    a.href = link[1];
    a.textContent = link[0];
    if (link[1] === here) a.setAttribute('aria-current', 'page');
    host.appendChild(a);
  });
})();
