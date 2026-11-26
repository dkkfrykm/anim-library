# Phase-6 batch B5: casters, each with its own gesture language (never high hands). Gravity = deliberate, oppressive,
# subtle gestures with huge force. DSL: powers6.py
from powers6 import *

SEAL = A2((45, 62, 0), 115, (-20, 0, 0))  # hands meet in front of the chest


@power("B5")
def chakra():  # hand seals at the chest, released as palm thrusts
    g = M(legs(lh=(14, 0, -12), lk=-22, rh=(-6, 0, 12), rk=-16, ra=8), body(root=(0, -18, 0), waist=(-2, -4, 0), neck=(0, 18, 0), p=(0, -0.18, 0)), SEAL)
    ws = dict(legs=0.15, torso=0.15, p=0.2)
    def palm(side):
        d = 1 if side == "R" else -1
        return T6(g, [SEAL, Bd(g, -6 * d, 0, (0, -0.04, 0.04))], [A(side, (74, 0, -4), 6, (-65, 0, 0)), A(other(side), (40, 50, 0), 110, (-20, 0, 0)), Bd(g, 24 * d, -6, (0, -0.08, -0.24), LeftKnee=-36)],
                  ws=ws, extra=[("w", -3, [A2((40, 66, 0), 118, (0, 0, 40)), Bd(g, 0, 0, (0, -0.06, 0.04))], "snap")])
    finger = T6(g, [SEAL], [A("R", (80, 5, -4), 0, (0, 0, 0)), A("L", (40, 55, 0), 110), Bd(g, 16, -4, (0, -0.06, -0.18))], es="expo", ws=ws)
    dpalm = T6(g, [SEAL, Bd(g, 0, 0, (0, -0.08, 0.08))], [A2((72, 12, -8), 8, (-65, 0, 0)), Bd(g, 0, -6, (0, -0.12, -0.3), LeftKnee=-40)], ws=ws, wend=14,
               extra=[("w", -5, [A2((40, 66, 0), 118, (0, 0, 40))], "snap"), ("w", -2, [A2((45, 62, 0), 115, (0, 0, -40))], "snap")])
    seals = dict(dpalm, extra=[("w", -14, [A2((40, 66, 0), 118, (0, 0, 40)), Bd(g, 0, 0, (0, -0.12, 0.06))], "snap"),
                               ("w", -10, [A2((45, 62, 0), 115, (0, 0, -40))], "snap"), ("w", -6, [A2((50, 60, 0), 110, (0, 0, 80))], "snap"),
                               ("w", -2, [SEAL, Bd(g, 0, 0, (0, -0.16, 0.08))], "snap")])
    shun = T6(g, [SEAL, Bd(g, 0, -8, (0, -0.2, 0.06), LeftKnee=-50)], [A("R", (74, 0, -4), 6, (-65, 0, 0)), A("L", (20, -20, 20), 40), Bd(g, 20, -14, (0, -0.2, -0.6), LeftKnee=-50)], es="expo", ws=ws)
    ult = dict(seals)
    s = {"M1_1": meta(dict(palm("R"), ws=dict(ws, legs=0.3, p=0.3)), "seal-release palm", foot=["advance"], torso=["cast"]),  # V7: stepping palms (vs psychic)
         "M1_2": meta(dict(palm("L"), ws=dict(ws, legs=0.3, p=0.3)), "seal-release palm (left)", foot=["advance"], side="L"),
         "M1_3": meta(finger, "two-finger chakra jab", foot=["advance"]),
         "M1_4": meta(dpalm, "double seal palm finisher", foot=["advance"], torso=["cast"]),
         "Blast": meta(seals, "seal chain release (heavy)", foot=["planted"], torso=["cast"]),
         "Burst": meta(rush(palm("R"), palm("L")), "palm volley", foot=["planted"]),
         "Dash": meta(shun, "body flicker (mobility)", foot=["dodge", "advance"]),
         "Ult": meta(ult, "full seal sequence", foot=["planted"], torso=["cast"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.006, period=96, breath=1.5))


@power("B5")
def chakramaster():  # two-hand orb held at the right hip (palm up below, palm down above), driven forward
    g = M(legs(lh=(22, 0, -14), lk=-36, rh=(-10, 0, 16), rk=-22, ra=10), body(root=(0, -34, 0), waist=(-4, -10, 0), neck=(2, 36, 0), p=(0, -0.3, 0)),
          A("R", (10, 30, 10), 85, (0, 0, -80)), A("L", (35, -40, -10), 110, (0, 0, 80)))
    ws = dict(legs=0.2, torso=0.2, p=0.2)
    orb = [A("R", (10, 30, 10), 85, (0, 0, -80)), A("L", (35, -40, -10), 110, (0, 0, 80))]
    drive = T6(g, orb + [Bd(g, -14, 0, (0, -0.06, 0.08))], [A("R", (78, 10, -6), 10, (0, 0, -80)), A("L", (82, -5, -10), 20, (0, 0, 80)), Bd(g, 30, -8, (0, -0.12, -0.36), LeftKnee=-48)], ws=ws)
    sweep = T6(g, orb + [Bd(g, -30, 0, (0, -0.04, 0.04))], [A("R", (70, -20, 60), 20, (0, 0, -80)), A("L", (75, -30, 40), 30, (0, 0, 80)), Bd(g, 30, -4, (0, -0.08, -0.16))], ws=ws, allow=("elbow_up",))
    slam = T6(g, [A("R", (50, 45, 10), 80, (0, 0, -80)), A("L", (58, 25, -10), 85, (0, 0, 80)), Bd(g, 0, 4, (0, 0.04, 0.04))],
              [A("R", (40, 20, 0), 20, (0, 0, -80)), A("L", (45, -10, 0), 30, (0, 0, 80)), Bd(g, 10, -18, (0, -0.32, -0.2), LeftKnee=-56)], ws=ws, ec="slow", allow=("elbow_up", "hand_in_head"))
    twin = T6(g, orb + [Bd(g, 0, 0, (0, -0.1, 0.08))], [A2((78, 15, -10), 10, (-60, 0, 0)), Bd(g, 0, -8, (0, -0.14, -0.34), LeftKnee=-48)], ws=ws, wend=14,
              extra=[("h", 3, [A2((74, 15, -10), 14, (-55, 0, 0)), Bd(g, 0, -6, (0, -0.12, -0.3))], "hold")])
    grow = dict(drive, ec="slow", extra=[("w", -12, orb + [Bd(g, -20, 0, (0, -0.16, 0.1))], "slow"), ("w", -6, [A("R", (0, 35, 15), 90, (0, 0, -80)), A("L", (40, -40, -10), 115, (0, 0, 80)), Bd(g, -24, 0, (0, -0.2, 0.12))], "slow")])
    dash = T6(g, orb + [Bd(g, 0, -8, (0, -0.16, 0.06))], [A("R", (78, 10, -6), 10, (0, 0, -80)), A("L", (82, -5, -10), 20, (0, 0, 80)), Bd(g, 24, -14, (0, -0.2, -0.62), LeftKnee=-56)], es="expo", ws=ws)
    ult = dict(grow)
    s = {"M1_1": meta(drive, "orb drive", foot=["advance"], torso=["cast"]),
         "M1_2": meta(sweep, "orb sweep", foot=["pivot"]),
         "M1_3": meta(slam, "orb slam down", foot=["planted"]),
         "M1_4": meta(twin, "twin orb thrust finisher", foot=["advance"], torso=["cast"]),
         "Blast": meta(grow, "spiralling orb (heavy)", foot=["advance"], torso=["cast"]),
         "Burst": meta(rush(drive, sweep), "orb barrage", foot=["planted"]),
         "Dash": meta(dash, "orb rush (mobility)", foot=["dash"]),
         "Ult": meta(ult, "great spiralling orb", foot=["advance"], torso=["cast"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.01, period=96, breath=2, sway=4))


@power("B5")
def psychic():  # one hand to the temple, the other projects; telekinetic wrist flicks, little body motion
    g = M(legs(lh=(10, 0, -10), lk=-14, rh=(-4, 0, 10), rk=-10), body(root=(0, -20, 0), waist=(2, -4, 0), neck=(-4, 20, 0), p=(0, -0.08, 0)),
          A2((35, 30, 0), 45, (-30, 0, 0)))
    ws = dict(legs=0.1, torso=0.1, p=0.1)
    temple = A("L", (60, 40, -10), 150, (-20, 0, 0))
    flick = T6(g, [A("R", (60, 20, 0), 60, (40, 0, 0)), temple], [A("R", (70, 10, -10), 20, (-50, 0, 0)), temple, Bd(g, 6, -2, (0, -0.02, -0.06))], es="expo", ws=ws,
               allow=("hand_in_head",), extra=[("h", 2, [A("R", (68, 10, -10), 24, (-40, 0, 0)), temple], "io")])
    push = T6(g, [A("R", (40, 20, 0), 90, (-30, 0, 0))], [A("R", (78, 0, -4), 4, (-70, 0, 0)), Bd(g, 10, -4, (0, -0.04, -0.14))], ws=ws)
    twist = T6(g, [A("R", (65, 10, 0), 30, (0, 0, 60)), temple], [A("R", (65, 10, 0), 30, (0, 0, -80)), temple, Bd(g, -8, 0, (0, 0, -0.04))], es="expo", ws=ws, allow=("hand_in_head",))
    # V7: the finisher keeps the temple hand; the free hand reaches out open, then clenches and yanks the target in
    # while the body rocks back (was a two-hand forward crush, too close to chakra's double palm)
    crush = T6(g, [A("R", (75, 15, -5), 10, (-50, 0, 0)), temple, Bd(g, 0, 2, (0, 0, 0.02))], [A("R", (35, 25, 0), 100, (40, 0, 0)), temple, Bd(g, -8, 6, (0, -0.06, 0.08))],
               ws=ws, ec="slow", wend=14, allow=("hand_in_head",), extra=[("h", 3, [A("R", (33, 25, 0), 105, (45, 0, 0)), temple], "hold")])
    focus = dict(flick, ec="slow", extra=[("w", -12, [A("R", (40, 20, 0), 60), temple, Bd(g, 0, 0, (0, -0.04, 0.02), neck=(10, 20, 0))], "slow"), ("h", 2, [A("R", (68, 10, -10), 24, (-40, 0, 0)), temple], "io")])
    lift = T6(g, [A2((0, 20, 0), 60, (20, 0, 0)), Bd(g, 0, 4, (0, -0.06, 0.02))], [A2((75, 5, -5), 10, (-40, 0, 0)), Bd(g, 0, 8, (0, 0.02, -0.08))], ws=ws, ec="slow", wend=14,
               extra=[("h", 3, [A2((72, 5, -5), 14, (-40, 0, 0))], "hold")])
    # V7: teleport = both hands to the temples, head dips, then the arms snap open low as the body reappears upright
    # (was a palm-forward lunge like chakra's body flicker)
    blink = T6(g, [temple, A("R", (60, 40, -10), 150, (-20, 0, 0)), Bd(g, 0, -4, (0, -0.06, 0), neck=(14, 20, 0))],
               [A2((15, 0, 45), 20), Bd(g, 0, 2, (0, 0.0, -0.4))], es="expo", ws=ws, allow=("hand_in_head",))
    ult = dict(rush(flick, twist), extra=[("w", -14, [temple, A("R", (40, 20, 0), 60), Bd(g, 0, 0, (0, -0.04, 0.02))], "slow")])
    ult["allow"] = tuple(ult.get("allow", ())) + ("hand_in_head",)
    s = {"M1_1": meta(flick, "telekinetic flick", foot=["planted"]),
         "M1_2": meta(push, "mind push", foot=["planted"]),
         "M1_3": meta(twist, "wrist-twist wrench", foot=["planted"]),
         "M1_4": meta(crush, "temple clench-and-yank finisher", foot=["planted"]),
         "Blast": meta(lift, "levitate-and-hurl (heavy)", foot=["planted"]),
         "Bolt": meta(dict(flick), "psi bolt", foot=["planted"]),
         "Dash": meta(blink, "temple teleport (mobility)", foot=["dodge"]),
         "Ult": meta(ult, "mind crush", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, breath=1.0, drift=3))


@power("B5")
def voidsovereign():  # gravity: tall and still, arms low and open; slow deliberate pulls and downward presses with huge force
    g = M(legs(lh=(10, 0, -16), lk=-20, rh=(-4, 0, 16), rk=-18), body(root=(-8, -16, 0), waist=(-8, -4, 0), neck=(12, 16, 0), p=(0, -0.16, 0)),
          A("R", (40, 15, 0), 10, (45, 0, 0)), A("L", (0, 0, 14), 20))
    ws = dict(legs=0.08, torso=0.1, p=0.1)
    press = T6(g, [A("R", (60, 10, 0), 40, (-60, 0, 0)), Bd(g, 0, 2, (0, 0.02, 0))], [A("R", (30, 10, 0), 30, (40, 0, 0)), Bd(g, 0, -6, (0, -0.1, -0.04))], ec="slow", es="snap", ws=ws,
               extra=[("h", 4, [A("R", (28, 10, 0), 30, (45, 0, 0))], "hold")])
    grasp = T6(g, [A("L", (70, -10, 0), 10, (-40, 0, 0)), Bd(g, -6, 0, (0, 0, -0.02))], [A("L", (28, 30, 10), 95, (40, 0, 0)), Bd(g, 10, 4, (0, 0.0, 0.06))], ec="slow", es="snap", ws=ws,
               extra=[("w", -3, [A("L", (72, -10, 0), 6, (60, 0, 0))], "snap")])
    sweep = T6(g, [A("R", (40, 0, 40), 20, (-40, 0, 0))], [A("R", (50, 30, -30), 20, (40, 0, 0)), Bd(g, 14, -2, (0, -0.04, 0))], ec="slow", ws=ws)
    collapse = T6(g, [A2((62, 10, 10), 30, (-50, 0, 0)), Bd(g, 0, 2, (0, 0.04, 0))], [A2((25, 10, 15), 20, (45, 0, 0)), Bd(g, 0, -8, (0, -0.2, -0.04), LeftKnee=-20, RightKnee=-20)],
                  ec="slow", ws=ws, wend=14, extra=[("w", -6, [A2((66, 10, 10), 30, (-60, 0, 0)), Bd(g, 0, 4, (0, 0.06, 0))], "slow"), ("h", 4, [A2((22, 10, 15), 20, (50, 0, 0))], "hold")])
    well = dict(collapse, extra=[("w", -14, [A2((40, 10, 10), 30, (-30, 0, 0)), Bd(g, 0, 0, (0, 0.02, 0))], "slow"), ("w", -6, [A2((66, 10, 10), 30, (-60, 0, 0)), Bd(g, 0, 4, (0, 0.08, 0))], "slow"),
                                 ("h", 6, [A2((22, 10, 15), 20, (50, 0, 0))], "hold")])
    pull = T6(g, [A("L", (70, -10, 0), 10, (-40, 0, 0))], [A("L", (28, 30, 10), 95, (40, 0, 0)), Bd(g, 0, 0, (0, 0, -0.5))], es="expo", ws=ws)
    ult = dict(well)
    s = {"M1_1": meta(press, "gravity press", foot=["planted"]),
         "M1_2": meta(grasp, "void grasp and pull", foot=["planted"], side="L"),
         "M1_3": meta(sweep, "event horizon sweep", foot=["planted"]),
         "M1_4": meta(collapse, "collapse finisher", foot=["planted"]),
         "Blast": meta(well, "singularity press (heavy)", foot=["planted"]),
         "Bolt": meta(dict(grasp), "void tether", foot=["planted"], side="L"),
         "Dash": meta(pull, "gravity slide (mobility)", foot=["dodge"], side="L"),
         "Ult": meta(ult, "absolute collapse", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, breath=0.8))


@power("B5")
def astraloverlord():  # celestial: arms open wide and low, grand sweeping arcs of both arms, upright and broad
    g = M(legs(lh=(8, 0, -30), lk=-20, rh=(0, 0, 30), rk=-18), body(root=(0, 0, 0), waist=(8, 0, 0), neck=(-10, 0, 0), p=(0, -0.2, 0)),
          A2((30, -10, 55), 10, (-40, 0, 0)))
    ws = dict(legs=0.12, torso=0.18, p=0.15)
    def arc(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (40, -20, 60), 10, (-30, 0, 0)), Bd(g, -20 * d, 0, (0, 0, 0.04))], [A(side, (70, 40, -30), 10, (-40, 0, 0)), Bd(g, 22 * d, -2, (0, -0.06, -0.12))],
                  ws=ws, allow=("elbow_up",), ec="io")
    both = T6(g, [A2((30, -20, 60), 10, (-30, 0, 0)), Bd(g, 0, 4, (0, 0.02, 0.04))], [A2((70, 30, -20), 10, (-50, 0, 0)), Bd(g, 0, -4, (0, -0.08, -0.16))], ws=ws, allow=("elbow_up",))
    spread = T6(g, [A2((65, 30, -20), 20, (-40, 0, 0)), Bd(g, 0, 0, (0, -0.04, 0))], [A2((40, -20, 65), 10, (-40, 0, 0)), Bd(g, 0, 6, (0, 0.02, -0.06))], ws=ws, allow=("elbow_up",), wend=14,
                extra=[("h", 3, [A2((38, -20, 68), 10, (-40, 0, 0))], "hold")])
    comet = T6(g, [A("R", (40, -20, 60), 10)], [A("R", (78, 0, -4), 0, (-60, 0, 0)), Bd(g, 14, -4, (0, -0.06, -0.2))], ws=ws)
    glide = T6(g, [A2((20, -10, 50), 20), Bd(g, 0, 0, (0, 0.04, 0))], [A2((10, -20, 60), 10), Bd(g, 0, -10, (0, 0.06, -0.6))], ws=ws, es="io", allow=("elbow_up",))
    ult = dict(rush(both, spread), extra=[("w", -14, [A2((20, -10, 65), 10), Bd(g, 0, 8, (0, 0.04, 0.04))], "slow")])
    s = {"M1_1": meta(arc("R"), "celestial arc", foot=["planted"]),
         "M1_2": meta(arc("L"), "celestial arc (left)", foot=["planted"], side="L"),
         "M1_3": meta(both, "converging arcs", foot=["planted"]),
         "M1_4": meta(spread, "starburst spread finisher", foot=["planted"]),
         "Bolt": meta(comet, "comet palm", foot=["advance"]),
         "Burst": meta(rush(arc("R"), arc("L")), "orbit arcs", foot=["planted"]),
         "Dash": meta(glide, "astral glide (mobility)", foot=["dodge"]),
         "Ult": meta(ult, "constellation", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.004, period=96, breath=2.5, sway=3, drift=4))


