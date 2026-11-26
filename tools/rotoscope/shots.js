// QA renderer: node tools/roto/shots.js <fileUrl> <spec.json> <outdir>
// spec: [{name, f:{src,key,t}, m:{src,key,t}|null, cam:{yaw,pitch,dist,fov,tgt:'pel'|'head'|'mid'|[x,y,z],dy}, room:[name,slot,fit], outfit, eval}]
// Drives RB3 directly from the title screen (no game loop), renders each shot at an exact clip time, logs bone probes + page errors.
const { chromium } = require('C:/Users/mytwo/node_modules/playwright');
(async () => {
  const [url, specF, out] = process.argv.slice(2); const fs = require('fs'); fs.mkdirSync(out, { recursive: true }); const spec = JSON.parse(fs.readFileSync(specF, 'utf8'));
  const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 960, height: 720 } }); const errs = [];
  p.on('console', m => { if (m.type() == 'error') errs.push('console: ' + m.text().slice(0, 300)); if (m.text().startsWith('ROTO')) console.log(m.text()); }); p.on('pageerror', e => errs.push('pageerror: ' + (e.stack || e.message).slice(0, 500)));
  await p.goto(url, { timeout: 240000 }); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 240000 }); await p.evaluate(() => window.RB3_READY);
  await p.evaluate(() => { document.querySelectorAll('body > *').forEach(e => { if (e.id != 'w') e.style.display = 'none'; }); const w = document.getElementById('w'); [...w.children].forEach(e => { if (e.id != 'c3') e.style.display = 'none'; }); const c = document.getElementById('c3'); c.hidden = false; c.style.cssText = 'position:fixed;left:0;top:0;width:100vw;height:100vh;display:block;z-index:9'; });
  for (const s of spec) {
    const info = await p.evaluate(async s => {
      for (const f of (s.load || [])) if (!(window.RB_OST_LOADED || {})[f.split('/').pop().slice(0, -3)]) await new Promise(r => { const e = document.createElement('script'); e.src = f; e.onload = r; e.onerror = r; document.head.appendChild(e); });
      const F = RB3.actor('reiko'), U = RB3.actor('player'), T = THREE; RB3.show(F, true); RB3.show(U, !!s.m); if (s.m) RB3.male(s.male || 'visible');
      RB3.place(F, 0, 0, 0); RB3.place(U, 0, 0, 0); RB3.outfit(F, s.outfit || 'nude'); const r = s.room || ['hbed', 'night', { floor: -.46, mattress: { x: 0, z: 0, w: 2.1, d: 2.3, top: 0 } }]; RB3.room(r[0], r[1], r[2]);
      const set = (A, c) => { if (!c) return; RB3.play(A, c.src, c.key, { fade: 0, time: c.t || 0, rate: 0 }); };
      set(F, s.f); set(U, s.m); if (s.eval) (0, eval)(s.eval);
      U.post = s.pen && window.PEN3 ? (A, d) => PEN3.step(U, F, d, { insert: 1, kind: s.pen, butt: !!s.butt }) : null;
      for (let i = 0; i < (s.settle || 40); i++) { if (s.f) F.cur.time = s.f.t || 0; if (s.m && U.cur) U.cur.time = s.m.t || 0; RB3.render(1 / 60); }
      if (s.fit) { /* emulate view3d fit(): feet to the floor, counter under the hands (pelvis.z - .45) */ F.root.position.y = 0; F.root.updateMatrixWorld(true); let lo = 1e9; ['NPC L Foot [Lft ]', 'NPC R Foot [Rft ]', 'NPC L Toe0 [LToe]', 'NPC R Toe0 [RToe]'].forEach(n => { const v = RB3.bonePos(F, n); if (v) lo = Math.min(lo, v.y); }); F.root.position.y = .03 - lo; F.root.updateMatrixWorld(true);
        const pel = RB3.bonePos(F, 'NPC Pelvis [Pelv]'), hy = Math.min(RB3.bonePos(F, 'NPC L Hand [LHnd]').y, RB3.bonePos(F, 'NPC R Hand [RHnd]').y); RB3.room(s.fit, 'evening', { floor: 0, counter: { x: pel.x, z: pel.z - .45, w: 1.8, d: .55, top: Math.max(.8, Math.min(1, hy)) } }); RB3.render(0); }
      const bp = (A, n) => { const v = RB3.bonePos(A, n); return v ? [+v.x.toFixed(3), +v.y.toFixed(3), +v.z.toFixed(3)] : null; };
      const P = { fpel: bp(F, 'NPC Pelvis [Pelv]'), fhead: bp(F, 'NPC Head [Head]'), flk: bp(F, 'NPC L Calf [LClf]'), frk: bp(F, 'NPC R Calf [RClf]'), flf: bp(F, 'NPC L Foot [Lft ]'), frf: bp(F, 'NPC R Foot [Rft ]'), flh: bp(F, 'NPC L Hand [LHnd]'), frh: bp(F, 'NPC R Hand [RHnd]') };
      if (s.pen && window.PEN3) P.pen = { eng: PEN3.st.engaged, depth: +PEN3.st.depth.toFixed(2) };
      if (s.probe) P.probe = (0, eval)(s.probe);
      if (s.m) Object.assign(P, { mpel: bp(U, 'NPC Pelvis [Pelv]'), mgen: bp(U, 'NPC GenitalsBase [GenBase]'), mtip: bp(U, 'NPC Genitals06 [Gen06]') });
      const c = s.cam || {}; const tg = c.tgt == 'head' ? RB3.bonePos(F, 'NPC Head [Head]') : Array.isArray(c.tgt) ? new T.Vector3(...c.tgt) : c.tgt == 'mid' && s.m ? RB3.bonePos(F, 'NPC Pelvis [Pelv]').add(RB3.bonePos(U, 'NPC Pelvis [Pelv]')).multiplyScalar(.5) : RB3.bonePos(F, 'NPC Pelvis [Pelv]');
      tg.y += c.dy || 0; RB3.cam.tTarget = null; RB3.cam.target.copy(tg); RB3.cam.yaw = c.yaw == null ? .6 : c.yaw; RB3.cam.pitch = c.pitch == null ? .2 : c.pitch; RB3.cam.dist = c.dist || 2.4; RB3.cam.fov = c.fov || 32;
      if (s.f) F.cur.time = s.f.t || 0; if (s.m && U.cur) U.cur.time = s.m.t || 0; RB3.render(0); return P; }, s);
    await p.screenshot({ path: out + '/' + s.name + '.png' }); console.log(s.name, JSON.stringify(info));
  }
  console.log('errors', errs.length); errs.slice(0, 15).forEach(e => console.log(e)); await b.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
