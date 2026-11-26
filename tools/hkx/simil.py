# Pairwise motion distinctness between powers from phase-5/6 rows.json.
# Per shared clip slot: DTW over per-frame R15 joint rotations (geodesic deg, summed over joints) + pelvis path (deg-equivalent),
# normalised by the warp path length. Power distance = mean over shared slots. Guard distance = frame-0 pose distance.
# Run: python simil.py <rows.json> <out.json> [--slots M1_1,M1_2,...]
import sys, json, math, itertools
import numpy as np

JOINTS = ["Root", "Waist", "Neck", "RightShoulder", "RightElbow", "RightWrist", "LeftShoulder", "LeftElbow", "LeftWrist",
          "RightHip", "RightKnee", "RightAnkle", "LeftHip", "LeftKnee", "LeftAnkle"]
P_W = 60.0  # deg per stud of pelvis offset
SLOTS = ["M1_1", "M1_2", "M1_3", "M1_4", "Dash", "Bolt", "Blast", "Burst", "Ult"]


def quat(e):
    x, y, z = (math.radians(a) / 2 for a in e)
    qx = np.array([math.cos(x), math.sin(x), 0, 0]); qy = np.array([math.cos(y), 0, math.sin(y), 0]); qz = np.array([math.cos(z), 0, 0, math.sin(z)])
    return qmul(qmul(qx, qy), qz)


def qmul(a, b):
    w1, x1, y1, z1 = a; w2, x2, y2, z2 = b
    return np.array([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2])


def feats(rows, n=None):
    rows = rows[:n + 1] if n else rows
    Q = np.array([[quat(r.get(j, (0, 0, 0))) for j in JOINTS] for r in rows])  # F x J x 4
    Pv = np.array([r.get("p", (0, 0, 0)) for r in rows])
    return Q, Pv


def cost(A, B):
    (Qa, Pa), (Qb, Pb) = A, B
    d = np.abs(np.einsum("ajk,bjk->abj", Qa, Qb)).clip(0, 1)
    ang = np.degrees(2 * np.arccos(d)).sum(-1)
    pd = np.linalg.norm(Pa[:, None, :] - Pb[None, :, :], axis=-1) * P_W
    return ang + pd


def dtw(C):
    n, m = C.shape
    D = np.full((n + 1, m + 1), np.inf); D[0, 0] = 0
    L = np.zeros((n + 1, m + 1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            k = np.argmin((D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]))
            pi, pj = ((i - 1, j - 1), (i - 1, j), (i, j - 1))[k]
            D[i, j] = C[i - 1, j - 1] + D[pi, pj]; L[i, j] = L[pi, pj] + 1
    return D[n, m] / L[n, m]


def main():
    import glob, os, re
    rows, NS = {}, {}
    for rf in sys.argv[1].split(","):  # later files override earlier (e.g. v5 baseline, then phase-6 batches)
        rows.update(json.load(open(rf)))
        for f in glob.glob(os.path.join(os.path.dirname(rf), "Clips_Sky*.lua")):
            NS.update({k: int(v) for k, v in re.findall(r"^(Sky_\w+?)=\{n=(\d+)", open(f).read(), re.M)})
    out = sys.argv[2]
    slots = sys.argv[sys.argv.index("--slots") + 1].split(",") if "--slots" in sys.argv else SLOTS
    by = {}
    for name, r in rows.items():
        parts = name.split("_")
        if len(parts) < 3 or parts[1] in ("Stand",) or parts[1][0].isupper():
            continue
        pid, slot = parts[1], "_".join(parts[2:])
        if slot in slots:
            by.setdefault(pid, {})[slot] = feats(r, NS.get(name))  # main clip (loops sit after n)
    pids = sorted(by)
    res = {"pids": pids, "dist": {}, "guard": {}, "slot": {}}
    for a, b in itertools.combinations(pids, 2):
        shared = [s for s in slots if s in by[a] and s in by[b]]
        ds = {s: float(dtw(cost(by[a][s], by[b][s]))) for s in shared}
        key = a + "|" + b
        res["slot"][key] = ds
        res["dist"][key] = float(np.mean(list(ds.values()))) if ds else None
        ga, gb = by[a]["M1_1"], by[b]["M1_1"]
        res["guard"][key] = float(cost((ga[0][:1], ga[1][:1]), (gb[0][:1], gb[1][:1]))[0, 0])
    json.dump(res, open(out, "w"), indent=0)
    pairs = sorted(res["dist"].items(), key=lambda kv: kv[1])
    kb = res["dist"].get("boxer|karate")
    print("karate|boxer =", round(kb, 1))
    print("below karate|boxer:", sum(1 for k, v in pairs if v < kb), "of", len(pairs))
    for k, v in pairs[:25]:
        print("%-34s %6.1f guard %6.1f" % (k, v, res["guard"][k]))
    gs = sorted(res["guard"].items(), key=lambda kv: kv[1])
    print("closest guards:", ", ".join("%s %.0f" % kv for kv in gs[:12]))


if __name__ == "__main__":
    main()
