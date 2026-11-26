"""QA only: side-by-side sheets (reference video frame vs our render at the same cycle phase) -> qa/roto/cmp_<clip>.jpg
Usage: python -I tools/roto/roto_compare.py <reiko_breed dir> <renders dir> <frames dir with v<i>.npy>
Renders come from tools/roto/shots.js with names <clip>_p<phase*100>. Internal QA material, not game assets."""
import sys, os, json, site; sys.path.append(site.getusersitepackages())
import numpy as np, cv2
D, R, V = sys.argv[1:4]; M = json.load(open(os.path.join(D, 'tools', 'roto', 'roto_measure.json')))
CL = {'roto_twerk': ('twerk', 2, False), 'roto_idle_sway': ('idle_sway', 3, False), 'roto_doggy': ('doggy', 8, True), 'roto_press': ('press', 10, False), 'roto_oral': ('oral', 20, False)}
for clip, (mk, k, flip) in CL.items():
    m = M[mk]; F = np.load(os.path.join(V, 'v%d.npy' % m['video']), mmap_mode='r'); top, bot = [], []
    for ph in (0, .25, .5, .75):
        fi = int(round(m['phase0_frame'] + (k + ph) * m['period_frames'])); im = np.array(F[min(fi, len(F) - 1)])
        im = cv2.resize(im, (int(im.shape[1] * 240 / im.shape[0]), 240)); cv2.putText(im, 'ref f%d  phase %.2f' % (fi, ph), (4, 16), 0, .45, (0, 255, 255), 1); top.append(im)
        r = cv2.imread(os.path.join(R, '%s_p%02d.png' % (clip, int(ph * 100)))); r = cv2.flip(r, 1) if flip else r
        r = cv2.resize(r, (int(r.shape[1] * 240 / r.shape[0]), 240)); cv2.putText(r, 'ours phase %.2f%s' % (ph, ' (mirrored)' if flip else ''), (4, 16), 0, .45, (0, 255, 255), 1); bot.append(r)
    w = max(sum(x.shape[1] for x in top), sum(x.shape[1] for x in bot)); pad = lambda row: np.hstack(row + [np.zeros((240, w - sum(x.shape[1] for x in row), 3), np.uint8)]) if w > sum(x.shape[1] for x in row) else np.hstack(row)
    hdr = np.zeros((26, w, 3), np.uint8); cv2.putText(hdr, '%s  period %.3fs  (QA only)' % (clip, m['period_s']), (6, 18), 0, .55, (255, 255, 255), 1)
    out = os.path.join(D, 'qa', 'roto', 'cmp_%s.jpg' % clip); cv2.imwrite(out, np.vstack([hdr, pad(top), pad(bot)]), [cv2.IMWRITE_JPEG_QUALITY, 85]); print('wrote', out)
