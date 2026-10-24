TradeSim - a trading simulator that teaches why diversification matters
=======================================================================

COMP9001 Introduction to Programming - Final Project - Semester 2 2026
Author: Quang (Cillian) Nguyen

All prices are SIMULATED. Tickers are borrowed from real companies so they
feel familiar, but no real market data is used. This is an educational game,
not financial advice.


WHAT IT IS
----------
You start with $10,000 of play money and 60 trading days in a live market of
100 simulated stocks (10 sectors) and 14 ETFs. Prices tick every five minutes
from the 09:30 bell to the 16:00 close, news breaks during the day, and the
market has hidden moods (bull, sideways, bear, crash). You buy and sell, and
the game tracks your portfolio value and profit/loss. Along the way it shows
you, with your own numbers, why spreading your money usually beats betting on
one stock, and what borrowing to invest (leverage) really does.

It runs as a web page served by a small Python program on your own computer.
No internet connection is needed.


HOW TO RUN
----------
You need: Python 3.11 or newer, and a web browser. Nothing else - no pip
install, no packages. The game uses only the Python standard library.

    python3 main.py

Then open http://127.0.0.1:8000 (a browser tab opens by itself). Stop the
server with Ctrl+C in the terminal.

Options:
    python3 main.py --seed 39       fresh game on the demo market
                                    (a crash followed by a recovery)
    python3 main.py --seed 42       fresh game, reproducible (same seed =
                                    identical market every time)
    python3 main.py --days 30       shorter game
    python3 main.py --port 8123     use another port
    python3 main.py --no-browser    do not open a browser tab
    python3 main.py --db FILE       use another save file

Without --seed the game resumes your last unfinished game, or starts a new
random market if there is none. Games are saved in saves/player.db.


FIRST GAME (about a minute)
---------------------------
1. Press "Open the market".
2. Double-click NVDA on the price board.
3. Buy 50%.
4. Watch the price tick, then press "To close" to jump to the closing bell.
5. Read the closing-bell card (you versus the market).
6. Try the Leverage page.


FEATURES
--------
Live market
  - Broker-style price board: bid/ask levels, last price, volume,
    high/low/open, your position. Prices flash green or red as they tick.
  - Clock speed 1x to 15x; pause, finish the day, or skip 1, 5, 20 days or
    to the end.
  - Candlestick charts (15-minute candles for today, daily candles with six
    months of history), moving averages, volume, your trades marked.

Core trading
  - Virtual cash, buy/sell with validation, $1 fee per trade, portfolio
    tracking, realised and unrealised profit/loss.
  - MIX6 ETF priced as a weighted average of six stocks, plus a whole-market
    ETF, ten sector ETFs and two themed ETFs.

Realistic prices
  - Hidden market moods (Markov chain), volatility clustering, and beta per
    stock. Inside each day, prices follow a seeded Brownian bridge between
    the daily closes. Same seed = same market.

Learn by playing (the original part of the project)
  - Leverage: margin account (1x-5x), loan interest, margin calls, and a
    Leverage Lab comparing the same 60 days at different leverage.
  - Diversification Lab: one stock vs an ETF on the same days, plus a
    Monte Carlo run over 200 markets.
  - News and Headline Lab: every headline compared with what really happened.
  - Trade Coach: tips after each trade (concentration, panic selling, fees).
  - What-if Replay: the same market replayed with 11 strategies.
  - Robo-analyst: two small logistic regressions written by hand in plain
    Python (a mood detector and a price forecaster).
  - Academy: glossary, quiz, 9 challenges and 20 badges.


RUNNING THE TESTS (for developers / markers)
--------------------------------------------
Playing needs nothing installed. The tests need pytest, installed with uv:

    uv sync
    uv run pytest

Without uv:

    pip install -r requirements-dev.txt
    python -m pytest

(Use "python -m pytest", not bare "pytest", so the tradesim package is found.)


FOLDER LAYOUT
-------------
    main.py                  entry point: reads options, starts the server
    tradesim/
        config.py            all constants (starting cash, fees, ports, ...)
        database.py          the only place (with cli/savegame.py) with SQL
        loader.py            loads stocks, ETFs and news from the database
        engine/              market, prices, portfolio, trades, margin
                             (no print/input - returns data or raises errors)
        education/           labs, coach, what-if, robo-analyst, academy
        cli/                 command parser, game commands, save/load
        webapp/              http.server back end + static HTML/CSS/JS page
    data/reference.db        game content (stocks, news, quiz, ...), read-only
    saves/player.db          your saved games (created when you play)
    tests/                   pytest test suite
    tools/                   helper scripts (retrain robo-analyst, pick seed)
    docs/                    requirements, architecture, finance model,
                             testing, roadmap, decisions log, debug log

Design rules in one line each:
  - The engine never does input/output; only cli/ and webapp/ talk to the user.
  - All randomness goes through one seeded random.Random owned by the market.
  - Bad user input shows a friendly message; it never crashes the program.


DOCUMENTATION
-------------
README.md and the docs/ folder go into more detail:
    docs/01-requirements.md     what must be built and why
    docs/02-architecture.md     stack, structure, classes, data flow
    docs/03-finance-model.md    every formula with worked examples
    docs/04-features-and-cli.md commands, screens, edge cases
    docs/05-testing.md          test plan
    docs/06-roadmap-and-demo.md phases and demo script
    docs/07-decisions-log.md    decisions made
    docs/debug-log.md           real bugs: symptom, cause, fix, test
