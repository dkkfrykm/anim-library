"""Optical-flow / keypoint measurements for the roto3 clips (motion only: numbers, no pixels are written anywhere).
Each region (box annotated on frame 0 in full-res px) is tracked through the clip with DIS dense optical flow; per frame a weighted
least-squares AFFINE fit of the flow inside the box gives translation + linear part (scale x/y, rotation); the box follows its own motion.
Clip 'prone'  (4dc1fb80): glutes L/R, thighs, waist band, upper back, head -> pelvis rigid motion, glute residual (jiggle), breathing, head turns.
Clip 'grope'  (8ae180ab): breasts L/R (tracked), partner's hands (green HSV mask: medial reach, vertical centre/extent, area), her head /
              shoulders / waist / wrist cuffs (red gem keypoints) -> squeeze rhythm, hand paths in each breast's normalised frame, breast deformation
              (affine scale/translation of the breast surface flow), her reaction motion.
Usage: python roto3_measure.py <reiko_breed dir> <video prone> <video grope>  -> tools/roto/roto3_measure.json"""
import sys, os, json
import numpy as np, cv2

D = os.path.abspath(sys.argv[1]); VID = {'prone': sys.argv[2], 'grope': sys.argv[3]}
SC = {'prone': .5, 'grope': .4}   # analysis scale (flow on downscaled grey frames)
# regions: full-res px boxes on frame 0 (x0, y0, x1, y1); her L/R = anatomical (prone, seen from her feet: screen-left = her L; grope, front view: screen-left = her R)
REG = {'prone': {'gluteL': (420, 640, 700, 880), 'gluteR': (780, 620, 1080, 880), 'thighL': (280, 980, 600, 1240), 'thighR': (720, 1020, 1040, 1300),
                 'waist': (940, 520, 1160, 600), 'back': (900, 400, 1300, 500), 'head': (1000, 60, 1250, 300), 'anc': (150, 80, 340, 520)},   # anc: background poles (static scenery)
       'grope': {'breastR': (300, 840, 660, 1320), 'breastL': (760, 840, 1110, 1320), 'head': (560, 260, 900, 700), 'shL': (1000, 780, 1160, 900), 'shR': (280, 780, 440, 900),
                 'waist': (540, 1380, 900, 1560), 'anc': (1250, 150, 1430, 500)}}
GLUTE_C = {'L': (560, 760), 'R': (930, 750)}

def frames(path, sc):
    c = cv2.VideoCapture(path); fps = c.get(5); out = []
    while True:
        ok, f = c.read()
        if not ok: break
        out.append(cv2.resize(f, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA))
    return out, fps

def affine_fit(fl, wgt, x0, y0, x1, y1):
    ys, xs = np.mgrid[y0:y1:2, x0:x1:2]; u = fl[y0:y1:2, x0:x1:2, 0].ravel(); v = fl[y0:y1:2, x0:x1:2, 1].ravel(); w = wgt[y0:y1:2, x0:x1:2].ravel()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; X = np.stack([np.ones_like(u), (xs.ravel() - cx), (ys.ravel() - cy)], 1); sw = np.sqrt(w)[:, None]
    au = np.linalg.lstsq(X * sw, u * sw[:, 0], rcond=None)[0]; av = np.linalg.lstsq(X * sw, v * sw[:, 0], rcond=None)[0]
    return np.array([au[0], av[0], au[1], au[2], av[1], av[2]])   # tx, ty, dux/dx, dux/dy, dvy/dx, dvy/dy

