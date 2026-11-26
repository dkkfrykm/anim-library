# Phase 5: all powers, personalised + QA-gated. Builds on phase4 (TechClip technique layer over Skyrim dynamics).
# Adds: per-discipline guards solved with guardfit, a generic technique library, output-based foot planting with
# crossed-knee prevention, temporal smoothing outside strike windows, full-body pose QA (posecheck) per clip.
# Run: blender --background --python phase5.py -- --powers a,b|--batch unarmed|blades|casters|stand|base [--render] [--videos]
import bpy, sys, os, math, json
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase4 as P4
import posecheck
P2 = P4.P2; S = P4.S; rig = P4.rig
P, M, mirror, T, pose_at, eul_q = P4.P, P4.M, P4.mirror, P4.T, P4.pose_at, P4.eul_q
OUT = "C:/Users/mytwo/soulbound/skyrim/out"
D5 = os.path.join(OUT, "phase5")
HOLD = P2.HOLD

# ------------------------------------------------------------------ guards (arms from guardfit solves)
ARM = dict(
    box=P(RightShoulder=(30, 55, 0), RightElbow=(125, 0, 0), LeftShoulder=(40, -50, 0), LeftElbow=(110, 0, 0)),
    light=P(RightShoulder=(5, 50, 0), RightElbow=(125, 0, 0), LeftShoulder=(20, -50, 0), LeftElbow=(115, 0, 0)),
    brawl=P(RightShoulder=(5, 40, 0), RightElbow=(120, 0, 0), LeftShoulder=(15, -40, 0), LeftElbow=(115, 0, 0)),
    mech=P(RightShoulder=(20, 50, 0), RightElbow=(120, 0, 0), LeftShoulder=(35, -50, 0), LeftElbow=(105, 0, 0)),
    claw=P(RightShoulder=(20, 35, 0), RightElbow=(90, 0, 0), RightWrist=(-35, 0, 0), LeftShoulder=(20, -35, 0), LeftElbow=(90, 0, 0), LeftWrist=(-35, 0, 0)),
    cast=P(RightShoulder=(10, 60, 0), RightElbow=(115, 0, 0), RightWrist=(-40, 0, 0), LeftShoulder=(10, -60, 0), LeftElbow=(115, 0, 0), LeftWrist=(-40, 0, 0)),
    karate=P(LeftShoulder=(70, -35, 25), LeftElbow=(40, 0, 0), RightShoulder=(-60, 5, -20), RightElbow=(118, 0, 0)),
    sword=P(RightShoulder=(25, 55, 0), RightElbow=(75, 0, 0), RightWrist=(-10, 0, 0), LeftShoulder=(10, -60, 0), LeftElbow=(100, 0, 0)),
    dagger=P(RightShoulder=(5, 40, 0), RightElbow=(95, 0, 0), LeftShoulder=(5, -40, 0), LeftElbow=(95, 0, 0)),
)
LEGS = dict(
    karate=P4.KARATE_LEGS, box=P4.BOX_LEGS, light=P4.KICK_LEGS,
    brawl=P(LeftHip=(20, 0, -14), LeftKnee=(-30, 0, 0), RightHip=(-6, 0, 14), RightKnee=(-24, 0, 0), RightAnkle=(10, 0, 0)),
    beast=P(LeftHip=(46, 0, -14), LeftKnee=(-70, 0, 0), LeftAnkle=(20, 0, 0), RightHip=(20, 0, 14), RightKnee=(-60, 0, 0), RightAnkle=(30, 0, 0)),
    cast=P(LeftHip=(12, 0, -10), LeftKnee=(-14, 0, 0), RightHip=(-4, 0, 10), RightKnee=(-10, 0, 0), RightAnkle=(6, 0, 0)),
    sword=P(LeftHip=(26, 0, -10), LeftKnee=(-28, 0, 0), RightHip=(-12, 0, 10), RightKnee=(-10, 0, 0), RightAnkle=(10, 0, 0)),
)
BODY = dict(
    karate=P(Root=(0, -22, 0), Waist=(-4, -8, 0), Neck=(0, 26, 0), p=(0, -0.28, 0)),
    box=P(Root=(0, -20, 0), Waist=(-8, -6, 0), Neck=(6, 18, 0), p=(0, -0.24, 0)),
    light=P(Root=(0, -24, 0), Waist=(-2, -6, 0), Neck=(0, 22, 0), p=(0, -0.16, 0)),
    brawl=P(Root=(0, -12, 0), Waist=(-10, -4, 0), Neck=(8, 10, 0), p=(0, -0.3, 0)),
    beast=P(Root=(-18, -10, 0), Waist=(-14, -4, 0), Neck=(26, 10, 0), p=(0, -0.55, 0)),
    mech=P(Root=(0, -16, 0), Waist=(-4, -6, 0), Neck=(2, 14, 0), p=(0, -0.2, 0)),
    cast=P(Root=(0, -14, 0), Waist=(-2, -4, 0), Neck=(0, 12, 0), p=(0, -0.14, 0)),
    sword=P(Root=(0, -24, 0), Waist=(-4, -6, 0), Neck=(0, 22, 0), p=(0, -0.24, 0)),
)


def guard(arm, legs, body):
    return M(LEGS[legs], BODY[body], ARM[arm])


G = dict(karate=guard("karate", "karate", "karate"), box=guard("box", "box", "box"), kick=guard("light", "light", "light"),
         brawl=guard("brawl", "brawl", "brawl"), beast=guard("claw", "beast", "beast"), mech=guard("mech", "box", "mech"),
         palm=guard("cast", "cast", "cast"), cast=guard("cast", "cast", "cast"), sword=guard("sword", "sword", "sword"),
         dagger=guard("dagger", "sword", "sword"), heavy=guard("brawl", "brawl", "brawl"))

