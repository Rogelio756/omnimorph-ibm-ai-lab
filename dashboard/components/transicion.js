/**
 * components/transicion.js
 * OMNIMORPH — Pantalla blanca con cubo de Rubik para cambios de página y fallas.
 *
 * Se carga en <head>, sin defer, para cubrir la página antes de que se pinte.
 * Uso desde otro script: OmniTransicion.falla('Mensaje', alTerminar).
 */
(function () {
  'use strict';

  var DURACION_MS = 5000; // Tiempo total de la pantalla, en cualquier caso
  var CLAVE = 'omni-transicion';

  var pantalla = null;
  var cierre = null;

  // ── Cubo: 27 piezas que giran por capas ──────────────────────────────────
  var COLORES = { U: '#F4D03F', D: '#F5F3EE', F: '#E03A2F', B: '#F07A1A', R: '#2A7DE1', L: '#3FAE49' };
  var GIROS = { x: 'rotateX', y: 'rotateY', z: 'rotateZ' };
  var LADO = 40; // px por pieza

  // Mezcla inicial: el cubo la deshace giro a giro hasta quedar resuelto
  var MEZCLA = [['y', -1, 1], ['x', 1, -1], ['z', 1, 1], ['y', 1, -1], ['x', -1, 1], ['z', -1, -1], ['y', -1, 1]];
  var ENTRADA_MS = 900; // Piezas que llegan volando
  var GIRO_MS = 340; // Cada giro al resolver
  var VUELTA_MS = 1000; // Vuelta final con el cubo armado

  function crearCubo() {
    var cubo = document.createElement('div');
    cubo.className = 'omni-cubo';
    var piezas = [];
    for (var x = -1; x <= 1; x++) {
      for (var y = -1; y <= 1; y++) {
        for (var z = -1; z <= 1; z++) {
          var pieza = document.createElement('div');
          pieza.className = 'omni-pieza';
          var dato = {
            el: pieza, x: x, y: y, z: z,
            giro: 'translate3d(' + x * LADO + 'px,' + y * LADO + 'px,' + z * LADO + 'px)',
          };
          pieza.style.transform = dato.giro;
          agregarCaras(pieza, x, y, z);
          cubo.appendChild(pieza);
          piezas.push(dato);
        }
      }
    }
    return { el: cubo, piezas: piezas };
  }

  function agregarCaras(pieza, x, y, z) {
    var caras = [
      ['rotateX(90deg)', y === -1 && COLORES.U],
      ['rotateX(-90deg)', y === 1 && COLORES.D],
      ['rotateY(0deg)', z === 1 && COLORES.F],
      ['rotateY(180deg)', z === -1 && COLORES.B],
      ['rotateY(90deg)', x === 1 && COLORES.R],
      ['rotateY(-90deg)', x === -1 && COLORES.L],
    ];
    caras.forEach(function (c) {
      var cara = document.createElement('div');
      cara.className = 'omni-cara';
      cara.style.transform = c[0] + ' translateZ(' + LADO / 2 + 'px)';
      if (c[1]) cara.style.backgroundColor = c[1];
      pieza.appendChild(cara);
    });
  }

  function piezasDeCapa(cubo, eje, capa) {
    return cubo.piezas.filter(function (p) { return p[eje] === capa; });
  }

  function fijarGiro(p, eje, sentido) {
    p.giro = GIROS[eje] + '(' + sentido * 90 + 'deg) ' + p.giro;
    p.el.style.transform = p.giro;
    rotarPosicion(p, eje, sentido);
  }

  function esperar(animaciones) {
    return Promise.all(animaciones.map(function (a) { return a.finished; }));
  }

  // Gira 90° la capa indicada y actualiza dónde queda cada pieza
  function girarCapa(cubo, eje, capa, sentido) {
    var capaPiezas = piezasDeCapa(cubo, eje, capa);
    var fin = GIROS[eje] + '(' + sentido * 90 + 'deg) ';
    var animaciones = capaPiezas.map(function (p) {
      return p.el.animate(
        [{ transform: GIROS[eje] + '(0deg) ' + p.giro }, { transform: fin + p.giro }],
        { duration: GIRO_MS, easing: 'ease-in-out', fill: 'forwards' });
    });
    return esperar(animaciones).then(function () {
      capaPiezas.forEach(function (p, i) {
        fijarGiro(p, eje, sentido);
        animaciones[i].cancel();
      });
    });
  }

  function rotarPosicion(p, eje, sentido) {
    var a = eje === 'x' ? 'y' : 'x';
    var b = eje === 'z' ? 'y' : 'z';
    var va = p[a];
    var vb = p[b];
    // CSS gira con el eje Y hacia abajo: los signos siguen esa convención
    if (eje === 'y') {
      p[a] = sentido * vb; p[b] = -sentido * va;
    } else {
      p[a] = -sentido * vb; p[b] = sentido * va;
    }
  }

  function azar(rango) {
    return Math.round((Math.random() - 0.5) * rango);
  }

  // Cada pieza llega desde un punto disperso hasta su lugar
  function juntarPiezas(cubo) {
    return esperar(cubo.piezas.map(function (p) {
      var desde = 'translate3d(' + azar(900) + 'px,' + azar(700) + 'px,' + azar(500) + 'px) '
        + 'rotateX(' + azar(720) + 'deg) rotateY(' + azar(720) + 'deg) ';
      return p.el.animate([
        { transform: desde + p.giro, opacity: 0 },
        { transform: 'translate3d(0px,0px,0px) rotateX(0deg) rotateY(0deg) ' + p.giro, opacity: 1 },
      ], { duration: ENTRADA_MS, delay: Math.random() * 250, easing: 'cubic-bezier(.2,.8,.2,1)', fill: 'backwards' });
    }));
  }

  function darVuelta(cubo) {
    var base = 'rotateX(-30deg) ';
    return cubo.el.animate(
      [{ transform: base + 'rotateY(-40deg)' }, { transform: base + 'rotateY(320deg)' }],
      { duration: VUELTA_MS, easing: 'ease-in-out' }).finished;
  }

  // Secuencia completa: mezclado → piezas que llegan → resuelto → vuelta final
  function armarCubo(cubo) {
    MEZCLA.forEach(function (m) {
      piezasDeCapa(cubo, m[0], m[1]).forEach(function (p) { fijarGiro(p, m[0], m[2]); });
    });
    var pasos = juntarPiezas(cubo);
    MEZCLA.slice().reverse().forEach(function (m) {
      pasos = pasos.then(function () { return girarCapa(cubo, m[0], m[1], -m[2]); });
    });
    pasos.then(function () { return darVuelta(cubo); }).catch(function () {});
  }

  // ── Pantalla ─────────────────────────────────────────────────────────────
  function mostrar(mensaje, esFalla) {
    if (pantalla) {
      if (mensaje) ponerMensaje(mensaje);
      return;
    }
    pantalla = document.createElement('div');
    pantalla.className = 'omni-transicion';
    pantalla.setAttribute('role', esFalla ? 'alert' : 'status');
    var escena = document.createElement('div');
    escena.className = 'omni-escena';
    var cubo = crearCubo();
    escena.appendChild(cubo.el);
    pantalla.appendChild(escena);
    var texto = document.createElement('p');
    texto.className = 'omni-transicion__texto';
    pantalla.appendChild(texto);
    // Va en <html>, no en <body>: así cubre la página antes de que exista el cuerpo
    document.documentElement.appendChild(pantalla);
    ponerMensaje(mensaje);
    armarCubo(cubo);
  }

  function ponerMensaje(mensaje) {
    var texto = pantalla.querySelector('.omni-transicion__texto');
    texto.textContent = mensaje || '';
    texto.classList.toggle('omni-transicion__texto--oculto', !mensaje);
    if (!mensaje) texto.textContent = 'Cargando';
  }

  function ocultar() {
    if (!pantalla) return;
    var saliente = pantalla;
    pantalla = null;
    saliente.classList.add('omni-transicion--saliendo');
    setTimeout(function () { saliente.remove(); }, 300);
  }

  function programarCierre(ms, alTerminar) {
    clearTimeout(cierre);
    cierre = setTimeout(function () {
      ocultar();
      if (alTerminar) alTerminar();
    }, Math.max(ms, 0));
  }

  // ── Cambio de página ─────────────────────────────────────────────────────
  function leerInicio() {
    try {
      var valor = Number(sessionStorage.getItem(CLAVE));
      sessionStorage.removeItem(CLAVE);
      return valor;
    } catch (e) {
      return 0;
    }
  }

  function guardarInicio() {
    try {
      sessionStorage.setItem(CLAVE, String(Date.now()));
      return true;
    } catch (e) {
      return false;
    }
  }

  // Si el clic venía de otra página, la pantalla sigue hasta completar la duración
  var inicio = leerInicio();
  if (inicio) {
    var restante = DURACION_MS - (Date.now() - inicio);
    if (restante > 0) {
      mostrar();
      programarCierre(restante);
    }
  }

  document.addEventListener('click', function (e) {
    if (e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    var enlace = e.target.closest && e.target.closest('a[href]');
    if (!enlace || enlace.target || enlace.hasAttribute('download')) return;
    var destino = new URL(enlace.href, location.href);
    if (destino.origin !== location.origin || !/\.html$/.test(destino.pathname)) return;
    if (destino.pathname === location.pathname) return;
    if (guardarInicio()) mostrar();
  });

  // Al volver con el botón Atrás el navegador puede restaurar la página con la pantalla puesta
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) {
      clearTimeout(cierre);
      ocultar();
    }
  });

  window.OmniTransicion = {
    // Muestra el cubo con un mensaje; la página queda visible al terminar
    falla: function (mensaje, alTerminar) {
      mostrar(mensaje || 'Algo no salió como esperábamos', true);
      programarCierre(DURACION_MS, alTerminar);
    },
  };
})();
