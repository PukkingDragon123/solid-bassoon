/**
 * Pointer- and tilt-driven parallax for the layered scene plates.
 *
 * Elements opt in with `data-depth`; the number is how far they travel
 * relative to the frame, so the sky barely moves and the near plate swings.
 */

const reduceMotion =
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

const MAX_SHIFT = 26; // px at depth 1

export class Parallax {
  constructor(root) {
    this.root = root;
    this.items = [...root.querySelectorAll('[data-depth]')].map((el) => ({
      el,
      depth: parseFloat(el.dataset.depth) || 0,
      // Read whatever transform the stylesheet already applies and keep it as
      // the base.  Guessing from the class name shifted full-width plates by
      // half their width, which put a foreground pillar across mid-screen.
      baseTransform: (() => {
        const t = getComputedStyle(el).transform;
        return t && t !== 'none' ? `${t} ` : '';
      })(),
    }));
    this.tx = 0;
    this.ty = 0;
    this.cx = 0;
    this.cy = 0;
    this.active = false;
    this._pointer = this.onPointer.bind(this);
    this._orient = this.onOrient.bind(this);
    this._frame = this.frame.bind(this);
  }

  start() {
    if (this.active || reduceMotion) return;
    this.active = true;
    window.addEventListener('pointermove', this._pointer, { passive: true });
    window.addEventListener('deviceorientation', this._orient, { passive: true });
    requestAnimationFrame(this._frame);
  }

  stop() {
    this.active = false;
    window.removeEventListener('pointermove', this._pointer);
    window.removeEventListener('deviceorientation', this._orient);
  }

  onPointer(e) {
    this.tx = (e.clientX / window.innerWidth - 0.5) * 2;
    this.ty = (e.clientY / window.innerHeight - 0.5) * 2;
  }

  onOrient(e) {
    if (e.gamma == null || e.beta == null) return;
    // gamma is left/right tilt, beta front/back; clamp so it cannot fly off
    this.tx = Math.max(-1, Math.min(1, e.gamma / 34));
    this.ty = Math.max(-1, Math.min(1, (e.beta - 45) / 40));
  }

  frame() {
    if (!this.active) return;
    // ease toward the target so tilt jitter does not shake the whole scene
    this.cx += (this.tx - this.cx) * 0.075;
    this.cy += (this.ty - this.cy) * 0.075;
    for (const it of this.items) {
      const x = -this.cx * MAX_SHIFT * it.depth;
      const y = -this.cy * MAX_SHIFT * it.depth * 0.6;
      it.el.style.transform = `${it.baseTransform} translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0)`;
    }
    requestAnimationFrame(this._frame);
  }
}
