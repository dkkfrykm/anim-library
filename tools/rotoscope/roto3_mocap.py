"""roto_idle_sway redone with the body-model pipeline (reuses mocap_bake.py / mocap_lib.py by import; does not modify them).
  1. NLF SMPL-X per-frame fit of the 60 fps source (scratch venv, streaming runner) -> 30 fps by pairwise rotation averaging
     (quaternion mean per joint, joints3d mean) -> tools/roto/mocap_kp/roto3_idle_sway.npz (own file)
  2. mocap_bake.bake(): ground frame, loop window, retarget, whole-clip torch optimisation (joint limits, arm/hand-vs-skin collision with
     swept sub-frames, ground/foot plants, cyclic smoothness) + finish() (hard limit projection, forearm twist split, metrics)
  3. -> tools/roto/roto_mocap.json['roto_idle_sway'] (roto_bake.py swaps it in) + tools/roto/roto3_mocap_log.json (own log)
Usage: <torch venv python> tools/roto/roto3_mocap.py <reiko_breed dir> <nlf 60fps npz> [--dry]"""
import sys, os, json, time
D = os.path.abspath(sys.argv[1]); SRC = sys.argv[2]; DRY = '--dry' in sys.argv
sys.argv = [sys.argv[0], D]; sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
import mocap_bake as MB
from mocap_lib import rodrigues, m2q, q2m, rot_log

from roto3_lib import decimate

if __name__ == '__main__':
    t0 = time.time(); kp = os.path.join(D, 'tools', 'roto', 'mocap_kp', 'roto3_idle_sway.npz'); m = decimate(SRC, kp); print('fit ->', kp, m, 'frames @30')
    cfg = dict(id='roto3_idle_sway', name='Idle sway', src='3e86b33c', lo=.4)
    try: r = MB.bake(cfg)
    except Exception as e:   # shared RTX: a CUDA OOM can leave the context unusable -> re-run this script on the CPU (float64) in a fresh process
        if MB.DEV.type != 'cuda': raise
        print('GPU failed (%s) -> CPU re-run' % str(e)[:80], flush=True); import subprocess
        env = dict(os.environ, MOCAP_DEVICE='cpu'); sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__), D, SRC] + (['--dry'] if DRY else []), env=env))
    clip, rl = MB.finish(cfg, r); rl['source'] = 'NLF SMPL-X fit of 3e86b33c (60 fps -> 30 fps) + mocap_bake.bake/finish'
    lp = os.path.join(D, 'tools', 'roto', 'roto3_mocap_log.json'); L = json.load(open(lp)) if os.path.exists(lp) else {}; L['roto_idle_sway'] = rl; json.dump(L, open(lp, 'w'), indent=1)
    cp = os.path.join(D, 'tools', 'roto', 'roto3_idle_sway_clip.json'); json.dump(clip, open(cp, 'w'), separators=(',', ':'))   # candidate (compared before it replaces anything)
    print(json.dumps({k: rl[k] for k in ('dur_s', 'loop', 'total_limit_violation_frames', 'feet', 'penetration', 'pelvis_range_deg_estimate', 'pelvis_range_deg_clip')}), round(time.time() - t0), 's')
