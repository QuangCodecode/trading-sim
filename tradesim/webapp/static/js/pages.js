// The smaller pages: News (+ Headline Lab), Labs (diversification, what-if, Monte Carlo),
// Robo-analyst, Learn (quiz, badges, glossary) and Challenges.
// Each page is {mount(section), show(arg)}; app.js calls them.

import { getJSON } from './api.js';
import { run, visit } from './actions.js';
import { store, onState } from './store.js';
import { money, pct, direction, esc } from './fmt.js';
import { LineChart, chartBox } from './chart.js';
import { openDialog, closeDialog } from './ui.js';

const COLOURS = ['#3987e5', '#d95926', '#199e70', '#c98500'];
const plain = (fraction, dp = 1) => pct(fraction, dp).replace('+', '');

/** The word counter's reading of a headline the player typed (the `hl` command's result). */
function headlineResult(r) {
  const tone = r.label === 'positive' ? 'up' : r.label === 'negative' ? 'down' : 'flat';
  return `<div class="lesson"><b class="${tone}">${esc(r.label)}</b> · the word counter found: ${esc(r.found)}.
    <p class="secondary" style="margin:4px 0 0">It only adds up listed words. Read the whole sentence yourself: is it a surprise, and a good or a bad one?</p></div>`;
}

/** The 200-markets table (the `lab mc` command's result). */
function monteCarloTable(r) {
  const row = (label, cell) => `<tr><td class="left">${label}</td>${r.sides.map((s) => `<td>${cell(s)}</td>`).join('')}</tr>`;
  const [stock, fund] = r.sides;
  return `<table class="data"><thead><tr><th class="left"></th>${r.sides.map((s) => `<th>${s.symbol}</th>`).join('')}</tr></thead><tbody>
      ${row('Average return', (s) => `<span class="${direction(s.average, 0)}">${pct(s.average, 1)}</span>`)}
      ${row(`Lost more than ${plain(-r.threshold, 0)}`, (s) => `${plain(s.big_loss, 0)} of runs`)}
      ${row('Best run', (s) => pct(s.best, 1))}${row('Worst run', (s) => pct(s.worst, 1))}</tbody></table>
    <div class="lesson">In ${r.runs} simulated markets, ${stock.symbol} lost more than ${plain(-r.threshold, 0)} in ${plain(stock.big_loss, 0)} of them;
      ${fund.symbol} in ${plain(fund.big_loss, 0)}. Diversification is about odds, not luck.</div>`;
}

/** Right or wrong, the explanation and the running score (the `quiz` command's result). */
function quizFeedback(r) {
  return `<div class="lesson ${r.correct ? 'good' : 'bad'}"><b>${r.correct ? '✔ Correct!' : `✗ Not quite — the answer is ${r.answer}.`}</b>
    <p style="margin:4px 0">${esc(r.explain)}</p><span class="muted">Score ${r.right}/${r.asked}. The next question is above.</span></div>`;
}

/** Re-run `load` when a new day closes while the page is open. */
function reloadOnNewDay(section, load) {
  let day = null;
  onState((state) => {
    if (section.hidden || state.clock.day === day) return;
    day = state.clock.day;
    load();
  });
}