@power("B5")
def starbornascension():  # levitating: hovers off the ground, legs relaxed; casts rise upward and lift the body further
    g = M(legs(lh=(14, 0, -6), lk=-24, la=-30, rh=(4, 0, 6), rk=-36, ra=-30), body(root=(-4, -12, 0), waist=(0, -4, 0), neck=(2, 12, 0), p=(0, 0.25, 0)),
          A2((20, 20, 20), 50, (-30, 0, 0)))
    ws = dict(legs=0.0, torso=0.15, p=0.05)
    rise = T6(g, [A("R", (10, 20, 20), 60, (-30, 0, 0)), Bd(g, -8, 0, (0, -0.06, 0))], [A("R", (85, 10, -10), 10, (-60, 0, 0)), Bd(g, 10, 4, (0, 0.15, -0.08))], ws=ws)
    rise_l = T6(g, [A("L", (10, 20, 20), 60, (-30, 0, 0)), Bd(g, 8, 0, (0, -0.06, 0))], [A("L", (85, 10, -10), 10, (-60, 0, 0)), Bd(g, -10, 4, (0, 0.15, -0.08))], ws=ws)
    halo = T6(g, [A2((20, 30, 20), 70), Bd(g, 0, 0, (0, -0.04, 0))], [A2((75, 0, 30), 20, (-40, 0, 0)), Bd(g, 0, 6, (0, 0.2, -0.04))], ws=ws, allow=("elbow_up",))
    nova = T6(g, [A2((40, 50, 0), 100, (-20, 0, 0)), Bd(g, 0, 0, (0, -0.08, 0.02))], [A2((70, 10, -10), 4, (-65, 0, 0)), Bd(g, 0, 0, (0, 0.24, -0.2))], ws=ws, wend=14,
               extra=[("h", 3, [A2((68, 10, -10), 8, (-60, 0, 0)), Bd(g, 0, 0, (0, 0.24, -0.18))], "hold")])
    ascend = T6(g, [A2((20, 20, 20), 50), Bd(g, 0, 0, (0, -0.1, 0))], [A2((10, 0, 30), 20, (-40, 0, 0)), Bd(g, 0, -10, (0, 0.3, -0.5))], ws=ws, es="io")
    ult = dict(nova, extra=[("w", -14, [A2((30, 20, 30), 40), Bd(g, 0, 4, (0, 0.1, 0))], "slow"), ("w", -6, [A2((40, 50, 0), 100, (-20, 0, 0)), Bd(g, 0, 0, (0, 0.3, 0.04))], "slow"),
                            ("h", 4, [A2((68, 10, -10), 8, (-60, 0, 0)), Bd(g, 0, 0, (0, 0.34, -0.18))], "hold")])
    s = {"M1_1": meta(rise, "rising palm", foot=None),
         "M1_2": meta(rise_l, "rising palm (left)", foot=None, side="L"),
         "M1_3": meta(halo, "halo lift", foot=None),
         "M1_4": meta(nova, "star burst finisher", foot=None),
         "Bolt": meta(dict(rise), "starfall bolt", foot=None),
         "Dash": meta(ascend, "drift (mobility)", foot=None),
         "Ult": meta(ult, "ascension", foot=None)}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, lift=0.06, breath=2, drift=4))


