/**
 * ฉาก ๕ · คำทำนาย — the slip, typeset for reading, and saveable as an image.
 */

import * as audio from '../audio.js';
import * as haptics from '../haptics.js';
import { go, toast } from '../router.js';
import { state, addHistory, formatDate } from '../state.js';
import { LEVELS, ASPECT_LABELS, toThaiNumber, getFortune } from '../data/fortunes.js';

const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

export function renderSheet(fortune, { name, wish, at } = {}) {
  const lv = LEVELS[fortune.level];
  const aspects = Object.entries(ASPECT_LABELS)
    .map(
      ([key, meta]) => `
      <div class="aspect">
        <div class="aspect-icon">${meta.icon}</div>
        <div>
          <div class="aspect-label">${meta.th}</div>
          <div class="aspect-text">${esc(fortune.aspects[key])}</div>
        </div>
      </div>`,
    )
    .join('');

  const echo =
    name || wish
      ? `<div class="wish-echo">
           ${name ? `<b>ผู้เสี่ยงทาย:</b> ${esc(name)}<br>` : ''}
           ${wish ? `<b>คำอธิษฐาน:</b> ${esc(wish)}<br>` : ''}
           ${at ? `<b>วันที่เสี่ยง:</b> ${esc(formatDate(at))}` : ''}
         </div>`
      : '';

  return `
    <div class="sheet-rule"></div>
    <img class="reading-corner tl" src="assets/props/kanok-corner.png" alt="">
    <img class="reading-corner tr" src="assets/props/kanok-corner.png" alt="">
    <img class="reading-corner bl" src="assets/props/kanok-corner.png" alt="">
    <img class="reading-corner br" src="assets/props/kanok-corner.png" alt="">
    <header class="sheet-head">
      <div class="seal" data-level="${fortune.level}">${lv.seal}</div>
      <p class="sheet-kicker">ใบเซียมซี</p>
      <div class="sheet-number">${toThaiNumber(fortune.n)}<small>ที่ ${fortune.n} · ${lv.th}</small></div>
      <h1 class="sheet-title">${esc(fortune.title)}</h1>
    </header>
    <div class="verse"><p>${fortune.verse.map(esc).join('\n')}</p></div>
    <p class="summary">${esc(fortune.summary)}</p>
    <div class="aspects">${aspects}</div>
    <div class="charm">
      <h3>คำแนะนำ · แก้เคล็ด</h3>
      <p>${esc(fortune.advice)}</p>
      <div class="lucky">
        <span class="chip">สีมงคล <b>${esc(fortune.color)}</b></span>
        <span class="chip">เลขมงคล <b>${fortune.numbers.map(toThaiNumber).join(' · ')}</b></span>
      </div>
    </div>
    ${echo}
    <p class="disclaimer">เซียมซีนี้จัดทำขึ้นเพื่อความบันเทิงและเป็นกำลังใจ<br>โปรดใช้วิจารณญาณ และอย่าประมาทในการดำเนินชีวิต</p>
  `;
}

export function createReading() {
  const el = document.getElementById('scene-reading');
  const sheet = document.getElementById('reading-sheet');
  let shown = null;

  el.querySelector('[data-action="restart"]').addEventListener('click', () => {
    haptics.tap();
    window.dispatchEvent(new CustomEvent('sala:restart'));
  });

  el.querySelector('[data-action="save-image"]').addEventListener('click', async () => {
    haptics.tap();
    try {
      const blob = await renderCard(shown ?? state.fortune, state);
      const file = new File([blob], `siamsee-${(shown ?? state.fortune).n}.png`, { type: 'image/png' });
      if (navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: 'ใบเซียมซีของฉัน' });
      } else {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = file.name;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
        toast('บันทึกใบเซียมซีแล้ว');
      }
    } catch {
      toast('บันทึกไม่สำเร็จ ลองใหม่อีกครั้ง');
    }
  });

  return {
    el,
    /** `opts.fortune` shows a past reading instead of the fresh one. */
    enter(opts = {}) {
      const f = opts.fortune ? getFortune(opts.fortune) : state.fortune;
      if (!f) { go('gate'); return; }
      shown = f;
      const meta = opts.history ?? { name: state.name, wish: state.wish, at: new Date().toISOString() };
      sheet.innerHTML = renderSheet(f, meta);
      el.scrollTop = 0;
      audio.paperRustle();
      setTimeout(() => audio.bell(), 400);
      haptics.success();

      if (!opts.fortune) {
        addHistory({ n: f.n, level: f.level, title: f.title, name: state.name, wish: state.wish, at: meta.at });
      }
    },
    exit() {},
  };
}

