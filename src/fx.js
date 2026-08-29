/**
 * Canvas particle layer — incense smoke, embers, dust and fireflies.
 *
 * One engine per canvas.  Emitters are declared once and keep producing;
 * bursts are one-shot.  Everything is DPR-aware and pauses when hidden.
 */

const SPRITES = {};

export function loadSprites(map) {
  return Promise.all(
    Object.entries(map).map(
      ([key, src]) =>
        new Promise((resolve) => {
          const img = new Image();
          img.onload = () => { SPRITES[key] = img; resolve(); };
          img.onerror = () => resolve();
          img.src = src;
        }),
    ),
  );
}

const reduceMotion =
  typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

export class FX {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.particles = [];
    this.emitters = [];
    this.running = false;
    this.last = 0;
    this.w = 0;
    this.h = 0;
    this._resize = this.resize.bind(this);
    this._frame = this.frame.bind(this);
    window.addEventListener('resize', this._resize);
    this.resize();
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const r = this.canvas.getBoundingClientRect();
    this.w = r.width || window.innerWidth;
    this.h = r.height || window.innerHeight;
    this.canvas.width = Math.round(this.w * dpr);
    this.canvas.height = Math.round(this.h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.last = performance.now();
    requestAnimationFrame(this._frame);
  }

  stop() {
    this.running = false;
  }

  clear() {
    this.particles.length = 0;
    this.emitters.length = 0;
    this.ctx.clearRect(0, 0, this.w, this.h);
  }

  destroy() {
    this.stop();
    window.removeEventListener('resize', this._resize);
  }

  /** Continuous source.  Returns a handle so callers can move or stop it. */
  emit(spec) {
    const e = { rate: 10, acc: 0, on: true, ...spec };
    this.emitters.push(e);
    return e;
  }

  remove(emitter) {
    const i = this.emitters.indexOf(emitter);
    if (i >= 0) this.emitters.splice(i, 1);
  }

  burst(spec, count) {
    for (let i = 0; i < count; i++) this.spawn(spec);
  }

  spawn(spec) {
    const p = spec.make();
    p.kind = spec.kind;
    p.age = 0;
    this.particles.push(p);
    // a hard cap keeps a long session from crawling on a weak phone
    if (this.particles.length > 460) this.particles.splice(0, this.particles.length - 460);
  }

  frame(now) {
    if (!this.running) return;
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;
    const { ctx } = this;
    ctx.clearRect(0, 0, this.w, this.h);

    for (const e of this.emitters) {
      if (!e.on) continue;
      e.acc += dt * e.rate;
      while (e.acc >= 1) {
        e.acc -= 1;
        this.spawn(e);
      }
    }

    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.age += dt;
      if (p.age >= p.life) {
        this.particles.splice(i, 1);
        continue;
      }
      p.update(p, dt);
      p.draw(ctx, p);
    }
    requestAnimationFrame(this._frame);
  }
}

// ── particle recipes ──────────────────────────────────────────

