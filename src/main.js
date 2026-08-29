/** ศาลาเซียมซี — bootstrap: preload, wire the scenes, open the gate. */

import { preload, ASSETS } from './preload.js';
import { loadSprites } from './fx.js';
import { register, go, currentScene, toast } from './router.js';
import { createGate } from './scenes/gate.js';
import { createShrine } from './scenes/shrine.js';
import { createShake } from './scenes/shake.js';
import { createDrawer } from './scenes/drawer.js';
import { createReading } from './scenes/reading.js';
import * as audio from './audio.js';
import * as haptics from './haptics.js';
import { prefs, savePrefs, getHistory, formatDate, resetRitual, lastDrawToday } from './state.js';
import { LEVELS, toThaiNumber } from './data/fortunes.js';

const loader = document.getElementById('loader');
const loaderFg = loader.querySelector('.lr-fg');
const loaderPct = loader.querySelector('.loader-pct');

function setProgress(p) {
  loaderFg.style.strokeDashoffset = String(327 * (1 - p));
  loaderPct.textContent = `${Math.round(p * 100)}%`;
}

const scenes = {};

async function boot() {
  await Promise.all([
    preload(ASSETS, setProgress),
    loadSprites({ smoke: 'assets/fx/smoke.png', ember: 'assets/fx/ember.png' }),
  ]);

  scenes.gate = createGate();
  scenes.shrine = createShrine();
  scenes.shake = createShake();
  scenes.drawer = createDrawer();
  scenes.reading = createReading();
  Object.entries(scenes).forEach(([name, scene]) => register(name, scene));

  wireChrome();

  setProgress(1);
  loader.classList.add('done');
  setTimeout(() => { loader.hidden = true; }, 800);
  go('gate');
}

function wireChrome() {
  const soundBtn = document.getElementById('sound-btn');
  const homeBtn = document.getElementById('home-btn');
  const historyModal = document.getElementById('history-modal');
  const historyList = document.getElementById('history-list');

  // ── sound ────────────────────────────────────────────────
  audio.setEnabled(prefs.sound);
  haptics.setEnabled(prefs.sound);
  soundBtn.setAttribute('aria-pressed', String(prefs.sound));
  soundBtn.textContent = prefs.sound ? '♪' : '♪̸';
  soundBtn.addEventListener('click', () => {
    prefs.sound = !prefs.sound;
    savePrefs();
    audio.unlock();
    audio.setEnabled(prefs.sound);
    haptics.setEnabled(prefs.sound);
    soundBtn.setAttribute('aria-pressed', String(prefs.sound));
    soundBtn.textContent = prefs.sound ? '♪' : '♪̸';
    if (prefs.sound) { audio.startBed(); audio.chime(); }
  });

  // ── home ─────────────────────────────────────────────────
  homeBtn.addEventListener('click', restart);
  window.addEventListener('sala:restart', restart);

  function restart() {
    resetRitual();
    scenes.shrine.reset?.();
    scenes.shake.reset?.();
    scenes.drawer.reset?.();
    go('gate');
  }

  // show the home button once we are past the entrance
  const observer = new MutationObserver(() => {
    homeBtn.hidden = currentScene() === 'gate' || currentScene() == null;
  });
  document.querySelectorAll('.scene').forEach((s) => observer.observe(s, { attributes: true, attributeFilter: ['class', 'hidden'] }));

  // ── history ──────────────────────────────────────────────
  const openHistory = () => {
    const items = getHistory();
    historyList.innerHTML = items.length
      ? items
          .map(
            (h, i) => `
        <button class="history-item" data-i="${i}" data-n="${h.n}">
          <span class="history-num">${toThaiNumber(h.n)}</span>
          <span>
            <span class="history-title">${h.title}</span>
            <span class="history-meta">${formatDate(h.at)}${h.wish ? ` · ${h.wish.slice(0, 28)}` : ''}</span>
          </span>
          <span class="history-level" style="color:${LEVELS[h.level]?.tone ?? '#e8b24a'}">${LEVELS[h.level]?.th ?? ''}</span>
        </button>`,
          )
          .join('')
      : '<p class="history-empty">ยังไม่เคยเสี่ยงเซียมซี<br>เข้าวัดแล้วลองเสี่ยงดูสักใบ</p>';
    historyModal.hidden = false;
  };

  document.querySelectorAll('[data-action="history"]').forEach((b) => b.addEventListener('click', openHistory));
  document.querySelector('[data-action="close-history"]').addEventListener('click', () => { historyModal.hidden = true; });
  historyModal.addEventListener('click', (e) => { if (e.target === historyModal) historyModal.hidden = true; });

  historyList.addEventListener('click', (e) => {
    const item = e.target.closest('.history-item');
    if (!item) return;
    const entry = getHistory()[Number(item.dataset.i)];
    historyModal.hidden = true;
    go('reading', { fortune: Number(item.dataset.n), history: entry });
  });

  // ── gentle nudge: tradition says one slip a day ──────────
  document.querySelector('[data-action="enter"]').addEventListener('click', () => {
    const today = lastDrawToday();
    if (today) {
      setTimeout(
        () => toast(`วันนี้เสี่ยงไปแล้ว ๑ ใบ (ใบที่ ${toThaiNumber(today.n)}) — เสี่ยงอีกได้ แต่โบราณว่าให้เชื่อใบแรก`, 4200),
        1600,
      );
    }
  }, { capture: true });

  // the first gesture anywhere is what lets the audio context start
  const kick = () => { audio.unlock(); window.removeEventListener('pointerdown', kick); };
  window.addEventListener('pointerdown', kick);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !historyModal.hidden) historyModal.hidden = true;
  });
}

boot().catch((err) => {
  console.error(err);
  loader.querySelector('.loader-text').textContent = 'เปิดแอปไม่สำเร็จ — ลองรีเฟรชหน้าอีกครั้ง';
});
