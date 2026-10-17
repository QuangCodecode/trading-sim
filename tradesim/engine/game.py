"""The Game class: ties the market, the portfolio and the clock together (C-03)."""

from tradesim.engine.errors import GameOverError, InvalidQuantityError
from tradesim.engine.events import MarketEvent
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.engine.trade import Trade


class Game:
    """One play-through. The player only ever sees prices up to `day` (no peeking ahead)."""

    def __init__(self, market: Market, portfolio: Portfolio) -> None:
        """Start on day 0 with an equity snapshot of the opening position."""
        self.market = market
        self.portfolio = portfolio
        self.day = 0
        self.equity_history = [self.equity()]

    def is_over(self) -> bool:
        """True once the final day has been reached."""
        return self.day >= self.market.num_days

    def days_left(self) -> int:
        """Trading days remaining after today."""
        return self.market.num_days - self.day

    def advance(self, days: int = 1) -> list[MarketEvent]:
        """Move forward `days` (capped at the end) and return the news events passed."""
        if self.is_over():
            raise GameOverError("The game has ended. Type report or quit")
        if days <= 0:
            raise InvalidQuantityError("Days must be a whole number greater than 0.")
        events = []
        for _ in range(min(days, self.days_left())):
            self.day += 1
            self.equity_history.append(self.equity())
            events.extend(self.market.events_on(self.day))
        return events

    def buy(self, symbol: str, qty: int) -> Trade:
        """Buy `qty` shares of `symbol` at today's price."""
        price = self._price_for_trade(symbol)
        return self.portfolio.buy(symbol, qty, price, self.day)

    def sell(self, symbol: str, qty: int) -> Trade:
        """Sell `qty` shares of `symbol` at today's price."""
        price = self._price_for_trade(symbol)
        return self.portfolio.sell(symbol, qty, price, self.day)

    def max_buy(self, symbol: str) -> int:
        """Most shares of `symbol` the player can afford today."""
        return self.portfolio.max_affordable(self.market.price(symbol, self.day))

    def _price_for_trade(self, symbol: str) -> float:
        """Today's price, after checking the game is still running and the symbol exists."""
        if self.is_over():
            raise GameOverError("The game has ended. Type report or quit")
        return self.market.price(symbol, self.day)

    def current_prices(self) -> dict[str, float]:
        """Today's price for every symbol."""
        return self.market.prices_on(self.day)

    def equity(self) -> float:
        """The portfolio's value at today's prices."""
        return self.portfolio.equity(self.current_prices())

    def __str__(self) -> str:
        return f"Day {self.day} / {self.market.num_days}, equity ${self.equity():,.2f}"

    def __repr__(self) -> str:
        return f"Game(day={self.day}, market={self.market!r}, portfolio={self.portfolio!r})"
