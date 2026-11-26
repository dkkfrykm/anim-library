# Skyrim SE HKX -> Soulbound R15 clip converter (runs inside Blender for mathutils + contact-sheet renders).
# Run:
#   blender --background --python sky2r15.py -- --module SkyrimTest --clip <anim.hkx>=<ClipName> [--clip ...]
#           [--render ClipName] [--out <dir>]
# Retarget: world-space rotation deltas, rest-pose aligned. For each R15 part j driven by Skyrim bone s:
#   P_j(t) = S_s(t) * S_s(bind)^-1 * Corr_j        (all in Roblox character space, X right, Y up, -Z forward)
# Corr_j = two-vector alignment taking the R15 rest part frame onto the Skyrim bind bone frame (bone direction
# primary; facing / blade secondary). Joint Transform = P_parent^-1 * P_j, decomposed as CFrame.Angles(x,y,z),
# then decimated and encoded exactly like soulbound/anim/build.py.
import bpy, sys, os, math, json
from mathutils import Matrix, Quaternion, Vector

TOOLS = os.path.dirname(os.path.abspath(__file__))
ANIM = os.environ.get("R15_RIG_DIR") or TOOLS  # rig.py (R15 joint layout) ships next to this script
sys.path.insert(0, TOOLS)
sys.path.insert(0, ANIM)
import hkx
import rig

SKEL = os.environ.get("SKYRIM_SKELETON") or ("C:/Users/mytwo/soulbound/skyrim/src/XP32 Maximum Skeleton Special Extended/Skeleton Rig/HDT/"
        "meshes/actors/character/character assets/skeleton.hkx")
FPS = 60
TOL = 3.5
PTOL = 0.03
K = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))  # Skyrim (X right, Y fwd, Z up) -> Roblox (X right, Y up, -Z fwd)
KT = K.transposed()
LEG_SCALE = 1.55 / 62.8   # studs per Skyrim unit for pelvis offsets (R15 hip->ankle 1.55 / Skyrim 62.8)
BODY_SCALE = 5.0 / 128.0  # studs per Skyrim unit for whole-body travel (height ratio)

# R15 joint -> (Skyrim bone prefix, child prefix for direction or None, secondary kind)
MAP = {
    "Root": ("NPC Pelvis", None, None),
    "Waist": ("NPC Spine2", None, None),
    "Neck": ("NPC Head", None, None),
    "RightShoulder": ("NPC R UpperArm", "NPC R Forearm", "front"),
    "RightElbow": ("NPC R Forearm", "NPC R Hand", "front"),
    "RightWrist": ("NPC R Hand", "NPC R Finger20", "bladeR"),
    "LeftShoulder": ("NPC L UpperArm", "NPC L Forearm", "front"),
    "LeftElbow": ("NPC L Forearm", "NPC L Hand", "front"),
    "LeftWrist": ("NPC L Hand", "NPC L Finger20", "bladeL"),
    "RightHip": ("NPC R Thigh", "NPC R Calf", "front"),
    "RightKnee": ("NPC R Calf", "NPC R Foot", "front"),
    "RightAnkle": ("NPC R Foot", "NPC R Toe0", "up"),
    "LeftHip": ("NPC L Thigh", "NPC L Calf", "front"),
    "LeftKnee": ("NPC L Calf", "NPC L Foot", "front"),
    "LeftAnkle": ("NPC L Foot", "NPC L Toe0", "up"),
}
SHORT = {"Root": "Rt", "Waist": "W", "Neck": "N", "RightShoulder": "RS", "RightElbow": "RE", "RightWrist": "RW",
         "LeftShoulder": "LS", "LeftElbow": "LE", "LeftWrist": "LW", "RightHip": "RH", "RightKnee": "RK",
         "RightAnkle": "RA", "LeftHip": "LH", "LeftKnee": "LK", "LeftAnkle": "LA"}


def q_of(x):  # json/hkx (x,y,z,w) -> mathutils
    return Quaternion((x[3], x[0], x[1], x[2]))


