"""'Groping from behind' foreplay base (catalog scene fp_grope) from 8ae180ab (close-up torso: motion only).
Body-model fitting fails on this framing (NLF: 78/401 frames without a person, the rest truncated at the hips), so roto3_measure.py tracks
regions with DIS optical flow (affine per region) + the partner's hands by colour mask -> roto3_measure.json['grope'].
  her  : standing, both hands on hips (Sonders 'licorice_24'), + the measured reaction: shoulder rise/roll (breathing ~0.45 Hz + the squeezes),
         upper-body lateral sway, head translation/roll, waist shift; feet planted (two-bone IK), hands ride on her hips (pelvis-relative IK)
  him  : standing behind her (Billyy 'fp_finger_stand' male, one frame, held), turned to her heading, pelvis ~13 u behind hers; his arms are
         placed at runtime (web/src3d/roto_extra3d.js) on her REAL breast surface along the rotoscoped hand paths
  data : RB_GROPE_DATA = per-frame hand paths in each breast's normalised frame (medial reach of the fingers, contact-patch centre / top / bottom,
         in breast half-widths / half-heights), breast translation (medial, down) + affine scale, squeeze period; same 30 fps timeline as her clip
Writes web/assets/anims/fore/fp_grope.js (+ tools/roto/roto3_grope_log.json).  Usage: python -I tools/roto/roto3_grope.py <reiko_breed dir>"""
import sys, os, json, math, site
sys.path.append(site.getusersitepackages())
D = os.path.abspath(sys.argv[1]); sys.argv = [sys.argv[0], D]; sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
import roto_bake as R
from roto_bake import SF, SM, U, ZUP, COM, PEL, SP0, SP1, SP2, NECK, HEAD, LEG, ARM, Pose, qaxis, qmul, qinv, qrot, qnorm, encode, keepset, clipdict, base, lat_of
CLV = {s: 'NPC %s Clavicle [%sClv]' % (s, s) for s in 'LR'}

def crop_blend(x, B):
    """cyclic clip from a series: crop [B:], crossfade its last B samples into the B samples that precede the crop start (mocap_bake.crop_blend)"""
    x = np.asarray(x, float); y = x[B:].copy(); L = len(y)
    for k in range(B):
        w = (k + 1) / (B + 1); w = w * w * (3 - 2 * w); y[L - B + k] = y[L - B + k] * (1 - w) + x[k] * w
    return y

