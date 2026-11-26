import sys
from PIL import Image, ImageDraw
D = "C:/Users/mytwo/.claude/projects/C--Users-mytwo/a97c05fc-0d88-4ff2-a88c-55a4cc879ab6/tool-results/"
items = [("c2zde0", "f0 guard"), ("4imhd5", "f13 settle"), ("z4xxng", "f26 windup (swing)"), ("1wl3u9", "f33 IMPACT"), ("d25gq6", "f35 follow (default colours)"), ("4wzf7e", "f50 follow-through")]
ims = []
for k, lab in items:
    im = Image.open(D + "mcp-roblox-studio-blob-%s.jpg" % [n for n in __import__("os").listdir(D) if k in n][0].split("blob-")[1].split(".")[0]).crop((330, 20, 1230, 560)).resize((450, 270))
    ImageDraw.Draw(im).text((8, 8), "Sky_Sword_A1 " + lab, fill="black")
    ims.append(im)
out = Image.new("RGB", (450 * 3, 270 * 2), "white")
for i, im in enumerate(ims):
    out.paste(im, ((i % 3) * 450, (i // 3) * 270))
out.save("C:/Users/mytwo/soulbound/skyrim/out/studio_Sky_Sword_A1.png"); print(out.size)