# ------------------------------------------------------------------------ source clip
class Source:
    def __init__(self, path, skel):
        r = hkx.load(path)
        a = r["anims"][0]
        self.anim = a
        self.frames = hkx.sample_frames(a)
        self.n = a["numFrames"]
        self.fd = a["frameDuration"]
        self.duration = a["duration"]
        t2b = r["bindings"][0]["t2b"] or list(range(a["ntt"]))
        self.t2b = t2b
        self.sk = skel
        self.anns = sorted((t, s) for _, l in a["annotations"] for t, s in l if s)
        names = skel["bones"]
        self.idx = {}
        for i, nm in enumerate(names):
            self.idx.setdefault(nm.split(" [")[0], i)

    def local(self, ft):
        """local (Vector t, Quaternion q) per skeleton bone at fractional source frame ft"""
        sk = self.sk
        loc = [(Vector(r["t"]), q_of(r["q"])) for r in sk["ref"]]
        f0 = max(0, min(self.n - 1, int(math.floor(ft))))
        f1 = min(self.n - 1, f0 + 1)
        u = max(0.0, min(1.0, ft - f0))
        A, B = self.frames[f0], self.frames[f1]
        for ti, bi in enumerate(self.t2b):
            if bi < 0 or bi >= len(loc):
                continue
            ta, qa, _ = A[ti]; tb, qb, _ = B[ti]
            t = Vector(ta).lerp(Vector(tb), u)
            q = q_of(qa).slerp(q_of(qb), u) if u > 0 else q_of(qa)
            loc[bi] = (t, q)
        return loc

    def world(self, loc):
        par = self.sk["parents"]
        W = [None] * len(loc)
        for i, (t, q) in enumerate(loc):
            p = par[i]
            if p < 0:
                W[i] = (t.copy(), q.copy())
            else:
                pt, pq = W[p]
                W[i] = (pt + pq @ t, pq @ q)
        return W

    def bind_world(self):
        return self.world([(Vector(r["t"]), q_of(r["q"])) for r in self.sk["ref"]])

    def world_at(self, ft):
        return self.world(self.local(ft))


def basis(a, b):
    u = a.normalized()
    v = (b - u * b.dot(u)).normalized()
    w = u.cross(v)
    return Matrix((u, v, w)).transposed()  # columns u, v, w


def rbx_rot(q):
    return K @ q.to_matrix() @ KT


def rbx_vec(v):
    return K @ v


class Retarget:
    def __init__(self, src):
        self.src = src
        B = src.bind_world()
        self.B = B
        I = src.idx
        self.bindInv = {}
        self.corr = {}
        wq = B[I["Weapon"]][1]
        bladeR = rbx_vec(wq @ Vector((0, 1, 0)))
        bladeL = Vector((-bladeR.x, bladeR.y, bladeR.z))
        for j, (bn, child, sec) in MAP.items():
            S = rbx_rot(B[I[bn]][1])
            self.bindInv[j] = S.inverted()
            if child is None:
                self.corr[j] = Matrix.Identity(3)
                continue
            par, piv, tail = rig.J[j][0], rig.J[j][1], rig.J[j][2]
            rdir = Vector(tail) - Vector(piv)
            sdir = rbx_vec(B[I[child]][0] - B[I[bn]][0])
            if sec == "front":
                rs, ss = Vector((0, 0, -1)), Vector((0, 0, -1))
            elif sec == "up":
                rs, ss = Vector((0, 1, 0)), Vector((0, 1, 0))
            else:
                rs, ss = Vector((0, 0, -1)), (bladeR if sec == "bladeR" else bladeL)
            self.corr[j] = basis(sdir, ss) @ basis(rdir, rs).transposed()
        self.pelvis0 = rbx_vec(B[I["NPC Pelvis"]][0])

    def pose(self, ft):
        src = self.src
        W = src.world_at(ft)
        I = src.idx
        P = {}
        for j, (bn, _, _) in MAP.items():
            P[j] = rbx_rot(W[I[bn]][1]) @ self.bindInv[j] @ self.corr[j]
        row = {}
        for j in rig.ORDER:
            par = rig.J[j][0]
            T = (P[par].transposed() @ P[j]) if par else P[j]
            m = T
            b = math.asin(max(-1, min(1, m[0][2])))
            a = math.atan2(-m[1][2], m[2][2])
            c = math.atan2(-m[0][1], m[0][0])
            row[j] = (math.degrees(a), math.degrees(b), math.degrees(c))
        d = (rbx_vec(W[I["NPC Pelvis"]][0]) - self.pelvis0) * LEG_SCALE
        row["p"] = (d.x, d.y, d.z)
        return row, W


