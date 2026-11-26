# Merge a partial phase6 build (--out DIR) over the full set: writes DIR/merged/{rows,markers}.json for kinks/simil.
# Run: python -I merge_rows.py <full_dir> <partial_dir>
import sys, os, json
full, part = sys.argv[1], sys.argv[2]
os.makedirs(os.path.join(part, "merged"), exist_ok=True)
for fn in ("rows.json", "markers.json"):
    d = json.load(open(os.path.join(full, fn)))
    d.update(json.load(open(os.path.join(part, fn))))
    json.dump(d, open(os.path.join(part, "merged", fn), "w"))
print("merged", len(d))
