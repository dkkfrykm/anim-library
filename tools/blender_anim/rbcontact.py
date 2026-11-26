"""RBCONTACT: hand-contact corrections on the CORR layer (Animator, tools/anim). exec AFTER rbanim.py in the same namespace.
hand_to_bone(cid, side, target_bone, along, offset, f0, f1, ramp=8, pole=None, pole_w=1.0)
  Hand head of <side> ('L'/'R') -> point = target_bone head + along * (target bone's farthest child joint - head) + offset, where offset is
  (right, forward, up) in the BODY frame (Spine2 pose axes: right = +X, forward = +Y, up = +Z; checked: head lies +Y of the neck), Skyrim units
  (= armature units here). Frames f0..f1 inclusive (f1 < f0 wraps), eased in/out over `ramp` frames.
  Elbow: analytic 2-bone IK in the plane toward the current elbow, or toward `pole` = (bone, (right, fwd, up)) blended by pole_w.
  Writes ONLY CORR quaternion keys on UpperArm/Forearm: CORR = BASE^-1 * target_basis (NLA Combine: final = BASE x CORR x POLISH).
  Solved against BASE alone (CORR/POLISH muted while solving), so it can be re-run; BASE is never touched.
arms_cross(cid, specs, f0, f1, ramp=8, iters=2): several arms solved together per frame (each hand follows the other's corrected arm).
  Returns the max hand-position error (u)."""
import bpy, math
from mathutils import Vector, Quaternion, Matrix

def _arm_names(s): return ('NPC %s UpperArm [%sUar]' % (s, s), 'NPC %s Forearm [%sLar]' % (s, s), 'NPC %s Hand [%sHnd]' % (s, s))
def _frames(f0, f1, n): return list(range(f0, f1 + 1)) if f1 >= f0 else list(range(f0, n)) + list(range(0, f1 + 1))
def _weight(i, m, ramp):
    if ramp <= 0: return 1.0
    w = min(1.0, (i + 1) / ramp, (m - i) / ramp); return w * w * (3 - 2 * w)
def _mute(cid, names, mute):
    for t in rig().animation_data.nla_tracks:
        if any(t.name == '%s:%s' % (cid, L) for L in names): t.mute = mute
def _body(pbs):
    M = pbs['NPC Spine2 [Spn2]'].matrix.to_3x3().normalized(); return M.col[0].copy(), M.col[1].copy(), M.col[2].copy()   # Spine2: +X her right, +Y forward (head sits +Y of neck), +Z up
def _armframe(pbs, bone):
    """roll-free frame of an upper arm: Y = arm direction (head -> farthest child joint), Z = body forward orthogonalised, X = Y x Z"""
    tg = pbs[bone]; tip = max(tg.children, key=lambda c: (c.head - tg.head).length).head if tg.children else tg.tail
    y = (tip - tg.head).normalized(); _, fw, _ = _body(pbs); z = (fw - y * fw.dot(y)).normalized(); x = y.cross(z)
    M = Matrix((x, y, z)).transposed(); return M

def _pt(pbs, bone, along, off):
    tg = pbs[bone]; tip = max(tg.children, key=lambda c: (c.head - tg.head).length).head if tg.children else tg.tail
    r, f, u = _body(pbs); return tg.head + (tip - tg.head) * along + r * off[0] + f * off[1] + u * off[2]

