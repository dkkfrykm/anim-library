import sys, math
sys.path.insert(0, "C:/Users/mytwo/soulbound/skyrim/tools")
import sky2r15 as S
from mathutils import Matrix, Vector
skel = S.hkx.load(S.SKEL)["skeletons"][0]
src, rt, mk, frames, worlds = S.convert(sys.argv[sys.argv.index("--") + 1], skel)
def E(e):
    x, y, z = (math.radians(a) for a in e)
    return Matrix.Rotation(x, 3, "X") @ Matrix.Rotation(y, 3, "Y") @ Matrix.Rotation(z, 3, "Z")
for f in (0, 31, 50):
    row, W = frames[f], worlds[f]
    P = {}
    for j in S.rig.ORDER:
        par = S.rig.J[j][0]
        P[j] = (P[par] @ E(row[j])) if par else E(row[j])
    for j, (bn, ch, _) in S.MAP.items():
        if not ch: 
            fw = P[j] @ Vector((0, 0, -1)); print(f, j, "fwd", [round(v, 2) for v in fw]); continue
        piv, tail = S.rig.J[j][1], S.rig.J[j][2]
        r = (P[j] @ (Vector(tail) - Vector(piv))).normalized()
        s = S.rbx_vec(W[src.idx[ch]][0] - W[src.idx[bn]][0]).normalized()
        print(f, j, round(math.degrees(r.angle(s)), 1), [round(v, 2) for v in r], [round(v, 2) for v in s])