@power("B5")
def infinityarchitect():  # precise geometry: one hand traces a shape (three sharp points) before projecting it
    g = M(legs(lh=(20, 0, -18), lk=-18, rh=(-14, 0, 18), rk=-8), body(root=(0, -4, 0), waist=(12, 0, 0), neck=(-16, 4, 0), p=(0, -0.1, 0)),
          A("R", (80, 10, 0), 0, (0, 0, 0)), A("L", (-10, 0, 35), 80))
    ws = dict(legs=0.1, torso=0.08, p=0.1)
    def trace(side, pts):
        d = 1 if side == "R" else -1
        ex = [("w", -6 + 2 * k, [A(side, sh, 30, (0, 0, 0))], "expo") for k, sh in enumerate(pts)]
        return T6(g, [A(side, pts[-1], 30)], [A(side, (78, 0, -4), 0, (-60, 0, 0)), Bd(g, 10 * d, -2, (0, -0.02, -0.12))], es="expo", ws=ws, extra=ex)
    tri = trace("R", [(70, 20, 10), (55, 40, -10), (55, 0, 20)])
    sq = trace("L", [(65, 20, 10), (65, 0, 30), (50, 0, 30)])
    line = T6(g, [A("R", (60, 30, 30), 20)], [A("R", (60, 30, -40), 20, (0, 0, 0)), Bd(g, 10, 0, (0, 0, -0.04))], es="lin", ws=ws, allow=("elbow_up",))
    lattice = T6(g, [A2((60, 30, 0), 40)], [A2((75, 10, -10), 4, (-60, 0, 0)), Bd(g, 0, -2, (0, -0.04, -0.16))], es="expo", ws=ws, wend=14,
                 extra=[("w", -6, [A2((60, 10, 20), 30)], "expo"), ("w", -4, [A2((50, 30, 20), 30)], "expo"), ("w", -2, [A2((60, 30, 0), 40)], "expo")])
    grid = dict(lattice, extra=[("w", -14, [A("R", (70, 20, 10), 30)], "expo"), ("w", -12, [A("R", (55, 40, -10), 30)], "expo"), ("w", -10, [A("R", (55, 0, 20), 30)], "expo"),
                                ("w", -6, [A2((60, 10, 20), 30)], "expo"), ("w", -3, [A2((50, 30, 20), 30)], "expo")])
    step = T6(g, [A("R", (45, 30, 0), 80)], [A("R", (78, 0, -4), 0, (-60, 0, 0)), Bd(g, 0, 0, (0, -0.02, -0.5))], es="expo", ws=ws)
    ult = dict(grid)
    frame_ = T6(g, [A2((60, 30, 0), 40)], [A2((75, 10, -10), 4, (-60, 0, 0)), Bd(g, 0, 0, (0, -0.02, -0.5))], es="expo", ws=ws)
    s = {"M1_1": meta(tri, "triangle trace", foot=["planted"]),
         "M1_2": meta(sq, "square trace (left)", foot=["planted"], side="L"),
         "M1_3": meta(line, "cutting line", foot=["planted"]),
         "M1_4": meta(lattice, "lattice projection finisher", foot=["planted"]),
         "Blast": meta(grid, "construct grid (heavy)", foot=["planted"]),
         "Bolt": meta(dict(line), "vector line", foot=["planted"]),
         "Dash": meta(frame_, "framed shift (mobility)", foot=["dodge"]),
         "Ult": meta(ult, "infinite blueprint", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, breath=1.0, drift=2))


