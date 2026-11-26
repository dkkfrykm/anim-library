# Soulbound clip pipeline: build R15 rig -> keyframe every clip as a Blender action (per-key Penner
# easing, overlap offsets on distal joints) -> bake (sample the evaluated pose) -> export decimated
# Luau tables (one ModuleScript source per style) -> optional contact-sheet renders.
# Run: blender --background --python build.py -- [--render CLIP,CLIP|all] [--only STYLE] [--save]
import bpy, sys, os, math, json, importlib
from mathutils import Matrix, Euler, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rig
importlib.reload(rig)
import clips as CL
importlib.reload(CL)

OUT = os.path.join(HERE, "out")
REN = os.path.join(HERE, "renders")
os.makedirs(OUT, exist_ok=True)
os.makedirs(REN, exist_ok=True)
FPS = 60
TOL = 3.5  # degrees for decimation
PTOL = 0.03  # studs

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else True
    return default

scene = bpy.context.scene
scene.render.fps = FPS
ob = rig.build()
REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
REST_HEAD = {b.name: b.head_local.copy() for b in ob.data.bones}

INTERP = {  # key easing id -> (interpolation, easing)
    "snap": ("EXPO", "EASE_OUT"), "out": ("QUAD", "EASE_OUT"), "in": ("QUAD", "EASE_IN"),
    "io": ("SINE", "EASE_IN_OUT"), "lin": ("LINEAR", "AUTO"), "back": ("BACK", "EASE_OUT"),
    "circ": ("CIRC", "EASE_OUT"), "bez": ("BEZIER", "AUTO"), "hold": ("CONSTANT", "AUTO"),
}


def rb_euler_to_local(j, e):
    x, y, z = (math.radians(a) for a in e)
    Rx = Matrix.Rotation(x, 3, "X"); Ry = Matrix.Rotation(y, 3, "Y"); Rz = Matrix.Rotation(z, 3, "Z")
    Rrb = Rx @ Ry @ Rz  # == Roblox CFrame.Angles(x, y, z)
    Rbl = rig.C @ Rrb @ rig.CT
    Rb = REST[j]
    return (Rb.inverted() @ Rbl @ Rb).to_quaternion()


def fcurves_of(action):
    try:
        return list(action.fcurves)
    except AttributeError:
        pass
    from bpy_extras import anim_utils
    out = []
    for slot in action.slots:
        cb = anim_utils.action_get_channelbag_for_slot(action, slot)
        if cb:
            out += list(cb.fcurves)
    return out


def make_action(name, c):
    ob.animation_data_clear()
    ob.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ob.animation_data.action = act
    for pb in ob.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    keys = c["keys"]
    base = c.get("base", {})
    lag = c.get("lag", CL.LAG)
    nkeys = len(keys)
    easemap = {}  # (joint, frame) -> ease id
    last_q = {}
    for ki, k in enumerate(keys):
        f, pose, ease = k[0], k[1], (k[2] if len(k) > 2 else "bez")
        full = dict(base)
        full.update(pose)
        for j in rig.ORDER:
            e = full.get(j, (0, 0, 0))
            q = rb_euler_to_local(j, e)
            if j in last_q and last_q[j].dot(q) < 0:
                q.negate()  # keep quaternion continuity
            last_q[j] = q
            pb = ob.pose.bones[j]
            pb.rotation_quaternion = q
            fj = f
            if 0 < ki < nkeys - 1:
                fj = f + lag.get(j, 0)
            pb.keyframe_insert("rotation_quaternion", frame=fj)
            easemap[(j, fj)] = ease
        p = full.get("p", (0, 0, 0))
        pr = ob.pose.bones["Root"]
        pr.location = REST["Root"].inverted() @ (rig.C @ Vector(p))
        pr.keyframe_insert("location", frame=f)
        easemap[("Root", f)] = ease
    for fc in fcurves_of(act):
        dp = fc.data_path
        j = dp.split('"')[1]
        for kp in fc.keyframe_points:
            e = easemap.get((j, int(round(kp.co[0]))), "bez")
            it, es = INTERP[e]
            kp.interpolation = it
            kp.easing = es
            if it == "BACK":
                kp.back = c.get("back", 1.4)
        fc.update()
    return act


