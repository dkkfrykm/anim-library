"""Animator's elbow/knee metric (same as animlib ingest_review): q_rel = rest^-1 * clip_local, swing-twist about local X (hinge);
off-rotation vector: Y = side-bend, Z = twist about the bone. Usage: python tools/roto/hinge_metric.py <clip.json or dance3d.js> <id>"""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as Rr
S = json.load(open('tools/anim/skeleton_xpmsse.json'))
def clip_of(path, cid):
    s = open(path, encoding='utf-8').read()
    if path.endswith('.js'): k = s.index('window.RB_DANCE3D=') + 18; return json.JSONDecoder().raw_decode(s[k:])[0]['clips'][cid]
    return json.loads(s)['clip']
def metric(c, b):
    rq = np.array(S['q'][S['names'].index(b)]); q = np.array(c['q'][b], float).reshape(-1, 4) / 1e4
    r = (Rr.from_quat(rq).inv() * Rr.from_quat(q)).as_quat(); th = 2 * np.arctan2(r[:, 0], r[:, 3])
    off = (Rr.from_rotvec(np.c_[th, 0 * th, 0 * th]).inv() * Rr.from_quat(r)).as_rotvec(); return np.degrees(np.abs(off[:, 1])), np.degrees(np.abs(off[:, 2])), np.degrees(th)
if __name__ == '__main__':
    c = clip_of(sys.argv[1], sys.argv[2])
    for b in ('NPC L Forearm [LLar]', 'NPC R Forearm [RLar]', 'NPC L Calf [LClf]', 'NPC R Calf [RClf]'):
        sb, tw, fl = metric(c, b); print('%-22s side p95 %5.1f max %5.1f | twist p95 %5.1f | flex %+.0f..%+.0f' % (b, np.percentile(sb, 95), sb.max(), np.percentile(tw, 95), fl.min(), fl.max()))
