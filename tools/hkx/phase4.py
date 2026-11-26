# Phase 4: personalised power clips = Skyrim source (body dynamics, timing, weight) + per-power technique layer.
# The technique layer (Roblox joint Eulers, CFrame.Angles XYZ degrees; conventions as soulbound/anim/clips.py) defines
# the discipline: guard/stance, the strike path (chamber -> snap -> kime hold -> retract), hikite, kick chamber/extension,
# torso rotation driving the strike. Source motion is blended underneath (legs/footwork, pelvis bob, torso), feet are
# planted with IK (kicking leg excluded), stylisation is toned down (no arm amp, no twist boost).
# Run: blender --background --python phase4.py -- --powers karate,boxer,kicker,demonhunter --render --out DIR
import bpy, sys, os, math, json
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import phase2 as P2
S = P2.S
rig = P2.rig
OUT = "C:/Users/mytwo/soulbound/skyrim/out"

P2.ARM_AMP = 1.0
P2.AMP = {}
P2.TWIST = {}


def P(**kw):
    return {k: tuple(v) for k, v in kw.items()}


def M(*ps):
    o = {}
    for p in ps:
        o.update(p)
    return o


SW = {}
for a, b in (("Right", "Left"),):
    for j in ("Shoulder", "Elbow", "Wrist", "Hip", "Knee", "Ankle"):
        SW[a + j] = b + j; SW[b + j] = a + j


def mirror(p):
    o = {}
    for k, v in p.items():
        if k == "p":
            o[k] = (-v[0], v[1], v[2])
        else:
            o[SW.get(k, k)] = (v[0], -v[1], -v[2])
    return o


# ------------------------------------------------------------------ stances / guards
KARATE_LEGS = P(LeftHip=(34, 0, -10), LeftKnee=(-34, 0, 0), LeftAnkle=(4, 0, 0),
                RightHip=(-16, 0, 10), RightKnee=(-6, 0, 0), RightAnkle=(10, 0, 0))
KARATE_GUARD = M(KARATE_LEGS, P(Root=(0, -22, 0), Waist=(-4, -8, 0), Neck=(0, 26, 0), p=(0, -0.28, 0),
                               LeftShoulder=(70, -35, 25), LeftElbow=(40, 0, 0),
                               RightShoulder=(-60, 5, -20), RightElbow=(118, 0, 0)))
HIKITE_R = P(RightShoulder=(-60, 5, -20), RightElbow=(118, 0, 0), RightWrist=(0, 0, 0))
HIKITE_L = P(LeftShoulder=(-60, -5, 20), LeftElbow=(118, 0, 0), LeftWrist=(0, 0, 0))
COVER = P(LeftShoulder=(20, -50, 0), LeftElbow=(115, 0, 0), RightShoulder=(5, 50, 0), RightElbow=(125, 0, 0))

BOX_LEGS = P(LeftHip=(22, 0, -10), LeftKnee=(-26, 0, 0), RightHip=(-8, 0, 10), RightKnee=(-22, 0, 0), RightAnkle=(14, 0, 0))
BOX_GUARD = M(BOX_LEGS, P(Root=(0, -20, 0), Waist=(-8, -6, 0), Neck=(6, 18, 0), p=(0, -0.24, 0),
                          LeftShoulder=(40, -50, 0), LeftElbow=(110, 0, 0), RightShoulder=(30, 55, 0), RightElbow=(125, 0, 0)))

KICK_LEGS = P(LeftHip=(18, 0, -10), LeftKnee=(-20, 0, 0), RightHip=(-10, 0, 10), RightKnee=(-10, 0, 0), RightAnkle=(8, 0, 0))
KICK_GUARD = M(KICK_LEGS, P(Root=(0, -24, 0), Waist=(-2, -6, 0), Neck=(0, 22, 0), p=(0, -0.16, 0),
                            LeftShoulder=(20, -50, 0), LeftElbow=(115, 0, 0), RightShoulder=(5, 50, 0), RightElbow=(125, 0, 0)))

SWORD_GUARD = P(RightShoulder=(56, -8, 10), RightElbow=(64, 0, 0), RightWrist=(-10, 0, 0),
                LeftShoulder=(42, 12, -14), LeftElbow=(88, 0, 0), Root=(0, -18, 0), Waist=(-4, -6, 0), Neck=(0, 18, 0),
                p=(0, -0.2, 0))

