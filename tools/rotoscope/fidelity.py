"""Fidelity audit of the mocap bake pre-stages (no optimisation): what the rotation pre-smoothing removes and how often the
reference itself exceeds the joint limits. Usage: <torch venv> python tools/roto/fidelity.py <reiko_breed dir> <id>"""
import sys, os, json
D = os.path.abspath(sys.argv[1]); ID = sys.argv[2]; sys.argv = [sys.argv[0], D]
sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
import mocap_bake as B
from mocap_lib import SMPL_OF, rot_log, m2q, q2m, rodrigues
def ang(Ra, Rb): return np.degrees(np.linalg.norm(rot_log(np.swapaxes(Ra, -1, -2) @ Rb), axis=-1))
cfg = next(c for c in B.DANCES + B.ROTO_SOLO if c['id'] == ID)
F = B.load_fit(ID); fps = F['fps']; Jg, Gg, gi = B.ground_frame(F)
Bn = int(round(fps * .5)); i, j = B.loop_window(Jg, Gg, fps, cfg.get('lo', .6), Bn); Jc, Gc = B.crop_blend(Jg, Gg, i, j, Bn)
Gs = np.stack([B.smooth_rot(Gc[:, k], int(fps * .23)) for k in range(22)], 1)
off = B.M.smpl_rest_offsets(F['G'], F['J']); PT, WTq = B.M.build_tpose(B.R, B.SF, off, B.M.hand_rest_offsets(F['G'], F['J55']))
out = {'smoothing_removed_deg': {}, 'raw_framediff_deg': {}, 'limit_exceed': {}}
for k in B.OPT:
    s = SMPL_OF[k]; a = ang(Gc[:, s], Gs[:, s]); fd = ang(Gc[1:, s], Gc[:-1, s])
    out['smoothing_removed_deg'][k] = [round(float(np.percentile(a, 50)), 1), round(float(np.percentile(a, 95)), 1), round(float(a.max()), 1)]
    out['raw_framediff_deg'][k] = [round(float(np.percentile(fd, 50)), 1), round(float(np.percentile(fd, 95)), 1)]
for tag, G_ in (('raw', Gc), ('smoothed', Gs)):
    Wt = B.world_targets(G_, WTq); res = {}
    for k in ['SP0', 'SP1', 'SP2', 'NECK', 'HEAD'] + [s + q for s in 'LR' for q in ('CLV', 'UA', 'FA', 'HD', 'TH', 'CF', 'FT')]:
        d, a1, a2, r1, r2, rt = B.LIMITS[k]; WTb = q2m(WTq[k]); WTp = q2m(WTq[B.APAR[k]])
        Rp = Wt[B.APAR[k]] @ WTp.T; Rr = np.swapaxes(Rp, -1, -2) @ (Wt[k] @ WTb.T); q = m2q(Rr)
        tw = 2 * np.arctan2(q[:, :3] @ d, q[:, 3]); tw = (tw + np.pi) % (2 * np.pi) - np.pi
        sv = rot_log(Rr @ rodrigues(-d[None] * tw[:, None])); c = [np.degrees(sv @ a1), np.degrees(sv @ a2), np.degrees(tw)]
        ex = np.max([np.maximum(0, lo - x) + np.maximum(0, x - hi) for x, (lo, hi) in zip(c, (r1, r2, rt))], 0)
        if (ex > 1).any(): res[k] = {'frames': int((ex > 1).sum()), 'max_over_deg': round(float(ex.max()), 1), 'which': [n for n, x, (lo, hi) in zip(('swing1', 'swing2', 'twist'), c, (r1, r2, rt)) if ((x < lo - 1) | (x > hi + 1)).any()]}
    out['limit_exceed'][tag] = res
out['frames'] = len(Gc); out['fps'] = fps
print(json.dumps(out, indent=None).replace('], "', '],\n "'))
