"""Corre un modo de examples/soccer/main.py midiendo tiempo, FPS y memoria.

Reproduce el bucle de main.main() (mismas funciones run_*, mismo VideoSink) pero
sin cv2.imshow, y agrega mediciones. Escribe una línea JSON en outputs/metrics.jsonl.

Uso:
  python scripts/run_mode.py --mode RADAR --source <video> --target outputs/RADAR.mp4 --device cuda
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time
import traceback

import psutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOCCER_DIR = os.path.join(ROOT, 'sports', 'examples', 'soccer')
sys.path.insert(0, SOCCER_DIR)


class PeakSampler(threading.Thread):
    """Muestrea RSS del proceso y memoria GPU (nvidia-smi) cada 0.5 s."""

    def __init__(self, use_gpu: bool):
        super().__init__(daemon=True)
        self.proc = psutil.Process()
        self.use_gpu = use_gpu
        self.peak_rss = 0
        self.peak_gpu_mib = 0
        self.base_gpu_mib = self._gpu_used() if use_gpu else 0
        self.stop_event = threading.Event()

    @staticmethod
    def _gpu_used() -> int:
        try:
            out = subprocess.run(
                ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5).stdout
            return int(out.strip().splitlines()[0])
        except Exception:
            return 0

    def run(self):
        while not self.stop_event.is_set():
            self.peak_rss = max(self.peak_rss, self.proc.memory_info().rss)
            if self.use_gpu:
                self.peak_gpu_mib = max(self.peak_gpu_mib, self._gpu_used())
            self.stop_event.wait(0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--metrics', default=os.path.join(ROOT, 'outputs', 'metrics.jsonl'))
    args = parser.parse_args()
    print(f'start mode={args.mode}', flush=True)

    record = {'mode': args.mode, 'device_requested': args.device,
              'source': args.source, 'target': args.target}
    sampler = PeakSampler(use_gpu=args.device.startswith('cuda'))
    sampler.start()
    t0 = time.perf_counter()
    first_frame_t = None
    frames = 0
    try:
        import torch
        import supervision as sv
        import main as soccer

        record['torch'] = torch.__version__
        record['cuda_available'] = torch.cuda.is_available()
        if torch.cuda.is_available():
            record['gpu_name'] = torch.cuda.get_device_name(0)

        mode = soccer.Mode(args.mode)
        runners = {
            soccer.Mode.PITCH_DETECTION: soccer.run_pitch_detection,
            soccer.Mode.PLAYER_DETECTION: soccer.run_player_detection,
            soccer.Mode.BALL_DETECTION: soccer.run_ball_detection,
            soccer.Mode.PLAYER_TRACKING: soccer.run_player_tracking,
            soccer.Mode.TEAM_CLASSIFICATION: soccer.run_team_classification,
            soccer.Mode.RADAR: soccer.run_radar,
        }
        frame_generator = runners[mode](source_video_path=args.source, device=args.device)
        video_info = sv.VideoInfo.from_video_path(args.source)
        record['source_frames'] = video_info.total_frames
        record['source_fps'] = video_info.fps
        record['resolution'] = f'{video_info.width}x{video_info.height}'
        with sv.VideoSink(args.target, video_info) as sink:
            for frame in frame_generator:
                if first_frame_t is None:
                    first_frame_t = time.perf_counter()
                sink.write_frame(frame)
                frames += 1
                if frames % 25 == 0:  # progreso visible si el proceso se detiene (prueba B)
                    print(f'frame {frames} t={time.perf_counter() - t0:.1f}s', flush=True)
        record['status'] = 'OK'
    except Exception as e:
        record['status'] = 'FAIL'
        record['error'] = f'{type(e).__name__}: {e}'
        record['traceback'] = traceback.format_exc()
    finally:
        t1 = time.perf_counter()
        sampler.stop_event.set()
        sampler.join()

    record['frames_written'] = frames
    record['total_s'] = round(t1 - t0, 2)
    record['fps_total'] = round(frames / (t1 - t0), 2) if frames else 0
    if first_frame_t is not None and frames > 1:
        # Excluye carga de modelos y el ajuste del clasificador de equipos (fase previa al 1er cuadro)
        record['setup_s'] = round(first_frame_t - t0, 2)
        record['fps_steady'] = round((frames - 1) / (t1 - first_frame_t), 2)
    record['peak_rss_mb'] = round(sampler.peak_rss / 2**20)
    if sampler.use_gpu:
        record['gpu_mem_baseline_mib'] = sampler.base_gpu_mib
        record['gpu_mem_peak_mib'] = sampler.peak_gpu_mib
        try:
            import torch
            if torch.cuda.is_available():
                record['torch_max_allocated_mb'] = round(torch.cuda.max_memory_allocated() / 2**20)
        except Exception:
            pass

    os.makedirs(os.path.dirname(args.metrics), exist_ok=True)
    with open(args.metrics, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    summary = {k: v for k, v in record.items() if k != 'traceback'}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if record['status'] != 'OK':
        print(record.get('traceback', ''), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
