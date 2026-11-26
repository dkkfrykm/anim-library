"""Pure-Python copy of the clip encoder (sky2r15/build.py) for authored clips without Blender."""
import posecheck as _pc
class rig: ORDER = _pc.ORDER
TOL = 3.5
PTOL = 0.03
SHORT = {"Root": "Rt", "Waist": "W", "Neck": "N", "RightShoulder": "RS", "RightElbow": "RE", "RightWrist": "RW",
         "LeftShoulder": "LS", "LeftElbow": "LE", "LeftWrist": "LW", "RightHip": "RH", "RightKnee": "RK",
         "RightAnkle": "RA", "LeftHip": "LH", "LeftKnee": "LK", "LeftAnkle": "LA"}
ALPHA = "".join(chr(c) for c in range(35, 127) if chr(c) != "]")


def e1(v):
    a = ((v + 180) % 360) - 180
    return ALPHA[max(0, min(90, int(round((a + 180) / 4))))]


def e2(v):
    v = max(0, min(91 * 91 - 1, int(v)))
    return ALPHA[v // 91] + ALPHA[v % 91]


def decimate_series(vals, force, tol):
    n = len(vals)
    keep = [0]
    s = 0
    dims = len(vals[0])
    while s < n - 1:
        best = s + 1
        e = s + 2
        while e < n:
            ok = True
            for m in range(s + 1, e):
                t = (m - s) / (e - s)
                for ax in range(dims):
                    v = vals[s][ax] + (vals[e][ax] - vals[s][ax]) * t
                    if abs(v - vals[m][ax]) > tol:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
            if any(abs(vals[e][ax] - vals[s][ax]) > 80 for ax in range(dims)):
                break
            best = e
            if e in force:
                break
            e += 1
        if any(s < f < best for f in force):
            best = min(f for f in force if s < f < best)
        keep.append(best)
        s = best
    return keep


def unwrap(vals):  # keep euler series continuous for decimation (encoder wraps anyway)
    out = [list(vals[0])]
    for v in vals[1:]:
        o = list(v)
        for k in range(3):
            while o[k] - out[-1][k] > 180: o[k] -= 360
            while o[k] - out[-1][k] < -180: o[k] += 360
        out.append(o)
    return out


def lua_clip(name, mk, frames):
    force = set(mk["i"]) | {mk["w"], mk["r"], mk["n"]}
    parts = []
    for j in rig.ORDER:
        vals = unwrap([frames[k][j] for k in range(len(frames))])
        if all(abs(v[0]) < 0.6 and abs(v[1]) < 0.6 and abs(v[2]) < 0.6 for v in vals):
            continue
        ks = decimate_series(vals, force, TOL)
        # 1-char frame delta caps at 90: split long gaps
        parts.append("%s=[[%s]]" % (SHORT[j], enc_keys(ks, lambda k: e1(vals[k][0]) + e1(vals[k][1]) + e1(vals[k][2]))))
    pv = [frames[k]["p"] for k in range(len(frames))]
    if any(abs(x) > 0.01 for v in pv for x in v):
        ks = decimate_series(pv, force, PTOL)
        parts.append("p=[[%s]]" % enc_keys(ks, lambda k: e2(pv[k][0] * 100 + 4000) + e2(pv[k][1] * 100 + 4000) + e2(pv[k][2] * 100 + 4000)))
    meta = "n=%d,w=%d,i={%s},r=%d" % (mk["n"], mk["w"], ",".join(str(i) for i in mk["i"]), mk["r"])
    if mk["sw"]:
        meta += ",sw={%s}" % ",".join(str(i) for i in mk["sw"])
    return "%s={%s,%s}" % (name, meta, ",".join(parts))


def enc_keys(ks, val):
    out = []
    prev = 0
    for n, k in enumerate(ks):
        d = k - prev if n else k
        while d > 90:  # never happens for < 1.5 s gaps; insert a hold key if it does
            out.append(ALPHA[90] + val(prev)); d -= 90; prev += 90
        out.append(ALPHA[d] + val(k))
        prev = k
    return "".join(out)
