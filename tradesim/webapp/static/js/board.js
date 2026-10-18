// The price board: every stock and ETF on one dense, live-updating table, like a broker's
// board. Prices above yesterday's close (the reference) are green ▲, below red ▼, equal amber.
// Rows are built once; each tick only changes the cells whose numbers moved, and those flash.

import { store, onState, toggleWatch } from './store.js';
import { price, volume, pct, direction, ARROWS, esc } from './fmt.js';
import { openTicket } from './ticket.js';

const BOOK = [2, 1, 0];               // bid levels shown best-last (3, 2, 1) like a real board
let section, tbody, tabs;
let filter = 'all';
let query = '';
let sort = { key: null, dir: -1 };
let selected = null;
const rows = new Map();              // symbol → {tr, cells}
let hintTimer = null;

const HEAD = `
  <thead>
    <tr>
      <th rowspan="2" class="sortable" data-sort="s" style="text-align:left">Symbol</th>
      <th rowspan="2" title="Reference price: yesterday's close">Ref</th>
      <th colspan="6">Bids — buyers waiting</th>
      <th colspan="4" class="grp-match">Last match</th>
      <th colspan="6">Asks — sellers waiting</th>
      <th rowspan="2" class="sortable" data-sort="v">Total vol</th>
      <th colspan="3">Today</th>
      <th colspan="2">You</th>
    </tr>
    <tr>
      <th>Bid 3</th><th>Vol</th><th>Bid 2</th><th>Vol</th><th>Bid 1</th><th>Vol</th>
      <th class="grp-match sortable" data-sort="c">Price</th><th class="grp-match">±</th>
      <th class="grp-match sortable" data-sort="pct">%</th><th class="grp-match">Vol</th>
      <th>Ask 1</th><th>Vol</th><th>Ask 2</th><th>Vol</th><th>Ask 3</th><th>Vol</th>
      <th>High</th><th>Low</th><th>Open</th>
      <th>Qty</th><th>P&amp;L</th>
    </tr>
  </thead>`;

export function mount(el) {
  section = el;
  section.innerHTML = `
    <div class="board-toolbar">
      <label class="search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>
        <input id="board-search" placeholder="Search symbol or company   /" aria-label="Search symbols" autocomplete="off"></label>
      <div class="board-tabs" role="tablist" aria-label="Board filter" id="board-tabs"></div>
      <div class="board-legend" aria-hidden="true"><span class="up">▲ above ref</span><span class="flat">■ unchanged</span><span class="down">▼ below ref</span></div>
    </div>
    <div class="board-wrap"><table class="board">${HEAD}<tbody></tbody></table></div>`;
  tbody = section.querySelector('tbody');
  tabs = section.querySelector('#board-tabs');
  section.querySelector('#board-search').addEventListener('input', (e) => { query = e.target.value.trim().toUpperCase(); layout(); });
  section.querySelectorAll('[data-sort]').forEach((th) => th.addEventListener('click', () => {
    sort = sort.key === th.dataset.sort ? { key: th.dataset.sort, dir: -sort.dir } : { key: th.dataset.sort, dir: th.dataset.sort === 's' ? 1 : -1 };
    layout();
  }));
  buildTabs();
  for (const row of store.universe.symbols) rows.set(row.symbol, makeRow(row));
  wireHint();
  layout();
  let heldKey = '';
  onState((state) => {
    if (section.hidden) return;
    const key = state.positions.map((p) => p.s).join();
    if (filter === 'mine' && key !== heldKey) { heldKey = key; layout(); } else refresh();
  });
  document.addEventListener('keydown', keys);
}

export function show() {
  layout();
}

function buildTabs() {
  const sectors = store.universe.sectors;
  const items = [['all', 'All'], ['watch', '★ Watchlist'], ['mine', 'My holdings'], ['etf', 'ETFs'], ...sectors.map((s) => [s, s])];
  tabs.innerHTML = items.map(([id, label]) => `<button role="tab" data-filter="${esc(id)}">${esc(label)}</button>`).join('');
  tabs.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => { filter = b.dataset.filter; layout(); }));
}

