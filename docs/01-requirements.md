# 01 — Requirements

## 1.1 Course context

| Item | Detail |
|---|---|
| Unit | COMP9001 Introduction to Programming, University of Sydney, S2 2026 |
| Assessment | Final Project — 15%, individual, student-proposed idea checked by tutor against a checklist |
| Due | Week 12 (multiple submissions allowed across the semester) |
| Demo | ~3 min live demo in the Week 13 lab; classmates vote; winner gets a certificate; Padlet showcase |
| Banned topics | Gambling, hacking, virtual boyfriend/girlfriend apps (this is paper-trading education, not gambling — keep the framing educational: no betting, no "jackpot" language) |
| Learning outcomes to evidence | Compose programs from a spec (LO2–4), test against a spec (LO9), debug (LO10), readable style (LO1), explain behaviour (LO5–6), use docs & standard library (LO5, LO11), recursion & array idioms (LO7–8) |

## 1.2 Instructor feedback (verbatim — this is the approval condition)

> Dear Cillian,
> Your trading simulator is a good and feasible idea for the final project.
> However, I recommend focusing on the core features first: virtual cash, a small number of
> simulated stocks, buying and selling, portfolio tracking, profit/loss calculation, and at
> least one ETF whose price is calculated using a weighted average of selected stocks. Other
> features should be treated as optional extensions rather than requirements.
> Also, since trading simulators already exist, consider adding one small original
> educational feature, such as explaining ETF diversification, comparing stock and ETF
> performance, or showing the effect of different investment decisions.
> Overall, your idea is approved in principle, provided that you clearly define the core
> features, keep the scope manageable, and include a meaningful original contribution.
> Best, Islam

**Approval conditions → how this project meets them**

| Condition | Met by |
|---|---|
| Clearly defined core features | §1.3 (C-01 … C-09), each with acceptance criteria |
| Manageable scope | Phased roadmap; Phase 1 = core + one original feature, shippable on its own |
| Meaningful original contribution | **Diversification Lab** (headline, Phase 1) + Events/Explainer, Coach, What-if Replay (Phases 2–4) |

## 1.3 Core features (Phase 1 — REQUIRED)

| ID | Feature | Acceptance criteria |
|---|---|---|
| C-01 | **Virtual cash** | Game starts with `STARTING_CASH` (default $10,000). Cash can never go negative. |
| C-02 | **Simulated stocks** | 6 stocks, 3 sectors (see `03-finance-model.md` §3.1). Prices update once per simulated trading day using a seeded random model. Price never drops below `MIN_PRICE`. |
| C-03 | **Time control** | `next` advances 1 day, `next N` advances N days (stops at game end). Game length `GAME_DAYS` (default 60). |
| C-04 | **ETF (weighted average)** | `MIX6` ETF priced every day from the six stocks using fixed weights that sum to 1 (formula in §3.3). Tradable exactly like a stock. Its composition is viewable. |
| C-05 | **Buy** | `buy SYMBOL QTY` buys whole shares at today's price plus a flat fee. Rejected with a clear message if: unknown symbol, qty ≤ 0 or not an integer, insufficient cash (incl. fee), game over. |
| C-06 | **Sell** | `sell SYMBOL QTY` / `sell SYMBOL all`. Rejected if not held or qty > held. |
| C-07 | **Portfolio tracking** | Shows each holding: qty, average cost, current price, market value, unrealised P&L ($, %), weight in portfolio; plus cash and total equity. |
| C-08 | **Profit / loss** | Realised P&L, unrealised P&L, total fees, total P&L and total return % vs starting cash. Invariant: `equity − starting_cash == realised + unrealised − fees` (to the cent). |
| C-09 | **Trade history & end report** | Every trade logged (day, side, symbol, qty, price, fee). End-of-game report summarises P&L and best/worst holding. |

## 1.4 Original educational features

