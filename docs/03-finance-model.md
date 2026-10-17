# 03 — Finance model (formulas + worked examples)

Every number the game shows comes from a formula on this page. Each worked example below
**must become a unit test** with exactly these numbers (see `05-testing.md`).

Notation: `P[s][t]` = price of symbol `s` on day `t`. Day 0 = starting prices.

## 3.1 Stock universe (`data/universe.json`)

Tickers are real (for familiarity); **all prices and parameters are invented**.

| Symbol | Name | Sector | Start price | Drift μ (daily) | Volatility σ (daily) | Personality |
|---|---|---|---|---|---|---|
| AAPL | Apple | Tech | 180.00 | 0.0006 | 0.018 | steady grower |
| NVDA | NVIDIA | Tech | 120.00 | 0.0010 | 0.032 | high-flyer, wild swings |
| XOM | Exxon Mobil | Energy | 110.00 | 0.0003 | 0.016 | cyclical |
| CVX | Chevron | Energy | 150.00 | 0.0003 | 0.017 | cyclical |
| KO | Coca-Cola | Consumer | 60.00 | 0.0002 | 0.010 | boring, defensive |
| WMT | Walmart | Consumer | 70.00 | 0.0003 | 0.012 | defensive |

ETFs (fictional tickers — rename if one collides with a real fund):

| Symbol | Name | Holdings & weights | Phase |
|---|---|---|---|
| **MIX6** | Mix-6 ETF | AAPL 0.20 · NVDA 0.15 · XOM 0.15 · CVX 0.15 · KO 0.15 · WMT 0.20 (sum = 1.00; tech 35%, energy 30%, consumer 35%) | 1 (core) |
| TECH2 | Tech-2 ETF | AAPL 0.50 · NVDA 0.50 | X-04 |

JSON shape:

```json
{
  "stocks": [
    {"symbol": "AAPL", "name": "Apple", "sector": "Tech",
     "start_price": 180.0, "drift": 0.0006, "volatility": 0.018}
  ],
  "etfs": [
    {"symbol": "MIX6", "name": "Mix-6 ETF", "base_value": 100.0,
     "weights": {"AAPL": 0.20, "NVDA": 0.15, "XOM": 0.15,
                 "CVX": 0.15, "KO": 0.15, "WMT": 0.20}}
  ]
}
```

`loader.py` validation (raise `DataFileError` with a clear message):
symbols unique and upper-case · start_price > 0 · volatility ≥ 0 · every ETF weight key is a
known symbol · all weights > 0 · weights sum to 1 within 1e-9.

## 3.2 Daily price model

Each stock's daily return is the sum of a **market** factor (everything moves together a
bit), a **sector** factor (same-sector stocks move together), the stock's own **noise**,
and any **event shock** (Phase 2):

```
r[s][t] = μ_s + M_t + S[sector(s)][t] + σ_s · ε[s][t] + shock[s][t]

M_t            ~ Normal(0, MARKET_VOL)       one draw per day
S[k][t]        ~ Normal(0, SECTOR_VOL)       one draw per sector per day
ε[s][t]        ~ Normal(0, 1)                one draw per stock per day
shock[s][t]    = sum of shocks of events that affect s on day t   (0 in Phase 1)

r  = clamp(r, -MAX_DAILY_MOVE, +MAX_DAILY_MOVE)
P[s][t] = round(max(MIN_PRICE, P[s][t-1] · (1 + r)), 2)
```

Why factors? With purely independent stocks diversification still works, but the market
and sector factors make it **realistic**: diversification reduces risk but can't remove
the market-wide part. That's a real lesson the Lab can state.

**Expected ballpark** (checked with a prototype of exactly this model, 200 seeds × 60 days,
no events). If your implementation is far off these, look for a bug:

| | AAPL | NVDA | XOM | CVX | KO | WMT | MIX6 |
|---|---|---|---|---|---|---|---|
| Avg daily volatility | 2.2% | 3.4% | 2.1% | 2.1% | 1.6% | 1.7% | **1.2%** |