function makeRow(info) {
  const tr = document.createElement('tr');
  tr.dataset.symbol = info.symbol;
  const cell = (cls = '') => { const td = document.createElement('td'); td.className = cls; tr.appendChild(td); return td; };
  const sym = cell('sym');
  sym.innerHTML = `<button class="star" aria-label="Watch ${esc(info.symbol)}">★</button><span class="code"></span>${info.etf ? '<span class="etf">ETF</span>' : ''}`;
  sym.title = `${info.name} · ${info.sector}`;
  const cells = { sym, code: sym.querySelector('.code'), star: sym.querySelector('.star'), ref: cell('ref') };
  cells.code.textContent = info.symbol;
  cells.bids = BOOK.map(() => [cell(), cell('vol')]);
  cells.price = cell('grp-match match-price');
  cells.change = cell('grp-match');
  cells.pct = cell('grp-match');
  cells.tickVol = cell('grp-match vol');
  cells.asks = [0, 1, 2].map(() => [cell(), cell('vol')]);
  cells.total = cell('vol');
  cells.high = cell();
  cells.low = cell();
  cells.open = cell();
  cells.qty = cell('mine');
  cells.pnl = cell('mine');
  cells.star.addEventListener('click', (e) => { e.stopPropagation(); toggleWatch(info.symbol); paintStar(info.symbol); if (filter === 'watch') layout(); });
  cells.code.addEventListener('click', () => { location.hash = `#trade/${info.symbol}`; });
  tr.addEventListener('click', () => select(info.symbol));
  tr.addEventListener('dblclick', () => openTicket(info.symbol, 'BUY'));
  return { tr, cells, info, last: null };
}

function paintStar(symbol) {
  rows.get(symbol).cells.star.classList.toggle('on', store.watch.has(symbol));
}

function select(symbol) {
  if (selected) rows.get(selected)?.tr.classList.remove('selected');
  selected = symbol;
  rows.get(symbol).tr.classList.add('selected');
  store.symbol = symbol;
}

/** Which rows to show, in which order. */
function visibleSymbols() {
  const held = new Set((store.state?.positions || []).map((p) => p.s));
  let list = store.universe.symbols.filter((row) => {
    if (filter === 'watch' && !store.watch.has(row.symbol)) return false;
    if (filter === 'mine' && !held.has(row.symbol)) return false;
    if (filter === 'etf' && !row.etf) return false;
    if (!['all', 'watch', 'mine', 'etf'].includes(filter) && row.sector !== filter) return false;
    return !query || row.symbol.includes(query) || row.name.toUpperCase().includes(query);
  }).map((row) => row.symbol);
  if (sort.key && store.state) {
    const value = (s) => {
      const q = store.quotes[s];
      if (sort.key === 's') return s;
      if (sort.key === 'pct') return q.c / q.ref - 1;
      return q[sort.key];
    };
    list.sort((a, b) => (value(a) > value(b) ? 1 : value(a) < value(b) ? -1 : 0) * sort.dir);
  }
  return list;
}

