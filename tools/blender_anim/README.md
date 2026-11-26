# Blender non-destructive animation stage (rbanim)

Run inside Blender (live via MCP `exec(open('rbanim.py').read())`, or headless `blender -b <blend> --python ...`).
Per clip: **BASE** (imported solve, locked NLA, REPLACE) → **CORR** and **POLISH** (COMBINE layers, edit only the affected bones/frames)
→ **FINAL** (evaluated stack exported back to the game format). Exact clip↔action mapping (rig = the game's glb; round trip 0.008°).
Dependency-aware cache: a layer edit only invalidates FINAL. `promote.py` ships a FINAL only with a QA verdict (`pass`, `user_ok`,
matching hash). `rbcontact.py`: hand-contact IK / pose transplant into CORR; `rblook.py`: the game's body-slider preset on shape keys.
Paths point at the *Half an Eye* project; adjust `ROOT`/`LIB`.