/* ────────────────────────────────────────────────────────────
   A shareable 1080×1920 card, drawn straight onto a canvas so
   there is no html-to-image dependency to ship.
   ──────────────────────────────────────────────────────────── */

const loadImage = (src) =>
  new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });

function wrapText(ctx, text, maxWidth) {
  // Thai has no inter-word spaces, so break on whatever fits — measuring
  // character by character is the only reliable option here.
  const lines = [];
  let line = '';
  for (const ch of text) {
    if (ch === '\n') { lines.push(line); line = ''; continue; }
    const test = line + ch;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = ch;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

export async function renderCard(fortune, ctxState = {}) {
  const W = 1080;
  const H = 1920;
  const c = document.createElement('canvas');
  c.width = W;
  c.height = H;
  const ctx = c.getContext('2d');
  const lv = LEVELS[fortune.level];

  const [paper, corner] = await Promise.all([
    loadImage('assets/tex/paper.png'),
    loadImage('assets/props/kanok-corner.png'),
  ]);

  // ground
  ctx.fillStyle = '#160b06';
  ctx.fillRect(0, 0, W, H);

  const M = 56;
  const sx = M;
  const sy = M;
  const sw = W - M * 2;
  const sh = H - M * 2;

  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,.7)';
  ctx.shadowBlur = 60;
  ctx.shadowOffsetY = 18;
  ctx.fillStyle = '#f6ecd6';
  ctx.fillRect(sx, sy, sw, sh);
  ctx.restore();

  if (paper) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(sx, sy, sw, sh);
    ctx.clip();
    ctx.globalAlpha = 0.85;
    for (let y = sy; y < sy + sh; y += 340) {
      for (let x = sx; x < sx + sw; x += 340) ctx.drawImage(paper, x, y, 340, 340);
    }
    ctx.restore();
  }

  // red rules
  ctx.strokeStyle = 'rgba(168,42,32,.6)';
  ctx.lineWidth = 3;
  ctx.strokeRect(sx + 22, sy + 22, sw - 44, sh - 44);
  ctx.strokeStyle = 'rgba(168,42,32,.34)';
  ctx.lineWidth = 1.5;
  ctx.strokeRect(sx + 32, sy + 32, sw - 64, sh - 64);

  if (corner) {
    const cs = 120;
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.drawImage(corner, sx + 34, sy + 34, cs, cs);
    ctx.save(); ctx.translate(sx + sw - 34, sy + 34); ctx.scale(-1, 1); ctx.drawImage(corner, 0, 0, cs, cs); ctx.restore();
    ctx.save(); ctx.translate(sx + 34, sy + sh - 34); ctx.scale(1, -1); ctx.drawImage(corner, 0, 0, cs, cs); ctx.restore();
    ctx.save(); ctx.translate(sx + sw - 34, sy + sh - 34); ctx.scale(-1, -1); ctx.drawImage(corner, 0, 0, cs, cs); ctx.restore();
    ctx.restore();
  }

  const cx = W / 2;
  let y = sy + 150;
  const display = "600 62px 'Noto Serif Thai', 'Sarabun', serif";
  const body = "400 30px 'Noto Sans Thai', 'Sarabun', sans-serif";

  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(168,42,32,.85)';
  ctx.font = "400 24px 'Noto Sans Thai', sans-serif";
  ctx.fillText('ใ บ เ ซี ย ม ซี', cx, y);

  y += 120;
  ctx.fillStyle = '#a82a20';
  ctx.font = "700 150px 'Noto Serif Thai', serif";
  ctx.fillText(toThaiNumber(fortune.n), cx, y);

  y += 46;
  ctx.font = "400 26px 'Noto Sans Thai', sans-serif";
  ctx.fillStyle = 'rgba(90,40,20,.7)';
  ctx.fillText(`ที่ ${fortune.n} · ${lv.th}`, cx, y);

  y += 74;
  ctx.font = display;
  ctx.fillStyle = '#4a1c10';
  ctx.fillText(fortune.title, cx, y);

  // verse block
  y += 56;
  const vh = 40 + fortune.verse.length * 52;
  ctx.fillStyle = 'rgba(168,42,32,.055)';
  ctx.fillRect(sx + 70, y, sw - 140, vh);
  ctx.fillStyle = 'rgba(168,42,32,.5)';
  ctx.fillRect(sx + 70, y, 5, vh);
  ctx.fillRect(sx + sw - 75, y, 5, vh);
  ctx.font = "400 34px 'Noto Serif Thai', serif";
  ctx.fillStyle = '#3d1a0e';
  let vy = y + 62;
  for (const line of fortune.verse) {
    ctx.fillText(line.replace(/\s{2,}/g, '   '), cx, vy);
    vy += 52;
  }
  y += vh + 62;

  // summary
  ctx.textAlign = 'left';
  ctx.font = body;
  ctx.fillStyle = '#35200f';
  for (const line of wrapText(ctx, fortune.summary, sw - 150).slice(0, 9)) {
    ctx.fillText(line, sx + 75, y);
    y += 48;
  }

  // five of the seven headings — the last two would not fit legibly
  y += 22;
  for (const key of ['work', 'money', 'love', 'health', 'travel']) {
    ctx.font = "600 27px 'Noto Serif Thai', serif";
    ctx.fillStyle = '#8e2318';
    ctx.fillText(ASPECT_LABELS[key].th, sx + 75, y);
    y += 42;
    ctx.font = "400 27px 'Noto Sans Thai', sans-serif";
    ctx.fillStyle = '#3a2412';
    for (const line of wrapText(ctx, fortune.aspects[key], sw - 150).slice(0, 2)) {
      ctx.fillText(line, sx + 75, y);
      y += 38;
    }
    y += 10;
  }

  // charm + lucky
  y += 8;
  ctx.font = "600 27px 'Noto Serif Thai', serif";
  ctx.fillStyle = '#8e2318';
  ctx.fillText('คำแนะนำ', sx + 75, y);
  y += 42;
  ctx.font = "400 27px 'Noto Sans Thai', sans-serif";
  ctx.fillStyle = '#3a2412';
  for (const line of wrapText(ctx, fortune.advice, sw - 150).slice(0, 3)) {
    ctx.fillText(line, sx + 75, y);
    y += 40;
  }
  y += 20;
  ctx.fillStyle = '#6a2010';
  ctx.font = "400 26px 'Noto Serif Thai', serif";
  ctx.fillText(`สีมงคล ${fortune.color}   ·   เลขมงคล ${fortune.numbers.map(toThaiNumber).join(' ')}`, sx + 75, y);

  if (ctxState.name) {
    y += 46;
    ctx.fillStyle = 'rgba(58,36,18,.75)';
    ctx.font = "400 24px 'Noto Sans Thai', sans-serif";
    ctx.fillText(`ผู้เสี่ยงทาย: ${ctxState.name}`, sx + 75, y);
  }

  // seal
  ctx.save();
  ctx.translate(sx + sw - 130, sy + 128);
  ctx.rotate((-13 * Math.PI) / 180);
  const sealColor = { excellent: '#b8860b', good: '#2e7d5b', fair: '#46567f', caution: '#a8482c' }[fortune.level];
  ctx.strokeStyle = sealColor;
  ctx.fillStyle = sealColor;
  ctx.globalAlpha = 0.85;
  ctx.lineWidth = 4;
  ctx.strokeRect(-56, -56, 112, 112);
  ctx.lineWidth = 1.6;
  ctx.strokeRect(-48, -48, 96, 96);
  ctx.textAlign = 'center';
  ctx.font = "700 30px 'Noto Serif Thai', serif";
  ctx.fillText(lv.seal, 0, 12);
  ctx.restore();

  // footer
  ctx.textAlign = 'center';
  ctx.globalAlpha = 0.65;
  ctx.fillStyle = 'rgba(90,60,35,.9)';
  ctx.font = "400 22px 'Noto Sans Thai', sans-serif";
  ctx.fillText('ศาลาเซียมซี · เพื่อความบันเทิงและเป็นกำลังใจ', cx, sy + sh - 60);
  ctx.globalAlpha = 1;

  return new Promise((resolve, reject) => {
    c.toBlob((b) => (b ? resolve(b) : reject(new Error('toBlob failed'))), 'image/png');
  });
}
