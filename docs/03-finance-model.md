# 03 — Finance model (formulas + worked examples)

Every number the game shows comes from a formula on this page. Each worked example below
**must become a unit test** with exactly these numbers (see `05-testing.md`).

Notation: `P[s][t]` = price of symbol `s` on day `t`. Day 0 = starting prices.

## 3.1 Stock universe (`stocks`, `etfs` and `etf_weights` tables in `data/reference.db`)

Tickers are real (for familiarity); **all prices and parameters are invented** (D-04).
Since D-38 there are **100 stocks in 10 sectors** (the table shows the original 12). `drift` is the stock's own extra daily
return ("alpha"); most of the trend now comes from the market's mood (§3.2).

| Symbol | Name | Sector | Start | Drift μ | Own vol σ | Beta β | Personality |
|---|---|---|---|---|---|---|---|
| AAPL | Apple | Tech | 180 | 0.0003 | 0.012 | 1.10 | steady giant |
| NVDA | NVIDIA | Tech | 120 | 0.0006 | 0.024 | 1.60 | high-flyer, wild swings |
| MSFT | Microsoft | Tech | 410 | 0.0003 | 0.011 | 1.05 | calm giant |
| XOM | Exxon Mobil | Energy | 110 | 0.0002 | 0.012 | 0.80 | oil price |
| CVX | Chevron | Energy | 150 | 0.0002 | 0.013 | 0.85 | oil price |
| KO | Coca-Cola | Consumer | 60 | 0.0001 | 0.007 | 0.55 | defensive |
| WMT | Walmart | Consumer | 70 | 0.0002 | 0.009 | 0.60 | defensive |
| AMZN | Amazon | Consumer | 175 | 0.0003 | 0.016 | 1.25 | consumer with tech energy |
| JPM | JPMorgan Chase | Finance | 195 | 0.0002 | 0.011 | 1.15 | economy-sensitive |
| V | Visa | Finance | 270 | 0.0003 | 0.010 | 1.00 | payments |
| JNJ | Johnson & Johnson | Healthcare | 155 | 0.0001 | 0.008 | 0.50 | defensive |
| PFE | Pfizer | Healthcare | 28 | 0.0000 | 0.014 | 0.65 | drug-trial news |

Each stock also has a one-paragraph `description` shown on its profile.

| ETF | Name | Holdings & weights |
|---|---|---|
| **MIX6** | Mix-6 ETF (core, C-04) | AAPL 0.20 · NVDA 0.15 · XOM 0.15 · CVX 0.15 · KO 0.15 · WMT 0.20 |
| MKT100 | Total Market ETF (was MKT12) | all 100, cap-weighted by rough company size (AAPL, MSFT, NVDA ≈ 9% each … ALB 0.03%) |
| TECH3 | Tech Leaders ETF | AAPL 0.34 · NVDA 0.33 · MSFT 0.33 (a fund, but one sector) |
| DEF4 | Defensive ETF | KO 0.25 · WMT 0.25 · JNJ 0.30 · PFE 0.20 |
| TECHX, COMMX, CONSX, ENRGX, FINX, HLTHX, INDUX, MATX, UTILX, REITX | Sector ETFs (D-38) | the ten stocks of one sector, cap-weighted |

MKT100 is "the market": the benchmark in reports, badges, what-if and the Robo-analyst.

**Since D-38 the universe has 100 stocks, 10 per sector** (the 12 above keep their numbers):

| Sector | Stocks | β range | Own vol σ range |
|---|---|---|---|
| Tech | AAPL MSFT NVDA AVGO ORCL CRM AMD ADBE INTC CSCO | 0.9–1.7 | 0.010–0.025 |
| Communication | GOOGL META NFLX DIS TMUS VZ T CMCSA EA TTWO | 0.45–1.3 | 0.009–0.019 |
| Consumer | AMZN TSLA HD MCD NKE KO PEP PG WMT COST | 0.5–1.9 | 0.007–0.032 |
| Energy | XOM CVX COP EOG SLB HAL OXY PSX MPC KMI | 0.75–1.2 | 0.010–0.020 |
| Finance | JPM BAC WFC C GS MS BLK AXP V MA | 1.0–1.35 | 0.010–0.017 |
| Healthcare | LLY UNH JNJ MRK ABBV TMO ABT AMGN PFE MRNA | 0.5–1.3 | 0.008–0.035 |
| Industrials | GE CAT BA HON UPS LMT RTX DE UNP FDX | 0.45–1.3 | 0.010–0.020 |
| Materials | LIN SHW APD ECL FCX NEM NUE DOW DD ALB | 0.4–1.5 | 0.009–0.028 |
| Utilities | NEE SO DUK D AEP EXC SRE XEL PCG ED | 0.35–0.7 | 0.007–0.014 |
| Real Estate | PLD AMT EQIX WELL SPG O PSA CCI DLR AVB | 0.6–1.15 | 0.009–0.015 |

