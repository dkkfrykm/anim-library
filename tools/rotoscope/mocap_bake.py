"""Daily-life dances from body-model mocap -> XPMSSE clips (replaces the 2D-lift dance_bake.py output; same ids / API / JSON format).
Pipeline (see tools/roto/MOCAP_NOTES in the report):
  1. NLF (Neural Localizer Fields v0.3.2, torchscript) per-frame SMPL-X fit on the video (scratch venv; motion only, no pixels kept)
     -> tools/roto/mocap_kp/<id>.npz : SMPL-X axis-angle pose, joints3d, betas, 2D joints, uncertainties
  2. ground plane + heading from the fit, loop window, target smoothing
  3. retarget joint ROTATIONS onto Reiko's XPMSSE skeleton through a T-pose built from this subject's SMPL rest offsets
  4. whole-clip optimisation (torch, CPU): rotation data + anatomical swing/twist limits per bone + self-collision (arm/hand skin points vs
     her torso/bust/belly/hips/thighs/head/other-arm skin, current RB_LOOK preset: tools/roto/dance_body_skin.json) + ground + foot contact/skate
     + cyclic temporal acceleration
  5. forearm twist split over ForearmTwist1/2, encode, metrics -> web/assets/anims/dance3d.js + tools/roto/mocap_bake_log.json
Usage: <venv with torch+numpy+scipy> python tools/roto/mocap_bake.py <reiko_breed dir> [ids comma list]"""
import sys, os, json, math, time
D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.'); ONLY = sys.argv[2].split(',') if len(sys.argv) > 2 else None
sys.argv = [sys.argv[0], D]; sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
from scipy.signal import savgol_filter
import roto_bake as R
import mocap_lib as M
from mocap_lib import N, SMPL_OF, SMPL_PARENT, MCAM, MCAN, U, rodrigues, m2q, q2m, nrm, frame, rot_log, slerp_m

SF = R.SF; A = os.path.join(D, 'web', 'assets'); LOG = {}
# fit source: NLF per-frame fits (tools/roto/mocap_kp) or GVHMR world-grounded fits (MOCAP_SRC=gvhmr -> tools/roto/mocap_kp_gvhmr);
# a non-default source only writes its per-clip results (tools/roto/mocap_clips_<src>/), never the game file
SRC = os.environ.get('MOCAP_SRC', 'nlf'); KP_DIR = 'mocap_kp' if SRC == 'nlf' else 'mocap_kp_' + SRC; CLIP_DIR = 'mocap_clips' if SRC == 'nlf' else 'mocap_clips_' + SRC
DANCES = [dict(id='dance_1', name='Pose & Attitude', src='0911f705'), dict(id='dance_2', name='Hair-Flip Sway', src='2225ca46'),
          dict(id='dance_3', name='Frame the Face', src='4357b869'), dict(id='dance_4', name='Crossed-Arm Groove', src='461461c2'),
          dict(id='dance_5', name='Hip Shimmy', src='5deb6f48'),
          dict(id='dance_7', name='Wave & Sway', src='5691b854'), dict(id='dance_8', name='Sunset Turn', src='81cd9e9a'), dict(id='dance_9', name='Hand Groove', src='b3dd0685'),
          dict(id='dance_10', name='Frame & Pop', src='2b557dd8'), dict(id='dance_11', name='Swing & Flick', src='e97747d0'),
          dict(id='dance_12', name='Lean & Point', src='ee6db89f'), dict(id='dance_13', name='Bounce Pose', src='889fdee6'),
          dict(id='dance_14', name='Strut & Shrug', src='3a59a852'), dict(id='dance_15', name='Clap & Glide', src='5845a7df'),
          dict(id='dance_16', name='Step & Bounce', src='283e6f97')]
# solo rotoscope clips redone the same way -> tools/roto/roto_mocap.json (roto_bake.py uses them instead of its optical-flow versions)
ROTO_SOLO = [dict(id='roto_twerk', name='Twerk', src='8e8ad85f', lo=.3), dict(id='roto_idle_sway', name='Idle sway', src='3e86b33c', lo=.4)]
OPT = ['COM', 'SP0', 'SP1', 'SP2', 'NECK', 'HEAD'] + [s + k for s in 'LR' for k in ('CLV', 'UA', 'FA', 'HD', 'TH', 'CF', 'FT')]
APAR = {'COM': None, 'SP0': 'COM', 'SP1': 'SP0', 'SP2': 'SP1', 'NECK': 'SP2', 'HEAD': 'NECK'}
for s in 'LR': APAR.update({s + 'CLV': 'SP2', s + 'UA': s + 'CLV', s + 'FA': s + 'UA', s + 'HD': s + 'FA', s + 'TH': 'COM', s + 'CF': s + 'TH', s + 'FT': s + 'CF'})
X, Y, Z = np.eye(3)
# anatomical limits on the T-pose-relative local rotation (Skyrim axes): bone axis d, swing axes a1/a2 (rotation-vector components, deg), twist (deg)
def LIM():
    L = {}
    for k in ('SP0', 'SP1', 'SP2'): L[k] = (Z, -X, Y, (-22, 32), (-20, 20), (-25, 25))
    L['NECK'] = (Z, -X, Y, (-35, 40), (-30, 30), (-45, 45)); L['HEAD'] = (Z, -X, Y, (-35, 35), (-28, 28), (-50, 50))
    for s, g in (('L', 1), ('R', -1)):
        d = -X * g
        L[s + 'CLV'] = (d, Y * g, -Z * g, (-12, 30), (-20, 25), (-20, 20))
        L[s + 'UA'] = (d, -Z * g, -Y * g, (-50, 140), (-110, 100), (-95, 95))
        L[s + 'FA'] = (d, -Z * g, Y, (-5, 150), (-15, 15), (-90, 90))
        L[s + 'HD'] = (d, -Y * g, -Z * g, (-65, 75), (-30, 30), (-45, 45))
        L[s + 'TH'] = (-Z, X, Y * g, (-25, 125), (-30, 50), (-45, 45))
        L[s + 'CF'] = (-Z, -X, Y, (-6, 150), (-8, 8), (-25, 25))
        L[s + 'FT'] = (Y, -X, Z, (-30, 50), (-25, 25), (-25, 25))
    return L
LIMITS = LIM()

def sgf(x, win, order=2):
    win = int(win) | 1
    if len(x) <= win: win = (len(x) - 1) | 1 if len(x) > 3 else 3
    return savgol_filter(x, max(win, order + 2 | 1), order, axis=0, mode='wrap') if len(x) > order + 2 else x
def smooth_rot(Rm, win):
    q = m2q(Rm)
    for k in range(1, len(q)):
        if (q[k] * q[k - 1]).sum() < 0: q[k] = -q[k]
    # cyclic smoothing: after the hemisphere chain the last frame can sit on the OPPOSITE sign of frame 0 (the loop closes on -q); a plain
    # mode='wrap' filter then averages q with ~-q across the seam -> near-zero quaternions -> 100-170 deg pops at the wrap (dance_2 thighs).
    # Pad with sign-corrected copies of the other end instead and filter the padded track.
    n = len(q); w = min(int(win) | 1, n - 1); sg = 1.0 if (q[-1] * q[0]).sum() >= 0 else -1.0
    if n > 4 and w >= 3:
        qp = np.concatenate([sg * q[n - w:], q, sg * q[:w]], 0); q = savgol_filter(qp, max(w, 3), 2, axis=0, mode='interp')[w:w + n]
    return q2m(q / np.linalg.norm(q, axis=-1, keepdims=True))

# ---------------- 1-2: fit -> ground frame, loop, targets ----------------
def load_fit(did):
    d = np.load(os.path.join(D, 'tools', 'roto', KP_DIR, did + '.npz')); pose = d['pose']; J = d['joints3d'][:, :22] * U / 1000   # NLF joints are mm -> m -> units
    ok = ~np.isnan(pose).any(1)
    if not ok.all():  # rare missed detections: nearest valid frame
        idx = np.arange(len(pose)); src = np.array([idx[ok][np.argmin(np.abs(idx[ok] - i))] for i in idx]); pose = pose[src]; J = J[src]
    G, _ = M.smpl_globals(pose[:, :66]); unc = d['juncert'][:, :22] if d['juncert'].ndim == 2 and d['juncert'].shape[1] >= 22 else np.zeros((len(pose), 22))
    J55 = d['joints3d'] * U / 1000
    if not ok.all(): J55 = J55[src]
    return dict(G=G, J=J, J55=J55, pose=pose, fps=float(d['fps']), unc=unc, j2=d['joints2d'][:, :22], wh=d['wh'])
def ground_frame(F):
    """camera -> ground frame: Z = floor normal (plane through the planted feet), Y = her median facing; feet out of shot -> body-up prior"""
    Jc = np.einsum('ij,ntj->nti', MCAM, F['J']); Gs = np.einsum('ij,ntjk,lk->ntil', MCAM, F['G'], MCAN)   # Skyrim axes, camera origin
    up_body = nrm(np.median(nrm(Jc[:, 12] - Jc[:, 0]), 0))
    feet = np.concatenate([Jc[:, 10], Jc[:, 11], Jc[:, 7], Jc[:, 8]]); unc_feet = np.concatenate([F['unc'][:, 10], F['unc'][:, 11], F['unc'][:, 7], F['unc'][:, 8]])
    h_img = float(F['wh'][1]); j2 = F['j2']; feet_ok = bool((((j2[:, [7, 8], 1] < h_img * .995) & (j2[:, [7, 8], 1] > 0)).all(1)).mean() > .6)   # ankles inside the frame most of the time
    nz = up_body
    if feet_ok:  # low points per frame -> plane by iterative reweighted least squares, normal near body-up
        low = np.stack([Jc[:, 10], Jc[:, 11]], 1); h = (low @ up_body); lo = low[np.arange(len(low)), np.argmin(h, 1)]
        for _ in range(5):
            c = lo.mean(0); u, s, vt = np.linalg.svd(lo - c); n_ = vt[2] * np.sign(vt[2] @ up_body)
            spread = s[1] / np.sqrt(len(lo)) / U * 100   # cm: feet that barely move (standing dances) span no plane -> its tilt is noise
            if spread >= 8 and np.degrees(np.arccos(np.clip(n_ @ up_body, -1, 1))) < 20: nz = n_
            else: nz = up_body
            r = np.abs((lo - c) @ nz); keep = r < np.percentile(r, 80) + 1e-6; lo = lo[keep] if keep.sum() > 10 else lo
    fwd = np.einsum('nij,j->ni', Gs[:, 0], Y); fwd = fwd - np.outer(fwd @ nz, nz); fh = nrm(np.median(nrm(fwd), 0))
    Rg = np.stack([np.cross(fh, nz), fh, nz])   # rows: new X, Y, Z
    Jg = np.einsum('ij,ntj->nti', Rg, Jc); Gg = np.einsum('ij,ntjk->ntik', Rg, Gs)
    F['J55g'] = np.einsum('ij,ntj->nti', Rg @ MCAM, F['J55'])   # all SMPL-X joints (hand knuckles for the relative hand targets)
    floor = np.percentile(np.minimum(Jg[:, 10, 2], Jg[:, 11, 2]), 5) - 2.0   # foot joint sits ~3 cm above the sole
    Jg[..., 2] -= floor; F['J55g'][..., 2] -= floor
    return Jg, Gg, dict(feet_tracked=bool(feet_ok), tilt_deg=round(float(np.degrees(np.arccos(np.clip(nz @ up_body, -1, 1)))), 1))
