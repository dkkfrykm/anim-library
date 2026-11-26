# Report distinctness for a set of powers from a simil.py result: pairs below threshold (default karate|boxer).
import sys, json
r = json.load(open(sys.argv[1])); pids = sys.argv[2].split(",")
thr = float(sys.argv[3]) if len(sys.argv) > 3 else r["dist"]["boxer|karate"]
print("threshold %.1f" % thr)
for p in pids:
    rel = sorted((v, k) for k, v in r["dist"].items() if p in k.split("|") and v is not None)
    low = [(v, k) for v, k in rel if v < thr]
    g = sorted((v, k) for k, v in r["guard"].items() if p in k.split("|"))
    print("%-16s min %6.1f (%s)  below:%d  closest guard %.0f (%s)" % (p, rel[0][0], rel[0][1], len(low), g[0][0], g[0][1]))
    for v, k in low[:6]:
        print("      %-34s %.1f" % (k, v))
