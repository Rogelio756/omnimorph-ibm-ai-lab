"""
build_telemetry_snapshot.py
============================
Lee objects.parquet y frames.parquet con pandas (o pyarrow como fallback),
filtra un frame concreto y genera muestra_telemetria.json.

Uso:
    python scripts/build_telemetry_snapshot.py               # frame 300 por defecto
    python scripts/build_telemetry_snapshot.py --frame 450
    python scripts/build_telemetry_snapshot.py --frame 300 --velocity-window 5

Velocidad aproximada: calculada como desplazamiento entre el frame anterior
y el siguiente dentro de la ventana indicada, escalado a cm/s con el FPS del video.
"""
import argparse
import json
import math
import os
import sys
import numpy as np

# ── Carga de datos con pandas si está disponible, pyarrow como fallback ──────
try:
    import pandas as pd
    def read_parquet(path):
        return pd.read_parquet(path)
    def to_list_of_dicts(df):
        return df.to_dict(orient="records")
    def filter_frame(df, frame_id):
        return df[df["frame"] == frame_id]
    def get_scalar(df, col):
        vals = df[col].dropna()
        return vals.iloc[0] if len(vals) else None
    BACKEND = "pandas"
except ImportError:
    import pyarrow.parquet as pq
    import pyarrow.compute as pc
    def read_parquet(path):
        return pq.read_table(path)
    def to_list_of_dicts(table):
        return [{col: table[col][i].as_py() for col in table.schema.names}
                for i in range(len(table))]
    def filter_frame(table, frame_id):
        mask = pc.equal(table["frame"], frame_id)
        return table.filter(mask)
    def get_scalar(table_or_df, col):
        import pyarrow as pa
        if hasattr(table_or_df, "column"):
            arr = table_or_df[col].drop_null()
            return arr[0].as_py() if len(arr) else None
        vals = table_or_df[col].dropna()
        return vals.iloc[0] if len(vals) else None
    BACKEND = "pyarrow"


