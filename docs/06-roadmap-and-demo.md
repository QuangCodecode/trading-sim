# 06 — Roadmap, demo plan and scoring checklist

## 6.1 Timeline (adjust to the real teaching calendar)

Now ≈ late September (around Week 8). Final project due **Week 12**; **Assignment 2 is
due Week 11** — keep that week light. The unit allows **multiple submissions**, so submit
a working version early and upgrade it.

| When | Phase | Goal | Submit? |
|---|---|---|---|
| Week 8 | 0 → 1 (engine) | Setup + engine classes + tests | — |
| Week 9 | 1 (CLI + Lab) | Fully playable core + Diversification Lab | **v1 → show tutor** |
| Week 10 | 2 + 3 | Events/Explainer, Trade Coach | v2 |
| Week 11 | 4 (light — A2 due) | What-if Replay | — |
| Week 11–12 | 5 | Web app (first Streamlit, now `--web`) + agent mode + Headline Lab (stand-out layer, D-19/D-25/D-26) | v3 |
| Week 12 | 7 (+6 if ahead) | Polish, demo seed, Padlet, final tests | **Final** |

> **Status 2026-10-18:** v1 done — Phases 1, 2 and 5b (Headline Lab on local Laya AI).
> v1 scope agreed with Quang: Phases 1, 2 and 5b (Headline Lab on Laya, D-21) in the
> rich REPL; Coach, What-if and the Textual dashboard follow after v1. If time runs
> short, cut in this order: Phase 6 → What-if (4) → Textual (5a). Keep Headline Lab (5b),
> since it works in the plain REPL too.
>
> **Update 2026-10-18 (D-25..D-27):** Streamlit replaces Textual as 5a, and agent mode
> (5c, X-06) lets AI agents play from a shell. Both are done.
>
> **Update 2026-10-18 (D-29..D-36):** Phases 3 and 4, X-01 and X-05 are done, plus the
> Phase 8 expansion (real-life trends, Robo-analyst, Academy, web redesign). Left: Phase 7 polish.
| Week 13 | — | 3-min live demo | — |

**Rule:** a later phase never starts while an earlier phase has failing tests or a known crash.

## 6.2 Phase checklists (tick as you go)

### Phase 0 — Setup
- [x] Folder layout from `02-architecture.md` §2.2, empty modules with docstrings
- [x] `requirements.txt`, `requirements-dev.txt`, `.gitignore` (`.venv/`, `saves/`, `__pycache__/`)
- [x] `config.py` with all constants; `errors.py` with the exception tree
- [x] `main.py` with `argparse` (`--seed`, `--days`), prints banner and exits
- [x] `pytest` runs (one smoke test)
- [x] (optional) `git init` and first commit

### Phase 1 — Core + Diversification Lab (C-01…C-09, E-01)
- [x] `data/universe.json` + `loader.py` with validation
- [x] `Stock`, `ETF` (+ `contributions`), `Market` (seeded generation, `from_prices` factory)
- [x] `Position`, `Trade`, `Portfolio` (buy/sell/valuation/P&L, invariant)
- [x] `analytics.py` (returns, volatility, worst day, max drawdown)
- [x] `Game` (clock, equity history, game over)
- [x] `cli/parser.py`, `cli/charts.py`, `cli/views.py`, `cli/app.py`
- [x] Commands: help, market, quote, chart, etf, buy, sell, portfolio, history, next, report, quit
- [x] `diversification_lab.compare` + `lab` command + verdict rules
- [x] (stretch) `lab mc` Monte Carlo
- [x] All Phase-1 tests in `05-testing.md` pass; manual script rows 1–8, 10, 11 pass
- [ ] README "Status" updated → **submit v1, show tutor, ask for their checklist**

### Phase 2 — Market Events + Explainer (E-02)
- [x] `data/events.json` (~12 templates) + `MarketEvent` + separate event RNG
- [x] Shocks applied in price generation; NEWS lines after `next`
- [x] `explainer.etf_move_breakdown` + `explain_event` + `news [DAY]`
- [x] "Your position changed by $X" line when holding affected stocks
- [x] Tests pass

### Phase 3 — Trade Coach (E-03)
- [x] `Tip` class, `TRADE_RULES`/`SESSION_RULES` lists, seven rules (incl. CHASE), max 2 tips after a trade
- [x] `coach` command + tips in end report (and as toasts in the web app)
- [x] One positive + one negative test per rule

### Phase 4 — What-if Replay (E-04)
- [x] `strategies.py` (11 strategies incl. Hold MKT100, Chase the winner, Follow the Robo-analyst; one signature)
- [x] `whatif.replay` + `compare_strategies`; replay-fidelity test passes
- [x] `whatif` table + chart + lesson line; offered automatically at game end

