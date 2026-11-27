"""Finger layer for a finished mocap clip: WiLoR hand capture (tools/roto/hands_kp/<id>.npz, from finger_capture.py) -> per-joint curl/spread
angles measured geometrically from the 21 3D hand keypoints (palm frame: wrist, index MCP, pinky MCP), so no MANO/XPMSSE convention mapping is
needed -> confidence-aware fill + smoothing + anatomical clamps -> cropped to the clip's loop exactly like the body (mocap_bake crop_blend) ->
written as the 30 finger tracks of the clip: local = rest * spread(about the hand's palm normal) * curl(about the joint's flex axis), the same
rig RBCONTACT.fingerRig uses in the game (flex axis = bone direction x palm normal). Body, arms and wrists are not touched.
Optional manual corrections (the poser): tools/roto/finger_overrides/<id>.json = {"L"|"R": {"<finger 0-4>_<joint 0-2>": [[t_s, add_curl_rad], ...]}}.
Usage: <torch venv> python tools/roto/finger_apply.py <reiko_breed dir> <id> [--game]"""
import sys, os, json, math
D = os.path.abspath(sys.argv[1]); ID = sys.argv[2]; GAME = '--game' in sys.argv; sys.argv = [sys.argv[0], D]
sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
from scipy.signal import savgol_filter
import roto_bake as R
from mocap_lib import q2m, m2q, rodrigues
SF = R.SF
CH = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16], [17, 18, 19, 20]]   # thumb, index, middle, ring, pinky (OpenPose order)
RELAX_SP = np.array([-.22, -.45, -.22, .08, .30])   # relaxed spread (raw): fingers loosely together = mean of the visible captured hands
RELAX = np.array([[.25, .28, .15], [.45, .50, .25], [.50, .55, .28], [.55, .60, .30], [.60, .62, .32]])   # Animator 2026-11-27: knuckle-led cascade, fingers lightly touching (tuned on the bind-tc hand)   # fallback when no hand is seen: natural relaxed hand, rad from FLAT
CURL_LIM = [[(-.3, .9), (-.2, 1.0), (-.2, 1.2)]] + [[(-.35, 1.6), (0, 1.9), (-.1, 1.4)]] * 4   # thumb CMC/MCP/IP; fingers MCP/PIP/DIP
SPREAD_LIM = [(-.6, .9), (-.65, .2), (-.4, .25), (-.2, .5), (-.15, .7)]   # raw, + = toward the thumb; relaxed fingers converge (index -, ring/pinky +)
def nrm(v): return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)
def sang(a, b, side):
    """angle a->b, positive when b turns toward `side` (perpendicular part)"""
    a = nrm(a); b = nrm(b); ang = np.arctan2(np.linalg.norm(np.cross(a, b), axis=-1), (a * b).sum(-1))
    perp = b - a * (a * b).sum(-1, keepdims=True); return ang * np.sign((perp * side).sum(-1) + 1e-12)

