"""The Portfolio class: cash, positions, trade log and profit/loss (C-01, C-05…C-08)."""

import math

from tradesim.engine.errors import (InsufficientCashError, InsufficientSharesError,
                                    InvalidQuantityError)
from tradesim.engine.position import Position
from tradesim.engine.trade import Trade


class Portfolio:
    """The player's account. Knows nothing about the market; prices are passed in."""

    def __init__(self, starting_cash: float, fee_per_trade: float, max_leverage: float = 1.0) -> None:
        """Open an account with `starting_cash` and a flat fee charged on every trade.

        `max_leverage` above 1 makes it a margin account: cash may go negative (a loan).
        """
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.fee_per_trade = fee_per_trade
        self.max_leverage = max_leverage
        self.interest_paid = 0.0
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []
        self.realised_pnl = 0.0
        self.fees_paid = 0.0

    def buy(self, symbol: str, qty: int, price: float, day: int, credit: float = 0.0,
            tick: int = 0) -> Trade:
        """Buy `qty` shares at `price`; raise if the quantity is bad or money is short.

        `credit` is how much the broker will lend on top of the cash (margin.credit).
        """
        check_quantity(qty)
        cost = qty * price + self.fee_per_trade
        # Tiny tolerance so float noise can't block a buy that uses exactly all the cash.
        if cost > self.cash + credit + 1e-9:
            what = "buying power" if credit > 0 else "cash"
            raise InsufficientCashError(
                f"Not enough {what}: need ${cost:,.2f}, you have ${max(0.0, self.cash + credit):,.2f}. "
                f"Max you can buy: {self.max_affordable(price, credit)} (try: buy {symbol} max)")
        self.cash -= cost
        self.positions.setdefault(symbol, Position(symbol)).add(qty, price)
        return self._record(Trade(day, "BUY", symbol, qty, price, self.fee_per_trade, tick=tick))

    def sell(self, symbol: str, qty: int, price: float, day: int, tick: int = 0,
             note: str = "") -> Trade:
        """Sell `qty` shares at `price`; the fee comes out of the proceeds."""
        check_quantity(qty)
        held = self.qty_held(symbol)
        if qty > held:
            raise InsufficientSharesError(f"You hold {held} {symbol}, can't sell {qty}")
        if qty * price < self.fee_per_trade:
            raise InsufficientCashError("The sale is worth less than the fee")
        position = self.positions[symbol]
        realised = (price - position.avg_cost) * qty
        position.remove(qty)
        if position.qty == 0:
            del self.positions[symbol]
        self.cash += qty * price - self.fee_per_trade
        self.realised_pnl += realised
        return self._record(Trade(day, "SELL", symbol, qty, price, self.fee_per_trade, realised,
                                  tick, note))

    def _record(self, trade: Trade) -> Trade:
        """Log a trade and its fee, then return it."""
        self.fees_paid += trade.fee
        self.trades.append(trade)
        return trade

    def qty_held(self, symbol: str) -> int:
        """Shares held of `symbol` (0 if none)."""
        if symbol in self.positions:
            return self.positions[symbol].qty
        return 0

    def max_affordable(self, price: float, credit: float = 0.0) -> int:
        """Most whole shares cash (plus `credit`) can buy at `price` after the fee (never below 0)."""
        return max(0, math.floor((self.cash + credit - self.fee_per_trade) / price))

    def loan(self) -> float:
        """Money owed to the broker: negative cash in a margin account (0 if none)."""
        return max(0.0, -self.cash)

    def charge_interest(self, yearly_rate: float, days_per_year: int) -> float:
        """Charge one night's interest on the loan, and return it."""
        interest = self.loan() * yearly_rate / days_per_year
        self.cash -= interest
        self.interest_paid += interest
        return interest

    def market_value(self, prices: dict[str, float]) -> float:
        """Total value of all holdings at `prices`."""
        return sum(pos.market_value(prices[sym]) for sym, pos in self.positions.items())

    def equity(self, prices: dict[str, float]) -> float:
        """Cash plus holdings: what the account is worth right now."""
        return self.cash + self.market_value(prices)

    def unrealised_pnl(self, prices: dict[str, float]) -> float:
        """Paper profit on shares still held."""
        return sum(pos.unrealised_pnl(prices[sym]) for sym, pos in self.positions.items())

    def total_pnl(self, prices: dict[str, float]) -> float:
        """Equity minus starting cash (= realised + unrealised − fees)."""
        return self.equity(prices) - self.starting_cash

    def total_return_pct(self, prices: dict[str, float]) -> float:
        """Total profit/loss as a percentage of starting cash."""
        return self.total_pnl(prices) / self.starting_cash * 100

    def weights(self, prices: dict[str, float]) -> dict[str, float]:
        """Share of equity in each holding plus "CASH"; the values add up to 1.

        With a loan, CASH is negative and the holdings add up to more than 1.
        """
        equity = max(self.equity(prices), 0.01)  # a wiped-out account can't divide by 0
        result = {sym: pos.market_value(prices[sym]) / equity
                  for sym, pos in self.positions.items()}
        result["CASH"] = self.cash / equity
        return result

    def __str__(self) -> str:
        return f"Portfolio: ${self.cash:,.2f} cash, {len(self.positions)} holdings"

    def __repr__(self) -> str:
        return (f"Portfolio(cash={self.cash}, positions={list(self.positions.values())!r}, "
                f"trades={len(self.trades)})")


def check_quantity(qty: int) -> None:
    """Raise InvalidQuantityError unless `qty` is a whole number above 0."""
    # bool is a subclass of int in Python, so rule it out explicitly.
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise InvalidQuantityError("Quantity must be a whole number greater than 0.")
