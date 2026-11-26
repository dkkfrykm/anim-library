# Phase-6 batch B3: bodies and shadow. Elastic = loose, rebounding overshoot; shadow = deceptive feints, odd angles,
# glide; acrobat = springy, aerial only where earned; beasts = feral crouch / draconic weight. DSL: powers6.py
from powers6 import *


@power("B3")
def elasticemperor():  # rubber: loose dangling arms, bouncy knees, windmill stretch punches that overshoot and snap back
    g = M(legs(lh=(20, 0, -10), lk=-40, rh=(20, 0, 10), rk=-40, ra=8), body(root=(0, -10, 0), waist=(-12, 0, 6), neck=(10, 0, -8), p=(0, -0.3, 0)),
          A("R", (-10, 0, 10), 15), A("L", (5, 0, -12), 10))
    rub = dict(legs=0.25, torso=0.3, p=0.3)
    def stretch(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (-70, 0, 20), 10), Bd(g, -24 * d, 4, (0, -0.06, 0.12))],
                  [A(side, (92, 0, -4), 0, (-10, 0, 0)), A(other(side), (-30, 0, 20), 10), Bd(g, 30 * d, -10, (0, -0.12, -0.44), LeftKnee=-52)],
                  ws=rub, wend=16, allow=("elbow_up",),
                  extra=[("h", 1, [A(side, (96, 0, -4), 0), Bd(g, 34 * d, -12, (0, -0.14, -0.5))], "snap"),
                         ("h", 4, [A(side, (70, 0, -4), 30), Bd(g, 18 * d, -4, (0, -0.06, -0.2))], "snap"),
                         ("h", 7, [A(side, (80, 0, -4), 12), Bd(g, 24 * d, -6, (0, -0.08, -0.28))], "io")])
    whip = T6(g, [A("R", (40, -30, 70), 0), Bd(g, -40, 0, (0, -0.04, 0.06))], [A("R", (75, 20, -60), 0), Bd(g, 40, -6, (0, -0.1, -0.2))],
              ws=rub, allow=("elbow_up", "hands_up", "crossed_knees"), extra=[("h", 3, [A("R", (70, 30, -75), 10), Bd(g, 46, -6, (0, -0.1, -0.2))], "snap")])
    bounce = T6(g, [A2((-20, 0, 20), 10), Bd(g, 0, 4, (0, -0.4, 0.04), LeftKnee=-70, RightKnee=-70)],
                [A2((85, 10, -6), 0), Bd(g, 0, -8, (0, 0.2, -0.4))], ws=rub, wend=14,
                extra=[("h", 4, [A2((70, 10, -6), 20), Bd(g, 0, -4, (0, 0.05, -0.26))], "snap")])
    mill = rush4(stretch("R"), stretch("L"), stretch("R"), stretch("L"))
    gatl = dict(mill)
    sling = T6(g, [A2((-60, 0, 20), 10), Bd(g, 0, 8, (0, -0.2, 0.2), LeftKnee=-60)], [A2((88, 0, -4), 0), Bd(g, 0, -14, (0, -0.16, -0.66))], es="expo", ws=rub, allow=("elbow_up",))
    ult = dict(mill)
    ult["extra"] = [("w", -14, [A2((-75, 0, 25), 10), Bd(g, 0, 10, (0, -0.24, 0.22), LeftKnee=-62)], "slow"),
                    ("w", -6, [A2((-85, 0, 25), 10), Bd(g, 0, 12, (0, -0.3, 0.26))], "slow")]
    s = {"M1_1": meta(stretch("R"), "stretch punch", foot=["advance"], torso=["attack"]),
         "M1_2": meta(stretch("L"), "stretch punch (left)", foot=["advance"], side="L"),
         "M1_3": meta(whip, "rubber whip swing", foot=["pivot"], torso=["attack", "twist"]),
         "M1_4": meta(bounce, "spring-loaded double palm finisher", foot=["planted", "crouch"]),
         "Blast": meta(gatl, "rubber gatling (heavy)", foot=["planted"]),
         "Bolt": meta(dict(stretch("R"), es="expo"), "pistol stretch", foot=["planted"]),
         "Dash": meta(sling, "slingshot launch (mobility)", foot=["dash"]),
         "Ult": meta(ult, "wind-up gatling", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.06, period=48, roll=8, sway=6, drift=12, breath=2))