# ------------------------------------------------------------------ techniques
# each: dict(guard, chamber, strike, retract?, loop=[(t, pose)...] for 18-frame cycles, kick="R"/"L"/None)
T = {}
# karate --------------------------------------------------------------------------
T["oi_zuki"] = dict(guard=KARATE_GUARD,
    chamber=M(KARATE_GUARD, HIKITE_R, P(LeftShoulder=(20, -50, 0), LeftElbow=(115, 0, 0), Root=(0, -16, 0), p=(0, -0.3, 0.04))),
    strike=M(KARATE_GUARD, HIKITE_R, P(LeftShoulder=(88, 0, 6), LeftElbow=(2, 0, 0), Root=(0, -30, 0), Waist=(-6, -12, 0),
                                       Neck=(0, 32, 0), p=(0, -0.34, -0.28), LeftKnee=(-46, 0, 0), RightKnee=(-2, 0, 0))))
T["gyaku_zuki"] = dict(guard=KARATE_GUARD,
    chamber=M(KARATE_GUARD, HIKITE_R, P(LeftShoulder=(80, 0, 2), LeftElbow=(18, 0, 0), Root=(0, -30, 0), Waist=(-4, -14, 0),
                                        p=(0, -0.3, 0.02))),
    strike=M(KARATE_GUARD, HIKITE_L, P(RightShoulder=(88, 0, -6), RightElbow=(2, 0, 0), Root=(0, 6, 0), Waist=(-8, 14, 0),
                                       Neck=(0, -4, 0), p=(0, -0.34, -0.16), LeftKnee=(-44, 0, 0), RightKnee=(0, 0, 0),
                                       RightAnkle=(16, 0, 0))))
T["mae_geri"] = dict(guard=KARATE_GUARD, kick="R",
    chamber=M(KARATE_GUARD, COVER, P(RightHip=(98, 0, 4), RightKnee=(-122, 0, 0), RightAnkle=(24, 0, 0), LeftKnee=(-22, 0, 0),
                                     Root=(4, -10, 0), p=(0, -0.12, 0))),
    strike=M(KARATE_GUARD, COVER, P(RightHip=(90, 0, 4), RightKnee=(-6, 0, 0), RightAnkle=(-26, 0, 0), LeftKnee=(-18, 0, 0),
                                    Root=(10, -6, 0), Waist=(-6, 0, 0), Neck=(0, 6, 0), p=(0, -0.08, -0.06))),
    retract=M(KARATE_GUARD, COVER, P(RightHip=(96, 0, 4), RightKnee=(-118, 0, 0), LeftKnee=(-22, 0, 0), Root=(4, -10, 0),
                                     p=(0, -0.12, 0))))
T["mawashi_geri"] = dict(guard=KARATE_GUARD, kick="R",
    chamber=M(KARATE_GUARD, COVER, P(RightHip=(58, 0, 66), RightKnee=(-122, 0, 0), Root=(0, 36, 0), Waist=(0, 10, 0),
                                     Neck=(0, -24, 0), LeftKnee=(-20, 0, 0), p=(0, -0.12, 0))),
    strike=M(KARATE_GUARD, P(RightHip=(72, 0, 84), RightKnee=(-8, 0, 0), RightAnkle=(-22, 0, 0), Root=(4, 64, 0), Waist=(-4, 8, 0),
                             Neck=(0, -46, 0), LeftKnee=(-16, 0, 0), LeftShoulder=(20, -50, 0), LeftElbow=(115, 0, 0),
                             RightShoulder=(16, 0, 36), RightElbow=(70, 0, 0), p=(0, -0.1, -0.04))),
    retract=M(KARATE_GUARD, COVER, P(RightHip=(56, 0, 64), RightKnee=(-118, 0, 0), Root=(0, 30, 0), Neck=(0, -18, 0),
                                     LeftKnee=(-20, 0, 0), p=(0, -0.12, 0))))
