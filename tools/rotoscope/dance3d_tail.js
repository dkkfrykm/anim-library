/* runtime glue: dance clips join RB_ROTO3D / RB_ANIM3D.roto (RB_ROTO.play) and RB_ANIM3D.poses (view3d tags 'dance', 'dance_loop', 'dance_N') */
(function () {
  const D = window.RB_DANCE3D, A = window.RB_ANIM3D = window.RB_ANIM3D || {}, C = D.clips, ids = Object.keys(C).sort();
  const RC = (window.RB_ROTO3D = window.RB_ROTO3D || { clips: {} }).clips; ids.forEach(k => { RC[k] = C[k]; });
  A.roto = A.roto || { clips: RC }; if (A.roto.clips !== RC) ids.forEach(k => { A.roto.clips[k] = C[k]; });
  if (A.poses && A.poses.clips) ids.forEach(k => { A.poses.clips[k] = C[k]; });
  /* view3d filters its tag lists by RB_ANIM3D.poses2.keepOld when that pose set is present: whitelist ours */
  if (A.poses2 && Array.isArray(A.poses2.keepOld)) ids.forEach(k => { if (!A.poses2.keepOld.includes(k)) A.poses2.keepOld.push(k); });
  const inH = () => !!(window.RBH && RBH.H), isR = a => !a || a == 'reiko' || (a && a.id == 'reiko');
  /* RB_DANCE.play([id]): she dances in the daily view (random dance when no id); outside the daily view the clip plays raw */
  window.RB_DANCE = { ids, names: D.names, log: D.log,
    play(id, o) { id = C[id] ? id : ids[(Math.random() * ids.length) | 0]; if (window.RBV3 && RBV3.direct && !inH()) { RBV3.direct({ pose: id }); return id; }
      const F = window.RB3 && RB3.actor('reiko'); return F ? RB3.play(F, 'roto', id, o) : null; } };
  /* RB_ROTO.play(actor, 'dance_N'): same routing as the solo roto clips (daily view -> RBV3 for floor fit + camera) */
  const RP = window.RB_ROTO; if (RP && RP.play) { const p0 = RP.play; RP.dances = ids;
    RP.play = function (actor, id, o) { if (C[id] && isR(actor) && !(o && o.raw) && window.RBV3 && RBV3.direct && !inH()) { RBV3.direct({ pose: id }); const F = RB3.actor('reiko'); return F && F.cur; } return p0.call(RP, actor, id, o); }; }
})();
