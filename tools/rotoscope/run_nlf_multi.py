"""NLF SMPL-X per frame, ALL people (up to 3) per frame, for two-person clips. Motion only (params/joints), no pixels kept.
Usage: python run_nlf_multi.py <video> <out.npz> [stride]"""
import sys, time, numpy as np, torch, torchvision, cv2  # torchvision registers the nms op the detector needs
vid, out = sys.argv[1], sys.argv[2]; stride = int(sys.argv[3]) if len(sys.argv) > 3 else 1
M = r'C:/Users/mytwo/rbsrc/nlf/nlf_l_multi_0.3.2.patch6.torchscript'
model = torch.jit.load(M).cuda().eval()
c = cv2.VideoCapture(vid); fps = c.get(5) / stride; K = 3; R = {k: [] for k in ('pose', 'betas', 'trans', 'joints3d', 'joints2d', 'juncert', 'box')}; cnt = []
batch = []; i = 0; t0 = time.time(); wh = None; R_shape = {'pose': (165,), 'betas': (10,), 'trans': (3,), 'joints3d': (55, 3), 'joints2d': (55, 2), 'juncert': (55,), 'box': (5,)}
def flush(batch):
    b = torch.from_numpy(np.stack(batch)).permute(0, 3, 1, 2).cuda()
    with torch.inference_mode(), torch.device('cuda'): pr = model.detect_smpl_batched(b, model_name='smplx', default_fov_degrees=55, detector_threshold=.15, detector_nms_iou_threshold=.85, suppress_implausible_poses=False, detector_flip_aug=True, num_aug=2)
    for k in range(len(batch)):
        m = min(K, len(pr['pose'][k])) if 'boxes' in pr else 0; cnt.append(m)
        for key, src in (('pose', 'pose'), ('betas', 'betas'), ('trans', 'trans'), ('joints3d', 'joints3d'), ('joints2d', 'joints2d'), ('juncert', 'joint_uncertainties'), ('box', 'boxes')):
            if m == 0: R[key].append(np.full((K,) + R_shape.get(key, (1,)), np.nan)); continue
            a = pr[src][k].cpu().numpy()[:K]; R_shape[key] = a.shape[1:]; pad = np.full((K,) + a.shape[1:], np.nan); pad[:m] = a[:m]; R[key].append(pad)
while True:
    ok, f = c.read()
    if not ok: break
    if i % stride == 0:
        wh = (f.shape[1], f.shape[0]); batch.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
        if len(batch) == 4: flush(batch); batch = []
    i += 1
    if i % 400 == 0: print(i, round(time.time() - t0), 's', flush=True)
if batch: flush(batch)
np.savez_compressed(out, fps=fps, wh=np.array(wh), count=np.array(cnt), **{k: np.stack(v) for k, v in R.items()})
print('done', len(cnt), 'frames; people per frame', np.bincount(cnt).tolist(), round(time.time() - t0), 's')
