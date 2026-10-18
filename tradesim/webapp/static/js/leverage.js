// The Leverage page: what borrowing to invest really does. Four ideas, your margin account,
// a calculator to feel the maths, and the Leverage Lab replaying this market with 1×–5×.

import { getJSON } from './api.js';
import { run } from './actions.js';
import { store, onState } from './store.js';
import { money, pct, direction, esc } from './fmt.js';
import { LineChart, chartBox } from './chart.js';

const COLOURS = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181'];
let section, chart;
let labSymbol = null;
let lab = null;
let lastDay = null;
const calc = { leverage: 2, move: -10 };

export function mount(el) {
  section = el;
  const options = store.universe.symbols.map((r) => `<option value="${r.symbol}">${r.symbol} — ${esc(r.name)}</option>`).join('');
  section.innerHTML = `
    <div class="page-head"><div><h1>Leverage: borrowed money cuts both ways</h1>
      <p>A margin account lets you borrow from the broker to buy more than your cash allows. It makes good days better
      and bad days much worse. Try it here with pretend money before you ever think about it with real money.</p></div></div>
    <div class="concepts">
      <div class="concept"><div class="icon">🔍</div><h3>It multiplies everything</h3><p>At 2×, a 10% rise is +20% on your money, and a 10% fall is −20%. The market doesn't care whose money it is.</p></div>
      <div class="concept"><div class="icon">💸</div><h3>Borrowing isn't free</h3><p>The loan costs <b>${(store.universe.margin_rate * 100).toFixed(0)}% a year</b>, charged every night, win or lose. Holding for months eats into gains.</p></div>
      <div class="concept"><div class="icon">📞</div><h3>Margin calls sell for you</h3><p>If your own money falls below the broker's minimum, it sells your shares at the worst moment, so you can't wait for the recovery.</p></div>
      <div class="concept"><div class="icon">🎢</div><h3>2× funds drift away</h3><p>Leveraged ETFs reset every day. In a zig-zag market they lose money even when the market ends flat: volatility decay.</p></div>
    </div>
    <div class="grid cols-2">
      <div class="card"><h2>Your margin account</h2>
        <p class="secondary" style="margin-top:0">How much may the broker lend you? 1× = cash only. ${store.universe.max_leverage}× = up to ${store.universe.max_leverage - 1} borrowed dollars for every dollar of yours.</p>
        <div class="lev-picker" data-f="picker">${Array.from({ length: store.universe.max_leverage }, (_, i) => `<button data-lev="${i + 1}">${i + 1}×</button>`).join('')}</div>
        <div data-f="account" style="margin-top:12px"></div>
      </div>
      <div class="card"><h2>Try it: what does a move do to <i>your</i> money?</h2>
        <div class="calc">
          <div>
            <div class="slider"><div class="top"><span>Leverage</span><b data-f="calc-lev"></b></div>
              <input type="range" min="1" max="${store.universe.max_leverage}" step="0.5" value="${calc.leverage}" data-calc="leverage" aria-label="Leverage"></div>
            <div class="slider"><div class="top"><span>The shares move</span><b data-f="calc-move"></b></div>
              <input type="range" min="-40" max="40" step="1" value="${calc.move}" data-calc="move" aria-label="Price move in percent"></div>
          </div>
          <div data-f="calc-out"></div>
        </div>
      </div>
    </div>
    <div class="card" style="margin-top:12px">
      <div class="page-head" style="margin-bottom:8px"><div><h2 style="margin:0">🧪 Leverage Lab — replay this market with borrowed money</h2>
        <p>$5,000 of your own money put into one symbol at the start of the window and held: no borrowing, 2×, 3× and 5× on margin
        (same broker rules as your game, checked at each close), and a 2× fund that resets every day.</p></div>
        <select class="symbol-picker" data-f="lab-symbol" aria-label="Symbol for the Leverage Lab">${options}</select></div>
      <div class="legend" data-f="lab-legend"></div>
      ${chartBox(320, 'Leverage Lab: equity of each way of holding')}
      <div class="grid cols-main-side" style="margin-top:12px"><div data-f="lab-table"></div><div data-f="lab-lessons"></div></div>
    </div>
    <div class="card" style="margin-top:12px"><h2>How small a fall hurts at each leverage</h2><div data-f="risk"></div>
      <p class="muted" style="margin:8px 0 0">The broker steps in when you've lost half of your starting cushion: maintenance = 50% ÷ leverage.
      Wipe-out = 1 ÷ leverage. At 5×, a 20% fall loses everything you put in.</p></div>`;
  chart = new LineChart(section.querySelector('.chart-wrap'));
  section.querySelectorAll('[data-lev]').forEach((b) => b.addEventListener('click', () => run(`leverage ${b.dataset.lev}`)));
  section.querySelectorAll('[data-calc]').forEach((input) => input.addEventListener('input', () => {
    calc[input.dataset.calc] = Number(input.value);
    drawCalc();
  }));
  section.querySelector('[data-f="lab-symbol"]').addEventListener('change', (e) => { labSymbol = e.target.value; loadLab(); });
  onState(() => {
    if (section.hidden) return;
    drawAccount();
    if (store.state.clock.day !== lastDay) loadLab();
  });
}

