// The report dialog's body, drawn from /api/report: grade, money, challenge goals,
// Trade Coach tips and (once the game is over) the market's hidden story.

import { money, pct, direction, esc } from './fmt.js';

const plain = (fraction, dp = 1) => pct(fraction, dp).replace('+', '');
const tone = (value) => direction(value, 0);

/** One "label  value" line of the money summary. */
const line = (label, value) => `<dt>${label}</dt><dd>${value}</dd>`;

function holdings(r) {
  if (!r.best) return line('Holdings', 'none open');
  const [best, worst] = [r.best, r.worst];
  const show = ([symbol, percent]) => `${symbol} <span class="${tone(percent)}">${pct(percent / 100, 1)}</span>`;
  return best[0] === worst[0] ? line('Holding', show(best)) : line('Best / worst holding', `${show(best)} · ${show(worst)}`);
}

function challenge(c) {
  const verdict = !c.over ? `<p class="muted">Goals are checked on the final day (day ${c.final_day}).</p>`
    : c.won ? `<div class="lesson good"><b>🏆 Challenge complete!</b> ${esc(c.lesson)}</div>`
      : `<div class="lesson bad"><b>✗ Not this time</b>: try again from the Goals page. ${esc(c.lesson)}</div>`;
  return `<h3>🎯 ${esc(c.title)}</h3>
    ${c.goals.map((g) => `<div>${g.passed ? '✅' : '⬜'} ${esc(g.text)} <span class="muted">· now ${esc(g.now)}</span></div>`).join('')}${verdict}`;
}

function story(s) {
  return `<h3>📖 The market's story: hidden moods, revealed</h3>
    <div class="timeline" title="One block per day">${s.path.map((name) => `<i class="mood-${name}"></i>`).join('')}</div>
    <table class="data"><tbody>${s.spells.map((m) => `<tr><td class="left">${m.emoji} ${esc(m.label)}</td>
      <td>day ${m.first} → ${m.last}</td><td>${esc(s.index)} <span class="${tone(m.move)}">${pct(m.move, 1)}</span></td></tr>`).join('')}</tbody></table>
    ${s.abouts.map((a) => `<p class="secondary" style="margin:4px 0">${a.emoji} ${esc(a.text)}</p>`).join('')}`;
}

/** The HTML for the report dialog, given the reply of /api/report. */
export function reportHTML(r) {
  const tips = r.tips.map((t) => `<div class="lesson ${t.severity === 'praise' ? 'good' : t.severity === 'warn' ? 'bad' : ''}">${esc(t.text)}</div>`).join('');
  return `<div class="lesson ${r.profit ? 'good' : 'bad'}"><b>Grade ${esc(r.grade)}</b> · ${esc(r.verdict)}</div>
    <dl class="kv" style="max-width:560px">
      ${line('Starting cash', money(r.start))}
      ${line('Equity', `${money(r.equity)} <span class="${tone(r.return)}">${pct(r.return, 1)}</span>`)}
      ${line('Whole market', `${esc(r.index)} <span class="${tone(r.market_return)}">${pct(r.market_return, 1)}</span> over the same days`)}
      ${line('Realised / unrealised', `${money(r.realised)} · ${money(r.unrealised)}`)}
      ${line('Fees paid', money(r.fees))}
      ${holdings(r)}
      ${line('Biggest drop from a peak', plain(r.drawdown, 1))}
      ${line('Trades / badges', `${r.trades} / ${r.badges}`)}
    </dl>
    ${r.challenge ? challenge(r.challenge) : ''}
    ${tips ? `<h3>🧑‍🏫 Trade Coach</h3>${tips}` : ''}
    ${r.story ? story(r.story) : ''}`;
}
