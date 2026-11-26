"""One-line-per-clip inventory of every pose/animation source the game has or has decoded -> qa/pack_inventory.tsv
columns: pack, status (live|decoded|game-format|hkx-only), name, n, fps, kind (pose=1 frame|anim), location. Usage: python -I tools/pack_inventory.py"""
import os, json, glob, gzip, re
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); A = R + '/web/assets/anims'; RB = 'C:/Users/mytwo/rbsrc'; out = []
def add(pack, status, name, n, fps, loc): out.append((pack, status, name, str(n), str(fps), 'pose' if n == 1 else 'anim', loc))
def js_obj(path, var):
    s = open(path, encoding='utf-8').read(); k = s.index(var + '=') + len(var) + 1; return json.JSONDecoder().raw_decode(s[k:])[0]
for f, pack in (('leito.json', 'leito (Leito 2 pairs)'), ('poses.json', 'sonders poses'), ('poses2.json', 'poses2 (enaposer/flufyfox/hexed/hotbabe)'), ('sos.json', 'sos')):
    d = json.load(open(A + '/' + f))
    for k, c in d.get('clips', {}).items(): add(pack, 'live', k, c.get('n', 1), c.get('fps', 30), 'web/assets/anims/' + f)
for f, var, pack in (('anims3d.js', 'window.RB_ANIM3D', 'anims3d bundle'), ('roto3d.js', 'window.RB_ROTO3D', 'roto (rotoscoped)'), ('dance3d.js', 'window.RB_DANCE3D', 'dances (rotoscoped)')):
    try:
        d = js_obj(A + '/' + f, var)
        sets = d['clips'] if 'clips' in d else {k: v for k, v in d.items() if isinstance(v, dict) and 'clips' in v}
        if 'clips' in d:
            for k, c in d['clips'].items(): add(pack, 'live', k, c.get('n', 1), c.get('fps', 30), 'web/assets/anims/' + f)
        else:
            for sk, sv in sets.items():
                for k, c in sv['clips'].items(): add(pack + ':' + sk, 'live', k, c.get('n', 1), c.get('fps', 30), 'web/assets/anims/' + f)
    except Exception as e: add(pack, 'ERR', str(e)[:60], 0, 0, f)
cat = js_obj(A + '/catalog3d.js', 'window.RB_CAT3D')
for sc in cat['scenes']:
    for i, st in enumerate(sc['stages']):
        for a in ('f', 'm'):
            fp = glob.glob('%s/%s/%s*.js' % (A, sc['pack'], sc['id'])); add('catalog:' + cat['packs'].get(sc['pack'], sc['pack']), 'live', '%s_%s_%s' % (sc['id'], st.get('c', i + 1), a), '?', 30, os.path.relpath(fp[0], R).replace(chr(92), '/') if fp else 'web/assets/anims/' + sc['pack'] + '/')
for f in glob.glob(R + '/qa/armmove/clips/*.json'):
    c = json.load(open(f))['clip']; add('AMA Arm Movement Animations OAR 3.0.2', 'game-format', os.path.basename(f)[:-5], c['n'], c['fps'], os.path.relpath(f, R).replace(chr(92), '/'))
for f in glob.glob(R + '/qa/packs/*/clips/*.json'):
    pk = f.replace(chr(92), '/').split('/qa/packs/')[1].split('/')[0]
    try: c = json.load(open(f))['clip']; add('pack:' + pk, 'game-format', os.path.basename(f)[:-5], c['n'], c['fps'], os.path.relpath(f, R).replace(chr(92), '/'))
    except Exception: pass
for d, pack in (('decoded', 'decoded (leito/misc)'), ('decoded_poses2', 'decoded poses2'), ('decoded_sonders', 'decoded sonders')):
    for f in glob.glob('%s/%s/**/*.json.gz' % (R, d), recursive=True):
        try: dd = json.load(gzip.open(f)); n = len(dd.get('frames', [])); fps = dd.get('fps', 30)
        except Exception: n, fps = '?', '?'
        add(pack, 'decoded', os.path.basename(f)[:-8], n, fps, os.path.relpath(f, R).replace(chr(92), '/'))
HK = [(R + '/' + p, p) for p in ('src_compendium', 'src_leito', 'src_sonders', 'src_sos', 'src_wallbang', 'src_xpmsse')] + [(RB + '/' + p, 'rbsrc/' + p) for p in ('billyy', 'enaposer', 'flufyfox', 'hexed', 'hotbabe', 'leito3', 'armmove')]
for d, pack in HK:
    for f in glob.glob(d + '/**/*.hkx', recursive=True):
        if 'skeleton' in os.path.basename(f).lower(): continue
        add(pack, 'hkx', os.path.basename(f)[:-4], '?', '?', f.replace(chr(92), '/'))
with open(R + '/qa/pack_inventory.tsv', 'w', encoding='utf-8') as o:
    o.write('pack\tstatus\tname\tn\tfps\tkind\tlocation\n'); [o.write('\t'.join(r) + '\n') for r in out]
from collections import Counter
for (p, s), c in sorted(Counter((r[0], r[1]) for r in out).items()): print('%5d  %-8s %s' % (c, s, p))
print(len(out), 'rows -> qa/pack_inventory.tsv')
