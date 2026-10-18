// Hand-drawn canvas charts (no chart library): candlesticks with volume, multi-line charts
// and sparklines. Every chart redraws itself on resize and shows a crosshair tooltip.

import { price as fmtPrice, volume as fmtVolume, pct, esc } from './fmt.js';

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const FONT = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

/** Size the canvas for the screen's pixel density and return a cleared 2D context. */
export function fitCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.font = FONT;
  return { ctx, w, h };
}

/** Round axis steps: 1, 2 or 5 × a power of ten. */
function niceTicks(lo, hi, count) {
  const raw = (hi - lo || 1) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const n = raw / mag;
  const step = (n < 1.5 ? 1 : n < 3 ? 2 : n < 7 ? 5 : 10) * mag;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-6; v += step) out.push(v);
  return out;
}

/** Average of the last `period` closes at each point (null until there are enough). */
export function movingAverage(values, period) {
  let sum = 0;
  return values.map((v, i) => {
    sum += v;
    if (i >= period) sum -= values[i - period];
    return i >= period - 1 ? sum / period : null;
  });
}

function dashed(ctx, x1, y1, x2, y2, color, dash = [4, 4]) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.setLineDash(dash);
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.restore();
}

function tag(ctx, x, y, text, bg, fg = '#fff') {
  const w = ctx.measureText(text).width + 10;
  ctx.fillStyle = bg;
  ctx.fillRect(x, y - 9, w, 18);
  ctx.fillStyle = fg;
  ctx.fillText(text, x + 5, y + 4);
}

