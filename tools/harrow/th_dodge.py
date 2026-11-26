"""Dodge sets (src4d: Kratos Step Dodge, Smooth Sway Dodge; free-use) -> PerfectEvade / Dodge clips per class.
E33-style perfect dodge: a short committed slip with real root travel, back on the mark by the end (end in stance).
HKX legs / pelvis / torso + animmotion root travel (Skyrim -> studs via sky2r15.K / LEG_SCALE); class arms held on the
class guard (shield, staff, bow, two-handed grip) with a share of the HKX arm sway. Slot timings unchanged (phase6 P2.SLOT):
PerfectEvade n34 w2 i9 r22, Dodge n36 w3 i12 r24. Bound into th_authored main after th_src4.
"""
import os, json, gzip, math
import th_src4 as S

CAT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'catalog', 'catalog.json')
SRC = {'dg_kr_L': ('Kratos Dodge Animations', 'mco_dodge-l-1'), 'dg_kr_R': ('Kratos Dodge Animations', 'mco_dodge-r-1'),
       'dg_kr_B': ('Kratos Dodge Animations', 'mco_dodge-b-1'), 'dg_kr_F': ('Kratos Dodge Animations', 'mco_dodge-f-1'),
       'dg_kr_LB': ('Kratos Dodge Animations', 'mco_dodge-lb-1'), 'dg_kr_RB': ('Kratos Dodge Animations', 'mco_dodge-rb-1'),
       'dg_kr_stepL': ('Kratos Dodge Animations', 'stepdodgeleft'), 'dg_kr_stepR': ('Kratos Dodge Animations', 'stepdodgeright'),
       'dg_sw_L': ('Smooth Sway Dodge', 'mco_dodge-l-1'), 'dg_sw_R': ('Smooth Sway Dodge', 'mco_dodge-r-1')}
STUD = 1.55 / 62.8
ARMS = ('RightShoulder', 'RightElbow', 'RightWrist', 'LeftShoulder', 'LeftElbow', 'LeftWrist')
_cat = None


def motion(name, n):
    """per-frame (60 fps) cumulative root travel in R15 studs from the clip's animmotion annotations"""
    global _cat
    if _cat is None:
        _cat = {(r['set'], r['clip']): r for r in json.load(open(CAT)) if 'error' not in r}
    d = json.load(gzip.open(os.path.join(os.path.dirname(CAT), '..', '..', _cat[SRC[name]]['decoded']), 'rt'))
    keys = [(0.0, 0.0, 0.0, 0.0)]
    for t, s in d['annotations']:
        if s.lower().startswith('animmotion'):
            try: keys.append((t,) + tuple(float(x) for x in s.split()[1:4]))
            except ValueError: pass
    keys.sort()
    out = []
    for f in range(n):
        t = f / 60.0
        k = 0
        while k + 1 < len(keys) and keys[k + 1][0] <= t: k += 1
        if k + 1 < len(keys):
            a, b = keys[k], keys[k + 1]; u = (t - a[0]) / max(1e-6, b[0] - a[0])
            v = [a[i] + (b[i] - a[i]) * u for i in (1, 2, 3)]
        else:
            v = list(keys[-1][1:])
        out.append((v[0] * STUD, v[2] * STUD, -v[1] * STUD))  # Skyrim (x right, y fwd, z up) -> R15 (x right, y up, -z fwd)
    return out


