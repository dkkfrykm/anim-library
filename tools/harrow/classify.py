import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import decode, fk
rows = json.load(open("../out/batch_clips.json"))
pref = sys.argv[1].split(",")
for path, name in rows:
    if not any(name.startswith("Sky_" + p + "_") for p in pref): continue
    d = decode.decode(path)
    B = d["skeleton"]["bones"]
    idx = {n.split(" [")[0]: i for i, n in enumerate(B)}
    parts = {"RH": "NPC R Hand", "LH": "NPC L Hand", "RF": "NPC R Foot", "LF": "NPC L Foot"}
    W = [fk.world(d, f) for f in range(d["numFrames"])]
    fps = d["fps"]
    hits = [t for t, s in d["annotations"] if s and s.lower() == "hitframe"]
    out = []
    for h in hits:
        f = int(round(h * fps))
        best = None
        for k, b in parts.items():
            i = idx[b]
            for g in range(max(1, f - 3), min(len(W), f + 5)):
                v = math.dist(W[g][i][0], W[g - 1][i][0])
                if best is None or v > best[0]: best = (v, k, round(W[g][i][0][2]))
        out.append("%.2f:%s(v%.0f,z%d)" % (h, best[1], best[0], best[2]))
    print(name, " ".join(out))