def angles(K):
    """K [n,21,3] one hand -> curl [n,5,3], spread [n,5]"""
    w = K[:, 0]; nr = nrm(np.cross(K[:, 5] - w, K[:, 17] - w))
    # palm side = the side the PIP joints bend to (they only flex): fixes the normal's sign for either hand/chirality
    pip = np.concatenate([sang(K[:, c[1]] - K[:, c[0]], K[:, c[2]] - K[:, c[1]], nr) for c in CH[1:]])
    palm = nr * (1 if np.median(pip) >= 0 else -1)
    thumb_side = nrm(K[:, 2] - K[:, 9])
    curl = np.zeros((len(K), 5, 3)); spread = np.zeros((len(K), 5))
    for f, c in enumerate(CH):
        m = nrm(K[:, c[0]] - w); s0 = K[:, c[1]] - K[:, c[0]]; s1 = K[:, c[2]] - K[:, c[1]]; s2 = K[:, c[3]] - K[:, c[2]]
        lat = nrm(np.cross(palm, m)); lat = lat * np.sign((lat * thumb_side).sum(-1, keepdims=True) + 1e-12)   # lateral axis pointing to the thumb side
        s0p = s0 - palm * (s0 * palm).sum(-1, keepdims=True)   # proximal segment in the palm plane
        spread[:, f] = np.arctan2((s0p * lat).sum(-1), (s0p * m).sum(-1))
        curl[:, f, 0] = sang(s0p, s0, palm)   # MCP/CMC flex = elevation out of the palm plane (spread is measured separately in it)
        if f:
            curl[:, f, 1] = sang(s0, s1, palm); curl[:, f, 2] = sang(s1, s2, palm)
        else:   # thumb MCP/IP: its flex plane is not the palm's -> unsigned bend angle (the thumb does not hyperextend much)
            curl[:, 0, 1] = np.abs(sang(s0, s1, palm)); curl[:, 0, 2] = np.abs(sang(s1, s2, palm))
    return curl, spread

def naturalize(cu, sp):
    """anatomical hand constraint, applied to EVERY frame (captured, interpolated or fallback), in true angles from a flat hand:
    joint ranges; DIP tied to PIP (shared flexor tendon: DIP ~ 2/3 PIP); adjacent fingers' curl coupled (middle/ring/pinky share tendons, index
    freer); spread bounded between neighbours (no crossing) and converging as the fingers curl; thumb flexes along when the hand closes.
    Returns new (cu, sp) and the fraction of frames it had to change by > 0.1 rad."""
    cu = cu.copy(); sp = sp.copy(); c0 = cu.copy(); s0 = sp.copy()
    NAT = [[(-.15, .8), (0, .9), (0, 1.1)]] + [[(-.2, 1.5), (0, 1.75), (0, 1.25)]] * 4
    for f in range(5):
        for j in range(3): cu[:, f, j] = np.clip(cu[:, f, j], *NAT[f][j])
    for f in range(1, 5):   # DIP within +-0.3 of 2/3 PIP
        tgt = .67 * cu[:, f, 1]; cu[:, f, 2] = np.clip(cu[:, f, 2], tgt - .3, tgt + .3)
    LIM_ADJ = {(1, 2): .9, (2, 3): .55, (3, 4): .6}   # max curl difference between neighbours per joint (index more independent)
    for _ in range(4):
        for (a, b), m in LIM_ADJ.items():
            d = cu[:, a, :2] - cu[:, b, :2]; ex = np.sign(d) * np.maximum(0, np.abs(d) - m); cu[:, a, :2] -= ex / 2; cu[:, b, :2] += ex / 2
    close = np.clip(cu[:, 1:, :2].mean((1, 2)) / 1.2, 0, 1)   # 0 open .. 1 fist
    cu[:, 0, 1] = np.maximum(cu[:, 0, 1], .5 * close); cu[:, 0, 2] = np.maximum(cu[:, 0, 2], .4 * close)   # thumb wraps with a closing hand
    conv = .7 * np.clip(cu[:, 1:, 0] / 1.3, 0, 1)   # spread converges (toward the relaxed, together spread) as the knuckles flex
    sp[:, 1:] = sp[:, 1:] * (1 - conv) + RELAX_SP[None, 1:] * conv
    for _ in range(4):   # neighbours' spread within 0.35 of each other: fingers never cross / splay apart unnaturally
        for a in (1, 2, 3):
            g = RELAX_SP[a] - RELAX_SP[a + 1]; d = sp[:, a] - sp[:, a + 1] - g; ex = np.sign(d) * np.maximum(0, np.abs(d) - .3);   # deviation from the natural gap sp[:, a] -= ex / 2; sp[:, a + 1] += ex / 2
    for f in range(5): sp[:, f] = np.clip(sp[:, f], *SPREAD_LIM[f])
    chg = (np.abs(cu - c0).max((1, 2)) > .1) | (np.abs(sp - s0).max(1) > .1)
    return cu, sp, float(chg.mean())

