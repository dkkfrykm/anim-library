# Phase-6 batch B2: elemental / power fists. Fire = explosive, forward, hip-driven, ignition; lightning = surgical,
# abrupt accel/decel, minimal motion; strength = commitment and weight. See powers6.py for the DSL.
from powers6 import *


@power("B2")
def flamefist():  # fire brawler-gauntlet: fists chambered at the hips, deep forward lunge, hip-driven thrusts, ignition flicks
    g = M(legs(lh=(44, 0, -14), lk=-70, la=10, rh=(-24, 0, 16), rk=-12, ra=14), body(root=(0, -35, 0), waist=(2, -8, 0), neck=(-2, 38, 0), p=(0, -0.55, 0)),
          A("R", (-15, 25, -10), 95), A("L", (-5, -25, 10), 95))
    hot = dict(legs=0.25, torso=0.25, p=0.3)
    def drive(side, k=1.0):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (-40, 20, -15), 110), Bd(g, -16 * d, 2, (0, -0.04, 0.1))],
                  [A(side, (86, 0, -4), 0), A(other(side), (-40, 25, -10), 110), Bd(g, 30 * d * k, -8, (0, -0.12, -0.36 * k), LeftKnee=-56)],
                  extra=[("h", 2, [A(side, (84, 0, -4), 4, (-30, 0, 0)), Bd(g, 26 * d, -6, (0, -0.1, -0.32 * k))], "io")], ws=hot)
    palm = T6(g, [A("L", (-30, 20, -10), 110, (-50, 0, 0)), Bd(g, 14, 0, (0, -0.04, 0.08))],
              [A("L", (78, 0, -4), 6, (-70, 0, 0)), Bd(g, -26, -8, (0, -0.12, -0.3), LeftKnee=-54)], ws=hot)
    rising = T6(g, [A("R", (-10, 10, 10), 70), Bd(g, -12, -8, (0, -0.2, 0.04), LeftKnee=-62)],
                [A("R", (100, 0, -12), 60), Bd(g, 18, 6, (0, 0.04, -0.12))], allow=("elbow_up", "hand_in_head", "hands_up"), ws=hot,
                extra=[("h", 3, [A("R", (95, 0, -12), 70), Bd(g, 14, 4, (0, 0.0, -0.1))], "io")])
    twin = T6(g, [A2((-45, 20, -10), 115), Bd(g, 0, 4, (0, -0.02, 0.14))], [A2((80, 10, -8), 2), Bd(g, 4, -10, (0, -0.16, -0.46), LeftKnee=-60)],
              extra=[("w", -4, [A2((-30, 20, -10), 110), Bd(g, 0, 0, (0, -0.1, 0.08))], "slow"),
                     ("h", 3, [A2((76, 10, -8), 8, (-40, 0, 0)), Bd(g, 4, -8, (0, -0.14, -0.4))], "io")], ws=hot, wend=14)
    ignite = T6(g, [A("R", (-30, 30, -10), 120, (40, 0, 0)), Bd(g, -20, 0, (0, -0.04, 0.06))],
                [A("R", (84, 0, -4), 0, (-60, 0, 0)), Bd(g, 28, -8, (0, -0.12, -0.34), LeftKnee=-56)], ws=hot,
                extra=[("w", -5, [A("R", (-10, 40, -10), 130, (60, 0, 0)), Bd(g, -24, 2, (0, -0.06, 0.08))], "snap")])
    burst = rush4(drive("R"), drive("L"), drive("R"), palm)
    dash = T6(g, [A2((-45, 20, -10), 115), Bd(g, 0, -6, (0, -0.14, 0.1), LeftKnee=-64)], [A("R", (86, 0, -4), 0), A("L", (-40, 25, -10), 110), Bd(g, 26, -14, (0, -0.2, -0.6), LeftKnee=-62)], es="expo", ws=hot)
    ult = dict(rush(drive("R", 1.2), drive("L", 1.2)))
    ult["extra"] = [("w", -12, [A2((-45, 20, -10), 115), Bd(g, 0, 6, (0, -0.24, 0.12), LeftKnee=-66)], "slow"), ("w", -4, [A2((-60, 20, -10), 120), Bd(g, 0, 8, (0, -0.28, 0.16))], "slow")]
    ult["ws"] = hot
    s = {"M1_1": meta(palm, "open-palm flare", foot=["advance"], side="L"),
         "M1_2": meta(drive("R"), "hip-chambered fire thrust", foot=["advance", "attack"], torso=["attack", "twist"]),
         "M1_3": meta(ignite, "ignition snap thrust", foot=["advance"], torso=["attack", "twist"]),
         "M1_4": meta(rising, "rising flame uppercut finisher", foot=["crouch"], torso=["attack", "heavy"]),
         "Bolt": meta(twin, "twin fire drive", foot=["advance"], torso=["attack"]),
         "Burst": meta(burst, "piston fire barrage", foot=["advance"]),
         "Dash": meta(dash, "flame-step lunge (mobility)", foot=["advance", "long"]),
         "Ult": meta(ult, "inferno drive: coil and erupt", foot=["advance"], torso=["attack", "heavy"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.03, period=24, breath=3, drift=4, shift=0.02))


@power("B2")
def thunderfist():  # lightning: tall bouncing stance, long lead hand, near-instant jabs that stop dead
    g = M(legs(lh=(14, 0, -8), lk=-18, la=10, rh=(-4, 0, 8), rk=-14, ra=16), body(root=(0, -30, 0), waist=(-2, -6, 0), neck=(0, 30, 0), p=(0, -0.1, 0)),
          A("L", (62, -12, 0), 55), A("R", (32, 48, 0), 118))
    sharp = dict(legs=0.12, torso=0.1, p=0.15)
    jab = T6(g, [A("L", (55, -15, 0), 70), Bd(g, -2)], [A("L", (90, 0, -4), 0), Bd(g, -8, -2, (0, -0.02, -0.14))], es="expo", ws=sharp)
    dbl = T6(g, [A("L", (55, -15, 0), 70)], [A("L", (90, 0, -4), 0), Bd(g, -8, -2, (0, -0.02, -0.14))], es="expo", ws=sharp, wend=14,
             extra=[("i", -4, [A("L", (90, 0, -4), 0), Bd(g, -6, 0, (0, -0.02, -0.08))], "expo"), ("i", -2, [A("L", (60, -12, 0), 60)], "expo")])
    cross = T6(g, [A("R", (30, 50, 0), 120)], [A("R", (90, 0, -6), 0), A("L", (40, -40, 0), 110), Bd(g, 22, -4, (0, -0.06, -0.18), LeftKnee=-30)], es="expo", ws=sharp)
    spear = T6(g, [A("R", (20, 50, 0), 125), Bd(g, -6, 0, (0, -0.02, 0.04))], [A("R", (90, 0, -6), 0, (-20, 0, 0)), A("L", (30, -40, 0), 115), Bd(g, 26, -6, (0, -0.08, -0.34), LeftKnee=-36)],
               es="expo", ws=sharp, extra=[("h", 1, [A("R", (90, 0, -6), 0, (-20, 0, 0)), Bd(g, 26, -6, (0, -0.08, -0.34))], "hold")])
    chop = T6(g, [A("R", (68, 45, 0), 95)], [A("R", (60, 0, -10), 10, (20, 0, 0)), Bd(g, 18, -6, (0, -0.06, -0.16))], es="expo", ws=sharp, allow=("hand_in_head",))
    blitz = rush4(jab, cross, jab, cross)
    blink = T6(g, [A("L", (62, -12, 0), 55), Bd(g, 0, 0, (0, -0.06, 0))], [A("R", (90, 0, -6), 0), A("L", (40, -40, 0), 110), Bd(g, 24, -6, (0, -0.06, -0.5), LeftKnee=-34)], es="expo", ws=sharp)
    ult = dict(rush4(jab, cross, dbl, spear))
    ult["extra"] = [("w", -10, [A("L", (62, -12, 0), 55), Bd(g, 0, 0, (0, -0.02, 0.02))], "hold"), ("w", -2, [A("R", (20, 50, 0), 125)], "expo")]
    ult["ws"] = sharp
    s = {"M1_1": meta(jab, "lightning jab", foot=["planted"], side="L"),
         "M1_2": meta(dbl, "double jab snap", foot=["advance"], side="L"),
         "M1_3": meta(cross, "flash cross", foot=["planted", "attack"]),
         "M1_4": meta(spear, "spear hand finisher", foot=["advance"], torso=["attack"]),
         "Bolt": meta(chop, "thunder chop", foot=["planted"]),
         "Burst": meta(blitz, "snap blitz", foot=["planted"]),
         "Dash": meta(blink, "blink step strike (mobility)", foot=["dodge", "advance"]),
         "Ult": meta(ult, "stillness then storm", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.05, period=24, breath=1, shift=0.02))


@power("B2")
def speedster():  # blur: sprinter's forward lean, arms low and back, strikes come in flurries
    g = M(legs(lh=(40, 0, -8), lk=-60, la=10, rh=(-20, 0, 8), rk=-30, ra=20), body(root=(-14, -8, 0), waist=(-10, -2, 0), neck=(18, 6, 0), p=(0, -0.3, 0)),
          A("R", (-30, 0, 20), 60), A("L", (-30, 0, 20), 60))
    blur = dict(legs=0.3, torso=0.2, p=0.35)
    def flurry(lead):
        o = other(lead)
        t = T6(g, [A(lead, (20, 30, 0), 110), Bd(g, 0, 0, (0, -0.02, 0.04))], [A(lead, (86, 0, -4), 0), A(o, (30, 30, 0), 110), Bd(g, 14 if lead == "R" else -14, -4, (0, -0.06, -0.2))],
               es="expo", ws=blur, wend=16,
               extra=[("h", 1, [A(lead, (40, 30, 0), 100), A(o, (86, 0, -4), 0), Bd(g, -12 if lead == "R" else 12, -4, (0, -0.06, -0.22))], "expo"),
                      ("h", 4, [A(lead, (86, 0, -4), 0), A(o, (40, 30, 0), 100), Bd(g, 12 if lead == "R" else -12, -4, (0, -0.06, -0.24))], "expo"),
                      ("h", 7, [A(lead, (20, 30, 0), 100), A(o, (20, 30, 0), 100), Bd(g, 0, -2, (0, -0.04, -0.1))], "io")])
        return t
    knee = kick(g, "R", "knee", arms=M(A("R", (-30, 0, 20), 60), A("L", (-30, 0, 20), 60)), stl=Bd(g, 0, 4, (0, 0.04, -0.2)), es="expo")
    knee["ws"] = blur
    spin = T6(g, [A("R", (40, 0, 50), 60), Bd(g, 30, 0, (0, -0.04, 0.04))], [A("R", (70, -10, 60), 10), Bd(g, -60, -4, (0, -0.06, -0.18))], es="expo", ws=blur,
              allow=("crossed_knees", "elbow_up"))
    zip_ = T6(g, [A2((-40, 0, 20), 50), Bd(g, 0, -10, (0, -0.16, 0.06), LeftKnee=-66)], [A("R", (86, 0, -4), 0), A("L", (-40, 0, 20), 50), Bd(g, 20, -16, (0, -0.2, -0.66), LeftKnee=-60)], es="expo", ws=blur)
    stormfists = rush4(flurry("R"), flurry("L"), flurry("R"), flurry("L"))
    ult = dict(rush4(flurry("R"), spin, flurry("L"), knee))
    ult["extra"] = [("w", -8, [A2((-45, 0, 20), 50), Bd(g, 0, -12, (0, -0.2, 0.08), LeftKnee=-66)], "slow")]
    s = {"M1_1": meta(flurry("R"), "triple blur jab", foot=["advance", "dash"]),
         "M1_2": meta(flurry("L"), "triple blur jab (left lead)", foot=["advance"], side="L"),
         "M1_3": meta(knee, "running knee", foot=["advance"], kick="R"),
         "M1_4": meta(spin, "whirl backfist finisher", foot=["pivot"], torso=["attack", "twist"]),
         "Blast": meta(stormfists, "hundred-fist storm (heavy)", foot=["planted"]),
         "Dash": meta(zip_, "zip strike (mobility)", foot=["dash"]),
         "Ult": meta(ult, "afterimage barrage", foot=["advance"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.035, period=24, shift=0.06, breath=2))


@power("B2")
def overdrive():  # cyborg pistons: rigid square stance, forearms level, linear stepped extension, zero torso give
    g = M(legs(lh=(10, 0, -24), lk=-36, rh=(4, 0, 24), rk=-36), body(root=(-4, -15, 0), waist=(-2, -2, 0), neck=(6, 16, 0), p=(0, -0.36, 0)),
          A("R", (-20, 10, 4), 100), A("L", (70, -5, 0), 10))
    rigid = dict(legs=0.08, torso=0.05, p=0.1)
    def piston(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (-45, 10, 4), 120), Bd(g, -20 * d, 0, (0, 0, 0.06))], [A(side, (88, 0, 0), 0), Bd(g, 25 * d, 0, (0, 0, -0.16))],
                  ec="step", es="lin", ws=rigid, extra=[("h", 3, [A(side, (88, 0, 0), 0)], "hold"), ("h", 6, [A(side, (40, 8, 4), 60)], "step")])
    dpist = T6(g, [A2((-25, 10, 4), 105), Bd(g, 0, 0, (0, 0, 0.06))], [A2((86, 0, 0), 0), Bd(g, 0, 0, (0, -0.02, -0.18))], ec="step", es="lin", ws=rigid,
               extra=[("h", 4, [A2((86, 0, 0), 0)], "hold")])
    drill = T6(g, [A("R", (-20, 10, 4), 100, (0, 0, 0))], [A("R", (88, 0, 0), 0, (0, 0, 0)), Bd(g, 6, 0, (0, 0, -0.14))], ec="step", es="lin", ws=rigid, wend=16,
               extra=[("h", 2, [A("R", (88, 0, 0), 0, (0, 60, 0))], "lin"), ("h", 5, [A("R", (88, 0, 0), 0, (0, 120, 0))], "lin"), ("h", 8, [A("R", (88, 0, 0), 0, (0, 180, 0))], "lin")])
    hammer = T6(g, [A("R", (80, 0, 85), 0), Bd(g, 60, 0, (0, 0, 0))], [A("R", (85, 0, -10), 0), Bd(g, -30, 0, (0, -0.02, -0.06))], ec="step", es="step", ws=rigid,
                allow=("elbow_up", "hands_up", "crossed_knees"), extra=[("w", -3, [A("R", (80, 0, 85), 0), Bd(g, 30, 0, (0, 0, 0))], "step")])
    boost = T6(g, [A2((-30, 10, 4), 110), Bd(g, 0, -8, (0, -0.1, 0.04))], [A2((86, 0, 0), 0), Bd(g, 0, -10, (0, -0.12, -0.6))], ec="step", es="expo", ws=rigid)
    gatling = rush4(piston("R"), piston("L"), piston("R"), piston("L"))
    ult = dict(rush(piston("R"), piston("L")))
    ult["extra"] = [("w", -12, [A2((-30, 10, 4), 110), Bd(g, 0, 0, (0, -0.04, 0.06))], "step"), ("w", -6, [A2((-40, 10, 4), 115)], "step")]
    s = {"M1_1": meta(piston("R"), "piston punch", foot=["planted"]),
         "M1_2": meta(piston("L"), "piston punch (left)", foot=["planted"], side="L"),
         "M1_3": meta(hammer, "rotor arm sweep", foot=["planted"]),
         "M1_4": meta(dpist, "twin piston finisher", foot=["advance"]),
         "Blast": meta(drill, "drill fist (heavy)", foot=["planted"]),
         "Burst": meta(gatling, "gatling pistons", foot=["planted"]),
         "Dash": meta(boost, "thruster boost (mobility)", foot=["dash"]),
         "Ult": meta(ult, "overclock: charge and fire", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, breath=0.6, drift=0))


