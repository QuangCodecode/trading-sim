"""Commands: the one way every front end changes the game (D-25, D-37, D-50).

`execute` runs one command line ("buy NVDA 10") on a game. The few commands that answer with
data (quiz, hl, lab mc) return a small dict; the rest return None. Nothing here prints.
"""

import difflib
import random

from tradesim import config
from tradesim.cli import parser
from tradesim.education import academy, achievements, diversification_lab, headline_lab
from tradesim.education.challenges import Challenge
from tradesim.education.robo_analyst import RoboAnalyst
from tradesim.engine.errors import CommandError, TradeSimError
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.loader import (load_challenges, load_events, load_quiz, load_regimes, load_robo,
                             load_universe)

MAX_SEED = 1_000_000


def new_game(seed: int | None, days: int, challenge: Challenge | None = None) -> Game:
    """Load the data files and build a fresh market and portfolio.

    A challenge brings its own seed, length and starting trades (education/challenges.py).
    """
    if challenge is not None:
        seed, days = challenge.seed, challenge.days
    if seed is None:
        # A seed is chosen once and shown, so any game can be replayed with --seed.
        seed = random.SystemRandom().randrange(MAX_SEED)
    stocks, etfs = load_universe()
    templates = load_events(stocks).templates
    regimes = load_regimes()
    market = Market(stocks, etfs, seed, days, templates, regime_model=regimes,
                    prehistory_days=config.PREHISTORY_DAYS)
    game = Game(market, Portfolio(config.STARTING_CASH, config.FEE_PER_TRADE), challenge)
    for line in challenge.start if challenge else []:
        execute(game, line)
    return game


def robo_model() -> RoboAnalyst:
    """The trained Robo-analyst (a small JSON file, so loading it each time is cheap)."""
    return load_robo(config.ROBO_MODEL_PATH)


def check_symbol(game: Game, symbol: str) -> str:
    """Return `symbol` if it trades in this market (raises UnknownSymbolError otherwise)."""
    game.market.name_of(symbol)
    return symbol


def do_buy(game: Game, args: list) -> None:
    symbol, qty = args
    if qty == parser.MAX:
        qty = game.max_buy(check_symbol(game, symbol))
        if qty == 0:
            raise TradeSimError(f"You can't afford even 1 {symbol} right now.")
    game.buy(symbol, qty)


def do_sell(game: Game, args: list) -> None:
    symbol, qty = args
    if qty == parser.ALL:
        qty = game.portfolio.qty_held(check_symbol(game, symbol))
        if qty == 0:
            raise TradeSimError(f"You don't hold any {symbol}.")
    game.sell(symbol, qty)


def do_next(game: Game, args: list) -> None:
    game.advance(args[0] if args else 1)


def do_tick(game: Game, args: list) -> None:
    game.step(args[0] if args else 1)


def do_leverage(game: Game, args: list) -> None:
    if args:        # a bare `leverage` (which once showed the account) is kept as a harmless no-op
        game.set_leverage(args[0])


def do_visit(game: Game, args: list) -> None:
    """news, robo, whatif, levlab: the page draws itself; this only records the visit for badges."""


def do_lab(game: Game, args: list) -> dict | None:
    """`lab` is a visit; `lab mc [STOCK]` builds 200 fresh markets and sums them up."""
    if not args:
        return None
    if args[0] != "MC":
        raise parser.usage_error("lab")
    stock = args[1] if len(args) > 1 else config.LAB_DEFAULT_STOCK
    market = game.market
    result = diversification_lab.monte_carlo(market.stocks, market.etfs, stock, config.LAB_DEFAULT_ETF,
                                             market.seed, regime_model=market.regime_model)
    return {"runs": result.runs, "threshold": result.loss_threshold,
            "sides": [monte_carlo_side(result, symbol, returns)
                      for symbol, returns in ((result.stock_symbol, result.stock_returns),
                                              (result.etf_symbol, result.etf_returns))]}


def monte_carlo_side(result: diversification_lab.MonteCarloResult, symbol: str, returns: list[float]) -> dict:
    """One column of the Monte Carlo table: average, odds of a big loss, best and worst run."""
    return {"symbol": symbol, "average": result.average(returns), "big_loss": result.big_loss_share(returns),
            "best": max(returns), "worst": min(returns)}


def do_headlines(game: Game, args: list) -> dict:
    """The word counter's reading of a headline the player typed."""
    words = load_events(game.market.stocks)
    verdict = headline_lab.keyword_verdict(args[0], words.positive_words, words.negative_words)
    return {"headline": args[0], "label": verdict.label, "found": verdict.reason}


def do_quiz(game: Game, args: list) -> dict | None:
    """Mark the answer to the current question and say what the right one was."""
    if not args:          # a bare `quiz` (which once showed the question) is kept as a harmless no-op
        return None
    questions = load_quiz()
    number, question = academy.current_question(questions, len(game.quiz_results))
    game.quiz_results.append(academy.mark(question, args[0]))
    return {"correct": game.quiz_results[-1], "answer": academy.LETTERS[question["answer"]],
            "explain": question["explain"], "right": sum(game.quiz_results), "asked": len(game.quiz_results)}


def do_challenge(game: Game, args: list) -> None:
    catalogue = load_challenges()
    if not args:
        raise parser.usage_error("challenge")
    if args[0] not in catalogue:
        close = difflib.get_close_matches(args[0], list(catalogue), n=1)
        hint = f' Did you mean "challenge {close[0]}"?' if close else ""
        raise TradeSimError(f'There is no challenge called "{args[0]}".{hint}')
    restart(game, new_game(None, config.GAME_DAYS, catalogue[args[0]]))


def restart(game: Game, fresh: Game) -> None:
    """Swap a finished or abandoned game for `fresh`, keeping the same Game object.

    The web session holds on to its Game, so changing it in place makes `new` and
    `challenge` work the same as a game loaded from a save.
    """
    game.reset(fresh.market, fresh.portfolio, fresh.challenge)
    game.equity_history = fresh.equity_history
    game.badges = fresh.badges


def do_new(game: Game, args: list) -> None:
    if args and args[0] >= MAX_SEED:      # a huge seed can't be saved in SQLite
        raise TradeSimError(f"The seed must be below {MAX_SEED:,} (e.g. new 42).")
    restart(game, new_game(args[0] if args else None, config.GAME_DAYS))


HANDLERS = {
    "buy": do_buy, "sell": do_sell, "next": do_next, "tick": do_tick, "leverage": do_leverage,
    "lab": do_lab, "headlines": do_headlines, "quiz": do_quiz, "challenge": do_challenge, "new": do_new,
    "news": do_visit, "robo": do_visit, "whatif": do_visit, "levlab": do_visit,
}


def execute(game: Game, line: str) -> dict | None:
    """Run one command line and return its result (a dict, or None). Raises TradeSimError on bad input."""
    command = parser.parse(line)
    if command is None:
        return None
    if command.name not in HANDLERS:
        raise CommandError(f"{command.name} isn't available.")
    result = HANDLERS[command.name](game, command.args)
    game.commands_used.add(command.name)
    achievements.newly_unlocked(game)        # fills game.badges; the web session announces them
    return result
