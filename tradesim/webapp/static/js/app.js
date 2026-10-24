// The app shell: loads the game, runs the market clock, draws the header and status bar,
// switches pages (#board, #trade/NVDA, …) and turns server notices into toasts and dialogs.

import { getJSON } from './api.js';
import { run, tick, refresh } from './actions.js';
import { store, onState, onNotice, setState } from './store.js';
import { money, price, pct, volume, direction, ARROWS, esc } from './fmt.js';
import { sparkline } from './chart.js';
import { toast, openDialog, closeDialog } from './ui.js';
import * as board from './board.js';
import * as trade from './trade.js';
import * as portfolio from './portfolio.js';
import * as leverage from './leverage.js';
import * as pages from './pages.js';
import { startTutorial, tutorialDone } from './tutorial.js';
import { reportHTML } from './report.js';

const PAGES = {
  board, trade, portfolio, leverage, news: pages.news, labs: pages.labs, robo: pages.robo,
  learn: pages.learn, challenges: pages.challenges,
};
const mounted = new Set();
let current = null;
let timer = null;
const headlines = [];

// ---------- boot ----------
async function boot() {
  store.universe = await getJSON('/api/universe');
  store.info = Object.fromEntries(store.universe.symbols.map((row) => [row.symbol, row]));
  buildIndexCards();
  wireControls();
  onState(drawHeader);
  onNotice(handleNotice);
  const first = await getJSON('/api/state', { since: 0 });
  // Notices from before this page was opened are old news: don't replay them as toasts.
  store.lastNotice = Math.max(0, ...first.notices.map((n) => n.id));
  setState(first);
  window.addEventListener('hashchange', route);
  route();
  if (!tutorialDone()) startTutorial({ setRunning });   // the first visit: a tutorial that cannot be skipped
}

// ---------- pages ----------
function route() {
  const [name, arg] = (location.hash.slice(1) || 'board').split('/');
  const page = PAGES[name] ? name : 'board';
  for (const section of document.querySelectorAll('main > section')) section.hidden = section.dataset.page !== page;
  document.querySelectorAll('.sidenav a').forEach((a) => a.setAttribute('aria-current', a.dataset.page === page ? 'page' : 'false'));
  const section = document.getElementById(`page-${page}`);
  if (!mounted.has(page)) { PAGES[page].mount(section); mounted.add(page); }
  current = page;
  PAGES[page].show(arg ? decodeURIComponent(arg).toUpperCase() : undefined);
}

// ---------- the market clock ----------
/** How many ticks per request and how long between requests for the chosen speed. */
function pace() {
  const interval = Math.max(200, 1000 / store.speed);
  return { interval, ticks: Math.max(1, Math.round(store.speed * interval / 1000)) };
}

function setRunning(on) {
  store.running = on && store.state.clock.phase !== 'over';
  clearTimeout(timer);
  if (store.running) timer = setTimeout(step, 150);
  drawControls();
}

async function step() {
  if (!store.running) return;
  const { interval, ticks } = pace();
  try {
    await tick(ticks);
  } catch (error) {
    toast({ kind: 'error', title: error.message });
    setRunning(false);
    return;
  }
  if (store.running) timer = setTimeout(step, interval);
}

function wireControls() {
  document.getElementById('btn-start').addEventListener('click', () => {
    if (store.state.clock.phase === 'over') { showReport(); return; }
    if (store.speed === 0) store.speed = 1;
    setRunning(true);
  });
  document.querySelectorAll('#speed button').forEach((b) => b.addEventListener('click', () => {
    const speed = Number(b.dataset.speed);
    if (speed === 0) { setRunning(false); return; }
    store.speed = speed;
    setRunning(true);
  }));
  document.getElementById('btn-close-day').addEventListener('click', async () => {
    setRunning(false);
    const { tick: now, ticks } = store.state.clock;
    await run(`tick ${ticks - now}`);
  });
  const skip = document.getElementById('btn-skip');
  const menu = document.getElementById('skip-menu');
  skip.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = !menu.classList.contains('open');
    menu.classList.toggle('open', open);
    skip.setAttribute('aria-expanded', String(open));
  });
  document.addEventListener('click', () => { menu.classList.remove('open'); skip.setAttribute('aria-expanded', 'false'); });
  menu.querySelectorAll('[data-skip]').forEach((b) => b.addEventListener('click', async () => {
    setRunning(false);
    await run(`next ${b.dataset.skip}`);
  }));
  document.getElementById('btn-tutorial').addEventListener('click', () => startTutorial({ replay: true, setRunning }));
  document.addEventListener('keydown', (e) => {
    if (e.code !== 'Space' || e.target.closest('input, textarea, select, button, dialog')) return;
    e.preventDefault();
    setRunning(!store.running);
  });
}