NVDA average max drawdown ≈ 24% vs MIX6 ≈ 9%; NVDA finishes 60 days down > 20% in ≈ 19%
of runs, MIX6 in < 1%. That gap *is* the lesson of the Diversification Lab.

**Determinism rules (critical):**
- `Market` owns `self._rng = random.Random(seed)` for prices.
- Draw order per day is fixed: `M_t`, then sectors in **sorted** name order, then stocks in
  **sorted** symbol order. Never iterate a set.
- Events use a **separate** `random.Random(seed + EVENT_SEED_OFFSET)` so switching events
  on/off (Phase 1 → 2) doesn't change the underlying random walk.
- Prices are rounded to cents when generated, so the displayed price is exactly the traded price.

## 3.3 ETF pricing — weighted average (instructor requirement C-04)

```
                     n
ETF[t] = BASE  ·    Σ   w_i · ( P[i][t] / P[i][0] )          with  Σ w_i = 1,  BASE = 100
                    i=1
```

It is a **weighted average of the stocks' price relatives** (each stock's price today
divided by its day-0 price), scaled so the ETF starts at 100.00. Round to 2 dp.

**Why not the literal `Σ w_i · P_i`?** A plain weighted average of *raw* prices lets an
expensive stock dominate: AAPL at $180 would move the ETF three times more than KO at $60
even with equal weights, so the weights would stop meaning "% of the fund". Normalising
by the day-0 price makes weight = true share of the fund at launch — which is how real
index funds think about weights. (This is a documented decision — see `07-decisions-log.md`
D-03. Switching to the literal version is a one-line change if the tutor prefers it.)

**Worked example A — ETF price**

| Stock | w | P[0] | P[t] | P[t]/P[0] | w × ratio |
|---|---|---|---|---|---|
| AAPL | 0.20 | 180.00 | 189.00 | 1.05 | 0.2100 |
| NVDA | 0.15 | 120.00 | 108.00 | 0.90 | 0.1350 |
| XOM | 0.15 | 110.00 | 110.00 | 1.00 | 0.1500 |
| CVX | 0.15 | 150.00 | 157.50 | 1.05 | 0.1575 |
| KO | 0.15 | 60.00 | 63.00 | 1.05 | 0.1575 |
| WMT | 0.20 | 70.00 | 70.00 | 1.00 | 0.2000 |
| | | | | **Σ** | **1.0100** |

`MIX6[t] = 100 × 1.0100 = 101.00`

## 3.4 ETF move breakdown (used by the Explainer, E-02)

Because the formula is linear, the ETF's change from day t−1 to t splits **exactly** into
per-stock contributions:

```
contribution_i = BASE · w_i · (P[i][t] − P[i][t−1]) / P[i][0]
Σ contribution_i = ETF[t] − ETF[t−1]            (exact, before rounding)
```

**Worked example B — "Chip export curbs hit tech": AAPL and NVDA −8%, others flat**
(starting from the day-t prices in example A)

| Stock | Move | Contribution to MIX6 (points) |
|---|---|---|
| AAPL | 189.00 → 173.88 (−8%) | 100 × 0.20 × (−15.12)/180 = **−1.68** |
| NVDA | 108.00 → 99.36 (−8%) | 100 × 0.15 × (−8.64)/120 = **−1.08** |
| XOM, CVX, KO, WMT | 0% | 0.00 |
| **MIX6** | 101.00 → 98.24 | **−2.76 points = −2.73%** |

Explainer sentence: *"Tech stocks fell 8%, but tech was only about 34% of MIX6 that day
(35% at launch; NVDA had lagged), so the ETF fell 2.73%. The other ~66% (energy +
consumer) didn't move and cushioned the blow."*

Effective share today = `w_i · P[i][t−1]/P[i][0]` ÷ `Σ_j w_j · P[j][t−1]/P[j][0]`
→ tech = (0.2100 + 0.1350) / 1.0100 = 34.2%.

