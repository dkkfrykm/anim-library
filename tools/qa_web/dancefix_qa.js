// node tools/dancefix_qa.js <id> <outdir> [label] [flags]  -- deterministic dance QA (virtual 30 fps clock): per-frame timeline
// (life3d hand/head/finger deltas, breast collision push, butt offsets) + multi-camera shots at given clip times.
// flags (comma list): nolife, noself (RB_PHYS self colliders off), nophys, times=a;b;c, cams=full;chest;head;handL;handR;hip
const { chromium } = require('C:/Users/mytwo/node_modules/playwright'); const fs = require('fs');
(async () => {
  const [id, out, label = 'run', flagStr = ''] = process.argv.slice(2); fs.mkdirSync(out, { recursive: true });
  const fl = {}; flagStr.split(',').filter(Boolean).forEach(s => { const [k, v] = s.split('='); fl[k] = v == null ? true : v; });
  const times = (fl.times || '').split(';').filter(Boolean).map(Number), cams = (fl.cams || 'full;chest;head;handL;handR;hip').split(';');
  const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.addInitScript(() => { const rRAF = window.requestAnimationFrame.bind(window), rNow = performance.now.bind(performance); let on = false, vt = 0, q = [], budget = 0, done = null;
    window.__vt = { start() { on = true; vt = rNow(); }, step(n) { budget = n; return new Promise(r => { done = r; }); } };
    performance.now = () => on ? vt : rNow(); window.requestAnimationFrame = cb => { if (!on) return rRAF(cb); q.push(cb); return 1; };
    const pump = () => { if (on && budget > 0 && q.length) { vt += 1000 / 30; const cbs = q; q = []; cbs.forEach(c => { try { c(vt); } catch (e) { console.error(e); } }); budget--; if (!budget && done) { const d = done; done = null; rRAF(() => rRAF(d)); } } rRAF(pump); }; rRAF(pump); });
  if (process.env.CLIPJSON) { const clip = JSON.parse(fs.readFileSync(process.env.CLIPJSON, 'utf8')).clip;   /* staged clip injected (QA before promoting; game files untouched) */
    await p.addInitScript(([id, clip]) => { let v; Object.defineProperty(window, 'RB_DANCE3D', { configurable: true, get() { return v; }, set(x) { if (x && x.clips) x.clips[id] = clip; v = x; } }); }, [id, clip]); }
  await p.goto('file:///C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed/reiko_breed_3d.html'); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 }); await p.evaluate(() => window.RB3_READY);
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); for (let i = 0; i < 14; i++) RBG.next(); ['dlg', 'hud', 'acts', 'choices'].forEach(k => { const e = document.getElementById(k); if (e) e.style.display = 'none'; }); });
  await p.waitForTimeout(1500);
  await p.evaluate(([id, fl]) => { RBV.scene(Object.assign({}, RBV._V, { room: 'living', slot: 'afternoon', her: true, outfit: fl.outfit || 'workout' })); RB_DANCE.play(id); RBV._V.cam = 'wide';
    if (fl.bsoft) { const v = fl.bsoft.split('_').map(Number); RB_PHYS.cfg.soft.Butt = { k: v[0], d: v[1], linX: v[2], linY: v[3], linZ: v[4], rot: v[5], off: v[6] }; if (v[7]) RB_PHYS.cfg.capCm.Butt = v[7]; (RB_PHYS.nodes || []).forEach(N => { N.pp = null; }); }
    if (fl.legK) RB_PHYS.cfg.cloth.leggings = +fl.legK;
    if (fl.nolife) RB_LIFE.enable(false); if (fl.nophys) RB_PHYS.on = false; if (fl.legacy) { RB_LIFE.cfg.anim.off = false; RB_PHYS.cfg.soft = {}; RB_PHYS.cfg.self = { nodeK: 1, rate: 12, cd: 0 }; RB_PHYS.cfg.cloth.butt = .55; RB_PHYS.cfg.capCm.Butt = 4; (RB_PHYS.nodes || []).forEach(N => { N.pp = null; }); }
    const T = THREE, F = RB3.her(), bp = n => RB3.bonePos(F, n), V = () => new T.Vector3();
    const HB = ['NPC L Hand [LHnd]', 'NPC R Hand [RHnd]', 'NPC Head [Head]', 'NPC L Finger21 [LF21]', 'NPC R Finger21 [RF21]', 'NPC L Finger12 [LF12]', 'NPC R Finger12 [RF12]'];
    const QD = (a, b) => { const x = a.clone().normalize().invert().multiply(b.clone().normalize()); return 2 * Math.atan2(Math.hypot(x.x, x.y, x.z), Math.abs(x.w)) * 57.3; };
    if (fl.noself) { const r0 = RB3.render; RB3.render = function () { if (RB_PHYS.selfCols && RB_PHYS.selfCols.length) RB_PHYS.selfCols = []; return r0.apply(this, arguments); }; }
    window.__tl = []; const rr = RB3.renderer, d0 = rr.render;
    /* fing=<15 curls thumb..pinky x MCP,PIP,DIP, '_'-sep, rad> : test hand = rest pose + curl about each joint's rest flex axis (RBCONTACT.fingerRig), set after the mixer, before every render */
    const FC = fl.fing ? fl.fing.split('_').map(Number) : null;
    const setFing = () => { if (!FC) return; const FR = RBCONTACT.fingerRig(F); ['L', 'R'].forEach(s => { if (!FR || !FR[s]) return; FR[s].forEach((ch, f) => ch.forEach((j, k) => { j.b.quaternion.copy(j.qRest).multiply(new T.Quaternion().setFromAxisAngle(j.axL, FC[f * 3 + k] || 0)); })); }); F.root.updateMatrixWorld(true); };
    rr.render = function (scene, cam) { if (scene === RB3.scene) setFing(); if (scene !== RB3.scene || window.__noTL) return d0.apply(this, arguments);

      const pre = HB.map(n => { const b = F.bones[n]; return b ? { p: b.getWorldPosition(V()), q: b.getWorldQuaternion(new T.Quaternion()), lq: b.quaternion.clone() } : null; });
      const r = d0.apply(this, arguments);
      const post = HB.map(n => { const b = F.bones[n]; return b ? { p: b.getWorldPosition(V()), q: b.getWorldQuaternion(new T.Quaternion()), lq: b.quaternion.clone() } : null; });
      const br = ['L', 'R'].map(s => bp('NPC ' + s + ' Breast01') || bp(s + ' Breast01')), hd = [0, 1].map(i => post[i] && post[i].p);
      const fg = [3, 4].map(i => post[i] && post[i].p);
      const nodes = (RB_PHYS.nodes || []).filter(N => N.lvl == 1 && (N.part == 'Breast' || N.part == 'Butt'));
      const rec = { t: +RB3.time(F).toFixed(3), dHand: [0, 1].map(i => pre[i] && +(pre[i].p.distanceTo(post[i].p) * 100).toFixed(2)), dHandQ: [0, 1].map(i => pre[i] && +QD(pre[i].q, post[i].q).toFixed(1)),
        dHeadQ: pre[2] && +QD(pre[2].q, post[2].q).toFixed(1), dFingQ: [3, 4, 5, 6].map(i => pre[i] && +QD(pre[i].lq, post[i].lq).toFixed(1)),
        hb: br[0] && hd[0] ? [Math.min(hd[0].distanceTo(br[0]), hd[0].distanceTo(br[1] || br[0]), fg[0].distanceTo(br[0])), Math.min(hd[1].distanceTo(br[1] || br[0]), hd[1].distanceTo(br[0]), fg[1].distanceTo(br[1] || br[0]))].map(x => +(x * 100).toFixed(1)) : null,
        col: nodes.filter(N => N.part == 'Breast').map(N => N.side + ':' + (N.col.length() * 1.4286).toFixed(2)), out: nodes.map(N => N.part.slice(0, 2) + N.side + ':' + N.out.toArray().map(x => (x * 1.4286).toFixed(2)).join('/')),
        b3: (() => { const t3 = ["L", "R"].map(s => bp(s + " Breast03") || bp("NPC " + s + " Breast03")); if (!t3[0]) return null; return [0, 1].map(i => +(Math.min(...[hd[i], fg[i]].flatMap(p => t3.map(q => p.distanceTo(q)))) * 100).toFixed(1)); })(), hy: [0, 1].map(i => +((hd[i].y - post[2].p.y) * 100).toFixed(0)), dev: (() => { const a = F.cur; if (!a || !a._interpolants) return null; let mq = 0, mqb = "", mp = 0, mpb = ""; const t = a.time; a._interpolants.forEach((ip, i) => { const pb = a._propertyBindings[i], bd = pb && pb.binding, nd = bd && bd.node, pn = bd && bd.parsedPath.propertyName; if (!nd || !nd.isBone) return; const nm = nd.userData.sky || nd.name; if (/Breast|Butt|Belly|FrontThigh|RearThigh|RearCalf|Pussy|Clitoral|Vagina|Anus/.test(nm)) return; const r = ip.evaluate(t); if (pn == "quaternion") { const d = QD(new T.Quaternion(r[0], r[1], r[2], r[3]).normalize(), nd.quaternion); if (d > mq) { mq = d; mqb = nm; } } else if (pn == "position") { const d = Math.hypot(r[0] - nd.position.x, r[1] - nd.position.y, r[2] - nd.position.z); if (d > mp) { mp = d; mpb = nm; } } }); return [+mq.toFixed(2), mqb, +mp.toFixed(4), mpb]; })(), lifeMs: +RB_LIFE.ms.toFixed(3), physMs: +(RB_PHYS.ms || 0).toFixed(3) };
      if (fl.clr && rec.t > 8.5 && __tl.length % 2 == 0) { const c = RB_LIFE.clearance(); rec.clr = c && [c.l.hand, c.l.finger, c.r.hand, c.r.finger].map(x => +(x * 100).toFixed(1)); }
      __tl.push(rec); return r; };
    /* camera rig for shots: re-render the held frame from several views */
    window.__shot = function (mode) { const cam = RB3.camera, f = (() => { const a = bp('NPC L Thigh [LThg]'), c = bp('NPC R Thigh [RThg]'); const lat = a.clone().sub(c); lat.y = 0; lat.normalize(); return lat.cross(new T.Vector3(0, 1, 0)).normalize(); })();
      const yaw0 = Math.atan2(f.x, f.z); let tg, dist, yaw = yaw0, pitch = .08;
      if (mode == 'full') { tg = bp('NPC Pelvis [Pelv]').add(new T.Vector3(0, .1, 0)); dist = 2.3; } else if (mode == 'bust') { tg = bp('NPC Spine2 [Spn2]').add(new T.Vector3(0, -.04, 0)).addScaledVector(f, .1); dist = .75; yaw += .35; pitch = .12; } else if (mode == 'upper') { tg = bp('NPC Spine2 [Spn2]').add(new T.Vector3(0, .1, 0)); dist = 1.6; yaw += .15; }
      else if (mode == 'chest') { tg = bp('NPC Spine2 [Spn2]').add(new T.Vector3(0, .02, 0)); dist = 1.15; yaw += .25; }
      else if (mode == 'head') { tg = bp('NPC Head [Head]').add(new T.Vector3(0, .05, 0)); dist = .75; yaw += .2; }
      else if (mode == 'handL' || mode == 'handR') { const s = mode[4]; tg = bp('NPC ' + s + ' Hand [' + s + 'Hnd]').lerp(bp('NPC ' + s + ' Finger21 [' + s + 'F21]'), .5); dist = .42; yaw += s == 'L' ? .6 : -.6; pitch = .2; }
      else if (mode == 'hip') { tg = bp('NPC Pelvis [Pelv]'); dist = 1.5; yaw += Math.PI + .55; pitch = .05; }
      if (fl.yaw) yaw = yaw0 + +fl.yaw;
      const C = RB3.cam; C.tTarget = null; C.target.copy(tg); C.dist = dist; C.yaw = yaw; C.pitch = pitch; C.fov = 32;
      window.__noTL = true; try { RB3.render(1e-5); } finally { window.__noTL = false; } }; /* the normal render path (RB_SHADE passes) with the QA camera, ~zero sim advance */
  }, [id, fl]);
  await p.evaluate(() => __vt.start()); await p.evaluate(() => __vt.step(60)); /* settle 2 s */
  const dur = await p.evaluate(() => RB3.her().cur.getClip().duration); const t0 = await p.evaluate(() => RB3.time(RB3.her())); console.log('dur', dur, 't0', t0);
  /* loop 2 is the measured one: step until the clip wraps, then step frame by frame */
  let prev = t0; for (; ;) { await p.evaluate(() => __vt.step(1)); const t = await p.evaluate(() => RB3.time(RB3.her())); if (t < prev) break; prev = t; }
  await p.evaluate(() => { __tl.length = 0; });
  const want = times.slice().sort((a, b) => a - b); let wi = 0; prev = 0;
  for (let k = 0; k < Math.ceil(dur * 30) + 2; k++) { await p.evaluate(() => __vt.step(1)); const t = await p.evaluate(() => RB3.time(RB3.her())); if (t < prev) break; prev = t;
    while (wi < want.length && t >= want[wi]) { for (const c of cams) { await p.evaluate(c => __shot(c), c); await p.screenshot({ path: `${out}/${label}_t${want[wi].toFixed(2)}_${c}.png`, clip: { x: 280, y: 0, width: 720, height: 720 } }); } wi++; } }
  const tl = await p.evaluate(() => __tl); fs.writeFileSync(`${out}/${label}_timeline.json`, JSON.stringify(tl));
  const agg = k => { const v = tl.map(r => r[k]).flat().filter(x => typeof x == 'number'); return v.length ? { max: Math.max(...v).toFixed(2), mean: (v.reduce((s, x) => s + x, 0) / v.length).toFixed(2) } : null; };
  const colMax = Math.max(0, ...tl.map(r => Math.max(0, ...r.col.map(s => +s.split(':')[1]))));
  console.log(label, 'frames', tl.length, 'dHand cm', JSON.stringify(agg('dHand')), 'dHandQ', JSON.stringify(agg('dHandQ')), 'dHeadQ', JSON.stringify(agg('dHeadQ')), 'dFingQ', JSON.stringify(agg('dFingQ')), 'breastColMax cm', colMax.toFixed(2), 'lifeMs', JSON.stringify(agg('lifeMs')), 'physMs', JSON.stringify(agg('physMs')));
  console.log('errs', errs.length, errs.slice(0, 5)); await b.close();
})().catch(e => { console.error('FAIL', e); process.exit(1); });
