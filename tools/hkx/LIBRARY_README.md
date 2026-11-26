# Skyrim SE HKX animation pipeline (reusable)

Decodes Skyrim SE (hk_2010.2.0-r1, 64-bit) HKX animations with a self-written pure-Python reader, retargets them to
Roblox R15 (or anything via BVH / decoded JSON), and catalogs them by strike metrics. Built for Soulbound, but
the tools are standalone. The user states the mod authors released these animations for free community use;
games must use generic set codes, never source character/franchise names.

## Layout
- `src/`, `src2/`, `src3/`: extracted HKX movesets (inputs, treated as data). `src3` = set 3 (13 free-use movesets, 3519 HKX,
  1734 unique after md5 de-dup, all decoded; see "Set 3" below). The skeleton is
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

## Production framework (phase 6, permanent)
Governing spec: `spec/DIRECTIVES.md` (HKX = foundation, modular reconstruction, per-power identity, uniqueness audit).

### 1. Source catalog (every HKX)
```
python -I tools/export_decoded.py src src2 --out out/decoded   # decode cache (933 unique clips)
python tools/catalog6.py                                        # -> out/catalog/catalog.json|tsv|html + gifs/
```
- `catalog.json` / `catalog.tsv`: per clip `set, clip, cond, cat, tags, frames, fps, dur, hits (Hitframe s), dom (fastest limb),
  travel/fwd/side (pelvis + animmotion, Skyrim units, actor faces +Y), peak60 / pelpeak60 (60 fps frame of peak limb /
  pelvis speed), rise, drop, turn (deg, hip line), lean, weapon, speed{lhand,rhand,lfoot,rfoot,weapon}, gif, decoded`.
- Categories: attack, locomotion, equip, dodge, cast, idle, jump_air, block_parry, hit_reaction, misc (filename/cond rules
  in `catalog6.CATS`). Tags: heavy, kick, hand, weapon, multihit, airborne, spin, travel, lean, dash.
- `catalog.html`: offline browser (type words to filter, e.g. `dodge unarmed`, `attack kick spin`), 12-frame stick GIF
  per clip (side view; orange = right limbs, green = left, blue line = weapon).

### 2. Unconvertible HKX: none left
The 45 earlier failures are all decoded now:
- 19 x `KeyError 'anims'`: the files use `hkaInterleavedUncompressedAnimation` (raw hkQsTransform per frame/track), not
  spline compression (Eryx/Kamen Rider `dodgeback/dodgeright/stepdodgeback`, Spiderman `mco_attack7`). Reader added:
  `hkx.read_interleaved_anim` (base hkaAnimation 56 B, `m_transforms` hkArray at +56, 48 B per transform).
- 26 x `FileNotFoundError`: Windows MAX_PATH (paths of 260-273 chars in the Phantom Blade SANGUINE set). Fixed with the
  extended-length prefix (`hkx.longpath`).
- Remaining non-animation: `FNIS_XPMSE_Behavior.hkx` is a behavior graph (no animation data), skipped by design.

### 3. Component library (modular building blocks)
```
python tools/components6.py      # -> out/catalog/components.json (~3000 segments)
```
Segment parts: `footwork` (pelvis + legs), `torso` (Waist/Neck relative to the hips), `arm_R/arm_L` and `leg_R/leg_L`
(strike segments per Hitframe). Each has an anchor frame (60 fps: hit, peak limb speed or peak pelvis speed) and tags
(`advance/retreat/sidestep_l/sidestep_r/planted`, `long`, `spin/pivot`, `airborne`, `crouch`, `dodge`, `dash`, source
category, `heavy/weapon/multihit/kick/hand`). Query from code: `components6.pick(part, need=[...], avoid=[...],
weapon=, sets=, exclude_sets=, used=)`.

### 4. Combiner + authoring layer (Blender)
```
blender --background --python tools/phase6.py -- --batch B1 [--render] [--out DIR]   # or --powers a,b
```
- `phase6.Clip6`: primary strike segment + footwork segment + torso segment from different HKX clips, each time-warped
  so its anchor lands on the slot impact frame; merged per body part (legs/pelvis from footwork, torso re-based on the
  hips, arms re-based on the new torso). Retarget profile = `sky2r15` corrections (XPMSSE -> R15, `rig.py`).
