# Animation library + HKX tools

A reusable animation library for any project (Roblox, Blender, HTML, Godot), built from user-supplied free-use Skyrim animation mods.

## Layout
- `library/`: the decoded library (from `animlib/skyrim_mco`). Read `library/README.md` and `library/PIPELINE_README.md` first.
  - `bvh/<SetCode>/*.bvh`: 673 clips, 27-bone humanoid, Y-up.
  - `roblox_r15/`: R15 Luau clip modules.
  - `catalog.tsv`: per clip: kind, hits, limb, first-hit time, quality.
  - `tools/`: export, retarget and stylise scripts.
- `tools/hkx/`: the pure-Python HKX decoder (`hkx.py`: hk_2010 64-bit, spline-compressed, skeleton, annotations), plus:
  - `sky2r15.py` (Blender retarget to R15)
  - `phase2.py` (retime, stylise, foot IK)
  - `guardfit.py` (pose QA gate)
  - `sheet.py` and catalog tools

  `LIBRARY_README.md` is the original library notes.
- `tools/harrow/`: Twelfth Hearth clip tools: combo builder, batch, check, kinks, standpose, rbxmx.
- `skeleton/xpmsse/`: the XPMSSE skeleton. Use the HDT variant; its first 97 bones are the animation tracks.
- `skeleton/skeleton.json`: the decoded skeleton.
- `catalogs/`: `clip_catalog.tsv` and `clip_catalog2.tsv`: duration, hit times, striking limb and root motion per source clip.
- `spec/DIRECTIVES.md`: the governing animation spec. Read it before any animation work.

## Not in the repo (size)
- Raw HKX sources `src` to `src5`: several GB. Re-extract them from the original mod archives.
- The decoded cache `out/decoded`: 4.3 GB. Regenerate it with `tools/hkx`.

Locally they live in `C:\Users\mytwo\soulbound\skyrim\`.
- `src5` holds the creature sets: draugr, troll, and dragon/wolf/bear/sabrecat. Creature rigs need their own skeleton to decode bone names.

## Rules
- Use clips as a BASE and modify them per move. Never ship them 1:1.
- Shipped games use generic set names, never source or franchise names.
- Gate every clip with `guardfit.py` (0 flags) before shipping.

## Pull anywhere
```
git clone https://github.com/dkkfrykm/anim-library.git
git -C anim-library pull
```
- `tools/rotoscope/`: video → mocap → game clip pipeline (NLF body + WiLoR hands → constrained solve on XPMSSE → fingers → QA → music). See its README.
- `tools/blender_anim/`: non-destructive Blender stage (BASE / CORR / POLISH → FINAL, QA-gated promote).
- `tools/packs/`: HKX packs → game-format clips, and a one-line-per-clip pack inventory.
- `tools/qa_web/`: Playwright in-game QA harnesses (deterministic shots, staged-clip injection, music sync).

