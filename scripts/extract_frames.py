"""Extrae cuadros de cada video en outputs/ para revisión visual (outputs/frames/<MODO>_<cuadro>.jpg).

Uso:  python scripts/extract_frames.py [cuadro1 cuadro2 ...]
"""
import glob
import os
import sys

import cv2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = [int(x) for x in sys.argv[1:]] or [50, 250, 450, 700]

out_dir = os.path.join(ROOT, 'outputs', 'frames')
os.makedirs(out_dir, exist_ok=True)
for path in sorted(glob.glob(os.path.join(ROOT, 'outputs', '*.mp4'))):
    mode = os.path.splitext(os.path.basename(path))[0]
    cap = cv2.VideoCapture(path)
    for idx in FRAMES:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            print(f'{mode}: no se pudo leer el cuadro {idx}')
            continue
        frame = cv2.resize(frame, (1280, 720))
        cv2.imwrite(os.path.join(out_dir, f'{mode}_{idx:04d}.jpg'), frame,
                    [cv2.IMWRITE_JPEG_QUALITY, 85])
    cap.release()
    print(f'{mode}: ok')