class _NumpyEncoder(json.JSONEncoder):
    """Serializa tipos numpy/pandas a Python nativos."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return None if np.isnan(obj) else float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBJ_PATH = os.path.join(ROOT, "outputs", "experiment", "C_data", "objects.parquet")
FRM_PATH = os.path.join(ROOT, "outputs", "experiment", "C_data", "frames.parquet")
OUT_PATH = os.path.join(ROOT, "muestra_telemetria.json")
VIDEO_FPS = 25.0   # FPS del video fuente (2e57b9_0.mp4)


def _nan_to_none(v):
    if v is None:
        return None
    try:
        if math.isnan(float(v)):
            return None
    except (TypeError, ValueError):
        pass
    return v


def compute_velocities(all_objects, frame_id, fps, window=5):
    """Calcula velocidades aproximadas para los track_id del frame_id dado.

    Estrategia: busca la posición del mismo track_id en
    [frame_id - window, frame_id + window], calcula el vector de
    desplazamiento y lo divide por el intervalo de tiempo en segundos.
    Devuelve dict {track_id: {"vx_cm_s": float, "vy_cm_s": float, "speed_cm_s": float}}.
    """
    # Construir índice rápido: track_id → {frame: (pitch_x, pitch_y)}
    idx = {}
    rows = to_list_of_dicts(all_objects) if BACKEND == "pyarrow" else all_objects.to_dict(orient="records")
    for row in rows:
        src = row.get("source")
        if src != "track":
            continue
        tid = row.get("track_id")
        frm = row.get("frame")
        px  = _nan_to_none(row.get("pitch_x"))
        py  = _nan_to_none(row.get("pitch_y"))
        if tid is None or px is None or py is None:
            continue
        if tid not in idx:
            idx[tid] = {}
        idx[tid][frm] = (px, py)

    result = {}
    for tid, fmap in idx.items():
        if frame_id not in fmap:
            continue
        # Buscar el frame más cercano antes y después dentro de la ventana
        before = [(f, fmap[f]) for f in fmap if frame_id - window <= f < frame_id]
        after  = [(f, fmap[f]) for f in fmap if frame_id < f <= frame_id + window]
        if not before and not after:
            continue

        if before and after:
            f0, (x0, y0) = max(before, key=lambda t: t[0])
            f1, (x1, y1) = min(after,  key=lambda t: t[0])
        elif before:
            f0, (x0, y0) = max(before, key=lambda t: t[0])
            f1, (x1, y1) = frame_id, fmap[frame_id]
        else:
            f0, (x0, y0) = frame_id, fmap[frame_id]
            f1, (x1, y1) = min(after,  key=lambda t: t[0])

        dt = (f1 - f0) / fps
        if dt == 0:
            continue
        vx = (x1 - x0) / dt
        vy = (y1 - y0) / dt
        speed = math.hypot(vx, vy)
        result[tid] = {
            "vx_cm_s":    round(vx, 1),
            "vy_cm_s":    round(vy, 1),
            "speed_cm_s": round(speed, 1),
        }
    return result


def build_snapshot(frame_id: int, velocity_window: int = 5) -> dict:
    print(f"[{BACKEND}] Leyendo {OBJ_PATH} ...", flush=True)
    all_objects = read_parquet(OBJ_PATH)

    print(f"[{BACKEND}] Leyendo {FRM_PATH} ...", flush=True)
    all_frames  = read_parquet(FRM_PATH)

    # ── Frame metadata ────────────────────────────────────────────────────────
    frm_row  = filter_frame(all_frames, frame_id)
    t_sec    = _nan_to_none(get_scalar(frm_row, "t"))
    n_det    = get_scalar(frm_row, "n_det")
    n_track  = get_scalar(frm_row, "n_track")
    ball_fnd = get_scalar(frm_row, "ball_found")
    h_valid  = get_scalar(frm_row, "homography_valid")
    n_kp     = get_scalar(frm_row, "n_kp_visible")

    # ── Filas del frame ────────────────────────────────────────────────────────
    frm_objects = filter_frame(all_objects, frame_id)
    rows        = to_list_of_dicts(frm_objects)

    # ── Velocidades ──────────────────────────────────────────────────────────
    print(f"  Calculando velocidades (ventana +/-{velocity_window} frames) ...", flush=True)
    velocities = compute_velocities(all_objects, frame_id, VIDEO_FPS, velocity_window)

    # ── Ball ──────────────────────────────────────────────────────────────────
    ball = None
    for r in rows:
        if r.get("source") == "ball":
            ball = {
                "pitch_x_cm": _nan_to_none(r.get("pitch_x")),
                "pitch_y_cm": _nan_to_none(r.get("pitch_y")),
                "conf":       round(_nan_to_none(r.get("conf")) or 0, 4),
                "bbox_px":    {
                    "x1": round(r["x1"], 1), "y1": round(r["y1"], 1),
                    "x2": round(r["x2"], 1), "y2": round(r["y2"], 1),
                },
            }
            break

    # ── Players ───────────────────────────────────────────────────────────────
    players = []
    referees = []
    for r in rows:
        if r.get("source") != "track":
            continue
        tid_raw = r.get("track_id")
        tid     = int(tid_raw) if tid_raw is not None and not (isinstance(tid_raw, float) and math.isnan(tid_raw)) else None
        cls     = r.get("class_name")
        team_raw = _nan_to_none(r.get("team"))
        team    = int(team_raw) if team_raw is not None else None
        px    = _nan_to_none(r.get("pitch_x"))
        py    = _nan_to_none(r.get("pitch_y"))
        vel   = velocities.get(tid, {})
        entry = {
            "track_id":   tid,
            "class":      cls,
            "team_id":    team,
            "pitch_x_cm": round(px, 1) if px is not None else None,
            "pitch_y_cm": round(py, 1) if py is not None else None,
            "conf":       round(_nan_to_none(r.get("conf")) or 0, 4),
            "bbox_px":    {
                "x1": round(r["x1"], 1), "y1": round(r["y1"], 1),
                "x2": round(r["x2"], 1), "y2": round(r["y2"], 1),
            },
            "velocity": vel if vel else None,
        }
        if cls == "referee":
            referees.append(entry)
        else:
            players.append(entry)

    players.sort(key=lambda p: (p["team_id"] if p["team_id"] is not None else 99, p["track_id"]))

    # ── Ensamblado final ──────────────────────────────────────────────────────
    snapshot = {
        "_meta": {
            "source_files": {
                "objects": OBJ_PATH,
                "frames":  FRM_PATH,
            },
            "backend": BACKEND,
            "velocity_window_frames": velocity_window,
            "pitch_reference": {
                "length_cm": 12000,
                "width_cm":  7000,
                "x_axis":    "0 = portería Argentina  →  12000 = portería Francia",
                "y_axis":    "0 = banda sur  →  7000 = banda norte",
            },
        },
        "frame_id":        frame_id,
        "timestamp_s":     round(t_sec, 3) if t_sec is not None else None,
        "n_detections":    n_det,
        "n_tracked":       n_track,
        "ball_found":      ball_fnd,
        "homography_valid": h_valid,
        "n_keypoints_visible": n_kp,
        "ball":            ball,
        "players":         players,
        "referees":        referees,
    }
    return snapshot


def main():
    parser = argparse.ArgumentParser(description="Genera muestra_telemetria.json para un frame.")
    parser.add_argument("--frame",            type=int, default=300,
                        help="Número de frame a extraer (default: 300)")
    parser.add_argument("--velocity-window",  type=int, default=5,
                        help="Ventana en frames para calcular velocidad (default: 5)")
    parser.add_argument("--output",           default=OUT_PATH,
                        help="Ruta del JSON de salida")
    args = parser.parse_args()

    snapshot = build_snapshot(args.frame, args.velocity_window)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, cls=_NumpyEncoder)

    print(f"\n  Guardado en: {args.output}")
    print(f"   frame_id={snapshot['frame_id']}  t={snapshot['timestamp_s']}s  "
          f"jugadores={len(snapshot['players'])}  arbitros={len(snapshot['referees'])}  "
          f"balon={'si' if snapshot['ball'] else 'no'}\n")
    # Usar sys.stdout.buffer para forzar UTF-8 independientemente de la
    # codificación de la consola (cp1252 en Windows rompe con caracteres no-ASCII).
    out = json.dumps(snapshot, ensure_ascii=False, indent=2, cls=_NumpyEncoder)
    sys.stdout.buffer.write(out.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
