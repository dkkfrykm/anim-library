// node tools/finger_probe.js <id> <t> -> prints her live finger joint world positions (hand + F f0..f2 heads) at clip time t as JSON
const { chromium } = require('C:/Users/mytwo/node_modules/playwright');
(async () => { const [id, t] = process.argv.slice(2); const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage(); await p.goto('file:///C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed/reiko_breed_3d.html'); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 });
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); for (let i = 0; i < 14; i++) RBG.next(); }); await p.waitForTimeout(1500);
  await p.evaluate(id => { RBV.scene(Object.assign({}, RBV._V, { room: 'living', slot: 'afternoon', her: true, outfit: 'nude' })); RB_DANCE.play(id); }, id); await p.waitForTimeout(3000);
  const r = await p.evaluate(t => { const F = RB3.her(), a = F.cur; a.paused = true; a.time = +t; F.mixer.update(0); F.root.updateMatrixWorld(true); const o = {};
    for (const s of ['L', 'R']) { const P = n => { const b = F.bones[n]; return b ? b.getWorldPosition(new THREE.Vector3()).toArray() : null; }; o[s] = { hand: P('NPC ' + s + ' Hand [' + s + 'Hnd]') };
      for (let f = 0; f < 5; f++) o[s]['f' + f] = [0, 1, 2].map(j => P('NPC ' + s + ' Finger' + f + j + ' [' + s + 'F' + f + j + ']'));
      o[s].q = [0, 1, 2].map(j => F.bones['NPC ' + s + ' Finger1' + j + ' [' + s + 'F1' + j + ']'].quaternion.toArray().map(x => +x.toFixed(4))); }
    return o; }, t);
  console.log(JSON.stringify(r)); await b.close(); })();
