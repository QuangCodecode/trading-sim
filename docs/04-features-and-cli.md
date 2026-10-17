# 04 — Features and CLI specification

Style: a command prompt (`> `), not numbered menus. Every screen is built in
`cli/views.py` with `rich` (Tables, Panels, colour). Mock-ups below are plain text; the
real output adds colour: **green** gains, **red** losses, **cyan** symbols, **yellow** tips.

From Phase 5 the same screens live inside a **Textual dashboard** (D-17, layout in §4.4).
Every command below still works from its command box. `python3 main.py --plain` keeps
the Phase 1 REPL.

## 4.1 Command reference

| Command | Aliases | Phase | What it does |
|---|---|---|---|
| `help [command]` | `?`, `h` | 1 | List commands / show usage + example for one command |
| `market` | `m` | 1 | Price table: symbol, name, sector, price, today's change %, sparkline of last 10 days |
| `quote SYMBOL` | `q SYMBOL` | 1 | One symbol: price, day change, high/low so far, your holding |
| `chart SYMBOL [SYMBOL2]` | `c` | 1 | ASCII line chart from day 0 to today (two symbols → same chart, normalised to $100) |
| `etf [SYMBOL]` | | 1 | ETF composition (weights, sectors, each holding's current share) + a one-paragraph "what is an ETF" |
| `buy SYMBOL QTY` / `buy SYMBOL max` | `b` | 1 | Buy whole shares at today's price + fee |
| `sell SYMBOL QTY` / `sell SYMBOL all` | `s` | 1 | Sell shares |
| `portfolio` | `pf`, `p` | 1 | Holdings table + cash, equity, P&L summary |
| `history` | `hist` | 1 | Trade log |
| `next [N]` | `n` | 1 | Advance 1 or N days (N ≥ 1, capped at days remaining); shows market summary + news |
| `lab [SYMBOL] [ETF]` | | 1 | Diversification Lab (default: NVDA vs MIX6) |
| `lab mc [SYMBOL]` | | 1 (stretch) | Monte Carlo lab over `MONTE_CARLO_RUNS` fresh markets |
| `report` | | 1 | End-of-game style report at any time |
| `news [DAY]` | | 2 | Today's (or a past day's) events + ETF move breakdown |
| `coach` | | 3 | Session review tips |
| `whatif` | `replay` | 4 | Strategy comparison table + chart |
| `headlines` | `hl` | 5 | Headline Lab: every headline so far, keyword vs Jev verdict vs real move, plus the hit score |
| `hl "TEXT"` | | 5 | Classify your own headline with both methods (no truth column — it never happened) |
| `scenario list` / `scenario start NAME` | | X-01 | Challenge mode |
| `save [NAME]` / `load NAME` | | X-02 | Save/restore game |
| `short SYMBOL QTY` | | X-03 | Open/increase a short (cover with `buy`) |
| `quit` | `exit` | 1 | Confirm, show final report, exit |

### Parsing rules (`cli/parser.py`)

- Split on whitespace; command and symbols are **case-insensitive** (`Buy aapl 5` works).
- Empty line → ignored. Leading/trailing spaces ignored.
- Unknown command → `CommandError` with a suggestion from
  `difflib.get_close_matches` (stdlib): `Unknown command "biy". Did you mean "buy"?`
- Wrong arg count → `CommandError` with the usage line: `Usage: buy SYMBOL QTY  e.g. buy AAPL 10`.
- QTY must be a positive whole number, or the keywords `max` (buy) / `all` (sell).
  `"10.5"`, `"-3"`, `"0"`, `"ten"` → `Quantity must be a whole number greater than 0.`
- The parser only checks *shape*. Business rules (enough cash, symbol exists, holdings)
  are enforced by the engine via exceptions.
- `Ctrl+C` / `Ctrl+D` (KeyboardInterrupt / EOFError) → treated as `quit` gracefully.

## 4.2 Screens

### Startup