### Phase 5 — Stand-out layer (D-17, D-19, D-20)
**5a Streamlit web app (D-25; replaces the Textual dashboard) — built, then replaced by the `--web` app and deleted (D-37, D-45)**
- [x] `web.py` + `tradesim/web/app.py`: metrics, Next buttons, Buy/Sell bar, tabs (Market, Chart, Portfolio, News, Lab, Headlines, Command)
- [x] Buttons send command lines through `cli.app.run_command`; `views.*` drawn as HTML (`to_html`)
- [x] Every command works from the Command tab; errors show red, no crash
- [x] `.streamlit/config.toml`: no usage stats, localhost only
- [x] `tests/test_web.py` (AppTest)

**5c Agent mode (X-06, D-26)**
- [x] `cli/app.py` split into `execute` (raises) + `run_command` (catches)
- [x] `cli/agent.py`: saved game = seed + days + commands (now in SQLite, D-46), replay on load, plain text, exit 0/1
- [x] `main.py`: optional command words + `--game NAME` + `--db`
- [x] `tests/test_agent.py`; README section with a prompt for agents

**5b Headline Lab (E-05)**
- [x] Settle Q-06 → Laya local (D-21). Q-07 (instructor OK with an AI model) still open
- [x] `events.json`: word lists + ~4 tricky headlines (§3.7)
- [x] `education/headline_lab.py`: `Verdict`, `keyword_verdict`, `truth`, `score` (pure)
- [x] `ai/sentiment.py`: cache → Laya (local, lazy) → `None` on any failure
- [x] `headlines` / `hl "TEXT"` command + Laya label on the news line
- [x] Headlines tab (in the 5a web app)
- [x] `tools/warm_cache.py`; commit a warmed `data/reference.db` (`sentiment` table)
- [x] Tests: fake classifier, offline fallback, corrupt cache, tricky-headline keyword misses

### Phase 6 — Extensions (pick in this order; skip freely)
- [x] X-02 Save/load (D-46: `saves/player.db`, agent mode + web app) and X-07 `games` / `/api/games`
- [x] X-05 Achievements (16 badges)
- [x] X-01 Challenge scenarios (7, fixed seeds with story tests)
- [ ] X-04 TECH2 + fund-of-funds recursive pricing (evidences recursion, LO7)
- [ ] X-03 Short selling

### Phase 8 — "Complete app" expansion (D-29…D-36, 2026-10-18)
- [x] Real-life trends: market moods (Markov chain), GARCH volatility memory, beta, company stories, fear gauge; calibrated (docs/03 §3.2)
- [x] 12 stocks / 5 sectors, 4 ETFs, 46 balanced headlines (Laya cache re-warmed)
- [x] Robo-analyst (E-06): pure-Python logistic regression ×2, `tools/train_robo.py`, `robo`, train-your-own in the web app
- [x] Academy (E-07): glossary + quiz; `story`, `sectors`, `new`, `challenge`, `badges`
- [x] Web redesign: 9 pages, dark theme, Vega-Lite charts, toasts, game-over report, shareable `?seed=` links
- [x] REPL: logo banner, status bar, day recap, coloured sectors, grades in the report
- [x] Verified with headless-Chrome screenshots of every page and `tools/verify.py cli` (35 steps)

### Phase 9 — Real web app, live market, leverage (D-37…D-43, 2026-10-18)
- [x] 100 stocks / 10 sectors, 14 ETFs (MKT12 → MKT100, sector ETFs), 84 balanced headlines (Laya cache re-warmed), news 25%/day
- [x] Intraday sessions: 78 ticks/day by Brownian bridge (market bridge × beta, opening gap, news jump), U-shaped volume, order book; `Game` (day, tick) clock, `tick N`
- [x] 120 days of pre-game history (warm-up market, rescaled); daily OHLCV bars; trading dates on charts
- [x] Margin account: `leverage N` (1–5×), credit, maintenance, margin calls every tick, liquidation, nightly interest
- [x] E-08 Leverage Lab (`levlab`), 2 coach rules, 4 badges, 2 challenges (Margin Madness, Borrowed Bull), 9 glossary terms, 5 quiz questions
- [x] Web app: stdlib server + JSON API + hand-written HTML/CSS/JS — price board, candlestick charts, order ticket, live clock (1×–15×), closing bell, skip days, 10 pages, toasts
- [x] Robo retrained, challenge seeds checked, demo seed re-picked (39), calibration re-checked
- [x] Tests: `test_intraday.py`, `test_margin.py`, `test_leverage.py`, `test_webapp.py` (real HTTP server) — 314 passing
- [x] Verified: `tools/verify.py cli` (45 steps) and Chrome on every page, a margin-call game to the final report
- [x] Q-08: the old Streamlit app (`tradesim/web/`, `web.py`, `.streamlit/`, `tests/test_web.py`, the `streamlit` dependency) was deleted (D-45)

### Phase 7 — Polish & submit
- [x] `tools/find_demo_seed.py`: early tech shock (NVDA ≤ −6%, MIX6 > −3%), a later bear/crash,
      ≥ 8 headlines, NVDA drawdown > 18% → **seed 39** (was 180 before D-38)
