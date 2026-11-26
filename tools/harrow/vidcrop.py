import sys, cv2
from PIL import Image
v = cv2.VideoCapture(sys.argv[1]); n = int(v.get(cv2.CAP_PROP_FRAME_COUNT))
a, b, k = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
x0, y0, x1, y1 = map(float, sys.argv[6].split(","))
ims = []
for i in range(k):
    p = a + (b - a) * i // (k - 1)
    v.set(cv2.CAP_PROP_POS_FRAMES, p); ok, fr = v.read()
    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)); W, H = im.size
    im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))).resize((300, 360))
    ims.append(im)
out = Image.new("RGB", (300 * k, 360)); [out.paste(im, (i * 300, 0)) for i, im in enumerate(ims)]
out.save(sys.argv[2]); print(n, out.size)
