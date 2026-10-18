// The Portfolio page: your money vs the whole market, what you own, where it sits by
// sector, every trade, and the Trade Coach's tips.

import { getJSON } from './api.js';
import { run } from './actions.js';
import { store, onState } from './store.js';
import { money, price, pct, direction, esc } from './fmt.js';
import { LineChart, chartBox } from './chart.js';
import { openTicket } from './ticket.js';

let section, chart;
let data = null;
let lastKey = '';

export function mount(el) {
  section = el;
  section.innerHTML = `
    <div class="page-head"><div><h1>Portfolio</h1><p>Everything you own, how it's doing, and how you compare with simply buying the whole market.</p></div></div>
    <div class="kpis" data-f="kpis"></div>
    <div class="grid cols-main-side">
      <div class="card"><h2>Your money vs the whole market</h2><div class="legend" data-f="legend"></div>${chartBox(300, 'Your money compared with the market')}</div>
      <div class="card"><h2>Where your money sits</h2><div data-f="sectors"></div></div>
    </div>
    <div class="card" style="margin-top:12px"><h2>Holdings</h2><div data-f="holdings"></div></div>
    <div class="grid cols-main-side" style="margin-top:12px">
      <div class="card"><h2>Trade history</h2><div data-f="trades" style="max-height:340px;overflow:auto"></div></div>
      <div class="card"><h2>🧑‍🏫 Trade Coach</h2><div data-f="tips"></div></div>
    </div>`;
  chart = new LineChart(section.querySelector('.chart-wrap'));
  onState(() => {
    if (section.hidden) return;
    drawLive();
    const c = store.state.clock;
    if (`${c.day}:${Math.floor(c.tick / 6)}:${store.state.positions.length}` !== lastKey) load();
  });
}

export function show() {
  drawLive();
  load();
}

async function load() {
  const c = store.state.clock;
  lastKey = `${c.day}:${Math.floor(c.tick / 6)}:${store.state.positions.length}`;
  data = await getJSON('/api/portfolio');
  drawChart();
  drawSectors();
  drawTrades();
}

function kpi(label, value, sub, cls = '') {
  return `<div class="kpi"><div class="label">${label}</div><div class="value ${cls}">${value}</div><div class="sub">${sub}</div></div>`;
}

function drawLive() {
  const a = store.state.account;
  const cashCard = a.loan > 0
    ? kpi('Loan from the broker', money(a.loan), `interest so far ${money(a.interest)}`, 'down')
    : kpi('Cash', money(a.cash), `${pct(a.cash / a.equity, 0).replace('+', '')} of your money`);
  const room = a.loan > 0 ? `${pct(a.room, 1).replace('+', '')} fall → margin call` : 'no loan, no margin calls';
  section.querySelector('[data-f="kpis"]').innerHTML =
    kpi('Your money (equity)', money(a.equity), `<span class="${direction(a.pnl, 0)}">${money(a.pnl)} (${pct(a.pnl_pct)}) total</span>`) +
    kpi('Today', `<span class="${direction(a.day_pnl, 0)}">${money(a.day_pnl)}</span>`, `<span class="${direction(a.day_pnl, 0)}">${pct(a.day_pct)}</span> since the last close`) +
    cashCard +
    kpi('Invested', money(a.invested), `buying power ${money(a.buying_power, 0)}`) +
    kpi('Leverage', `${a.used === null ? '∞' : a.used.toFixed(2)}×`, `allowed ${a.leverage}× · <a href="#leverage">change</a>`, a.used > 1.01 ? 'flat' : '') +
    kpi('Safety cushion', a.loan > 0 ? pct(a.room, 1).replace('+', '') : '—', room, a.loan > 0 && a.room < 0.1 ? 'down' : '');
  drawHoldings();
}

