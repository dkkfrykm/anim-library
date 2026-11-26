# Side + front view renders of a power's M1 chain (and optional extra clips) from phase4 rows.json -> PNG frames,
# then out/phase4/video_<pid>.mp4 is encoded by encode_vid.py (system python, cv2).
# Run: blender --background --python chainvid.py -- --powers karate,boxer --clips M1_1,M1_2,M1_3,M1_4,Blast
import bpy, sys, os, math, json
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky2r15 as S
rig = S.rig
D = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "C:/Users/mytwo/harrow/anim/out/phase4"
argv = sys.argv[sys.argv.index("--") + 1:]
powers = argv[argv.index("--powers") + 1].split(",")
clips = argv[argv.index("--clips") + 1].split(",") if "--clips" in argv else ["M1_1", "M1_2", "M1_3", "M1_4"]
rows = json.load(open(os.path.join(D, "rows.json")))
ob = S.setup_scene()
sc = bpy.context.scene
sc.render.resolution_x = 360; sc.render.resolution_y = 320
REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
cams = {"side": ((10.5, 0.4, -1.5), (0, -0.8, -0.8)), "front": ((0.0, 0.6, -10.5), (0, -0.6, 0)), "q34": ((6.5, 0.9, -7.5), (0, -0.5, 0))}
for pid in powers:
    fdir = os.path.join(D, "vid_" + pid); os.makedirs(fdir, exist_ok=True)
    k = 0
    MK = json.load(open(os.path.join(D, "markers.json"))) if os.path.exists(os.path.join(D, "markers.json")) else {}
    segs = []
    for cl in clips:
        name = "Sky_%s_%s" % (pid, cl)
        if name not in rows:
            continue
        R = rows[name]
        n = len(R)
        last = (MK[name]["n"] + 1) if name in MK else min(n, 60)  # main clip only (loop frames after n skipped)
        segs.append((cl, k))
        for f in range(0, last, 2):
            row = R[f]
            for j in rig.ORDER:
                ob.pose.bones[j].rotation_quaternion = S.rb_euler_to_local(REST, j, row[j])
            ob.pose.bones["Root"].location = REST["Root"].inverted() @ (rig.C @ Vector(row["p"]))
            bpy.context.view_layer.update()
            for cname, (cp, tg) in cams.items():
                S.place_cam(sc.camera, cp, tg)
                sc.render.filepath = os.path.join(fdir, "%s_%04d.png" % (cname, k))
                bpy.ops.render.render(write_still=True)
            k += 1
    json.dump({"frames": k, "clips": clips, "segs": segs}, open(os.path.join(fdir, "info.json"), "w"))
