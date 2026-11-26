"""Authored clips with no HKX source in the library (no sit / death / knockdown / sleep / meditate clips exist in the raw set):
Common_* camp & social clips and per-class Pose (creator flourish), relaxed Idle, Stance, Knockdown, Downed, GetUp, Death.
Poses use the powers6 DSL; class guards come from p6_bth so every class falls/rises from its own stance.
Pure Python. Output: ../out/th_auth/Clips_TH_<Rig>.lua + qa.json.  Usage: python -E -P th_authored.py
"""
import sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from powers6 import *
import powers6 as PW
import posecheck as PC
import th_enc as E

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'th_auth')
J = PC.ORDER


def full(p):
    o = {j: tuple(p.get(j, (0, 0, 0))) for j in J}
    o['p'] = tuple(p.get('p', (0, 0, 0)))
    return o


def ease(t, k):
    if k == 'lin': return t
    if k == 'io': return t * t * (3 - 2 * t)
    if k == 'out': return 1 - (1 - t) ** 3
    if k == 'in': return t ** 3
    if k == 'snap': return 1 - (1 - t) ** 5
    if k == 'hold': return 0.0
    return t


def bake(keys, n):
    """keys: [(frame, pose, ease_into_this_key)], frames 0..n-1"""
    keys = [(f, full(p), e) for f, p, e in keys]
    rows = []
    for f in range(n):
        k = 0
        while k + 1 < len(keys) and keys[k + 1][0] <= f:
            k += 1
        if k + 1 >= len(keys):
            rows.append(dict(keys[-1][1])); continue
        (f0, a, _), (f1, b, e) = keys[k], keys[k + 1]
        t = ease((f - f0) / max(1, f1 - f0), e)
        row = {j: tuple(a[j][i] + (b[j][i] - a[j][i]) * t for i in range(3)) for j in J}
        row['p'] = tuple(a['p'][i] + (b['p'][i] - a['p'][i]) * t for i in range(3))
        rows.append(row)
    return rows


def breathe(rows, amp=1.2, period=None, arms=0.6):
    n = len(rows); period = period or n
    for f, r in enumerate(rows):
        s = math.sin(2 * math.pi * f / period)
        r['Waist'] = (r['Waist'][0] - amp * s, r['Waist'][1], r['Waist'][2])
        r['Neck'] = (r['Neck'][0] + amp * 0.5 * s, r['Neck'][1], r['Neck'][2])
        for sd in ('Right', 'Left'):
            sh = r[sd + 'Shoulder']; r[sd + 'Shoulder'] = (sh[0] + arms * s, sh[1], sh[2])
    return rows


CLIPS, MK, QA, ROWS, QAF = {}, {}, {}, {}, {}
RELAXED, GUARD = {}, {}


def add(rig_, name, rows, w=0, i=(), r=None, loop=False, allow=()):
    n = len(rows)
    if loop:
        rows = rows + [dict(rows[0])]  # encoder sees the seam
        rows = rows[:n]
    mk = dict(n=n, w=w, i=list(i), r=r if r is not None else n, sw=[])
    key = '%s_%s' % (rig_, name)
    CLIPS.setdefault(rig_, {})[key] = E.lua_clip(key, mk, rows)
    ROWS[key] = rows
    fl = PC.check(rows + ([rows[0]] if loop else []), allow=set(allow) | {'foot_slide'}, windows=[(0, n)])
    QA[key] = {k: len(v) for k, v in fl.items()}
    QAF[key] = {k: sorted(set(v))[:40] for k, v in fl.items()}


# ---------------------------------------------------------------- shared poses
SIT = M(legs(lh=(88, 0, -6), lk=-88, la=0, rh=(88, 0, 6), rk=-88, ra=0), body(root=(0, 0, 0), waist=(-6, 0, 0), neck=(4, 0, 0)),
        A('R', (18, 14, 0), 46, (-10, 0, 0)), A('L', (18, 14, 0), 46, (-10, 0, 0)))
SIT_FWD = M(SIT, body(root=(-10, 0, 0), waist=(-10, 0, 0), neck=(14, 0, 0)), A('R', (44, 22, 0), 74, (-10, 0, 0)), A('L', (44, 22, 0), 74, (-10, 0, 0)))


