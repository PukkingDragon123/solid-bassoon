/** App state and the little that survives a reload. */

import { FORTUNES } from './data/fortunes.js';
import { PAYMENT } from './config.js';

const HISTORY_KEY = 'salasiamsee.history.v1';
const PREFS_KEY = 'salasiamsee.prefs.v1';
const PAID_KEY = 'salasiamsee.paid.v1';
const MAX_HISTORY = 40;

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback; // private mode, or a corrupted entry
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch { /* storage full or blocked — the session still works */ }
}

export const state = {
  name: '',
  wish: '',
  fortune: null,
  candleLit: false,
  incenseLit: false,
  incensePlanted: false,
  prayed: false,
};

export const prefs = {
  sound: true,
  ...read(PREFS_KEY, {}),
};

export function savePrefs() {
  write(PREFS_KEY, { sound: prefs.sound });
}

/**
 * Pick a slip.  Uses the platform CSPRNG with rejection sampling so every
 * one of the 28 is equally likely — a plain modulo would quietly favour
 * the low numbers.
 */
export function drawFortune() {
  const n = FORTUNES.length;
  let value;
  if (globalThis.crypto?.getRandomValues) {
    const limit = Math.floor(256 / n) * n;
    const buf = new Uint8Array(1);
    do {
      crypto.getRandomValues(buf);
      value = buf[0];
    } while (value >= limit);
    value %= n;
  } else {
    value = Math.floor(Math.random() * n);
  }
  return FORTUNES[value];
}

export function getHistory() {
  const h = read(HISTORY_KEY, []);
  return Array.isArray(h) ? h : [];
}

export function addHistory(entry) {
  const h = getHistory();
  h.unshift(entry);
  write(HISTORY_KEY, h.slice(0, MAX_HISTORY));
}

export function lastDrawToday() {
  const today = new Date().toDateString();
  return getHistory().find((e) => new Date(e.at).toDateString() === today) ?? null;
}

/**
 * Whether the visitor has already been through the donation box recently.
 * A convenience so regulars are not asked every visit — it is not, and cannot
 * be, proof that anything was actually paid.
 */
export function hasPaid() {
  const at = Number(read(PAID_KEY, 0));
  if (!at) return false;
  return (Date.now() - at) / 86400000 < (PAYMENT.rememberDays ?? 30);
}

export function markPaid() {
  write(PAID_KEY, Date.now());
}

export function resetRitual() {
  state.fortune = null;
  state.candleLit = false;
  state.incenseLit = false;
  state.incensePlanted = false;
  state.prayed = false;
}

export function formatDate(iso) {
  const d = new Date(iso);
  const months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
  const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear() + 543} · ${time} น.`;
}
