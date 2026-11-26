# Full-body R15 pose QA for Soulbound clip rows (dict joint -> Roblox Euler deg, "p" -> Root offset studs).
# Flags: elbow above shoulder, hands beside head, hand in head/torso, crossed knees, extreme lean, pops/jitter,
# planted-foot sliding. Allowed windows (frames) suppress technique-required flags (strike arcs).
import math

J = {  # joint: (parent, pivot) in HRP space at rest (rig.py)
    "Root": (None, (0, -1.0, 0)), "Waist": ("Root", (0, -0.8, 0)), "Neck": ("Waist", (0, 0.8, 0)),
    "RightShoulder": ("Waist", (1.0, 0.55, 0)), "RightElbow": ("RightShoulder", (1.5, -0.35, 0)), "RightWrist": ("RightElbow", (1.5, -1.35, 0)),
    "LeftShoulder": ("Waist", (-1.0, 0.55, 0)), "LeftElbow": ("LeftShoulder", (-1.5, -0.35, 0)), "LeftWrist": ("LeftElbow", (-1.5, -1.35, 0)),
    "RightHip": ("Root", (0.5, -1.2, 0)), "RightKnee": ("RightHip", (0.5, -2.0, 0)), "RightAnkle": ("RightKnee", (0.5, -2.75, 0)),
    "LeftHip": ("Root", (-0.5, -1.2, 0)), "LeftKnee": ("LeftHip", (-0.5, -2.0, 0)), "LeftAnkle": ("LeftKnee", (-0.5, -2.75, 0)),
}
ORDER = list(J.keys())
GROUND = -2.95


def R(e):
    x, y, z = (math.radians(a) for a in e)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    return mm(mm([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]), [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])


def mm(a, b): return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mv(a, v): return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]
def tr(a): return [[a[j][i] for j in range(3)] for i in range(3)]
def add(a, b): return [a[i] + b[i] for i in range(3)]
def sub(a, b): return [a[i] - b[i] for i in range(3)]


def fk(row):
    """-> pos (joint pivot positions), rot (world rotation) in HRP space; also hand/head centres"""
    pos, rot = {}, {}
    for j in ORDER:
        par, piv = J[j]
        Rl = R(row.get(j, (0, 0, 0)))
        if par is None:
            pos[j] = add(list(piv), list(row.get("p", (0, 0, 0))))
            rot[j] = Rl
        else:
            pos[j] = add(pos[par], mv(rot[par], sub(piv, J[par][1])))
            rot[j] = mm(rot[par], Rl)
    hand = {s: add(pos[s + "Wrist"], mv(rot[s + "Wrist"], [0, -0.17, 0])) for s in ("Right", "Left")}
    foot = {s: add(pos[s + "Ankle"], mv(rot[s + "Ankle"], [0, -0.13, -0.1])) for s in ("Right", "Left")}
    return pos, rot, hand, foot


def angle(Ra, Rb):
    m = mm(tr(Ra), Rb)
    c = max(-1.0, min(1.0, (m[0][0] + m[1][1] + m[2][2] - 1) / 2))
    return math.degrees(math.acos(c))


def check(rows, allow=(), windows=(), planted_tol=0.035, jitter_arm=34, jitter_body=22):
    """allow: set of flag kinds allowed inside windows; windows: list of (f0, f1). returns {kind: [frames]}"""
    flags = {}
    def flag(k, f):
        if k in allow and any(a <= f <= b for a, b in windows):
            return
        flags.setdefault(k, []).append(f)
    prev = None
    for f, row in enumerate(rows):
        pos, rot, hand, foot = fk(row)
        Wt = rot["Waist"]; Wi = tr(Wt)
        for s in ("Right", "Left"):
            sh = pos[s + "Shoulder"]; el = pos[s + "Elbow"]
            sh_t = mv(Wi, sub(sh, pos["Waist"])); el_t = mv(Wi, sub(el, pos["Waist"])); h_t = mv(Wi, sub(hand[s], pos["Waist"]))
            if el_t[1] > sh_t[1] + 0.05:
                flag("elbow_up", f)
            if abs(h_t[0]) > 1.2 and h_t[1] > 1.6:
                flag("hands_up", f)
            hc = mv(Wi, sub(hand[s], pos["Neck"]))  # head box around neck pivot +0.6
            if abs(hc[0]) < 0.75 and -0.05 < hc[1] < 1.3 and abs(hc[2]) < 0.75:
                flag("hand_in_head", f)
            if abs(h_t[0]) < 0.95 and -0.05 < h_t[1] < 1.55 and abs(h_t[2]) < 0.45:
                flag("hand_in_torso", f)
        Ri = tr(rot["Root"])
        kr = mv(Ri, sub(pos["RightKnee"], pos["Root"])); kl = mv(Ri, sub(pos["LeftKnee"], pos["Root"]))
        ar = mv(Ri, sub(pos["RightAnkle"], pos["Root"])); al = mv(Ri, sub(pos["LeftAnkle"], pos["Root"]))
        if kr[0] < kl[0] - 0.05 or ar[0] < al[0] - 0.05:
            flag("crossed_knees", f)
        up = mv(Wt, [0, 1, 0])
        if math.degrees(math.acos(max(-1, min(1, up[1])))) > 62:
            flag("extreme_lean", f)
        if prev is not None:
            prot, pfoot = prev
            for j in ORDER:
                lim = jitter_arm if ("Shoulder" in j or "Elbow" in j or "Wrist" in j or "Hip" in j or "Knee" in j or "Ankle" in j) else jitter_body
                if angle(prot[j], rot[j]) > lim:
                    flag("pop", f)
                    break
            for s in ("Right", "Left"):
                a, b = pfoot[s], foot[s]
                if a[1] < GROUND + 0.12 and b[1] < GROUND + 0.12 and math.hypot(a[0] - b[0], a[2] - b[2]) > planted_tol:
                    flag("foot_slide", f)
        prev = (rot, foot)
    return flags