LEG = lambda s: ('NPC %s Thigh [%sThg]' % (s, s), 'NPC %s Calf [%sClf]' % (s, s), 'NPC %s Foot [%sft ]' % (s, s))
def solve_frame(a, side, T, P=None, pole_w=1.0, names=None):
    """hinge-exact 2-bone IK: the forearm only FLEXES about its rest-local X (the XPMSSE elbow hinge, verified on 594 handmade clips;
    pose rotation_quaternion = rest^-1 * local, so a pure-X quaternion = zero side-bend/twist). Flex angle by bisection on |S-H| = |S-T|,
    sign kept from BASE; then the upper arm swings S->H onto S->T and rolls about that axis so the elbow lies toward the pole
    (P, blended by pole_w with the current elbow). Returns the hand error (u)."""
    pbs = a.pose.bones; ua_n, fa_n, hd_n = names or _arm_names(side); ua, fa, hd = pbs[ua_n], pbs[fa_n], pbs[hd_n]; vl = bpy.context.view_layer
    S = ua.head.copy(); E0 = fa.head.copy()
    b = fa.rotation_quaternion.copy(); sgn = 1.0 if b.x * b.w >= 0 else -1.0
    def setflex(th): fa.rotation_quaternion = Quaternion((1, 0, 0), sgn * th); vl.update(); return (hd.head - S).length
    d = (T - S).length; lo, hi = math.radians(8), math.radians(150); dmax = setflex(lo); dmin = setflex(hi)   # >= 8 deg flex: never lock straight (elbow plane degenerates -> flips)
    d = min(max(d, dmin), dmax)
    for _ in range(40):
        mid = (lo + hi) / 2
        if setflex(mid) > d: lo = mid
        else: hi = mid
    setflex((lo + hi) / 2)
    H = hd.head.copy(); q1 = (H - S).rotation_difference(T - S)
    ua.matrix = Matrix.Translation(S) @ (q1.to_matrix() @ ua.matrix.to_3x3()).to_4x4(); vl.update()
    ax = (T - S).normalized(); E = fa.head - S; want = (E0 - S) if P is None else (E0 - S).lerp(P - S, pole_w)
    e_p = E - ax * E.dot(ax); w_p = want - ax * want.dot(ax)
    if e_p.length > 1e-6 and w_p.length > 1e-6:
        ang = e_p.angle(w_p); 
        if e_p.cross(w_p).dot(ax) < 0: ang = -ang
        R = Quaternion(ax, ang); ua.matrix = Matrix.Translation(S) @ (R.to_matrix() @ ua.matrix.to_3x3()).to_4x4(); vl.update()
    return (hd.head - T).length

def hand_to_bone(cid, side, target_bone, along, offset, f0, f1, ramp=8, pole=None, pole_w=1.0):
    return arms_cross(cid, [(side, target_bone, along, offset, pole, pole_w)], f0, f1, ramp)

def arms_cross(cid, specs, f0, f1, ramp=8, iters=2):
    a = rig(); n = solo(cid); sc = bpy.context.scene; pbs = a.pose.bones; corr = bpy.data.actions[cid + '_CORR']
    _mute(cid, ('CORR', 'POLISH'), True); frames = _frames(f0, f1, n); res = {}
    for i, f in enumerate(frames):
        sc.frame_set(f); bpy.context.view_layer.update(); w = _weight(i, len(frames), ramp)
        base = {}
        for sp in specs:
            for b in _arm_names(sp[0])[:2]: base[b] = pbs[b].rotation_quaternion.copy()
        H0 = {sp[0]: pbs[_arm_names(sp[0])[2]].head.copy() for sp in specs}; err = 0.0
        for it in range(iters):
            for side, tb, al, off, pole, pw in specs:
                T = H0[side].lerp(_pt(pbs, tb, al, off), w)
                P = _pt(pbs, pole[0], 0.0, pole[1]) if pole else None
                e = solve_frame(a, side, T, P, pw * w)
                if it == iters - 1: err = max(err, e)
        res[f] = ({b: (base[b].inverted() @ pbs[b].rotation_quaternion).normalized() for b in base}, err)
        for b, q in base.items(): pbs[b].rotation_quaternion = q
    _mute(cid, ('CORR', 'POLISH'), False)
    for b in res[frames[0]][0]:
        path = 'pose.bones["%s"].rotation_quaternion' % b; fcs = [_slot_fc(corr, a, path, j, b) for j in range(4)]; prev = None
        for f in frames:
            q = res[f][0][b]
            if prev is not None and prev.dot(q) < 0: q = -q
            prev = q
            for j in range(4): fcs[j].keyframe_points.insert(f, q[j], options={'FAST'})
        for fc in fcs:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            fc.update()
    e = max(res[f][1] for f in frames); print('arms_cross', cid, [s[0] + '->' + s[1] for s in specs], 'frames', len(frames), 'max err %.3f u' % e); return e

# ---------------- reference grip from a handmade clip (e.g. AMA longtfoldedF) ----------------
def _fing(s): return ['NPC %s Finger%d%d [%sF%d%d]' % (s, f, j, s, f, j) for f in range(5) for j in range(3)]

