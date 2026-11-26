# Catalog every HKX under src2/ (offline only; source names stay out of the game).
# All files: duration, frames, annotations summary. Attack files (attack/powerattack/jump/sprint/dodge_attack):
# full decode + FK: striking limb per Hitframe, peak strike speed, snappiness (start/swing -> first hit), air time,
# max torso lean, root motion; quality score. Writes out/clip_catalog2.tsv + out/survey2.json.
import sys, os, json, re, math, traceback
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkx, decode, fk

SRC = "C:/Users/mytwo/soulbound/skyrim/src2"
OUT = "C:/Users/mytwo/harrow/anim/out"
ATTACK = re.compile(r"(attack|h2h)", re.I)
PARTS = {"RH": "NPC R Hand", "LH": "NPC L Hand", "RF": "NPC R Foot", "LF": "NPC L Foot"}


def analyse(path):
    row = dict(path=path)
    try:
        r = hkx.load(path)
        a = r["anims"][0]
        anns = sorted((round(t, 3), s) for _, l in a["annotations"] for t, s in l if s)
        row.update(frames=a["numFrames"], fps=round(1 / a["frameDuration"], 2), duration=round(a["duration"], 3),
                   tracks=a["ntt"], hits=[t for t, s in anns if s.lower() == "hitframe"],
                   swings=[t for t, s in anns if s.lower() in ("weaponswing", "weaponleftswing")],
                   motion=[s for t, s in anns if s.lower().startswith("animmotion")][-1:] or None)
        name = os.path.basename(path)
        if not ATTACK.search(name) or a["ntt"] > 130:
            return row
        d = decode.decode(path)
        B = d["skeleton"]["bones"]
        idx = {n.split(" [")[0]: i for i, n in enumerate(B)}
        W = [fk.world(d, f) for f in range(d["numFrames"])]
        fps = d["fps"]
        wi = idx["Weapon"]
        def tip(Wf):
            t, q = Wf[wi]
            v = decode.qrot(q, (0, 60, 0))
            return (t[0] + v[0], t[1] + v[1], t[2] + v[2])
        limbs, peak = [], 0.0
        for h in row["hits"] or []:
            f = int(round(h * fps))
            best = None
            for k, b in PARTS.items():
                i = idx[b]
                for g in range(max(1, f - 3), min(len(W), f + 5)):
                    v = math.dist(W[g][i][0], W[g - 1][i][0])
                    if best is None or v > best[0]:
                        best = (v, k)
            for g in range(max(1, f - 3), min(len(W), f + 5)):  # weapon tip (only meaningful for weapons)
                v = math.dist(tip(W[g]), tip(W[g - 1]))
                if best is None or v > best[0] * 1.6:
                    best = (v, "WPN")
            limbs.append(best[1]); peak = max(peak, best[0])
        pel = idx["NPC Pelvis"]; sp1 = idx["NPC Spine1"]; nk = idx["NPC Neck"]
        zs = [Wf[pel][0][2] for Wf in W]
        lean = 0.0
        for Wf in W:
            v = [Wf[nk][0][k] - Wf[sp1][0][k] for k in range(3)]
            L = math.sqrt(sum(x * x for x in v)) or 1
            lean = max(lean, math.degrees(math.acos(max(-1, min(1, v[2] / L)))))
        first = (row["hits"] or [None])[0]
        start = (row["swings"] or [0.0])[0] if row["swings"] else 0.0
        snap = round(first - (start if start < (first or 0) else 0), 3) if first is not None else None
        row.update(limbs=limbs, peak=round(peak * fps / 100, 2), air=round(max(zs) - zs[0], 1), drop=round(zs[0] - min(zs), 1),
                   lean=round(lean), snap=snap, first_hit=first)
        nh = len(row["hits"] or [])
        row["score"] = round(row["peak"] * 0.6 + min(nh, 5) * 0.5 - (first or 2) * 1.2 - max(0, lean - 55) * 0.05, 2)
    except Exception as e:
        row["error"] = "%s: %s" % (type(e).__name__, e)
    return row


def main():
    paths = []
    for dp, dn, fn in os.walk(SRC):
        for f in fn:
            if f.lower().endswith(".hkx"):
                paths.append(os.path.join(dp, f).replace("\\", "/"))
    paths.sort()
    with ProcessPoolExecutor(max_workers=6) as ex:
        rows = list(ex.map(analyse, paths, chunksize=8))
    for r in rows:
        rel = r["path"][len(SRC) + 1:]
        r["moveset"] = rel.split("/")[0]
        parts = rel.split("/")
        r["cond"] = parts[-2]
        r["file"] = parts[-1]
    json.dump(rows, open(os.path.join(OUT, "survey2.json"), "w"))
    cols = ["moveset", "cond", "file", "duration", "frames", "fps", "hits", "limbs", "first_hit", "snap", "peak", "air", "drop", "lean", "score", "motion", "error"]
    with open(os.path.join(OUT, "clip_catalog2.tsv"), "w", encoding="utf-8") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    ok = [r for r in rows if "error" not in r]
    att = [r for r in ok if "score" in r]
    print("files", len(rows), "decoded", len(ok), "attacks analysed", len(att), "errors", len(rows) - len(ok))
    errs = {}
    for r in rows:
        if "error" in r:
            errs.setdefault(r["error"][:60], 0); errs[r["error"][:60]] += 1
    print(errs)


if __name__ == "__main__":
    main()
