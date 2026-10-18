// The Trade page: a candlestick chart with history, the order ticket, the order book and
// everything worth knowing about one symbol before you buy it.

import { getJSON } from './api.js';
import { store, onState, toggleWatch } from './store.js';
import { price, pct, volume, direction, ARROWS, esc } from './fmt.js';
import { PriceChart, chartBox } from './chart.js';
import { renderTicket } from './ticket.js';

let section, chart;
let symbol = null;
let span = '1D';
let mode = 'candles';
const indicators = { ma20: true, ma50: false, volume: true };
let chartData = null;
let loading = false;
let pending = false;
let lastDay = null;
let lastTick = null;
let profile = null;
let heldQty = null;

export function mount(el) {
  section = el;
  const groups = {};
  for (const row of store.universe.symbols) (groups[row.sector] ||= []).push(row);
  const options = Object.entries(groups).map(([sector, list]) => `<optgroup label="${esc(sector)}">${
    list.map((r) => `<option value="${r.symbol}">${r.symbol} — ${esc(r.name)}</option>`).join('')}</optgroup>`).join('');
  section.innerHTML = `
    <div class="quote-head">
      <div><div style="display:flex;gap:8px;align-items:center"><span class="sym" data-f="sym"></span>
          <select class="symbol-picker" aria-label="Choose a symbol">${options}</select>
          <button class="btn small ghost" data-watch>★ Watch</button></div>
        <div class="name" data-f="name"></div></div>
      <div><div class="price" data-f="price"></div><div data-f="change"></div></div>
      <div class="stats" data-f="stats"></div>
    </div>
    <div class="grid cols-main-side">
      <div>
        <div class="card">
          <div class="chart-toolbar">
            <div class="seg" role="group" aria-label="Chart range" data-group="span">
              <button data-v="1D">1D</button><button data-v="1M">1M</button><button data-v="3M">3M</button>
              <button data-v="6M">6M</button><button data-v="ALL">All</button></div>
            <div class="seg" role="group" aria-label="Chart type" data-group="mode">
              <button data-v="candles">Candles</button><button data-v="line">Line</button></div>
            <div class="seg" role="group" aria-label="Indicators" data-group="ind">
              <button data-v="ma20">MA 20</button><button data-v="ma50">MA 50</button><button data-v="volume">Volume</button></div>
            <div class="legend" style="margin:0 0 0 auto" data-f="legend"></div>
          </div>
          ${chartBox(470, 'Price chart')}
        </div>
        <div class="grid cols-2" style="margin-top:12px">
          <div class="card about" data-f="about"></div>
          <div class="card" data-f="side-info"></div>
        </div>
      </div>
      <div>
        <div class="card"><h2>Place an order</h2><div data-f="ticket"></div></div>
        <div class="card"><h2>Order book <span class="muted" style="font-weight:400">· waiting orders</span></h2><div data-f="depth"></div>
          <p class="muted" style="margin:8px 0 0;font-size:11.5px">Buyers queue below the last price (bids), sellers above it (asks).
          The gap between the best bid and the best ask is the spread. In this game, market orders fill at the last price.</p></div>
      </div>
    </div>`;
  chart = new PriceChart(section.querySelector('.chart-wrap'));
  section.querySelector('.symbol-picker').addEventListener('change', (e) => { location.hash = `#trade/${e.target.value}`; });
  section.querySelector('[data-watch]').addEventListener('click', () => { toggleWatch(symbol); drawQuote(); });
  section.querySelectorAll('[data-group] button').forEach((b) => b.addEventListener('click', () => {
    const group = b.closest('[data-group]').dataset.group;
    if (group === 'span') { span = b.dataset.v; loadChart(); }
    if (group === 'mode') { mode = b.dataset.v; drawChart(); }
    if (group === 'ind') { indicators[b.dataset.v] = !indicators[b.dataset.v]; drawChart(); }
    drawToolbar();
  }));
  onState(() => { if (!section.hidden) live(); });
}

export function show(arg) {
  const next = arg && store.info[arg] ? arg : (symbol || store.symbol || 'NVDA');
  if (next !== symbol) {
    symbol = next;
    store.symbol = next;
    heldQty = store.state.positions.find((p) => p.s === symbol)?.qty || 0;
    section.querySelector('.symbol-picker').value = symbol;
    renderTicket(section.querySelector('[data-f="ticket"]'), symbol, 'BUY');
    loadChart();
    loadProfile();
  } else {
    loadChart();
  }
  drawToolbar();
  drawQuote();
}