T["teisho"] = dict(guard=KARATE_GUARD,
    chamber=M(KARATE_GUARD, HIKITE_R, P(RightWrist=(-60, 0, 0), LeftShoulder=(76, 0, 0), LeftElbow=(24, 0, 0), Root=(0, -28, 0),
                                        p=(0, -0.32, 0.04))),
    strike=M(KARATE_GUARD, HIKITE_L, P(RightShoulder=(86, 0, -4), RightElbow=(4, 0, 0), RightWrist=(-72, 0, 0), Root=(0, 8, 0),
                                       Waist=(-8, 14, 0), Neck=(0, -6, 0), p=(0, -0.36, -0.2), LeftKnee=(-46, 0, 0), RightKnee=(0, 0, 0))))
T["yoko_geri"] = dict(guard=KARATE_GUARD, kick="R",
    chamber=M(KARATE_GUARD, COVER, P(RightHip=(76, 0, 44), RightKnee=(-124, 0, 0), Root=(0, 54, 0), Waist=(0, 14, 0),
                                     Neck=(0, -50, 0), LeftKnee=(-24, 0, 0), p=(0, -0.14, 0))),
    strike=M(KARATE_GUARD, COVER, P(RightHip=(14, 0, 84), RightKnee=(-4, 0, 0), RightAnkle=(10, 0, 0), Root=(0, 82, 0), Waist=(-2, 8, 0),
                                    Neck=(0, -70, 0), LeftKnee=(-18, 0, 0), p=(0.1, -0.1, 0))),
    retract=M(KARATE_GUARD, COVER, P(RightHip=(74, 0, 42), RightKnee=(-120, 0, 0), Root=(0, 50, 0), Neck=(0, -44, 0),
                                     LeftKnee=(-22, 0, 0), p=(0, -0.14, 0))))
_R = T["gyaku_zuki"]["strike"]
_L = M(KARATE_GUARD, HIKITE_R, P(LeftShoulder=(88, 0, 6), LeftElbow=(2, 0, 0), Root=(0, -26, 0), Waist=(-6, -12, 0), Neck=(0, 28, 0),
                                 p=(0, -0.34, -0.2), LeftKnee=(-44, 0, 0)))
T["zuki_rush"] = dict(guard=KARATE_GUARD, chamber=T["gyaku_zuki"]["chamber"], strike=_R,
                      loop=[(0, _R), (4, M(_R, HIKITE_R, P(LeftShoulder=(60, 0, -6), LeftElbow=(60, 0, 0)))), (9, _L),
                            (13, M(_L, HIKITE_L, P(RightShoulder=(60, 0, 6), RightElbow=(60, 0, 0)))), (18, _R)])
# boxer ---------------------------------------------------------------------------
T["jab"] = dict(guard=BOX_GUARD,
    chamber=M(BOX_GUARD, P(LeftShoulder=(35, -50, 0), LeftElbow=(118, 0, 0), p=(0, -0.28, 0.02))),
    strike=M(BOX_GUARD, P(LeftShoulder=(90, 0, 4), LeftElbow=(2, 0, 0), Root=(0, -26, 0), Waist=(-8, -12, 0), Neck=(6, 24, 0),
                          p=(0, -0.26, -0.14))))
T["cross"] = dict(guard=BOX_GUARD,
    chamber=M(BOX_GUARD, P(Root=(0, -28, 0), Waist=(-8, -12, 0), RightShoulder=(25, 55, 0), RightElbow=(130, 0, 0), p=(0, -0.28, 0.04))),
    strike=M(BOX_GUARD, P(RightShoulder=(90, 0, -8), RightElbow=(2, 0, 0), Root=(0, 14, 0), Waist=(-12, 20, 0), Neck=(6, -10, 0),
                          RightHip=(-12, 0, 4), RightKnee=(-4, 0, 0), RightAnkle=(26, 0, 0), LeftKnee=(-34, 0, 0), p=(0, -0.3, -0.2))))
T["lead_hook"] = dict(guard=BOX_GUARD,
    chamber=M(BOX_GUARD, P(Root=(0, 2, 0), Waist=(-8, 14, 0), LeftShoulder=(62, 10, -30), LeftElbow=(96, 0, 0), p=(0, -0.3, 0))),
    strike=M(BOX_GUARD, P(LeftShoulder=(44, 0, -84), LeftElbow=(94, 0, 0), LeftWrist=(0, 0, 0), Root=(0, -34, 0), Waist=(-8, -30, 0),
                          Neck=(6, 40, 0), LeftKnee=(-30, 0, 0), p=(0, -0.3, -0.06))))
