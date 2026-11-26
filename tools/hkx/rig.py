# R15-proportioned armature for Soulbound clip authoring (Blender 5.x).
# Bones are named after the R15 Motor6D that drives the part, so exported data maps 1:1.
# Coordinates below are ROBLOX space (studs, HRP origin, X right, Y up, -Z forward);
# rb2bl() converts to Blender space (character faces -Y, Z up).
import bpy
from mathutils import Vector, Matrix

# joint: (parent, pivot_rbx, tail_rbx, part box size (x,y,z) and centre for preview mesh)
J = {
    "Root":          (None,            (0, -1.0, 0), (0, -0.8, 0), (2.0, 0.4, 1.0), (0, -1.0, 0)),
    "Waist":         ("Root",          (0, -0.8, 0), (0, 0.8, 0),  (2.0, 1.6, 1.0), (0, 0.0, 0)),
    "Neck":          ("Waist",         (0, 0.8, 0),  (0, 2.0, 0),  (1.2, 1.2, 1.2), (0, 1.4, 0)),
    "RightShoulder": ("Waist",         (1.0, 0.55, 0), (1.5, -0.35, 0), (1.0, 1.1, 1.0), (1.5, 0.05, 0)),
    "RightElbow":    ("RightShoulder", (1.5, -0.35, 0), (1.5, -1.35, 0), (0.9, 1.0, 0.9), (1.5, -0.85, 0)),
    "RightWrist":    ("RightElbow",    (1.5, -1.35, 0), (1.5, -1.7, 0), (0.9, 0.35, 0.9), (1.5, -1.52, 0)),
    "LeftShoulder":  ("Waist",         (-1.0, 0.55, 0), (-1.5, -0.35, 0), (1.0, 1.1, 1.0), (-1.5, 0.05, 0)),
    "LeftElbow":     ("LeftShoulder",  (-1.5, -0.35, 0), (-1.5, -1.35, 0), (0.9, 1.0, 0.9), (-1.5, -0.85, 0)),
    "LeftWrist":     ("LeftElbow",     (-1.5, -1.35, 0), (-1.5, -1.7, 0), (0.9, 0.35, 0.9), (-1.5, -1.52, 0)),
    "RightHip":      ("Root",          (0.5, -1.2, 0), (0.5, -2.0, 0), (1.0, 0.85, 1.0), (0.5, -1.6, 0)),
    "RightKnee":     ("RightHip",      (0.5, -2.0, 0), (0.5, -2.75, 0), (0.95, 0.8, 0.95), (0.5, -2.37, 0)),
    "RightAnkle":    ("RightKnee",     (0.5, -2.75, 0), (0.5, -2.95, -0.6), (1.0, 0.25, 1.2), (0.5, -2.88, -0.1)),
    "LeftHip":       ("Root",          (-0.5, -1.2, 0), (-0.5, -2.0, 0), (1.0, 0.85, 1.0), (-0.5, -1.6, 0)),
    "LeftKnee":      ("LeftHip",       (-0.5, -2.0, 0), (-0.5, -2.75, 0), (0.95, 0.8, 0.95), (-0.5, -2.37, 0)),
    "LeftAnkle":     ("LeftKnee",      (-0.5, -2.75, 0), (-0.5, -2.95, -0.6), (1.0, 0.25, 1.2), (-0.5, -2.88, -0.1)),
}
ORDER = list(J.keys())

# Roblox -> Blender axis change (proper rotation): bx = -rx, by = rz, bz = ry
C = Matrix(((-1, 0, 0), (0, 0, 1), (0, 1, 0)))  # maps rbx vec -> bl vec
CT = C.transposed()


def rb2bl(v):
    return C @ Vector(v)


def build(name="R15"):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    arm = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for j in ORDER:
        par, piv, tail, _, _ = J[j]
        b = arm.edit_bones.new(j)
        b.head = rb2bl(piv)
        b.tail = rb2bl(tail)
        b.roll = 0
        if par:
            b.parent = arm.edit_bones[par]
            b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in ob.pose.bones:
        pb.rotation_mode = "QUATERNION"
    # preview boxes (for contact-sheet renders)
    mat = bpy.data.materials.new("skin")
    mat.diffuse_color = (0.85, 0.7, 0.55, 1)
    mat2 = bpy.data.materials.new("cloth")
    mat2.diffuse_color = (0.2, 0.35, 0.8, 1)
    for j in ORDER:
        _, piv, _, size, centre = J[j]
        bpy.ops.mesh.primitive_cube_add(size=1)
        box = bpy.context.active_object
        box.name = "box_" + j
        box.scale = (size[0], size[2], size[1])  # bl axes: x, y(depth), z(up)
        box.location = rb2bl(centre)
        col = {"Waist": (0.2, 0.35, 0.85), "Root": (0.15, 0.15, 0.2), "Neck": (0.95, 0.8, 0.3)}.get(j)
        if not col:
            col = (0.9, 0.45, 0.2) if j.startswith("Right") else (0.3, 0.75, 0.35)
        m = bpy.data.materials.new("m_" + j); m.diffuse_color = (*col, 1)
        box.data.materials.append(m)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        mw = box.matrix_world.copy()
        box.parent = ob
        box.parent_type = "BONE"
        box.parent_bone = j
        box.matrix_world = mw
    return ob