SIDE = {"R": "Right", "L": "Left"}


def armk(side, sh, el, wr=(0, 0, 0)):
    s = SIDE[side]
    sh = sh if side == "R" else (sh[0], -sh[1], -sh[2])
    return {s + "Shoulder": sh, s + "Elbow": (el, 0, 0), s + "Wrist": wr}


def turn(g, deg, lean=0, dp=(0, 0, 0), legs=None):
    b = {"Root": (g["Root"][0] + lean, g["Root"][1] + deg, 0), "Waist": (g["Waist"][0] + lean * 0.5, g["Waist"][1] + deg * 0.5, 0),
         "Neck": (g["Neck"][0], g["Neck"][1] - deg * 1.2, 0), "p": tuple(g["p"][k] + dp[k] for k in range(3))}
    if legs:
        b.update(legs)
    return b


def other(side): return "L" if side == "R" else "R"


# ------------------------------------------------------------------ technique builders
def strike_punch(g, side, kind="straight", hikite=False, power=1.0):
    d = 1 if side == "R" else -1  # right strikes turn hips left (+y)
    front = "LeftKnee" if True else "RightKnee"
    if kind == "straight":
        ch = M(g, armk(side, (28, 55, 0), 130), turn(g, -10 * d, dp=(0, -0.03, 0.03)))
        st = M(g, armk(side, (88, 0, -6), 2), turn(g, 26 * d * power, lean=-4 * power, dp=(0, -0.06 * power, -0.2 * power),
                                                  legs={front: (-40, 0, 0)}))
    elif kind == "palm":
        ch = M(g, armk(side, (-30, 20, -20), 120, (-60, 0, 0)), turn(g, -14 * d))
        st = M(g, armk(side, (86, 0, -4), 4, (-72, 0, 0)), turn(g, 28 * d, lean=-6, dp=(0, -0.08, -0.22), legs={front: (-42, 0, 0)}))
    elif kind == "hook":
        ch = M(g, armk(side, (40, 30, 30), 100), turn(g, 14 * d))
        st = M(g, armk(side, (44, 0, -84), 94), turn(g, -26 * d, lean=-4, dp=(0, -0.04, -0.06)))
    elif kind == "uppercut":
        ch = M(g, armk(side, (26, 30, 10), 104), turn(g, -12 * d, lean=-8, dp=(0, -0.16, 0)))
        st = M(g, armk(side, (118, 0, -10), 72), turn(g, 16 * d, lean=6, dp=(0, 0.06, -0.08)))
    elif kind == "haymaker":
        ch = M(g, armk(side, (20, -10, 50), 90), turn(g, -34 * d, dp=(0, -0.04, 0.12)))
        st = M(g, armk(side, (92, 0, -22), 10), turn(g, 34 * d * power, lean=-12, dp=(0, -0.14, -0.36), legs={front: (-48, 0, 0)}))
    elif kind == "claw":
        ch = M(g, armk(side, (70, -10, 55), 60, (-30, 0, 0)), turn(g, -20 * d, dp=(0, 0.02, 0.06)))
        st = M(g, armk(side, (40, 30, -40), 25, (-40, 0, 0)), turn(g, 28 * d, lean=-10, dp=(0, -0.12, -0.3), legs={front: (-50, 0, 0)}))
    elif kind == "slam":  # double-fist hammer (both arms)
        ch = M(g, armk("R", (150, 0, 20), 40), armk("L", (150, 0, 20), 40), turn(g, 0, lean=8, dp=(0, 0.08, 0.05)))
        st = M(g, armk("R", (60, 0, 10), 20), armk("L", (60, 0, 10), 20), turn(g, 0, lean=-18, dp=(0, -0.4, -0.15),
                                                                              legs={"LeftKnee": (-55, 0, 0), "RightKnee": (-45, 0, 0)}))
    elif kind == "double_palm":
        ch = M(g, armk("R", (-30, 20, -20), 120, (-60, 0, 0)), armk("L", (-30, 20, -20), 120, (-60, 0, 0)), turn(g, 0, dp=(0, -0.04, 0.06)))
        st = M(g, armk("R", (84, 0, -12), 6, (-72, 0, 0)), armk("L", (84, 0, -12), 6, (-72, 0, 0)), turn(g, 8, lean=-6, dp=(0, -0.1, -0.22),
                                                                                                   legs={front: (-42, 0, 0)}))
    elif kind == "sweep":  # caster horizontal sweep
        ch = M(g, armk(side, (70, 0, 60), 20, (-50, 0, 0)), turn(g, -26 * d))
        st = M(g, armk(side, (80, 0, -30), 10, (-60, 0, 0)), turn(g, 30 * d, lean=-4, dp=(0, -0.06, -0.12)))
    elif kind == "cut_diag":  # kesa-giri: from over the shoulder down across the body
        ch = M(g, armk(side, (150, 20, 25), 50, (-20, 0, 0)), turn(g, -22 * d, lean=4, dp=(0, 0.02, 0.06)))
        st = M(g, armk(side, (70, 30, -35), 10, (10, 0, 0)), turn(g, 30 * d, lean=-10, dp=(0, -0.12, -0.3), legs={front: (-46, 0, 0)}))
    elif kind == "cut_horiz":  # do: flat cut across
        ch = M(g, armk(side, (60, -30, 75), 50, (0, 0, 0)), turn(g, -34 * d, dp=(0, -0.02, 0.06)))
        st = M(g, armk(side, (85, 10, -45), 6, (0, 0, 0)), turn(g, 36 * d, lean=-6, dp=(0, -0.1, -0.24), legs={front: (-44, 0, 0)}))
    elif kind == "cut_rise":  # kiri-age: low to high
        ch = M(g, armk(side, (-5, 20, 25), 25, (10, 0, 0)), turn(g, -20 * d, lean=-8, dp=(0, -0.14, 0.04)))
        st = M(g, armk(side, (112, 0, -22), 14, (-12, 0, 0)), turn(g, 24 * d, lean=4, dp=(0, 0.02, -0.2)))
    elif kind == "thrust":  # tsuki: straight lunge
        ch = M(g, armk(side, (35, 55, 0), 115, (-10, 0, 0)), turn(g, -16 * d, dp=(0, -0.02, 0.1)))
        st = M(g, armk(side, (88, 0, -6), 2, (-12, 0, 0)), turn(g, 22 * d, lean=-8, dp=(0, -0.14, -0.42), legs={front: (-50, 0, 0)}))
    elif kind == "cleave2h":  # two-hand overhead cleave
        ch = M(g, armk("R", (160, 0, 12), 40), armk("L", (160, 0, 12), 50), turn(g, 0, lean=6, dp=(0, 0.04, 0.08)))
        st = M(g, armk("R", (72, 0, -8), 8), armk("L", (68, 0, -14), 14), turn(g, 6, lean=-16, dp=(0, -0.3, -0.3),
                                                                            legs={"LeftKnee": (-52, 0, 0), "RightKnee": (-24, 0, 0)}))
    elif kind == "dagger_slash":  # reverse-grip horizontal slash, other hand guarding low
        ch = M(g, armk(side, (50, -20, 60), 70, (-30, 0, 0)), turn(g, -26 * d, dp=(0, -0.06, 0.04)))
        st = M(g, armk(side, (70, 20, -50), 30, (-30, 0, 0)), turn(g, 30 * d, lean=-8, dp=(0, -0.12, -0.24), legs={front: (-44, 0, 0)}))
    else:
        raise KeyError(kind)
    if hikite and kind in ("straight", "palm"):
        oh = other(side)
        st = M(st, armk(oh, (-60, 5, -20), 118))
    return dict(guard=g, chamber=ch, strike=st, allow=("elbow_up", "hands_up", "hand_in_head") if kind in ("hook", "uppercut", "claw", "slam", "haymaker", "sweep", "cut_diag", "cut_horiz", "cut_rise", "cleave2h", "dagger_slash") else ())


