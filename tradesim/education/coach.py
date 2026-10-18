"""E-03 Trade Coach: small rule functions that spot good and bad investing habits.

Each rule takes the game (and the trade just made, for trade rules) and returns a Tip
or None. Rules live in plain lists, so adding a habit is one function plus one list entry.
"""

from tradesim import config
from tradesim.education.explainer import effective_shares
from tradesim.engine import margin
from tradesim.engine.game import Game
from tradesim.engine.trade import Trade

WARN = "warn"
PRAISE = "praise"
INFO = "info"


class Tip:
    """One piece of coaching."""

    def __init__(self, rule_id: str, severity: str, message: str) -> None:
        """`severity` is WARN (bad habit), PRAISE (good habit) or INFO."""
        self.rule_id = rule_id
        self.severity = severity
        self.message = message

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"Tip({self.rule_id!r}, {self.severity!r})"


def stock_weights(game: Game) -> dict[str, float]:
    """Share of equity in each single stock held (ETFs left out: they're already spread)."""
    weights = game.portfolio.weights(game.current_prices())
    return {s: w for s, w in weights.items() if s in game.market.stocks}


def sectors_held(game: Game) -> set[str]:
    """Every sector the player owns, counting the companies inside ETFs too."""
    market, sectors = game.market, set()
    for symbol in game.portfolio.positions:
        holdings = market.etfs[symbol].weights if market.is_etf(symbol) else [symbol]
        sectors.update(market.stocks[s].sector for s in holdings)
    return sectors


def concentration(game: Game, trade: Trade | None = None) -> Tip | None:
    """One stock is more than half of everything you own."""
    for symbol, weight in stock_weights(game).items():
        if weight > config.CONCENTRATION_LIMIT:
            return Tip("CONC", WARN, f"{symbol} is now {weight:.0%} of your money. One bad headline "
                                     f"could hurt a lot — an ETF like {config.LAB_DEFAULT_ETF} "
                                     "spreads the risk.")
    return None


def panic(game: Game, trade: Trade) -> Tip | None:
    """Sold at a loss right after a sharp drop."""
    if trade.side != "SELL" or trade.realised_pnl >= 0:
        return None
    start = max(0, game.day - config.PANIC_WINDOW_DAYS)
    peak = max(game.market.history(trade.symbol, start, game.day))
    if trade.price <= peak * (1 - config.PANIC_DROP):
        return Tip("PANIC", WARN, f"You sold {trade.symbol} right after a sharp drop. Selling in a "
                                  "panic locks in the loss — ask 'has anything really changed?'")
    return None


def chasing(game: Game, trade: Trade) -> Tip | None:
    """Bought something that has just shot up."""
    if trade.side != "BUY" or game.day < config.CHASE_WINDOW_DAYS:
        return None
    before = game.market.price(trade.symbol, game.day - config.CHASE_WINDOW_DAYS)
    rise = trade.price / before - 1
    if rise >= config.CHASE_RISE:
        return Tip("CHASE", INFO, f"{trade.symbol} is up {rise:.0%} in {config.CHASE_WINDOW_DAYS} "
                                  "days. Buying after a big jump is 'chasing' — hot streaks often "
                                  "cool off.")
    return None


def overtrading(game: Game, trade: Trade) -> Tip | None:
    """Lots of trades on one day."""
    today = sum(1 for t in game.portfolio.trades if t.day == trade.day)
    if today >= config.OVERTRADE_PER_DAY:
        fees = today * game.portfolio.fee_per_trade
        return Tip("OVER", WARN, f"{today} trades today = ${fees:,.0f} in fees. Frequent trading "
                                 "rarely beats patience.")
    return None


def idle_cash(game: Game) -> Tip | None:
    """Most of the money is still sitting in cash."""
    cash_share = game.portfolio.weights(game.current_prices())["CASH"]
    if game.day >= config.IDLE_CASH_GRACE_DAYS and cash_share > config.IDLE_CASH_LIMIT:
        return Tip("IDLE", INFO, f"{cash_share:.0%} of your money is sitting in cash. Cash is safe, "
                                 "but it doesn't grow.")
    return None


def fees(game: Game) -> Tip | None:
    """Fees ate a big part of the result."""
    paid = game.portfolio.fees_paid
    result = abs(game.portfolio.total_pnl(game.current_prices()))
    if paid >= config.FEE_TIP_MIN and paid > config.FEE_SHARE_LIMIT * result:
        return Tip("FEES", WARN, f"You've paid ${paid:,.0f} in fees — that's a big slice of your "
                                 f"${result:,.0f} result. Fewer, bigger decisions cost less.")
    return None


def diversified(game: Game) -> Tip | None:
    """Praise a spread-out portfolio (positive feedback matters too), but not one on borrowed money."""
    if not game.portfolio.positions or game.portfolio.loan() > 0:
        return None
    biggest = max(stock_weights(game).values(), default=0.0)
    if len(sectors_held(game)) >= config.GOOD_MIN_SECTORS and biggest <= config.GOOD_MAX_WEIGHT:
        return Tip("GOOD", PRAISE, "Nicely diversified — you own several sectors and no single "
                                   "company can sink you.")
    return None


def borrowing(game: Game, trade: Trade | None = None) -> Tip | None:
    """You owe the broker money: say how small a fall would trigger a margin call."""
    account, prices = game.portfolio, game.current_prices()
    if account.loan() == 0 or (trade is not None and trade.side != "BUY"):
        return None
    room = margin.fall_to_call(account, prices)
    severity = WARN if room < config.MARGIN_DANGER else INFO
    return Tip("LEV", severity, f"You're borrowing ${account.loan():,.0f} "
                                f"({margin.leverage_used(account, prices):.1f}× leverage). If your holdings "
                                f"fall {room:.0%}, the broker will sell them for you (a margin call).")


def margin_called(game: Game) -> Tip | None:
    """The broker had to sell: leverage turned a dip into a forced sale."""
    if not game.margin_calls:
        return None
    return Tip("CALL", WARN, f"You were margin-called {len(game.margin_calls)} time(s): the broker sold "
                             "at a bad moment to cover your loan. Less leverage leaves room for normal dips.")


TRADE_RULES = [borrowing, concentration, panic, chasing, overtrading]
SESSION_RULES = [margin_called, borrowing, concentration, idle_cash, fees, diversified]


def review_trade(game: Game, trade: Trade) -> list[Tip]:
    """Tips right after a trade (at most MAX_TIPS_AFTER_TRADE, so it isn't naggy)."""
    tips = [rule(game, trade) for rule in TRADE_RULES]
    return [tip for tip in tips if tip][:config.MAX_TIPS_AFTER_TRADE]


def review_session(game: Game) -> list[Tip]:
    """Every session tip that applies right now."""
    tips = [rule(game) for rule in SESSION_RULES]
    return [tip for tip in tips if tip]


def sector_exposure(game: Game) -> dict[str, float]:
    """Dollars in each sector, looking inside ETFs (a fund's value is split by its holdings)."""
    market, prices = game.market, game.current_prices()
    exposure = {}
    for symbol, position in game.portfolio.positions.items():
        value = position.market_value(prices[symbol])
        shares = effective_shares(market, symbol, game.day) if market.is_etf(symbol) else {symbol: 1.0}
        for stock, share in shares.items():
            sector = market.stocks[stock].sector
            exposure[sector] = exposure.get(sector, 0.0) + value * share
    return exposure
