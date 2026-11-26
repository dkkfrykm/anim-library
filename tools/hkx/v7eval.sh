#!/bin/sh
# V7 iteration loop: build powers into out/v7tmp, merge over out/phase6, run kinks + simil (M1 and all slots).
# Usage: sh tools/v7eval.sh pid,pid,...
cd "$(dirname "$0")/.."
B="/c/Program Files (x86)/Steam/steamapps/common/Blender/blender.exe"
rm -rf out/v7tmp/*.json out/v7tmp/*.lua out/v7tmp/merged
"$B" --background --python tools/phase6.py -- --powers "$1" --out out/v7tmp > out/v7tmp/build.log 2>&1
grep -a "SUMMARY\|Traceback\|  FLAG" out/v7tmp/build.log
python -I tools/merge_rows.py out/phase6 out/v7tmp > /dev/null
cp out/phase6/Clips_Sky*.lua out/v7tmp/merged/; cp out/v7tmp/Clips_Sky*.lua out/v7tmp/merged/
python -I tools/kinks.py out/v7tmp/merged | tail -2
cd out/v7tmp/merged
python ../../../tools/simil.py rows.json simil_m1.json --slots M1_1,M1_2,M1_3,M1_4 > /dev/null
python ../../../tools/simil.py rows.json simil_all_slots.json > /dev/null
python -I -c "
import json
for f in ['simil_m1.json','simil_all_slots.json']:
  r=json.load(open(f));thr=r['dist']['boxer|karate'];low=sorted((round(v),k) for k,v in r['dist'].items() if v is not None and v<thr);print(f,'thr',round(thr),'low',low,'minguard',round(min(r['guard'].values())))"
