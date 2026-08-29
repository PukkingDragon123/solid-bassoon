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