@power("B2")
def dragonfist():  # kung fu dragon: low sideways horse stance, claw hands, circular parries into palms, flowing
    g = M(legs(lh=(16, 0, -32), lk=-58, rh=(16, 0, 32), rk=-58), body(root=(0, -40, 0), waist=(0, -6, 0), neck=(0, 42, 0), p=(0, -0.5, 0)),
          A("L", (65, -25, 10), 45, (-55, 0, 0)), A("R", (25, 45, 0), 115, (-55, 0, 0)))
    flow = dict(legs=0.15, torso=0.2, p=0.15)
    circle = T6(g, [A("L", (60, 30, -30), 40, (-40, 0, 0)), A("R", (10, 30, 0), 110, (-60, 0, 0)), Bd(g, -10, 0, (0, -0.02, 0.04))],
                [A("L", (30, 10, 40), 50, (-40, 0, 0)), A("R", (84, 0, -4), 4, (-70, 0, 0)), Bd(g, 30, -4, (0, -0.06, -0.22))], ws=flow,
                extra=[("w", -3, [A("L", (70, 0, 0), 40, (-40, 0, 0))], "io")])
    claw = T6(g, [A("L", (75, -10, 45), 50, (-50, 0, 0)), Bd(g, 16, 0, (0, 0.02, 0.04))], [A("L", (45, 20, -30), 30, (-55, 0, 0)), Bd(g, -26, -6, (0, -0.1, -0.24))], ws=flow,
               allow=("elbow_up", "hand_in_head"))
    tail = kick(g, "R", "low", arms=M(A("L", (65, -25, 10), 45, (-55, 0, 0)), A("R", (25, 45, 0), 115, (-55, 0, 0))), chl=Bd(g, 10, 0, (0, -0.06, 0)), stl=Bd(g, 50, 0, (0, -0.12, -0.04)))
    tail["ws"] = flow
    dclaw = T6(g, [A2((20, 35, 10), 95, (-55, 0, 0)), Bd(g, 0, 0, (0, -0.06, 0.08))], [A2((75, 10, -8), 20, (-60, 0, 0)), Bd(g, 10, -8, (0, -0.14, -0.3))], ws=flow, wend=14,
               extra=[("h", 3, [A2((70, 15, -20), 30, (-60, 0, 0)), Bd(g, 8, -6, (0, -0.12, -0.26))], "io")])
    pearl = T6(g, [A2((20, 30, 0), 110, (-60, 0, 0)), Bd(g, 0, 0, (0, -0.14, 0.08))], [A2((75, 15, -10), 6, (-75, 0, 0)), Bd(g, 0, -6, (0, -0.16, -0.26))], ws=flow, ec="io",
               extra=[("w", -6, [A("R", (60, 30, -30), 40, (-40, 0, 0)), A("L", (60, 30, -30), 40, (-40, 0, 0)), Bd(g, -8, 0, (0, -0.1, 0.04))], "io")])
    coil = T6(g, [A("L", (65, -25, 10), 45, (-55, 0, 0)), Bd(g, -20, 0, (0, -0.06, 0.04))], [A("R", (80, 0, -4), 10, (-60, 0, 0)), A("L", (30, -20, 30), 60), Bd(g, 30, -6, (0, -0.14, -0.5))], ws=flow, es="io")
    storm = rush(claw, circle)
    ult = dict(rush(circle, dclaw))
    ult["extra"] = [("w", -12, [A("L", (60, 30, -30), 40, (-40, 0, 0)), A("R", (60, 30, -30), 40, (-40, 0, 0)), Bd(g, -12, 0, (0, -0.12, 0.04))], "io")]
    s = {"M1_1": meta(circle, "circular parry into palm", foot=["planted"], torso=["attack"]),
         "M1_2": meta(claw, "dragon claw rake", foot=["planted"], side="L"),
         "M1_3": meta(tail, "dragon tail sweep", foot=["planted", "crouch"], kick="R"),
         "M1_4": meta(dclaw, "twin dragon claws finisher", foot=["advance"], torso=["attack"]),
         "Bolt": meta(pearl, "dragon pearl double palm", foot=["planted"]),
         "Burst": meta(storm, "claw-and-circle cycle", foot=["planted"]),
         "Dash": meta(coil, "coiling dragon step (mobility)", foot=["advance", "long"]),
         "Ult": meta(ult, "nine dragons cycle", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.008, period=96, sway=6, drift=8, breath=2))


