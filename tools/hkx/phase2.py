# Phase 2: turn retargeted Skyrim clips into Soulbound power clips.
#   trim + retime onto Soulbound slot timing (anticipation -> swing -> impact hold -> fast recovery to neutral),
#   stylise (amplified arcs, extra torso twist, impact squash), blend from/to neutral (Soulbound idle base),
#   simple 2-bone foot planting, multi-hit loop (la..lb, 18 frames) for slots that need one.
# Run: blender --background --python phase2.py -- [--styles Blade,Fighter] [--render] [--out DIR]
# Writes DIR/Clips_Sky<Style>.lua, DIR/Sky_markers.json, renders + DIR/sheet_style_<Style>.png data (renders json).
import bpy, sys, os, math, json
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky2r15 as S
rig = S.rig

FPS = 60
SRC_ROOT = "C:/Users/mytwo/soulbound/skyrim/src"
BATCH = json.load(open("C:/Users/mytwo/soulbound/skyrim/out/batch_clips.json"))
SRCPATH = {n: p for p, n in BATCH}

# Soulbound slot timing (copied from anim/out/Clips_*.lua): n, w, i, r, la (None = no loop)
SLOT = {
    "M1": (36, 6, 10, 28, None), "M1_4": (40, 6, 12, 30, None),
    "Bolt": (46, 10, 14, 36, 52), "Burst": (50, 12, 16, 40, 56), "Blast": (56, 18, 22, 46, 62),
    "Dash": (36, 5, 8, 28, 42), "Ult": (72, 24, 30, 62, 78),
}
TITAN_SLOW = {"M1": (40, 7, 11, 30, None), "M1_4": (42, 8, 12, 32, None), "Bolt": (50, 12, 16, 40, 56),
              "Burst": (54, 14, 18, 44, 60)}