def ref_grip(ref_cid, frame, sides=('L', 'R')):
    """import the handmade reference clip (CLIPS/<ref_cid>.json) as its own BASE, sample `frame`: per side the hand head position and hand
    world rotation in the TORSO (Spine2) pose frame, plus the 15 finger local rotations (pose basis). Leaves the rig soloed on the ref."""
    a = rig(); import_base(ref_cid, force=True); solo(ref_cid); bpy.context.scene.frame_set(frame); bpy.context.view_layer.update(); pbs = a.pose.bones; out = {}
    for s in sides:
        U = pbs['NPC Spine2 [Spn2]'].matrix; Ui = U.inverted(); hd = pbs['NPC %s Hand [%sHnd]' % (s, s)]   # torso frame: both ref arms already folded
        o = 'R' if s == 'L' else 'L'; Ua = _armframe(pbs, 'NPC %s UpperArm [%sUar]' % (o, o))
        out[s] = dict(pos=(Ui @ hd.head).copy(), rot=(Ui.to_3x3().normalized() @ hd.matrix.to_3x3().normalized()).to_quaternion(),
                      rot_arm=(Ua.inverted() @ hd.matrix.to_3x3().normalized()).to_quaternion(),
                      pos_arm=(pbs['NPC %s UpperArm [%sUar]' % (o, o)].matrix.inverted() @ hd.head).copy(),
                      fingers={b: pbs[b].rotation_quaternion.copy() for b in _fing(s) if b in pbs})
    return out

_MS = Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, 1)))   # L<->R mirror in the Spine2 frame; bones: M_L = S M_R S (measured, residual 0.001)
def _mirror_q(q): return Quaternion((q.w, q.x, -q.y, -q.z))   # same mirror for pose-basis (bone-local) quaternions

def _fsrc(ref, s, b, mirror_L):
    if mirror_L and s == 'L': return _mirror_q(ref['R']['fingers'][b.replace('NPC L', 'NPC R').replace('[LF', '[RF')])
    return ref[s]['fingers'][b]