export function show() {
  labSymbol ||= store.universe.index;
  section.querySelector('[data-f="lab-symbol"]').value = labSymbol;
  drawAccount();
  drawCalc();
  loadLab();
}

function drawAccount() {
  const a = store.state.account;
  section.querySelectorAll('[data-lev]').forEach((b) => b.setAttribute('aria-pressed', String(Number(b.dataset.lev) === a.leverage)));
  const nightly = a.loan * store.universe.margin_rate / 252;
  const used = a.used === null ? Infinity : a.used;
  // Cushion: your money as a share of what you hold, against the broker's minimum
  const level = a.invested > 0 ? Math.max(0, a.equity / a.invested) : 1;
  const maint = a.maintenance;
  section.querySelector('[data-f="account"]').innerHTML = `
    <dl class="kv">
      <dt>Using now</dt><dd>${used === Infinity ? '∞' : used.toFixed(2)}× <span class="muted" style="font-weight:400">of ${a.leverage}× allowed</span></dd>
      <dt>Buying power</dt><dd>${money(a.buying_power)}</dd>
      <dt>Loan</dt><dd class="${a.loan > 0 ? 'down' : ''}">${money(a.loan)}</dd>
      <dt>Interest</dt><dd>${money(nightly)} a night · ${money(a.interest)} so far</dd>
      <dt>Margin calls so far</dt><dd class="${a.margin_calls ? 'down' : ''}">${a.margin_calls}</dd>
    </dl>
    <div class="cushion" title="Your own money as a share of your holdings">
      <div class="secondary" style="font-size:12px;margin-bottom:4px">${a.loan > 0
        ? `Safety cushion: your own money is <b>${pct(level, 0).replace('+', '')}</b> of your holdings · margin call below
           <b class="down">${pct(maint, 0).replace('+', '')}</b> (a ${pct(a.room, 1).replace('+', '')} fall away)`
        : 'Safety cushion: <b>full</b> — you owe nothing, so no margin call can happen.'}</div>
      <div class="track"><div class="fill" style="width:${a.loan > 0 ? Math.min(100, level * 100) : 100}%;background:${a.loan > 0 && a.room < 0.1 ? 'var(--down)' : a.loan > 0 ? 'var(--warn)' : 'var(--up)'}"></div>
        ${a.loan > 0 ? `<div class="line" style="left:${maint * 100}%"></div>` : ''}</div>
      <div class="labels"><span>0% (wiped out)</span><span>100% (no loan)</span></div>
    </div>
    ${a.loan > 0 ? '' : '<p class="muted" style="margin:10px 0 0">Pick 2× above, then buy something on the board: the ticket shows how much is borrowed.</p>'}`;
}

