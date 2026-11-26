# Phase-6 batch B1: martial powers (grounded, believable). See powers6.py for the DSL.
from powers6 import *


@power("B1")
def karate():  # approved phase-4 kihon, modular footwork/torso; crisp kime, hikite
    s = {"M1_1": p4("oi_zuki", "oi-zuki lunge punch", foot=["advance", "attack"], torso=["attack"], side="L"),
         "M1_2": p4("gyaku_zuki", "gyaku-zuki reverse punch", foot=["planted", "attack"], torso=["attack"]),
         "M1_3": p4("mae_geri", "mae-geri front snap kick", foot=["planted"], kick="R"),
         "M1_4": p4("mawashi_geri", "mawashi-geri roundhouse finisher", foot=["planted"], kick="R"),
         "Bolt": p4("teisho", "teisho palm heel", foot=["advance"], torso=["attack"]),
         "Blast": p4("yoko_geri", "yoko-geri side thrust kick (heavy)", foot=["planted"], kick="R"),
         "Dash": p4("oi_zuki", "surikomi lunge punch (mobility)", foot=["advance", "long"], side="L"),
         "Ult": p4("zuki_rush", "renzuki barrage into gyaku-zuki", foot=["advance"], torso=["attack", "twist"])}
    return dict(guard=None, slots=s, guard_p4="KARATE_GUARD", idle=dict(bounce=0.01, period=96, breath=1.5))


@power("B1")
def boxer():  # approved phase-4 boxing, modular footwork
    s = {"M1_1": p4("jab", "jab", foot=["advance", "attack"], side="L"),
         "M1_2": p4("cross", "cross", foot=["planted", "attack"], torso=["attack"]),
         "M1_3": p4("lead_hook", "lead hook", foot=["pivot"], side="L"),
         "M1_4": p4("uppercut", "rear uppercut finisher", foot=["crouch"], torso=["attack"]),
         "Blast": p4("overhand", "overhand right (heavy)", foot=["advance"], torso=["attack", "twist"]),
         "Dash": p4("jab", "step-in jab (mobility)", foot=["advance", "long"], side="L"),
         "Ult": p4("combo_rush", "1-2-hook combination rush", foot=["advance"], torso=["attack"])}
    return dict(guard=None, slots=s, guard_p4="BOX_GUARD", idle=dict(bounce=0.05, period=24, sway=6, breath=1.5))


@power("B1")
def kicker():  # approved phase-4 kicking set
    s = {"M1_1": p4("front_snap", "front snap kick", foot=["planted"], kick="R"),
         "M1_2": p4("roundhouse_l", "lead roundhouse", foot=["planted"], kick="L"),
         "M1_3": p4("side_kick", "side kick", foot=["planted"], kick="R"),
         "M1_4": p4("axe_kick", "axe kick finisher", foot=["planted"], kick="R"),
         "Burst": p4("double_round", "double roundhouse", foot=["planted"], kick="R"),
         "Blast": p4("push_kick", "push kick (heavy)", foot=["advance"], kick="R"),
         "Dash": p4("push_kick", "skip-in push kick (mobility)", foot=["advance", "long"], kick="R"),
         "Ult": p4("kick_rush", "kick barrage", foot=["planted"], kick="R")}
    return dict(guard=None, slots=s, guard_p4="KICK_GUARD", idle=dict(bounce=0.04, period=48, shift=0.05, breath=1.5))


