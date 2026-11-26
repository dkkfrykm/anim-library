# Read-only QA of the Enigma agent's Clips_StandPose (static stand-user poses) with posecheck.
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__)); import posecheck as PC
ALPHA = "".join(chr(c) for c in range(35, 127) if chr(c) != "]")
SHORT = {"Rt": "Root", "W": "Waist", "N": "Neck", "RS": "RightShoulder", "RE": "RightElbow", "RW": "RightWrist", "LS": "LeftShoulder", "LE": "LeftElbow",
         "LW": "LeftWrist", "RH": "RightHip", "RK": "RightKnee", "RA": "RightAnkle", "LH": "LeftHip", "LK": "LeftKnee", "LA": "LeftAnkle"}
def keys(s):
    out, f = [], 0
    for k in range(0, len(s), 4):
        f += ALPHA.index(s[k]); out.append((f, tuple(ALPHA.index(c) * 4 - 180 for c in s[k + 1:k + 4])))
    return out
def sample(ks, f):
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1:
            t = (f - f0) / max(1, f1 - f0); return tuple(a + (b - a) * t for a, b in zip(v0, v1))
    return ks[-1][1] if f > ks[-1][0] else ks[0][1]
src = open(sys.argv[1]).read()
for name, body in re.findall(r"(Pose_\w+) = \{(.*?)\},?\n", src):
    n = int(re.search(r"n = (\d+)", body).group(1))
    tr = {SHORT[k]: keys(v) for k, v in re.findall(r"(\w+) = \[=\[(.*?)\]=\]", body)}
    rows = [{j: sample(ks, f) for j, ks in tr.items()} for f in range(n)]
    fl = PC.check(rows)
    pose = rows[20]
    print(name, {k: len(v) for k, v in fl.items()} or "FLAGS: 0", " RS", pose.get("RightShoulder"), "RE", pose.get("RightElbow"), "LS", pose.get("LeftShoulder"), "LE", pose.get("LeftElbow"))
