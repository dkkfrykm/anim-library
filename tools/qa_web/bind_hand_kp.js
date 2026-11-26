// node tools/bind_hand_kp.js -> tools/roto/bind_hand_kp.json: her rest (bind) hand as 21 OpenPose keypoints per side (wrist, finger bone heads,
// fingertips = farthest skin vertex of each distal bone along it), so finger_apply.py can subtract the bind hand's own curl/spread.
const { chromium } = require('C:/Users/mytwo/node_modules/playwright'); const fs = require('fs');
(async () => { const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file:///C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed/reiko_breed_3d.html'); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 });
  const out = await p.evaluate(() => { const T = THREE, F = RB3.actor('reiko'); const hm = F.meshes.find(m => m.isSkinnedMesh && m.name == 'Hands') || F.meshes.find(m => m.isSkinnedMesh);
    const sk = hm.skeleton, bindW = b => { const i = sk.bones.indexOf(b); return i < 0 ? null : new T.Matrix4().copy(sk.boneInverses[i]).invert(); };
    const g = hm.geometry, pos = g.attributes.position, si = g.attributes.skinIndex, sw = g.attributes.skinWeight; const R = { mesh: hm.name };
    for (const s of ['L', 'R']) { const B = n => F.bones[n]; const hand = B('NPC ' + s + ' Hand [' + s + 'Hnd]'); const kp = new Array(21);
      const P = b => new T.Vector3().setFromMatrixPosition(bindW(b)); kp[0] = P(hand).toArray();
      const order = [0, 1, 2, 3, 4]; /* thumb..pinky -> OpenPose chains 1-4, 5-8, 9-12, 13-16, 17-20 */
      for (const f of order) { const bs = [0, 1, 2].map(j => B('NPC ' + s + ' Finger' + f + j + ' [' + s + 'F' + f + j + ']')); const base = 1 + f * 4;
        bs.forEach((bb, j) => { kp[base + j] = P(bb).toArray(); });
        const p1 = P(bs[1]), p2 = P(bs[2]), d = p2.clone().sub(p1).normalize(), bi = sk.bones.indexOf(bs[2]); let best = null, bd = -1e9; const v = new T.Vector3();
        for (let i = 0; i < pos.count; i++) { let dom = -1, wm = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > wm) { wm = w; dom = si.getComponent(i, k); } } if (dom !== bi) continue;
          v.fromBufferAttribute(pos, i).applyMatrix4(hm.bindMatrix); const a = v.clone().sub(p2).dot(d); if (a > bd) { bd = a; best = v.clone(); } }
        /* tip on the bone's line through the farthest vertex's projection (the vertex itself sits on the nail/pad surface) */
        kp[base + 3] = (best ? p2.clone().addScaledVector(best.clone().sub(p2).normalize(), best.distanceTo(p2) * 0.9) : p2.clone().addScaledVector(d, 2)).toArray(); }
      R[s] = kp; }
    return R; });
  fs.writeFileSync('tools/roto/bind_hand_kp.json', JSON.stringify(out)); console.log('mesh', out.mesh, 'errs', errs.length); await b.close(); })();