def main():
    MS = json.load(open(os.path.join(D, 'tools', 'roto', 'roto3_measure.json')))['grope']; S = MS['series30']; per = 1 / 1.5; B = 8
    m0 = min(len(v) for v in S.values()); arr = {k: crop_blend(np.asarray(v, float)[:m0], B) for k, v in S.items()}; n = m0 - B   # whole clip, loop-blended
    mean = {k: v.mean(0) for k, v in arr.items()}; arr = {k: v - mean[k] for k, v in arr.items()}
    key = 'licorice_24'; Q, T = base(SF, 'poses', key); Q, T = R.tile(*R.mean_pose(Q, T), n); F = Pose(SF, Q, T)
    lat = lat_of(F); lat[:, 2] = 0; lat /= np.linalg.norm(lat, axis=-1, keepdims=True); fwd = np.cross(ZUP, lat)
    ua = np.linalg.norm(F.p(ARM['L'][0])[0] - F.p(ARM['R'][0])[0]); shw = 1.3 * ua   # video 'shoulder width' = deltoid breadth ~1.3x the upper-arm joint spacing
    # hands on hips: hand position + rotation in the PELVIS frame (from the held pose), re-applied per frame after the body moves
    hp = {s: (qrot(qinv(F.wq(PEL)), F.p(ARM[s][2]) - F.p(PEL)), qmul(qinv(F.wq(PEL)), F.wq(ARM[s][2]))) for s in 'LR'}
    feet = R.fixed(F)
    # video front view: screen x + = her LEFT (= -lat), screen y + = down
    sx = lambda a: -a[:, 0] * shw; sy = lambda a: -a[:, 1] * shw
    wx, wy = sx(arr['waist']), sy(arr['waist'])
    F.translate_world(COM, lat * wx[:, None] + ZUP * (wy - 0.6 / 100 * U)[:, None])   # 6 mm knee slack so the planted legs never lock straight
    lx = (sx(arr['shL']) + sx(arr['shR'])) / 2 - wx; rise = (sy(arr['shL']) + sy(arr['shR'])) / 2 - wy; droll = sy(arr['shL']) - sy(arr['shR'])
    sp2 = F.p(SP2); F.aim(SP0, SP2, sp2 + lat * lx[:, None])                                    # upper body sways laterally with the shoulders
    roll = np.arctan2(droll, ua); F.rotate_world(SP2, qaxis(fwd, -roll))                         # her L shoulder up (+droll) = roll toward her right about her front axis
    for s in 'LR':   # shoulder rise (breathing + reaction): clavicles elevate; the rest (half) by a little spine extension
        c0 = F.p(ARM[s][0]); F.aim(CLV[s], ARM[s][0], c0 + ZUP * (rise * .5)[:, None])
    F.rotate_world(SP1, qaxis(lat, -np.arctan2(rise * .5, 20.0)))                                 # chest lifts (extension about her lateral axis)
    hx = sx(arr['head']) - (sx(arr['shL']) + sx(arr['shR'])) / 2; hy = sy(arr['head']) - (sy(arr['shL']) + sy(arr['shR'])) / 2
    hd0 = F.p(HEAD); F.aim(NECK, HEAD, hd0 + lat * hx[:, None] + ZUP * hy[:, None]); F.rotate_world(HEAD, qaxis(fwd, np.asarray(arr['head_rot'], float)))   # in-plane head roll (front view: + = ccw on screen = toward her left)
    e1 = R.plant(F, feet, legs=True)
    tg = {}
    for s in 'LR':
        p, q = hp[s]; tg[s] = (F.p(PEL) + qrot(F.wq(PEL), np.repeat(p[None], n, 0) if p.ndim == 1 else p), qmul(F.wq(PEL), q))
    # arms akimbo with the elbows OUT in her frontal plane (as in the reference: elbows wide, wrists on the hips) instead of the pose's
    # backward elbows: opens the gap between her arm and waist his forearms pass through (same hand placement, arm swivelled about shoulder->hand)
    e2 = 0
    for s_ in 'LR':
        a_, b_, c_ = ARM[s_]; out_ = lat * (1 if s_ == 'R' else -1); e2 = max(e2, F.ik2(a_, b_, c_, tg[s_][0], tg[s_][1], pole=out_ - fwd * .2))
    keep = keepset(clipdict('poses', key)) | {COM}
    clip_f = encode(F, 30.0, keep, extra_t=(COM,))
    # him: Billyy standing-fingering male, one frame held, turned to her heading, pelvis behind hers
    Qm, Tm = base(SM, 'billyy/fp_finger_stand', 'fp_finger_stand_1_m'); Qm, Tm = Qm[:1], Tm[:1]; M = Pose(SM, np.repeat(Qm, 2, 0), np.repeat(Tm, 2, 0))
    # his upper body squared up (spine / neck / clavicles at the skeleton's rest = upright, shoulders level and full width): the fingering frame has
    # his torso twisted (one shoulder ~7 cm medial of hers), which put that upper arm through her shoulder; legs/pelvis stay as the clip has them
    for nm in (SP0, SP1, SP2, NECK, HEAD, CLV['L'], CLV['R']): M.Q[:, SM['i'][nm]] = SM['q'][SM['i'][nm]]
    M.upd()
    latm = M.p(LEG['R'][0]) - M.p(LEG['L'][0]); latm[:, 2] = 0; latm /= np.linalg.norm(latm, axis=-1, keepdims=True); fm = np.cross(ZUP, latm)
    ff = fwd[:1]; ang = math.atan2(np.cross(fm[0], ff[0])[2], (fm[0] * ff[0]).sum()); M.rotate_world(COM, qaxis(ZUP, np.full(2, ang)))
    back_u = 13.0; want = F.p(PEL).mean(0) - ff[0] * back_u; d = want - M.p(PEL)[0]; d[2] = 0; M.translate_world(COM, np.repeat(d[None], 2, 0))
    clip_m = encode(M, 1.0, keepset(clipdict('billyy/fp_finger_stand', 'fp_finger_stand_1_m')) | {COM}, extra_t=(COM,)); clip_m['dur'] = 2.0
    data = dict(fps=30.0, n=n, period_s=round(per, 4), src='8ae180ab (rotoscoped: optical flow + hand colour mask; motion only)',
                hand={s: np.round(arr['hand' + s] + mean['hand' + s], 4).tolist() for s in 'LR'},   # absolute (mean restored): [medial reach, centre v, top v, bottom v, mean dx]
                breast_t={s: np.round(arr['breast' + s + '_t'], 4).tolist() for s in 'LR'}, breast_s={s: np.round(arr['breast' + s + '_s'], 4).tolist() for s in 'LR'},
                cols=['reach_medial', 'v_centre', 'v_top', 'v_bottom', 'dx_mean'])
    js = ('(function(){var A=window.RB_ANIM3D=window.RB_ANIM3D||{};var S=A.ost=A.ost||{clips:{}};var c=' + json.dumps({'fp_grope_1_f': clip_f, 'fp_grope_1_m': clip_m}, separators=(',', ':'))
          + ';for(var k in c)S.clips[k]=c[k];(window.RB_OST_LOADED=window.RB_OST_LOADED||{})["fp_grope"]=1;window.RB_GROPE_DATA=' + json.dumps(data, separators=(',', ':')) + ';})();\n')
    out = os.path.join(D, 'web', 'assets', 'anims', 'fore', 'fp_grope.js'); open(out, 'w', encoding='utf-8').write('/* generated by tools/roto/roto3_grope.py (motion only from a reference video) */\n' + js)
    log = dict(base_f=key, base_m='billyy/fp_finger_stand:fp_finger_stand_1_m@0', frames=n, period_s=per, ik_err_units=dict(feet=round(e1, 3), hands=round(e2, 3)),
               shoulder_width_units=round(float(shw), 2), reaction_cm=dict(waist_lat_ptp=round(float(np.ptp(wx)) / U * 100, 2), shoulder_rise_ptp=round(float(np.ptp(rise)) / U * 100, 2),
               chest_lat_ptp=round(float(np.ptp(lx)) / U * 100, 2), roll_deg_ptp=round(float(np.degrees(np.ptp(roll))), 2), head_lat_ptp=round(float(np.ptp(hx)) / U * 100, 2), head_roll_deg_ptp=round(float(np.degrees(np.ptp(arr['head_rot']))), 2)),
               his_offset=dict(yaw_deg=round(math.degrees(ang), 1), back_units=back_u), size_kb=round(os.path.getsize(out) / 1e3, 1))
    json.dump(log, open(os.path.join(D, 'tools', 'roto', 'roto3_grope_log.json'), 'w'), indent=1); print(json.dumps(log))

if __name__ == '__main__': main()