def m3(pb):
    return pb.matrix.to_3x3()


def bake(c):
    n = c["keys"][-1][0]
    frames = []
    for f in range(0, n + 1):
        scene.frame_set(f)
        D = {}
        for j in rig.ORDER:
            pb = ob.pose.bones[j]
            D[j] = m3(pb) @ REST[j].inverted()
        row = {}
        for j in rig.ORDER:
            par = rig.J[j][0]
            T = (D[par].inverted() @ D[j]) if par else D[j]
            Trb = rig.CT @ T @ rig.C
            # decompose as Rx Ry Rz
            m = Trb
            b = math.asin(max(-1, min(1, m[0][2])))
            a = math.atan2(-m[1][2], m[2][2])
            cc = math.atan2(-m[0][1], m[0][0])
            row[j] = (math.degrees(a), math.degrees(b), math.degrees(cc))
        pr = ob.pose.bones["Root"]
        d = pr.head - REST_HEAD["Root"]  # pose.bones head is armature space
        prb = rig.CT @ d
        row["p"] = (prb.x, prb.y, prb.z)
        frames.append(row)
    return frames


def decimate_series(vals, force, tol):
    # vals: list of tuples per frame; greedy linear-reconstruction decimation
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


ALPHA = "".join(chr(c) for c in range(35, 127) if chr(c) != "]")  # 91 symbols, safe inside [[ ]]


def e1(v):  # angle (deg) -> 1 char, 4 deg steps
    a = ((v + 180) % 360) - 180
    return ALPHA[max(0, min(90, int(round((a + 180) / 4))))]