T["uppercut"] = dict(guard=BOX_GUARD,
    chamber=M(BOX_GUARD, P(p=(0, -0.42, 0), Root=(0, -14, 0), Waist=(-12, -10, 0), RightShoulder=(26, -10, 20), RightElbow=(104, 0, 0),
                           RightKnee=(-36, 0, 0), LeftKnee=(-40, 0, 0))),
    strike=M(BOX_GUARD, P(RightShoulder=(118, 0, -10), RightElbow=(72, 0, 0), Root=(0, 14, 0), Waist=(6, 18, 0), Neck=(10, -8, 0),
                          p=(0, -0.16, -0.08), RightKnee=(-10, 0, 0), LeftKnee=(-18, 0, 0))))
T["overhand"] = dict(guard=BOX_GUARD,
    chamber=M(BOX_GUARD, P(Root=(0, -36, 0), Waist=(-4, -22, 0), RightShoulder=(118, -22, 40), RightElbow=(112, 0, 0), Neck=(4, 34, 0),
                           p=(0, -0.3, 0.12))),
    strike=M(BOX_GUARD, P(RightShoulder=(98, 0, -8), RightElbow=(8, 0, 0), Root=(0, 26, 0), Waist=(-18, 26, 0), Neck=(8, -18, 0),
                          p=(0, -0.38, -0.36), LeftKnee=(-48, 0, 0), RightHip=(-16, 0, 4), RightKnee=(-4, 0, 0), RightAnkle=(26, 0, 0))))
_BJ = T["jab"]["strike"]; _BC = T["cross"]["strike"]
T["combo_rush"] = dict(guard=BOX_GUARD, chamber=T["cross"]["chamber"], strike=_BC,
                       loop=[(0, _BC), (5, BOX_GUARD), (9, _BJ), (14, BOX_GUARD), (18, _BC)])
# kicker --------------------------------------------------------------------------
T["front_snap"] = dict(guard=KICK_GUARD, kick="R",
    chamber=M(KICK_GUARD, P(RightHip=(104, 0, 4), RightKnee=(-124, 0, 0), RightAnkle=(20, 0, 0), LeftKnee=(-18, 0, 0), Root=(4, -12, 0))),
    strike=M(KICK_GUARD, P(RightHip=(100, 0, 4), RightKnee=(-4, 0, 0), RightAnkle=(-28, 0, 0), LeftKnee=(-14, 0, 0), Root=(12, -8, 0),
                           Waist=(-6, 0, 0), p=(0, -0.06, -0.08))),
    retract=M(KICK_GUARD, P(RightHip=(100, 0, 4), RightKnee=(-118, 0, 0), LeftKnee=(-18, 0, 0), Root=(4, -12, 0))))
T["roundhouse_l"] = dict(guard=KICK_GUARD, kick="L",
    chamber=M(KICK_GUARD, mirror(P(RightHip=(56, 0, 64), RightKnee=(-120, 0, 0))), P(Root=(0, -50, 0), Neck=(0, 36, 0), RightKnee=(-20, 0, 0))),
    strike=M(KICK_GUARD, mirror(P(RightHip=(76, 0, 86), RightKnee=(-8, 0, 0), RightAnkle=(-22, 0, 0))),
             P(Root=(4, -66, 0), Waist=(-4, -10, 0), Neck=(0, 50, 0), RightKnee=(-16, 0, 0), LeftShoulder=(16, 0, -36), LeftElbow=(70, 0, 0),
               p=(0, -0.08, -0.04))),
    retract=M(KICK_GUARD, mirror(P(RightHip=(54, 0, 62), RightKnee=(-116, 0, 0))), P(Root=(0, -44, 0), Neck=(0, 30, 0), RightKnee=(-20, 0, 0))))
T["side_kick"] = dict(T["yoko_geri"], guard=KICK_GUARD)
T["side_kick"] = dict(guard=KICK_GUARD, kick="R",
                      chamber=M(KICK_GUARD, {k: v for k, v in T["yoko_geri"]["chamber"].items() if k not in KARATE_GUARD or k in ("RightHip", "RightKnee", "Root", "Neck", "Waist")}),
                      strike=M(KICK_GUARD, {k: v for k, v in T["yoko_geri"]["strike"].items() if k in ("RightHip", "RightKnee", "RightAnkle", "Root", "Neck", "Waist", "p")}),
                      retract=M(KICK_GUARD, {k: v for k, v in T["yoko_geri"]["retract"].items() if k in ("RightHip", "RightKnee", "Root", "Neck")}))
