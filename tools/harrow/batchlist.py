# Build out/batch_clips.json ([path, clipName]) for every surveyed HKX. Names: Sky_<Set>_<A|P><n> or Sky_<Set>_<Misc>.
import json, re, os
OUT = "C:/Users/mytwo/harrow/anim/out"
SET = {"HeavyBlade": "Heavy", "Kingsglaive": "Glaive", "MCO Normal": "Generic", "Rapier": "Rapier",
       "Reversed Dual Dagger": "Dagger", "Scythe": "Scythe", "Shinobi Magic": "ShinMagic", "Shinobi Normal": "Shinobi",
       "Sword": "Sword", "Unarmed Normal and Power Combo": "Skysa", "Unarmed Normal and Power For": "Unarmed"}
rows = json.load(open(os.path.join(OUT, "survey.json")))
out, seen = [], set()
for r in rows:
    st = next(v for k, v in SET.items() if r["mod"].startswith(k))
    f = os.path.splitext(r["file"])[0].lower()
    m = re.match(r"(?:mco_|skysa_)?(power)?(?:attack|h2h)(\d+)$", f)
    if m:
        tag = ("P" if m.group(1) else "A") + m.group(2)
    else:
        tag = re.sub(r"[^A-Za-z0-9]", "", f.title())
    name = "Sky_%s_%s" % (st, tag)
    k = 2
    base = name
    while name in seen:  # e.g. Kingsglaive has a second condition folder
        name = "%s_%d" % (base, k); k += 1
    seen.add(name)
    out.append([r["path"], name])
json.dump(out, open(os.path.join(OUT, "batch_clips.json"), "w"), indent=0)
print(len(out), [n for _, n in out][:200])
