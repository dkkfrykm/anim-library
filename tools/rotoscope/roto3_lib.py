"""shared helpers for the roto3 bakes"""
import numpy as np
from mocap_lib import rodrigues, m2q, q2m, rot_log

def decimate(src, dst):
    d = np.load(src); n = len(d['pose']) // 2 * 2; out = {}
    P = d['pose'][:n].reshape(n // 2, 2, -1, 3); q = m2q(rodrigues(P))            # [m,2,J,4]
    s = np.sign((q[:, 0] * q[:, 1]).sum(-1, keepdims=True)); qa = q[:, 0] + q[:, 1] * s; qa /= np.linalg.norm(qa, axis=-1, keepdims=True)
    out['pose'] = rot_log(q2m(qa)).reshape(n // 2, -1)
    for k in ('betas', 'trans', 'joints3d', 'joints2d', 'juncert', 'box'): out[k] = d[k][:n].reshape((n // 2, 2) + d[k].shape[1:]).mean(1)
    out['nppl'] = d['nppl'][:n:2]
    np.savez_compressed(dst, fps=float(d['fps']) / 2, wh=d['wh'], fov=d['fov'], model=d['model'], **out); return n // 2

