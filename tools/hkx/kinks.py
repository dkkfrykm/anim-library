# Kink hunt over built clips (rows.json + markers.json): pops / acceleration spikes outside strike windows, elbow
# hyperextension and wrist flips, start-vs-stance snaps, loop seams (hit loops and Idle loops), plus posecheck gates.
# Run: python kinks.py <dir> [--json out.json] [--verbose]
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import posecheck as PC

ARMJ = {"RightShoulder", "RightElbow", "RightWrist", "LeftShoulder", "LeftElbow", "LeftWrist"}
LIMB = ARMJ | {"RightHip", "RightKnee", "RightAnkle", "LeftHip", "LeftKnee", "LeftAnkle"}
VEL = {"limb": 30.0, "body": 18.0}      # deg/frame outside strike windows
ACC = {"limb": 22.0, "body": 14.0}      # deg/frame^2 (change of angular speed) outside strike windows
SEAM = 12.0                              # deg per joint max jump across a loop seam
START = 45.0                             # deg per joint: frame 0 vs the power's stance (crossfade is 0.08 s)


def rot(row):
    return {j: PC.R(row.get(j, (0, 0, 0))) for j in PC.ORDER}


def jdist(a, b):
    return {j: PC.angle(a[j], b[j]) for j in PC.ORDER}


DIRECT = ("bladedancer", "divinesaiyan")  # authored HKX sets kept as-is: strike window from w-8 (same as QA)


def windows(mk, sword=False):
    i, w, r, n = mk["i"][0], mk["w"], mk["r"], mk["n"]
    return [(max(0, w - (8 if sword else 3)), min(n, r + (3 if sword else 0)))]


def analyse(name, rows, mk, stance0=None):
    out = {}
    n = mk["n"]
    main = rows[:n + 1]
    R = [rot(x) for x in main]
    win = windows(mk, name.split("_")[1] in DIRECT)
    inwin = lambda f: any(a <= f <= b for a, b in win)
    vel = [None] + [jdist(R[f - 1], R[f]) for f in range(1, len(R))]
    for f in range(1, len(R)):
        if inwin(f):
            continue
        for j, v in vel[f].items():
            if v > VEL["limb" if j in LIMB else "body"]:
                out.setdefault("pop", []).append((f, j, round(v)))
                break
        if f >= 2:
            for j in PC.ORDER:
                a = abs(vel[f][j] - vel[f - 1][j])
                if a > ACC["limb" if j in LIMB else "body"]:
                    out.setdefault("accel", []).append((f, j, round(a)))
                    break
    for f, row in enumerate(main):  # elbow hyperextension (negative bend) / wrist folded past 95 deg
        for s in ("Right", "Left"):
            e = row.get(s + "Elbow", (0, 0, 0))
            if e[0] < -8:
                out.setdefault("elbow_hyper", []).append((f, s, round(e[0])))
            wr = row.get(s + "Wrist", (0, 0, 0))
            a = PC.angle(PC.R((0, 0, 0)), PC.R(wr))
            if a > 130 and not inwin(f):  # wrist folded/twisted past anatomical range outside a strike
                out.setdefault("wrist_flip", []).append((f, s, round(a)))
    if stance0 is not None and not name.endswith("_Idle"):
        d = jdist(stance0, R[0])
        worst = max(d.items(), key=lambda kv: kv[1])
        if worst[1] > START:
            out["start_snap"] = [(0, worst[0], round(worst[1]))]
    if mk.get("la"):
        la, lb = mk["la"], mk["lb"]
        if lb < len(rows):
            d = jdist(rot(rows[la]), rot(rows[lb]))
            worst = max(d.items(), key=lambda kv: kv[1])
            if worst[1] > SEAM:
                out["loop_seam"] = [(la, worst[0], round(worst[1]))]
    if name.endswith("_Idle"):
        d = jdist(R[0], rot(rows[-1]))
        worst = max(d.items(), key=lambda kv: kv[1])
        if worst[1] > SEAM:
            out["idle_seam"] = [(len(rows) - 1, worst[0], round(worst[1]))]
    g = PC.check(main)
    for k in ("foot_slide", "hand_in_torso", "hand_in_head", "crossed_knees", "extreme_lean"):
        if k in g and not inwin(g[k][0]):
            out.setdefault("gate_" + k, []).extend(g[k][:3])
    return out


def main():
    D = sys.argv[1]
    rows = json.load(open(os.path.join(D, "rows.json")))
    mks = json.load(open(os.path.join(D, "markers.json")))
    stance = {}
    for name, r in rows.items():
        if name.endswith("_Idle"):
            stance[name.split("_")[1]] = rot(r[0])
    rep, tot = {}, {}
    for name, r in rows.items():
        mk = mks.get(name)
        if not mk:
            if name.endswith("_Idle"):
                mk = {"n": len(r) - 1, "w": 0, "i": [0], "r": len(r) - 1}
            else:
                continue
        pid = name.split("_")[1]
        k = analyse(name, r, mk, stance.get(pid))
        if k:
            rep[name] = k
            for kk, v in k.items():
                tot[kk] = tot.get(kk, 0) + 1
    print("clips analysed", len(rows), "with kinks", len(rep))
    print("clips per kink type:", tot)
    if "--verbose" in sys.argv:
        for nm, k in sorted(rep.items())[:60]:
            print(" ", nm, {a: b[:3] for a, b in k.items()})
    if "--json" in sys.argv:
        json.dump(rep, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=0)


if __name__ == "__main__":
    main()
