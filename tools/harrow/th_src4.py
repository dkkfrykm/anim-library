"""Set 4 (src4: Vanargand / Leviathan, free-use) composition stage for th_authored.py.
Fighter 1H attacks (Vanargand II sword), Fighter _2H greatsword/maul set (Leviathan II), Rogue strikes (Vanargand dual-wield
sneak), new Archer rig (Vanargand archery / sneak archery). Melee slot timings unchanged (phase6 P2.SLOT).
Direct dumps: out/direct/v4_*.json (th_direct.py, jobs out/direct_jobs_src4*.json).
"""
import os, math, json


def bind(T):
    """use the running th_authored module's state (it runs as __main__)"""
    g = globals()
    for k in ('J', 'load', 'lerp3', 'seal', 'blend_in', 'bake', 'ease', 'full', 'add', 'footsteps', 'ROWS', 'GUARD', 'FOOT', 'OUT'):
        g[k] = getattr(T, k)
import posecheck as PC
import th_enc as E


def unwrapped(rows):
    rows = [dict(r) for r in rows]
    for j in J:
        u = E.unwrap([r[j] for r in rows])
        for f, r in enumerate(rows): r[j] = tuple(u[f])
    return rows


def warp(rows, src, dst):
    """piecewise-linear retime: source frames src[k] land on output frames dst[k]; output length dst[-1] + 1"""
    rows = unwrapped(rows); out = []
    for f in range(dst[-1] + 1):
        k = 0
        while k + 2 < len(dst) and f > dst[k + 1]: k += 1
        t = (f - dst[k]) / max(1, dst[k + 1] - dst[k])
        x = min(len(rows) - 1, max(0.0, src[k] + (src[k + 1] - src[k]) * t))
        a = int(x); b = min(a + 1, len(rows) - 1); u = x - a
        out.append({j: lerp3(rows[a][j], rows[b][j], u) for j in J} | {'p': lerp3(rows[a]['p'], rows[b]['p'], u)})
    return out


def peak(rows, side='Right'):
    """frame of the fastest hand (strike contact proxy)"""
    hs = [PC.fk(r)[2][side] for r in rows]
    sp = [(sum((hs[f + 1][i] - hs[f - 1][i]) ** 2 for i in range(3)), f) for f in range(1, len(rows) - 2)]
    return max(sp)[1]


def near(t, r):
    """target euler triple moved by whole turns to the branch nearest r (unwrapped series)"""
    return tuple(t[i] + 360.0 * round((r[i] - t[i]) / 360.0) for i in range(3))


