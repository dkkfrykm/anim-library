"""Body-model mocap -> XPMSSE retarget helpers (numpy). Used by mocap_bake.py.
Input: per-frame SMPL / SMPL-X fits from NLF (Neural Localizer Fields, github.com/isarandi/nlf, torchscript run in a scratch venv):
axis-angle pose per joint (camera frame), joints3d (camera, m). Only motion is used.
Frames: camera (x right, y down, z away) -> Skyrim (X her right, Y her front, Z up, units ~1.4286 cm). SMPL canonical: x body-left, y up, z front."""
import os, sys, json, math
import numpy as np

SMPL_PARENT = [-1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19]  # first 22 joints (SMPL and SMPL-X share them)
# SMPL-X hands: 25-39 left (index1-3, middle1-3, pinky1-3, ring1-3, thumb1-3), 40-54 right; parents: wrist for each *1, previous for 2,3
SMPLX_HAND = {'L': 25, 'R': 40}
MCAM = np.array([[-1, 0, 0], [0, 0, -1], [0, -1, 0.0]])   # camera -> Skyrim
MCAN = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0.0]])     # SMPL canonical -> Skyrim
U = 1 / 0.014286

def rodrigues(v):
    v = np.asarray(v, float); th = np.linalg.norm(v, axis=-1, keepdims=True); k = v / np.maximum(th, 1e-12); th = th[..., None]
    K = np.zeros(v.shape[:-1] + (3, 3)); K[..., 0, 1] = -k[..., 2]; K[..., 0, 2] = k[..., 1]; K[..., 1, 0] = k[..., 2]; K[..., 1, 2] = -k[..., 0]; K[..., 2, 0] = -k[..., 1]; K[..., 2, 1] = k[..., 0]
    I = np.broadcast_to(np.eye(3), K.shape); return I + np.sin(th) * K + (1 - np.cos(th)) * (K @ K)
def m2q(M):
    M = np.asarray(M, float); sh = M.shape[:-2]; M = M.reshape(-1, 3, 3); q = np.zeros((len(M), 4))
    for i, m in enumerate(M):
        tr = m[0, 0] + m[1, 1] + m[2, 2]
        if tr > 0: s = math.sqrt(tr + 1) * 2; q[i] = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]
        elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]: s = math.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2; q[i] = [s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
        elif m[1, 1] > m[2, 2]: s = math.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2; q[i] = [(m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
        else: s = math.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2; q[i] = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4, (m[1, 0] - m[0, 1]) / s]
    q /= np.linalg.norm(q, axis=-1, keepdims=True); return q.reshape(sh + (4,))
def q2m(q):
    x, y, z, w = np.moveaxis(np.asarray(q, float), -1, 0)
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1), np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)
def nrm(v): return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)
def frame(a, b):
    a = nrm(a); b = nrm(b - a * (a * b).sum(-1, keepdims=True)); return np.stack([a, b, np.cross(a, b)], -1)
def rot_log(Rm):
    c = np.clip((np.trace(Rm, axis1=-2, axis2=-1) - 1) / 2, -1, 1); th = np.arccos(c)
    v = np.stack([Rm[..., 2, 1] - Rm[..., 1, 2], Rm[..., 0, 2] - Rm[..., 2, 0], Rm[..., 1, 0] - Rm[..., 0, 1]], -1)
    s = np.sin(th)[..., None]; return np.where(s > 1e-6, v / np.maximum(2 * s, 1e-9) * th[..., None], v / 2)
def slerp_m(A, B, w):
    return A @ rodrigues(rot_log(np.swapaxes(A, -1, -2) @ B) * np.asarray(w)[..., None])

def smpl_globals(pose):
    """pose [n, J*3] axis-angle (local) -> global rotations [n, 22, 3, 3] in camera frame"""
    n = len(pose); L = rodrigues(pose.reshape(n, -1, 3)); G = np.zeros((n, 22, 3, 3))
    for j in range(22):
        p = SMPL_PARENT[j]; G[:, j] = L[:, j] if p < 0 else G[:, p] @ L[:, j]
    return G, L
