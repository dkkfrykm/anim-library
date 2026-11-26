// node tools/dance_preview.js <id> <outdir>  — records the freshly baked clip tools/roto/mocap_clips/<id>.json playing on Reiko (does not modify game files)
const { chromium } = require('C:/Users/mytwo/node_modules/playwright'); const fs = require('fs');
(async () => { const [id, out] = process.argv.slice(2); fs.mkdirSync(out, { recursive: true });
  const SRC = process.env.CLIPDIR || 'tools/roto/mocap_clips'; const clip = JSON.parse(fs.readFileSync(SRC + '/' + id + '.json', 'utf8')).clip;
  const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files'] });
  const ctx = await b.newContext({ viewport: { width: 960, height: 1080 }, recordVideo: { dir: out, size: { width: 960, height: 1080 } } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.addInitScript(([id, clip]) => { let v; Object.defineProperty(window, 'RB_DANCE3D', { configurable: true, get() { return v; }, set(x) { if (x && x.clips) x.clips[id] = clip; v = x; } }); }, [id, clip]);
  await p.goto('file:///C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed/reiko_breed_3d.html'); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 }); await p.evaluate(() => window.RB3_READY);
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); for (let i = 0; i < 14; i++) RBG.next(); ['dlg', 'hud', 'acts', 'choices'].forEach(k => { const e = document.getElementById(k); if (e) e.style.display = 'none'; }); });
  await p.waitForTimeout(1500); await p.evaluate(id => { RBV.scene(Object.assign({}, RBV._V, { room: 'living', slot: 'afternoon', her: true, outfit: 'workout' })); RB_DANCE.play(id); RBV._V.cam = 'wide'; }, id);
  await p.waitForTimeout((clip.dur * 2 + 2) * 1000); console.log('errs', errs); await p.close(); await ctx.close(); await b.close();
  const f = fs.readdirSync(out).filter(x => x.endsWith('.webm')).map(x => out + '/' + x).sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0]; fs.renameSync(f, out + '/' + id + '.webm'); console.log(out + '/' + id + '.webm'); })();