def common():
    # Common_Sit (tavern bench / chair): hands on thighs, weight settled, slow breath + occasional glance
    n = 240
    rows = bake([(0, SIT, 'io'), (90, M(SIT, body(neck=(4, 14, 0))), 'io'), (150, M(SIT, body(neck=(2, -10, 0))), 'io'), (239, SIT, 'io')], n)
    add('Common', 'Sit', breathe(rows, 1.0, 120), loop=True)
    # Common_CampRest: forearms on knees, leaning into the fire's warmth
    rest = M(SIT_FWD, legs(lh=(80, 0, -10), lk=-96, rh=(80, 0, 10), rk=-96))
    rows = bake([(0, rest, 'io'), (120, M(rest, body(root=(-12, 0, 0), waist=(-12, 4, 0), neck=(16, 6, 0))), 'io'), (239, rest, 'io')], n)
    add('Common', 'CampRest', breathe(rows, 1.4, 160, 0.3), loop=True)
    # Common_CampWarm: hands out to the fire, slow rub
    warm = M(SIT_FWD, A('R', (72, 18, 0), 28, (-30, 0, 0)), A('L', (72, 18, 0), 28, (-30, 0, 0)))
    rub = M(warm, A('R', (70, 26, 0), 34, (-30, 0, 0)), A('L', (70, 26, 0), 34, (-30, 0, 0)))
    rows = bake([(0, warm, 'io'), (40, rub, 'io'), (60, warm, 'io'), (80, rub, 'io'), (100, warm, 'io'), (180, warm, 'io'), (239, warm, 'io')], n)
    add('Common', 'CampWarm', breathe(rows, 0.8, 120, 0.2), loop=True)
    # Common_CampCraft: working an item in the lap, right hand taps / pulls (stitching, whittling)
    craft = M(SIT_FWD, A('R', (40, 40, 0), 104, (-20, 0, 0)), A('L', (36, 40, 0), 100, (-10, 0, 0)), body(root=(-12, 0, 0), waist=(-14, 0, 0), neck=(24, 0, 0)))
    pull = M(craft, A('R', (40, 22, 10), 86, (0, 0, 0)))
    keys = []
    for k in range(6):
        keys += [(k * 40, craft, 'io'), (k * 40 + 18, pull, 'out')]
    keys.append((239, craft, 'io'))
    add('Common', 'CampCraft', breathe(bake(keys, n), 0.8, 120, 0.2), loop=True)
    # Common_CampBandage: left forearm out, right hand wraps around it in loops
    band = M(SIT_FWD, A('L', (54, 30, 0), 60, (0, 0, 0)), A('R', (50, 48, 0), 96, (-10, 0, 0)), body(neck=(24, -10, 0)))
    wrap1 = M(band, A('R', (46, 40, 12), 92, (20, 0, 0)))
    wrap2 = M(band, A('R', (42, 56, -10), 104, (-30, 0, 0)))
    keys = [(0, band, 'io')]
    for k in range(5):
        keys += [(k * 44 + 14, wrap1, 'io'), (k * 44 + 30, wrap2, 'io')]
    keys.append((239, band, 'io'))
    add('Common', 'CampBandage', bake(keys, n), loop=True)
    # Common_CampInspect: weapon held up, turned in the light
    insp = M(SIT, A('R', (64, 34, 0), 90, (0, 0, 0)), A('L', (54, 40, 0), 96, (0, 0, 0)), body(waist=(-8, 0, 0), neck=(16, 0, 0)))
    turn = M(insp, A('R', (66, 30, 0), 90, (0, 0, 50)), body(waist=(-8, 6, 0), neck=(16, 8, 0)))
    rows = bake([(0, insp, 'io'), (70, turn, 'io'), (150, insp, 'io'), (239, insp, 'io')], n)
    add('Common', 'CampInspect', breathe(rows, 0.8, 120, 0.2), loop=True)
    # Common_CampMeditate: cross-legged, hands on knees, very slow breath
    med = M(legs(lh=(70, 0, -40), lk=-132, la=20, rh=(70, 0, 40), rk=-132, ra=20), body(root=(2, 0, 0), waist=(2, 0, 0), neck=(10, 0, 0), p=(0, -1.0, 0)),
            A('R', (24, -6, 10), 30, (-20, 0, 0)), A('L', (24, -6, 10), 30, (-20, 0, 0)))
    add('Common', 'CampMeditate', breathe(bake([(0, med, 'io'), (239, med, 'io')], n), 2.0, 240, 0.4), loop=True, allow=('crossed_knees',))
    # Common_CampSleep: curled on the side under a bedroll
    sleep = M(legs(lh=(60, 0, 0), lk=-80, rh=(50, 0, 0), rk=-70), body(root=(0, 0, 88), waist=(-10, 0, 0), neck=(16, 0, 0), p=(0, -2.3, 0)),
              A('R', (60, 30, 0), 100), A('L', (40, 20, 0), 80))
    add('Common', 'CampSleep', breathe(bake([(0, sleep, 'io'), (239, sleep, 'io')], n), 1.6, 240, 0.3), loop=True, allow=('extreme_lean',))
    # Common_LevelUp: chest lifts, fist clenches up to the chest, a grounded nod (earned, not a cheer)
    st = M(legs(lh=(4, 0, -6), lk=-6, rh=(-2, 0, 6), rk=-4), body(), A('R', (8, 10, 0), 16), A('L', (8, 10, 0), 16))
    up = M(st, body(waist=(6, 0, 0), neck=(-12, 0, 0), p=(0, 0.06, 0)), A('R', (50, 50, 0), 130, (-20, 0, 0)), A('L', (14, 10, 10), 30))
    rows = bake([(0, st, 'io'), (18, M(st, body(waist=(-6, 0, 0), neck=(10, 0, 0), p=(0, -0.08, 0))), 'io'), (40, up, 'out'), (80, up, 'hold'),
                 (100, M(up, body(neck=(10, 0, 0))), 'io'), (130, st, 'io'), (149, st, 'io')], 150)
    add('Common', 'LevelUp', rows, w=18, i=[40], r=100, allow=('hand_in_head',))
    # Common_Defeat: sinks to one knee, head drops
    kneel = M(legs(lh=(80, 0, -6), lk=-80, rh=(-10, 0, 6), rk=-110, ra=30), body(root=(-10, 0, 0), waist=(-16, 0, 0), neck=(30, 0, 0), p=(0, -1.6, 0)),
              A('R', (10, 0, 6), 10), A('L', (30, 10, 0), 40))
    rows = bake([(0, st, 'io'), (40, M(st, body(waist=(-10, 0, 0), neck=(16, 0, 0), p=(0, -0.2, 0))), 'io'), (80, kneel, 'io'), (179, kneel, 'hold')], 180)
    add('Common', 'Defeat', rows, w=40, i=[80], r=179, allow=('extreme_lean',))