@power("B5")
def supernovagod():  # charged blasts: hands compress energy at the chest, then fling open and forward explosively
    g = M(legs(lh=(12, 0, -30), lk=-44, rh=(12, 0, 30), rk=-44), body(root=(0, -6, 0), waist=(6, 0, 0), neck=(-6, 6, 0), p=(0, -0.42, 0)),
          A("R", (-20, 20, -10), 100), A("L", (40, -30, 0), 80, (0, 0, -80)))
    ws = dict(legs=0.2, torso=0.25, p=0.25)
    comp = A2((40, 62, 0), 120, (0, 0, 0))
    def fling(side):
        d = 1 if side == "R" else -1
        return T6(g, [comp, Bd(g, -8 * d, 4, (0, -0.06, 0.06))], [A(side, (78, -10, 10), 0, (-60, 0, 0)), A(other(side), (20, -10, 40), 20), Bd(g, 26 * d, -8, (0, -0.12, -0.3), LeftKnee=-48)], ws=ws)
    burst = T6(g, [comp, Bd(g, 0, 6, (0, -0.1, 0.08))], [A2((60, -30, 40), 0, (-60, 0, 0)), Bd(g, 0, -10, (0, -0.14, -0.3), LeftKnee=-48)], ws=ws, allow=("elbow_up",), wend=14,
                 extra=[("h", 3, [A2((58, -30, 42), 6, (-55, 0, 0))], "hold")])
    charged = T6(g, [comp, Bd(g, 0, 6, (0, -0.16, 0.1))], [A2((76, 10, -8), 0, (-65, 0, 0)), Bd(g, 0, -12, (0, -0.2, -0.4), LeftKnee=-56)], ws=ws, ec="slow",
                 extra=[("w", -10, [A2((30, 55, 10), 110), Bd(g, 0, 4, (0, -0.2, 0.08))], "slow"), ("w", -4, [comp, Bd(g, 0, 8, (0, -0.24, 0.12))], "slow")])
    flare = T6(g, [comp, Bd(g, 0, -8, (0, -0.2, 0.06))], [A2((60, -30, 40), 0, (-60, 0, 0)), Bd(g, 0, -14, (0, -0.2, -0.6))], es="expo", ws=ws, allow=("elbow_up",))
    ult = dict(burst, extra=[("w", -16, [comp, Bd(g, 0, 6, (0, -0.3, 0.1), LeftKnee=-56)], "slow"), ("w", -6, [A2((35, 66, 0), 125), Bd(g, 0, 10, (0, -0.34, 0.14))], "slow"),
                             ("h", 6, [A2((58, -30, 42), 6, (-55, 0, 0))], "hold")])
    s = {"M1_1": meta(fling("R"), "nova fling", foot=["advance"], torso=["cast"]),
         "M1_2": meta(fling("L"), "nova fling (left)", foot=["advance"], side="L"),
         "M1_3": meta(charged, "compressed blast", foot=["planted"], torso=["cast"]),
         "M1_4": meta(burst, "supernova spread finisher", foot=["planted"], torso=["cast", "heavy"]),
         "Bolt": meta(dict(fling("R"), es="expo"), "star shard", foot=["advance"]),
         "Burst": meta(rush(fling("R"), fling("L")), "flare volley", foot=["planted"]),
         "Dash": meta(flare, "flare burst (mobility)", foot=["dash"]),
         "Ult": meta(ult, "supernova", foot=["planted"], torso=["cast", "heavy"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.02, period=48, breath=3, drift=5))


@power("B5")
def absoluteinfinity():  # calm, minimal, godlike: stands relaxed, almost still; a finger flick does everything
    g = M(legs(lh=(10, 0, -4), lk=-14, rh=(-4, 0, 10), rk=0), body(root=(0, -12, -6), waist=(4, 0, 6), neck=(-10, 10, 0), p=(0.14, -0.04, 0)),
          A2((-4, 0, 10), 12))
    ws = dict(legs=0.0, torso=0.05, p=0.0)
    flickr = T6(g, [A("R", (35, 40, -10), 70, (20, 0, 0))], [A("R", (40, -20, 50), 10, (-20, 0, 0)), Bd(g, -6, 0, (0, 0, 0))], es="expo", ws=ws,
                allow=("elbow_up",), extra=[("h", 4, [A("R", (40, -20, 50), 10, (-20, 0, 0))], "hold")])
    flickl = T6(g, [A("L", (35, 40, -10), 70, (20, 0, 0))], [A("L", (40, -20, 50), 10, (-20, 0, 0)), Bd(g, 6, 0, (0, 0, 0))], es="expo", ws=ws,
                allow=("elbow_up",), extra=[("h", 4, [A("L", (40, -20, 50), 10, (-20, 0, 0))], "hold")])
    palm = T6(g, [A("R", (60, 20, 0), 70, (40, 0, 0))], [A("R", (25, 15, 0), 20, (50, 0, 0)), Bd(g, 0, -4, (0, -0.06, 0))], es="expo", ws=ws)
    snap = T6(g, [A("R", (45, 20, 10), 70, (0, 0, 20))], [A("R", (45, 20, 10), 70, (0, 0, -20))], es="expo", ws=ws, wend=16,
              extra=[("h", 6, [A("R", (45, 20, 10), 70, (0, 0, -20))], "hold")])
    decree = dict(snap, ec="slow", extra=[("w", -12, [A("R", (25, 15, 10), 50)], "slow"), ("h", 8, [A("R", (45, 20, 10), 70, (0, 0, -20))], "hold")])
    shift = T6(g, [A2((0, 0, 8), 10)], [A2((0, 0, 8), 10), Bd(g, 0, 0, (0, 0, -0.4))], es="expo", ws=ws)
    ult = dict(snap, extra=[("w", -16, [A2((0, 0, 8), 10)], "hold"), ("w", -6, [A("R", (45, 20, 10), 70, (0, 0, 20))], "slow"), ("h", 10, [A("R", (45, 20, 10), 70, (0, 0, -20))], "hold")])
    s = {"M1_1": meta(flickr, "dismissive backhand", foot=None),
         "M1_2": meta(flickl, "dismissive backhand (left)", foot=None, side="L"),
         "M1_3": meta(palm, "downward palm press", foot=None),
         "M1_4": meta(snap, "finger snap finisher", foot=None),
         "Blast": meta(decree, "decree (heavy)", foot=None),
         "Burst": meta(rush(flickr, flickl), "flick cascade", foot=None),
         "Dash": meta(shift, "unmoving step (mobility)", foot=None),
         "Ult": meta(ult, "end of all things", foot=None)}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, breath=0.6))