def arms_cross_ref(cid, ref, f0, f1, ramp=8, lift=(0, 0, 0), pole_fwd=16, pole_side=6, pole_up=-3, iters=3, fingers=True, arm_target=None, wrist_max=70.0, mirror_L=None, mirror_rot_L=False):
    """mirror_L=(right, fwd, up): solve R as usual, then put the LEFT hand at the mirror image of the right hand (position + world
    orientation, Spine2 frame) plus this offset (stack the forearms instead of intersecting); left fingers = mirrored right fingers."""
    """arm_target=(along, (r,f,u)): hand POSITION on the opposite upper arm (for bodies the reference's torso-frame placement doesn't fit),
    hand ORIENTATION from the reference relative to that arm (palm wraps it), clamped so the wrist bends <= wrist_max deg from BASE."""
    """both hands onto the opposite upper arm at the reference grip (pos/rot in that arm's frame), + `lift` (right, fwd, up body frame,
    u: clears a bigger bust than the reference body). Arms: hinge-exact IK (CORR on UpperArm/Forearm); hand orientation: CORR on Hand;
    fingers: POLISH = BASE^-1 * ref finger pose (so the final finger pose IS the reference grip)."""
    a = rig(); n = solo(cid); sc = bpy.context.scene; pbs = a.pose.bones; vl = bpy.context.view_layer
    corr = bpy.data.actions[cid + '_CORR']; pol = bpy.data.actions[cid + '_POLISH']
    _mute(cid, ('CORR', 'POLISH'), True); frames = _frames(f0, f1, n); res = {}; errs = []
    sides = [s for s in (('R', 'L') if (mirror_L or mirror_rot_L) else ('L', 'R')) if s in ref]
    for i, f in enumerate(frames):
        sc.frame_set(f); vl.update(); w = _weight(i, len(frames), ramp)
        bones = [b for s in sides for b in _arm_names(s)]; base = {b: pbs[b].rotation_quaternion.copy() for b in bones}
        fb = {b: pbs[b].rotation_quaternion.copy() for s in sides for b in _fing(s) if b in pbs}
        H0 = {s: pbs[_arm_names(s)[2]].head.copy() for s in sides}; R0 = {s: pbs[_arm_names(s)[2]].matrix.to_3x3().normalized().to_quaternion() for s in sides}
        for it in range(iters):
            for s in sides:
                U = pbs['NPC Spine2 [Spn2]'].matrix; o = 'R' if s == 'L' else 'L'; ua_o = 'NPC %s UpperArm [%sUar]' % (o, o)
                r_, f_, u_ = _body(pbs)
                if mirror_L and s == 'L':
                    B = pbs['NPC Spine2 [Spn2]'].matrix; Bo = B.to_translation(); B3 = B.to_3x3().normalized(); hR = pbs[_arm_names('R')[2]]
                    T = Bo + B3 @ (_MS @ (B3.inverted() @ (hR.head - Bo))) + r_ * mirror_L[0] + f_ * mirror_L[1] + u_ * mirror_L[2]
                elif arm_target == 'ref': T = pbs[ua_o].matrix @ ref[s]['pos_arm'] + r_ * lift[0] + f_ * lift[1] + u_ * lift[2]
                elif arm_target:   # offset[0] = OUTWARD from the target arm (mirrored per side), then forward, up; dict = per side
                    at = arm_target[s] if isinstance(arm_target, dict) else arm_target
                    ot = at[1]; T = _pt(pbs, ua_o, at[0], (ot[0] * (1 if s == 'L' else -1), ot[1], ot[2]))
                else: T = (U @ ref[s]['pos']) + r_ * lift[0] + f_ * lift[1] + u_ * lift[2]
                T = H0[s].lerp(T, w)
                sd = 1 if s == 'R' else -1   # elbow pole: in front of the chest, toward the elbow's own side
                ps, pf, pu = (pole_side[s] if isinstance(pole_side, dict) else (pole_side, pole_fwd, pole_up))
                P = pbs['NPC Spine1 [Spn1]'].head + r_ * (sd * ps) + f_ * pf + u_ * pu
                e = solve_frame(a, s, T, P, w)
                # hand world orientation = reference (in the opposite arm's frame), blended by w; written as the hand's basis
                hd = pbs[_arm_names(s)[2]]
                if (mirror_L or mirror_rot_L) and s == 'L':   # orientation = mirror of the solved right hand (position may differ)
                    B3 = pbs['NPC Spine2 [Spn2]'].matrix.to_3x3().normalized(); MR = pbs[_arm_names('R')[2]].matrix.to_3x3().normalized()
                    tgt = (B3 @ _MS @ B3.inverted() @ MR @ _MS).to_quaternion()
                else: tgt = (_armframe(pbs, ua_o).to_quaternion() @ ref[s]['rot_arm']) if arm_target else (U.to_3x3().normalized().to_quaternion() @ ref[s]['rot'])
                hb = base[_arm_names(s)[2]]; M = hd.matrix.copy(); hd.matrix = Matrix.Translation(M.to_translation()) @ R0[s].slerp(tgt, w).to_matrix().to_4x4(); vl.update()
                dq = hb.inverted() @ hd.rotation_quaternion; ang = math.degrees(dq.angle) if dq.angle <= math.pi else 360 - math.degrees(dq.angle)
                if it == iters - 1 and f == frames[0]: print('WRIST', s, 'requested %.0f deg from BASE' % ang)
                if ang > wrist_max: hd.rotation_quaternion = hb.slerp(hd.rotation_quaternion, wrist_max / ang); vl.update()
                if it == iters - 1: errs.append((hd.head - T).length)
        res[f] = ({b: (base[b].inverted() @ pbs[b].rotation_quaternion).normalized() for b in bones},
                  {b: (fb[b].inverted() @ _fsrc(ref, s, b, mirror_L or mirror_rot_L)).normalized() if w >= 1 else fb[b].inverted().slerp(fb[b].inverted() @ _fsrc(ref, s, b, mirror_L or mirror_rot_L), w) for s in sides for b in _fing(s) if b in fb})
        for b, q in base.items(): pbs[b].rotation_quaternion = q
    _mute(cid, ('CORR', 'POLISH'), False)
    def write(act, idx):
        for b in res[frames[0]][idx]:
            path = 'pose.bones["%s"].rotation_quaternion' % b; fcs = [_slot_fc(act, a, path, j, b) for j in range(4)]; prev = None
            for f in frames:
                q = res[f][idx][b]
                if prev is not None and prev.dot(q) < 0: q = -q
                prev = q
                for j in range(4): fcs[j].keyframe_points.insert(f, q[j], options={'FAST'})
            for fc in fcs:
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
                fc.update()
    write(corr, 0)
    if fingers: write(pol, 1)
    print('arms_cross_ref', cid, 'frames', len(frames), 'max hand err %.3f u' % max(errs)); return max(errs)