| ID | Feature | Phase | Learning goal for the player |
|---|---|---|---|
| E-01 | **Diversification Lab** *(headline)* | 1 | "Putting everything in one stock is riskier than an ETF, even when the average return is similar." Compares one stock vs MIX6 over the same days: total return, volatility, worst day, max drawdown, ASCII chart, verdict. Stretch: Monte Carlo over many seeds ("in 200 simulated markets, NVDA lost more than 20% in about 1 of every 5; MIX6 almost never"). |
| E-02 | **Market Events + Explainer** | 2 | "News that crushes one sector only dents a diversified fund." Random events shock a stock/sector/market; `news` shows the headline and a breakdown of each stock's contribution to the ETF's move. |
| E-03 | **Trade Coach** | 3 | "Good habits: don't concentrate, don't panic-sell, watch fees." Rule-based tips after trades and in the end report. |
| E-04 | **What-if Replay** | 4 | "Your decisions matter — compare them." Replays the identical market with preset strategies and the player's own trades; shows a ranked table and equity curves. |
| E-05 | **Headline Lab** *(AI)* | 5 | "Reading news is harder than counting good and bad words." Each event headline is labelled by an offline keyword counter **and** by the Jev AI (sentiment plus probability). Both are scored against the real price move. The player can also type a headline and see both verdicts. Display-only: AI never changes prices (D-20). |

## 1.5 Optional extensions (Phase 6 — only after Phases 1–5 are done or if time allows)

| ID | Extension | Notes |
|---|---|---|
| X-01 | Challenge scenarios | Fixed seed + forced events + goal (e.g. "Tech Crash: finish ≥ $9,500"). Stored in `data/scenarios.json`. |
| X-02 | Save / load game | JSON file stores seed, day, portfolio, trade log. Market is regenerated from the seed (no need to store prices). |
| X-03 | Short selling | Negative quantity; collateral rule in §3.9. One P&L formula works for long and short. |
| X-05 | Achievements | Wall Street Survivor-style badges checked by small rule functions (like the Coach): "Diversified" (≥ 3 sectors, no stock > 30%), "Diamond hands" (held MIX6 through a ≥ 5% dip), "Fee-aware" (fees < $5 at game end). Shown in the end report. |
| X-04 | Second ETF + fund-of-funds | A sector ETF (`TECH2`) and optionally an ETF that holds another ETF, priced **recursively** — a natural, non-contrived use of recursion (LO7). |

## 1.6 Explicit non-goals (do NOT build)

Real market data or real news feeds · web/Pygame/Tkinter GUI (the Textual terminal
dashboard, D-17, is allowed) · internet APIs other than the optional Jev call in E-05
(D-19) · margin, leverage, margin calls ·
options, futures · order types other than market orders at today's price · intraday prices ·
multiplayer · user accounts/passwords · dividends, splits, taxes · currency conversion.

## 1.7 Non-functional requirements

| ID | Requirement |
|---|---|
| N-01 | Runs with `python3 main.py` on Python 3.10+ on macOS/Linux/Windows lab machines. Dependencies are `rich` and `textual` only (D-18); `--plain` needs only `rich`. |
| N-02 | Never crashes on user input; every invalid command gives a one-line reason + hint. |
| N-03 | Deterministic with `--seed`; the same seed and same commands give the same output. |
| N-04 | Engine logic covered by pytest; target ≥ 85% line coverage of `tradesim/engine` and `tradesim/education`. |
| N-05 | Readable: docstrings + type hints on public functions, constants in `config.py`, no function > ~30 lines without reason. |
| N-06 | A full 60-day game is playable in under 3 minutes for the demo (`next 10` etc.). |
| N-07 | Startup banner states prices are simulated and it is not financial advice. |
| N-08 | Fully playable offline with no API key. Missing key, network error or timeout → keyword counter only, plus one dim "AI offline" note. Never a crash, and never a wait longer than `JEV_TIMEOUT_S`. |
