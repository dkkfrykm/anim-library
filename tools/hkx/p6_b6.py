# Phase-6 batch B6: the stand's own attack set (Clips_SkyStand, keyed by joint track; the Enigma stand body plays it).
# Identity: a floating fighter-spirit: upright, chin down, fists forward, legs trailing; straight rapid barrages.
from powers6 import *


@power("B6")
def Stand():
    g = M(legs(lh=(20, 0, -6), lk=-40, la=-30, rh=(6, 0, 6), rk=-50, ra=-30), body(root=(-6, -10, 0), waist=(-4, -4, 0), neck=(8, 10, 0), p=(0, 0.2, 0)),
          A("R", (40, 45, 0), 110), A("L", (50, -40, 0), 100))
    ws = dict(legs=0.0, torso=0.15, p=0.05)
    def straight(side, k=1.0):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (30, 50, 0), 120), Bd(g, -8 * d, 0, (0, 0, 0.04))], [A(side, (90, 0, -4), 0), A(other(side), (40, 45, 0), 115), Bd(g, 22 * d * k, -6, (0, 0, -0.3 * k))],
                  es="expo", ws=ws)
    heavy = T6(g, [A("R", (10, 40, 30), 120), Bd(g, -30, 2, (0, 0.04, 0.12))], [A("R", (90, 0, -4), 0), A("L", (20, -30, 20), 70), Bd(g, 34, -12, (0, -0.04, -0.5))], ws=ws, ec="slow",
                 extra=[("h", 4, [A("R", (88, 0, -4), 4), Bd(g, 30, -10, (0, -0.04, -0.46))], "hold")])
    upper = T6(g, [A("R", (0, 20, 10), 90), Bd(g, -10, -8, (0, -0.2, 0.02))], [A("R", (100, 0, -10), 60), Bd(g, 16, 10, (0, 0.2, -0.1))], ws=ws, allow=("elbow_up", "hand_in_head", "hands_up"))
    rush_ = T6(g, [A2((30, 50, 0), 120), Bd(g, 0, -8, (0, 0, 0.06))], [A("R", (90, 0, -4), 0), A("L", (30, 45, 0), 120), Bd(g, 20, -14, (0, -0.04, -0.66))], es="expo", ws=ws)
    barrage = rush4(straight("R"), straight("L"), straight("R"), straight("L"))
    ult = dict(barrage)
    ult["ec"] = "slow"  # wind-up comes from the chamber key
    s = {"M1_1": meta(straight("R"), "stand straight", foot=None), "M1_2": meta(straight("L"), "stand straight (left)", foot=None, side="L"),
         "Barrage": meta(barrage, "rapid-fist barrage", foot=None), "Heavy": meta(heavy, "heavy straight", foot=None),
         "Uppercut": meta(upper, "rising uppercut", foot=None), "Rush": meta(rush_, "lunging rush", foot=None),
         "Ult": meta(ult, "wind-up barrage", foot=None)}
    timing = {"M1_1": "M1", "M1_2": "M1", "Barrage": "Burst", "Heavy": "Blast", "Uppercut": "M1_4", "Rush": "Dash", "Ult": "Ult"}
    return dict(guard=g, slots=s, module="Clips_SkyStand", timing=timing, no_idle=True)
