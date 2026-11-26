"""Promote a QA-passed FINAL (tools/anim/final/<id>.json) into the game file web/assets/anims/dance3d.js (keeps all other clips).
Gate (all required): qa/stage/<id>/verdict.json has pass == true, user_ok == true, and final_hash == file hash of the CURRENT
tools/anim/final/<id>.json (final_file_hash(): sha1 of the file bytes, first 16 hex). Any edit of the FINAL after the verdict blocks it.
Usage: <python> tools/anim/promote.py <dir> <id>      |   <python> tools/anim/promote.py <dir> <id> --hash   (print the FINAL's hash only)"""
import sys, os, json, hashlib
D = os.path.abspath(sys.argv[1]); ID = sys.argv[2]; HASH_ONLY = '--hash' in sys.argv
FIN = os.path.join(D, 'tools', 'anim', 'final', ID + '.json')

def final_file_hash(path=FIN):
    return hashlib.sha1(open(path, 'rb').read()).hexdigest()[:16]

if HASH_ONLY: print(final_file_hash()); sys.exit(0)
if not os.path.exists(FIN): sys.exit('%s: no FINAL at %s - not promoted' % (ID, FIN))
VP = os.path.join(D, 'qa', 'stage', ID, 'verdict.json')
if not os.path.exists(VP): sys.exit('%s: no verdict at %s - not promoted' % (ID, VP))
V = json.load(open(VP)); h = final_file_hash()
if V.get('final_hash') != h: sys.exit('%s: verdict is for FINAL %s, current FINAL is %s - not promoted' % (ID, V.get('final_hash'), h))
if V.get('pass') is not True: sys.exit('%s: verdict pass=%s - not promoted' % (ID, V.get('pass')))
if V.get('user_ok') is not True: sys.exit('%s: user has not OK\'d the sheets (verdict user_ok=%s) - not promoted' % (ID, V.get('user_ok')))
sys.argv = [sys.argv[0], D]; sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import mocap_bake as MB
F = json.load(open(FIN)); MB.LOG[ID] = F['log']; MB.write({ID: F['clip']}, {x['id']: x['name'] for x in MB.DANCES}); print(ID, 'promoted', h)
