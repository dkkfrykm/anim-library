// node tools/dance_music_test.js <id> -> checks RB_DANCE_MUSIC: starts with the dance, stays in sync with the clip, stops on another pose
const { chromium } = require('C:/Users/mytwo/node_modules/playwright');
(async () => { const id = process.argv[2] || 'dance_2'; const b = await chromium.launch({ headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--allow-file-access-from-files', '--autoplay-policy=no-user-gesture-required'] });
  const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (/RB_DANCE_MUSIC/.test(m.text())) errs.push(m.text()); });
  await p.goto('file:///C:/Users/mytwo/OneDrive/Desktop/gaem2/reiko_breed/reiko_breed_3d.html'); await p.waitForFunction(() => window.RB3_READY && RB3.actor && RB3.actor('reiko'), null, { timeout: 180000 });
  await p.evaluate(() => { localStorage.clear(); RBG.newGame('Kai'); for (let i = 0; i < 14; i++) RBG.next(); }); await p.mouse.click(5, 5); await p.waitForTimeout(1500);
  console.log('tracks', await p.evaluate(() => Object.keys(window.RB_DANCE_AUDIO || {}).length), 'module', await p.evaluate(() => !!window.RB_DANCE_MUSIC));
  await p.evaluate(id => { RBV.scene(Object.assign({}, RBV._V, { room: 'living', slot: 'afternoon', her: true })); RB_DANCE.play(id); }, id);
  for (let k = 0; k < 6; k++) { await p.waitForTimeout(1500); console.log(await p.evaluate(() => { const F = RB3.her(), a = F.cur, c = a && a.getClip(); return JSON.stringify({ clip: c && c.name, t: a && +a.time.toFixed(2), playing: RB_DANCE_MUSIC.playing, restarts: RB_DANCE_MUSIC.restarts, maxDriftMs: Math.round(1000 * (RB_DANCE_MUSIC.drift || 0)) }); })); }
  await p.evaluate(() => { RBV3.direct({ pose: 'stand' }); }); await p.waitForTimeout(2000);
  console.log('after other pose:', await p.evaluate(() => { const c = RB3.her().cur && RB3.her().cur.getClip(); return JSON.stringify({ clip: c && c.name, playing: RB_DANCE_MUSIC.playing }); }));
  console.log('errs', errs); await b.close(); })();