KICKS = {  # right-leg deltas (from phase4 karate/kicker sets)
    "front": (P(RightHip=(102, 0, 4), RightKnee=(-124, 0, 0), RightAnkle=(22, 0, 0), LeftKnee=(-20, 0, 0)), P(RightHip=(96, 0, 4), RightKnee=(-4, 0, 0), RightAnkle=(-28, 0, 0), LeftKnee=(-16, 0, 0)), 0, 8),
    "round": (P(RightHip=(58, 0, 66), RightKnee=(-122, 0, 0), LeftKnee=(-20, 0, 0)), P(RightHip=(74, 0, 84), RightKnee=(-8, 0, 0), RightAnkle=(-22, 0, 0), LeftKnee=(-16, 0, 0)), 62, 4),
    "side": (P(RightHip=(76, 0, 44), RightKnee=(-124, 0, 0), LeftKnee=(-24, 0, 0)), P(RightHip=(14, 0, 84), RightKnee=(-4, 0, 0), RightAnkle=(10, 0, 0), LeftKnee=(-18, 0, 0)), 80, 0),
    "axe": (P(RightHip=(150, 0, 12), RightKnee=(-12, 0, 0), LeftKnee=(-10, 0, 0)), P(RightHip=(52, 0, 6), RightKnee=(-4, 0, 0), RightAnkle=(-10, 0, 0), LeftKnee=(-26, 0, 0)), 0, -10),
    "push": (P(RightHip=(110, 0, 4), RightKnee=(-120, 0, 0), RightAnkle=(30, 0, 0), LeftKnee=(-24, 0, 0)), P(RightHip=(96, 0, 4), RightKnee=(-2, 0, 0), RightAnkle=(16, 0, 0), LeftKnee=(-10, 0, 0)), 0, 16),
    "knee": (P(RightHip=(70, 0, 4), RightKnee=(-100, 0, 0), LeftKnee=(-16, 0, 0)), P(RightHip=(118, 0, 4), RightKnee=(-130, 0, 0), RightAnkle=(20, 0, 0), LeftKnee=(-10, 0, 0)), 0, -10),
}
COVER_ARMS = ARM["light"]


def kick(g, side, kind):
    ch_l, st_l, yaw, lean = KICKS[kind]
    if side == "L":
        ch_l, st_l = mirror(ch_l), mirror(st_l)
        yaw = -yaw
    arms = dict(COVER_ARMS)
    if kind == "round":  # counter-balance arm swings down/back
        arms.update(armk(side, (16, 0, 36), 70))
    ch = M(g, arms, ch_l, turn(g, yaw * 0.55, lean=lean * 0.3))
    st = M(g, arms, st_l, turn(g, yaw, lean=lean, dp=(0, 0.04, -0.06)))
    rt = M(g, arms, ch_l, turn(g, yaw * 0.5, lean=lean * 0.3))
    return dict(guard=g, chamber=ch, strike=st, retract=rt, kick=side, allow=(("elbow_up",) if kind == "axe" else ()) + (("crossed_knees",) if kind in ("round", "side") else ()))


