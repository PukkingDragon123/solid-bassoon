/**
 * Temple sound, synthesised.
 *
 * Nothing here loads a file: every sound is built from oscillators and
 * noise so the app stays small and works offline.  The context is created
 * lazily on the first gesture, as browsers require.
 */

let ctx = null;
let master = null;
let bed = null;
let enabled = true;

function ac() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = enabled ? 0.9 : 0;
    master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

export function unlock() {
  const c = ac();
  if (!c) return;
  // a silent blip: some browsers need an actual scheduled node to wake up
  const o = c.createOscillator();
  const g = c.createGain();
  g.gain.value = 0.0001;
  o.connect(g).connect(master);
  o.start();
  o.stop(c.currentTime + 0.02);
}

export function setEnabled(on) {
  enabled = on;
  if (master && ctx) master.gain.setTargetAtTime(on ? 0.9 : 0, ctx.currentTime, 0.05);
}

export function isEnabled() {
  return enabled;
}

// ── building blocks ───────────────────────────────────────────

function noiseBuffer(c, seconds = 1) {
  const len = Math.floor(c.sampleRate * seconds);
  const buf = c.createBuffer(1, len, c.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
  return buf;
}

let sharedNoise = null;
function noise(c) {
  if (!sharedNoise || sharedNoise.sampleRate !== c.sampleRate) sharedNoise = noiseBuffer(c, 2);
  const src = c.createBufferSource();
  src.buffer = sharedNoise;
  return src;
}

function env(c, gain, t0, attack, decay, peak = 1) {
  gain.gain.setValueAtTime(0.0001, t0);
  gain.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0002), t0 + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, t0 + attack + decay);
}

/** A struck metal body: inharmonic partials, each with its own decay. */
function struck(c, t0, fundamental, partials, dur, level) {
  const out = c.createGain();
  out.gain.value = level;
  out.connect(master);
  partials.forEach(([ratio, amp, decayScale]) => {
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = 'sine';
    o.frequency.value = fundamental * ratio;
    // very slight downward drift is what makes struck metal sound struck
    o.frequency.setValueAtTime(fundamental * ratio * 1.006, t0);
    o.frequency.exponentialRampToValueAtTime(fundamental * ratio, t0 + 0.16);
    env(c, g, t0, 0.004, dur * decayScale, amp);
    o.connect(g).connect(out);
    o.start(t0);
    o.stop(t0 + dur * decayScale + 0.1);
  });
  // strike transient
  const n = noise(c);
  const nf = c.createBiquadFilter();
  const ng = c.createGain();
  nf.type = 'bandpass';
  nf.frequency.value = fundamental * 6;
  nf.Q.value = 1.2;
  env(c, ng, t0, 0.002, 0.09, 0.5);
  n.connect(nf).connect(ng).connect(out);
  n.start(t0);
  n.stop(t0 + 0.2);
}

// ── the sounds ────────────────────────────────────────────────

export function bell() {
  const c = ac();
  if (!c) return;
  struck(c, c.currentTime, 520, [[1, 0.5, 1], [2.02, 0.3, 0.72], [3.01, 0.2, 0.5], [4.22, 0.12, 0.34], [5.43, 0.07, 0.22]], 3.6, 0.34);
}

export function gong() {
  const c = ac();
  if (!c) return;
  struck(c, c.currentTime, 118, [[1, 0.6, 1], [1.48, 0.34, 0.86], [2.13, 0.26, 0.7], [2.97, 0.16, 0.55], [4.31, 0.1, 0.38]], 6.5, 0.4);
}

export function chime() {
  const c = ac();
  if (!c) return;
  struck(c, c.currentTime, 1180, [[1, 0.4, 1], [2.76, 0.16, 0.5], [5.4, 0.07, 0.3]], 1.5, 0.2);
}

