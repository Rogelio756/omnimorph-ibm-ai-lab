"""Valida los datos de C (o C2) contra los de A, comparando datos, no píxeles.

Criterios:
  cajas      emparejadas por cuadro y clase (Hungarian sobre IoU); cuentan si IoU > 0.95
  track_id   mismo id en las cajas emparejadas
  equipos    mismo equipo en jugadores/porteros emparejados
  keypoints  distancia < 3 px en los puntos visibles en ambos (x > 1 y y > 1)
Un chequeo pasa si >= 99 % de los elementos cumplen (se reporta el % exacto).

Uso:
  python scripts/validate.py --a outputs/experiment/A_data --c outputs/experiment/C_data
"""
import argparse
import json
import os

import numpy as np
import pyarrow.parquet as pq
from scipy.optimize import linear_sum_assignment

IOU_MIN, KP_PX, PASS = 0.95, 3.0, 0.99


def load(path):
    return pq.read_table(path).to_pylist() if os.path.exists(path) else None


def by_frame(rows, source, classes=None, max_frame=None):
    out = {}
    for r in rows:
        if r['source'] != source or (classes and r['class_id'] not in classes):
            continue
        if max_frame is not None and r['frame'] >= max_frame:
            continue
        out.setdefault(r['frame'], []).append(r)
    return out


