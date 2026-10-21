"""Margin trading (leverage): borrowing from the broker to buy more (finance model §3.13).

A margin account lets cash go below zero: that negative cash is a loan. The rules:

    leverage used     = holdings value / your own money (equity)
    may borrow        = (L − 1) × equity               so holdings ≤ L × equity after a buy
    maintenance       = MAINTENANCE_SHARE / L          e.g. 25% of holdings at L = 2
    margin call       when equity < maintenance × holdings value (and you owe money)
    then the broker sells your biggest holdings until holdings ≤ L × equity again.

Because equity moves L times faster than prices, the fall that triggers a margin call
shrinks as L grows: 1 / (2L − 1) of the holdings' value (33% at 2×, 11% at 5×).
"""

import math

from tradesim import config
from tradesim.engine.errors import TradeSimError
from tradesim.engine.portfolio import Portfolio
from tradesim.engine.trade import Trade


def credit(portfolio: Portfolio, prices: dict[str, float]) -> float:
    """How much the broker will lend for a buy: (L − 1) × your money after the fee."""
    own = portfolio.equity(prices) - portfolio.fee_per_trade
    return max(0.0, (portfolio.max_leverage - 1) * own)


def buying_power(portfolio: Portfolio, prices: dict[str, float]) -> float:
    """Cash you can spend on shares right now, counting what the broker will lend."""
    return max(0.0, portfolio.cash + credit(portfolio, prices))


def leverage_used(portfolio: Portfolio, prices: dict[str, float]) -> float:
    """Holdings value ÷ equity: 1.0 = no borrowing, 2.0 = half the holdings are borrowed."""
    holdings = portfolio.market_value(prices)
    equity = portfolio.equity(prices)
    if holdings == 0:
        return 0.0
    return holdings / equity if equity > 0 else math.inf


def maintenance(leverage: float) -> float:
    """Share of the holdings' value your own money must stay above: half the starting cushion."""
    return config.MAINTENANCE_SHARE / leverage


def call_move(leverage: float) -> float:
    """The fall in holdings (as a fraction) that triggers a margin call at full leverage."""
    return 1 / (2 * leverage - 1) if leverage > 1 else 1.0


def wipeout_move(leverage: float) -> float:
    """The fall in holdings that wipes out all your own money at full leverage."""
    return 1 / leverage


def fall_to_call(portfolio: Portfolio, prices: dict[str, float]) -> float:
    """How far your holdings can fall (as a fraction) before a margin call; 1.0 if you don't borrow.

    Solves (E − x·H) / (H − x·H) = m for x, where E = equity, H = holdings, m = maintenance.
    """
    holdings = portfolio.market_value(prices)
    if portfolio.loan() == 0 or holdings == 0:
        return 1.0
    m = maintenance(portfolio.max_leverage)
    return max(0.0, (portfolio.equity(prices) - m * holdings) / (holdings * (1 - m)))


def is_margin_call(portfolio: Portfolio, prices: dict[str, float]) -> bool:
    """True if you owe the broker and your own money has fallen below maintenance.

    After a wipeout nothing is left to sell, so the leftover debt is not a margin call.
    """
    if portfolio.loan() == 0 or not portfolio.positions:
        return False
    holdings = portfolio.market_value(prices)
    return portfolio.equity(prices) < maintenance(portfolio.max_leverage) * holdings


def liquidate(portfolio: Portfolio, prices: dict[str, float], day: int, tick: int) -> list[Trade]:
    """The broker sells your biggest holdings first until holdings ≤ L × equity again.

    If your equity is gone (≤ 0) everything is sold, and any debt left stays as negative cash.
    """
    trades = []
    biggest_first = sorted(portfolio.positions, key=lambda s: -portfolio.positions[s].market_value(prices[s]))
    for symbol in biggest_first:
        equity = portfolio.equity(prices)
        excess = portfolio.market_value(prices) - portfolio.max_leverage * (equity - portfolio.fee_per_trade)
        if equity > 0 and excess <= 0:
            break
        held = portfolio.qty_held(symbol)
        qty = held if equity <= 0 else min(held, math.ceil(excess / prices[symbol]))
        trades.append(portfolio.sell(symbol, qty, prices[symbol], day, tick, note="margin call"))
    return trades


def check_new_leverage(portfolio: Portfolio, prices: dict[str, float], leverage: int) -> None:
    """Raise TradeSimError unless `leverage` is allowed and you already fit under it."""
    if not 1 <= leverage <= config.MAX_LEVERAGE:
        raise TradeSimError(f"Leverage must be between 1 and {config.MAX_LEVERAGE} (e.g. leverage 2).")
    used = leverage_used(portfolio, prices)
    if used > leverage + 1e-9:
        raise TradeSimError(f"You're using {used:.1f}× now. Sell some holdings before lowering it to {leverage}×.")