## 3.5 Portfolio accounting (average-cost method)

| Action | Cash | Position | Realised P&L | Fees |
|---|---|---|---|---|
| **Buy** q @ p | `cash −= q·p + FEE` (reject if result < 0) | `avg = (old_qty·old_avg + q·p) / (old_qty + q)`; `qty += q` | — | `+= FEE` |
| **Sell** q @ p | `cash += q·p − FEE` | `qty −= q`; avg unchanged; remove position when qty = 0 | `+= (p − avg)·q` | `+= FEE` |

Fees are tracked **separately** (not folded into avg cost) so the player sees them clearly.

```
market_value   = Σ qty_s · P[s][today]
equity         = cash + market_value
unrealised_pnl = Σ (P[s][today] − avg_s) · qty_s
total_pnl      = equity − starting_cash
total_return % = total_pnl / starting_cash × 100
weight_s       = qty_s · P[s][today] / equity

INVARIANT:  total_pnl == realised_pnl + unrealised_pnl − fees_paid     (to 1e-6)
```

**Sell fee rule:** the fee is taken from the sale proceeds, so a sell is allowed even when
cash < FEE, as long as `q·p ≥ FEE`; otherwise reject.

**Worked example C** (start $10,000, FEE = $1)

| Step | Action | Cash after | Position | Realised | Fees |
|---|---|---|---|---|---|
| 1 | buy 10 AAPL @ 180 | 10,000 − 1,800 − 1 = **8,199.00** | 10 @ 180.00 | 0 | 1 |
| 2 | buy 5 AAPL @ 190 | 8,199 − 950 − 1 = **7,248.00** | 15 @ 183.3333 | 0 | 2 |
| 3 | sell 6 AAPL @ 200 | 7,248 + 1,200 − 1 = **8,447.00** | 9 @ 183.3333 | (200 − 183.3333)·6 = **100.00** | 3 |
| 4 | price now 195 | — | value 9·195 = 1,755 | unrealised (195 − 183.3333)·9 = **105.00** | — |

`equity = 8,447 + 1,755 = 10,202.00` → `total_pnl = 202.00 = 100 + 105 − 3` ✔

**Max affordable quantity** (used by strategies and a `buy SYMBOL max` convenience):
`qty = floor((cash − FEE) / price)`; if `qty ≤ 0` the buy is skipped/rejected.

## 3.6 Performance metrics (`engine/analytics.py` — pure functions on `list[float]`)

| Metric | Formula | Notes |
|---|---|---|
| Daily returns | `r_t = v_t / v_{t−1} − 1` for t ≥ 1 | length n−1 |
| Total return | `v_end / v_start − 1` | |
| Volatility | `statistics.stdev(daily_returns)` | "typical daily swing"; needs ≥ 2 returns; show as % |
| Worst day | `min(daily_returns)` (+ which day) | |
| Max drawdown | `max over t of (peak_t − v_t) / peak_t`, `peak_t = max(v_0..v_t)` | "worst fall from a high" |
| Value of $X | `X × v_t / v_start` | for charting both assets on one scale |

**Worked example D — volatility**

| Series | Values | Daily returns (%) | Total | Volatility (sample stdev) |
|---|---|---|---|---|
| Jumpy stock | 100, 102, 99, 101, 104 | +2.000, −2.941, +2.020, +2.970 | +4.0% | **2.674%** |
| Calm ETF | 100, 100.5, 100.2, 100.6, 101.0 | +0.500, −0.299, +0.399, +0.398 | +1.0% | **0.369%** |

**Worked example E — max drawdown**: equity `10000, 10400, 9800, 10100, 9500, 10300`
→ peak 10,400, lowest point after it 9,500 → `900 / 10400 = 8.65%`.

## 3.7 Market events (Phase 2, E-02)

`data/events.json` holds templates:

