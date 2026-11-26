#!/bin/bash
# WiLoR hand capture for every dance, one at a time (run from reiko_breed). Source videos: HalfAnEye_HANDOFF/dance_sources/<id>__*.mov
PY=/c/Users/mytwo/rbsrc/venvs/handvenv/Scripts/python.exe; SRC=/c/Users/mytwo/OneDrive/Desktop/HalfAnEye_HANDOFF/dance_sources
for id in "$@"; do
  v=$(ls $SRC/${id}__* 2>/dev/null | head -1); [ -z "$v" ] && { echo "== $id: no video"; continue; }
  TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 HAND_DEVICE=cuda $PY tools/roto/finger_capture.py . $id "$v" 2>&1 | grep -v -i warn
  echo "== $id hands done $(date +%H:%M)"
done
