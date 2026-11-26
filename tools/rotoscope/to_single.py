import sys, numpy as np
sys.path.insert(0, '.'); from track import tracks
src, out = sys.argv[1], sys.argv[2]; d = np.load(src); T = tracks(d, 1)[0]; n = len(T)
o = {}
for k in ('pose', 'betas', 'trans', 'joints3d', 'joints2d', 'juncert', 'box'):
    a = d[k]; o[k] = np.stack([a[t, T[t]] if T[t] >= 0 else np.full(a.shape[2:], np.nan) for t in range(n)])
np.savez_compressed(out, fps=d['fps'], wh=d['wh'], model='smplx', fov=55, nppl=d['count'], **o); print(out, n, 'coverage', (T >= 0).mean().round(2))