function drawCalc() {
  const { leverage: L, move } = calc;
  const m = move / 100;
  const own = 10000;
  const holdings = own * L, loan = own * (L - 1);
  const after = own * (1 + L * m);
  const callAt = L > 1 ? 1 / (2 * L - 1) : null;
  const wipeAt = 1 / L;
  section.querySelector('[data-f="calc-lev"]').textContent = `${L}×`;
  section.querySelector('[data-f="calc-move"]').innerHTML = `<span class="${direction(m, 0)}">${pct(m, 0)}</span>`;
  const scale = Math.max(holdings, holdings * (1 + m), 1);
  const yours = Math.max(0, after);
  let status = '';
  if (after <= 0) status = `<div class="lesson bad">💀 <b>Wiped out.</b> A ${pct(wipeAt, 0).replace('+', '')} fall erases your money at ${L}×. You'd still owe the broker ${money(-after, 0)}.</div>`;
  else if (callAt !== null && -m >= callAt) status = `<div class="lesson bad">📞 <b>Margin call.</b> The broker steps in after a ${pct(callAt, 1).replace('+', '')} fall at ${L}× and sells your shares.</div>`;
  else if (m > 0 && L > 1) status = `<div class="lesson good">Leverage worked this time: ${pct(L * m, 0)} instead of ${pct(m, 0)}. Same bet, the other way, costs the same multiple.</div>`;
  else if (L === 1) status = '<div class="lesson">No loan: you can never lose more than you put in, and nobody can force you to sell.</div>';
  section.querySelector('[data-f="calc-out"]').innerHTML = `
    <div class="secondary" style="font-size:12px">Before: ${money(own, 0)} yours ${L > 1 ? `+ ${money(loan, 0)} borrowed` : ''} = ${money(holdings, 0)} of shares</div>
    <div class="stack" style="margin:4px 0 10px"><div class="own" style="flex-basis:${own / scale * 100}%">yours</div>${L > 1 ? `<div class="borrowed" style="flex-basis:${loan / scale * 100}%">borrowed</div>` : ''}</div>
    <div class="secondary" style="font-size:12px">After a ${pct(m, 0)} move: shares worth ${money(holdings * (1 + m), 0)}, still owing ${money(loan, 0)}</div>
    <div class="stack" style="margin:4px 0 6px"><div class="${after >= own ? 'own' : 'lost'}" style="flex-basis:${yours / scale * 100}%">${yours > 0 ? 'yours' : ''}</div>${L > 1 ? `<div class="borrowed" style="flex-basis:${loan / scale * 100}%">borrowed</div>` : ''}</div>
    <div class="result-big ${direction(after - own, 0)}">${money(after, 0)} <span style="font-size:16px">(${pct(after / own - 1, 0)})</span></div>
    <div class="muted">your ${money(own, 0)} after a ${pct(m, 0)} move at ${L}× (before interest)</div>${status}`;
}

async function loadLab() {
  lastDay = store.state.clock.day;
  try {
    lab = await getJSON('/api/leverage', { symbol: labSymbol || store.universe.index });
  } catch (error) {
    section.querySelector('[data-f="lab-table"]').innerHTML = `<div class="empty">${esc(error.message)}</div>`;
    return;
  }
  drawLab();
  drawRisk();
}

function drawLab() {
  const series = lab.runs.map((r, i) => ({ name: r.label, values: r.values, color: COLOURS[i], dash: r.label.includes('daily') }));
  const marks = lab.runs.flatMap((r, i) => (r.called_index === null ? [] : [{ series: i, index: r.called_index, text: `📞 ${r.label}: margin call` }]));
  section.querySelector('[data-f="lab-legend"]').innerHTML = series.map((s) => `<span class="${s.dash ? 'dashed' : ''}" style="--c:${s.color}">${esc(s.name)}</span>`).join('') +
    '<span style="--c:var(--down)">● margin call</span>';
  chart.setData({ labels: lab.labels, series, marks, format: (v) => money(v, 0), baseline: 5000 });
  section.querySelector('[data-f="lab-table"]').innerHTML = `<table class="data"><thead><tr><th>Way</th><th>Final</th><th>Return</th><th>Max drop</th><th>Margin call</th><th>Interest</th></tr></thead>
    <tbody>${lab.runs.map((r, i) => `<tr><td><i class="sw" style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${COLOURS[i]};margin-right:6px"></i>${esc(r.label)}</td>
      <td>${money(r.values[r.values.length - 1], 0)}</td><td class="${direction(r.return, 0)}">${pct(r.return, 1)}</td>
      <td>${pct(r.drop, 1).replace('+', '')}</td><td class="${r.called_label ? 'down' : 'muted'}">${r.called_label ? esc(r.called_label) : '—'}</td><td>${money(r.interest, 0)}</td></tr>`).join('')}</tbody></table>`;
  section.querySelector('[data-f="lab-lessons"]').innerHTML = lab.lessons.map((l) => `<div class="lesson">${esc(l)}</div>`).join('');
}

function drawRisk() {
  const own = 10000;
  const mine = store.state.account.leverage;
  section.querySelector('[data-f="risk"]').innerHTML = `<table class="data"><thead><tr><th>Leverage</th><th>$10,000 of yours buys</th>
      <th>Broker's minimum (maintenance)</th><th>Margin call after a fall of</th><th>Wiped out after a fall of</th></tr></thead>
    <tbody>${lab.risk.map((r) => `<tr class="${r.leverage === mine ? 'mine' : ''}"><td>${r.leverage}×${r.leverage === mine ? ' (you)' : ''}</td><td>${money(own * r.leverage, 0)}</td>
      <td>${r.leverage === 1 ? '—' : pct(r.maintenance, 0).replace('+', '')}</td><td class="${r.leverage === 1 ? '' : 'down'}">${r.leverage === 1 ? 'never (no loan)' : pct(r.call, 1).replace('+', '')}</td>
      <td class="down">${pct(r.wipe, 0).replace('+', '')}</td></tr>`).join('')}</tbody></table>`;
}
