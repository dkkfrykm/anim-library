# Rotoscope pipeline (video → mocap → game clip)

Turns a reference video of one dancer into a looping XPMSSE-skeleton clip (game format of `tools/packs/anims3d.py`:
`{n, fps, dur, q:{bone:[xyzw*1e4 per frame]}, t:{bone:[xyz*100]}, tc:{bone:[xyz]}}`), with captured fingers, QA metrics and the
song cut to the loop. Built for *Half an Eye* (paths in the scripts point at that project; adjust them).

Licences: NLF, SMPL/SMPL-X, MANO and WiLoR are non-commercial research licences. This repo has only the tools, no model weights or data.

## Stages (each cached; re-run only what changed)
1. **Body capture (SOURCE)**: `run_nlf_multi.py <video> <out_multi.npz>` (NLF v0.3.2 torchscript, SMPL-X per frame, all people)
   → `to_single.py` (track one person, `track.py`) → `mocap_kp/<id>.npz`.
2. **Hand capture (SOURCE)**: `finger_capture.py . <id> <video>` (WiLoR-mini, MANO per hand, assigned to the NLF wrists) → `hands_kp/<id>.npz`.
   Needs `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` with torch ≥ 2.6.
3. **Solve (BASE)**: `mocap_bake.py <project> <id>` (torch, CUDA). Staged by default (writes `mocap_clips/<id>.json` + raw solve
   `mocap_raw/<id>.pkl`, never the game file). Key design (see docstrings):
   - capture spike repair, uncertainty-scaled target smoothing, rotation-aware loop window, ground plane only when the feet spread;
   - **elbow/knee/wrist limits in the skeleton REST-local frame** (hinge = local X, measured on handmade clips), per-frame Viterbi
     upper-arm/thigh roll (hinge alignment), leg turn-out about the hip→ankle line;
   - corrections as a cyclic cubic B-spline + P-spline penalty (no optimiser jitter);
   - **arm terms (rot/dir/collision) via an arm-only FK view** (torso frozen) → the torso follows the video, arms adapt;
   - post-solve: limit projection, foot lock (tracked feet), calf twist → foot, forearm pronation (unwrapped, ±95°) → hand + twist bones.
   `mocap_refinish.py` re-runs the post-solve stage from the pkl in seconds.
4. **Fingers**: `finger_apply.py . <id>`: capture → per-joint curl/spread from 3D keypoints → anatomical `naturalize()` (ranges,
   DIP≈⅔PIP, neighbour coupling, no crossing, thumb wrap) → bind-hand subtraction → 30 finger tracks + bind finger offsets
   (`finger_tc_bind.json`). Needs `mano_flat_joints.npy` (MANO flat-hand joints; regenerate from WiLoR's MANO layer, not shipped)
   and `bind_hand_kp.json` (from `tools/qa_web/bind_hand_kp.js`).
5. **QA**: `qa_metrics.py . <id>` (PASS/FAIL vs the video: pelvis/spine/head error, pelvis range, penetration, limits, jitter, skate),
   `hinge_metric.py <clip|dance3d.js> <id>` (elbow/knee side-bend/twist like handmade clips), `qa_dance.sh <id>` (metrics + in-game
   video-vs-game sheets; `QA_CLIP=<final.json>` to check a Blender FINAL), `fidelity.py` (what each pre-stage removes).
6. **Music**: `dance_audio.py <project> [ids]` cuts each source's audio to the clip loop with the motion's seam crossfade (Opus, base64 JS);
   runtime player `dance_audio3d.js` (music is the clock).
- Batch: `stage_all.sh <ids…>` (one GPU job at a time), `new_dance.sh <ids…>` (fit + bake + hands + fingers).
- `roto_bake.py`, `roto3_*.py`: the earlier pair/foreplay rotoscope pipeline (period/phase fitting onto pose packs).
- Required project data not shipped: `dance_body_skin.json` (per-bone skin points of the character for collision).
