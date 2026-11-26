# Per-style contact sheets from phase2 renders.json: one row per clip, columns = marker frames.
import sys, json, os
from PIL import Image, ImageDraw
D = sys.argv[2] if len(sys.argv) > 2 else "C:/Users/mytwo/soulbound/skyrim/out/phase2"
R = json.load(open(os.path.join(D, "renders.json")))
styles = sys.argv[1].split(",")
for st in styles:
    names = [n for n in R if n.split("_")[1] == st]
    if not names:
        continue
    w, h = Image.open(R[names[0]][0][2]).size
    cols = max(len(R[n]) for n in names)
    sheet = Image.new("RGB", (cols * w, len(names) * (h + 16)), "white")
    d = ImageDraw.Draw(sheet)
    for r, n in enumerate(names):
        for c, (f, tag, p) in enumerate(R[n]):
            sheet.paste(Image.open(p), (c * w, r * (h + 16) + 16))
            d.text((c * w + 4, r * (h + 16) + 2), "%s f%d %s" % (n.replace("Sky_", ""), f, tag), fill="black")
    out = os.path.join(D, "sheet_style_%s.png" % st)
    sheet.save(out)
    print(out, sheet.size)
