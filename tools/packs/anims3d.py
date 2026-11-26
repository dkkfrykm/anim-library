"""Decoded HKX clips (export_decoded.py json.gz: local bone tracks) -> compact web JSON for three.js AnimationClips.
Usage: python -I tools/anims3d.py <decoded_leito_dir> <decoded_sonders_dir> <out_dir>
Output: <out>/leito.json, <out>/poses.json
  { fps, bones:[names], clips:{ key:{ n, fps, dur, q:{bone:[ints x4 per frame]}, t:{bone:[ints x3 per frame, 0.01 units]}, tc:{bone:[x,y,z] const translation} } } }
Quaternions *1e4 (xyzw, hemisphere-continuous). Translations in Skyrim units *100. A track is kept only if it moves; unmoving bones fall back to the skeleton rest pose.
Leito keys: <pos>_<stage>_<m|f> (pos = missionary1, missionary2, cowgirl, revcowgirl, spooning, doggy); Sonders keys: pose id (e.g. paprika_4)."""
import sys, os, gzip, json, glob, math

POS = {'leitomissionary1': 'missionary1', 'leitomissionary2': 'missionary2', 'leitocowgirl': 'cowgirl', 'leitoreversecowgirl': 'revcowgirl', 'leitospooning': 'spooning', 'leitodoggystyle': 'doggy'}
SKIP = ('Camera', 'AnimObject', 'Weapon', 'Shield', 'Quiver', 'MagicNode', 'MagicEffects', 'Pauldron', 'LookNode', 'x_NPC', 'Skirt')


def conv(d, drop_dup=True, decim=1):
    fr = d['frames']; n = len(fr)
    if drop_dup and n > 2:
        a, b = fr[0], fr[-1]
        if max(abs(a[i][k] - b[i][k]) for i in range(len(a)) for k in range(7)) < 1e-3:
            fr = fr[:-1]; n -= 1
    fr = fr[::decim]; n = len(fr)
    q, t, tc = {}, {}, {}
    for ti, name in enumerate(d['tracks']):
        if any(s in name for s in SKIP) or name.startswith('track'):
            continue
        qs = []; prev = None
        for f in fr:
            x, y, z, w = f[ti][3:7]
            if prev and prev[0] * x + prev[1] * y + prev[2] * z + prev[3] * w < 0:
                x, y, z, w = -x, -y, -z, -w
            prev = (x, y, z, w); qs += [round(x * 1e4), round(y * 1e4), round(z * 1e4), round(w * 1e4)]
        if n > 1 and all(qs[i] == qs[i % 4] for i in range(len(qs))):
            qs = qs[:4]
        q[name] = qs
        ts = [f[ti][0:3] for f in fr]
        span = max(max(v[k] for v in ts) - min(v[k] for v in ts) for k in range(3))
        if span > 0.02:
            t[name] = [round(v * 100) for p in ts for v in p]
        else:
            tc[name] = [round(v, 3) for v in ts[0]]
    return n, q, t, tc


def main():
    dl, ds, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    L = {'clips': {}}
    for p in sorted(glob.glob(os.path.join(dl, '*', '*.json.gz'))):
        b = os.path.basename(p)[:-8]; pos, st, act = b.rsplit('_', 2)
        d = json.load(gzip.open(p)); n, q, t, tc = conv(d)
        L['clips']['%s_%s_%s' % (POS[pos], st, 'm' if act == '0' else 'f')] = dict(n=n, fps=round(d['fps'], 3), dur=round(n / d['fps'], 4), q=q, t=t, tc=tc)
    # OStim per-stage sosBend (male actor) from the scene JSONs next to the decoded data
    sb = {}
    sc = os.path.join(os.path.dirname(os.path.abspath(dl)), 'src_leito', 'SKSE', 'Plugins', 'OStim', 'scenes', 'LeitoExtra', 'fm')
    for pth in glob.glob(os.path.join(sc, '*', '*.json')):
        nm = os.path.basename(pth)[:-5].lower(); pos, st = nm.rsplit('-', 1)
        try:
            j = json.load(open(pth, encoding='utf-8')); sb['%s_%s' % (POS.get(pos, pos), st)] = (j.get('actors') or [{}])[0].get('sosBend', 0)
        except Exception as e:
            print('sosBend read failed', pth, e)
    L['sosBend'] = sb
    json.dump(L, open(os.path.join(out, 'leito.json'), 'w'), separators=(',', ':'))
    P = {'clips': {}}
    # poser ids (e.g. paprika_4) via the FNIS list: '<event> <file>.hkx'
    fmap = {}
    fl = glob.glob(os.path.join(os.path.dirname(os.path.abspath(ds)), 'src_sonders', '**', 'FNIS_*_List.txt'), recursive=True)
    for f in fl:
        for line in open(f, encoding='utf-8', errors='ignore'):
            parts = line.split()
            if len(parts) >= 3 and parts[-1].lower().endswith('.hkx') and not line.startswith("'"):
                ev = parts[-2]; import re as _r; ev = _r.sub(r'^\[[a-z]{2}sdb\]_', '', ev.lower()); fmap[parts[-1].lower()[:-4]] = ev
    for p in sorted(glob.glob(os.path.join(ds, '**', '*.json.gz'), recursive=True)):
        b = os.path.basename(p)[:-8].lower()
        d = json.load(gzip.open(p))
        static = d['numFrames'] <= 3 or 'animated' not in b and 'zenless' not in b
        if static:
            d['frames'] = d['frames'][:1]
        n, q, t, tc = conv(d, drop_dup=not static, decim=1 if static else 2)
        import re; key = fmap.get(b, re.sub(r'^.*sdb_', '', b))
        P['clips'][key] = dict(n=n, fps=round(d['fps'] / (1 if static else 2), 3), dur=round(max(1, n) / d['fps'] * (1 if static else 2), 4), q=q, t=t, tc=tc, src=b)
    json.dump(P, open(os.path.join(out, 'poses.json'), 'w'), separators=(',', ':'))
    for f in ('leito.json', 'poses.json'):
        print(f, round(os.path.getsize(os.path.join(out, f)) / 1e6, 2), 'MB')
    print('leito clips', len(L['clips']), 'poses', len(P['clips']), 'sample keys', list(P['clips'])[:5])


if __name__ == '__main__':
    main()