Calibration with 100 stocks (150 markets × 252 days): MKT100 ≈ +13% mean (+9% median) a year,
≈ 17% yearly volatility — the same ballpark as before and as a real total-market index.

`loader.py` validation (raise `DataFileError` with a clear message):
symbols unique and upper-case · start_price > 0 · volatility ≥ 0 · every ETF weight key is a
known symbol · all weights > 0 · weights sum to 1 within 1e-9 · every regime table sums to 1.

## 3.2 Daily price model — real-life trends (D-30)

Real markets have **moods that last weeks** (bull runs, sideways chop, bear markets, the odd
crash), **calm and stormy spells** (big moves cluster), and stocks that follow the market
**more or less strongly**. The model has one ingredient for each:

```
mood_t        Markov chain over {bull, sideways, bear, crash}: tomorrow's mood is drawn from
              today's row of the transition table (`regime_next` in data/reference.db) (own RNG, D-09 style)

nervous_t   = (1 − α − β) + α · z_{t−1}² + β · nervous_{t−1}        GARCH(1,1), average 1
storm_t     = vol_scale(mood_t) · √nervous_t                          1 = normal, 2.6 = crash

M_t         = drift(mood_t) + MARKET_VOL · storm_t · z_t              z_t ~ N(0,1), the market factor
S[k][t]     ~ N(0, SECTOR_VOL · storm_t)                              one per sector
story_s     ~ N(0, STORY_SPREAD)                                      once per game: a good or bad year
r[s][t]     = μ_s + story_s + β_s · M_t + S[sector][t] + σ_s · storm_t · ε + shock[s][t]

r = clamp(r, −MAX_DAILY_MOVE, +MAX_DAILY_MOVE);  P[s][t] = round(max(MIN_PRICE, P[s][t−1]·(1+r)), 2)
```

| Mood | Daily drift | Storminess | Stays each day | Average spell |
|---|---|---|---|---|
| 🐂 Bull | +0.16% | 0.8× | 98% | 50 days |
| 🦀 Sideways | +0.02% | 0.9× | 96% | 25 days |
| 🐻 Bear | −0.30% | 1.35× | 95% | 20 days |
| 💥 Crash | −2.0% | 2.6× | 72% | 3.6 days (then bear or a rebound) |

`α = STORM_KICK = 0.10`, `β = STORM_MEMORY = 0.85`, `MARKET_VOL = 0.0072`, `SECTOR_VOL = 0.0055`,
`STORY_SPREAD = 0.0006`. The **fear gauge** is `storm_t × MARKET_VOL × √252 × 100`, a VIX-style
"expected yearly swing": about 10 when calm, 30+ in a crash.

**Calibration** (300 markets × 252 days, with news; re-run `tools`-style checks after any change):

| | MKT100 | MIX6 | DEF4 | TECH3 | NVDA | KO |
|---|---|---|---|---|---|---|
| Yearly return (mean / median) | +11.5% / +9.1% | +10.4% / +8.5% | +3.3% / +1.4% | +16.8% / +12.1% | +27.9% / +16.0% | +2.3% / −0.5% |
| Daily volatility | 1.12% | 1.13% | 0.94% | 1.72% | 2.91% | 1.17% |
| Lost > 20% in a 60-day game | 5.3% | 4.3% | 2.3% | 7.7% | 15.7% | 2.7% |

Moods are visible in prices: 86% of bull spells rise, 82% of bear spells fall, every crash
falls (median −12%). Moods are spent ≈ 54% bull, 28% sideways, 17% bear, 1% crash, with ≈ 2
switches per 60-day game. NVDA losing > 20% in about 1 game in 6 vs MIX6 in 1 in 23 is the
Diversification Lab's lesson.

**Determinism rules (critical):**
- `Market` owns `self._rng = random.Random(seed)` for prices; moods use
  `Random(seed + REGIME_SEED_OFFSET)`, events `Random(seed + EVENT_SEED_OFFSET)`.
- Draw order: company stories (sorted symbols) once, then per day: `z_t`, sectors in **sorted**
  order, stocks in **sorted** symbol order. Never iterate a set.
- Prices are rounded to cents when generated, so the displayed price is exactly the traded price.
- A market built without `regime_model` uses one calm "normal" mood (tests, hand-made markets).

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

