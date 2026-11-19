"""Piezas compartidas del experimento A/B/C/C2 (ver REPORTE.md §9).

- Rutas y variables de entorno (HF_HOME, YOLO_CONFIG_DIR dentro del proyecto).
- SeededTeamClassifier: TeamClassifier con semillas fijas en UMAP y KMeans.
- GpuLog: nvidia-smi cada 1 s a CSV (temperatura, relojes, potencia, memoria).
- write_parquet: escribe un dict de columnas con pyarrow.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOCCER_DIR = os.path.join(ROOT, 'sports', 'examples', 'soccer')
DEFAULT_VIDEO = os.path.join(SOCCER_DIR, 'data', '2e57b9_0.mp4')
SV023_DIR = os.path.join(ROOT, '.sv023')  # supervision 0.23.0 aislado, solo para BALL original
SEED = 42

os.environ.setdefault('HF_HOME', os.path.join(ROOT, '.hf_cache'))
os.environ.setdefault('YOLO_CONFIG_DIR', os.path.join(ROOT, '.ultralytics'))
# TeamClassifier abre una barra tqdm por cuadro; se apaga en todas las pruebas por igual
os.environ.setdefault('TQDM_DISABLE', '1')
if SOCCER_DIR not in sys.path:
    sys.path.insert(0, SOCCER_DIR)

GPU_FIELDS = ('timestamp,temperature.gpu,clocks.sm,clocks.mem,power.draw,'
              'memory.used,utilization.gpu,clocks_event_reasons.active')


def make_seeded_team_classifier(seed: int = SEED):
    """Devuelve una subclase de TeamClassifier con UMAP y KMeans sembrados.

    Mismo modelo y mismos hiperparámetros que el original; solo agrega random_state.
    UMAP con random_state corre en un solo hilo (más lento, pero determinista).
    """
    import umap
    from sklearn.cluster import KMeans
    from sports.common.team import TeamClassifier

    class SeededTeamClassifier(TeamClassifier):
        def __init__(self, device: str = 'cpu', batch_size: int = 32):
            super().__init__(device=device, batch_size=batch_size)
            self.reducer = umap.UMAP(n_components=3, random_state=seed)
            self.cluster_model = KMeans(n_clusters=2, random_state=seed)

    return SeededTeamClassifier


def seed_everything(seed: int = SEED) -> None:
    import random
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class GpuLog:
    """nvidia-smi en segundo plano, una muestra por segundo, a un CSV."""

    def __init__(self, path: str):
        self.path = path
        self.proc = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.proc = subprocess.Popen(
            ['nvidia-smi', f'--query-gpu={GPU_FIELDS}', '--format=csv',
             '-lms', '1000', '-f', self.path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return self

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=10)


def gpu_now() -> dict:
    """Una lectura puntual de nvidia-smi (temperatura, reloj, potencia, memoria)."""
    out = subprocess.run(
        ['nvidia-smi', '--query-gpu=temperature.gpu,clocks.sm,power.draw,memory.used',
         '--format=csv,noheader,nounits'],
        capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
    temp, clock, power, mem = [x.strip() for x in out.split(',')]
    return {'temp_c': int(temp), 'sm_mhz': int(clock),
            'power_w': float(power), 'mem_used_mib': int(mem)}


def write_parquet(columns: dict, path: str) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pq.write_table(pa.table(columns), path, compression='zstd')
