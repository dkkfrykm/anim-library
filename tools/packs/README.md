# Animation packs → game clips

- `pack_convert.sh <name> <hkx_root | decoded_dir> [decoded]`: HKX tree → decoded json.gz (`library/tools` / skyrim_mco
  `export_decoded.py`, XPMSSE female HDT skeleton) → game clips (`pack_to_clips.py`) in `qa/packs/<name>/clips/`.
- `anims3d.py`: decoded clip → compact web clip (`conv()`), used by everything else.
- `pack_inventory.py`: one line per clip of every pack (live / game-format / decoded / hkx) → `qa/pack_inventory.tsv`, for a
  nearest-pose search.
