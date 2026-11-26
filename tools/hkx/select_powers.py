# Per-power clip selection from the unified pool (out/pool.json) -> out/power_mapping.json.
# Each power gets its own set: M1_1..4 + one clip per ability Kind in its kit (E/R/F) + Ult (G).
# Archetype references (offline only) decide which source sets a power draws from.
import json, os, sys

OUT = "C:/Users/mytwo/soulbound/skyrim/out"
POOL = json.load(open(os.path.join(OUT, "pool.json")))
for _c in POOL:  # motion signature: identical moves copied across condition folders differ only in bytes
    _c["md5"] = "%s|%s|%s" % (round(_c["duration"], 2), _c["hits"], round(_c["peak"], 1))

KITS = {  # pid: (style, kinds used by E/R/F, M1 limb class, sets in priority order)
    "demonhunter": ("Blade", ["Bolt", "Burst"], "blade", ["SwordB", "Gauntlet"]),
    "bladedancer": ("Blade", ["Bolt", "Burst"], "blade", ["SwordD", "Dagger"]),
    "soulblade": ("Blade", ["Bolt", "Blast"], "blade", ["SwordC", "SwordD"]),
    "sunblade": ("Blade", ["Bolt", "Burst"], "blade", ["Heavy", "SwordC"]),
    "soulrequiem": ("Blade", ["Bolt", "Burst"], "blade", ["Glaive", "SwordC"]),
    "eclipsemonarch": ("Spirit", ["Blast", "Burst"], "blade", ["Dagger", "SwordD", "ShinMagic"]),
    "eclipseblacksun": ("Spirit", ["Bolt", "Burst"], "blade", ["Dagger", "SwordB", "ShinMagic"]),
    "flamefist": ("Fighter", ["Bolt", "Burst"], "hand", ["Gauntlet", "BrawlB"]),
    "dragonfist": ("Fighter", ["Bolt", "Burst"], "any_unarmed", ["Gauntlet", "Feral"]),
    "thunderfist": ("Fighter", ["Bolt", "Burst"], "hand", ["Mech", "Gauntlet"]),
    "brawler": ("Fighter", ["Blast", "Burst"], "hand", ["BrawlB", "Unarmed"]),
    "boxer": ("Fighter", ["Blast"], "hand", ["BrawlB", "Skysa", "Unarmed"]),
    "karate": ("Fighter", ["Bolt", "Blast"], "any_unarmed", ["UnarmedB", "KickSet", "Unarmed"]),
    "windfist": ("Fighter", ["Bolt", "Blast"], "kick", ["Agile", "KickSet"]),
    "frosttouch": ("Fighter", ["Bolt", "Blast"], "hand", ["UnarmedB", "Unarmed", "Skysa"]),
    "speedster": ("Fighter", ["Dash", "Blast"], "hand", ["Agile", "Unarmed"]),
    "phantomstep": ("Fighter", ["Dash", "Burst"], "any_unarmed", ["Agile", "Shinobi"]),
    "kicker": ("Fighter", ["Burst", "Blast"], "kick", ["KickSet", "Unarmed"]),
    "acrobat": ("Fighter", ["Dash", "Burst", "Blast"], "kick", ["Agile", "KickSet"]),
    "limitbreaker": ("Fighter", ["Blast", "Bolt"], "hand", ["Mech", "Flight"]),
    "overdrive": ("Titan", ["Blast", "Burst"], "hand", ["Mech", "Flight"]),
    "ironbody": ("Titan", ["Blast", "Burst"], "hand", ["Flight", "BrawlB"]),
    "titanstrength": ("Titan", ["Blast", "Bolt"], "hand", ["Flight", "Heavy"]),
    "unitedmight": ("Titan", ["Blast", "Bolt"], "hand", ["Flight", "Gauntlet"]),
    "elasticemperor": ("Titan", ["Bolt", "Blast"], "any_unarmed", ["Agile", "Flight"]),
    "beastform": ("Beast", ["Bolt", "Burst"], "any_unarmed", ["Feral", "Scythe"]),
    "dragonshift": ("Beast", ["Bolt", "Burst"], "any_unarmed", ["Feral", "Gauntlet"]),
    "chakra": ("Mystic", ["Blast", "Burst"], "any", ["ShinMagic", "Shinobi"]),
    "psychic": ("Mystic", ["Bolt", "Blast"], "any", ["ShinMagic", "Flight"]),
    "chakramaster": ("Mystic", ["Blast", "Burst"], "any", ["Shinobi", "ShinMagic"]),
    "voidsovereign": ("Mystic", ["Bolt", "Blast"], "any", ["Shinobi", "ShinMagic", "Agile"]),
    "starbornascension": ("Mystic", ["Bolt"], "any", ["Flight", "ShinMagic"]),
    "astraloverlord": ("Mystic", ["Bolt", "Burst"], "any", ["Flight", "ShinMagic"]),
    "infinityarchitect": ("Mystic", ["Blast", "Bolt"], "any", ["ShinMagic", "Mech"]),
    "supernovagod": ("Mystic", ["Bolt", "Burst"], "any", ["Flight", "Gauntlet"]),
    "absoluteinfinity": ("Mystic", ["Blast", "Burst"], "any", ["Flight", "ShinMagic", "Agile"]),
    "divinesaiyan": ("Mystic", ["Bolt", "Blast"], "hand", ["Flight", "Agile"]),
    "stando": ("Spirit", ["Blast", "Burst"], "any", ["ShinMagic", "Shinobi"]),
}
TITAN = {"Titan"}
ULT_SLAM = {"titanstrength", "supernovagod", "divinesaiyan"}

