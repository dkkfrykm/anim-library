// game half of the roto3 side-by-side strips: node tools/roto/roto3_strips.js <fileUrl> <outdir> <json spec>
// spec: {clip:'prone'|'sway'|'grope', times:[clip seconds...], cam:{yaw,pitch,dist,bone}}; the clip is paused at each time (her action; for grope
// the rotoscoped hand layer reads the same clip time), the camera is held by a render wrapper, one PNG per time -> <outdir>/<clip>_<k>.png
const { chromium } = require('C:/Users/mytwo/node_modules/playwright');
(async () => {
  const [url, out, specS] = process.argv.slice(2), sp = JSON.parse(specS); require('fs').mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 900, height: 900 } }); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(url, { timeout: 180000 }); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 });
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); for (let i = 0; i < 14; i++) RBG.next(); document.getElementById('choices').innerHTML = ''; }); await p.waitForTimeout(2500);
  if (sp.clip == 'grope') { await p.evaluate(() => { document.getElementById('dlg').hidden = true; RBG.startH({ pos: 'fp_grope', outfit: 'nude' }); }); await p.waitForFunction(() => window.RB_ROTO3X && RB_ROTO3X.metrics, null, { timeout: 60000 });
    await p.evaluate(() => document.querySelectorAll('button').forEach(b => { if (/^Him: silhouette/.test(b.textContent)) b.click(); })); }
  else await p.evaluate(t => { RBG.S.room = 'herroom'; RBG.ui(); RBV.direct({ pose: t }); }, sp.clip == 'prone' ? 'lie_phone' : 'idle_sway');
  await p.waitForTimeout(4000);
  await p.evaluate(c => { document.querySelectorAll('#dlg,#choices,.panel,#hud,#hbar,#hpanel,.hpanel').forEach(e => { e.style.visibility = 'hidden'; }); document.querySelectorAll('button,select,label').forEach(e => { e.style.visibility = 'hidden'; });
    window.__qaCam = c; const r0 = RB3.render; RB3.render = function (dt) { const q = window.__qaCam; if (q) { const F = RB3.her(), t = RB3.bonePos(F, q.bone); if (t) { RB3.cam.tTarget = t; RB3.cam.target.copy(t); } RB3.cam.yaw = q.yaw; RB3.cam.pitch = q.pitch; RB3.cam.dist = q.dist; } return r0.apply(this, arguments); }; }, sp.cam);
  for (let k = 0; k < sp.times.length; k++) { await p.evaluate(t => { const a = RB3.her().cur; a.paused = true; a.time = t; }, sp.times[k]); await p.waitForTimeout(700); await p.screenshot({ path: `${out}/${sp.clip}_${k}.png` }); }
  console.log('errors', errs.length, errs.slice(0, 3).join(' | ')); await b.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
