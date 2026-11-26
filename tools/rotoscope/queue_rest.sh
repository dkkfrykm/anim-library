#!/bin/bash
# after the running new_dance.sh (10-13): dances 14-16, then re-bake 7/10/11 (root smoothing), music for all, rebuild. One GPU job at a time.
L=/c/Users/mytwo/OneDrive/Desktop/HalfAnEye_HANDOFF/state_notes
P=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/torchvenv/Scripts/python.exe
until grep -aq "dance_13 pipeline done" $L/new_dances.log; do sleep 30; done
bash tools/roto/new_dance.sh dance_14 dance_15 dance_16 > $L/new_dances2.log 2>&1
for id in dance_7 dance_10 dance_11; do
  MOCAP_DEVICE=cuda $P tools/roto/mocap_bake.py . $id 2>&1 | grep -a "^$id {\|Traceback" | cut -c1-160
  MOCAP_DEVICE=cpu $P tools/roto/finger_apply.py . $id --game 2>&1 | grep applied
done > $L/rebake_root.log 2>&1
$P tools/roto/dance_audio.py . >> $L/rebake_root.log 2>&1
python -I build3d.py . >> $L/rebake_root.log 2>&1
echo "== ALL DONE $(date +%H:%M)" >> $L/rebake_root.log
