/**
 * ฉาก ๔ · ตู้ใบเซียมซี — the numbered drawers, and the slip coming out.
 */

import * as audio from '../audio.js';
import * as haptics from '../haptics.js';
import { go } from '../router.js';
import { state } from '../state.js';
import { FORTUNES, toThaiNumber } from '../data/fortunes.js';

export function createDrawer() {
  const el = document.getElementById('scene-drawer');
  const grid = document.getElementById('drawer-grid');
  const slip = document.getElementById('slip-fly');
  const peek = document.getElementById('slip-peek');
  const caption = document.getElementById('drawer-caption');
  const openBtn = document.getElementById('open-slip');
  let timers = [];

  // one cell per slip, laid over the rendered cabinet
  FORTUNES.forEach((f) => {
    const cell = document.createElement('div');
    cell.className = 'drawer-cell';
    cell.dataset.n = String(f.n);
    cell.setAttribute('role', 'listitem');
    const front = document.createElement('div');
    front.className = 'drawer-front';
    front.textContent = toThaiNumber(f.n);
    cell.appendChild(front);
    grid.appendChild(cell);
  });

  openBtn.addEventListener('click', () => {
    audio.paperRustle();
    haptics.tap();
    go('reading');
  });
  slip.addEventListener('click', () => { if (!openBtn.hidden) openBtn.click(); });

  return {
    el,
    enter() {
      const f = state.fortune;
      if (!f) { go('gate'); return; }
      caption.textContent = `กำลังหยิบใบที่ ${toThaiNumber(f.n)}…`;
      peek.textContent = toThaiNumber(f.n);

      const cell = grid.querySelector(`[data-n="${f.n}"]`);
      timers.push(
        setTimeout(() => {
          cell?.classList.add('open');
          audio.clack(0.45);
          haptics.tap();
        }, 620),
      );
      timers.push(
        setTimeout(() => {
          // fly the slip from its drawer to the middle of the frame
          if (cell) {
            const r = cell.getBoundingClientRect();
            slip.style.left = `${r.left + r.width / 2}px`;
            slip.style.top = `${r.top + r.height / 2}px`;
          }
          slip.hidden = false;
          audio.paperRustle();
          requestAnimationFrame(() => {
            slip.style.left = '50%';
            slip.style.top = '50%';
            slip.classList.add('up');
          });
        }, 1150),
      );
      timers.push(
        setTimeout(() => {
          caption.textContent = `ใบที่ ${toThaiNumber(f.n)} · ${f.title}`;
          openBtn.hidden = false;
          audio.chime();
        }, 2200),
      );
    },
    exit() {
      timers.forEach(clearTimeout);
      timers = [];
    },
    reset() {
      grid.querySelectorAll('.drawer-cell.open').forEach((c) => c.classList.remove('open'));
      slip.hidden = true;
      slip.classList.remove('up');
      slip.style.left = '50%';
      slip.style.top = '50%';
      openBtn.hidden = true;
      caption.textContent = 'กำลังหยิบใบเซียมซี…';
    },
  };
}