def crop_blend1(X, i, j, B):
    X2 = X[i:j].copy(); L = len(X2)
    for k in range(B):
        w = (k + 1) / (B + 1); w = w * w * (3 - 2 * w); t = L - B + k; X2[t] = X2[t] * (1 - w) + X[i - B + k] * w
    return X2

def fill_smooth(A, ok, fps):
    """A [n, ...] with frames ok[n]: gaps interpolated (cyclic), long gaps eased to RELAX-like default by the caller, then SG smoothing"""
    n = len(A); A = A.reshape(n, -1).copy(); t = np.arange(n)
    if ok.sum() < 2: return None
    for k in range(A.shape[1]): A[~ok, k] = np.interp(t[~ok], t[ok], A[ok, k], period=n)
    win = max(5, int(fps * .17) | 1); return savgol_filter(A, win, 2, axis=0, mode='wrap')

def rig():
    """per side/finger/joint: rest local quat, local flex axis, local spread axis (palm normal) from the skeleton rest pose"""
    P = R.Pose(SF, SF['q'][None].copy(), SF['t'][None].copy()); out = {}
    for s in 'LR':
        hq = q2m(P.wq('NPC %s Hand [%sHnd]' % (s, s))[0]); nW = hq @ np.array([0, -1, 0.])
        thumb_side = P.p('NPC %s Finger01 [%sF01]' % (s, s))[0] - P.p('NPC %s Finger20 [%sF20]' % (s, s))[0]   # same reference as the capture (thumb MCP - middle MCP)
        for f in range(5):
            names = ['NPC %s Finger%d%d [%sF%d%d]' % (s, f, j, s, f, j) for j in range(3)]; dprev = None
            for j, b in enumerate(names):
                p0 = P.p(b)[0]; d = nrm(P.p(names[j + 1])[0] - p0) if j < 2 else dprev; dprev = d
                Bq = q2m(P.wq(b)[0]); ax = nrm(np.cross(d, nW))
                sgn = 1.0 if np.cross(nW, d) @ thumb_side >= 0 else -1.0   # +spread must move the finger toward the thumb on BOTH (mirrored) hands
                out[(s, f, j)] = (SF['q'][SF['i'][b]].copy(), Bq.T @ ax, Bq.T @ nW * sgn, b)
    return out

# MANO flat hand (identity joint rotations, from WiLoR's MANO layer; tools/roto/mano_flat_joints.npy): its keypoint geometry does not read as
# zero curl/spread with this measurement (joint centres are not collinear, metacarpals fan) -> measured once and subtracted
_FJ = np.load(os.path.join(D, 'tools', 'roto', 'mano_flat_joints.npy'))[None]
NEU_CU, NEU_SP = (x[0] for x in angles(_FJ))
# her bind hand is NOT flat (pre-curled ~0.55 rad MCP): its true curl/spread (same measurement, minus the flat bias; keypoints from the game mesh,
# tools/bind_hand_kp.js -> tools/roto/bind_hand_kp.json) is subtracted at the end, so rest * delta reproduces the captured hand
_BK = json.load(open(os.path.join(D, 'tools', 'roto', 'bind_hand_kp.json')))
BIND = {s: tuple(x[0] for x in angles(np.array(_BK[s], float)[None])) for s in 'LR'}
# (no flat-bias subtraction here: that bias belongs to MANO's joint placement; her bone heads lie on the finger axis -> raw = true)

