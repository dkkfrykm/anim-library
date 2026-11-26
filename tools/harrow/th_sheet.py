import sys, os, glob, re
from PIL import Image, ImageDraw
d, out, pat = sys.argv[1], sys.argv[2], re.compile(sys.argv[3])
clips = {}
for f in sorted(glob.glob(os.path.join(d, 'renders', '*.png'))):
    n = re.sub(r'_\d+\.png$', '', os.path.basename(f))
    if pat.search(n): clips.setdefault(n, []).append(f)
W, H = 150, 130
cols = max(len(v) for v in clips.values())
im = Image.new('RGB', (180 + cols * W, len(clips) * H), (30, 28, 26)); dr = ImageDraw.Draw(im)
for r, (n, fs) in enumerate(clips.items()):
    dr.text((4, r * H + 55), n.replace('Sky_', ''), fill=(230, 220, 200))
    for c, f in enumerate(fs):
        im.paste(Image.open(f).convert('RGB').resize((W, H)), (180 + c * W, r * H))
im.save(out); print(len(clips))
