"""Orquesta el experimento en el orden acordado:

  1. C_data    run_together.py --no-video
  2. C_video   run_together.py
  3. C2_video  run_together.py --threads
  4. B         6 procesos run_mode.py a la vez (BALL con supervision 0.23); timeout 10 min
  5. A_data    capture_a.py, los 6 modos originales uno por uno (datos para validar)
  6. validate  C_data, C_video y C2_video contra A_data

Antes de cada fase espera a que la GPU se enfríe. Durante cada fase guarda
nvidia-smi cada 1 s (gpu_<fase>.csv) y RAM del sistema cada 1 s (ram_<fase>.csv).
Resumen por fase en outputs/experiment/phases.jsonl.

Uso (desde omnimorph-pruebas):
  .venv/Scripts/python.exe scripts/run_experiment.py
  .venv/Scripts/python.exe scripts/run_experiment.py --phases B --b-timeout 60   # parcial
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

import psutil

import exp_common as ec

PY = sys.executable
SCRIPTS = os.path.join(ec.ROOT, 'scripts')
MODES = ['PITCH_DETECTION', 'PLAYER_DETECTION', 'BALL_DETECTION',
         'PLAYER_TRACKING', 'TEAM_CLASSIFICATION', 'RADAR']
ALL_PHASES = ['C_data', 'C_video', 'C2_video', 'B', 'A_data', 'validate']


def now():
    return datetime.now().isoformat(timespec='seconds')


def log(msg):
    print(f'[{now()}] {msg}', flush=True)


def tree_rss_mb(pid):
    """RSS del proceso y sus hijos: en Windows .venv/Scripts/python.exe es un
    lanzador que abre el intérprete real como proceso hijo."""
    root = psutil.Process(pid)
    procs = [root] + root.children(recursive=True)
    total = 0
    for q in procs:
        try:
            total += q.memory_info().rss
        except psutil.Error:
            pass
    return total >> 20


def kill_tree(p):
    try:
        for q in psutil.Process(p.pid).children(recursive=True):
            try:
                q.kill()
            except psutil.Error:
                pass
    except psutil.Error:
        pass
    p.kill()
    p.wait()


def env_for(mode=None):
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    if mode == 'BALL_DETECTION':
        env['PYTHONPATH'] = ec.SV023_DIR
    return env


class RamLog(threading.Thread):
    """RAM disponible del sistema y RSS de procesos vigilados, cada 1 s."""

    def __init__(self, path, pids=None):
        super().__init__(daemon=True)
        self.path, self.pids = path, pids or {}
        self.stop_event = threading.Event()
        self.min_available_mb = None
        self.peak_rss = {}

    def run(self):
        with open(self.path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['t', 'available_mb', 'used_pct', 'swap_used_mb'] + list(self.pids))
            t0 = time.time()
            while not self.stop_event.is_set():
                vm, sw = psutil.virtual_memory(), psutil.swap_memory()
                avail = vm.available >> 20
                self.min_available_mb = avail if self.min_available_mb is None else min(self.min_available_mb, avail)
                row = [round(time.time() - t0, 1), avail, vm.percent, sw.used >> 20]
                for name, pid in self.pids.items():
                    try:
                        rss = tree_rss_mb(pid)
                    except psutil.Error:
                        rss = ''
                    if rss != '':
                        self.peak_rss[name] = max(self.peak_rss.get(name, 0), rss)
                    row.append(rss)
                w.writerow(row); f.flush()
                self.stop_event.wait(1.0)


def cooldown(args):
    if args.cool_max <= 0:
        return ec.gpu_now()
    t0 = time.time()
    log(f'enfriando (mín {args.cool_min}s, hasta <= {args.cool_temp} °C, máx {args.cool_max}s)')
    while True:
        g = ec.gpu_now()
        el = time.time() - t0
        if el >= args.cool_max or (el >= args.cool_min and g['temp_c'] <= args.cool_temp):
            log(f"GPU {g['temp_c']} °C tras {el:.0f}s")
            return dict(g, cooldown_s=round(el))
        time.sleep(10)


def run_logged(cmd, logpath, env=None, timeout=None):
    with open(logpath, 'w', encoding='utf-8') as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, env=env or env_for(), cwd=ec.ROOT)
        try:
            return p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            kill_tree(p)
            return 'timeout'


def tail(path, n=3, contains=None):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            lines = [l.rstrip() for l in f if l.strip()]
    except OSError:
        return []
    if contains:
        lines = [l for l in lines if any(c in l for c in contains)]
    return lines[-n:]


def phase_together(name, extra, args, base):
    outdir = os.path.join(base, name)
    os.makedirs(outdir, exist_ok=True)
    cmd = [PY, os.path.join(SCRIPTS, 'run_together.py'), '--outdir', outdir, '--label', name] + extra
    if args.max_frames:
        cmd += ['--max-frames', str(args.max_frames)]
    code = run_logged(cmd, os.path.join(outdir, 'run.log'))
    res = {'exit': code}
    try:
        with open(os.path.join(outdir, 'metrics.json'), encoding='utf-8') as f:
            m = json.load(f)
        res.update({k: m.get(k) for k in ['status', 'error', 'frames', 'total_s', 'setup_s',
                                          'loop_s', 'fps_total', 'fps_loop', 'peak_rss_mb',
                                          'gpu_mem_peak_mib', 'torch_max_allocated_mb']})
    except OSError:
        res['status'] = 'NO_METRICS'
    return res


def phase_b(args, base, ram_path):
    outdir = os.path.join(base, 'B')
    os.makedirs(outdir, exist_ok=True)
    procs, files = {}, {}
    t0 = time.time()
    for mode in MODES:
        cmd = [PY, os.path.join(SCRIPTS, 'run_mode.py'), '--mode', mode, '--source', ec.DEFAULT_VIDEO,
               '--target', os.path.join(outdir, f'{mode}.mp4'), '--device', 'cuda',
               '--metrics', os.path.join(outdir, 'metrics.jsonl')]
        files[mode] = open(os.path.join(outdir, f'{mode}.log'), 'w', encoding='utf-8')
        procs[mode] = subprocess.Popen(cmd, stdout=files[mode], stderr=subprocess.STDOUT,
                                       env=env_for(mode), cwd=ec.ROOT)
    log(f'B: 6 procesos lanzados, timeout {args.b_timeout}s')
    ram = RamLog(ram_path, {m: p.pid for m, p in procs.items()})
    ram.start()
    ended = {}
    while len(ended) < len(procs) and time.time() - t0 < args.b_timeout:
        for m, p in procs.items():
            if m not in ended and p.poll() is not None:
                ended[m] = round(time.time() - t0, 1)
                log(f'B: {m} terminó (exit {p.returncode}) a los {ended[m]}s')
        time.sleep(1)
    killed = []
    for m, p in procs.items():
        if p.poll() is None:
            kill_tree(p); killed.append(m)
    elapsed = round(time.time() - t0, 1)
    if killed:
        log(f'B: detenidos por timeout a los {elapsed}s: {killed}')
    ram.stop_event.set(); ram.join()
    for f in files.values():
        f.close()

    res = {'elapsed_s': elapsed, 'timeout_s': args.b_timeout, 'killed': killed,
           'ram_min_available_mb': ram.min_available_mb, 'procs': {}}
    for m, p in procs.items():
        lp = os.path.join(outdir, f'{m}.log')
        progress = tail(lp, 1, ['frame '])
        errs = tail(lp, 3, ['Error', 'error', 'CUDA out of memory', 'MemoryError'])
        res['procs'][m] = {
            'exit': p.returncode, 'ended_s': ended.get(m),
            'state': 'killed_timeout' if m in killed else ('ok' if p.returncode == 0 else 'failed'),
            'last_progress': progress[0] if progress else None,
            'error_lines': errs, 'peak_rss_mb': ram.peak_rss.get(m)}
    return res


def phase_a(args, base):
    outdir = os.path.join(base, 'A_data')
    os.makedirs(outdir, exist_ok=True)
    res = {}
    for mode in MODES:
        cmd = [PY, os.path.join(SCRIPTS, 'capture_a.py'), '--mode', mode, '--outdir', outdir]
        if args.max_frames:
            cmd += ['--max-frames', str(args.max_frames)]
        t0 = time.time()
        log(f'A_data: {mode}')
        code = run_logged(cmd, os.path.join(outdir, f'{mode}.log'), env=env_for(mode))
        r = {'exit': code, 'wall_s': round(time.time() - t0, 1)}
        try:
            with open(os.path.join(outdir, mode, 'metrics.json'), encoding='utf-8') as f:
                m = json.load(f)
            r.update({k: m.get(k) for k in ['status', 'error', 'supervision', 'frames', 'total_s',
                                            'setup_s', 'fps_steady', 'peak_rss_mb', 'gpu_mem_peak_mib']})
        except OSError:
            r['status'] = 'NO_METRICS'
        res[mode] = r
        log(f"A_data: {mode} -> {r.get('status')} {r.get('total_s')}s")
    return res


def phase_validate(base):
    res = {}
    for name in ['C_data', 'C_video', 'C2_video']:
        cdir = os.path.join(base, name)
        if not os.path.exists(os.path.join(cdir, 'objects.parquet')):
            continue
        code = run_logged([PY, os.path.join(SCRIPTS, 'validate.py'), '--a', os.path.join(base, 'A_data'),
                           '--c', cdir], os.path.join(cdir, 'validation.log'))
        try:
            with open(os.path.join(cdir, 'validation.json'), encoding='utf-8') as f:
                v = json.load(f)
            res[name] = {'all_pass': v['all_pass'],
                         'failed': [c['check'] for c in v['checks'] if not c['pass']]}
        except OSError:
            res[name] = {'exit': code}
    return res


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--phases', nargs='+', default=ALL_PHASES, choices=ALL_PHASES)
    p.add_argument('--base', default=os.path.join(ec.ROOT, 'outputs', 'experiment'))
    p.add_argument('--max-frames', type=int, default=None, help='solo para pruebas rápidas')
    p.add_argument('--b-timeout', type=int, default=600)
    p.add_argument('--cool-min', type=int, default=120)
    p.add_argument('--cool-max', type=int, default=600)
    p.add_argument('--cool-temp', type=int, default=65)
    args = p.parse_args()
    os.makedirs(args.base, exist_ok=True)
    log(f'fases: {args.phases}')

    for name in args.phases:
        rec = {'phase': name, 'max_frames': args.max_frames}
        if name != 'validate':
            rec['gpu_before'] = cooldown(args)
        rec['ram_available_start_mb'] = psutil.virtual_memory().available >> 20
        rec['start'] = now()
        t0 = time.time()
        log(f'== {name}')
        gpu_csv = os.path.join(args.base, f'gpu_{name}.csv')
        ram_csv = os.path.join(args.base, f'ram_{name}.csv')
        with ec.GpuLog(gpu_csv):
            if name == 'B':
                rec['result'] = phase_b(args, args.base, ram_csv)
            else:
                ram = RamLog(ram_csv)
                ram.start()
                try:
                    if name == 'C_data':
                        rec['result'] = phase_together(name, ['--no-video'], args, args.base)
                    elif name == 'C_video':
                        rec['result'] = phase_together(name, [], args, args.base)
                    elif name == 'C2_video':
                        rec['result'] = phase_together(name, ['--threads'], args, args.base)
                    elif name == 'A_data':
                        rec['result'] = phase_a(args, args.base)
                    elif name == 'validate':
                        rec['result'] = phase_validate(args.base)
                finally:
                    ram.stop_event.set(); ram.join()
                rec['ram_min_available_mb'] = ram.min_available_mb
        rec['end'] = now()
        rec['wall_s'] = round(time.time() - t0, 1)
        rec['gpu_after'] = ec.gpu_now()
        with open(os.path.join(args.base, 'phases.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        log(f"== {name} listo en {rec['wall_s']}s: {json.dumps(rec.get('result'), ensure_ascii=False)[:600]}")
    log('FIN')


if __name__ == '__main__':
    main()
