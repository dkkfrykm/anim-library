# Skyrim SE HKX animation pipeline (reusable)

Decodes Skyrim SE (hk_2010.2.0-r1, 64-bit) HKX animations with a self-written pure-Python reader, retargets them to
Roblox R15 (or anything via BVH / decoded JSON), and catalogs them by strike metrics. Built for Soulbound, but
the tools are standalone. The user states the mod authors released these animations for free community use;
games must use generic set codes, never source character/franchise names.

## Layout
- `src/`, `src2/`: extracted HKX movesets (inputs, treated as data). The skeleton is
  `src/XP32 Maximum Skeleton Special Extended/Skeleton Rig/HDT/.../skeleton.hkx`. Its first 97 bones are vanilla and
  identical in the HDT/HDT 4.51/TBBP variants.
- `tools/`: pipeline scripts. Run with `C:\Python315\python -I` (pure Python) or Blender `--background --python`.
  Env overrides: `SKYRIM_SKELETON=<skeleton.hkx>`, `R15_RIG_DIR=<dir with rig.py>` (default: tools/).
- `out/decoded/`: rig-neutral cache, one `.json.gz` per unique clip (930), plus `skeleton.json` (see schema below).
- `out/catalog files`: `survey.json`/`clip_catalog.tsv` (set 1), `survey2.json`/`clip_catalog2.tsv` (set 2),
  `pool.json` (406 de-duplicated striking clips with generic codes), `power_mapping.json/.txt` (per-power picks).
- `out/phase2/`, `out/phase3/`: built R15 clip modules (`Clips_Sky*.lua`, `Clips_SkyP_<power>.lua`), markers, and
  contact sheets.
- Library copy for other projects: `C:\Users\mytwo\animlib\skyrim_mco\` (BVH for every clip + catalog + tools).

## Decode (any project)
```
python -I tools/decode.py <clip.hkx> <out.json>              # one clip, with validation stats
python -I tools/export_decoded.py src src2 --out out/decoded  # whole trees, de-duplicated by md5
python -I tools/export_lib.py <libdir>                         # BVH library (27-bone humanoid, Y-up)
```
`tools/hkx.py` API: `hkx.load(path)` returns `{skeletons, anims, bindings}`. `hkx.sample_frames(anim)` gives a list
over frames of a list over tracks of `(t xyz, q xyzw, s xyz)`, the skeleton-local transforms. Map tracks to bones via
`bindings[0].t2b` (empty = identity). Supported: packfile sections, local/global/virtual fixups, hkaSkeleton,
hkaAnimationBinding, annotation tracks, hkaSplineCompressedAnimation (static/spline tracks, B-spline evaluation,
THREECOMP 48/40/24 and uncompressed quaternions, 8/16-bit vectors).

### Decoded cache schema (`out/decoded/<set>/<clip>.json.gz`)
`{source, fps, frameDuration, numFrames, duration, tracks[names], t2b[bone idx],
  frames[frame][track] = [tx,ty,tz, qx,qy,qz,qw, sx,sy,sz], annotations[[time_s, text]]}`.
Skyrim model space: X right, Y forward, Z up; 1 unit ~ 1.428 cm (128 units ~ body height). Use `tools/fk.py` for
world transforms (bones not animated keep the bind pose from `skeleton.json`).

## Retarget to R15 (Blender 5.x)
```
blender --background --python tools/sky2r15.py -- --module Name --clip <a.hkx>=ClipName [--render all] --out <dir>
blender --background --python tools/phase2.py -- --mapping out/power_mapping.json --render --out <dir>
```
- `sky2r15.py`: world-space rotation-delta retarget, `P = S(t) S(bind)^-1 Corr`. Corr aligns the R15 rest pose to the
  Skyrim bind pose by bone direction plus facing (blade = Weapon bone +Y for hands). Outputs the Soulbound Luau clip
  format: 60 fps, 1-char frame deltas, 4° Euler steps, `p` root offset, markers `n/w/i/r/sw`.
- `phase2.py`: trims and retimes onto slot timing (anticipation, swing, 3-frame impact hold, follow, return to
  neutral). Then stylises (arm and twist amplification, impact squash), runs the torso chain-vector solve and lean
  limiter, plants feet with 2-bone IK, and builds seamless 18-frame multi-hit loops.
- Impact = peak strike-point speed near the HKX `Hitframe` (Hitframe fires 1-3 frames before visible contact).
  Root motion lives in `animmotion x y z` annotations, not the bones.

## Catalog columns
- `clip_catalog.tsv` (set 1): clip, source file, frames, fps, duration, swing_s, hitframe_s, refined impact frame
  (60 fps), windup and recover frames, animmotion (studs), other events.
- `clip_catalog2.tsv` / `pool.json` / `animlib catalog.tsv`: moveset, cond folder, file, duration, frames, fps, hits
  (Hitframe s), limbs (striking limb per hit: RH/LH/RF/LF/WPN), first_hit (s), snap (swing to hit), peak (strike
  speed), air / drop (pelvis rise/fall, units), lean (max torso lean, deg), score, motion.
  - Score = 0.6*peak + 0.5*min(hits,5) - 1.2*first_hit - 0.05*max(0, lean-55).
