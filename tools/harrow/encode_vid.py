# Encode out/phase4/vid_<pid>/side_*.png + front_*.png side by side into out/phase4/video_<pid>.mp4 (30 fps = half-rate of 60).
import sys, os, json, cv2, numpy as np
D = sys.argv[2] if len(sys.argv) > 2 else "C:/Users/mytwo/harrow/anim/out/phase4"
for pid in sys.argv[1].split(","):
    fdir = os.path.join(D, "vid_" + pid)
    info = json.load(open(os.path.join(fdir, "info.json"))); n = info["frames"]; segs = info.get("segs", [])
    out = None
    for k in range(n):
        ims = [cv2.imread(os.path.join(fdir, "%s_%04d.png" % (v, k))) for v in ("side", "front", "q34")]
        fr = np.hstack([i for i in ims if i is not None])
        lab = [c for c, k0 in segs if k0 <= k]
        cv2.putText(fr, pid + ("  " + lab[-1] if lab else "") + "   side | front | 3/4", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        if out is None:
            out = cv2.VideoWriter(os.path.join(D, "video_%s.mp4" % pid), cv2.VideoWriter_fourcc(*"mp4v"), 30, (fr.shape[1], fr.shape[0]))
        out.write(fr)
    out.release()
    print(pid, n, "frames")