def per_class():
    PW.load_all()
    for cls in ('Fighter', 'Rogue', 'Wizard', 'Cleric'):
        g = PW.POWERS[cls]()['guard']
        # Stance = the combat guard loop (phase6 Idle is the same guard; Idle below is the relaxed tavern stand)
        relaxed = {
            'Fighter': M(legs(lh=(6, 0, -8), lk=-6, rh=(-4, 0, 8), rk=-4), body(root=(0, -6, 0), waist=(2, -2, 0), neck=(0, 8, 0)), A('R', (6, 8, 0), 18, (-10, 0, 0)), A('L', (12, 18, 0), 40)),
            'Rogue': M(legs(lh=(10, 0, -6), lk=-14, rh=(-6, 0, 10), rk=-6, ra=6), body(root=(0, -14, 4), waist=(-4, -6, 0), neck=(6, 16, 0), p=(0, -0.06, 0)), A('R', (10, 20, 0), 60, (-20, 0, 0)), A('L', (4, 10, 0), 24)),
            'Wizard': M(legs(lh=(4, 0, -6), lk=-4, rh=(-2, 0, 6), rk=-4), body(root=(0, -4, 0), waist=(0, 0, 0), neck=(6, 4, 0)), A('L', (22, 8, 0), 70), A('R', (30, 60, 0), 110, (-20, 0, 0))),
            'Cleric': M(legs(lh=(4, 0, -8), lk=-6, rh=(-4, 0, 8), rk=-6), body(root=(0, -4, 0), waist=(-2, 0, 0), neck=(6, 4, 0)), A('L', (14, 24, 0), 50), A('R', (10, 10, 0), 30, (-10, 0, 0))),
        }[cls]
        RELAXED[cls], GUARD[cls] = relaxed, g
        n = 192
        rows = bake([(0, relaxed, 'io'), (96, M(relaxed, body(neck=(relaxed['Neck'][0], relaxed['Neck'][1] + 10, 0))), 'io'), (191, relaxed, 'io')], n)
        add(cls, 'Idle', breathe(rows, 1.0, 96, 0.4), loop=True, allow=('hand_in_head',))
        # Pose: class flourish for the creator, returns to Idle
        flourish = {
            'Fighter': [(30, M(relaxed, A('R', (70, 10, 0), 70), body(waist=(4, 0, 0), neck=(-6, 0, 0))), 'io'), (60, M(g, A('R', (100, 0, 0), 20)), 'snap'), (100, g, 'io')],
            'Rogue': [(24, M(relaxed, A('R', (60, 40, 0), 120, (-40, 0, 40))), 'io'), (44, M(relaxed, A('R', (64, 40, 0), 120, (-40, 0, -90))), 'out'), (70, M(g), 'out'), (104, g, 'io')],
            'Wizard': [(40, M(relaxed, A('R', (60, 20, 10), 40, (-30, 0, 0))), 'io'), (80, M(relaxed, A('R', (78, -10, 0), 20, (10, 0, 0)), body(neck=(0, -6, 0))), 'io'), (110, relaxed, 'io')],
            'Cleric': [(36, M(relaxed, A('R', (60, 40, 0), 110), body(neck=(20, 0, 0))), 'io'), (80, M(relaxed, A('R', (60, 40, 0), 110), body(neck=(24, 0, 0))), 'hold'), (116, M(g), 'io')],
        }[cls]
        keys = [(0, relaxed, 'io')] + flourish + [(150, relaxed, 'io'), (179, relaxed, 'io')]
        add(cls, 'Pose', bake(keys, 180), w=0, i=[flourish[1][0]], r=150, allow=('hand_in_head', 'elbow_up', 'hands_up'))
        # Knockdown (thrown onto the back), Downed (loop), GetUp, Death
        air = M(g, body(root=(30, g['Root'][1], 0), waist=(10, 0, 0), neck=(-14, 0, 0), p=(0, 0.2, 0.9)), A('R', (60, -20, 40), 20), A('L', (60, -20, 40), 20),
                legs(lh=(50, 0, -10), lk=-40, rh=(30, 0, 10), rk=-60))
        down = M(legs(lh=(20, 0, -14), lk=-30, rh=(6, 0, 14), rk=-10), body(root=(86, 10, 0), waist=(4, 0, 0), neck=(-10, 14, 0), p=(0, -2.35, 2.2)),
                 A('R', (20, -10, 50), 20), A('L', (14, -20, 30), 30))
        rows = bake([(0, g, 'io'), (6, M(g, body(root=(g['Root'][0] + 10, g['Root'][1], 0), waist=(8, 0, 0), neck=(-12, 0, 0), p=(0, -0.1, 0.2))), 'snap'),
                     (18, air, 'out'), (30, down, 'in'), (36, M(down, body(root=(82, 10, 0), p=(0, -2.25, 2.25))), 'out'), (44, down, 'io'), (59, down, 'hold')], 60)
        add(cls, 'Knockdown', rows, w=0, i=[30], r=44, allow=('extreme_lean', 'hands_up', 'elbow_up'))
        rows = bake([(0, down, 'io'), (60, M(down, body(neck=(-4, 20, 0), root=(86, 12, 0), p=(0, -2.35, 2.2))), 'io'), (119, down, 'io')], 120)
        add(cls, 'Downed', breathe(rows, 2.0, 60, 0.3), loop=True, allow=('extreme_lean',))
        situp = M(legs(lh=(70, 0, -10), lk=-100, rh=(20, 0, 10), rk=-30), body(root=(30, 0, 0), waist=(-20, 0, 0), neck=(10, 0, 0), p=(0, -2.0, 1.6)), A('R', (-30, 0, 20), 20), A('L', (20, 20, 0), 60))
        kneel = M(legs(lh=(80, 0, -6), lk=-84, rh=(-6, 0, 8), rk=-104, ra=26), body(root=(-12, 0, 0), waist=(-10, 0, 0), neck=(12, 0, 0), p=(0, -1.4, 0.6)), A('R', (20, 10, 0), 40), A('L', (40, 20, 0), 60))
        rows = bake([(0, down, 'io'), (16, situp, 'out'), (34, kneel, 'io'), (52, M(g, body(p=(g['p'][0], g['p'][1] - 0.15, 0.1))), 'io'), (64, g, 'io'), (71, g, 'hold')], 72)
        add(cls, 'GetUp', rows, w=0, i=[52], r=64, allow=('extreme_lean', 'crossed_knees'))
        dead = M(legs(lh=(24, 0, -18), lk=-34, rh=(4, 0, 16), rk=-8, ra=20), body(root=(88, 18, -6), waist=(6, 6, 0), neck=(-6, 30, 0), p=(0, -2.4, 2.0)),
                 A('R', (30, -20, 70), 30), A('L', (10, -10, 40), 20))
        sag = M(g, body(root=(g['Root'][0] - 14, g['Root'][1], 0), waist=(-18, 0, 0), neck=(26, 0, 0), p=(0, -0.5, 0)), A('R', (10, 0, 10), 10), A('L', (10, 0, 10), 10),
                legs(lh=(30, 0, -10), lk=-50, rh=(10, 0, 10), rk=-60))
        knees = M(sag, legs(lh=(70, 0, -6), lk=-110, rh=(60, 0, 6), rk=-120), body(root=(-6, g['Root'][1], 0), waist=(-20, 0, 0), neck=(30, 0, 0), p=(0, -1.6, 0.2)))
        rows = bake([(0, g, 'io'), (10, M(g, body(root=(g['Root'][0] + 12, g['Root'][1], 0), neck=(-20, 0, 0), p=(0, 0, 0.25))), 'snap'), (34, sag, 'io'),
                     (56, knees, 'in'), (80, dead, 'in'), (86, M(dead, body(root=(84, 18, -6), p=(0, -2.3, 2.05))), 'out'), (96, dead, 'io'), (119, dead, 'hold')], 120)
        add(cls, 'Death', rows, w=0, i=[80], r=96, allow=('extreme_lean', 'crossed_knees'))


