"""Retarget whole HKX clips to R15 rows (Blender background) and dump them as JSON for th_authored.py to compose.
Run from C:/Users/mytwo/harrow/anim (src/src2/src3 junctions):
  blender --background --factory-startup --python tools/th_direct.py -- <jobs.json>
jobs.json: [[catalog_set, catalog_clip, out_name], ...]  -> out/direct/<out_name>.json {n, src, frames:[{joint:[x,y,z], p:[x,y,z]}]}
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky2r15 as S
import hkx

argv = sys.argv[sys.argv.index("--") + 1:]
jobs = json.load(open(argv[0]))
cat = json.load(open("out/catalog/catalog.json"))
idx = {(r["set"], r["clip"]): r for r in cat}
skel = hkx.load(S.SKEL)["skeletons"][0]
os.makedirs("out/direct", exist_ok=True)
for st, clip, name in jobs:
    r = idx[(st, clip)]
    src, rt, mk, frames, worlds = S.convert(r["source"], skel)
    rows = [{k: [round(float(x), 3) for x in v] for k, v in fr.items()} for fr in frames]
    json.dump(dict(n=len(rows), src="%s/%s" % (st, clip), frames=rows), open(os.path.join("out/direct", name + ".json"), "w"))
    print("direct", name, len(rows), r["source"][-60:])