def qslerp(a, b, w):
    """per-frame slerp of quaternion arrays [n,4] (xyzw) by w [n]"""
    a = np.broadcast_to(a, b.shape).copy(); d = (a * b).sum(1); b = b * np.sign(d + 1e-12)[:, None]; d = np.abs(d).clip(0, 1)
    th = np.arccos(d); sn = np.sin(th); w = np.asarray(w, float)
    k0 = np.where(sn > 1e-6, np.sin((1 - w) * th) / np.maximum(sn, 1e-9), 1 - w); k1 = np.where(sn > 1e-6, np.sin(w * th) / np.maximum(sn, 1e-9), w)
    q = a * k0[:, None] + b * k1[:, None]; return q / np.linalg.norm(q, axis=1, keepdims=True)
def qmul_axis(q, ax, ang):
    """q * axis-angle(ax local, ang [n])"""
    h = ang / 2; r = np.concatenate([ax[None] * np.sin(h)[:, None], np.cos(h)[:, None]], 1); x1, y1, z1, w1 = q.T; x2, y2, z2, w2 = r.T
    return np.stack([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2], 1)
CAP_GAIN = float(os.environ.get('FINGER_CAP_GAIN', '.6')); CAP_MAX = float(os.environ.get('FINGER_CAP_MAX', '.4'))
_HP = {k: json.load(open(os.path.join(D, 'tools', 'roto', 'hand_pose_%s.json' % k)))['q'] for k in ('hang', 'raised')}
def fallback_hands(clip, s, n, fps):
    """context hand for frames the tracker can't see: authored HANG (forearm down) <-> RAISED (forearm level/up) by forearm pitch,
    plus 'lag' (0..1): fingers trail/open slightly on fast wrist motion (low-pass of the hand's angular speed) so they never look frozen"""
    Q = np.repeat(np.asarray(SF['q'], float)[None], n, 0)
    for b, v in clip['q'].items():
        if b in SF['i']: a = np.array(v, float).reshape(-1, 4) / 1e4; Q[:, SF['i'][b]] = a[np.arange(n) % len(a)]
    P = R.Pose(SF, Q, np.repeat(np.asarray(SF['t'], float)[None], n, 0))
    fa = P.p('NPC %s Forearm [%sLar]' % (s, s)); hd = P.p('NPC %s Hand [%sHnd]' % (s, s)); dz = nrm(hd - fa)[:, 2]
    w = np.clip((dz + .6) / .9, 0, 1); w = w * w * (3 - 2 * w); w = savgol_filter(w, max(5, int(fps * .3) | 1), 2, mode='wrap').clip(0, 1)
    hq = P.wq('NPC %s Hand [%sHnd]' % (s, s)); v = np.degrees(2 * np.arccos(np.clip(np.abs((hq * np.roll(hq, 1, 0)).sum(1)), 0, 1))) * fps
    o = np.clip(v / 400.0, 0, 1); lag = np.zeros(n); a_ = 1 - math.exp(-1 / (fps * .15))
    for _ in range(2):
        for t in range(n): lag[t] = lag[t - 1] + a_ * (o[t] - lag[t - 1])
    out = {}
    for b in _HP['hang']:
        if not b.startswith('NPC %s ' % s): continue
        h0 = np.array(_HP['hang'][b], float) / 1e4; r0 = np.array(_HP['raised'][b], float) / 1e4
        out[b] = qslerp(np.repeat(h0[None], n, 0), np.repeat(r0[None], n, 0), w)
    return {'q': out, 'lag': lag}