def rush(a, b):
    """18-frame loop alternating two techniques (strike poses), ending on a's strike"""
    t = dict(a)
    t["loop"] = [(0, a["strike"]), (5, a["guard"]), (9, b["strike"]), (14, b["guard"]), (18, a["strike"])]
    t["allow"] = tuple(set(a.get("allow", ())) | set(b.get("allow", ())))
    if a.get("kick") or b.get("kick"):
        t["kick"] = a.get("kick") or b.get("kick")
    return t


def tech(g, spec):
    kind, side = spec[0], spec[1]
    if kind in KICKS:
        return kick(G[g], side, kind)
    if kind == "rush":
        return rush(tech(g, spec[2]), tech(g, spec[3]))
    return strike_punch(G[g], side, kind, hikite=(g == "karate"), power=spec[2] if len(spec) > 2 and isinstance(spec[2], (int, float)) else 1.0)


# ------------------------------------------------------------------ per-power specs: guard, slots {slot: tech spec}
st = lambda k, s="R", *a: (k, s) + a
POWERS = {
    "brawler": ("brawl", {"M1_1": st("haymaker", "R"), "M1_2": st("hook", "L"), "M1_3": st("uppercut", "R"), "M1_4": st("slam"), "Blast": st("haymaker", "R", 1.3), "Burst": st("rush", "R", st("haymaker", "R"), st("hook", "L")), "Ult": st("rush", "R", st("haymaker", "R"), st("haymaker", "L"))}),
    "flamefist": ("box", {"M1_1": st("straight", "L"), "M1_2": st("straight", "R"), "M1_3": st("hook", "L"), "M1_4": st("uppercut", "R"), "Bolt": st("straight", "R", 1.3), "Burst": st("rush", "R", st("straight", "R"), st("hook", "L")), "Ult": st("rush", "R", st("uppercut", "R"), st("hook", "L"))}),
    "dragonfist": ("beast", {"M1_1": st("palm", "R"), "M1_2": st("claw", "L"), "M1_3": st("front", "R"), "M1_4": st("claw", "R"), "Bolt": st("double_palm"), "Burst": st("rush", "R", st("claw", "R"), st("claw", "L")), "Ult": st("rush", "R", st("palm", "R"), st("round", "R"))}),
    "thunderfist": ("mech", {"M1_1": st("straight", "L"), "M1_2": st("straight", "R"), "M1_3": st("uppercut", "R"), "M1_4": st("straight", "R", 1.4), "Bolt": st("palm", "R"), "Burst": st("rush", "R", st("straight", "R"), st("straight", "L")), "Ult": st("rush", "R", st("straight", "R"), st("uppercut", "L"))}),
    "windfist": ("kick", {"M1_1": st("palm", "R"), "M1_2": st("round", "R"), "M1_3": st("palm", "L"), "M1_4": st("side", "R"), "Bolt": st("double_palm"), "Blast": st("round", "L"), "Ult": st("rush", "R", st("round", "R"), st("round", "L"))}),
    "frosttouch": ("palm", {"M1_1": st("palm", "R"), "M1_2": st("palm", "L"), "M1_3": st("sweep", "R"), "M1_4": st("double_palm"), "Bolt": st("palm", "R", 1.2), "Blast": st("double_palm"), "Ult": st("rush", "R", st("palm", "R"), st("palm", "L"))}),
    "speedster": ("box", {"M1_1": st("straight", "L"), "M1_2": st("straight", "R"), "M1_3": st("straight", "L"), "M1_4": st("hook", "R"), "Dash": st("straight", "R", 1.3), "Blast": st("rush", "R", st("straight", "R"), st("straight", "L")), "Ult": st("rush", "R", st("straight", "R"), st("straight", "L"))}),
    "phantomstep": ("kick", {"M1_1": st("palm", "R"), "M1_2": st("front", "R"), "M1_3": st("palm", "L"), "M1_4": st("round", "R"), "Dash": st("palm", "R", 1.3), "Burst": st("rush", "R", st("palm", "R"), st("front", "R")), "Ult": st("rush", "R", st("round", "R"), st("palm", "L"))}),
    "acrobat": ("kick", {"M1_1": st("front", "R"), "M1_2": st("round", "L"), "M1_3": st("round", "R"), "M1_4": st("axe", "R"), "Dash": st("push", "R"), "Burst": st("rush", "R", st("round", "R"), st("round", "L")), "Blast": st("side", "R"), "Ult": st("rush", "R", st("front", "R"), st("round", "L"))}),
    "limitbreaker": ("brawl", {"M1_1": st("straight", "L", 0.7), "M1_2": st("straight", "R", 0.7), "M1_3": st("hook", "L"), "M1_4": st("straight", "R", 1.4), "Blast": st("straight", "R", 1.5), "Bolt": st("palm", "R"), "Ult": st("rush", "R", st("straight", "R", 1.4), st("straight", "L", 1.2))}),
    "overdrive": ("mech", {"M1_1": st("straight", "R"), "M1_2": st("straight", "L"), "M1_3": st("hook", "R"), "M1_4": st("haymaker", "R"), "Blast": st("haymaker", "R", 1.3), "Burst": st("rush", "R", st("straight", "R"), st("straight", "L")), "Ult": st("rush", "R", st("haymaker", "R"), st("haymaker", "L"))}),
    "ironbody": ("heavy", {"M1_1": st("haymaker", "R"), "M1_2": st("haymaker", "L"), "M1_3": st("uppercut", "R"), "M1_4": st("slam"), "Blast": st("slam"), "Burst": st("rush", "R", st("haymaker", "R"), st("haymaker", "L")), "Ult": st("slam")}),
    "titanstrength": ("heavy", {"M1_1": st("straight", "R", 1.2), "M1_2": st("hook", "L"), "M1_3": st("uppercut", "R"), "M1_4": st("slam"), "Blast": st("haymaker", "R", 1.4), "Bolt": st("double_palm"), "Ult": st("slam")}),
    "unitedmight": ("box", {"M1_1": st("straight", "L"), "M1_2": st("straight", "R", 1.2), "M1_3": st("uppercut", "R"), "M1_4": st("haymaker", "R"), "Blast": st("straight", "R", 1.5), "Bolt": st("double_palm"), "Ult": st("rush", "R", st("straight", "R", 1.3), st("uppercut", "L"))}),
    "elasticemperor": ("kick", {"M1_1": st("straight", "L"), "M1_2": st("straight", "R"), "M1_3": st("front", "R"), "M1_4": st("haymaker", "R"), "Bolt": st("straight", "R", 1.4), "Blast": st("rush", "R", st("straight", "R"), st("straight", "L")), "Ult": st("rush", "R", st("straight", "R"), st("straight", "L"))}),
    "beastform": ("beast", {"M1_1": st("claw", "R"), "M1_2": st("claw", "L"), "M1_3": st("claw", "R"), "M1_4": st("double_palm"), "Bolt": st("claw", "R", 1.2), "Burst": st("rush", "R", st("claw", "R"), st("claw", "L")), "Ult": st("rush", "R", st("claw", "R"), st("claw", "L"))}),
    "dragonshift": ("beast", {"M1_1": st("claw", "L"), "M1_2": st("claw", "R"), "M1_3": st("haymaker", "R"), "M1_4": st("slam"), "Bolt": st("claw", "R"), "Burst": st("rush", "R", st("claw", "R"), st("claw", "L")), "Ult": st("slam")}),
}
for pid in ["karate", "boxer", "kicker"]:
    POWERS[pid] = None  # phase4 technique sets (approved)
