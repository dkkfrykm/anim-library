// node hand_pen.js <clipId> <times a;b;c|all>  -- numeric hand-vs-own-body penetration gate for a skinned three.js character (XPMSSE bone names).
// Metric: frames are frozen at the given clip times (24 loop phases with "all"). For the palm, every finger joint, each segment midpoint and an
// extrapolated fingertip: nearest skinned body vertex (excluding the hand's own arm chain), signed distance along the SKINNED vertex normal, minus a
// finger skin radius (0.75 cm). < 0 = finger surface inside the skin. Gate: FAIL if the worst value over all times and both hands is < -0.3 cm.
// The page is driven through an adapter module (env QA_ADAPTER, default ./qa_adapter.js) exporting
//   url: page URL;  async setup(page, clipId): load the scene and start playing the clip;  async duration(page): clip length in s;
//   async setTime(page, t): pose the character at t and freeze it.  The page must define window.__qaActor() -> {root, meshes, bones{name: Bone}}.
// env: BODY_MESH (skinned body mesh name, default "Body"), PLAYWRIGHT (module path, default "playwright"), CLIPJSON passed through to the adapter.
const path = require('path'); const { chromium } = require(process.env.PLAYWRIGHT || 'playwright');
const A = require(path.resolve(process.env.QA_ADAPTER || './qa_adapter.js')); const BODY = process.env.BODY_MESH || 'Body';
(async () => { const [id, timesArg = 'all'] = process.argv.slice(2);
  const b = await chromium.launch({ headless: true, args: ['--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] }); const p = await b.newPage({ viewport: { width: 960, height: 540 } });
  await p.goto(A.url, { timeout: 240000 }); await A.setup(p, id);
  const dur = await A.duration(p); const times = timesArg == 'all' ? Array.from({ length: 24 }, (_, i) => +(i * dur / 24).toFixed(3)) : timesArg.split(';').map(Number);
  let worst = 0;
  for (const t of times) { await A.setTime(p, t);
    const r = await p.evaluate(BODY => { const T = THREE, F = window.__qaActor(), body = F.meshes.find(m => m.name == BODY); F.root.updateMatrixWorld(true); body.skeleton.update();
      const g = body.geometry, pos = g.attributes.position, nor = g.attributes.normal, si = g.attributes.skinIndex, sw = g.attributes.skinWeight, bones = body.skeleton.bones, n = pos.count;
      const W = new Float32Array(n * 3), N = new Float32Array(n * 3), dom = new Int16Array(n), v = new T.Vector3(), v2 = new T.Vector3();
      for (let i = 0; i < n; i++) { body.getVertexPosition(i, v); v.applyMatrix4(body.matrixWorld); W[i * 3] = v.x; W[i * 3 + 1] = v.y; W[i * 3 + 2] = v.z; let bw = -1, bi = 0; for (let k = 0; k < 4; k++) { const w = sw.getComponent(i, k); if (w > bw) { bw = w; bi = si.getComponent(i, k); } } dom[i] = bi; }
      const nrm = i => { /* skinned normal: skin (rest pos + 1 mm along the rest normal) minus skinned pos */ const save = [pos.getX(i), pos.getY(i), pos.getZ(i)]; pos.setXYZ(i, save[0] + nor.getX(i) * .001, save[1] + nor.getY(i) * .001, save[2] + nor.getZ(i) * .001); body.getVertexPosition(i, v2); pos.setXYZ(i, save[0], save[1], save[2]); v2.applyMatrix4(body.matrixWorld); return v2.sub(new T.Vector3(W[i * 3], W[i * 3 + 1], W[i * 3 + 2])).normalize(); };
      const bp = nm => { const x = F.bones[nm]; return x && x.getWorldPosition(new T.Vector3()); }, FR = .0075 * 0.8517 / .8517; /* finger skin radius ~0.75 cm */
      const out = {}; for (const s of ['L', 'R']) { const own = new RegExp('NPC[ _]' + s + '[ _](Hand|Finger|Forearm|ForearmTwist|Lar|Hnd)'); const pts = []; const hand = bp('NPC ' + s + ' Hand [' + s + 'Hnd]');
        for (let f = 0; f < 5; f++) { const j = [0, 1, 2].map(k => bp('NPC ' + s + ' Finger' + f + k + ' [' + s + 'F' + f + k + ']')).filter(Boolean); j.forEach((q, k) => { pts.push([q, 'F' + f + k]); if (k) pts.push([q.clone().lerp(j[k - 1], .5), 'F' + f + (k - 1) + '-' + k]); });
          if (j.length == 3) pts.push([j[2].clone().addScaledVector(j[2].clone().sub(j[1]), .8), 'F' + f + 'tip']); if (f && j[0]) pts.push([hand.clone().lerp(j[0], .5), 'palm' + f]); }
        let best = null; for (const [q, tag] of pts) { let bd = 1e9, bi = -1; for (let i = 0; i < n; i++) { if (own.test(bones[dom[i]].name)) continue; const dx = W[i * 3] - q.x, dy = W[i * 3 + 1] - q.y, dz = W[i * 3 + 2] - q.z, d2 = dx * dx + dy * dy + dz * dz; if (d2 < bd) { bd = d2; bi = i; } }
          if (bi < 0 || bd > .04 * .04) continue; const nn = nrm(bi), sd = q.clone().sub(new T.Vector3(W[bi * 3], W[bi * 3 + 1], W[bi * 3 + 2])).dot(nn) - FR; if (!best || sd < best.sd) best = { sd, tag, region: bones[dom[bi]].name }; }
        out[s] = best ? { cm: +(best.sd * 100).toFixed(2), at: best.tag, vs: best.region } : null; } return out; }, BODY);
    for (const s of ['L', 'R']) if (r[s]) worst = Math.min(worst, r[s].cm); console.log('t', t, JSON.stringify(r)); }
  console.log((worst < -.3 ? 'FAIL' : 'PASS') + ' hand penetration: worst ' + worst.toFixed(2) + ' cm (gate -0.3)'); await b.close(); })().catch(e => { console.log('FAIL', e.message); process.exit(1); });
