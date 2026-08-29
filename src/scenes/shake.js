/**
 * ฉาก ๓ · เขย่าเซียมซี — shake the tube until a stick works its way out.
 *
 * Energy comes from three sources that all feed the same meter: dragging
 * the tube, real device shaking, or just tapping.  When it fills, one
 * stick drops and its number is the reading.
 */

import { FX, dustSpec, emberSpec } from '../fx.js';
import * as audio from '../audio.js';
import * as haptics from '../haptics.js';
import { go, ripple } from '../router.js';
import { state, drawFortune } from '../state.js';
import { toThaiNumber } from '../data/fortunes.js';

// what the meter says as the energy climbs — silence for eight seconds of
// shaking feels like the app has stopped listening
const MILESTONES = [
  [0.00, ''],
  [0.22, 'เขย่าต่อ… ไม้เริ่มขยับแล้ว'],
  [0.50, 'ใกล้แล้ว อย่าเพิ่งหยุด'],
  [0.78, 'อีกนิดเดียว!'],
];

const NEEDED = 100;
const DECAY = 14;          // energy bled off per second, so it takes real effort

// The tube is a damped torsional spring; the stick bundle inside is a second,
// looser spring chasing it.  That lag is what makes the shake feel like it is
// moving real mass instead of playing a canned animation.
const K = 165;             // tube stiffness      (1/s²)
const C = 4.4;             // tube damping
const SK = 62;             // bundle stiffness — deliberately slack
const SC = 3.0;            // bundle damping
const STROKE_MIN = 240;    // reversal speed that counts as a real shake
const MAX_V = 1500;