function drawSprite(ctx, p, key, tint) {
  const img = SPRITES[key];
  const t = p.age / p.life;
  const alpha = p.alpha(t);
  if (alpha <= 0.002) return;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.globalCompositeOperation = p.blend || 'source-over';
  ctx.translate(p.x, p.y);
  ctx.rotate(p.rot);
  const s = p.size * (p.grow ? 1 + t * p.grow : 1);
  if (img) {
    ctx.drawImage(img, -s / 2, -s / 2, s, s);
  } else {
    ctx.fillStyle = tint || '#fff';
    ctx.beginPath();
    ctx.arc(0, 0, s / 2, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

/** Incense smoke: rises, drifts on a slow sine, swells and thins. */
export function smokeSpec(getOrigin, opts = {}) {
  const scale = opts.scale ?? 1;
  return {
    kind: 'smoke',
    rate: reduceMotion ? 3 : (opts.rate ?? 9),
    make() {
      const o = getOrigin();
      const drift = (Math.random() - 0.5) * 26;
      const phase = Math.random() * Math.PI * 2;
      const rise = (48 + Math.random() * 42) * scale;
      return {
        x: o.x + (Math.random() - 0.5) * 12 * scale,
        y: o.y + (Math.random() - 0.5) * 6,
        vx: drift,
        vy: -rise,
        rot: Math.random() * Math.PI * 2,
        vr: (Math.random() - 0.5) * 0.5,
        size: (24 + Math.random() * 26) * scale,
        grow: 2.6,
        life: 3.2 + Math.random() * 2.4,
        blend: 'screen',
        alpha: (t) => (opts.opacity ?? 0.30) * Math.sin(Math.min(t, 1) * Math.PI) ** 0.8,
        update(p, dt) {
          p.age2 = (p.age2 ?? phase) + dt;
          // the sideways wander is what makes smoke read as smoke
          p.x += (p.vx + Math.sin(p.age2 * 1.5) * 17 * scale) * dt;
          p.y += p.vy * dt;
          p.vy *= 1 - 0.28 * dt;
          p.rot += p.vr * dt;
        },
        draw: (ctx, p) => drawSprite(ctx, p, 'smoke', '#d8d0c4'),
      };
    },
  };
}

/** Sparks flung off a freshly lit tip. */
export function emberSpec(getOrigin, opts = {}) {
  return {
    kind: 'ember',
    rate: opts.rate ?? 0,
    make() {
      const o = getOrigin();
      const a = -Math.PI / 2 + (Math.random() - 0.5) * 1.5;
      const sp = 40 + Math.random() * 120;
      return {
        x: o.x,
        y: o.y,
        vx: Math.cos(a) * sp,
        vy: Math.sin(a) * sp,
        rot: 0,
        size: 5 + Math.random() * 9,
        life: 0.7 + Math.random() * 1.1,
        blend: 'screen',
        alpha: (t) => (1 - t) ** 1.6,
        update(p, dt) {
          p.x += p.vx * dt;
          p.y += p.vy * dt;
          p.vy += 92 * dt;           // gravity pulls the spark back down
          p.vx *= 1 - 1.5 * dt;
        },
        draw: (ctx, p) => drawSprite(ctx, p, 'ember', '#ff9c3a'),
      };
    },
  };
}

/** Motes hanging in a shaft of light. */
export function dustSpec(w, h, opts = {}) {
  return {
    kind: 'dust',
    rate: reduceMotion ? 0.5 : (opts.rate ?? 2.2),
    make() {
      const phase = Math.random() * Math.PI * 2;
      return {
        x: Math.random() * w(),
        y: h() * (0.15 + Math.random() * 0.85),
        vx: (Math.random() - 0.5) * 9,
        vy: -3 - Math.random() * 9,
        rot: 0,
        size: 2 + Math.random() * 4,
        life: 7 + Math.random() * 7,
        blend: 'screen',
        alpha: (t) => 0.42 * Math.sin(Math.min(t, 1) * Math.PI),
        update(p, dt) {
          p.age2 = (p.age2 ?? phase) + dt;
          p.x += (p.vx + Math.sin(p.age2 * 0.7) * 6) * dt;
          p.y += p.vy * dt;
        },
        draw: (ctx, p) => drawSprite(ctx, p, 'ember', '#ffe3a3'),
      };
    },
  };
}

/** Slow blinking lights out in the temple grounds. */
export function fireflySpec(w, h, opts = {}) {
  return {
    kind: 'firefly',
    rate: reduceMotion ? 0.2 : (opts.rate ?? 0.8),
    make() {
      const phase = Math.random() * Math.PI * 2;
      const blink = 0.5 + Math.random() * 0.9;
      return {
        x: Math.random() * w(),
        y: h() * (0.45 + Math.random() * 0.55),
        vx: (Math.random() - 0.5) * 16,
        vy: (Math.random() - 0.5) * 10,
        rot: 0,
        size: 6 + Math.random() * 7,
        life: 8 + Math.random() * 8,
        blend: 'screen',
        alpha: (t) =>
          0.75 * Math.sin(Math.min(t, 1) * Math.PI) * (0.35 + 0.65 * Math.abs(Math.sin(t * 14 * blink))),
        update(p, dt) {
          p.age2 = (p.age2 ?? phase) + dt;
          p.x += (p.vx + Math.sin(p.age2 * 0.9) * 12) * dt;
          p.y += (p.vy + Math.cos(p.age2 * 0.7) * 8) * dt;
        },
        draw: (ctx, p) => drawSprite(ctx, p, 'ember', '#ffd06a'),
      };
    },
  };
}