def track(fr, boxes, sc):
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM); B = {k: np.array(b, float) * sc for k, b in boxes.items()}
    P = {k: [[(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]] for k, b in B.items()}; S = {k: [[1.0, 1.0, 0.0]] for k in B}   # cumulative scale x / y, rotation (rad)
    prev = cv2.cvtColor(fr[0], cv2.COLOR_BGR2GRAY); H, W = prev.shape; FL = None
    for f in range(1, len(fr)):
        cur = cv2.cvtColor(fr[f], cv2.COLOR_BGR2GRAY); fl = dis.calc(prev, cur, None)
        gx = cv2.Sobel(prev, cv2.CV_32F, 1, 0); gy = cv2.Sobel(prev, cv2.CV_32F, 0, 1); wgt = np.sqrt(gx * gx + gy * gy) + 2
        for k, b in B.items():
            x0, y0, x1, y1 = [int(round(t)) for t in b]; x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
            a = affine_fit(fl, wgt, x0, y0, x1, y1) if x1 - x0 > 6 and y1 - y0 > 6 else np.zeros(6)
            b += [a[0], a[1], a[0], a[1]]; p = P[k][-1]; P[k].append([p[0] + a[0], p[1] + a[1]])
            s = S[k][-1]; S[k].append([s[0] * (1 + a[2]), s[1] * (1 + a[5]), s[2] + (a[4] - a[3]) / 2])
        prev = cur
    return {k: np.array(v) / sc for k, v in P.items()}, {k: np.array(v) for k, v in S.items()}, FL

def to30(x, fps):  # resample a [n,...] series to 30 fps (linear)
    n = len(x); t = np.arange(n) / fps; t2 = np.arange(0, t[-1], 1 / 30); x = np.asarray(x, float)
    return np.stack([np.interp(t2, t, x[:, j]) for j in range(x.shape[1])], 1) if x.ndim == 2 else np.interp(t2, t, x)

def hp(x, fps, sec):  # high-pass: minus a centred moving average of `sec`
    k = max(3, int(fps * sec) | 1); pad = k // 2; xp = np.pad(x, ((pad, pad),) + ((0, 0),) * (x.ndim - 1), mode='edge'); ker = np.ones(k) / k
    lo = np.stack([np.convolve(xp[:, j], ker, 'valid') for j in range(x.shape[1])], 1) if x.ndim == 2 else np.convolve(xp, ker, 'valid'); return x - lo, lo

def arx2(r, u):
    """system id: r[t] = a1 r[t-1] + a2 r[t-2] + b0 u[t] + b1 u[t-1]  (least squares) -> discrete poles -> natural freq (Hz @ given fps) + damping ratio"""
    Y = r[2:]; X = np.stack([r[1:-1], r[:-2], u[2:], u[1:-1]], 1); th, *_ = np.linalg.lstsq(X, Y, rcond=None); res = Y - X @ th
    return th, float(1 - res.var() / max(1e-12, Y.var()))

def poles_to_fz(a1, a2, fps):
    z = np.roots([1, -a1, -a2]); z = z[np.argmax(np.abs(z.imag))] if np.any(np.abs(z.imag) > 1e-9) else z[0]
    s = np.log(z.astype(complex)) * fps; wn = abs(s); zeta = -s.real / max(1e-9, wn); return float(wn / (2 * np.pi)), float(zeta)

def measure_prone():
    fr, fps = frames(VID['prone'], SC['prone']); P, S, FL = track(fr, REG['prone'], SC['prone']); n = len(fr)
    anc = P['anc'] - P['anc'][0]; P = {k: v - anc for k, v in P.items()}   # camera-shake reference (static bed corner): ~0 if the camera is locked
    hipw = abs(GLUTE_C['R'][0] - GLUTE_C['L'][0]) * 2   # ~ glute-centre spacing x2 ~ hip width in px (scale reference)
    gl, gr = P['gluteL'] - P['gluteL'][0], P['gluteR'] - P['gluteR'][0]
    thl, thr, wa = P['thighL'] - P['thighL'][0], P['thighR'] - P['thighR'][0], P['waist'] - P['waist'][0]
    # rigid pelvis estimate (bone-carried, low tissue): waist band + upper thighs + low-passed glute centres
    rig = (wa + (thl + thr) / 2) / 2
    gm = (gl + gr) / 2; _, gm_lo = hp(gm, fps, .5)
    pel = .5 * rig + .5 * gm_lo   # pelvis: rigid carriers + slow part of the glute motion
    roll = np.arctan2(-(gr[:, 1] - gl[:, 1]), hipw * .5)   # glute heights differ -> pelvis roll about her long axis (rad, + = her R side up)
    _, roll_lo = hp(roll, fps, .4)
    # jiggle: each glute's motion minus the pelvis (rigid) motion at its centre, high-passed (> ~1.3 Hz)
    res = {}
    for s, g in (('L', gl), ('R', gr)):
        side = -1 if s == 'L' else 1; carried = pel.copy(); carried[:, 1] += -side * roll_lo * hipw * .25   # roll lifts one side
        r, _ = hp(g - carried, fps, .75); res[s] = r
    acc = np.gradient(np.gradient(pel[:, 1])) * fps * fps   # pelvis vertical acceleration (px/s^2), the drive
    accx = np.gradient(np.gradient(pel[:, 0])) * fps * fps
    ids = {}
    for s in 'LR':
        for ax, u in ((1, acc), (0, accx)):
            dd = 4; r_ = res[s][::dd, ax]; u_ = u[::dd] / (fps / dd) ** 2   # at 15 fps: a smooth 60 fps signal makes AR(2) fit the smoothness, not the dynamics
            th, r2 = arx2(r_, u_); f0, z = poles_to_fz(th[0], th[1], fps / dd); ids[s + 'xy'[ax]] = dict(f_hz=round(f0, 2), zeta=round(z, 3), r2=round(r2, 3))
    # spectrum of the residual (both glutes, vertical): peak frequency
    rv = (res['L'][:, 1] + res['R'][:, 1]) / 2; F_ = np.abs(np.fft.rfft(rv * np.hanning(len(rv)))); fq = np.fft.rfftfreq(len(rv), 1 / fps); band = (fq > .8) & (fq < 8)
    fpk = float(fq[band][np.argmax(F_[band])])
    # breathing: upper back vertical (rel. to waist), band 0.15-0.6 Hz
    br = (P['back'][:, 1] - P['waist'][:, 1]); br = br - br.mean(); Fb = np.abs(np.fft.rfft(br * np.hanning(n))); fb = np.fft.rfftfreq(n, 1 / fps); bb = (fb > .12) & (fb < .7)
    breath_hz = float(fb[bb][np.argmax(Fb[bb])])
    head = P['head'] - P['head'][0]; hrot = S['head'][:, 2]
    norm = lambda x: (np.asarray(x) / hipw)   # -> fraction of hip width
    out = dict(fps=fps, frames=n, scale_ref=dict(hip_width_px=hipw, note='positions as fraction of hip width; her hip width in game converts to units'),
               camera_shake_px=round(float(np.abs(anc).max()), 2),
               series30=dict(pel_x=np.round(to30(norm(pel[:, 0]), fps), 5).tolist(), pel_y=np.round(to30(norm(pel[:, 1]), fps), 5).tolist(),
                             roll=np.round(to30(roll_lo, fps), 5).tolist(),
                             gluteL_res=np.round(to30(norm(res['L']), fps), 5).tolist(), gluteR_res=np.round(to30(norm(res['R']), fps), 5).tolist(),
                             thighL=np.round(to30(norm(thl), fps), 5).tolist(), thighR=np.round(to30(norm(thr), fps), 5).tolist(),
                             back_y=np.round(to30(norm(br), fps), 5).tolist(), head=np.round(to30(norm(head), fps), 5).tolist(), head_rot=np.round(to30(hrot, fps), 5).tolist()),
               jiggle=dict(arx=ids, residual_peak_hz=round(fpk, 2), residual_rms=dict(L=np.round(norm(res['L']).std(0), 5).tolist(), R=np.round(norm(res['R']).std(0), 5).tolist()),
                           pelvis_acc_rms_hipw_s2=round(float(norm(acc).std()), 4)),
               breath_hz=round(breath_hz, 3),
               ranges=dict(pel_x=round(float(np.ptp(norm(pel[:, 0]))), 4), pel_y=round(float(np.ptp(norm(pel[:, 1]))), 4), roll_deg=round(float(np.degrees(np.ptp(roll_lo))), 2),
                           thighL=np.round(np.ptp(norm(thl), 0), 4).tolist(), thighR=np.round(np.ptp(norm(thr), 0), 4).tolist(), head=np.round(np.ptp(norm(head), 0), 4).tolist(),
                           head_rot_deg=round(float(np.degrees(np.ptp(hrot))), 2), back_y=round(float(np.ptp(norm(br))), 4)))
    return out

def green_mask(f):
    h = cv2.cvtColor(f, cv2.COLOR_BGR2HSV); return ((h[..., 0] > 30) & (h[..., 0] < 90) & (h[..., 1] > 50) & (h[..., 2] > 40))
def red_pts(f, sc):   # wrist-cuff gems: saturated red blobs, one per side of the midline
    h = cv2.cvtColor(f, cv2.COLOR_BGR2HSV); m = (((h[..., 0] < 8) | (h[..., 0] > 172)) & (h[..., 1] > 120) & (h[..., 2] > 90)).astype(np.uint8)
    H, W = m.shape; m[: int(H * .6)] = 0; out = []
    for x0, x1 in ((0, W // 2), (W // 2, W)):
        ys, xs = np.nonzero(m[:, x0:x1]); out.append([xs.mean() + x0, ys.mean()] if len(xs) > 20 else [np.nan, np.nan])
    return np.array(out) / sc

def measure_grope():
    sc = SC['grope']; fr, fps = frames(VID['grope'], sc); P, S, FL = track(fr, REG['grope'], sc); n = len(fr)
    anc = P['anc'] - P['anc'][0]; P = {k: v - anc for k, v in P.items()}
    mid0 = 720.0; shw = 1160 - 280.0   # midline, shoulder width px (frame 0 annotation)
    br = {'R': np.array(REG['grope']['breastR'], float), 'L': np.array(REG['grope']['breastL'], float)}
    hands = {s: [] for s in 'LR'}; gems = []
    for f in range(n):
        g = green_mask(fr[f]); H, W = g.shape; gems.append(red_pts(fr[f], sc))
        for s, sgn in (('R', -1), ('L', 1)):   # her R = screen left
            c = P['breast' + s][f]; b = br[s]; hw, hh = (b[2] - b[0]) / 2, (b[3] - b[1]) / 2
            # breast-local window: the hand at this breast (forearm further out excluded): |dx| <= 1.6 half-widths, |dy| <= 1.2 half-heights
            x0 = int(max(0, (c[0] - 1.9 * hw) * sc)); x1 = int(min(W, (c[0] + 1.9 * hw) * sc)); y0 = int(max(0, (c[1] - 1.25 * hh) * sc)); y1 = int(min(H, (c[1] + 1.25 * hh) * sc))
            ys, xs = np.nonzero(g[y0:y1, x0:x1]); xs = (xs + x0) / sc; ys = (ys + y0) / sc
            if len(xs) < 30: hands[s].append([np.nan] * 7); continue
            dx = (xs - c[0]) / hw * sgn * -1   # + = toward her midline (medial)
            dy = (ys - c[1]) / hh             # + = down
            k = dx > np.percentile(dx, 70)    # the medial 30%: fingers / palm on the breast, not the forearm
            hands[s].append([np.percentile(dx, 97), dy[k].mean(), np.percentile(dy[k], 5), np.percentile(dy[k], 95), dx[k].mean(), len(xs) * 1.0, (dx > -1.0).mean()])
    hands = {s: np.array(v) for s, v in hands.items()}; gems = np.array(gems)
    for s in 'LR':   # fill tracking gaps
        h = hands[s]
        for j in range(h.shape[1]):
            bad = np.isnan(h[:, j])
            if bad.any() and (~bad).any(): h[bad, j] = np.interp(np.nonzero(bad)[0], np.nonzero(~bad)[0], h[~bad, j])
    # squeeze rhythm: medial reach (fingertips toward the midline) + breast horizontal compression; dominant period by autocorrelation
    reach = (hands['L'][:, 0] + hands['R'][:, 0]) / 2; comp = -((S['breastL'][:, 0] - 1) + (S['breastR'][:, 0] - 1)) / 2
    def period(x):
        x = x - x.mean(); ac = np.correlate(x, x, 'full')[len(x) - 1:]; ac /= ac[0]; lo = int(fps * .5); hi = int(fps * 4); k = lo + int(np.argmax(ac[lo:hi])); return k / fps, float(ac[k])
    pr, pr_q = period(reach); pc, pc_q = period(comp)
    head = (P['head'] - P['head'][0]) / shw; shl = (P['shL'] - P['shL'][0]) / shw; shr = (P['shR'] - P['shR'][0]) / shw; wa = (P['waist'] - P['waist'][0]) / shw
    gem = (gems - gems[0]) / shw
    bL = (P['breastL'] - P['breastL'][0]); bR = (P['breastR'] - P['breastR'][0])
    hwb = {s: (br[s][2] - br[s][0]) / 2 for s in 'LR'}; hhb = {s: (br[s][3] - br[s][1]) / 2 for s in 'LR'}
    out = dict(fps=fps, frames=n, scale_ref=dict(shoulder_width_px=shw, breast_half_w_px={s: hwb[s] for s in 'LR'}, breast_half_h_px={s: hhb[s] for s in 'LR'}),
               camera_shake_px=round(float(np.abs(anc).max()), 2),
               squeeze=dict(period_reach_s=round(pr, 3), ac_reach=round(pr_q, 3), period_breast_comp_s=round(pc, 3), ac_comp=round(pc_q, 3)),
               series30={**{'hand' + s: np.round(to30(hands[s][:, :5], fps), 4).tolist() for s in 'LR'},   # [medial reach, v-centre, top, bottom, mean dx] in breast half-sizes
                         **{'breast' + s + '_t': np.round(to30(np.stack([(P['breast' + s] - P['breast' + s][0])[:, 0] / hwb[s] * (1 if s == 'L' else -1) * -1, (P['breast' + s] - P['breast' + s][0])[:, 1] / hhb[s]], 1), fps), 4).tolist() for s in 'LR'},   # + x = medial, + y = down
                         **{'breast' + s + '_s': np.round(to30(S['breast' + s][:, :2], fps), 4).tolist() for s in 'LR'},
                         'head': np.round(to30(head, fps), 4).tolist(), 'head_rot': np.round(to30(S['head'][:, 2], fps), 4).tolist(),
                         'shL': np.round(to30(shl, fps), 4).tolist(), 'shR': np.round(to30(shr, fps), 4).tolist(), 'waist': np.round(to30(wa, fps), 4).tolist(),
                         'gems': np.round(to30(gem.reshape(n, 4), fps), 4).tolist()},
               ranges=dict(head=np.round(np.ptp(head, 0), 4).tolist(), head_rot_deg=round(float(np.degrees(np.ptp(S['head'][:, 2]))), 2), shL=np.round(np.ptp(shl, 0), 4).tolist(), shR=np.round(np.ptp(shr, 0), 4).tolist(),
                           waist=np.round(np.ptp(wa, 0), 4).tolist(), handL=np.round(np.nanmax(hands['L'][:, :5], 0) - np.nanmin(hands['L'][:, :5], 0), 3).tolist(), handR=np.round(np.nanmax(hands['R'][:, :5], 0) - np.nanmin(hands['R'][:, :5], 0), 3).tolist(),
                           breastL_scale=np.round(np.ptp(S['breastL'][:, :2], 0), 4).tolist(), breastR_scale=np.round(np.ptp(S['breastR'][:, :2], 0), 4).tolist(),
                           breastL_t=[round(float(np.ptp(bL[:, 0]) / hwb['L']), 4), round(float(np.ptp(bL[:, 1]) / hhb['L']), 4)], breastR_t=[round(float(np.ptp(bR[:, 0]) / hwb['R']), 4), round(float(np.ptp(bR[:, 1]) / hhb['R']), 4)]))
    return out

if __name__ == '__main__':
    which = sys.argv[4].split(',') if len(sys.argv) > 4 else ['prone', 'grope']
    op = os.path.join(D, 'tools', 'roto', 'roto3_measure.json'); M = json.load(open(op)) if os.path.exists(op) else {}
    for w in which:
        M[w] = measure_prone() if w == 'prone' else measure_grope(); print(w, json.dumps({k: v for k, v in M[w].items() if k not in ('series30',)})[:1500])
    json.dump(M, open(op, 'w'), indent=0)
