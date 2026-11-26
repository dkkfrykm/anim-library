"""RBANIM: non-destructive animation pipeline for Half an Eye, run INSIDE Blender (live via MCP: exec(open(...).read()); headless:
blender -b <blend> --python tools/anim/rbanim_cli.py -- <cmd> ...).

Stages per clip id (one persistent library .blend, C:/Users/mytwo/rbsrc/anim/reiko_anim.blend):
  SOURCE  cached capture (tools/roto/mocap_kp, hands_kp)            - never touched here
  BASE    retargeted solve (tools/roto/mocap_clips/<id>.json) -> action <id>_BASE, NLA track BASE (locked, REPLACE)
  CORR    additive fixes  -> action <id>_CORR,  NLA track CORR  (COMBINE: identity = no change)
  POLISH  artistic layer  -> action <id>_POLISH, NLA track POLISH (COMBINE)
  FINAL   NLA stack evaluated per frame -> clip JSON (game format, tools/anims3d.py) staged in tools/anim/final/<id>.json
Rig: web/assets/reiko_body.glb imported once (armature UBE_Root). Its bones keep the game's node axes (armature space = Rx(+90) x Skyrim),
so a clip's local quaternion q (three.js bone.quaternion) maps exactly: pose basis = rest_local^-1 @ q (and back), COM translation t likewise.
Cache: tools/anim/cache/<id>.json = {base_src_hash, base_hash, corr_hash, polish_hash, final_hash, qa}: a layer edit only invalidates FINAL."""
import bpy, json, os, hashlib, math, re
from mathutils import Quaternion, Matrix, Vector

ROOT = r'C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed'
LIB = r'C:/Users/mytwo/rbsrc/anim/reiko_anim.blend'
CLIPS = ROOT + '/tools/roto/mocap_clips'; FINAL = ROOT + '/tools/anim/final'; CACHE = ROOT + '/tools/anim/cache'
ARM = 'UBE_Root'; LAYERS = ('BASE', 'CORR', 'POLISH')
for d in (FINAL, CACHE): os.makedirs(d, exist_ok=True)

def _ctx():
    win = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), None) if win else None
    return dict(window=win, area=area) if area else {}

def rig():
    """the rig armature; imported from the game glb once (meshes kept for visual checks)"""
    a = bpy.data.objects.get(ARM)
    if a:
        if not a.animation_data: a.animation_data_create()
        return a
    with bpy.context.temp_override(**_ctx()):
        bpy.ops.import_scene.gltf(filepath=ROOT + '/web/assets/reiko_body.glb')
    a = bpy.data.objects[ARM]; a.animation_data_create()
    for pb in a.pose.bones: pb['rb_rest_basis'] = list(pb.location) + list(pb.rotation_quaternion) + list(pb.scale)   # see solo()
    return a

def _h(obj): return hashlib.sha1(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]
def _cache(cid, **kw):
    p = CACHE + '/%s.json' % cid; c = json.load(open(p)) if os.path.exists(p) else {}
    if kw: c.update(kw); json.dump(c, open(p, 'w'), indent=1)
    return c