// ---------------------------------------------------------------- News
export const news = {
  mount(section) {
    this.section = section;
    section.innerHTML = `
      <div class="page-head"><div><h1>News</h1><p>Headlines move prices: one company, one sector or the whole market.
        A "sentence reader" (its answers were worked out beforehand) and a simple keyword counter each guess whether a headline is good or bad news.
        After the closing bell you see what really happened.</p></div><div data-f="score"></div></div>
      <div class="grid cols-main-side">
        <div class="card"><div data-f="list"></div></div>
        <div><div class="card"><h2>🗞️ Headline Lab: test your own</h2>
          <p class="secondary" style="margin-top:0">Write a headline and see what the word counter makes of it. Does it get the tricky ones right?</p>
          <div class="input-row" style="margin-top:0"><input data-f="hl" placeholder="e.g. Losses narrow sharply at chipmaker" maxlength="200" aria-label="Your headline">
            <button class="btn primary" data-f="hl-go">Test</button></div><div data-f="hl-out" style="margin-top:10px"></div></div>
          <div class="card"><h2>Why news moves prices</h2><p class="secondary" style="margin:0">Prices move on <b>surprises</b>.
            "Profits fall less than feared" is good news: investors expected worse. That is why counting good and bad words often gets it wrong.</p></div></div>
      </div>`;
    const go = async () => {
      const text = section.querySelector('[data-f="hl"]').value.trim();
      if (!text) return;
      const reply = await run(`hl "${text.replace(/"/g, "'")}"`, { quiet: true });
      section.querySelector('[data-f="hl-out"]').innerHTML = reply.error ? `<p class="down">${esc(reply.error)}</p>` : headlineResult(reply.result);
    };
    section.querySelector('[data-f="hl-go"]').addEventListener('click', go);
    section.querySelector('[data-f="hl"]').addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
    let seen = -1;
    onState(() => {
      if (section.hidden) return;
      const count = store.lastNotice;
      if (count !== seen) { seen = count; this.load(); }
    });
  },
  show() { visit('news'); this.load(); },
  async load() {
    const { news: items } = await getJSON('/api/news');
    const list = this.section.querySelector('[data-f="list"]');
    if (!items.length) {
      list.innerHTML = '<div class="empty">No news yet. Open the market: about one day in four brings a headline.</div>';
      this.section.querySelector('[data-f="score"]').innerHTML = '';
      return;
    }
    const mark = (label, truth) => (truth === null ? '' : label === truth ? ' <span class="up">✔</span>' : ' <span class="down">✗</span>');
    list.innerHTML = items.map((n) => `<div class="news-item">
        <div class="when">${esc(n.date)}<br>${esc(n.time)}<br><span class="chip">${n.scope === 'market' ? 'Whole market' : esc(n.target)}</span></div>
        <div><div class="headline">${esc(n.headline)}</div><div class="why">${esc(n.explanation)}</div>
          ${n.moves.length ? `<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">${n.moves.map(([s, m]) => `<a class="chip ${direction(m, 0)}" href="#trade/${s}">${s} ${pct(m / 100, 1)}</a>`).join('')}</div>`
            : '<div class="muted" style="margin-top:6px;font-size:12px">Breaking today: the full effect is known at the close.</div>'}</div>
        <dl class="verdicts"><dt>Reader</dt><dd>${n.reading ? `${esc(n.reading.label)} ${plain(n.reading.confidence, 0)}${mark(n.reading.label, n.truth)}` : '<span class="muted">no reading</span>'}</dd>
          <dt>Keywords</dt><dd>${esc(n.words)}${mark(n.words, n.truth)}</dd>
          <dt>Really</dt><dd>${n.truth ? `<b class="${n.truth === 'positive' ? 'up' : 'down'}">${n.truth}</b>` : '<span class="muted">after the close</span>'}</dd></dl>
      </div>`).join('');
    const closed = items.filter((n) => n.truth);
    const read = closed.filter((n) => n.reading && n.reading.label === n.truth).length;
    const words = closed.filter((n) => n.words === n.truth).length;
    this.section.querySelector('[data-f="score"]').innerHTML = closed.length
      ? `<div class="chip">Score so far · reader ${read}/${closed.length} · keywords ${words}/${closed.length}</div>` : '';
  },
};

// ---------------------------------------------------------------- Labs
export const labs = {
  mount(section) {
    this.section = section;
    this.tab = 'div';
    const stocks = store.universe.symbols.filter((r) => !r.etf).map((r) => `<option value="${r.symbol}">${r.symbol} — ${esc(r.name)}</option>`).join('');
    const etfs = store.universe.symbols.filter((r) => r.etf).map((r) => `<option value="${r.symbol}">${r.symbol} — ${esc(r.name)}</option>`).join('');
    section.innerHTML = `
      <div class="page-head"><div><h1>Labs</h1><p>Experiments on this very market: does spreading your money out help, and how would other strategies have done?</p></div></div>
      <div class="tabs" role="tablist"><button role="tab" data-tab="div">Diversification Lab</button><button role="tab" data-tab="whatif">What-if Replay</button>
        <button role="tab" data-tab="mc">200 markets (Monte Carlo)</button></div>
      <div data-panel="div">
        <div class="chart-toolbar"><label>One stock <select class="symbol-picker" data-f="stock">${stocks}</select></label>
          <label>vs fund <select class="symbol-picker" data-f="etf">${etfs}</select></label>
          <span class="muted">$5,000 in each, over the last 60 days (including the history before day 0)</span></div>
        <div class="grid cols-main-side"><div class="card"><div class="legend" data-f="div-legend"></div>${chartBox(300, 'One stock compared with an ETF')}</div>
          <div class="card" data-f="div-stats"></div></div>
      </div>
      <div data-panel="whatif" hidden><div class="grid cols-main-side"><div class="card"><div class="legend" data-f="wi-legend"></div>${chartBox(300, 'Strategy comparison')}</div>
        <div class="card" data-f="wi-lessons"></div></div><div class="card" style="margin-top:12px" data-f="wi-table"></div></div>
      <div data-panel="mc" hidden><div class="card"><p class="secondary" style="margin-top:0">One market can be lucky. This builds 200 brand-new markets
        and compares one stock with MIX6 in every one of them.</p><button class="btn primary" data-f="mc-go">Run 200 markets with NVDA</button>
        <div data-f="mc-out" class="report" style="margin-top:12px"></div></div></div>`;
    this.divChart = new LineChart(section.querySelector('[data-panel="div"] .chart-wrap'));
    this.wiChart = new LineChart(section.querySelector('[data-panel="whatif"] .chart-wrap'));
    section.querySelector('[data-f="stock"]').value = 'NVDA';
    section.querySelector('[data-f="etf"]').value = 'MIX6';
    section.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', () => { this.tab = b.dataset.tab; this.show(); }));
    section.querySelectorAll('[data-f="stock"], [data-f="etf"]').forEach((s) => s.addEventListener('change', () => this.loadDiv()));
    section.querySelector('[data-f="mc-go"]').addEventListener('click', async () => {
      const out = section.querySelector('[data-f="mc-out"]');
      out.innerHTML = '<p class="muted">Building 200 markets…</p>';
      const reply = await run('lab mc NVDA', { quiet: true });
      out.innerHTML = reply.error ? `<p class="down">${esc(reply.error)}</p>` : monteCarloTable(reply.result);
    });
    reloadOnNewDay(section, () => this.show());
  },
  show() {
    this.section.querySelectorAll('[data-tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === this.tab)));
    this.section.querySelectorAll('[data-panel]').forEach((p) => { p.hidden = p.dataset.panel !== this.tab; });
    if (this.tab === 'div') { visit('lab'); this.loadDiv(); }
    if (this.tab === 'whatif') { visit('whatif'); this.loadWhatIf(); }
  },
  async loadDiv() {
    const stock = this.section.querySelector('[data-f="stock"]').value;
    const etf = this.section.querySelector('[data-f="etf"]').value;
    let d;
    try { d = await getJSON('/api/diversification', { stock, etf }); } catch (error) {
      this.section.querySelector('[data-f="div-stats"]').innerHTML = `<div class="empty">${esc(error.message)}</div>`;
      return;
    }
    const [a, b] = d.sides;
    this.section.querySelector('[data-f="div-legend"]').innerHTML = `<span style="--c:${COLOURS[0]}">${a.symbol}</span><span style="--c:${COLOURS[1]}">${b.symbol}</span>`;
    this.divChart.setData({ labels: d.labels, series: [{ name: a.symbol, values: a.values, color: COLOURS[0] }, { name: b.symbol, values: b.values, color: COLOURS[1] }],
      format: (v) => money(v, 0), baseline: d.amount });
    const row = (label, f) => `<tr><td>${label}</td><td>${f(a)}</td><td>${f(b)}</td></tr>`;
    this.section.querySelector('[data-f="div-stats"]').innerHTML = `<table class="data"><thead><tr><th></th><th>${a.symbol}</th><th>${b.symbol}</th></tr></thead><tbody>
        ${row('Return', (s) => `<span class="${direction(s.return, 0)}">${pct(s.return, 1)}</span>`)}
        ${row('Typical daily swing', (s) => plain(s.vol, 2))}
        ${row('Worst day', (s) => `<span class="down">${pct(s.worst, 1)}</span>`)}
        ${row('Biggest fall from a peak', (s) => plain(s.drop, 1))}</tbody></table>
      ${d.verdict.map((v) => `<div class="lesson">${esc(v.replace(/\*/g, ''))}</div>`).join('')}`;
  },
  async loadWhatIf() {
    let d;
    try { d = await getJSON('/api/whatif'); } catch (error) {
      this.section.querySelector('[data-f="wi-table"]').innerHTML = `<div class="empty">${esc(error.message)}</div>`;
      this.section.querySelector('[data-f="wi-lessons"]').innerHTML = '';
      this.wiChart.setData({ labels: [], series: [] });
      return;
    }
    const pick = [d.results.find((r) => r.name === d.yours), d.results.find((r) => r.name.startsWith('Hold MKT')), d.results[0], d.results[d.results.length - 1]];
    const shown = [...new Set(pick.filter(Boolean))].slice(0, 4);
    this.section.querySelector('[data-f="wi-legend"]').innerHTML = shown.map((r, i) => `<span style="--c:${COLOURS[i]}">${esc(r.name)}</span>`).join('');
    this.wiChart.setData({ labels: d.labels, series: shown.map((r, i) => ({ name: r.name, values: r.curve, color: COLOURS[i] })), format: (v) => money(v, 0), baseline: 10000 });
    this.section.querySelector('[data-f="wi-lessons"]').innerHTML = `<h2>What it shows</h2>${d.lessons.map((l) => `<div class="lesson">${esc(l)}</div>`).join('')}`;
    this.section.querySelector('[data-f="wi-table"]').innerHTML = `<h2>Every strategy on this market, day 0 → today, $10,000 each</h2>
      <table class="data"><thead><tr><th>#</th><th class="left">Strategy</th><th class="left">How it works</th><th>Final</th><th>Return</th><th>Max drop</th><th>Trades</th><th>Fees</th></tr></thead>
      <tbody>${d.results.map((r, i) => `<tr class="${r.name === d.yours ? 'mine' : ''}"><td>${i + 1}</td><td class="left">${esc(r.name)}</td>
        <td class="left secondary" style="white-space:normal">${esc(r.about)}</td><td>${money(r.final, 0)}</td>
        <td class="${direction(r.return, 0)}">${pct(r.return, 1)}</td><td>${plain(r.drop)}</td><td>${r.trades}</td><td>${money(r.fees, 0)}</td></tr>`).join('')}</tbody></table>`;
  },
};

// ---------------------------------------------------------------- Robo-analyst
export const robo = {
  mount(section) {
    this.section = section;
    section.innerHTML = `<div class="page-head"><div><h1>🤖 Robo-analyst</h1><p>Two tiny machine-learning models (logistic regressions written in plain Python)
      read the charts. One guesses the market's hidden mood, the other whether each price will be higher in 5 days. Both were tested honestly on markets they never saw.</p></div></div>
      <div data-f="body"></div>`;
    reloadOnNewDay(section, () => this.load());
  },
  show() { visit('robo'); this.load(); },
  async load() {
    const d = await getJSON('/api/robo');
    const body = this.section.querySelector('[data-f="body"]');
    if (!d.ready) { body.innerHTML = '<div class="card empty">The models need 20 days of history first.</div>'; return; }
    const biggest = Math.max(...d.reasons.map(([, v]) => Math.abs(v)), 0.01);
    const list = (items, up) => `<table class="data"><tbody>${items.map((o) => `<tr class="clickable" onclick="location.hash='#trade/${o.s}'">
        <td><b>${o.s}</b> <span class="muted">${esc(store.info[o.s].name)}</span></td>
        <td><span class="bar-cell" style="width:${Math.abs(o.chance - 0.5) * 400}px;background:${up ? 'var(--up)' : 'var(--down)'}"></span></td>
        <td>${plain(o.chance, 0)} up</td></tr>`).join('')}</tbody></table>`;
    const mr = d.mood_report, pr = d.price_report;
    body.innerHTML = `<div class="grid cols-2">
        <div class="card"><h2>Market mood detector</h2>
          <div class="result-big ${d.downturn >= 0.6 ? 'down' : d.downturn <= 0.3 ? 'up' : 'flat'}">${esc(d.mood_call)}</div>
          <div class="secondary">${plain(d.downturn, 0)} chance the market is in a bear market or crash right now</div>
          <div class="meter" style="margin:10px 0"><div style="width:${d.downturn * 100}%;background:${d.downturn >= 0.6 ? 'var(--down)' : d.downturn <= 0.3 ? 'var(--up)' : 'var(--warn)'}"></div></div>
          <h3>Why it thinks so</h3>
          <table class="data"><tbody>${d.reasons.map(([name, v]) => `<tr><td>${esc(name)}</td><td><span class="bar-cell" style="width:${Math.abs(v) / biggest * 120}px;background:${v > 0 ? 'var(--down)' : 'var(--up)'}"></span></td>
            <td class="${v > 0 ? 'down' : 'up'}">${v > 0 ? 'more worried' : 'calmer'}</td></tr>`).join('')}</tbody></table>
          <p class="muted" style="font-size:12px">On unseen markets it was right ${plain(mr.test_accuracy, 0)} of the time (always saying "no downturn" scores ${plain(mr.lazy_accuracy, 0)}).</p></div>
        <div class="card"><h2>5-day price forecaster</h2>
          <div class="lesson">On unseen markets it was right only ${plain(pr.test_accuracy, 0)} of the time, barely better than always guessing "up" (${plain(pr.lazy_accuracy, 0)}).
            Short-term prices are mostly noise: be suspicious of anyone (or any robot) who says otherwise.</div>
          <div class="grid cols-2"><div><h3 class="up">Leaning up</h3>${list(d.up, true)}</div><div><h3 class="down">Leaning down</h3>${list(d.down, false)}</div></div></div>
      </div>`;
  },
};

// ---------------------------------------------------------------- Learn
export const learn = {
  mount(section) {
    this.section = section;
    section.innerHTML = `<div class="page-head"><div><h1>Learn</h1><p>Quiz yourself, collect badges and look up any investing word.</p></div></div>
      <div class="grid cols-2"><div class="card" data-f="quiz"></div><div class="card"><h2>🏅 Badges</h2><div class="badges" data-f="badges"></div></div></div>
      <div class="card" style="margin-top:12px"><div class="page-head" style="margin-bottom:10px"><h2 style="margin:0">📖 Glossary</h2>
        <label class="search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg><input data-f="q" placeholder="Search terms" aria-label="Search the glossary"></label></div>
        <div class="terms" data-f="terms"></div></div>`;
    section.querySelector('[data-f="q"]').addEventListener('input', () => this.drawTerms());
    this.feedback = '';
  },
  show() { this.load(); },
  async load() {
    this.data = await getJSON('/api/learn');
    this.drawQuiz();
    this.drawTerms();
    this.section.querySelector('[data-f="badges"]').innerHTML = this.data.badges.map((b) => `<div class="badge ${b.won ? '' : 'locked'}" title="${esc(b.how)}">
      <div class="e">${b.won ? b.emoji : '🔒'}</div><div class="t">${esc(b.title)}</div><div class="h">${esc(b.how)}</div></div>`).join('');
  },
  drawQuiz() {
    const q = this.data.quiz;
    const box = this.section.querySelector('[data-f="quiz"]');
    box.innerHTML = `<h2>🎓 Quiz <span class="muted" style="font-weight:400">· question ${q.number + 1} of ${q.total} · score ${q.right}/${q.answered}</span></h2>
      <p style="font-size:15px;font-weight:600">${esc(q.question)}</p>
      ${q.options.map((o, i) => `<button class="quiz-option" data-letter="${'ABCD'[i]}"><b>${'ABCD'[i]}</b>${esc(o)}</button>`).join('')}
      <div data-f="feedback" class="report">${this.feedback}</div>`;
    box.querySelectorAll('[data-letter]').forEach((b) => b.addEventListener('click', async () => {
      const reply = await run(`quiz ${b.dataset.letter}`);
      this.feedback = reply.error ? '' : quizFeedback(reply.result);
      this.load();
    }));
  },
  drawTerms() {
    if (!this.data) return;
    const q = this.section.querySelector('[data-f="q"]').value.trim().toLowerCase();
    const terms = this.data.terms.filter((t) => !q || `${t.term} ${t.short} ${t.long}`.toLowerCase().includes(q));
    this.section.querySelector('[data-f="terms"]').innerHTML = terms.map((t) => `<div class="term"><h3>${t.emoji} ${esc(t.term)}</h3>
      <p class="short">${esc(t.short)}</p><p class="long">${esc(t.long)}</p><span class="chip">try: ${esc(t.try)}</span></div>`).join('') || '<p class="muted">No term matches.</p>';
  },
};

// ---------------------------------------------------------------- Challenges
export const challenges = {
  mount(section) {
    this.section = section;
    section.innerHTML = `<div class="page-head"><div><h1>🎯 Challenges</h1><p>Fixed markets with a story and a goal. Everyone gets the same market, so you can compare results with classmates.</p></div></div>
      <div data-f="current"></div><div class="grid cols-3" data-f="list"></div>
      <div class="card" style="margin-top:12px"><h2>Free play</h2><p class="secondary">A new random market (or type a seed to replay one, e.g. 42 or 180).</p>
        <div class="input-row" style="max-width:420px"><input data-f="seed" placeholder="Seed (blank = random)" inputmode="numeric" aria-label="Seed">
        <button class="btn primary" data-f="new">New game</button></div></div>`;
    section.querySelector('[data-f="new"]').addEventListener('click', () => {
      const seed = section.querySelector('[data-f="seed"]').value.replace(/\D/g, '');
      this.confirm('a new free-play game', seed ? `new ${seed}` : 'new');
    });
    onState(() => { if (!section.hidden) this.drawCurrent(); });
  },
  show() { this.load(); },
  confirm(what, line) {
    openDialog({
      title: 'Start over?', body: `<p>This ends your current game and starts ${esc(what)}.</p>`,
      foot: '<button class="btn" data-close>Cancel</button><button class="btn primary" data-ok>Start</button>',
      onOpen: (dialog) => dialog.querySelector('[data-ok]').addEventListener('click', async () => {
        closeDialog();
        const reply = await run(line);
        if (!reply.error) location.hash = '#board';
      }),
    });
  },
  async load() {
    const { challenges: list } = await getJSON('/api/challenges');
    this.section.querySelector('[data-f="list"]').innerHTML = list.map((c) => `<div class="card challenge-card ${c.playing ? 'playing' : ''}">
        <div class="e">${c.emoji}</div><h2 style="margin:0">${esc(c.title)}</h2><p class="secondary" style="margin:0">${esc(c.intro)}</p>
        <ul>${c.goals.map((g) => `<li>${esc(g)}</li>`).join('')}</ul>
        ${c.start.length ? `<div class="muted" style="font-size:12px">Starts with: ${c.start.map(esc).join(', ')}</div>` : ''}
        <button class="btn ${c.playing ? '' : 'primary'}" data-id="${c.id}" data-title="${esc(c.title)}">${c.playing ? 'Restart' : 'Start'}</button></div>`).join('');
    this.section.querySelectorAll('[data-id]').forEach((b) => b.addEventListener('click', () => this.confirm(`the "${b.dataset.title}" challenge`, `challenge ${b.dataset.id}`)));
    this.drawCurrent();
  },
  drawCurrent() {
    const c = store.state.clock.challenge;
    this.section.querySelector('[data-f="current"]').innerHTML = c ? `<div class="card" style="margin-bottom:12px"><h2>Now playing: ${c.emoji} ${esc(c.title)}</h2>
      ${c.goals.map((g) => `<div class="row" style="display:flex;gap:8px;padding:3px 0">${g.passed ? '✅' : '⬜'} ${esc(g.text)} <span class="muted">· now ${esc(g.now)}</span></div>`).join('')}
      <p class="muted" style="margin:6px 0 0">Goals are judged on the final day.</p></div>` : '';
  },
};
