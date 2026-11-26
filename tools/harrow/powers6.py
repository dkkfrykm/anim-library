# Phase 6: per-power motion identities (pure Python, no bpy). Each power: own guard (stance/arms/silhouette),
# own signature techniques, own rhythm (chamber/strike eases, extra keys, follow-ups, loops).
# Tech dict: guard, chamber, strike, [ec, es, extra=[(anchor, offset, pose, ease)], allow, kick, wend, loop]
# anchors: 0, w, i, h (=i+HOLD), r, n.  Consumed by phase6.py (Blender) and precheck6.py (static QA).
import math

def P(**kw): return {k: tuple(v) for k, v in kw.items()}
def M(*ps):
    o = {}
    for p in ps:
        if p: o.update(p)
    return o
SIDE = {"R": "Right", "L": "Left"}
def other(s): return "L" if s == "R" else "R"

def A(side, sh, el=0, wr=(0, 0, 0)):
    s = SIDE[side]
    sh = sh if side == "R" else (sh[0], -sh[1], -sh[2])
    wr = wr if side == "R" else (wr[0], -wr[1], -wr[2])
    return {s + "Shoulder": tuple(sh), s + "Elbow": (el, 0, 0), s + "Wrist": tuple(wr)}
def A2(sh, el=0, wr=(0, 0, 0)): return M(A("R", sh, el, wr), A("L", sh, el, wr))

def legs(lh=(0, 0, 0), lk=0, la=0, rh=(0, 0, 0), rk=0, ra=0):
    return P(LeftHip=lh, LeftKnee=(lk, 0, 0), LeftAnkle=(la, 0, 0), RightHip=rh, RightKnee=(rk, 0, 0), RightAnkle=(ra, 0, 0))

def body(root=(0, 0, 0), waist=(0, 0, 0), neck=(0, 0, 0), p=(0, 0, 0)):
    return P(Root=root, Waist=waist, Neck=neck, p=p)

def Bd(g, yaw=0, lean=0, dp=(0, 0, 0), neck=None, roll=0, **lg):
    """body relative to guard g: yaw (+left), lean (-forward), pelvis delta; lg: LeftKnee=-40 style scalars or tuples"""
    ty = yaw if abs(yaw) <= 150 else 0.0  # spins: the torso/head turn with the hips (keeps keys 360-consistent)
    b = {"Root": (g["Root"][0] + lean, g["Root"][1] + yaw, g["Root"][2] + roll),
         "Waist": (g["Waist"][0] + lean * 0.5, g["Waist"][1] + ty * 0.5, g["Waist"][2]),
         "Neck": neck if neck is not None else (g["Neck"][0] - lean * 0.4, g["Neck"][1] - ty * 1.1, g["Neck"][2]),
         "p": tuple(g["p"][k] + dp[k] for k in range(3))}
    for k, v in lg.items():
        b[k] = (v, 0, 0) if isinstance(v, (int, float)) else tuple(v)
    return b

def T6(g, ch, st, ec="io", es="snap", extra=(), allow=(), kick=None, wend=None, loop=None, rt=None, **kw):
    t = dict(guard=g, chamber=M(g, *ch), strike=M(g, *st), ec=ec, es=es, allow=tuple(allow), kick=kick, wend=wend,
             extra=[(a, o, (g if ps == "g" else M(g, *ps)), e) for a, o, ps, e in extra])
    if rt:
        t["retract"] = M(g, *rt)
    if loop:
        t["loop"] = loop
    t.update(kw)
    return t

def loopseq(t, poses, ease="snap"):
    """poses: [(frame, pose)] 0..18, first == last; attaches to t"""
    t = dict(t); t["loop"] = poses; return t

def rush(a, b):
    t = dict(a)
    t["loop"] = [(0, a["strike"]), (5, a["guard"]), (9, b["strike"]), (14, b["guard"]), (18, a["strike"])]
    t["allow"] = tuple(set(a.get("allow", ())) | set(b.get("allow", ())))
    if a.get("kick") or b.get("kick"):
        t["kick"] = a.get("kick") or b.get("kick")
    return t

