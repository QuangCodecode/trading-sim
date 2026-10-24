// The tutorial: a guided tour of every page, then a short first game played with real clicks.
// The first time it cannot be skipped: the card has no close button, and while it is open everything
// except the lit-up part of the page is `inert` (it ignores clicks, focus and keys). A replay is
// optional and can be closed. What the cards say lives in tutorial-steps.js.

import { store } from './store.js';
import { run } from './actions.js';
import { element } from './ui.js';
import { STEPS } from './tutorial-steps.js';

const DONE_KEY = 'tradesim.tutorial';          // 'done' once the whole tutorial has been finished
const REACHED_KEY = 'tradesim.tutorial.step';  // furthest step reached: a reload carries on from there
const GAP = 14;                                // px between the lit-up part and the card
const PAD = 6;                                 // px of breathing room around the lit-up part

let root, spot, card;                          // the three pieces this module adds to the page
let required = true;                           // true the first time: no way out before the end
let pauseClock;                                // app.js's setRunning, handed over by startTutorial
let index = 0;                                 // the step on show
let reached = 0;                               // the furthest step opened so far
let target;                                    // the lit-up element (null = none on screen, undefined = not looked up yet)
let locked = [];                               // the elements made inert around the target
let frame = 0;                                 // requestAnimationFrame id
let shownDone = null;                          // was the task last drawn as done? (redraw only on a change)

/** Has this player finished the tutorial before? */
export function tutorialDone() {
  return localStorage.getItem(DONE_KEY) === 'done';
}

/** Open the tutorial. `replay`: the player asked for it again, so it can be closed and no task is enforced. */
export function startTutorial({ replay = false, setRunning }) {
  if (root) return;
  required = !replay;
  pauseClock = setRunning;
  root = element(`<div class="tour"><div class="tour-spot" hidden></div>
    <section class="tour-card" aria-label="Tutorial" aria-live="polite" tabindex="-1"></section></div>`);
  document.body.append(root);
  spot = root.querySelector('.tour-spot');
  card = root.querySelector('.tour-card');
  window.addEventListener('keydown', guardKeys, true);
  reached = required ? Math.min(Number(localStorage.getItem(REACHED_KEY)) || 0, STEPS.length - 1) : 0;
  openStep(reached);
  frame = requestAnimationFrame(follow);
}

// ---------- steps ----------
/** Show step `i`: go to its page, pause the market, draw its card. */
function openStep(i) {
  index = i;
  reached = Math.max(reached, i);
  if (required) localStorage.setItem(REACHED_KEY, String(reached));
  const step = STEPS[i];
  if (step.page) location.hash = `#${step.page}`;
  if (!step.live) pauseClock(false);
  target = undefined;                            // look the target up again: the page may have changed
  shownDone = null;
  card.innerHTML = cardHtml(step, i);
  card.querySelector('[data-back]').addEventListener('click', () => openStep(index - 1));
  card.querySelector('[data-next]')?.addEventListener('click', () => openStep(index + 1));
  card.querySelectorAll('[data-finish]').forEach((b) => b.addEventListener('click', () => finish(b.dataset.finish === 'new')));
  card.querySelector('[data-close]')?.addEventListener('click', () => finish(false));
  refreshTask(step);
  const next = card.querySelector('[data-next]');
  (next && !next.disabled ? next : card).focus();
}

function cardHtml(step, i) {
  const last = i === STEPS.length - 1;
  const over = store.state.clock.phase === 'over';
  const forward = !last ? '<button class="btn primary" data-next>Next →</button>'
    : !required ? '<button class="btn primary" data-finish>Done</button>'
    : `${over ? '' : '<button class="btn" data-finish>Keep this game</button>'}<button class="btn primary" data-finish="new">▶ Start a fresh game</button>`;
  return `<div class="tour-bar"><i style="width:${(i + 1) / STEPS.length * 100}%"></i></div>
    <div class="tour-head"><span>${step.part}</span><span>${i + 1} / ${STEPS.length}</span>
      ${required ? '' : '<button class="close-x" data-close aria-label="Close the tutorial">×</button>'}</div>
    <h2>${step.title}</h2>
    <div class="tour-text">${step.text}</div>
    ${step.task ? '<div class="tour-task"></div>' : ''}
    <div class="tour-foot"><button class="btn" data-back ${i ? '' : 'disabled'}>← Back</button>${forward}</div>`;
}

/** Has the player done what the step asks? A finished game counts: nothing more can be done in it. */
function isDone(step) {
  return !step.done || store.state.clock.phase === 'over' || step.done(store.state);
}

