/** Warm the image cache before the first scene, with honest progress. */

/** Portrait phones load the tall plates; everything else the wide ones. */
export const isPortrait =
  typeof matchMedia === 'function' && matchMedia('(max-aspect-ratio: 3 / 4)').matches;

const P = isPortrait ? '-p' : '';

export const ASSETS = [
  `assets/scenes/gate-sky${P}.png`,
  `assets/scenes/gate-far${P}.png`,
  `assets/scenes/gate-mid${P}.png`,
  `assets/scenes/gate-near${P}.png`,
  `assets/scenes/hall-bg${P}.png`,
  'assets/scenes/hall-altar.png',
  'assets/scenes/hall-near.png',
  `assets/scenes/drawer-wall${P}.png`,
  'assets/props/buddha.png',
  'assets/props/censer.png',
  'assets/props/candle.png',
  'assets/props/incense.png',
  'assets/props/incense-lit.png',
  'assets/props/tube.png',
  'assets/props/stick.png',
  'assets/props/slip.png',
  'assets/props/lotus.png',
  'assets/props/kanok-corner.png',
  'assets/tex/paper.png',
  'assets/tex/grain.png',
  'assets/fx/smoke.png',
  'assets/fx/ember.png',
];

export function preload(urls, onProgress) {
  let done = 0;
  const total = urls.length;
  return Promise.all(
    urls.map(
      (src) =>
        new Promise((resolve) => {
          const img = new Image();
          const finish = () => {
            done += 1;
            onProgress?.(done / total, src);
            resolve(img);
          };
          img.onload = finish;
          // a missing asset must not wedge the loader
          img.onerror = finish;
          img.src = src;
        }),
    ),
  );
}