def rush4(a, b, c, d):
    t = dict(a)
    t["loop"] = [(0, a["strike"]), (3, a["chamber"]), (5, b["strike"]), (8, b["chamber"]), (9, c["strike"]), (12, c["chamber"]),
                 (14, d["strike"]), (16, d["chamber"]), (18, a["strike"])]
    t["allow"] = tuple(set().union(*[x.get("allow", ()) for x in (a, b, c, d)]))
    return t

# generic kick with the power's own arms (from phase5 KICKS deltas)
KICKS = {
    "front": (P(RightHip=(102, 0, 4), RightKnee=(-124, 0, 0), RightAnkle=(22, 0, 0)), P(RightHip=(96, 0, 4), RightKnee=(-4, 0, 0), RightAnkle=(-28, 0, 0)), 0, 8),
    "round": (P(RightHip=(58, 0, 66), RightKnee=(-122, 0, 0)), P(RightHip=(74, 0, 84), RightKnee=(-8, 0, 0), RightAnkle=(-22, 0, 0)), 62, 4),
    "side": (P(RightHip=(76, 0, 44), RightKnee=(-124, 0, 0)), P(RightHip=(14, 0, 84), RightKnee=(-4, 0, 0), RightAnkle=(10, 0, 0)), 80, 0),
    "push": (P(RightHip=(110, 0, 4), RightKnee=(-120, 0, 0), RightAnkle=(30, 0, 0)), P(RightHip=(96, 0, 4), RightKnee=(-2, 0, 0), RightAnkle=(16, 0, 0)), 0, 16),
    "knee": (P(RightHip=(70, 0, 4), RightKnee=(-100, 0, 0)), P(RightHip=(118, 0, 4), RightKnee=(-130, 0, 0), RightAnkle=(20, 0, 0)), 0, -10),
    "low": (P(RightHip=(30, 0, 40), RightKnee=(-90, 0, 0)), P(RightHip=(40, 0, 60), RightKnee=(-6, 0, 0), RightAnkle=(-10, 0, 0)), 50, 0),
}
def mir(p):
    o = {}
    for k, v in p.items():
        if k == "p": o[k] = (-v[0], v[1], v[2])
        elif k.startswith("Right"): o["Left" + k[5:]] = (v[0], -v[1], -v[2])
        elif k.startswith("Left"): o["Right" + k[4:]] = (v[0], -v[1], -v[2])
        else: o[k] = (v[0], -v[1], -v[2])
    return o
def kick(g, side, kind, arms=None, chl=None, stl=None, extra=(), es="snap", dp=(0, 0.04, -0.06), lift=0.0):
    ch_l, st_l, yaw, lean = KICKS[kind]
    sup = "LeftKnee" if side == "R" else "RightKnee"
    ch_l = M(ch_l, {mirk("LeftKnee", side): (-20, 0, 0)}); st_l = M(st_l, {mirk("LeftKnee", side): (-16, 0, 0)})
    if side == "L":
        ch_l, st_l, yaw = mir(ch_l), mir(st_l), -yaw
    arms = arms or {}
    ch = M(g, arms, chl, ch_l, Bd(g, yaw * 0.55, lean * 0.3, dp=(0, lift * 0.5, 0)))
    st = M(g, arms, stl, st_l, Bd(g, yaw, lean, dp=(dp[0], dp[1] + lift, dp[2])))
    rt = M(g, arms, ch_l, Bd(g, yaw * 0.5, lean * 0.3))
    al = (("crossed_knees",) if kind in ("round", "side", "low") else ()) + (("extreme_lean",) if kind == "side" else ())
    t = dict(guard=g, chamber=ch, strike=st, retract=rt, kick=side, allow=al, ec="io", es=es, extra=list(extra), wend=None)
    return t
def mirk(k, side): return k


# ======================================================================== registry (batches live in p6_b*.py)
POWERS, BATCHES = {}, {}
def power(batch):
    def deco(fn):
        POWERS[fn.__name__] = fn
        BATCHES.setdefault(batch, []).append(fn.__name__)
        return fn
    return deco
def meta(t, name, foot=None, torso=None, side="R", **kw):
    """attach component queries (footwork/torso tags) and a technique name"""
    t = dict(t); t.update(name=name, foot=foot, torso=torso, side=side); t.update(kw); return t