```
╭──────────────────────── TradeSim ────────────────────────╮
│  Learn to invest with $10,000 of virtual cash.           │
│  60 trading days · 6 stocks · 1 ETF (MIX6)               │
│  Prices are SIMULATED. Not real data, not advice.        │
│  Seed 42  — run with --seed 42 to replay this market.    │
╰──────────────────────────────────────────────────────────╯
Type help for commands, market to see prices, lab to learn about diversification.
```

### `market`

```
Day 12 / 60
Symbol  Name          Sector     Price    Today   Last 10 days
AAPL    Apple         Tech      186.40   +1.21%   ▃▄▄▅▆▅▆▇▇█
NVDA    NVIDIA        Tech      110.05   -8.34%   ▅▆▇█▇▆▆▅▄▁
XOM     Exxon Mobil   Energy    112.31   +0.40%   ▄▄▅▄▃▄▅▅▅▆
CVX     Chevron       Energy    151.20   -0.12%   ▅▄▄▅▅▄▄▅▅▅
KO      Coca-Cola     Consumer   60.88   +0.05%   ▄▄▄▅▄▄▅▅▅▅
WMT     Walmart       Consumer   71.02   +0.33%   ▃▄▄▄▅▅▅▅▆▆
MIX6    Mix-6 ETF     ETF        99.12   -2.10%   ▅▅▆▇▆▆▆▆▅▃
```

### `buy` confirmation (and rejection)

```
> buy nvda 20
Bought 20 NVDA @ $110.05 = $2,201.00 + $1.00 fee.  Cash left: $7,798.00
> buy nvda 200
✗ Not enough cash: need $22,011.00, you have $7,798.00. Max you can buy: 70 (try: buy NVDA max)
```

### `portfolio`

```
Day 12 / 60
Symbol  Qty   Avg cost    Price    Value      Unrealised       Weight
NVDA     20    110.05    110.05   2,201.00      +0.00 (+0.0%)   21.4%
MIX6     30     98.40     99.12   2,973.60     +21.60 (+0.7%)   28.9%
────────────────────────────────────────────────────────────────────────
Cash                                5,109.40                    49.7%
Equity    10,284.00      Total P&L  +284.00 (+2.84%)
Realised    +265.40      Unrealised  +21.60      Fees  -3.00
```
(Numbers illustrative; the three P&L parts must always add up to Total P&L.)

### `chart NVDA MIX6` (two series normalised to $100 at day 0)

```
 NVDA (*) vs MIX6 (o) — value of $100 invested, day 0 → 12
 112 ┤          **
 108 ┤        **  *
 104 ┤   ** **     *
 100 ┼oo*oo*ooooooo*ooo
  96 ┤  *            *o
  92 ┤                 *
     └──────────────────
      0     4     8    12
```

