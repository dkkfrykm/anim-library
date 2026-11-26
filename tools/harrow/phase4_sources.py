# Phase 4 dynamics-source picker: for each technique slot, choose an UNARMED Skyrim clip whose striking limb matches
# the technique and which is not a weapon-style swing (raw weapon-tip dominant), to provide body dynamics/timing only.
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import survey2

OUT = "C:/Users/mytwo/harrow/anim/out"
POOL = json.load(open(os.path.join(OUT, "pool.json")))
UNARMED = ["Unarmed", "Skysa", "BrawlB", "UnarmedB", "Mech", "Gauntlet", "Feral", "Agile", "KickSet"]
_raw = {}


def raw_limbs(c):
    if c["path"] not in _raw:
        _raw[c["path"]] = survey2.analyse(c["path"]).get("limbs", [])
    return _raw[c["path"]]


def pick(limb, used, sets=UNARMED, multi=False):
    best = None
    for c in POOL:
        if c["set"] not in sets or c["code"] in used:
            continue
        if c["drop"] > 40 or c["lean"] > 75 or c["air"] > 35:
            continue
        if multi != (len(c["hits"]) >= 2):
            continue
        if c["limbs"][0] != limb:
            continue
        if "WPN" in raw_limbs(c):  # sword-like arc even in an unarmed set
            continue
        sc = c["score"] - sets.index(c["set"]) * 3
        if best is None or sc > best[0]:
            best = (sc, c)
    if best:
        used.add(best[1]["code"])
        return best[1]
    return None


def main():
    plan = json.load(open(os.path.join(OUT, "phase4", "techniques_plan.json")))
    res = {}
    for power, slots in plan.items():
        used = set()
        for slot, (tech, limb, multi, sets) in slots.items():
            c = pick(limb, used, sets or UNARMED, multi) or pick(limb, used, UNARMED, multi) or pick(limb, used, UNARMED, not multi)
            res["Sky_%s_%s" % (power, slot)] = dict(tech=tech, code=c["code"], path=c["path"], src_file=c["file"], src_set=c["set"])
            print(power, slot, tech, "<-", c["code"], c["file"], c["limbs"])
    json.dump(res, open(os.path.join(OUT, "phase4", "sources.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
