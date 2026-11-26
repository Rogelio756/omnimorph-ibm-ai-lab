/**
 * dashboard/components/transmision-logica.js
 * OMNIMORPH — Lógica pura de los gráficos de la página Transmisión.
 * Sin DOM. Funciona en el navegador (window.TransmisionLogica) y en Node (module.exports).
 */
(function (raiz) {
  'use strict';
  var L = {};

  // ── Paso 2: cuadro, reloj, escala ──────────────────────────────────────────

  /**
   * indiceCuadro(t, fps, n) → índice de cuadro (0..n-1).
   * t negativo o NaN → 0. Acotado a 0..n-1.
   */
  L.indiceCuadro = function (t, fps, n) {
    if (typeof t !== 'number' || isNaN(t) || t < 0) return 0;
    var i = Math.floor(t * fps);
    if (i < 0) return 0;
    if (i >= n) return n - 1;
    return i;
  };

  /**
   * reloj(t, inicioS) → "MM:SS".
   * Suma inicioS + floor(max(t, 0)), con ceros a la izquierda.
   */
  L.reloj = function (t, inicioS) {
    var seg = inicioS + Math.floor(Math.max(t, 0));
    var mm  = Math.floor(seg / 60);
    var ss  = seg % 60;
    return (mm < 10 ? '0' : '') + mm + ':' + (ss < 10 ? '0' : '') + ss;
  };

  /**
   * escala(anchoEscenario, anchoVideo) → anchoEscenario / anchoVideo.
   * Si alguno es 0 o no numérico → 1.
   */
  L.escala = function (anchoEscenario, anchoVideo) {
    if (!anchoEscenario || !anchoVideo
        || typeof anchoEscenario !== 'number'
        || typeof anchoVideo    !== 'number') return 1;
    if (anchoEscenario === 0 || anchoVideo === 0) return 1;
    return anchoEscenario / anchoVideo;
  };

  // ── Paso 4: jugadas, gráficos visibles, caja, estela ───────────────────────

  /**
   * jugadaEn(t, jugadas) → índice (-1 si no hay jugadas ni coincide).
   * Busca la jugada con t0 <= t < t1.
   * Si t >= t1 de la última → índice de la última.
   * t negativo o sin jugadas → -1.
   */
  L.jugadaEn = function (t, jugadas) {
    if (!jugadas || jugadas.length === 0) return -1;
    if (typeof t !== 'number' || isNaN(t) || t < 0) return -1;
    for (var i = 0; i < jugadas.length; i++) {
      if (t >= jugadas[i].t0 && t < jugadas[i].t1) return i;
    }
    // t está más allá de la última jugada
    var last = jugadas[jugadas.length - 1];
    if (t >= last.t1) return jugadas.length - 1;
    return -1;
  };

  /**
   * graficosVisibles(t, jugadas) → {indice, protagonista, radar, ficha}.
   * indice: índice de la jugada (o -1).
   * Si i === -1 → todos false.
   * dt = t - j.t0.
   * protagonista = 0.5 <= dt && dt < 3.5
   * ficha        = alineaciones solo al inicio: jugada 0, 0.5 <= dt < 3.5
   * radar        = fijo el resto del clip (desde dt 0.5 de la jugada 0 y sin ficha)
   */
  L.graficosVisibles = function (t, jugadas) {
    var i = L.jugadaEn(t, jugadas);
    if (i === -1) return { indice: -1, protagonista: false, radar: false, ficha: false };
    var dt    = t - jugadas[i].t0;
    var ficha = i === 0 && dt >= 0.5 && dt < 3.5;
    return {
      indice:       i,
      protagonista: dt >= 0.5 && dt < 3.5,
      radar:        !ficha && (i > 0 || dt >= 0.5),
      ficha:        ficha,
    };
  };

  /**
   * datoCurioso(lista, i) → el dato que toca en la jugada i (rota), o null.
   */
  L.datoCurioso = function (lista, i) {
    if (!lista || !lista.length || i < 0) return null;
    return lista[i % lista.length];
  };

  /**
   * ultimoValido(cancha) → arreglo: para cada cuadro f, el último cuadro <= f
   * con jugadores en el radar, o -1. En tomas cerradas el radar se queda con
   * la última posición conocida en vez de quedarse vacío.
   */
  L.ultimoValido = function (cancha) {
    var out = new Array(cancha.length);
    var ult = -1;
    for (var f = 0; f < cancha.length; f++) {
      var c = cancha[f];
      if (c && c.p && c.p.length) ult = f;
      out[f] = ult;
    }
    return out;
  };

  /**
   * cajaDe(cuadro, id) → caja [id, x1, y1, x2, y2] con ese id, o null.
   */
  L.cajaDe = function (cuadro, id) {
    if (!cuadro) return null;
    for (var i = 0; i < cuadro.length; i++) {
      if (cuadro[i][0] === id) return cuadro[i];
    }
    return null;
  };

  /**
   * estela(cuadros, id, f, largo) → [[x, y], …] = centros inferiores de la caja.
   * Rango: max(0, f-largo+1) .. f, en orden, saltando cuadros donde no está.
   */
  L.estela = function (cuadros, id, f, largo) {
    var puntos = [];
    var inicio = Math.max(0, f - largo + 1);
    for (var i = inicio; i <= f; i++) {
      var caja = L.cajaDe(cuadros[i], id);
      if (caja) {
        var x = (caja[1] + caja[3]) / 2;
        var y = caja[4];
        puntos.push([x, y]);
      }
    }
    return puntos;
  };

  // ── Paso 5: radar, filasFicha ───────────────────────────────────────────────

  /**
   * puntosRadar(entradaCancha) → {jugadores: [{id, team, x, y}], balon: {x,y}|null}.
   * entradaCancha: {"p": [[id, team, x, y], …], "b": [x, y] | null}
   */
  L.puntosRadar = function (entradaCancha) {
    var jugadores = (entradaCancha.p || []).map(function (row) {
      return { id: row[0], team: row[1], x: row[2], y: row[3] };
    });
    var b = entradaCancha.b;
    var balon = b ? { x: b[0], y: b[1] } : null;
    return { jugadores: jugadores, balon: balon };
  };

  /**
   * filasFicha(ficha, partido) → [{codigo, color, texto}].
   * Primero local, luego visita.
   * texto = esquema + " · " + entrenador
   */
  L.filasFicha = function (ficha, partido) {
    return [
      {
        codigo: partido.local.codigo,
        color:  partido.local.color,
        texto:  ficha.local.esquema + ' \u00b7 ' + ficha.local.entrenador,
      },
      {
        codigo: partido.visita.codigo,
        color:  partido.visita.color,
        texto:  ficha.visita.esquema + ' \u00b7 ' + ficha.visita.entrenador,
      },
    ];
  };

  // ── Paso 6: voz de MATEO ───────────────────────────────────────────────────

  /**
   * textoMateo(texto) → quita prefijo [Wn] y recorta espacios.
   */
  L.textoMateo = function (texto) {
    return texto.replace(/^\[W\d+\]\s*/, '').trim();
  };

  /**
   * ajusteVoz(tVideo, tVoz) → tVideo si abs(diferencia) > 0.3, si no null.
   */
  L.ajusteVoz = function (tVideo, tVoz) {
    return Math.abs(tVideo - tVoz) > 0.3 ? tVideo : null;
  };

  /**
   * fraseEn(t, jugadas) → texto de MATEO sin prefijo para la jugada actual.
   * "" si jugadaEn devuelve -1.
   */
  L.fraseEn = function (t, jugadas) {
    var i = L.jugadaEn(t, jugadas);
    if (i === -1) return '';
    return L.textoMateo(jugadas[i].texto);
  };

  // ── Exportar ───────────────────────────────────────────────────────────────
  if (typeof module !== 'undefined' && module.exports) module.exports = L;
  else raiz.TransmisionLogica = L;
})(this);