The `event_templates` table in `data/reference.db` holds templates (shown here in their original JSON shape, which `database.py` still returns):

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
- 46 templates (D-36): 23 good, 23 bad, balanced per company and per sector, covering all 12
  stocks and 5 sectors, plus 8 market-wide. The same template can't repeat within
  `EVENT_REPEAT_GAP` (40) days. Laya labels 44/46 correctly; the keyword counter 37/46.
- Include both good and bad news; roughly balanced so events add risk, not free money.
- **E-05 (Phase 5):** a template's true sentiment is the sign of its shock range. Every
  template is all positive or all negative, never straddling 0. Write ~4 **tricky**
  headlines whose words mislead a word counter. These are the Headline Lab's teaching moments:
  - "Walmart sales not as bad as feared" (positive, but uses "bad")
  - "Oil glut fears ease as demand recovers" (positive, but uses "fears")
  - "Record highs fail to hold as chip rally fizzles" (negative, but uses "record", "rally")
- The `event_words` table also holds two small word lists for the keyword counter:
  `"positive_words": [...]` and `"negative_words": [...]` (~20 each).

## 3.8 What-if strategies (Phase 4, E-04)

All start with `STARTING_CASH`, pay the same fee, trade at the same daily prices, run from
day 0 to the game's current (or final) day, and **only use information up to that day**.

| Strategy | Rule |
|---|---|
| **Your trades** | Re-executes the player's trade log day by day. Its final equity must equal the real game's equity (test). |
| Cash only | Never trades. Baseline. |
| Hold MKT100 | Day 0: buy max affordable of the whole market. Hold. |
| Hold MIX6 | Day 0: buy max affordable MIX6. Hold. |
| DIY equal-weight | Day 0: split cash equally across all 12 stocks. Hold. |
| All-in one stock | Day 0: buy max of the stock the player spent most on (fallback NVDA). Hold. |
| Panic seller | Same as All-in, but sells everything the first day the price is ≥ `PANIC_DROP` (8%) below its buy price, then stays in cash. |
| Buy the dip | Day 0: 20% of starting cash in MIX6; again after each day MIX6 falls ≥ 2%. |
| Steady saver | Every 5th day invest `STARTING_CASH / ceil((days+1)/5)` in MKT100 (dollar-cost averaging). |
| Chase the winner | Every 5 days, switch everything into the stock that rose most over the last 5 days. |
| Follow the Robo-analyst | Hold MKT100, but sell to cash while the mood detector's downturn chance is > 50% (buy back when it falls). |

Strategies are plain functions with one signature; the ones that need settings are made by
small "factory" functions (`buy_and_hold("MIX6")` returns a strategy) — functions as values.
Orders are filled in order, so a strategy can sell and spend the proceeds on the same day.

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


## 3.11 Robo-analyst — tiny machine learning (E-06, D-31)

*(Retrained for 100 stocks, D-43: mood ≈ 85% vs lazy 80%, catches 42% of downturn days; price ≈ 55% vs 54%.)*

Two **logistic regressions**, written in plain Python (`education/robo_analyst.py`):

```
z_i   = (x_i − mean_i) / scale_i                    standardise each feature (learnt in training)
score = b + Σ w_i · z_i
P     = 1 / (1 + e^(−score))                         the sigmoid: any number → a probability
loss  = −mean( y·ln P + (1−y)·ln(1−P) )              log loss: big when confident and wrong
w_i  ← w_i − rate · mean( (P − y) · z_i )            gradient descent, one step per epoch
```

| Model | Features (from the last 20 days only — no peeking) | Answer y | Unseen-market score |
|---|---|---|---|
| Mood detector | MKT100 20-day trend · gap to 20-day average · fall from 20-day high · 10-day swing · 20-day swing | 1 if the hidden mood is bear or crash | ≈ 84% (lazy "never" 80%), catches ≈ 35% of downturn days |
| Price forecaster | 5-day trend · 20-day trend · gap to average · 10-day swing · market 20-day trend | 1 if the price is higher 5 days later | ≈ 54% (lazy "always up" 54%) |