def repair_spikes(Gg, fps, thr_deg=40.0, info=None):
    """capture spikes (NLF briefly swaps/loses a limb: forearm direction jumps up to 176 deg in one frame): per joint, frames whose global
    rotation is > thr from a robust local reference (quaternion component median over +-0.15 s) are flagged and rebuilt by slerp between
    the nearest good frames. Real motion is never that far from its own 0.3 s median; the flagged share is logged."""
    n = len(Gg); h = max(2, int(fps * .15)); out = Gg.copy()
    for k in range(Gg.shape[1]):
        q = m2q(Gg[:, k]); ref = q[0]
        for t in range(n):
            if q[t] @ ref < 0: q[t] = -q[t]
            ref = q[t]
        med = np.stack([np.median(q[max(0, t - h):t + h + 1], 0) for t in range(n)]); med /= np.linalg.norm(med, axis=1, keepdims=True)
        dev = np.degrees(2 * np.arccos(np.clip(np.abs((q * med).sum(1)), 0, 1))); bad = dev > thr_deg
        if not bad.any() or bad.all(): continue
        good = np.where(~bad)[0]
        for t in np.where(bad)[0]:
            a = good[good < t]; b = good[good > t]
            if not len(a): out[t, k] = Gg[b[0], k]; continue
            if not len(b): out[t, k] = Gg[a[-1], k]; continue
            a, b = a[-1], b[0]; out[t, k] = slerp_m(Gg[a, k], Gg[b, k], (t - a) / (b - a))
        if info is not None: info[int(k)] = int(bad.sum())
    return out

