# Blender authoring template: R15 rig + slot timeline markers + NLA tracks of chosen HKX components, plus (optionally)
# an existing phase-6 clip baked as the editable action, for hand refinement in the Graph Editor.
# Run: blender --background --python make_template.py -- [--slot M1] [--clip Sky_karate_M1_1] [--foot <component id>]
#        [--torso <component id>] [--strike <component id>] [--out out/template/r15_authoring.blend]
# Export back: rows from the "Authored" action -> phase2.lua_clip (see phase6.py) or keep the .blend as a reference.
import bpy, sys, os, json
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase5 as P5
import components6 as CL
P2, S, rig = P5.P2, P5.S, P5.rig
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def bake(ob, REST, rows, name):
    act = bpy.data.actions.new(name)
    ob.animation_data_create()
    ob.animation_data.action = act
    for f, row in enumerate(rows):
        for j in rig.ORDER:
            pb = ob.pose.bones[j]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = S.rb_euler_to_local(REST, j, row[j])
            pb.keyframe_insert("rotation_quaternion", frame=f)
        ob.pose.bones["Root"].location = REST["Root"].inverted() @ (rig.C @ Vector(row["p"]))
        ob.pose.bones["Root"].keyframe_insert("location", frame=f)
    return act


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k, d=None: argv[argv.index(k) + 1] if k in argv else d
    slot = opt("--slot", "M1")
    out = os.path.abspath(opt("--out", os.path.join(ROOT, "out", "template", "r15_authoring.blend")))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ob = S.setup_scene()
    REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
    sc = bpy.context.scene
    n, w, i, r, la = P2.SLOT.get(slot, P2.SLOT["M1"])
    sc.frame_start, sc.frame_end, sc.render.fps = 0, n, 60
    for nm, f in (("windup w", w), ("IMPACT i", i), ("hold end", i + P2.HOLD), ("recover r", r), ("end n", n)):
        sc.timeline_markers.new(nm, frame=f)
    skel = S.hkx.load(S.SKEL)["skeletons"][0]
    comps = json.load(open(os.path.join(ROOT, "out", "catalog", "components.json")))
    byid = {c["id"]: c for c in comps}
    picks = {"footwork": opt("--foot"), "torso": opt("--torso"), "strike": opt("--strike")}
    if not any(picks.values()):  # sensible defaults so the template is never empty
        picks = {"footwork": CL.pick("footwork", need=["advance", "attack"])[0]["id"],
                 "torso": CL.pick("torso", need=["attack", "twist"])[0]["id"],
                 "strike": CL.pick("arm_R", need=["attack"])[0]["id"]}
    ob.animation_data_create()
    for part, cid in picks.items():
        if not cid:
            continue
        c = byid[cid]
        P2.SRCPATH[cid] = c["source"]
        clip = P2.Clip("tmpl_" + part, cid, slot if slot in P2.SLOT else "M1", {"loop": False}, skel)
        clip.si = max(2, min(clip.send - 2, int(c["anchor"])))
        rows = []
        for f in range(n + 1):
            Pm, p, _ = clip.sample(clip.warp(f))
            rows.append(P2.to_rows(Pm, p))
        act = bake(ob, REST, rows, "%s: %s" % (part, os.path.basename(c["source"])))
        tr = ob.animation_data.nla_tracks.new()
        tr.name = part
        tr.strips.new(act.name, 0, act)
        tr.mute = part != "footwork"
        ob.animation_data.action = None
    if opt("--clip"):
        rows_all = json.load(open(os.path.join(ROOT, "out", "phase6", "rows.json")))
        rows = rows_all[opt("--clip")]
        bake(ob, REST, rows[:n + 1], "Authored")
    else:
        ob.animation_data.action = bpy.data.actions.new("Authored")
    meta = dict(slot=slot, markers=dict(n=n, w=w, i=i, r=r), components=picks, clip=opt("--clip"))
    txt = bpy.data.texts.new("README_template")
    txt.write("R15 authoring template\n" + json.dumps(meta, indent=1) +
              "\nNLA tracks = HKX components (footwork/torso/strike), unmute to compare. Edit the 'Authored' action;"
              "\nkeep impact on marker i. Export rows with phase6/phase2 helpers.\n")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("template ->", out, meta)


if __name__ == "__main__":
    main()