CASTERS = ["chakra", "psychic", "chakramaster", "voidsovereign", "starbornascension", "astraloverlord", "infinityarchitect", "supernovagod", "absoluteinfinity", "divinesaiyan"]
CAST_SETS = [
    {"M1_1": st("palm", "R"), "M1_2": st("palm", "L"), "M1_3": st("sweep", "R"), "M1_4": st("double_palm")},
    {"M1_1": st("palm", "L"), "M1_2": st("sweep", "R"), "M1_3": st("palm", "R"), "M1_4": st("double_palm")},
    {"M1_1": st("sweep", "R"), "M1_2": st("sweep", "L"), "M1_3": st("palm", "R"), "M1_4": st("double_palm")},
    {"M1_1": st("palm", "R"), "M1_2": st("straight", "L"), "M1_3": st("palm", "R"), "M1_4": st("double_palm")},
]
BLADE_POWERS = {
    "demonhunter": ("sword", {"M1_1": st("cut_rise", "R"), "M1_2": st("cut_horiz", "R"), "M1_3": st("cut_diag", "R"), "M1_4": st("thrust", "R", 1.3), "Bolt": st("cut_diag", "R", 1.2), "Burst": st("rush", "R", st("cut_horiz", "R"), st("cut_diag", "R")), "Ult": st("rush", "R", st("cut_diag", "R"), st("cut_rise", "R"))}),
    "bladedancer": ("dagger", {"M1_1": st("dagger_slash", "R"), "M1_2": st("dagger_slash", "L"), "M1_3": st("cut_horiz", "R"), "M1_4": st("thrust", "R", 1.2), "Bolt": st("cut_diag", "R"), "Burst": st("rush", "R", st("dagger_slash", "R"), st("dagger_slash", "L")), "Ult": st("rush", "R", st("dagger_slash", "R"), st("dagger_slash", "L"))}),
    "soulblade": ("sword", {"M1_1": st("thrust", "R"), "M1_2": st("cut_diag", "R"), "M1_3": st("cut_rise", "R"), "M1_4": st("cut_horiz", "R", 1.2), "Bolt": st("thrust", "R", 1.3), "Blast": st("cut_diag", "R", 1.3), "Ult": st("rush", "R", st("thrust", "R"), st("cut_diag", "R"))}),
    "sunblade": ("sword", {"M1_1": st("cleave2h"), "M1_2": st("cut_horiz", "R"), "M1_3": st("cut_rise", "R"), "M1_4": st("cleave2h"), "Bolt": st("cut_diag", "R", 1.3), "Burst": st("rush", "R", st("cut_horiz", "R"), st("cleave2h")), "Ult": st("cleave2h")}),
    "soulrequiem": ("sword", {"M1_1": st("cut_horiz", "R"), "M1_2": st("cut_rise", "R"), "M1_3": st("thrust", "R"), "M1_4": st("cut_diag", "R"), "Bolt": st("thrust", "R", 1.3), "Burst": st("rush", "R", st("cut_horiz", "R"), st("cut_rise", "R")), "Ult": st("rush", "R", st("cut_diag", "R"), st("cut_horiz", "R"))}),
    "eclipsemonarch": ("dagger", {"M1_1": st("dagger_slash", "R"), "M1_2": st("dagger_slash", "L"), "M1_3": st("thrust", "R"), "M1_4": st("dagger_slash", "R", 1.2), "Blast": st("thrust", "R", 1.4), "Burst": st("rush", "R", st("dagger_slash", "R"), st("dagger_slash", "L")), "Ult": st("rush", "R", st("thrust", "R"), st("dagger_slash", "L"))}),
    "eclipseblacksun": ("dagger", {"M1_1": st("dagger_slash", "L"), "M1_2": st("dagger_slash", "R"), "M1_3": st("cut_rise", "R"), "M1_4": st("thrust", "R", 1.3), "Bolt": st("thrust", "R", 1.2), "Burst": st("rush", "R", st("dagger_slash", "L"), st("dagger_slash", "R")), "Ult": st("rush", "R", st("cut_rise", "R"), st("dagger_slash", "L"))}),
}
BLADES = ["demonhunter", "bladedancer", "soulblade", "sunblade", "soulrequiem", "eclipsemonarch", "eclipseblacksun"]
STAND = {"Sky_Stand_M1_1": st("straight", "R"), "Sky_Stand_M1_2": st("straight", "L"), "Sky_Stand_Barrage": st("rush", "R", st("straight", "R"), st("straight", "L")),
         "Sky_Stand_Heavy": st("haymaker", "R", 1.4), "Sky_Stand_Uppercut": st("uppercut", "R"), "Sky_Stand_Rush": st("straight", "R", 1.5),
         "Sky_Stand_Ult": st("rush", "R", st("hook", "R"), st("hook", "L"))}
