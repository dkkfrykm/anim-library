#!/bin/bash
# QA a STAGED dance before promoting: numbers (qa_metrics.py) + video-vs-game sheets (full body + chest) at 8 loop phases.
# Usage (from reiko_breed): bash tools/roto/qa_dance.sh <id>   -> qa/stage/<id>/{full,upper}.jpg + metrics.txt
id=$1; O=qa/stage/$id${QA_TAG:+_$QA_TAG}; mkdir -p $O; P=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/torchvenv/Scripts/python.exe
F=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/ffbin/ffmpeg.exe
V=$(ls /c/Users/mytwo/OneDrive/Desktop/HalfAnEye_HANDOFF/dance_sources/${id}__* | head -1)
QA_CLIP=${QA_CLIP:-} MOCAP_DEVICE=cpu $P tools/roto/qa_metrics.py . $id 2>&1 | grep -v Warn > $O/metrics.txt
read FR TS <<< $($P -I -c "
import json; l=json.load(open('tools/roto/mocap_clips/$id.json'))['log']; lo,hi=l['loop']; fps=l['fps']
fr=[int(lo+(hi-lo)*(i+.5)/8) for i in range(8)]; print(','.join(map(str,fr)), ';'.join('%.2f'%((f-lo)/fps) for f in fr))")
CLIPJSON=${QA_CLIP:-tools/roto/mocap_clips/$id.json} node tools/dancefix_qa.js $id $O s "times=$TS,cams=full;upper,outfit=nude" > $O/render.log 2>&1
i=0; for f in ${FR//,/ }; do $F -y -loglevel error -i "$V" -vf "select=eq(n\,$f),scale=-2:400,crop=min(iw\,300):400" -frames:v 1 $O/v_$i.png; i=$((i+1)); done
T=(${TS//;/ })
for cam in full upper; do args=""; for i in 0 1 2 3 4 5 6 7; do args="$args -i $O/v_$i.png"; done; for i in 0 1 2 3 4 5 6 7; do args="$args -i $O/s_t${T[$i]}_$cam.png"; done
  $F -y -loglevel error $args -filter_complex "$(for i in $(seq 0 7); do echo -n "[$i]scale=225:400:force_original_aspect_ratio=decrease,pad=225:400:(ow-iw)/2:0[a$i];[$((i+8))]crop=405:720:157:0,scale=225:400[b$i];"; done)[a0][a1][a2][a3][a4][a5][a6][a7]hstack=8[A];[b0][b1][b2][b3][b4][b5][b6][b7]hstack=8[B];[A][B]vstack" $O/$cam.jpg; done
cat $O/metrics.txt
