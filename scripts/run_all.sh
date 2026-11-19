#!/bin/bash
# Corre los 6 modos de examples/soccer/main.py sobre el mismo video, en GPU.
# Uso (Git Bash, desde omnimorph-pruebas):  bash scripts/run_all.sh [cuda|cpu]
set -u
cd "$(dirname "$0")/.."
DEVICE="${1:-cuda}"
VIDEO="sports/examples/soccer/data/2e57b9_0.mp4"
export HF_HOME="$PWD/.hf_cache"            # SigLIP se descarga aquí, no en el perfil del usuario
export YOLO_CONFIG_DIR="$PWD/.ultralytics" # settings de ultralytics dentro del proyecto
mkdir -p outputs logs
for MODE in PITCH_DETECTION PLAYER_DETECTION BALL_DETECTION PLAYER_TRACKING TEAM_CLASSIFICATION RADAR; do
  echo "=== $MODE ($(date +%T))"
  .venv/Scripts/python.exe scripts/run_mode.py --mode "$MODE" --source "$VIDEO" \
    --target "outputs/$MODE.mp4" --device "$DEVICE" > "logs/$MODE.log" 2>&1
  echo "exit=$? $(grep -E '"status"|"fps_steady"|"error"' "logs/$MODE.log" | tr -d '\n')"
done
echo "=== DONE"
