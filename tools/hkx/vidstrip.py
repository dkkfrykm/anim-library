import sys, cv2
from PIL import Image
v = cv2.VideoCapture(sys.argv[1]); n = int(v.get(cv2.CAP_PROP_FRAME_COUNT)); fps = v.get(cv2.CAP_PROP_FPS)
k = int(sys.argv[3]) if len(sys.argv) > 3 else 12
picks = [int(i * (n - 1) / (k - 1)) for i in range(k)]
ims = []
for p in picks:
    v.set(cv2.CAP_PROP_POS_FRAMES, p); ok, fr = v.read()
    if ok: ims.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
w, h = ims[0].size; s = 360 / w
ims = [im.resize((360, int(h * s))) for im in ims]
cols = 6; H = ims[0].size[1]
out = Image.new("RGB", (360 * cols, H * ((len(ims) + cols - 1) // cols)), "white")
for i, im in enumerate(ims): out.paste(im, ((i % cols) * 360, (i // cols) * H))
out.save(sys.argv[2]); print(n, fps, out.size)
