/**
 * components/data-adapter.js
 * OMNIMORPH — Adaptador de datos
 * ================================
 * Archivo ÚNICO que mapea los formatos CSV/JSON entregados por el equipo de
 * análisis a los objetos que consumen los componentes del tablero.
 *
 * Uso:
 *   import { adaptTactical, adaptNarrations, adaptPlayers } from './data-adapter.js';
 *
 * El equipo de análisis solo necesita tocar este archivo cuando cambie
 * el formato de los datos de entrada. Los componentes del tablero nunca
 * consultan el pipeline directamente.
 */

// ── Tipos de entrada esperados (documentación de contrato) ────────────────
//
// Tactical window (tactical_summaries.json):
//   { window_id, t0, t1, frame_start, frame_end, block_height_m,
//     transition_speed_mps, block_compactness_m, pressure_context,
//     dominant_team, n_arg, n_fra, centroid_arg_x_cm, centroid_fra_x_cm }
//
// Narration (narrations.json):
//   { window_id, t0, t1, narracion_es, analisis_tactico,
//     latency_ms, tokens_in, tokens_out, mode }
//
// Player row (objects_cleaned.parquet → CSV/JSON):
//   { frame, track_id_stitched, team, pitch_x_smooth, pitch_y_smooth,
//     pitch_x, pitch_y, source, class_name, x1, y1, x2, y2 }
//
// Monitor report (monitor_m*.json):
//   { monitor, name, status, timestamp, checks, summary }

'use strict';

/**
 * adaptTactical(rawWindow)
 * Convierte una ventana táctica del pipeline al formato que consumen
 * los componentes KPI y el reloj maestro.
 *
 * @param {Object} rawWindow — objeto de tactical_summaries.json
 * @returns {Object} windowData normalizado
 */
function adaptTactical(rawWindow) {
  if (!rawWindow) return null;

  // Normalizar team IDs: el pipeline puede devolver ARG/BRA o FRA/GER
  var domRaw = rawWindow.dominant_team || '';
  var dominant = domRaw === 'ARG' ? 'BRA'
               : domRaw === 'FRA' ? 'GER'
               : domRaw;

  return {
    windowId:         rawWindow.window_id        || 'W?',
    t0:               parseFloat(rawWindow.t0    || 0),
    t1:               parseFloat(rawWindow.t1    || 4),
    frameStart:       parseInt(rawWindow.frame_start || 0),
    frameEnd:         parseInt(rawWindow.frame_end   || 0),
    blockHeightM:     toNum(rawWindow.block_height_m),
    transitionSpeedMps: toNum(rawWindow.transition_speed_mps),
    compactnessM:     toNum(rawWindow.block_compactness_m),
    pressure:         rawWindow.pressure_context  || '—',
    dominantTeam:     dominant,
    nTeamA:           rawWindow.n_arg             ?? null,
    nTeamB:           rawWindow.n_fra             ?? null,
    centroidAx:       toNum(rawWindow.centroid_arg_x_cm),  // en cm
    centroidBx:       toNum(rawWindow.centroid_fra_x_cm),  // en cm
  };
}

/**
 * adaptNarrations(rawNarrations)
 * Convierte el array de narrations.json al formato del panel de crónica.
 *
 * @param {Array} rawNarrations
 * @returns {Array} narraciones normalizadas
 */
function adaptNarrations(rawNarrations) {
  if (!Array.isArray(rawNarrations)) return [];
  return rawNarrations.map(function (n) {
    return {
      windowId:       n.window_id    || 'W?',
      t0:             parseFloat(n.t0 || 0),
      t1:             parseFloat(n.t1 || 4),
      text:           n.narracion_es || n.text || '—',
      analysis:       n.analisis_tactico || '',
      latencyMs:      parseInt(n.latency_ms  || 0),
      tokensIn:       parseInt(n.tokens_in   || 0),
      tokensOut:      parseInt(n.tokens_out  || 0),
      mode:           n.mode || 'offline',
    };
  });
}

/**
 * adaptPlayers(rawObjects, frame, team)
 * Filtra y ordena los jugadores de un equipo en un frame dado.
 * Devuelve los 5 con mayor valor de la métrica activa.
 *
 * @param {Array}  rawObjects  — filas de objects_cleaned.parquet (como array JSON)
 * @param {number} frame       — número de frame
 * @param {number} team        — 0 = BRA, 1 = GER
 * @param {string} metric      — 'pitch_x_smooth' | 'pitch_y_smooth' | etc.
 * @returns {Array} jugadores [{trackId, metricValue, pitchX, pitchY}]
 */