HERO = "Superman"


def hero(clips, name, **kw):
    return dict(sword_direct=True, src_clip=clips, src_set=HERO, name=name, side="R", **kw)


@power("B5")
def divinesaiyan():  # user order: the flying-hero (Superman/Omniman) set used directly as the whole moveset
    L = ["mco_attack1", "mco_attack2", "mco_attack3", "mco_attack5", "mco_attack4", "mco_attack6", "mco_attack7", "mco_attack9", "mco-attack5"]
    H = ["mco_powerattack1__2", "mco_powerattack3", "mco_powerattack2", "mco_powerattack4", "mco_powerattack1__3"]
    s = {"M1_1": hero(L, "hero light 1"),
         "M1_2": hero(L[1:] + L[:1], "hero light 2"),
         "M1_3": hero(L[2:] + L[:2], "hero light 3"),
         "M1_4": hero(["mco_attack5", "mco_attack9", "mco_attack8"] + L, "hero finisher"),
         "Bolt": hero(["mco_attack9", "mco_attack8", "mco-attack5"] + L, "hero strike"),
         "Blast": hero(H, "hero power blow (heavy)"),
         "Dash": hero(["mco_attack1__5", "mco_attack2__5", "mco_attack3__3", "dodgeforward", "stepdodgeback"], "hero dash strike (mobility)"),
         "Ult": hero(["mco_powerattack1", "mco_powerattack4", "mco_powerattack2"] + H, "hero ultimate")}
    return dict(guard=None, guard_src=("1hm_idle", HERO), slots=s, idle_direct=("1hm_idle", HERO))