- Choreography layer: `tools/powers6.py` (DSL: guard, `T6` techniques with chamber/strike/extra keys, eases
  `snap/expo/slow/step/lin/io`, loops) and per-batch power files `tools/p6_b*.py`. Weights `ws` set how much of the
  HKX dynamics (legs / torso / pelvis) survives under the authored poses.
- Polish: smoothing outside strike windows, pelvis pull-to-feet, foot planting (2-bone IK), short IK-glitch repair,
  seamless 18-frame hit loops, combat stance loops (`Sky_<pid>_Idle`, 96 frames, from an HKX idle + per-power beat).
- QA gate per clip (posecheck); a failing clip is rebuilt automatically with different components (up to 5 tries).
- Outputs (`out/phase6/`): `Clips_SkyP_<pid>.lua`, `rows.json`, `markers.json`, `qa_report.json`,
  `provenance.json` (every clip: power, slot, technique, all contributing HKX segments with anchor frames).

### 5. Validation
```
python tools/precheck6.py B1                  # static pose check of authored keys + guard distances (no Blender)
python tools/simil.py <rows.json[,more]> <out.json> --slots M1_1,M1_2,M1_3,M1_4
python tools/simil_report.py <out.json> <pid,pid>     # pairs below the karate|boxer threshold, closest guards
```
- `posecheck.py`: elbow above shoulder, hands beside head, hand in head/torso, crossed knees, extreme lean, pops,
  planted-foot sliding (allowed only inside strike windows where the technique requires it).
- `simil.py`: DTW over R15 joint rotations + pelvis path per shared slot, mean per power pair; guard distance = frame-0
  pose distance. Gates: every pair >= karate|boxer distance (motion), guard distance >= 100.
- Review media: `chainvid.py --dir D --powers .. --clips ..` + `encode_vid.py` (3-view per power) and
  `gridvid.py D pids out.mp4 M1_1` (one tile per power, same slot, half speed).

### 6. Blender authoring template
`tools/make_template.py` builds `out/template/r15_authoring.blend`: the R15 rig, slot markers (w/i/r/n) for a chosen
slot, and NLA tracks for footwork / torso / strike components picked from the library, for hand refinement in the Graph
Editor before export.

## Set 3 (src3, added 2026-11-23) and V7 polish
### Library (reusable for any project)
- Decoded: `python -I tools/export_decoded.py src3 --out out/decoded` -> 1734 unique clips (3519 files, the rest are md5
  duplicates inside the OAR/condition folder trees), **0 failures, nothing unconvertible** (all SE 64-bit, spline or
  interleaved). Cache total: 2667 clips.
- Catalog: `python tools/catalog6.py` (system python with PIL) -> `out/catalog/catalog.json|tsv|html` + GIFs, 2667 clips.
  Components: `python tools/components6.py` -> 7698 segments. The 933 set-1/2 rows and 2994 old components are unchanged.
- BVH: `python -I tools/export_lib.py C:/Users/mytwo/animlib/skyrim_mco --decoded out/decoded <set folder> ...` (reads the
  decoded cache, no second spline decode; appends to the library catalog.tsv). Generic set codes (tools/pool.py SETCODE):
  Duelist (For Honor in Skyrim), SmoothMove (Smooth Moveset OAR), KatanaA (BFCO ER Katana), CastA (Goetia casting),
  CastB (Smooth Magic Casting), GreatswordB (YY Zweihander), SpellKnight (YY Mystic Knight), GreatswordL
  (LightGreatswords), BladeE (Elder Creed Blade), SwordE2 (BFCO Version), KatanaDual (Elden Rim x DS3 Dual Katana),
  SwordE (Elden Sword Definitive), Stinger (Elden Stingers).
- Category caveat: casting/weapon-replacer sets name their walk/run/sprint/turn cycles `mag_*`/`magcast_*`, so the
  catalog files many of them under `cast`. Set-3 queries filter them by name (`powers6.LOCO3`).
