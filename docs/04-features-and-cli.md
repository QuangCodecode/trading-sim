# 04 — Features and CLI specification

Style: a command prompt (`> `), not numbered menus. Every screen is built in
`cli/views.py` with `rich` (Tables, Panels, colour). Mock-ups below are plain text; the
real output adds colour: **green** gains, **red** losses, **cyan** symbols, **yellow** tips.

The same commands and screens are available in two more front ends:
- the **web app** for ordinary players (`uv run main.py --web`, D-37, layout in §4.4). Its
  buttons send these command lines, and its Terminal page accepts any of them.
- **agent mode** for AI agents: one command per shell call, plain-text output (D-26, §4.7).

## 4.1 Command reference

| Command | Aliases | Phase | What it does |
|---|---|---|---|
| `help [command]` | `?`, `h` | 1 | List commands / show usage + example for one command |
| `market [SECTOR]` | `m` | 1, 9 | Price table: symbol, name, sector, price, today's change %, sparkline of last 10 days. `market tech` / `market real` (any sector prefix) or `market etf` show one group of the 114 symbols |
| `quote SYMBOL` | `q SYMBOL` | 1 | One symbol: price, day change, high/low so far, your holding |
| `chart SYMBOL [SYMBOL2]` | `c` | 1 | ASCII line chart from day 0 to today (two symbols → same chart, normalised to $100) |
| `etf [SYMBOL]` | | 1 | ETF composition (weights, sectors, each holding's current share) + a one-paragraph "what is an ETF" |
| `buy SYMBOL QTY` / `buy SYMBOL max` | `b` | 1 | Buy whole shares at today's price + fee |
| `sell SYMBOL QTY` / `sell SYMBOL all` | `s` | 1 | Sell shares |
| `portfolio` | `pf`, `p` | 1 | Holdings table + cash, equity, P&L summary |
| `history` | `hist` | 1 | Trade log |
| `next [N]` | `n` | 1 | Advance 1 or N days (N ≥ 1, capped at days remaining); shows market summary + news. A running session counts as the first day |
| `tick [N]` | `t`, `wait` | 9 | Let today's session run N five-minute ticks (default 1); stops at the closing bell (tick 78). Prints the time, breaking news and any margin call (D-39) |
| `leverage [N]` | `lev`, `margin` | 9 | Your margin account (allowed/used leverage, loan, interest, buying power, distance to a margin call) and the risk table; `leverage 2` sets the limit (1–5; lowering it needs you to already fit) (D-41) |
| `levlab [SYMBOL]` | `ll` | 9 | Leverage Lab: the last 60 days (history included) of SYMBOL (default MKT100) at 1×, 2×, 3×, 5× on margin and a 2× daily fund — table, chart, lessons (E-08) |
| `lab [SYMBOL] [ETF]` | | 1 | Diversification Lab (default: NVDA vs MIX6) |
| `lab mc [SYMBOL]` | | 1 (stretch) | Monte Carlo lab over `MONTE_CARLO_RUNS` fresh markets |
| `report` | | 1 | End-of-game style report at any time |
| `news [DAY]` | | 2 | Today's (or a past day's) events + ETF move breakdown |
| `coach` | | 3 | Session review tips (tips also appear after each trade, max 2) |
| `whatif` | `replay`, `wi` | 4 | 11 strategies replayed on the same market: ranked table, chart, lessons |
| `sectors` | `sector` | 8 | Each sector's move today, over 5 days and since day 0 |
| `robo [SYMBOL]` | `bot` | 8 | Robo-analyst (E-06): downturn chance + reasons, every symbol's 5-day outlook, track records |
| `story` | `moods` | 8 | The market's hidden moods so far, revealed 10 days late (all at the end) |
| `badges` | `achievements` | 8 | 20 badges, won and locked (X-05) |
| `challenge [NAME]` | `ch` | 8 | List the 9 challenges, or start one (restarts the game in place) |
| `learn [TERM]` | `glossary` | 8 | Glossary list, or one term explained (typos and partial words OK) |
| `quiz [A-D]` | | 8 | Show the next question / answer it; 5 right = Scholar badge |
| `new [SEED]` | | 8 | Start a new free-play game (seed 0–999,999, like `--seed`; a bigger one can't be saved) |
| `headlines` | `hl` | 5 | Headline Lab: every headline so far, keyword vs Laya (AI) verdict vs real move, plus the hit score |
| `hl "TEXT"` | | 5 | Classify your own headline with both methods (no truth column — it never happened) |
| `scenario list` / `scenario start NAME` | | X-01 | Challenge mode |
| `save [NAME]` / `load NAME` | | X-02 | Save/restore game |
| `games` | | X-07 | Your saved games: result vs the market, challenges passed, badges won across games (`history` is still the trade log) |
| `uv run main.py [--game NAME] [--db PATH] COMMAND…` | | X-06 | Agent mode: run one command on the saved game and exit (§4.7) |
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
- If the player **holds** an affected stock, add: "Your NVDA position changed by $X that day."
  Shown in the NEWS lines after `next` only (holdings can't change during `next`, so the
  quantity is right; for an old day in `news DAY` it might not be).
- Market-wide events say "Market-wide news can't be diversified away" instead of the
  share sentence (every holding was hit). `news 0` / a future day → friendly error.
- The `event_templates` table ships 84 templates (23 good, 23 bad; D-36), including tricky headlines
  such as "Walmart sales not as bad as feared", "Electric car boom dents oil demand" and
  "Bank stress fears fade as deposits return". A headline can't repeat within 40 days.

### E-03 Trade Coach (Phase 3)

Rules are small functions in a list `RULES` — each takes the game (and optionally the
trade just made) and returns a `Tip` or `None`. Easy to add/remove; easy to unit-test.

| ID | When checked | Trigger | Tip (example) |
|---|---|---|---|
| CONC | after buy | a single **stock** > `CONCENTRATION_LIMIT` (50%) of equity (ETFs exempt — they're already diversified) | "NVDA is now 62% of your money. One bad headline could hurt a lot — MIX6 spreads risk across 6 companies." |
| PANIC | after sell | sold at a loss **and** the price is ≥ `PANIC_DROP` (8%) below its high of the last `PANIC_WINDOW_DAYS` (3) days | "You sold NVDA right after a sharp drop. Selling in panic locks in losses; ask 'has anything really changed?'" |
| CHASE | after buy | the symbol rose ≥ `CHASE_RISE` (12%) over the last 5 days | "NVDA is up 15% in 5 days. Buying after a big jump is 'chasing' — hot streaks often cool off." |
| OVER | after any trade | ≥ `OVERTRADE_PER_DAY` (5) trades on the same day | "5 trades today = $5 in fees. Frequent trading rarely beats patience." |
| IDLE | session review | day ≥ `IDLE_CASH_GRACE_DAYS` (10) and cash > `IDLE_CASH_LIMIT` (80%) of equity | "80% of your money is sitting in cash. Cash is safe but doesn't grow." |
| FEES | session review | fees ≥ $10 and fees > `FEE_SHARE_LIMIT` (25%) of |total P&L| | "Fees ate 40% of your profit." |
| GOOD | session review | owns ≥ 3 sectors (looking inside ETFs) and no single stock > 30% | "Nicely diversified — no single company can sink you." (positive feedback matters) |

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
   - The Laya verdict comes from `SentimentClassifier.classify`: a two-label Choice
     (positive / negative) plus the probability of its pick (D-22). Below `NEUTRAL_BAND`
     it is shown dimmed as "(unsure)" but still scored.
   - The truth is the sign of the event's shock.
3. Score each method: hits out of headlines.
4. Closing lesson by rule:
   - Laya beat the keywords: "Words like 'bad' or 'record' can point the wrong way. Reading the whole sentence matters."
   - They tied: "Simple headlines are easy. Watch the tricky ones."
   - Laya did worse: "The AI missed more than the word counter this time — it reads language well, but it isn't magic."
   - Always: "Sentiment isn't price: even a correct call doesn't say how much. On day D
     SYMBOL moved X%, but MIX6 only Y%." (uses the headline with the biggest stock move)
5. **AI offline** (model not downloaded, `laya` not installed, load error, odd answer):
   - The Laya column shows `—` and the score line says "AI offline: keyword counter only".
   - Never a traceback (N-08).
6. **Own headline:** both verdicts are shown, with no truth and no score. Empty text gives "Usage: hl \"TEXT\"".
   - Text over 200 characters is rejected by the parser.
   - The keyword line lists the words it counted (e.g. `bad −, feared −`) so the player sees *why* it failed.
7. NEWS lines after `next` end with `· Laya: negative 91%` when the answer is cached (never loads the model).

**Real output** (`--seed 42`, `next 60`, `hl`)
```
 Day  Headline                                         Keywords    Laya (AI)       Real move   MIX6
  21  Record highs fail to hold as chip rally fizzles  positive ✗  negative 72% ✔  AAPL -6.3%  -1.1%
  41  Exxon hit with record fine over oil spill        negative ✔  negative 97% ✔   XOM -8.9%  -1.4%
  47  AI spending boom lifts tech shares               positive ✔  positive 97% ✔  NVDA +14.4% +5.2%
  …
 Score: keywords 4/6 · Laya 6/6
 ▸ Words like 'bad' or 'record' can point the wrong way. Reading the whole sentence matters.
 ▸ Sentiment isn't price: even a correct call doesn't say how much. On day 47 NVDA moved +14.4%, but MIX6 only +5.2%.
```
Over all 46 templates (D-36): keywords 37/46, Laya 44/46 (its misses: "Central bank surprises
with rate cut", shown as `negative 53% (unsure)`, and "JPMorgan sets aside billions for bad loans").

**Caching and demo safety (D-20, D-21, D-23)**
- `classify` checks the `sentiment` tables first (shipped labels in `reference.db`, typed headlines in `player.db`); a hit is used and the model is never loaded.
- On a miss it loads Laya from `models/laya/` (once, ~10 s, CLI shows a spinner), asks it,
  stores the answer, then saves the cache. `HF_HUB_OFFLINE=1` is set so it never goes online.
- `tools/download_model.py` fetches the weights once; `tools/warm_cache.py` labels every
  event headline, so the game shows Laya's answers even on a machine without the model.
- Headlines the player types with `hl "TEXT"` are cached too, in `saves/player.db` (git-ignored),
  so playing never changes a committed file.

## 4.4 Web app layout (D-37)

Run with `uv run main.py --web` (opens `http://127.0.0.1:8000`; `--seed 39`, `--port`, `--no-browser`).
Modelled on a Vietnamese broker's price board: dark, dense, colour-coded, live.

```
┌ TradeSim │ [MKT100 101.40 ▲+1.40% ~spark~] [TECHX …] [FINX …] … │ 11:35 ●LIVE  Day 3/60 · Wed 07 Jan │ [⏸ 1× 2× 5× 15×] [To close ⏭] [Skip days ▾] │ Your money $10,234 │
├──────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│Board │ 🔍 search   All ★Watchlist My holdings ETFs Communication Consumer Energy …                     ▲ above ref ■ unchanged ▼ below │
│Trade │ Symbol│ Ref │ Bid3 Vol Bid2 Vol Bid1 Vol │ Price ± % Vol │ Ask1 Vol Ask2 Vol Ask3 Vol │ Total vol │ High Low Open │ You: Qty P&L│
│Port. │ ★AAPL │180.00│ 180.65 38K …            │ 180.92 +0.92 ▲0.51% 32K │ 181.01 45K …   │ 200K │ 180.97 180.72 180.97 │  40  −0.4% │
│News  │  … 114 rows, prices flash green/red as they tick; double-click a row (or B / S) for the order ticket …                    │
│Lever.│                                                                                                                            │
│Labs …│                                                                                                     toasts stack bottom-right │
├──────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 😱 Fear gauge 13 (calm) · 🏦 Borrowing $19,910 · margin call if holdings fall 20.1%      📰 latest headlines scroll…     seed 39 │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

| Page | What's on it |
|---|---|
| Board | The price board above. Tabs per sector, watchlist (★, saved in the browser), my holdings, ETFs; search (`/`); sort by price, %, volume; ↑/↓ select, Enter/B buy, S sell |
| Trade `#trade/NVDA` | Symbol picker · big last price vs ref · OHLC + volume · **candlestick chart**: 1D (15-minute candles, live), 1M/3M/6M/All (daily candles back to day −120), candles/line, MA 20/MA 50, volume pane, your buys ▲ / sells ▼, crosshair tooltip · order ticket (Buy/Sell, quantity, 25/50/75/Max, cost, fee, borrowed amount) · 3-level order book · about (beta, yearly volatility, 6-month high/low) · Robo outlook · position · news |
| Portfolio | Equity, today, cash or loan, invested, leverage used/allowed, safety cushion · you vs MKT100 chart · sector exposure (inside ETFs) · holdings (Trade / Sell all) · trade history (margin-call sales flagged) · coach |
| News | Every headline seen (newest first) with Laya vs keywords vs what really happened (after the close), the moves it caused; Headline Lab "test your own" |
| Leverage | 4 concept cards · margin account: 1×–5× picker, buying power, loan, nightly interest, safety-cushion bar with the maintenance line · "what a move does" calculator (two sliders, yours/borrowed bars, margin-call and wipe-out warnings) · Leverage Lab chart + table + lessons · risk table |
| Labs | Diversification Lab (any stock vs any ETF, last 60 days) · What-if Replay (ranked table + 4 curves + lessons) · Monte Carlo (200 markets) |
| Robo | Mood detector (downturn chance, reasons) · 5-day forecaster: most bullish / bearish symbols, honest scores |
| Learn | Quiz (A–D buttons, feedback) · 20 badges · searchable glossary (33 terms) |
| Goals | 9 challenge cards (confirm before restarting) · current goals · free play with a seed |
| Terminal | Any command, drawn exactly like the terminal (rich → HTML) |

- **The clock** lives in the page: every `1/speed` seconds it POSTs `/api/tick` (1 tick per request,
  up to 3 at 15×) and waits for the reply before the next one, so ticks never overlap. Pause with ⏸ or
  space. "To close ⏭" runs the rest of the day (`tick N`); "Skip days" runs `next N`.
- **Closing bell**: a dialog with you vs the market and the day's best/worst stocks; "Keep the market
  running" turns it into a toast instead. The game-over dialog shows the final report (rich → HTML).
- **Notices → toasts**: `WebSession.run` compares the game before/after each command and queues
  notices (trade, coach tip, breaking news, margin call, closing bell, badge, leverage change). The
  page asks for notices newer than the last id it showed; after a reload old ones are skipped.
- **Errors**: rule breaks (`TradeSimError`) → HTTP 400 with the friendly message → a red toast (or a
  red line in the Terminal). Bad JSON, out-of-range ticks, unknown paths → 400/404; a bug → 500 and
  the traceback in the server's terminal; the server never stops.
- **Tutorial (D-49)**: the first visit opens a required, 36-step tutorial (part 1 the screen, part 2 the ten
  pages, part 3 a guided first game). It lights up one part of the page with a card beside it; the rest of the
  page is `inert`. In part 3 *Next* unlocks only when the game shows the task is done (market open, speed 5×,
  paused, NVDA bought, day closed, NVDA sold, days skipped). A pop-up (the closing bell) hides the card until
  it is closed. Reload resumes at the furthest step; the last card keeps the game or starts a fresh one. The
  sidebar **Tour** button replays it (closable, nothing enforced). Dev tools: set `localStorage.tradesim.tutorial`
  to `done` to skip it, or `tradesim.tutorial.step` to `35` to jump to the last card.
- **Safety**: listens on 127.0.0.1 only; static files only from `webapp/static/` (no `..`); request
  bodies ≤ 10 KB; command lines ≤ 300 characters.

## 4.5 Extension specs (only if time allows)

**X-01 Challenge scenarios** — the `challenges` table (the spec below shows the original JSON shape):
```json
{"id": "tech_crash", "title": "Survive the Tech Crash", "seed": 2024, "days": 30,
 "forced_events": [{"day": 8, "template": "chip_curbs", "shock": -0.20}],
 "goal": {"type": "min_equity", "value": 9500},
 "intro": "Rumours say tech is overheated. Finish 30 days with at least $9,500."}
```
Goal types: `min_equity`, `beat_symbol` (beat buy-and-hold of a symbol), `max_drawdown_below`.
Show PASS/FAIL + a lesson at the end. Suggested set: Tech Crash, Bull Run (beat MIX6),
Sideways Market (keep fees < $10 and finish positive).

**X-02 Save / load (D-46)** — `saves/player.db` (SQLite) has `games` (seed, days, challenge, a `slot` such as
`agent` or `web` for the current game, and a summary row refreshed after every saved command),
`commands` (the lines that changed the game, in order), `badges` and `sentiment`. On load, rebuild
`Market` from the seed and replay the commands through `app.execute`. A command that no longer works,
a damaged file or another `user_version` → friendly "damaged" error. `new` / `challenge` archive the old
game (slot → NULL) and start a new row, so nothing is lost. The web app autosaves after every command and
resumes its last unfinished game on restart; `--seed` starts a fresh one. The REPL keeps nothing.

**X-07 `games`** — one row per saved game (newest first): started, name (challenge title or `Free play, seed N`),
day, return, market return, result (✅ passed / ❌ failed / 🏁 finished / ▶ playing now / left unfinished), then the
badges won across all games. `GET /api/games` returns the same rows as JSON. Resuming a full 60-day web game
(4,680 one-tick commands) takes about 0.6 s.

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
- `hl` with no downloaded model, `laya` not installed, an odd model answer, or a corrupt `player.db` (treated as an empty cache).
  Each falls back to the keyword counter (a corrupt cache is treated as empty).
- `hl ""`, `hl` with 201+ characters, `hl` before any news.
- Agent mode: no saved game yet; damaged/edited database; `--seed` different from the saved game;
  a failing command (exit 1, file unchanged); `quit` (just says "still playing" — use `report`).
- Web app: bad command in the Command tab; Buy/Sell/Next after game over (buttons disabled);
  `lab` before day 5 (red message in the Lab tab).

## 4.7 Agent mode (X-06, D-26)

Lets a script play from a shell, one command per call:

```bash
uv run main.py --seed 42 market     # no saved game yet → new seed-42 game ('agent') in saves/player.db
uv run main.py buy NVDA 20          # continues that game
uv run main.py next 5
uv run main.py hl "Walmart sales not as bad as feared"
uv run main.py report
uv run main.py new                  # start over (the old game stays in `games`); or --game NAME for a second game
```

- **Output:** first a status line (`Day 5 / 60 · Cash $7,599.00 · Equity $9,943.80 · Seed 42`),
  then the same screens as the REPL with no colour codes, `AGENT_WIDTH` (100) characters wide.
- **Exit code:** `0` ok; `1` for any `TradeSimError`, printed as one `✗ …` line. Agents can use it to
  notice a rejected trade.
- **Saved game** (`--game NAME`, default `agent`, in `--db PATH`, default `saves/player.db`): a `games` row
  (seed, days, challenge) plus its `commands` rows, e.g. `buy NVDA 20`, `next 5`.
  - Only successful `buy`/`sell`/`next`/`tick`/`quiz`/`leverage` lines are stored.
  - Loading rebuilds the market from the seed and replays them through `app.execute`, giving the
    identical game (D-08). Prices and cash are never stored, so they can't be edited.
  - `--seed`/`--days` only apply when the game is created. A different `--seed` later is refused (use `new SEED`).
  - A new game is saved only after a state-changing command or when `--seed` is given, so `help` or
    `market` before choosing a seed doesn't lock in a random one.
  - A damaged database, another version, or a stored command that now fails → `Saved game '…' is damaged`, exit 1.
- **Prompt to give an agent** (also in the README): *"Play TradeSim. Run `uv run main.py help`
  to see the commands, then `uv run main.py --seed 42 market` to start. Run one command per call
  and try to beat MIX6 by day 60."*
