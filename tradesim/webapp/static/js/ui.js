// Toasts and the one dialog: small helpers every page uses.

import { esc } from './fmt.js';

const ICONS = { trade: '✅', tip: '🧑‍🏫', news: '📰', margin: '📞', close: '🔔', badge: '🏅', game: '🎮', error: '⚠️', info: 'ℹ️' };

/** Pop a toast in the corner; it leaves by itself after a few seconds. */
export function toast({ kind = 'info', title, text = '', extra = '', icon }) {
  const box = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = `toast ${kind} ${extra}`;
  el.innerHTML = `<div class="t"><span aria-hidden="true">${icon || ICONS[kind] || ''}</span>${esc(title)}</div>${text ? `<div class="x">${esc(text)}</div>` : ''}`;
  box.prepend(el);   // newest at the bottom (the box stacks upwards)
  while (box.children.length > 5) {
    // drop the oldest toast, but keep margin calls on screen as long as possible
    const old = [...box.children].reverse();
    (old.find((t) => !t.classList.contains('margin')) || old[0]).remove();
  }
  const life = kind === 'margin' ? 12000 : kind === 'error' ? 6000 : 5000;
  setTimeout(() => { el.classList.add('leaving'); setTimeout(() => el.remove(), 300); }, life);
}

/** Show the dialog. `onOpen(el)` wires its buttons; returns the dialog element. */
export function openDialog({ title, body, foot = '', wide = false, onOpen }) {
  const dialog = document.getElementById('dialog');
  dialog.className = wide ? 'wide' : '';
  dialog.innerHTML = `<div class="dlg-head"><h2 id="dialog-title">${title}</h2>
      <button class="close-x" data-close aria-label="Close">×</button></div>
    <div class="dlg-body">${body}</div>${foot ? `<div class="dlg-foot">${foot}</div>` : ''}`;
  dialog.querySelectorAll('[data-close]').forEach((b) => b.addEventListener('click', () => dialog.close()));
  if (!dialog.open) dialog.showModal();
  if (onOpen) onOpen(dialog);
  return dialog;
}

export function closeDialog() {
  const dialog = document.getElementById('dialog');
  if (dialog.open) dialog.close();
}

/** `html` → an element (first child), handy for building rows. */
export function element(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}
