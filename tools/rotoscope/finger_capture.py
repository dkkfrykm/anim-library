"""Per-frame MANO hand capture of a reference video with WiLoR (wilor-mini; venv C:/Users/mytwo/rbsrc/venvs/handvenv). Motion only, no pixels kept.
Each detection is assigned to her L/R hand by distance to the NLF wrist (tools/roto/mocap_kp/<id>.npz joints2d 20/21), not by the detector's
handedness flag alone (crossed / occluded hands). -> tools/roto/hands_kp/<id>.npz:
  pose [n,2,15,3] MANO finger axis-angle (L, R; left already in left-hand convention), orient [n,2,3], kp2d [n,2,21,2], kp3d [n,2,21,3] (hand-local camera space, OpenPose order: wrist, thumb 1-4, index 5-8, middle 9-12, ring 13-16, pinky 17-20), conf [n,2] (0 = no hand)
Usage: handvenv python tools/roto/finger_capture.py <reiko_breed dir> <id> <video> [max_frames]"""
import sys, os, numpy as np, cv2, torch
D, ID, VID = sys.argv[1:4]; MAXF = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
from wilor_mini.pipelines.wilor_hand_pose3d_estimation_pipeline import WiLorHandPose3dEstimationPipeline
dev = torch.device(os.environ.get('HAND_DEVICE', 'cuda' if torch.cuda.is_available() else 'cpu'))
pipe = WiLorHandPose3dEstimationPipeline(device=dev, dtype=torch.float16 if dev.type == 'cuda' else torch.float32, verbose=False)
nlf = np.load(os.path.join(D, 'tools', 'roto', 'mocap_kp', ID + '.npz')); wr2 = nlf['joints2d'][:, [20, 21]]   # her L, R wrist (image px)
cap = cv2.VideoCapture(VID); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); n = min(n, MAXF, len(wr2))
pose = np.zeros((n, 2, 15, 3), np.float32); orient = np.zeros((n, 2, 3), np.float32); kp2 = np.zeros((n, 2, 21, 2), np.float32); kp3 = np.zeros((n, 2, 21, 3), np.float32); conf = np.zeros((n, 2), np.float32)
for f in range(n):
    ok, im = cap.read()
    if not ok: break
    out = pipe.predict(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    cands = []
    for o in out:
        p = o['wilor_preds']; k2 = np.asarray(p['pred_keypoints_2d'])[0]; bb = np.asarray(o['hand_bbox'], float)
        size = max(bb[2] - bb[0], bb[3] - bb[1], 1.0)
        for s in (0, 1):
            d = np.linalg.norm(k2[0] - wr2[f, s]) / size   # MANO joint 0 = wrist
            prior = 0 if int(o['is_right']) == s else .35   # detector handedness as a soft prior (video is not mirrored: her R = image left)
            cands.append((d + prior, s, o, k2, size))
    used = set(); taken = set()
    for c, s, o, k2, size in sorted(cands, key=lambda x: x[0]):
        if s in used or id(o) in taken or c > 1.5: continue
        used.add(s); taken.add(id(o)); p = o['wilor_preds']
        pose[f, s] = np.asarray(p['hand_pose']).reshape(15, 3); orient[f, s] = np.asarray(p['global_orient']).reshape(3); kp2[f, s] = k2; kp3[f, s] = np.asarray(p['pred_keypoints_3d'])[0]
        conf[f, s] = float(np.exp(-c))
    if f % 50 == 0: print(ID, f, '/', n, 'hands', int((conf[f] > 0).sum()), flush=True)
np.savez_compressed(os.path.join(D, 'tools', 'roto', 'hands_kp', ID + '.npz'), pose=pose, orient=orient, kp2d=kp2, kp3d=kp3, conf=conf, fps=nlf['fps'])
print('wrote', ID, n, 'frames; hand found L %.2f R %.2f' % tuple((conf > 0).mean(0)))
