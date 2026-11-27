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
def seam():
    """loop seam: largest per-frame rotation step of any bone within 3 frames of the wrap, minus that bone's own interior p99 step
    (a natural fast move is not a pop). dance_2 had a 134 deg thigh pop here that the p99 jitter checks could not see."""
    worst, wb = 0.0, ''
    for k, v in clip['q'].items():
        q = np.array(v, float).reshape(-1, 4) / 1e4
        if len(q) < 12: continue
        q /= np.linalg.norm(q, axis=1, keepdims=True); st = np.degrees(2 * np.arccos(np.clip(np.abs((q * np.roll(q, -1, 0)).sum(1)), 0, 1)))
        near = np.r_[st[-3:], st[:3]]; ex = float(near.max() - np.percentile(st[3:-3], 99))
        if ex > worst: worst, wb = ex, k
    return worst, wb
sw, sb = seam(); chk('loop seam pop deg (%s)' % sb.split('[')[-1].rstrip(']'), sw, 15)
if l['ground']['feet_tracked']:
    chk('foot skate mean cm', max(l['feet']['L']['skate_cm_mean'], l['feet']['R']['skate_cm_mean']), .5, '%.2f')
# hand gate (Animator): mean over fingers 1-4 of PIP + DIP angle vs her BIND hand (deg); old RELAX claw 20, authored kiss 7, bind 0.
# FAIL if a hanging hand (forearm pointing down) stays > 12 for > 0.5 s.
import roto_bake as RB_
from mocap_lib import nrm as nrm_
SFq = np.asarray(RB_.SF['q'], float); n = clip['n']; fps = clip['fps']; Qa = np.repeat(SFq[None], n, 0)
for b, v in clip['q'].items():
    if b in RB_.SF['i']: a_ = np.array(v, float).reshape(-1, 4) / 1e4; Qa[:, RB_.SF['i'][b]] = a_[np.arange(n) % len(a_)]
Pa = RB_.Pose(RB_.SF, Qa, np.repeat(np.asarray(RB_.SF['t'], float)[None], n, 0))
BINDH = json.load(open(os.path.join(D, 'tools', 'roto', 'hand_pose_hang.json')))['q']   # her bind hand (Animator: the separating reference)
def bind_ang(b):
    i = RB_.SF['i'][b]; q = Qa[:, i]; r = np.array(BINDH[b], float) / 1e4; r /= np.linalg.norm(r); return np.degrees(2 * np.arccos(np.clip(np.abs((q * r).sum(1)), 0, 1)))
def rest_ang(b):
    i = RB_.SF['i'][b]; q = Qa[:, i]; r = SFq[i]; return np.degrees(2 * np.arccos(np.clip(np.abs((q * r).sum(1)), 0, 1)))
for s_ in 'LR':
    claw = np.mean([bind_ang('NPC %s Finger%d1 [%sF%d1]' % (s_, f, s_, f)) + bind_ang('NPC %s Finger%d2 [%sF%d2]' % (s_, f, s_, f)) for f in range(1, 5)], 0)   # PIP+DIP vs her BIND hand
    dz = nrm_(Pa.p('NPC %s Hand [%sHnd]' % (s_, s_)) - Pa.p('NPC %s Forearm [%sLar]' % (s_, s_)))[:, 2]; bad = (claw > 12) & (dz < -.6)
    run = 0; mx = 0
    for b_ in np.concatenate([bad, bad]): run = run + 1 if b_ else 0; mx = max(mx, run)
    print('  %s hand claw p50 %.0f p95 %.0f (hanging frames %d)' % (s_, np.percentile(claw, 50), np.percentile(claw, 95), int((dz < -.6).sum())))
    chk('%s hand claw while hanging, longest run s' % s_, min(mx, n) / fps, .5, '%.2f')
print('OVERALL', 'PASS' if all(res) else 'FAIL (%d)' % res.count(False))