/** Rebuild the row order after a filter, search or sort change. */
function layout() {
  if (!tbody) return;
  tabs.querySelectorAll('button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.filter === filter)));
  section.querySelectorAll('[data-sort]').forEach((th) => th.setAttribute('aria-sort',
    sort.key !== th.dataset.sort ? 'none' : sort.dir > 0 ? 'ascending' : 'descending'));
  const list = visibleSymbols();
  tbody.replaceChildren(...list.map((s) => rows.get(s).tr));
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="24" class="empty" style="text-align:center">${
      filter === 'mine' ? 'You don\'t own anything yet. Double-click a row to buy.' : 'Nothing matches.'}</td></tr>`;
  }
  list.forEach(paintStar);
  for (const s of list) rows.get(s).last = null;   // repaint every visible cell
  refresh();
}

function setCell(td, text, cls) {
  if (td.textContent !== text) td.textContent = text;
  const want = cls || '';
  if (td.dataset.c !== want) {
    if (td.dataset.c) td.classList.remove(td.dataset.c);
    if (want) td.classList.add(want);
    td.dataset.c = want;
  }
}

function flash(td, dir) {
  td.classList.remove('flash-up', 'flash-down');
  void td.offsetWidth;               // restart the CSS animation
  td.classList.add(dir === 'up' ? 'flash-up' : 'flash-down');
}

/** Update the numbers of the visible rows for the newest tick. */
function refresh() {
  if (!store.state) return;
  const held = Object.fromEntries(store.state.positions.map((p) => [p.s, p]));
  for (const tr of tbody.children) {
    const row = rows.get(tr.dataset.symbol);
    if (!row) continue;
    const q = store.quotes[row.info.symbol];
    const c = row.cells;
    const d = (v) => direction(v, q.ref);
    setCell(c.code, row.info.symbol, d(q.c));
    setCell(c.ref, price(q.ref), 'flat');
    BOOK.forEach((level, i) => {
      const bid = q.bid[level];
      setCell(c.bids[i][0], bid ? price(bid[0]) : '', bid ? d(bid[0]) : '');
      setCell(c.bids[i][1], bid ? volume(bid[1]) : '', bid ? d(bid[0]) : '');
    });
    q.ask.forEach((ask, i) => {
      setCell(c.asks[i][0], price(ask[0]), d(ask[0]));
      setCell(c.asks[i][1], volume(ask[1]), d(ask[0]));
    });
    const dir = d(q.c);
    setCell(c.price, price(q.c), dir);
    setCell(c.change, (q.c - q.ref > 0 ? '+' : q.c - q.ref < 0 ? '−' : '') + price(Math.abs(q.c - q.ref)), dir);
    setCell(c.pct, `${ARROWS[dir]} ${pct(q.c / q.ref - 1).replace(/^[+−]/, '')}`, dir);
    const prev = store.previous[row.info.symbol];
    const tickVol = prev && store.state.clock.phase === 'open' ? Math.max(0, q.v - prev.v) : 0;
    setCell(c.tickVol, tickVol ? volume(tickVol) : '', dir);
    setCell(c.total, volume(q.v), '');
    setCell(c.high, price(q.h), d(q.h));
    setCell(c.low, price(q.l), d(q.l));
    setCell(c.open, price(q.o), d(q.o));
    const mine = held[row.info.symbol];
    setCell(c.qty, mine ? String(mine.qty) : '', '');
    setCell(c.pnl, mine ? pct(mine.pnl_pct, 1) : '', mine ? direction(mine.pnl, 0) : '');
    if (row.last !== null && row.last !== q.c) flash(c.price, q.c > row.last ? 'up' : 'down');
    row.last = q.c;
  }
}

function wireHint() {
  const hint = document.getElementById('board-hint');
  let pos = { x: 0, y: 0 };
  tbody.addEventListener('mousemove', (e) => {
    pos = { x: e.clientX, y: e.clientY };
    hint.style.left = `${pos.x + 14}px`;
    hint.style.top = `${pos.y + 16}px`;
  });
  tbody.addEventListener('mouseover', () => {
    clearTimeout(hintTimer);
    hint.style.display = 'none';
    hintTimer = setTimeout(() => { hint.style.display = 'block'; }, 1200);
  });
  tbody.addEventListener('mouseleave', () => { clearTimeout(hintTimer); hint.style.display = 'none'; });
  tbody.addEventListener('dblclick', () => { clearTimeout(hintTimer); hint.style.display = 'none'; });
}

/** "/" search, ↑/↓ move the selection, Enter or B buys, S sells. */
function keys(e) {
  if (section.hidden || e.target.closest('input, textarea, select, dialog')) return;
  if (e.key === '/') { e.preventDefault(); section.querySelector('#board-search').focus(); return; }
  const list = [...tbody.children].map((tr) => tr.dataset.symbol).filter(Boolean);
  if (!list.length) return;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    const i = list.indexOf(selected);
    const next = list[Math.min(list.length - 1, Math.max(0, i + (e.key === 'ArrowDown' ? 1 : -1)))];
    select(next);
    rows.get(next).tr.scrollIntoView({ block: 'nearest' });
  } else if (selected && (e.key === 'Enter' || e.key.toLowerCase() === 'b')) {
    e.preventDefault();
    openTicket(selected, 'BUY');
  } else if (selected && e.key.toLowerCase() === 's') {
    e.preventDefault();
    openTicket(selected, 'SELL');
  }
}