```json
{"id": "chip_curbs", "scope": "sector", "target": "Tech",
 "shock_min": -0.10, "shock_max": -0.05,
 "headline": "Chip export curbs hit tech stocks",
 "explanation": "Tech companies depend on chip sales abroad; the whole sector reprices."}
```

- `scope`: `"stock"` (one symbol), `"sector"` (all stocks in a sector), `"market"` (all stocks).
- Each day (t ≥ 1), with probability `EVENT_PROBABILITY`, pick one template uniformly
  (event RNG), draw `shock` uniformly in `[shock_min, shock_max]`, attach a `MarketEvent`
  to that day, and add `shock` to the return of every affected stock (§3.2).
- Provide ~12 templates: 4 stock-level (e.g. "NVDA smashes earnings" +6..+12%), 5
  sector-level (positive and negative for each sector), 3 market-wide (smaller: ±2..4%).
- Include both good and bad news; roughly balanced so events add risk, not free money.
- **E-05 (Phase 5):** a template's true sentiment is the sign of its shock range. Every
  template is all positive or all negative, never straddling 0. Write ~4 **tricky**
  headlines whose words mislead a word counter. These are the Headline Lab's teaching moments:
  - "Walmart sales not as bad as feared" (positive, but uses "bad")
  - "Oil glut fears ease as demand recovers" (positive, but uses "fears")
  - "Record highs fail to hold as chip rally fizzles" (negative, but uses "record", "rally")
- `events.json` also holds two small word lists for the keyword counter:
  `"positive_words": [...]` and `"negative_words": [...]` (~20 each).

## 3.8 What-if strategies (Phase 4, E-04)

All start with `STARTING_CASH`, pay the same fee, trade at the same daily prices, run from
day 0 to the game's current (or final) day, and **only use information up to that day**.

| Strategy | Rule |
|---|---|
| **Your trades** | Re-executes the player's trade log day by day. Its final equity must equal the real game's equity (great test). |
| Cash only | Never trades. Baseline. |
| Hold MIX6 | Day 0: buy max affordable MIX6. Hold. |
| DIY equal-weight | Day 0: split cash equally across the 6 stocks, buy max affordable of each. Hold. |
| All-in one stock | Day 0: buy max affordable of the stock the player spent most on (fallback: highest-volatility stock, NVDA). Hold. |
| Panic seller | Same as All-in, but sells everything the first day the price closes ≥ `PANIC_DROP` (8%) below its buy price, then stays in cash. |
| Buy the dip | Day 0: invest 20% of starting cash in MIX6. Each day MIX6 falls ≥ 2% on the day, invest another 20% of starting cash (if cash allows). |
| DCA weekly | Every 5th day (0, 5, 10, …) invest `STARTING_CASH / ceil(days/5)` in MIX6. |

Output per strategy: final equity, total return, volatility, max drawdown, #trades, fees;
sorted by final equity; highlight "Your trades" row; ASCII chart of 2–3 chosen curves.

## 3.9 Short selling (X-03, optional)

- Short = sell shares you don't own: position qty becomes negative; cash increases by `q·p − FEE`.
- Collateral rule (keeps it simple): opening/increasing a short requires
  `cash ≥ SHORT_COLLATERAL (1.5) × |short market value after trade|`; otherwise reject.
- Buying back ("cover") uses `buy`. Same P&L formula `(P − avg)·qty` works because qty < 0.
- Equity formula unchanged (`cash + Σ qty·P`, negative terms for shorts).
- Coach tip: "Short losses are unlimited — the price can keep rising."

## 3.10 Fund-of-funds recursive pricing (X-04, optional)

Allow an ETF's weights to include another ETF. Price recursively:

```python
def relative(symbol, day):             # price relative P[t]/P[0]
    if symbol is a stock:  return P[symbol][day] / P[symbol][0]
    return sum(w * relative(child, day) for child, w in etf.weights.items())
```

Detect cycles (ETF A holds B holds A) at load time with a recursive DFS carrying a
`visiting` set → raise `DataFileError`. This is a genuine recursion use case for LO7.