@power("B2")
def ironbody():  # sumo / strongman: very wide rooted stance, open palms forward, slow heavy teppo and charges
    g = M(legs(lh=(14, 0, -38), lk=-62, rh=(14, 0, 38), rk=-62), body(root=(-8, 0, 0), waist=(-6, 0, 0), neck=(10, 0, 0), p=(0, -0.55, 0)),
          A2((35, 25, 0), 35, (-60, 0, 0)))
    heavy = dict(legs=0.1, torso=0.15, p=0.15)
    def teppo(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (20, 30, 0), 100, (-60, 0, 0)), Bd(g, -10 * d, 2, (0, -0.02, 0.06))],
                  [A(side, (80, 0, -6), 4, (-75, 0, 0)), A(other(side), (20, 25, 0), 60, (-60, 0, 0)), Bd(g, 16 * d, -8, (0, -0.06, -0.28))],
                  ec="slow", ws=heavy, extra=[("h", 3, [A(side, (78, 0, -6), 6, (-72, 0, 0)), Bd(g, 14 * d, -6, (0, -0.06, -0.26))], "hold")])
    charge = T6(g, [A2((10, 20, 10), 110), Bd(g, -30, 0, (0, -0.04, 0.08))], [A("L", (25, -40, 0), 120), A("R", (0, 20, 15), 100), Bd(g, -55, -12, (0.1, -0.08, -0.4))],
                ec="slow", ws=heavy, allow=("crossed_knees",))
    stomp = kick(g, "R", "knee", arms=A2((20, 0, 40), 20, (-40, 0, 0)), stl=Bd(g, 0, 0, (0, 0.08, 0)), es="slow")
    stomp["strike"] = M(g, A2((20, 0, 40), 20, (-40, 0, 0)), Bd(g, 0, -8, (0, -0.6, -0.04)))
    stomp["allow"] = ("crossed_knees",)
    stomp["ws"] = heavy
    dteppo = T6(g, [A2((15, 30, 0), 105, (-60, 0, 0)), Bd(g, 0, 4, (0, -0.02, 0.1))], [A2((78, 10, -6), 4, (-75, 0, 0)), Bd(g, 0, -10, (0, -0.1, -0.36))], ec="slow", ws=heavy, wend=14,
                extra=[("w", -6, [A2((5, 30, 0), 110, (-60, 0, 0)), Bd(g, 0, 6, (0, 0.0, 0.12))], "slow")])
    flurry = rush4(teppo("R"), teppo("L"), teppo("R"), teppo("L"))
    sumo_dash = T6(g, [A2((35, 25, 0), 35, (-60, 0, 0)), Bd(g, 0, -10, (0, -0.06, 0.06))], [A2((70, 15, -4), 10, (-75, 0, 0)), Bd(g, 0, -16, (0, -0.1, -0.6))], ws=heavy)
    ult = dict(rush(teppo("R"), teppo("L")))
    ult["extra"] = [("w", -14, [A2((20, 0, 40), 20, (-40, 0, 0)), Bd(g, 0, 0, (0, -0.1, 0))], "slow"), ("w", -6, [A2((15, 30, 0), 105, (-60, 0, 0)), Bd(g, 0, 4, (0, -0.6, 0.06))], "slow")]
    s = {"M1_1": meta(teppo("R"), "teppo palm thrust", foot=["planted"]),
         "M1_2": meta(teppo("L"), "teppo palm thrust (left)", foot=["planted"], side="L"),
         "M1_3": meta(charge, "shoulder charge", foot=["advance"], torso=["attack", "heavy"]),
         "M1_4": meta(dteppo, "double teppo finisher", foot=["advance"]),
         "Blast": meta(stomp, "shiko stomp (heavy)", foot=["planted"], kick="R"),
         "Burst": meta(flurry, "tsuppari slap barrage", foot=["planted"]),
         "Dash": meta(sumo_dash, "tachiai charge (mobility)", foot=["advance", "long"]),
         "Ult": meta(ult, "stomp, set, tsuppari", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.01, period=96, shift=0.08, breath=3))