DIRECT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'direct')
LEGS = ['RightHip', 'RightKnee', 'RightAnkle', 'LeftHip', 'LeftKnee', 'LeftAnkle']
ARMS = ['RightShoulder', 'RightElbow', 'RightWrist', 'LeftShoulder', 'LeftElbow', 'LeftWrist']
FOOT = {}


def load(name):
    d = json.load(open(os.path.join(DIRECT, name + '.json')))
    return [{j: tuple(f.get(j, (0, 0, 0))) for j in J} | {'p': tuple(f.get('p', (0, 0, 0)))} for f in d['frames']]


def mean_row(rows):
    m = {j: tuple(sum(r[j][i] for r in rows) / len(rows) for i in range(3)) for j in J}
    m['p'] = tuple(sum(r['p'][i] for r in rows) / len(rows) for i in range(3)); return m


def lerp3(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def seal(rows, k=8):
    n = len(rows)
    for q in range(k):
        t = ease((q + 1) / (k + 1), 'io'); f = n - k + q
        rows[f] = {j: lerp3(rows[f][j], rows[0][j], t) for j in J} | {'p': lerp3(rows[f]['p'], rows[0]['p'], t)}
    return rows


def blend_in(rows, start, k):
    for f in range(min(k, len(rows))):
        t = ease(f / k, 'io')
        rows[f] = {j: lerp3(start[j], rows[f][j], t) for j in J} | {'p': lerp3(start['p'], rows[f]['p'], t)}
    return rows


def footsteps(rows):
    """frames where each foot is lowest (contact), from posecheck FK"""
    hs = {'L': [], 'R': []}
    for r in rows:
        pos = PC.fk(r)[0]
        hs['L'].append(pos.get('LeftFoot', pos.get('LeftAnkle'))[1]); hs['R'].append(pos.get('RightFoot', pos.get('RightAnkle'))[1])
    out = {}
    for s, h in hs.items():
        n = len(h); lo = min(h)
        cand = sorted((h[f], f) for f in range(n) if h[f] <= lo + 0.06 and h[f] <= h[f - 1] and h[f] <= h[(f + 1) % n])
        pick = []
        for _, f in cand:
            if all(min(abs(f - q), n - abs(f - q)) > n // 3 for q in pick): pick.append(f)
        out['Foot' + s] = sorted(pick)
    return out


def smooth(rows, start=6, it=2):
    for j in J:  # unwrap euler series first so averaging never crosses the +-180 seam
        u = E.unwrap([r[j] for r in rows])
        for f, r in enumerate(rows): r[j] = tuple(u[f])
    for _ in range(it):
        out = [dict(r) for r in rows]
        for f in range(max(1, start), len(rows) - 1):
            for j in J:
                out[f][j] = tuple((rows[f - 1][j][i] + 2 * rows[f][j][i] + rows[f + 1][j][i]) / 4 for i in range(3))
        rows = out
    return rows


def hkx_based():
    """Upgrades from the new free-use sets: UNDERDOG locomotion (Walk/Run), UNDERDOG Death (Death x3, Knockdown),
    Take a Seat (sits, camp base). HKX legs/root carry weight and gait; class arms/torso stay authored."""
    walk = {'Fighter': 'v4_sw_walk', 'Rogue': 'walk_R', 'Wizard': 'walk_W', 'Cleric': 'walk_C'}
    run = {'Fighter': 'v4_sw_run', 'Rogue': 'run_R', 'Wizard': 'run_W', 'Cleric': 'run_C'}
    armsw = {'Fighter': 0.25, 'Rogue': 0.35, 'Wizard': 0.15, 'Cleric': 0.25}
    for cls in ('Fighter', 'Rogue', 'Wizard', 'Cleric'):
        rel, g = RELAXED[cls], GUARD[cls]
        for slot, src, base in (('Walk', walk[cls], rel), ('Run', run[cls], M(rel, {k: g[k] for k in ARMS if k in g}))):
            h = load(src); mh = mean_row(h); rows = []
            for r in h:
                o = {j: r[j] for j in LEGS}
                o['Root'] = r['Root']; o['p'] = r['p']
                for j in ('Waist', 'Neck'):
                    o[j] = lerp3(base.get(j, (0, 0, 0)), r[j], 0.5)
                for j in ARMS:  # class arm pose + a share of the HKX swing (delta from the clip mean)
                    b = base.get(j, (0, 0, 0)); o[j] = tuple(b[i] + (r[j][i] - mh[j][i]) * armsw[cls] for i in range(3))
                rows.append(o)
            rows = seal(rows)
            add(cls, slot, rows, loop=True, allow=('crossed_knees', 'hand_in_head'))
            FOOT['%s_%s' % (cls, slot)] = footsteps(rows)
        # deaths: three variants per class, eased in from the class stance; Death = variant 1 (compat)
        for k in (1, 2, 3):
            rows = smooth(blend_in(load('death_%s%d' % (cls[0], k)), g, 12), 12)
            ys = [r['p'][1] for r in rows]; yN = ys[-1]
            hit = next((f for f in range(len(rows)) if ys[f] <= yN + 0.12), len(rows) - 1)
            name = 'Death' if k == 1 else 'Death%d' % k
            add(cls, name, rows, w=0, i=[hit], r=len(rows) - 1, allow=('extreme_lean', 'crossed_knees', 'hands_up', 'elbow_up', 'hand_in_head'))
        # knockdown (HKX fall) -> Downed (its last pose, breathing) -> GetUp (from that pose to the stance)
        rows = smooth(blend_in(load('knock_' + cls[0]), g, 8), 8)
        ys = [r['p'][1] for r in rows]; hit = next((f for f in range(len(rows)) if ys[f] <= ys[-1] + 0.12), len(rows) - 1)
        add(cls, 'Knockdown', rows, w=0, i=[hit], r=len(rows) - 1, allow=('hand_in_torso', 'extreme_lean', 'crossed_knees', 'hands_up', 'elbow_up', 'hand_in_head'))
        down = dict(rows[-1])
        add(cls, 'Downed', breathe(bake([(0, down, 'io'), (119, down, 'io')], 120), 1.6, 60, 0.3), loop=True, allow=('extreme_lean', 'crossed_knees', 'hands_up', 'elbow_up', 'hand_in_head'))
        situp = M(down, legs(lh=(70, 0, -10), lk=-100, rh=(20, 0, 10), rk=-30), body(root=(30, down['Root'][1], 0), waist=(-20, 0, 0), neck=(10, 0, 0), p=(0, -2.0, down['p'][2] * 0.6)))
        kneel = M(legs(lh=(80, 0, -6), lk=-84, rh=(-6, 0, 8), rk=-104, ra=26), body(root=(-12, down['Root'][1] * 0.5, 0), waist=(-10, 0, 0), neck=(12, 0, 0), p=(0, -1.4, 0.3)), A('R', (20, 10, 0), 40), A('L', (40, 20, 0), 60))
        rows = bake([(0, down, 'io'), (24, situp, 'io'), (48, kneel, 'io'), (72, M(g, body(p=(g['p'][0], g['p'][1] - 0.15, 0.05))), 'io'), (86, g, 'io'), (89, g, 'hold')], 90)
        add(cls, 'GetUp', rows, w=0, i=[72], r=86, allow=('extreme_lean', 'crossed_knees', 'hands_up', 'elbow_up', 'hand_in_head'))
    # sits: Seat handles height, so the HKX pelvis drop is removed (keep only its motion around frame 0)
    def sit(src):
        h = load(src); p0 = h[0]['p']
        return [dict(r) | {'p': tuple(r['p'][i] - p0[i] for i in range(3))} for r in h]
    add('Common', 'Sit', seal(sit('sit_a')), loop=True, allow=('crossed_knees',))
    add('Common', 'Sit2', seal(sit('sit_b')), loop=True, allow=('crossed_knees', 'elbow_up', 'hand_in_head'))  # lounging: hands behind the head (intentional)
    add('Common', 'CampRest', seal(sit('sit_lean')), loop=True, allow=('crossed_knees',))
    add('Common', 'SitGround', seal(sit('sit_cross')), loop=True, allow=('crossed_knees', 'elbow_up', 'hand_in_head'))
    add('Common', 'CampMeditate', seal(load('meditate')), loop=True, allow=('crossed_knees',))
    # camp activity clips keep their authored arms over the HKX seated lower body / torso
    base = sit('sit_a'); nb = len(base)
    for name in ('CampWarm', 'CampCraft', 'CampBandage', 'CampInspect'):
        rows = ROWS['Common_' + name]
        out = []
        for f, r in enumerate(rows):
            b = base[(f * 2) % nb]
            o = dict(r); [o.__setitem__(j, b[j]) for j in LEGS]; o['Root'] = b['Root']; o['p'] = b['p']
            o['Waist'] = lerp3(r['Waist'], b['Waist'], 0.5)
            out.append(o)
        add('Common', name, seal(out), loop=True, allow=('crossed_knees', 'hands_up', 'elbow_up', 'hand_in_head'))


def main():
    os.makedirs(OUT, exist_ok=True)
    common(); per_class(); hkx_based()
    import th_src4; th_src4.bind(sys.modules[__name__]); th_src4.build()  # set 4 upgrades (Vanargand / Leviathan)
    import th_dodge; th_dodge.build(sys.modules[__name__])  # dodge sets (Kratos / Smooth Sway)
    import th_combo; th_combo.build(sys.modules[__name__])  # COMBAT_TIMING combo chains
    json.dump(FOOT, open(os.path.join(OUT, 'footsteps.json'), 'w'))
    for rig_, items in CLIPS.items():
        open(os.path.join(OUT, 'Clips_TH_%s.lua' % rig_), 'w', newline='\n').write('return {\n' + ',\n'.join(items.values()) + '\n}\n')
    json.dump(QA, open(os.path.join(OUT, 'qa.json'), 'w'), indent=0)
    json.dump(QAF, open(os.path.join(OUT, 'qa_frames.json'), 'w'))
    json.dump({k: v for k, v in ROWS.items() if k.startswith('Archer_') or k.endswith('_2H') or 'Evade' in k or 'Dodge' in k or 'Combo' in k or 'Finisher' in k or k in ('Fighter_AttackLight', 'Fighter_AttackHeavy', 'Rogue_AttackLight', 'Rogue_AttackHeavy', 'Fighter_Walk', 'Fighter_Run')}, open(os.path.join(OUT, 'rows_src4.json'), 'w'))
    bad = {k: v for k, v in QA.items() if v}
    print('clips', len(QA), 'flagged', len(bad))
    for k, v in bad.items(): print('  ', k, v)


if __name__ == '__main__':
    main()
