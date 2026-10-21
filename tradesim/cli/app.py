"""The REPL: read a command, run it, print the result. The only module that talks to the user."""

import random

from rich.console import Console
from rich.markup import escape

import difflib
from pathlib import Path

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
from tradesim.cli import insights, parser, progress, views
from tradesim.database import read_games
from tradesim.education import (academy, achievements, coach, diversification_lab,
                                headline_lab, leverage_lab, whatif)
from tradesim.education.challenges import Challenge
from tradesim.education.robo_analyst import RoboAnalyst
from tradesim.engine.errors import CommandError, TradeSimError
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.loader import (load_challenges, load_events, load_glossary, load_quiz, load_regimes, load_robo,
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


def do_market(game: Game, args: list) -> object:
    return views.market_table(game, pick_symbols(game, args[0]) if args else None)


def pick_symbols(game: Game, word: str) -> list[str]:
    """The stocks of the sector starting with `word` ("tech", "real"…), or the ETFs for "etf"."""
    market = game.market
    if word in ("etf", "etfs"):
        return list(market.etfs)
    sectors = [name for name in market.sectors() if name.lower().startswith(word)]
    if not sectors:
        names = ", ".join(name.lower() for name in market.sectors())
        raise TradeSimError(f'No sector called "{word}". Try market etf or one of: {names}')
    return [symbol for symbol, stock in market.stocks.items() if stock.sector == sectors[0]]


def do_quote(game: Game, args: list) -> object:
    symbol = check_symbol(game, args[0])
    return views.quote_panel(game, symbol, insights.outlook_text(robo_model(), game, symbol))


def do_chart(game: Game, args: list) -> object:
    return views.chart_panel(game, [check_symbol(game, s) for s in args])


def do_etf(game: Game, args: list) -> object:
    symbol = args[0] if args else config.LAB_DEFAULT_ETF
    if not game.market.is_etf(check_symbol(game, symbol)):
        raise TradeSimError(f"{symbol} is a stock, not an ETF. Try: etf {config.LAB_DEFAULT_ETF}")
    return views.etf_panel(game, symbol)


def do_buy(game: Game, args: list) -> object:
    symbol, qty = args
    if qty == parser.MAX:
        qty = game.max_buy(check_symbol(game, symbol))
        if qty == 0:
            raise TradeSimError(f"You can't afford even 1 {symbol} right now.")
    trade = game.buy(symbol, qty)
    return trade_output(game, trade)


def do_sell(game: Game, args: list) -> object:
    symbol, qty = args
    if qty == parser.ALL:
        qty = game.portfolio.qty_held(check_symbol(game, symbol))
        if qty == 0:
            raise TradeSimError(f"You don't hold any {symbol}.")
    trade = game.sell(symbol, qty)
    return trade_output(game, trade)


def trade_output(game: Game, trade) -> list:
    """The confirmation line plus any Trade Coach tips about it (E-03)."""
    tips = coach.review_trade(game, trade)
    return [views.trade_message(trade, game.portfolio.cash)] + [insights.tip_line(t) for t in tips]


def do_portfolio(game: Game, args: list) -> object:
    return views.portfolio_view(game)


def do_history(game: Game, args: list) -> object:
    return views.history_table(game.portfolio.trades)


def no_ai(headline: str) -> None:
    """Stand-in classifier when no AI was given: always 'unavailable'."""
    return None


def do_next(game: Game, args: list, ai: SentimentClassifier | None) -> object:
    asked = args[0] if args else 1
    start, calls = game.day, len(game.margin_calls)
    events = game.advance(asked)
    moved = game.day - start
    lookup = ai.cached if ai else no_ai
    output = [views.recap_panel(game, start)] + views.news_lines(game, events, lookup)
    output += [insights.margin_call_line(trades) for trades in game.margin_calls[calls:]]
    if moved < asked:
        output.append(f"[yellow]Only {moved} day(s) were left — the game has ended.[/yellow]")
    return output + game_over_lines(game)


def game_over_lines(game: Game) -> list:
    """The final report and what to do next, once the last day has closed (else nothing)."""
    if not game.is_over():
        return []
    # Award the last-day badges first, so the report's badge count includes them.
    output = [progress.badge_line(b) for b in achievements.newly_unlocked(game)]
    return output + report_bundle(game) + ["Curious how other choices would have done? Type "
                                           "[cyan]whatif[/cyan]. Play again: [cyan]new[/cyan] or "
                                           "[cyan]challenge[/cyan]."]


def do_tick(game: Game, args: list) -> object:
    start, calls = game.day, len(game.margin_calls)
    news = game.step(args[0] if args else 1)
    news_tick = game.market.session(start + 1).news_tick
    output = [insights.tick_line(game)] + [insights.breaking_line(e, news_tick) for e in news]
    output += [insights.margin_call_line(trades) for trades in game.margin_calls[calls:]]
    if game.day > start:
        output += [views.recap_panel(game, start)] + game_over_lines(game)
    return output


def do_leverage(game: Game, args: list) -> object:
    if not args:
        return insights.leverage_view(game)
    game.set_leverage(args[0])
    return [f"[green]✓ You may now borrow up to {args[0]}× your own money.[/green]",
            insights.leverage_view(game)]


def do_levlab(game: Game, args: list) -> object:
    market = game.market
    symbol = check_symbol(game, args[0]) if args else market.index_symbol()
    start = max(market.first_day, game.day - config.LEVERAGE_LAB_DAYS)
    if start == game.day:
        raise TradeSimError("Play a few days first (next 5): the lab replays days you have seen.")
    runs = leverage_lab.compare(market, symbol, start, game.day)
    return insights.leverage_lab_view(symbol, runs, leverage_lab.lessons(runs, symbol), start, game.day)


def do_lab(game: Game, args: list) -> object:
    if args and args[0] == "MC":
        stock = args[1] if len(args) > 1 else config.LAB_DEFAULT_STOCK
        market = game.market
        result = diversification_lab.monte_carlo(market.stocks, market.etfs, stock,
                                                 config.LAB_DEFAULT_ETF, market.seed,
                                                 regime_model=market.regime_model)
        return views.monte_carlo_view(result)
    stock = args[0] if args else config.LAB_DEFAULT_STOCK
    etf = args[1] if len(args) > 1 else config.LAB_DEFAULT_ETF
    result = diversification_lab.compare(game.market, stock, etf, 0, game.day)
    return views.lab_view(result)


def do_news(game: Game, args: list) -> object:
    day = args[0] if args else game.day
    if day == 0:
        raise TradeSimError("Day 0 is the opening day — there's no news yet. Try: next")
    if day > game.day:
        raise TradeSimError(f"Day {day} hasn't happened yet (today is day {game.day}).")
    return views.news_view(game, day)


def do_headlines(game: Game, args: list, ai: SentimentClassifier | None) -> object:
    classify = ai.classify if ai else no_ai
    words = load_events(game.market.stocks)
    if args:
        keywords = headline_lab.keyword_verdict(args[0], words.positive_words, words.negative_words)
        return views.own_headline_view(args[0], keywords, classify(args[0]))
    events = [e for day in range(1, game.day + 1) for e in game.market.events_on(day)]
    if not events:
        return 'No news so far. Try next 5, or: hl "Chipmaker beats forecasts"'
    result = headline_lab.score(events, classify, words.positive_words, words.negative_words)
    return views.headline_lab_view(game, result)


def report_bundle(game: Game) -> list:
    """The report, challenge goals, coach tips and (at the end) the market's story."""
    output = [views.report_panel(game)]
    goals = progress.goals_panel(game)
    if goals:
        output.append(goals)
    output += [insights.tip_line(tip) for tip in coach.review_session(game)]
    if game.is_over():
        output.append(insights.story_view(game))
    return output


def do_report(game: Game, args: list) -> object:
    return report_bundle(game)


def do_robo(game: Game, args: list) -> object:
    analyst = robo_model()
    if args:
        return insights.symbol_robo_view(game, analyst, check_symbol(game, args[0]))
    return insights.robo_view(game, analyst)


def do_story(game: Game, args: list) -> object:
    return insights.story_view(game)


def do_sectors(game: Game, args: list) -> object:
    return insights.sectors_view(game)


def do_coach(game: Game, args: list) -> object:
    return insights.coach_view(coach.review_session(game))


def do_whatif(game: Game, args: list) -> object:
    if game.day == 0:
        raise TradeSimError("Nothing to replay on day 0. Play a few days first: next 5")
    results = whatif.compare_strategies(game, robo_model())
    index = game.market.index_symbol()
    return insights.whatif_view(results, whatif.lessons(results, index), game.day, index)


def do_badges(game: Game, args: list) -> object:
    return progress.badges_view(game)


def do_games(game: Game, args: list, db_path: Path | None) -> object:
    if db_path is None:
        raise TradeSimError("Saved games aren't kept in this session.")
    return progress.games_view(read_games(db_path), load_challenges())


def do_challenge(game: Game, args: list) -> object:
    catalogue = load_challenges()
    if not args:
        return progress.challenges_view(catalogue)
    if args[0] not in catalogue:
        close = difflib.get_close_matches(args[0], list(catalogue), n=1)
        hint = f' Did you mean "challenge {close[0]}"?' if close else " Type challenge to list them."
        raise TradeSimError(f'There is no challenge called "{args[0]}".{hint}')
    fresh = new_game(None, config.GAME_DAYS, catalogue[args[0]])
    restart(game, fresh)
    return [progress.challenge_intro(game), views.market_table(game)]


def restart(game: Game, fresh: Game) -> None:
    """Swap a finished or abandoned game for `fresh`, keeping the same Game object.

    Every front end holds on to its Game, so changing it in place means `new` and
    `challenge` work the same in the REPL, agent mode and the web app.
    """
    game.reset(fresh.market, fresh.portfolio, fresh.challenge)
    game.equity_history = fresh.equity_history
    game.badges = fresh.badges


def do_new(game: Game, args: list) -> object:
    if args and args[0] >= MAX_SEED:      # a huge seed can't be saved in SQLite
        raise TradeSimError(f"The seed must be below {MAX_SEED:,} (e.g. new 42).")
    restart(game, new_game(args[0] if args else None, config.GAME_DAYS))
    return [views.banner(game), views.quick_start()]


def do_learn(game: Game, args: list) -> object:
    terms = load_glossary()
    if not args:
        return progress.glossary_view(terms)
    return progress.term_view(academy.find_term(terms, args[0]))


def do_quiz(game: Game, args: list) -> object:
    questions = load_quiz()
    number, question = academy.current_question(questions, len(game.quiz_results))
    if not args:
        return progress.question_view(number, question, len(questions), quiz_score(game))
    game.quiz_results.append(academy.mark(question, args[0]))
    return progress.answer_view(question, game.quiz_results[-1], quiz_score(game))


def quiz_score(game: Game) -> tuple[int, int]:
    """(right answers, questions answered)."""
    return sum(game.quiz_results), len(game.quiz_results)


def do_help(game: Game, args: list) -> object:
    return views.help_view(parser.COMMANDS, args[0] if args else None)


HANDLERS = {
    "market": do_market, "quote": do_quote, "chart": do_chart, "etf": do_etf,
    "buy": do_buy, "sell": do_sell, "portfolio": do_portfolio, "history": do_history,
    "news": do_news, "lab": do_lab, "report": do_report, "help": do_help,
    "robo": do_robo, "story": do_story, "sectors": do_sectors, "coach": do_coach,
    "whatif": do_whatif, "badges": do_badges, "challenge": do_challenge, "new": do_new,
    "learn": do_learn, "quiz": do_quiz, "tick": do_tick, "leverage": do_leverage,
    "levlab": do_levlab,
}


# These commands also need the AI classifier (the rest only need the game).
AI_HANDLERS = {"next": do_next, "headlines": do_headlines}
# These read the player database (None = this session keeps no saved games).
DB_HANDLERS = {"games": do_games}


def execute(game: Game, line: str, ai: SentimentClassifier | None = None,
            db_path: Path | None = config.PLAYER_DB_PATH) -> list:
    """Run one input line and return what to print. Raises TradeSimError on bad input."""
    command = parser.parse(line)
    if command is None:
        return []
    if command.name == "quit":
        return ["Cancelled — still playing."]
    if command.name in AI_HANDLERS:
        result = AI_HANDLERS[command.name](game, command.args, ai)
    elif command.name in DB_HANDLERS:
        result = DB_HANDLERS[command.name](game, command.args, db_path)
    elif command.name in HANDLERS:
        result = HANDLERS[command.name](game, command.args)
    else:
        raise CommandError(f"{command.name} isn't available yet.")
    output = result if isinstance(result, list) else [result]
    game.commands_used.add(command.name)
    return output + [progress.badge_line(b) for b in achievements.newly_unlocked(game)]


def run_command(game: Game, line: str, ai: SentimentClassifier | None = None) -> list:
    """Run one input line and return what to print. Never raises TradeSimError."""
    try:
        return execute(game, line, ai)
    except TradeSimError as error:
        # escape: the message may quote the player's text, and "[/x]" would be read as a style tag
        return [f"[red]✗ {escape(str(error))}[/red]"]


def is_command(line: str, name: str) -> bool:
    """True if `line` starts with command `name` or one of its aliases."""
    words = line.split()
    if not words:
        return False
    word = words[0].lower()
    return word == name or parser.ALIASES.get(word) == name


def is_quit(line: str) -> bool:
    """True if the player typed quit (or its alias exit)."""
    return is_command(line, "quit")


def run(seed: int | None, days: int) -> None:
    """Play one game in the terminal until the player quits."""
    console = Console()
    game = new_game(seed, days)
    ai = SentimentClassifier()
    console.print(views.banner(game))
    console.print(views.quick_start())
    while True:
        try:
            line = console.input("[bold cyan]> [/bold cyan]")
            if is_quit(line) and console.input("Quit and see your final report? (y/n) ").lower().startswith("y"):
                break
        except (KeyboardInterrupt, EOFError):
            break  # Ctrl+C / Ctrl+D: leave gracefully, no traceback
        if is_command(line, "headlines"):
            # Laya loads on first use (~10 s on a CPU), so show a spinner while the AI works.
            with console.status("Asking Laya AI… (the first time loads the model, ~10 s)"):
                output = run_command(game, line, ai)
        else:
            output = run_command(game, line, ai)
        for renderable in output:
            console.print(renderable)
        if output:
            console.print(views.status_bar(game), style="dim")
    console.print()
    console.print(views.report_panel(game))
    console.print("Thanks for playing!")