/** Put the tooltip next to the cursor, flipped so it stays inside the chart. */
function placeTip(tip, wrap, x, y) {
  tip.style.display = 'block';
  const box = wrap.getBoundingClientRect();
  const left = x + 16 + tip.offsetWidth > box.width ? x - 16 - tip.offsetWidth : x + 16;
  const top = Math.min(Math.max(4, y - tip.offsetHeight / 2), box.height - tip.offsetHeight - 4);
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

/** Shared behaviour: hover tracking, resize redraws, the tooltip element. */
class HoverChart {
  constructor(wrap) {
    this.wrap = wrap;
    this.canvas = wrap.querySelector('canvas');
    this.tip = wrap.querySelector('.tooltip');
    this.hover = null;
    this.data = null;
    this.canvas.addEventListener('mousemove', (e) => {
      const r = this.canvas.getBoundingClientRect();
      this.hover = { x: e.clientX - r.left, y: e.clientY - r.top };
      this.draw();
    });
    this.canvas.addEventListener('mouseleave', () => { this.hover = null; this.draw(); });
    new ResizeObserver(() => this.draw()).observe(this.canvas);
  }

  setData(data) {
    this.data = data;
    this.draw();
  }

  hideTip() {
    if (this.tip) this.tip.style.display = 'none';
  }
}

/**
 * Candlestick (or line) price chart with a volume pane underneath.
 * data = {candles: [{t, k, o, h, l, c, v}], mode: 'candles'|'line', ma: [{period, color}],
 *         volume: bool, ref: number|null, markers: [{k, side, qty, price, forced}], slots: number}
 */
export class PriceChart extends HoverChart {
  draw() {
    if (!this.data) return;
    const { ctx, w, h } = fitCanvas(this.canvas);
    const d = this.data;
    const candles = d.candles;
    const up = css('--up'), down = css('--down'), muted = css('--text-muted'), grid = '#1a1f27';
    const left = 6, right = 66, top = 12, bottom = 22;
    const volH = d.volume ? Math.round((h - top - bottom) * 0.2) : 0;
    const gap = d.volume ? 10 : 0;
    const plotH = h - top - bottom - volH - gap;
    const plotW = w - left - right;
    if (!candles.length) {
      this.hideTip();
      ctx.fillStyle = muted;
      ctx.font = '13px -apple-system, sans-serif';
      ctx.fillText(d.empty || 'No trades yet — open the market to start the clock.', left + 16, top + plotH / 2);
      return;
    }
    const n = Math.max(candles.length, d.slots || 0);
    const slot = plotW / n;
    const xc = (i) => left + slot * (i + 0.5);
    const closes = candles.map((c) => c.c);
    const averages = (d.ma || []).map((m) => ({ ...m, values: movingAverage(closes, m.period) }));

    let lo = Infinity, hi = -Infinity;
    for (const c of candles) {
      lo = Math.min(lo, d.mode === 'line' ? c.c : c.l);
      hi = Math.max(hi, d.mode === 'line' ? c.c : c.h);
    }
    for (const m of averages) for (const v of m.values) if (v !== null) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    if (d.ref) { lo = Math.min(lo, d.ref); hi = Math.max(hi, d.ref); }
    const pad = (hi - lo) * 0.08 || hi * 0.01 || 1;
    lo -= pad; hi += pad;
    const y = (v) => top + (hi - v) / (hi - lo) * plotH;

    // Grid and price axis
    ctx.lineWidth = 1;
    for (const t of niceTicks(lo, hi, 6)) {
      ctx.fillStyle = grid;
      ctx.fillRect(left, Math.round(y(t)) + 0.5, plotW, 1);
      ctx.fillStyle = muted;
      ctx.fillText(fmtPrice(t), left + plotW + 8, y(t) + 4);
    }
    // Time axis: a label roughly every 90px
    const every = Math.max(1, Math.ceil(90 / slot));
    ctx.fillStyle = muted;
    candles.forEach((c, i) => {
      if (i % every === 0) ctx.fillText(c.t, Math.max(left, xc(i) - ctx.measureText(c.t).width / 2), h - 6);
    });

    if (d.ref) {
      dashed(ctx, left, y(d.ref), left + plotW, y(d.ref), css('--ref'), [2, 4]);
    }

    const bodyW = Math.max(1, Math.min(16, slot * 0.68));
    if (d.volume) {
      const vmax = Math.max(...candles.map((c) => c.v), 1);
      const base = top + plotH + gap + volH;
      candles.forEach((c, i) => {
        const bh = Math.max(1, c.v / vmax * volH);
        ctx.fillStyle = c.c >= c.o ? 'rgba(14,203,129,0.35)' : 'rgba(246,70,93,0.35)';
        ctx.fillRect(xc(i) - bodyW / 2, base - bh, bodyW, bh);
      });
      ctx.fillStyle = muted;
      ctx.fillText('Vol ' + fmtVolume(vmax), left + plotW + 8, top + plotH + gap + 10);
    }

    if (d.mode === 'line') {
      const accent = css('--accent');
      const grad = ctx.createLinearGradient(0, top, 0, top + plotH);
      grad.addColorStop(0, 'rgba(57,135,229,0.28)');
      grad.addColorStop(1, 'rgba(57,135,229,0)');
      ctx.beginPath();
      candles.forEach((c, i) => (i ? ctx.lineTo(xc(i), y(c.c)) : ctx.moveTo(xc(i), y(c.c))));
      ctx.lineTo(xc(candles.length - 1), top + plotH);
      ctx.lineTo(xc(0), top + plotH);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.beginPath();
      candles.forEach((c, i) => (i ? ctx.lineTo(xc(i), y(c.c)) : ctx.moveTo(xc(i), y(c.c))));
      ctx.strokeStyle = accent;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.lineWidth = 1;
    } else {
      candles.forEach((c, i) => {
        const colour = c.c > c.o ? up : c.c < c.o ? down : css('--ref');
        ctx.fillStyle = colour;
        ctx.fillRect(Math.round(xc(i)) - 0.5, y(c.h), 1, Math.max(1, y(c.l) - y(c.h)));
        const topY = y(Math.max(c.o, c.c));
        ctx.fillRect(xc(i) - bodyW / 2, topY, bodyW, Math.max(1, Math.abs(y(c.o) - y(c.c))));
      });
    }

    for (const m of averages) {
      ctx.beginPath();
      let started = false;
      m.values.forEach((v, i) => {
        if (v === null) return;
        if (started) ctx.lineTo(xc(i), y(v)); else { ctx.moveTo(xc(i), y(v)); started = true; }
      });
      ctx.strokeStyle = m.color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.lineWidth = 1;
    }

    // Your trades: ▲ buy under the candle, ▼ sell above it, ✕ when the broker forced a sale
    const index = new Map(candles.map((c, i) => [c.k, i]));
    for (const m of d.markers || []) {
      const i = index.get(m.k);
      if (i === undefined) continue;
      const c = candles[i];
      const x = xc(i);
      ctx.fillStyle = m.forced ? down : m.side === 'BUY' ? css('--series-1') : css('--series-2');
      ctx.beginPath();
      if (m.side === 'BUY') {
        const yy = y(c.l) + 8;
        ctx.moveTo(x, yy); ctx.lineTo(x - 6, yy + 9); ctx.lineTo(x + 6, yy + 9);
      } else {
        const yy = y(c.h) - 8;
        ctx.moveTo(x, yy); ctx.lineTo(x - 6, yy - 9); ctx.lineTo(x + 6, yy - 9);
      }
      ctx.closePath();
      ctx.fill();
    }

    // Last price: a coloured tag on the axis
    const last = candles[candles.length - 1];
    const prevClose = candles.length > 1 ? candles[candles.length - 2].c : (d.ref ?? last.o);
    const lastColour = last.c >= (d.ref ?? prevClose) ? up : down;
    dashed(ctx, left, y(last.c), left + plotW, y(last.c), lastColour, [1, 3]);
    tag(ctx, left + plotW + 2, y(last.c), fmtPrice(last.c), lastColour, '#06110c');

    this.drawCrosshair(ctx, { left, top, plotW, plotH, slot, xc, y, lo, hi, candles, muted });
  }

  drawCrosshair(ctx, g) {
    const hov = this.hover;
    if (!hov || hov.x < g.left || hov.x > g.left + g.plotW || hov.y < g.top) {
      this.hideTip();
      return;
    }
    const i = Math.min(g.candles.length - 1, Math.max(0, Math.floor((hov.x - g.left) / g.slot)));
    const c = g.candles[i];
    const x = g.xc(i);
    dashed(ctx, x, g.top, x, g.top + g.plotH, '#5b6472', [3, 3]);
    if (hov.y <= g.top + g.plotH) {
      dashed(ctx, g.left, hov.y, g.left + g.plotW, hov.y, '#5b6472', [3, 3]);
      const v = g.hi - (hov.y - g.top) / g.plotH * (g.hi - g.lo);
      tag(ctx, g.left + g.plotW + 2, hov.y, fmtPrice(v), '#2b3340');
    }
    const prev = i > 0 ? g.candles[i - 1].c : (this.data.ref ?? c.o);
    const change = c.c / prev - 1;
    const cls = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    this.tip.innerHTML = `<b>${esc(c.t)}${c.live ? ' · live' : ''}</b>
      <div class="row"><span>Open</span><span>${fmtPrice(c.o)}</span></div>
      <div class="row"><span>High</span><span>${fmtPrice(c.h)}</span></div>
      <div class="row"><span>Low</span><span>${fmtPrice(c.l)}</span></div>
      <div class="row"><span>Close</span><span class="${cls}">${fmtPrice(c.c)} (${pct(change)})</span></div>
      <div class="row"><span>Volume</span><span>${fmtVolume(c.v)}</span></div>`;
    placeTip(this.tip, this.wrap, x, hov.y);
  }
}

/**
 * Several lines on one value axis with a hover tooltip listing every series.
 * data = {labels: [...], series: [{name, values, color, dash}], format: v => text,
 *         marks: [{series, index, text}], baseline: number|null}
 */
export class LineChart extends HoverChart {
  draw() {
    if (!this.data) return;
    const { ctx, w, h } = fitCanvas(this.canvas);
    const d = this.data;
    const muted = css('--text-muted');
    const fmt = d.format || ((v) => fmtPrice(v));
    const left = 6, right = 78, top = 12, bottom = 22;
    const plotW = w - left - right, plotH = h - top - bottom;
    const n = d.labels.length;
    if (n < 2) {
      this.hideTip();
      ctx.fillStyle = muted;
      ctx.fillText(d.empty || 'Not enough days yet.', left + 16, top + plotH / 2);
      return;
    }
    const all = d.series.flatMap((s) => s.values).filter((v) => v !== null && isFinite(v));
    let lo = Math.min(...all), hi = Math.max(...all);
    if (d.baseline !== undefined && d.baseline !== null) { lo = Math.min(lo, d.baseline); hi = Math.max(hi, d.baseline); }
    const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.02 || 1;
    lo -= pad; hi += pad;
    const x = (i) => left + i / (n - 1) * plotW;
    const y = (v) => top + (hi - v) / (hi - lo) * plotH;

    for (const t of niceTicks(lo, hi, 5)) {
      ctx.fillStyle = '#1a1f27';
      ctx.fillRect(left, Math.round(y(t)) + 0.5, plotW, 1);
      ctx.fillStyle = muted;
      ctx.fillText(fmt(t), left + plotW + 8, y(t) + 4);
    }
    const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(plotW / 90))));
    d.labels.forEach((label, i) => {
      if (i % every === 0) ctx.fillText(label, Math.min(Math.max(left, x(i) - ctx.measureText(label).width / 2), left + plotW - 60), h - 6);
    });
    if (d.baseline !== undefined && d.baseline !== null) dashed(ctx, left, y(d.baseline), left + plotW, y(d.baseline), '#4a5260', [2, 4]);

    for (const s of d.series) {
      ctx.beginPath();
      s.values.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
      ctx.strokeStyle = s.color;
      ctx.lineWidth = s.width || 2;
      ctx.setLineDash(s.dash ? [6, 4] : []);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineWidth = 1;
    }
    for (const m of d.marks || []) {
      const s = d.series[m.series];
      const px = x(m.index), py = y(s.values[m.index]);
      ctx.fillStyle = css('--down');
      ctx.beginPath();
      ctx.arc(px, py, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillText('!', px - 1.5, py + 4);
    }

    const hov = this.hover;
    if (!hov || hov.x < left || hov.x > left + plotW) {
      this.hideTip();
      return;
    }
    const i = Math.round((hov.x - left) / plotW * (n - 1));
    dashed(ctx, x(i), top, x(i), top + plotH, '#5b6472', [3, 3]);
    let rows = '';
    for (const s of d.series) {
      ctx.fillStyle = s.color;
      ctx.beginPath();
      ctx.arc(x(i), y(s.values[i]), 4, 0, Math.PI * 2);
      ctx.fill();
      rows += `<div class="row"><span><i class="sw" style="background:${s.color}"></i>${esc(s.name)}</span><span>${fmt(s.values[i])}</span></div>`;
    }
    const note = (d.marks || []).filter((m) => m.index === i).map((m) => `<div class="down">${esc(m.text)}</div>`).join('');
    this.tip.innerHTML = `<b>${esc(d.labels[i])}</b>${rows}${note}`;
    placeTip(this.tip, this.wrap, x(i), hov.y);
  }
}