function drawToolbar() {
  section.querySelectorAll('[data-group="span"] button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === span)));
  section.querySelectorAll('[data-group="mode"] button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === mode)));
  section.querySelectorAll('[data-group="ind"] button').forEach((b) => b.setAttribute('aria-pressed', String(indicators[b.dataset.v])));
}

async function loadChart() {
  if (loading) { pending = true; return; }   // one request at a time; catch up afterwards
  loading = true;
  try {
    lastDay = store.state.clock.day;
    lastTick = store.state.clock.tick;
    chartData = await getJSON('/api/chart', { symbol, span });
  } catch (error) {
    chartData = null;
  } finally {
    loading = false;
  }
  drawChart();
  if (pending) { pending = false; loadChart(); }
}

async function loadProfile() {
  profile = await getJSON('/api/quote', { symbol });
  drawProfile();
}

function drawChart() {
  if (!chartData || chartData.symbol !== symbol) return;
  const ma = [];
  if (indicators.ma20) ma.push({ period: 20, color: '#c98500' });
  if (indicators.ma50) ma.push({ period: 50, color: '#d55181' });
  const intraday = chartData.span === '1D';
  chart.setData({
    candles: chartData.candles, markers: chartData.markers, ref: chartData.ref, mode,
    volume: indicators.volume, ma: intraday ? [] : ma,
    slots: intraday ? Math.ceil(store.universe.ticks / 3) : Math.max(chartData.candles.length, 20),
    empty: intraday ? 'The market is closed. Open it to watch today\'s 15-minute candles form.' : 'No history yet.',
  });
  const items = [];
  if (intraday) items.push('<span style="--c:var(--ref)" class="dashed">Ref (yesterday\'s close)</span>');
  else ma.forEach((m) => items.push(`<span style="--c:${m.color}">MA ${m.period}</span>`));
  items.push('<span style="--c:var(--series-1)">▲ your buys</span><span style="--c:var(--series-2)">▼ sells</span>');
  section.querySelector('[data-f="legend"]').innerHTML = items.join('');
}

/** Each new tick: refresh the header numbers and the chart's newest candle. */
function live() {
  drawQuote();
  const clock = store.state.clock;
  const held = store.state.positions.find((p) => p.s === symbol)?.qty || 0;
  if (held !== heldQty) { heldQty = held; loadProfile(); loadChart(); return; }   // you traded it
  if (clock.day !== lastDay || (span === '1D' && clock.tick !== lastTick)) {
    loadChart();
    if (clock.day !== lastDay) loadProfile();
    return;
  }
  if (span !== '1D' && chartData && clock.phase === 'open') {
    const q = store.quotes[symbol];
    const last = chartData.candles[chartData.candles.length - 1];
    if (last?.live) Object.assign(last, { o: q.o, h: q.h, l: q.l, c: q.c, v: q.v });
    drawChart();
  }
}

function drawQuote() {
  const q = store.quotes[symbol];
  const info = store.info[symbol];
  if (!q) return;
  const dir = direction(q.c, q.ref);
  section.querySelector('[data-f="sym"]').textContent = symbol;
  section.querySelector('[data-f="name"]').textContent = `${info.name} · ${info.etf ? 'ETF' : info.sector}${info.beta ? ` · beta ${info.beta}` : ''}`;
  const priceEl = section.querySelector('[data-f="price"]');
  priceEl.textContent = price(q.c);
  priceEl.className = `price ${dir}`;
  section.querySelector('[data-f="change"]').innerHTML = `<span class="${dir}">${ARROWS[dir]} ${price(Math.abs(q.c - q.ref))} (${pct(q.c / q.ref - 1)})</span> <span class="muted">vs ref</span>`;
  section.querySelector('[data-f="stats"]').innerHTML = `<span>Ref<b class="flat">${price(q.ref)}</b></span><span>Open<b>${price(q.o)}</b></span>
    <span>High<b>${price(q.h)}</b></span><span>Low<b>${price(q.l)}</b></span><span>Volume<b>${volume(q.v)}</b></span>`;
  section.querySelector('[data-watch]').textContent = store.watch.has(symbol) ? '★ Watching' : '☆ Watch';
  drawDepth(q);
}

function drawDepth(q) {
  const levels = [...q.ask].reverse().map(([p, v]) => ['ask', p, v]).concat([['mid', q.c, 0]], q.bid.map(([p, v]) => ['bid', p, v]));
  const biggest = Math.max(...q.bid.map((b) => b[1]), ...q.ask.map((a) => a[1]), 1);
  section.querySelector('[data-f="depth"]').innerHTML = `<table class="depth"><tbody>${levels.map(([side, p, v]) => side === 'mid'
    ? `<tr class="mid"><td>Last</td><td class="${direction(p, q.ref)}">${price(p)}</td><td></td></tr>`
    : `<tr><td class="muted">${side === 'ask' ? 'Ask' : 'Bid'}</td><td class="${side === 'ask' ? 'down' : 'up'}">${price(p)}</td>
         <td>${volume(v)}<span class="fill" style="width:${v / biggest * 100}%;background:${side === 'ask' ? 'var(--down)' : 'var(--up)'}"></span></td></tr>`).join('')}</tbody></table>`;
}

function drawProfile() {
  const p = profile;
  if (!p || p.symbol !== symbol) return;
  const about = section.querySelector('[data-f="about"]');
  const betaWords = p.beta === undefined ? '' : p.beta > 1.2 ? 'aggressive: moves more than the market' : p.beta < 0.8 ? 'defensive: moves less than the market' : 'moves about like the market';
  about.innerHTML = `<h2>About ${esc(p.symbol)}</h2>
    <p>${esc(p.about || store.info[symbol].about)}</p>
    <dl class="kv">
      ${p.beta !== undefined ? `<dt>Beta</dt><dd>${p.beta} <span class="muted" style="font-weight:400">(${betaWords})</span></dd>` : ''}
      <dt>Yearly volatility</dt><dd>${pct(p.vol, 0).replace('+', '')}</dd>
      <dt>6-month high / low</dt><dd>${price(p.high)} / ${price(p.low)}</dd>
      <dt>1 month / 3 months</dt><dd><span class="${direction(p.m1, 0)}">${pct(p.m1, 1)}</span> / <span class="${direction(p.m3, 0)}">${pct(p.m3, 1)}</span></dd>
      <dt>Since day 0</dt><dd class="${direction(p.since_start, 0)}">${pct(p.since_start, 1)}</dd>
    </dl>
    ${p.holdings ? `<h3 style="margin-top:12px">Inside this ETF (${p.holdings.length} holdings)</h3>
      <table class="data"><tbody>${p.holdings.slice(0, 10).map((h) => `<tr><td><a href="#trade/${h.s}">${h.s}</a> <span class="muted">${esc(h.sector)}</span></td>
      <td><span class="bar-cell" style="width:${h.w * 160}px"></span> ${pct(h.w, 1).replace('+', '')}</td></tr>`).join('')}</tbody></table>
      ${p.holdings.length > 10 ? `<p class="muted">…and ${p.holdings.length - 10} more.</p>` : ''}` : ''}`;
  const side = section.querySelector('[data-f="side-info"]');
  const robo = p.robo ? `<div class="lesson ${p.robo.chance >= 0.55 ? 'good' : p.robo.chance <= 0.45 ? 'bad' : ''}">🤖 <b>Robo-analyst:</b> ${esc(p.robo.call)} —
      ${pct(p.robo.chance, 0).replace('+', '')} chance it's higher in 5 days. <span class="muted">It's right only about 55% of the time: treat it as a coin with a slight bend.</span></div>` : '';
  const pos = p.position ? `<div class="summary-rows"><div class="row"><span>You hold</span><b>${p.position.qty} shares</b></div>
      <div class="row"><span>Average cost</span><b>${price(p.position.avg)}</b></div></div>` : '<p class="muted">You don\'t own any yet.</p>';
  const news = p.news.length ? p.news.map((n) => `<div style="margin-bottom:8px"><div class="muted" style="font-size:11.5px">${esc(n.date)} ${esc(n.time)}</div>
      <div>${esc(n.headline)}</div></div>`).join('') : '<p class="muted">No news about it so far.</p>';
  side.innerHTML = `<h2>Your position</h2>${pos}${robo}<h2 style="margin-top:14px">News</h2>${news}`;
}
