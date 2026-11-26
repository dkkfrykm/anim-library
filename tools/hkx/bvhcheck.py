import bpy, sys, math
argv = sys.argv[sys.argv.index("--") + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_anim.bvh(filepath=argv[0], axis_forward="-Z", axis_up="Y", global_scale=0.01, update_scene_fps=True, update_scene_duration=True)
ob = bpy.context.selected_objects[0]
sc = bpy.context.scene
print("bones", len(ob.data.bones), "frames", sc.frame_start, sc.frame_end)
sc.render.engine = "BLENDER_WORKBENCH"; sc.render.resolution_x = 320; sc.render.resolution_y = 320
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (2.2, -2.6, 1.2); cam.rotation_euler = (math.radians(80), 0, math.radians(40))
ob.data.display_type = "STICK"
sc.display.shading.show_xray = False
import mathutils
for k, f in enumerate([sc.frame_start, (sc.frame_start + sc.frame_end) // 2, sc.frame_end]):
    sc.frame_set(f)
    # bones as cylinders for workbench render
    for o in [o for o in sc.objects if o.name.startswith("seg")]:
        bpy.data.objects.remove(o, do_unlink=True)
    for pb in ob.pose.bones:
        a = ob.matrix_world @ pb.head; b = ob.matrix_world @ pb.tail
        d = b - a
        if d.length < 1e-4: continue
        bpy.ops.mesh.primitive_cylinder_add(radius=0.015, depth=d.length, location=(a + b) / 2, vertices=6)
        o = bpy.context.active_object; o.name = "seg"; o.rotation_mode = "QUATERNION"; o.rotation_quaternion = d.to_track_quat("Z", "Y")
    sc.render.filepath = argv[1] + "_%d.png" % k
    bpy.ops.render.render(write_still=True)
