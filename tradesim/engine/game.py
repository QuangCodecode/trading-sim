"""The Game class: ties the market, the portfolio and the clock together (C-03)."""

from tradesim import config
from tradesim.engine import margin
from tradesim.engine.errors import GameOverError, InvalidQuantityError
from tradesim.engine.events import MarketEvent
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.engine.trade import Trade


class Game:
    """One play-through. The player only ever sees prices up to now (no peeking ahead).

    The clock is (`day`, `tick`): `day` is the last day that has closed, and `tick` is how
    many five-minute ticks of the next day's session have passed (0 = before the bell,
    when prices are still `day`'s closes). The terminal only moves whole days; the web
    app lets the session run tick by tick.
    """

    def __init__(self, market: Market, portfolio: Portfolio, challenge: object = None) -> None:
        """Start on day 0 with an equity snapshot of the opening position."""
        self.reset(market, portfolio, challenge)

    def reset(self, market: Market, portfolio: Portfolio, challenge: object = None) -> None:
        """Throw away the current game and start again (used by `new` and `challenge`).

        `challenge` is the goal being played for (education/challenges.py), or None.
        The last lists remember the player's progress: badges won, commands tried
        (for the "explorer" badges), right/wrong quiz answers and margin calls suffered.
        """
        self.market = market
        self.portfolio = portfolio
        self.challenge = challenge
        self.day = 0
        self.tick = 0
        self.equity_history = [self.equity()]
        self.badges: list[str] = []
        self.commands_used: set[str] = set()
        self.quiz_results: list[bool] = []
        self.margin_calls: list[list[Trade]] = []

    def is_over(self) -> bool:
        """True once the final day has been reached."""
        return self.day >= self.market.num_days

    def days_left(self) -> int:
        """Trading days remaining after today."""
        return self.market.num_days - self.day

    def is_open(self) -> bool:
        """True while a session is running (between the opening and closing bells)."""
        return self.tick > 0

    def step(self, ticks: int = 1) -> list[MarketEvent]:
        """Let the market run `ticks` five-minute ticks, stopping at the closing bell.

        Returns the news that broke during those ticks.
        """
        self._check_running()
        if ticks <= 0:
            raise InvalidQuantityError("Ticks must be a whole number greater than 0.")
        news = []
        for _ in range(ticks):
            self.tick += 1
            if self.tick == self.market.session(self.day + 1).news_tick:
                news.extend(self.market.events_on(self.day + 1))
            if self.tick == self.market.ticks_per_day:
                self._close_day()
                break
            self.check_margin()
        return news

    def advance(self, days: int = 1) -> list[MarketEvent]:
        """Move forward `days` (capped at the end) and return the news events passed.

        A session that is already running counts as the first of those days.
        """
        self._check_running()
        if days <= 0:
            raise InvalidQuantityError("Days must be a whole number greater than 0.")
        events = []
        for _ in range(min(days, self.days_left())):
            # Only a borrower can be margin-called, so only then does every tick matter.
            while self.portfolio.loan() > 0 and self.tick < self.market.ticks_per_day - 1:
                self.tick += 1
                self.check_margin()
            self._close_day()
            events.extend(self.market.events_on(self.day))
        return events

    def _close_day(self) -> None:
        """The closing bell: the day is done, interest is charged, the equity is recorded."""
        self.day += 1
        self.tick = 0
        self.portfolio.charge_interest(config.MARGIN_RATE, config.TRADING_DAYS_PER_YEAR)
        self.check_margin()
        self.equity_history.append(self.equity())

    def check_margin(self) -> list[Trade]:
        """If the account is below maintenance, let the broker sell (and remember it)."""
        prices = self.current_prices()
        if not margin.is_margin_call(self.portfolio, prices):
            return []
        trades = margin.liquidate(self.portfolio, prices, self.day, self.tick)
        self.margin_calls.append(trades)
        return trades

    def set_leverage(self, leverage: int) -> None:
        """Change how much the broker may lend (1 = cash account, no borrowing)."""
        margin.check_new_leverage(self.portfolio, self.current_prices(), leverage)
        self.portfolio.max_leverage = leverage

    def buy(self, symbol: str, qty: int) -> Trade:
        """Buy `qty` shares of `symbol` at the current price (borrowing if allowed)."""
        price = self.price_for_trade(symbol)
        credit = margin.credit(self.portfolio, self.current_prices())
        return self.portfolio.buy(symbol, qty, price, self.day, credit, self.tick)

    def sell(self, symbol: str, qty: int) -> Trade:
        """Sell `qty` shares of `symbol` at the current price."""
        price = self.price_for_trade(symbol)
        return self.portfolio.sell(symbol, qty, price, self.day, self.tick)

    def max_buy(self, symbol: str) -> int:
        """Most shares of `symbol` the player can afford right now (including the loan)."""
        credit = margin.credit(self.portfolio, self.current_prices())
        return self.portfolio.max_affordable(self.price_for_trade(symbol), credit)

    def price_for_trade(self, symbol: str) -> float:
        """The current price, after checking the game is still running and the symbol exists."""
        self._check_running()
        self.market.price(symbol, self.day)          # raises for an unknown symbol
        return self.current_prices()[symbol]

    def _check_running(self) -> None:
        """Raise GameOverError after the final day."""
        if self.is_over():
            raise GameOverError("The game has ended. Type report or quit")

    def current_prices(self) -> dict[str, float]:
        """Every symbol's price right now: the last close, or the live session's tick."""
        if self.tick == 0:
            return self.market.prices_on(self.day)
        return self.market.session(self.day + 1).prices_at(self.tick)

    def equity(self) -> float:
        """The portfolio's value at the current prices."""
        return self.portfolio.equity(self.current_prices())

    def __str__(self) -> str:
        return f"Day {self.day} / {self.market.num_days}, equity ${self.equity():,.2f}"

    def __repr__(self) -> str:
        return f"Game(day={self.day}, tick={self.tick}, market={self.market!r}, portfolio={self.portfolio!r})"
