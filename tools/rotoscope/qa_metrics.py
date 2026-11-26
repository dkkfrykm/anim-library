"""Numeric QA of a staged dance (tools/roto/mocap_clips/<id>.json + mocap_raw/<id>.pkl): body follows the video (chest/head/pelvis world
rotation error vs the retarget targets), no lean the video doesn't have, penetration, limits, jitter, feet. Prints PASS/FAIL per check."""
import sys, os, json, pickle
D = os.path.abspath(sys.argv[1]); ID = sys.argv[2]; sys.argv = [sys.argv[0], D]; sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
import mocap_bake as B
C = json.load(open(os.environ.get('QA_CLIP') or os.path.join(D, 'tools', 'roto', 'mocap_clips', ID + '.json'))); l = C['log']; clip = C['clip']   # QA_CLIP = a FINAL (Blender-stage) clip; body/limit metrics still from the BASE solve
r = pickle.load(open(os.path.join(D, 'tools', 'roto', 'mocap_raw', ID + '.pkl'), 'rb')); W = r['W']; idx = r['idx']; Wt = r['Wt']
def err(k): return np.degrees(np.arccos(np.clip((np.trace(np.einsum('nji,njk->nik', Wt[k], W[:, idx[k]]), axis1=1, axis2=2) - 1) / 2, -1, 1)))
res = []
def chk(name, val, lim, fmt='%.1f'): ok = val <= lim; res.append(ok); print(('PASS ' if ok else 'FAIL ') + name + ' = ' + (fmt % val) + ' (limit ' + str(lim) + ')')
for k, lim in (('COM', 15), ('SP1', 15), ('SP2', 15), ('NECK', 20), ('HEAD', 20)): chk('%s err vs video p95 deg' % k, float(np.percentile(err(k), 95)), lim)
pe, pc = l['pelvis_range_deg_estimate'], l['pelvis_range_deg_clip']
for a in ('yaw', 'tilt', 'roll'): chk('pelvis %s range excess deg' % a, pc[a] - pe[a], 8)
pen = max([v['max_mm'] for v in l['penetration'].values()] or [0]); chk('max penetration mm', pen, 10)
chk('limit violation frames', l['total_limit_violation_frames'], 0, '%d')
def jit(b):
    k = [x for x in clip['q'] if '[' + b in x][0]; q = np.array(clip['q'][k], float).reshape(-1, 4) / 1e4
    if len(q) < 4: return 0
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    for i in range(1, len(q)):
        if q[i] @ q[i - 1] < 0: q[i] = -q[i]
    return float(np.percentile(np.degrees(2 * np.linalg.norm(q[2:] - 2 * q[1:-1] + q[:-2], axis=1)), 99))
for b, lim in (('COM ', 6), ('Spn1', 6), ('Head', 6), ('LClf', 8), ('RClf', 8), ('LHnd', 14), ('RHnd', 14)): chk('jitter %s p99' % b.strip(), jit(b), lim)
if l['ground']['feet_tracked']:
    chk('foot skate mean cm', max(l['feet']['L']['skate_cm_mean'], l['feet']['R']['skate_cm_mean']), .5, '%.2f')
print('OVERALL', 'PASS' if all(res) else 'FAIL (%d)' % res.count(False))
