// node tools/roto/roto_h_test.js <fileUrl> <outdir> : rotoscoped clips through the real game paths (H scene catalog positions + daily-view RB_ROTO.play)
const { chromium } = require('C:/Users/mytwo/node_modules/playwright');
(async () => {
  const [url, out] = process.argv.slice(2); require('fs').mkdirSync(out, { recursive: true });
  const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); const errs = [];
  p.on('console', m => { if (m.type() == 'error' || (m.type() == 'warning' && /roto|RB_ROTO|clip missing/i.test(m.text()))) errs.push(m.type() + ': ' + m.text().slice(0, 300)); }); p.on('pageerror', e => errs.push('pageerror: ' + (e.stack || e.message).slice(0, 500)));
  await p.goto(url, { timeout: 240000 }); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 240000 }); await p.evaluate(() => window.RB3_READY);
  console.log('registry', JSON.stringify(await p.evaluate(() => ({ roto: Object.keys(RB_ANIM3D.roto.clips).length, cat: RB_CAT3D.scenes.filter(s => s.pack == 'roto').map(s => s.id + ':' + s.kind), packs: RB_CAT3D.packs.roto, posesAlias: !!RB_ANIM3D.poses.clips.roto_twerk }))));
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); }); await p.waitForTimeout(2500);
  for (const pos of ['roto_doggy', 'roto_press', 'roto_oral']) {
    await p.evaluate(pos => { if (RBH.H) RBH.end(); document.getElementById('dlg').hidden = true; RBG.startH({ pos, outfit: 'nude' }); }, pos); await p.waitForTimeout(2500);
    await p.evaluate(() => { RBH.toggleInsert(); }); const rows = [];
    for (const sp of [.3, .55, .8]) { await p.evaluate(sp => { RBH.H.speed = sp; }, sp); await p.waitForTimeout(1800);
      const smp = await p.evaluate(() => new Promise(r => { const S = []; let n = 0; const f = () => { S.push({ eng: PEN3.st.engaged, d: PEN3.st.depth, ph: RBH.H.ph }); if (++n < 90) requestAnimationFrame(f); else r(S); }; requestAnimationFrame(f); }));
      const ds = smp.map(s => s.d), eng = smp.filter(s => s.eng).length / smp.length; let wraps = 0; for (let i = 1; i < smp.length; i++) if (smp[i].ph < smp[i - 1].ph - .5) wraps++;
      const info = await p.evaluate(() => { const F = RB3.actor('reiko'); return { stage: RBH.H.stage, clip: F.cur && F.cur.getClip().name, rate: F.cur && +F.cur.timeScale.toFixed(2) }; });
      rows.push({ speed: sp, ...info, engaged: +eng.toFixed(2), depth: [+Math.min(...ds).toFixed(2), +Math.max(...ds).toFixed(2)], cyclesIn90f: wraps }); }
    await p.screenshot({ path: out + '/h_' + pos + '.png' }); console.log(pos, JSON.stringify(rows));
  }
  await p.evaluate(() => { RBH.end(); }); await p.waitForTimeout(1000);
  for (const id of ['roto_twerk', 'roto_idle_sway']) {
    await p.evaluate(id => { RBV3._V.her = true; RBV3._V.present = true; RB_ROTO.play('reiko', id); }, id); await p.waitForTimeout(2500);
    console.log(id, JSON.stringify(await p.evaluate(() => { const F = RB3.actor('reiko'); return { clip: F.cur && F.cur.getClip().name, t: +F.cur.time.toFixed(2), tag: RBV3._V.tag, id: RBV3._V.id }; })));
    await p.screenshot({ path: out + '/daily_' + id + '.png' });
  }
  console.log('errors', errs.length); errs.slice(0, 20).forEach(e => console.log(e)); await b.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
