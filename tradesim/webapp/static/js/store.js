// The page's memory: the latest game state from the server, plus a few UI choices.
// Pages subscribe with onState() and redraw whenever a new state arrives.

export const store = {
  universe: null,        // names, sectors, ETF holdings (never changes in a game)
  info: {},              // symbol → its universe row
  state: null,           // the latest /api/state reply
  quotes: {},            // symbol → quote row (this tick)
  previous: {},          // symbol → quote row (the tick before: for the flashing cells)
  lastNotice: 0,         // newest notice id already shown
  running: false,        // is the clock ticking?
  speed: 1,              // ticks per second
  autoplay: false,       // keep going after the closing bell?
  symbol: 'NVDA',        // the symbol the Trade page shows
  watch: new Set(JSON.parse(localStorage.getItem('tradesim.watch') || '["NVDA","AAPL","MKT100","TSLA","JPM","XOM"]')),
};

const stateListeners = new Set();
const noticeListeners = new Set();

/** Call `fn(state)` after every new state; returns a function that stops it. */
export function onState(fn) {
  stateListeners.add(fn);
  return () => stateListeners.delete(fn);
}

/** Call `fn(notice)` for every new notice (trade, news, margin call, closing bell…). */
export function onNotice(fn) { noticeListeners.add(fn); }

/** Take a reply that carries a state: remember it, then tell everyone. */
export function setState(reply) {
  store.previous = store.quotes;
  store.state = reply;
  store.quotes = Object.fromEntries(reply.quotes.map((q) => [q.s, q]));
  for (const notice of reply.notices || []) {
    if (notice.id <= store.lastNotice) continue;
    store.lastNotice = notice.id;
    noticeListeners.forEach((fn) => fn(notice));
  }
  stateListeners.forEach((fn) => fn(reply));
}

/** Star or un-star a symbol (saved in this browser). */
export function toggleWatch(symbol) {
  if (store.watch.has(symbol)) store.watch.delete(symbol); else store.watch.add(symbol);
  localStorage.setItem('tradesim.watch', JSON.stringify([...store.watch]));
}