// ---------- header ----------
function buildIndexCards() {
  const strip = document.getElementById('index-strip');
  strip.innerHTML = store.universe.cards.map((s) => `
    <button class="index-card" data-symbol="${s}" title="${esc(store.info[s].name)}">
      <div><span class="name">${s}</span><span class="value"></span></div>
      <div class="change"></div><div class="meta"></div><canvas aria-hidden="true"></canvas>
    </button>`).join('');
  strip.querySelectorAll('.index-card').forEach((card) => card.addEventListener('click', () => {
    location.hash = `#trade/${card.dataset.symbol}`;
  }));
}

function drawHeader(state) {
  const { clock, account } = state;
  document.getElementById('clock-time').textContent = clock.time;
  const phase = document.getElementById('clock-phase');
  phase.textContent = { open: 'LIVE', closed: 'CLOSED', over: 'GAME OVER' }[clock.phase];
  phase.className = `phase ${clock.phase}`;
  document.getElementById('clock-when').textContent = `Day ${clock.shown_day}/${clock.days} · ${clock.date}`;
  document.getElementById('session-progress').style.width = `${clock.phase === 'open' ? clock.tick / clock.ticks * 100 : 100}%`;
  for (const card of document.querySelectorAll('.index-card')) {
    const q = store.quotes[card.dataset.symbol];
    const dir = direction(q.c, q.ref);
    card.querySelector('.value').textContent = price(q.c);
    card.querySelector('.value').className = `value ${dir}`;
    card.querySelector('.change').innerHTML = `<span class="${dir}">${ARROWS[dir]} ${price(Math.abs(q.c - q.ref))} ${pct(q.c / q.ref - 1)}</span>`;
    card.querySelector('.meta').textContent = `Vol ${volume(q.v)}`;
    sparkline(card.querySelector('canvas'), state.sparks[card.dataset.symbol], q.ref, clock.phase === 'open' ? clock.ticks + 1 : 0);
  }
  document.getElementById('chip-equity').textContent = money(account.equity);
  const dayDir = direction(account.day_pnl, 0), totalDir = direction(account.pnl, 0);
  document.getElementById('chip-pnl').innerHTML =
    `<span class="${dayDir}">${pct(account.day_pct)} today</span> · <span class="${totalDir}">${pct(account.pnl_pct)} total</span>`;
  document.getElementById('status-fear').innerHTML = `😱 Fear gauge <b>${clock.fear.toFixed(0)}</b> (${esc(clock.fear_word)})`;
  document.getElementById('status-seed').textContent = `seed ${clock.seed}`;
  const goal = document.getElementById('status-goal');
  if (clock.challenge) {
    const done = clock.challenge.goals.filter((g) => g.passed).length;
    goal.innerHTML = `${clock.challenge.emoji} <b>${esc(clock.challenge.title)}</b> · ${done}/${clock.challenge.goals.length} goals on track`;
  } else goal.textContent = account.loan > 0 ? `🏦 Borrowing ${money(account.loan, 0)} · margin call if holdings fall ${pct(account.room, 1).replace('+', '')}` : '';
  drawControls();
}

function drawControls() {
  if (!store.state) return;
  const { phase } = store.state.clock;
  const start = document.getElementById('btn-start');
  start.classList.toggle('hidden', store.running);
  start.textContent = phase === 'over' ? '🏁 Final report' : phase === 'open' ? '▶ Resume' : `▶ Open day ${store.state.clock.day + 1}`;
  start.classList.toggle('start-btn', phase !== 'over');
  document.querySelectorAll('#speed button').forEach((b) => {
    const s = Number(b.dataset.speed);
    b.setAttribute('aria-pressed', String(store.running ? s === store.speed : s === 0));
  });
  document.getElementById('btn-close-day').disabled = phase === 'over';
  document.getElementById('btn-close-day').textContent = phase === 'open' ? 'To close ⏭' : 'Play day ⏭';
  document.getElementById('btn-skip').disabled = phase === 'over';
}

