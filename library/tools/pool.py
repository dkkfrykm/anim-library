# Unified, de-duplicated clip pool over src (MCO set 1) and src2 (set 2) with strike metrics.
# Every clip gets a GENERIC code (Sky_<SetCode>_<n>) used in-game; real set names stay in out/pool.json only.
import sys, os, json, hashlib, re
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import survey2

OUT = "C:/Users/mytwo/soulbound/skyrim/out"
SETCODE = {  # folder prefix -> generic code
    "HeavyBlade": "Heavy", "Kingsglaive": "Glaive", "MCO Normal": "Generic", "Rapier": "Rapier",
    "Reversed Dual Dagger": "Dagger", "Scythe": "Scythe", "Shinobi Magic": "ShinMagic", "Shinobi Normal": "Shinobi",
    "Sword Normal": "Sword", "Unarmed Normal and Power Combo": "Skysa", "Unarmed Normal and Power For": "Unarmed",
    "mco nero": "SwordB", "BFCO Dante": "Gauntlet", "BFCO MCO Phantom": "SwordC", "Swordplay": "SwordD",
    "MCO Spiderman": "Agile", "MCO SCAR": "Flight", "MCO Kamen": "KickSet", "MCO Ultimate Ultra": "BrawlB",
    "MCO Dwemer": "Mech", "MCO Eryx": "UnarmedB", "MCO Turbo": "Feral",
    # set 3 (src3, 2026-11-23)
    "For Honor": "Duelist", "Smooth Moveset": "SmoothMove", "BFCO ER Katana": "KatanaA", "Goetia": "CastA",
    "Smooth Magic": "CastB", "YY Animation Replacer - Zweihander": "GreatswordB", "YY Animation Replacer - Mystic": "SpellKnight",
    "LightGreatswords": "GreatswordL", "Elder Creed": "BladeE", "BFCO Version": "SwordE2", "Elden Rim x DS3": "KatanaDual",
    "Elden Sword": "SwordE", "Elden Stingers": "Stinger",
}
WEAPON_SETS = {"Heavy", "Glaive", "Generic", "Rapier", "Dagger", "Scythe", "Sword", "SwordB", "SwordC", "SwordD", "Shinobi"}


def code_of(moveset):
    for k, v in SETCODE.items():
        if moveset.startswith(k):
            return v
    return None


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def main():
    rows = json.load(open(os.path.join(OUT, "survey2.json")))
    src1 = []
    S1 = "C:/Users/mytwo/soulbound/skyrim/src"
    for dp, dn, fn in os.walk(S1):
        if "XP32" in dp:
            continue
        for f in fn:
            if f.lower().endswith(".hkx"):
                src1.append(os.path.join(dp, f).replace("\\", "/"))
    with ProcessPoolExecutor(max_workers=6) as ex:
        r1 = list(ex.map(survey2.analyse, sorted(src1)))
    for r in r1:
        rel = r["path"][len(S1) + 1:]
        r["moveset"] = rel.split("/")[0]; r["cond"] = rel.split("/")[-2]; r["file"] = rel.split("/")[-1]
    seen, pool = set(), []
    counters = {}
    for r in r1 + rows:
        if "error" in r or not r.get("hits") or "score" not in r:
            continue
        h = md5(r["path"])
        if h in seen:
            continue
        seen.add(h)
        c = code_of(r["moveset"])
        if not c:
            continue
        counters[c] = counters.get(c, 0) + 1
        f = r["file"].lower()
        kind = "power" if "power" in f else "attack"
        if "sprint" in f: kind = "sprint"
        if "dodge" in f: kind = "dodge"
        if "jump" in f: kind = "jump"
        limbs = r["limbs"]
        if c not in WEAPON_SETS:
            limbs = ["RH" if l == "WPN" else l for l in limbs]  # unarmed: weapon-tip speed = right hand
        r.update(code="Sky_%s_%d" % (c, counters[c]), set=c, kind=kind, limbs=limbs, md5=h, weapon=c in WEAPON_SETS)
        pool.append(r)
    json.dump(pool, open(os.path.join(OUT, "pool.json"), "w"), indent=0)
    from collections import Counter
    print(len(pool), "unique striking clips;", dict(Counter(p["set"] for p in pool)))


if __name__ == "__main__":
    main()
