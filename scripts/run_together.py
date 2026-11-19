"""Pruebas C y C2: los 6 modos de examples/soccer/main.py en UN proceso.

El video se decodifica una vez; en cada cuadro cada modelo corre una sola vez
(cancha, jugadores, balón, SigLIP) y el resultado se reparte a los 6 dibujos.
Replica la lógica de main.py (mismos modelos, parámetros y anotadores) sin
modificar el repo. Única adaptación: InferenceSlicer usa `overlap_filter`
(el alias `overlap_filter_strategy` se eliminó en supervision 0.24; el código
del slicer es idéntico entre 0.23 y 0.25.1).

Salidas en --outdir:
  objects.parquet   una fila por objeto y cuadro (source = det | track | ball)
  frames.parquet    una fila por cuadro (keypoints de cancha, homografía)
  timings.parquet   ms por etapa y por cuadro
  metrics.json      resumen (también se agrega a outputs/experiment/metrics.jsonl)
  <MODO>.mp4        los 6 videos (salvo con --no-video)

Uso:
  python scripts/run_together.py --outdir outputs/experiment/C_video --device cuda
  python scripts/run_together.py --outdir outputs/experiment/C_data --no-video
  python scripts/run_together.py --outdir outputs/experiment/C2 --threads
"""
import argparse
import contextlib
import json
import os
import queue
import threading
import time
import traceback

import exp_common as ec
from run_mode import PeakSampler

STAGES = ['decode', 'pitch', 'player', 'ball', 'tracking', 'teams',
          'homography', 'draw', 'write']
MODES = ['PITCH_DETECTION', 'PLAYER_DETECTION', 'BALL_DETECTION',
         'PLAYER_TRACKING', 'TEAM_CLASSIFICATION', 'RADAR']
CLASS_NAMES = {0: 'ball', 1: 'goalkeeper', 2: 'player', 3: 'referee'}


