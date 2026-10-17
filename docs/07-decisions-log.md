# 07 — Decisions log and open questions

Decisions below are **settled** — follow them unless Quang changes them. When anything
changes, add a new row (don't delete old ones; mark them "superseded by D-xx").

## Decisions

| ID | Date | Decision | Why | Source |
|---|---|---|---|---|
| D-01 | 2026-09-23 | **Terminal (CLI) only** — no GUI/web/Pygame *(superseded by D-17)* | Matches course tooling; keeps scope manageable | Quang |
| D-02 | 2026-09-23 | Libraries: **`rich`** (runtime) + **`pytest`** (dev); everything else stdlib *(superseded by D-18)* | Better demo for one dependency; nicer tests | Quang |
| D-03 | 2026-09-23 | ETF price = BASE × Σ wᵢ · (Pᵢ,t / Pᵢ,0) (weighted average of price relatives) | Raw-price average lets expensive stocks dominate; weights keep their meaning. Literal Σ wᵢPᵢ is a one-line swap if the tutor wants it | Quang, pending tutor OK (Q-02) |
| D-04 | 2026-09-23 | **Real tickers, simulated prices** (AAPL, NVDA, XOM, CVX, KO, WMT); ETF tickers fictional (MIX6, TECH2) | Familiar names make the demo relatable; disclaimer on startup | Quang |
| D-05 | 2026-09-23 | Headline original feature = **Diversification Lab** (Phase 1). Events+Explainer, Coach, What-if follow as Phases 2–4 | Instructor asked for one small original feature + manageable scope; the others are upgrades | Quang |
| D-06 | 2026-09-23 | Optional extensions: challenge scenarios, save/load, short selling (+ fund-of-funds for recursion) | Fun, but only after core | Quang |
| D-07 | 2026-09-23 | Margin, leverage, margin calls, options, futures from the earlier design notes are **out of scope** | Instructor feedback on scope | Instructor |
| D-08 | 2026-09-23 | Whole market path **pre-generated** from the seed; player sees only up to today | Enables replay, lab windows, save/load by seed; trades don't move prices | Quang |
| D-09 | 2026-09-23 | Separate RNG for events | Turning events on doesn't change the base random walk | Quang |
| D-10 | 2026-09-23 | Whole shares only; market orders at the day's price; flat **$1** fee per trade; average-cost accounting; fees tracked separately | Simplest model that still teaches fees | Quang |
| D-11 | 2026-09-23 | Starting cash **$10,000**, game length **60** days, prices rounded to cents at generation | Round numbers; demo fits in 3 min | Quang (change in `config.py`) |
| D-12 | 2026-09-23 | Command-prompt UI (`buy AAPL 10`) with aliases + `help`, not numbered menus | Faster to demo; `difflib` suggestions for typos | Quang |
| D-13 | 2026-09-23 | Plain classes with `__init__/__str__/__repr__`, not `@dataclass` | Mirrors Week 7 OOP content Quang must explain | Quang |
| D-14 | 2026-09-23 | Game over at the final day: `next`/trading disabled, read-only commands + `whatif` still work | Clear end state for report and replay | Quang |
| D-15 | 2026-09-23 | Engine/education layers never print or read input | Testability | Quang |
| D-17 | 2026-10-17 | Phase 5 adds a **Textual** dashboard (`cli/tui.py`) as the main front end. It's still a terminal app, but with tabs, buttons and mouse. The Phase 1 `rich` REPL stays as the fallback (`--plain`). `parser.py`, `views.py` and `charts.py` are reused unchanged (Textual displays rich renderables) | Stands out in the class vote; Textual is by the rich team, so only `cli/` changes | Quang |
| D-18 | 2026-10-17 | Libraries: `rich` + `textual` (runtime), `pytest` (dev). Jev is called with stdlib `urllib` + `json`, with no SDK. `textual-plotext` only if time allows | Smallest dependency set that delivers D-17 and D-19 | Quang |
| D-19 | 2026-10-17 | New original feature **E-05 Headline Lab**: TypeSafe **Jev** labels event headlines with sentiment and a probability. An offline keyword counter labels the same headlines, and both are scored against the real move | Real AI feature that teaches *why* judgement beats word counting | Quang |
| D-20 | 2026-10-17 | **AI never moves prices.** Event shocks stay seed-driven (D-09). Jev output is display-only, cached in `data/sentiment_cache.json`, and falls back to the keyword counter when there's no key or network. Tests never touch the network | Keeps the same-seed ⇒ same-market rule, offline tests, and a Wi-Fi-proof demo | Quang |

| D-21 | 2026-10-18 | Headline Lab AI = **Laya** (`convaiinnovations/laya`, Apache-2.0, open weights), run **locally on CPU** instead of paid Jev. Weights (~808 MB) downloaded to `models/laya/` (git-ignored) by `tools/download_model.py`; `laya` (pulls in torch + transformers) goes in `requirements.txt`. Supersedes the Jev parts of D-18/D-19 and settles Q-06. `perplexity-ai/pplx-decider-flash-v1.2` was considered but needs a CUDA GPU (Quang's M4 Mac has none) | Open source, free, offline after download, same Choice question shape as Jev, 0.1 s per headline on CPU | Quang |
| D-22 | 2026-10-18 | Ask Laya a **two-label** Choice (positive / negative) and always show its pick with its probability; below `NEUTRAL_BAND` (60%) it is shown dimmed as "unsure" but still scored. Replaces the 3-label + neutral design in docs/04 §4.3 | Every event is truly positive or negative (§3.7). With 3 labels Laya's probabilities were 0.50–0.83 and 2 of 3 tricky headlines would have been hidden as "neutral"; with 2 labels it scored 6/6 at 0.61–0.99 | Quang |
| D-23 | 2026-10-18 | Load Laya **lazily** on first AI use (~10 s once, with a spinner); answers cached in `data/sentiment_cache.json` | Game starts instantly; repeat headlines and a pre-warmed demo need no model load | Quang |
| D-24 | 2026-10-18 | v1 = Phases 1 + 2 + 5b in the rich REPL. Phase 3 (Coach), 4 (What-if) and 5a (Textual) come after v1 | Get the AI stand-out feature demoable first | Quang |

## Open questions (ask the tutor / decide later)

| ID | Question | Default until answered |
|---|---|---|
| Q-01 | What's on the tutor's marking checklist for the final project? | Cover all LOs visibly (06 §6.4) |
| Q-02 | Is the normalised weighted-average ETF formula (D-03) acceptable, or must it be literally Σ wᵢPᵢ? | Use D-03 and explain it in the demo |
| Q-03 | Are `pip install` dependencies (`rich`, `textual`) OK for marking, or must it run on bare Python? | Use them; `--plain` REPL needs only `rich`, and `views.py` is the only file to rewrite with `print` |
| Q-04 | Submission format (Ed upload? zip? GitHub link?) and Padlet requirements | Keep repo clean + zip-ready |
| Q-05 | Any issue using real company names/tickers in a student project? | Keep, with "simulated prices" disclaimer; rename is a data-file change |
| Q-06 | ~~Which Jev route~~ **Settled by D-21 (Laya, local).** Which Jev route and exact request/response schema? Direct API (`POST api.typesafe.ai/v1/systemone`, waitlisted) vs OpenRouter (`typesafe/jev-1.13`, beta). **No free tier**, but a full game costs < 1¢ | Decide at the start of Phase 5 and verify against the provider docs before coding `ai/sentiment.py`. Key read from env var `JEV_API_KEY`, never committed |
| Q-07 | Does the instructor accept an internet API in the project, given the original non-goal (§1.6)? | Ask at the v1 check-in. Headline Lab works fully offline with the keyword counter, so a "no" only hides the Jev column |
