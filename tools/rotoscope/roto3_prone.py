"""Lying-prone phone idle ('roto_prone_idle', daily view) from 4dc1fb80 (motion only).
  posture + slow shifts / head turns: NLF SMPL-X per-frame fit (60 fps -> 30 fps), retargeted with mocap_bake/mocap_lib (imported, unmodified),
     in a BED frame (plane through the fitted elbows / knees / ankles, up = away from her front; +Y = toward her head), low-passed (single-frame
     estimator noise on this foreshortened view ~15 mm)
  fine motion: roto3_measure.json['prone'] (DIS optical flow, affine per region): pelvis translation + roll, thigh shifts, breathing (upper back),
     high-passed and layered on the fit (complementary filter: fit below ~1 Hz, flow above)
  whole-clip torch optimisation: rotation data + anatomical limits (mocap_bake.LIMITS) + arm/hand-vs-skin collision (mocap_bake.collide, swept)
     + mattress (her skin points of every carrier bone never below the mattress plane; pelvis/thighs, knees/shins, elbows/forearms resting on it)
     + cyclic smoothness; then mocap_bake.finish (hard limit projection, forearm twist split, encode, penetration/limit metrics)
  soft tissue: glute jiggle frequency / damping measured (ARX on glute-minus-pelvis residual vs pelvis acceleration) -> RB_PHYS per-clip Butt tune
     (multipliers that make phys3d's CBPC spring at Bounce5 ring at the measured frequency / damping ratio)
Writes tools/roto/roto3_clips.json['roto_prone_idle'] (+ log) — merged into web/assets/anims/roto3d.js by roto_bake.py.
Usage: <torch venv python> tools/roto/roto3_prone.py <reiko_breed dir> <nlf 60fps npz>"""
import sys, os, json, math, time
D = os.path.abspath(sys.argv[1]); SRC = sys.argv[2]
sys.argv = [sys.argv[0], D]; sys.path.insert(0, os.path.join(D, 'tools', 'roto'))
import numpy as np
import mocap_bake as MB
import mocap_lib as M
from mocap_lib import N, MCAM, MCAN, U, nrm, rodrigues, m2q, q2m, rot_log
from roto3_lib import decimate
R = MB.R; SF = MB.SF; torch = MB.torch; OPT = MB.OPT
ID = 'roto3_prone'; X3, Y3, Z3 = np.eye(3)

def bed_frame(F):
    J = F['J']; Jc = np.einsum('ij,ntj->nti', MCAM, J); Gs = np.einsum('ij,ntjk,lk->ntil', MCAM, F['G'], MCAN)
    front = nrm(np.median(nrm(np.einsum('nij,j->ni', Gs[:, 0], Y3)), 0))            # pelvis +Y local = her front
    C = [4, 5, 7, 8, 18, 19]; pts = Jc[:, C].reshape(-1, 3); c = np.median(pts, 0)
    _, _, vt = np.linalg.svd(pts - c); n = vt[2] * (-np.sign(vt[2] @ front))           # bed normal = away from her front
    head = nrm(np.median(nrm(Jc[:, 15] - Jc[:, 0]), 0)); fh = nrm(head - (head @ n) * n)
    Rg = np.stack([np.cross(fh, n), fh, n]); Jg = np.einsum('ij,ntj->nti', Rg, Jc); Gg = np.einsum('ij,ntjk->ntik', Rg, Gs)
    Jg[..., 2] -= np.median(Jg[:, C, 2]) - 3.0
    return Jg, Gg, dict(bed_normal_vs_front_deg=round(float(np.degrees(np.arccos(np.clip(-n @ front, -1, 1)))), 1), contact_plane_rms_cm=round(float(np.sqrt(((pts - c) @ n).var()) / 10), 2))

def hp(x, win):  # minus a cyclic moving average (frames)
    k = int(win) | 1; xp = np.concatenate([x[-k:], x, x[:k]]); ker = np.ones(k) / k
    lo = np.stack([np.convolve(xp[:, j], ker, 'same') for j in range(x.shape[1])], 1) if x.ndim == 2 else np.convolve(xp, ker, 'same'); return x - lo[k:-k]

def rot_subtree_targets(Wt, keys, Rm):
    for k in keys: Wt[k] = Rm @ Wt[k]