function adaptPlayers(rawObjects, frame, team, metric) {
  metric = metric || 'pitch_x_smooth';
  if (!Array.isArray(rawObjects)) return [];

  return rawObjects
    .filter(function (r) {
      return r.frame === frame
          && r.source === 'track'
          && (r.team === team || r.team === String(team));
    })
    .map(function (r) {
      return {
        trackId:     r.track_id_stitched || r.track_id || '?',
        metricValue: toNum(r[metric] || r.pitch_x_smooth || r.pitch_x),
        pitchX:      toNum(r.pitch_x_smooth || r.pitch_x),
        pitchY:      toNum(r.pitch_y_smooth || r.pitch_y),
      };
    })
    .sort(function (a, b) { return b.metricValue - a.metricValue; })
    .slice(0, 5);
}

/**
 * adaptRadarFrame(rawObjects, frame)
 * Devuelve jugadores y balón en coordenadas pitch para el radar SVG.
 * Coordenadas en cm (0–12000 × 0–7000).
 *
 * @param {Array}  rawObjects
 * @param {number} frame
 * @returns {{ teamA: Array, teamB: Array, ball: Object|null }}
 */
function adaptRadarFrame(rawObjects, frame) {
  if (!Array.isArray(rawObjects)) return { teamA: [], teamB: [], ball: null };

  var pxCol = 'pitch_x_smooth';
  var pyCol = 'pitch_y_smooth';
  var useSmooth = rawObjects.length > 0 && pxCol in rawObjects[0];

  var xCol = useSmooth ? pxCol : 'pitch_x';
  var yCol = useSmooth ? pyCol : 'pitch_y';

  var frameRows = rawObjects.filter(function (r) { return r.frame === frame; });
  var teamA = [], teamB = [], ball = null;

  frameRows.forEach(function (r) {
    if (r.source === 'ball') {
      ball = { x: toNum(r[xCol] || r.pitch_x), y: toNum(r[yCol] || r.pitch_y) };
      return;
    }
    if (r.source !== 'track') return;

    var teamId = parseInt(r.team);
    var obj = {
      trackId: r.track_id_stitched || r.track_id || '?',
      x: toNum(r[xCol] || r.pitch_x),
      y: toNum(r[yCol] || r.pitch_y),
    };

    if (teamId === 0)      teamA.push(obj);
    else if (teamId === 1) teamB.push(obj);
  });

  return { teamA: teamA, teamB: teamB, ball: ball };
}

/**
 * adaptMonitorStatus(rawReport)
 * Extrae el estado de un reporte de monitor para los chips de observabilidad.
 *
 * @param {Object} rawReport — contenido de monitor_m*.json
 * @returns {{ status: 'ok'|'warn'|'alert', label: string }}
 */
function adaptMonitorStatus(rawReport) {
  if (!rawReport) return { status: 'alert', label: '—' };
  var s = (rawReport.status || '').toUpperCase();
  return {
    status: s === 'PASS' ? 'ok' : s === 'WARN' ? 'warn' : 'alert',
    label:  rawReport.monitor || rawReport.name || '?',
  };
}

// ── Utilidades internas ───────────────────────────────────────────────────

function toNum(val) {
  var n = parseFloat(val);
  return isNaN(n) ? null : n;
}

// ── Exportar (compatible con CJS, ESM y script tag global) ────────────────
var DataAdapter = {
  adaptTactical:     adaptTactical,
  adaptNarrations:   adaptNarrations,
  adaptPlayers:      adaptPlayers,
  adaptRadarFrame:   adaptRadarFrame,
  adaptMonitorStatus: adaptMonitorStatus,
};

// ESM
if (typeof exports !== 'undefined') {
  exports.adaptTactical      = adaptTactical;
  exports.adaptNarrations    = adaptNarrations;
  exports.adaptPlayers       = adaptPlayers;
  exports.adaptRadarFrame    = adaptRadarFrame;
  exports.adaptMonitorStatus = adaptMonitorStatus;
}

// Global (browser sin bundler)
if (typeof window !== 'undefined') {
  window.DataAdapter = DataAdapter;
}
