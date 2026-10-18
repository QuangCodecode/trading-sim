"""E-04 preset strategies for the What-if Replay.

Every strategy is a function with the SAME signature:

    strategy(day, market, portfolio) -> list of orders, each ("BUY" or "SELL", symbol, qty)

so the replay engine can run any of them. Strategies may only look at prices up to `day`.
Some are built by a "factory" function that returns a strategy function: e.g.
buy_and_hold("MIX6") makes the strategy "spend everything on MIX6 on day 0".
"""

import math
from collections.abc import Callable

from tradesim import config
from tradesim.education.robo_analyst import RoboAnalyst
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.engine.trade import Trade

Order = tuple[str, str, int]
Strategy = Callable[[int, Market, Portfolio], list[Order]]   # the one shared signature


def spend(portfolio: Portfolio, market: Market, symbol: str, day: int, amount: float) -> Order:
    """An order buying as many whole shares of `symbol` as `amount` (after the fee) allows."""
    affordable = amount - portfolio.fee_per_trade
    return ("BUY", symbol, max(0, math.floor(affordable / market.price(symbol, day))))


def sell_everything(portfolio: Portfolio) -> list[Order]:
    """Orders that sell every holding."""
    return [("SELL", symbol, pos.qty) for symbol, pos in portfolio.positions.items()]


def cash_only(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
    """Never invest. The baseline every other strategy should beat."""
    return []


def buy_and_hold(symbol: str) -> Strategy:
    """Make a strategy that puts all cash into `symbol` on day 0 and then does nothing."""
    def strategy(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
        return [spend(portfolio, market, symbol, 0, portfolio.cash)] if day == 0 else []
    return strategy


def equal_weight(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
    """DIY index: on day 0 split the cash equally across every single stock."""
    if day != 0:
        return []
    share = portfolio.cash / len(market.stocks)
    return [spend(portfolio, market, symbol, 0, share) for symbol in market.stocks]


def panic_seller(symbol: str) -> Strategy:
    """Make a strategy: all-in on `symbol`, then sell everything after an 8% fall, for good."""
    def strategy(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
        if day == 0:
            return [spend(portfolio, market, symbol, 0, portfolio.cash)]
        position = portfolio.positions.get(symbol)
        if position and market.price(symbol, day) <= position.avg_cost * (1 - config.PANIC_DROP):
            return sell_everything(portfolio)
        return []
    return strategy


def buy_the_dip(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
    """Invest 20% of starting cash in the ETF on day 0 and again after every 2% daily fall."""
    tranche = config.DIP_TRANCHE * portfolio.starting_cash
    fund = config.LAB_DEFAULT_ETF
    if day == 0 or market.daily_change_pct(fund, day) <= -config.DIP_TRIGGER * 100:
        return [spend(portfolio, market, fund, day, min(tranche, portfolio.cash))]
    return []


def steady_saver(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
    """Dollar-cost averaging: invest an equal slice in the whole market every 5 days."""
    if day % config.DCA_INTERVAL_DAYS != 0:
        return []
    slices = math.ceil((market.num_days + 1) / config.DCA_INTERVAL_DAYS)
    amount = min(portfolio.starting_cash / slices, portfolio.cash)
    return [spend(portfolio, market, market.index_symbol(), day, amount)]


def chase_the_winner(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
    """Every 5 days, move everything into the stock that rose most over the last 5 days."""
    if day == 0 or day % config.CHASE_EVERY_DAYS != 0:
        return []
    start = day - config.CHASE_EVERY_DAYS
    best = max(market.stocks, key=lambda s: market.price(s, day) / market.price(s, start))
    if best in portfolio.positions:
        return []
    sells = sell_everything(portfolio)
    # Cash after the sells run (orders are filled in order, so the buy can use the proceeds).
    value = portfolio.equity(market.prices_on(day)) - portfolio.fee_per_trade * len(sells)
    return sells + [spend(portfolio, market, best, day, value)]


def follow_robo(analyst: RoboAnalyst) -> Strategy:
    """Make a strategy: hold the whole market, but go to cash while the robo smells a downturn."""
    index = config.MARKET_INDEX  # the robo's features are about MKT100

    def strategy(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
        worried = analyst.ready(day) and analyst.downturn_chance(market, day) > 0.5
        if worried and portfolio.positions:
            return sell_everything(portfolio)
        if not worried and not portfolio.positions:
            return [spend(portfolio, market, index, day, portfolio.cash)]
        return []
    return strategy


def copy_trades(trades: list[Trade]) -> Strategy:
    """Make a strategy that repeats the player's own trades on the same days."""
    def strategy(day: int, market: Market, portfolio: Portfolio) -> list[Order]:
        return [(t.side, t.symbol, t.qty) for t in trades if t.day == day]
    return strategy