/** Show the task or its "done" message, and unlock Next once it is done (only on the furthest step). */
function refreshTask(step) {
  const done = isDone(step);
  const next = card.querySelector('[data-next]');
  if (next) next.disabled = required && index === reached && !done;
  if (!step.task || done === shownDone) return;
  shownDone = done;
  const box = card.querySelector('.tour-task');
  box.classList.toggle('done', done);
  box.innerHTML = done ? `✅ ${step.after}` : `👉 <b>Your turn:</b> ${step.task}`;
}

/** The last step is over (or, in a replay, closed): remember it, tidy up, and maybe start a new game. */
async function finish(fresh) {
  localStorage.setItem(DONE_KEY, 'done');
  localStorage.removeItem(REACHED_KEY);
  cancelAnimationFrame(frame);
  window.removeEventListener('keydown', guardKeys, true);
  unlock();
  root.remove();
  root = null;
  location.hash = '#board';
  if (fresh) await run('new');
}

// ---------- keeping the player inside the tutorial ----------
/** Make everything except `keep` (and the cards above it in the page) inert. */
function lock(keep) {
  unlock();
  for (let node = keep || root; node !== document.body; node = node.parentElement) {
    for (const other of node.parentElement.children) {
      // pop-ups (the closing bell) must stay usable, and so must the tutorial itself
      if (other !== node && other !== root && other.tagName !== 'DIALOG') { other.inert = true; locked.push(other); }
    }
  }
}

function unlock() {
  locked.forEach((el) => { el.inert = false; });
  locked = [];
}

/** Keys only reach the card, the lit-up part and pop-ups: the page's own shortcuts (Space, B, S, /) stay quiet. */
function guardKeys(e) {
  if (e.target.closest('.tour-card, dialog') || target?.contains(e.target)) return;
  e.stopPropagation();
}

// ---------- drawing, once per frame ----------
/** The step's target if it is on screen right now (its page may still be loading), else null. */
function lookUp(selector) {
  const el = selector ? document.querySelector(selector) : null;
  const r = el?.getBoundingClientRect();
  return r && r.width > 0 && r.height > 0 ? el : null;
}

/** Keep the light, the lock, the card and the Next button right, whatever the page does. */
function follow() {
  frame = requestAnimationFrame(follow);          // first, so that one error can't stop the tutorial
  const step = STEPS[index];
  const popup = document.getElementById('dialog').open;
  root.hidden = popup;                            // the closing bell has the stage: wait behind it
  refreshTask(step);
  if (popup) return;
  const found = lookUp(step.target);
  if (found !== target) {
    target = found;
    lock(found);
    if (found) found.scrollIntoView({ block: found.getBoundingClientRect().height < innerHeight * 0.7 ? 'center' : 'start' });
  }
  const r = found?.getBoundingClientRect();
  root.classList.toggle('plain', !found);
  placeSpot(r);
  placeCard(r, step);
}

/** The glowing frame around the target. (Everything outside it is dimmed by its huge box-shadow.) */
function placeSpot(r) {
  spot.hidden = !r;
  if (!r) return;
  const left = Math.max(0, r.left - PAD), top = Math.max(0, r.top - PAD);
  Object.assign(spot.style, {
    left: `${left}px`, top: `${top}px`,
    width: `${Math.min(innerWidth, r.right + PAD) - left}px`, height: `${Math.min(innerHeight, r.bottom + PAD) - top}px`,
  });
}

/** Put the card on the first side of the target with room for it; in the middle if there is no target. */
function placeCard(r, step) {
  const w = card.offsetWidth, h = card.offsetHeight;
  const clamp = (v, size, max) => Math.max(GAP, Math.min(v, max - size - GAP));
  let x = (innerWidth - w) / 2, y = (innerHeight - h) / 2;
  if (r) {
    const gap = GAP + (step.away || 0);
    const room = { bottom: innerHeight - r.bottom - gap, top: r.top - gap, right: innerWidth - r.right - gap, left: r.left - gap };
    const need = { bottom: h + GAP, top: h + GAP, right: w + GAP, left: w + GAP };
    const side = [step.side, 'bottom', 'top', 'right', 'left'].find((s) => s && room[s] >= need[s]);
    if (!side) { x = innerWidth - w - GAP; y = innerHeight - h - GAP; }   // no free side: sit in the corner
    else {
      x = clamp(side === 'right' ? r.right + gap : side === 'left' ? r.left - w - gap : r.left, w, innerWidth);
      y = clamp(side === 'bottom' ? r.bottom + gap : side === 'top' ? r.top - h - gap : r.top, h, innerHeight);
    }
  }
  card.style.left = `${x}px`;
  card.style.top = `${y}px`;
}