LOOP_ROT_W = float(os.environ.get('MOCAP_LOOP_ROT_W', '150'))
def loop_window(Jg, Gg, fps, lo_frac=.6, B=12):
    c = Jg[:, 0:1]; X_ = (Jg - c).reshape(len(Jg), -1); V = np.gradient(X_, axis=0); n = len(Jg); best = (1e18, B, n)
    hd = np.arctan2(-Gg[:, 0, 0, 1], Gg[:, 0, 1, 1])
    LJ = [1, 2, 4, 5, 16, 17, 18, 19, 20, 21]   # limb segment rotations: the seam must also match in twist (positions alone allowed 120-150 deg rotation seams)
    for i in range(B, max(B + 1, n // 3)):
        tr = np.einsum('jkab,kab->jk', Gg[:, LJ], Gg[i, LJ]); rot = np.arccos(np.clip((tr - 1) / 2, -1, 1)); rcost = (rot ** 2).sum(1)
        for j in range(i + int(lo_frac * n), n + 1):
            jj = min(j, n - 1); dh = (hd[i] - hd[jj] + np.pi) % (2 * np.pi) - np.pi
            cost = ((X_[i] - X_[jj]) ** 2).sum() + 6 * ((V[i] - V[jj]) ** 2).sum() + 400 * dh * dh + LOOP_ROT_W * rcost[jj]
            if cost < best[0]: best = (cost, i, j)
    return best[1], best[2]
def crop_blend(Jg, Gg, i, j, B):
    J2 = Jg[i:j].copy(); G2 = Gg[i:j].copy(); L = len(J2)
    for k in range(B):
        w = (k + 1) / (B + 1); w = w * w * (3 - 2 * w); t = L - B + k
        J2[t] = J2[t] * (1 - w) + Jg[i - B + k] * w; G2[t] = slerp_m(G2[t], Gg[i - B + k], w)
    return J2, G2

# ---------------- 3: retarget targets ----------------
def _hinge_parts(Wt, WTq, par, ch):
    """swing components (a1 = hinge flex, a2 = off-hinge) and twist of child `ch` relative to `par` in the limit frame"""
    d, a1, a2 = LIMITS[ch][:3]; Fp, Fc = _frames(ch, WTq); Rr = np.swapaxes(Wt[par] @ Fp.T, -1, -2) @ (Wt[ch] @ Fc.T); q = m2q(Rr)
    tw = 2 * np.arctan2(q[:, :3] @ d, q[:, 3]); sv = rot_log(Rr @ rodrigues(-d[None] * tw[:, None])); return sv @ a1, sv @ a2, d
LFRAME = {}   # limit key -> (parent frame, child frame) the limit is measured in; default = this clip's retarget T-pose (WTq)
def _rest_world():
    P = R.Pose(SF, SF['q'][None].copy(), SF['t'][None].copy()); return {k: q2m(P.wq(N[k])[0]) for k in OPT}
REST_W = None
def anat_limits(WTq):
    """elbows/knees are measured exactly like the handmade clips (Animator's check, 594 clips, off-hinge p95 <= 0.8 deg): rotation relative to
    the skeleton REST local, hinge = local X (forearm flexes about -X, calf about +X), bone axis = local Z (twist), side-bend = local Y.
    Done by measuring these limits in the parent's/child's REST world frames instead of the retarget T-pose: then
    Rr = (W_p R0_p^T)^T (W_c R0_c^T) = R0_c (rest^-1 local) R0_c^T, i.e. the rest-relative rotation in rest-world axes R0_c X/Y/Z."""
    global REST_W
    LIMITS.clear(); LIMITS.update(LIM()); LFRAME.clear(); REST_W = REST_W or _rest_world()
    for s in 'LR':
        for k, sg, rt in ((s + 'FA', -1.0, (-90, 90)), (s + 'CF', 1.0, (int(os.environ.get('MOCAP_CF_TW', '8')) * -1, int(os.environ.get('MOCAP_CF_TW', '8'))))):
            R0 = REST_W[k]; P0 = REST_W[APAR[k]]; _, _, _, r1, r2, _ = LIMITS[k]
            LIMITS[k] = (R0 @ np.array([0, 0, 1.0]), R0 @ np.array([sg, 0, 0]), R0 @ np.array([0, 1.0, 0]), (-5, 150), (-4, 4), rt)
            LFRAME[k] = (P0, R0)
        # wrist: same rest-local measurement; axes/ranges from 6,300 handmade clip frames (leito/poses/poses2): flex about local X -85..+50,
        # side about local Y ~-40..+45, axial twist (local Z, = pronation in handmade clips) up to ~+-95
        k = s + 'HD'; R0 = REST_W[k]; P0 = REST_W[s + 'FA']
        LIMITS[k] = (R0 @ np.array([0, 0, 1.0]), R0 @ np.array([1.0, 0, 0]), R0 @ np.array([0, 1.0, 0]), (-88, 55), (-44, 48), (-100, 100)); LFRAME[k] = (P0, R0)
def _frames(k, WTq):
    return LFRAME[k] if k in LFRAME else (q2m(WTq[APAR[k]]), q2m(WTq[k]))

SMOOTH_FPS = 30.0
def _viterbi_roll(cand, cost, lam=1.0):
    """globally consistent roll track: per-frame costs + lam * (wrapped change)^2 between frames (dynamic programming), so the roll can't
    hop between equivalent branches; closed for the loop (start/end on the same branch); returned unwrapped and drift-free (cyclic)"""
    K, n = cost.shape; dc = np.angle(np.exp(1j * (cand[:, None] - cand[None, :]))); T = lam * dc ** 2
    acc = cost[:, 0].copy(); back = np.zeros((n, K), int)
    for t in range(1, n):
        m = acc[None, :] + T; back[t] = np.argmin(m, 1); acc = m[np.arange(K), back[t]] + cost[:, t]
    acc = acc + lam * np.angle(np.exp(1j * (cand - cand[np.argmin(cost[:, 0])]))) ** 2   # close the loop
    path = np.zeros(n, int); path[-1] = int(np.argmin(acc))
    for t in range(n - 1, 0, -1): path[t - 1] = back[t, path[t]]
    phi = np.unwrap(cand[path]); k = np.round((phi[-1] - phi[0]) / (2 * np.pi)); return phi - np.linspace(0, k * 2 * np.pi, n)
def _twist(Wt, WTq, ch):
    d = LIMITS[ch][0]; Fp, Fc = _frames(ch, WTq); q = m2q(np.swapaxes(Wt[APAR[ch]] @ Fp.T, -1, -2) @ (Wt[ch] @ Fc.T)); return 2 * np.arctan2(q[:, :3] @ d, q[:, 3])
def hinge_calibrate(Wt, WTq, info=None):
    """elbows/knees are hinges: the retarget (bone directions only) leaves each limb's roll arbitrary, so SMPL flexion lands partly on the
    XPMSSE off-hinge axis (31-42 deg). Per limb and clip, a constant roll of the PARENT (upper arm / thigh) about its own axis turns the
    measured flexion plane onto the hinge (flex-weighted circular mean). The child's world target is unchanged (forearm/shin keep their
    direction); the roll becomes humeral/femoral rotation, where it belongs anatomically."""
    for s in 'LR':
        for pk, ck in ((s + 'UA', s + 'FA'), (s + 'TH', s + 'CF')):
            c1, c2, _ = _hinge_parts(Wt, WTq, pk, ck); d = LIMITS[pk][0]; mag = np.hypot(c1, c2); w = np.clip(mag - np.radians(15), 0, None)
            if w.sum() < 1e-6: continue
            # per frame, numeric 1-D search of the parent's roll about its own axis: minimise side-bend^2 + twist beyond 10 deg (^2) of the child
            # (bent: the flexion plane decides; straight: the twist decides), then circular-unwrap + 0.2 s smoothing so the roll never jitters
            WT = q2m(WTq[pk]); cand = np.radians(np.arange(-180, 180, 3)); cost = np.zeros((len(cand), len(c1)))   # full circle: undoes capture twist flips
            for ci, ph in enumerate(cand):
                Wn = dict(Wt); Wn[pk] = Wt[pk] @ WT.T @ rodrigues((d * ph)[None])[0] @ WT; _, cc2, _ = _hinge_parts(Wn, WTq, pk, ck); tw = _twist(Wn, WTq, ck)
                cost[ci] = cc2 ** 2 + np.maximum(0, np.abs(tw) - np.radians(10)) ** 2 + 1e-3 * ph ** 2
            phi = _viterbi_roll(cand, cost); phi = sgf(phi, max(5, int(SMOOTH_FPS * .2)))
            Wt[pk] = Wt[pk] @ WT.T[None] @ rodrigues(d[None] * phi[:, None]) @ WT[None]; _, c2b, _ = _hinge_parts(Wt, WTq, pk, ck)
            # child (forearm/shin) target: swing only - its axial twist is the capture's most flip-prone channel and is handed to the hand/foot
            # anyway (finish), whose own world targets carry the wrist/foot orientation from the video
            Fp, Fc = _frames(ck, WTq); dd = LIMITS[ck][0]; Rr = np.swapaxes(Wt[pk] @ Fp.T, -1, -2) @ (Wt[ck] @ Fc.T); qq = m2q(Rr); tw = 2 * np.arctan2(qq[:, :3] @ dd, qq[:, 3])
            Wt[ck] = (Wt[pk] @ Fp.T) @ (Rr @ rodrigues(-dd[None] * tw[:, None])) @ Fc
            if info is not None: info[pk] = dict(roll_deg_mean=round(float(np.degrees(np.mean(phi))), 1), roll_deg_range=round(float(np.degrees(np.ptp(phi))), 1), offhinge_p95_before=round(float(np.degrees(np.percentile(np.abs(c2), 95))), 1), offhinge_p95_after=round(float(np.degrees(np.percentile(np.abs(c2b), 95))), 1))
    return Wt

def leg_turnout(Wt, WTq, Jc, info=None):
    """a turned-out foot is HIP rotation: rotate thigh+shin rigidly about the hip->ankle line (ankle position fixed, knee hinge relation
    unchanged, the knee swings to point over the foot) by the per-frame angle that removes the foot's axial twist vs the shin beyond 5 deg
    (Viterbi over -60..60 deg, smoothed). Joint positions Jc (SMPL order: hip 1/2, ankle 7/8) give the axis."""
    for s, hj, aj in (('L', 1, 7), ('R', 2, 8)):
        th, cf, ft = s + 'TH', s + 'CF', s + 'FT'; ax = nrm(Jc[:, aj] - Jc[:, hj]); d = LIMITS[cf][0]; Rc0 = REST_W[cf]; Rf0 = REST_W[ft]
        def ank(Wcf): q = m2q(np.swapaxes(Wcf @ Rc0.T, -1, -2) @ (Wt[ft] @ Rf0.T)); return 2 * np.arctan2(q[:, :3] @ d, q[:, 3])
        tw0 = ank(Wt[cf]); cand = np.radians(np.arange(-60, 61, 3)); cost = np.zeros((len(cand), len(tw0)))
        for ci, ph in enumerate(cand):
            Rr = rodrigues(ax * ph); cost[ci] = np.maximum(0, np.abs(ank(Rr @ Wt[cf])) - np.radians(5)) ** 2 + .05 * ph ** 2
        phi = sgf(_viterbi_roll(cand, cost), max(5, int(SMOOTH_FPS * .2))); Rr = rodrigues(ax * phi[:, None])
        Wt[th] = Rr @ Wt[th]; Wt[cf] = Rr @ Wt[cf]
        if info is not None: info[s] = dict(ankle_twist_p95_before=round(float(np.degrees(np.percentile(np.abs(tw0), 95))), 1), after=round(float(np.degrees(np.percentile(np.abs(ank(Wt[cf])), 95))), 1), hip_roll_mean=round(float(np.degrees(phi.mean())), 1))
    return Wt

def world_targets(Gg, WT):
    """per frame world rotation (matrix) of each OPT bone: R_j(t) @ WT_b"""
    T = {}
    for k in OPT:
        T[k] = Gg[:, SMPL_OF[k]] @ q2m(WT[k])[None]
    return T

# ---------------- 4: torch model ----------------
import torch
torch.set_num_threads(max(4, (os.cpu_count() or 8) - 2))
DEV = torch.device(os.environ.get('MOCAP_DEVICE', 'cuda' if torch.cuda.is_available() else 'cpu'))   # RTX (float32, ~70 MB VRAM); MOCAP_DEVICE=cpu for float64 on CPU
TD = torch.float32 if DEV.type == 'cuda' else torch.float64
def t_(x): return torch.as_tensor(np.asarray(x), dtype=TD, device=DEV)
def t_rod(v):
    th = torch.linalg.norm(v, dim=-1, keepdim=True).clamp_min(1e-12); k = v / th; th = th[..., None]
    z = torch.zeros_like(k[..., 0]); K = torch.stack([torch.stack([z, -k[..., 2], k[..., 1]], -1), torch.stack([k[..., 2], z, -k[..., 0]], -1), torch.stack([-k[..., 1], k[..., 0], z], -1)], -2)
    I = torch.eye(3, dtype=TD, device=v.device).expand(K.shape); return I + torch.sin(th) * K + (1 - torch.cos(th)) * (K @ K)
def t_log(Rm):
    c = ((Rm[..., 0, 0] + Rm[..., 1, 1] + Rm[..., 2, 2] - 1) / 2).clamp(-1 + 1e-6, 1 - 1e-6); th = torch.acos(c)
    v = torch.stack([Rm[..., 2, 1] - Rm[..., 1, 2], Rm[..., 0, 2] - Rm[..., 2, 0], Rm[..., 1, 0] - Rm[..., 0, 1]], -1)
    return v * (th / (2 * torch.sin(th)).clamp_min(1e-7))[..., None]
def t_quat(Rm):  # matrix -> quaternion xyzw (w>=0 branch, fine away from 180 deg)
    w = torch.sqrt((1 + Rm[..., 0, 0] + Rm[..., 1, 1] + Rm[..., 2, 2]).clamp_min(1e-9)) / 2
    return torch.stack([(Rm[..., 2, 1] - Rm[..., 1, 2]) / (4 * w), (Rm[..., 0, 2] - Rm[..., 2, 0]) / (4 * w), (Rm[..., 1, 0] - Rm[..., 0, 1]) / (4 * w), w], -1)

class Skel:
    """batched FK over the full XPMSSE skeleton; OPT bones get local = init_local @ rod(delta)"""
    def __init__(s, S, Lq0, T0):
        s.S = S; s.nb = len(S['names']); s.par = S['parent']; s.sc = np.array(S['s'], float)
        s.L0 = t_(q2m(Lq0)); s.T = t_(T0)   # [n, nb, 3, 3], [n, nb, 3]
        s.opt = [S['i'][N[k]] for k in OPT]; s.oi = {b: k for k, b in enumerate(s.opt)}
        ws = np.ones(s.nb)
        for b in range(s.nb):
            p = s.par[b]; ws[b] = s.sc[b] * (ws[p] if p >= 0 else 1)
        s.ws = t_(ws)
        need = set(s.opt) | {S['i'][N[k]] for k in ('PEL', 'LTOE', 'RTOE', 'LF20', 'RF20')}   # FK only over what the losses read (+ ancestors)
        for b in list(need):
            p = s.par[b]
            while p >= 0: need.add(p); p = s.par[p]
        s.order = sorted(need)
    def fk(s, delta, droot):
        n = s.L0.shape[0]; dR = t_rod(delta); com = s.S['i'][N['COM']]
        zW = torch.zeros((n, 3, 3), dtype=TD, device=DEV); zP = torch.zeros((n, 3), dtype=TD, device=DEV); Wl = [zW] * s.nb; Pl = [zP] * s.nb
        for b in s.order:
            L = s.L0[:, b] if b not in s.oi else s.L0[:, b] @ dR[:, s.oi[b]]
            p = s.par[b]; t = s.T[:, b] + (droot if b == com else 0)
            if p < 0: Wl[b] = L; Pl[b] = t
            else: Wl[b] = Wl[p] @ L; Pl[b] = Pl[p] + (Wl[p] @ (t * s.ws[p])[..., None])[..., 0]
        return torch.stack(Wl, 1), torch.stack(Pl, 1)
    def arm_fk(s, W, P, delta):
        """collision view: everything DETACHED except the two arm chains (clavicle..hand), which are re-evaluated from a frozen copy of
        their spine parent with live arm locals -> the collision gradient can only move arm bones (one backward pass, no masking)"""
        if not hasattr(s, 'arms'):
            s.arms = []
            for sd in 'LR':
                b = s.S['i'][N[sd + 'HD']]; chain = []
                while s.S['names'][b] != N['SP2']: chain.append(b); b = s.par[b]
                s.arms += chain[::-1]
        dR = t_rod(delta); Wl = list(W.detach().unbind(1)); Pl = list(P.detach().unbind(1))
        for b in s.arms:
            L = s.L0[:, b] if b not in s.oi else s.L0[:, b] @ dR[:, s.oi[b]]; p = s.par[b]
            Wl[b] = Wl[p] @ L; Pl[b] = Pl[p] + (Wl[p] @ (s.T[:, b] * s.ws[p])[..., None])[..., 0]
        return torch.stack(Wl, 1), torch.stack(Pl, 1)

def limit_terms(W, WT, idx):
    """T-pose-relative local rotation per limited bone -> swing (2 comps) / twist (deg) and squared excess (rad^2)"""
    pen = 0; viol = {}; comps = {}
    for k, (d, a1, a2, r1, r2, rt) in LIMITS.items():
        b = idx[k]; p = idx[APAR[k]]
        if k in LFRAME: Fp, Fb = t_(LFRAME[k][0]), t_(LFRAME[k][1])
        else: Fp, Fb = WT[APAR[k]], WT[k]
        Rb = W[:, b] @ Fb.T; Rp = W[:, p] @ Fp.T; Rr = Rp.transpose(-1, -2) @ Rb
        q = t_quat(Rr); dd = t_(d); tw = 2 * torch.atan2((q[:, :3] * dd).sum(-1), q[:, 3])
        twq = torch.cat([dd * torch.sin(tw / 2)[:, None], torch.cos(tw / 2)[:, None]], -1)
        # swing = q * twist^-1
        x1, y1, z1, w1 = q.unbind(-1); x2, y2, z2, w2 = (-twq[:, 0], -twq[:, 1], -twq[:, 2], twq[:, 3])
        sw = torch.stack([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2], -1)
        sw = sw * torch.sign(sw[:, 3:4] + 1e-12); ang = 2 * torch.atan2(torch.linalg.norm(sw[:, :3], dim=-1), sw[:, 3])
        sv = sw[:, :3] / torch.linalg.norm(sw[:, :3], dim=-1, keepdim=True).clamp_min(1e-9) * ang[:, None]
        c1 = (sv * t_(a1)).sum(-1); c2 = (sv * t_(a2)).sum(-1); comps[k] = (c1, c2, tw)
        e = 0
        for c, (lo, hi) in ((c1, r1), (c2, r2), (tw, rt)):
            ex = torch.relu(math.radians(lo) - c) + torch.relu(c - math.radians(hi)); e = e + ex * ex
        pen = pen + e.sum(); viol[k] = e
    return pen, viol, comps

# ---------------- collision model: her skin (current look preset) per carrier bone ----------------
SKIN = json.load(open(os.path.join(D, 'tools', 'roto', 'dance_body_skin.json')))['pts']
def vox(a, v):
    k = np.round(a[:, :3] / v).astype(int); _, ix = np.unique(k, axis=0, return_index=True); return a[np.sort(ix)]
BODY_CARRIERS = ['PEL', 'SP0', 'SP1', 'SP2', 'HEAD', 'LTH', 'RTH']
def collision_sets():
    surf = {}; qry = {}
    for k in BODY_CARRIERS + [s + p for s in 'LR' for p in ('UA', 'FA', 'HD')]:
        a = np.array(SKIN[N[k] if k != 'PEL' else N['PEL']], float); surf[k] = vox(a, 2.0 if k in BODY_CARRIERS else 1.6)
    for s in 'LR':
        for p, v in (('UA', 3.0), ('FA', 2.2), ('HD', 1.8)):
            a = np.array(SKIN[N[s + p]], float); a = vox(a, v)
            if p == 'UA':  # skip the shoulder/armpit half (contact there is anatomical)
                ax = SF['t'][SF['i'][N[s + 'FA']]]; L_ = np.linalg.norm(ax); tpar = a[:, :3] @ (ax / L_) / L_; a = a[tpar > .45]
            qry[s + p] = a
    return surf, qry
SURF, QRY = collision_sets()
def pair_list(s):
    o = 'R' if s == 'L' else 'L'
    return [(s + p, c) for p in ('UA', 'FA', 'HD') for c in BODY_CARRIERS + [o + 'UA', o + 'FA', o + 'HD'] if not (p == 'UA' and c in ('SP2',))] + [(s + 'HD', s + 'UA')]
SWEEP = (0.0, 1 / 3, 2 / 3)   # sub-frame samples between frame t and t+1 (cyclic): catches an arm tunnelling through the body/other arm between frames
def collide(W, P, idx, ws, margin=.35, frames=None, report=False):
    """signed distance of arm/hand skin points to the nearest skin point (with normal) of each body carrier, at each frame and at
    swept sub-frame samples (both bodies interpolated linearly between consecutive frames); penalty for sd < margin"""
    pen = 0; rep = {}; n = W.shape[0]
    fr = torch.arange(n, device=W.device) if frames is None else frames; fr2 = (fr + 1) % n
    for s in 'LR':
        for qk, ck in pair_list(s):
            qb, cb = idx[qk], idx[ck]; Qp = t_(QRY[qk][:, :3]); Cp = t_(SURF[ck][:, :3]); Cn = t_(SURF[ck][:, 3:])
            pwa = P[fr, qb][:, None] + (W[fr, qb] @ (Qp * ws[qb]).T).transpose(-1, -2); pwb = P[fr2, qb][:, None] + (W[fr2, qb] @ (Qp * ws[qb]).T).transpose(-1, -2)
            worst = None
            for al in SWEEP:
                pw = pwa * (1 - al) + pwb * al; Pc = P[fr, cb] * (1 - al) + P[fr2, cb] * al; Wc = W[fr, cb] * (1 - al) + W[fr2, cb] * al
                loc = ((pw - Pc[:, None]) @ Wc) / ws[cb]
                with torch.no_grad():  # nearest skin point: piecewise-constant index, no graph needed (gradient flows through loc)
                    dist = torch.cdist(loc, Cp[None].expand(loc.shape[0], -1, -1)); dmin, ix = dist.min(-1); del dist
                sd = ((loc - Cp[ix]) * Cn[ix]).sum(-1); bad = (dmin < 9) & (sd < margin)
                e = torch.where(bad, (margin - sd), torch.zeros_like(sd)); pen = pen + (e * e).sum() * (1.0 if al == 0 else .7)
                if report:
                    depth = torch.where((dmin < 9) & (sd < 0), -sd, torch.zeros_like(sd)).max(-1).values; worst = depth if worst is None else torch.maximum(worst, depth)
            if report: rep[qk + '|' + ck] = worst.detach().cpu().double().numpy() / U * 1000   # mm per frame (incl. swept samples to the next frame)
    return pen, rep

# ---------------- bake ----------------
def close_loop(x):
    n = len(x); v = ((x[1] - x[0]) + (x[-1] - x[-2])) / 2; gap = x[-1] + v - x[0]; return x - np.linspace(0, 1, n)[:, None] * gap[None]
def pelvis_angles(Rm):
    """pelvis yaw/tilt/roll (deg) in the ground frame, relative to the clip's mean heading"""
    f = Rm[:, :, 1]; u = Rm[:, :, 2]; yaw = np.degrees(np.unwrap(np.arctan2(-f[:, 0], f[:, 1]))); yaw -= np.median(yaw)
    c, s_ = np.cos(np.radians(yaw)), np.sin(np.radians(yaw)); ux = c * u[:, 0] + s_ * u[:, 1]; uy = -s_ * u[:, 0] + c * u[:, 1]
    tilt = np.degrees(np.arctan2(uy, u[:, 2])); roll = np.degrees(np.arctan2(ux, u[:, 2]))
    rng = lambda a: round(float(np.percentile(a, 95) - np.percentile(a, 5)), 1)
    return dict(yaw=rng(yaw), tilt=rng(tilt - np.median(tilt)), roll=rng(roll - np.median(roll)))
def sole_points(s):
    a = np.array(SKIN[N[s + 'FT']], float); Pr = R.Pose(SF, SF['q'][None], SF['t'][None]); b = SF['i'][N[s + 'FT']]
    w = Pr.WP[0, b] + R.qrot(np.repeat(Pr.WQ[0, b][None], len(a), 0), a[:, :3]); lo = a[w[:, 2] < w[:, 2].min() + 1.2]
    k = np.linspace(0, len(lo) - 1, min(14, len(lo))).astype(int); return lo[k, :3]

# ---------------- self-relative hand targets ----------------
# end effectors: wrist -> her Hand bone, middle knuckle -> her Finger20; landmarks: SMPL joint -> her bone (position + frame)
REL_EE = [('L', 20, 'LHD', None), ('L', 28, None, 'LF20'), ('R', 21, 'RHD', None), ('R', 43, None, 'RF20')]
REL_LM = {'HEAD': 15, 'NECK': 12, 'SP2': 9, 'SP1': 6, 'SP0': 3, 'COM': 0, 'LUA': 16, 'RUA': 17, 'LFA': 18, 'RFA': 19, 'LHD': 20, 'RHD': 21, 'LTH': 1, 'RTH': 2, 'LCF': 4, 'RCF': 5}
RSM_W = float(os.environ.get('MOCAP_RSM_W', '2.0')); PSM_W = float(os.environ.get('MOCAP_PSM_W', '5.0')); REL_W = float(os.environ.get('MOCAP_REL_W', '0')); REL_HUB = .03 * U; REL_D0 = .10 * U; REL_DMAX = .35 * U   # REL_W OFF: pulled hands into her (bigger) bust; collision now arm-only
def rel_targets(Hc, Gc, WTq, sc):
    """per (end effector, landmark) pair: offset of the effector in the landmark's frame (video, scaled to her) + closeness weight"""
    pairs = []; out = {}
    for s, je, hb, fb in REL_EE:
        for lk, jl in REL_LM.items():
            if lk[0] == s and lk[1:] in ('UA', 'FA', 'HD'): continue   # own arm chain: given by the bone directions
            v = Hc[:, je] - Hc[:, jl]; d = np.linalg.norm(v, axis=-1)
            w = np.exp(-d / REL_D0) * (d < REL_DMAX)
            if w.max() < .05: continue
            loc = np.einsum('nji,nj->ni', Gc[:, SMPL_OF[lk]], v) * sc   # video offset in the landmark frame, scaled to her
            key = '%s|%s|%s' % (hb or fb, lk, je); pairs.append((key, hb, fb, lk)); out[key + ':o'] = loc; out[key + ':w'] = w
    out['pairs'] = pairs; return out
def rel_loss(W, P, idx, REL, RELt):
    tot = 0; err = {}
    for key, hb, fb, lk in REL['pairs']:
        ep = P[:, idx[hb]] if hb else P[:, SKI[fb]]
        Fl = W[:, idx[lk]].detach() @ WTT[lk].transpose(-1, -2)   # her landmark frame = the SMPL frame equivalent; DETACHED: the hand moves to the
        tgt = P[:, idx[lk]].detach() + (Fl @ RELt[key + ':o'][..., None])[..., 0]   # body, the body (head/spine) is never turned to bring the target to the hand
        e2 = ((ep - tgt) ** 2).sum(-1); w = RELt[key + ':w']
        hb_ = REL_HUB * REL_HUB; tot = tot + (w * 2 * hb_ * (torch.sqrt(1 + e2 / hb_) - 1)).sum() / len(w)   # pseudo-Huber: quadratic within ~3 cm, then a
        # bounded pull, so a target her body cannot reach (joint-correspondence offset, bigger hips/bust, collision) never overpowers the solve
        if torch.is_grad_enabled(): continue   # stats only in the final no-grad pass
        m = w > .3
        if bool(m.any()): err[key] = [round(float(torch.quantile(e2[m].sqrt(), q)) / U * 100, 1) for q in (.5, .95)] + [int(m.sum())]
    return tot, err

KNOT = float(os.environ.get('MOCAP_KNOT', '3')); PROJ = os.environ.get('MOCAP_PROJ', 'old')   # 'smooth' (normalised convolution) breaks on large overlapping corrections (dance_5 head 143 deg/frame)
def bspline_basis(n, K):
    """[n, K] cyclic uniform cubic B-spline weights (each row sums to 1)"""
    B = np.zeros((n, K))
    for t in range(n):
        u = t * K / n; i = int(np.floor(u)); f = u - i
        w = ((1 - f) ** 3 / 6, (3 * f ** 3 - 6 * f ** 2 + 4) / 6, (-3 * f ** 3 + 3 * f ** 2 + 3 * f + 1) / 6, f ** 3 / 6)
        for o, wi in zip((-1, 0, 1, 2), w): B[t, (i + o) % K] += wi
    return B

def bake(cfg, iters=tuple(int(x) for x in os.environ.get('MOCAP_ITERS', '300,200,350,150').split(',')), log_every=100):   # losses plateau by ~1000 (was 500,300,600,300)
    t0 = time.time(); F = load_fit(cfg['id']); fps = F['fps']
    Jg, Gg, ginfo = ground_frame(F)
    SPK = {}; Gg = repair_spikes(Gg, fps, 40.0, SPK); ginfo['spike_frames'] = {str(k): v for k, v in SPK.items()}   # capture limb swaps/losses
    B = int(round(fps * .5)); i, j = loop_window(Jg, Gg, fps, cfg.get('lo', .6), B); Jc, Gc = crop_blend(Jg, Gg, i, j, B); n = len(Jc)
    Hc, _ = crop_blend(F['J55g'], Gg, i, j, B)   # same crop/blend for the 55 joints
    # smooth the per-frame fits (single-frame estimator): rotations SG ~0.23 s, cyclic
    # window per joint scaled by NLF's own uncertainty (segment k -> its end joint): well-seen joints keep their detail (0.23 s), legs/feet out of
    # shot (3-4x the torso's uncertainty) get up to 3x the window instead of passing their per-frame noise into the clip as leg jitter
    uw = np.nanmedian(np.where(np.isfinite(F['unc']), F['unc'], np.nan), 0); uw = np.where(np.isfinite(uw), uw, np.nanmax(uw)); u_ref = np.median(uw[[0, 3, 6, 9, 12]]); CH = {1: 4, 2: 5, 4: 7, 5: 8, 7: 10, 8: 11, 16: 18, 17: 19, 18: 20, 19: 21, 13: 16, 14: 17, 12: 15}   # (nanmedian: NaN uncertainty on missed-detection frames)
    SWIN = [fps * .23 * float(np.clip(max(uw[k], uw[CH.get(k, k)]) / max(u_ref, 1e-6), 1, 3)) for k in range(22)]
    Gc = np.stack([smooth_rot(Gc[:, k], int(SWIN[k])) for k in range(22)], 1)
    off = M.smpl_rest_offsets(F['G'], F['J']); PT, WTq = M.build_tpose(R, SF, off, M.hand_rest_offsets(F['G'], F['J55']))
    anat_limits(WTq)   # elbow/knee hinge = bone-local X of this rig (per clip T-pose)
    Wt = world_targets(Gc, WTq); HINGE = {}
    TURN = {}; Wt = leg_turnout(Wt, WTq, Jc, TURN); print(cfg['id'], 'leg turnout', json.dumps(TURN), flush=True)
    if os.environ.get('MOCAP_HINGE', '1') == '1': Wt = hinge_calibrate(Wt, WTq, HINGE); print(cfg['id'], 'hinge calibration', json.dumps(HINGE), flush=True)
    # root: pelvis joint scaled to her leg length, in place-ish (high-passed, loop-closed)
    leg_s = np.linalg.norm(off[4]) + np.linalg.norm(off[7]); leg_r = np.linalg.norm(SF['t'][SF['i'][N['LCF']]]) + np.linalg.norm(SF['t'][SF['i'][N['LFT']]]); sc = leg_r / leg_s
    pos = Jc[:, 0] * sc; pos[:, :2] = sgf(pos[:, :2], int(fps * .3))   # NLF pelvis jitters ~0.4 cm (p95 1.1-1.4): unsmoothed it shakes the planted legs/feet
    pos[:, :2] = close_loop(pos[:, :2]); pos[:, :2] -= sgf(pos[:, :2], int(fps * 3), 1); pos[:, :2] = np.clip(pos[:, :2], -18, 18); pos[:, 2] = sgf(pos[:, 2], 7)
    # contacts (data): foot joints low + slow
    cont = {}
    for s, (an, ft) in (('L', (7, 10)), ('R', (8, 11))):
        # (also when the feet are out of shot: the fit's legs follow the visible thighs, so a lifted knee is not forced down)
        h = np.minimum(Jc[:, an, 2] - np.percentile(Jc[:, an, 2], 5), Jc[:, ft, 2] - np.percentile(Jc[:, ft, 2], 5)) * sc
        fp = sgf(Jc[:, ft, :2] * sc, 9); v = np.linalg.norm(np.gradient(fp, axis=0), axis=-1); c = ((sgf(h, 7) < 3.0) & (v < .75)).astype(float)
        from scipy.signal import medfilt; cont[s] = medfilt(c, 5)
    # init locals: T-pose locals everywhere, relaxed fingers, OPT bones from world targets
    nb = len(SF['names']); Lq = np.repeat(PT.Q[:1], n, 0).copy(); Tt = np.repeat(PT.T[:1], n, 0).copy()
    RF = M.relaxed_fingers(R, SF, PT, os.path.join(D, 'tools', 'roto', 'smplx_relaxed_hand.json'))   # natural relaxed hand (replaces the posed-pack fingers)
    for nm, q in RF.items(): Lq[:, SF['i'][nm]] = q
    Tt[:, SF['i'][N['COM']]] = pos
    Wm = [None] * nb; Lm = q2m(Lq)
    for b in range(nb):
        p = SF['parent'][b]; key = next((k for k in OPT if N[k] == SF['names'][b]), None)
        if key is not None:
            Wm[b] = Wt[key]; Lm[:, b] = (np.swapaxes(Wm[p], -1, -2) @ Wt[key]) if p >= 0 else Wt[key]
        else: Wm[b] = Lm[:, b] if p < 0 else Wm[p] @ Lm[:, b]
    # root height: her soles on the floor (lowest sole point per frame, smoothed), not the camera-depth pelvis height
    Pi = R.Pose(SF, m2q(Lm), Tt); zs = []
    for s in 'LR':
        fb = SF['i'][N[s + 'FT']]; so = sole_points(s); zs.append((Pi.WP[:, fb][:, None] + R.qrot(np.repeat(Pi.WQ[:, fb][:, None], len(so), 1), so[None] * 1.0))[..., 2].min(-1))
    zmin = np.minimum(*zs); Tt[:, SF['i'][N['COM']], 2] -= sgf(zmin, 5); pos[:, 2] = Tt[:, SF['i'][N['COM']], 2]
    sk = Skel(SF, m2q(Lm), Tt)
    idx = {k: SF['i'][N[k]] for k in OPT + ['PEL', 'LUA', 'RUA']}; idx.update({k: SF['i'][N[k]] for k in ['LTOE', 'RTOE']})
    WT = {k: t_(q2m(WTq[k])) for k in OPT}; global WTT, SKI; WTT = WT; SKI = {k: SF['i'][N[k]] for k in ('LF20', 'RF20')}
    Wtt = {k: t_(Wt[k]) for k in OPT}; post = t_(pos); C = {s: t_(cont[s]) for s in 'LR'}; SOLE = {s: t_(sole_points(s)) for s in 'LR'}
    wrot = {k: (10.0 if k == 'COM' else .5 if k.endswith('HD') else .7 if k in ('HEAD', 'NECK') else .6 if k.endswith('FT') else 1.0) for k in OPT}   # pelvis weighted up: hip roll/tilt/gyration must survive the foot plants
    LIMB = [s + k for s in 'LR' for k in ('UA', 'FA', 'TH', 'CF')]
    LAX = {k: t_(nrm(SF['t'][SF['i'][N[k[0] + {'UA': 'FA', 'FA': 'HD', 'TH': 'CF', 'CF': 'FT'}[k[1:]]]]])) for k in LIMB}   # child offset = bone axis (local)
    # the corrections on top of the retargeted data are a cyclic cubic B-spline over time (a control point every KNOT frames), not free per-frame
    # values: stiff limit/collision penalties + Adam otherwise kick single frames back and forth (pelvis/spine/head 'convulse'); the video's own
    # detail stays in the init pose, only the constraint corrections are band-limited
    K = max(8, int(round(n / KNOT))); Bm = t_(bspline_basis(n, K))
    dpar = torch.zeros((K, len(OPT), 3), dtype=TD, device=DEV, requires_grad=True); rpar = torch.zeros((K, 3), dtype=TD, device=DEV, requires_grad=True)
    cur = lambda: (torch.einsum('nk,kbd->nbd', Bm, dpar), Bm @ rpar)
    ACC = [idx[k] for k in OPT] + [SF['i'][N['LF20']], SF['i'][N['RF20']], idx['LTOE'], idx['RTOE']]
    # self-relative hand targets: where each hand is relative to her own head/torso/arms/other hand in the video (hands behind the head, on the
    # hips, framing the face, arms crossed) -> the same place on her body, as bone-local offsets scaled to her size; weighted by closeness in the
    # video, so near-contact poses are reproduced even where her proportions differ (bone directions alone put the hands elsewhere)
    REL = rel_targets(Hc, Gc, WTq, sc); RELt = {k: t_(v) for k, v in REL.items() if k != 'pairs'}
    phase = {'lim': 40.0, 'col': 4.0, 'all': False, 'it': 0}
    def losses(full=True):
        delta, droot = cur(); W, P = sk.fk(delta, droot); Ls = {}
        Wa, Pa = sk.arm_fk(W, P, delta)   # arm-only view: every ARM term (rot/dir/collision) moves arm bones only - the torso follows the video
        AW = lambda k: Wa if k in ARMK else W
        # limbs: bone DIRECTION is the data; their twist only weakly (shoulder/hip twist vs elbow/knee off-hinge rotation is ambiguous in the fit,
        # so the hinge limits decide it); trunk/head/hands/feet: full rotation
        Ls['rot'] = sum(wrot[k] * (t_log(Wtt[k].transpose(-1, -2) @ AW(k)[:, idx[k]]) ** 2).sum(-1).mean() * (.12 if k in LIMB else 1) * (.1 if (not ginfo['feet_tracked'] and k[1:] in ('TH', 'CF', 'FT')) else 1) for k in OPT)
        Ls['dir'] = sum((4 if (ginfo['feet_tracked'] or k[1:] in ('UA', 'FA')) else .4) * (((AW(k)[:, idx[k]] - Wtt[k]) @ LAX[k]) ** 2).sum(-1).mean() for k in LIMB)   # legs out of shot: their directions are guesses -> weak
        Ls['root'] = .02 * ((P[:, idx['COM']] - post) ** 2).sum(-1).mean()
        Ls['rel'] = REL_W * rel_loss(W, P, idx, REL, RELt)[0]
        lp, _, _ = limit_terms(W, WT, idx); Ls['limit'] = phase['lim'] * lp / n
        if full:
            fr = torch.arange(phase['it'] % 3, n, 3, device=DEV) if phase['all'] else torch.randperm(n, device=DEV)[:max(8, n // 3)]   # final phase: every frame, in 3 interleaved sets
            cp, _ = collide(Wa, Pa, idx, sk.ws, frames=fr); Ls['collide'] = phase['col'] * cp / len(fr)   # arm-only gradient by construction
        g = 0; sk_ = 0; zlow = []
        for s in 'LR':
            fb = idx[s + 'FT']; sp = P[:, fb][:, None] + (W[:, fb] @ (SOLE[s] * sk.ws[fb]).T).transpose(-1, -2)
            g = g + (torch.relu(-sp[..., 2]) ** 2).sum() + (torch.relu(2.0 - P[:, idx[s + 'CF'], 2]) ** 2).sum()
            zmin = sp[..., 2].min(-1).values; zlow.append(zmin); dxy = sp[:, :, :2] - torch.roll(sp[:, :, :2], 1, 0); cc = C[s] * torch.roll(C[s], 1, 0)
            sk_ = sk_ + (cc[:, None] * (dxy ** 2).sum(-1)).sum() + (C[s] * torch.relu(zmin - .3) ** 2).sum()
        Ls['support'] = 3 * (torch.relu(torch.minimum(zlow[0], zlow[1]) - .3) ** 2).mean()   # no jumps in these dances: one sole always on the floor
        Ls['ground'] = 10 * g / n; Ls['skate'] = .3 * sk_ / n   # feet out of shot: soft plants, so the hips can shift weight/roll (feet may re-place)
        X_ = P[:, ACC]; acc = torch.roll(X_, -1, 0) - 2 * X_ + torch.roll(X_, 1, 0); Ls['smooth'] = .02 * (acc ** 2).sum(-1).mean() * len(ACC) / 10
        Ld = torch.roll(delta, -1, 0) - 2 * delta + torch.roll(delta, 1, 0); Ls['dsmooth'] = .5 * (Ld ** 2).sum(-1).mean()
        # rotational smoothness of every solved bone's WORLD rotation (cyclic angular acceleration): neighbouring spine/arm bones can zig-zag in
        # opposite directions that cancel in the joint positions (so 'smooth' misses it) but twitch the skin -> the body 'convulses'
        # P-spline penalty: second differences of the control points themselves (cyclic) -> no knot-to-knot zig-zag from the stiff foot/floor terms
        D2 = torch.roll(dpar, -1, 0) - 2 * dpar + torch.roll(dpar, 1, 0); R2 = torch.roll(rpar, -1, 0) - 2 * rpar + torch.roll(rpar, 1, 0)
        Ls['psmooth'] = PSM_W * ((D2 ** 2).sum(-1).mean() * len(OPT) + .01 * (R2 ** 2).sum(-1).mean())
        Wo = W[:, [idx[k] for k in OPT]]; Ra = torch.roll(Wo, -1, 0) - 2 * Wo + torch.roll(Wo, 1, 0); Ls['rsmooth'] = RSM_W * (Ra ** 2).sum((-1, -2)).mean() * len(OPT)
        return Ls, W, P
    opt = torch.optim.Adam([dpar, rpar], lr=.01); hist = []
    ARMK = {s + k for s in 'LR' for k in ('CLV', 'UA', 'FA', 'HD')}
    for it in range(sum(iters)):
        if it == iters[0]:
            for g_ in opt.param_groups: g_['lr'] = .003
        if it == iters[0] + iters[1]:   # final phase: limits and collisions become (nearly) hard, every frame
            phase.update(lim=5000.0, col=600.0, all=True)
            for g_ in opt.param_groups: g_['lr'] = .002
        if len(iters) > 3 and it == iters[0] + iters[1] + iters[2]:   # polish: limits effectively hard (drives the last violating frames to 0)
            phase.update(lim=60000.0, col=1200.0)
            for g_ in opt.param_groups: g_['lr'] = .001
        phase['it'] = it; opt.zero_grad(); Ls, W, P = losses()
        # collision moves ONLY the arm bones: its gradient on spine/pelvis/legs/root is dropped (otherwise the solver turns the whole body to
        # clear the arms out of her bust); every other term updates everything as usual
        tot = sum(Ls.values()); tot.backward(); opt.step()
        if it % log_every == 0 or it == sum(iters) - 1: hist.append({k: round(float(v.detach()), 5) for k, v in Ls.items()}); print(cfg['id'], it, json.dumps(hist[-1]), round(time.time() - t0), 's', flush=True)
    with torch.no_grad(): Ls, W, P = losses(full=False)
    with torch.no_grad(): relerr = rel_loss(W, P, idx, REL, RELt)[1]; delta, droot = cur()
    L0q = m2q(Lm)   # init local rotations (fingers, twist helpers...): used for every bone the FK did not evaluate
    return dict(L0q=L0q, relerr=relerr, F=F, fps=fps, n=n, loop=[int(i), int(j)], ginfo=ginfo, sk=sk, W=W.detach().cpu().double().numpy(), P=P.detach().cpu().double().numpy(), WT=WTq, Wt=Wt, idx=idx, cont=cont, hist=hist, Gc=Gc, delta=delta.detach().cpu(), droot=droot.detach().cpu(), sc=sc)

# ---------------- 5a: hard joint-limit projection (after the optimiser), spread over neighbouring frames so nothing pops ----------------
def project_limits(W, WTq, idx, spread=4):
    """clamp each limited bone's T-pose-relative local rotation (swing components + twist) into its range, parents first; the correction
    rotation of a clamped frame is eased in/out over +-spread frames (cyclic). Returns new world rotations and the number of clamped frames."""
    W = W.copy(); n = len(W); total = 0
    for k in ['SP0', 'SP1', 'SP2', 'NECK', 'HEAD'] + [s + j for s in 'LR' for j in ('CLV', 'UA', 'FA', 'HD', 'TH', 'CF', 'FT')]:
        d, a1, a2, r1, r2, rt = LIMITS[k]; b = idx[k]; pb = idx[APAR[k]]; WTp, WTb = _frames(k, WTq)
        Rp = W[:, pb] @ WTp.T; Rr = np.swapaxes(Rp, -1, -2) @ (W[:, b] @ WTb.T); q = m2q(Rr)
        q = q * np.sign(q[:, 3:4] + 1e-12); tw = 2 * np.arctan2(q[:, :3] @ d, q[:, 3])
        tw = np.unwrap(tw); tw -= 2 * np.pi * np.round(tw.mean() / (2 * np.pi))   # continuous twist: a wrapped angle near +-180 clamped to +range on one
        # frame and -range on the next (200 deg hand flip, dance_1 f158); unwrapped, an over-twist clamps to the SAME side every frame
        Rsw = Rr @ rodrigues(-d[None] * tw[:, None]); sv = rot_log(Rsw); c1 = sv @ a1; c2 = sv @ a2; rest = sv - np.outer(c1, a1) - np.outer(c2, a2)
        lo = np.radians; c1n = np.clip(c1, lo(r1[0]), lo(r1[1])); c2n = np.clip(c2, lo(r2[0]), lo(r2[1])); twn = np.clip(tw, lo(rt[0]), lo(rt[1]))
        hit = (np.abs(c1n - c1) + np.abs(c2n - c2) + np.abs(twn - tw)) > 1e-6
        if not hit.any(): continue
        total += int(hit.sum())
        Rn = rodrigues(np.outer(c1n, a1) + np.outer(c2n, a2) + rest) @ rodrigues(d[None] * twn[:, None])
        Wn = Rp @ Rn @ WTb; corr = rot_log(Wn @ np.swapaxes(W[:, b], -1, -2))   # world correction (rotation vector) on clamped frames
        if PROJ == 'smooth':
            # normalised convolution: the correction field is interpolated smoothly between clamped frames (no switching between neighbouring
            # frames' corrections -> no per-frame jumps), full on clamped frames, eased to zero over ~spread frames outside them
            m = hit.astype(float); ker = np.hanning(2 * spread + 3)[1:-1]; cw = lambda x: np.real(np.fft.ifft(np.fft.fft(x, axis=0) * np.fft.fft(np.roll(np.pad(ker, (0, n - len(ker))), -spread))[:, None] if x.ndim > 1 else np.fft.ifft(np.fft.fft(x) * np.fft.fft(np.roll(np.pad(ker, (0, n - len(ker))), -spread)))))
            den = cw(m); num = cw(corr * m[:, None]); cv = num / np.maximum(den, 1e-9)[:, None]
            ramp = np.clip(den / ker.max(), 0, 1); ramp = ramp * ramp * (3 - 2 * ramp); cv = cv * ramp[:, None]; cv[hit] = corr[hit]
        else:
            wgt = np.zeros(n); cv = np.zeros((n, 3))
            for t in np.where(hit)[0]:
                for o in range(-spread, spread + 1):
                    u = (t + o) % n; w = 1 - abs(o) / (spread + 1)
                    if w > wgt[u]: wgt[u] = w; cv[u] = corr[t] * (1 if o == 0 else w)
            cv[hit] = corr[hit]
        # rotate this bone's subtree (world rotations) by the correction about the bone
        C = rodrigues(cv); sub = [i for i in range(len(SF['names'])) if i == b or _desc(i, b)]
        for i in sub: W[:, i] = C @ W[:, i]
    return W, total
_DESC = {}
def _desc(i, b):
    key = (i, b)
    if key not in _DESC:
        p = SF['parent'][i]
        while p >= 0 and p != b: p = SF['parent'][p]
        _DESC[key] = p == b
    return _DESC[key]

# ---------------- 5: twist split, encode, metrics ----------------
FL_SM = int(os.environ.get('MOCAP_FL_SM', '9'))
def foot_lock(W, Wraw, P, idx, cont, n, WTq):
    """planted feet stay put: per contact segment the ankle is pinned to its mean position there (eased in/out with a smoothed contact weight);
    two-bone IK on thigh/calf (knee stays in its current plane), foot world rotation kept. Post-solve, so no optimiser jitter."""
    W = W.copy(); W0 = W.copy()
    if os.environ.get('MOCAP_FOOTLOCK') == '0': return W   # on for videos with tracked feet (the planted positions are real data then)
    for s in 'LR':
        th, cf, ft = idx[s + 'TH'], idx[s + 'CF'], idx[s + 'FT']; c = (cont[s] > .5).astype(float)
        c = _runs(c, 1, 3)        # close gaps of <= 3 frames inside a plant (cyclic)
        c = 1 - _runs(1 - c, 1, 4)   # drop plants shorter than 5 frames (detector flicker, not real steps)
        if c.sum() < 3: continue
        # bone offsets from the raw solve (positions P belong to it), joint positions rebuilt from the FINAL rotations (after limit projection)
        o1 = np.einsum('nji,nj->ni', Wraw[:, th], P[:, cf] - P[:, th]).mean(0); o2 = np.einsum('nji,nj->ni', Wraw[:, cf], P[:, ft] - P[:, cf]).mean(0)
        h = P[:, th].copy(); k = h + np.einsum('nij,j->ni', W[:, th], o1); a = k + np.einsum('nij,j->ni', W[:, cf], o2); l1 = np.linalg.norm(o1); l2 = np.linalg.norm(o2)
        seg = np.zeros(n, int) - 1; sid = 0; anchors = []   # contact segments (cyclic wrap joined)
        start = int(np.argmin(c)) if c.min() < .5 else 0
        order = [(start + t) % n for t in range(n)]; cur = None
        for t in order:
            if c[t] > .5:
                if cur is None: cur = sid; sid += 1; anchors.append([])
                seg[t] = cur; anchors[cur].append(a[t])
            else: cur = None
        anchors = [np.mean(x, 0) for x in anchors]   # (xy used: height stays per frame, so no floor penetration from a mean)
        # planted foot ROTATION too (yaw only: the sole's pitch/roll may roll heel->toe): per segment mean yaw -> toes stop sweeping around the ankle
        yaws = {}
        for t in range(n):
            if seg[t] >= 0: f_ = W[t, ft] @ np.array([0, 1.0, 0]); yaws.setdefault(seg[t], []).append(math.atan2(f_[1], f_[0]))
        segyaw = {g: math.atan2(np.mean(np.sin(v)), np.mean(np.cos(v))) for g, v in yaws.items()}
        wgt = np.clip(sgf(c, 7, 2), 0, 1) if n > 9 else c; wgt = wgt * wgt * (3 - 2 * wgt)
        near = seg.copy()   # nearest segment for the eased frames around each plant
        for t in range(n):
            if near[t] < 0:
                for o in range(1, 8):
                    for u in ((t - o) % n, (t + o) % n):
                        if seg[u] >= 0 and near[t] < 0: near[t] = seg[u]
        for t in range(n):
            if near[t] < 0 or wgt[t] < 1e-3: continue
            dlt = anchors[near[t]] - a[t]; dlt[2] = 0; tgt = a[t] + wgt[t] * dlt; d = tgt - h[t]; L = np.linalg.norm(d); u = d / max(L, 1e-9)
            L0 = float(np.linalg.norm(a[t] - h[t]))   # current reach: only a LENGTHENING beyond it is limited (smoothly) -> untouched frames and
            if L > L0:                                  # shortened targets keep their exact leg length (no length flicker on a straight leg)
                room = max(.999 * (l1 + l2) - L0, 1e-6); L = L0 + room * math.tanh((L - L0) / room)
            L = max(L, abs(l1 - l2) + 1e-3)
            # (1) knee: flex about its OWN hinge axis only (never off-hinge) until hip->ankle has the target length
            hx = (W[t, th] @ q2m(WTq[s + 'TH']).T) @ LIMITS[s + 'CF'][1]; hx = hx / max(np.linalg.norm(hx), 1e-9); Wft = W[t, ft].copy()
            best = None
            for sg in (1.0, -1.0):   # law of cosines gives |angle change|; pick the direction that reaches L
                th0 = math.acos(np.clip((h[t] - k[t]) @ (a[t] - k[t]) / (l1 * l2), -1, 1)); th1 = math.acos(np.clip((l1 * l1 + l2 * l2 - L * L) / (2 * l1 * l2), -1, 1))
                Rk = rodrigues((hx * sg * (th1 - th0))[None])[0]; a2 = k[t] + Rk @ (a[t] - k[t]); e = abs(np.linalg.norm(a2 - h[t]) - L)
                if best is None or e < best[0]: best = (e, Rk, a2)
            _, Rk, a2 = best; W[t, cf] = Rk @ W[t, cf]
            # (2) hip: minimal rotation of the whole leg so the ankle lands on the target
            R1 = _align(a2 - h[t], tgt - h[t]); W[t, th] = R1 @ W[t, th]; W[t, cf] = R1 @ W[t, cf]
            W[t, ft] = Wft if os.environ.get('MOCAP_FOOTYAW') != '1' else rodrigues(np.array([[0, 0, wgt[t] * math.atan2(math.sin(segyaw[near[t]] - math.atan2((Wft @ np.array([0, 1.0, 0]))[1], (Wft @ np.array([0, 1.0, 0]))[0])), math.cos(segyaw[near[t]] - math.atan2((Wft @ np.array([0, 1.0, 0]))[1], (Wft @ np.array([0, 1.0, 0]))[0])))]]))[0] @ Wft   # yaw lock: OFF (measured: toes drifted more, 0.3 -> 1.3 u)
        # the IK passes hip wobble straight into the knee (planted foot): smooth the leg CORRECTIONS over ~0.3 s (the data's own leg motion is untouched)
        for b_ in (th, cf):
            C_ = W[:, b_] @ np.swapaxes(W0[:, b_], -1, -2); cv = sgf(rot_log(C_), int(FL_SM))
            W[:, b_] = rodrigues(cv) @ W0[:, b_]
        if True:   # thigh changed -> calf/foot world follow; keep the foot's world rotation of the IK result
            pass
        DBG[s] = dict(wgt=wgt, near=near, seg=seg, a=a, h=h, l=l1 + l2, anchors=anchors)
    return W
DBG = {}
def _runs(c, val, maxlen):
    """cyclic: runs of (1-val) no longer than maxlen that sit between val-runs become val"""
    c = c.copy(); n = len(c)
    if c.min() == c.max(): return c
    t0 = int(np.argmax(c == val)); t = 0
    while t < n:
        u = (t0 + t) % n
        if c[u] != val:
            L = 0
            while L < n and c[(u + L) % n] != val: L += 1
            if L <= maxlen:
                for o in range(L): c[(u + o) % n] = val
            t += L
        else: t += 1
    return c
def _align(u, v):
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v); ax = np.cross(u, v); sn = np.linalg.norm(ax); cs = float(u @ v)
    return np.eye(3) if sn < 1e-9 else rodrigues((ax / sn * math.atan2(sn, cs))[None])[0]

FINGER_TC = json.load(open(os.path.join(D, 'tools', 'roto', 'finger_tc_bind.json')))['tc']
def apply_finger_tc(clip):
    """finger constant translations = the Hands mesh BIND offsets (what handmade HKX clips carry; Animator QA-006). The skeleton-rest offsets
    (x0.725) pulled the knuckles ~27% into the palm -> bunched palm skin over the finger bases."""
    for b, v in FINGER_TC.items(): clip.setdefault('tc', {})[b] = v
    return clip

def finish(cfg, r):
    anat_limits(r['WT'])   # per-clip limit frames (rest-local elbows/knees); idempotent, also for callers that never ran bake() (roto3_*)
    sk, W, P, idx, WTq, n, fps = r['sk'], r['W'], r['P'], r['idx'], r['WT'], r['n'], r['fps']
    Wraw = W; W, nproj = project_limits(W, WTq, idx); r['W'] = W   # any frame the optimiser left outside a limit is clamped (eased over neighbours)
    if r['ginfo']['feet_tracked'] or os.environ.get('MOCAP_FOOTLOCK') == '1': W = foot_lock(W, Wraw, r['P'], idx, r['cont'], n, WTq); W, _ = project_limits(W, WTq, idx); r['W'] = W   # IK may push the ankle out of range
    nb = len(SF['names']); par = SF['parent']
    # local rotations from final world
    Lm = np.zeros((n, nb, 3, 3))
    for b in range(nb):
        p = par[b]; Lm[:, b] = W[:, b] if p < 0 else np.swapaxes(W[:, p], -1, -2) @ W[:, b]
        if np.abs(W[:, b]).sum() == 0 or (p >= 0 and np.abs(W[:, p]).sum() == 0):   # bone outside the solved FK chain: keep its init local
            Lm[:, b] = q2m(r['L0q'][:, b]) if 'L0q' in r else q2m(np.repeat(np.asarray(SF['q'][b])[None], n, 0))
    info = {}
    for s in 'LR':  # forearm: hinge swing only; its twist moves to the hand + ForearmTwist1/2 (2/3, 1/3) so the forearm skin twists gradually
        fa, ua, hd = idx[s + 'FA'], idx[s + 'UA'], idx[s + 'HD']; Fp, Fb = _frames(s + 'FA', WTq); d = LIMITS[s + 'FA'][0]   # rest-local frames (anat_limits)
        Rrel = np.swapaxes(W[:, ua] @ Fp.T, -1, -2) @ (W[:, fa] @ Fb.T); q = m2q(Rrel)
        tw = 2 * np.arctan2(q[:, :3] @ d, q[:, 3]); Rsw = Rrel @ rodrigues(-d[None] * tw[:, None])
        Wfa = (W[:, ua] @ Fp.T) @ Rsw @ Fb
        Lm[:, fa] = np.swapaxes(W[:, ua], -1, -2) @ Wfa; Lm[:, hd] = np.swapaxes(Wfa, -1, -2) @ W[:, hd]
        Fh = REST_W[s + 'HD'] if REST_W else q2m(WTq[s + 'HD'])
        Rh = np.swapaxes(Wfa @ Fb.T, -1, -2) @ (W[:, hd] @ Fh.T); qh = m2q(Rh); tau = 2 * np.arctan2(qh[:, :3] @ d, qh[:, 3])
        # pronation/supination is continuous and physiologically ~+-90: unwrap the twist over time (no +-180 branch flips from the capture's
        # wrist), keep the loop-mean near 0, clamp to +-95 deg (smoothly), and turn the HAND about the forearm axis by the removed part
        qh = qh * np.sign(qh[:, 3:4] + 1e-12); tau = 2 * np.arctan2(qh[:, :3] @ d, qh[:, 3])   # one hemisphere
        swa = np.degrees(np.linalg.norm(rot_log(Rh @ rodrigues(-d[None] * tau[:, None])), axis=-1)); ok_ = swa < 140   # twist is ill-defined for a hand bent > ~140 deg off the forearm
        tu = np.unwrap(tau)
        if (~ok_).any() and ok_.sum() > 2: tt = np.arange(len(tu)); tu[~ok_] = np.interp(tt[~ok_], tt[ok_], tu[ok_]); info[s + '_wrist_illdefined_frames'] = int((~ok_).sum())
        tu = np.unwrap(tu); tu -= 2 * np.pi * np.round(tu.mean() / (2 * np.pi)); tc = np.radians(95) * np.tanh(tu / np.radians(95))
        tc = sgf(tc, 5); dl = tc - tau; aw = Wfa[:, :, 2]   # forearm bone axis (local Z) in world
        W[:, hd] = rodrigues(aw * dl[:, None]) @ W[:, hd]; Lm[:, hd] = np.swapaxes(Wfa, -1, -2) @ W[:, hd]; tau = tc
        info[s + '_pronation_unwrapped_deg_max'] = round(float(np.degrees(np.abs(tu).max())), 1)
        ax = SF['t'][SF['i'][N[s + 'HD']]]; ax = ax / np.linalg.norm(ax)
        for tb, fr in ((N[s + 'T1'], 2 / 3), (N[s + 'T2'], 1 / 3)):
            b = SF['i'][tb]; Lm[:, b] = rodrigues(ax[None] * (fr * tau)[:, None]) @ q2m(SF['q'][b])[None]
        info[s + '_wrist_twist_deg_p95'] = round(float(np.percentile(np.abs(np.degrees(tau)), 95)), 1)
    for s in 'LR':  # calf: hinge swing only; its twist goes to the foot (the rig never twists the shin - reads as a twisted knee).
        # foot WORLD rotation unchanged -> knee/ankle/foot positions identical (twist is about the shin axis)
        cf, th, ft = idx[s + 'CF'], idx[s + 'TH'], idx[s + 'FT']; Fp, Fb = _frames(s + 'CF', WTq); d = LIMITS[s + 'CF'][0]
        Rrel = np.swapaxes(W[:, th] @ Fp.T, -1, -2) @ (W[:, cf] @ Fb.T); q = m2q(Rrel); tw = 2 * np.arctan2(q[:, :3] @ d, q[:, 3])
        Wcf = (W[:, th] @ Fp.T) @ (Rrel @ rodrigues(-d[None] * tw[:, None])) @ Fb
        Lm[:, cf] = np.swapaxes(W[:, th], -1, -2) @ Wcf; Lm[:, ft] = np.swapaxes(Wcf, -1, -2) @ W[:, ft]
        info[s + '_calf_twist_to_foot_deg_p95'] = round(float(np.percentile(np.abs(np.degrees(tw)), 95)), 1)
        Rf = np.swapaxes(Wcf @ Fb.T, -1, -2) @ (W[:, ft] @ REST_W[s + 'FT'].T); qf = m2q(Rf); twf = 2 * np.arctan2(qf[:, :3] @ d, qf[:, 3])   # ankle axial twist (about the shin axis), rest-relative
        info[s + '_ankle_twist_deg_p95'] = round(float(np.percentile(np.abs(np.degrees(twf)), 95)), 1)
    Q = m2q(Lm); T = sk.T.cpu().double().numpy().copy(); T[:, SF['i'][N['COM']]] += r['droot'].double().numpy()
    Pf = R.Pose(SF, Q, T)
    keep = {N[k] for k in OPT} | {N['PEL'], N['LTOE'], N['RTOE']} | {N[s + t] for s in 'LR' for t in ('T1', 'T2')} | {nm for nm in SF['names'] if 'Finger' in nm}
    clip = R.encode(Pf, fps, keep, extra_t=(N['COM'],))
    apply_finger_tc(clip)
    # metrics on the final pose (after the twist split)
    Wf = q2m(Pf.WQ); Pp = Pf.WP; Wt_ = t_(Wf); Pt_ = t_(Pp)
    with torch.no_grad(): _, rep = collide(Wt_, Pt_, idx, r['sk'].ws, report=True)
    pen = {k: dict(max_mm=round(float(v.max()), 1), frames_over_5mm=int((v > 5).sum()), frames_over_10mm=int((v > 10).sum())) for k, v in rep.items() if v.max() > 0}
    _, viol, comps = limit_terms(t_(W), {k: t_(q2m(WTq[k])) for k in OPT}, idx)   # anatomical limits: before the forearm-twist split (which moves pronation into hand + twist bones by design)
    lim = {k: int((np.sqrt(v.detach().cpu().numpy()) > math.radians(1)).sum()) for k, v in viol.items()}
    sk_ = {}; sole_z = {}
    for s in 'LR':
        fb = idx[s + 'FT']; so = sole_points(s); sp = Pp[:, fb][:, None] + np.einsum('nij,kj->nki', Wf[:, fb], so * float(r['sk'].ws[fb].item()))
        c = (r['cont'][s] > .5) & (np.roll(r['cont'][s], 1) > .5); d = np.linalg.norm(sp[:, :, :2] - np.roll(sp[:, :, :2], 1, 0), axis=-1).max(-1)
        zsole = sp[..., 2].min(-1); sole_z[s] = zsole
        sk_[s] = dict(contact_frac=round(float(r['cont'][s].mean()), 2), skate_cm_max=round(float(d[c].max() / U * 100) if c.any() else 0, 2), skate_cm_mean=round(float(d[c].mean() / U * 100) if c.any() else 0, 3),
                      floor_pen_mm=round(float(max(0, -sp[..., 2].min()) / U * 1000), 1))
    lowest = np.minimum(sole_z['L'], sole_z['R']) / U * 100; sk_['lowest_sole_cm_p95'] = round(float(np.percentile(lowest, 95)), 2); sk_['lowest_sole_cm_max'] = round(float(lowest.max()), 2)
    pel_est = pelvis_angles(r['Gc'][:, 0] @ q2m(WTq['COM'])[None]); pel_out = pelvis_angles(Wf[:, idx['COM']])
    rlog = dict(rel_err_cm={k: v for k, v in r.get('relerr', {}).items()}, name=cfg['name'], src_frames=int(len(r['F']['pose'])), fps=round(fps, 3), loop=r['loop'], frames=n, dur_s=round(n / fps, 2), ground=r['ginfo'], leg_scale=round(float(r['sc']), 3),
                penetration=pen, limit_violation_frames=lim, total_limit_violation_frames=int(sum(lim.values())), feet=sk_, pelvis_range_deg_estimate=pel_est, pelvis_range_deg_clip=pel_out,
                loss_hist=[r['hist'][0], r['hist'][-1]], limit_projected_frames=nproj, **info)
    return clip, rlog

def write(C, names):
    out = os.path.join(A, 'anims', 'dance3d.js')
    if os.path.exists(out):  # keep clips not re-baked this run (same file)
        s = open(out, encoding='utf-8').read(); k0 = s.index('window.RB_DANCE3D=') + 18; old = json.JSONDecoder().raw_decode(s[k0:])[0]
        for k, v in old['clips'].items():
            if k in names: C.setdefault(k, v)
        for k, v in old.get('log', {}).items():
            if k in names: LOG.setdefault(k, v)
    C = {k: C[k] for k in sorted(C) if k in names}
    js = ('/* generated by tools/roto/mocap_bake.py: daily-life dances from body-model mocap (NLF SMPL-X fits of reference videos, motion only) retargeted + optimised on the XPMSSE skeleton. Clip format = tools/anims3d.py. */\n'
          'window.RB_DANCE3D=' + json.dumps({'clips': C, 'names': {k: names[k] for k in C}, 'log': {k: LOG[k] for k in C if k in LOG}}, separators=(',', ':')) + ';\n'
          + open(os.path.join(D, 'tools', 'roto', 'dance3d_tail.js'), encoding='utf-8').read())
    open(out, 'w', encoding='utf-8').write(js); print('wrote', out, round(os.path.getsize(out) / 1e3, 1), 'KB', list(C))

if __name__ == '__main__':
    C = {}; names = {c['id']: c['name'] for c in DANCES}
    lp = os.path.join(D, 'tools', 'roto', 'mocap_bake_log.json' if SRC == 'nlf' else 'mocap_bake_log_%s.json' % SRC)
    if os.path.exists(lp): LOG.update(json.load(open(lp)))
    for cfg in DANCES + ROTO_SOLO:
        if (ONLY and cfg['id'] not in ONLY) or (not ONLY and cfg['id'].startswith('roto_')): continue
        if not os.path.exists(os.path.join(D, 'tools', 'roto', KP_DIR, cfg['id'] + '.npz')): print('skip (no fit)', cfg['id']); continue
        r = bake(cfg)
        import pickle; os.makedirs(os.path.join(D, 'tools', 'roto', 'mocap_raw'), exist_ok=True)   # raw solve (before limit projection / encode) so finish() can be iterated without re-baking
        pickle.dump(dict({k: v for k, v in r.items() if k != 'sk'}, skT=r['sk'].T.cpu().numpy(), skws=r['sk'].ws.cpu().numpy()), open(os.path.join(D, 'tools', 'roto', 'mocap_raw', cfg['id'] + '.pkl'), 'wb'))
        # (a CUDA error ends the process: tools/roto/mocap_run.sh then redoes that clip on the CPU in a fresh process
        clip, rl = finish(cfg, r); C[cfg['id']] = clip; LOG[cfg['id']] = rl
        os.makedirs(os.path.join(D, 'tools', 'roto', CLIP_DIR), exist_ok=True)   # per-clip results, so separate / interrupted runs keep finished clips
        json.dump({'clip': clip, 'log': rl}, open(os.path.join(D, 'tools', 'roto', CLIP_DIR, cfg['id'] + '.json'), 'w'), separators=(',', ':'))
        print(cfg['id'], json.dumps({k: rl[k] for k in ('dur_s', 'loop', 'total_limit_violation_frames', 'feet', 'pelvis_range_deg_estimate', 'pelvis_range_deg_clip')}))
        json.dump(LOG, open(lp, 'w'), indent=1)
    if SRC != 'nlf': print('comparison source', SRC, '-> per-clip results only in tools/roto/' + CLIP_DIR); sys.exit(0)
    # (no merging of other per-clip results: staged experiments must never leak into the game file)
    json.dump({k: v for k, v in LOG.items() if not k.startswith('roto_')}, open(lp, 'w'), indent=1)
    RC = {k: v for k, v in C.items() if k.startswith('roto_')}
    if RC:
        rp = os.path.join(D, 'tools', 'roto', 'roto_mocap.json'); old = json.load(open(rp)) if os.path.exists(rp) else {}
        old.update(RC); json.dump(old, open(rp, 'w'), separators=(',', ':')); print('wrote roto_mocap.json', list(old))
    C = {k: v for k, v in C.items() if not k.startswith('roto_')}
    if C and os.environ.get('MOCAP_PROMOTE') == '1': write(C, names)   # default = STAGED (per-clip result only); the game file is written only by an explicit, QA-gated promote