# ---------------- direct pose transplant from a handmade clip (same XPMSSE skeleton) ----------------
ARM_CHAIN = lambda s: ['NPC %s Clavicle [%sClv]' % (s, s), 'NPC %s UpperArm [%sUar]' % (s, s), 'NPC %s UpperarmTwist1 [%sUt1]' % (s, s),
                       'NPC %s Forearm [%sLar]' % (s, s), 'NPC %s ForearmTwist1 [%sLt1]' % (s, s), 'NPC %s ForearmTwist2 [%sLt2]' % (s, s),
                       'NPC %s Hand [%sHnd]' % (s, s)] + _fing(s)

def sample_pose(ref_cid, frame, bones):
    """pose-basis quaternions of `bones` in a handmade clip at `frame` (imports it as its own BASE)"""
    a = rig(); import_base(ref_cid, force=True); solo(ref_cid); bpy.context.scene.frame_set(frame); bpy.context.view_layer.update()
    return {b: a.pose.bones[b].rotation_quaternion.copy() for b in bones if b in a.pose.bones}

def pose_transplant(cid, ref_pose, f0, f1, ramp=8, nudge=None, weight=1.0, layer='CORR'):
    """nudge = {bone: [(axis, deg), ...]}: after taking the ref rotation, turn that bone about a BODY axis through its head
    (axis 'r' = her right/lateral: + raises the arm forward, 'f' = forward, 'u' = up). Small corrections on top of the transplanted pose."""
    """CORR so the listed bones take the reference's LOCAL rotations (final = BASE x CORR = ref), eased in/out over `ramp` frames.
    Local rotations on the same skeleton reproduce the reference arm pose relative to the dance's own torso."""
    a = rig(); n = solo(cid); sc = bpy.context.scene; pbs = a.pose.bones; corr = bpy.data.actions[cid + '_' + layer]
    _mute(cid, ('CORR', 'POLISH'), True); frames = _frames(f0, f1, n); res = {}
    for i, f in enumerate(frames):
        sc.frame_set(f); bpy.context.view_layer.update(); w = _weight(i, len(frames), ramp) * weight
        res[f] = {}; base = {b: pbs[b].rotation_quaternion.copy() for b in ref_pose}
        for b, rq in ref_pose.items(): pbs[b].rotation_quaternion = base[b].slerp(rq, w) if w < 1 else rq
        bpy.context.view_layer.update()
        if nudge:
            r_, f_, u_ = _body(pbs); AX = {'r': r_, 'f': f_, 'u': u_}
            for b, lst in nudge.items():
                for ax, deg in lst:
                    pb = pbs[b]; R = Quaternion(AX[ax], math.radians(deg * w)).to_matrix()
                    pb.matrix = Matrix.Translation(pb.head) @ (R @ pb.matrix.to_3x3()).to_4x4(); bpy.context.view_layer.update()
        for b in ref_pose: res[f][b] = (base[b].inverted() @ pbs[b].rotation_quaternion).normalized(); pbs[b].rotation_quaternion = base[b]
    _mute(cid, ('CORR', 'POLISH'), False)
    for b in ref_pose:
        path = 'pose.bones["%s"].rotation_quaternion' % b; fcs = [_slot_fc(corr, a, path, j, b) for j in range(4)]; prev = None
        for f in frames:
            q = res[f][b]
            if prev is not None and prev.dot(q) < 0: q = -q
            prev = q
            for j in range(4): fcs[j].keyframe_points.insert(f, q[j], options={'FAST'})
        for fc in fcs:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
            fc.update()
    print('pose_transplant', cid, len(ref_pose), 'bones', len(frames), 'frames')