@power("B3")
def phantomstep():  # shadow: body bladed sideways, drooping hands, feint one side and strike from the other, glides
    g = M(legs(lh=(12, 0, -10), lk=-26, rh=(-6, 0, 12), rk=-30), body(root=(0, -55, 0), waist=(4, -8, 0), neck=(-4, 52, 0), p=(0, -0.2, 0)),
          A("R", (25, 20, 10), 30, (30, 0, 0)), A("L", (35, -10, -10), 40, (30, 0, 0)))
    ghost = dict(legs=0.2, torso=0.15, p=0.3)
    feint = T6(g, [A("L", (70, -10, 0), 20), Bd(g, -10, 0, (-0.12, -0.04, 0))],
               [A("R", (80, 30, -40), 10, (-30, 0, 0)), A("L", (20, -20, 10), 60), Bd(g, 40, -6, (0.25, -0.1, -0.2), LeftKnee=-36)],
               ws=ghost, allow=("crossed_knees",), extra=[("w", -3, [A("L", (78, -10, 0), 10), Bd(g, -14, -2, (-0.16, -0.04, -0.04))], "expo")])
    low = T6(g, [A("R", (-20, 20, 20), 60, (30, 0, 0)), Bd(g, 10, -10, (0, -0.3, 0.04), LeftKnee=-60, RightKnee=-56)],
             [A("R", (70, 0, -10), 10, (-60, 0, 0)), Bd(g, 30, 4, (0, -0.06, -0.24))], ws=ghost, es="expo")
    side = T6(g, [A("L", (40, -20, 0), 60), Bd(g, 20, 0, (-0.3, -0.06, 0))], [A("L", (75, -40, 50), 0, (20, 0, 0)), Bd(g, -30, -4, (-0.45, -0.1, -0.1))],
              ws=ghost, allow=("elbow_up", "crossed_knees"))
    back = T6(g, [A("R", (60, 40, -40), 110), Bd(g, 30, 0, (0.1, -0.04, 0.04))], [A("R", (70, -20, 70), 10), Bd(g, -50, -4, (0.2, -0.08, -0.16))],
              ws=ghost, allow=("elbow_up", "hands_up", "crossed_knees"), extra=[("h", 3, [A("R", (68, -25, 72), 14), Bd(g, -54, -4, (0.22, -0.08, -0.16))], "hold")])
    glide = T6(g, [A("L", (35, -10, -10), 40, (30, 0, 0)), Bd(g, 0, 0, (0, -0.1, 0.08))], [A("R", (80, 0, -4), 0, (-40, 0, 0)), Bd(g, 30, -4, (0.3, -0.14, -0.55))], es="expo", ws=ghost)
    swarm = rush4(feint, side, low, back)
    ult = dict(swarm)
    ult["extra"] = [("w", -14, [A2((25, 20, 10), 30, (40, 0, 0)), Bd(g, -20, 0, (-0.3, -0.1, 0.06))], "io"), ("w", -6, [A("L", (78, -10, 0), 10), Bd(g, 10, -2, (0.3, -0.1, 0))], "expo")]
    s = {"M1_1": meta(feint, "feint-left, strike-right", foot=["sidestep_r"], torso=["attack"]),
         "M1_2": meta(low, "rising palm from below", foot=["crouch"]),
         "M1_3": meta(side, "side-slip backhand", foot=["sidestep_l"], side="L"),
         "M1_4": meta(back, "turning backfist finisher", foot=["pivot"], torso=["attack", "twist"]),
         "Burst": meta(swarm, "phantom angles", foot=["dodge"]),
         "Dash": meta(glide, "shadow glide strike (mobility)", foot=["dodge", "advance"]),
         "Ult": meta(ult, "vanish and strike from everywhere", foot=["dodge"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, sway=8, shift=0.1, breath=1.5, drift=6))


@power("B3")
def acrobat():  # gymnast: springy wide base, balance arms out; jump kicks on basics, flips/spins saved for the ult
    g = M(legs(lh=(10, 0, -18), lk=-28, la=14, rh=(10, 0, 18), rk=-28, ra=14), body(root=(0, -10, 0), waist=(-2, 0, 0), neck=(2, 8, 0), p=(0, -0.22, 0)),
          A2((15, 0, 48), 30))
    spring = dict(legs=0.3, torso=0.25, p=0.4)
    arms = A2((15, 0, 48), 30)
    hop = kick(g, "R", "front", arms=arms, chl=Bd(g, 0, 0, (0, -0.2, 0)), stl=Bd(g, 0, 6, (0, 0.35, -0.1)), lift=0.0)
    hop["ws"] = spring
    scissor = kick(g, "L", "round", arms=A2((20, 0, 60), 20), chl=Bd(g, 0, 0, (0, 0.1, 0)), stl=Bd(g, 0, 0, (0, 0.4, -0.06)))
    scissor["ws"] = spring
    cart = T6(g, [A2((40, 0, 70), 10), Bd(g, 0, 0, (0, -0.14, 0), roll=0)], [M(A2((60, 0, 75), 0)), P(RightHip=(30, 0, 70), RightKnee=(-6, 0, 0)), Bd(g, 40, 0, (0.3, 0.1, -0.1), roll=-40)],
              ws=spring, kick="R", allow=("crossed_knees", "elbow_up", "hands_up", "extreme_lean"), extra=[("h", 3, [P(RightHip=(20, 0, 60), RightKnee=(-20, 0, 0)), Bd(g, 30, 0, (0.3, 0.06, -0.1), roll=-30)], "io")])
    axe = kick(g, "R", "push", arms=arms, chl=Bd(g, 0, 0, (0, 0.1, 0)), stl=Bd(g, 0, 8, (0, 0.3, -0.12)))
    axe["ws"] = spring
    sidek = kick(g, "R", "side", arms=A2((20, 0, 60), 20), chl=Bd(g, 0, 0, (0, 0.05, 0)), stl=Bd(g, 0, 0, (0, 0.3, -0.04)))
    sidek["ws"] = spring
    tornado = T6(g, [A2((20, 0, 60), 20), Bd(g, -60, 0, (0, -0.2, 0))],
                 [A2((30, 0, 70), 10), P(RightHip=(70, 0, 80), RightKnee=(-6, 0, 0), LeftKnee=(-60, 0, 0)), Bd(g, 0, 0, (0, 0.45, -0.1))],
                 ws=spring, kick="R", allow=("crossed_knees", "elbow_up", "pop"), wend=16,
                 extra=[("w", 3, [Bd(g, -180, 0, (0, 0.2, 0))], "lin"), ("i", -2, [Bd(g, -300, 0, (0, 0.4, -0.05))], "lin"), ("h", 6, [Bd(g, -360, 0, (0, 0.0, -0.1))], "io")])
    roll = T6(g, [A2((40, 0, 30), 60), Bd(g, 0, -20, (0, -0.4, 0.04), LeftKnee=-70, RightKnee=-70)], [A2((60, 0, 30), 40), Bd(g, 0, -40, (0, -0.5, -0.6), LeftKnee=-80, RightKnee=-80)],
              ws=spring, allow=("extreme_lean",), es="io")
    whirl = rush(scissor, hop)
    ult = dict(tornado)
    ult["extra"] = [("w", -14, [A2((40, 0, 70), 10), Bd(g, 0, 0, (0, -0.3, 0), LeftKnee=-60, RightKnee=-60)], "slow"),
                    ("w", -6, [A2((60, 0, 75), 0), Bd(g, -60, 0, (0, 0.2, 0))], "io"), ("w", 2, [Bd(g, -180, 0, (0, 0.45, 0))], "lin"),
                    ("i", -2, [Bd(g, -300, 0, (0, 0.5, -0.05))], "lin"), ("h", 8, [Bd(g, -360, 0, (0, 0.0, -0.1))], "io")]
    ult["allow"] = tuple(ult.get("allow", ())) + ("extreme_lean",)
    s = {"M1_1": meta(hop, "hop front kick", foot=["planted"], kick="R"),
         "M1_2": meta(scissor, "jumping scissor kick", foot=["airborne"], kick="L"),
         "M1_3": meta(sidek, "hop side kick", foot=["planted"], kick="R"),
         "M1_4": meta(cart, "cartwheel kick finisher", foot=["sidestep_r"], kick="R"),
         "Blast": meta(tornado, "tornado kick (heavy)", foot=["airborne", "spin"], kick="R"),
         "Burst": meta(whirl, "aerial kick chain", foot=["airborne"], kick="L"),
         "Dash": meta(roll, "dive roll (mobility)", foot=["dodge"]),
         "Ult": meta(ult, "springboard tornado", foot=["airborne"], kick="R")}
    return dict(guard=g, slots=s, idle=dict(bounce=0.06, period=24, shift=0.04, breath=1.5))


@power("B3")
def beastform():  # feral: deep forward crouch, hands low near the ground, raking claws, pounces and a lunging bite
    g = M(legs(lh=(50, 0, -16), lk=-80, la=24, rh=(24, 0, 16), rk=-66, ra=30), body(root=(-26, -6, 0), waist=(-20, 0, 0), neck=(40, 6, 0), p=(0, -0.7, 0)),
          A2((55, 30, 0), 30, (-40, 0, 0)))
    feral = dict(legs=0.25, torso=0.25, p=0.3)
    def rake(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (80, -10, 50), 40, (-50, 0, 0)), Bd(g, -14 * d, 4, (0, 0.06, 0.04))],
                  [A(side, (35, 30, -35), 20, (-55, 0, 0)), Bd(g, 20 * d, -6, (0, -0.06, -0.24))], ws=feral, allow=("elbow_up", "hand_in_head"))
    pounce = T6(g, [A2((20, 30, 0), 60, (-40, 0, 0)), Bd(g, 0, -4, (0, -0.8, 0.06))],
                [A2((80, 20, -10), 20, (-60, 0, 0)), Bd(g, 0, 20, (0, 0.2, -0.6), LeftKnee=-40, RightKnee=-30)], ws=feral, es="expo", wend=14,
                extra=[("h", 4, [A2((40, 25, 0), 40, (-55, 0, 0)), Bd(g, 0, 0, (0, -0.5, -0.3))], "io")])
    bite = T6(g, [A2((0, 20, 20), 50), Bd(g, 0, 6, (0, -0.6, 0.1), neck=(55, 0, 0))], [A2((-20, 10, 30), 40), Bd(g, 0, -10, (0, -0.4, -0.4), neck=(10, 0, 0))],
              ws=feral, es="expo")
    frenzy = rush4(rake("R"), rake("L"), rake("R"), rake("L"))
    lunge = T6(g, [A2((40, 30, 0), 40, (-40, 0, 0)), Bd(g, 0, -4, (0, -0.8, 0.06))], [A2((70, 20, 0), 20, (-50, 0, 0)), Bd(g, 0, 10, (0, -0.3, -0.66))], es="expo", ws=feral)
    howl = T6(g, [A2((20, 0, 40), 40, (-40, 0, 0)), Bd(g, 0, 20, (0, -0.4, 0.06), neck=(-20, 0, 0))], [A2((60, 20, 0), 20, (-55, 0, 0)), Bd(g, 0, 0, (0, -0.4, -0.3))], ws=feral, ec="slow")
    ult = dict(frenzy)
    ult["extra"] = [("w", -14, [A2((10, 0, 45), 40, (-40, 0, 0)), Bd(g, 0, 22, (0, -0.3, 0.08), neck=(-25, 0, 0))], "slow"), ("w", -4, [A2((20, 30, 0), 60, (-40, 0, 0)), Bd(g, 0, -4, (0, -0.8, 0.06))], "io")]
    s = {"M1_1": meta(rake("R"), "claw rake", foot=["advance", "crouch"]),
         "M1_2": meta(rake("L"), "claw rake (left)", foot=["advance"], side="L"),
         "M1_3": meta(bite, "lunging bite", foot=["advance"]),
         "M1_4": meta(pounce, "pounce finisher", foot=["airborne"], torso=["attack"]),
         "Bolt": meta(howl, "howl swipe", foot=["planted"]),
         "Burst": meta(frenzy, "claw frenzy", foot=["planted"]),
         "Dash": meta(lunge, "feral lunge (mobility)", foot=["dash"]),
         "Ult": meta(ult, "howl into frenzy", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.03, period=48, sway=6, breath=4, shift=0.05))