@power("B1")
def limitbreaker():  # MMA: athletic crouch, open hands, knees/elbows/clinch, level changes
    g = M(legs(lh=(22, 0, -18), lk=-36, la=4, rh=(-4, 0, 18), rk=-30, ra=14), body(root=(-4, -14, 0), waist=(-10, -4, 0), neck=(10, 12, 0), p=(0, -0.38, 0)),
          A("R", (32, 42, 0), 112, (-20, 0, 0)), A("L", (46, -38, 0), 98, (-20, 0, 0)))
    clinch = A2((44, 52, 0), 72, (-30, 0, 0))
    jab = T6(g, [A("L", (40, -30, 0), 104), Bd(g, -4, dp=(0, -0.02, 0.02))], [A("L", (88, 0, -6), 2, (-10, 0, 0)), Bd(g, -12, -4, (0, -0.06, -0.16), LeftKnee=-42)])
    cross = T6(g, [A("R", (28, 50, 0), 118), Bd(g, -8, dp=(0, -0.03, 0.03))],
               [A("R", (88, 0, -6), 2, (-10, 0, 0)), A("L", (40, -45, 0), 112), Bd(g, 30, -8, (0, -0.1, -0.24), LeftKnee=-46, RightAnkle=24)])
    elbow = T6(g, [A("R", (55, 20, 25), 140), Bd(g, -18, dp=(0, -0.04, 0.02))], [A("R", (80, 55, -10), 150), A("L", (40, -45, 0), 110), Bd(g, 38, -6, (0, -0.08, -0.16), LeftKnee=-44)],
               allow=("elbow_up", "hand_in_head", "hands_up"), extra=[("h", 4, [A("R", (60, 40, 0), 140), Bd(g, 28, -4, (0, -0.06, -0.12))], "io")])
    knee = kick(g, "R", "knee", arms=clinch, chl=Bd(g, 0, -10, (0, -0.02, -0.08)), stl=Bd(g, 0, -14, (0, 0.06, -0.18)),
                extra=[("w", -3, [clinch, Bd(g, 0, -6, (0, -0.06, -0.06))], "io")])
    knee["allow"] = knee["allow"] + ("hand_in_head",)
    superman = T6(g, [A("R", (20, 50, 0), 120), P(RightHip=(-40, 0, 14), RightKnee=(-70, 0, 0)), Bd(g, -10, 4, (0, 0.14, 0.02))],
                  [A("R", (88, 0, -6), 2, (-10, 0, 0)), A("L", (10, -30, 20), 60), P(RightHip=(-30, 0, 14), RightKnee=(-40, 0, 0)), Bd(g, 28, -14, (0, 0.04, -0.5), LeftKnee=-40)],
                  extra=[("w", -6, [A("R", (25, 50, 0), 118), Bd(g, -6, 0, (0, -0.16, 0.06), LeftKnee=-56, RightKnee=-50)], "slow")], wend=14)
    shoot = T6(g, [A2((30, 30, 0), 90), Bd(g, 0, -6, (0, -0.2, 0.04), LeftKnee=-60, RightKnee=-54)],
               [A2((70, 20, 0), 30, (-20, 0, 0)), Bd(g, 6, -22, (0, -0.42, -0.5), LeftKnee=-70, RightKnee=-20)], es="expo")
    ult = dict(rush(knee, elbow), extra=[("w", -10, [clinch, Bd(g, 0, -8, (0, -0.06, -0.1))], "io")])
    calf = kick(g, "R", "low", arms=M(A("R", (40, 40, 0), 110, (-20, 0, 0)), A("L", (30, -20, 20), 60)), chl=Bd(g, 10, 0, (0, -0.04, 0)), stl=Bd(g, 40, 4, (0, -0.02, -0.06)))
    s = {"M1_1": meta(calf, "low calf kick", foot=["planted"], kick="R"),
         "M1_2": meta(cross, "cross", foot=["planted", "attack"], torso=["attack"]),
         "M1_3": meta(elbow, "horizontal elbow", foot=["pivot"], torso=["attack", "twist"]),
         "M1_4": meta(knee, "clinch knee finisher", foot=["planted"], kick="R"),
         "Blast": meta(superman, "superman punch (heavy)", foot=["advance", "airborne"], torso=["attack"]),
         "Dash": meta(shoot, "level-change shoot (mobility)", foot=["advance", "crouch"]),
         "Ult": meta(ult, "clinch: knees into elbow", foot=["planted"], torso=["attack"], kick="R")}
    return dict(guard=g, slots=s, idle=dict(bounce=0.02, period=48, shift=0.03, drift=6, breath=2))


