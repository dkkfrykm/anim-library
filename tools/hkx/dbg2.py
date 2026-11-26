import sys, math
sys.path.insert(0, "C:/Users/mytwo/soulbound/skyrim/tools")
import phase2 as P2
S = P2.S
skel = S.hkx.load(S.SKEL)["skeletons"][0]
c = P2.Clip("x", "Sky_Generic_P2", "Dash", {}, skel)
print("src marks", c.mk["w"], c.mk["i"], c.mk.get("hit_raw"), "s0", c.s0, "sw", c.sw_, "si", c.si, "sr", c.sr)
for f in (0, 5, 8, 11, 18):
    sf = c.warp(f)
    Pm, p, Wd = c.sample(sf)
    L = P2.local_of(Pm)
    def e(q): return tuple(round(math.degrees(a)) for a in q.to_euler("XYZ"))
    pel = Wd[c.src.idx["NPC Pelvis"]][0]; spn = Wd[c.src.idx["NPC Spine2"]][0]
    print(f, round(sf,1), "Root", e(L["Root"]), "Waist", e(L["Waist"]), "p", tuple(round(v,2) for v in p), "src pelvis z", round(pel.z), "spine2", tuple(round(v) for v in spn))
