"""The ETF class: a fund priced as a weighted average of its stocks (C-04)."""


class ETF:
    """An exchange-traded fund whose price is derived entirely from its holdings."""

    def __init__(self, symbol: str, name: str, weights: dict[str, float],
                 base_value: float) -> None:
        """Store the fund's holdings; `weights` maps stock symbol → share of the fund (sum 1)."""
        self.symbol = symbol
        self.name = name
        self.weights = weights
        self.base_value = base_value

    def compute_price(self, prices: dict[str, float],
                      start_prices: dict[str, float]) -> float:
        """Return BASE × Σ wᵢ · (Pᵢ,t / Pᵢ,0), rounded to cents (finance model §3.3).

        Dividing by the day-0 price stops expensive stocks dominating: a weight of
        0.20 always means "20% of the fund at launch".
        """
        total = 0.0
        for symbol, weight in self.weights.items():
            total += weight * prices[symbol] / start_prices[symbol]
        return round(self.base_value * total, 2)

    def contributions(self, prev: dict[str, float], today: dict[str, float],
                      start_prices: dict[str, float]) -> dict[str, float]:
        """Split the ETF's day move into points contributed by each stock (§3.4).

        The formula is linear, so the contributions add up exactly to the ETF change.
        """
        result = {}
        for symbol, weight in self.weights.items():
            change = today[symbol] - prev[symbol]
            result[symbol] = self.base_value * weight * change / start_prices[symbol]
        return result

    def __str__(self) -> str:
        return f"{self.symbol} ({self.name}, {len(self.weights)} holdings)"

    def __repr__(self) -> str:
        return f"ETF({self.symbol!r}, {self.name!r}, {self.weights!r}, {self.base_value})"