# target clip -> (source catalog clip, slot timing key, options)
MAPPING = {
    # Blade
    "Sky_Blade_M1_1": ("Sky_Sword_A1", "M1", {}),
    "Sky_Blade_M1_2": ("Sky_Sword_A2", "M1", {}),
    "Sky_Blade_M1_3": ("Sky_Sword_A3", "M1", {}),
    "Sky_Blade_M1_4": ("Sky_Sword_A4", "M1_4", {"loop": True}),
    "Sky_Blade_Bolt": ("Sky_Sword_P5", "Bolt", {}),
    "Sky_Blade_Burst": ("Sky_Glaive_P4", "Burst", {}),
    "Sky_Blade_Blast": ("Sky_Sword_P1", "Blast", {}),
    "Sky_Blade_Dash": ("Sky_Rapier_A3", "Dash", {}),
    "Sky_Blade_Ult": ("Sky_Glaive_P2", "Ult", {}),
    # Fighter (punches verified by strike-limb analysis: Unarmed A1 RH, A2 LH, Skysa A4 LH, Skysa P1 RH)
    "Sky_Fighter_M1_1": ("Sky_Unarmed_A1", "M1", {}),
    "Sky_Fighter_M1_2": ("Sky_Unarmed_A2", "M1", {}),
    "Sky_Fighter_M1_3": ("Sky_Skysa_A2", "M1", {}),
    "Sky_Fighter_M1_4": ("Sky_Skysa_P1", "M1_4", {}),
    "Sky_Fighter_Bolt": ("Sky_Unarmed_P1", "Bolt", {}),
    "Sky_Fighter_Burst": ("Sky_Unarmed_P2", "Burst", {}),
    "Sky_Fighter_Blast": ("Sky_Unarmed_P4", "Blast", {}),
    "Sky_Fighter_Dash": ("Sky_Skysa_A1", "Dash", {}),
    # Kick (Skysa is mixed punch/kick -> Unarmed kicks: A3 RF, A4 LF, A6 LF, A5 LF high)
    "Sky_Kick_M1_1": ("Sky_Unarmed_A3", "M1", {}),
    "Sky_Kick_M1_2": ("Sky_Unarmed_A4", "M1", {}),
    "Sky_Kick_M1_3": ("Sky_Unarmed_A6", "M1", {}),
    "Sky_Kick_M1_4": ("Sky_Unarmed_A5", "M1_4", {}),
    # Titan
    "Sky_Titan_M1_1": ("Sky_Heavy_A6", "M1", {"titan": True}),
    "Sky_Titan_M1_2": ("Sky_Heavy_A1", "M1", {"titan": True}),
    "Sky_Titan_M1_3": ("Sky_Heavy_A2", "M1", {"titan": True}),
    "Sky_Titan_M1_4": ("Sky_Heavy_A3", "M1_4", {"titan": True}),
    "Sky_Titan_Bolt": ("Sky_Heavy_P9", "Bolt", {"titan": True}),
    "Sky_Titan_Burst": ("Sky_Heavy_P5", "Burst", {"titan": True}),
    "Sky_Titan_Blast": ("Sky_Heavy_P3", "Blast", {"titan": True}),
    "Sky_Titan_Dash": ("Sky_Heavy_P4", "Dash", {"titan": True}),
    # Beast
    "Sky_Beast_M1_1": ("Sky_Scythe_A1", "M1", {}),
    "Sky_Beast_M1_2": ("Sky_Scythe_A2", "M1", {}),
    "Sky_Beast_M1_3": ("Sky_Scythe_A8", "M1", {}),
    "Sky_Beast_M1_4": ("Sky_Scythe_A6", "M1_4", {}),
    "Sky_Beast_Bolt": ("Sky_Scythe_P2", "Bolt", {}),
    "Sky_Beast_Burst": ("Sky_Scythe_P1", "Burst", {}),
    "Sky_Beast_Blast": ("Sky_Unarmed_P3", "Blast", {}),
    "Sky_Beast_Dash": ("Sky_Shinobi_A3", "Dash", {}),
    # Mystic
    "Sky_Mystic_M1_1": ("Sky_ShinMagic_A1", "M1", {}),
    "Sky_Mystic_M1_2": ("Sky_ShinMagic_A3", "M1", {}),
    "Sky_Mystic_M1_3": ("Sky_ShinMagic_A4", "M1", {}),
    "Sky_Mystic_M1_4": ("Sky_ShinMagic_A5", "M1_4", {}),
    "Sky_Mystic_Bolt": ("Sky_ShinMagic_P1", "Bolt", {}),
    "Sky_Mystic_Burst": ("Sky_ShinMagic_P2", "Burst", {}),
    "Sky_Mystic_Blast": ("Sky_ShinMagic_P7", "Blast", {}),
    "Sky_Mystic_Dash": ("Sky_ShinMagic_Dodgeleft", "Dash", {}),
    # Spirit
    "Sky_Spirit_Bolt": ("Sky_ShinMagic_P3", "Bolt", {}),
    "Sky_Spirit_Burst": ("Sky_ShinMagic_P4", "Burst", {}),
    "Sky_Spirit_Blast": ("Sky_ShinMagic_P5", "Blast", {}),
    "Sky_Spirit_Dash": ("Sky_Shinobi_Dodgeback", "Dash", {}),
    # Ults
    "Sky_Ult_Leap": ("Sky_Heavy_P1", "Ult", {}),
    "Sky_Ult_Beam": ("Sky_ShinMagic_P6", "Ult", {}),
    "Sky_Ult_Nuke": ("Sky_ShinMagic_P7_2", "Ult", {}),
}

_pp = "C:/Users/mytwo/soulbound/skyrim/out/pool.json"
POOL_LIMBS = {c["code"]: c["limbs"] for c in json.load(open(_pp))} if os.path.exists(_pp) else {}
ARMS = {"RightShoulder", "RightElbow", "RightWrist", "LeftShoulder", "LeftElbow", "LeftWrist"}
LEGS = {"RightHip", "RightKnee", "RightAnkle", "LeftHip", "LeftKnee", "LeftAnkle"}
AMP = {"Neck": 1.1}
TWIST = {"Waist": 1.35, "Root": 1.15}  # extra yaw (torso twist) only; pitch/roll untouched
ARM_AMP = 1.15
HOLD = 3          # impact hold frames
GROUND_Y = -2.95  # R15 sole height relative to HRP (ankle pivot -2.75, foot 0.2 below)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def qpow(q, k):
    """rotate by k times the angle of q (extrapolates for k > 1)"""
    q = q.normalized()
    if q.w < 0:
        q = -q
    ang = 2 * math.acos(max(-1.0, min(1.0, q.w)))
    if ang < 1e-6:
        return Quaternion()
    axis = Vector((q.x, q.y, q.z)).normalized()
    ang = max(-math.pi * 0.95, min(math.pi * 0.95, ang * k))
    return Quaternion(axis, ang)


