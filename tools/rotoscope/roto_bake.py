"""Rotoscoped motion -> 3D clips on the XPMSSE skeleton (same JSON clip format as tools/anims3d.py).
Usage: python -I tools/roto/roto_bake.py <reiko_breed dir>
Reads  tools/roto/roto_measure.json (periods + phase-folded waveforms from the reference videos, see roto_measure.py)
       web/assets/anims/leito.json, poses.json (base poses) and the UBE GLBs (rest skeleton).
Writes web/assets/anims/roto3d.js  (window.RB_ROTO3D = {clips:{...}}, merged into RB_ANIM3D.roto at load).
Only motion is used from the videos (timing, amplitude, phase, lag); poses come from the Leito / Sonders packs.
FK/IK in Skyrim space (Z up, units ~1.43 cm). Legs/arms re-solved with two-bone IK so knees/feet/hands stay planted."""
import sys, os, json, struct, math, site
sys.path.append(site.getusersitepackages())  # numpy lives in the user site (not on the -I path)
import numpy as np

D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
A = os.path.join(D, 'web', 'assets')
U = 1 / 0.014286  # metres -> Skyrim units
MEAS = json.load(open(os.path.join(D, 'tools', 'roto', 'roto_measure.json')))
LEITO = json.load(open(os.path.join(A, 'anims', 'leito.json')))['clips']
POSES = json.load(open(os.path.join(A, 'anims', 'poses.json')))['clips']
LOG = {}

# ---------------- quaternion helpers (xyzw, arrays [...,4]) ----------------
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], -1)
def qinv(q): return q * np.array([-1, -1, -1, 1.0])
def qrot(q, v):
    u = q[..., :3]; w = q[..., 3:4]; t = 2 * np.cross(u, v); return v + w * t + np.cross(u, t)
def qnorm(q): return q / np.linalg.norm(q, axis=-1, keepdims=True)
def qaxis(ax, ang):
    ax = np.asarray(ax, float); ax = ax / np.linalg.norm(ax, axis=-1, keepdims=True); ang = np.asarray(ang, float)[..., None]
    return np.concatenate([ax * np.sin(ang / 2), np.cos(ang / 2)], -1)
def qfromvecs(u, v):
    u = u / np.linalg.norm(u, axis=-1, keepdims=True); v = v / np.linalg.norm(v, axis=-1, keepdims=True)
    c = np.cross(u, v); d = (u * v).sum(-1, keepdims=True); return qnorm(np.concatenate([c, 1 + d], -1))
def qscale(q, w):  # partial rotation (slerp from identity)
    q = np.where(q[..., 3:4] < 0, -q, q); ang = 2 * np.arccos(np.clip(q[..., 3], -1, 1)); s = np.sin(ang / 2)
    ax = np.where(s[..., None] > 1e-8, q[..., :3] / np.maximum(s, 1e-8)[..., None], np.array([1.0, 0, 0])); return qaxis(ax, ang * w)
def qavg(Q):  # Q [n,4] -> mean
    Q = Q * np.sign((Q * Q[0]).sum(-1, keepdims=True)); return qnorm(Q.mean(0))

# ---------------- skeleton + clips ----------------
def load_skel(glb):
    b = open(glb, 'rb').read(); L = struct.unpack('<I', b[12:16])[0]; J = json.loads(b[20:20 + L]); N = J['nodes']; par = {}
    for i, n in enumerate(N):
        for c in n.get('children', []): par[c] = i
    root = next(i for i, n in enumerate(N) if n.get('name') == 'NPC Root [Root]'); order = [root]; k = 0
    while k < len(order):
        order += N[order[k]].get('children', []); k += 1
    idx = {o: j for j, o in enumerate(order)}
    S = {'names': [N[o]['name'] for o in order], 'parent': [idx.get(par.get(o), -1) if o != root else -1 for o in order],
         't': np.array([N[o].get('translation', [0, 0, 0]) for o in order], float), 'q': np.array([N[o].get('rotation', [0, 0, 0, 1]) for o in order], float),
         's': np.array([(N[o].get('scale') or [1])[0] for o in order], float)}
    S['i'] = {n: j for j, n in enumerate(S['names'])}; return S
SF = load_skel(os.path.join(A, 'reiko_body.glb')); SM = load_skel(os.path.join(A, 'player_body.glb'))