# ------------------------------------------------------------------------ markers from annotations
def markers(src):
    hits, swings, win, ev = [], [], None, []
    motion = []
    for t, s in src.anns:
        sl = s.lower()
        f = int(round(t * FPS))
        if sl == "hitframe":
            hits.append(f)
        elif sl in ("weaponswing", "weaponleftswing"):
            swings.append(f)
        elif sl == "mco_winopen" and win is None:
            win = f
        elif sl.startswith("animmotion"):
            try:
                motion.append((round(t, 3),) + tuple(float(x) for x in s.split()[1:4]))
            except ValueError:
                pass
        ev.append((round(t, 3), s))
    n = int(round(src.duration * FPS))
    hits = sorted(set(hits))
    w = swings[0] if swings else (max(0, hits[0] - 5) if hits else 0)
    if hits and w >= hits[0]:
        w = max(0, hits[0] - 3)
    last = hits[-1] if hits else w
    r = win if (win and win > last) else min(n, last + 18)
    r = min(r, n)
    return dict(n=n, w=w, i=hits, r=r, sw=sorted(set(swings)), motion=motion, events=ev)


# ------------------------------------------------------------------------ encoding (mirrors build.py)
ALPHA = "".join(chr(c) for c in range(35, 127) if chr(c) != "]")


def e1(v):
    a = ((v + 180) % 360) - 180
    return ALPHA[max(0, min(90, int(round((a + 180) / 4))))]


