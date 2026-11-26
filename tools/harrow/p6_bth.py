# Twelfth Hearth slice classes (ASSETS). Batch "TH". Each class: own guard/silhouette, own rhythm, own techniques.
# Foundation = HKX components picked per slot (footwork/torso/strike) from the raw Skyrim library; poses authored here.
# Fighter  : disciplined shield-wall soldier. Square, grounded, shield always covering; short economical cuts; one committed cleave.
# Rogue    : low predatory crouch, reverse-grip daggers; fast flicks, sudden lunges, slips rather than blocks.
# Wizard   : upright, still, staff in the left hand; restrained precise gestures; power from small motions.
# Cleric   : planted devout warrior, mace + shield bearing a holy symbol; deliberate, two-beat rhythm, prayers with the whole body.
from powers6 import *

UP = ("elbow_up", "hands_up")


def th(spec, cls):
    spec["module"] = "Clips_TH_" + cls
    spec["timing"] = {k: k for k in spec["slots"]}
    spec["end_in_stance"] = True
    return spec


@power("TH")
def Fighter():
    g = M(legs(lh=(24, 0, -10), lk=-28, la=4, rh=(-10, 0, 12), rk=-14, ra=10), body(root=(-4, -18, 0), waist=(-4, -6, 0), neck=(4, 20, 0), p=(0, -0.2, 0)),
          A("R", (22, 28, 0), 62, (-12, 0, 0)), A("L", (38, 42, 0), 96))
    ws = dict(legs=0.25, torso=0.2, p=0.25)
    light = T6(g, [A("R", (8, 40, 0), 112, (-20, 0, 0)), Bd(g, -10, 0, (0, 0, 0.05))],
               [A("R", (84, 4, 0), 6, (8, 0, 0)), A("L", (44, 46, 0), 92), Bd(g, 16, -6, (0, -0.05, -0.35))], es="snap", ws=ws)
    heavy = T6(g, [A("R", (150, 18, 22), 92, (-30, 0, 0)), A("L", (30, 30, 0), 80), Bd(g, -18, 6, (0, 0.04, 0.12))],
               [A("R", (58, 8, 0), 10, (30, 0, 0)), A("L", (20, 20, 10), 70), Bd(g, 22, -16, (0, -0.26, -0.55), LeftKnee=-48)], ec="slow", es="snap", ws=ws,
               allow=UP, extra=[("h", 5, [A("R", (54, 8, 0), 12, (34, 0, 0)), Bd(g, 20, -15, (0, -0.27, -0.56), LeftKnee=-50)], "hold")])
    rally = T6(g, [A("R", (10, 20, 0), 30, (0, 0, 0)), A("L", (10, 20, 0), 40), Bd(g, 0, 8, (0, 0.06, 0))],
               [A("R", (100, 18, 0), 70, (-20, 0, 0)), A("L", (34, 40, 0), 90), Bd(g, 4, -2, (0, 0.02, 0))], ec="slow", es="io", ws=ws, allow=UP,
               extra=[("h", 10, [A("R", (98, 18, 0), 72, (-20, 0, 0)), Bd(g, 4, -3, (0, 0.03, 0))], "hold")])
    throw = T6(g, [A("R", (130, -10, 40), 100, (-30, 0, 0)), Bd(g, -24, 6, (0, 0, 0.1))],
               [A("R", (70, 8, 0), 12, (20, 0, 0)), Bd(g, 20, -8, (0, -0.06, -0.2))], es="expo", ws=ws, allow=UP)
    drink = T6(g, [A("R", (30, 50, 0), 100, (-20, 0, 0))], [A("R", (62, 62, 0), 142, (-30, 0, 0)), Bd(g, 0, 8, (0, 0, 0), neck=(-12, 20, 0))],
               ec="io", es="io", ws=ws, allow=UP + ("hand_in_head", "hand_beside_head"),
               extra=[("h", 10, [A("R", (64, 62, 0), 144, (-34, 0, 0)), Bd(g, 0, 10, (0, 0, 0), neck=(-16, 20, 0))], "hold")])
    dodge = T6(g, [Bd(g, 0, 2, (0, -0.06, 0))], [Bd(g, 12, 6, (0.95, -0.18, 0.45)), A("L", (46, 46, 0), 94)], es="expo", ws=dict(ws, legs=0.4))
    perfect = T6(g, [Bd(g, 0, 0, (0, -0.1, 0))], [Bd(g, -28, -10, (-1.25, -0.34, 0.15), LeftKnee=-60), A("R", (30, 40, 0), 70)], es="expo", ws=dict(ws, legs=0.45))
    block = T6(g, [A("L", (60, 36, 0), 92)], [A("L", (70, 30, 0), 100), A("R", (16, 26, 0), 66), Bd(g, -6, 6, (0, -0.12, 0.18))], es="snap", ws=ws)
    hit = T6(g, [Bd(g, 0, 2, (0, 0, 0.05))], [Bd(g, 14, 14, (0, -0.06, 0.36), neck=(-10, 10, 0)), A("R", (10, 30, 20), 40), A("L", (20, 30, 10), 70)], es="snap", ws=ws)
    victory = T6(g, [A("R", (60, 10, 0), 80, (-10, 0, 0)), Bd(g, 0, 2, (0, 0, 0))],
                 [A("R", (162, 0, 10), 12, (0, 0, 0)), A("L", (14, 20, 0), 60), Bd(g, 6, 6, (0, 0.06, 0), neck=(-14, 10, 0))], ec="slow", es="io", ws=ws, allow=UP,
                 extra=[("h", 18, [A("R", (164, 0, 10), 10, (0, 0, 0)), Bd(g, 6, 7, (0, 0.07, 0), neck=(-16, 10, 0))], "hold")])
    s = {"AttackLight": meta(light, "covered thrust", foot=["advance"]),
         "AttackHeavy": meta(heavy, "committed overhead cleave", foot=["advance", "long"]),
         "Ability": meta(rally, "second wind rally", foot=["planted"]),
         "Throw": meta(throw, "overhand throw", foot=["planted"]),
         "UseItem": meta(drink, "draught behind the shield", foot=["planted"]),
         "Dodge": meta(dodge, "shield-side step out", foot=["dodge"]),
         "PerfectEvade": meta(perfect, "low slip under the swing", foot=["dodge"]),
         "Block": meta(block, "shield brace", foot=["planted"]),
         "Hit": meta(hit, "recoil", foot=["retreat"]),
         "Victory": meta(victory, "blade raised", foot=["planted"])}
    return th(dict(guard=g, slots=s, idle=dict(bounce=0.01, period=96, breath=1.6, sway=1.5)), "Fighter")