T["axe_kick"] = dict(guard=KICK_GUARD, kick="R",
    chamber=M(KICK_GUARD, P(RightHip=(150, 0, 12), RightKnee=(-12, 0, 0), RightAnkle=(10, 0, 0), Root=(-6, -14, 0), Waist=(6, 0, 0),
                            LeftKnee=(-10, 0, 0), p=(0, -0.04, 0.06))),
    strike=M(KICK_GUARD, P(RightHip=(52, 0, 6), RightKnee=(-4, 0, 0), RightAnkle=(-10, 0, 0), Root=(12, -10, 0), Waist=(-12, 0, 0),
                           LeftKnee=(-26, 0, 0), p=(0, -0.2, -0.12))),
    retract=M(KICK_GUARD, P(RightHip=(40, 0, 6), RightKnee=(-60, 0, 0), Root=(6, -14, 0), LeftKnee=(-22, 0, 0))))
T["push_kick"] = dict(guard=KICK_GUARD, kick="R",
    chamber=M(KICK_GUARD, P(RightHip=(110, 0, 4), RightKnee=(-120, 0, 0), RightAnkle=(30, 0, 0), Root=(0, -8, 0), LeftKnee=(-24, 0, 0),
                            p=(0, -0.14, 0.08))),
    strike=M(KICK_GUARD, P(RightHip=(96, 0, 4), RightKnee=(-2, 0, 0), RightAnkle=(16, 0, 0), Root=(18, -4, 0), Waist=(-4, 0, 0),
                           LeftKnee=(-10, 0, 0), p=(0, -0.06, -0.3))),
    retract=M(KICK_GUARD, P(RightHip=(100, 0, 4), RightKnee=(-110, 0, 0), Root=(6, -8, 0), LeftKnee=(-20, 0, 0))))
_KF = T["front_snap"]["strike"]; _KR = T["roundhouse_l"]["strike"]
T["double_round"] = dict(guard=KICK_GUARD, kick="R", chamber=T["mawashi_geri"]["chamber"],
                         strike=M(KICK_GUARD, {k: v for k, v in T["mawashi_geri"]["strike"].items() if k in ("RightHip", "RightKnee", "RightAnkle", "Root", "Neck", "Waist", "p")}),
                         loop=None)
T["double_round"]["loop"] = [(0, T["double_round"]["strike"]), (6, M(KICK_GUARD, P(RightHip=(58, 0, 66), RightKnee=(-120, 0, 0), Root=(0, 30, 0)))),
                             (12, M(KICK_GUARD, P(RightHip=(84, 0, 80), RightKnee=(-10, 0, 0), Root=(4, 70, 0), Neck=(0, -50, 0)))),
                             (18, T["double_round"]["strike"])]
T["kick_rush"] = dict(guard=KICK_GUARD, kick="R", chamber=T["front_snap"]["chamber"], strike=_KF,
                      loop=[(0, _KF), (5, T["front_snap"]["retract"]), (9, M(KICK_GUARD, P(RightHip=(104, 0, 4), RightKnee=(-6, 0, 0), RightAnkle=(-28, 0, 0), Root=(12, -8, 0)))),
                            (14, T["front_snap"]["retract"]), (18, _KF)])

# ------------------------------------------------------------------ easing / sampling
def ease(t, kind):
    t = max(0.0, min(1.0, t))
    if kind == "snap":
        return 1 - (1 - t) ** 3.2
    if kind == "in":
        return t * t
    if kind == "hold":
        return 0.0
    return t * t * (3 - 2 * t)


def eul_q(e):
    x, y, z = (math.radians(a) for a in e)
    return (Matrix.Rotation(x, 3, "X") @ Matrix.Rotation(y, 3, "Y") @ Matrix.Rotation(z, 3, "Z")).to_quaternion()


