import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decode import ang
d = json.load(open(sys.argv[1]))
names = sys.argv[2:]
fr = d["frames"]
steps = []
for t, n in enumerate(d["tracks"]):
    m = max(ang(fr[f][t][1], fr[f - 1][t][1]) for f in range(1, len(fr)))
    steps.append((round(m, 1), n))
steps.sort(reverse=True)
print(steps[:12])
for n in names:
    t = d["tracks"].index(n)
    for f in range(len(fr)):
        print(f, n, fr[f][t][1], round(ang(fr[f][t][1], fr[max(0, f - 1)][t][1]), 1))
