/** ฉาก ๑ · หน้าวัด — the entrance, and the invitation to come in. */

import { FX, fireflySpec, dustSpec } from '../fx.js';
import { Parallax } from '../parallax.js';
import * as audio from '../audio.js';
import * as haptics from '../haptics.js';
import { go, flash } from '../router.js';

export function createGate() {
  const el = document.getElementById('scene-gate');
  const fx = new FX(document.getElementById('fx-gate'));
  const parallax = new Parallax(el.querySelector('[data-parallax]'));

  el.querySelector('[data-action="enter"]').addEventListener('click', () => {
    audio.unlock();
    audio.startBed();
    audio.bell();
    haptics.knock();
    // walk through the door: push into the near plate, then wash to gold
    el.querySelectorAll('.layer').forEach((layer) => {
      const depth = parseFloat(layer.dataset.depth) || 0;
      layer.style.transition = 'transform 1.15s cubic-bezier(.5,0,.75,0), opacity .9s ease-in';
      layer.style.transform = `scale(${1 + depth * 0.55})`;
      if (depth >= 0.5) layer.style.opacity = '0';
    });
    el.querySelector('.gate-ui').style.opacity = '0';
    setTimeout(flash, 620);
    setTimeout(() => go('shrine'), 900);
  });

  return {
    el,
    enter() {
      fx.clear();
      fx.emit(fireflySpec(() => fx.w, () => fx.h, { rate: 0.9 }));
      fx.emit(dustSpec(() => fx.w, () => fx.h, { rate: 1.1 }));
      fx.start();
      parallax.start();
      // reset anything the transition left behind, in case we come back
      el.querySelectorAll('.layer').forEach((layer) => {
        layer.style.transition = '';
        layer.style.transform = '';
        layer.style.opacity = '';
      });
      el.querySelector('.gate-ui').style.opacity = '';
    },
    exit() {
      fx.stop();
      parallax.stop();
    },
  };
}
