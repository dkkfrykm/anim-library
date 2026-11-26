import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkx
r = hkx.load(sys.argv[1])
print(r["version"], r["classes"])
for s in r.get("skeletons", []):
    print("skel", s["name"], len(s["bones"]), len(s["ref"]), s["bones"][:20])
for a in r.get("anims", []):
    print({k: a[k] for k in ("duration", "ntt", "nft", "numFrames", "numBlocks", "maxFPB", "mqs", "frameDuration",
                             "blockOffsets", "dataLen", "blockEnds", "rotQuantStats")})
    for n, anns in a["annotations"]:
        if anns: print("  ann", n, anns)
for bd in r.get("bindings", []):
    print("bind", bd["skel"], len(bd["t2b"]), bd["t2b"][:10])
