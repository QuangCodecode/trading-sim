"""The Stock class: fixed facts about one simulated company."""


class Stock:
    """One tradable company and the parameters of its random price path."""

    def __init__(self, symbol: str, name: str, sector: str,
                 start_price: float, drift: float, volatility: float) -> None:
        """Store the stock's identity and daily drift/volatility (see finance model §3.2)."""
        self.symbol = symbol
        self.name = name
        self.sector = sector
        self.start_price = start_price
        self.drift = drift
        self.volatility = volatility

    def __str__(self) -> str:
        return f"{self.symbol} ({self.name}, {self.sector})"

    def __repr__(self) -> str:
        return (f"Stock({self.symbol!r}, {self.name!r}, {self.sector!r}, "
                f"{self.start_price}, {self.drift}, {self.volatility})")
