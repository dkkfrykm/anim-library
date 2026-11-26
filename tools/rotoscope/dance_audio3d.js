/* RB_DANCE_MUSIC: plays each dance's music (window.RB_DANCE_AUDIO, tools/roto/dance_audio.py) while that dance clip plays on her, locked to
   the clip: same loop length, started at the clip's current time, re-synced if audio and animation drift > 60 ms (the animation is the clock,
   so pause/slow-mo/scrubbing stay in sync; small drift from slow frames is corrected on the animation's clock, so the music never skips). Stops on any other clip. WebAudio buffers decoded from embedded data URIs (file:// safe).
   Respects the game's mute (window.RB_MUTE / RBAUD) ; RB_DANCE_MUSIC.volume (0..1, remembered), .enabled. */
(function () {
  const A = window.RB_DANCE_AUDIO; if (!A) return;
  let ctx = null, gain = null, src = null, cur = null, t0 = 0, buf = {}, pending = {};
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } };
  const M = window.RB_DANCE_MUSIC = { volume: +(store('rb_dance_vol') || .7), enabled: store('rb_dance_on') !== '0', get playing() { return cur; },
    setVolume(v) { M.volume = Math.max(0, Math.min(1, +v)); store('rb_dance_vol', String(M.volume)); },
    setEnabled(b) { M.enabled = !!b; store('rb_dance_on', b ? '1' : '0'); if (!b) stop(); } };
  function ensure() { if (ctx) return ctx; const C = window.AudioContext || window.webkitAudioContext; if (!C) return null; ctx = new C(); gain = ctx.createGain(); gain.connect(ctx.destination); return ctx; }
  ['pointerdown', 'keydown', 'touchstart'].forEach(e => window.addEventListener(e, () => { const c = ensure(); if (c && c.state === 'suspended') c.resume(); }, { capture: true, passive: true }));
  function load(id) { if (buf[id] || pending[id] || !ensure()) return; const d = A[id]; if (!d) return; pending[id] = true;
    const b64 = d.data.slice(d.data.indexOf(',') + 1), bin = atob(b64), ab = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) ab[i] = bin.charCodeAt(i);
    ctx.decodeAudioData(ab.buffer).then(x => { buf[id] = x; pending[id] = false; }, e => { pending[id] = false; console.warn('RB_DANCE_MUSIC decode', id, e); }); }
  function stop() { if (src) { try { src.stop(); } catch (e) { } src.disconnect(); src = null; } cur = null; }
  function start(id, t) { stop(); const b = buf[id]; if (!b) return; src = ctx.createBufferSource(); src.buffer = b; src.loop = true; src.loopStart = 0; src.loopEnd = b.duration;
    M.restarts = (M.restarts || 0) + 1; src.connect(gain); const off = ((t % b.duration) + b.duration) % b.duration; src.start(0, off); t0 = ctx.currentTime - off; cur = id; }
  function danceOf(F) { const a = F && F.cur, c = a && a.getClip && a.getClip(); if (!c || !a.enabled || a.getEffectiveWeight() < .5) return null; const m = /:(dance_\d+)$/.exec(c.name); return m && A[m[1]] ? m[1] : null; }
  function tick() {
    requestAnimationFrame(tick);
    const R = window.RB3, F = R && R.her && R.her(); const id = M.enabled ? danceOf(F) : null;
    const muted = !!window.RB_MUTE || (window.RBAUD && RBAUD.mute);
    if (gain) gain.gain.value = muted ? 0 : M.volume;
    if (!id) { if (cur) stop(); return; }
    if (!ensure() || ctx.state !== 'running') return; load(id); if (!buf[id]) return;
    const a = F.cur, d = buf[id].duration, t = a.time, paused = a.paused || a.timeScale === 0 || (typeof R.paused === 'function' && R.paused());
    if (paused) { if (cur) stop(); return; }
    if (cur !== id) { start(id, t); return; }
    const at = (ctx.currentTime - t0) % d; let dt = Math.abs(at - (t % d)); dt = Math.min(dt, d - dt);
    M.drift = Math.max(M.drift || 0, dt);
    if (Math.abs(a.timeScale - 1) > .01) { stop(); return; }   // non-1x speed: silent
    if (dt > .5) { start(id, t); return; }   // the clip jumped (scrub / restart): music follows it
    if (dt > .05) a.time = at;   // slow frames hold the animation clock back: the music is the clock, the dance is put back on the beat (timing only, poses untouched)
  }
  requestAnimationFrame(tick);
})();
