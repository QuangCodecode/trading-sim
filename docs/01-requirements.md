# 01 — Requirements

> **D-50:** the terminal game, agent mode, `rich` and Laya were removed; rows below that mention them are marked or updated.

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
| Meaningful original contribution | **Diversification Lab** (headline, Phase 1) + Events/Explainer, Coach, What-if Replay (Phases 2–4), Headline Lab, Robo-analyst (tiny ML), Academy |

## 1.3 Core features (Phase 1 — REQUIRED)

| ID | Feature | Acceptance criteria |
|---|---|---|
| C-01 | **Virtual cash** | Game starts with `STARTING_CASH` (default $10,000). Cash never goes negative in a cash account (leverage 1×, the default); a margin account (D-41) may borrow. |
| C-02 | **Simulated stocks** | **100 stocks, 10 sectors** since D-38 (12 / 5 since D-30, 6 / 3 at first; see `03-finance-model.md` §3.1). Daily closes come from a seeded model with real-life trends (market moods, volatility memory, beta); inside each day prices tick every 5 minutes (§3.12, D-39). Price never drops below `MIN_PRICE`. |
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
| E-05 | **Headline Lab** | 5 | "Reading news is harder than counting good and bad words." Each event headline is labelled by a keyword counter **and** by a stored "sentence reader" label (an AI model's good/bad answer with its confidence, worked out once and kept as data, D-50). Both are scored against the real price move. The player can also type a headline and see what the word counter says. Display-only: never changes prices (D-20). |
| E-06 | **Robo-analyst** *(tiny ML)* | 8 | "Machine learning can spot a stormy market, but next week's price is close to a coin flip." Two pure-Python logistic regressions read the charts: a market-mood detector and a 5-day price forecaster, each with its reasons and an honest track record. Players can train their own and watch the loss fall (D-31). |
| E-07 | **Academy** | 8 | "Know the words, test yourself." 33-term glossary (`learn TERM`) and a 21-question quiz (`quiz`). |
| E-08 | **Leverage Lab + margin account** | 9 | "Borrowed money multiplies losses too, costs interest, and a margin call sells at the bottom." `leverage N` (1–5×), margin calls checked every tick, nightly interest; `levlab` replays the last 60 days at 1×/2×/3×/5× and with a 2× daily fund; a calculator and risk table on the web Leverage page; 2 challenges, 4 badges, 2 coach rules (D-41, D-42). |
| E-09 | **Live market (web app)** | 9 | "Markets move all day; news breaks mid-session; you can't trade at yesterday's price." A broker-style price board (100 stocks, bid/ask depth, flashing prices), 5-minute ticks at 1×–15× speed, skip to the close or skip days, candlestick charts with 6 months of history (D-37, D-39, D-40). |

## 1.5 Optional extensions (Phase 6 — only after Phases 1–5 are done or if time allows)

| ID | Extension | Notes |
|---|---|---|
| X-01 | Challenge scenarios ✅ (7 built, D-33) | Fixed seed + forced events + goal (e.g. "Tech Crash: finish ≥ $9,500"). Stored in the `challenges` table of `data/reference.db` (D-46). |
| X-02 | Save / load game ✅ (D-46) | `saves/player.db` stores the seed and the commands that changed the game; the market is regenerated from the seed and the commands replayed (no prices stored). Agent mode and the web app save and resume. |
| X-03 | Short selling | Negative quantity; collateral rule in §3.9. One P&L formula works for long and short. |
| X-05 | Achievements ✅ (16 badges, D-33) | Wall Street Survivor-style badges checked by small rule functions (like the Coach): "Diversified" (≥ 3 sectors, no stock > 30%), "Diamond hands" (held MIX6 through a ≥ 5% dip), "Fee-aware" (fees < $5 at game end). Shown in the end report. |
| X-06 | ~~Agent mode~~ | **Removed by D-50** (with the terminal front ends). It ran one command on a saved game and printed plain text. |
| X-07 | Saved games and progress ✅ (D-46, D-47) | The `games` command (and `/api/games`) lists every saved game: result vs the market, challenges passed, badges won across games. |
| X-04 | Second ETF + fund-of-funds | A sector ETF (`TECH2`) and optionally an ETF that holds another ETF, priced **recursively** — a natural, non-contrived use of recursion (LO7). |

## 1.6 Explicit non-goals (do NOT build)

Real market data or real news feeds · Pygame/Tkinter GUI (the local web app, D-25/D-37, is
allowed; no hosting, accounts or multiplayer) · internet APIs · ~~margin, leverage, margin
calls~~ (in scope since D-41) · options, futures · order types other than market orders at the
current price · ~~intraday prices~~ (in scope since D-39) ·
multiplayer · user accounts/passwords · dividends, splits, taxes · currency conversion.

## 1.7 Non-functional requirements

| ID | Requirement |
|---|---|
| N-01 | Runs with `python3 main.py` on Python 3.11+ on macOS/Linux/Windows lab machines with **no packages installed** (D-50): the server is the standard library and the page is plain HTML/CSS/JS in any web browser. |
| N-02 | Never crashes on user input; every invalid command gives a one-line reason + hint. |
| N-03 | Deterministic with `--seed`; the same seed and same commands give the same output. |
| N-04 | Engine logic covered by pytest; target ≥ 85% line coverage of `tradesim/engine` and `tradesim/education`. |
| N-05 | Readable: docstrings + type hints on public functions, constants in `config.py`, no function > ~30 lines without reason. |
| N-06 | A full 60-day game is playable in under 3 minutes for the demo (`next 10` etc.). |
| N-07 | Startup banner states prices are simulated and it is not financial advice. |
| N-08 | Fully playable offline with no API key and no model: the Headline Lab's readings are stored data (D-50). |
