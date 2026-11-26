import gzip, json, glob, os, sys
os.chdir(r'C:\Users\mytwo\soulbound\skyrim\out\decoded')
B = chr(92)
pres = ['C:' + B + 'Users' + B + 'mytwo' + B + 'harrow' + B + 'anim' + B + 'newsets2' + B, 'C:' + B + 'Users' + B + 'mytwo' + B + 'harrow' + B + 'anim' + B + 'newsets' + B]
n = 0
for s in ['UNDERDOG Death Animations OAR', 'Take a Seat - OAR Animations', 'UNDERDOG Animations OAR']:
    for f in glob.glob(os.path.join(s, '*.json.gz')):
        d = json.load(gzip.open(f, 'rt'))
        src = d['source'].replace('/', B)
        for pre in pres:
            if src.startswith(pre):
                src = 'src3' + B + src[len(pre):]
        if src != d['source']:
            d['source'] = src; json.dump(d, gzip.open(f, 'wt')); n += 1
print('fixed', n)
print(json.load(gzip.open('UNDERDOG Death Animations OAR/340.json.gz', 'rt'))['source'][:80])
