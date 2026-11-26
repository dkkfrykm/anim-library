"""decoded json.gz dir (skyrim_mco export_decoded.py output) -> game-format {clip, log} files: python -I tools/pack_to_clips.py <decoded_dir> <out_clips_dir> <pack label>"""
import sys, os, glob, gzip, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
import anims3d as A
src, out, label = sys.argv[1:4]; os.makedirs(out, exist_ok=True); k = 0; bad = 0
for f in sorted(glob.glob(src + '/**/*.json.gz', recursive=True)):
    nm = os.path.basename(f)[:-8]
    try:
        d = json.load(gzip.open(f)); n, q, t, tc = A.conv(d, drop_dup=False); fps = d.get('fps') or 30
        if n < 1: bad += 1; continue
        json.dump({'clip': dict(n=n, fps=fps, dur=round(n / fps, 4), q=q, t=t, tc=tc), 'log': {'source': label + '/' + nm, 'decoded': os.path.relpath(f, src).replace(chr(92), '/')}}, open(os.path.join(out, nm + '.json'), 'w'), separators=(',', ':')); k += 1
    except Exception as e: bad += 1; print('skip', nm, str(e)[:80])
print(label, 'clips', k, 'skipped', bad, '->', out)