def p4(name, label, foot=None, torso=None, side="R", **kw):
    return dict(p4=name, name=label, foot=foot, torso=torso, side=side, **kw)
def load_all():
    import glob, importlib, os
    for f in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "p6_b*.py"))):
        importlib.import_module(os.path.splitext(os.path.basename(f))[0])


# ======================================================================== combat idle / stance loops
IDLE_N = 96  # 1.6 s loop
def idle_keys(g, bounce=0.015, period=96, sway=0.0, shift=0.0, breath=2.0, drift=0.0, roll=0.0, lift=0.0):
    """loop keys [(frame, pose)] around guard g: bounce (studs, per `period` frames), sway (Root yaw deg), shift
    (pelvis x studs), breath (Waist pitch deg), drift (shoulder pitch deg, arms alternate), roll (Waist roll deg), lift (hover)"""
    ks = []
    for k in range(9):
        f = k * IDLE_N // 8
        ph = 2 * math.pi * k / 8
        bp = 2 * math.pi * f / period
        q = dict(g)
        dy = -bounce * (1 - math.cos(bp)) / 2 + lift * math.sin(ph) * 0.5
        q["p"] = (g["p"][0] + shift * math.sin(ph), g["p"][1] + dy, g["p"][2])
        q["Root"] = (g["Root"][0], g["Root"][1] + sway * math.sin(ph), g["Root"][2])
        q["Waist"] = (g["Waist"][0] - breath * math.sin(ph), g["Waist"][1] - sway * 0.4 * math.sin(ph), g["Waist"][2] + roll * math.sin(ph))
        q["Neck"] = (g["Neck"][0] + breath * 0.5 * math.sin(ph), g["Neck"][1] - sway * 0.6 * math.sin(ph), g["Neck"][2])
        for s, sg in (("Right", 1), ("Left", -1)):
            sh = g.get(s + "Shoulder", (0, 0, 0))
            q[s + "Shoulder"] = (sh[0] + drift * sg * math.sin(ph), sh[1], sh[2])
        ks.append((f, q))
    return ks


# ======================================================================== V7: set-3 source upgrades (opt-in per power)
LOCO3 = r"run|walk|sprint|turn|strafe|jog|equip|sheath|draw"
def lib3(spec, sets, arms=0.0, strike=("cast",), weapon=False, torso=("cast",), planted=("cast", "planted"), moving=None,
         idle_sets=None, idle_weapon=None, skip=("Dash",), slots=None):
    """re-source a power's HKX components from set-3 libraries (src3) without touching its authored poses:
    primary strike segment + torso from `sets`, planted footwork from `sets` (caster weight shifts), moving footwork
    from `moving` sets when given; `arms` blends that much of the source arm motion under the authored arms;
    idle stance source from `idle_sets`. Slots in `skip` keep their pre-V7 queries."""
    out = dict(spec); out["slots"] = dict(spec["slots"])
    for k, t in spec["slots"].items():
        if k in skip or (slots and k not in slots) or t.get("sword_direct"):
            continue
        t = dict(t)
        t["prim_sets"] = list(sets); t["strike_tags"] = list(strike); t["prim_weapon"] = weapon
        t["avoid_name3"] = LOCO3  # casting/weapon sets file their walk/run/sprint/turn cycles under "cast"/"attack"
        t["strike_tags_fallback"] = t.get("strike_tags_fallback") or ["attack"]
        if torso:
            t["torso"] = t.get("torso") or list(torso[:1]); t["torso_sets"] = list(sets); t["torso_tags3"] = list(torso)
        f = t.get("foot")
        if f and list(f) == ["planted"] and planted:
            t["foot_sets"] = list(sets); t["foot_tags3"] = list(planted)
        elif f and moving:
            t["foot_sets"] = list(moving)
        if arms:
            t["ws"] = dict(t.get("ws") or {}, arms=arms)
        out["slots"][k] = t
    if idle_sets:
        out["idle_sets"] = list(idle_sets)
        out["idle_avoid"] = LOCO3 + "|sneak|turn"
        if idle_weapon is not None:
            out["idle_weapon"] = idle_weapon
    return out
