import json, re
cat = json.load(open('out/catalog/catalog.json'))
seen = {}
for r in cat:
    if r['set'] == 'UNDERDOG Animations OAR' and re.match(r'mt_(walk|run)forward(__\d+)?$', r['clip']):
        parts = r['source'].replace('/', chr(92)).split(chr(92))
        try:
            i = parts.index('Special Locomotion NPC'); k = (parts[i + 1], parts[i + 2])
        except ValueError:
            k = (parts[-3], parts[-2])
        seen.setdefault(k, []).append(r['clip'])
for k, v in sorted(seen.items()): print(k, v)
