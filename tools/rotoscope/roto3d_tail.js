/* runtime glue: RB_ANIM3D.roto registry, speed variants, daily-view aliases, RB_ROTO.play */
(function () {
  const R = window.RB_ROTO3D, A = window.RB_ANIM3D = window.RB_ANIM3D || {}, C = R.clips;
  /* stage speed variants by time-scaling (same keyframes, scaled fps) */
  ['roto_doggy', 'roto_press', 'roto_oral'].forEach(id => ['_f', '_m'].forEach(s => { const c = C[id + s]; if (!c) return;
    [['slow', .7], ['fast', 1.3]].forEach(([v, k]) => { C[id + '_' + v + s] = Object.assign({}, c, { fps: +(c.fps * k).toFixed(4), dur: +(c.dur / k).toFixed(4) }); }); }));
  [['roto_twerk', 'slow', .75], ['roto_twerk', 'fast', 1.25]].forEach(([id, v, k]) => { const c = C[id]; if (c) C[id + '_' + v] = Object.assign({}, c, { fps: +(c.fps * k).toFixed(4), dur: +(c.dur / k).toFixed(4) }); });
  A.roto = { clips: C };
  /* H positions: duo clips join the OStim catalog (catalog3d.js -> RB_CAT3D, read by src/hscene.js + h3d.js) as pack 'roto'.
     h3d plays src 'ost', key <scene>_<c>_<m|f>; the clips are registered here up front, so no per-scene file is fetched. Tier speed = stage r. */
  const O = A.ost = A.ost || { clips: {} }, LD = window.RB_OST_LOADED = window.RB_OST_LOADED || {};
  const CAT = window.RB_CAT3D = window.RB_CAT3D || { packs: {}, scenes: [] }; CAT.packs = CAT.packs || {}; CAT.scenes = CAT.scenes || []; CAT.packs.roto = 'Rotoscoped';
  const MAT = { floor: -.46, mattress: { x: 0, z: 0, w: 2.1, d: 2.3, top: 0 } };
  [['roto_doggy', 'Doggy (rotoscoped)', 'vagina', ['allfours', 'doggy', 'kneeling', 'holdingwaist', 'vaginalsex', 'roto']],
   ['roto_press', 'Mating press (rotoscoped)', 'vagina', ['lyingback', 'matingpress', 'legsup', 'vaginalsex', 'roto']],
   ['roto_oral', 'Kneeling deepthroat (rotoscoped)', 'mouth', ['blowjob', 'deepthroat', 'kneeling', 'holdingthigh', 'roto']]].forEach(([id, name, kind, tags]) => {
    if (!C[id + '_f'] || !C[id + '_m']) return; O.clips[id + '_1_f'] = C[id + '_f']; O.clips[id + '_1_m'] = C[id + '_m']; LD[id] = true;
    if (CAT.scenes.some(s => s.id == id)) return;
    CAT.scenes.push({ id, pack: 'roto', name, kind, tags, furniture: 'mattress', stages: [.7, 1, 1.3, 1.55, 1].map(r => ({ c: 1, r, b: 0, k: kind })), file: 'web/assets/anims/roto3d.js', src: 'roto', fit: MAT, period: (R.log[id] || {}).period_s }); });
  /* daily view (view3d.js) picks poses by id from RB_ANIM3D.poses -> alias the solo clips there (tags 'twerk' / 'idle_sway') */
  if (A.poses && A.poses.clips) ['roto_twerk', 'roto_idle_sway', 'roto_prone_idle'].forEach(k => { A.poses.clips[k] = C[k]; });
  /* view3d filters its tag lists by RB_ANIM3D.poses2.keepOld (+support) when that pose set is present: whitelist ours */
  if (A.poses2 && Array.isArray(A.poses2.keepOld)) ['roto_twerk', 'roto_idle_sway', 'roto_prone_idle'].forEach(k => { if (!A.poses2.keepOld.includes(k)) A.poses2.keepOld.push(k); });
  const TAG = { roto_twerk: 'twerk', roto_idle_sway: 'idle_sway', roto_prone_idle: 'lie_phone' };
  const act = a => typeof a == 'string' ? window.RB3 && RB3.actor(a) : a;
  window.RB_ROTO = { clips: C, solo: ['roto_twerk', 'roto_idle_sway', 'roto_prone_idle'], duo: ['roto_doggy', 'roto_press', 'roto_oral'], kind: { roto_doggy: 'vagina', roto_press: 'vagina', roto_oral: 'mouth' }, log: R.log,
    /* play(actor|'reiko'|'player'|null, id[, {fade, rate, time}]): solo id on Reiko in the daily view goes through RBV3 (furniture fit + camera);
       a duo id without suffix plays _f on Reiko and _m on the player, time-locked */
    play(actor, id, o) { o = o || {}; if (!window.RB3) return null;
      if (C[id + '_f'] && C[id + '_m'] && !/_[fm]$/.test(id)) { const F = RB3.actor('reiko'), U = RB3.actor('player'), t = o.time || 0;
        const a = RB3.play(F, 'roto', id + '_f', Object.assign({}, o, { time: t })), b = RB3.play(U, 'roto', id + '_m', Object.assign({}, o, { time: t })); return [a, b]; }
      const A2 = act(actor || 'reiko'); if (!A2 || !C[id]) { console.warn('RB_ROTO: no clip', id); return null; }
      const base = id.replace(/_(slow|fast)$/, '');
      if (A2.id == 'reiko' && TAG[base] && window.RBV3 && RBV3.direct && !(window.RBH && RBH.H) && id == base) { RBV3.direct({ pose: TAG[base] }); return A2.cur; }
      return RB3.play(A2, 'roto', id, o); } };
})();
