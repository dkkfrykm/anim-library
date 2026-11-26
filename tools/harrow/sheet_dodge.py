"""Stick contact sheet for the set-4 clips: frames 0 / w / i / r / end, front-3/4 view. python -E -P sheet4.py"""
import sys, os, json, math, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import posecheck as PC
from PIL import Image, ImageDraw
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'th_auth')
rows = json.load(open(os.path.join(OUT, 'rows_dodge.json')))
lua = {}
for f in os.listdir(OUT):
    if f.startswith('Clips_TH_'):
        for m in re.finditer(r'(\w+)=\{n=(\d+),w=(\d+),i=\{([\d,]*)\},r=(\d+)', open(os.path.join(OUT, f)).read()):
            lua[m.group(1)] = (int(m.group(2)), int(m.group(3)), [int(x) for x in m.group(4).split(',') if x], int(m.group(5)))
BONES = [('Root', 'Waist'), ('Waist', 'Neck'), ('Neck', 'RightShoulder'), ('RightShoulder', 'RightElbow'), ('RightElbow', 'RightWrist'),
         ('Neck', 'LeftShoulder'), ('LeftShoulder', 'LeftElbow'), ('LeftElbow', 'LeftWrist'), ('Root', 'RightHip'), ('RightHip', 'RightKnee'),
         ('RightKnee', 'RightAnkle'), ('Root', 'LeftHip'), ('LeftHip', 'LeftKnee'), ('LeftKnee', 'LeftAnkle')]
names = sorted(rows)
W, H, S = 150, 190, 26
img = Image.new('RGB', (W * 5 + 160, H * len(names)), (24, 26, 32)); d = ImageDraw.Draw(img)
yaw = math.radians(35)
def pj(p, ox, oy):
    x = p[0] * math.cos(yaw) + p[2] * math.sin(yaw)
    return ox + W / 2 + x * S, oy + H * 0.62 - p[1] * S
for r, nm in enumerate(names):
    rr = rows[nm]; n = len(rr)
    mk = lua.get(nm)
    fr = [0, mk[1], mk[2][0] if mk[2] else n // 2, min(mk[3], n - 1), n - 1] if mk and mk[2] else [0, n // 4, n // 2, 3 * n // 4, n - 1]
    d.text((6, r * H + 8), nm, fill=(230, 230, 230))
    for c, f in enumerate(fr):
        ox, oy = 160 + c * W, r * H
        pos, rot, hand, foot = PC.fk(rr[f])
        for a, b in BONES:
            if a in pos and b in pos:
                col = (240, 140, 60) if 'Right' in b else (90, 200, 110) if 'Left' in b else (200, 200, 210)
                d.line([pj(pos[a], ox, oy), pj(pos[b], ox, oy)], fill=col, width=3)
        for s, col in (('Right', (255, 170, 80)), ('Left', (120, 230, 140))):
            x, y = pj(hand[s], ox, oy); d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=col)
        x, y = pj(pos['Neck'], ox, oy); d.ellipse((x - 7, y - 16, x + 7, y - 2), outline=(220, 220, 220))
        d.text((ox + 4, oy + H - 16), 'f%d' % f, fill=(160, 160, 170))
img.save(os.path.join(OUT, 'dodge_sheet.png'))
print(len(names), 'clips')
