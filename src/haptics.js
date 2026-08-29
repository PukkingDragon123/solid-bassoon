/** Vibration, where the device offers it.  Silently does nothing elsewhere. */

let enabled = true;

export function setEnabled(on) {
  enabled = on;
}

function buzz(pattern) {
  if (!enabled) return;
  if (typeof navigator === 'undefined' || !navigator.vibrate) return;
  try { navigator.vibrate(pattern); } catch { /* blocked by the platform */ }
}

export const tap = () => buzz(12);
export const light = () => buzz(8);
export const knock = () => buzz([0, 26]);
export const doubleTap = () => buzz([0, 16, 60, 16]);
export const success = () => buzz([0, 22, 70, 22, 70, 46]);
export const shake = (strength = 1) => buzz(Math.round(6 + 16 * strength));