# V7 (2026-11-23): casters re-sourced from the set-3 casting libraries (Goetia / Smooth Magic / Mystic Knight): primary
# strike + torso + planted weight shifts + idle source come from real spell-casting mocap; `arms` blends that much of the
# casting arm dynamics under each power's authored gesture language. Ult of supernovagod stays on the hero base.
V7 = {"psychic": dict(sets=["Goetia"], idle_sets=["Goetia"]),
      "infinityarchitect": dict(sets=["Smooth Magic"], idle_sets=["Smooth Magic"]),
      "voidsovereign": dict(sets=["Mystic"], idle_sets=["Mystic"], planted=None, slots=("M1_4", "Blast", "Ult")),  # heavies only; lights keep pre-V7 sources
      "astraloverlord": dict(sets=["Goetia"], idle_sets=["Goetia"]),
      "supernovagod": dict(sets=["Smooth Magic"], skip=("Dash", "Ult")),
      "chakra": dict(sets=["Mystic"], idle_sets=["Mystic"], planted=None, moving=["For Honor"]),  # martial step-in palms
      "chakramaster": dict(sets=["Goetia"]),
      "starbornascension": dict(sets=["Mystic"]),
      "absoluteinfinity": dict(sets=["Smooth Magic"])}
for _pid, _kw in V7.items():
    POWERS[_pid] = (lambda f, kw: (lambda: lib3(f(), **kw)))(POWERS[_pid], _kw)