def twist_amp(q, k):
    """swing-twist split about the joint's Y (up) axis; scale only the twist"""
    q = q.normalized()
    tw = Quaternion((q.w, 0, q.y, 0))
    if tw.magnitude < 1e-6:
        return q.copy()
    tw.normalize()
    swing = q @ tw.inverted()
    return swing @ qpow(tw, k)


def to_rows(P, p):
    row = {}
    for j in rig.ORDER:
        par = rig.J[j][0]
        T = (P[par].transposed() @ P[j]) if par else P[j]
        m = T
        b = math.asin(max(-1, min(1, m[0][2])))
        a = math.atan2(-m[1][2], m[2][2])
        c = math.atan2(-m[0][1], m[0][0])
        row[j] = (math.degrees(a), math.degrees(b), math.degrees(c))
    row["p"] = (p.x, p.y, p.z)
    return row


def local_of(P):
    """joint-local rotations (quaternions) from world P"""
    L = {}
    for j in rig.ORDER:
        par = rig.J[j][0]
        L[j] = ((P[par].transposed() @ P[j]) if par else P[j]).to_quaternion()
    return L


def world_of(L):
    P = {}
    for j in rig.ORDER:
        par = rig.J[j][0]
        m = L[j].to_matrix()
        P[j] = (P[par] @ m) if par else m
    return P


def joint_pos(P, p):
    """world (HRP space) pivot positions of every joint + ankle tips"""
    X = {}
    for j in rig.ORDER:
        par = rig.J[j][0]
        piv = Vector(rig.J[j][1])
        if not par:
            X[j] = piv + p
        else:
            X[j] = X[par] + P[par] @ (piv - Vector(rig.J[par][1]))
    return X


def min_rot(a, b):
    a = a.normalized(); b = b.normalized()
    return a.rotation_difference(b).to_matrix()


IDX = {}
LEAN_MAX = {"Root": 28.0, "Waist": 40.0}  # deg from vertical before softening (deep Skyrim bows read prone on R15)


def lean_limit(M, mx):
    up = M @ Vector((0, 1, 0))
    ang = math.degrees(up.angle(Vector((0, 1, 0))))
    if ang <= mx:
        return M
    axis = up.cross(Vector((0, 1, 0)))
    if axis.length < 1e-6:
        return M
    back = (ang - mx) * 0.8
    return Matrix.Rotation(math.radians(back), 3, axis.normalized()) @ M


def _pos(W, name):
    return S.rbx_vec(W[IDX[name]][0])


def _basis(right, up):
    x = right.normalized()
    y = (up - x * up.dot(x)).normalized()
    return Matrix((x, y, x.cross(y))).transposed()


TORSO = {
    "Root": lambda W: _basis(_pos(W, "NPC R Thigh") - _pos(W, "NPC L Thigh"), _pos(W, "NPC Spine1") - _pos(W, "NPC Pelvis")),
    "Waist": lambda W: _basis(_pos(W, "NPC R Clavicle") - _pos(W, "NPC L Clavicle"), _pos(W, "NPC Neck") - _pos(W, "NPC Spine1")),
}


