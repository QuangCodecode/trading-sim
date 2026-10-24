# 05 — Testing plan

> **D-50:** the terminal game, agent mode, the rich screens and Laya are gone, and so are `test_charts.py`, `test_agent.py`
> and `test_sentiment.py`. `test_app.py` now tests the command layer, and `test_stdlib_only.py` guards "no packages".

Testing against a specification is an assessed learning outcome (LO9), and a green test
run is a strong demo/tutor talking point. Use **pytest**.

## 5.1 Principles

1. **Test the engine, not the terminal.** Engine and education modules are pure → easy to
   test. CLI tests cover only `parser.py` and `charts.py` (both pure functions).
2. **Hand-checked numbers.** Every worked example in `03-finance-model.md` becomes a test
   with those exact numbers.
3. **Fixed markets.** Most tests should NOT depend on random prices. Provide a
   `Market.from_prices(stocks, etfs, prices)` `@staticmethod` factory that builds a market
   from known stock price lists (ETF prices still computed by the real formula), so a test
   can inject exact price paths. Randomness is tested separately (determinism + statistical sanity).
4. **Floats:** compare with `pytest.approx(x, abs=1e-6)` (money to the cent: `abs=0.005`).
5. Test names say the behaviour: `test_buy_rejects_when_cash_short_by_one_cent`.

## 5.2 Fixtures (`tests/conftest.py`)

```python
@pytest.fixture
def universe():            # the real data/reference.db loaded via loader
@pytest.fixture
def tiny_market():         # Market.from_prices with 3 stocks + 1 ETF, 6 days of known prices
@pytest.fixture
def portfolio():           # Portfolio(starting_cash=10_000, fee_per_trade=1.0)
@pytest.fixture
def game(tiny_market, portfolio):
```

## 5.3 Required test cases

### `test_etf.py`
- Worked example A → `MIX6 == 101.00`.
- ETF on day 0 == `base_value` exactly.
- All stocks +10% → ETF +10%.
- Contributions sum equals ETF change (worked example B: −1.68, −1.08, sum −2.76).
- One stock at `MIN_PRICE` floor → ETF still finite and positive.

### `test_loader.py`
- The real `reference.db` loads: 100 stocks in 10 sectors, MIX6 weights sum to 1. Bad data is built with `write_reference` into a `tmp_path` database.
- Weights summing to 0.99 → `DataFileError`; unknown symbol in weights → `DataFileError`;
  duplicate symbol → `DataFileError`; missing file → `DataFileError` with path in message.
- (X-04) ETF cycle A→B→A → `DataFileError`.

### `test_market.py`
- **Determinism:** two markets with seed 42 have identical histories; seed 43 differs.
- Events use a separate RNG: with events enabled, every price **before the first event day** is identical to the events-disabled market.
- History length is `num_days + 1`; day-0 prices equal start prices.
- No price < `MIN_PRICE`; no daily move beyond `MAX_DAILY_MOVE` (except floor effects).
- `price("XYZ", 3)` → `UnknownSymbolError`; `price("AAPL", 999)` → error.
- Statistical sanity (seeded, 20 runs × 250 days): NVDA sample volatility > KO volatility;
  MIX6 volatility < average stock volatility.

### `test_portfolio.py`
- Worked example C, step by step: cash 8,199 → 7,248 → 8,447; avg cost 183.3333;
  realised 100.00; unrealised at 195 = 105.00; equity 10,202.00.
- **Invariant** `total_pnl == realised + unrealised − fees` after a random sequence of
  100 valid trades (seeded) — property-style loop.
- Buy with exactly enough cash → cash 0.00. One cent short → `InsufficientCashError`.
- qty 0 / negative → `InvalidQuantityError`.
- Sell more than held → `InsufficientSharesError`; sell unheld → `InsufficientSharesError`.
- Selling all removes the position from `positions`.
- Every buy/sell appends exactly one `Trade` with correct fields.
- `weights()` sums to 1 including cash.

### `test_analytics.py`
- Worked example D: volatility 2.674% and 0.369% (to 3 dp); total returns 4.0% and 1.0%.
- Worked example E: max drawdown 0.0865 (8.65%).
- Monotonic rising series → drawdown 0; series with < 3 values → volatility returns `0.0`
  (documented behaviour, no exception).

