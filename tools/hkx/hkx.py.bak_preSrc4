# Pure-Python reader for Havok 2010 (hk_2010.2.0-r1) 64-bit packfiles as used by Skyrim SE.
# Reads hkaAnimationContainer: hkaSkeleton, hkaSplineCompressedAnimation (decompressed), hkaAnimationBinding,
# annotation tracks. Input files are treated as data only.
import struct, math, os


def longpath(p):
    """Windows MAX_PATH (260) workaround: extended-length prefix for long absolute paths"""
    pre = "\\\\?\\"
    if os.name == "nt" and len(p) >= 240 and not p.startswith(pre):
        return pre + os.path.abspath(p).replace("/", "\\")
    return p


class Packfile:
    def __init__(self, path):
        self.b = b = open(longpath(path), "rb").read()
        m0, m1, utag, ver = struct.unpack_from("<IIii", b, 0)
        assert (m0, m1) == (0x57E0E057, 0x10C0C010), "not a havok packfile"
        self.ptr, self.le = b[16], b[17]
        assert self.ptr == 8 and self.le == 1, "expected 64-bit little endian"
        nsec, = struct.unpack_from("<i", b, 20)
        self.cidx, self.coff, self.cnidx, self.cnoff = struct.unpack_from("<iiii", b, 24)
        self.version = b[40:56].split(b"\0")[0].decode("latin1")
        hs = 0x40
        self.sections = []
        for i in range(nsec):
            o = hs + i * 0x30
            tag = b[o:o + 19].split(b"\0")[0].decode("latin1")
            start, lf, gf, vf, ex, im, end = struct.unpack_from("<7i", b, o + 20)
            self.sections.append(dict(tag=tag, start=start, lf=lf, gf=gf, vf=vf, ex=ex, im=im, end=end))
        self.ptrs = {}      # absolute src -> absolute dst
        self.objclass = {}  # absolute obj -> class name
        for s in self.sections:
            st = s["start"]
            o = st + s["lf"]
            while o + 8 <= st + s["gf"]:
                a, d = struct.unpack_from("<ii", b, o); o += 8
                if a == -1: continue
                self.ptrs[st + a] = st + d
            o = st + s["gf"]
            while o + 12 <= st + s["vf"]:
                a, sec, d = struct.unpack_from("<iii", b, o); o += 12
                if a == -1: continue
                self.ptrs[st + a] = self.sections[sec]["start"] + d
            o = st + s["vf"]
            while o + 12 <= st + s["ex"]:
                a, sec, d = struct.unpack_from("<iii", b, o); o += 12
                if a == -1: continue
                no = self.sections[sec]["start"] + d
                self.objclass[st + a] = b[no:b.index(b"\0", no)].decode("latin1")

    def objects(self, cls):
        return [o for o, c in sorted(self.objclass.items()) if c == cls]

    def i16(self, o): return struct.unpack_from("<h", self.b, o)[0]
    def i32(self, o): return struct.unpack_from("<i", self.b, o)[0]
    def f32(self, o): return struct.unpack_from("<f", self.b, o)[0]
    def p(self, o): return self.ptrs.get(o)

    def cstr(self, o):
        d = self.p(o)
        if d is None: return None
        return self.b[d:self.b.index(b"\0", d)].decode("latin1")

    def arr(self, o):  # hkArray (64-bit): ptr, int size, int capacityAndFlags
        return self.p(o), self.i32(o + 8)


# ------------------------------------------------------------------------ skeleton
def read_qs(b, o):
    t = struct.unpack_from("<4f", b, o); q = struct.unpack_from("<4f", b, o + 16); s = struct.unpack_from("<4f", b, o + 32)
    return dict(t=t[:3], q=q, s=s[:3])  # q = (x, y, z, w)