Algorithm (`cli/charts.py`, pure function returning `list[str]` so it's testable):
1. Resample each series to at most `CHART_WIDTH` points (pick evenly spaced indices).
2. `lo, hi = min, max` across all series (if `hi == lo`, pad by 1).
3. `row = round((v − lo) / (hi − lo) × (CHART_HEIGHT − 1))`; draw bottom-up in a 2D list
   of characters (a 2D-list exercise — LO8). Overlaps draw `#`.
4. Left axis labels at top/middle/bottom rows; bottom axis with day ticks.

Sparkline: map each value to one of `▁▂▃▄▅▆▇█` by the same scaling with 8 levels.

### End-of-game report (also `report`)

```
╭────────────── Final report — Day 60 ──────────────╮
│ Starting cash   $10,000.00                         │
│ Final equity    $10,912.45   (+9.12%)              │
│ Realised +612.10 · Unrealised +318.35 · Fees -18   │
│ Best holding  AAPL  +14.2%   Worst  XOM  -6.1%     │
│ Max drawdown  7.8%   Trades 18                     │
╰────────────────────────────────────────────────────╯
Coach says: (Phase 3 tips here)
Curious how other choices would have done? Type whatif.
```

## 4.3 Feature specs — original features

### E-01 Diversification Lab (headline, Phase 1)

**Command:** `lab [STOCK] [ETF]` — defaults NVDA vs MIX6; window = day 0 → today.

**Behaviour**
1. Requires today ≥ 5 (else: "Play at least 5 days first — or try `lab mc` for a
   simulated preview.").
2. Imagine investing `LAB_DEFAULT_AMOUNT` ($5,000) in each at day 0 (fractional, no fees —
   it's a thought experiment; say so on screen).
3. For each series compute (from `analytics.py`): final value, total return, volatility,
   worst day, max drawdown.
4. Show a two-column comparison table, a normalised chart (`chart` renderer), and a
   verdict generated by rules:

| Condition | Verdict sentence |
|---|---|
| stock vol ≥ 1.5 × ETF vol | "NVDA swung {x}× harder day to day than MIX6." |
| stock drawdown > ETF drawdown | "At its worst, NVDA was {a}% below its peak; MIX6 only {b}%." |
| stock return > ETF return **and** stock vol ≤ ETF vol | "KO beat MIX6 this time with smaller swings — one stock can get lucky over a few days. Try: lab mc KO to see the odds over 200 markets." (added after Bug 1) |
| stock return > ETF return (stock riskier) | "NVDA earned more this time — but you took much more risk to get it. Would you have held through the {a}% drop?" |
| stock return ≤ ETF return | "MIX6 did better *and* was calmer. That's diversification working." |
| always | "MIX6 holds 6 companies in 3 sectors, so bad news for one is diluted by the others." |

**Mock-up**
```
 Diversification Lab — $5,000 in NVDA vs $5,000 in MIX6, day 0 → 30
                      NVDA        MIX6
 Final value      $5,412.00   $5,188.00
 Total return        +8.2%       +3.8%
 Daily swing (vol)    3.1%        1.0%
 Worst day           -9.4%       -2.7%
 Max drawdown        24.3%        6.9%
 [chart]
 ▸ NVDA swung 3.1× harder day to day than MIX6.
 ▸ At its worst, NVDA was 24.3% below its peak; MIX6 only 6.9%.
 ▸ NVDA earned more this time — but would you have held through a 24% drop?
```

**Stretch — `lab mc [STOCK]`:** build `MONTE_CARLO_RUNS` fresh `Market`s with seeds
`game_seed + 1 … + runs`, `GAME_DAYS` long; for each record stock vs ETF total return.
Report: average return of each, % of runs with loss worse than −20%, best/worst run.
Must finish in < 3 s. Shows diversification is about **odds**, not one lucky path.

### E-02 Market Events + Explainer (Phase 2)

- Events generated per §3.7. When `next` passes a day with events, print each headline
  as a yellow NEWS line with affected symbols and their move.
- `news [DAY]` shows, for that day: headline, explanation text, then the MIX6 breakdown
  table (§3.4): each stock's move %, weight, contribution in points, and the explainer
  sentence built from the numbers (template below).
- Explainer template: *"{affected} moved {x}%. They make up about {share}% of MIX6 today,
  so they moved the ETF {c} points. Everything else moved it {o} points. Net: MIX6 {m}%."*
  where `share = Σ w_i·P[i][t−1]/P[i][0] / Σ_all (same) × 100` (current effective weight).
- If the player **holds** an affected stock, add: "Your NVDA position changed by $X today."

### E-03 Trade Coach (Phase 3)

Rules are small functions in a list `RULES` — each takes the game (and optionally the
trade just made) and returns a `Tip` or `None`. Easy to add/remove; easy to unit-test.

| ID | When checked | Trigger | Tip (example) |
|---|---|---|---|
| CONC | after buy | a single **stock** > `CONCENTRATION_LIMIT` (50%) of equity (ETFs exempt — they're already diversified) | "NVDA is now 62% of your money. One bad headline could hurt a lot — MIX6 spreads risk across 6 companies." |
| PANIC | after sell | sold at a loss **and** that symbol fell ≥ `PANIC_DROP` (8%) over the last `PANIC_WINDOW_DAYS` (2) days | "You sold NVDA right after a sharp drop. Selling in panic locks in losses; ask 'has anything really changed?'" |
| OVER | after any trade | ≥ `OVERTRADE_PER_DAY` (5) trades on the same day | "5 trades today = $5 in fees. Frequent trading rarely beats patience." |
| IDLE | session review | day ≥ `IDLE_CASH_GRACE_DAYS` (10) and cash > `IDLE_CASH_LIMIT` (80%) of equity | "80% of your money is sitting in cash. Cash is safe but doesn't grow." |
| FEES | session review | fees ≥ $10 and fees > `FEE_SHARE_LIMIT` (25%) of |total P&L| | "Fees ate 40% of your profit." |
| GOOD | session review | holds MIX6 or ≥ 3 sectors, and no stock > 30% | "Nicely diversified — no single company can sink you." (positive feedback matters) |

Show at most 2 tips after a trade (so it's not naggy); `coach` shows all session tips.

### E-04 What-if Replay (Phase 4)

- `whatif` runs every strategy in §3.8 over day 0 → today on the **same** market.
- Output: table sorted by final equity with columns *Strategy · Final · Return · Max
  drawdown · Volatility · Trades · Fees*; "Your trades" row highlighted; then a chart of
  "Your trades" vs "Hold MIX6" vs the best strategy.
- Closing lesson line chosen by rules, e.g. if Panic seller < All-in: "Panic-selling
  turned a temporary dip into a permanent loss." If Hold MIX6 beat "Your trades": "Doing
  less would have earned more — a classic lesson."
- Correctness check: the "Your trades" replay's final equity must equal the real game's
  equity (assert in tests; if it ever differs, the replay engine has a bug).

### E-05 Headline Lab (Phase 5, AI)

**Command:** `headlines` / `hl`, or `hl "your own headline"`.

**Behaviour**
1. Collect every `MarketEvent` from day 1 → today (none yet → "No news so far. Try
   `next 5`, or `hl \"Chipmaker beats forecasts\"`.").
2. For each headline:
   - The keyword verdict comes from `headline_lab.keyword_verdict`: (positive hits − negative hits).
     Over 0 is positive, under 0 is negative, 0 is neutral.
   - The Jev verdict comes from `sentiment.classify`: a label plus a probability.
     A probability below `NEUTRAL_BAND` shows as neutral.
   - The truth is the sign of the event's shock.
3. Score each method: hits out of headlines.
4. Closing lesson by rule:
   - Jev beat the keywords: "Words like 'bad' or 'record' can point the wrong way. Reading the whole sentence matters."
   - They tied: "Simple headlines are easy. Watch the tricky ones."
   - Always: "Sentiment isn't price. Even correct news calls don't tell you *how much* a stock moves, and the ETF moved less than either."
5. **AI offline** (no key, network error, timeout, bad response):
   - The Jev column shows `—` and the score line says "AI offline: keyword counter only".
   - Never a traceback (N-08).
6. **Own headline:** both verdicts are shown, with no truth and no score. Empty text gives "Usage: hl \"TEXT\"".
   - Text over 200 characters is rejected by the parser.

**Mock-up**
```
 Headline Lab — day 1 → 24                 Keywords   Jev (AI)      Real move
 d3  Chip export curbs hit tech stocks     negative   negative 97%  NVDA −8.1% ✔✔
 d9  Walmart sales not as bad as feared    negative✗  positive 88%  WMT  +4.2% ✗✔
 d15 Oil glut fears ease as demand recovers negative✗  positive 91%  XOM  +3.0% ✗✔
 d21 Record highs fail to hold…            positive✗  negative 84%  AAPL −5.5% ✗✔
 Score: keywords 1/4 · Jev 4/4
 ▸ Words like "bad" or "record" can point the wrong way. Reading the whole sentence matters.
 ▸ Sentiment isn't price: MIX6 moved only −1.6% on day 3.
```

**Caching and demo safety (D-20)**
- `classify` checks `data/sentiment_cache.json` first; a hit is used and the network is never touched.
- On a miss it calls Jev with `JEV_TIMEOUT_S`, stores the answer, then saves the cache.
- `tools/warm_cache.py` labels every `events.json` headline once before the demo, so the live demo needs no Wi-Fi.
- The API key comes only from the `JEV_API_KEY` environment variable. Never print it, log it or commit it.

## 4.4 Textual dashboard layout (Phase 5, D-17)

```
┌ TradeSim · Day 12/60 · Equity $10,284.00 (+2.84%) · Seed 42 ─────────────────┐
│ [Market] [Portfolio] [Lab] [News] [Headlines] [What-if]          ← tabs (F1–F6)│
│ ┌ market table (views.market_table) ─┐ ┌ chart (charts.line_chart) ────────┐ │
│ │ AAPL 186.40 +1.21% ▃▄▄▅▆▅▆▇▇█      │ │ NVDA (*) vs MIX6 (o)               │ │
│ │ NVDA 110.05 −8.34% ▅▆▇█▇▆▆▅▄▁      │ │ … click a row to chart it          │ │
│ └────────────────────────────────────┘ └────────────────────────────────────┘ │
│ NEWS d12: Chip export curbs hit tech stocks — Jev: negative 97%               │
│ > buy nvda 20_                                   [Next day ▶] [Next 5 ▶▶]      │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Reused unchanged:** `parser.parse`, `views.*` and `charts.*`. Textual's `Static` widget displays the rich
  Tables and Panels that `views.py` already returns.
- **New in `tui.py`:**
  - One `App` subclass with `compose()`.
  - An `Input` whose submit handler runs the same parse → handler → view steps as `app.py`.
  - Two buttons that call `game.advance`.
  - `TradeSimError` shows as a red message line, as in the REPL.
- **Kept simple**: plain `on_button_pressed` / `on_input_submitted` methods, with no
  `@on` decorators, no async code and no custom CSS beyond a few lines.

## 4.5 Extension specs (only if time allows)

**X-01 Challenge scenarios** — `data/scenarios.json`:
```json
{"id": "tech_crash", "title": "Survive the Tech Crash", "seed": 2024, "days": 30,
 "forced_events": [{"day": 8, "template": "chip_curbs", "shock": -0.20}],
 "goal": {"type": "min_equity", "value": 9500},
 "intro": "Rumours say tech is overheated. Finish 30 days with at least $9,500."}
```
Goal types: `min_equity`, `beat_symbol` (beat buy-and-hold of a symbol), `max_drawdown_below`.
Show PASS/FAIL + a lesson at the end. Suggested set: Tech Crash, Bull Run (beat MIX6),
Sideways Market (keep fees < $10 and finish positive).

**X-02 Save / load** — `saves/NAME.json` stores `{version, seed, num_days, day,
starting_cash, fee, cash, positions, trades, scenario_id}`. On load, rebuild `Market` from
the seed and **verify** by replaying trades that cash/positions match (detects tampering or
version mismatch → friendly error). Handle missing file, bad JSON, wrong version.

**X-03 Short selling** — rules in §3.9; `portfolio` shows shorts with a "SHORT" tag and
negative qty.

## 4.6 Edge cases checklist (each should have a test or a manual check)

- Buy with exactly enough cash (cash ends at 0.00) ✔ allowed.
- Buy 1 share that costs more than cash → rejected with max-qty hint (max may be 0).
- Sell more than held; sell a symbol never held; sell `all` of nothing.
- `next 0`, `next -2`, `next abc`, `next 999` (caps at remaining days, says so).
- Trading after game end → `GameOverError` message.
- Price hitting `MIN_PRICE` floor; ETF still computed correctly.
- `lab` before day 5; `lab` with an ETF as the "stock" argument or unknown symbol.
- `chart` with a flat series (hi == lo) — no division by zero.
- Very long input, unicode input, only spaces.
- `--days 1` game; `--seed` negative or huge.
- `hl` with no API key, a network timeout, a malformed Jev reply, or a corrupt `sentiment_cache.json`.
  Each falls back to the keyword counter (a corrupt cache is treated as empty).
- `hl ""`, `hl` with 201+ characters, `hl` before any news.