@power("TH")
def Rogue():
    g = M(legs(lh=(40, 0, -14), lk=-62, la=20, rh=(8, 0, 16), rk=-52, ra=26), body(root=(-14, -26, 0), waist=(-10, -6, 0), neck=(16, 26, 0), p=(0, -0.55, 0)),
          A("R", (30, 34, 0), 100, (-30, 0, 0)), A("L", (42, 28, 0), 112, (-20, 0, 0)))
    ws = dict(legs=0.35, torso=0.25, p=0.35)
    light = T6(g, [A("R", (24, 70, 0), 122, (-30, 0, 0)), Bd(g, 10, 0, (0, 0, 0.04))],
               [A("R", (72, -30, 0), 22, (10, 0, 0)), Bd(g, -22, -6, (0, -0.04, -0.32))], es="expo", ws=ws)
    heavy = T6(g, [A("R", (140, 20, 10), 70, (-20, 0, 0)), A("L", (110, 10, 0), 70), Bd(g, 0, 4, (0, -0.2, 0.12))],
               [A("R", (62, 10, 0), 22, (50, 0, 0)), A("L", (50, 10, 0), 30, (40, 0, 0)), Bd(g, 8, -30, (0, -0.42, -0.9))], ec="io", es="expo", ws=ws,
               allow=UP + ("extreme_lean",), extra=[("h", 4, [A("R", (58, 10, 0), 24, (54, 0, 0)), Bd(g, 8, -31, (0, -0.44, -0.92))], "hold")])
    dash = T6(g, [Bd(g, 0, 4, (0, -0.1, 0.1))], [Bd(g, 0, -22, (0, -0.32, -1.6)), A("R", (10, 20, 0), 60), A("L", (10, 20, 0), 60)], es="expo", ws=dict(ws, legs=0.5),
              allow=("extreme_lean",))
    throw = T6(g, [A("R", (30, 74, 0), 118, (-40, 0, 0)), Bd(g, 16, 0, (0, 0, 0.04))],
               [A("R", (82, -42, 0), 0, (20, 0, 0)), Bd(g, -24, -6, (0, -0.02, -0.1))], es="expo", ws=ws)
    drink = T6(g, [A("L", (30, 50, 0), 100)], [A("L", (60, 64, 0), 144, (-30, 0, 0)), Bd(g, 0, 10, (0, 0.1, 0), neck=(-14, 26, 0))], ec="snap", es="snap", ws=ws,
               allow=UP + ("hand_in_head", "hand_beside_head"))
    dodge = T6(g, [Bd(g, 0, 0, (0, -0.08, 0))], [Bd(g, 30, -10, (-1.2, -0.4, 0.3)), A("R", (20, 20, 20), 60), A("L", (30, 20, 20), 60)], es="expo", ws=dict(ws, legs=0.5))
    perfect = T6(g, [Bd(g, 0, 0, (0, -0.12, 0))], [Bd(g, 46, -14, (0.7, -0.3, -0.55)), A("R", (60, -20, 0), 40)], es="expo", ws=dict(ws, legs=0.5))
    block = T6(g, [A2((40, 50, 0), 100)], [A2((62, 42, 0), 88, (-20, 0, 0)), Bd(g, 0, 6, (0, -0.06, 0.16))], es="snap", ws=ws)
    hit = T6(g, [Bd(g, 0, 2, (0, 0, 0.04))], [Bd(g, -16, 16, (0, 0.02, 0.4), neck=(-6, 26, 0)), A("R", (10, 20, 30), 60), A("L", (10, 20, 30), 60)], es="snap", ws=ws)
    victory = T6(g, [A("R", (70, 30, 0), 120)], [A("R", (70, 50, 0), 118, (-50, 0, 0)), A("L", (10, 10, 10), 30), Bd(g, 10, 14, (0, 0.4, 0), neck=(-6, 6, 0))],
                 ec="io", es="io", ws=ws, allow=UP, extra=[("h", 16, [A("R", (40, 30, 0), 90), Bd(g, 12, 16, (0, 0.42, 0))], "slow")])
    s = {"AttackLight": meta(light, "flick slash", foot=["advance"]),
         "AttackHeavy": meta(heavy, "plunging sneak strike", foot=["advance", "long"]),
         "Ability": meta(dash, "cunning dash", foot=["dash"]),
         "Throw": meta(throw, "sidearm knife flick", foot=["planted"]),
         "UseItem": meta(drink, "quick swig", foot=["planted"], side="L"),
         "Dodge": meta(dodge, "low side roll-out", foot=["dodge"]),
         "PerfectEvade": meta(perfect, "slip past the edge", foot=["dodge"]),
         "Block": meta(block, "crossed-dagger catch", foot=["planted"]),
         "Hit": meta(hit, "twisting recoil", foot=["retreat"]),
         "Victory": meta(victory, "dagger flip and rise", foot=["planted"])}
    return th(dict(guard=g, slots=s, idle=dict(bounce=0.03, period=48, breath=1.0, shift=0.04, sway=3.0)), "Rogue")


