# Modular component library over the HKX catalog: tagged footwork / torso / arm-strike / leg-strike segments.
# A segment = (decoded clip, anchor frame @60fps [hit or peak], part, tags, metrics). The Blender combiner (phase6.py)
# aligns each component's anchor to the slot's impact frame and merges parts: footwork = pelvis + legs, torso =
# Waist/Neck relative to the hips, arm = shoulder..wrist relative to the torso.
# Run: python components6.py   -> out/catalog/components.json ; query from code: pick(part, need=[tags], avoid=[tags], ...)
import os, sys, json, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CAT = os.path.join(ROOT, "out", "catalog", "catalog.json")
OUT = os.path.join(ROOT, "out", "catalog", "components.json")


def footwork_tags(r):
    t = []
    f, s, trn = r["fwd"], r["side"], r["turn"]
    if r["travel"] < 25: t.append("planted")
    elif abs(f) >= abs(s): t.append("advance" if f > 0 else "retreat")
    else: t.append("sidestep_r" if s > 0 else "sidestep_l")
    if r["travel"] > 200: t.append("long")
    if abs(trn) > 270: t.append("spin")
    elif abs(trn) > 90: t.append("pivot")
    if r["rise"] > 25: t.append("airborne")
    if r["drop"] > 20: t.append("crouch")
    if r["cat"] == "dodge": t.append("dodge")
    if "dash" in r["tags"] or "sprint" in r["clip"]: t.append("dash")
    return t


def build():
    cat = json.load(open(CAT))
    comps = []
    for r in cat:
        if "error" in r:
            continue
        base = dict(clip=r["decoded"], source=r["source"], set=r["set"], name=r["clip"], cat=r["cat"], weapon=r["weapon"],
                    dur=r["dur"], frames60=round(r["dur"] * 60))
        hits60 = [round(h * 60) for h in r["hits"]] or [r["peak60"]]
        if r["cat"] in ("attack", "dodge", "locomotion", "jump_air", "block_parry", "cast", "misc", "idle", "hit_reaction"):
            anchor = r["pelpeak60"] if r["cat"] in ("dodge", "locomotion", "jump_air") else hits60[0]
            comps.append(dict(base, id="%s/%s#foot" % (r["set"], r["clip"]), part="footwork", anchor=anchor,
                              tags=footwork_tags(r) + [r["cat"]], travel=r["travel"], fwd=r["fwd"], side=r["side"], turn=r["turn"]))
        if r["cat"] in ("attack", "cast", "block_parry", "idle", "misc"):
            comps.append(dict(base, id="%s/%s#torso" % (r["set"], r["clip"]), part="torso", anchor=hits60[0],
                              tags=[r["cat"]] + (["twist"] if abs(r["turn"]) > 60 else []) + (["lean"] if r["lean"] > 45 else []) + (["heavy"] if "heavy" in r["tags"] else []),
                              turn=r["turn"], lean=r["lean"]))
        if r["cat"] in ("attack", "cast", "block_parry"):
            sp = r["speed"]
            for k, h in enumerate(hits60[:4]):
                for limb, part in (("rhand", "arm_R"), ("lhand", "arm_L"), ("rfoot", "leg_R"), ("lfoot", "leg_L")):
                    if sp[limb] >= 0.55 * max(sp[x] for x in ("rhand", "lhand", "rfoot", "lfoot")):
                        comps.append(dict(base, id="%s/%s#%s@%d" % (r["set"], r["clip"], part, k), part=part, anchor=h, hit=k,
                                          tags=[r["cat"]] + [t for t in r["tags"] if t in ("heavy", "weapon", "multihit", "kick", "hand")],
                                          speed=sp[limb]))
    json.dump(comps, open(OUT, "w"), indent=0)
    from collections import Counter
    print("components", len(comps), Counter(c["part"] for c in comps))
    print("footwork tags", Counter(t for c in comps if c["part"] == "footwork" for t in c["tags"]).most_common(14))


_C = None
# set 3 (src3, added 2026-11-23): opt-in only. pick() returns these only when `sets` names them explicitly, so every
# existing build (which queries without naming a set-3 source) keeps its exact component choices.
SET3 = ("For Honor", "Smooth Moveset", "BFCO ER Katana", "Goetia", "Smooth Magic", "YY Animation Replacer", "LightGreatswords",
        "Elder Creed", "BFCO Version", "Elden Rim", "Elden Sword", "Elden Stingers")


def is_set3(setname):
    return any(setname.startswith(k) for k in SET3)


def pick(part, need=(), avoid=(), weapon=None, sets=None, exclude_sets=(), used=(), key=None, n=1, avoid_name=None):
    """query the library: all `need` tags present, no `avoid` tags; optional weapon flag / set filters; returns best n"""
    global _C
    if _C is None:
        _C = json.load(open(OUT))
    out = []
    for c in _C:
        if c["part"] != part or c["id"] in used:
            continue
        if any(t not in c["tags"] for t in need) or any(t in c["tags"] for t in avoid):
            continue
        if weapon is not None and c["weapon"] != weapon:
            continue
        if sets and not any(s.lower() in c["set"].lower() for s in sets):
            continue
        if is_set3(c["set"]) and not (sets and any(s.lower() in c["set"].lower() for s in sets)):
            continue
        if avoid_name and re.search(avoid_name, c["name"].lower()):  # e.g. casting-set locomotion filed under "cast"
            continue
        if any(s.lower() in c["set"].lower() for s in exclude_sets):
            continue
        out.append(c)
    out.sort(key=key or (lambda c: -(c.get("speed") or c.get("travel") or 0)))
    return out[:n] if n else out


if __name__ == "__main__":
    build()