class Clip:
    def __init__(self, target, srcname, slot, opts, skel):
        self.target, self.srcname, self.opts = target, srcname, opts
        path = SRCPATH[srcname]
        self.src, self.rt, self.mk, frames, self.worlds60 = S.convert(path, skel)
        IDX.update(self.src.idx)
        tim = (TITAN_SLOW if opts.get("titan") else {}).get(slot) or SLOT[slot]
        self.n, self.w, self.i, self.r, self.la = tim
        if not opts.get("loop", True) or (slot.startswith("M1") and not opts.get("loop")):
            self.la = None
        mk = self.mk
        if not mk["i"]:  # dodges: impact = peak pelvis speed
            W = self.worlds60
            I = self.src.idx["NPC Pelvis"]
            sp = [0] + [(W[f][I][0] - W[f - 1][I][0]).length for f in range(1, len(W))]
            mk["i"] = [max(range(len(sp)), key=lambda f: sp[f])]
            mk["w"] = max(0, mk["i"][0] - 8)
        self.si = mk["i"][0]
        self.sw_ = min(mk["w"], self.si - 2)
        self.sw_ = max(0, self.sw_)
        self.s0 = max(0, self.sw_ - 20)                       # keep <= 1/3 s of source anticipation
        self.send = mk["n"]
        follow_out = self.r - self.i - HOLD
        self.sr = min(self.send, self.si + int(follow_out * 1.6))  # follow-through at <= 1.6x speed
        self.hits = mk["i"]

    # output frame -> source frame (60 fps units)
    def warp(self, f):
        w, i, r = self.w, self.i, self.r
        if f <= w:
            return self.s0 + (self.sw_ - self.s0) * (f / max(1, w))
        if f <= i:
            t = (f - w) / max(1, i - w)
            return self.sw_ + (self.si - self.sw_) * t
        if f <= i + HOLD:
            return self.si + 0.6 * (f - i) / HOLD          # near-hold: drifts 0.6 src frame
        if f <= r:
            t = (f - i - HOLD) / max(1, r - i - HOLD)
            return self.si + 0.6 + (self.sr - self.si - 0.6) * t
        return self.sr + (f - r) * 0.5

    def sample(self, sf):
        src = self.src
        ft = min(src.n - 1, max(0.0, (sf / FPS) / src.fd))
        Wd = src.world_at(ft)
        I = src.idx
        P = {}
        for j, (bn, _, _) in S.MAP.items():
            P[j] = S.rbx_rot(Wd[I[bn]][1]) @ self.rt.bindInv[j] @ self.rt.corr[j]
        # torso from aggregate chain vectors (R15 has one block for the whole spine): hips line + pelvis->spine,
        # clavicle line + spine->neck; delta vs the same basis in the bind pose
        if not hasattr(self, "tb"):
            self.tb = {k: fn(self.rt.B).inverted() for k, fn in TORSO.items()}
        for k, fn in TORSO.items():
            P[k] = lean_limit(fn(Wd) @ self.tb[k], LEAN_MAX[k])
        p = (S.rbx_vec(Wd[I["NPC Pelvis"]][0]) - self.rt.pelvis0) * S.LEG_SCALE
        if p.y < -0.3:  # R15 legs are short: soften deep Skyrim lunges (foot IK keeps the soles planted)
            p.y = -0.3 + (p.y + 0.3) * 0.35
        # flying/dive sets bake large body travel into the pelvis: keep only a local offset (travel is the server's job)
        p.x = max(-0.8, min(0.8, p.x)); p.z = max(-0.9, min(0.9, p.z)); p.y = max(-0.65, min(0.6, p.y))
        return P, p, Wd

    def stylise(self, L, p, f):
        out = {}
        for j, q in L.items():
            if j in ARMS:
                out[j] = qpow(q, ARM_AMP)
            elif j in AMP:
                out[j] = qpow(q, AMP[j])
            elif j in TWIST:
                out[j] = twist_amp(q, TWIST[j])
            else:
                out[j] = q.copy()
        # impact squash: dip + forward pitch for a few frames after each impact
        for ih in self.out_hits:
            d = f - ih
            if -1 <= d <= 8:
                k = math.sin(math.pi * max(0.0, d + 1) / 10.0)
                p = p + Vector((0, -0.16 * k, 0))
                out["Waist"] = out["Waist"] @ Quaternion(Vector((1, 0, 0)), math.radians(-7 * k))
        return out, p

    def build(self):
        n, w, i, r = self.n, self.w, self.i, self.r
        self.out_hits = [i]
        frames, src_worlds, srcf = [], [], []
        Ls, ps = [], []
        for f in range(n + 1):
            sf = self.warp(f)
            P, p, Wd = self.sample(sf)
            Ls.append(local_of(P)); ps.append(p); src_worlds.append(Wd); srcf.append(sf)
        # neutral blend in (first frames) and out (r..n): Soulbound idle = identity transforms
        bin_ = min(4, max(1, w))
        self.kw = []
        for f in range(n + 1):
            k = 1.0
            if f < bin_:
                k = smooth(f / bin_)
            if f > r:
                k = 1 - smooth((f - r) / max(1, n - r))
            self.kw.append(k)
            if k < 1:
                Ls[f] = {j: Quaternion().slerp(q, k) for j, q in Ls[f].items()}
                ps[f] = ps[f] * k
        # stylise
        for f in range(n + 1):
            Ls[f], ps[f] = self.stylise(Ls[f], ps[f], f)
        Ps = [world_of(L) for L in Ls]
        # loop frames (la..lb), appended after n with a bridge
        loop = None
        if self.la:
            la, lb = self.la, self.la + 18
            hitL, hitP = Ls[i], ps[i]
            if len(self.hits) >= 2:
                h1, h2 = self.hits[0], self.hits[1]
                seg = [h1 + (h2 - h1) * t / 18 for t in range(19)]
            else:
                seg = [self.si + (self.sw_ - self.si) * smooth(t / 8) for t in range(9)] + \
                      [self.sw_ + (self.si - self.sw_) * (t / 10) for t in range(1, 11)]
            for f in range(n + 1, lb + 1):
                if f < la:
                    k = (f - n) / (la - n)
                    L = {j: Ls[n][j].slerp(hitL[j], smooth(k)) for j in rig.ORDER}
                    pp = ps[n].lerp(hitP, smooth(k))
                    Wd = src_worlds[n]; sf = srcf[n]
                else:
                    t = f - la
                    sf = seg[t]
                    P, pp, Wd = self.sample(sf)
                    L = local_of(P)
                    L, pp = self.stylise(L, pp, -99)
                    # seamless ends: blend toward the hit pose near both loop ends
                    e = max(smooth(1 - t / 5.0), smooth((t - 12) / 6.0))
                    L = {j: L[j].slerp(hitL[j], e) for j in rig.ORDER}
                    pp = pp.lerp(hitP, e)
                    if t >= 15:  # small squash at the looped hit
                        pass
                Ls.append(L); ps.append(pp); Ps.append(world_of(L)); src_worlds.append(Wd); srcf.append(sf)
            loop = (la, lb)
        self.foot_plant(Ps, ps, src_worlds)
        rows = [to_rows(P, p) for P, p in zip(Ps, ps)]
        self.lean = max(math.degrees((P["Waist"] @ Vector((0, 1, 0))).angle(Vector((0, 1, 0)))) for P in Ps)
        self.neck = min(joint_pos(P, p)["Neck"].y for P, p in zip(Ps, ps))
        self.rows, self.Ps, self.ps, self.src_worlds, self.srcf, self.loop = rows, Ps, ps, src_worlds, srcf, loop
        # markers: swing frames mapped into output
        sw = sorted(set([w] + [f for f in range(n + 1) if any(abs(self.warp(f) - s) < 0.5 for s in self.mk["sw"]) and f <= i]))
        self.markers = dict(n=n, w=w, i=[i], r=r, sw=sw, src=self.srcname)
        lim = POOL_LIMBS.get(self.srcname)
        if lim:
            self.markers["limb"] = [lim[0]]
        if loop:
            self.markers.update(la=loop[0], lb=loop[1])
        return self

    def foot_plant(self, Ps, ps, src_worlds):
        """2-bone IK: feet that are on the ground in the source stay put while planted, and never sink below it."""
        I = self.src.idx
        for side, (hip, knee, ankle, sb) in {"R": ("RightHip", "RightKnee", "RightAnkle", "NPC R Foot"),
                                              "L": ("LeftHip", "LeftKnee", "LeftAnkle", "NPC L Foot")}.items():
            if side in getattr(self, "no_ik", ()):
                continue
            a = (Vector(rig.J[knee][1]) - Vector(rig.J[hip][1])).length
            b = (Vector(rig.J[ankle][1]) - Vector(rig.J[knee][1])).length
            anchor = None
            prev_sp = None
            for f in range(len(Ps)):
                Wd = src_worlds[f]
                fz = Wd[I[sb]][0].z
                spd = 0.0
                if f > 0:
                    d = Wd[I[sb]][0] - src_worlds[f - 1][I[sb]][0]
                    spd = math.hypot(d.x, d.y)
                planted = fz < 12.0 and spd < 1.2
                X = joint_pos(Ps[f], ps[f])
                A = X[ankle]
                if planted:
                    if anchor is None:
                        anchor = A.copy()
                    T = anchor.copy()
                else:
                    anchor = None
                    T = A.copy()
                T.y = max(T.y, GROUND_Y + 0.2)
                kw = self.kw[f] if f < len(self.kw) else 1.0
                T = A.lerp(T, kw)  # IK fades out with the blend to neutral
                if (T - A).length < 1e-3:
                    continue
                H, K = X[hip], X[knee]
                d = (T - H)
                dl = min(d.length, a + b - 1e-3)
                u = d.normalized()
                ca = max(-1, min(1, (a * a + dl * dl - b * b) / (2 * a * dl)))
                sa = math.sqrt(1 - ca * ca)
                pole = (K - H) - u * (K - H).dot(u)
                if pole.length < 1e-4:
                    pole = Ps[f]["Root"] @ Vector((0, 0, -1))
                    pole = pole - u * pole.dot(u)
                nK = H + (u * ca + pole.normalized() * sa) * a
                nT = H + u * dl
                foot_world = Ps[f][ankle].copy()
                r1 = min_rot(K - H, nK - H)
                Ps[f][hip] = r1 @ Ps[f][hip]
                Ps[f][knee] = min_rot(r1 @ (A - K), nT - nK) @ r1 @ Ps[f][knee]
                Ps[f][ankle] = foot_world


