# Comparison grid: one tile per power playing the same clip slot (default M1_1), from chainvid frames (vid_<pid>/q34_*.png).
# Run: python gridvid.py <dir> <pid,pid,...> <out.mp4> [clip=M1_1] [view=q34] [cols=4]
import sys, os, json, cv2, numpy as np
D, pids, out = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
clip = sys.argv[4] if len(sys.argv) > 4 else "M1_1"
view = sys.argv[5] if len(sys.argv) > 5 else "q34"
cols = int(sys.argv[6]) if len(sys.argv) > 6 else 4
seqs = {}
for pid in pids:
    fdir = os.path.join(D, "vid_" + pid)
    info = json.load(open(os.path.join(fdir, "info.json")))
    segs = info.get("segs") or [(c, None) for c in info["clips"]]
    ks = [k for c, k in segs] + [info["frames"]]
    names = [c for c, k in segs]
    if clip not in names:
        continue
    a = ks[names.index(clip)]; b = ks[names.index(clip) + 1]
    seqs[pid] = [cv2.imread(os.path.join(fdir, "%s_%04d.png" % (view, k))) for k in range(a, b)]
L = max(len(v) for v in seqs.values())
h, w = next(iter(seqs.values()))[0].shape[:2]
rows = (len(seqs) + cols - 1) // cols
vw = None
for rep in range(2):  # play twice
    for f in range(L + 6):
        canvas = np.zeros((rows * h, cols * w, 3), np.uint8)
        for n, (pid, fr) in enumerate(seqs.items()):
            im = fr[min(f, len(fr) - 1)].copy()
            cv2.putText(im, pid, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            r, c = divmod(n, cols)
            canvas[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
        if vw is None:
            vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), 15, (canvas.shape[1], canvas.shape[0]))
        vw.write(canvas)
vw.release()
print(out, len(seqs), "tiles", L, "frames")
