# R15 arm FK in UpperTorso space + guard solver + pose checks (elbows above shoulders, hands inside head/torso).
# Conventions: Roblox joint Eulers, CFrame.Angles(x,y,z) = Rx*Ry*Rz, degrees; studs; X right, Y up, -Z forward.
import math, itertools, json, sys

J = {  # pivots (rig.py), relative to the HRP-space rest pose
    "RightShoulder": (1.0, 0.55, 0), "RightElbow": (1.5, -0.35, 0), "RightWrist": (1.5, -1.35, 0),
    "LeftShoulder": (-1.0, 0.55, 0), "LeftElbow": (-1.5, -0.35, 0), "LeftWrist": (-1.5, -1.35, 0),
    "Waist": (0, -0.8, 0), "Neck": (0, 0.8, 0),
}
HEAD = ((0, 1.4, 0), (0.6, 0.6, 0.6))     # centre, half extents (UpperTorso space: Waist pivot offset ignored -> use torso origin)
TORSO = ((0, 0.0, 0), (1.0, 0.8, 0.5))


def R(e):
    x, y, z = (math.radians(a) for a in e)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]; Ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]; Rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]
    return mm(mm(Rx, Ry), Rz)


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def add(a, b): return [a[i] + b[i] for i in range(3)]
def sub(a, b): return [a[i] - b[i] for i in range(3)]


def arm(side, sh, el, wr=(0, 0, 0)):
    S, E, W = J[side + "Shoulder"], J[side + "Elbow"], J[side + "Wrist"]
    Rs = R(sh); Re = mm(Rs, R(el)); Rw = mm(Re, R(wr))
    elbow = add(S, mv(Rs, sub(E, S)))
    wrist = add(elbow, mv(Re, sub(W, E)))
    hand = add(wrist, mv(Rw, [0, -0.17, 0]))
    return elbow, wrist, hand


def inside(p, box, pad=0.25):
    c, h = box
    return all(abs(p[i] - c[i]) < h[i] + pad for i in range(3))


def solve(side, target, sx=(0, 70), sz=(-25, 25), el=(40, 140), sy=(-70, 70), w_elbow=1.0):
    best = None
    for a, b, c, d in itertools.product(range(sx[0], sx[1] + 1, 5), range(sy[0], sy[1] + 1, 5), range(sz[0], sz[1] + 1, 5), range(el[0], el[1] + 1, 5)):
        e, w, h = arm(side, (a, b, c), (d, 0, 0))
        err = math.dist(h, target)
        if e[1] > J[side + "Shoulder"][1] - 0.3:      # elbow must stay well below shoulder
            err += 2
        if inside(h, HEAD) or inside(h, TORSO, 0.15):
            err += 1.5
        err += 0.004 * abs(b) + 0.006 * abs(c)        # prefer little twist / abduction
        if best is None or err < best[0]:
            best = (err, (a, b, c), d, h, e)
    return best


def check_rows(rows, allow=()):
    """returns list of (frame, issue) for a clip's 60fps rows (dict joint->euler)"""
    out = []
    for f, r in enumerate(rows):
        for side in ("Right", "Left"):
            if side + "Shoulder" not in r:
                continue
            e, w, h = arm(side, r[side + "Shoulder"], r[side + "Elbow"], r.get(side + "Wrist", (0, 0, 0)))
            if e[1] > J[side + "Shoulder"][1] + 0.05 and "elbow_up" not in allow:
                out.append((f, side + " elbow above shoulder"))
            if abs(h[0]) > 1.2 and h[1] > 0.8 and "elbow_up" not in allow:
                out.append((f, side + " hands-up beside head"))
            if inside(h, HEAD, 0.05):
                out.append((f, side + " hand in head"))
            if inside(h, TORSO, -0.05):
                out.append((f, side + " hand in torso"))
    return out


if __name__ == "__main__":
    targets = json.loads(sys.argv[1])
    for name, (side, t) in targets.items():
        b = solve(side, t)
        print(name, "shoulder", b[1], "elbow", b[2], "hand", [round(x, 2) for x in b[3]], "elbowpos", [round(x, 2) for x in b[4]], "err %.2f" % b[0])