def _q(e):  # XYZ euler (deg, R = Rx Ry Rz as posecheck.R) -> quaternion (w,x,y,z)
    m = PC.R(e); t = m[0][0] + m[1][1] + m[2][2]
    if t > 0:
        s = math.sqrt(t + 1) * 2; return ((0.25 * s), (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    i = max(range(3), key=lambda k: m[k][k]); j, k = (i + 1) % 3, (i + 2) % 3
    s = math.sqrt(1 + m[i][i] - m[j][j] - m[k][k]) * 2
    q = [0.0] * 4; q[0] = (m[k][j] - m[j][k]) / s; q[1 + i] = 0.25 * s; q[1 + j] = (m[j][i] + m[i][j]) / s; q[1 + k] = (m[k][i] + m[i][k]) / s
    return tuple(q)


def _e(q):  # quaternion -> XYZ euler (deg), same decomposition as sky2r15
    w, x, y, z = q
    m02 = 2 * (x * z + w * y); m12 = 2 * (y * z - w * x); m22 = 1 - 2 * (x * x + y * y); m01 = 2 * (x * y - w * z); m00 = 1 - 2 * (y * y + z * z)
    return (math.degrees(math.atan2(-m12, m22)), math.degrees(math.asin(max(-1, min(1, m02)))), math.degrees(math.atan2(-m01, m00)))


def lerpa(a, b, u):
    """rotation blend on the shortest arc (quaternion slerp), result moved to the euler branch nearest a (no flips/spins)"""
    qa, qb = _q(a), _q(b)
    d = sum(qa[i] * qb[i] for i in range(4))
    if d < 0: qb = tuple(-v for v in qb); d = -d
    if d > 0.9995:
        q = tuple(qa[i] + (qb[i] - qa[i]) * u for i in range(4))
    else:
        th = math.acos(d); s0 = math.sin((1 - u) * th) / math.sin(th); s1 = math.sin(u * th) / math.sin(th)
        q = tuple(qa[i] * s0 + qb[i] * s1 for i in range(4))
    n = math.sqrt(sum(v * v for v in q)); q = tuple(v / n for v in q)
    return near(_e(q), a)


def blend_in2(rows, start, k):
    start = full(start)
    for f in range(min(k, len(rows))):
        t = ease(f / k, 'io')
        rows[f] = {j: lerpa(start[j], rows[f][j], t) if j != 'p' else None for j in J} | {'p': lerp3(start['p'], rows[f]['p'], t)}
    return rows


def seal2(rows, k=8):
    n = len(rows)
    for q in range(k):
        t = ease((q + 1) / (k + 1), 'io'); f = n - k + q
        rows[f] = {j: lerpa(rows[f][j], rows[0][j], t) for j in J} | {'p': lerp3(rows[f]['p'], rows[0]['p'], t)}
    return rows


def settle(rows, target, k):
    n = len(rows); target = full(target)
    for q in range(k):
        f = n - k + q; t = ease((q + 1) / k, 'io')
        rows[f] = {j: lerpa(rows[f][j], target[j], t) for j in J} | {'p': lerp3(rows[f]['p'], target['p'], t)}
    return rows


def keep_arm(rows, pose, side, w=1.0):
    for r in rows:
        for j in (side + 'Shoulder', side + 'Elbow', side + 'Wrist'):
            r[j] = lerpa(r[j], tuple(pose.get(j, (0, 0, 0))), w)
    return rows


def damp_travel(rows, k=0.5):
    p0 = rows[0]['p']
    for r in rows:
        r['p'] = (p0[0] + (r['p'][0] - p0[0]) * k, r['p'][1], p0[2] + (r['p'][2] - p0[2]) * k)
    return rows


def strike(src, pre, post, dst, start, end, side='Right'):
    h = load(src); pk = peak(h, side)
    rows = warp(h, [max(0, pk - pre), pk, min(len(h) - 1, pk + post)], dst)
    rows = blend_in2(damp_travel(rows), full(start), 10)
    imp = dst[1]
    return soften(settle(rows, end, len(rows) - imp - 6), keep=(imp,)), pk


def soften(rows, keep=(), it=3):
    """3-tap smoothing everywhere except +-3 frames around each frame in keep (impacts stay sharp)"""
    rows = unwrapped(rows); hold = {f + d for f in keep for d in range(-3, 4)}
    for _ in range(it):
        out = [dict(r) for r in rows]
        for f in range(1, len(rows) - 1):
            if f in hold: continue
            for j in list(J) + ['p']:
                out[f][j] = tuple((rows[f - 1][j][i] + 2 * rows[f][j][i] + rows[f + 1][j][i]) / 4 for i in range(3))
        rows = out
    return rows


def hand_gap(rows, f):
    hand = PC.fk(rows[f])[2]
    return round(math.dist(hand['Right'], hand['Left']), 2)


OK = ('extreme_lean', 'crossed_knees', 'hands_up', 'elbow_up', 'hand_in_head', 'hand_beside_head', 'hand_in_torso')


def build():
    rep = {}
    g = GUARD['Fighter']  # Fighter 1H: HKX whole body, shield arm (left) held on the class guard
    rows, rep['Fighter_AttackLight'] = strike('v4_sw_light', 26, 40, [0, 18, 41], g, g)
    add('Fighter', 'AttackLight', keep_arm(rows, g, 'Left', 0.85), w=8, i=[18], r=32, allow=OK)
    rows, rep['Fighter_AttackHeavy'] = strike('v4_sw_heavy', 60, 40, [0, 38, 65], g, g)
    add('Fighter', 'AttackHeavy', keep_arm(rows, g, 'Left', 0.85), w=20, i=[38], r=52, allow=OK)
    # Fighter _2H (greatsword / maul / dane axe / spear; ARMORY grip offsets keep the off hand on the haft)
    stance = seal2(unwrapped(load('v4_gs_stance')[:192]), 16); s0 = stance[0]
    add('Fighter', 'Stance_2H', stance, loop=True, allow=OK)
    rows, rep['Fighter_AttackLight_2H'] = strike('v4_gs_light', 30, 24, [0, 18, 41], s0, s0)
    add('Fighter', 'AttackLight_2H', rows, w=8, i=[18], r=32, allow=OK)
    rows, rep['Fighter_AttackHeavy_2H'] = strike('v4_gs_heavy', 56, 40, [0, 38, 65], s0, s0)
    add('Fighter', 'AttackHeavy_2H', rows, w=20, i=[38], r=52, allow=OK)
    h = load('v4_gs_block'); pk = peak(h, 'Left')
    add('Fighter', 'Block_2H', settle(blend_in2(warp(h, [0, pk, len(h) - 1], [0, 10, 33]), s0, 4), s0, 8), w=3, i=[10], r=22, allow=OK)
    h = load('v4_gs_hit'); pk = peak(h, 'Left')
    add('Fighter', 'Hit_2H', soften(settle(blend_in2(warp(h, [0, pk, len(h) - 1], [0, 6, 35]), s0, 4), s0, 16), keep=(6,)), w=2, i=[6], r=20, allow=OK)
    low = dict(s0); low['p'] = (s0['p'][0] - 1.25, s0['p'][1] - 0.34, s0['p'][2] + 0.15)
    low['Root'] = (s0['Root'][0] - 28, s0['Root'][1] - 10, s0['Root'][2]); low['LeftKnee'] = (s0['LeftKnee'][0] - 30, 0, 0)
    add('Fighter', 'PerfectEvade_2H', bake([(0, s0, 'io'), (9, low, 'snap'), (20, low, 'hold'), (33, s0, 'io')], 34), w=2, i=[9], r=22, allow=OK)
    g = GUARD['Rogue']  # Rogue: dual-wield sneak thrust (light), dual power strike (heavy)
    rows, rep['Rogue_AttackLight'] = strike('v4_dw_light', 26, 30, [0, 18, 41], g, g)
    add('Rogue', 'AttackLight', rows, w=8, i=[18], r=32, allow=OK)
    rows, rep['Rogue_AttackHeavy'] = strike('v4_dw_heavy', 44, 12, [0, 38, 65], g, g)
    add('Rogue', 'AttackHeavy', rows, w=20, i=[38], r=52, allow=OK)
    # Archer rig (Ranger later + ranged enemies): bow in the left hand, string hand right
    st = seal2(unwrapped(load('v4_bow_stance')[:240]), 20); a0 = st[0]
    add('Archer', 'Stance', st, loop=True, allow=OK)
    add('Archer', 'Idle', [dict(r) for r in st], loop=True, allow=OK)
    for slot, src in (('Walk', 'v4_bow_walk'), ('Run', 'v4_bow_run')):
        rows = seal2(unwrapped(load(src)), 6)
        add('Archer', slot, rows, loop=True, allow=OK); FOOT['Archer_' + slot] = footsteps(rows)
    add('Archer', 'Aim', seal2(unwrapped(load('v4_bow_aim')), 12), loop=True, allow=OK)
    d, r_ = load('v4_bow_draw'), load('v4_bow_release')
    rows = warp(d, [0, len(d) - 1], [0, 48]) + warp(r_, [0, len(r_) - 1], [0, 24])
    add('Archer', 'AttackLight', soften(settle(blend_in2(rows, a0, 16), a0, 16), keep=(51,)), w=4, i=[51], r=66, allow=OK)
    d, a, r_ = load('v4_sbow_draw'), load('v4_sbow_aim'), load('v4_sbow_release')
    rows = warp(d, [0, len(d) - 1], [0, 43]) + warp(a, [0, 60], [0, 39]) + warp(r_, [0, len(r_) - 1], [0, 31])
    add('Archer', 'AttackHeavy', soften(settle(blend_in2(rows, a0, 16), a0, 16), keep=(86,)), w=4, i=[86], r=104, allow=OK)
    rep['hand_gap_2H'] = {k: hand_gap(ROWS['Fighter_' + k], f) for k, f in (('Stance_2H', 0), ('Block_2H', 10), ('AttackLight_2H', 18), ('AttackHeavy_2H', 38))}
    rep['hand_gap_Archer_aim'] = hand_gap(ROWS['Archer_Aim'], 0)
    json.dump(rep, open(os.path.join(OUT, 'src4_report.json'), 'w'), indent=1)
    return rep