used_global = {}


def limb_ok(c, cls):
    l = set(c["limbs"])
    if cls == "blade":
        return c["weapon"] and "WPN" in l
    if cls == "hand":
        return bool(l & {"RH", "LH"}) and not c["weapon"]
    if cls == "kick":
        return bool(l & {"RF", "LF"}) and not c["weapon"]
    if cls == "any_unarmed":
        return not c["weapon"]
    return True


def cands(sets, cls, pred):
    out = []
    base = pred
    pred = lambda c: base(c) and (c["drop"] <= 60 or base is RULES["UltSlam"]) and c["lean"] <= 95
    for si, s in enumerate(sets):
        for c in POOL:
            if c["set"] != s or not pred(c):
                continue
            if not limb_ok(c, cls) and not (cls == "any" and True):
                continue
            pen = si * 15 + used_global.get(c["code"], 0) * 15 + max(0, c["lean"] - 70) * 0.15
            out.append((c["score"] - pen, c))
    out.sort(key=lambda x: -x[0])
    return [c for _, c in out]


RULES = {
    "M1": lambda c: c["kind"] in ("attack", "sprint") and len(c["hits"]) <= 2 and c["first_hit"] <= 0.65 and c["air"] <= 45,
    "Bolt": lambda c: len(c["hits"]) == 1 and c["first_hit"] <= 0.95 and c["air"] <= 60,
    "Blast": lambda c: len(c["hits"]) <= 2 and c["air"] <= 70,
    "Burst": lambda c: len(c["hits"]) >= 2,
    "Dash": lambda c: c["kind"] in ("sprint", "dodge") or c["first_hit"] <= 0.35,
    "Ult": lambda c: len(c["hits"]) >= 3,
    "UltSlam": lambda c: c["air"] >= 50 and c["peak"] >= 30,
}


def pick(sets, cls, rule, used, n=1):
    got = []
    for c in cands(sets, cls, RULES[rule]):
        if c["md5"] in used:
            continue
        got.append(c); used.add(c["md5"])
        if len(got) == n:
            break
    if len(got) < n:  # relax limb class, then sets
        for c in cands(sets, "any", RULES[rule]) + cands(sets, "any", lambda c: True):
            if c["md5"] in used:
                continue
            got.append(c); used.add(c["md5"])
            if len(got) == n:
                break
    for c in got:
        used_global[c["code"]] = used_global.get(c["code"], 0) + 1
    return got


def main():
    mapping, report = {}, {}
    for pid, (style, kinds, cls, sets) in KITS.items():
        used = set()
        m1 = pick(sets, cls, "M1", used, 4)
        rows = {}
        for k, c in enumerate(m1):
            rows["M1_%d" % (k + 1)] = (c, "M1_4" if k == 3 else "M1")
        for kd in kinds:
            c = pick(sets, cls if kd != "Dash" else "any", kd, used, 1)
            if c:
                rows[kd] = (c[0], kd)
        u = pick(sets, "any", "UltSlam" if pid in ULT_SLAM else "Ult", used, 1) or pick(sets, "any", "Burst", used, 1)
        if u:
            rows["Ult"] = (u[0], "Ult")
        for suffix, (c, slot) in rows.items():
            tgt = "Sky_%s_%s" % (pid, suffix)
            mapping[tgt] = dict(path=c["path"], code=c["code"], slot=slot, titan=style in TITAN, loop=(suffix == "M1_4" and style == "Blade"))
            report.setdefault(pid, []).append("%s<-%s(%s %s h%d %.2fs)" % (suffix, c["code"], c["moveset"][:18], c["file"][:22], len(c["hits"]), c["first_hit"]))
    json.dump(mapping, open(os.path.join(OUT, "power_mapping.json"), "w"), indent=1)
    with open(os.path.join(OUT, "power_mapping.txt"), "w", encoding="utf-8") as fh:
        for pid, l in report.items():
            fh.write("%s: %s\n" % (pid, "; ".join(l)))
    print(len(mapping), "clips for", len(report), "powers")


if __name__ == "__main__":
    main()