# ------------------------------------------------------------------------ encoding with loop support
def lua_clip(name, mk, frames):
    force = set(mk["i"]) | {mk["w"], mk["r"], mk["n"]}
    if mk.get("la"):
        force |= {mk["la"], mk["lb"], mk["n"] + 1}
    parts = []
    for j in rig.ORDER:
        vals = S.unwrap([fr[j] for fr in frames])
        if all(abs(v[0]) < 0.6 and abs(v[1]) < 0.6 and abs(v[2]) < 0.6 for v in vals):
            continue
        ks = S.decimate_series(vals, force, S.TOL)
        parts.append("%s=[[%s]]" % (S.SHORT[j], S.enc_keys(ks, lambda k: S.e1(vals[k][0]) + S.e1(vals[k][1]) + S.e1(vals[k][2]))))
    pv = [fr["p"] for fr in frames]
    if any(abs(x) > 0.01 for v in pv for x in v):
        ks = S.decimate_series(pv, force, S.PTOL)
        parts.append("p=[[%s]]" % S.enc_keys(ks, lambda k: S.e2(pv[k][0] * 100 + 4000) + S.e2(pv[k][1] * 100 + 4000) + S.e2(pv[k][2] * 100 + 4000)))
    meta = "n=%d,w=%d,i={%s},r=%d" % (mk["n"], mk["w"], ",".join(map(str, mk["i"])), mk["r"])
    if mk.get("la"):
        meta += ",la=%d,lb=%d" % (mk["la"], mk["lb"])
    meta += ",sw={%s},src=%s" % (",".join(map(str, mk["sw"])), json.dumps(mk["src"]))
    if mk.get("limb"):
        meta += ",limb={%s}" % ",".join(json.dumps(x) for x in mk["limb"])
    return "%s={%s,%s}" % (name, meta, ",".join(parts))