def decode(S, d):
    """clip dict -> (Q [n,nb,4], T [n,nb,3]) with rest pose for untracked bones"""
    n = max(1, d['n']); nb = len(S['names']); Q = np.repeat(S['q'][None], n, 0).copy(); T = np.repeat(S['t'][None], n, 0).copy()
    for b, q in d['q'].items():
        if b in S['i']:
            a = np.array(q, float).reshape(-1, 4) * 1e-4; Q[:, S['i'][b]] = a[np.arange(n) % len(a)]
    for b, t in d.get('tc', {}).items():
        if b in S['i']: T[:, S['i'][b]] = t
    for b, t in d.get('t', {}).items():
        if b in S['i']: T[:, S['i'][b]] = (np.array(t, float).reshape(-1, 3) * .01)[np.arange(n) % (len(t) // 3)]
    return qnorm(Q), T

def fk(S, Q, T):
    n, nb = Q.shape[:2]; WQ = np.zeros_like(Q); WP = np.zeros_like(T); WS = np.ones((n, nb))
    for b in range(nb):
        p = S['parent'][b]
        if p < 0: WQ[:, b] = Q[:, b]; WP[:, b] = T[:, b]; WS[:, b] = S['s'][b]
        else: WQ[:, b] = qmul(WQ[:, p], Q[:, b]); WP[:, b] = WP[:, p] + qrot(WQ[:, p], WS[:, p, None] * T[:, b]); WS[:, b] = WS[:, p] * S['s'][b]
    return WQ, WP

class Pose:
    def __init__(s, S, Q, T): s.S, s.Q, s.T = S, Q.copy(), T.copy(); s.upd()
    def upd(s): s.WQ, s.WP = fk(s.S, s.Q, s.T); return s
    def i(s, n): return s.S['i'][n]
    def p(s, n): return s.WP[:, s.i(n)].copy()
    def wq(s, n): return s.WQ[:, s.i(n)].copy()
    def set_world_q(s, n, wq):
        b = s.i(n); par = s.S['parent'][b]; s.Q[:, b] = qnorm(qmul(qinv(s.WQ[:, par]), wq)); s.upd()
    def rotate_world(s, n, R, pivot=None):
        """apply world rotation R (about the bone's own origin, or about pivot) to bone n's subtree"""
        b = s.i(n); par = s.S['parent'][b]; wq = qmul(R, s.WQ[:, b])
        if pivot is not None:
            wp = pivot + qrot(R, s.WP[:, b] - pivot); pq = s.WQ[:, par]; pp = s.WP[:, par]
            s.T[:, b] = qrot(qinv(pq), wp - pp)  # parent scale is 1 on the spine/root chain
        s.Q[:, b] = qnorm(qmul(qinv(s.WQ[:, par]), wq)); s.upd()
    def translate_world(s, n, d):
        b = s.i(n); par = s.S['parent'][b]; s.T[:, b] += qrot(qinv(s.WQ[:, par]), d); s.upd()
    def aim(s, n, child, target, w=1.0):
        """rotate bone n so that descendant `child` moves toward target (world)"""
        pa = s.p(n); r = qfromvecs(s.p(child) - pa, target - pa); s.rotate_world(n, qscale(r, w))
    def ik2(s, a, b, c, tgt, tgt_q=None, pole=None):
        """two-bone IK: bones a (upper) -> b (lower) -> c (end); end reaches tgt [n,3]; optional end world rotation; pole = bend hint [n,3]"""
        pa, pb, pc = s.p(a), s.p(b), s.p(c); la = np.linalg.norm(pb - pa, axis=-1); lb = np.linalg.norm(pc - pb, axis=-1)
        dv = tgt - pa; d = np.clip(np.linalg.norm(dv, axis=-1), np.abs(la - lb) + 1e-3, la + lb - 1e-3); dirv = dv / np.linalg.norm(dv, axis=-1, keepdims=True)
        pl = (pb - pa) if pole is None else pole; pl = pl - dirv * (pl * dirv).sum(-1, keepdims=True); pl = pl / np.maximum(np.linalg.norm(pl, axis=-1, keepdims=True), 1e-6)
        ca = np.clip((la ** 2 + d ** 2 - lb ** 2) / (2 * la * d), -1, 1); knee = pa + dirv * (la * ca)[:, None] + pl * (la * np.sqrt(1 - ca ** 2))[:, None]
        s.rotate_world(a, qfromvecs(pb - pa, knee - pa)); pb, pc = s.p(b), s.p(c); s.rotate_world(b, qfromvecs(pc - pb, tgt - pb))
        if tgt_q is not None: s.set_world_q(c, tgt_q)
        return float(np.abs(np.linalg.norm(s.p(c) - tgt, axis=-1)).max())

OST = {}
def ost(pack, scene):
    """clips of an OStim-catalog scene file (web/assets/anims/<pack>/<scene>.js, written by another agent's importer)"""
    if scene not in OST:
        s = open(os.path.join(A, 'anims', pack, scene + '.js'), encoding='utf-8').read(); OST[scene] = json.JSONDecoder().raw_decode(s[s.index('var c=') + 6:])[0]
    return OST[scene]
def clipdict(src, key):
    if src == 'leito': return LEITO[key]
    if src == 'poses': return POSES[key]
    pack, scene = src.split('/'); return ost(pack, scene)[key]
def base(S, src, key): return decode(S, clipdict(src, key))
def lat_of(P):  # her/his right, from the hip joints (the pelvis bone's local X is not lateral on XPMSSE)
    v = P.p(LEG['R'][0]) - P.p(LEG['L'][0]); return v / np.linalg.norm(v, axis=-1, keepdims=True)
def mean_pose(Q, T):
    return np.stack([qavg(Q[:, b]) for b in range(Q.shape[1])])[None], T.mean(0)[None]
def tile(Q, T, n): return np.repeat(Q, n, 0), np.repeat(T, n, 0)
def sample(Q, T, psi):
    """periodic sample at fractional base frames psi"""
    m = len(Q); i0 = np.floor(psi).astype(int) % m; i1 = (i0 + 1) % m; f = (psi - np.floor(psi))[:, None, None]
    q0, q1 = Q[i0], Q[i1]; q1 = q1 * np.sign((q0 * q1).sum(-1, keepdims=True)); return qnorm(q0 * (1 - f) + q1 * f), T[i0] * (1 - f) + T[i1] * f
def wave(w, n, shift=0.0):
    """48-sample periodic waveform -> n samples (Fourier interpolation), phase-shifted by `shift` cycles"""
    w = np.asarray(w, float); F = np.fft.rfft(w); k = np.arange(len(F)); ph = np.exp(-2j * np.pi * k * shift)
    t = np.arange(n) / n; return np.real(sum(F[j] * ph[j] * np.exp(2j * np.pi * j * t) * (1 if j == 0 or j == len(w) // 2 else 2) for j in range(len(F)))) / len(w)
def unit01(x): x = np.asarray(x, float); return (x - x.min()) / max(1e-9, np.ptp(x))
def frames_for(period): n = max(8, int(round(period * 30))); return n, n / period

# ---------------- encode ----------------
def encode(P, fps, keep_q, extra_t=()):
    n = len(P.Q); out = {'n': n, 'fps': round(fps, 4), 'dur': round(n / fps, 4), 'q': {}, 't': {}, 'tc': {}}
    for b, nm in enumerate(P.S['names']):
        if nm not in keep_q: continue
        q = P.Q[:, b].copy()
        for k in range(1, n):
            if (q[k] * q[k - 1]).sum() < 0: q[k] = -q[k]
        qi = np.round(q * 1e4).astype(int)
        out['q'][nm] = qi[0].tolist() if (qi == qi[0]).all() else qi.reshape(-1).tolist()
    for b, nm in enumerate(P.S['names']):
        if nm not in keep_q and nm not in extra_t: continue
        t = P.T[:, b]
        if np.ptp(t, axis=0).max() > .02: out['t'][nm] = np.round(t * 100).astype(int).reshape(-1).tolist()
        else: out['tc'][nm] = np.round(t[0], 3).tolist()
    return out
def keepset(d): return set(d['q']) | set(d.get('tc', {})) | set(d.get('t', {}))

# shared bone names
COM, PEL, SP0, SP1, SP2, NECK, HEAD = 'NPC COM [COM ]', 'NPC Pelvis [Pelv]', 'NPC Spine [Spn0]', 'NPC Spine1 [Spn1]', 'NPC Spine2 [Spn2]', 'NPC Neck [Neck]', 'NPC Head [Head]'
LEG = {s: ('NPC %s Thigh [%sThg]' % (s, s), 'NPC %s Calf [%sClf]' % (s, s), 'NPC %s Foot [%sft ]' % (s, s)) for s in 'LR'}
ARM = {s: ('NPC %s UpperArm [%sUar]' % (s, s), 'NPC %s Forearm [%sLar]' % (s, s), 'NPC %s Hand [%sHnd]' % (s, s)) for s in 'LR'}
GEN = ['NPC GenitalsBase [GenBase]', 'NPC Genitals01 [Gen01]', 'NPC Genitals02 [Gen02]', 'NPC Genitals03 [Gen03]', 'NPC Genitals04 [Gen04]', 'NPC Genitals05 [Gen05]', 'NPC Genitals06 [Gen06]']
ZUP = np.array([0, 0, 1.0])

def plant(P, ref, legs=True, arms=False, arm_tgt=None):
    """re-solve limbs so ankles (and hands) sit where they are in `ref` (a Pose with the same frame count)"""
    err = 0
    if legs == 'knee':  # kneeling: knee and ankle both pinned (thigh aims at the knee, calf at the ankle)
        for s in 'LR':
            a, b, c = LEG[s]; P.aim(a, b, ref.p(b)); P.aim(b, c, ref.p(c)); P.set_world_q(c, ref.wq(c)); err = max(err, float(np.linalg.norm(P.p(b) - ref.p(b), axis=-1).max()))
    elif legs:
        for _ in range(3):  # standing: drop the COM where a leg could not reach its planted ankle (keeps feet locked, bends the knee instead)
            ex = np.zeros(len(P.Q))
            for s in 'LR':
                a, b, c = LEG[s]; reach = np.linalg.norm(P.p(b) - P.p(a), axis=-1) + np.linalg.norm(P.p(c) - P.p(b), axis=-1)
                ex = np.maximum(ex, np.linalg.norm(ref.p(c) - P.p(a), axis=-1) - .985 * reach)
            if ex.max() <= 0: break
            P.translate_world(COM, -ZUP * (ex * 1.15)[:, None])
        for s in 'LR':  # bend plane through a knee point that follows half the hip motion (keeps the knee swing soft, no flip near full extension)
            a, b, c = LEG[s]; kt = ref.p(b) + .5 * (P.p(a) - ref.p(a)); err = max(err, P.ik2(a, b, c, ref.p(c), ref.wq(c), pole=kt - P.p(a)))
    if arms:
        for s in 'LR':
            a, b, c = ARM[s]; tg = arm_tgt[s] if arm_tgt else (ref.p(c), ref.wq(c)); err = max(err, P.ik2(a, b, c, tg[0], tg[1], pole=ref.p(b) - ref.p(a)))
    return err
def fixed(P):  # per-frame planted target = mean over the cycle (removes base-clip foot/hand slide)
    class R: pass
    r = R(); snap = Pose(P.S, P.Q, P.T)   # snapshot: targets must not follow later edits
    def p(n): return np.repeat(snap.p(n).mean(0, keepdims=True), len(snap.Q), 0)
    def wq(n): return np.repeat(qavg(snap.wq(n))[None], len(snap.Q), 0)
    r.p, r.wq = p, wq; return r

def vag_entrance(F):  # PEN3 CFG.vagina anchor: Pelvis + [0,-1,-4.32]; first waypoint +[0,.7,6]
    q = F.wq(PEL); p = F.p(PEL); return p + qrot(q, np.array([0, -1, -4.32])), p + qrot(q, np.array([0, -1 + .7, -4.32 + 6]))
def mouth_entrance(F):
    q = F.wq(HEAD); p = F.p(HEAD); return p + qrot(q, np.array([0, 2, -1.5])), p + qrot(q, np.array([0, 2 - 5, -1.5 + 2]))
def shaft(M):
    b = M.p(GEN[0]); L = sum(np.linalg.norm(M.p(GEN[i + 1]) - M.p(GEN[i]), axis=-1) for i in range(len(GEN) - 1)) + 2.5
    return b, L, M.p(GEN[-1]) - M.p(GEN[0])

def report(name, F, M=None, ent_fn=None):
    r = {}
    for s in 'LR':
        r['ankle_slide_%s_cm' % s] = round(float(np.ptp(F.p(LEG[s][2]), axis=0).max() / U * 100), 2)
        r['knee_slide_%s_cm' % s] = round(float(np.ptp(F.p(LEG[s][1]), axis=0).max() / U * 100), 2)
    if M is not None:
        b, L, _ = shaft(M); e, _ = ent_fn(F); a = np.linalg.norm(e - b, axis=-1); dep = L - a
        r.update(shaft_len_cm=round(float(L.mean() / U * 100), 1), depth_cm=[round(float(dep.min() / U * 100), 1), round(float(dep.max() / U * 100), 1)], depth_frac=[round(float((dep / L).min()), 2), round(float((dep / L).max()), 2)])
        for s in 'LR': r['his_ankle_slide_%s_cm' % s] = round(float(np.ptp(M.p(LEG[s][2]), axis=0).max() / U * 100), 2)
    LOG[name] = r; print(name, r)

# ======================= solo: twerk =======================
def bake_twerk():
    """standing, bent forward, feet planted, hands on a support (counter/bed edge) in front; the hips roll + bounce (reference video 0)"""
    m = MEAS['twerk']; per = m['period_s']; n, fps = frames_for(per); W = m['sig']; key = 'staranise_48'
    Q, T = base(SF, 'poses', key); Q, T = tile(Q, T, n); F = Pose(SF, Q, T)
    # face Skyrim -Y (three -Z): view3d's 'counter' fit puts the support at pelvis.z - 0.45 and the daily camera then sees her from behind
    fw = F.p(HEAD) - F.p(PEL); fw[:, 2] = 0; ang = math.atan2(fw[0, 0], fw[0, 1]); F.rotate_world(COM, qaxis(ZUP, np.full(n, ang - math.pi)), pivot=F.p(COM))
    lat = lat_of(F); lat[:, 2] = 0; lat /= np.linalg.norm(lat, axis=-1, keepdims=True); fwd = np.cross(ZUP, lat)
    z0 = min(F.p(LEG[s][2])[:, 2].min() for s in 'LR')
    # soft knees (2.5 cm) so the hip bounce never locks the legs; bend the upper back down toward the support
    F.translate_world(COM, np.repeat(np.array([[0, 0, -.025 * U]]), n, 0))
    # square the stance (the base pose has one foot forward, which would go through the support): feet hip-width, under/behind the hips
    for s_, sg in (('L', -1), ('R', 1)):
        a_, b_, c_ = LEG[s_]; at = F.p(PEL) * np.array([1, 1, 0]) + lat * (sg * .13 * U) - fwd * (.04 * U); at[:, 2] = F.p(c_)[:, 2]
        F.ik2(a_, b_, c_, at, F.wq(c_), pole=fwd * 10 + ZUP * 0)
    sh = (F.p(ARM['L'][0]) + F.p(ARM['R'][0])) / 2
    hand_h, reach = .84 * U, .62 * U
    tgt = {s: (F.p(PEL) * np.array([1, 1, 0]) + fwd * reach + lat * (sg * .19 * U) + ZUP * (z0 + hand_h)) for s, sg in (('L', -1), ('R', 1))}
    # torso inclined up (like the reference, ~35 deg): chest clear above the support, arms reach down to it
    pz = F.p(PEL)[:, 2]; F.aim(SP0, SP2, F.p(PEL) * np.array([1, 1, 0]) + fwd * (.30 * U) + ZUP[None] * (pz + .25 * U)[:, None])
    F.aim(NECK, HEAD, F.p(HEAD) + ZUP * (.03 * U), .5)
    ref = fixed(F)
    x = wave(W['pel_x']['w'], n) * U; y = wave(W['pel_y']['w'], n) * U
    roll = np.radians(wave(W['roll_deg']['w'], n))                          # cheek-top trackers: +-9 deg, one cheek up while the other drops
    pitch = np.arctan2(y / U, .12)                                         # butt bounce = pelvic tilt about the hip joints
    chest0 = F.p(SP2)
    F.translate_world(COM, lat * x[:, None])
    F.rotate_world(PEL, qmul(qaxis(fwd, -roll), qaxis(lat, -pitch)))
    bx = wave(W['back_x']['w'], n) * U; by = wave(W['back_y']['w'], n) * U
    F.aim(SP0, SP2, chest0 + lat * bx[:, None] + ZUP * by[:, None])
    e = plant(F, ref, legs=True)
    hq = {s: np.repeat(qavg(F.wq(ARM[s][2]))[None], n, 0) for s in 'LR'}
    for s in 'LR':
        a, b, c = ARM[s]; e = max(e, F.ik2(a, b, c, tgt[s], hq[s], pole=(F.p(b) - F.p(a)) * .2 - lat * (1 if s == 'R' else -1) * 0 + ZUP * -.0 + (F.p(b) - F.p(a))))
    hl = np.ptp(F.p(ARM['L'][2]), axis=0).max() / U * 100
    cl, cr = F.p('NPC L Butt'), F.p('NPC R Butt')
    report('roto_twerk', F); LOG['roto_twerk'].update(base=key + ' (standing bent over, hands on support)', ik_err_units=round(e, 3), period_s=per, hand_slide_cm=round(float(hl), 2),
        pel_lat_amp_cm=round(float(np.ptp(x) / 2 / U * 100), 2), butt_vert_amp_cm=round(float(np.ptp(y) / 2 / U * 100), 2), pelvic_tilt_amp_deg=round(float(np.degrees(np.ptp(pitch) / 2)), 2),
        roll_amp_deg=round(float(np.degrees(np.ptp(roll) / 2)), 2), cheekL_z_ptp_cm=round(float(np.ptp(cl[:, 2]) / U * 100), 1), cheekR_z_ptp_cm=round(float(np.ptp(cr[:, 2]) / U * 100), 1),
        cheek_LR_diff_ptp_cm=round(float(np.ptp(cl[:, 2] - cr[:, 2]) / U * 100), 1),
        hands_h_m=.84, hands_fwd_m=.62)
    return {'roto_twerk': encode(F, fps, keepset(POSES[key]) | {COM}, extra_t=(COM,))}

# ======================= solo: idle sway (standing, hands behind head) =======================
def bake_idle():
    m = MEAS['idle_sway']; per = m['period_s']; n, fps = frames_for(per); W = m['sig']; key = 'gochugaru_75'
    Q, T = base(SF, 'poses', key); Q, T = tile(Q, T, n); F = Pose(SF, Q, T); ref = fixed(F)
    lat = lat_of(F); lat[:, 2] = 0; lat /= np.linalg.norm(lat, axis=-1, keepdims=True); fwd = np.cross(ZUP, lat)
    x = wave(W['pel_x']['w'], n) * U; y = wave(W['pel_y']['w'], n) * U - 1.0 * U / 100   # 1 cm knee slack; plant() drops the COM further where a leg can't reach
    roll = np.arctan2(wave(W['hipL_y']['w'], n) - wave(W['hipR_y']['w'], n), .576)
    ch0, hd0 = F.p(SP2), F.p(HEAD); cx = wave(W['chest_x']['w'], n) * U; hx = wave(W['head_x']['w'], n) * U; hy = wave(W['head_y']['w'], n) * U
    F.translate_world(COM, lat * x[:, None] + ZUP * y[:, None]); F.rotate_world(PEL, qaxis(fwd, roll))
    F.aim(SP0, SP2, ch0 + lat * cx[:, None]); F.aim(NECK, HEAD, hd0 + lat * hx[:, None] + ZUP * hy[:, None])
    e = plant(F, ref, legs=True)
    report('roto_idle_sway', F); LOG['roto_idle_sway'].update(ik_err_units=round(e, 3), period_s=per, base=key, pel_lat_amp_cm=round(float(np.ptp(x) / 2 / U * 100), 2), roll_amp_deg=round(float(np.degrees(np.ptp(roll) / 2)), 2))
    keep = keepset(POSES[key]) | {COM}
    return {'roto_idle_sway': encode(F, fps, keep, extra_t=(COM,))}

# ======================= duo helpers =======================
ENT = {'vagina': vag_entrance, 'mouth': mouth_entrance}
def warp_base(src, kf, km, n, vid_depth01, kind):
    """phase-warp the base pair so its deepest/shallowest frames land where the video's are; returns (F, M) Poses"""
    Qf, Tf = base(SF, src, kf); Qm, Tm = base(SM, src, km); m = len(Qf)
    F0, M0 = Pose(SF, Qf, Tf), Pose(SM, Qm, Tm); b, L, _ = shaft(M0); e, _ = ENT[kind](F0); dep = L - np.linalg.norm(e - b, axis=-1)
    lp, lt = int(np.argmax(dep)), int(np.argmin(dep)); vp, vt = int(np.argmax(vid_depth01)), int(np.argmin(vid_depth01))
    psi = np.zeros(n)  # piecewise-linear map video frame -> base frame: deepest->deepest, shallowest->shallowest
    for i in range(n):
        if (i - vp) % n <= (vt - vp) % n:
            u = ((i - vp) % n) / max(1, (vt - vp) % n); psi[i] = lp + u * ((lt - lp) % m)
        else:
            u = ((i - vt) % n) / max(1, (vp - vt) % n); psi[i] = lt + u * ((lp - lt) % m)
    qf, tf = sample(Qf, Tf, psi); qm, tm = sample(Qm, Tm, psi)
    return Pose(SF, qf, tf), Pose(SM, qm, tm), {'base': src + ':' + kf[:-2], 'base_depth_frac': [round(float((dep / L).min()), 2), round(float((dep / L).max()), 2)], 'base_period_s': round(m / 30, 3)}

class Shift:  # a reference pose moved by a constant world offset (re-placed actor)
    def __init__(s, ref, d): s.ref, s.d = ref, d
    def p(s, n): return s.ref.p(n) + s.d
    def wq(s, n): return s.ref.wq(n)

def gap(M, F, kind):
    b, L, _ = shaft(M); e, _ = ENT[kind](F); d = e - b; a = np.linalg.norm(d, axis=-1); return a, d / a[:, None], L

def gap_fix(M, F, kind, depth_u, mover, refs):
    """depth = shaft length - |shaft base -> entrance|. The cycle-mean part re-places the mover (whole body, limbs' plant targets move along:
    the pack bases were authored for a longer SOS member); the oscillating part is the stroke itself (COM translation, or for her a rock about the knees)"""
    a, u, L = gap(M, F, kind); mv = u * (a - (L - depth_u))[:, None]; mean = mv.mean(0); hz = mean * np.array([1, 1, 0.0]); vz = mean[2]
    X, sg = (M, 1) if mover == 'm' else (F, -1)
    # horizontal part: re-place the whole body (plant targets move along); vertical part: absorbed by posture, never by floating/sinking the contacts
    X.translate_world(COM, np.repeat(sg * hz[None], len(mv), 0)); refs[mover] = Shift(refs[mover], sg * hz); LOG.setdefault('_replace', {})[kind + mover] = np.round(sg * mean / U * 100, 2).tolist()
    if mover == 'm': M.translate_world(COM, np.repeat(np.array([[0, 0, vz]]), len(mv), 0))   # his hips lower/raise; legs (and hands) re-solved to the planted spots
    else:  # her: bend at the waist/neck so the mouth/opening meets him (kneeling thighs can't lengthen)
        h0 = F.p(HEAD); F.aim(SP0, HEAD, h0 - np.array([0, 0, vz]) * .6); h1 = F.p(HEAD); F.aim(NECK, HEAD, h1 - (h0 - np.array([0, 0, vz]) - h1) * -1)
    if mover == 'm' or mover == 'f':
        a, u, L = gap(M, F, kind); X.translate_world(COM, sg * u * (a - (L - depth_u))[:, None]); return
    # mover 'fk' (kneeling her, re-placed above): the stroke itself is his hips (standing, ankles re-planted), her knees stay put
    a, u, L = gap(M, F, kind); M.translate_world(COM, u * (a - (L - depth_u))[:, None])

def hands_on(P, other, bone):
    """remember P's hands in `other`'s bone frame (cycle mean) -> per-frame IK targets after edits"""
    loc = {s: (qrot(qinv(other.wq(bone)), P.p(ARM[s][2]) - other.p(bone)).mean(0), qavg(qmul(qinv(other.wq(bone)), P.wq(ARM[s][2])))) for s in 'LR'}
    return lambda: {s: (other.p(bone) + qrot(other.wq(bone), loc[s][0]), qmul(other.wq(bone), np.repeat(loc[s][1][None], len(P.Q), 0))) for s in 'LR'}

def bake_duo(name, src, key, kind, sv, per, dmin, dmax, her_rock=None, mover='m', her_legs=True, her_arms=True, his_hands=None, her_hands=None, pre=None, his_slack_cm=0, calm=None):
    n, fps = frames_for(per); F, M, info = warp_base(src, key + '_f', key + '_m', n, sv, kind)
    refF, refM = fixed(F), fixed(M)
    hh = 'bed' if his_hands == 'bed' else hands_on(M, F, his_hands) if his_hands else None; fh = hands_on(F, M, her_hands) if her_hands and her_hands != 'thighs' else None
    if pre: pre(F, M, n)
    if calm:  # damp the base clip's own swing on these bones toward the cycle mean (the reference moves the head far less)
        for nm, k in calm.items():
            b = F.i(nm); mq = qavg(F.Q[:, b]); q = F.Q[:, b] * np.sign((F.Q[:, b] * mq).sum(-1, keepdims=True)); F.Q[:, b] = qnorm(q * (1 - k) + mq[None] * k)
        F.upd()
    if his_slack_cm: M.translate_world(COM, np.repeat(np.array([[0, 0, -his_slack_cm * U / 100]]), n, 0))   # soft knees so his hip stroke never hits full leg reach
    if her_rock is not None:  # replace her base rock (along the shaft axis) with the video's
        b, _, _ = shaft(M); e, _ = ENT[kind](F); ax = e - b; ax = (ax / np.linalg.norm(ax, axis=-1, keepdims=True)).mean(0); ax /= np.linalg.norm(ax)
        c0 = F.p(COM).mean(0)
        if her_legs == 'knee':  # kneeling: rock about the knee axis (knees stay planted)
            for _ in range(3):
                cur = ((F.p(COM) - c0) * ax).sum(-1); piv = (F.p(LEG['L'][1]) + F.p(LEG['R'][1])) / 2; lx = lat_of(F); rate = (np.cross(lx, F.p(COM) - piv) * ax).sum(-1)
                F.rotate_world(COM, qaxis(lx, np.clip((her_rock - cur) / np.where(np.abs(rate) < 1e-6, 1e-6, rate), -.3, .3)), pivot=piv)
        else:
            cur = ((F.p(COM) - c0) * ax).sum(-1); F.translate_world(COM, ax[None] * (her_rock - cur)[:, None])
    _, L, _ = shaft(M); refs = {'m': refM, 'f': refF, 'fk': refF}; gap_fix(M, F, kind, (dmin + (dmax - dmin) * sv) * L, mover, refs); refF = refs['f'] if mover != 'fk' else refs['fk']; refM = refs['m']
    if her_legs: plant(F, refF, legs=her_legs)
    if her_arms and not fh: plant(F, refF, legs=False, arms=True)
    if her_hands == 'thighs':  # her hands on the outside of his thighs (her L hand -> his R thigh), a third of the way down
        tg = {}
        for s_, o_ in (('L', 'R'), ('R', 'L')):
            hp_, kn_ = M.p(LEG[o_][0]), M.p(LEG[o_][1]); out_ = hp_ - M.p(PEL); out_[:, 2] = 0; out_ /= np.linalg.norm(out_, axis=-1, keepdims=True)
            tg[s_] = (hp_ + (kn_ - hp_) * .33 + out_ * 8.0, None)
        for s_ in 'LR':
            a_, b_, c_ = ARM[s_]; F.ik2(a_, b_, c_, tg[s_][0], None, pole=(F.p(b_) - F.p(a_)) - ZUP * 20)
    elif fh: plant(F, refF, legs=False, arms=True, arm_tgt=fh())
    for it in range(3 if mover in ('m', 'fk') else 1):  # his leg re-plant can drop his hips (reach) -> re-fix the gap, re-plant
        if it: a_, u_, L_ = gap(M, F, kind); M.translate_world(COM, u_ * (a_ - (L_ - (dmin + (dmax - dmin) * sv) * L_))[:, None])
        if mover in ('m', 'fk') or hh: plant(M, refM, legs=mover in ('m', 'fk'), arms=bool(hh), arm_tgt=hh() if hh not in (None, 'bed') and hh else None)
    report(name, F, M, ENT[kind]); LOG[name].update(info, period_s=per, depth_target_frac=[dmin, dmax], mover=mover)
    kf, km = keepset(clipdict(src, key + '_f')), keepset(clipdict(src, key + '_m'))
    return {name + '_f': encode(F, fps, kf, extra_t=(COM,)), name + '_m': encode(M, fps, km, extra_t=(COM,))}

def bake_doggy():
    m = MEAS['doggy']; per = m['period_s']; n, _ = frames_for(per); W = m['sig']
    sv = unit01(wave(W['stroke']['w'], n))                    # 1 = deepest (him minus her butt, screen x)
    rock = wave(W['her_x']['w'], n); rock = -(rock - rock.mean()) / max(1e-9, np.ptp(rock) / 2) * .026 * U   # 2.6 cm per-cycle amplitude; + = toward him
    def head_back(F, M, n):  # she looks back over her right shoulder, like the reference
        F.rotate_world(NECK, qaxis(ZUP, np.full(n, math.radians(22)))); F.rotate_world(HEAD, qaxis(ZUP, np.full(n, math.radians(26))))
    return bake_duo('roto_doggy', 'leito', 'doggy_3', 'vagina', sv, per, .30, .97, her_rock=rock, his_hands=PEL, pre=head_back, her_legs='knee')

def bake_press():
    m = MEAS['press']; per = m['period_s']; n, _ = frames_for(per); W = m['sig']
    sv = 1 - unit01(wave(W['stroke']['w'], n))   # screen-y stroke: his ROI lowest = deepest
    hb = wave(W['her_y']['w'], n); hb = -(hb - hb.mean()) / max(1e-9, np.ptp(hb) / 2) * .010 * U   # her butt bounce 1.0 cm, pushed down (= away from him) after each stroke
    return bake_duo('roto_press', 'billyy/bl_matingp', 'bl_matingp_3', 'vagina', sv, per, .58, .90, her_rock=hb, her_legs=False, her_arms=False, his_hands='bed')

def bake_oral():
    m = MEAS['oral']; per = m['period_s']; n, _ = frames_for(per); W = m['sig']
    sv = 1 - unit01(wave(W['stroke']['w'], n))   # face-minus-shaft x: face furthest toward him = deepest
    return bake_duo('roto_oral', 'leito3/l3_blowjob', 'l3_blowjob_3', 'mouth', sv, per, .66, .92, mover='fk', her_legs='knee', her_hands='thighs', his_slack_cm=4, calm={SP1: .6, SP2: .6, NECK: .75, HEAD: .75})

if __name__ == '__main__':
    C = {}
    MC = json.load(open(os.path.join(D, 'tools', 'roto', 'roto_mocap.json'))) if os.path.exists(os.path.join(D, 'tools', 'roto', 'roto_mocap.json')) else {}   # body-model mocap versions (mocap_bake.py)
    for f in (bake_twerk, bake_idle, bake_doggy, bake_press, bake_oral): C.update(f())
    for k, v in MC.items():
        if k in C: C[k] = v; LOG.setdefault(k, {})['source'] = 'mocap_bake.py (NLF SMPL-X fit + optimised retarget)'
    X3 = os.path.join(D, 'tools', 'roto', 'roto3_clips.json')   # roto3 clips (roto3_prone.py: NLF fit + optical-flow layer + optimisation; motion only)
    if os.path.exists(X3):
        X3 = json.load(open(X3)); L3 = X3.pop('_log', {})
        for k, v in X3.items(): C[k] = v; LOG[k] = L3.get(k, {})
    meta = {k: {'period_s': LOG.get(k.rsplit('_', 1)[0] if k.endswith(('_f', '_m')) else k, {}).get('period_s')} for k in C}
    js = ('/* generated by tools/roto/roto_bake.py: rotoscoped motion (timing/amplitude/phase from reference videos) on XPMSSE poses. Clip format = tools/anims3d.py. */\n'
          'window.RB_ROTO3D=' + json.dumps({'clips': C, 'log': LOG}, separators=(',', ':')) + ';\n'
          + open(os.path.join(D, 'tools', 'roto', 'roto3d_tail.js'), encoding='utf-8').read())
    open(os.path.join(A, 'anims', 'roto3d.js'), 'w', encoding='utf-8').write(js)
    json.dump(LOG, open(os.path.join(D, 'tools', 'roto', 'roto_bake_log.json'), 'w'), indent=1)
    print('wrote roto3d.js', round(os.path.getsize(os.path.join(A, 'anims', 'roto3d.js')) / 1e3, 1), 'KB; clips', list(C))
