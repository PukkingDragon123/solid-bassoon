/**
 * ฉาก ๓ · เขย่าเซียมซี — shake the tube until a stick works its way out.
 *
 * Energy comes from three sources that all feed the same meter: dragging
 * the tube, real device shaking, or just tapping.  When it fills, one
 * stick drops and its number is the reading.
 */

import { FX, dustSpec } from '../fx.js';
import * as audio from '../audio.js';
import * as haptics from '../haptics.js';
import { go } from '../router.js';
import { state, drawFortune } from '../state.js';
import { toThaiNumber } from '../data/fortunes.js';

const NEEDED = 100;
const DECAY = 22;          // energy bled off per second, so it takes real effort
const DRAG_GAIN = 0.30;    // energy per px of drag
const MOTION_GAIN = 1.5;

export function createShake() {
  const el = document.getElementById('scene-shake');
  const fx = new FX(document.getElementById('fx-shake'));
  const wrap = document.getElementById('tube-wrap');
  const fill = document.getElementById('shake-fill');
  const caption = document.getElementById('shake-caption');
  const stick = document.getElementById('falling-stick');
  const numEl = document.getElementById('stick-number');
  const motionBtn = document.getElementById('motion-btn');

  let energy = 0;
  let dropped = false;
  let dragging = false;
  let lastY = 0;
  let lastX = 0;
  let raf = 0;
  let lastT = 0;
  let lastRattle = 0;
  let motionOn = false;
  let lastAcc = null;

  const addEnergy = (amount) => {
    if (dropped) return;
    energy = Math.min(NEEDED, energy + amount);
    const pct = energy / NEEDED;
    fill.style.width = `${pct * 100}%`;

    const now = performance.now();
    if (now - lastRattle > 110 - pct * 55) {
      lastRattle = now;
      audio.rattle(0.4 + pct);
      haptics.shake(0.3 + pct * 0.7);
    }
    // the tube leans harder the more it is worked
    const lean = (Math.random() - 0.5) * (6 + pct * 16);
    wrap.style.transform = `rotate(${lean.toFixed(1)}deg) translateY(${(-pct * 8).toFixed(1)}px)`;

    if (energy >= NEEDED) drop();
  };

  function tick(t) {
    const dt = Math.min((t - lastT) / 1000, 0.06);
    lastT = t;
    if (!dropped && energy > 0) {
      energy = Math.max(0, energy - DECAY * dt);
      fill.style.width = `${(energy / NEEDED) * 100}%`;
    }
    raf = requestAnimationFrame(tick);
  }

  // ── drag ────────────────────────────────────────────────────
  wrap.addEventListener('pointerdown', (e) => {
    if (dropped) return;
    dragging = true;
    lastY = e.clientY;
    lastX = e.clientX;
    wrap.classList.remove('idle');
    wrap.setPointerCapture?.(e.pointerId);
    audio.unlock();
  });
  wrap.addEventListener('pointermove', (e) => {
    if (!dragging || dropped) return;
    const d = Math.abs(e.clientY - lastY) + Math.abs(e.clientX - lastX) * 0.5;
    lastY = e.clientY;
    lastX = e.clientX;
    if (d > 1.5) addEnergy(d * DRAG_GAIN);
  });
  const endDrag = () => {
    dragging = false;
    if (!dropped) wrap.style.transform = '';
  };
  wrap.addEventListener('pointerup', endDrag);
  wrap.addEventListener('pointercancel', endDrag);
  wrap.addEventListener('click', () => { if (!dropped) addEnergy(9); });

  // ── real device motion ──────────────────────────────────────
  function onMotion(e) {
    const a = e.accelerationIncludingGravity;
    if (!a || a.x == null) return;
    if (lastAcc) {
      const d = Math.abs(a.x - lastAcc.x) + Math.abs(a.y - lastAcc.y) + Math.abs(a.z - lastAcc.z);
      if (d > 3) addEnergy(Math.min(d, 30) * MOTION_GAIN);
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

  // ── the drop ────────────────────────────────────────────────
  function drop() {
    dropped = true;
    const fortune = drawFortune();
    state.fortune = fortune;

    wrap.style.transform = 'rotate(28deg) translateY(-6px)';
    wrap.classList.remove('idle');
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
      raf = requestAnimationFrame(tick);
      wrap.classList.add('idle');
      if (!motionOn && window.DeviceMotionEvent) motionBtn.hidden = false;
    },
    exit() {
      fx.stop();
      cancelAnimationFrame(raf);
    },
    reset() {
      energy = 0;
      dropped = false;
      lastAcc = null;
      fill.style.width = '0%';
      wrap.style.transform = '';
      wrap.classList.add('idle');
      stick.hidden = true;
      stick.getAnimations().forEach((a) => a.cancel());
      numEl.hidden = true;
      numEl.classList.remove('show');
      caption.textContent = 'เขย่ากระบอก จนกว่าไม้เซียมซีจะหล่นออกมา';
    },
  };
}
