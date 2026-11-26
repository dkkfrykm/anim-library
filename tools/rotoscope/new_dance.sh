#!/bin/bash
# Full pipeline for new dance ids, strictly one GPU job at a time (run from reiko_breed):
# NLF body fit -> mocap bake -> WiLoR hands -> finger layer. Source: HalfAnEye_HANDOFF/dance_sources/<id>__*.mov; DANCES entry must exist in mocap_bake.py.
P=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/torchvenv/Scripts/python.exe
SRC=/c/Users/mytwo/OneDrive/Desktop/HalfAnEye_HANDOFF/dance_sources
for id in "$@"; do
  v=$(ls $SRC/${id}__* | head -1)
  (cd tools/roto && $P run_nlf_multi.py "$v" mocap_kp/${id}_multi.npz 2>&1 | grep -v -i warn | tail -1 && $P to_single.py mocap_kp/${id}_multi.npz mocap_kp/${id}.npz | tail -1)
  MOCAP_DEVICE=cuda $P tools/roto/mocap_bake.py . $id 2>&1 | grep -a "^$id {\|^wrote\|Traceback\|Error" | cut -c1-200
  bash tools/roto/finger_capture_all.sh $id | grep "^wrote\|Error"
  MOCAP_DEVICE=cpu $P tools/roto/finger_apply.py . $id --game 2>&1 | grep "applied\|Error"
  echo "== $id pipeline done $(date +%H:%M)"
done
