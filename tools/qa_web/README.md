# In-game QA harnesses (Playwright, headless Chromium)

- `dancefix_qa.js <id> <outdir> <label> "times=…,cams=full;upper;handL;handR;…,outfit=…[,nolife,nophys,fing=…,yaw=…]"`:
  deterministic virtual-clock shots + per-frame timeline; `CLIPJSON=<clip.json>` injects a staged clip without touching game files.
- `dance_preview.js <id> <outdir>` (webm), `dance_music_test.js <id>` (music start/sync/stop), `finger_probe.js <id> <t>`
  (live finger joints), `bind_hand_kp.js` (bind hand keypoints from the game mesh, for `finger_apply.py`).
- `hand_pen.js <clipId> <times|all>`: numeric hand-vs-own-body penetration gate (signed skin distance of palm/finger points, FAIL < -0.3 cm);
  game-agnostic via an adapter module (`QA_ADAPTER`: url, setup, duration, setTime; page exposes `window.__qaActor()`).
