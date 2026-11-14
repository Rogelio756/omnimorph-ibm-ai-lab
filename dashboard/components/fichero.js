/**
 * components/fichero.js
 * OMNIMORPH — Fichero de jugadores de Partido, con estilo de selección de videojuego.
 * Solo muestra datos reales del partido: no inventa valoraciones ni usa fotos.
 * Uso: OmniFichero.render(host, datos, el), con el creador de nodos de partido.js.
 */
(function () {
  'use strict';

  var CLASES_EQ_DEFAULT = ['bra', 'ger'];
  var CLASES_EQ_UNIFORME = ['partido-a', 'partido-b'];
  var LINEAS = [['', 'Todos'], ['POR', 'Porteros'], ['DEF', 'Defensas'], ['MED', 'Medios'], ['DEL', 'Delanteros']];
  var ORDEN = { POR: 0, DEF: 1, MED: 2, DEL: 3 };
  var CAMISETA = 'M32 12 18 18 6 38l14 8 6-8v52h48V38l6 8 14-8-12-20-14-6q-18 12-36 0z';
  var SVG = 'http://www.w3.org/2000/svg';

  function linea(posicion) {
    if (/portero/i.test(posicion)) return 'POR';
    if (/defensa|lateral/i.test(posicion)) return 'DEF';
    if (/extremo|delantero/i.test(posicion)) return 'DEL';
    return 'MED';
  }

  function camiseta(dorsal, equipo) {
    var s = document.createElementNS(SVG, 'svg');
    s.setAttribute('viewBox', '0 0 100 100');
    s.setAttribute('class', 'camiseta camiseta--' + equipo);
    s.setAttribute('aria-hidden', 'true');
    var forma = document.createElementNS(SVG, 'path');
    forma.setAttribute('d', CAMISETA);
    var numero = document.createElementNS(SVG, 'text');
    numero.setAttribute('x', '50');
    numero.setAttribute('y', '58');
    numero.textContent = String(dorsal);
    s.appendChild(forma);
    s.appendChild(numero);
    return s;
  }

  /** Índice de rendimiento individual: {equipo+dorsal → stats}. */
  function indiceRendimiento(datos) {
    var lista = datos.estadisticas && datos.estadisticas.rendimiento_individual_destacado;
    if (!lista) return {};
    var idx = {};
    lista.forEach(function (r) {
      var clave = (r.equipo || '') + '|' + r.dorsal;
      idx[clave] = r;
    });
    return idx;
  }

  /** Plantilla del equipo con los goles y asistencias que salen de la cronología. */
  function jugadoresDe(datos, clave, rendIdx) {
    var eq = datos.equipos[clave];
    var propios = (datos.goles || []).filter(function (g) { return g.equipo_anotador === eq.pais; });
    var vistos = (datos.vistos_en_clip && datos.vistos_en_clip[clave]) || [];
    return Object.keys(eq.plantilla).map(function (d) {
      var j = eq.plantilla[d];
      var dorsal = Number(d);
      var rendKey = eq.pais + '|' + dorsal;
      return {
        dorsal: dorsal,
        nombre: j.nombre,
        posicion: j.posicion,
        rol_tactico: j.rol_tactico || null,
        titular: j.titular,
        minutos: j.minutos,
        eventos: j.eventos || [],
        visto_en_clip: vistos.indexOf(dorsal) >= 0,
        linea: linea(j.posicion),
        goles: propios.filter(function (g) { return g.anotador && g.anotador.dorsal === dorsal; }).length,
        asistencias: propios.filter(function (g) { return g.asistente && g.asistente.dorsal === dorsal; }).length,
        rendimiento: rendIdx[rendKey] || null,
      };
    }).sort(function (a, b) {
      return (b.titular - a.titular) || (ORDEN[a.linea] - ORDEN[b.linea]) || (a.dorsal - b.dorsal);
    });
  }

  function insignias(j) {
    var texto = j.eventos.join(' ');
    var lista = [];
    if (/Jugador del Partido/i.test(texto)) lista.push(['Jugador del partido', 'estrella']);
    if (/Capit[aá]n/i.test(texto)) lista.push(['Capitán', '']);
    if (j.visto_en_clip) lista.push(['Visto en el clip', '']);
    if (/Baja/i.test(texto)) lista.push(['Baja', 'alerta']);
    if (/Suspendido/i.test(texto)) lista.push(['Suspendido', 'alerta']);
    if (/Tarjeta amarilla/i.test(texto)) lista.push(['Tarjeta amarilla', 'aviso']);
    return lista;
  }

  function render(host, datos, el) {
    var orden = (datos.equipos_orden && datos.equipos_orden.length)
      ? datos.equipos_orden
      : Object.keys(datos.equipos);
    var tieneUniforme = datos.colores_uniforme && orden.length >= 2 &&
      (datos.colores_uniforme[orden[0]] || datos.colores_uniforme[orden[1]]);
    var clasesEq = tieneUniforme ? CLASES_EQ_UNIFORME : CLASES_EQ_DEFAULT;
    var equipos = orden.map(function (k, i) {
      return [k, datos.equipos[k].codigo, clasesEq[i] || 'bra'];
    });
    var estado = { equipo: equipos[0][0], linea: '', dorsal: null };
    var rendIdx = indiceRendimiento(datos);
    var plantillas = {};
    equipos.forEach(function (e) { plantillas[e[0]] = jugadoresDe(datos, e[0], rendIdx); });

    var detalle = el('article', { class: 'fichero__detalle', 'aria-live': 'polite' });
    var rejilla = el('div', { class: 'fichero__rejilla', role: 'group', 'aria-label': 'Jugadores' });
    var botonesEquipo = {};
    var botonesLinea = {};

    function numR(v, dec) {
      if (v == null || isNaN(Number(v))) return '—';
      return Number(v).toLocaleString('es-MX', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
    }

    function pintarDetalle(j) {
      while (detalle.firstChild) detalle.removeChild(detalle.firstChild);
      var codigo = equipos.filter(function (e) { return e[0] === estado.equipo; })[0];
      detalle.className = 'fichero__detalle fichero__detalle--' + codigo[2];
      detalle.appendChild(el('div', { class: 'fichero__retrato' }, camiseta(j.dorsal, codigo[2])));
      detalle.appendChild(el('h2', { text: j.nombre }));
      var puestoTexto = j.posicion + ' · ' + (j.titular ? 'Titular' : 'Suplente') + ' · ' + codigo[1];
      if (j.rol_tactico) puestoTexto += ' · ' + j.rol_tactico;
      detalle.appendChild(el('p', { class: 'fichero__puesto', text: puestoTexto }));
      var marcas = insignias(j);
      if (marcas.length) {
        detalle.appendChild(el('div', { class: 'fichero__insignias' }, marcas.map(function (m) {
          return el('span', { class: 'insignia' + (m[1] ? ' insignia--' + m[1] : ''), text: m[0] });
        })));
      }
      detalle.appendChild(el('dl', { class: 'fichero__cifras' },
        [['Minutos', j.minutos], ['Goles', j.goles], ['Asistencias', j.asistencias]].map(function (c) {
          return el('div', null, el('dt', { text: c[0] }), el('dd', { text: String(c[1]) }));
        })));
      // Rendimiento individual FotMob/Opta (si existe)
      var r = j.rendimiento;
      if (r) {
        var esPortero = r.atajadas != null || r.goles_recibidos != null;
        var cifras = esPortero
          ? [['Calificación', numR(r.calificacion_fotmob, 2)],
             ['Atajadas', numR(r.atajadas, 0)],
             ['Goles rec.', numR(r.goles_recibidos, 0)],
             ['Toques', numR(r.toques, 0)],
             ['Pases', (r.pases_completados != null ? r.pases_completados + '/' + r.pases_totales : '—')],
             ['Recup.', numR(r.recuperaciones, 0)]]
          : [['Calificación', numR(r.calificacion_fotmob, 2)],
             ['Toques', numR(r.toques, 0)],
             ['Pases', (r.pases_completados != null ? r.pases_completados + '/' + r.pases_totales : '—')],
             ['Tiros', numR(r.tiros_totales, 0)],
             ['Duelos G.', numR(r.duelos_ganados, 0)],
             ['Recup.', numR(r.recuperaciones, 0)]];
        detalle.appendChild(el('p', { class: 'fichero__rend-titulo', text: 'FotMob / Opta' }));
        detalle.appendChild(el('dl', { class: 'fichero__cifras fichero__cifras--rend' },
          cifras.map(function (c) {
            return el('div', null, el('dt', { text: c[0] }), el('dd', { text: c[1] }));
          })));
      }
      if (j.eventos.length) {
        detalle.appendChild(el('ul', { class: 'fichero__eventos' },
          j.eventos.map(function (t) { return el('li', { text: t }); })));
      } else {
        detalle.appendChild(el('p', { class: 'fichero__sin-eventos', text: 'Sin eventos registrados en el partido.' }));
      }
    }

    function pintarRejilla() {
      while (rejilla.firstChild) rejilla.removeChild(rejilla.firstChild);
      var codigo = equipos.filter(function (e) { return e[0] === estado.equipo; })[0][2];
      var lista = plantillas[estado.equipo].filter(function (j) { return !estado.linea || j.linea === estado.linea; });
      if (!lista.some(function (j) { return j.dorsal === estado.dorsal; })) estado.dorsal = lista[0].dorsal;
      lista.forEach(function (j) {
        var activa = j.dorsal === estado.dorsal;
        var carta = el('button', { class: 'carta carta--' + codigo + (j.titular ? '' : ' carta--suplente'),
          type: 'button', 'aria-pressed': activa ? 'true' : 'false' },
          el('span', { class: 'carta__linea', text: j.linea }),
          camiseta(j.dorsal, codigo),
          el('span', { class: 'carta__nombre', text: j.nombre }),
          el('span', { class: 'carta__marca', text: j.goles ? j.goles + ' G' + (j.asistencias ? ' · ' + j.asistencias + ' A' : '')
            : (j.asistencias ? j.asistencias + ' A' : j.minutos + ' min') }));
        carta.addEventListener('click', function () {
          estado.dorsal = j.dorsal;
          pintarRejilla();
          if (window.matchMedia('(max-width: 860px)').matches) {
            detalle.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          }
        });
        rejilla.appendChild(carta);
      });
      pintarDetalle(lista.filter(function (j) { return j.dorsal === estado.dorsal; })[0]);
    }

    function marcar() {
      Object.keys(botonesEquipo).forEach(function (k) {
        botonesEquipo[k].setAttribute('aria-pressed', String(k === estado.equipo));
      });
      Object.keys(botonesLinea).forEach(function (k) {
        botonesLinea[k].setAttribute('aria-pressed', String(k === estado.linea));
      });
    }

    var filtros = el('div', { class: 'fichero__filtros' },
      el('div', { class: 'fichero__grupo', role: 'group', 'aria-label': 'Equipo' }, equipos.map(function (e) {
        var eq = datos.equipos[e[0]];
        var etiqueta = eq.pais + (eq.esquema_nota ? ' · ' + eq.esquema_nota.split(' ')[0] : '');
        var b = el('button', { class: 'fichero__filtro', type: 'button', text: etiqueta });
        b.addEventListener('click', function () {
          estado.equipo = e[0]; estado.dorsal = null; marcar(); pintarRejilla();
        });
        botonesEquipo[e[0]] = b;
        return b;
      })),
      el('div', { class: 'fichero__grupo', role: 'group', 'aria-label': 'Línea' }, LINEAS.map(function (l) {
        var b = el('button', { class: 'fichero__filtro', type: 'button', text: l[1] });
        b.addEventListener('click', function () { estado.linea = l[0]; marcar(); pintarRejilla(); });
        botonesLinea[l[0]] = b;
        return b;
      })));

    host.appendChild(filtros);
    host.appendChild(el('div', { class: 'fichero__cuerpo' }, detalle, rejilla));
    marcar();
    pintarRejilla();
  }

  window.OmniFichero = { render: render };
})();