def pose_at(keys, f, guard):
    """keys: [(frame, pose, ease_into)] -> {joint: Quaternion}, p Vector"""
    if f <= keys[0][0]:
        a = b = keys[0]; t = 0.0
    elif f >= keys[-1][0]:
        a = b = keys[-1]; t = 0.0
    else:
        for k in range(len(keys) - 1):
            if keys[k][0] <= f <= keys[k + 1][0]:
                a, b = keys[k], keys[k + 1]
                t = ease((f - a[0]) / max(1e-6, b[0] - a[0]), b[2])
                break
    out = {}
    for j in rig.ORDER:
        qa = eul_q(a[1].get(j, guard.get(j, (0, 0, 0))))
        qb = eul_q(b[1].get(j, guard.get(j, (0, 0, 0))))
        if qa.dot(qb) < 0:
            qb = -qb
        out[j] = qa.slerp(qb, t)
    pa = Vector(a[1].get("p", guard.get("p", (0, 0, 0)))); pb = Vector(b[1].get("p", guard.get("p", (0, 0, 0))))
    return out, pa.lerp(pb, t)


ARMS = P2.ARMS
LEGS = P2.LEGS


class TechClip(P2.Clip):
    def setup_tech(self, tech, sword=False):
        self.tech = tech
        self.sword = sword
        self._lt = 0
        if tech and tech.get("kick"):
            self.no_ik = {tech["kick"]}

    def keys(self):
        t = self.tech
        n, w, i, r = self.n, self.w, self.i, self.r
        H = P2.HOLD
        ks = [(0, t["guard"], "io"), (w, t["chamber"], "io"), (i, t["strike"], "snap"), (i + H, t["strike"], "hold")]
        if t.get("retract"):
            ks.append((i + H + max(3, (r - i - H) // 3), t["retract"], "io"))
        ks += [(r, t["guard"], "io"), (n, t["guard"], "io")]
        return ks

    def stylise(self, L, p, f):
        if self.sword:  # weapon power: keep source technique, blend in the sword guard at the ends, limit spins
            kw = self.kw[f] if 0 <= f < len(self.kw) else 1.0
            out = dict(L)
            for j in ("Root", "Waist"):
                m = out[j].to_matrix()
                b = math.asin(max(-1, min(1, m[0][2]))); a = math.atan2(-m[1][2], m[2][2]); c = math.atan2(-m[0][1], m[0][0])
                b = max(-math.radians(80), min(math.radians(80), b))
                out[j] = (Matrix.Rotation(a, 3, "X") @ Matrix.Rotation(b, 3, "Y") @ Matrix.Rotation(c, 3, "Z")).to_quaternion()
            if f >= 0:
                g = min(1.0, max(0.0, 1 - min(f / max(1, self.w), (self.n - f) / max(1, self.n - self.r))))
                if g > 0:
                    gq, gp = pose_at([(0, SWORD_GUARD, "io")], 0, SWORD_GUARD)
                    for j in ARMS | {"Root", "Waist", "Neck"}:
                        out[j] = out[j].slerp(Quaternion().slerp(gq[j], kw), g * 0.6)
            return out, p
        if f >= 0:
            tq, tp = pose_at(self.keys(), f, self.tech["guard"])
            kw = self.kw[f] if (f < len(self.kw) and f > self.r) else 1.0  # start directly in guard (CharAnim crossfades in)
        else:
            lp = self.tech.get("loop") or [(0, self.tech["strike"], "io"), (18, self.tech["strike"], "io")]
            lk = [(k[0], k[1], "snap" if k[1] is self.tech["strike"] else "io") for k in lp]
            tq, tp = pose_at(lk, self._lt, self.tech["guard"])
            self._lt += 1
            kw = 1.0
        kick = self.tech.get("kick")
        out = {}
        for j in rig.ORDER:
            src, tch = L[j], tq[j]
            if tch.dot(src) < 0:
                tch = -tch
            if j in ARMS:
                q = tch
            elif j in LEGS:
                side = "R" if j.startswith("Right") else "L"
                if side == kick:
                    q = tch
                else:
                    ang = math.degrees(src.rotation_difference(tch).angle)
                    q = tch.slerp(src, 0.25 * max(0.0, 1.0 - ang / 70.0))
            else:  # torso/neck: source adds life, but fades out when it disagrees strongly (avoids hemisphere flips)
                ang = math.degrees(src.rotation_difference(tch).angle)
                ws = (0.22 if j in ("Root", "Waist") else 0.3) * max(0.0, 1.0 - ang / 60.0)
                q = tch.slerp(src, ws)
            out[j] = Quaternion().slerp(q, kw) if kw < 1 else q
        pp = (tp * 0.75 + p * 0.25) * kw
        for ih in getattr(self, "out_hits", []):
            d = f - ih
            if 0 <= d <= 6:
                pp = pp + Vector((0, -0.05 * math.sin(math.pi * d / 6), 0))
        return out, pp


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    powers = None; outdir = os.path.join(OUT, "phase4"); rnd = False
    for k, a in enumerate(argv):
        if a == "--powers": powers = set(argv[k + 1].split(","))
        if a == "--out": outdir = argv[k + 1]
        if a == "--render": rnd = True
    os.makedirs(os.path.join(outdir, "renders"), exist_ok=True)
    skel = S.hkx.load(S.SKEL)["skeleton" + "s"][0]
    srcs = json.load(open(os.path.join(OUT, "phase4", "sources.json")))
    pmap = json.load(open(os.path.join(OUT, "power_mapping.json")))
    jobs = []
    for t, e in srcs.items():
        jobs.append((t, e["code"], e["path"], e["tech"]))
    for t, e in pmap.items():  # weapon powers in the list keep their source, with the sword treatment
        pid = t.split("_")[1]
        if powers and pid in powers and not any(j[0] == t for j in jobs) and pid in ("demonhunter",):
            jobs.append((t, e["code"], e["path"], "SWORD"))
    by, markers, renders = {}, {}, {}
    if rnd:
        ob = S.setup_scene()
        bpy.context.scene.render.resolution_x = 300; bpy.context.scene.render.resolution_y = 260
        REST = {b.name: b.matrix_local.to_3x3() for b in ob.data.bones}
        coll = bpy.data.collections.new("stick"); bpy.context.scene.collection.children.link(coll)
        mats = {}
        for k, col in (("r", (0.9, 0.45, 0.2)), ("l", (0.3, 0.75, 0.35)), ("c", (0.85, 0.8, 0.75)), ("s", (0.7, 0.9, 1.0))):
            mm = bpy.data.materials.new("st_" + k); mm.diffuse_color = (*col, 1); mats[k] = mm
    allrows = {}
    for t, code, path, tech in jobs:
        pid = t.split("_")[1]; slot = "_".join(t.split("_")[2:])
        if powers and pid not in powers:
            continue
        P2.SRCPATH[code] = path
        slotkey = "M1_4" if slot == "M1_4" else ("M1" if slot.startswith("M1") else slot)
        c = TechClip(t, code, slotkey, {}, skel)
        c.setup_tech(None if tech == "SWORD" else T[tech], sword=(tech == "SWORD"))
        c.build()
        by.setdefault(pid, []).append(P2.lua_clip(t, c.markers, c.rows))
        markers[t] = dict(c.markers, technique=tech)
        allrows[t] = c.rows
        import guardfit
        allow = ("elbow_up",) if tech in ("lead_hook", "uppercut", "overhand", "SWORD") else ()
        iss = guardfit.check_rows(c.rows[:c.n + 1], allow)
        kinds = {}
        for fr, msg in iss:
            kinds.setdefault(msg, []).append(fr)
        print("built", t, tech, "<-", code, "lean %.0f" % c.lean, "CHECK:", {k: "%d frames (%d-%d)" % (len(v), v[0], v[-1]) for k, v in kinds.items()} or "ok")
        if rnd:
            renders[t] = P2.render_clip(c, os.path.join(outdir, "renders"), ob, REST, coll, mats)
    for pid, items in by.items():
        src = ("-- AUTO-GENERATED by soulbound/skyrim/tools/phase4.py: personalised power clips (Skyrim source dynamics +\n"
               "-- per-power technique layer). Same format as anim/build.py plus sw, src, limb.\nreturn {\n" + ",\n".join(items) + "\n}\n")
        open(os.path.join(outdir, "Clips_SkyP_%s.lua" % pid), "w", newline="\n").write(src)
        print("wrote Clips_SkyP_%s" % pid, len(items))
    json.dump(markers, open(os.path.join(outdir, "markers.json"), "w"), indent=1)
    json.dump({k: [{j: v for j, v in r.items()} for r in rows] for k, rows in allrows.items()}, open(os.path.join(outdir, "rows.json"), "w"))
    if rnd:
        rp = os.path.join(outdir, "renders.json")
        json.dump(renders, open(rp, "w"))


if __name__ == "__main__":
    main()
