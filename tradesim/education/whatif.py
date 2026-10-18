"""E-04 What-if Replay: run many strategies on the SAME market and compare them.

The market is pre-generated from the seed (D-08), so every strategy sees exactly the
prices the player saw. Each one starts with the same cash and pays the same fee.
"""

from tradesim import config
from tradesim.education import strategies
from tradesim.education.robo_analyst import RoboAnalyst
from tradesim.engine import analytics
from tradesim.engine.errors import TradeSimError
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio

YOURS = "Your trades"


class ReplayResult:
    """One strategy's equity curve and the numbers we compare."""

    def __init__(self, name: str, about: str, curve: list[float], trades: int, fees: float) -> None:
        """`curve` = equity at the end of each day from day 0."""
        self.name = name
        self.about = about
        self.curve = curve
        self.trades = trades
        self.fees = fees
        self.final = curve[-1]
        self.total_return = self.final / config.STARTING_CASH - 1
        self.volatility = analytics.volatility(curve)
        self.max_drawdown = analytics.max_drawdown(curve)

    def __repr__(self) -> str:
        return f"ReplayResult({self.name!r}, final={self.final:.2f})"


def replay(market: Market, name: str, about: str, strategy, end_day: int) -> ReplayResult:
    """Run `strategy` from day 0 to `end_day`, trading at each day's price."""
    portfolio = Portfolio(config.STARTING_CASH, config.FEE_PER_TRADE)
    curve = []
    for day in range(end_day + 1):
        for side, symbol, qty in strategy(day, market, portfolio):
            try:
                if side == "BUY":
                    portfolio.buy(symbol, qty, market.price(symbol, day), day)
                else:
                    portfolio.sell(symbol, qty, market.price(symbol, day), day)
            except TradeSimError:
                pass  # an order that can't be filled (e.g. 0 shares) is simply skipped
        curve.append(portfolio.equity(market.prices_on(day)))
    return ReplayResult(name, about, curve, len(portfolio.trades), portfolio.fees_paid)


def favourite_stock(game: Game) -> str:
    """The stock the player spent most on (fallback: the jumpiest stock, NVDA)."""
    spent = {}
    for trade in game.portfolio.trades:
        if trade.side == "BUY" and trade.symbol in game.market.stocks:
            spent[trade.symbol] = spent.get(trade.symbol, 0) + trade.value()
    return max(spent, key=spent.get) if spent else config.LAB_DEFAULT_STOCK


def strategy_menu(game: Game, analyst: RoboAnalyst) -> list[tuple[str, str, object]]:
    """(name, one-line description, strategy function) for every contender."""
    stock, fund, index = favourite_stock(game), config.LAB_DEFAULT_ETF, game.market.index_symbol()
    return [
        ("Cash only", "Never invest", strategies.cash_only),
        (f"Hold {index}", "Buy the whole market on day 0, then relax", strategies.buy_and_hold(index)),
        (f"Hold {fund}", "Buy the six-stock ETF on day 0", strategies.buy_and_hold(fund)),
        ("DIY equal-weight", "Split cash equally across every stock", strategies.equal_weight),
        (f"All-in {stock}", "Everything in one stock", strategies.buy_and_hold(stock)),
        (f"Panic seller ({stock})", "All-in, then sell after an 8% fall", strategies.panic_seller(stock)),
        ("Buy the dip", f"Add to {fund} after each 2% drop", strategies.buy_the_dip),
        ("Steady saver", f"Invest in {index} every 5 days", strategies.steady_saver),
        ("Chase the winner", "Jump into last week's best stock", strategies.chase_the_winner),
        ("Follow the Robo-analyst", f"Hold {index}, flee to cash on downturn alarms",
         strategies.follow_robo(analyst)),
    ]


def your_result(game: Game) -> ReplayResult:
    """What really happened to you: the real equity curve, so trades made mid-session, borrowing,
    interest and margin calls all count (a close-price replay in a cash account would miss them)."""
    return ReplayResult(YOURS, "Exactly the trades you made", list(game.equity_history),
                        len(game.portfolio.trades), game.portfolio.fees_paid)


def compare_strategies(game: Game, analyst: RoboAnalyst) -> list[ReplayResult]:
    """Replay every strategy up to today (plus your real result), best final equity first."""
    results = [replay(game.market, name, about, strategy, game.day)
               for name, about, strategy in strategy_menu(game, analyst)]
    results.append(your_result(game))
    return sorted(results, key=lambda r: r.final, reverse=True)


def lessons(results: list[ReplayResult], index_symbol: str) -> list[str]:
    """Closing lessons chosen by rule from how the strategies did."""
    by_name = {r.name.split(" (")[0]: r for r in results}
    yours, index = by_name[YOURS], by_name[f"Hold {index_symbol}"]
    robo = by_name["Follow the Robo-analyst"]
    lines = []
    if results[0].name == YOURS:
        lines.append("You beat every preset strategy this time — check the drawdown column "
                     "to see how much risk you took to do it.")
    elif index.final > yours.final:
        lines.append(f"Simply holding the whole market ({index.name}) would have beaten your "
                     "trades. Doing less often earns more.")
    if robo.final < index.final:
        lines.append("Following the Robo-analyst did worse than just holding: by the time a "
                     "downturn is obvious, much of the fall has already happened.")
    chase = by_name["Chase the winner"]
    if chase.final < index.final:
        lines.append(f"Chasing last week's winner paid ${chase.fees:,.0f} in fees and still "
                     "trailed the market — hot streaks rarely last.")
    return lines or ["Every path is different: compare the return with the drawdown, not "
                     "the return alone."]
