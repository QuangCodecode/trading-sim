# 05 — Testing plan

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
def universe():            # the real data/universe.json loaded via loader
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
- Real `universe.json` loads; 6 stocks, MIX6 weights sum to 1.
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

### `test_charts.py`
- Output has exactly `CHART_HEIGHT` plot rows; flat series doesn't crash; max value sits
  on the top row and min on the bottom row; sparkline length == input length.

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

### `test_headline_lab.py` (Phase 5, no network)
- `keyword_verdict`:
  - "Chip export curbs hit tech stocks" → negative.
  - The tricky "Walmart sales not as bad as feared" → negative. This documents the counter's weakness on purpose.
- `truth` is the sign of the shock.
- `score` with a **fake classifier** (a plain function returning fixed `Verdict`s) gives the correct hit counts.
- `score` with a classifier that always returns `None` gives an "offline" result: no Jev hits, no crash.

### `test_sentiment.py` (Phase 5, network mocked)
- A cache hit returns the stored verdict, and the network function is never called (use `monkeypatch`).
- No `JEV_API_KEY` → `None`, without calling the network.
- The network function raises `TimeoutError` / `URLError`, or returns malformed JSON → `None`.
- A corrupt cache file is treated as empty, and the next save rewrites it.
- **Determinism guard:** take a snapshot of every `Market` price, run `headline_lab.score` over all events, and assert the prices are unchanged (D-20).

## 5.4 Running

```bash
pytest                                  # all
pytest -q --cov=tradesim --cov-report=term-missing   # coverage (target ≥ 85% engine+education)
```

## 5.5 Manual test script (before every submission)

| # | Do | Expect |
|---|---|---|
| 1 | `python3 main.py --seed 42` | Banner with disclaimer + seed |
| 2 | `market`, `etf` | 7 rows; MIX6 composition sums to 100% |
| 3 | `buy nvda 10`, `buy NVDA 99999`, `buy XYZ 1`, `buy nvda ten` | success, then 3 friendly errors, no traceback |
| 4 | `next 5`, `portfolio` | day 5; P&L parts add up to total |
| 5 | `sell nvda all`, `history` | position gone; 2 trades listed |
| 6 | `lab`, `lab KO`, `chart NVDA MIX6` | tables + chart render, verdict readable |
| 7 | `next 100` | caps at final day; final report shows |
| 8 | `buy AAPL 1` after end | GameOverError message |
| 9 | `whatif` (Phase 4) | "Your trades" matches final equity |
| 10 | Ctrl+C mid-game | graceful exit, no traceback |
| 11 | Run twice with `--seed 42` and same commands | identical output |