// ---------- notices ----------
function handleNotice(notice) {
  if (notice.kind === 'news') {
    headlines.unshift(notice.text);
    document.querySelector('#status-ticker').innerHTML = `<span>📰 ${headlines.slice(0, 5).map(esc).join('   ·   📰 ')}</span>`;
    toast({ kind: 'news', title: notice.text, text: `${notice.title} — ${notice.data.explanation}` });
  } else if (notice.kind === 'close') {
    if (!store.autoplay || notice.data.over) setRunning(false);
    if (store.autoplay && !notice.data.over) toast({ kind: 'close', title: `Day ${notice.data.to} closed`, text: `You ${pct(notice.data.you)}, market ${pct(notice.data.market)}` });
    else closingBell(notice.data);
  } else if (notice.kind === 'game' && notice.title === 'Game over') {
    setRunning(false);
  } else if (notice.kind === 'game' && notice.title === 'New game') {
    setRunning(false);
    setTimeout(() => location.reload(), 400);   // a different market: start every page afresh
  } else if (notice.kind === 'margin') {
    toast({ kind: 'margin', title: notice.title, text: notice.text });
  } else if (notice.kind === 'badge') {
    toast({ kind: 'badge', title: notice.title, text: notice.text, icon: notice.data.emoji });
  } else if (notice.kind === 'trade') {
    toast({ kind: 'trade', title: notice.title, text: notice.text, extra: notice.data.side === 'SELL' ? 'sell' : '' });
  } else {
    toast({ kind: notice.kind, title: notice.title, text: notice.text });
  }
}

function moverList(list) {
  return list.map(([s, m]) => `<div class="row"><span>${esc(s)} <span class="muted">${esc(store.info[s]?.name || '')}</span></span><b class="${direction(m, 0)}">${pct(m)}</b></div>`).join('');
}

/** The closing-bell card: how you did against the market, and what's next. */
function closingBell(d) {
  const days = d.to - d.from > 1 ? `Days ${d.from + 1}–${d.to}` : `Day ${d.to}`;
  const verdict = d.you > d.market + 0.001 ? '<div class="lesson good">You beat the market. Nice.</div>'
    : d.you < d.market - 0.001 ? '<div class="lesson bad">The market beat you this time.</div>' : '';
  openDialog({
    title: `🔔 Closing bell — ${days}`,
    body: `<div class="versus">
        <div><div class="secondary">You</div><div class="big ${direction(d.you, 0)}">${pct(d.you)}</div><div class="muted">${money(d.equity)}</div></div>
        <div><div class="secondary">Whole market (${esc(d.index)})</div><div class="big ${direction(d.market, 0)}">${pct(d.market)}</div></div>
      </div>${verdict}
      <div class="grid cols-2"><div class="summary-rows"><h3>▲ Best stocks</h3>${moverList(d.best)}</div>
      <div class="summary-rows"><h3>▼ Worst stocks</h3>${moverList(d.worst)}</div></div>
      <label style="display:flex;gap:8px;align-items:center;margin-top:14px;color:var(--text-secondary)">
        <input type="checkbox" data-auto ${store.autoplay ? 'checked' : ''}> Keep the market running after each close (no pop-up)</label>`,
    foot: d.over ? '<button class="btn primary" data-report>🏁 See your final report</button>'
      : `<button class="btn" data-go="portfolio">Review portfolio</button><button class="btn" data-skip5>Skip 5 days ⏩</button>
         <button class="btn primary" data-next>▶ Open day ${d.to + 1}</button>`,
    onOpen: (dialog) => {
      dialog.querySelector('[data-auto]').addEventListener('change', (e) => { store.autoplay = e.target.checked; });
      dialog.querySelector('[data-next]')?.addEventListener('click', () => { closeDialog(); setRunning(true); });
      dialog.querySelector('[data-skip5]')?.addEventListener('click', async () => { closeDialog(); await run('next 5'); });
      dialog.querySelector('[data-go]')?.addEventListener('click', () => { closeDialog(); location.hash = '#portfolio'; });
      dialog.querySelector('[data-report]')?.addEventListener('click', showReport);
      dialog.querySelector('[data-next], [data-report]')?.focus();
    },
  });
}

/** The final report: grade, goals, coach tips and the market's hidden story. */
export async function showReport() {
  const report = await getJSON('/api/report');
  openDialog({
    title: '🏁 Your report', wide: true, body: `<div class="report">${reportHTML(report)}</div>`,
    foot: `<button class="btn" data-go="labs">What if I had…? (replay)</button>
           <button class="btn" data-go="challenges">Try a challenge</button>
           <button class="btn primary" data-new>New game</button>`,
    onOpen: (dialog) => {
      dialog.querySelectorAll('[data-go]').forEach((b) => b.addEventListener('click', () => { closeDialog(); location.hash = `#${b.dataset.go}`; }));
      dialog.querySelector('[data-new]').addEventListener('click', async () => { closeDialog(); await run('new'); });
    },
  });
}

boot().catch((error) => {
  document.getElementById('main').innerHTML = `<div class="empty">Couldn't load the game: ${esc(error.message)}. Is the server still running?</div>`;
});

export { setRunning, refresh };
