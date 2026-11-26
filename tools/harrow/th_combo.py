"""COMBAT_TIMING combo clips (COMBAT request 2026-11-23): distinct MCO-library clips per weapon category, never one clip retimed.
<Class>_Combo1/2/3 (one contact each, chain 1->2->3 by cross-fading at r into the next clip's start = class guard) + <Class>_Finisher.
Impact gaps (prev r - prev i + next i): Fighter 1H 0.57 s, Rogue 0.40 s (0.30-0.45), Cleric 0.90 s (0.70-1.10), Fighter 2H 1.00 s (0.8-1.2).
Archer_Draw (i = FullDraw) + Archer_Release (i = string release). Markers w/sw/i/r; contact = annotated Hitframe or peak hand speed.
Bound into th_authored main after th_dodge.
"""
import os, json
import th_src4 as S

HITS = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out', 'direct', 'combo_hits.json')))
# cls: guard key, (w, i, r, n) for combos, sources c1..c3, finisher
PLAN = {
    'Fighter': ('Fighter', (6, 18, 34, 48), ['v4_sw_light', 'cb_sw_c2', 'cb_sw_c3'], 'cb_sw_fin'),
    'Fighter2H': ('Stance_2H', (14, 32, 60, 78), ['cb_gs_c1', 'cb_gs_c2', 'cb_gs_c3'], 'cb_gs_fin'),
    'Rogue': ('Rogue', (4, 12, 24, 38), ['v4_dw_light', 'cb_dg_c2', 'cb_dg_c3'], 'cb_dg_fin'),
    'Cleric': ('Cleric', (12, 30, 54, 70), ['cb_mc_c1', 'cb_mc_c2', 'cb_mc_c3'], 'v4_sw_heavy'),
}


def contact(name, rows):
    h = HITS.get(name) or []
    if h:
        return min(len(rows) - 2, max(2, int(round(h[0] * 60))))
    return S.peak(rows)


def build_one(src, guard, w, i, r, n, keep_left=None, smooth=3, comp=1.6):
    h = S.load(src); pk = contact(src, h)
    pre = min(pk, int(i * comp) + 2); post = min(len(h) - 1 - pk, int((n - i) * 1.3))
    rows = S.warp(h, [pk - pre, pk, pk + post], [0, i, n - 1])
    rows = S.blend_in2(S.damp_travel(rows, 0.45), S.full(guard), max(8, w))
    rows = S.settle(rows, guard, max(8, n - r))          # tail after r eases into the guard (= next combo's first pose)
    if keep_left is not None:
        rows = S.keep_arm(rows, keep_left, 'Left', 0.8)
    return S.soften(rows, keep=(i,), it=smooth), pk


def build(T):
    rep = {}
    for key, (gk, (w, i, r, n), srcs, fin) in PLAN.items():
        rig = 'Fighter' if key.startswith('Fighter') else key
        suf = '_2H' if key == 'Fighter2H' else ''
        g = T.ROWS['Fighter_Stance_2H'][0] if gk == 'Stance_2H' else T.GUARD[gk]
        shield = T.GUARD['Fighter'] if key == 'Fighter' else (T.GUARD['Cleric'] if key == 'Cleric' else None)
        for k, src in enumerate(srcs):
            rows, pk = build_one(src, g, w, i, r, n, shield, *((6, 1.2) if key == 'Cleric' else (3, 1.6)))
            name = 'Combo%d%s' % (k + 1, suf)
            T.add(rig, name, rows, w=w, i=[i], r=r, allow=S.OK)
            rep['%s_%s' % (rig, name)] = dict(src=src, contact=pk)
        fi, fr, fn = i + 10, i + 10 + 34, i + 10 + 34 + 24
        rows, pk = build_one(fin, g, w + 6, fi, fr, fn, shield, *((6, 1.2) if key == 'Cleric' else (3, 1.6)))
        T.add(rig, 'Finisher' + suf, rows, w=w + 6, i=[fi], r=fr, allow=S.OK); rep['%s_Finisher%s' % (rig, suf)] = dict(src=fin, contact=pk)
    # bow: draw to full (FullDraw = i) and release (i = string leaves)
    a0 = T.ROWS['Archer_Stance'][0]
    d = S.load('v4_bow_draw'); rows = S.warp(d, [0, len(d) - 1], [0, 39]) + [dict(S.warp(d, [0, len(d) - 1], [0, 39])[-1]) for _ in range(6)]
    T.add('Archer', 'Draw', S.soften(S.blend_in2(rows, a0, 10), keep=(39,)), w=4, i=[39], r=45, allow=S.OK)
    rl = S.load('v4_bow_release'); rows = S.settle(S.warp(rl, [0, len(rl) - 1], [0, 33]), a0, 14)
    T.add('Archer', 'Release', S.soften(rows, keep=(2,)), w=0, i=[2], r=20, allow=S.OK)
    json.dump(rep, open(os.path.join(T.OUT, 'combo_report.json'), 'w'), indent=1)
    return rep
