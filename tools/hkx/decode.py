# Decode one Skyrim SE HKX animation -> JSON (local per-track transforms per frame + skeleton + annotations),
# with validation stats. Usage: python -I decode.py <anim.hkx> <out.json> [skeleton.hkx]
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hkx

SKEL = os.environ.get("SKYRIM_SKELETON") or ("C:/Users/mytwo/soulbound/skyrim/src/XP32 Maximum Skeleton Special Extended/Skeleton Rig/HDT/"
        "meshes/actors/character/character assets/skeleton.hkx")


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qrot(q, v):
    x, y, z, w = q
    p = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return p[:3]


def ang(a, b):
    d = abs(sum(x * y for x, y in zip(a, b)))
    return math.degrees(2 * math.acos(min(1.0, d)))


def decode(path, skel_path=SKEL):
    r = hkx.load(path)
    sk = hkx.load(skel_path)["skeletons"][0]
    a = r["anims"][0]
    bd = r["bindings"][0]
    t2b = bd["t2b"] or list(range(a["ntt"]))
    # raw (pre-normalisation) quaternion norm check on control points
    worst_norm = 0.0
    for tr in a["blocks"][0]:
        R = tr[1]
        pts = R.cps if R.kind == "spline" else [R.static]
        for q in pts:
            worst_norm = max(worst_norm, abs(math.sqrt(sum(x * x for x in q)) - 1))
    frames = hkx.sample_frames(a)
    # continuity: worst per-frame angular step of any track
    worst_step, worst_at = 0.0, None
    for f in range(1, len(frames)):
        for t in range(a["ntt"]):
            s = ang(frames[f][t][1], frames[f - 1][t][1])
            if s > worst_step:
                worst_step, worst_at = s, (f, sk["bones"][t2b[t]])
    anns = []
    for _, lst in a["annotations"]:
        anns += [(round(t, 4), s) for t, s in lst]
    anns.sort()
    out = dict(src=path, version=r["version"], duration=a["duration"], numFrames=a["numFrames"],
               fps=round(1 / a["frameDuration"], 3), tracks=[sk["bones"][i] for i in t2b], t2b=t2b,
               skeleton=dict(bones=sk["bones"], parents=sk["parents"], ref=sk["ref"]),
               annotations=anns, rotQuant=a["rotQuantStats"],
               validate=dict(ctrl_quat_norm_err=worst_norm, worst_frame_step_deg=worst_step, worst_at=worst_at,
                             block_bytes_used=a["blockEnds"], data_len=a["dataLen"]),
               frames=[[[list(map(lambda v: round(v, 5), t)), list(map(lambda v: round(v, 6), q)),
                         list(map(lambda v: round(v, 4), s))] for t, q, s in row] for row in frames])
    return out


if __name__ == "__main__":
    o = decode(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else SKEL)
    json.dump(o, open(sys.argv[2], "w"))
    print(json.dumps({k: o[k] for k in ("duration", "numFrames", "fps", "rotQuant", "validate")}))
    print(o["annotations"])