@power("TH")
def Wizard():
    g = M(legs(lh=(10, 0, -8), lk=-12, rh=(-4, 0, 8), rk=-8, ra=4), body(root=(-2, -10, 0), waist=(-2, -3, 0), neck=(4, 10, 0), p=(0, -0.05, 0)),
          A("L", (24, 10, 0), 72, (0, 0, 0)), A("R", (14, 22, 0), 38, (-20, 0, 0)))
    ws = dict(legs=0.08, torso=0.12, p=0.08)
    bolt = T6(g, [A("R", (34, 72, 0), 118, (-40, 0, 0)), Bd(g, -6, 0, (0, 0, 0.02))],
              [A("R", (90, 2, 0), 0, (12, 0, 0)), Bd(g, 8, -2, (0, 0, -0.04))], ec="io", es="expo", ws=ws,
              extra=[("h", 6, [A("R", (88, 2, 0), 2, (14, 0, 0))], "hold")])
    aoe = T6(g, [A("L", (150, 0, 0), 30, (0, 0, 0)), A("R", (60, 20, 30), 40), Bd(g, 0, 6, (0, 0.06, 0))],
             [A("L", (66, 10, 0), 20, (10, 0, 0)), A("R", (20, 20, 20), 30), Bd(g, -6, -10, (0, -0.22, -0.06), LeftKnee=-34, RightKnee=-26)], ec="slow", es="snap", ws=ws,
             allow=UP, extra=[("h", 8, [A("L", (64, 10, 0), 20, (12, 0, 0)), Bd(g, -6, -11, (0, -0.23, -0.06), LeftKnee=-36, RightKnee=-28)], "hold")])
    buff = T6(g, [A("R", (70, 30, 30), 60, (-10, 0, 0))], [A("R", (88, -20, -10), 20, (-20, 0, 0)), Bd(g, -4, 0, (0, 0, 0))], ec="io", es="io", ws=ws, allow=UP,
              extra=[("w", 8, [A("R", (100, 10, 10), 40, (-10, 0, 0))], "io"), ("w", 16, [A("R", (80, 40, -10), 30, (-10, 0, 0))], "io")])
    jab = T6(g, [A("L", (34, 20, 0), 90), A("R", (30, 50, 0), 100), Bd(g, -8, 2, (0, 0, 0.06))],
             [A("L", (62, 20, 0), 40), A("R", (52, 40, 0), 70), Bd(g, 10, -6, (0, -0.04, -0.3))], es="snap", ws=dict(ws, legs=0.2, p=0.2))
    throw = T6(g, [A("R", (40, 60, 0), 120, (-30, 0, 0))], [A("R", (80, -10, 0), 10, (10, 0, 0)), Bd(g, 10, -4, (0, 0, -0.06))], es="io", ws=ws)
    drink = T6(g, [A("R", (30, 50, 0), 100)], [A("R", (62, 62, 0), 144, (-30, 0, 0)), Bd(g, 0, 6, (0, 0, 0), neck=(-14, 10, 0))], ec="io", es="io", ws=ws,
               allow=UP + ("hand_in_head", "hand_beside_head"), extra=[("h", 12, [A("R", (64, 62, 0), 145, (-32, 0, 0))], "hold")])
    dodge = T6(g, [Bd(g, 0, 0, (0, -0.04, 0))], [Bd(g, 0, 4, (0, -0.08, 1.2)), A("R", (30, -10, 30), 20)], es="expo", ws=dict(ws, legs=0.3))
    perfect = T6(g, [Bd(g, 0, 0, (0, -0.06, 0))], [Bd(g, -40, -4, (-1.0, -0.16, 0.1)), A("R", (40, -30, 20), 10)], es="expo", ws=dict(ws, legs=0.35))
    block = T6(g, [A("L", (50, -10, 0), 70)], [A("L", (64, -24, 0), 64, (0, 0, 0)), A("R", (66, 44, 0), 64), Bd(g, 0, 6, (0, -0.04, 0.14))], es="snap", ws=ws)
    hit = T6(g, [Bd(g, 0, 2, (0, 0, 0.03))], [Bd(g, 10, 16, (0, 0, 0.34), neck=(-12, 10, 0)), A("R", (20, -10, 40), 20)], es="snap", ws=ws)
    victory = T6(g, [A("R", (40, 60, 0), 110)], [A("R", (36, 74, 0), 114, (-30, 0, 0)), Bd(g, 0, -8, (0, 0, 0), neck=(18, 0, 0))], ec="slow", es="io", ws=ws,
                 extra=[("h", 20, [A("R", (36, 74, 0), 114, (-30, 0, 0)), Bd(g, 0, -9, (0, 0, 0), neck=(20, 0, 0))], "hold")])
    s = {"CastBolt": meta(bolt, "drawn arcane dart", foot=["planted"], torso=["cast"]),
         "CastAoE": meta(aoe, "staff-strike shockwave", foot=["planted"], torso=["cast"]),
         "CastBuff": meta(buff, "traced ward sigil", foot=["planted"], torso=["cast"]),
         "AttackLight": meta(jab, "staff jab", foot=["advance"]),
         "Throw": meta(throw, "underhand toss", foot=["planted"]),
         "UseItem": meta(drink, "measured sip", foot=["planted"]),
         "Dodge": meta(dodge, "gliding step back", foot=["dodge"]),
         "PerfectEvade": meta(perfect, "turning sidestep", foot=["dodge"]),
         "Block": meta(block, "staff ward", foot=["planted"]),
         "Hit": meta(hit, "staggered back", foot=["retreat"]),
         "Victory": meta(victory, "quiet bow", foot=["planted"])}
    return th(dict(guard=g, slots=s, idle=dict(bounce=0.0, period=96, breath=0.9)), "Wizard")