def main():
    cp = os.path.join(D, 'tools', 'roto', 'mocap_clips', ID + '.json'); C = json.load(open(cp)); clip, log = C['clip'], C['log']
    H = np.load(os.path.join(D, 'tools', 'roto', 'hands_kp', ID + '.npz')); K3 = H['kp3d']; conf = H['conf'].copy(); fps = float(log['fps'])
    wh = np.load(os.path.join(D, 'tools', 'roto', 'mocap_kp', ID + '.npz'))['wh']; k2 = H['kp2d']; mg = 4
    inside = ((k2[..., 0] > mg) & (k2[..., 0] < wh[0] - mg) & (k2[..., 1] > mg) & (k2[..., 1] < wh[1] - mg)).all(-1)   # whole hand in frame
    size = np.linalg.norm(k2.max(-2) - k2.min(-2), axis=-1)   # hand box diagonal (px)
    conf = conf * inside * (size >= 55)   # a hand cut by the frame edge, behind clothes or a few dozen px wide is a guess: treated as unseen
    i, j = log['loop']; B = int(round(fps * .5)); n = clip['n']
    res = {}
    for si, s in enumerate('LR'):
        cu, sp = angles(K3[:, si].astype(float)); cu = cu - NEU_CU   # curl relative to MANO's flat hand (joint-placement bias); spread stays raw = angle to the finger's own metacarpal ray (same measure on her bind)
        # anatomical plausibility: joints bent far past their range (backwards fingertips, >1.6 rad knuckles) mean a failed fit, not a pose
        over = sum(np.maximum(0, np.maximum(CURL_LIM[f][jj][0] - cu[:, f, jj], cu[:, f, jj] - CURL_LIM[f][jj][1])) for f in range(5) for jj in range(3))
        over = over + sum(np.maximum(0, np.maximum(SPREAD_LIM[f][0] - sp[:, f], sp[:, f] - SPREAD_LIM[f][1])) for f in range(5))
        ok = (conf[:, si] > .3) & (over < .6)
        X = np.concatenate([cu.reshape(len(cu), -1), sp], 1); X[~ok] = np.nan
        Xs = fill_smooth(np.nan_to_num(X), ok, fps)
        if Xs is None: print(s, 'no hand seen -> relaxed'); Xs = np.tile(np.concatenate([RELAX.reshape(-1), RELAX_SP]), (len(X), 1))
        # away from any valid detection: eased to the relaxed hand from 0.15 s, fully by 0.4 s: ease toward the relaxed hand instead of holding a stale guess
        dist = np.array([np.min(np.abs((np.where(ok)[0] - t + len(ok) // 2) % len(ok) - len(ok) // 2)) if ok.any() else 1e9 for t in range(len(ok))])
        wr = np.clip((dist / fps - .15) / .25, 0, 1)[:, None]; wr = wr * wr * (3 - 2 * wr)   # weight of the authored fallback hand (blended in quaternion space below)
        if not ok.any(): wr = np.ones((len(ok), 1))
        wrc = np.clip(crop_blend1(wr, i, j, B)[:n, 0], 0, 1)
        Xc = crop_blend1(Xs, i, j, B)[:n]
        cu = Xc[:, :15].reshape(n, 5, 3); sp = Xc[:, 15:]
        for f in range(5):
            sp[:, f] = np.clip(sp[:, f], *SPREAD_LIM[f])
            for jj in range(3): cu[:, f, jj] = np.clip(cu[:, f, jj], *CURL_LIM[f][jj])
        cu, sp, nchg = naturalize(cu, sp); res[s] = (cu, sp, float(ok.mean()), wrc); print(s, 'naturalize changed %.0f%% of frames' % (100 * nchg))
    ov = os.path.join(D, 'tools', 'roto', 'finger_overrides', ID + '.json')
    if os.path.exists(ov):   # poser corrections: keyframed curl offsets (rad), linearly interpolated, cyclic
        O = json.load(open(ov)); tt = np.arange(n) / fps
        for s, keys in O.items():
            for fj, kf in keys.items():
                f, jj = map(int, fj.split('_')); kf = sorted(kf); ts = np.array([k[0] for k in kf]); vs = np.array([k[1] for k in kf])
                res[s][0][:, f, jj] += np.interp(tt, ts, vs, period=n / fps)
    RG = rig()
    for s in 'LR':
        cu, sp, _, wrc = res[s]; FB = fallback_hands(clip, s, n, fps)
        if os.environ.get('FINGER_TEST') == 'flat': cu = cu * 0; sp = sp * 0   # mapping test: a true flat hand must render flat
        if os.environ.get('FINGER_TEST') == 'relax': cu = cu * 0 + RELAX[None]; sp = sp * 0 + RELAX_SP[None]
        cu_raw, sp_raw = cu.copy(), sp.copy()   # true-space angles (for the relative mode)
        cu = cu - BIND[s][0][None]; sp = sp - BIND[s][1][None]
        if os.environ.get('FINGER_POSE'):   # tuning: constant pose given directly as deltas on her bind hand ("15 curls;5 spreads")
            c_, s_ = os.environ['FINGER_POSE'].split(';'); cu = cu * 0 + np.array([float(x) for x in c_.split(',')]).reshape(5, 3)[None]; sp = sp * 0 + np.array([float(x) for x in s_.split(',')])[None]   # true pose -> delta on her pre-curled bind hand
        for f in range(5):
            for jj in range(3):
                q0, axL, nL, b = RG[(s, f, jj)]
                M = q2m(q0)[None] @ (rodrigues(nL[None] * sp[:, f:f + 1]) if jj == 0 else np.eye(3)[None]) @ rodrigues(axL[None] * cu[:, f, jj:jj + 1])
                q = m2q(M); q = q * np.sign(q[:, 3:4] + 1e-12)
                if os.environ.get('FINGER_FALLBACK', 'authored') == 'authored' and not os.environ.get('FINGER_POSE') and not os.environ.get('FINGER_TEST'):
                    # captured motion RELATIVE to her authored hand: the capture's absolute curl is biased (captured hands read as claws, claw
                    # 22-25 deg vs bind 2-4); its frame-to-frame changes (gestures, curling, opening) are real -> applied around the context hand
                    sw_ = (wrc < .5); cu0 = np.median(cu_raw[sw_, f, jj]) if sw_.any() else 0.0; sp0 = np.median(sp_raw[sw_, f]) if (sw_.any() and jj == 0) else 0.0
                    qc = FB['q'][b]
                    # small phone-video hands: WiLoR deltas are noisy -> keep the broad gestures only (0.3 s low-pass, x CAP_GAIN, +-CAP_MAX rad)
                    dcu = np.clip(CAP_GAIN * savgol_filter(cu_raw[:, f, jj] - cu0, max(5, int(fps * .3) | 1), 2, mode='wrap'), -CAP_MAX, CAP_MAX)
                    if jj == 0: qc = qmul_axis(qc, nL, np.clip(CAP_GAIN * savgol_filter(sp_raw[:, f] - sp0, max(5, int(fps * .3) | 1), 2, mode='wrap'), -CAP_MAX / 2, CAP_MAX / 2))
                    qc = qmul_axis(qc, axL, dcu)
                    q = qslerp(FB['q'][b], qc, 1 - wrc)   # captured (relative) where seen, authored context hand elsewhere (eased)
                    if f and jj < 2: q = qmul_axis(q, axL, -FB['lag'] * (.22 if jj == 0 else .12))   # fingers trail/open slightly on fast wrist motion
                q = q * np.sign(q[:, 3:4] + 1e-12)
                clip['q'][b] = [int(round(x * 1e4)) for x in q.reshape(-1)]
    for b_, v_ in json.load(open(os.path.join(D, 'tools', 'roto', 'finger_tc_bind.json')))['tc'].items(): clip.setdefault('tc', {})[b_] = v_   # bind finger offsets (QA-006)
    log['fingers'] = {s: dict(seen=round(res[s][2], 2), curl_mean=np.round(res[s][0].mean((0,)), 2).tolist()) for s in 'LR'}
    json.dump(C, open(cp, 'w'), separators=(',', ':'))
    print(ID, 'fingers applied; hand seen L %.2f R %.2f' % (res['L'][2], res['R'][2]))
    if GAME: print('--game ignored: the game file is written only by tools/anim/promote.py after QA')

if __name__ == '__main__': main()