def read_skeleton(pf, o):
    name = pf.cstr(o + 16)
    pp, pn = pf.arr(o + 24)
    parents = [pf.i16(pp + 2 * i) for i in range(pn)]
    bp, bn = pf.arr(o + 40)
    bones = [pf.cstr(bp + 16 * i) for i in range(bn)]
    rp, rn = pf.arr(o + 56)
    ref = [read_qs(pf.b, rp + 48 * i) for i in range(rn)]
    return dict(name=name, parents=parents, bones=bones, ref=ref)


# ------------------------------------------------------------------------ binding / annotations
def read_binding(pf, o):
    tp, tn = pf.arr(o + 32)
    return dict(skel=pf.cstr(o + 16), anim=pf.p(o + 24), t2b=[pf.i16(tp + 2 * i) for i in range(tn)])


def read_anim_base(pf, o):
    a = dict(type=pf.i32(o + 16), duration=pf.f32(o + 20), ntt=pf.i32(o + 24), nft=pf.i32(o + 28),
             motion=pf.p(o + 32), cls=pf.objclass.get(o))
    ap, an = pf.arr(o + 40)
    tracks = []
    for i in range(an):
        t = ap + 24 * i
        np_, nn = pf.arr(t + 8)
        anns = [(pf.f32(np_ + 16 * k), pf.cstr(np_ + 16 * k + 8)) for k in range(nn)]
        tracks.append((pf.cstr(t), anns))
    a["annotations"] = tracks
    return a


# ------------------------------------------------------------------------ spline decompression
ROT_SIZE = {0: 4, 1: 5, 2: 6, 3: 3, 4: 2, 5: 16}
ROT_ALIGN = {0: 4, 1: 1, 2: 2, 3: 1, 4: 2, 5: 4}
R2 = 0.7071067811865476


def _align(o, base, a):
    r = (o - base) % a
    return o + (a - r) % a


def _finish(v, shift, neg):
    w = math.sqrt(max(0.0, 1.0 - (v[0] ** 2 + v[1] ** 2 + v[2] ** 2)))
    if neg: w = -w
    v.insert(shift, w)
    return tuple(v)


def q48(b, o):
    x, y, z = struct.unpack_from("<3H", b, o)
    shift = ((y >> 14) & 2) | ((x >> 15) & 1)
    neg = (z >> 15) & 1
    M = 0x7FFF
    f = R2 / 16383.5
    return _finish([((x & M) - 16383.5) * f, ((y & M) - 16383.5) * f, ((z & M) - 16383.5) * f], shift, neg)


def q40(b, o):
    n = int.from_bytes(b[o:o + 5], "little")
    M = 0xFFF
    f = R2 / 2047.5
    v = [((n & M) - 2047.5) * f, (((n >> 12) & M) - 2047.5) * f, (((n >> 24) & M) - 2047.5) * f]
    return _finish(v, (n >> 36) & 3, (n >> 38) & 1)


def q24(b, o):
    n = int.from_bytes(b[o:o + 3], "little")
    M = 0x7F
    f = R2 / 63.5
    v = [((n & M) - 63.5) * f, (((n >> 7) & M) - 63.5) * f, (((n >> 14) & M) - 63.5) * f]
    return _finish(v, (n >> 21) & 3, (n >> 23) & 1)


def read_quat(b, o, qt):
    if qt == 2: return q48(b, o)
    if qt == 1: return q40(b, o)
    if qt == 3: return q24(b, o)
    if qt == 5: return struct.unpack_from("<4f", b, o)
    raise NotImplementedError("rotation quantisation %d" % qt)


def find_span(deg, t, ncp, knots):
    if t >= knots[ncp]:
        return ncp - 1
    if t <= knots[deg]:
        return deg
    lo, hi = deg, ncp
    mid = (lo + hi) // 2
    while t < knots[mid] or t >= knots[mid + 1]:
        if t < knots[mid]: hi = mid
        else: lo = mid
        mid = (lo + hi) // 2
    return mid


