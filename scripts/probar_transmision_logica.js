/**
 * scripts/probar_transmision_logica.js
 * =====================================
 * Pruebas de las funciones puras de transmision-logica.js con Node.
 * Acepta --hasta N (2–7, por defecto 7).
 * Imprime "OK <n> casos" y sale 0, o el primer error y sale 1.
 *
 * Uso:
 *   node scripts/probar_transmision_logica.js --hasta 2
 */
'use strict';

var assert = require('node:assert/strict');
var L = require('../dashboard/components/transmision-logica.js');

// ── argparse mínimo ──────────────────────────────────────────────────────────
var hasta = 7;
var args = process.argv.slice(2);
for (var ai = 0; ai < args.length; ai++) {
  if (args[ai] === '--hasta' && args[ai + 1]) {
    hasta = parseInt(args[ai + 1], 10);
    ai++;
  }
}

var ncasos = 0;

function ok(descripcion, fn) {
  fn();
  ncasos++;
}

// ── Paso 2: indiceCuadro, reloj, escala ─────────────────────────────────────
function grupo2() {
  ok('indiceCuadro(0, 29.97, 1080) === 0',       function () { assert.equal(L.indiceCuadro(0, 29.97, 1080), 0); });
  ok('indiceCuadro(1, 29.97, 1080) === 29',       function () { assert.equal(L.indiceCuadro(1, 29.97, 1080), 29); });
  ok('indiceCuadro(100, 29.97, 1080) === 1079',   function () { assert.equal(L.indiceCuadro(100, 29.97, 1080), 1079); });
  ok('indiceCuadro(-1, 29.97, 1080) === 0',       function () { assert.equal(L.indiceCuadro(-1, 29.97, 1080), 0); });

  ok('reloj(0, 63) === "01:03"',                  function () { assert.equal(L.reloj(0, 63),    '01:03'); });
  ok('reloj(36.04, 63) === "01:39"',              function () { assert.equal(L.reloj(36.04, 63), '01:39'); });
  ok('reloj(-2, 63) === "01:03"',                 function () { assert.equal(L.reloj(-2, 63),   '01:03'); });

  ok('escala(640, 1280) === 0.5',                 function () { assert.equal(L.escala(640, 1280), 0.5); });
  ok('escala(0, 1280) === 1',                     function () { assert.equal(L.escala(0, 1280),   1); });
}

// ── Paso 4: jugadaEn, graficosVisibles, cajaDe, estela ──────────────────────
function grupo4() {
  var J = [{ t0: 0, t1: 4.5 }, { t0: 4.5, t1: 9.01 }];

  ok('jugadaEn(1, J) === 0',    function () { assert.equal(L.jugadaEn(1,  J), 0); });
  ok('jugadaEn(5, J) === 1',    function () { assert.equal(L.jugadaEn(5,  J), 1); });
  ok('jugadaEn(20, J) === 1',   function () { assert.equal(L.jugadaEn(20, J), 1); });
  ok('jugadaEn(-1, J) === -1',  function () { assert.equal(L.jugadaEn(-1, J), -1); });

  ok('graficosVisibles(0.2, J) → todos false', function () {
    var v = L.graficosVisibles(0.2, J);
    assert.equal(v.protagonista, false);
    assert.equal(v.radar,        false);
    assert.equal(v.ficha,        false);
  });

  ok('graficosVisibles(1.0, J) → {indice:0, protagonista:true, radar:false, ficha:true}', function () {
    var v = L.graficosVisibles(1.0, J);
    assert.equal(v.indice,       0);
    assert.equal(v.protagonista, true);
    assert.equal(v.radar,        false);
    assert.equal(v.ficha,        true);
  });

  ok('graficosVisibles(4.4, J) → protagonista:false, radar:true, ficha:false', function () {
    var v = L.graficosVisibles(4.4, J);
    assert.equal(v.protagonista, false);
    assert.equal(v.radar,        true);
    assert.equal(v.ficha,        false);
  });

  ok('graficosVisibles(5.0, J) → {indice:1, protagonista:true, radar:true, ficha:false}', function () {
    var v = L.graficosVisibles(5.0, J);
    assert.equal(v.indice,       1);
    assert.equal(v.protagonista, true);
    assert.equal(v.radar,        true);
    assert.equal(v.ficha,        false);
  });

  ok('graficosVisibles(4.6, J) → radar sigue fijo al cambiar de jugada', function () {
    assert.equal(L.graficosVisibles(4.6, J).radar, true);
  });

  ok('datoCurioso rota por jugada y tolera listas vacías', function () {
    var D = [{ texto: 'a' }, { texto: 'b' }];
    assert.equal(L.datoCurioso(D, 0).texto, 'a');
    assert.equal(L.datoCurioso(D, 3).texto, 'b');
    assert.equal(L.datoCurioso([], 1), null);
    assert.equal(L.datoCurioso(D, -1), null);
  });

  ok('ultimoValido conserva la última posición en tomas cerradas', function () {
    var K = [{ p: [] }, { p: [[1, 0, 10, 10]] }, { p: [] }, null, { p: [[2, 1, 5, 5]] }];
    assert.deepEqual(L.ultimoValido(K), [-1, 1, 1, 1, 4]);
  });

  var C = [[[6, 10, 10, 20, 40]], [], [[6, 12, 10, 22, 42]]];

  ok('cajaDe(C[2], 6)[4] === 42',       function () { assert.equal(L.cajaDe(C[2], 6)[4], 42); });
  ok('cajaDe(C[1], 6) === null',        function () { assert.equal(L.cajaDe(C[1], 6), null); });
  ok('estela(C, 6, 2, 15) == [[15,40],[17,42]]', function () {
    assert.deepEqual(L.estela(C, 6, 2, 15), [[15, 40], [17, 42]]);
  });
}

