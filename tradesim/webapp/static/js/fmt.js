// Number and text formatting shared by every page.

const nf = (dp) => new Intl.NumberFormat('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp });
const NF = [nf(0), nf(1), nf(2)];

/** $1,234.56 (or −$1,234.56). */
export function money(value, dp = 2) {
  const shown = NF[dp].format(Math.abs(value));
  return (value < 0 && Number(shown.replace(/,/g, '')) !== 0 ? '−$' : '$') + shown;
}

/** 1,234.56 — a price without the $ sign. */
export function price(value) {
  return NF[2].format(value);
}

/** +1.23% from a fraction (0.0123). */
export function pct(fraction, dp = 2) {
  if (fraction === null || fraction === undefined || !isFinite(fraction)) return '—';
  const shown = NF[Math.min(dp, 2)].format(Math.abs(fraction * 100));
  const sign = Number(shown) === 0 ? '' : fraction > 0 ? '+' : '−';   // no "−0.00%"
  return sign + shown + '%';
}

/** +12.34 with a sign. */
export function signed(value, dp = 2) {
  const shown = NF[dp].format(Math.abs(value));
  const sign = Number(shown.replace(/,/g, '')) === 0 ? '' : value > 0 ? '+' : '−';
  return sign + shown;
}

/** 12.3K, 4.56M — share volumes. */
export function volume(value) {
  if (value >= 1e9) return (value / 1e9).toFixed(2) + 'B';
  if (value >= 1e6) return (value / 1e6).toFixed(2) + 'M';
  if (value >= 1e4) return (value / 1e3).toFixed(1) + 'K';
  return NF[0].format(value);
}

/** 'up' | 'down' | 'flat' comparing a value with a reference. */
export function direction(value, ref) {
  if (value > ref + 1e-9) return 'up';
  if (value < ref - 1e-9) return 'down';
  return 'flat';
}

export const ARROWS = { up: '▲', down: '▼', flat: '■' };

/** Escape text for innerHTML. */
export function esc(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
