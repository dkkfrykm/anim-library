// roto3 in-game QA: node tools/roto/roto3_qa.js <fileUrl> <outdir> [grope|prone|sway|all] [girl]
// grope: H scene fp_grope (nude), contact metrics per frame (RB_ROTO3X.metrics), his capsule penetration (RBCONTACT.debugTop), shots front/side/close at phases
// prone/sway: daily view pose by tag (lie_phone / idle_sway), shots at phases + RB_PHYS butt node output (drive check)
const { chromium } = require('C:/Users/mytwo/node_modules/playwright');
(async () => {
  const [url, out, what0, girl] = process.argv.slice(2), what = what0 || 'all'; require('fs').mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); const errs = [];
  p.on('pageerror', e => errs.push('pageerror: ' + (e.stack || e.message).slice(0, 500))); p.on('console', m => { if (m.type() == 'error') errs.push(m.text().slice(0, 300)); if (/RB_ROTO3X/.test(m.text())) errs.push(m.type() + ': ' + m.text().slice(0, 300)); });
  await p.goto(url, { timeout: 180000 }); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 });
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); for (let i = 0; i < 14; i++) RBG.next(); document.getElementById('choices').innerHTML = ''; }); await p.waitForTimeout(2500);
  if (girl) { await p.evaluate(g => window.RB_GIRLS && RB_GIRLS.set && RB_GIRLS.set(g), girl); await p.waitForTimeout(6000); }
  const hide = () => p.evaluate(() => { document.querySelectorAll('#dlg,#choices,.panel,#hud,#hbar').forEach(e => { e.style.visibility = 'hidden'; }); });
  if (what == 'grope' || what == 'all') {
    await p.evaluate(() => { if (RBH.H) RBH.end(); document.getElementById('dlg').hidden = true; RBG.startH({ pos: 'fp_grope', outfit: 'nude' }); RB_ROTO3X.qa = true; });
    await p.waitForFunction(() => (window.RB_OST_LOADED || {}).fp_grope && window.RB_ROTO3X && RB_ROTO3X.metrics, null, { timeout: 60000 }).catch(() => errs.push('grope never active'));
    await p.waitForTimeout(3000); const M = [];
    for (let k = 0; k < 40; k++) { M.push(await p.evaluate(() => { const U = RB3.actor('player'), F = RB3.her(); return { m: RB_ROTO3X.metrics, mode: RB3.maleMode, top: window.RBCONTACT && RBCONTACT.debugTop ? RBCONTACT.debugTop(U, F, 3).map(([k, v]) => [k.replace(/NPC_|_[A-Z][A-Za-z0-9]{2,4}/g, ''), v.max]) : null }; })); await p.waitForTimeout(160); }
    const S = ['L', 'R'], agg = {}; S.forEach(s => { const r = M.map(x => x.m && x.m.side[s]).filter(Boolean); if (!r.length) return; const col = k => r.map(x => x[k]).filter(x => x != null);
      agg[s] = { n: r.length, palmMm: [Math.min(...col('palmMm')), Math.max(...col('palmMm'))], pressMm: [Math.min(...col('pressMm')), Math.max(...col('pressMm'))], palmToPatchMm_max: Math.max(...col('palmToPatchMm')), palmFacing_min: Math.min(...col('palmFacing')),
        tipJointMm_min: Math.min(...r.flatMap(x => x.tipJointMm)), tipJointMm_max: Math.max(...r.flatMap(x => x.tipJointMm)), extCm_max: Math.max(...col('extCm')), hwCm: r[0].hwCm, hhCm: r[0].hhCm }; });
    const g = k => M.map(x => x.m && x.m[k]).filter(x => x != null); agg.armPenMm = [Math.min(...g('armPenMm')), Math.max(...g('armPenMm'))]; agg.handPenMm = [Math.min(...g('handPenMm')), Math.max(...g('handPenMm'))]; agg.torsoPenMm = [Math.min(...g('torsoPenMm')), Math.max(...g('torsoPenMm'))]; agg.backCm = g('backCm').slice(-1)[0]; agg.mode = M[M.length - 1].mode;
    console.log('grope metrics', JSON.stringify(agg)); console.log('his capsules (top penetrations, per sample)', JSON.stringify(M.filter((x, i) => i % 4 == 0).map(x => x.top)));
    require('fs').writeFileSync(out + '/grope_metrics.json', JSON.stringify(M));
    await hide(); await p.evaluate(() => { document.querySelectorAll('button').forEach(b => { if (/^Him: silhouette/.test(b.textContent)) b.click(); }); const r0 = RB3.render; RB3.render = function (dt) { const c = window.__qaCam; if (c) { const F = RB3.her(), t = RB3.bonePos(F, c.bone); if (t) { RB3.cam.tTarget = t; RB3.cam.target.copy(t); } RB3.cam.yaw = c.yaw + (F.root.rotation.y || 0); RB3.cam.pitch = c.pitch; RB3.cam.dist = c.dist; } return r0.apply(this, arguments); }; });
    for (const [nm, yaw, pitch, zoom] of [['front', 0, .12, 2.2], ['side', 1.35, .1, 2.0], ['close', .35, .05, 3.6], ['back34', 2.4, .2, 1.8], ['top', 0.01, 1.4, 1.4], ['rear', 3.14, .15, 1.6]]) {
      for (const ph of [0, 1]) { await p.evaluate(([y, pi, z]) => { window.__qaCam = { yaw: y, pitch: pi, dist: 2.2 / z, bone: 'NPC Spine2 [Spn2]' }; }, [yaw, pitch, zoom]); await p.waitForTimeout(ph ? 330 : 900); await p.screenshot({ path: `${out}/grope_${nm}_${ph}.png` }); } }
    await p.evaluate(() => { window.__qaCam = null; if (RBH.H) RBH.end(); });
  }
  for (const [w, tag] of [['prone', 'lie_phone'], ['sway', 'idle_sway']]) { if (what != w && what != 'all') continue;
    await p.evaluate(t => { const r = RBG.herRoom ? RBG.herRoom() : 'herroom'; RBG.S.room = r; RBG.ui(); RBV.direct({ pose: t }); }, tag); await p.waitForTimeout(4000); await hide();
    const info = await p.evaluate(() => ({ id: RBV3._V.id, tune: window.RB_PHYS && RB_PHYS.tuneKey, phone: !!(RB_ROTO3X.phone && RB_ROTO3X.phone.visible) })); console.log(w, JSON.stringify(info));
    if (w == 'prone') { const smp = []; for (let k = 0; k < 90; k++) { smp.push(await p.evaluate(() => { const N = (RB_PHYS.nodes || []).filter(n => n.part == 'Butt'); return N.map(n => [n.side, +(n.out ? n.out.x : 0).toFixed(3), +(n.out ? n.out.y : 0).toFixed(3), +(n.out ? n.out.z : 0).toFixed(3), n.driveGain || 0, +RB_PHYS.time.toFixed(3)]); })); await p.waitForTimeout(33); }
      require('fs').writeFileSync(out + '/prone_butt.json', JSON.stringify(smp)); }
    for (let k = 0; k < 4; k++) { await p.waitForTimeout(1100); await p.screenshot({ path: `${out}/${w}_${k}.png` }); }
  }
  console.log('errors', errs.length); errs.slice(0, 12).forEach(e => console.log(e)); await b.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
