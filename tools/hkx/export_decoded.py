# Rig-neutral decoded cache: one gzip JSON per unique HKX clip with Skyrim-skeleton LOCAL transforms per frame
# (native ~30 fps) + annotations, so other projects can retarget without re-decoding.
# Usage: python -I export_decoded.py <in_root> [<in_root2> ...] --out <dir> [--skeleton skeleton.hkx]
# File schema (<dir>/<SetOrFolder>/<clip>.json.gz):
#   {"source": path, "fps": f, "frameDuration": s, "numFrames": n, "duration": s,
#    "tracks": [bone names, track order], "t2b": [skeleton bone index per track],
#    "frames": [[ [tx,ty,tz, qx,qy,qz,qw, sx,sy,sz], ...per track ], ...per frame],
#    "annotations": [[time_s, text], ...]}
#   <dir>/skeleton.json: {"bones", "parents", "ref": [{"t","q","s"}]} (bind pose, local).
# Axes: Skyrim model space, X right, Y forward, Z up; units ~1.428 cm.
import sys, os, json, gzip, hashlib
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkx

DEFAULT_SKEL = os.environ.get("SKYRIM_SKELETON") or ("C:/Users/mytwo/soulbound/skyrim/src/XP32 Maximum Skeleton Special Extended/Skeleton Rig/HDT/"
                "meshes/actors/character/character assets/skeleton.hkx")


def one(args):
    path, outp, names = args
    try:
        r = hkx.load(path)
        a = r["anims"][0]
        t2b = r["bindings"][0]["t2b"] or list(range(a["ntt"]))
        fr = hkx.sample_frames(a)
        anns = sorted((round(t, 4), s) for _, l in a["annotations"] for t, s in l if s)
        d = dict(source=path, fps=round(1 / a["frameDuration"], 4), frameDuration=a["frameDuration"], numFrames=a["numFrames"],
                 duration=a["duration"], tracks=[names[i] if 0 <= i < len(names) else "track%d" % i for i in t2b], t2b=t2b,
                 frames=[[[round(v, 4) for v in t] + [round(v, 6) for v in q] + [round(v, 4) for v in s] for t, q, s in row] for row in fr],
                 annotations=anns)
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        with gzip.open(outp, "wt") as fh:
            json.dump(d, fh, separators=(",", ":"))
        return True
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)


def main():
    args = sys.argv[1:]
    out = args[args.index("--out") + 1]
    skel = args[args.index("--skeleton") + 1] if "--skeleton" in args else DEFAULT_SKEL
    roots = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
    sk = hkx.load(skel)["skeletons"][0]
    os.makedirs(out, exist_ok=True)
    json.dump(dict(bones=sk["bones"], parents=sk["parents"], ref=sk["ref"]), open(os.path.join(out, "skeleton.json"), "w"))
    seen, jobs, names_used = set(), [], {}
    for root in roots:
        for dp, dn, fn in os.walk(root):
            for f in sorted(fn):
                if not f.lower().endswith(".hkx") or "skeleton" in f.lower():
                    continue
                p = os.path.join(dp, f)
                try:
                    h = hashlib.md5(open(hkx.longpath(p), "rb").read()).hexdigest()
                except OSError:
                    continue
                if h in seen:
                    continue
                seen.add(h)
                top = os.path.relpath(p, root).split(os.sep)[0]
                base = os.path.splitext(f)[0].lower()
                k = names_used.get((top, base), 0) + 1
                names_used[(top, base)] = k
                jobs.append((p, os.path.join(out, top, base + ("" if k == 1 else "__%d" % k) + ".json.gz"), sk["bones"]))
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, jobs, chunksize=8))
    ok = sum(1 for r in res if r is True)
    print("decoded", ok, "of", len(jobs), "unique clips ->", out)
    for (p, o, _), r in zip(jobs, res):
        if r is not True:
            print("FAIL", p, r)


if __name__ == "__main__":
    main()
