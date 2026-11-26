#!/bin/bash
# Bake dance clips one process per clip: CUDA first, CPU (float64) fallback in a fresh process if the GPU run fails.
# Usage: bash tools/roto/mocap_run.sh <python-with-torch> id1 id2 ...   (run from the reiko_breed dir)
PY=$1; shift
for id in "$@"; do
  MOCAP_DEVICE=cuda "$PY" tools/roto/mocap_bake.py . $id || { echo "== $id: CUDA run failed -> CPU"; MOCAP_DEVICE=cpu "$PY" tools/roto/mocap_bake.py . $id; }
  echo "== $id done $(date +%H:%M)"
done
