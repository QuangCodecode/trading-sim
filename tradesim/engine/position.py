"""The Position class: how many shares of one symbol you hold, and what they cost."""


class Position:
    """Shares held in one symbol, using the average-cost method (finance model §3.5)."""

    def __init__(self, symbol: str, qty: int = 0, avg_cost: float = 0.0) -> None:
        """Start a position; a new one usually has no shares yet."""
        self.symbol = symbol
        self.qty = qty
        self.avg_cost = avg_cost

    def add(self, qty: int, price: float) -> None:
        """Buy more shares: the average cost becomes the blend of old and new."""
        total_cost = self.qty * self.avg_cost + qty * price
        self.qty += qty
        self.avg_cost = total_cost / self.qty

    def remove(self, qty: int) -> None:
        """Sell shares; the average cost of the remaining shares does not change."""
        self.qty -= qty

    def market_value(self, price: float) -> float:
        """What the shares are worth at `price`."""
        return self.qty * price

    def unrealised_pnl(self, price: float) -> float:
        """Profit (or loss) if you sold everything at `price`, ignoring fees."""
        return (price - self.avg_cost) * self.qty

    def __str__(self) -> str:
        return f"{self.qty} {self.symbol} @ avg ${self.avg_cost:,.2f}"

    def __repr__(self) -> str:
        return f"Position({self.symbol!r}, qty={self.qty}, avg_cost={self.avg_cost})"
