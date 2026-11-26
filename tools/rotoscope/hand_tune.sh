#!/bin/bash
# bash tools/roto/hand_tune.sh <label> "<15 curls>;<5 spreads>"  -> qa/handtune/<label>.jpg: both hands, 3 views, dance_7 staged copy (game untouched)
lab=$1; pose=$2; P=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/torchvenv/Scripts/python.exe
F=/c/Users/mytwo/AppData/Local/Temp/claude/532a5d2f69a76e11/95d684a3-cf60-44a6-a967-cafb84428bc5/scratchpad/ffbin/ffmpeg.exe; O=qa/handtune; mkdir -p $O
cp tools/roto/mocap_clips/dance_7.json $O/_keep.json
FINGER_POSE="$pose" MOCAP_DEVICE=cpu $P tools/roto/finger_apply.py . dance_7 > /dev/null 2>&1; cp tools/roto/mocap_clips/dance_7.json $O/$lab.clip.json; cp $O/_keep.json tools/roto/mocap_clips/dance_7.json
for y in 0 1.6 3.14; do CLIPJSON=$O/$lab.clip.json node tools/dancefix_qa.js dance_7 $O ${lab}_y$y "times=4.7,cams=handL;handR,yaw=$y,outfit=nude" > /dev/null 2>&1; done
$F -y -loglevel error -i $O/${lab}_y0_t4.70_handL.png -i $O/${lab}_y1.6_t4.70_handL.png -i $O/${lab}_y3.14_t4.70_handL.png -i $O/${lab}_y0_t4.70_handR.png -i $O/${lab}_y1.6_t4.70_handR.png -i $O/${lab}_y3.14_t4.70_handR.png -filter_complex "[0][1][2]hstack=3[a];[3][4][5]hstack=3[b];[a][b]vstack,scale=1200:-1" $O/$lab.jpg && echo $O/$lab.jpg