STAND_SLOT = {"Sky_Stand_M1_1": "M1", "Sky_Stand_M1_2": "M1", "Sky_Stand_Barrage": "Burst", "Sky_Stand_Heavy": "Blast", "Sky_Stand_Uppercut": "M1_4",
              "Sky_Stand_Rush": "Dash", "Sky_Stand_Ult": "Ult"}

# kit kinds per power (E/R/F) from Powers config
KIT = json.load(open(os.path.join(OUT, "phase5_kits.json"))) if os.path.exists(os.path.join(OUT, "phase5_kits.json")) else {}


class Clip5(P4.TechClip):
    def windows(self):
        w = [(1, self.i + HOLD + max(9, (self.r - self.i - HOLD) // 2))]
        if self.loop:
            w.append((self.loop[0] - 1, self.loop[1]))
        if self.sword:
            w = [(max(0, self.w - 8), self.r)] + w[1:]
        return w

    def post(self):
        rows = self.rows
        n = len(rows)
        L = [{j: eul_q(r[j]) for j in rig.ORDER} for r in rows]
        ps = [Vector(r["p"]) for r in rows]
        win = self.windows()
        inwin = lambda f: any(a <= f <= b for a, b in win)
        for _ in range(5):  # smoothing outside strike windows, never across main->loop boundary
            new = [dict(x) for x in L]
            for f in range(1, n - 1):
                if inwin(f) or f in (self.n, self.n + 1):
                    continue
                for j in rig.ORDER:
                    a, b, c = L[f - 1][j], L[f][j], L[f + 1][j]
                    if a.dot(b) < 0: a = -a
                    if c.dot(b) < 0: c = -c
                    new[f][j] = b.slerp(a.slerp(c, 0.5), 0.5)
                ps_f = (ps[f - 1] + ps[f] * 2 + ps[f + 1]) / 4
                ps[f] = ps_f
            L = new
        for _ in range(3):  # pull the pelvis toward planted feet that are out of reach, then plant
            Ps = [P2.world_of(x) for x in L]
            shift = self.plant([dict(x) for x in Ps], ps, dry=True)
            if not shift:
                break
            for f, v in shift.items():
                ps[f] = ps[f] + v
        Ps = [P2.world_of(x) for x in L]
        self.plant(Ps, ps)
        # despike leg joints outside strike windows (IK pole flips), local space
        for f in range(1, n - 1):
            if inwin(f) or f in (self.n, self.n + 1):
                continue
            for j in ("RightHip", "RightKnee", "RightAnkle", "LeftHip", "LeftKnee", "LeftAnkle"):
                par = rig.J[j][0]
                lq = lambda g: (Ps[g][par].transposed() @ Ps[g][j]).to_quaternion()
                a, b, c = lq(f - 1), lq(f), lq(f + 1)
                if a.rotation_difference(b).angle > math.radians(22):
                    if c.dot(a) < 0: c = -c
                    m = a.slerp(c, 0.5)
                    Ps[f][j] = Ps[f][par] @ m.to_matrix()
                    for ch in [k for k in rig.ORDER if rig.J[k][0] == j]:
                        pass
            # re-derive children world rotations after a parent change
            for j in ("RightKnee", "RightAnkle", "LeftKnee", "LeftAnkle"):
                pass
        self.rows = [P2.to_rows(Pm, p) for Pm, p in zip(Ps, ps)]

    def plant(self, Ps, ps, dry=False):
        shift = {}
        kick = (self.tech or {}).get("kick") if self.tech else None
        n = len(Ps)
        for side, (hip, knee, ankle) in {"R": ("RightHip", "RightKnee", "RightAnkle"), "L": ("LeftHip", "LeftKnee", "LeftAnkle")}.items():
            a = (Vector(rig.J[knee][1]) - Vector(rig.J[hip][1])).length
            b = (Vector(rig.J[ankle][1]) - Vector(rig.J[knee][1])).length
            anchor = None
            rel = None
            for f in range(n):
                X = P2.joint_pos(Ps[f], ps[f])
                A = X[ankle]
                Fp = A + Ps[f][ankle] @ Vector((0, -0.13, -0.1))
                planted = Fp.y < posecheck.GROUND + 0.16 or (anchor is not None and Fp.y < posecheck.GROUND + 0.26)
                Rr = Ps[f]["Root"]
                if planted:
                    if anchor is None:
                        anchor = A.copy()
                        arot = Ps[f][ankle].copy()
                        # keep feet apart in the pelvis frame (no crossing), decided once per plant
                        loc = Rr.transposed() @ (anchor - X["Root"])
                        lim = 0.32
                        if side == "R" and loc.x < lim: loc.x = lim
                        if side == "L" and loc.x > -lim: loc.x = -lim
                        anchor = X["Root"] + Rr @ loc
                    Tg = Vector((anchor.x, A.y, anchor.z))
                else:
                    if anchor is not None:  # just released: ease out of the plant over 6 frames
                        rel = (anchor.copy(), arot.copy(), 0)
                    anchor = None
                    Tg = A.copy()
                    if rel is not None:
                        ra, rr, k = rel
                        k += 1
                        t = P4.ease(k / 6.0, "io")
                        Tg = Vector((ra.x, A.y, ra.z)).lerp(A, t)
                        rel = (ra, rr, k) if k < 6 else None
                Tg.y = max(Tg.y, -2.78)
                if (Tg - A).length < 1e-3:
                    if planted:
                        Ps[f][ankle] = arot
                    continue
                H, K = X[hip], X[knee]
                d = Tg - H
                if planted and d.length > a + b - 0.02:
                    v = d.normalized() * (d.length - (a + b - 0.02))
                    if f not in shift or v.length > shift[f].length:
                        shift[f] = v
                dl = min(d.length, a + b - 1e-3)
                u = d.normalized()
                ca = max(-1, min(1, (a * a + dl * dl - b * b) / (2 * a * dl)))
                sa = math.sqrt(1 - ca * ca)
                pole = Rr @ Vector((0, 0, -1))  # knees track forward over the toes
                pole = pole - u * pole.dot(u)
                nK = H + (u * ca + pole.normalized() * sa) * a
                nT = H + u * dl
                fw = arot if planted else Ps[f][ankle].copy()
                r1 = P2.min_rot(K - H, nK - H)
                Ps[f][hip] = r1 @ Ps[f][hip]
                Ps[f][knee] = P2.min_rot(r1 @ (A - K), nT - nK) @ r1 @ Ps[f][knee]
                Ps[f][ankle] = fw
        return shift

    def qa(self):
        main = [dict(r) for r in self.rows[:self.n + 1]]
        allow = set((self.tech or {}).get("allow", ())) if self.tech else set()
        if self.sword:
            allow |= {"elbow_up", "hands_up", "hand_in_head"}
        allow |= {"pop"}  # strikes are allowed to be fast inside their windows
        fl = posecheck.check(main, allow=allow, windows=self.windows())
        if self.loop:
            lp = [dict(r) for r in self.rows[self.loop[0]:self.loop[1] + 1]]
            fl2 = posecheck.check(lp, allow=allow | {"pop", "foot_slide"}, windows=[(0, 18)])
            for k, v in fl2.items():
                fl.setdefault("loop_" + k, []).extend(v)
        return fl


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opt = lambda k: argv[argv.index(k) + 1] if k in argv else None
    batch = opt("--batch"); only = set(opt("--powers").split(",")) if opt("--powers") else None
    rnd = "--render" in argv
    os.makedirs(os.path.join(D5, "renders"), exist_ok=True)
    skel = S.hkx.load(S.SKEL)["skeletons"][0]
    pool = {c["code"]: c for c in json.load(open(os.path.join(OUT, "pool.json")))}
    pmap = json.load(open(os.path.join(OUT, "power_mapping.json")))
    import phase4_sources as PS  # dynamics source picker (system-python compatible)
    jobs = []  # (target, module, tech_dict or None, sword?, slotkey, code, path)
    def src_for(limb, used, multi=False, sets=None):
        c = None
        for cand in sorted(pool.values(), key=lambda c: -c["score"]):
            if cand["weapon"] or cand["code"] in used or cand["drop"] > 40 or cand["lean"] > 75 or cand["air"] > 35:
                continue
            if sets and cand["set"] not in sets:
                continue
            if limb in ("RH", "LH") and cand["set"] in ("KickSet", "Agile"):
                continue
            if (len(cand["hits"]) >= 2) != multi or cand["limbs"][0] != limb:
                continue
            c = cand; break
        if c is None:
            return src_for(limb, used, not multi, sets) if sets is None else src_for(limb, used, multi, None)
        used.add(c["code"]); return c
    def add_power(pid, g, slots, fill=True, weapon_src=False):
        used = set()
        kinds = KIT.get(pid, []) if fill else list(slots.keys())
        slots = dict(slots)
        DASH = {"kick": st("push", "R"), "beast": st("claw", "R", 1.3), "palm": st("palm", "R", 1.3), "cast": st("palm", "R", 1.3),
                "sword": st("thrust", "R", 1.4), "dagger": st("thrust", "R", 1.4)}
        for kd in kinds:
            if kd not in slots:
                slots[kd] = {"Dash": DASH.get(g, st("straight", "R", 1.3)), "Bolt": st("palm", "R", 1.2) if g in ("palm", "cast") else st("straight", "R", 1.3),
                             "Blast": st("double_palm") if g in ("palm", "cast") else st("haymaker", "R", 1.3),
                             "Burst": st("rush", "R", st("straight", "R"), st("straight", "L"))}[kd]
        slots = {k: v for k, v in slots.items() if k.startswith("M1") or k == "Ult" or k in kinds}
        for slot, spec in slots.items():
            t = tech(g, spec)
            limb = (("RF" if t.get("kick") == "R" else "LF") if t.get("kick") else ("RH" if spec[1] == "R" else "LH"))
            if weapon_src:  # sword dynamics from the power's earlier weapon source for that slot (falls back to M1_1)
                e = pmap.get("Sky_%s_%s" % (pid, slot)) or pmap["Sky_%s_M1_1" % pid]
                c = pool[e["code"]]
            else:
                c = src_for(limb, used, multi=bool(t.get("loop")))
            sk = "M1_4" if slot == "M1_4" else ("M1" if slot.startswith("M1") else slot)
            jobs.append(("Sky_%s_%s" % (pid, slot), "Clips_SkyP_" + pid, t, False, sk, c["code"], c["path"]))
    want = lambda pid, grp: (only and pid in only) or (batch == grp)
    for pid, spec in POWERS.items():
        if spec and want(pid, "unarmed"):
            g, slots = spec
            add_power(pid, g, slots)
    p4src = json.load(open(os.path.join(OUT, "phase4", "sources.json")))
    P4K = {"karate": "karate", "boxer": "box", "kicker": "kick"}
    for t, e in p4src.items():
        pid = t.split("_")[1]
        if want(pid, "unarmed"):
            slot = "_".join(t.split("_")[2:])
            sk = "M1_4" if slot == "M1_4" else ("M1" if slot.startswith("M1") else slot)
            jobs.append((t, "Clips_SkyP_" + pid, dict(T[e["tech"]], allow=(("elbow_up", "hands_up") if e["tech"] in ("lead_hook", "uppercut", "overhand", "axe_kick") else ()) + (("crossed_knees",) if e["tech"] in ("mawashi_geri", "yoko_geri", "roundhouse_l", "side_kick", "double_round") else ())), False, sk, e["code"], e["path"]))
    for pid in ("karate", "boxer", "kicker"):  # Dash slot (kit F) missing from phase4
        if want(pid, "unarmed"):
            add_power(pid, P4K[pid], {"Dash": {"kick": st("push", "R")}.get(P4K[pid], st("straight", "R", 1.3))}, fill=False)
    for k, pid in enumerate(CASTERS):
        if want(pid, "casters"):
            kinds = KIT.get(pid, ["Bolt", "Blast", "Burst"])
            s = dict(CAST_SETS[k % len(CAST_SETS)])
            for kd in kinds:
                s[kd] = {"Bolt": st("palm", "R", 1.2), "Blast": st("double_palm"), "Burst": st("rush", "R", st("palm", "R"), st("palm", "L")),
                         "Dash": st("palm", "R", 1.3)}[kd]
            s["Ult"] = st("rush", "R", st("double_palm"), st("sweep", "R")) if k % 2 else st("rush", "R", st("palm", "R"), st("palm", "L"))
            add_power(pid, "cast", s)
    for pid, (g, slots) in BLADE_POWERS.items():
        if want(pid, "blades"):
            add_power(pid, g, slots, weapon_src=True)
    for pid in []:
        if want(pid, "blades"):
            for t, e in pmap.items():
                if t.startswith("Sky_%s_" % pid):
                    slot = "_".join(t.split("_")[2:])
                    sk = "M1_4" if slot == "M1_4" else ("M1" if slot.startswith("M1") else slot)
                    jobs.append((t, "Clips_SkyP_" + pid, None, "dagger" if "eclipse" in pid else "sword", sk, e["code"], e["path"]))
    if batch == "stand" or (only and "Stand" in only):
        used = set()
        for t, spec in STAND.items():
            tt = tech("box", spec)
            c = src_for("RH" if spec[1] == "R" else "LH", used, multi=bool(tt.get("loop")))
            jobs.append((t, "Clips_SkyStand", tt, False, STAND_SLOT[t], c["code"], c["path"]))
    by, report, renders, rowsout = {}, {}, {}, {}
    if rnd:
        ob = S.setup_scene()
        bpy.context.scene.render.resolution_x = 300; bpy.context.scene.render.resolution_y = 260
        REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
        coll = bpy.data.collections.new("stick"); bpy.context.scene.collection.children.link(coll)
        mats = {}
        for k, col in (("r", (0.9, 0.45, 0.2)), ("l", (0.3, 0.75, 0.35)), ("c", (0.85, 0.8, 0.75)), ("s", (0.7, 0.9, 1.0))):
            mm = bpy.data.materials.new("st_" + k); mm.diffuse_color = (*col, 1); mats[k] = mm
    for t, mod, tt, sword, sk, code, path in jobs:
        P2.SRCPATH[code] = path
        c = Clip5(t, code, sk, {}, skel)
        if sword:
            c.setup_tech(None, sword=True)
            P4.SWORD_GUARD.clear(); P4.SWORD_GUARD.update(G["dagger" if sword == "dagger" else "sword"])
        else:
            c.setup_tech(tt)
        c.build()
        c.post()
        fl = c.qa()
        report[t] = {k: len(v) for k, v in fl.items()}
        by.setdefault(mod, []).append(P2.lua_clip(t, c.markers, c.rows))
        rowsout[t] = c.rows
        print("QA", t, "<-", code, "FLAGS:", report[t] or 0)
        if rnd:
            renders[t] = P2.render_clip(c, os.path.join(D5, "renders"), ob, REST, coll, mats)
    for mod, items in by.items():
        src = ("-- AUTO-GENERATED by soulbound/skyrim/tools/phase5.py: personalised, QA-gated power clips (Skyrim dynamics +\n"
               "-- per-discipline technique layer). Same format as anim/build.py plus sw, src, limb.\nreturn {\n" + ",\n".join(items) + "\n}\n")
        open(os.path.join(D5, mod + ".lua"), "w", newline="\n").write(src)
    for fn, data in (("qa_report.json", report), ("rows.json", rowsout), ("renders.json", renders)):
        p = os.path.join(D5, fn)
        old = json.load(open(p)) if os.path.exists(p) else {}
        old.update(data)
        json.dump(old, open(p, "w"))
    bad = {k: v for k, v in report.items() if v}
    print("SUMMARY clips", len(report), "with flags", len(bad))


if __name__ == "__main__":
    main()