def _rest_local(pb):
    # parentless bone (NPC Root): its matrix_local carries the importer's axis conversion (armature space = Rx(+90) x Skyrim); in the game
    # that conversion lives in a PARENT node, so a clip's Root q is relative to identity (Skyrim Root rest = identity). Using matrix_local
    # here made every clip that keys Root (handmade packs, AMA) lie down in Blender. Dances don't key Root (unaffected).
    b = pb.bone; return (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else Matrix.Identity(4)

def _nla(a, cid):
    ad = a.animation_data; tr = {}
    for name in LAYERS:
        t = ad.nla_tracks.get(cid + ':' + name) or ad.nla_tracks.new(); t.name = cid + ':' + name; tr[name] = t
    return tr

def _layer_action(cid, name, n):
    act = bpy.data.actions.get('%s_%s' % (cid, name)) or bpy.data.actions.new('%s_%s' % (cid, name)); act.use_fake_user = True
    try:   # Blender 5 slotted actions: create the slot NOW so the NLA strip binds to it (a strip made before the slot exists stays
        if not len(act.slots): act.slots.new(id_type='OBJECT', name=ARM)   # unbound -> its keys are never evaluated)
    except AttributeError: pass
    act['rb_frames'] = n; return act

def _bind_strips(act, slot):
    """bind every NLA strip that uses `act` but has no slot (layers created before this fix) -> otherwise CORR/POLISH keys are ignored"""
    for o in bpy.data.objects:
        ad = o.animation_data
        if not ad: continue
        for t in ad.nla_tracks:
            for st in t.strips:
                if st.action == act and getattr(st, 'action_slot', 1) is None:
                    try: st.action_slot = slot
                    except Exception as e: print('bind slot failed', st.name, e)

def _slot_fc(act, a, path, index, group):
    """fcurve on the action for the armature (Blender 5 slotted actions)"""
    try:
        slot = act.slots[0] if len(act.slots) else act.slots.new(id_type='OBJECT', name=a.name)
        bag = act.layers[0].strips[0].channelbag(slot, ensure=True) if len(act.layers) else None
        if bag is None:
            lay = act.layers.new('Layer'); st = lay.strips.new(type='KEYFRAME'); bag = st.channelbag(slot, ensure=True)
        _bind_strips(act, slot)
        return bag.fcurves.find(path, index=index) or bag.fcurves.new(path, index=index, group_name=group)
    except AttributeError:   # legacy actions
        return act.fcurves.find(path, index=index) or act.fcurves.new(path, index=index, action_group=group)

def _fcurves(act):
    try:
        out = []
        for lay in act.layers:
            for st in lay.strips:
                for slot in act.slots:
                    bag = st.channelbag(slot)
                    if bag: out += list(bag.fcurves)
        return out
    except AttributeError: return list(act.fcurves)

def _set_strip(track, act, n, blend):
    for s in list(track.strips): track.strips.remove(s)
    s = track.strips.new(act.name, 0, act); s.blend_type = blend; s.action_frame_start = 0; s.action_frame_end = max(1, n - 1)
    s.frame_start = 0; s.frame_end = max(1, n - 1); s.extrapolation = 'HOLD'
    try: s.action_slot = act.slots[0]
    except Exception: pass
    return s

def import_base(cid, force=False):
    """BASE action from the baked clip (tools/roto/mocap_clips/<id>.json); skipped when the source clip hash is unchanged"""
    a = rig(); C = json.load(open('%s/%s.json' % (CLIPS, cid))); clip = C['clip']; n = clip['n']; src = _h(clip)
    c = _cache(cid)
    if not force and c.get('base_src_hash') == src and bpy.data.actions.get(cid + '_BASE'): print(cid, 'BASE up to date'); return
    act = _layer_action(cid, 'BASE', n)
    for fc in _fcurves(act): pass
    try:
        for lay in list(act.layers): act.layers.remove(lay)
    except AttributeError:
        for fc in list(act.fcurves): act.fcurves.remove(fc)
    pbs = a.pose.bones; frames = list(range(n)); missing = []
    for bname, qv in clip['q'].items():
        pb = pbs.get(bname)
        if not pb: missing.append(bname); continue
        m = len(qv) // 4; Rl = _rest_local(pb).to_quaternion().inverted(); path = 'pose.bones["%s"].rotation_quaternion' % bname
        pb.rotation_mode = 'QUATERNION'; fcs = [_slot_fc(act, a, path, k, bname) for k in range(4)]; prev = None
        keys = [[], [], [], []]
        for f in frames:
            j = (f % m) * 4; q = Quaternion((qv[j + 3] * 1e-4, qv[j] * 1e-4, qv[j + 1] * 1e-4, qv[j + 2] * 1e-4)); b = Rl @ q
            if prev is not None and prev.dot(b) < 0: b.negate()
            prev = b
            for k in range(4): keys[k] += [f, b[k]]
            if m == 1: break
        for k in range(4): fcs[k].keyframe_points.add(len(keys[k]) // 2); fcs[k].keyframe_points.foreach_set('co', keys[k]); [setattr(kp, 'interpolation', 'LINEAR') for kp in fcs[k].keyframe_points]; fcs[k].update()
    for bname, tv in clip.get('t', {}).items():
        pb = pbs.get(bname)
        if not pb: missing.append(bname); continue
        RL = _rest_local(pb).inverted(); path = 'pose.bones["%s"].location' % bname; fcs = [_slot_fc(act, a, path, k, bname) for k in range(3)]; keys = [[], [], []]
        for f in frames:
            j = (f % (len(tv) // 3)) * 3; loc = (RL @ Matrix.Translation(Vector((tv[j] * .01, tv[j + 1] * .01, tv[j + 2] * .01)))).to_translation()
            for k in range(3): keys[k] += [f, loc[k]]
        for k in range(3): fcs[k].keyframe_points.add(len(keys[k]) // 2); fcs[k].keyframe_points.foreach_set('co', keys[k]); [setattr(kp, 'interpolation', 'LINEAR') for kp in fcs[k].keyframe_points]; fcs[k].update()
    # constant translations (tc): the game applies them as position tracks (web/src3d/rb3d.js), e.g. the HKX finger/knuckle offsets
    # that differ from the glb node rest by 1.8-5 u. Without them the Blender stage shows wrong joint positions (knuckle "mitten cuff").
    # Keyed once (constant) on BASE; export_final passes tc through unchanged via rb_clip.
    for bname, tv in clip.get('tc', {}).items():
        pb = pbs.get(bname)
        if not pb or bname in clip.get('t', {}): continue
        RL = _rest_local(pb).inverted(); loc = (RL @ Matrix.Translation(Vector(tv))).to_translation()
        fcs = [_slot_fc(act, a, 'pose.bones["%s"].location' % bname, k, bname) for k in range(3)]
        for k in range(3): fcs[k].keyframe_points.add(1); fcs[k].keyframe_points.foreach_set('co', [0, loc[k]]); fcs[k].keyframe_points[0].interpolation = 'CONSTANT'; fcs[k].update()
    act['rb_fps'] = clip['fps']; act['rb_clip'] = json.dumps({k: clip[k] for k in clip if k not in ('q', 't')})
    tr = _nla(a, cid); _set_strip(tr['BASE'], act, n, 'REPLACE'); tr['BASE'].lock = True
    for name in ('CORR', 'POLISH'):
        la = _layer_action(cid, name, n)
        if not tr[name].strips: _set_strip(tr[name], la, n, 'COMBINE')
    _cache(cid, base_src_hash=src, base_hash=src, final_hash=None, qa=None)
    print(cid, 'BASE imported:', n, 'frames', len(clip['q']), 'bones', 'missing', missing[:5])

def solo(cid):
    """only this clip's tracks active (several clips share the rig)"""
    a = rig()
    for t in a.animation_data.nla_tracks: t.mute = not t.name.startswith(cid + ':')
    # muted tracks do NOT reset what they drove: bones this clip doesn't key would keep the previous clip's values (e.g. a ref clip's
    # Root/COM) -> reset every pose basis to rest first (= the game's fallback for untracked bones)
    for pb in a.pose.bones:   # reset to the IMPORT-TIME basis (glb node TRS vs bind: e.g. Hand scale 0.8517, breast nodes), not identity
        r = pb.get('rb_rest_basis')
        if r: pb.location = r[0:3]; pb.rotation_quaternion = r[3:7]; pb.scale = r[7:10]
        else: pb.location = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.scale = (1, 1, 1)
    a.animation_data.action = None; n = bpy.data.actions[cid + '_BASE']['rb_frames']; sc = bpy.context.scene
    sc.frame_start = 0; sc.frame_end = n - 1; sc.render.fps = round(bpy.data.actions[cid + '_BASE']['rb_fps']); return n

# ---------------- corrections (CORR / POLISH layers, COMBINE: quaternion multiply on top, identity = untouched) ----------------
def _ease(t): return t * t * (3 - 2 * t)
def correct_rotation(cid, bone, f0, f1, euler_deg, layer='CORR', ramp=6, fmid=None):
    """add a local rotation (bone axes, degrees) to `bone` over [f0, f1], eased in/out over `ramp` frames: keys only on that bone/range"""
    a = rig(); act = bpy.data.actions['%s_%s' % (cid, layer)]; pb = a.pose.bones[bone]; pb.rotation_mode = 'QUATERNION'
    path = 'pose.bones["%s"].rotation_quaternion' % bone; fcs = [_slot_fc(act, a, path, k, bone) for k in range(4)]
    from mathutils import Euler
    dq = Euler([math.radians(x) for x in euler_deg]).to_quaternion()
    pts = [(f0 - ramp, 0.0), (f0, 1.0), (f1, 1.0), (f1 + ramp, 0.0)]
    for f, w in pts:
        q = Quaternion().slerp(dq, w); old = [fc.evaluate(f) if len(fc.keyframe_points) else (1.0 if k == 0 else 0.0) for k, fc in enumerate(fcs)]
        qo = Quaternion(old) if any(old) else Quaternion(); qn = qo @ q if w > 0 else qo
        for k in range(4): fcs[k].keyframe_points.insert(f, qn[k], options={'FAST'})
    for fc in fcs: fc.update()
    print(cid, layer, bone, 'rot', euler_deg, 'frames', f0, f1)

def smooth_range(cid, bones, f0, f1, win=5, layer='CORR'):
    """smooth the EVALUATED rotation of `bones` over [f0, f1] (centred moving average, `win` frames) by writing the difference to `layer`"""
    a = rig(); n = solo(cid); act = bpy.data.actions['%s_%s' % (cid, layer)]; sc = bpy.context.scene; ev = {}
    for f in range(max(0, f0 - win), min(n, f1 + win + 1)):
        sc.frame_set(f); ev[f] = {b: a.pose.bones[b].rotation_quaternion.copy() for b in bones}
    for b in bones:
        path = 'pose.bones["%s"].rotation_quaternion' % b; fcs = [_slot_fc(act, a, path, k, b) for k in range(4)]
        for f in range(f0, f1 + 1):
            acc = Vector((0, 0, 0, 0)); ref = ev[f][b]
            for o in range(-(win // 2), win // 2 + 1):
                q = ev.get(f + o, ev[f])[b]; q = q if q.dot(ref) >= 0 else -q; acc += Vector(q)
            qs = Quaternion(acc.normalized()); cur = Quaternion([fc.evaluate(f) if len(fc.keyframe_points) else (1.0 if k == 0 else 0.0) for k, fc in enumerate(fcs)])
            delta = ref.inverted() @ qs   # what the stack must add
            qn = cur @ delta
            for k in range(4): fcs[k].keyframe_points.insert(f, qn[k], options={'FAST'})
        for fc in fcs: fc.update()
    print(cid, layer, 'smoothed', bones, f0, f1)

def layer_hash(cid, layer):
    act = bpy.data.actions.get('%s_%s' % (cid, layer))
    if not act: return None
    return _h([[fc.data_path, fc.array_index, [list(kp.co) for kp in fc.keyframe_points]] for fc in _fcurves(act)])

# ---------------- FINAL: evaluate the stack -> game clip ----------------
def export_final(cid, force=False):
    a = rig(); c = _cache(cid); hs = {L: layer_hash(cid, L) for L in LAYERS}; key = _h(hs)
    out = FINAL + '/%s.json' % cid
    if not force and c.get('final_hash') == key and os.path.exists(out): print(cid, 'FINAL up to date'); return out
    n = solo(cid); base = bpy.data.actions[cid + '_BASE']; meta = json.loads(base['rb_clip']); src = json.load(open('%s/%s.json' % (CLIPS, cid)))
    bones = list(src['clip']['q'].keys()); tbones = list(src['clip'].get('t', {}).keys()); sc = bpy.context.scene
    for L in ('CORR', 'POLISH'):   # bones that got LOCATION keys in a layer must be exported per frame too (else e.g. a COM shift is lost)
        la = bpy.data.actions.get('%s_%s' % (cid, L))
        for fc in (_fcurves(la) if la else []):
            m = re.match(r'pose\.bones\["(.+)"\]\.location', fc.data_path)
            if m and m.group(1) not in tbones and any(abs(k.co[1]) > 1e-6 for k in fc.keyframe_points): tbones.append(m.group(1))
    q = {b: [] for b in bones if b in a.pose.bones}; t = {b: [] for b in tbones if b in a.pose.bones}
    for f in range(n):
        sc.frame_set(f)
        for b in q:
            pb = a.pose.bones[b]; L = _rest_local(pb).to_quaternion() @ pb.rotation_quaternion.normalized()
            q[b] += [int(round(L.x * 1e4)), int(round(L.y * 1e4)), int(round(L.z * 1e4)), int(round(L.w * 1e4))]
        for b in t:
            pb = a.pose.bones[b]; M = _rest_local(pb) @ Matrix.Translation(pb.location); v = M.to_translation()
            t[b] += [int(round(v.x * 100)), int(round(v.y * 100)), int(round(v.z * 100))]
    clip = dict(meta); clip['q'] = q; clip['t'] = t
    if clip.get('tc'): clip['tc'] = {b: v for b, v in clip['tc'].items() if b not in t}   # per-frame t supersedes the constant (no duplicate position track)
    for b, v in src['clip']['q'].items():
        if b not in q: clip['q'][b] = v   # bones absent from the rig pass through unchanged
    json.dump({'clip': clip, 'log': dict(src['log'], rbanim=dict(layers=hs))}, open(out, 'w'), separators=(',', ':'))
    _cache(cid, final_hash=key, qa=None); print(cid, 'FINAL exported', out, n, 'frames'); return out

def roundtrip_error(cid):
    """BASE-only export vs the source clip: max quaternion angle error (deg) -> must be ~0 (validates the mapping)"""
    import numpy as np
    src = json.load(open('%s/%s.json' % (CLIPS, cid)))['clip']; out = json.load(open(export_final(cid, force=True)))['clip']; worst = (0, None)
    for b, v in out['q'].items():
        a_ = np.array(v, float).reshape(-1, 4) / 1e4; m = len(src['q'][b]) // 4; s_ = np.array(src['q'][b], float).reshape(-1, 4)[np.arange(len(a_)) % m] / 1e4
        d = np.degrees(2 * np.arccos(np.clip(np.abs((a_ * s_).sum(1)) / np.linalg.norm(a_, axis=1) / np.linalg.norm(s_, axis=1), 0, 1))).max()
        if d > worst[0]: worst = (d, b)
    print(cid, 'roundtrip max err deg %.3f at %s' % worst); return worst

def save(): bpy.ops.wm.save_as_mainfile(filepath=LIB) if bpy.data.filepath != LIB else bpy.ops.wm.save_mainfile(); print('saved', LIB)
print('rbanim loaded')

def contact_sheet(cid, frames=None, count=8, out=None):
    """workbench renders of the evaluated stack at `frames` (default: `count` evenly over the loop), tiled -> qa/anim/<id>_sheet.png"""
    import numpy as np
    n = solo(cid); sc = bpy.context.scene; frames = frames or [int(n * (i + .5) / count) for i in range(count)]
    os.makedirs(ROOT + '/qa/anim', exist_ok=True); tiles = []
    for f in frames:
        sc.frame_set(f); sc.render.filepath = ROOT + '/qa/anim/_t.png'; bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(sc.render.filepath, check_existing=False); w, h = img.size; px = np.array(img.pixels[:]).reshape(h, w, 4); bpy.data.images.remove(img); tiles.append(px)
    sheet = np.concatenate(tiles, 1); h, w = sheet.shape[:2]; im = bpy.data.images.new('sheet', w, h); im.pixels = sheet.ravel()
    out = out or ROOT + '/qa/anim/%s_sheet.png' % cid; im.filepath_raw = out; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im); print('sheet', out, frames); return out
