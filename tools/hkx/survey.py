# Decode every HKX under src/ (except the skeleton mod) and write out/survey.json + out/survey.txt:
# per clip: moveset, file, frames, fps, duration, track count, rot quant types, data-length check, annotations.
import sys, os, json, re, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkx

SRC = "C:/Users/mytwo/soulbound/skyrim/src"
OUT = "C:/Users/mytwo/soulbound/skyrim/out"
rows = []
for mod in sorted(os.listdir(SRC)):
    if mod.startswith("XP32"):
        continue
    for dp, dn, fn in os.walk(os.path.join(SRC, mod)):
        for f in sorted(fn):
            if not f.lower().endswith(".hkx"):
                continue
            p = os.path.join(dp, f).replace("\\", "/")
            row = dict(mod=mod, file=f, path=p, cond=os.path.basename(dp))
            try:
                r = hkx.load(p)
                a = r["anims"][0]
                fr = hkx.sample_frames(a)  # exercises full decompression
                anns = sorted((round(t, 3), s) for _, l in a["annotations"] for t, s in l)
                row.update(frames=a["numFrames"], fps=round(1 / a["frameDuration"], 2), duration=round(a["duration"], 3),
                           tracks=a["ntt"], floats=a["nft"], rq=a["rotQuantStats"], blocks=a["numBlocks"],
                           bytes_ok=abs(a["blockEnds"][-1] + a["blockOffsets"][-1] - a["dataLen"]) < 16,
                           annotations=anns, t2b=len(r["bindings"][0]["t2b"]))
            except Exception as e:
                row["error"] = "%s: %s" % (type(e).__name__, e)
            rows.append(row)
json.dump(rows, open(os.path.join(OUT, "survey.json"), "w"), indent=0)
ok = [r for r in rows if "error" not in r]
print("total", len(rows), "decoded", len(ok), "bytes_ok", sum(1 for r in ok if r["bytes_ok"]))
from collections import Counter
print("rq", Counter(k for r in ok for k in r["rq"]), "tracks", Counter(r["tracks"] for r in ok), "fps", Counter(r["fps"] for r in ok))
for r in rows:
    if "error" in r: print("ERR", r["path"], r["error"])
    elif not r["bytes_ok"]: print("BYTES", r["path"])
with open(os.path.join(OUT, "survey.txt"), "w") as fh:
    for r in rows:
        if "error" in r:
            fh.write("%s | %s | ERROR %s\n" % (r["mod"], r["file"], r["error"])); continue
        hit = [t for t, s in r["annotations"] if s.lower() == "hitframe"]
        sw = [t for t, s in r["annotations"] if s.lower() == "weaponswing" or s.lower() == "weaponleftswing"]
        fh.write("%s | %s/%s | %d fr @%g = %.3fs | swing %s | hit %s\n" % (r["mod"], r["cond"], r["file"], r["frames"], r["fps"], r["duration"], sw, hit))