def smpl_rest_offsets(G, J):
    """rest (canonical) offsets child-parent from posed joints + globals: off = G_p^T (J_c - J_p), robust median over frames"""
    off = np.zeros((22, 3))
    for j in range(1, 22):
        p = SMPL_PARENT[j]; o = np.einsum('nji,nj->ni', G[:, p], J[:, j] - J[:, p]); off[j] = np.nanmedian(o, 0)
    return off

# ---------------- XPMSSE mapping ----------------
def names():
    N = {'COM': 'NPC COM [COM ]', 'PEL': 'NPC Pelvis [Pelv]', 'SP0': 'NPC Spine [Spn0]', 'SP1': 'NPC Spine1 [Spn1]', 'SP2': 'NPC Spine2 [Spn2]', 'NECK': 'NPC Neck [Neck]', 'HEAD': 'NPC Head [Head]'}
    for s in 'LR':
        N.update({s + 'CLV': 'NPC %s Clavicle [%sClv]' % (s, s), s + 'UA': 'NPC %s UpperArm [%sUar]' % (s, s), s + 'FA': 'NPC %s Forearm [%sLar]' % (s, s), s + 'HD': 'NPC %s Hand [%sHnd]' % (s, s),
                  s + 'TH': 'NPC %s Thigh [%sThg]' % (s, s), s + 'CF': 'NPC %s Calf [%sClf]' % (s, s), s + 'FT': 'NPC %s Foot [%sft ]' % (s, s), s + 'TOE': 'NPC %s Toe0 [%sToe]' % (s, s),
                  s + 'T1': 'NPC %s ForearmTwist1 [%sLt1]' % (s, s), s + 'T2': 'NPC %s ForearmTwist2 [%sLt2]' % (s, s), s + 'F00': 'NPC %s Finger00 [%sF00]' % (s, s), s + 'F10': 'NPC %s Finger10 [%sF10]' % (s, s),
                  s + 'F20': 'NPC %s Finger20 [%sF20]' % (s, s), s + 'F40': 'NPC %s Finger40 [%sF40]' % (s, s)})
    return N
N = names()
# XPMSSE bone key -> SMPL joint whose global rotation drives it
SMPL_OF = {'COM': 0, 'SP0': 3, 'SP1': 6, 'SP2': 9, 'NECK': 12, 'HEAD': 15, 'LCLV': 13, 'RCLV': 14, 'LUA': 16, 'RUA': 17, 'LFA': 18, 'RFA': 19, 'LHD': 20, 'RHD': 21,
           'LTH': 1, 'RTH': 2, 'LCF': 4, 'RCF': 5, 'LFT': 7, 'RFT': 8}

def hand_rest_offsets(G, J55):
    """SMPL-X rest offsets (canonical) wrist -> index1 / middle1 / pinky1 per side (palm frame for the hand T-pose)"""
    out = {}
    for s, wr, (ix, mi, pk) in (('L', 20, (25, 28, 31)), ('R', 21, (40, 43, 46))):
        out[s] = {k: np.nanmedian(np.einsum('nji,nj->ni', G[:, wr], J55[:, j] - J55[:, wr]), 0) for k, j in (('ix', ix), ('mi', mi), ('pk', pk))}
    return out
