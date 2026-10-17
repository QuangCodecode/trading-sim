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
| Week 11–12 | 5 | Textual dashboard + Headline Lab (stand-out layer, D-17/D-19) | v3 |
| Week 12 | 7 (+6 if ahead) | Polish, demo seed, Padlet, final tests | **Final** |

> **Status 2026-10-18:** Phase 1 done (core + Diversification Lab + `lab mc`, 110 tests).
> v1 scope agreed with Quang: Phases 1, 2 and 5b (Headline Lab on Laya, D-21) in the
> rich REPL; Coach, What-if and the Textual dashboard follow after v1. If time runs
> short, cut in this order: Phase 6 → What-if (4) → Textual (5a). Keep Headline Lab (5b),
> since it works in the plain REPL too.
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
- [ ] `data/events.json` (~12 templates) + `MarketEvent` + separate event RNG
- [ ] Shocks applied in price generation; NEWS lines after `next`
- [ ] `explainer.etf_move_breakdown` + `explain_event` + `news [DAY]`
- [ ] "Your position changed by $X" line when holding affected stocks
- [ ] Tests pass

### Phase 3 — Trade Coach (E-03)
- [ ] `Tip` class, `RULES` list, six rules, max 2 tips after a trade
- [ ] `coach` command + tips in end report
- [ ] One positive + one negative test per rule

### Phase 4 — What-if Replay (E-04)
- [ ] `strategies.py` (8 strategies, one signature, `STRATEGIES` dict)
- [ ] `whatif.replay` + `compare_strategies`; replay-fidelity test passes
- [ ] `whatif` table + chart + lesson line; offered automatically at game end

### Phase 5 — Stand-out layer (D-17, D-19, D-20)
**5a Textual dashboard**
- [ ] `cli/tui.py`: `App` with tabs, market table, chart, news line, command `Input`, Next buttons
- [ ] Reuses `parser`/`views`/`charts` unchanged; `--plain` still launches `app.py`
- [ ] Every Phase 1–4 command works from the command box; errors show red, no crash

**5b Headline Lab (E-05)**
- [ ] Settle Q-06 (Jev route + schema) and Q-07 (instructor OK with an API) first
- [ ] `events.json`: word lists + ~4 tricky headlines (§3.7)
- [ ] `education/headline_lab.py`: `Verdict`, `keyword_verdict`, `truth`, `score` (pure)
- [ ] `ai/sentiment.py`: cache → Jev (`urllib`, `JEV_TIMEOUT_S`) → `None` on any failure
- [ ] `headlines` / `hl "TEXT"` command + Headlines tab + Jev label on the news line
- [ ] `tools/warm_cache.py`; commit a warmed `data/sentiment_cache.json`
- [ ] Tests: fake classifier, offline fallback, corrupt cache, tricky-headline keyword misses

### Phase 6 — Extensions (pick in this order; skip freely)
- [ ] X-02 Save/load (small, useful for the demo — start the demo from a save)
- [ ] X-05 Achievements (cheap, demo-friendly)
- [ ] X-01 Challenge scenarios
- [ ] X-04 TECH2 + fund-of-funds recursive pricing (evidences recursion, LO7)
- [ ] X-03 Short selling

### Phase 7 — Polish & submit
- [ ] `tools/find_demo_seed.py`: loop over seeds, pick one where a tech-sector shock of
      ≤ −6% happens between days 5–12 and NVDA's max drawdown > 15% → dramatic, reliable demo
- [ ] Docstring + type-hint audit; remove dead code; no function > ~30 lines without reason
- [ ] Full manual test script (05 §5.5) on a clean venv
- [ ] README: screenshot(s), how to run, feature list, what I learned
- [ ] `docs/debug-log.md` has ≥ 5 real bugs found/fixed (evidence for LO10 — see §6.4)
- [ ] Padlet post: title, 3-line pitch, 1 screenshot/GIF, "run with `--seed N`"
- [ ] Rehearse demo to ≤ 3:00 twice

## 6.3 Three-minute demo script

Run `python3 main.py --seed <DEMO_SEED>` (or `load demo`). Terminal font large, dark theme.

| Time | Say | Type |
|---|---|---|
| 0:00–0:15 | "You have $10k. Put it all in one hot stock, or spread it out? Most people guess wrong. Let's play." | *(banner showing)* |
| 0:15–0:45 | "Six stocks, three sectors, and MIX6 — an ETF whose price is a weighted average of all six." | `market` · `etf` |
| 0:45–1:10 | "I'll go big on NVIDIA… and put a little in the ETF." | `buy nvda 60` → coach warns about concentration (Phase 3) · `buy mix6 20` · `portfolio` |
| 1:10–1:40 | "Let's skip ahead." News hits. "Tech dropped 8%, but the ETF only 2.7% — here's exactly why." | `next 7` · `news` |
| 1:40–2:05 | "Can AI read the news? A word counter says 'not as bad as feared' is bad news; the Jev AI gets it right." | `hl` *(Headlines tab)* |
| 2:05–2:35 | "The Diversification Lab compares both on the same days." | `lab` |
| 2:35–2:50 | "What if I'd made different choices? Same market, eight strategies." | `whatif` |
| 2:50–3:00 | "Pure Python, one AI call, <N> automated tests, works offline. What I learned: diversification is about odds, not luck." | *(show `pytest -q` summary screenshot)* |

Backup: a screen recording of the same run in case of a live failure.

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
| Demo appeal (class vote) | Dramatic seed, Textual dashboard, charts, AI headline reading, a clear one-sentence lesson |

`docs/debug-log.md` entry template:

```
## Bug 3 — Portfolio equity off by the fee after selling all shares
Symptom:  equity 1.00 lower than expected in test_invariant
Traceback / failing assert: assert 10201.0 == approx(10202.0)
Cause:    fee subtracted twice when position closed (in sell() and in _remove_position())
Fix:      subtract fee only in sell(); commit abc123
Test:     test_sell_all_charges_fee_once
```
