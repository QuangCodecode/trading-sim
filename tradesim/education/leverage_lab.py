"""E-08 Leverage Lab: replay the market so far with borrowed money (finance model §3.13).

The same symbol over the same days, five ways: no borrowing, 2×, 3× and 5× on margin
(same broker rules as the game: nightly interest, margin calls at maintenance), and a
2× "daily" fund that resets its leverage every day like real leveraged ETFs. It shows
the three things leverage really does: it multiplies the swings, it costs interest, and
a margin call can force you to sell at the bottom so you miss the recovery.
"""

from tradesim import config
from tradesim.engine import margin
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio


class LeverageRun:
    """One way of holding the symbol: its equity each day and what happened along the way."""

    def __init__(self, label: str, leverage: float, values: list[float], called_on: int | None,
                 interest: float) -> None:
        """`called_on` is the day of the first margin call (None if there was none)."""
        self.label = label
        self.leverage = leverage
        self.values = values
        self.called_on = called_on
        self.interest = interest

    def total_return(self) -> float:
        """Return on your own money from the first day to the last, as a fraction."""
        return self.values[-1] / self.values[0] - 1

    def __repr__(self) -> str:
        return f"LeverageRun({self.label!r}, return={self.total_return():+.1%}, called_on={self.called_on})"


def margin_run(market: Market, symbol: str, start: int, end: int, leverage: int,
               amount: float) -> LeverageRun:
    """Buy as much `symbol` as `leverage` allows on `start` and hold it; the broker checks each close."""
    account = Portfolio(amount, config.FEE_PER_TRADE, max_leverage=leverage)
    prices = {symbol: market.price(symbol, start)}
    credit = margin.credit(account, prices)
    qty = account.max_affordable(prices[symbol], credit)
    if qty > 0:
        account.buy(symbol, qty, prices[symbol], start, credit)
    values, called_on = [account.equity(prices)], None
    for day in range(start + 1, end + 1):
        prices = {symbol: market.price(symbol, day)}
        account.charge_interest(config.MARGIN_RATE, config.TRADING_DAYS_PER_YEAR)
        if margin.is_margin_call(account, prices):
            margin.liquidate(account, prices, day, 0)
            called_on = called_on or day
        values.append(account.equity(prices))
    name = "No borrowing" if leverage == 1 else f"{leverage}× on margin"
    return LeverageRun(name, leverage, values, called_on, account.interest_paid)


def daily_fund_run(market: Market, symbol: str, start: int, end: int, leverage: int,
                   amount: float) -> LeverageRun:
    """A leveraged fund that resets every day: each day it moves `leverage` × that day's move."""
    values = [amount]
    for day in range(start + 1, end + 1):
        move = market.price(symbol, day) / market.price(symbol, day - 1) - 1
        values.append(max(0.0, values[-1] * (1 + leverage * move)))
    return LeverageRun(f"{leverage}× daily fund", leverage, values, None, 0.0)


def compare(market: Market, symbol: str, start: int, end: int,
            amount: float = config.LAB_DEFAULT_AMOUNT) -> list[LeverageRun]:
    """Every margin level in LEVERAGE_LAB_LEVELS, then the 2× daily fund."""
    runs = [margin_run(market, symbol, start, end, level, amount) for level in config.LEVERAGE_LAB_LEVELS]
    runs.append(daily_fund_run(market, symbol, start, end, 2, amount))
    return runs


def lessons(runs: list[LeverageRun], symbol: str, day_name=lambda day: f"day {day}") -> list[str]:
    """Plain-English takeaways from a comparison; `day_name` turns a day number into words."""
    plain, two, fund = runs[0], runs[1], runs[-1]
    move = plain.total_return()
    lines = [f"{symbol} returned {move:+.1%}. 2× on margin returned {two.total_return():+.1%}, not "
             f"{2 * move:+.1%}: ${two.interest:,.0f} of interest and fees came out of it."]
    called = [run for run in runs if run.called_on is not None]
    if called:
        first = min(called, key=lambda run: run.called_on)
        lines.append(f"{first.label} was margin-called on {day_name(first.called_on)}: the broker sold at the "
                     "bottom, so it couldn't win back the losses even if prices recovered.")
    else:
        worst = margin.call_move(runs[-2].leverage)
        lines.append(f"Nobody was margin-called this time. At {runs[-2].leverage:.0f}× a fall of only "
                     f"{worst:.0%} would have done it.")
    lines.append(f"The 2× daily fund returned {fund.total_return():+.1%}. Resetting every day loses money "
                 "when prices zig-zag (volatility decay), so it rarely gives exactly 2× over many days.")
    return lines


def risk_table() -> list[tuple[int, float, float, float]]:
    """(leverage, maintenance, fall that triggers a margin call, fall that wipes you out) per level."""
    return [(level, margin.maintenance(level), margin.call_move(level), margin.wipeout_move(level))
            for level in range(1, config.MAX_LEVERAGE + 1)]
