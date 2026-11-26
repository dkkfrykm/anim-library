#!/bin/bash
# HKX pack -> decoded (XPMSSE female HDT skeleton) -> game-format clips in qa/packs/<name>/clips/ ; CPU only. Usage: bash tools/pack_convert.sh <name> <hkx_root_or_decoded_dir> [decoded]
name=$1; src=$2; mode=$3; PY=python; [ -x /c/Python315/python.exe ] && PY=/c/Python315/python.exe
SK="/c/Users/mytwo/soulbound/skyrim/src/XP32 Maximum Skeleton Special Extended/Skeleton Rig/HDT/meshes/actors/character/character assets female/skeleton_female.hkx"
DEC=/c/Users/mytwo/rbsrc/packs_decoded/$name
if [ "$mode" != decoded ]; then (cd /c/Users/mytwo/animlib/skyrim_mco && SKYRIM_SKELETON="$SK" $PY -I tools/export_decoded.py "$src" --out $DEC 2>&1 | tail -1); else DEC=$src; fi
python -I tools/pack_to_clips.py $DEC qa/packs/$name/clips "$name" | tail -2
echo "== $name converted $(date +%H:%M)"