export function createShake() {
  const el = document.getElementById('scene-shake');
  const fx = new FX(document.getElementById('fx-shake'));
  const wrap = document.getElementById('tube-wrap');
  const fill = document.getElementById('shake-fill');
  const caption = document.getElementById('shake-caption');
  const stick = document.getElementById('falling-stick');
  const numEl = document.getElementById('stick-number');
  const motionBtn = document.getElementById('motion-btn');
  const label = document.getElementById('shake-label');
  const firefly = document.getElementById('firefly');
  const stage = document.getElementById('tube-stage');
  const sticks = document.getElementById('tube-sticks');
  const glow = document.getElementById('tube-glow');

  let energy = 0;
  let dropped = false;
  let dragging = false;
  let lastY = 0;
  let lastX = 0;
  let raf = 0;
  let lastT = 0;

  // simulation state: tube angle/bob, then the bundle trailing behind
  let ang = 0, angV = 0, bob = 0, bobV = 0;
  let sAng = 0, sAngV = 0, sBob = 0, sBobV = 0;
  let peak = 0, lastSign = 0, idleT = 0;
  let motionOn = false;
  let lastAcc = null;
  let fireflyTimer = 0;
  let fireflyAway = false;

  const mouthPoint = () => {
    const r = wrap.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height * 0.33 };
  };

  /** One completed shake stroke: the moment the tube reverses direction. */
  function stroke(power) {
    if (dropped) return;
    // tuned against the decay so a vigorous shake takes roughly eight seconds
    // rather than four strokes
    const gain = Math.min(12, power / 70);
    energy = Math.min(NEEDED, energy + gain);
    const pct = energy / NEEDED;

    audio.clack(0.45 + Math.min(1, power / 900) * 0.55);
    if (Math.random() < 0.6) audio.rattle(0.3 + pct * 0.8);
    haptics.shake(0.3 + Math.min(1, power / 1100) * 0.7);
    fx.burst(emberSpec(mouthPoint), 2 + Math.round(pct * 5));
    if (power > 520) {
      const m = mouthPoint();
      ripple(m.x, m.y, { size: 150 + pct * 260, soft: pct < 0.5 });
    }

    const at = MILESTONES.filter(([x]) => pct >= x).pop();
    if (at && label.textContent !== at[1]) label.textContent = at[1];
    if (pct > 0.06 && !fireflyAway) scareFirefly();
    if (energy >= NEEDED) drop();
  }

  function tick(t) {
    const dt = Math.min((t - lastT) / 1000, 0.04);
    lastT = t;
    idleT += dt;

    if (!dropped) {
      // a barely-there sway so a tube nobody is touching still looks alive
      if (!dragging && energy < 3) angV += Math.sin(idleT * 1.15) * 26 * dt;

      angV += (-K * ang - C * angV) * dt;
      ang += angV * dt;
      bobV += (-K * 1.5 * bob - C * bobV) * dt;
      bob += bobV * dt;

      // the bundle chases the tube, always a beat behind
      sAngV += (SK * (ang - sAng) - SC * sAngV) * dt;
      sAng += sAngV * dt;
      sBobV += (SK * 1.15 * (bob - sBob) - SC * sBobV) * dt;
      sBob += sBobV * dt;

      angV = Math.max(-MAX_V, Math.min(MAX_V, angV));
      bobV = Math.max(-MAX_V, Math.min(MAX_V, bobV));
      ang = Math.max(-34, Math.min(34, ang));
      bob = Math.max(-70, Math.min(70, bob));

      // a stroke is a reversal, not a pixel count — you have to really shake it
      const sv = angV + bobV * 0.62;
      peak = Math.max(peak, Math.abs(sv));
      const sign = Math.sign(sv);
      if (sign !== 0) {
        if (lastSign !== 0 && sign !== lastSign && peak > STROKE_MIN) {
          stroke(peak);
          peak = 0;
        }
        lastSign = sign;
      }

      if (energy > 0) energy = Math.max(0, energy - DECAY * dt);
      const pct = energy / NEEDED;
      fill.style.width = `${pct * 100}%`;
      glow.style.opacity = String(pct * 0.85);

      wrap.style.transform = `rotate(${ang.toFixed(2)}deg) translateY(${bob.toFixed(1)}px)`;
      // relative to the wrap, so only the lag shows
      sticks.style.transform =
        `rotate(${((sAng - ang) * 0.85).toFixed(2)}deg) ` +
        `translateY(${((sBob - bob) * 0.9 - pct * 16).toFixed(1)}px)`;
    }
    raf = requestAnimationFrame(tick);
  }

  // ── drag: push the spring, do not fake the motion ───────────
  wrap.addEventListener('pointerdown', (e) => {
    if (dropped) return;
    ripple(e.clientX, e.clientY, { size: 190, soft: true });
    dragging = true;
    lastY = e.clientY;
    lastX = e.clientX;
    wrap.setPointerCapture?.(e.pointerId);
    audio.unlock();
  });
  wrap.addEventListener('pointermove', (e) => {
    if (!dragging || dropped) return;
    const dx = e.clientX - lastX;
    const dy = e.clientY - lastY;
    lastX = e.clientX;
    lastY = e.clientY;
    const r = wrap.getBoundingClientRect();
    const off = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    // sideways drag twists it; up-and-down drives the bob and, off-centre,
    // twists it too — the way a real tube behaves in one hand
    angV += dx * 3.2 + dy * 1.5 * off;
    bobV += dy * 7.5;
  });
  const endDrag = () => { dragging = false; };
  wrap.addEventListener('pointerup', endDrag);
  wrap.addEventListener('pointercancel', endDrag);
  wrap.addEventListener('click', () => {
    if (dropped) return;
    angV += (Math.random() > 0.5 ? 1 : -1) * 430;
    bobV -= 180;
  });

  // ── real device motion ──────────────────────────────────────
  function onMotion(e) {
    const a = e.accelerationIncludingGravity;
    if (!a || a.x == null) return;
    if (lastAcc) {
      const dx = a.x - lastAcc.x;
      const dy = a.y - lastAcc.y;
      if (Math.abs(dx) + Math.abs(dy) > 1.6) {
        angV += dx * 34;
        bobV -= dy * 40;
      }
    }
    lastAcc = { x: a.x, y: a.y, z: a.z };
  }

  function enableMotion() {
    const DM = window.DeviceMotionEvent;
    if (!DM) return;
    if (typeof DM.requestPermission === 'function') {
      DM.requestPermission()
        .then((res) => {
          if (res === 'granted') {
            window.addEventListener('devicemotion', onMotion);
            motionOn = true;
            motionBtn.hidden = true;
            caption.textContent = 'เขย่าเครื่องได้เลย — หรือจะลากกระบอกก็ได้';
          }
        })
        .catch(() => { /* the user declined; dragging still works */ });
    } else {
      window.addEventListener('devicemotion', onMotion);
      motionOn = true;
      motionBtn.hidden = true;
    }
  }
  motionBtn.addEventListener('click', enableMotion);

  // ── หิ่งห้อย: a firefly that keeps you company ───────────────
  function fireflyPerch() {
    const r = wrap.getBoundingClientRect();
    const s_ = stage.getBoundingClientRect();
    if (!r.width) return;
    // pick a spot on the tube's body, in stage-relative coordinates
    firefly.style.left = `${r.left - s_.left + r.width * (0.18 + Math.random() * 0.64)}px`;
    firefly.style.top = `${r.top - s_.top + r.height * (0.42 + Math.random() * 0.46)}px`;
  }

  function fireflyArrive(delay = 1400) {
    clearTimeout(fireflyTimer);
    fireflyTimer = setTimeout(() => {
      if (dropped) return;
      fireflyAway = false;
      firefly.hidden = false;
      firefly.classList.remove('away');
      fireflyPerch();
      wander();
    }, delay);
  }

  let wanderTimer = 0;
  function wander() {
    clearTimeout(wanderTimer);
    wanderTimer = setTimeout(() => {
      if (!fireflyAway && !dropped) {
        fireflyPerch();
        wander();
      }
    }, 2600 + Math.random() * 2400);
  }

  function scareFirefly(tapped = false) {
    if (fireflyAway || firefly.hidden) return;
    fireflyAway = true;
    clearTimeout(wanderTimer);
    const r = firefly.getBoundingClientRect();
    fx.burst(emberSpec(() => ({ x: r.left + r.width / 2, y: r.top + r.height / 2 })), tapped ? 14 : 6);
    if (tapped) { audio.chime(); haptics.light(); }
    firefly.classList.add('away');
    firefly.style.left = `${(Math.random() > 0.5 ? 1.15 : -0.15) * stage.clientWidth}px`;
    firefly.style.top = `${stage.clientHeight * (0.1 + Math.random() * 0.4)}px`;
    setTimeout(() => { firefly.hidden = true; }, 950);
    if (!dropped) fireflyArrive(4200 + Math.random() * 3600);
  }

  firefly.addEventListener('click', (e) => { e.stopPropagation(); scareFirefly(true); });

  // ── the drop ────────────────────────────────────────────────
  function drop() {
    dropped = true;
    clearTimeout(fireflyTimer);
    clearTimeout(wanderTimer);
    scareFirefly();
    label.textContent = '';
    const fortune = drawFortune();
    state.fortune = fortune;

    wrap.style.transform = 'rotate(26deg) translateY(-8px)';
    sticks.style.transform = 'rotate(-5deg) translateY(-18px)';
    glow.style.opacity = '0';
    caption.textContent = 'ไม้เซียมซีหล่นออกมาแล้ว';

    stick.hidden = false;
    stick.animate(
      [
        { transform: 'translate(-50%, -40%) rotate(24deg)', opacity: 0 },
        { transform: 'translate(-30%, 30%) rotate(64deg)', opacity: 1, offset: 0.45 },
        { transform: 'translate(-20%, 210%) rotate(104deg)', opacity: 1 },
      ],
      { duration: 950, easing: 'cubic-bezier(.4,0,.7,1)', fill: 'forwards' },
    );
    setTimeout(() => { audio.clack(1); haptics.knock(); }, 460);
    setTimeout(() => { audio.clack(0.6); }, 620);

    setTimeout(() => {
      numEl.textContent = toThaiNumber(fortune.n);
      numEl.hidden = false;
      requestAnimationFrame(() => numEl.classList.add('show'));
      audio.bell();
      haptics.success();
      caption.textContent = `ได้ใบที่ ${toThaiNumber(fortune.n)} — ${fortune.title}`;
    }, 1050);

    setTimeout(() => go('drawer'), 2600);
  }

  return {
    el,
    enter() {
      fx.clear();
      fx.emit(dustSpec(() => fx.w, () => fx.h, { rate: 1.4 }));
      fx.start();
      lastT = performance.now();
      idleT = 0;
      raf = requestAnimationFrame(tick);
      if (!motionOn && window.DeviceMotionEvent) motionBtn.hidden = false;
      if (!dropped) fireflyArrive(1600);
    },
    exit() {
      fx.stop();
      cancelAnimationFrame(raf);
      clearTimeout(fireflyTimer);
      clearTimeout(wanderTimer);
      firefly.hidden = true;
    },
    reset() {
      energy = 0;
      dropped = false;
      lastAcc = null;
      ang = angV = bob = bobV = 0;
      sAng = sAngV = sBob = sBobV = 0;
      peak = 0; lastSign = 0; idleT = 0;
      fill.style.width = '0%';
      wrap.style.transform = '';
      sticks.style.transform = '';
      glow.style.opacity = '0';
      stick.hidden = true;
      stick.getAnimations().forEach((a) => a.cancel());
      numEl.hidden = true;
      numEl.classList.remove('show');
      label.textContent = '';
      firefly.hidden = true;
      firefly.classList.remove('away');
      fireflyAway = false;
      caption.textContent = 'เขย่ากระบอก จนกว่าไม้เซียมซีจะหล่นออกมา';
    },
  };
}