- [ ] Docstring + type-hint audit; remove dead code; no function > ~30 lines without reason
- [ ] Full manual test script (05 §5.5) on a clean venv
- [x] README: screenshot(s), how to run, feature list (add "what I learned" yourself)
- [x] `docs/debug-log.md` has ≥ 5 real bugs found/fixed (13 so far — evidence for LO10, see §6.4)
- [ ] Padlet post: title, 3-line pitch, 1 screenshot/GIF, "run with `--seed N`"
- [ ] Rehearse demo to ≤ 3:00 twice

## 6.3 Three-minute demo script (updated for D-37…D-43)

Start the web app on the demo market: `uv run main.py --web --seed 39` (opens
`http://127.0.0.1:8000`). Seed 39: sideways start, a **bear market days 6–22**, and on **day 14
at 13:10 "Chip export curbs hit tech stocks"** → NVDA −10.3%, MIX6 only −2.9%.
Browser zoom 100–110%. Backup: a screen recording of the same run, plus the REPL
(`uv run main.py --seed 39`).

| Time | Say | Do |
|---|---|---|
| 0:00–0:20 | "This is a real-time market: 100 companies, 10 sectors. Every second is five minutes of trading. Green is above yesterday's close, red below." | Welcome → **Open the market**; the board flashes |
| 0:20–0:45 | "Double-click to trade. I'll put half my money in NVIDIA…" | Double-click NVDA → 50% → Buy; toast + coach tip |
| 0:45–1:10 | "Candlesticks with six months of history — this is what traders look at." | Trade page: 1D live candles, then All + MA 20/50, hover the tooltip |
| 1:10–1:35 | "Now the dangerous part: borrowing. At 3× leverage, a 20% fall triggers a margin call — the broker sells for you." | Leverage page: 3× → calculator −10% at 3× = −30%; Leverage Lab chart with the margin-call dot |
| 1:35–2:00 | "Let's skip ahead…" (Skip 5 days ×2, then play day 14 at 15×) "Breaking news at 13:10 — NVIDIA −10%. The ETF? Under 3%." | Skip days, 15× → breaking-news toast; News page: Laya vs keywords vs truth |
| 2:00–2:25 | "Same stock, 200 different markets: one stock loses 20%+ far more often than the ETF." | Labs → Monte Carlo (or Diversification) |
| 2:25–2:45 | "Skip to the end: the report, the hidden story, and what eleven other strategies would have done." | Skip to the end → report → What-if |
| 2:45–3:00 | "Standard-library Python server, hand-drawn charts, a local AI, a hand-written ML model, 314 tests. Lesson: diversify, and be very careful with borrowed money." | `uv run pytest -q` summary |

Optional 10 s beat: a script playing through agent mode (`uv run main.py tick 6`, `leverage 2`, `buy …`).

## 6.4 Scoring checklist (map features → what markers look for)

The tutor marks against their own checklist — **ask for it at the v1 check-in** and add
it here. Until then, cover every learning outcome visibly:

| Learning outcome | Where it shows in this project |
|---|---|
| LO1 Readable code / style | Docstrings, type hints, named constants in `config.py`, small functions, consistent naming |
| LO2–4 Build from a spec / extend | These docs; requirement IDs (C-xx, E-xx) referenced in code comments and commit messages |
| LO5–6 Explain execution | `__str__`/`__repr__` on every class; demo narration; worked examples in docs |
| LO7 Recursion | X-04 fund-of-funds pricing + ETF cycle detection (DFS) |
| LO8 Array/list idioms | Price histories, list comprehensions, 2D character grid in `charts.py`, sliding windows in coach rules |
| LO9 Testing | pytest suite, worked-example tests, invariant test, replay-fidelity test, coverage report |
| LO10 Debugging | Custom exception tree, friendly errors, `docs/debug-log.md` (symptom → traceback → cause → fix → test added) |
| LO11 Docs & stdlib | `random`, `statistics`, `json`, `argparse`, `pathlib`, `difflib`, `math`, `urllib`, `os`; two well-used libraries (`rich`, `textual`); one external API (Jev) behind a cache |
| Week 7 OOP | Classes with constructors, instance vs **class variable** (e.g. `Trade._next_id` counter for trade IDs), `@staticmethod` (`Market.from_prices`), one class per file, driver file `main.py` |
| Originality (instructor condition) | Diversification Lab + Explainer + Coach + What-if + Headline Lab — framed as "teaches *why*", not just "lets you trade" |
| Demo appeal (class vote) | Dramatic seed, a live broker-style price board and candlestick charts (own web app), leverage and margin calls, an AI agent playing via agent mode, AI headline reading, a clear one-sentence lesson |

`docs/debug-log.md` entry template:

```
## Bug 3 — Portfolio equity off by the fee after selling all shares
Symptom:  equity 1.00 lower than expected in test_invariant
Traceback / failing assert: assert 10201.0 == approx(10202.0)
Cause:    fee subtracted twice when position closed (in sell() and in _remove_position())
Fix:      subtract fee only in sell(); commit abc123
Test:     test_sell_all_charges_fee_once
```