def basis(span, t, deg, knots):
    N = [1.0] + [0.0] * deg
    left = [0.0] * (deg + 1); right = [0.0] * (deg + 1)
    for j in range(1, deg + 1):
        left[j] = t - knots[span + 1 - j]
        right[j] = knots[span + j] - t
        saved = 0.0
        for r in range(j):
            den = right[r + 1] + left[j - r]
            tmp = N[r] / den if den else 0.0
            N[r] = saved + right[r + 1] * tmp
            saved = left[j - r] * tmp
        N[j] = saved
    return N


def eval_spline(t, deg, knots, cps):
    ncp = len(cps)
    span = find_span(deg, t, ncp, knots)
    N = basis(span, t, deg, knots)
    dim = len(cps[0])
    out = [0.0] * dim
    for i in range(deg + 1):
        c = cps[span - deg + i]
        for k in range(dim):
            out[k] += N[i] * c[k]
    return out


class Track:
    __slots__ = ("kind", "deg", "knots", "cps", "static")

    def __init__(self, kind, static=None, deg=0, knots=None, cps=None):
        self.kind, self.static, self.deg, self.knots, self.cps = kind, static, deg, knots, cps

    def at(self, t):
        if self.kind == "spline":
            return eval_spline(t, self.deg, self.knots, self.cps)
        return list(self.static)


def read_vec_track(b, o, base, mask, quant, ident):
    spl = (mask >> 4) & 7
    sta = mask & 7
    if spl:
        n = struct.unpack_from("<H", b, o)[0]; deg = b[o + 2]; o += 3
        knots = list(b[o:o + n + deg + 2]); o += n + deg + 2
        o = _align(o, base, 4)
        rng = []
        for ax in range(3):
            if spl & (1 << ax):
                mn, mx = struct.unpack_from("<2f", b, o); o += 8; rng.append(("s", mn, mx))
            elif sta & (1 << ax):
                v, = struct.unpack_from("<f", b, o); o += 4; rng.append(("c", v))
            else:
                rng.append(("c", ident))
        cps = []
        for i in range(n + 1):
            cp = []
            for ax in range(3):
                r = rng[ax]
                if r[0] == "s":
                    if quant == 0:
                        q = b[o] / 255.0; o += 1
                    else:
                        q = struct.unpack_from("<H", b, o)[0] / 65535.0; o += 2
                    cp.append(r[1] + (r[2] - r[1]) * q)
                else:
                    cp.append(r[1])
            cps.append(cp)
        o = _align(o, base, 4)
        return o, Track("spline", deg=deg, knots=knots, cps=cps)
    v = [ident] * 3
    for ax in range(3):
        if sta & (1 << ax):
            v[ax], = struct.unpack_from("<f", b, o); o += 4
    return o, Track("static", static=v)


def read_rot_track(b, o, base, mask, qt):
    if mask & 0xF0:
        n = struct.unpack_from("<H", b, o)[0]; deg = b[o + 2]; o += 3
        knots = list(b[o:o + n + deg + 2]); o += n + deg + 2
        o = _align(o, base, ROT_ALIGN[qt])
        cps = []
        for i in range(n + 1):
            cps.append(read_quat(b, o, qt)); o += ROT_SIZE[qt]
        for i in range(1, len(cps)):  # hemisphere continuity
            if sum(a * c for a, c in zip(cps[i], cps[i - 1])) < 0:
                cps[i] = tuple(-x for x in cps[i])
        o = _align(o, base, 4)
        return o, Track("spline", deg=deg, knots=knots, cps=cps)
    if mask & 0x0F:
        o = _align(o, base, ROT_ALIGN[qt])
        q = read_quat(b, o, qt); o += ROT_SIZE[qt]
        o = _align(o, base, 4)
        return o, Track("static", static=q)
    return o, Track("static", static=(0.0, 0.0, 0.0, 1.0))


