# Skyrim MCO/BFCO animation library (reusable)

673 (sets 1-2) + 1734 (set 3, 2026-11-23) unique humanoid animations decoded from Skyrim SE HKX movesets (combat attacks, power attacks, dodges, jumps,
staggers, idles, locomotion). The user states the mod authors released them for free community use; keep original
set/character names out of shipped games (use the generic set codes below).

## Layout
- `bvh/<SetCode>/<clip>.bvh`: engine-neutral BVH, 27-bone humanoid (COM root with translation, pelvis, spine x3,
  neck, head, clavicles, arms, hands, middle-finger base, legs, toes, plus `Weapon` and `Shield` attach bones).
  Native fps (~30), Y-up, -Z/+Z per BVH convention, units = Skyrim units (1 unit ~ 1.428 cm; 128 units ~ body height).
  Import: Blender `File > Import > BVH` (scale 0.01-0.014), Unity/Godot via Blender, or any BVH retargeter.
- `catalog.tsv`: one row per clip. Columns: id, set code, pool_code, kind (attack/power/sprint/dodge/jump),
  duration, frames, fps, hits (Hitframe times, s), limbs (striking limb per hit: RH/LH/RF/LF/WPN), first_hit,
  score (strike speed + hit count - slowness), source set + file (offline reference only), bvh path.
- `roblox_r15/soulbound_style_modules/`: retargeted, retimed, stylised R15 clips in the Soulbound clip format
  (Luau tables decoded by Client.CharAnim; see `CharAnim_reference_local_copy.lua`). `Sky_markers.json` holds
  windup/impact/recover/swing frames (60 fps) for SFX/VFX keying.
- `roblox_r15/raw_batch/`: all 147 set-1 clips retargeted to R15 without retiming (full source length).
- `tools/`: the pipeline (pure Python + Blender 5.x), all scripts are self-written:
  - `hkx.py`: hk_2010 64-bit packfile reader + hkaSplineCompressedAnimation decompressor (THREECOMP 48/40/24).
  - `decode.py`, `fk.py`: per-frame local transforms and forward kinematics with the XPMSSE skeleton.
  - `sky2r15.py`: world-space rotation-delta retarget to R15 (Blender), contact sheets.
  - `phase2.py`: trim/retime to slot timing, stylise, foot-plant IK, multi-hit loops; `--mapping` for per-power sets.
  - `survey2.py`, `pool.py`, `select_powers.py`: cataloguing, de-dup, strike metrics, per-power selection.
  - `export_lib.py`: regenerates this library.

## Set codes (generic, safe for games)
Sword, Glaive (polearm-sword), Rapier, Dagger (reverse dual), Heavy (greatsword), Scythe, Shinobi, ShinMagic
(caster ninja), Generic, Unarmed, Skysa (unarmed combo), SwordB (stylish demon-hunter sword), SwordC (fast precise
sword), SwordD (one-hand swordplay), Gauntlet (gauntlet/kick combos), Agile (acrobatic flips/web-swing style),
Flight (flying-hero power punches/dives/slams), KickSet (hero rider kicks), BrawlB (heavy brawler), Mech (cyborg
unarmed), UnarmedB (martial unarmed), Feral (feral cat unarmed).

## Source data
HKX sources: `C:\Users\mytwo\soulbound\skyrim\src` (set 1) and `...\src2` (set 2); skeleton: XPMSSE HDT
`skeleton.hkx` (first 97 bones = vanilla, identical across HDT/TBBP variants).

## Set 3 (2026-11-23)
Codes: Duelist (multi-style duel weapons + unarmed, 702), SmoothMove (weapon locomotion/idles/equips, 503), CastA (spell
casting incl. ritual/ward/concentration, 137), CastB (spell casting, 87), SpellKnight (spell casting, 96), GreatswordB
(two-hand greatsword locomotion/idles, 46), GreatswordL (light greatsword attacks + locomotion, 51), KatanaA (katana, 23),
KatanaDual (dual katana, 17), BladeE (hidden-blade/blade attacks + draw/sheathe, 34), SwordE2 (16), SwordE (sword
locomotion, 14), Stinger (8). Exported from the decoded cache: `python -I tools/export_lib.py <LIB> --decoded
<soulbound/skyrim/out/decoded> <set folder> ...`. Casting sets file their run/walk cycles under kind `cast` (names
mag_run*/magcast_walk*): filter by name.