def e2(v):  # int 0..8280 -> 2 chars
    v = max(0, min(91 * 91 - 1, int(v)))
    return ALPHA[v // 91] + ALPHA[v % 91]


SHORT = {"Root": "Rt", "Waist": "W", "Neck": "N", "RightShoulder": "RS", "RightElbow": "RE", "RightWrist": "RW",
         "LeftShoulder": "LS", "LeftElbow": "LE", "LeftWrist": "LW", "RightHip": "RH", "RightKnee": "RK",
         "RightAnkle": "RA", "LeftHip": "LH", "LeftKnee": "LK", "LeftAnkle": "LA"}


def lua_clip(name, c, frames):
    mk = c.get("mk", {})
    imp = mk.get("impact", [])
    if isinstance(imp, int):
        imp = [imp]
    force = set(imp) | {mk.get("windup", 0), mk.get("recover", 0), c.get("e", 0)}
    if c.get("loop"):
        force |= set(c["loop"])
    parts = []
    for j in rig.ORDER:
        vals = [frames[k][j] for k in range(len(frames))]
        if all(abs(v[0]) < 0.6 and abs(v[1]) < 0.6 and abs(v[2]) < 0.6 for v in vals):
            continue
        ks = decimate_series(vals, force, TOL)
        parts.append("%s=[[%s]]" % (SHORT[j], "".join(ALPHA[k - (ks[n - 1] if n else 0)] + e1(vals[k][0]) + e1(vals[k][1]) + e1(vals[k][2]) for n, k in enumerate(ks))))
    pv = [frames[k]["p"] for k in range(len(frames))]
    if any(abs(x) > 0.01 for v in pv for x in v):
        ks = decimate_series(pv, force, PTOL)
        parts.append("p=[[%s]]" % "".join(ALPHA[k - (ks[n - 1] if n else 0)] + e2(pv[k][0] * 100 + 4000) + e2(pv[k][1] * 100 + 4000) + e2(pv[k][2] * 100 + 4000) for n, k in enumerate(ks)))
    meta = "n=%d,w=%d,i={%s},r=%d" % (c.get("e", len(frames) - 1), mk.get("windup", 0), ",".join(str(i) for i in imp), mk.get("recover", len(frames) - 1))
    if c.get("loop"):
        meta += ",la=%d,lb=%d" % tuple(c["loop"])
    return "%s={%s,%s}" % (name, meta, ",".join(parts))


CAMS = [(4.0, 1.0, -9.0), (9.5, 0.5, 0.5)]


def place_cam(cam, pos):
    cam.location = rig.rb2bl(pos)
    d = rig.rb2bl((0, -0.8, 0)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_render():
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 200
    scene.render.resolution_y = 220
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    place_cam(cam, (4.0, 1.0, -9.0))
    cam_data.lens = 40
    scene.camera = cam
    # facing marker (nose) on the head
    dark = bpy.data.materials.new("dark"); dark.diffuse_color = (0.05, 0.05, 0.05, 1)
    bpy.ops.mesh.primitive_cube_add(size=1)
    nose = bpy.context.active_object
    nose.data.materials.append(dark)
    nose.scale = (0.3, 0.3, 0.3)
    nose.location = rig.rb2bl((0, 1.4, -0.65))
    mw = nose.matrix_world.copy()
    nose.parent = ob; nose.parent_type = "BONE"; nose.parent_bone = "Neck"; nose.matrix_world = mw
    # weapon preview blades (shown for clips with weapon="R"/"RL")
    global BLADES
    BLADES = {}
    steel = bpy.data.materials.new("steel"); steel.diffuse_color = (0.7, 0.9, 1.0, 1)
    for side, x in (("R", 1.5), ("L", -1.5)):
        bpy.ops.mesh.primitive_cube_add(size=1)
        bl = bpy.context.active_object
        bl.scale = (0.12, 3.4, 0.35)  # bl axes: x, y (= rbx z), z (= rbx y)
        bl.location = rig.rb2bl((x, -1.6, -1.9))
        bl.data.materials.append(steel)
        mw = bl.matrix_world.copy()
        bl.parent = ob; bl.parent_type = "BONE"; bl.parent_bone = ("Right" if side == "R" else "Left") + "Wrist"; bl.matrix_world = mw
        BLADES[side] = bl
    # ground
    bpy.ops.mesh.primitive_plane_add(size=14, location=rig.rb2bl((0, -3.0, 0)))


def render_clip(name, c):
    w = c.get("weapon", "")
    for side, bl in BLADES.items():
        bl.hide_render = side not in w
    n = c["keys"][-1][0]
    mk = c.get("mk", {})
    imp = mk.get("impact", [])
    if isinstance(imp, int):
        imp = [imp]
    e = c.get("e", n)
    picks = sorted(set([0, mk.get("windup", 0)] + imp[:3] + [min(e, (imp[0] if imp else 0) + 6), mk.get("recover", e)] + ([c["loop"][0] + 8] if c.get("loop") else [])))
    paths = []
    for f in picks:
        scene.frame_set(f)
        pair = []
        for ci, cp in enumerate(CAMS):
            place_cam(scene.camera, cp)
            p = os.path.join(REN, "%s_%03d_%d.png" % (name, f, ci))
            scene.render.filepath = p
            bpy.ops.render.render(write_still=True)
            pair.append(p)
        paths.append(pair)
    return paths


def main():
    only = arg("--only")
    rnd = arg("--render")
    styles = {}
    renders = {}
    if rnd:
        setup_render()
    for name, c in CL.CLIPS.items():
        style = name.split("_")[0]
        if only and style not in only.split(","):
            continue
        make_action(name, c)
        frames = bake(c)
        styles.setdefault(style, []).append(lua_clip(name, c, frames))
        if rnd and (rnd is True or rnd == "all" or name in rnd.split(",")):
            renders[name] = render_clip(name, c)
    for style, items in styles.items():
        src = "-- AUTO-GENERATED by soulbound/anim/build.py from Blender (baked, decimated). Do not hand edit.\n" \
              "-- per clip: n=frames@60, w=windup end, i=impacts, r=recover end, la/lb=multi-hit loop, t=key frames,\n" \
              "-- joints: per key 1-char frame delta + 3x 1-char angle (4 deg steps, CFrame.Angles XYZ); p: delta + 3x 2-char centistuds+4000; alphabet ASCII 35..126 minus ]. Decoder: Client.CharAnim.\n" \
              "return {\n" + ",\n".join(items) + "\n}\n"
        with open(os.path.join(OUT, "Clips_%s.lua" % style), "w") as fh:
            fh.write(src)
        print("wrote", style, len(items), "clips", len(src), "bytes")
    with open(os.path.join(REN, "index.json"), "w") as fh:
        json.dump(renders, fh)
    if arg("--save"):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "soulbound_clips.blend"))


main()
