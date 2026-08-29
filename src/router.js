/** Scene switching: cross-fades, and gives each scene an enter/exit hook. */

const scenes = new Map();
let current = null;
let busy = false;

export function register(name, scene) {
  scenes.set(name, scene);
}

export function currentScene() {
  return current;
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

export async function go(name, opts = {}) {
  if (busy || name === current) return;
  const next = scenes.get(name);
  if (!next) return;
  busy = true;

  const prev = scenes.get(current);
  if (prev) {
    prev.el.classList.remove('active');
    prev.el.classList.add('leaving');
    await wait(opts.fadeOut ?? 620);
    prev.exit?.();
    prev.el.hidden = true;
    prev.el.classList.remove('leaving');
  }

  // three rings expanding out of the centre carry the eye across the cut —
  // but not on the very first scene, which has nothing to cut away from
  if (prev && opts.ripple !== false) {
    const cx = window.innerWidth / 2;
    const cy = window.innerHeight / 2;
    const big = Math.max(window.innerWidth, window.innerHeight) * 1.5;
    ripple(cx, cy, { size: big });
    ripple(cx, cy, { size: big * 0.72, delay: 130, soft: true });
    ripple(cx, cy, { size: big * 0.5, delay: 260, soft: true });
  }

  next.el.hidden = false;
  // one frame with the element laid out but still transparent, so the
  // browser has something to transition *from*
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  next.el.classList.add('active');
  current = name;
  next.enter?.(opts);
  busy = false;
}

export function flash() {
  const el = document.getElementById('flash');
  if (!el) return;
  el.classList.remove('fire');
  void el.offsetWidth; // restart the animation
  el.classList.add('fire');
}

/**
 * A ring of light spreading from a point.  Used both for the cut between
 * scenes and as feedback for a touch anywhere in the hall.
 */
export function ripple(x, y, { size = 460, soft = false, delay = 0 } = {}) {
  const el = document.createElement('div');
  el.className = soft ? 'zen-ripple soft' : 'zen-ripple';
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.style.width = `${size}px`;
  el.style.height = `${size}px`;
  if (delay) el.style.animationDelay = `${delay}ms`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1600 + delay);
}

/** A word that floats up from a point on screen and fades. */
export function floatWord(text, x, y) {
  const el = document.createElement('div');
  el.className = 'float-word';
  el.textContent = text;
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1600);
}

export function toast(message, ms = 2600) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => {
    el.classList.add('out');
    setTimeout(() => el.remove(), 450);
  }, ms);
}