@power("B3")
def dragonshift():  # draconic: upright wide, chest out, arms spread with claws, heavy swipes, tail-like spinning backfist, roar
    g = M(legs(lh=(10, 0, -26), lk=-34, rh=(10, 0, 26), rk=-34), body(root=(0, -8, 0), waist=(4, 0, 0), neck=(-6, 6, 0), p=(0, -0.3, 0)),
          A2((25, -5, 40), 70, (-45, 0, 0)))
    drake = dict(legs=0.2, torso=0.25, p=0.25)
    def swipe(side):
        d = 1 if side == "R" else -1
        return T6(g, [A(side, (60, -30, 60), 60, (-50, 0, 0)), Bd(g, -26 * d, 2, (0, 0.02, 0.06))],
                  [A(side, (70, 40, -50), 20, (-55, 0, 0)), Bd(g, 30 * d, -8, (0, -0.12, -0.26), LeftKnee=-44)], ws=drake, ec="slow",
                  allow=("elbow_up", "hands_up", "crossed_knees"))
    tailspin = T6(g, [A("R", (30, 0, 50), 60), Bd(g, 40, 0, (0, -0.06, 0))],
                  [A("R", (70, -20, 70), 10), Bd(g, -200, -4, (0, -0.1, -0.16))], ws=drake, allow=("crossed_knees", "elbow_up", "pop", "foot_slide"), wend=18,
                  extra=[("i", -3, [Bd(g, -90, 0, (0, -0.08, -0.08))], "lin"), ("h", 6, [A("R", (60, -20, 60), 20), Bd(g, -330, -2, (0, -0.06, -0.1))], "io"), ("r", 0, [Bd(g, -360, 0, (0, 0, 0))], "io")])
    maul = T6(g, [A2((60, -20, 60), 70, (-50, 0, 0)), Bd(g, 0, 6, (0, 0.06, 0.06))], [A2((50, 40, -30), 20, (-55, 0, 0)), Bd(g, 0, -14, (0, -0.24, -0.3), LeftKnee=-50)],
               ws=drake, ec="slow", allow=("elbow_up", "hands_up"), wend=14, extra=[("h", 3, [A2((45, 40, -35), 24, (-55, 0, 0)), Bd(g, 0, -12, (0, -0.22, -0.28))], "hold")])
    roar = T6(g, [A2((10, -10, 50), 60, (-40, 0, 0)), Bd(g, 0, -10, (0, -0.1, 0.04), neck=(10, 0, 0))], [A2((20, -30, 70), 30, (-50, 0, 0)), Bd(g, 0, 10, (0, 0.02, -0.1), neck=(-24, 0, 0))],
              ws=drake, ec="slow", allow=("elbow_up",))
    rend = rush(swipe("R"), swipe("L"))
    wing = T6(g, [A2((20, -20, 70), 40), Bd(g, 0, -10, (0, -0.3, 0.06), LeftKnee=-56, RightKnee=-56)], [A2((70, 20, -20), 20, (-55, 0, 0)), Bd(g, 0, -12, (0, 0.1, -0.6))], ws=drake, es="expo", allow=("elbow_up",))
    ult = dict(maul)
    ult["extra"] = [("w", -16, [A2((20, -30, 70), 30, (-50, 0, 0)), Bd(g, 0, 10, (0, 0.02, -0.06), neck=(-24, 0, 0))], "slow"),
                    ("w", -6, [A2((60, -20, 60), 70, (-50, 0, 0)), Bd(g, 0, 8, (0, 0.08, 0.08))], "slow"), ("h", 6, [A2((45, 40, -35), 24, (-55, 0, 0)), Bd(g, 0, -12, (0, -0.22, -0.28))], "hold")]
    s = {"M1_1": meta(swipe("R"), "heavy claw swipe", foot=["planted"], torso=["attack", "heavy"]),
         "M1_2": meta(swipe("L"), "heavy claw swipe (left)", foot=["planted"], side="L"),
         "M1_3": meta(tailspin, "tail-whip spinning backfist", foot=["spin"], torso=["attack", "twist"]),
         "M1_4": meta(maul, "two-claw maul finisher", foot=["advance"], torso=["heavy"]),
         "Bolt": meta(roar, "dragon roar", foot=["planted"]),
         "Burst": meta(rend, "rending claws", foot=["planted"]),
         "Dash": meta(wing, "wing-beat lunge (mobility)", foot=["dash"]),
         "Ult": meta(ult, "roar then maul", foot=["planted"], torso=["heavy"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.012, period=96, breath=4, sway=4, roll=3))
