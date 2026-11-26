import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkx
R = "C:/Users/mytwo/soulbound/skyrim/src/XP32 Maximum Skeleton Special Extended/Skeleton Rig/%s/meshes/actors/character/character assets/skeleton.hkx"
sk = {v: hkx.load(R % v)["skeletons"][0] for v in ("HDT", "HDT 4.51", "TBBP")}
a = sk["HDT"]
for v, s in sk.items():
    same = 0
    for i in range(min(len(s["bones"]), len(a["bones"]))):
        if s["bones"][i] != a["bones"][i] or s["parents"][i] != a["parents"][i]:
            break
        same += 1
    refsame = all(abs(x - y) < 1e-4 for i in range(97) for x, y in zip(s["ref"][i]["q"] + s["ref"][i]["t"], a["ref"][i]["q"] + a["ref"][i]["t"]))
    print(v, len(s["bones"]), "common prefix", same, "ref97 same", refsame)
for i in range(100):
    print(i, a["parents"][i], a["bones"][i], [round(x, 2) for x in a["ref"][i]["t"]], [round(x, 3) for x in a["ref"][i]["q"]])
