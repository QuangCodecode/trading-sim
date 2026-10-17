"""The Trade class: one line in the trade log."""


class Trade:
    """A completed buy or sell. Trades are never changed after they are created."""

    _next_id = 1  # class variable: shared by every Trade, so each one gets a unique id

    def __init__(self, day: int, side: str, symbol: str, qty: int, price: float,
                 fee: float, realised_pnl: float = 0.0) -> None:
        """Record a trade; `side` is "BUY" or "SELL"; `realised_pnl` is set for sells."""
        self.trade_id = Trade._next_id
        Trade._next_id += 1
        self.day = day
        self.side = side
        self.symbol = symbol
        self.qty = qty
        self.price = price
        self.fee = fee
        self.realised_pnl = realised_pnl

    def value(self) -> float:
        """Shares × price, before the fee."""
        return self.qty * self.price

    def __str__(self) -> str:
        return (f"Day {self.day}: {self.side} {self.qty} {self.symbol} @ ${self.price:,.2f}"
                f" (fee ${self.fee:,.2f})")

    def __repr__(self) -> str:
        return (f"Trade(id={self.trade_id}, day={self.day}, side={self.side!r}, "
                f"symbol={self.symbol!r}, qty={self.qty}, price={self.price}, fee={self.fee})")