# ------------------------------------------------------------------------ renders
def render_clip(c, outdir, ob, REST, coll, mats):
    scene = bpy.context.scene
    m = c.markers
    picks = [0, m["w"], m["i"][0], m["i"][0] + HOLD, (m["i"][0] + m["r"]) // 2, m["r"], m["n"] - 3]
    if c.loop:
        picks.append(c.loop[0] + 9)
    res = []
    for f in picks:
        row = c.rows[f]
        for j in rig.ORDER:
            ob.pose.bones[j].rotation_quaternion = S.rb_euler_to_local(REST, j, row[j])
        ob.pose.bones["Root"].location = REST["Root"].inverted() @ (rig.C @ Vector(row["p"]))
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        S.draw_stick(c.src, c.src_worlds[f], coll, mats)
        bpy.context.view_layer.update()
        S.place_cam(scene.camera, (3.0, 1.8, -12.5), (-1.8, -0.9, 0))
        p = os.path.join(outdir, "%s_%03d.png" % (c.target, f))
        scene.render.filepath = p
        if not os.path.exists(p):
            bpy.ops.render.render(write_still=True)
        tag = "start" if f == 0 else "w" if f == m["w"] else "IMPACT" if f == m["i"][0] else "hold" if f == m["i"][0] + HOLD else \
            "r" if f == m["r"] else "loop" if c.loop and f == c.loop[0] + 9 else "end" if f == m["n"] - 3 else "follow"
        res.append((f, tag, p))
    return res


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    styles = None; outdir = "C:/Users/mytwo/soulbound/skyrim/out/phase2"; rnd = False
    for k, a in enumerate(argv):
        if a == "--styles": styles = set(argv[k + 1].split(","))
        if a == "--out": outdir = argv[k + 1]
        if a == "--render": rnd = True
    os.makedirs(os.path.join(outdir, "renders"), exist_ok=True)
    skel = S.hkx.load(S.SKEL)["skeletons"][0]
    by_style, markers, renders = {}, {}, {}
    if rnd:
        ob = S.setup_scene()
        bpy.context.scene.render.resolution_x = 300
        bpy.context.scene.render.resolution_y = 260
        REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
        coll = bpy.data.collections.new("stick"); bpy.context.scene.collection.children.link(coll)
        mats = {}
        for k, col in (("r", (0.9, 0.45, 0.2)), ("l", (0.3, 0.75, 0.35)), ("c", (0.85, 0.8, 0.75)), ("s", (0.7, 0.9, 1.0))):
            mm = bpy.data.materials.new("st_" + k); mm.diffuse_color = (*col, 1); mats[k] = mm
    jobs = [(t, v[0], v[1], v[2]) for t, v in MAPPING.items()]
    mapfile = next((argv[k + 1] for k, a in enumerate(argv) if a == "--mapping"), None)
    only = next((argv[k + 1] for k, a in enumerate(argv) if a == "--powers"), None)
    if mapfile:
        jobs = []
        for t, e in json.load(open(mapfile)).items():
            if only and t.split("_")[1] not in only.split(","):
                continue
            SRCPATH[e["code"]] = e["path"]
            o = {"titan": e.get("titan", False)}
            if e.get("loop"):
                o["loop"] = True
            jobs.append((t, e["code"], e["slot"], o))
    for target, srcname, slot, opts in jobs:
        style = target.split("_")[1]
        if styles and style not in styles:
            continue
        c = Clip(target, srcname, slot, opts, skel).build()
        by_style.setdefault(style, []).append(lua_clip(target, c.markers, c.rows))
        markers[target] = c.markers
        print("built", target, "<-", srcname, "lean %.0f neckY %.2f%s" % (c.lean, c.neck, "  PRONE?" if c.lean > 56 or c.neck < -0.55 else ""), c.markers["i"])
        if rnd:
            renders[target] = render_clip(c, os.path.join(outdir, "renders"), ob, REST, coll, mats)
    for style, items in by_style.items():
        src = ("-- AUTO-GENERATED by soulbound/skyrim/tools/phase2.py: Skyrim MCO/Skysa clips retargeted to R15, trimmed and\n"
               "-- retimed to Soulbound slot timing, stylised, foot-planted. Same format as anim/build.py plus sw (swing frames)\n"
               "-- and src (HKX base clip, catalog name). Used by Client.CharAnim when CharAnim.UseSkyrim is true.\n"
               "return {\n" + ",\n".join(items) + "\n}\n")
        mname = ("Clips_SkyP_%s" if mapfile else "Clips_Sky%s") % style
        open(os.path.join(outdir, mname + ".lua"), "w").write(src)
        print("wrote", mname, len(items), "clips", len(src), "bytes")
    old = {}
    mp = os.path.join(outdir, "Sky_markers.json")
    if os.path.exists(mp):
        old = json.load(open(mp))
    old.update(markers)
    json.dump(old, open(mp, "w"), indent=1)
    if rnd:
        rp = os.path.join(outdir, "renders.json")
        allr = json.load(open(rp)) if os.path.exists(rp) else {}
        allr.update(renders)
        json.dump(allr, open(rp, "w"))


if __name__ == "__main__":
    main()
