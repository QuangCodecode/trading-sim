// The order ticket: buy or sell at the live price. Used in a dialog (double-click a board row)
// and in the Trade page's side panel. The server checks every rule; this only previews.

import { run } from './actions.js';
import { store, onState } from './store.js';
import { money, price, esc } from './fmt.js';
import { openDialog, closeDialog } from './ui.js';

/** Max shares: buying power (cash + what the broker lends) for a buy, holdings for a sell. */
function limits(symbol) {
  const account = store.state.account;
  const last = store.quotes[symbol].c;
  const held = store.state.positions.find((p) => p.s === symbol)?.qty || 0;
  const fee = store.universe.fee;
  return { last, held, fee, account, maxBuy: Math.max(0, Math.floor((account.buying_power - fee) / last)) };
}

/** Draw a ticket for `symbol` into `box`. `onDone` runs after a successful order. */
export function renderTicket(box, symbol, side = 'BUY', onDone = null) {
  let qty = 0;
  const info = store.info[symbol];
  box.innerHTML = `
    <div class="ticket">
      <div class="side-tabs" role="group" aria-label="Order side">
        <button class="buy" data-side="BUY">Buy</button><button class="sell" data-side="SELL">Sell</button>
      </div>
      <div class="summary-rows">
        <div class="row"><span>${esc(info.name)}</span><b data-f="last"></b></div>
        <div class="row"><span>Order type</span><b>Market · fills at the last price</b></div>
      </div>
      <div class="field"><label for="qty-${symbol}">Shares</label>
        <div class="input"><button data-step="-1" aria-label="One less">−</button>
          <input id="qty-${symbol}" inputmode="numeric" autocomplete="off" value="">
          <button data-step="1" aria-label="One more">+</button></div></div>
      <div class="quick"><button data-frac="0.25">25%</button><button data-frac="0.5">50%</button>
        <button data-frac="0.75">75%</button><button data-frac="1">Max</button></div>
      <div class="summary-rows">
        <div class="row"><span data-f="value-label">Value</span><b data-f="value"></b></div>
        <div class="row"><span>Fee</span><b data-f="fee"></b></div>
        <div class="row"><span data-f="total-label">Total</span><b data-f="total"></b></div>
        <div class="row"><span data-f="room-label"></span><b data-f="room"></b></div>
      </div>
      <div class="warnline" data-f="warn"></div>
      <button class="btn big submit" data-f="submit"></button>
    </div>`;
  const input = box.querySelector('input');
  const field = (name) => box.querySelector(`[data-f="${name}"]`);

  let stop = null;
  function update() {
    if (!box.isConnected) { if (stop) stop(); return; }   // the ticket was closed
    if (!store.state) return;
    const { last, held, fee, account, maxBuy } = limits(symbol);
    const buying = side === 'BUY';
    box.querySelectorAll('[data-side]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.side === side)));
    field('last').textContent = `${price(last)}`;
    const value = qty * last;
    field('value').textContent = money(value);
    field('fee').textContent = money(qty ? fee : 0);
    field('total-label').textContent = buying ? 'You pay' : 'You receive';
    field('total').textContent = money(qty ? (buying ? value + fee : value - fee) : 0);
    field('room-label').textContent = buying ? 'Max you can buy' : 'You hold';
    field('room').textContent = buying ? `${maxBuy} shares` : `${held} shares`;
    const borrowed = buying && qty ? Math.max(0, value + fee - Math.max(0, account.cash)) : 0;
    const warn = field('warn');
    if (store.state.clock.phase === 'over') warn.innerHTML = '<span class="down">The game is over — trading is closed.</span>';
    else if (buying && qty > maxBuy) warn.innerHTML = `<span class="down">Not enough buying power (max ${maxBuy}).</span>`;
    else if (!buying && qty > held) warn.innerHTML = `<span class="down">You only hold ${held}.</span>`;
    else if (borrowed > 0) warn.innerHTML = `<span class="chip warn">On margin</span> ${money(borrowed)} of this is borrowed at ${(store.universe.margin_rate * 100).toFixed(0)}% a year.`;
    else if (account.leverage === 1 && buying) warn.innerHTML = '<span class="muted">Cash account: no borrowing. Change it on the Leverage page.</span>';
    else warn.innerHTML = '';
    const submit = field('submit');
    submit.className = `btn big submit ${buying ? 'buy' : 'sell'}`;
    submit.textContent = `${buying ? 'Buy' : 'Sell'} ${qty || ''} ${symbol}`;
    submit.disabled = !qty || store.state.clock.phase === 'over';
  }

  function setQty(value) {
    qty = Math.max(0, Math.floor(Number(value) || 0));
    input.value = qty ? String(qty) : '';
    update();
  }

  box.querySelectorAll('[data-side]').forEach((b) => b.addEventListener('click', () => { side = b.dataset.side; setQty(0); }));
  box.querySelectorAll('[data-step]').forEach((b) => b.addEventListener('click', () => setQty(qty + Number(b.dataset.step))));
  box.querySelectorAll('[data-frac]').forEach((b) => b.addEventListener('click', () => {
    const { held, maxBuy } = limits(symbol);
    setQty(Math.floor((side === 'BUY' ? maxBuy : held) * Number(b.dataset.frac)));
  }));
  input.addEventListener('input', () => { qty = Math.max(0, Math.floor(Number(input.value.replace(/\D/g, '')) || 0)); update(); });
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') field('submit').click(); });
  field('submit').addEventListener('click', async () => {
    if (!qty) return;
    const reply = await run(`${side === 'BUY' ? 'buy' : 'sell'} ${symbol} ${qty}`);
    if (!reply.error) {
      setQty(0);
      if (onDone) onDone();
    }
  });
  stop = onState(update);
  update();
  return input;
}

/** The ticket in a dialog (double-click on the board, or the B / S keys). */
export function openTicket(symbol, side = 'BUY') {
  if (!store.quotes[symbol]) return;
  openDialog({
    title: `Trade <span class="muted">${esc(symbol)}</span>`,
    body: '<div data-ticket></div>',
    onOpen: (dialog) => {
      const input = renderTicket(dialog.querySelector('[data-ticket]'), symbol, side, closeDialog);
      input.focus();
    },
  });
}
