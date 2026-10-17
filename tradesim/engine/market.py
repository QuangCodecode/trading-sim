"""The Market class: generates and serves the whole price history from one seed."""

import random

from tradesim import config
from tradesim.engine.errors import UnknownSymbolError, TradeSimError
from tradesim.engine.etf import ETF
from tradesim.engine.stock import Stock


class Market:
    """Every price for days 0..num_days, pre-generated so the same seed gives the same market."""

    def __init__(self, stocks: dict[str, Stock], etfs: dict[str, ETF], seed: int,
                 num_days: int, stock_prices: dict[str, list[float]] | None = None) -> None:
        """Generate (or accept) stock prices for every day, then derive ETF prices.

        `stock_prices` is only passed by `from_prices` so tests can inject exact paths.
        """
        self.stocks = stocks
        self.etfs = etfs
        self.seed = seed
        self.num_days = num_days
        self._rng = random.Random(seed)
        self._events: dict[int, list] = {}
        if stock_prices is None:
            stock_prices = self._generate_stock_prices()
        self._history = dict(stock_prices)
        for symbol, etf in etfs.items():
            self._history[symbol] = self._etf_history(etf)

    @staticmethod
    def from_prices(stocks: dict[str, Stock], etfs: dict[str, ETF],
                    prices: dict[str, list[float]]) -> "Market":
        """Build a market from known stock price lists (ETF prices still use the real formula)."""
        num_days = len(next(iter(prices.values()))) - 1
        return Market(stocks, etfs, seed=0, num_days=num_days, stock_prices=prices)

    def _generate_stock_prices(self) -> dict[str, list[float]]:
        """Run the factor model of finance model §3.2 for every day."""
        prices = {symbol: [stock.start_price] for symbol, stock in self.stocks.items()}
        sectors = sorted({stock.sector for stock in self.stocks.values()})
        for _day in range(1, self.num_days + 1):
            # Fixed draw order (market, sorted sectors, sorted stocks) keeps runs reproducible.
            market_move = self._rng.gauss(0, config.MARKET_VOL)
            sector_moves = {name: self._rng.gauss(0, config.SECTOR_VOL) for name in sectors}
            for symbol in sorted(self.stocks):
                stock = self.stocks[symbol]
                noise = stock.volatility * self._rng.gauss(0, 1)
                daily_return = stock.drift + market_move + sector_moves[stock.sector] + noise
                prices[symbol].append(next_price(prices[symbol][-1], daily_return))
        return prices

    def _etf_history(self, etf: ETF) -> list[float]:
        """Price the ETF on every day from its holdings' prices."""
        return [etf.compute_price(self.stock_prices_on(day), self.stock_prices_on(0))
                for day in range(self.num_days + 1)]

    def symbols(self) -> list[str]:
        """All tradable symbols: stocks first, then ETFs."""
        return list(self.stocks) + list(self.etfs)

    def is_etf(self, symbol: str) -> bool:
        """True if `symbol` is an ETF."""
        return symbol in self.etfs

    def name_of(self, symbol: str) -> str:
        """The display name of a stock or ETF."""
        self._check_symbol(symbol)
        if self.is_etf(symbol):
            return self.etfs[symbol].name
        return self.stocks[symbol].name

    def price(self, symbol: str, day: int) -> float:
        """The price of `symbol` on `day`."""
        self._check_symbol(symbol)
        self._check_day(day)
        return self._history[symbol][day]

    def stock_prices_on(self, day: int) -> dict[str, float]:
        """Prices of the stocks only (not ETFs) on `day`."""
        return {symbol: self._history[symbol][day] for symbol in self.stocks}

    def prices_on(self, day: int) -> dict[str, float]:
        """Prices of every symbol on `day`."""
        self._check_day(day)
        return {symbol: self._history[symbol][day] for symbol in self.symbols()}

    def history(self, symbol: str, start: int, end: int) -> list[float]:
        """Prices of `symbol` from day `start` to day `end`, inclusive."""
        self._check_symbol(symbol)
        self._check_day(start)
        self._check_day(end)
        return self._history[symbol][start:end + 1]

    def events_on(self, day: int) -> list:
        """News events that happened on `day` (empty list if none)."""
        return self._events.get(day, [])

    def daily_change_pct(self, symbol: str, day: int) -> float:
        """Percentage change from the previous day (0.0 on day 0)."""
        if day == 0:
            return 0.0
        return (self.price(symbol, day) / self.price(symbol, day - 1) - 1) * 100

    def _check_symbol(self, symbol: str) -> None:
        """Raise UnknownSymbolError if `symbol` is not traded here."""
        if symbol not in self._history:
            raise UnknownSymbolError(
                f"{symbol} is not a tradable symbol. Try: market")

    def _check_day(self, day: int) -> None:
        """Raise TradeSimError if `day` is outside 0..num_days."""
        if not 0 <= day <= self.num_days:
            raise TradeSimError(f"Day {day} is outside 0..{self.num_days}")

    def __str__(self) -> str:
        return f"Market of {len(self.symbols())} symbols over {self.num_days} days (seed {self.seed})"

    def __repr__(self) -> str:
        return f"Market(seed={self.seed}, num_days={self.num_days}, symbols={self.symbols()!r})"


def next_price(previous: float, daily_return: float) -> float:
    """Apply one day's return, clamped to ±MAX_DAILY_MOVE, floored at MIN_PRICE, in cents."""
    clamped = max(-config.MAX_DAILY_MOVE, min(config.MAX_DAILY_MOVE, daily_return))
    return round(max(config.MIN_PRICE, previous * (1 + clamped)), 2)