@power("B1")
def brawler():  # scrappy street fighter: hunched, loose, wild arcs, headbutts and shoulders
    g = M(legs(lh=(18, 0, -16), lk=-30, rh=(-8, 0, 16), rk=-26, ra=10), body(root=(-6, -10, 0), waist=(-16, -4, 0), neck=(18, 8, 0), p=(0, -0.32, 0)),
          A("R", (10, 30, 0), 100), A("L", (25, -35, 0), 90))
    hay = T6(g, [A("R", (15, -15, 55), 85), Bd(g, -32, 2, (0, -0.02, 0.1))], [A("R", (86, 10, -30), 14), A("L", (5, -20, 20), 70), Bd(g, 30, -6, (0, -0.1, -0.26), LeftKnee=-46)],
             allow=("elbow_up", "hands_up"))
    over = T6(g, [A("L", (60, 0, 50), 100), Bd(g, 20, 4, (0, 0.02, 0.06))], [A("L", (80, 10, -25), 20), A("R", (15, 30, 0), 100), Bd(g, -30, -16, (0, -0.16, -0.24), LeftKnee=-50)],
              allow=("elbow_up", "hands_up", "hand_in_head"))
    bump = T6(g, [A2((5, 10, 10), 110), Bd(g, -40, 0, (0.06, -0.04, 0.08))], [A("L", (20, -60, 0), 120), A("R", (-10, 20, 15), 90), Bd(g, -70, -10, (0.18, -0.12, -0.32), LeftKnee=-46)],
              allow=("crossed_knees",))
    head = T6(g, [A2((-15, 0, 35), 70), Bd(g, 0, 10, (0, 0.06, 0.12), neck=(30, 0, 0))],
              [A2((-20, 0, 40), 60), Bd(g, 0, -26, (0, -0.1, -0.36), neck=(-22, 0, 0), LeftKnee=-50)],
              extra=[("h", 3, [A2((-20, 0, 40), 60), Bd(g, 0, -18, (0, -0.08, -0.28), neck=(-4, 0, 0))], "io")], wend=14)
    big = T6(g, [A("R", (20, -30, 60), 80), Bd(g, -40, 4, (0, 0.04, 0.12))], [A("R", (88, 10, -30), 10), A("L", (0, -20, 25), 60), Bd(g, 40, -16, (0, -0.2, -0.4), LeftKnee=-54)],
             allow=("elbow_up", "hands_up"), extra=[("w", -8, [A("R", (5, -25, 55), 80), Bd(g, -46, 2, (0, -0.06, 0.16))], "slow")])
    tackle = T6(g, [A2((10, 20, 0), 100), Bd(g, -20, -10, (0, -0.16, 0.06), LeftKnee=-56)], [A2((40, 30, 0), 80), Bd(g, -40, -30, (0, -0.3, -0.5), LeftKnee=-60)])
    pound_l = T6(g, [A("L", (70, 0, 45), 110)], [A("L", (70, 15, -15), 30), Bd(g, -18, -18, (0, -0.2, -0.16))], allow=("elbow_up", "hands_up", "hand_in_head"))
    pound_r = T6(g, [A("R", (70, 0, 45), 110)], [A("R", (70, 15, -15), 30), Bd(g, 18, -18, (0, -0.2, -0.16))], allow=("elbow_up", "hands_up", "hand_in_head"))
    ult = dict(rush(pound_r, pound_l), extra=[("w", -10, [A2((-15, 0, 35), 70), Bd(g, 0, 8, (0, 0.04, 0.1), neck=(26, 0, 0))], "io")])
    for t in (hay, over, bump, head, big, tackle, pound_l, pound_r, ult):
        t["ws"] = dict(legs=0.22, torso=0.12, p=0.22)
    s = {"M1_1": meta(hay, "looping haymaker", foot=["advance", "attack"], torso=["attack", "twist"]),
         "M1_2": meta(over, "wild overhand", foot=["planted"], side="L"),
         "M1_3": meta(bump, "shoulder bump", foot=["sidestep_l"], torso=["attack"]),
         "M1_4": meta(head, "headbutt finisher", foot=["advance"], torso=["attack"]),
         "Blast": meta(big, "wound-up haymaker (heavy)", foot=["advance"], torso=["attack", "twist"]),
         "Burst": meta(rush(hay, over), "wild swing flurry", foot=["advance"]),
         "Dash": meta(tackle, "shoulder tackle (mobility)", foot=["advance", "long"]),
         "Ult": meta(ult, "grab-and-pound into headbutt", foot=["planted"], torso=["attack"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.02, period=96, roll=6, sway=8, breath=3))


@power("B1")
def frosttouch():  # aikido: calm hanmi, centre-line open hands, redirect then strike, minimal torso
    g = M(legs(lh=(18, 0, -8), lk=-20, rh=(-10, 0, 24), rk=-14), body(root=(0, -40, 0), waist=(0, -4, 0), neck=(0, 40, 0), p=(0, -0.18, 0)),
          A("R", (48, 18, 0), 45), A("L", (58, -12, 0), 30))
    calm = dict(legs=0.15, torso=0.12, p=0.15)
    redirect = T6(g, [A("L", (62, 40, -25), 25), A("R", (10, 25, 0), 95, (-40, 0, 0)), Bd(g, -8, dp=(0, -0.02, 0.02))],
                  [A("L", (50, 55, -35), 20), A("R", (70, 0, -4), 6, (-60, 0, 0)), Bd(g, 22, -4, (0, -0.06, -0.16), LeftKnee=-30)])
    shomen = T6(g, [A("L", (68, 30, 0), 70), Bd(g, 6, 2, (0, 0.02, 0.02))], [A("L", (50, -5, 0), 8, (10, 0, 0)), Bd(g, -10, -6, (0, -0.08, -0.14), LeftKnee=-30)],
                allow=("hand_in_head",))
    irimi = T6(g, [A("L", (30, -40, 0), 80, (-40, 0, 0)), Bd(g, 0, 0, (0.1, -0.02, 0))],
               [A("L", (72, -30, -10), 30, (-60, 0, 0)), A("R", (30, 10, 10), 70), Bd(g, 60, -4, (0.2, -0.08, -0.22), LeftKnee=-30)], allow=("crossed_knees",))
    kote = T6(g, [A2((55, 25, 0), 45, (0, 0, 30)), Bd(g, 10, 0, (0, -0.02, 0))],
              [A2((40, 30, 0), 50, (0, 0, -40)), Bd(g, -50, -10, (0, -0.24, -0.06), LeftKnee=-40, RightKnee=-36)], wend=14,
              extra=[("h", 4, [A2((35, 30, 0), 55, (0, 0, -50)), Bd(g, -56, -12, (0, -0.26, -0.04))], "io")])
    icepalm = T6(g, [A("R", (0, 20, 0), 110, (-50, 0, 0)), Bd(g, -10, 0, (0, -0.04, 0.04))], [A("R", (72, 0, -4), 4, (-65, 0, 0)), Bd(g, 26, -6, (0, -0.08, -0.22), LeftKnee=-32)])
    kokyu = T6(g, [A2((30, 30, 0), 70, (-30, 0, 0)), Bd(g, -12, 0, (0, -0.14, 0.06))],
               [A2((70, 10, -15), 10, (-55, 0, 0)), Bd(g, 18, -8, (0, -0.22, -0.3), LeftKnee=-44)], ec="slow",
               extra=[("w", -8, [A2((15, 30, 0), 90, (-40, 0, 0)), Bd(g, -20, 2, (0, -0.2, 0.08))], "io")])
    tenkan = T6(g, [A("L", (58, -12, 0), 30), Bd(g, -30, 0, (0, -0.04, 0))], [A("L", (70, -20, 0), 20, (-40, 0, 0)), Bd(g, -120, -2, (0.24, -0.08, -0.1))],
                allow=("crossed_knees", "pop"), es="io")
    ult = dict(rush(redirect, irimi), extra=[("w", -10, [A("L", (62, 40, -25), 25), Bd(g, -12, 0, (0, -0.06, 0.04))], "io")])
    for t in (redirect, shomen, irimi, kote, icepalm, kokyu, tenkan, ult):
        t["ws"] = calm
    s = {"M1_1": meta(redirect, "parry-redirect into palm", foot=["planted"], torso=["block_parry"]),
         "M1_2": meta(shomen, "shomen-uchi hand blade", foot=["advance"], side="L"),
         "M1_3": meta(irimi, "irimi entering palm", foot=["sidestep_r"], side="L"),
         "M1_4": meta(kote, "kote-gaeshi wrist turn finisher", foot=["pivot"], torso=["attack", "twist"]),
         "Bolt": meta(icepalm, "frost palm thrust", foot=["advance"]),
         "Blast": meta(kokyu, "kokyu-nage two-hand throw (heavy)", foot=["advance"], torso=["attack"]),
         "Dash": meta(tenkan, "tenkan pivot glide (mobility)", foot=["dodge"]),
         "Ult": meta(ult, "redirect-enter cycle", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.006, period=96, breath=1.0))


@power("B1")
def windfist():  # tai chi: soft bow stance, rounded ward-off, flowing chambers into short fa-jin release
    g = M(legs(lh=(30, 0, -12), lk=-40, rh=(-18, 0, 18), rk=-6, ra=10), body(root=(0, -30, 0), neck=(0, 30, 0), p=(0, -0.25, 0)),
          A("L", (55, -45, 0), 80), A("R", (15, 20, 0), 60, (-60, 0, 0)))
    flow = dict(legs=0.2, torso=0.25, p=0.2)
    brush = T6(g, [A("L", (20, -20, 30), 40), A("R", (20, 20, 15), 110, (-50, 0, 0)), Bd(g, -16, 0, (0, -0.08, 0.12))],
               [A("L", (-5, 0, 25), 15, (-40, 0, 0)), A("R", (72, 0, -4), 6, (-62, 0, 0)), Bd(g, 22, -4, (0, -0.1, -0.24), LeftKnee=-48)])
    cloud = T6(g, [A("L", (60, 40, -20), 40, (-30, 0, 0)), Bd(g, 24, 0, (0, -0.06, 0))],
               [A("L", (65, -40, 40), 30, (-40, 0, 0)), A("R", (20, 30, 0), 70, (-40, 0, 0)), Bd(g, -30, 0, (0, -0.08, -0.06))], es="io", allow=("elbow_up",))
    mane = T6(g, [A("L", (10, 30, 0), 60), A("R", (60, 20, 0), 90, (-30, 0, 0)), Bd(g, -10, 0, (0, -0.06, 0.08))],
              [A("L", (75, -20, 35), 15, (-20, 0, 0)), A("R", (0, 0, 20), 10, (-50, 0, 0)), Bd(g, 26, -2, (0, -0.06, -0.2), LeftKnee=-46)], allow=("elbow_up",))
    dpush = T6(g, [A2((35, 30, 0), 115, (-60, 0, 0)), Bd(g, 0, 2, (0, -0.12, 0.14))], [A2((70, 15, -10), 10, (-62, 0, 0)), Bd(g, 6, -6, (0, -0.14, -0.3), LeftKnee=-50)],
               wend=14, extra=[("h", 3, [A2((68, 15, -10), 14, (-60, 0, 0)), Bd(g, 6, -4, (0, -0.13, -0.26))], "io")])
    whip = T6(g, [A("L", (30, -30, 0), 90, (-40, 0, 0)), A("R", (60, 0, 50), 20, (60, 0, 0)), Bd(g, 20, 0, (0, -0.06, 0.06))],
              [A("L", (72, 0, 6), 6, (-62, 0, 0)), A("R", (55, 0, 60), 10, (60, 0, 0)), Bd(g, -26, -4, (0, -0.08, -0.22), LeftKnee=-46)], allow=("elbow_up",))
    heavy = dict(dpush, ec="slow", extra=[("w", -10, [A2((25, 30, 0), 120, (-60, 0, 0)), Bd(g, -6, 4, (0, -0.24, 0.18))], "slow")])
    heavy["extra"] = [(a, o, (g if ps == "g" else M(g, *ps)), e) for a, o, ps, e in [("w", -10, [A2((25, 30, 0), 120, (-60, 0, 0)), Bd(g, -6, 4, (0, -0.24, 0.18))], "slow")]]
    glide = T6(g, [A("L", (55, -45, 0), 80), Bd(g, 0, 0, (0, -0.1, 0.04))], [A("L", (70, -30, 0), 50), A("R", (40, 20, 0), 60, (-50, 0, 0)), Bd(g, 10, -4, (0, -0.12, -0.3))], es="io")
    ult = dict(rush(cloud, brush))
    ult["extra"] = [("w", -12, M(g, A2((30, 30, 0), 110, (-60, 0, 0)), Bd(g, 0, 2, (0, -0.2, 0.14))), "slow")]
    for t in (brush, cloud, mane, dpush, whip, heavy, glide, ult):
        t["ws"] = flow
    s = {"M1_1": meta(brush, "brush-knee push", foot=["advance"], torso=["attack"]),
         "M1_2": meta(cloud, "cloud hands sweep", foot=["sidestep_l"], side="L"),
         "M1_3": meta(mane, "parting the wild horse mane", foot=["advance"], side="L"),
         "M1_4": meta(dpush, "double push fa-jin finisher", foot=["planted"], torso=["attack"]),
         "Bolt": meta(whip, "single whip palm", foot=["advance"], side="L"),
         "Blast": meta(heavy, "sinking double push (heavy)", foot=["advance"], torso=["attack", "heavy"]),
         "Dash": meta(glide, "cat-step glide (mobility)", foot=["advance", "long"]),
         "Ult": meta(ult, "cloud hands into push cycle", foot=["planted"])}
    return dict(guard=g, slots=s, idle=dict(bounce=0.012, period=96, sway=10, drift=10, breath=2, shift=0.04))
