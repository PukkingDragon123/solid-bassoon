/**
 * ฉาก ๒ · วิหาร — the ritual, in order:
 * light the candle → light the incense from it → raise it and pray →
 * plant it in the censer → make the wish.
 */

import { FX, smokeSpec, emberSpec, dustSpec } from '../fx.js';
import { Parallax } from '../parallax.js';
import * as audio from '../audio.js';
import * as haptics from '../haptics.js';
import { go, flash } from '../router.js';
import { state } from '../state.js';

const PRAY_MS = 3400;

const CAPTIONS = {
  candle: 'แตะที่เทียนเพื่อจุด',
  incense: 'ลากธูปไปจ่อเปลวเทียน เพื่อจุดธูป',
  pray: 'กดค้างไว้ ยกธูปขึ้นจบเหนือหน้าผาก',
  plant: 'ลากธูปไปปักที่กระถาง',
  wish: 'เขียนคำอธิษฐาน แล้วน้อมจิตให้มั่น',
};

export function createShrine() {
  const el = document.getElementById('scene-shrine');
  const fx = new FX(document.getElementById('fx-shrine'));
  const parallax = new Parallax(el.querySelector('[data-parallax]'));

  const candle = el.querySelector('.hotspot-candle');
  const censerDrop = el.querySelector('[data-drop="censer"]');
  const hand = document.getElementById('incense-hand');
  const handImg = document.getElementById('incense-img');
  const caption = document.getElementById('shrine-caption');
  const prayRing = document.getElementById('pray-ring');
  const prayFg = prayRing.querySelector('.pr-fg');
  const chant = document.getElementById('chant');
  const wishPanel = document.getElementById('wish-panel');

  let step = 'candle';
  let handPos = { x: 0, y: 0 };
  let dragging = false;
  let candleSmoke = null;
  let censerSmoke = null;
  let prayStart = 0;
  let prayTimer = null;

  const setStep = (s) => {
    step = s;
    caption.textContent = CAPTIONS[s] ?? '';
    // re-trigger the caption's entrance animation
    caption.style.animation = 'none';
    void caption.offsetWidth;
    caption.style.animation = '';
  };

  const rectCenter = (node, fx_ = 0.5, fy = 0.5) => {
    const r = node.getBoundingClientRect();
    return { x: r.left + r.width * fx_, y: r.top + r.height * fy };
  };

  const flameOrigin = () => rectCenter(candle, 0.5, -0.06);
  const censerOrigin = () => rectCenter(el.querySelector('.prop-censer'), 0.5, 0.24);
  const handTipOrigin = () => ({ x: handPos.x, y: handPos.y - hand.offsetHeight * 0.40 });

  const moveHand = (x, y) => {
    handPos = { x, y };
    hand.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`;
  };

  // ── step 1: light the candle ────────────────────────────────
  candle.addEventListener('click', () => {
    if (state.candleLit) return;
    state.candleLit = true;
    candle.classList.add('lit', 'done');
    audio.matchStrike();
    haptics.tap();
    setTimeout(() => audio.whoosh(0.6), 180);
    fx.burst(emberSpec(flameOrigin), 14);
    candleSmoke = fx.emit(smokeSpec(flameOrigin, { rate: 2.2, scale: 0.5, opacity: 0.14 }));

    setTimeout(() => {
      hand.hidden = false;
      const r = el.getBoundingClientRect();
      moveHand(r.width * 0.22, r.height * 0.72);
      setStep('incense');
    }, 700);
  });

  // ── step 2 & 4: drag the incense ────────────────────────────
  const onDown = (e) => {
    if (hand.hidden || step === 'pray' || step === 'wish') return;
    const t = e.touches?.[0] ?? e;
    const r = hand.getBoundingClientRect();
    const inside =
      t.clientX > r.left - 44 && t.clientX < r.right + 44 && t.clientY > r.top - 44 && t.clientY < r.bottom + 44;
    if (!inside) return;
    dragging = true;
    hand.classList.add('grabbing');
    e.preventDefault();
  };

  const onMove = (e) => {
    if (!dragging) return;
    const t = e.touches?.[0] ?? e;
    moveHand(t.clientX, t.clientY);
    if (step === 'plant') {
      const c = censerOrigin();
      const near = Math.hypot(t.clientX - c.x, t.clientY - c.y) < 110;
      censerDrop.classList.toggle('armed', near);
    }
    e.preventDefault();
  };

  const onUp = () => {
    if (!dragging) return;
    dragging = false;
    hand.classList.remove('grabbing');
    censerDrop.classList.remove('armed');

    if (step === 'incense') {
      const f = flameOrigin();
      const tip = handTipOrigin();
      if (Math.hypot(tip.x - f.x, tip.y - f.y) < 130) lightIncense();
    } else if (step === 'plant') {
      const c = censerOrigin();
      if (Math.hypot(handPos.x - c.x, handPos.y - c.y) < 130) plantIncense();
    }
  };

  function lightIncense() {
    state.incenseLit = true;
    handImg.src = 'assets/props/incense-lit.png';
    hand.classList.add('lit');
    audio.whoosh(0.5);
    haptics.doubleTap();
    fx.burst(emberSpec(handTipOrigin), 18);
    fx.emit(smokeSpec(handTipOrigin, { rate: 7, scale: 0.72, opacity: 0.26 }));
    setStep('pray');
    prayRing.hidden = false;
  }

  function plantIncense() {
    state.incensePlanted = true;
    const c = censerOrigin();
    moveHand(c.x, c.y - hand.offsetHeight * 0.30);
    hand.style.opacity = '0.001';
    audio.clack(0.5);
    haptics.tap();
    censerSmoke = fx.emit(smokeSpec(censerOrigin, { rate: 9, scale: 0.95, opacity: 0.3 }));
    setTimeout(() => {
      setStep('wish');
      wishPanel.hidden = false;
      audio.chime();
    }, 700);
  }

  // ── step 3: hold to pray ────────────────────────────────────
  const startPray = (e) => {
    if (step !== 'pray' || prayTimer) return;
    e.preventDefault();
    prayStart = performance.now();
    chant.classList.add('on');
    const baseY = handPos.y;
    prayTimer = setInterval(() => {
      const t = Math.min((performance.now() - prayStart) / PRAY_MS, 1);
      prayFg.style.strokeDashoffset = String(339 * (1 - t));
      // the incense rises to the forehead as the prayer completes
      moveHand(handPos.x, baseY - t * 70);
      if (t >= 0.34 && t < 0.36) haptics.light();
      if (t >= 0.67 && t < 0.69) haptics.light();
      if (t >= 1) endPray(true);
    }, 40);
  };

  const cancelPray = () => {
    if (!prayTimer || step !== 'pray') return;
    endPray(false);
  };

  function endPray(complete) {
    clearInterval(prayTimer);
    prayTimer = null;
    if (complete) {
      state.prayed = true;
      audio.bell();
      haptics.success();
      prayRing.hidden = true;
      chant.classList.remove('on');
      setStep('plant');
    } else {
      prayFg.style.strokeDashoffset = '339';
      chant.classList.remove('on');
    }
  }

  el.addEventListener('pointerdown', (e) => {
    if (step === 'pray') startPray(e);
    else onDown(e);
  });
  window.addEventListener('pointermove', onMove, { passive: false });
  window.addEventListener('pointerup', () => { onUp(); cancelPray(); });
  window.addEventListener('pointercancel', () => { onUp(); cancelPray(); });

  // ── step 5: the wish ────────────────────────────────────────
  el.querySelector('[data-action="to-shake"]').addEventListener('click', () => {
    state.name = document.getElementById('wish-name').value.trim();
    state.wish = document.getElementById('wish-text').value.trim();
    audio.gong();
    haptics.knock();
    flash();
    go('shake');
  });

  return {
    el,
    enter() {
      fx.clear();
      fx.emit(dustSpec(() => fx.w, () => fx.h, { rate: 1.6 }));
      if (state.candleLit) candleSmoke = fx.emit(smokeSpec(flameOrigin, { rate: 2.2, scale: 0.5, opacity: 0.14 }));
      if (state.incensePlanted) censerSmoke = fx.emit(smokeSpec(censerOrigin, { rate: 9, scale: 0.95, opacity: 0.3 }));
      fx.start();
      parallax.start();
      if (!state.candleLit) setStep('candle');
    },
    exit() {
      fx.stop();
      parallax.stop();
    },
    reset() {
      fx.clear();
      candleSmoke = censerSmoke = null;
      candle.classList.remove('lit', 'done');
      hand.hidden = true;
      hand.classList.remove('lit');
      hand.style.opacity = '';
      handImg.src = 'assets/props/incense.png';
      prayRing.hidden = true;
      prayFg.style.strokeDashoffset = '339';
      wishPanel.hidden = true;
      setStep('candle');
    },
  };
}