def e2(v):
    v = max(0, min(91 * 91 - 1, int(v)))
    return ALPHA[v // 91] + ALPHA[v % 91]


def decimate_series(vals, force, tol):
    n = len(vals)
    keep = [0]
    s = 0
    dims = len(vals[0])
    while s < n - 1:
        best = s + 1
        e = s + 2
        while e < n:
            ok = True
            for m in range(s + 1, e):
                t = (m - s) / (e - s)
                for ax in range(dims):
                    v = vals[s][ax] + (vals[e][ax] - vals[s][ax]) * t
                    if abs(v - vals[m][ax]) > tol:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
            if any(abs(vals[e][ax] - vals[s][ax]) > 80 for ax in range(dims)):
                break
            best = e
            if e in force:
                break
            e += 1
        if any(s < f < best for f in force):
            best = min(f for f in force if s < f < best)
        keep.append(best)
        s = best
    return keep


def unwrap(vals):  # keep euler series continuous for decimation (encoder wraps anyway)
    out = [list(vals[0])]
    for v in vals[1:]:
        o = list(v)
        for k in range(3):
            while o[k] - out[-1][k] > 180: o[k] -= 360
            while o[k] - out[-1][k] < -180: o[k] += 360
        out.append(o)
    return out


def lua_clip(name, mk, frames):
    force = set(mk["i"]) | {mk["w"], mk["r"], mk["n"]}
    parts = []
    for j in rig.ORDER:
        vals = unwrap([frames[k][j] for k in range(len(frames))])
        if all(abs(v[0]) < 0.6 and abs(v[1]) < 0.6 and abs(v[2]) < 0.6 for v in vals):
            continue
        ks = decimate_series(vals, force, TOL)
        # 1-char frame delta caps at 90: split long gaps
        parts.append("%s=[[%s]]" % (SHORT[j], enc_keys(ks, lambda k: e1(vals[k][0]) + e1(vals[k][1]) + e1(vals[k][2]))))
    pv = [frames[k]["p"] for k in range(len(frames))]
    if any(abs(x) > 0.01 for v in pv for x in v):
        ks = decimate_series(pv, force, PTOL)
        parts.append("p=[[%s]]" % enc_keys(ks, lambda k: e2(pv[k][0] * 100 + 4000) + e2(pv[k][1] * 100 + 4000) + e2(pv[k][2] * 100 + 4000)))
    meta = "n=%d,w=%d,i={%s},r=%d" % (mk["n"], mk["w"], ",".join(str(i) for i in mk["i"]), mk["r"])
    if mk["sw"]:
        meta += ",sw={%s}" % ",".join(str(i) for i in mk["sw"])
    return "%s={%s,%s}" % (name, meta, ",".join(parts))


def enc_keys(ks, val):
    out = []
    prev = 0
    for n, k in enumerate(ks):
        d = k - prev if n else k
        while d > 90:  # never happens for < 1.5 s gaps; insert a hold key if it does
            out.append(ALPHA[90] + val(prev)); d -= 90; prev += 90
        out.append(ALPHA[d] + val(k))
        prev = k
    return "".join(out)


# ------------------------------------------------------------------------ convert
def convert(path, skel):
    src = Source(path, skel)
    rt = Retarget(src)
    mk = markers(src)
    frames, worlds = [], []
    for f in range(mk["n"] + 1):
        ft = min(src.n - 1, (f / FPS) / src.fd)
        row, W = rt.pose(ft)
        frames.append(row)
        worlds.append(W)
    refine_hits(src, mk, worlds)
    return src, rt, mk, frames, worlds


def refine_hits(src, mk, worlds):
    """Skyrim 'Hitframe' opens hit detection, usually just BEFORE the visible strike. Soulbound's impact marker
    should be the visible contact: move each hit to the frame of peak strike-point speed in [hit-3, hit+12]."""
    I = src.idx
    def pts(W):
        wt, wq = W[I["Weapon"]]
        out = [wt + wq @ Vector((0, 60, 0))]
        for b in ("NPC R Hand", "NPC L Hand", "NPC R Foot", "NPC L Foot"):
            out.append(W[I[b]][0])
        return out
    P = [pts(W) for W in worlds]
    def speed(f):
        if f <= 0 or f >= len(P):
            return 0.0
        return max((a - b).length for a, b in zip(P[f], P[f - 1]))
    mk["hit_raw"] = list(mk["i"])
    new = []
    for h in mk["i"]:
        lo, hi = max(1, h - 3), min(len(P) - 1, h + 12)
        best = max(range(lo, hi + 1), key=speed) if hi >= lo else h
        new.append(best)
    if new:
        mk["i"] = sorted(set(new))
        if mk["w"] >= mk["i"][0]:
            mk["w"] = max(0, mk["i"][0] - 3)
        if mk["r"] <= mk["i"][-1]:
            mk["r"] = min(mk["n"], mk["i"][-1] + 6)


# ------------------------------------------------------------------------ preview render
STICK = [("NPC Pelvis", "NPC Spine"), ("NPC Spine", "NPC Spine1"), ("NPC Spine1", "NPC Spine2"), ("NPC Spine2", "NPC Neck"),
         ("NPC Neck", "NPC Head"), ("NPC Spine2", "NPC R Clavicle"), ("NPC R Clavicle", "NPC R UpperArm"),
         ("NPC R UpperArm", "NPC R Forearm"), ("NPC R Forearm", "NPC R Hand"), ("NPC R Hand", "NPC R Finger20"),
         ("NPC Spine2", "NPC L Clavicle"), ("NPC L Clavicle", "NPC L UpperArm"), ("NPC L UpperArm", "NPC L Forearm"),
         ("NPC L Forearm", "NPC L Hand"), ("NPC L Hand", "NPC L Finger20"), ("NPC Pelvis", "NPC R Thigh"),
         ("NPC R Thigh", "NPC R Calf"), ("NPC R Calf", "NPC R Foot"), ("NPC R Foot", "NPC R Toe0"),
         ("NPC Pelvis", "NPC L Thigh"), ("NPC L Thigh", "NPC L Calf"), ("NPC L Calf", "NPC L Foot"), ("NPC L Foot", "NPC L Toe0")]
STICK_OFF = Vector((-4.5, -3.0, 0))  # rbx offset of the Skyrim figure (left of the R15), feet on y=-3


def rb_euler_to_local(REST, j, e):
    x, y, z = (math.radians(a) for a in e)
    Rrb = Matrix.Rotation(x, 3, "X") @ Matrix.Rotation(y, 3, "Y") @ Matrix.Rotation(z, 3, "Z")
    Rbl = rig.C @ Rrb @ rig.CT
    Rb = REST[j]
    return (Rb.inverted() @ Rbl @ Rb).to_quaternion()


def setup_scene():
    ob = rig.build()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 420
    scene.render.resolution_y = 300
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    cam.data.lens = 35
    scene.camera = cam
    steel = bpy.data.materials.new("steel"); steel.diffuse_color = (0.7, 0.9, 1.0, 1)
    bpy.ops.mesh.primitive_cube_add(size=1)
    bl = bpy.context.active_object
    bl.scale = (0.12, 3.4, 0.35)
    bl.location = rig.rb2bl((1.5, -1.6, -1.9))
    bl.data.materials.append(steel)
    mw = bl.matrix_world.copy()
    bl.parent = ob; bl.parent_type = "BONE"; bl.parent_bone = "RightWrist"; bl.matrix_world = mw
    dark = bpy.data.materials.new("dark"); dark.diffuse_color = (0.05, 0.05, 0.05, 1)
    bpy.ops.mesh.primitive_cube_add(size=1)
    nose = bpy.context.active_object
    nose.data.materials.append(dark)
    nose.scale = (0.3, 0.3, 0.3)
    nose.location = rig.rb2bl((0, 1.4, -0.65))
    mw = nose.matrix_world.copy()
    nose.parent = ob; nose.parent_type = "BONE"; nose.parent_bone = "Neck"; nose.matrix_world = mw
    bpy.ops.mesh.primitive_plane_add(size=30, location=rig.rb2bl((2, -3.0, 0)))
    gm = bpy.data.materials.new("ground"); gm.diffuse_color = (0.55, 0.55, 0.5, 1)
    bpy.context.active_object.data.materials.append(gm)
    for pb in ob.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return ob


def seg(a, b, r, mat, coll):
    d = b - a
    L = d.length
    if L < 1e-4:
        return
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=L, location=(a + b) / 2, vertices=8)
    o = bpy.context.active_object
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = d.to_track_quat("Z", "Y")
    o.data.materials.append(mat)
    for c in o.users_collection:
        c.objects.unlink(o)
    coll.objects.link(o)


