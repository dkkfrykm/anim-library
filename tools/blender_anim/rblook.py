"""RBLOOK (Animator, tools/anim): apply a girl's body-slider preset to the Blender rig's shape keys, read straight from the game JS
(web/src3d/reiko_look.js for 'reiko', web/src3d/girls3d.js entries for the others) so the Blender stage shows the in-game body
(the game's RB3.morph sets morphTargetInfluences[name] = value on every mesh that has the morph; same here).
exec after rbanim.py:  apply_look('reiko')  -> {applied: n, missing: [...]}"""
import bpy, re, os
ROOT_JS = r'C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed/web/src3d'

def _strip(s): return re.sub(r'/\*.*?\*/', '', s, flags=re.S)

def _obj_after(src, start):
    i = src.index('{', start); d = 0
    for k in range(i, len(src)):
        if src[k] == '{': d += 1
        elif src[k] == '}':
            d -= 1
            if d == 0: return src[i:k + 1]

def _parse(body):
    return {m.group(1): float(m.group(2)) for m in re.finditer(r"'([^']+)'\s*:\s*(-?[\d.]+)", _strip(body))}

def preset_of(girl='reiko'):
    if girl == 'reiko':
        s = open(os.path.join(ROOT_JS, 'reiko_look.js'), encoding='utf-8').read(); return _parse(_obj_after(s, s.index('preset:')))
    s = open(os.path.join(ROOT_JS, 'girls3d.js'), encoding='utf-8').read()
    m = re.search(r"id:\s*'%s'" % re.escape(girl), s)
    if not m: raise KeyError(girl)
    return _parse(_obj_after(s, s.index('preset:', m.end())))

def apply_look(girl='reiko'):
    P = preset_of(girl); hit = set()
    for o in bpy.data.objects:
        kb = o.data.shape_keys.key_blocks if o.type == 'MESH' and o.data.shape_keys else None
        if not kb: continue
        for k in kb:
            if k.name == 'Basis': continue
            if k.name in P: k.slider_min = min(k.slider_min, P[k.name]); k.value = P[k.name]; hit.add(k.name)
            elif k.value: k.value = 0.0
    miss = sorted(set(P) - hit); print('apply_look', girl, 'applied', len(hit), 'missing', miss); return {'applied': len(hit), 'missing': miss}
