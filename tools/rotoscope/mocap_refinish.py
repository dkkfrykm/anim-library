"""Re-run finish() (limit projection, forearm twist split, encode, metrics) on a saved raw solve (tools/roto/mocap_raw/<id>.pkl) without re-baking.
Writes tools/roto/mocap_clips/<id>.json (and, with --game, merges into web/assets/anims/dance3d.js).  Usage: <torch venv> python tools/roto/mocap_refinish.py <dir> <id> [--game]"""
import sys, os, pickle, json
D = os.path.abspath(sys.argv[1]); ID = sys.argv[2]; GAME = '--game' in sys.argv; sys.argv = [sys.argv[0], D]
sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import mocap_bake as B
r = pickle.load(open(os.path.join(D, 'tools', 'roto', 'mocap_raw', ID + '.pkl'), 'rb'))
class _Sk: pass
sk = _Sk(); sk.T = B.t_(r.pop('skT')); sk.ws = B.t_(r.pop('skws')); r['sk'] = sk
cfg = next(c for c in B.DANCES + B.ROTO_SOLO if c['id'] == ID)
B.anat_limits(r['WT'])   # limit frames are per clip (rest-local elbows/knees)
clip, rl = B.finish(cfg, r)
json.dump({'clip': clip, 'log': rl}, open(os.path.join(D, 'tools', 'roto', B.CLIP_DIR, ID + '.json'), 'w'), separators=(',', ':'))
print(ID, 'refinished; limit_projected_frames', rl.get('limit_projected_frames'), 'feet', json.dumps(rl['feet']))
if GAME: print('--game ignored: the game file is written only by tools/anim/promote.py after QA')