def build_tpose(R, S, off, hand=None):
    """Reiko's skeleton posed like the SMPL rest (T-pose of this subject's offsets), as world quaternions per mapped bone.
    Each bone: primary = direction to its child joint matched to the SMPL segment; secondary (twist) = an anatomical axis:
    lateral for trunk/head/feet, front for arms (elbow bends forward, thumb forward = palms down) and legs (kneecap forward)."""
    Q0 = S['q'][None].copy(); T0 = S['t'][None].copy(); P = R.Pose(S, Q0, T0)
    can = lambda v: MCAN @ v
    def J(j):  # SMPL rest joint position (canonical -> Skyrim), pelvis at 0
        p = np.zeros(3); k = j
        while k > 0: p = p + off[k]; k = SMPL_PARENT[k]
        return can(p)
    X, Y, Z = np.eye(3)
    hipv = J(2) - J(1); upv = J(3) - J(0)
    # trunk (spine, neck, head) and clavicles keep HER rest posture: at SMPL zero pose she stands in her own bind posture (no imported
    # collar slope = no shrug, no imported spine curve = no hunch); SMPL's spine/collar rotations then act as deltas on her posture.
    spec = [('COM', None, hipv, upv, 'lat')]
    for s, sg in (('L', 1), ('R', 2)):
        c, sh, el, wr = (13, 16, 18, 20) if s == 'L' else (14, 17, 19, 21); hp, kn, an, ft = (1, 4, 7, 10) if s == 'L' else (2, 5, 8, 11)
        hd_t = (can(hand[s]['mi']), can(hand[s]['ix'] - hand[s]['pk'])) if hand else (J(wr) - J(el), Y)
        spec += [(s + 'UA', s + 'FA', J(el) - J(sh), Y, 'bend'), (s + 'FA', s + 'HD', J(wr) - J(el), Y, 'thumb'),
                 (s + 'HD', s + 'F20', hd_t[0], hd_t[1], 'palm' if hand else 'thumb'), (s + 'TH', s + 'CF', J(kn) - J(hp), Y, 'Y'), (s + 'CF', s + 'FT', J(an) - J(kn), Y, 'Y'), (s + 'FT', s + 'TOE', J(ft) - J(an), X, 'X')]
    W = {}
    for key, child, tp, ts, kind in spec:
        b = N[key]; p0 = P.p(b)[0]
        if kind == 'head': continue      # head keeps its rest pose relative to the neck
        if kind == 'lat': pr, se = P.p(N['RTH'])[0] - P.p(N['LTH'])[0], P.p(N['SP1'])[0] - p0
        else:
            pr = P.p(N[child])[0] - p0
            if kind == 'X': se = X
            elif kind == 'Y': se = Y
            elif kind == 'bend': se = P.p(N[child[0] + 'HD'])[0] - P.p(N[child])[0]   # forearm direction: elbow bend plane
            elif kind == 'thumb': hd = N[key[0] + 'HD']; se = P.p(N[key[0] + 'F00'])[0] - P.p(hd)[0]
            elif kind == 'palm': se = P.p(N[key[0] + 'F10'])[0] - P.p(N[key[0] + 'F40'])[0]   # index -> pinky knuckle line (matches SMPL-X index1 - pinky1)
        Ft, F0 = frame(tp, ts), frame(pr, se)
        Rw = Ft @ F0.T; P.set_world_q(b, R.qmul(m2q(Rw)[None], P.wq(b)))
        W[key] = P.wq(b)[0]
    for k in SMPL_OF: W[k] = P.wq(N[k])[0]   # final T-pose world rotation of every driven bone (aligned limbs; trunk/clavicles/head = her rest)
    return P, W

# ---------------- natural relaxed hand ----------------
def relaxed_fingers(R, S, PT, path, amount=.75):
    """finger + thumb local rotations (relative to the hand) for a natural relaxed hand: each XPMSSE finger segment is turned to the
    direction of the matching SMPL-X segment in a blend of the flat and the model-mean (relaxed) hand (amount 0..1), in the T-pose
    where her palm is aligned to the SMPL-X palm. Directions only (minimal swing), so flex always goes the anatomical way."""
    H = json.load(open(path)); P = R.Pose(S, PT.Q.copy(), PT.T.copy()); out = {}
    for s in 'LR':
        for f, xf in (('thumb', 0), ('index', 1), ('middle', 2), ('ring', 3), ('pinky', 4)):
            fl = np.array(H[s]['flat'][f]); rl = np.array(H[s]['relaxed'][f]); names_ = ['NPC %s Finger%d%d [%sF%d%d]' % (s, xf, k, s, xf, k) for k in range(3)]
            for k in range(3):
                df = nrm(fl[k + 1] - fl[k]); dr = nrm(rl[k + 1] - rl[k]); tgt = MCAN @ nrm(df * (1 - amount) + dr * amount)
                b = names_[k]; p0 = P.p(b)[0]
                cur = (P.p(names_[k + 1])[0] - p0) if k < 2 else (P.p(names_[2])[0] - P.p(names_[1])[0])
                c = nrm(cur); ax = np.cross(c, tgt); sn = np.linalg.norm(ax); cs = float(c @ tgt)
                if sn > 1e-8:
                    Rw = rodrigues((ax / sn * math.atan2(sn, cs))[None])[0]
                    P.set_world_q(b, R.qmul(m2q(Rw)[None], P.wq(b)))
            for b in names_: out[b] = P.Q[0, S['i'][b]].copy()
    return out
