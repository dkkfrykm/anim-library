# Forward kinematics over decoded JSON (Skyrim model space, units). Bones not animated use the reference pose.
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode import qmul, qrot


def world(d, f):
    sk = d["skeleton"]
    nb = len(sk["bones"])
    loc = [(tuple(r["t"]), tuple(r["q"])) for r in sk["ref"]]
    for ti, bi in enumerate(d["t2b"]):
        t, q, s = d["frames"][f][ti]
        loc[bi] = (tuple(t), tuple(q))
    W = [None] * nb
    for i in range(nb):
        p = sk["parents"][i]
        t, q = loc[i]
        if p < 0:
            W[i] = (t, q)
        else:
            pt, pq = W[p]
            wt = qrot(pq, t)
            W[i] = ((pt[0] + wt[0], pt[1] + wt[1], pt[2] + wt[2]), qmul(pq, q))
    return W


def ref_world(d):
    sk = d["skeleton"]
    W = []
    for i, r in enumerate(sk["ref"]):
        p = sk["parents"][i]
        t, q = tuple(r["t"]), tuple(r["q"])
        if p < 0:
            W.append((t, q))
        else:
            pt, pq = W[p]
            wt = qrot(pq, t)
            W.append(((pt[0] + wt[0], pt[1] + wt[1], pt[2] + wt[2]), qmul(pq, q)))
    return W


if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    bones = d["skeleton"]["bones"]
    names = sys.argv[2:]
    R = ref_world(d)
    for n in names:
        i = bones.index(n)
        print("ref", n, [round(x, 1) for x in R[i][0]])
    for f in range(d["numFrames"]):
        W = world(d, f)
        print(f, "  ".join("%s %s" % (n.split("[")[0].strip()[-8:], [round(x, 1) for x in W[bones.index(n)][0]]) for n in names))