def draw_stick(src, W, coll, mats, off=None):
    off = STICK_OFF if off is None else off
    I = src.idx
    def P(name):
        v = rbx_vec(W[I[name]][0]) * BODY_SCALE + off
        return rig.rb2bl(v)
    for a, b in STICK:
        side = " R " in a + b
        side_l = " L " in a + b
        seg(P(a), P(b), 0.09, mats["r"] if side else mats["l"] if side_l else mats["c"], coll)
    h = P("NPC Head")
    seg(h, h + (h - P("NPC Neck")).normalized() * 0.5, 0.25, mats["c"], coll)
    # sword along Weapon +Y (~80 Skyrim units)
    wt, wq = W[I["Weapon"]]
    a = rig.rb2bl(rbx_vec(wt) * BODY_SCALE + off)
    b = rig.rb2bl(rbx_vec(wt + wq @ Vector((0, 80, 0))) * BODY_SCALE + off)
    seg(a, b, 0.06, mats["s"], coll)


def place_cam(cam, pos, target):
    cam.location = rig.rb2bl(pos)
    d = rig.rb2bl(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render(name, src, rt, mk, frames, worlds, outdir):
    ob = setup_scene()
    REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
    REST_HEAD = {b.name: b.head_local.copy() for b in ob.data.bones}
    scene = bpy.context.scene
    coll = bpy.data.collections.new("stick"); scene.collection.children.link(coll)
    mats = {}
    for k, c in (("r", (0.9, 0.45, 0.2)), ("l", (0.3, 0.75, 0.35)), ("c", (0.85, 0.8, 0.75)), ("s", (0.7, 0.9, 1.0))):
        m = bpy.data.materials.new("st_" + k); m.diffuse_color = (*c, 1); mats[k] = m
    imp = mk["i"][0] if mk["i"] else mk["w"]
    picks = sorted(set([0, mk["w"], imp, min(mk["n"], imp + 6), min(mk["n"], (imp + mk["r"]) // 2), mk["r"]]))
    if len(picks) < 6:
        picks = sorted(set(picks + [min(mk["n"], mk["r"] + 12), max(0, mk["w"] // 2)]))[:7]
    cams = [((-4.0, 1.5, -19.0), (-2.25, -0.6, 0)), ((13.0, 0.5, 0.0), (0.0, -0.8, 0.0))]
    out = []
    for f in picks:
        row = frames[f]
        for j in rig.ORDER:
            ob.pose.bones[j].rotation_quaternion = rb_euler_to_local(REST, j, row[j])
        pr = ob.pose.bones["Root"]
        pr.location = REST["Root"].inverted() @ (rig.C @ Vector(row["p"]))
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        draw_stick(src, worlds[f], coll, mats)
        draw_stick(src, worlds[f], coll, mats, Vector((0, -1.0, 0)) - rt.pelvis0 * BODY_SCALE)
        bpy.context.view_layer.update()
        pair = []
        for ci, (cp, tg) in enumerate(cams):
            place_cam(scene.camera, cp, tg)
            p = os.path.join(outdir, "%s_%03d_%d.png" % (name, f, ci))
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            pair.append(p)
        out.append((f, pair))
    return out


# ------------------------------------------------------------------------ main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    clips, module, rnd, outdir = [], "SkyrimTest", set(), "C:/Users/mytwo/soulbound/skyrim/out"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--clip":
            p, n = argv[i + 1].rsplit("=", 1); clips.append((p, n)); i += 2
        elif a == "--clips":  # json list of [path, name]
            clips += [tuple(x) for x in json.load(open(argv[i + 1]))]; i += 2
        elif a == "--module":
            module = argv[i + 1]; i += 2
        elif a == "--render":
            rnd |= set(argv[i + 1].split(",")); i += 2
        elif a == "--out":
            outdir = argv[i + 1]; i += 2
        else:
            i += 1
    skel = hkx.load(SKEL)["skeletons"][0]
    items, meta, renders = [], {}, {}
    rdir = os.path.join(outdir, "renders"); os.makedirs(rdir, exist_ok=True)
    for path, name in clips:
        src, rt, mk, frames, worlds = convert(path, skel)
        items.append(lua_clip(name, mk, frames))
        meta[name] = dict(src=path, src_frames=src.n, src_fps=round(1 / src.fd, 3), duration=round(src.duration, 3),
                          n=mk["n"], w=mk["w"], i=mk["i"], hit_raw=mk.get("hit_raw"), r=mk["r"], sw=mk["sw"], motion=mk["motion"],
                          motion_studs=[(m[0], round(m[1] * BODY_SCALE, 2), round(m[2] * BODY_SCALE, 2), round(m[3] * BODY_SCALE, 2)) for m in mk["motion"]],
                          events=mk["events"])
        if name in rnd or "all" in rnd:
            renders[name] = render(name, src, rt, mk, frames, worlds, rdir)
            json.dump({"frames": frames}, open(os.path.join(outdir, name + "_frames.json"), "w"))
        print("converted", name, "n=%d w=%d i=%s r=%d" % (mk["n"], mk["w"], mk["i"], mk["r"]))
    src_txt = ("-- AUTO-GENERATED by soulbound/skyrim/tools/sky2r15.py from Skyrim SE HKX (retargeted, baked @60, decimated).\n"
               "-- Same format as anim/build.py: n=frames@60, w=windup end (WeaponSwing), i=impacts (Hitframe), r=recover (MCO_WinOpen),\n"
               "-- sw=swing frames (SFX keys). Joints: 1-char frame delta + 3x 1-char angle; p: delta + 3x 2-char centistuds+4000.\n"
               "return {\n" + ",\n".join(items) + "\n}\n")
    with open(os.path.join(outdir, "Clips_%s.lua" % module), "w") as fh:
        fh.write(src_txt)
    json.dump(meta, open(os.path.join(outdir, "Clips_%s.meta.json" % module), "w"), indent=1)
    json.dump(renders, open(os.path.join(outdir, "renders_%s.json" % module), "w"))
    print("wrote module", module, len(items), "clips", len(src_txt), "bytes")


if __name__ == "__main__":
    main()