def bake(iters=(500, 300, 600, 300)):
    t0 = time.time(); F = MB.load_fit(ID); fps = F['fps']; Jg, Gg, ginfo = bed_frame(F)
    B = int(round(fps * .6)); i, j = MB.loop_window(Jg, Gg, fps, .55, B); Jc, Gc = MB.crop_blend(Jg, Gg, i, j, B); n = len(Jc)
    # low-pass the fit: trunk/legs ~1.0 s, arms .6 s, neck/head .35 s (head turns are real and big in frame)
    win = {0: 1.0, 3: 1.0, 6: 1.0, 9: 1.0, 1: 1.0, 2: 1.0, 4: 1.0, 5: 1.0, 7: 1.0, 8: 1.0, 10: 1.0, 11: 1.0, 12: .35, 15: .35, 13: .6, 14: .6, 16: .6, 17: .6, 18: .6, 19: .6, 20: .6, 21: .6}
    Gc = np.stack([MB.smooth_rot(Gc[:, k], int(fps * win.get(k, .6))) for k in range(22)], 1)
    off = M.smpl_rest_offsets(F['G'], F['J']); PT, WTq = M.build_tpose(R, SF, off); Wt = MB.world_targets(Gc, WTq)
    # legs: the shins/feet are out of shot and the fit's leg joints carry 350-600 mm uncertainty (it guessed one knee lifted ~20 cm and splayed);
    # the visible thighs lie on the mattress, so the legs get a lying prior instead: thighs/shins along the bed (slightly apart, knees ~10 deg
    # flexed), kneecaps down, feet pointed (tops of the feet on the bed); the measured thigh shifts (flow) are layered on below
    can = lambda v: MCAN @ np.asarray(v, float)
    for s_, sg in (('L', -1), ('R', 1)):
        ab = math.radians(4) * sg; dth = nrm(np.array([math.sin(ab), -math.cos(ab), -.10])); dcf = nrm(np.array([math.sin(ab) * .5, -1, .08])); a_ = math.radians(42)
        dft = np.array([0, -math.cos(a_), -math.sin(a_)])
        kn, an, ft = (4, 7, 10) if s_ == 'L' else (5, 8, 11)
        for key, rest, want, sec_r, sec_w in ((s_ + 'TH', nrm(can(off[kn])), dth, Y3, -Z3), (s_ + 'CF', nrm(can(off[an])), dcf, Y3, -Z3), (s_ + 'FT', nrm(can(off[ft])), dft, X3, X3)):
            Rm = M.frame(want, sec_w) @ M.frame(rest, sec_r).T; Wt[key] = np.repeat((Rm @ q2m(WTq[key]))[None], n, 0)
    # ---- flow layer (high-passed > ~1 Hz band edge: 1.0 s cyclic moving average removed), same 30 fps timeline, same crop ----
    MS = json.load(open(os.path.join(D, 'tools', 'roto', 'roto3_measure.json')))['prone']; S30 = MS['series30']
    def ser(k): a = np.asarray(S30[k], float); a = a[:len(F['pose'])]; a = np.concatenate([a, np.repeat(a[-1:], len(F['pose']) - len(a), 0)]) if len(a) < len(F['pose']) else a; return a[i:j]
    hipw = 2 * np.linalg.norm(SF['t'][SF['i'][N['RTH']]] - SF['t'][SF['i'][N['LTH']]])   # her hip width (units) ~ 2x hip-joint spacing (same definition as the video's)
    W1 = int(fps * 1.0)
    px, py, roll = hp(ser('pel_x'), W1) * hipw, hp(ser('pel_y'), W1) * hipw, hp(ser('roll'), W1)
    thL, thR, back = hp(ser('thighL'), W1) * hipw, hp(ser('thighR'), W1) * hipw, ser('back_y') * hipw; back = back - back.mean()
    lay = dict(_py=py.copy(), pel_lat_cm_ptp=round(float(np.ptp(px)) / U * 100, 2), pel_up_cm_ptp=round(float(np.ptp(py)) / U * 100, 2), roll_deg_ptp=round(float(np.degrees(np.ptp(roll))), 2), breath_cm_ptp=round(float(np.ptp(back)) / U * 100, 2))
    # roll about her long axis (+Y): her R side up -> rotation about +Y by -roll; spine takes it out gradually
    for k, w in (('COM', 1), ('LTH', 1), ('RTH', 1), ('LCF', 1), ('RCF', 1), ('LFT', 1), ('RFT', 1), ('SP0', .6), ('SP1', .3)):
        rot_subtree_targets(Wt, [k], rodrigues(-Y3[None] * (roll * w)[:, None]))
    thl = np.linalg.norm(SF['t'][SF['i'][N['LCF']]])
    for s, th in (('L', thL), ('R', thR)):   # region centre ~45% down the thigh: lateral shift -> abduction about Z, vertical (screen up = lift) about X
        a_ab = th[:, 0] / (.45 * thl); a_lf = th[:, 1] / (.45 * thl)
        Rm = rodrigues(Z3[None] * (a_ab * (1 if s == 'R' else 1))[:, None]) @ rodrigues(X3[None] * (a_lf)[:, None])
        rot_subtree_targets(Wt, [s + 'TH', s + 'CF', s + 'FT'], Rm)
    br = -back / 25.0   # chest rise over ~25 units of spine lever -> extension angle (rad), about her lateral axis
    for k, w in (('SP1', .5), ('SP2', 1.0), ('NECK', 1.0), ('HEAD', 1.0), ('LCLV', 1), ('RCLV', 1), ('LUA', .3), ('RUA', .3)):
        rot_subtree_targets(Wt, [k], rodrigues(X3[None] * (br * w * .5)[:, None]))   # +angle about +X lifts the head end
    leg_s = np.linalg.norm(off[4]) + np.linalg.norm(off[7]); leg_r = np.linalg.norm(SF['t'][SF['i'][N['LCF']]]) + np.linalg.norm(SF['t'][SF['i'][N['LFT']]]); sc = leg_r / leg_s
    pos = Jc[:, 0] * sc; pos[:, :2] = MB.close_loop(pos[:, :2]); pos[:, :2] -= MB.sgf(pos[:, :2], int(fps * 3), 1); pos[:, 2] = MB.sgf(pos[:, 2], int(fps * 1.0) | 1)
    pos[:, 0] += px; pos[:, 2] += -py
    # ---- init locals (as mocap_bake.bake) ----
    nb = len(SF['names']); Lq = np.repeat(PT.Q[:1], n, 0).copy(); Tt = np.repeat(PT.T[:1], n, 0).copy()
    BQ, BT = R.base(SF, 'poses', 'paprika_4')
    for b, nm in enumerate(SF['names']):
        if 'Finger' in nm: Lq[:, b] = BQ[0, b]
    Tt[:, SF['i'][N['COM']]] = pos; Wm = [None] * nb; Lm = q2m(Lq)
    for b in range(nb):
        p = SF['parent'][b]; key = next((k for k in OPT if N[k] == SF['names'][b]), None)
        if key is not None: Wm[b] = Wt[key]; Lm[:, b] = (np.swapaxes(Wm[p], -1, -2) @ Wt[key]) if p >= 0 else Wt[key]
        else: Wm[b] = Lm[:, b] if p < 0 else Wm[p] @ Lm[:, b]
    sk = MB.Skel(SF, m2q(Lm), Tt); t_ = MB.t_
    idx = {k: SF['i'][N[k]] for k in OPT + ['PEL', 'LUA', 'RUA', 'LTOE', 'RTOE']}
    # mattress sample: skin points per carrier (voxel 2.5 u); soft allowance (units) where her tissue squashes on the mattress
    BEDC = {'PEL': 1.2, 'SP0': .8, 'SP1': .8, 'SP2': 1.8, 'LTH': .8, 'RTH': .8, 'LCF': .4, 'RCF': .4, 'LFT': .2, 'RFT': .2, 'LUA': .4, 'RUA': .4, 'LFA': .4, 'RFA': .4, 'LHD': .2, 'RHD': .2, 'HEAD': .2}
    BP = {k: t_(MB.vox(np.array(MB.SKIN[N[k]], float), 2.5)[:, :3]) for k in BEDC}
    REST = {'hipthigh': ['PEL', 'LTH', 'RTH'], 'kneeL': ['LCF'], 'kneeR': ['RCF'], 'thighL': ['LTH'], 'thighR': ['RTH'], 'elbowL': ['LFA'], 'elbowR': ['RFA']}   # each leg and each elbow rests on the mattress
    WT = {k: t_(q2m(WTq[k])) for k in OPT}; Wtt = {k: t_(Wt[k]) for k in OPT}; post = t_(pos)
    wrot = {k: 3.0 if k == 'COM' else .5 if k.endswith('HD') else .8 if k in ('HEAD', 'NECK') else 1.0 for k in OPT}
    LIMB = [s + k for s in 'LR' for k in ('UA', 'FA', 'TH', 'CF')]
    LAX = {k: t_(nrm(SF['t'][SF['i'][N[k[0] + {'UA': 'FA', 'FA': 'HD', 'TH': 'CF', 'CF': 'FT'}[k[1:]]]]])) for k in LIMB}
    DEV, TD = MB.DEV, MB.TD
    delta = torch.zeros((n, len(OPT), 3), dtype=TD, device=DEV, requires_grad=True); droot = torch.zeros((n, 3), dtype=TD, device=DEV, requires_grad=True)
    ACC = [idx[k] for k in OPT]; phase = {'lim': 40.0, 'col': 4.0, 'bed': 20.0, 'all': False, 'it': 0}
    def bedpts(W, P, k):
        b = idx[k] if k != 'PEL' else SF['i'][N['PEL']]; return P[:, b][:, None] + (W[:, b] @ (BP[k] * sk.ws[b]).T).transpose(-1, -2)
    def losses(full=True):
        W, P = sk.fk(delta, droot); Ls = {}
        Ls['rot'] = sum(wrot[k] * (MB.t_log(Wtt[k].transpose(-1, -2) @ W[:, idx[k]]) ** 2).sum(-1).mean() * (.12 if k in LIMB else 1) for k in OPT)
        Ls['dir'] = sum((4 if k[1:] in ('UA', 'FA', 'TH') else .4) * (((W[:, idx[k]] - Wtt[k]) @ LAX[k]) ** 2).sum(-1).mean() for k in LIMB)
        Ls['root'] = .02 * ((P[:, idx['COM'], :2] - post[:, :2]) ** 2).sum(-1).mean()
        lp, _, _ = MB.limit_terms(W, WT, idx); Ls['limit'] = phase['lim'] * lp / n
        if full:
            fr = torch.arange(phase['it'] % 4, n, 4, device=DEV) if phase['all'] else torch.randperm(n, device=DEV)[:max(8, n // 4)]   # 4 interleaved sets (4 GB shared RTX)
            cp, _ = MB.collide(W, P, idx, sk.ws, frames=fr); Ls['collide'] = phase['col'] * cp / len(fr)
        pen = 0; rest = 0; Z = {}
        for k, allow in BEDC.items():
            z = bedpts(W, P, k)[..., 2]; Z[k] = z.min(-1).values; pen = pen + (torch.relu(-allow - z) ** 2).sum()
        for g, ks in REST.items():
            zm = torch.stack([Z[k] for k in ks], -1).min(-1).values; rest = rest + ((zm - (-.3)) ** 2).sum()   # resting: lowest skin of the group just touching (-3 mm)
        Ls['bed'] = phase['bed'] * pen / n; Ls['rest'] = 2.0 * rest / n
        X_ = P[:, ACC]; acc = torch.roll(X_, -1, 0) - 2 * X_ + torch.roll(X_, 1, 0); Ls['smooth'] = .02 * (acc ** 2).sum(-1).mean() * len(ACC) / 10
        Ld = torch.roll(delta, -1, 0) - 2 * delta + torch.roll(delta, 1, 0); Ls['dsmooth'] = .5 * (Ld ** 2).sum(-1).mean()
        Lr = torch.roll(droot, -1, 0) - 2 * droot + torch.roll(droot, 1, 0); Ls['rsmooth'] = 2.0 * (Lr ** 2).sum(-1).mean()
        return Ls, W, P
    opt = torch.optim.Adam([delta, droot], lr=.01); hist = []
    with torch.no_grad():   # start resting on the mattress: lift/lower the root so the hips touch
        W0, P0 = sk.fk(delta, droot); z0 = torch.stack([bedpts(W0, P0, k)[..., 2].min(-1).values for k in REST['hipthigh']], -1).min(-1).values; droot[:, 2] -= z0
    for it in range(sum(iters)):
        if it == iters[0]:
            for g_ in opt.param_groups: g_['lr'] = .003
        if it == iters[0] + iters[1]:
            phase.update(lim=5000.0, col=600.0, bed=400.0, all=True)
            for g_ in opt.param_groups: g_['lr'] = .002
        if it == iters[0] + iters[1] + iters[2]:
            phase.update(lim=60000.0, col=1200.0, bed=2000.0)
            for g_ in opt.param_groups: g_['lr'] = .001
        phase['it'] = it; opt.zero_grad(); Ls, W, P = losses(); tot = sum(Ls.values()); tot.backward(); opt.step()
        if it % 100 == 0 or it == sum(iters) - 1: hist.append({k: round(float(v.detach()), 5) for k, v in Ls.items()}); print(ID, it, json.dumps(hist[-1]), round(time.time() - t0), 's', flush=True)
    with torch.no_grad():
        Ls, W, P = losses(full=False); bedz = {k: (bedpts(W, P, k)[..., 2].min(-1).values.cpu().double().numpy() / U * 1000) for k in BEDC}
    r = dict(L0q=m2q(Lm), F=F, fps=fps, n=n, loop=[int(i), int(j)], ginfo=ginfo, sk=sk, W=W.detach().cpu().double().numpy(), P=P.detach().cpu().double().numpy(), WT=WTq, Wt=Wt, idx=idx,
             cont={'L': np.zeros(n), 'R': np.zeros(n)}, hist=hist, Gc=Gc, delta=delta.detach().cpu(), droot=droot.detach().cpu(), sc=sc)
    return r, bedz, lay

BUTT5 = dict(k=0.03, k2=0.01, d=0.05, ts=0.4 * 15 / 13.33, linY=0.667)   # RB_CBPC levels120.Bounce5.Butt (web/assets/cbpc.js): stiffness, stiffness2, damping, timeStep x 15/timetick, linearY
def spring_fz(k, d, ts, hz=120):
    A = np.array([[1 - k * ts * ts * (1 - d * ts), ts * (1 - d * ts)], [-k * ts * (1 - d * ts), 1 - d * ts]]); z = np.linalg.eigvals(A); z = z[np.argmax(z.imag)]
    s_ = np.log(z.astype(complex)) * hz; wn = abs(s_); return wn / 2 / np.pi, -s_.real / wn
def spring_sim(k, d, ts, drive, hz=120):   # drive: target position per 120 Hz substep -> lag x = P - target
    x = 0.0; v = 0.0; out = np.zeros(len(drive)); prev = drive[0]
    for i, tg in enumerate(drive):
        P = prev + x; F = (tg - P) * k; v = (v + F * ts) * (1 - d * ts); P = P + v * ts; x = P - tg; prev = tg; out[i] = x
    return out
def jiggle_tune(MS, py_units, fps):
    """The source's glute motion (minus the rigid pelvis) is a SUSTAINED wobble: one sinusoid explains 98-99% of its variance, constant amplitude
    over the clip (ACF envelope ~no decay) -> its tissue damping is not identifiable; what is measured is frequency, amplitude and phase (L/R, lateral vs
    vertical). Runtime (phys3d per-clip tune): (a) Butt stiffness x km so phys3d's CBPC spring at Bounce5 has its natural frequency at the measured
    wobble frequency (damping stays the level's), (b) drive = the measured wobble as a target oscillation, amplitude given as the VISIBLE amplitude
    (fraction of her hip width -> units at runtime), phys3d divides by its own spring gain |H| and linear output and advances the phase by arg H."""
    from scipy.optimize import minimize_scalar
    S30 = MS['series30']; t = np.arange(len(S30['gluteL_res'])) / 30; x = np.asarray(S30['gluteL_res'], float)[:, 1]; x = x - x.mean()
    f = float(minimize_scalar(lambda f: -abs((x * np.exp(-2j * np.pi * f * t)).mean()), bounds=(1.2, 2.4), method='bounded').x)
    amp = {}; ph = {}; expl = {}
    for s_ in 'LR':
        a = np.asarray(S30['glute' + s_ + '_res'], float)
        for j, ax in ((0, 'x'), (1, 'y')):   # screen x + = her right = body +X; screen y + = toward the mattress = her front = body +Y (prone)
            v = a[:, j] - a[:, j].mean(); c = (v * np.exp(-2j * np.pi * f * t)).mean() * 2; r_ = v - np.real(c * np.exp(2j * np.pi * f * t))
            amp[s_ + ax] = float(abs(c)); ph[s_ + ax] = float(np.angle(c)); expl[s_ + ax] = round(float(1 - r_.var() / v.var()), 3)
    k_eff = BUTT5['k'] + BUTT5['k2'] * .5
    km = float(minimize_scalar(lambda m: (spring_fz(k_eff * m, BUTT5['d'], BUTT5['ts'])[0] - f) ** 2, bounds=(.2, 5), method='bounded').x)
    fb, zb = spring_fz(k_eff, BUTT5['d'], BUTT5['ts'])
    return dict(Butt=dict(k=round(km, 3), drive=dict(hz=round(f, 4), ax_hipw=[round(amp['Lx'], 5), round(amp['Rx'], 5)], ay_hipw=[round(amp['Ly'], 5), round(amp['Ry'], 5)],
                                                      phx=[round(ph['Lx'], 3), round(ph['Rx'], 3)], phy=[round(ph['Ly'], 3), round(ph['Ry'], 3)])),
                measured=dict(wobble_hz=round(f, 3), variance_explained=expl, note='sustained wobble: damping not identifiable; CBPC damping kept at the Bounce level'),
                bounce5_butt=dict(natural_hz=round(fb, 2), zeta=round(zb, 3)), tuned_natural_hz=round(spring_fz(k_eff * km, BUTT5['d'], BUTT5['ts'])[0], 2))

if __name__ == '__main__':
    t0 = time.time(); kp = os.path.join(D, 'tools', 'roto', 'mocap_kp', ID + '.npz'); m = decimate(SRC, kp); print('fit ->', kp, m, 'frames @30', flush=True)
    MS = json.load(open(os.path.join(D, 'tools', 'roto', 'roto3_measure.json')))['prone']
    try: r, bedz, lay = bake()
    except Exception as e:   # shared RTX: a CUDA OOM can leave the context unusable -> re-run on the CPU (float64) in a fresh process
        if MB.DEV.type != 'cuda': raise
        print('GPU failed (%s) -> CPU re-run' % str(e)[:80], flush=True); import subprocess
        sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__), D, SRC], env=dict(os.environ, MOCAP_DEVICE='cpu')))
    if MB.DEV.type == 'cuda':   # final metrics (all frames at once, no grad) on the CPU: no VRAM spike
        MB.DEV = torch.device('cpu'); MB.TD = torch.float64; r['sk'].ws = r['sk'].ws.detach().cpu().double()
    PY = lay.pop('_py')
    cfg = dict(id='roto_prone_idle', name='Lying on her phone')
    clip, rl = MB.finish(cfg, r)
    for k in ('feet',): rl.pop(k, None)
    rl.update(source='NLF SMPL-X fit (posture, slow shifts, head turns) + DIS optical flow layer (pelvis/thighs/breathing) of 4dc1fb80, optimised on the XPMSSE skeleton',
              bed=r['ginfo'], flow_layer=lay,
              mattress_min_skin_mm={k: dict(p1=round(float(np.percentile(v, 1)), 1), p50=round(float(np.median(v)), 1)) for k, v in bedz.items()},
              period_s=round(r['n'] / r['fps'], 3))
    rl['phys_tune'] = jiggle_tune(MS, PY, r['fps'])
    cp = os.path.join(D, 'tools', 'roto', 'roto3_clips.json'); C = json.load(open(cp)) if os.path.exists(cp) else {}
    C['roto_prone_idle'] = clip; C.setdefault('_log', {})['roto_prone_idle'] = rl; json.dump(C, open(cp, 'w'), separators=(',', ':'))
    print(json.dumps({k: rl[k] for k in ('dur_s', 'loop', 'total_limit_violation_frames', 'penetration', 'mattress_min_skin_mm', 'flow_layer', 'phys_tune', 'bed')}), round(time.time() - t0), 's')