Training data: 40 markets × 250 days from seeds 50,000,000+ (players' seeds are below 1,000,000);
test data: 20 more markets. `reasons(features)` returns each `w_i · z_i`, so the screen can show
*why* the model thinks what it thinks. The largest learnt weights are on the swing features —
the model rediscovered that **storms mean danger** (the idea behind the VIX).


## 3.12 Intraday sessions — prices tick by tick (D-39, `engine/intraday.py`)

The daily closes of §3.2 are fixed first. Day d's **session** fills in 78 five-minute ticks
(09:30 → 16:00) from yesterday's close `P0` (tick 0, the *reference price*) to today's close `P1`
(tick 78) with a **Brownian bridge** — a random walk pinned at both ends:

```
t[k]   = share of the day's variance used by tick k:  t[0]=0, t[1]=GAP (0.2, the opening gap),
         then evenly to t[78]=1
W[k]   = W[k−1] + z·√(t[k] − t[k−1])                 a random walk, z ~ N(0,1)
B[k]   = W[k] − t[k]·W[78]                           the bridge: B[0] = B[78] = 0
x[k]   = t[k]·(R − J) + J·(k ≥ news) + β·σm·storm·M[k] + σs·storm·E[k]
price  = round(P0 · e^x[k], 2)                        R = ln(P1/P0), J = ln(1 + news shock)
```

`M` is one bridge shared by every stock (so the whole board rises and falls together, more for
high-beta stocks), `E` is each stock's own bridge, `news` is the tick a headline breaks (one
random tick per day; the affected stocks jump there). ETFs are priced each tick with the §3.3
formula, so MIX6 at 11:00 is exactly the weighted average of its holdings at 11:00.

**Worked example (shape, not random numbers):** P0 = 100, P1 = 104, no news. At the close
x = 1·ln(1.04) + 0 + 0 = ln 1.04 → price 104.00 exactly; in between the bridges add noise that
is largest at lunch (t ≈ 0.5) and zero at both ends.

**Volume** per tick = `TICK_DOLLARS / price × (1 + 1.5·m²) × (0.5 + |step| / usual step)` where
m runs −1 → 0 → +1 over the day: trading is busiest at the open and the close and on big moves.
**Order book:** three bids and three asks 0.05% apart around the last price, sizes drawn from a
seeded RNG. It is cosmetic; orders fill at the last price.

**History before day 0 (D-40):** a warm-up market (seed + 4,000,037, 120 days, 15-minute ticks)
is rescaled so its last close equals each symbol's day-0 price: `price(−k) = warm(120 − k) ×
day0 / warm(120)`. Candles for any day come from that day's session: open = first tick,
high/low = max/min of the ticks, close = last tick, volume = sum.

**Determinism:** day d of seed s uses `Random(s × 100,003 + d + 3,000,017)`, its own RNG, so a
session is the same whether you watch it live, skip it, or draw its candle later.

## 3.13 Margin trading — leverage (D-41, `engine/margin.py`)

A margin account lets **cash go below zero**; the negative cash is a **loan** from the broker.

```
equity E          = cash + holdings H                         (as before)
leverage used     = H / E
may borrow        = (L − 1) × (E − fee)                         L = allowed leverage, 1…5
buy allowed if    qty·price + fee ≤ cash + may borrow           → H ≤ L × E after the buy
maintenance m     = 0.5 / L                                     25% at 2×, 10% at 5×
margin call when  loan > 0 and E < m × H                        checked every tick while borrowing
then              sell the biggest holdings until H ≤ L × E     (all of them if E ≤ 0)
interest          loan × 8% / 252, every night
```

**Worked example (tests/test_margin.py):** $10,000, L = 2, fee $1. May borrow (2 − 1) × 9,999 =
**$9,999**. Buy 199 X @ $100 = $19,901 → cash **−$9,901** (the loan), H = 19,900, E = 9,999.

| X falls to | H | E = H − 9,901 | E / H | Margin call (m = 25%)? |
|---|---|---|---|---|
| $70 (−30%) | 13,930 | 4,029 | 28.9% | no |
| $65 (−35%) | 12,935 | 3,034 | 23.5% | **yes** → sell ⌈(12,935 − 2 × 3,033) / 65⌉ = **106** shares |
| $40 (−60%) | 7,960 | −1,941 | — | wiped out: sell all 199, cash = **−$1,942** still owed |

After selling 106 @ $65: 93 shares left (H = 6,045), cash = −9,901 + 6,890 − 1 = **−$3,012**,
E = 3,033, leverage 1.99× ≤ 2 ✓. One night's interest on the original loan: 9,901 × 0.08 / 252
= **$3.14**.

**How far can prices fall?** At full leverage E/H starts at 1/L. A fall x gives
(1/L − x)/(1 − x) = m = 1/(2L) ⇒ **x = 1/(2L − 1)**: 33% at 2×, 20% at 3×, 11% at 5×.
Everything is gone after a fall of **1/L**: 50% at 2×, 20% at 5×.

**Leverage Lab (E-08):** the same symbol over the last 60 days with $5,000: 1×, 2×, 3×, 5× on
margin (rules above, checked at each close) and a **2× daily-reset fund**
`V[d] = V[d−1] × (1 + 2 × r[d])`. Example of volatility decay: +10% then −10% leaves the market
at −1% but the 2× fund at 1.2 × 0.8 = **−4%**, worse than 2 × −1%.
