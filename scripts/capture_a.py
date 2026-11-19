"""Prueba A (datos): corre UN modo original de main.py y captura sus datos.

No modifica main.py: reemplaza en memoria los anotadores por envoltorios que
guardan lo que reciben (cajas, track_id, equipos, keypoints) y luego dibujan
igual que siempre. Los cuadros se descartan (sin video). TeamClassifier se
sustituye por la versión con semillas (mismas que en C).

BALL_DETECTION necesita supervision 0.23: correr con PYTHONPATH=.sv023.

Uso:
  python scripts/capture_a.py --mode RADAR --outdir outputs/experiment/A_data
"""
import argparse
import json
import os
import time
import traceback

import exp_common as ec
from run_mode import PeakSampler

CLASS_NAMES = {0: 'ball', 1: 'goalkeeper', 2: 'player', 3: 'referee'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', required=True)
    p.add_argument('--source', default=ec.DEFAULT_VIDEO)
    p.add_argument('--outdir', required=True)
    p.add_argument('--device', default='cuda')
    p.add_argument('--seed', type=int, default=ec.SEED)
    p.add_argument('--max-frames', type=int, default=None)
    args = p.parse_args()

    import numpy as np
    import supervision as sv
    import main as soccer
    from sports.common.ball import BallAnnotator
    from sports.common.view import ViewTransformer

    cur = {'i': 0}
    obj = {k: [] for k in ['frame', 'source', 'track_id', 'class_id', 'class_name', 'team',
                           'x1', 'y1', 'x2', 'y2', 'conf']}
    frm = {k: [] for k in ['frame', 'kp_x', 'kp_y', 'kp_conf', 'H']}

    def add_dets(source, d, lookup=None):
        for k in range(len(d)):
            obj['frame'].append(cur['i']); obj['source'].append(source)
            tid = None if d.tracker_id is None else int(d.tracker_id[k])
            obj['track_id'].append(tid)
            obj['class_id'].append(int(d.class_id[k]))
            obj['class_name'].append(CLASS_NAMES.get(int(d.class_id[k])))
            team = None
            if lookup is not None and int(lookup[k]) in (0, 1):
                team = int(lookup[k])
            obj['team'].append(team)
            for c, v in zip(['x1', 'y1', 'x2', 'y2'], d.xyxy[k]):
                obj[c].append(float(v))
            obj['conf'].append(None if d.confidence is None else float(d.confidence[k]))

    def add_kp(keypoints, H=None):
        xy = keypoints.xy[0] if len(keypoints) else np.zeros((0, 2))
        conf = (keypoints.confidence[0] if len(keypoints) and keypoints.confidence is not None
                else np.zeros((len(xy),)))
        frm['frame'].append(cur['i'])
        frm['kp_x'].append([float(v) for v in xy[:, 0]])
        frm['kp_y'].append([float(v) for v in xy[:, 1]])
        frm['kp_conf'].append([float(v) for v in conf])
        frm['H'].append(None if H is None else [float(v) for v in H.ravel()])

    def wrap(annotator, fn):
        orig = annotator.annotate
        def annotate(*a, **kw):
            fn(*a, **kw)
            return orig(*a, **kw)
        annotator.annotate = annotate

    mode = args.mode
    soccer.TeamClassifier = ec.make_seeded_team_classifier(args.seed)
    if mode == 'PITCH_DETECTION':
        wrap(soccer.VERTEX_LABEL_ANNOTATOR, lambda scene, kp, *a, **kw: add_kp(kp))
    elif mode == 'PLAYER_DETECTION':
        wrap(soccer.BOX_ANNOTATOR, lambda scene, d, *a, **kw: add_dets('det', d))
    elif mode == 'PLAYER_TRACKING':
        wrap(soccer.ELLIPSE_ANNOTATOR, lambda scene, d, *a, **kw: add_dets('track', d))
    elif mode in ('TEAM_CLASSIFICATION', 'RADAR'):
        wrap(soccer.ELLIPSE_ANNOTATOR, lambda scene, d, *a, custom_color_lookup=None, **kw:
             add_dets('track', d, custom_color_lookup))
        if mode == 'RADAR':
            orig_render = soccer.render_radar
            def render_radar(detections, keypoints, color_lookup):
                m = (keypoints.xy[0][:, 0] > 1) & (keypoints.xy[0][:, 1] > 1)
                try:
                    H = ViewTransformer(keypoints.xy[0][m].astype(np.float32),
                                        np.array(soccer.CONFIG.vertices)[m].astype(np.float32)).m
                except Exception:
                    H = None
                add_kp(keypoints, H)
                return orig_render(detections, keypoints, color_lookup)
            soccer.render_radar = render_radar
    elif mode == 'BALL_DETECTION':
        class RecordingBallAnnotator(BallAnnotator):
            def annotate(self, frame, detections):
                add_dets('ball', detections)
                return super().annotate(frame, detections)
        soccer.BallAnnotator = RecordingBallAnnotator
    else:
        raise SystemExit(f'modo desconocido: {mode}')

    runners = {
        'PITCH_DETECTION': soccer.run_pitch_detection,
        'PLAYER_DETECTION': soccer.run_player_detection,
        'BALL_DETECTION': soccer.run_ball_detection,
        'PLAYER_TRACKING': soccer.run_player_tracking,
        'TEAM_CLASSIFICATION': soccer.run_team_classification,
        'RADAR': soccer.run_radar,
    }
    record = {'test': 'A_data', 'mode': mode, 'supervision': sv.__version__, 'seed': args.seed}
    sampler = PeakSampler(use_gpu=args.device.startswith('cuda'))
    sampler.start()
    record['gpu_start'] = ec.gpu_now()
    t0 = time.perf_counter()
    first = None
    try:
        ec.seed_everything(args.seed)
        for _ in runners[mode](source_video_path=args.source, device=args.device):
            if first is None:
                first = time.perf_counter()
            cur['i'] += 1
            if cur['i'] % 50 == 0:
                print(f"frame {cur['i']}", flush=True)
            if args.max_frames and cur['i'] >= args.max_frames:
                break
        record['status'] = 'OK'
    except Exception as e:
        record['status'] = 'FAIL'
        record['error'] = f'{type(e).__name__}: {e}'.splitlines()[0]
        record['traceback'] = traceback.format_exc()
    t1 = time.perf_counter()
    sampler.stop_event.set(); sampler.join()

    outdir = os.path.join(args.outdir, mode)
    ec.write_parquet(obj, os.path.join(outdir, 'objects.parquet'))
    if frm['frame']:
        ec.write_parquet(frm, os.path.join(outdir, 'frames.parquet'))
    record['frames'] = cur['i']
    record['total_s'] = round(t1 - t0, 2)
    if first is not None and cur['i'] > 1:
        record['setup_s'] = round(first - t0, 2)
        record['fps_steady'] = round((cur['i'] - 1) / (t1 - first), 3)
    record['peak_rss_mb'] = round(sampler.peak_rss / 2**20)
    record['gpu_mem_peak_mib'] = sampler.peak_gpu_mib
    record['gpu_end'] = ec.gpu_now()
    with open(os.path.join(outdir, 'metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in record.items() if k != 'traceback'}, ensure_ascii=False))
    if record['status'] != 'OK':
        print(record['traceback'])
        raise SystemExit(1)


if __name__ == '__main__':
    main()
