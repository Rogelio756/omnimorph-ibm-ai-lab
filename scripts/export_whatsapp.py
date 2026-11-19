"""Convierte un video a H.264 / yuv420p / MP4 (faststart), apto para WhatsApp.

WhatsApp manda como video archivos de hasta 16 MB; si sale más pesado, sube --crf
(más compresión) o baja --height.

Uso:
  python scripts/export_whatsapp.py outputs/experiment/TODOS_JUNTOS.mp4
  python scripts/export_whatsapp.py <entrada> --out <salida> --height 720 --crf 26
"""
import argparse
import os

import av


def main():
    p = argparse.ArgumentParser()
    p.add_argument('src')
    p.add_argument('--out', default=None)
    p.add_argument('--height', type=int, default=720)
    p.add_argument('--crf', type=int, default=26)
    args = p.parse_args()
    out = args.out or os.path.splitext(args.src)[0] + '_whatsapp.mp4'

    with av.open(args.src) as inp, av.open(out, 'w', options={'movflags': '+faststart'}) as dst:
        vin = inp.streams.video[0]
        width = round(vin.width * args.height / vin.height / 2) * 2
        vout = dst.add_stream('libx264', rate=vin.average_rate)
        vout.width, vout.height, vout.pix_fmt = width, args.height, 'yuv420p'
        vout.options = {'crf': str(args.crf), 'preset': 'medium', 'profile': 'main'}
        for frame in inp.decode(vin):
            frame = frame.reformat(width=width, height=args.height, format='yuv420p')
            for packet in vout.encode(frame):
                dst.mux(packet)
        for packet in vout.encode():
            dst.mux(packet)
    print(f'{out}  {os.path.getsize(out) / 2**20:.1f} MB')


if __name__ == '__main__':
    main()