### `test_game.py`
- `advance(1)` increments day and appends one equity snapshot.
- `advance(999)` caps at the end; `is_over()` then True; `buy` → `GameOverError`.
- Game never exposes future prices (`current_prices()` equals `market.prices_on(day)`).

### `test_parser.py`
- `"Buy aapl 10"` → `Command("buy", ["AAPL", 10])`.
- `"buy AAPL max"`, `"sell AAPL all"` parse to sentinel values.
- `"buy AAPL 10.5"`, `"buy AAPL -1"`, `"buy AAPL"`, `"biy AAPL 1"` → `CommandError`
  (and the last one's message contains `Did you mean "buy"`).
- `"   "` → `None` (ignored); aliases map correctly (`pf` → `portfolio`).

### `test_diversification_lab.py` (Phase 1)
- On `tiny_market` with a jumpy stock and calm ETF: stock vol > ETF vol; verdict includes
  the "swung … harder" sentence.
- `lab` before day 5 → error; unknown symbol → `UnknownSymbolError`.
- Monte Carlo with `runs=20` is deterministic for a given base seed.

### `test_explainer.py` (Phase 2)
- Worked example B numbers; affected share of MIX6 on day t−1 = (0.21 + 0.135) / 1.01 =
  **34.2%**; explainer sentence contains "34%" and "-2.73%".
- Stock-scope event affects only its target; sector-scope only that sector.

### `test_coach.py` (Phase 3)
- One test per rule that it fires on a crafted situation **and** stays silent otherwise
  (e.g. CONC fires at 62% NVDA, silent at 62% MIX6).

### `test_whatif.py` (Phase 4)
- **Replay fidelity:** play a scripted game (10 trades), then "Your trades" replay final
  equity == game equity (to the cent).
- Cash only → final equity == starting cash.
- Hold MIX6 on `tiny_market` → hand-computed final value.
- No strategy uses future prices (strategy receives a market view capped at the current day).

### `test_headline_lab.py` (Phase 5)
- `keyword_verdict`:
  - "Chip export curbs hit tech stocks" → negative.
  - The tricky "Walmart sales not as bad as feared" → negative. This documents the counter's weakness on purpose.
- `truth` is the sign of the shock.
- `score` with a **fake classifier** (a plain function returning fixed `Verdict`s) gives the correct hit counts.
- `score` with a classifier that always returns `None` gives an "offline" result: no Jev hits, no crash.

### `test_loader.py` — stored readings (E-05, D-50)
- Every shipped headline has a stored reading (label positive/negative, confidence 0.5–1), and loading them never changes a market (D-20).

### `test_database.py` / `test_savegame.py` (D-46, `tmp_path`)
- Every reference section round-trips through `write_reference` → `read_section` with row, weight and transition order kept (they feed the seeded RNG).
- The reference connection is read-only; missing/garbage files → `DataFileError`; another `user_version` → "delete it"; foreign keys on.
- A saved game replays to the same equity; the summary row and badges follow the game; a finished challenge records pass/fail;
  starting again in a slot archives the old game; a command that no longer works → "damaged".
- Web: resume after a restart (day, tick, holdings), `--seed` starts fresh and keeps the old game, a finished game is not resumed,
  `new`/`challenge` archive, a damaged save starts a new game with a message, `db_path=None` saves nothing, `/api/games`.

### `test_app.py` (the command layer, D-50) and `test_stdlib_only.py`
- Every odd line (`buy`, `next -2`, `hl`, `quit`, `ünïcødé 🚀`, 500 characters…) returns a result or raises a `TradeSimError`, never anything else.
- `quiz` marks the answer and keeps the score, `hl` reports what the word counter found, `lab mc` returns both columns, the "visit" commands (`robo`, `news`, `whatif`, `levlab`, `lab`) unlock their badges.
- `test_stdlib_only.py` parses every `.py` of the game and its tools: only the standard library and `tradesim` may be imported.

### `test_intraday.py` (D-39, D-40)
- Variance clock 0 → 1, bridges start and end at 0; a session runs from yesterday's close to today's close for stocks and ETFs; ETF ticks follow the §3.3 formula.
- Same seed → same session, days differ; bars are OHLC-consistent; news jumps at its tick and only for the stocks it hits.
- Pre-history joins day 0 without a jump, day 0 has a session, negative days outside the history raise; no history → day 0 bar is flat.
- Order book brackets the last price and is the same every time; `step` moves the clock, stops at the bell, reports news when it breaks; trades mid-session use the tick price; `next` finishes a running day.

### `test_margin.py` (D-41, worked numbers from docs/03 §3.13)
- Cash accounts can't borrow; 2× borrows $9,999; the −30% / −35% margin-call table; liquidation sells 106 and leaves −$3,012; wipe-out leaves a debt; interest only on loans; changing leverage; a game's margin call happens mid-session and `next` checks every tick.

### `test_leverage.py` (E-08 and the new commands)
- 1× run = buy and hold; 2× ≈ double the move plus interest; 5× is called on day 4 and ends in debt; the 2× daily fund shows volatility decay; lessons; risk table.
- `leverage`, `tick`, `levlab` (works from day 0 thanks to the history); Margin Madness punishes doing nothing; new badges.

### `test_webapp.py` (D-37)
- Trading dates skip weekends; the state is JSON-ready; the board never shows prices past the current tick.
- Notices: trade, badge, closing bell (with summary), news only once it breaks, margin call, leverage change, a new game forgets old news.
- Charts (1D candles, daily + live candle, bad span), trade markers on the right candle, every page's builder.
- A real `HTTPServer` on a free port: page + state, commands + ticks, five bad requests → 400 with a message, paths outside `static/` → 404.

### Real-life trends (`test_market.py`, D-30)
- Mood path deterministic, one mood per day, own RNG (doesn't reshuffle the noise).
- Bull spells long, crashes short; a market stuck in a crash falls > 20%, one stuck in a bull rises.
- High-beta NVDA swings > 2× low-beta JNJ; fear gauge ≈ 11 when calm, > 2.5× in a crash.
- A headline never repeats within `EVENT_REPEAT_GAP` days.

### `test_robo_analyst.py` (E-06, pure Python)
- Sigmoid bounds; features on hand-made series (5/20-day trend, gap, fall from high).
- Training learns an easy rule (accuracy > 95%) and the loss falls; `reasons` add up to the score.
- Save/load round trip; scorecard vs lazy guess and catch rate.
- The shipped model learnt "storms mean danger"; models never peek past `day` (future prices tripled → same answer).

### `test_coach.py`, `test_whatif.py`, `test_progress.py`
- One positive + one negative case per coach rule; sector exposure looks inside ETFs.
- What-if: "Your trades" replay equals the real equity (fidelity); 11 strategies ranked; chase reinvests proceeds; strategies never peek.
- Badges announced once; command badges; every challenge seed still tells its story (7 cases);
  goals pass/fail; `challenge`/`new` restart in place; glossary partial/typo lookup; quiz marking; quiz answers vary.

## 5.4 Running

```bash
pytest                                  # all
pytest -q --cov=tradesim --cov-report=term-missing   # coverage (target ≥ 85% engine+education)
```

## 5.5 Manual test script (before every submission)

| # | Do | Expect |
|---|---|---|
| 1 | `python3 -m venv /tmp/blank && /tmp/blank/bin/python main.py --seed 42 --no-browser` (no packages installed) | "TradeSim is running at http://127.0.0.1:8000 (seed 42, day 0)"; `/api/state` answers |
| 2 | Open the page in a browser: Board, Trade (`#trade/NVDA`), Portfolio, News, Leverage, Labs, Robo, Learn, Goals | every page loads, no red error in the browser console |
| 3 | Trade: buy 10 NVDA, `NVDA 99999`, sell all | success toast, then friendly red toasts, never a traceback in the server terminal |
| 4 | Skip 5 days; check the portfolio | P&L parts add up to the total |
| 5 | Skip to the end | final report dialog (grade, goals, coach, hidden story); `🏁 Finisher` badge |
| 6 | Run twice with `--seed 42` and the same clicks | identical numbers |
| 7 | Restart the server without `--seed` | the same day and holdings come back (D-46) |
| 8 | Labs → 200 markets; Learn → answer a quiz question; News → test your own headline | each shows its result card; the badges toast |
| 9 | `python3 main.py --seed 42`: Open the market, double-click NVDA → buy 10, Trade page (1D and All), Leverage 2× → buy MKT100 max, Skip 20 days, every page | live board, toasts, closing bell; no traceback in the server terminal |
| 10 | Same, at 15× speed for a whole day, then **To close ⏭** and **Skip to the end** | the clock never stalls; final report dialog |