// ── Paso 5: puntosRadar, filasFicha ─────────────────────────────────────────
function grupo5() {
  ok('puntosRadar sin balon', function () {
    assert.deepEqual(
      L.puntosRadar({ p: [[6, 1, 640, 310]], b: null }),
      { jugadores: [{ id: 6, team: 1, x: 640, y: 310 }], balon: null }
    );
  });

  ok('puntosRadar con balon', function () {
    assert.deepEqual(
      L.puntosRadar({ p: [], b: [578, 397] }).balon,
      { x: 578, y: 397 }
    );
  });

  var F = {
    local:  { esquema: '3-4-2-1', entrenador: 'Gustavo Alfaro' },
    visita: { esquema: '5-4-1',   entrenador: 'Francisco Molina' },
  };
  var P = {
    local:  { codigo: 'CRC', color: '#00BFFF' },
    visita: { codigo: 'SKN', color: '#FF1493' },
  };

  ok('filasFicha CRC y SKN', function () {
    assert.deepEqual(L.filasFicha(F, P), [
      { codigo: 'CRC', color: '#00BFFF', texto: '3-4-2-1 · Gustavo Alfaro' },
      { codigo: 'SKN', color: '#FF1493', texto: '5-4-1 · Francisco Molina' },
    ]);
  });
}

// ── Paso 6: textoMateo, ajusteVoz, fraseEn ──────────────────────────────────
function grupo6() {
  ok('textoMateo con prefijo [W0]', function () {
    assert.equal(
      L.textoMateo('[W0] San Cristóbal y Nieves presiona'),
      'San Cristóbal y Nieves presiona'
    );
  });
  ok('textoMateo sin prefijo', function () {
    assert.equal(L.textoMateo('  Sin prefijo '), 'Sin prefijo');
  });

  ok('ajusteVoz(10, 10.2) === null',  function () { assert.equal(L.ajusteVoz(10, 10.2), null); });
  ok('ajusteVoz(10, 10.5) === 10',    function () { assert.equal(L.ajusteVoz(10, 10.5), 10); });

  ok('fraseEn con prefijo', function () {
    assert.equal(
      L.fraseEn(1, [{ t0: 0, t1: 4.5, texto: '[W0] Hola' }]),
      'Hola'
    );
  });
  ok('fraseEn con array vacío', function () {
    assert.equal(L.fraseEn(-1, []), '');
  });
}

// ── Ejecutar ─────────────────────────────────────────────────────────────────
try {
  if (hasta >= 2) grupo2();
  if (hasta >= 4) grupo4();
  if (hasta >= 5) grupo5();
  if (hasta >= 6) grupo6();
  console.log('OK ' + ncasos + ' casos');
  process.exit(0);
} catch (e) {
  console.error('FALLA:', e.message);
  process.exit(1);
}
