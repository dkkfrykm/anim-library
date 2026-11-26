#!/bin/bash
# Staged re-bake of dances, strictly one GPU job at a time, NEVER touching the game file:
# [NLF fit if missing] -> mocap_bake (staged) -> [WiLoR hands if missing] -> finger_apply (staged) -> hinge metric + qa_dance (metrics + sheets).
# Usage (from reiko_breed): bash tools/roto/stage_all.sh dance_1 dance_2 ...   Log: HalfAnEye_HANDOFF/state_notes/stage_all.log
P=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/torchvenv/Scripts/python.exe
SRC=/c/Users/mytwo/OneDrive/Desktop/HalfAnEye_HANDOFF/dance_sources
for id in "$@"; do
  v=$(ls $SRC/${id}__* | head -1)
  if [ ! -f tools/roto/mocap_kp/$id.npz ]; then (cd tools/roto && $P run_nlf_multi.py "$v" mocap_kp/${id}_multi.npz 2>&1 | grep -v -i warn | tail -1 && $P to_single.py mocap_kp/${id}_multi.npz mocap_kp/${id}.npz | tail -1); fi
  MOCAP_DEVICE=cuda $P tools/roto/mocap_bake.py . $id 2>&1 | grep -a "^$id {\|hinge calibration\|Traceback\|Error" | cut -c1-240
  [ -f tools/roto/hands_kp/$id.npz ] || bash tools/roto/finger_capture_all.sh $id | grep "^wrote\|Error"
  MOCAP_DEVICE=cpu $P tools/roto/finger_apply.py . $id 2>&1 | grep "applied\|Error"
  $P -I tools/roto/hinge_metric.py tools/roto/mocap_clips/$id.json $id
  bash tools/roto/qa_dance.sh $id 2>&1 | grep "FAIL\|OVERALL"
  echo "== $id staged $(date +%H:%M)"
done
