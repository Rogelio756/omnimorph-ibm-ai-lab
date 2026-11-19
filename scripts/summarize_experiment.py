"""Resume outputs/experiment/ en tablas Markdown (para REPORTE.md §9).

Uso: python scripts/summarize_experiment.py [--base outputs/experiment]
"""
import argparse
import csv
import json
import os

import numpy as np
import pyarrow.parquet as pq

STAGES = ['decode', 'pitch', 'player', 'ball', 'tracking', 'teams', 'homography', 'draw', 'write']


def gpu_stats(path):
    rows = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for r in csv.reader(f):
            if len(r) >= 8 and r[1].strip().isdigit():
                rows.append(r)
    if not rows:
        return {}
    num = lambda i: np.array([float(r[i].split()[0]) for r in rows])
    temp, sm, power, mem, util = num(1), num(2), num(4), num(5), num(6)
    busy = util >= 50  # solo muestras con la GPU trabajando
    reasons = [int(r[7].strip(), 16) for r in rows]
    # bits de clocks_event_reasons: 0x20 sw thermal, 0x40 hw thermal, 0x4 sw power cap, 0x8 hw slowdown
    thermal = sum(1 for x, b in zip(reasons, busy) if b and x & 0x60)
    powercap = sum(1 for x, b in zip(reasons, busy) if b and x & 0x4)
    return {'samples': len(rows), 'temp_max': int(temp.max()),
            'temp_mean_busy': round(float(temp[busy].mean()), 1) if busy.any() else None,
            'sm_median_busy': int(np.median(sm[busy])) if busy.any() else None,
            'sm_min_busy': int(sm[busy].min()) if busy.any() else None,
            'power_mean_busy': round(float(power[busy].mean()), 1) if busy.any() else None,
            'mem_max_mib': int(mem.max()), 'util_median': int(np.median(util)),
            'busy_pct_thermal': round(100 * thermal / max(busy.sum(), 1), 1),
            'busy_pct_powercap': round(100 * powercap / max(busy.sum(), 1), 1)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), 'outputs', 'experiment'))
    args = p.parse_args()
    base = args.base
    phases = {}
    with open(os.path.join(base, 'phases.jsonl'), encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            phases[r['phase']] = r

    print('## Fases\n')
    print('| Fase | Inicio | Pared (s) | GPU antes (°C) | RAM libre mín (MB) | T máx (°C) | Reloj SM mediana / mín ocupada (MHz) | Potencia media ocupada (W) | Mem GPU máx (MiB) | % muestras ocupadas con freno térmico / potencia |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for name, r in phases.items():
        g = gpu_stats(os.path.join(base, f'gpu_{name}.csv')) if name != 'validate' else {}
        ram = r.get('ram_min_available_mb') or (r.get('result') or {}).get('ram_min_available_mb')
        print(f"| {name} | {r['start'][11:]} | {r['wall_s']} | {(r.get('gpu_before') or {}).get('temp_c', '')} | {ram} | "
              f"{g.get('temp_max', '')} | {g.get('sm_median_busy', '')} / {g.get('sm_min_busy', '')} | "
              f"{g.get('power_mean_busy', '')} | {g.get('mem_max_mib', '')} | "
              f"{g.get('busy_pct_thermal', '')} / {g.get('busy_pct_powercap', '')} |")

    print('\n## C / C2\n')
    print('| Prueba | Estado | Cuadros | Total (s) | Preparación (s) | Bucle (s) | FPS total | FPS bucle | RAM pico (MB) | VRAM pico Δ nvidia-smi (MiB) | torch máx (MB) |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for name in ['C_data', 'C_video', 'C2_video']:
        path = os.path.join(base, name, 'metrics.json')
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            m = json.load(f)
        print(f"| {name} | {m['status']} | {m['frames']} | {m['total_s']} | {m.get('setup_s')} | {m.get('loop_s')} | "
              f"{m['fps_total']} | {m.get('fps_loop')} | {m['peak_rss_mb']} | "
              f"{m['gpu_mem_peak_mib'] - m['gpu_mem_baseline_mib']} | {m.get('torch_max_allocated_mb')} |")
        print(f"|  | preparación: {m.get('setup')} |||||||||| ")

    print('\n## ms por etapa (media / p95)\n')
    names = [n for n in ['C_data', 'C_video', 'C2_video'] if os.path.exists(os.path.join(base, n, 'timings.parquet'))]
    print('| Etapa | ' + ' | '.join(names) + ' |')
    print('|---|' + '---|' * len(names))
    tabs = {n: pq.read_table(os.path.join(base, n, 'timings.parquet')).to_pydict() for n in names}
    for s in STAGES:
        cells = []
        for n in names:
            v = np.array([x for x in tabs[n][f'{s}_ms'] if x is not None])
            cells.append(f'{v.mean():.1f} / {np.percentile(v, 95):.1f}' if len(v) else '—')
        print(f'| {s} | ' + ' | '.join(cells) + ' |')
    # serie temporal: ms de 'ball' y 'player' por bloques de 150 cuadros (efecto térmico)
    print('\n## Media de (pitch+player+ball+teams) ms por bloque de 150 cuadros\n')
    print('| Prueba | ' + ' | '.join(f'{i}-{i + 149}' for i in range(0, 750, 150)) + ' |')
    print('|---|' + '---|' * 5)
    for n in names:
        t = tabs[n]
        gpu = np.array([sum(t[f'{s}_ms'][i] or 0 for s in ['pitch', 'player', 'ball', 'teams'])
                        for i in range(len(t['frame']))])
        print(f'| {n} | ' + ' | '.join(f'{gpu[i:i + 150].mean():.0f}' for i in range(0, len(gpu), 150)) + ' |')

    if 'B' in phases:
        r = phases['B']['result']
        print(f"\n## B (timeout {r['timeout_s']} s, transcurrido {r['elapsed_s']} s, RAM libre mín {r['ram_min_available_mb']} MB)\n")
        print('| Modo | Estado | Terminó a los (s) | Último progreso | RSS pico (MB) | Errores |')
        print('|---|---|---|---|---|---|')
        for m, x in r['procs'].items():
            print(f"| {m} | {x['state']} | {x['ended_s'] or ''} | {x['last_progress'] or 'sin cuadros'} | "
                  f"{x['peak_rss_mb']} | {'; '.join(x['error_lines']) or '—'} |")

    if 'A_data' in phases:
        print('\n## A_data (modos originales, solo datos)\n')
        print('| Modo | Estado | supervision | Cuadros | Total (s) | Preparación (s) | FPS sostenido | RAM pico (MB) |')
        print('|---|---|---|---|---|---|---|---|')
        tot = 0
        for m, x in phases['A_data']['result'].items():
            tot += x.get('total_s') or 0
            print(f"| {m} | {x.get('status')} | {x.get('supervision')} | {x.get('frames')} | {x.get('total_s')} | "
                  f"{x.get('setup_s')} | {x.get('fps_steady')} | {x.get('peak_rss_mb')} |")
        print(f'| **suma** | | | | **{tot:.0f}** | | | |')

    print('\n## Validación\n')
    for n in ['C_data', 'C_video', 'C2_video']:
        path = os.path.join(base, n, 'validation.json')
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as f:
            v = json.load(f)
        print(f"### {n}: {'PASA' if v['all_pass'] else 'NO PASA'}\n")
        print('| Chequeo | Resultado | Extra |')
        print('|---|---|---|')
        for c in v['checks']:
            if 'ratio' in c:
                res = f"{c['ok']}/{c['total']} ({100 * c['ratio']:.2f} %)"
            else:
                res = f"A={c['A']} C={c['C']}"
            extra = {k: x for k, x in c.items() if k not in ('check', 'ok', 'total', 'ratio', 'pass', 'A', 'C')}
            print(f"| {'✔' if c['pass'] else '✘'} {c['check']} | {res} | {extra or ''} |")
        print()


if __name__ == '__main__':
    main()