def dodge(name, dst, guard, arm_keep, travel, drop=0.0):
    h = S.load(name); n = len(h)
    mv = motion(name, n)
    sp = [math.dist(mv[min(n - 1, f + 1)], mv[max(0, f - 1)]) for f in range(n)]
    tot = math.dist(mv[-1], mv[0]) or 1e-6
    pk = next((f for f in range(1, n - 1) if math.dist(mv[f], mv[0]) >= 0.6 * tot), n // 3)  # evade moment: 60% of the travel
    end = next((f for f in range(pk, n) if math.dist(mv[f], mv[0]) >= 0.97 * tot), n - 1)
    pk = max(pk, 3)
    end = min(n - 1, end + 10)
    for f, r in enumerate(h):
        m = mv[f]
        r['p'] = (r['p'][0] + m[0] * travel, r['p'][1] - drop * min(1.0, sp[f] / (max(sp) or 1)), r['p'][2] + m[2] * travel)
    rows = S.warp(h, [0, pk, end], dst)
    g = S.full(guard)
    for r in rows:  # class arms: guard pose + a share of the HKX sway
        for j in ARMS:
            r[j] = S.lerpa(r[j], g[j], arm_keep)
    rows = S.blend_in2(rows, g, 6)
    rows = S.settle(rows, g, max(8, dst[-1] - dst[1] - 10))
    return S.soften(rows, keep=(dst[1],), it=2), dict(src=SRC[name], peak=pk, end=end, travel=round(tot * travel, 2))


PE = [0, 9, 33]
DG = [0, 12, 35]
OK = S.OK + ('foot_slide',)
# rig: guard source, arm keep, (PerfectEvade src, travel, drop), (PerfectEvade_Alt), (Dodge src, travel), (Dodge_Back)
STYLE = {  # PerfectEvade = Smooth Sway (tight upright slip, E33 core); Dodge: armored/casters sway wider, agile classes roll (Kratos)
    'Fighter': ('Fighter', 0.85, ('dg_sw_L', 0.55, 0.05), ('dg_sw_R', 0.55, 0.05), ('dg_sw_L', 0.8), ('dg_sw_R', 0.8)),        # shield-side slip, square
    'Rogue':   ('Rogue', 0.45, ('dg_sw_R', 0.7, 0.2), ('dg_sw_L', 0.7, 0.2), ('dg_kr_LB', 0.75), ('dg_kr_B', 0.75)),       # low, fast; rolls
    'Wizard':  ('Wizard', 0.8, ('dg_sw_R', 0.4, 0.0), ('dg_sw_L', 0.4, 0.0), ('dg_sw_R', 0.6), ('dg_sw_L', 0.6)),          # small, upright
    'Cleric':  ('Cleric', 0.85, ('dg_sw_R', 0.5, 0.05), ('dg_sw_L', 0.5, 0.05), ('dg_sw_R', 0.75), ('dg_sw_L', 0.75)),     # planted, deliberate
    'Archer':  ('Archer', 0.6, ('dg_sw_R', 0.65, 0.1), ('dg_sw_L', 0.65, 0.1), ('dg_kr_LB', 0.7), ('dg_kr_B', 0.7)),       # skirmisher; rolls
}


def build(T):
    rep = {}
    for rig, (gk, keep, pe, pe2, dg, dg2) in STYLE.items():
        g = T.GUARD.get(gk) or T.ROWS['Archer_Stance'][0]
        for slot, (src, tr, dr) in (('PerfectEvade', pe), ('PerfectEvade_Alt', pe2)):
            rows, info = dodge(src, PE, g, keep, tr, dr)
            T.add(rig, slot, rows, w=2, i=[9], r=22, allow=OK); rep['%s_%s' % (rig, slot)] = info
        for slot, (src, tr) in (('Dodge', dg), ('Dodge_Alt', dg2)):
            rows, info = dodge(src, DG, g, keep, tr)
            T.add(rig, slot, rows, w=3, i=[12], r=24, allow=OK); rep['%s_%s' % (rig, slot)] = info
    s0 = T.ROWS['Fighter_Stance_2H'][0]  # two-handed: keep both hands on the grip
    rows, rep['Fighter_PerfectEvade_2H'] = dodge('dg_sw_L', PE, s0, 0.92, 0.5, 0.08)
    T.add('Fighter', 'PerfectEvade_2H', rows, w=2, i=[9], r=22, allow=OK)
    rows, rep['Fighter_Dodge_2H'] = dodge('dg_sw_R', DG, s0, 0.92, 0.75)
    T.add('Fighter', 'Dodge_2H', rows, w=3, i=[12], r=24, allow=OK)
    json.dump(rep, open(os.path.join(T.OUT, 'dodge_report.json'), 'w'), indent=1)
    return rep