def iou_matrix(a, b):
    A = np.array([[r['x1'], r['y1'], r['x2'], r['y2']] for r in a], float)
    B = np.array([[r['x1'], r['y1'], r['x2'], r['y2']] for r in b], float)
    x1 = np.maximum(A[:, None, 0], B[None, :, 0]); y1 = np.maximum(A[:, None, 1], B[None, :, 1])
    x2 = np.minimum(A[:, None, 2], B[None, :, 2]); y2 = np.minimum(A[:, None, 3], B[None, :, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = lambda X: (X[:, 2] - X[:, 0]) * (X[:, 3] - X[:, 1])
    return inter / (area(A)[:, None] + area(B)[None, :] - inter + 1e-9)


def match(fa, fc, frames):
    """Pares (ra, rc, iou) emparejados por clase, más conteos sin pareja."""
    pairs, n_a, n_c = [], 0, 0
    for f in frames:
        a_rows, c_rows = fa.get(f, []), fc.get(f, [])
        n_a += len(a_rows); n_c += len(c_rows)
        for cls in {r['class_id'] for r in a_rows} | {r['class_id'] for r in c_rows}:
            a = [r for r in a_rows if r['class_id'] == cls]
            c = [r for r in c_rows if r['class_id'] == cls]
            if not a or not c:
                continue
            m = iou_matrix(a, c)
            ia, ic = linear_sum_assignment(-m)
            pairs += [(a[i], c[j], float(m[i, j])) for i, j in zip(ia, ic)]
    return pairs, n_a, n_c


def check(name, ok, total, extra=None):
    ratio = ok / total if total else 1.0
    d = {'check': name, 'ok': int(ok), 'total': int(total), 'ratio': round(ratio, 5),
         'pass': ratio >= PASS}
    if extra:
        d.update(extra)
    return d


def box_checks(label, a_rows, c_rows, source_a, source_c, classes, frames,
               ids=False, teams=False):
    fa = by_frame(a_rows, source_a, classes)
    fc = by_frame(c_rows, source_c, classes)
    pairs, n_a, n_c = match(fa, fc, frames)
    good = [(ra, rc) for ra, rc, iou in pairs if iou > IOU_MIN]
    ious = [iou for _, _, iou in pairs]
    out = [check(f'{label}: cajas de A con pareja IoU>{IOU_MIN}', len(good), n_a,
                 {'mean_iou': round(float(np.mean(ious)), 5) if ious else None}),
           check(f'{label}: cajas de C con pareja IoU>{IOU_MIN}', len(good), n_c)]
    if ids:
        same = sum(ra['track_id'] == rc['track_id'] for ra, rc in good)
        out.append(check(f'{label}: mismo track_id', same, len(good)))
    if teams:
        tg = [(ra, rc) for ra, rc in good if ra['team'] is not None or rc['team'] is not None]
        same = sum(ra['team'] == rc['team'] for ra, rc in tg)
        swapped = sum(ra['team'] is not None and rc['team'] is not None and ra['team'] == 1 - rc['team']
                      for ra, rc in tg)
        out.append(check(f'{label}: mismo equipo', same, len(tg),
                         {'same_if_labels_swapped': swapped}))
    return out


def kp_checks(label, a_frames, c_frames, frames):
    ca = {r['frame']: r for r in a_frames}
    cc = {r['frame']: r for r in c_frames}
    close = both = vis_agree = vis_total = 0
    max_d = 0.0
    for f in frames:
        if f not in ca or f not in cc:
            continue
        ax, ay = np.array(ca[f]['kp_x']), np.array(ca[f]['kp_y'])
        cx, cy = np.array(cc[f]['kp_x']), np.array(cc[f]['kp_y'])
        if len(ax) != len(cx):
            vis_total += max(len(ax), len(cx)); continue
        va, vc = (ax > 1) & (ay > 1), (cx > 1) & (cy > 1)
        vis_agree += int((va == vc).sum()); vis_total += len(va)
        m = va & vc
        d = np.hypot(ax[m] - cx[m], ay[m] - cy[m])
        both += int(m.sum()); close += int((d < KP_PX).sum())
        if len(d):
            max_d = max(max_d, float(d.max()))
    return [check(f'{label}: keypoints a < {KP_PX} px', close, both, {'max_px': round(max_d, 3)}),
            check(f'{label}: misma visibilidad de keypoints', vis_agree, vis_total)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--a', required=True, help='carpeta con A_data/<MODO>/')
    p.add_argument('--c', required=True, help='carpeta de C o C2 (objects/frames.parquet)')
    p.add_argument('--out', default=None)
    args = p.parse_args()

    c_obj = load(os.path.join(args.c, 'objects.parquet'))
    c_frm = load(os.path.join(args.c, 'frames.parquet'))
    n_frames = len(c_frm)
    results = []

    def a(mode, kind='objects'):
        return load(os.path.join(args.a, mode, f'{kind}.parquet'))

    def fr(mode):
        """Cuadros comparables: los que procesaron A (metrics.json) y C."""
        with open(os.path.join(args.a, mode, 'metrics.json'), encoding='utf-8') as f:
            return range(min(n_frames, json.load(f)['frames']))

    rows = a('PITCH_DETECTION', 'frames')
    if rows:
        results += kp_checks('PITCH_DETECTION', rows, c_frm, fr('PITCH_DETECTION'))
    rows = a('PLAYER_DETECTION')
    if rows is not None:
        results += box_checks('PLAYER_DETECTION', rows, c_obj, 'det', 'det', None, fr('PLAYER_DETECTION'))
    rows = a('BALL_DETECTION')
    if rows is not None:
        results += box_checks('BALL_DETECTION', rows, c_obj, 'ball', 'ball', None, fr('BALL_DETECTION'))
    rows = a('PLAYER_TRACKING')
    if rows is not None:
        results += box_checks('PLAYER_TRACKING', rows, c_obj, 'track', 'track', None,
                              fr('PLAYER_TRACKING'), ids=True)
    for mode in ('TEAM_CLASSIFICATION', 'RADAR'):
        rows = a(mode)
        if rows is not None:
            results += box_checks(mode, rows, c_obj, 'track', 'track', {1, 2, 3},
                                  fr(mode), ids=True, teams=True)
    rows = a('RADAR', 'frames')
    if rows:
        results += kp_checks('RADAR', rows, c_frm, fr('RADAR'))
        n = len(fr('RADAR'))
        h_a = sum(r['H'] is not None for r in rows[:n])
        h_c = sum(r['homography_valid'] for r in c_frm[:n])
        results.append({'check': 'RADAR: cuadros con homografía válida (A vs C)',
                        'A': h_a, 'C': h_c, 'pass': h_a == h_c})

    report = {'a': args.a, 'c': args.c, 'frames': n_frames, 'iou_min': IOU_MIN,
              'kp_px': KP_PX, 'pass_ratio': PASS, 'all_pass': all(r['pass'] for r in results),
              'checks': results}
    out = args.out or os.path.join(args.c, 'validation.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    for r in results:
        mark = 'OK ' if r['pass'] else 'NO '
        detail = (f"{r['ok']}/{r['total']} ({100 * r['ratio']:.2f} %)" if 'ratio' in r
                  else f"A={r['A']} C={r['C']}")
        extra = {k: v for k, v in r.items() if k not in ('check', 'ok', 'total', 'ratio', 'pass', 'A', 'C')}
        print(f"{mark} {r['check']}: {detail} {extra if extra else ''}")
    print('TODO PASA' if report['all_pass'] else 'HAY CHEQUEOS QUE NO PASAN')


if __name__ == '__main__':
    main()
