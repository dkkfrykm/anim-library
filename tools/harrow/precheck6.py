# Static pre-check of phase-6 authored poses (no Blender): guard must be flag-free; key poses report flags not covered
# by the technique's allow list. Also lists guard-to-guard distances (shared/near-identical guards).
# Run: python precheck6.py B1 [B2 ...] | --powers a,b
import sys, os, math, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import powers6 as PW, posecheck as PC

STATIC = {"pop", "foot_slide"}


def flags(pose, allow=()):
    f = PC.check([pose], allow=set(allow) | STATIC, windows=[(0, 0)])
    return sorted(k for k in f if k not in STATIC)


def gdist(a, b):
    d = sum(PC.angle(PC.R(a.get(j, (0, 0, 0))), PC.R(b.get(j, (0, 0, 0)))) for j in PC.ORDER)
    pa, pb = a.get("p", (0, 0, 0)), b.get("p", (0, 0, 0))
    return d + 60 * math.dist(pa, pb)


def main():
    PW.load_all()
    a = sys.argv[1:]
    pids = a[a.index("--powers") + 1].split(",") if "--powers" in a else [p for b in a for p in PW.BATCHES[b]]
    guards, bad = {}, 0
    for pid in pids:
        spec = PW.POWERS[pid]()
        g = spec["guard"]
        if g is None:
            continue
        guards[pid] = g
        gf = flags(g)
        if gf:
            print("GUARD", pid, gf); bad += 1
        for slot, t in spec["slots"].items():
            if t.get("p4") or t.get("sword_direct"):
                continue
            for k in ("chamber", "strike", "retract"):
                if t.get(k):
                    f = flags(t[k], t.get("allow", ()))
                    if f:
                        print("  %s %s %s %s" % (pid, slot, k, f)); bad += 1
            for a_, o, pose, e in t.get("extra", ()):
                pose = PW.M(g, *pose) if isinstance(pose, (list, tuple)) else pose
                f = flags(pose, t.get("allow", ()))
                if f:
                    print("  %s %s extra@%s%+d %s" % (pid, slot, a_, o, f)); bad += 1
            for fr, pose in t.get("loop", ()) or ():
                f = flags(pose, t.get("allow", ()))
                if f:
                    print("  %s %s loop@%d %s" % (pid, slot, fr, f)); bad += 1
    print("issues", bad)
    if len(guards) > 1:
        ds = sorted((gdist(guards[x], guards[y]), x, y) for x, y in itertools.combinations(guards, 2))
        print("closest guards:", ", ".join("%s|%s %.0f" % (x, y, d) for d, x, y in ds[:8]))


if __name__ == "__main__":
    main()