@power("B2")
def titanstrength():  # colossal: upright square, arms hanging wide, overhead hammer-fists and ground pounds, huge wind-ups
    g = M(legs(lh=(6, 0, -20), lk=-22, rh=(6, 0, 20), rk=-22), body(root=(0, -6, 0), waist=(2, 0, 0), neck=(-4, 4, 0), p=(0, -0.12, 0)),
          A2((32, 15, 24), 75))
    huge = dict(legs=0.15, torso=0.2, p=0.2)
    def hammer(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (85, 10, 40), 120), Bd(g, -14 * d, 6, (0, 0.06, 0.06))], [A(side, (55, 10, -10), 20), Bd(g, 16 * d, -16, (0, -0.24, -0.2), LeftKnee=-40)],
                  ec="slow", ws=huge, allow=("elbow_up", "hands_up", "hand_in_head"),
                  extra=[("w", -4, [A(side, (80, 10, 45), 115), Bd(g, -16 * d, 8, (0, 0.08, 0.08))], "slow")])
    pound = T6(g, [A("R", (50, 30, 20), 95), Bd(g, -10, 0, (0, 0.04, 0.04))], [A("R", (40, 0, -5), 0), A("L", (20, 0, 30), 40), Bd(g, 10, -30, (0, -0.55, -0.2), LeftKnee=-70, RightKnee=-56)],
               ec="slow", ws=huge, allow=("elbow_up", "extreme_lean"))
    slam2 = T6(g, [A2((88, 0, 15), 60), Bd(g, 0, 8, (0, 0.08, 0.06))], [A2((50, 0, 5), 10), Bd(g, 0, -24, (0, -0.5, -0.22), LeftKnee=-66, RightKnee=-60)],
               ec="slow", ws=huge, allow=("elbow_up", "hands_up", "hand_in_head"), wend=14,
               extra=[("w", -6, [A2((80, 0, 20), 70), Bd(g, 0, 10, (0, 0.1, 0.1))], "slow"), ("h", 4, [A2((48, 0, 5), 14), Bd(g, 0, -22, (0, -0.48, -0.2))], "hold")])
    bolt = T6(g, [A2((30, 20, 0), 100), Bd(g, 0, 0, (0, -0.06, 0.06))], [A2((80, 10, -8), 4), Bd(g, 0, -10, (0, -0.16, -0.34), LeftKnee=-44)], ec="slow", ws=huge)
    quake = dict(slam2, extra=[("w", -14, [A2((40, 0, 35), 60), Bd(g, 0, 4, (0, -0.2, 0.04))], "slow"), ("w", -6, [A2((88, 0, 15), 60), Bd(g, 0, 10, (0, 0.12, 0.08))], "slow")])
    stomp = kick(g, "R", "knee", arms=A2((25, 10, 40), 40), stl=Bd(g, 0, 4, (0, 0.1, 0)), es="slow")
    stomp["strike"] = M(g, A2((25, 10, 40), 40), Bd(g, 0, -12, (0, -0.5, -0.06), LeftKnee=-50, RightKnee=-40))
    stomp["extra"] = [("i", -3, M(g, A2((25, 10, 40), 40), P(RightHip=(100, 0, 20), RightKnee=(-100, 0, 0)), Bd(g, 0, 6, (0, 0.12, 0))), "slow")]
    stomp["allow"] = ("crossed_knees",); stomp["ws"] = huge
    leap = T6(g, [A2((20, 10, 28), 45), Bd(g, 0, -6, (0, -0.3, 0.04), LeftKnee=-60, RightKnee=-60)], [A2((60, 0, 10), 10), Bd(g, 0, -14, (0, -0.4, -0.5), LeftKnee=-64, RightKnee=-50)], ws=huge, es="slow")
    ult = dict(slam2)
    ult["extra"] = [("w", -16, [A2((40, 0, 35), 60), Bd(g, 0, 4, (0, -0.24, 0.04), LeftKnee=-56, RightKnee=-56)], "slow"),
                    ("w", -6, [A2((88, 0, 15), 60), Bd(g, 0, 10, (0, 0.16, 0.08))], "slow"),
                    ("h", 6, [A2((48, 0, 5), 14), Bd(g, 0, -22, (0, -0.48, -0.2))], "hold")]
    s = {"M1_1": meta(hammer("R"), "hammer fist", foot=["planted"]),
         "M1_2": meta(hammer("L"), "hammer fist (left)", foot=["planted"], side="L"),
         "M1_3": meta(stomp, "titan stomp", foot=["planted"], kick="R"),
         "M1_4": meta(pound, "ground pound finisher", foot=["planted", "crouch"], torso=["heavy"]),
         "Blast": meta(quake, "earthquake double-axe (heavy)", foot=["planted"], torso=["heavy"]),
         "Bolt": meta(dict(bolt, ec="slow"), "titan shove wave", foot=["planted"]),
         "Dash": meta(leap, "titan bound (mobility)", foot=["advance", "long"]),
         "Ult": meta(ult, "colossus smash", foot=["planted"], torso=["heavy"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.01, period=96, breath=4, roll=2))


@power("B2")
def unitedmight():  # superhero: upright proud stance, fist ready, big clean heroic punches, flying punch
    g = M(legs(lh=(4, 0, -12), lk=-6, rh=(-4, 0, 12), rk=-6), body(root=(0, -15, 0), waist=(6, 0, 0), neck=(-8, 10, 0), p=(0, -0.04, 0)),
          A("R", (8, 0, 16), 25), A("L", (55, -30, 0), 100))
    hero = dict(legs=0.2, torso=0.2, p=0.25)
    hay = T6(g, [A("R", (30, -20, 55), 70), Bd(g, -28, 0, (0, -0.02, 0.1))], [A("R", (88, 5, -15), 4), A("L", (20, -30, 20), 60), Bd(g, 30, -8, (0, -0.1, -0.3), LeftKnee=-40)], ws=hero, allow=("elbow_up",))
    straight = T6(g, [A("L", (30, -40, 0), 110)], [A("L", (88, 0, -4), 0), A("R", (8, 0, 16), 30), Bd(g, -18, -4, (0, -0.06, -0.22), LeftKnee=-36)], ws=hero)
    upper = T6(g, [A("R", (10, 20, 10), 90), Bd(g, -10, -6, (0, -0.16, 0.02))], [A("R", (100, 0, -10), 60), Bd(g, 16, 8, (0, 0.06, -0.1))], ws=hero, allow=("elbow_up", "hand_in_head", "hands_up"))
    fly = T6(g, [A("R", (-20, 0, 20), 60), P(RightHip=(-20, 0, 12), RightKnee=(-50, 0, 0)), Bd(g, -10, -6, (0, -0.24, 0.06), LeftKnee=-50)],
             [A("R", (88, 0, -4), 0), A("L", (-10, 0, 25), 20), P(RightHip=(-30, 0, 12), RightKnee=(-20, 0, 0), LeftHip=(-10, 0, -12), LeftKnee=(-30, 0, 0)), Bd(g, 10, -20, (0, 0.3, -0.6))],
             ws=hero, wend=14, extra=[("h", 3, [A("R", (88, 0, -4), 0), Bd(g, 10, -18, (0, 0.26, -0.56))], "hold")])
    beam = T6(g, [A2((5, 40, 0), 100), Bd(g, -6, 2, (0, -0.06, 0.06))], [A2((84, 10, -10), 0), Bd(g, 0, -6, (0, -0.1, -0.24), LeftKnee=-36)], ws=hero)
    smash = T6(g, [A("R", (30, -20, 60), 70), Bd(g, -36, 4, (0, 0.0, 0.14))], [A("R", (88, 5, -15), 0), A("L", (0, -30, 30), 40), Bd(g, 36, -12, (0, -0.14, -0.42), LeftKnee=-48)],
               ws=hero, allow=("elbow_up",), extra=[("w", -8, [A("R", (20, -30, 60), 60), A("L", (55, -30, 0), 100), Bd(g, -40, 2, (0, -0.04, 0.16))], "slow")])
    ult = dict(fly)
    ult["extra"] = [("w", -14, [A("R", (8, 0, 16), 25), A("L", (8, 0, 16), 25), Bd(g, 0, 4, (0, -0.06, 0.02))], "slow"),
                    ("w", -6, [A("R", (-20, 0, 20), 60), Bd(g, -10, -8, (0, -0.3, 0.08), LeftKnee=-56)], "slow"),
                    ("h", 4, [A("R", (88, 0, -4), 0), Bd(g, 10, -18, (0, 0.28, -0.58))], "hold")]
    s = {"M1_1": meta(straight, "heroic straight", foot=["advance"], side="L"),
         "M1_2": meta(hay, "big right hook", foot=["advance", "attack"], torso=["attack", "twist"]),
         "M1_3": meta(upper, "rising uppercut", foot=["crouch"]),
         "M1_4": meta(fly, "flying punch finisher", foot=["advance", "airborne"]),
         "Blast": meta(smash, "planet-cracker haymaker (heavy)", foot=["advance"], torso=["heavy"]),
         "Bolt": meta(beam, "twin-fist shockwave", foot=["planted"]),
         "Dash": meta(dict(fly), "superman dash (mobility)", foot=["dash"]),
         "Ult": meta(ult, "united strike: rise and fly", foot=["advance", "airborne"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.005, period=96, breath=2.5, sway=3))