function drawHoldings() {
  const box = section.querySelector('[data-f="holdings"]');
  const rows = [...store.state.positions].sort((x, y) => y.value - x.value);
  if (!rows.length) {
    box.innerHTML = '<div class="empty">You don\'t own anything yet. Go to the <a href="#board">board</a> and double-click a stock, or try a whole-market ETF: <button class="btn small" data-buy="MKT100">Buy MKT100</button></div>';
    box.querySelector('[data-buy]').addEventListener('click', () => openTicket('MKT100', 'BUY'));
    return;
  }
  box.innerHTML = `<table class="data"><thead><tr><th>Symbol</th><th class="left">Name</th><th>Qty</th><th>Avg cost</th><th>Last</th>
      <th>Value</th><th>P&amp;L</th><th>P&amp;L %</th><th class="left">Weight</th><th></th></tr></thead><tbody>${rows.map((p) => `
      <tr class="clickable" data-s="${p.s}"><td><b>${p.s}</b></td><td class="left secondary">${esc(store.info[p.s].name)}</td>
      <td>${p.qty}</td><td>${price(p.avg)}</td><td class="${direction(p.last, store.quotes[p.s].ref)}">${price(p.last)}</td>
      <td>${money(p.value)}</td><td class="${direction(p.pnl, 0)}">${money(p.pnl)}</td><td class="${direction(p.pnl, 0)}">${pct(p.pnl_pct)}</td>
      <td class="left"><span class="bar-cell" style="width:${Math.min(1, p.weight) * 120}px"></span> ${pct(p.weight, 0).replace('+', '')}</td>
      <td><button class="btn small" data-trade="${p.s}">Trade</button> <button class="btn small ghost" data-sell="${p.s}">Sell all</button></td></tr>`).join('')}
    </tbody></table>`;
  box.querySelectorAll('tr[data-s]').forEach((tr) => tr.addEventListener('dblclick', () => openTicket(tr.dataset.s, 'SELL')));
  box.querySelectorAll('[data-trade]').forEach((b) => b.addEventListener('click', (e) => { e.stopPropagation(); location.hash = `#trade/${b.dataset.trade}`; }));
  box.querySelectorAll('[data-sell]').forEach((b) => b.addEventListener('click', (e) => { e.stopPropagation(); run(`sell ${b.dataset.sell} all`); }));
}

function drawChart() {
  const index = data.index;
  section.querySelector('[data-f="legend"]').innerHTML =
    `<span style="--c:var(--series-1)">You</span><span style="--c:var(--series-2)">${esc(index)} bought on day 0</span><span style="--c:#4a5260" class="dashed">Starting cash</span>`;
  chart.setData({
    labels: data.labels,
    series: [{ name: 'You', values: data.you, color: '#3987e5' },
      { name: `${index} (whole market)`, values: data.market, color: '#d95926' }],
    format: (v) => money(v, 0), baseline: store.state.account.start,
    empty: 'Your money vs the market appears after the first day closes.',
  });
}

function drawSectors() {
  const box = section.querySelector('[data-f="sectors"]');
  const total = data.sectors.reduce((sum, [, v]) => sum + v, 0);
  if (!total) {
    box.innerHTML = '<div class="empty">All cash. Owning several sectors (or an ETF) spreads your risk.</div>';
    return;
  }
  box.innerHTML = `<table class="data"><tbody>${data.sectors.map(([sector, value]) => `<tr><td>${esc(sector)}</td>
      <td><span class="bar-cell" style="width:${value / total * 130}px"></span></td><td>${pct(value / total, 0).replace('+', '')}</td></tr>`).join('')}
    </tbody></table><p class="muted" style="font-size:12px;margin:8px 0 0">ETFs are split into the companies they hold. ${data.sectors.length >= 3
      ? 'Three or more sectors: one piece of bad news can\'t sink everything.' : 'Fewer than three sectors: one sector\'s bad day hits most of your money.'}</p>`;
}

function drawTrades() {
  const box = section.querySelector('[data-f="trades"]');
  box.innerHTML = data.trades.length ? `<table class="data"><thead><tr><th>When</th><th class="left">Side</th><th>Symbol</th><th>Qty</th><th>Price</th>
      <th>Fee</th><th>Realised P&amp;L</th></tr></thead><tbody>${data.trades.map((t) => `<tr><td>${esc(t.when)}</td>
      <td class="left ${t.side === 'BUY' ? 'up' : 'down'}">${t.side}${t.note ? ` <span class="chip down">${esc(t.note)}</span>` : ''}</td>
      <td>${t.s}</td><td>${t.qty}</td><td>${price(t.price)}</td><td>${money(t.fee)}</td>
      <td class="${t.pnl === null ? '' : direction(t.pnl, 0)}">${t.pnl === null ? '' : money(t.pnl)}</td></tr>`).join('')}</tbody></table>`
    : '<div class="empty">No trades yet.</div>';
  const tips = section.querySelector('[data-f="tips"]');
  tips.innerHTML = data.tips.length ? data.tips.map((t) => `<div class="lesson ${t.severity === 'praise' ? 'good' : t.severity === 'warn' ? 'bad' : ''}">${esc(t.text)}</div>`).join('')
    : '<p class="muted">No tips right now — your habits look fine.</p>';
}
