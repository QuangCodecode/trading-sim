"""The Stock class: fixed facts about one simulated company."""


class Stock:
    """One tradable company and the parameters of its random price path."""

    def __init__(self, symbol: str, name: str, sector: str, start_price: float,
                 drift: float, volatility: float, beta: float = 1.0,
                 description: str = "") -> None:
        """Store the stock's identity and price-model parameters (finance model §3.2).

        `beta` is how strongly the stock follows the whole market: 1.0 moves with it,
        1.5 moves 50% more (aggressive), 0.5 half as much (defensive).
        """
        self.symbol = symbol
        self.name = name
        self.sector = sector
        self.start_price = start_price
        self.drift = drift
        self.volatility = volatility
        self.beta = beta
        self.description = description

    def __str__(self) -> str:
        return f"{self.symbol} ({self.name}, {self.sector})"

    def __repr__(self) -> str:
        return (f"Stock({self.symbol!r}, {self.name!r}, {self.sector!r}, "
                f"{self.start_price}, {self.drift}, {self.volatility}, beta={self.beta})")