@power("TH")
def Cleric():
    g = M(legs(lh=(16, 0, -10), lk=-18, la=2, rh=(-6, 0, 10), rk=-12, ra=6), body(root=(-4, -12, 0), waist=(-6, -4, 0), neck=(6, 12, 0), p=(0, -0.12, 0)),
          A("L", (30, 36, 0), 82), A("R", (26, 24, 0), 80, (-20, 0, 0)))
    ws = dict(legs=0.2, torso=0.15, p=0.2)
    chop = T6(g, [A("R", (112, 10, 22), 100, (-30, 0, 0)), Bd(g, -10, 4, (0, 0.04, 0.06))],
              [A("R", (60, 10, 0), 22, (30, 0, 0)), Bd(g, 14, -8, (0, -0.12, -0.26))], ec="io", es="snap", ws=ws, allow=UP,
              extra=[("h", 4, [A("R", (58, 10, 0), 24, (32, 0, 0))], "hold")])
    heavy = T6(g, [A("L", (70, 30, 0), 80), A("R", (40, 30, 30), 90), Bd(g, -14, -4, (0, -0.04, -0.2))],
               [A("R", (64, 6, 0), 14, (36, 0, 0)), A("L", (30, 30, 10), 70), Bd(g, 18, -14, (0, -0.22, -0.48))], ec="io", es="snap", ws=ws, allow=UP,
               extra=[("w", 6, [A("R", (150, 10, 10), 90, (-30, 0, 0)), A("L", (60, 30, 0), 80), Bd(g, -8, 4, (0, 0.04, -0.24))], "io")])
    flame = T6(g, [A("L", (40, 40, 0), 100), Bd(g, -6, 2, (0, 0, 0.04))], [A("L", (88, 12, 0), 10), Bd(g, -18, -4, (0, -0.04, -0.12))], ec="io", es="snap", ws=ws, allow=("elbow_up",),
               extra=[("h", 8, [A("L", (88, 12, 0), 10), Bd(g, -18, -5, (0, -0.05, -0.13))], "hold")])
    ring = T6(g, [A("R", (160, 0, 10), 20), Bd(g, 0, 6, (0, 0.06, 0), neck=(-14, 12, 0))],
              [A("R", (40, 10, 0), 0, (20, 0, 0)), Bd(g, 0, -10, (0, -0.62, -0.1), LeftKnee=-80, RightKnee=-40)], ec="slow", es="snap", ws=dict(ws, legs=0.05),
              allow=UP + ("crossed_knees",), extra=[("h", 10, [A("R", (40, 10, 0), 0, (22, 0, 0)), Bd(g, 0, -10, (0, -0.63, -0.1), LeftKnee=-82, RightKnee=-42)], "hold")])
    bless = T6(g, [A("R", (50, 40, 0), 100)], [A("R", (82, 40, 0), 124, (-10, 0, 0)), A("L", (40, 60, 0), 110), Bd(g, 0, -6, (0, -0.04, 0), neck=(22, 0, 0))],
               ec="slow", es="io", ws=ws, allow=UP + ("hand_in_head",), extra=[("h", 12, [A("R", (82, 40, 0), 124, (-10, 0, 0)), Bd(g, 0, -7, (0, -0.05, 0), neck=(24, 0, 0))], "hold")])
    heal = T6(g, [A("L", (34, 66, 0), 118, (0, 0, 0)), Bd(g, 0, 4, (0, 0.02, 0), neck=(16, 10, 0))],
              [A("L", (80, -20, 0), 10, (-60, 0, 0)), Bd(g, -8, -4, (0, -0.02, -0.06), neck=(0, 12, 0))], ec="slow", es="io", ws=ws,
              extra=[("h", 10, [A("L", (82, -20, 0), 8, (-62, 0, 0))], "hold")])
    channel = T6(g, [A2((30, 30, 0), 60), Bd(g, 0, -6, (0, -0.1, 0), neck=(20, 0, 0))],
                 [A2((150, 0, 40), 20), Bd(g, 0, 8, (0, 0.06, 0), neck=(-24, 0, 0))], ec="slow", es="io", ws=ws, allow=UP,
                 extra=[("h", 12, [A2((154, 0, 42), 18), Bd(g, 0, 9, (0, 0.07, 0), neck=(-26, 0, 0))], "hold")])
    throw = T6(g, [A("R", (126, -10, 40), 100, (-30, 0, 0)), Bd(g, -20, 6, (0, 0, 0.08))], [A("R", (72, 8, 0), 14, (20, 0, 0)), Bd(g, 18, -8, (0, -0.06, -0.18))],
               es="io", ws=ws, allow=UP)
    drink = T6(g, [A("R", (30, 50, 0), 100)], [A("R", (62, 62, 0), 142, (-30, 0, 0)), Bd(g, 0, 8, (0, 0, 0), neck=(-12, 12, 0))], ec="io", es="io", ws=ws,
               allow=UP + ("hand_in_head", "hand_beside_head"), extra=[("h", 10, [A("R", (64, 62, 0), 144, (-32, 0, 0))], "hold")])
    dodge = T6(g, [Bd(g, 0, 2, (0, -0.06, 0))], [Bd(g, -14, 4, (-0.9, -0.16, 0.4)), A("L", (52, 40, 0), 86)], es="io", ws=dict(ws, legs=0.4))
    perfect = T6(g, [Bd(g, 0, 0, (0, -0.1, 0))], [Bd(g, 24, -8, (1.1, -0.3, 0.2), RightKnee=-56), A("L", (60, 40, 0), 86)], es="expo", ws=dict(ws, legs=0.45))
    block = T6(g, [A("L", (56, 36, 0), 86)], [A("L", (68, 26, 0), 96), A("R", (20, 24, 0), 80), Bd(g, -4, 8, (0, -0.14, 0.16), neck=(14, 12, 0))], es="snap", ws=ws)
    hit = T6(g, [Bd(g, 0, 2, (0, 0, 0.04))], [Bd(g, -12, 12, (0, -0.06, 0.3), neck=(-8, 12, 0)), A("R", (10, 30, 20), 50)], es="snap", ws=ws)
    victory = T6(g, [A("R", (60, 20, 0), 90)], [A("R", (150, 10, 10), 30), A("L", (20, 40, 0), 90), Bd(g, 0, 4, (0, 0.04, 0), neck=(-16, 0, 0))], ec="slow", es="io", ws=ws,
                 allow=UP, extra=[("h", 14, [A("R", (70, 40, 0), 110, (-20, 0, 0)), Bd(g, 0, -6, (0, -0.02, 0), neck=(22, 0, 0))], "slow")])
    s = {"AttackLight": meta(chop, "mace chop", foot=["advance"]),
         "AttackHeavy": meta(heavy, "shield-check into overhead smash", foot=["advance", "long"]),
         "CastBolt": meta(flame, "symbol thrust (sacred flame)", foot=["planted"], side="L", torso=["cast"]),
         "CastAoE": meta(ring, "kneeling mace-plant ring", foot=["planted"], torso=["cast"]),
         "CastBuff": meta(bless, "bowed blessing", foot=["planted"], torso=["cast"]),
         "Heal": meta(heal, "heart-to-palm mend", foot=["planted"], side="L", torso=["cast"]),
         "Ability": meta(channel, "channel divinity", foot=["planted"]),
         "Throw": meta(throw, "overhand throw", foot=["planted"]),
         "UseItem": meta(drink, "draught", foot=["planted"]),
         "Dodge": meta(dodge, "heavy step aside", foot=["dodge"]),
         "PerfectEvade": meta(perfect, "pivot under", foot=["dodge"]),
         "Block": meta(block, "braced shield, head down", foot=["planted"]),
         "Hit": meta(hit, "absorbing recoil", foot=["retreat"]),
         "Victory": meta(victory, "mace raised, then prayer", foot=["planted"])}
    return th(dict(guard=g, slots=s, idle=dict(bounce=0.006, period=96, breath=1.4, sway=1.0)), "Cleric")
