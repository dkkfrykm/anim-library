import os, re, collections, sys
for dp, dn, fn in os.walk(sys.argv[1]):
    for f in fn:
        b = open(os.path.join(dp, f), 'rb').read()
        tex = sorted(set(os.path.basename(t.decode('latin1').replace(chr(92), '/')).lower() for t in re.findall(rb'[A-Za-z0-9_ ./\x5c-]{3,}\.dds', b, re.I)))
        blk = collections.Counter(m.decode() for m in re.findall(rb'(NiParticleSystem|BSStripParticleSystem|BSEffectShaderProperty|NiPointLight)', b))
        print("%-34s %5dKB psys=%d strips=%d fxshaders=%d lights=%d tex=%s" % (f[:34], len(b) // 1024, blk['NiParticleSystem'], blk['BSStripParticleSystem'], blk['BSEffectShaderProperty'], blk['NiPointLight'], ", ".join(tex)[:160]))