def ms_since(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


class Pipeline:
    """Modelos y estado (trackers, clasificador) compartidos por los 6 modos."""

    def __init__(self, device: str, seed: int):
        import numpy as np
        import supervision as sv
        from ultralytics import YOLO
        import main as soccer
        from sports.common.ball import BallTracker

        self.np, self.sv, self.soccer = np, sv, soccer
        self.device = device
        self.setup = {}

        t0 = time.perf_counter()
        self.pitch_model = YOLO(soccer.PITCH_DETECTION_MODEL_PATH).to(device=device)
        self.player_model = YOLO(soccer.PLAYER_DETECTION_MODEL_PATH).to(device=device)
        self.ball_model = YOLO(soccer.BALL_DETECTION_MODEL_PATH).to(device=device)
        self.setup['load_yolo_s'] = round(time.perf_counter() - t0, 2)

        def callback(image_slice):
            result = self.ball_model(image_slice, imgsz=640, verbose=False)[0]
            return sv.Detections.from_ultralytics(result)

        self.slicer = sv.InferenceSlicer(
            callback=callback,
            overlap_filter=sv.OverlapFilter.NONE,
            slice_wh=(640, 640),
        )
        self.ball_tracker = BallTracker(buffer_size=20)
        self.tracker = sv.ByteTrack(minimum_consecutive_frames=3)
        self.team_classifier = None
        self.seed = seed

    def fit_teams(self, source: str) -> None:
        """Igual que run_team_classification/run_radar, pero una sola vez."""
        sv, soccer = self.sv, self.soccer
        t0 = time.perf_counter()
        crops = []
        for frame in sv.get_video_frames_generator(source_path=source, stride=soccer.STRIDE):
            result = self.player_model(frame, imgsz=1280, verbose=False)[0]
            detections = sv.Detections.from_ultralytics(result)
            crops += soccer.get_crops(
                frame, detections[detections.class_id == soccer.PLAYER_CLASS_ID])
        self.setup['crops_s'] = round(time.perf_counter() - t0, 2)
        self.setup['n_fit_crops'] = len(crops)

        t0 = time.perf_counter()
        ec.seed_everything(self.seed)
        self.team_classifier = ec.make_seeded_team_classifier(self.seed)(device=self.device)
        self.setup['load_siglip_s'] = round(time.perf_counter() - t0, 2)
        t0 = time.perf_counter()
        self.team_classifier.fit(crops)
        self.setup['fit_umap_kmeans_s'] = round(time.perf_counter() - t0, 2)

    def infer(self, frame, tm: dict) -> dict:
        np, sv, soccer = self.np, self.sv, self.soccer
        from sports.common.view import ViewTransformer

        t = time.perf_counter()
        result = self.pitch_model(frame, verbose=False)[0]
        keypoints = sv.KeyPoints.from_ultralytics(result)
        tm['pitch'] = ms_since(t)

        t = time.perf_counter()
        result = self.player_model(frame, imgsz=1280, verbose=False)[0]
        det = sv.Detections.from_ultralytics(result)
        tm['player'] = ms_since(t)

        t = time.perf_counter()
        ball = self.slicer(frame).with_nms(threshold=0.1)
        ball = self.ball_tracker.update(ball)
        tm['ball'] = ms_since(t)

        t = time.perf_counter()
        tracked = self.tracker.update_with_detections(det)
        tm['tracking'] = ms_since(t)

        t = time.perf_counter()
        players = tracked[tracked.class_id == soccer.PLAYER_CLASS_ID]
        players_team_id = self.team_classifier.predict(soccer.get_crops(frame, players))
        goalkeepers = tracked[tracked.class_id == soccer.GOALKEEPER_CLASS_ID]
        goalkeepers_team_id = soccer.resolve_goalkeepers_team_id(
            players, players_team_id, goalkeepers)
        referees = tracked[tracked.class_id == soccer.REFEREE_CLASS_ID]
        merged = sv.Detections.merge([players, goalkeepers, referees])
        color_lookup = np.array(
            players_team_id.tolist() +
            goalkeepers_team_id.tolist() +
            [soccer.REFEREE_CLASS_ID] * len(referees)
        )
        tm['teams'] = ms_since(t)

        # Homografía como en render_radar(); si no se puede calcular, main.py
        # lanzaría excepción. Aquí se marca como inválida y se sigue.
        t = time.perf_counter()
        H, h_error, merged_xy, ball_xy = None, None, None, None
        if len(keypoints) == 0:
            h_error = 'no pitch keypoints'
            kp_xy = np.zeros((0, 2), np.float32)
            kp_conf = np.zeros((0,), np.float32)
        else:
            kp_xy = keypoints.xy[0]
            kp_conf = (keypoints.confidence[0] if keypoints.confidence is not None
                       else np.full(len(kp_xy), np.nan, np.float32))
        mask = (kp_xy[:, 0] > 1) & (kp_xy[:, 1] > 1)
        if h_error is None:
            try:
                transformer = ViewTransformer(
                    source=kp_xy[mask].astype(np.float32),
                    target=np.array(soccer.CONFIG.vertices)[mask].astype(np.float32))
                H = transformer.m
                merged_xy = transformer.transform_points(
                    merged.get_anchors_coordinates(sv.Position.BOTTOM_CENTER))
                ball_xy = transformer.transform_points(
                    ball.get_anchors_coordinates(sv.Position.BOTTOM_CENTER))
            except Exception as e:  # ValueError de ViewTransformer o cv2.error (<4 puntos)
                h_error = f'{type(e).__name__}: {e}'.splitlines()[0][:200]
        tm['homography'] = ms_since(t)

        return dict(keypoints=keypoints, kp_xy=kp_xy, kp_conf=kp_conf, kp_mask=mask,
                    det=det, ball=ball, tracked=tracked, merged=merged,
                    color_lookup=color_lookup, H=H, h_error=h_error,
                    merged_xy=merged_xy, ball_xy=ball_xy)


class Renderer:
    """Dibuja los 6 videos exactamente como main.py y los escribe."""

    def __init__(self, video_info, outdir: str, stack: contextlib.ExitStack):
        import supervision as sv
        import main as soccer
        from sports.common.ball import BallAnnotator
        self.sv, self.soccer = sv, soccer
        self.ball_annotator = BallAnnotator(radius=6, buffer_size=10)
        self.sinks = {m: stack.enter_context(
            sv.VideoSink(os.path.join(outdir, f'{m}.mp4'), video_info)) for m in MODES}

    def draw(self, frame, st: dict) -> dict:
        sv, soccer = self.sv, self.soccer
        from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
        out = {}

        img = frame.copy()
        out['PITCH_DETECTION'] = soccer.VERTEX_LABEL_ANNOTATOR.annotate(
            img, st['keypoints'], soccer.CONFIG.labels)

        img = frame.copy()
        img = soccer.BOX_ANNOTATOR.annotate(img, st['det'])
        out['PLAYER_DETECTION'] = soccer.BOX_LABEL_ANNOTATOR.annotate(img, st['det'])

        out['BALL_DETECTION'] = self.ball_annotator.annotate(frame.copy(), st['ball'])

        tracked = st['tracked']
        img = frame.copy()
        img = soccer.ELLIPSE_ANNOTATOR.annotate(img, tracked)
        out['PLAYER_TRACKING'] = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
            img, tracked, labels=[str(i) for i in tracked.tracker_id])

        merged, lookup = st['merged'], st['color_lookup']
        labels = [str(i) for i in merged.tracker_id]
        img = frame.copy()
        img = soccer.ELLIPSE_ANNOTATOR.annotate(img, merged, custom_color_lookup=lookup)
        img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
            img, merged, labels, custom_color_lookup=lookup)
        out['TEAM_CLASSIFICATION'] = img

        img = img.copy()
        if st['H'] is not None:  # mismo dibujo que render_radar()
            radar = draw_pitch(config=soccer.CONFIG)
            for k in range(4):
                radar = draw_points_on_pitch(
                    config=soccer.CONFIG, xy=st['merged_xy'][lookup == k],
                    face_color=sv.Color.from_hex(soccer.COLORS[k]), radius=20, pitch=radar)
            h, w, _ = frame.shape
            radar = sv.resize_image(radar, (w // 2, h // 2))
            radar_h, radar_w, _ = radar.shape
            rect = sv.Rect(x=w // 2 - radar_w // 2, y=h - radar_h,
                           width=radar_w, height=radar_h)
            img = sv.draw_image(img, radar, opacity=0.5, rect=rect)
        out['RADAR'] = img
        return out

    def write(self, images: dict) -> None:
        for m in MODES:
            self.sinks[m].write_frame(images[m])


class Recorder:
    """Acumula filas para los parquet."""

    def __init__(self, fps: float):
        self.fps = fps
        self.obj = {k: [] for k in ['frame', 't', 'source', 'track_id', 'class_id', 'class_name',
                                    'team', 'x1', 'y1', 'x2', 'y2', 'conf', 'pitch_x', 'pitch_y']}
        self.frm = {k: [] for k in ['frame', 't', 'n_det', 'n_track', 'ball_found',
                                    'homography_valid', 'homography_error', 'n_kp_visible',
                                    'kp_x', 'kp_y', 'kp_conf', 'H']}
        self.timings = {}

    def _add(self, i, source, xyxy, cls, conf, tid=None, team=None, pxy=None):
        o = self.obj
        o['frame'].append(i); o['t'].append(i / self.fps); o['source'].append(source)
        o['track_id'].append(None if tid is None else int(tid))
        o['class_id'].append(int(cls)); o['class_name'].append(CLASS_NAMES.get(int(cls), str(cls)))
        o['team'].append(team)
        for k, v in zip(['x1', 'y1', 'x2', 'y2'], xyxy):
            o[k].append(float(v))
        o['conf'].append(None if conf is None else float(conf))
        o['pitch_x'].append(None if pxy is None else float(pxy[0]))
        o['pitch_y'].append(None if pxy is None else float(pxy[1]))

    def add(self, i: int, st: dict) -> None:
        det, tracked, merged, ball = st['det'], st['tracked'], st['merged'], st['ball']
        for k in range(len(det)):
            self._add(i, 'det', det.xyxy[k], det.class_id[k], det.confidence[k])
        # equipo (0/1 jugadores y porteros; nulo árbitro) y coordenadas en cancha por track_id
        team_by_tid, pxy_by_tid = {}, {}
        for k in range(len(merged)):
            tid = int(merged.tracker_id[k])
            lk = int(st['color_lookup'][k])
            team_by_tid[tid] = lk if lk in (0, 1) else None
            if st['merged_xy'] is not None:
                pxy_by_tid[tid] = st['merged_xy'][k]
        for k in range(len(tracked)):
            tid = int(tracked.tracker_id[k])
            self._add(i, 'track', tracked.xyxy[k], tracked.class_id[k], tracked.confidence[k],
                      tid=tid, team=team_by_tid.get(tid), pxy=pxy_by_tid.get(tid))
        for k in range(len(ball)):
            self._add(i, 'ball', ball.xyxy[k], ball.class_id[k],
                      None if ball.confidence is None else ball.confidence[k],
                      pxy=None if st['ball_xy'] is None else st['ball_xy'][k])
        f = self.frm
        f['frame'].append(i); f['t'].append(i / self.fps)
        f['n_det'].append(len(det)); f['n_track'].append(len(tracked))
        f['ball_found'].append(len(ball) > 0)
        f['homography_valid'].append(st['H'] is not None)
        f['homography_error'].append(st['h_error'])
        f['n_kp_visible'].append(int(st['kp_mask'].sum()))
        f['kp_x'].append([float(v) for v in st['kp_xy'][:, 0]])
        f['kp_y'].append([float(v) for v in st['kp_xy'][:, 1]])
        f['kp_conf'].append([float(v) for v in st['kp_conf']])
        f['H'].append(None if st['H'] is None else [float(v) for v in st['H'].ravel()])

    def save(self, outdir: str) -> None:
        ec.write_parquet(self.obj, os.path.join(outdir, 'objects.parquet'))
        ec.write_parquet(self.frm, os.path.join(outdir, 'frames.parquet'))
        idx = sorted(self.timings)
        cols = {'frame': idx}
        for s in STAGES:
            cols[f'{s}_ms'] = [self.timings[i].get(s) for i in idx]
        ec.write_parquet(cols, os.path.join(outdir, 'timings.parquet'))

    def stage_summary(self) -> dict:
        import numpy as np
        out = {}
        for s in STAGES:
            v = np.array([t[s] for t in self.timings.values() if t.get(s) is not None])
            if len(v):
                out[s] = {'mean': round(float(v.mean()), 2), 'p50': round(float(np.median(v)), 2),
                          'p95': round(float(np.percentile(v, 95)), 2),
                          'total_s': round(float(v.sum()) / 1000, 2)}
        return out


def run_sequential(pipe, gen, rec, renderer, marks):
    while True:
        tm = {}
        t = time.perf_counter()
        try:
            frame = next(gen)
        except StopIteration:
            break
        tm['decode'] = ms_since(t)
        i = marks['frames']
        st = pipe.infer(frame, tm)
        rec.add(i, st)
        if renderer is not None:
            t = time.perf_counter()
            images = renderer.draw(frame, st)
            tm['draw'] = ms_since(t)
            t = time.perf_counter()
            renderer.write(images)
            tm['write'] = ms_since(t)
        rec.timings[i] = tm
        if marks['first'] is None:
            marks['first'] = time.perf_counter()
        marks['frames'] += 1
        if marks['frames'] % 50 == 0:
            print(f"frame {marks['frames']}", flush=True)


def run_threaded(pipe, gen, rec, renderer, marks, qsize: int = 8):
    """C2: hilo de decodificación -> hilo principal (GPU + CPU) -> hilo de escritura."""
    q_in, q_out = queue.Queue(maxsize=qsize), queue.Queue(maxsize=qsize)
    errors, stop = [], threading.Event()

    def put(q, item):
        while not stop.is_set():
            try:
                q.put(item, timeout=0.5)
                return
            except queue.Full:
                pass

    def decoder():
        try:
            i = 0
            while not stop.is_set():
                t = time.perf_counter()
                try:
                    frame = next(gen)
                except StopIteration:
                    break
                put(q_in, (i, frame, ms_since(t)))
                i += 1
        except Exception:
            errors.append(traceback.format_exc()); stop.set()
        finally:
            put(q_in, None)

    def get(q):
        """Espera un elemento; devuelve None si otro hilo marcó stop."""
        while True:
            try:
                return q.get(timeout=0.5)
            except queue.Empty:
                if stop.is_set():
                    return None

    def writer():
        try:
            while True:
                item = get(q_out)
                if item is None:
                    break
                i, frame, st = item
                if renderer is not None:
                    t = time.perf_counter()
                    images = renderer.draw(frame, st)
                    rec.timings[i]['draw'] = ms_since(t)
                    t = time.perf_counter()
                    renderer.write(images)
                    rec.timings[i]['write'] = ms_since(t)
                marks['frames'] += 1
                if marks['first'] is None:
                    marks['first'] = time.perf_counter()
                if marks['frames'] % 50 == 0:
                    print(f"frame {marks['frames']}", flush=True)
        except Exception:
            errors.append(traceback.format_exc()); stop.set()

    td, tw = threading.Thread(target=decoder), threading.Thread(target=writer)
    td.start(); tw.start()
    try:
        while True:
            item = get(q_in)
            if item is None:
                break
            i, frame, decode_ms = item
            tm = {'decode': decode_ms}
            rec.timings[i] = tm
            st = pipe.infer(frame, tm)
            rec.add(i, st)
            put(q_out, (i, frame, st))
    except Exception:
        errors.append(traceback.format_exc()); stop.set()
    finally:
        put(q_out, None)
        td.join(); tw.join()
    if errors:
        raise RuntimeError('error en un hilo:\n' + errors[0])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', default=ec.DEFAULT_VIDEO)
    p.add_argument('--outdir', required=True)
    p.add_argument('--device', default='cuda')
    p.add_argument('--no-video', action='store_true', help='solo datos: no dibuja ni escribe videos')
    p.add_argument('--threads', action='store_true', help='variante C2 (decode / GPU / escritura)')
    p.add_argument('--seed', type=int, default=ec.SEED)
    p.add_argument('--max-frames', type=int, default=None, help='para pruebas rápidas')
    p.add_argument('--label', default=None)
    p.add_argument('--metrics', default=os.path.join(ec.ROOT, 'outputs', 'experiment', 'metrics.jsonl'))
    args = p.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    variant = 'C2' if args.threads else 'C'
    record = {'test': variant, 'label': args.label or variant, 'video': not args.no_video,
              'device': args.device, 'seed': args.seed, 'source': args.source,
              'outdir': args.outdir, 'max_frames': args.max_frames}
    sampler = PeakSampler(use_gpu=args.device.startswith('cuda'))
    sampler.start()
    record['gpu_start'] = ec.gpu_now()
    import psutil
    record['ram_available_start_mb'] = psutil.virtual_memory().available >> 20
    t0 = time.perf_counter()
    marks = {'frames': 0, 'first': None}
    rec = None
    try:
        import supervision as sv
        import torch
        record['supervision'] = sv.__version__
        record['torch'] = torch.__version__
        ec.seed_everything(args.seed)

        pipe = Pipeline(args.device, args.seed)
        pipe.fit_teams(args.source)
        record['setup'] = pipe.setup

        video_info = sv.VideoInfo.from_video_path(args.source)
        record['source_frames'] = video_info.total_frames
        rec = Recorder(video_info.fps)
        gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
        with contextlib.ExitStack() as stack:
            renderer = None if args.no_video else Renderer(video_info, args.outdir, stack)
            record['setup_s'] = round(time.perf_counter() - t0, 2)
            t_loop = time.perf_counter()
            if args.threads:
                run_threaded(pipe, gen, rec, renderer, marks)
            else:
                run_sequential(pipe, gen, rec, renderer, marks)
            record['loop_s'] = round(time.perf_counter() - t_loop, 2)
        record['status'] = 'OK'
    except Exception as e:
        record['status'] = 'FAIL'
        record['error'] = f'{type(e).__name__}: {e}'.splitlines()[0]
        record['traceback'] = traceback.format_exc()
    finally:
        t1 = time.perf_counter()
        sampler.stop_event.set()
        sampler.join()

    if rec is not None and rec.timings:
        rec.save(args.outdir)
        record['stages_ms'] = rec.stage_summary()
    n = marks['frames']
    record['frames'] = n
    record['total_s'] = round(t1 - t0, 2)
    record['fps_total'] = round(n / (t1 - t0), 3) if n else 0
    if record.get('loop_s'):
        record['fps_loop'] = round(n / record['loop_s'], 3)
    record['peak_rss_mb'] = round(sampler.peak_rss / 2**20)
    if sampler.use_gpu:
        record['gpu_mem_baseline_mib'] = sampler.base_gpu_mib
        record['gpu_mem_peak_mib'] = sampler.peak_gpu_mib
        try:
            import torch
            record['torch_max_allocated_mb'] = round(torch.cuda.max_memory_allocated() / 2**20)
        except Exception:
            pass
    record['gpu_end'] = ec.gpu_now()

    summary = {k: v for k, v in record.items() if k != 'traceback'}
    with open(os.path.join(args.outdir, 'metrics.json'), 'w', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=1)
    os.makedirs(os.path.dirname(args.metrics), exist_ok=True)
    with open(args.metrics, 'a', encoding='utf-8') as f:
        f.write(json.dumps(summary, ensure_ascii=False) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if record['status'] != 'OK':
        print(record.get('traceback', ''), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