def read_spline_anim(pf, o):
    a = read_anim_base(pf, o)
    b = pf.b
    a.update(numFrames=pf.i32(o + 56), numBlocks=pf.i32(o + 60), maxFPB=pf.i32(o + 64), mqs=pf.i32(o + 68),
             blockDuration=pf.f32(o + 72), blockInv=pf.f32(o + 76), frameDuration=pf.f32(o + 80))
    bop, bon = pf.arr(o + 88)
    a["blockOffsets"] = [pf.i32(bop + 4 * i) for i in range(bon)]
    dp, dn = pf.arr(o + 152)
    a["dataStart"], a["dataLen"] = dp, dn
    nt = a["ntt"]
    blocks, ends = [], []
    stats = {}
    for bi in range(a["numBlocks"]):
        base = dp + a["blockOffsets"][bi]
        masks = [tuple(b[base + 4 * t: base + 4 * t + 4]) for t in range(nt)]
        oo = base + a["mqs"]
        tracks = []
        for t in range(nt):
            qtypes, pm, rm, sm = masks[t]
            pq = qtypes & 3; rq = (qtypes >> 2) & 0xF; sq = (qtypes >> 6) & 3
            stats[rq] = stats.get(rq, 0) + 1
            oo, P = read_vec_track(b, oo, base, pm, pq, 0.0)
            oo, R = read_rot_track(b, oo, base, rm, rq)
            oo, S = read_vec_track(b, oo, base, sm, sq, 1.0)
            tracks.append((P, R, S))
        blocks.append(tracks)
        ends.append(oo - base)
    a["blocks"], a["blockEnds"], a["rotQuantStats"] = blocks, ends, stats
    return a


def read_interleaved_anim(pf, o):
    """hkaInterleavedUncompressedAnimation (64-bit hk_2010): base(56) + hkArray<hkQsTransform> at 56 + hkArray<float> at 72"""
    a = read_anim_base(pf, o)
    tp, tn = pf.arr(o + 56)
    nt = max(1, a["ntt"])
    nf = tn // nt
    fr = []
    for f in range(nf):
        row = []
        for t in range(nt):
            q = tp + 48 * (f * nt + t)
            v = struct.unpack_from("<12f", pf.b, q)
            r = v[4:8]; n = math.sqrt(sum(x * x for x in r)) or 1.0
            row.append((tuple(v[0:3]), tuple(x / n for x in r), tuple(v[8:11])))
        fr.append(row)
    a.update(numFrames=nf, frameDuration=(a["duration"] / max(1, nf - 1)), frames=fr)
    return a


def sample_frames(a):
    """-> list over frames of list over tracks of (t xyz, q xyzw normalised, s xyz)"""
    if "frames" in a:
        return a["frames"]
    out = []
    fpb = a["maxFPB"]
    for f in range(a["numFrames"]):
        bi = min(f // (fpb - 1), a["numBlocks"] - 1)
        lt = float(f - bi * (fpb - 1))
        row = []
        for P, R, S in a["blocks"][bi]:
            q = R.at(lt)
            n = math.sqrt(sum(x * x for x in q)) or 1.0
            row.append((tuple(P.at(lt)), tuple(x / n for x in q), tuple(S.at(lt))))
        out.append(row)
    return out


def load(path):
    pf = Packfile(path)
    res = dict(version=pf.version, classes=sorted(set(pf.objclass.values())))
    sk = pf.objects("hkaSkeleton")
    if sk: res["skeletons"] = [read_skeleton(pf, o) for o in sk]
    an = pf.objects("hkaSplineCompressedAnimation")
    if an: res["anims"] = [read_spline_anim(pf, o) for o in an]
    ia = pf.objects("hkaInterleavedUncompressedAnimation")
    if ia: res.setdefault("anims", []).extend(read_interleaved_anim(pf, o) for o in ia)
    bd = pf.objects("hkaAnimationBinding")
    if bd: res["bindings"] = [read_binding(pf, o) for o in bd]
    return res