### Opt-in rule (keeps old builds bit-identical)
`components6.pick()` returns set-3 segments only when `sets=` names that set; `phase6.find_clip()` without a set name
prefers set 1/2. A power uses set 3 through `powers6.lib3(spec, sets, ...)` (per-part `prim_sets` / `torso_sets` /
`foot_sets`, idle `idle_sets`, optional `arms` blend). Applied in `p6_b5.py` (V7 dict: 9 casters) and `p6_b4.py` (V7 dict:
soulblade, sunblade, eclipseblacksun, eclipsemonarch, demonhunter, soulrequiem).
Finding: blending set-3 casting arms (`arms=0.2-0.3`) made the casters converge (M1 pairs fell under the bar), so caster
arms stay authored; set 3 supplies torso, planted weight shifts, strike timing anchors and idle sources.
### De-kink stage (phase6.Clip6.post / dekink)
Idle built first; every move eases in from its power's stance (Idle frame 0, with a stepping foot when the stance
foot must relocate); extra keys never land on frame 0; elbow hyperextension / wrist clamps outside strike windows;
iterative windowed smoothing of angular velocity/acceleration spikes outside the strike window (impact kept sharp);
hit-loop seam closed over 5 frames; Idle loop tail eased into frame 0. Audit: `python -I tools/kinks.py out/phase6`.
### Iteration loop
`sh tools/v7eval.sh pid,pid` = build into out/v7tmp, merge over out/phase6 (`merge_rows.py`), kinks + simil (M1 and all
slots). Promote by rebuilding the same powers into out/phase6 (deterministic). Pre-V7 outputs: `out/phase6/preV7/`.
### V7 results (2026-11-23)
kinks: 76 clips before the de-kink stage (31 loop seams, 42 pops, 39 accel spikes, 13 start snaps, 1 wrist flip,
1 elbow hyperextension) -> 0 / 335. QA 0 flags, precheck 0 issues. M1 distinctness: 0 pairs under karate|boxer (286),
min guard 116. All slots: only titanstrength|unitedmight (hero family, relaxed bar) at 297; chakra|psychic and
boxer|soulblade lifted above the bar (psychic M1_4 and Dash re-authored, chakra M1_1/M1_2 step in). Rbxmx:
`out/phase6/SkyClipsV7.rbxmx` (46 modules, 387 clips).
### V7 runtime + go-live (2026-11-23)
Installed V7 into Client.CharAnim (old set: ServerStorage.LoadPerf_Backups.SkyClips_preV7); decode check 445 clips
(387 Sky). Real-input play tests (videos `out/phase6/play/play_V7_*.mp4`): M1 click chains, M1->ability cancel,
stance->walk->jump, death/respawn reset, stand set (stando), Sky clips on the game's own CharAnim instance. Impact marker
vs server `CombatFx` hit arrival: +2..+16 ms (within 1 frame) except the first press of a session (+21 ms, client RTT
estimate not yet measured), so no clip retiming. Timing probe: set attribute `DebugMarkers` on CharAnim (runtime) and
watch the character's `SkyMarker` attribute. Go-live: `UseSkyrim = true` on Client.CharAnim (Edit, saved by the lead as v264).

## Set 4 (src4, added 2026-11-23): Vanargand / Leviathan (free-use)
- 14 movesets, 345 HKX -> 280 unique by md5 inside the set, 2 of them duplicates of set 1 (FNIS base) and dropped from the
  cache -> **278 new clips decoded, 0 failures** (`export_decoded.py src4`). Cache 2945 clips; catalog rebuilt (catalog6), components 8752.
- Fix: `hkx.longpath` now measures the absolute path (relative src4 paths under 240 chars were > 260 absolute and were
  silently skipped by the md5 pass). Backup `tools/hkx.py.bak_preSrc4`.
- Set codes (pool.SETCODE): SwordV, SwordVPow, SwordVLow, SwordVLoco, UnarmedV, ArcheryV, ArcherySneakV, DualSneakV, DualThrustV,
  GreatswordLev, GreatswordLevPow, GreatswordLevLow, GreatswordLevSneak, GreatswordLevMove. BVH in animlib/skyrim_mco/bvh/<code>/.
- Most src4 attacks carry no Hitframe annotation: use the peak hand speed (catalog `peak60`, or `th_src4.peak`).
