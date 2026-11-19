"""Un solo video con los resultados de todos los modelos encima de la misma imagen.

No vuelve a correr los modelos: dibuja a partir de los parquet de run_together.py
(objects.parquet y frames.parquet) sobre el video original.

  - keypoints de la cancha (modelo de cancha)
  - jugadores, porteros y árbitros con elipse del color de su equipo y su track_id
    (modelo de jugadores + ByteTrack + SigLIP/UMAP/KMeans)
  - balón con su rastro (modelo de balón)
  - radar con la vista cenital (homografía)

Uso:
  python scripts/render_combined.py --data outputs/experiment/C2_video --target outputs/experiment/TODOS_JUNTOS.mp4
"""
import argparse
import os

import cv2
import numpy as np
import pyarrow.parquet as pq

import exp_common as ec


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', default=ec.DEFAULT_VIDEO)
    p.add_argument('--data', default=os.path.join(ec.ROOT, 'outputs', 'experiment', 'C2_video'))
    p.add_argument('--target', default=os.path.join(ec.ROOT, 'outputs', 'experiment', 'TODOS_JUNTOS.mp4'))
    p.add_argument('--radar-size', type=float, default=0.15,
                   help='ancho del radar como fracción del ancho del video (RADAR original: 0.5)')
    args = p.parse_args()

    import supervision as sv
    import main as soccer
    from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
    from sports.common.ball import BallAnnotator

    objs = pq.read_table(os.path.join(args.data, 'objects.parquet')).to_pydict()
    frms = pq.read_table(os.path.join(args.data, 'frames.parquet')).to_pydict()
    by_frame = {}
    for k in range(len(objs['frame'])):
        by_frame.setdefault(objs['frame'][k], []).append(k)
    frame_info = {f: i for i, f in enumerate(frms['frame'])}

    def detections(idx):
        if not idx:
            return sv.Detections.empty()
        return sv.Detections(
            xyxy=np.array([[objs[c][k] for c in ('x1', 'y1', 'x2', 'y2')] for k in idx], np.float32),
            class_id=np.array([objs['class_id'][k] for k in idx]),
            tracker_id=np.array([objs['track_id'][k] if objs['track_id'][k] is not None else -1 for k in idx]),
            confidence=np.array([objs['conf'][k] if objs['conf'][k] is not None else 1.0 for k in idx], np.float32))

    vertex = sv.VertexAnnotator(color=sv.Color.from_hex('#A020F0'), radius=6)
    ball_annotator = BallAnnotator(radius=6, buffer_size=10)
    colors = [sv.Color.from_hex(c) for c in soccer.COLORS]
    legend = [('Equipo 1', colors[0]), ('Equipo 2', colors[1]), ('Arbitro', colors[3]),
              ('Cancha (puntos)', sv.Color.from_hex('#A020F0')), ('Balon (rastro)', sv.Color.from_hex('#FFFFFF'))]

    video_info = sv.VideoInfo.from_video_path(args.source)
    with sv.VideoSink(args.target, video_info) as sink:
        for f, frame in enumerate(sv.get_video_frames_generator(args.source)):
            img = frame.copy()
            rows = by_frame.get(f, [])
            fi = frame_info.get(f)

            # cancha
            if fi is not None and frms['kp_x'][fi]:
                xy = np.stack([frms['kp_x'][fi], frms['kp_y'][fi]], axis=1).astype(np.float32)
                vis = (xy[:, 0] > 1) & (xy[:, 1] > 1)
                if vis.any():
                    img = vertex.annotate(img, sv.KeyPoints(xy=xy[vis][None]))

            # jugadores / porteros / árbitros por equipo (como TEAM_CLASSIFICATION)
            people = [k for k in rows if objs['source'][k] == 'track' and objs['class_id'][k] in (1, 2, 3)]
            dets = detections(people)
            lookup = np.array([objs['team'][k] if objs['team'][k] is not None else soccer.REFEREE_CLASS_ID
                               for k in people], dtype=int)
            if len(dets):
                labels = [str(t) for t in dets.tracker_id]
                img = soccer.ELLIPSE_ANNOTATOR.annotate(img, dets, custom_color_lookup=lookup)
                img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(img, dets, labels, custom_color_lookup=lookup)

            # balón con rastro
            ball = detections([k for k in rows if objs['source'][k] == 'ball'])
            img = ball_annotator.annotate(img, ball)

            # radar (como RADAR)
            h, w, _ = frame.shape
            if fi is not None and frms['homography_valid'][fi]:
                radar = draw_pitch(config=soccer.CONFIG)
                pxy = np.array([[objs['pitch_x'][k], objs['pitch_y'][k]] for k in people
                                if objs['pitch_x'][k] is not None], np.float32).reshape(-1, 2)
                lk = np.array([lookup[i] for i, k in enumerate(people)
                               if objs['pitch_x'][k] is not None], dtype=int)
                for c in range(4):
                    radar = draw_points_on_pitch(config=soccer.CONFIG, xy=pxy[lk == c],
                                                 face_color=colors[c], radius=20, pitch=radar)
                bxy = np.array([[objs['pitch_x'][k], objs['pitch_y'][k]] for k in rows
                                if objs['source'][k] == 'ball' and objs['pitch_x'][k] is not None],
                               np.float32).reshape(-1, 2)
                radar = draw_points_on_pitch(config=soccer.CONFIG, xy=bxy, face_color=sv.Color.WHITE,
                                             edge_color=sv.Color.BLACK, radius=12, pitch=radar)
                rw_max = int(w * args.radar_size)
                radar = sv.resize_image(radar, (rw_max, h), keep_aspect_ratio=True)
                rh, rw, _ = radar.shape
                img = sv.draw_image(img, radar, opacity=0.6,
                                    rect=sv.Rect(x=w // 2 - rw // 2, y=h - rh - 10, width=rw, height=rh))

            # leyenda
            cv2.rectangle(img, (10, 10), (330, 30 + 32 * len(legend)), (0, 0, 0), -1)
            for i, (text, color) in enumerate(legend):
                y = 40 + 32 * i
                cv2.circle(img, (30, y - 8), 9, color.as_bgr(), -1)
                cv2.putText(img, text, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(img, f'cuadro {f}', (w - 200, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            sink.write_frame(img)
            if f % 150 == 0:
                print(f'frame {f}', flush=True)
    print('listo:', args.target)


if __name__ == '__main__':
    main()
