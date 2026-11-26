# Compose renders_<module>.json into contact sheets: per clip, columns = picked frames, rows = camera views.
import sys, json, os
from PIL import Image, ImageDraw
OUT = sys.argv[2] if len(sys.argv) > 2 else "C:/Users/mytwo/harrow/anim/out"
idx = json.load(open(os.path.join(OUT, "renders_%s.json" % sys.argv[1])))
for name, picks in idx.items():
    ims = [[Image.open(p) for p in pair] for f, pair in picks]
    w, h = ims[0][0].size
    sheet = Image.new("RGB", (w * len(ims), h * 2 + 22), "white")
    d = ImageDraw.Draw(sheet)
    for c, ((f, _), pair) in enumerate(zip(picks, ims)):
        for r, im in enumerate(pair):
            sheet.paste(im, (c * w, 22 + r * h))
        d.text((c * w + 6, 5), "%s f%d@60 (%.2fs)" % (name, f, f / 60), fill="black")
    p = os.path.join(OUT, "sheet_%s.png" % name)
    sheet.save(p)
    print(p, sheet.size)
