import sys, numpy as np
def tracks(d, maxn=2):
    """greedy 3D tracking of NLF detections by pelvis position; returns list of index arrays per track (-1 = missing)"""
    J = d['joints3d']; n, K = J.shape[:2]; pel = J[:, :, 0]; T = []
    for t in range(n):
        dets = [k for k in range(K) if not np.isnan(pel[t, k, 0])]; used = set()
        for tr in T:
            last = next((pel[s, tr['idx'][s]] for s in range(t - 1, max(-1, t - 15), -1) if tr['idx'][s] >= 0), None)
            if last is None: tr['idx'].append(-1); continue
            c = [(np.linalg.norm(pel[t, k] - last), k) for k in dets if k not in used]
            c = [x for x in c if x[0] < 350]
            if c: k = min(c)[1]; used.add(k); tr['idx'].append(k)
            else: tr['idx'].append(-1)
        for k in dets:
            if k not in used and len(T) < 6: T.append({'idx': [-1] * t + [k]})
    T = [np.array(tr['idx']) for tr in T]; T.sort(key=lambda a: -(a >= 0).sum()); return T[:maxn]
if __name__ == '__main__':
    d = np.load(sys.argv[1]); T = tracks(d, 3); J = d['joints3d']
    for i, tr in enumerate(T):
        ok = tr >= 0; jj = np.array([J[t, k] for t, k in enumerate(tr) if k >= 0])
        tor = jj[:, 12] - jj[:, 0]; horiz = np.degrees(np.arccos(np.clip(np.abs(-tor[:, 1]) / np.linalg.norm(tor, axis=-1), 0, 1)))
        print('track', i, 'coverage', round(ok.mean(), 2), 'pelvis cam y/z mm', np.median(jj[:, 0, 1]).round(), np.median(jj[:, 0, 2]).round(), 'torso from vertical deg', np.median(horiz).round(), 'height-ish head y', np.median(jj[:, 15, 1]).round(), 'betas0', np.nanmedian([d['betas'][t, k, 0] for t, k in enumerate(tr) if k >= 0]).round(2))
