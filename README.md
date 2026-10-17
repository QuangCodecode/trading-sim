# TradeSim — a terminal trading simulator that teaches diversification

> COMP9001 Introduction to Programming · Final Project · Semester 2 2026 · Quang (Cillian) Nguyen
>
> **All prices are simulated.** Tickers are borrowed from real companies to feel familiar,
> but no real market data is used. This is an educational game, not financial advice.

## The idea in one line

Start with **$10,000 of virtual cash**, trade **6 simulated stocks and an ETF** day by day,
and find out — with your own numbers — **why a diversified ETF usually survives shocks that
wreck a single stock.**

```
 Day 12 / 60                                   Cash $4,212.50   Equity $10,418.20 (+4.18%)
 ┌────────┬──────────────┬─────────┬─────────┐
 │ Symbol │ Name         │   Price │  Today  │
 ├────────┼──────────────┼─────────┼─────────┤
 │ AAPL   │ Apple        │  186.40 │  +1.2%  │
 │ NVDA   │ NVIDIA       │  110.05 │  -8.3%  │   NEWS: Chip export curbs hit tech stocks
 │ MIX6   │ Mix-6 ETF    │   99.12 │  -2.1%  │   → ETF fell far less: tech is only 35% of it
 └────────┴──────────────┴─────────┴─────────┘
 > buy MIX6 20
```
*(illustrative mock-up — see `docs/04-features-and-cli.md` for the real screens)*

## Features

**Core (required by the instructor)**
- Virtual cash account, 6 simulated stocks across 3 sectors, day-by-day price simulation
- Buy and sell with validation (cash, holdings, quantity)
- Portfolio tracking: holdings, average cost, market value, equity
- Profit/loss: realised, unrealised, fees, total return %
- **MIX6 ETF** priced each day as a **weighted average** of the six stocks

**Original educational contribution**
- **Diversification Lab** *(headline)* — single stock vs ETF on the same market: return,
  volatility, worst day, max drawdown, side-by-side ASCII chart, plain-English verdict
- **Market Events + Explainer** — news shocks hit a stock/sector; the app shows exactly
  how much of the shock reached the ETF and why
- **Trade Coach** — rule-based feedback on concentration, idle cash, fees, panic selling
- **What-if Replay** — replay the *same* market with different strategies (hold the ETF,
  all-in one stock, panic-sell, buy-the-dip) and compare with what you actually did

**Optional extensions** — challenge scenarios, save/load, short selling (see roadmap).

## Quick start

```bash
cd FinalProject/trading-sim
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python3 main.py --seed 42
```
Type `help` in the game for all commands. Run tests with `pytest`.

## Documentation

| Doc | Purpose |
|---|---|
| [`docs/01-requirements.md`](docs/01-requirements.md) | What must be built and why |
| [`docs/02-architecture.md`](docs/02-architecture.md) | Stack, structure, classes, data flow |
| [`docs/03-finance-model.md`](docs/03-finance-model.md) | Formulas + worked examples |
| [`docs/04-features-and-cli.md`](docs/04-features-and-cli.md) | Commands, screens, edge cases |
| [`docs/05-testing.md`](docs/05-testing.md) | Test plan |
| [`docs/06-roadmap-and-demo.md`](docs/06-roadmap-and-demo.md) | Phases, demo script, scoring checklist |
| [`docs/07-decisions-log.md`](docs/07-decisions-log.md) | Decisions and open questions |

## Status

See the checklist in `docs/06-roadmap-and-demo.md`. Current phase: **Phase 2 — Market Events** (Phase 1 done).