/** One bamboo stick knocking another. */
export function clack(level = 1) {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime;
  const n = noise(c);
  const f = c.createBiquadFilter();
  const g = c.createGain();
  f.type = 'bandpass';
  f.frequency.value = 1500 + Math.random() * 900;
  f.Q.value = 3.4;
  env(c, g, t0, 0.001, 0.075, 0.42 * level);
  n.connect(f).connect(g).connect(master);
  n.start(t0);
  n.stop(t0 + 0.16);

  const o = c.createOscillator();
  const og = c.createGain();
  o.type = 'triangle';
  o.frequency.setValueAtTime(760 + Math.random() * 380, t0);
  o.frequency.exponentialRampToValueAtTime(240, t0 + 0.055);
  env(c, og, t0, 0.001, 0.055, 0.18 * level);
  o.connect(og).connect(master);
  o.start(t0);
  o.stop(t0 + 0.14);
}

/** Many sticks rattling inside a bamboo tube. */
export function rattle(intensity = 1) {
  const n = 2 + Math.floor(Math.random() * 3 * intensity);
  for (let i = 0; i < n; i++) {
    setTimeout(() => clack(0.35 + Math.random() * 0.55 * intensity), i * (18 + Math.random() * 46));
  }
}

export function matchStrike() {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime;
  const n = noise(c);
  const f = c.createBiquadFilter();
  const g = c.createGain();
  f.type = 'bandpass';
  f.Q.value = 0.9;
  f.frequency.setValueAtTime(900, t0);
  f.frequency.exponentialRampToValueAtTime(4200, t0 + 0.10);
  f.frequency.exponentialRampToValueAtTime(600, t0 + 0.42);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(0.34, t0 + 0.03);
  g.gain.exponentialRampToValueAtTime(0.10, t0 + 0.16);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.7);
  n.connect(f).connect(g).connect(master);
  n.start(t0);
  n.stop(t0 + 0.8);
}

export function whoosh(dur = 0.8) {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime;
  const n = noise(c);
  const f = c.createBiquadFilter();
  const g = c.createGain();
  f.type = 'lowpass';
  f.frequency.setValueAtTime(260, t0);
  f.frequency.exponentialRampToValueAtTime(2600, t0 + dur * 0.45);
  f.frequency.exponentialRampToValueAtTime(300, t0 + dur);
  env(c, g, t0, dur * 0.35, dur * 0.65, 0.22);
  n.connect(f).connect(g).connect(master);
  n.start(t0);
  n.stop(t0 + dur + 0.1);
}

export function paperRustle() {
  const c = ac();
  if (!c) return;
  const t0 = c.currentTime;
  for (let i = 0; i < 5; i++) {
    const t = t0 + i * (0.045 + Math.random() * 0.05);
    const n = noise(c);
    const f = c.createBiquadFilter();
    const g = c.createGain();
    f.type = 'highpass';
    f.frequency.value = 2400 + Math.random() * 2200;
    env(c, g, t, 0.004, 0.07 + Math.random() * 0.06, 0.10 + Math.random() * 0.08);
    n.connect(f).connect(g).connect(master);
    n.start(t);
    n.stop(t + 0.2);
  }
}

/** A low room tone so the halls do not feel like dead silence. */
export function startBed() {
  const c = ac();
  if (!c || bed) return;
  const n = noise(c);
  n.loop = true;
  const f = c.createBiquadFilter();
  f.type = 'lowpass';
  f.frequency.value = 240;
  const g = c.createGain();
  g.gain.value = 0.035;
  // a slow swell keeps it from sounding like a flat hiss
  const lfo = c.createOscillator();
  const lfoGain = c.createGain();
  lfo.frequency.value = 0.06;
  lfoGain.gain.value = 0.016;
  lfo.connect(lfoGain).connect(g.gain);
  n.connect(f).connect(g).connect(master);
  n.start();
  lfo.start();
  bed = { n, lfo };
}

export function stopBed() {
  if (!bed) return;
  try { bed.n.stop(); bed.lfo.stop(); } catch { /* already stopped */ }
  bed = null;
}
