"""Monitor en vivo del experimento (solo lee archivos; no afecta la corrida).

Uso (otra terminal, desde omnimorph-pruebas):
  .venv\\Scripts\\python.exe scripts\\monitor.py
  .venv\\Scripts\\python.exe scripts\\monitor.py --base <carpeta> --total 20
Ctrl+C para salir.
"""
import argparse
import json
import os
import re
import sys
import time

import psutil

import exp_common as ec

PHASES = ['C_data', 'C_video', 'C2_video', 'B', 'A_data', 'validate']
MODES = ['PITCH_DETECTION', 'PLAYER_DETECTION', 'BALL_DETECTION',
         'PLAYER_TRACKING', 'TEAM_CLASSIFICATION', 'RADAR']
G, Y, R, C, D, B0, X = '\033[32m', '\033[33m', '\033[31m', '\033[36m', '\033[2m', '\033[1m', '\033[0m'
FRAME_RE = re.compile(r'frame (\d+)')


def read_lines(path):
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read().splitlines()
    except OSError:
        return []


def last_frame(path):
    for line in reversed(read_lines(path)):
        m = FRAME_RE.search(line)
        if m:
            return int(m.group(1))
    return None


def has_error(path):
    return any(('Traceback' in l or 'out of memory' in l) for l in read_lines(path))


def bar(n, total, width=28):
    if n is None:
        return f'{D}[{"·" * width}] preparando (modelos / ajuste de equipos){X}'
    frac = min(n / total, 1.0)
    full = int(frac * width)
    return f'[{G}{"█" * full}{X}{"░" * (width - full)}] {n:>4}/{total} ({100 * frac:4.1f} %)'


def eta(path, n, total):
    """Estima tiempo restante con la velocidad desde la primera línea 'frame'."""
    if not n:
        return ''
    try:
        age = time.time() - os.path.getmtime(path)
        lines = [l for l in read_lines(path) if FRAME_RE.search(l)]
        if len(lines) < 2:
            return ''
        # run_mode imprime t=..s; los otros scripts no: usar mtime del log como aproximación
        m = re.search(r't=([\d.]+)s', lines[-1])
        m0 = re.search(r't=([\d.]+)s', lines[0])
        if m and m0:
            n0 = int(FRAME_RE.search(lines[0]).group(1))
            fps = (n - n0) / max(float(m.group(1)) - float(m0.group(1)), 1e-6)
            return f'  ~{fps:.2f} FPS, faltan ~{(total - n) / fps / 60:.0f} min'
    except Exception:
        pass
    return ''


def gpu_line():
    try:
        g = ec.gpu_now()
        t = g['temp_c']
        col = G if t < 75 else (Y if t < 85 else R)
        return (f"GPU  {col}{t} °C{X}  reloj {g['sm_mhz']} MHz  {g['power_w']:.0f} W  "
                f"memoria {g['mem_used_mib']}/6144 MiB")
    except Exception as e:
        return f'GPU  {R}sin lectura ({e}){X}'


def ram_line():
    vm = psutil.virtual_memory()
    av = vm.available >> 20
    col = G if av > 4000 else (Y if av > 2000 else R)
    return f'RAM  libre {col}{av / 1024:.1f} GB{X} de {vm.total / 2**30:.1f} GB ({vm.percent:.0f} % usado)'


def render(base, total):
    done = {}
    for line in read_lines(os.path.join(base, 'phases.jsonl')):
        try:
            r = json.loads(line)
            done[r['phase']] = r
        except json.JSONDecodeError:
            pass
    orch = read_lines(os.path.join(base, 'orchestrator.log'))
    current = None
    cooling = False
    for line in orch:
        m = re.search(r'== (\w+)$', line)
        if m:
            current = m.group(1)
        cooling = 'enfriando' in line and current is not None
    if current in done:
        current = None
    finished = any(l.endswith('FIN') for l in orch)

    out = [f'{B0}Experimento omnimorph — los 6 modos{X}   {D}{time.strftime("%H:%M:%S")}  (Ctrl+C para salir){X}',
           '', gpu_line(), ram_line(), '']
    for ph in PHASES:
        if ph in done:
            r = done[ph]
            res = r.get('result') or {}
            status = res.get('status') if isinstance(res, dict) else None
            if ph == 'B':
                info = f"{len(res.get('killed', []))} detenidos por timeout, {res.get('elapsed_s')} s"
            elif ph == 'A_data':
                ok = sum(1 for v in res.values() if v.get('status') == 'OK')
                info = f'{ok}/6 modos OK'
            elif ph == 'validate':
                info = ', '.join(f"{k}: {'PASA' if v.get('all_pass') else 'NO PASA'}" for k, v in res.items())
            else:
                info = (f"{status}  {res.get('frames')} cuadros  {res.get('total_s')} s  "
                        f"bucle {res.get('fps_loop')} FPS")
            col = G if (status in (None, 'OK')) else R
            out.append(f'{col}✔ {ph:<9}{X} {info}   {D}({r["wall_s"]:.0f} s){X}')
        elif ph == current:
            out.append(f'{C}▶ {ph:<9}{X} ' + (f'{Y}enfriando GPU…{X}' if cooling else 'corriendo'))
            if ph in ('C_data', 'C_video', 'C2_video'):
                lp = os.path.join(base, ph, 'run.log')
                n = last_frame(lp)
                out.append(f'    {bar(n, total)}' + (f'  {R}ERROR (ver run.log){X}' if has_error(lp) else ''))
            elif ph == 'B':
                for m in MODES:
                    lp = os.path.join(base, 'B', f'{m}.log')
                    n = last_frame(lp)
                    err = f'  {R}ERROR{X}' if has_error(lp) else ''
                    out.append(f'    {m:<20} {bar(n, total, 20)}{eta(lp, n, total)}{err}')
            elif ph == 'A_data':
                for m in MODES:
                    lp = os.path.join(base, 'A_data', f'{m}.log')
                    if os.path.exists(os.path.join(base, 'A_data', m, 'metrics.json')):
                        out.append(f'    {G}✔{X} {m}')
                    elif os.path.exists(lp):
                        out.append(f'    {C}▶{X} {m:<20} {bar(last_frame(lp), total, 20)}')
                    else:
                        out.append(f'    {D}· {m}{X}')
        else:
            out.append(f'{D}· {ph:<9} pendiente{X}')
    out.append('')
    if finished:
        out.append(f'{G}{B0}Experimento terminado.{X}')
    elif not orch:
        out.append(f'{Y}Aún no hay orchestrator.log en {base}{X}')
    else:
        out.append(f'{D}Última línea: {orch[-1][:110]}{X}')
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', default=os.path.join(ec.ROOT, 'outputs', 'experiment'))
    p.add_argument('--total', type=int, default=750, help='cuadros del video')
    p.add_argument('--every', type=float, default=2.0)
    args = p.parse_args()
    os.system('')  # activa colores ANSI en la consola de Windows
    try:
        while True:
            screen = render(args.base, args.total)
            sys.stdout.write('\033[H\033[2J' + screen + '\n')
            sys.stdout.flush()
            time.sleep(args.every)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
