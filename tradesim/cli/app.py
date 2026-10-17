"""The REPL: read a command, run it, print the result. The only module that talks to the user."""

import random

from rich.console import Console

from tradesim import config
from tradesim.cli import parser, views
from tradesim.education import diversification_lab
from tradesim.engine.errors import CommandError, TradeSimError
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.loader import load_events, load_universe

MAX_SEED = 1_000_000


def new_game(seed: int | None, days: int) -> Game:
    """Load the universe and build a fresh market and portfolio."""
    if seed is None:
        # A seed is chosen once and shown, so any game can be replayed with --seed.
        seed = random.SystemRandom().randrange(MAX_SEED)
    stocks, etfs = load_universe(config.UNIVERSE_PATH)
    templates = load_events(config.EVENTS_PATH, stocks).templates
    market = Market(stocks, etfs, seed, days, templates)
    return Game(market, Portfolio(config.STARTING_CASH, config.FEE_PER_TRADE))


def check_symbol(game: Game, symbol: str) -> str:
    """Return `symbol` if it trades in this market (raises UnknownSymbolError otherwise)."""
    game.market.name_of(symbol)
    return symbol


def do_market(game: Game, args: list) -> object:
    return views.market_table(game)


def do_quote(game: Game, args: list) -> object:
    return views.quote_panel(game, check_symbol(game, args[0]))


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
    return views.trade_message(trade, game.portfolio.cash)


def do_sell(game: Game, args: list) -> object:
    symbol, qty = args
    if qty == parser.ALL:
        qty = game.portfolio.qty_held(check_symbol(game, symbol))
        if qty == 0:
            raise TradeSimError(f"You don't hold any {symbol}.")
    trade = game.sell(symbol, qty)
    return views.trade_message(trade, game.portfolio.cash)


def do_portfolio(game: Game, args: list) -> object:
    return views.portfolio_view(game)


def do_history(game: Game, args: list) -> object:
    return views.history_table(game.portfolio.trades)


def do_next(game: Game, args: list) -> object:
    asked = args[0] if args else 1
    start = game.day
    events = game.advance(asked)
    moved = game.day - start
    output = [views.market_table(game)] + views.news_lines(game, events)
    if moved < asked:
        output.append(f"[yellow]Only {moved} day(s) were left — the game has ended.[/yellow]")
    if game.is_over():
        output.append(views.report_panel(game))
    return output


def do_lab(game: Game, args: list) -> object:
    if args and args[0] == "MC":
        stock = args[1] if len(args) > 1 else config.LAB_DEFAULT_STOCK
        market = game.market
        result = diversification_lab.monte_carlo(market.stocks, market.etfs, stock,
                                                 config.LAB_DEFAULT_ETF, market.seed)
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


def do_report(game: Game, args: list) -> object:
    return views.report_panel(game)


def do_help(game: Game, args: list) -> object:
    return views.help_view(parser.COMMANDS, args[0] if args else None)


HANDLERS = {
    "market": do_market, "quote": do_quote, "chart": do_chart, "etf": do_etf,
    "buy": do_buy, "sell": do_sell, "portfolio": do_portfolio, "history": do_history,
    "next": do_next, "news": do_news, "lab": do_lab, "report": do_report, "help": do_help,
}


def run_command(game: Game, line: str) -> list:
    """Run one input line and return what to print. Never raises TradeSimError."""
    try:
        command = parser.parse(line)
        if command is None:
            return []
        if command.name == "quit":
            return ["Cancelled — still playing."]
        if command.name not in HANDLERS:
            raise CommandError(f"{command.name} isn't available yet.")
        result = HANDLERS[command.name](game, command.args)
    except TradeSimError as error:
        return [f"[red]✗ {error}[/red]"]
    return result if isinstance(result, list) else [result]


def is_quit(line: str) -> bool:
    """True if the player typed quit (or its alias exit)."""
    words = line.split()
    return bool(words) and words[0].lower() in ("quit", "exit")


def run(seed: int | None, days: int) -> None:
    """Play one game in the terminal until the player quits."""
    console = Console()
    game = new_game(seed, days)
    console.print(views.banner(game))
    console.print("Type [cyan]help[/cyan] for commands, [cyan]market[/cyan] to see prices, "
                  "[cyan]lab[/cyan] to learn about diversification.")
    while True:
        try:
            line = console.input("[bold cyan]> [/bold cyan]")
            if is_quit(line) and console.input("Quit and see your final report? (y/n) ").lower().startswith("y"):
                break
        except (KeyboardInterrupt, EOFError):
            break  # Ctrl+C / Ctrl+D: leave gracefully, no traceback
        for renderable in run_command(game, line):
            console.print(renderable)
    console.print()
    console.print(views.report_panel(game))
    console.print("Thanks for playing!")