/** A tiny area chart for index cards: the day so far against yesterday's close. */
export function sparkline(canvas, values, ref, slots) {
  const { ctx, w, h } = fitCanvas(canvas);
  if (!values || values.length < 2) {
    ctx.strokeStyle = css('--text-muted');
    dashed(ctx, 0, h / 2, w, h / 2, css('--text-muted'), [2, 3]);
    return;
  }
  const lo = Math.min(...values, ref), hi = Math.max(...values, ref);
  const n = Math.max(values.length, slots || 0);
  const x = (i) => i / (n - 1) * w;
  const y = (v) => 3 + (hi - v) / (hi - lo || 1) * (h - 6);
  const last = values[values.length - 1];
  const colour = last >= ref ? css('--up') : css('--down');
  dashed(ctx, 0, y(ref), w, y(ref), 'rgba(240,185,11,0.6)', [2, 2]);
  ctx.beginPath();
  values.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
  ctx.lineTo(x(values.length - 1), h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = last >= ref ? 'rgba(14,203,129,0.18)' : 'rgba(246,70,93,0.18)';
  ctx.fill();
  ctx.beginPath();
  values.forEach((v, i) => (i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v))));
  ctx.strokeStyle = colour;
  ctx.lineWidth = 1.4;
  ctx.stroke();
}

/** The markup a chart needs: a canvas and a tooltip inside a positioned wrapper. */
export function chartBox(height, label) {
  return `<div class="chart-wrap"><canvas style="height:${height}px" role="img" aria-label="${esc(label)}"></canvas><div class="tooltip"></div></div>`;
}
