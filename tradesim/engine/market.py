"""The Market class: generates and serves the whole price history from one seed."""

import math
import random

from tradesim import config
from tradesim.engine.errors import UnknownSymbolError, TradeSimError
from tradesim.engine.etf import ETF
from tradesim.engine.events import MarketEvent, generate_events
from tradesim.engine.intraday import Bar, Session, make_session, order_book
from tradesim.engine.regime import FLAT_MODEL, Regime, RegimeModel
from tradesim.engine.stock import Stock


class Market:
    """Every price for days 0..num_days, pre-generated so the same seed gives the same market."""

    def __init__(self, stocks: dict[str, Stock], etfs: dict[str, ETF], seed: int,
                 num_days: int, event_templates: list[dict] | None = None,
                 stock_prices: dict[str, list[float]] | None = None,
                 regime_model: RegimeModel | None = None, prehistory_days: int = 0,
                 ticks_per_day: int = config.TICKS_PER_DAY) -> None:
        """Generate the market's moods, news events and stock prices, then derive ETF prices.

        `event_templates` are the rows of the events table (None = no news) and `regime_model`
        comes from the regimes tables (None = one calm mood, no trends).
        `stock_prices` is only passed by `from_prices` so tests can inject exact paths.
        `prehistory_days` adds that many days of price history before day 0 (for charts).
        """
        self.stocks = stocks
        self.etfs = etfs
        self.seed = seed
        self.num_days = num_days
        self.regime_model = regime_model or FLAT_MODEL
        self._rng = random.Random(seed)
        self._events = generate_events(event_templates or [], seed, num_days)
        self.regime_path = self.regime_model.generate(seed, num_days)
        self._storm = [self.regime_on(0).vol_scale] * (num_days + 1)
        if stock_prices is None:
            stock_prices = self._generate_stock_prices()
        self._history = dict(stock_prices)
        for symbol, etf in etfs.items():
            self._history[symbol] = self._etf_history(etf)
        self.ticks_per_day = ticks_per_day
        self._session: Session | None = None     # only the latest session is kept (memory)
        self._bars: dict[int, dict[str, Bar]] = {}
        self._make_prehistory(prehistory_days)

    def _make_prehistory(self, days: int) -> None:
        """Days -days..-1 come from a warm-up market (own seed), rescaled to meet day 0.

        Scaling every price by (day-0 price / warm-up's last price) keeps the warm-up's
        shape and makes the history join today's prices without a jump.
        """
        self.first_day = -days
        self._before: dict[str, list[float]] = {symbol: [] for symbol in self._history}
        self.warmup = None
        if days == 0:
            return
        self.warmup = Market(self.stocks, self.etfs, self.seed + config.PREHISTORY_SEED_OFFSET,
                             days, regime_model=self.regime_model, ticks_per_day=config.PREHISTORY_TICKS)
        self._scale = {symbol: path[0] / self.warmup._history[symbol][-1]
                       for symbol, path in self._history.items()}
        for symbol, factor in self._scale.items():
            self._before[symbol] = [round(p * factor, 2) for p in self.warmup._history[symbol][:-1]]

    @staticmethod
    def from_prices(stocks: dict[str, Stock], etfs: dict[str, ETF],
                    prices: dict[str, list[float]]) -> "Market":
        """Build a market from known stock price lists (ETF prices still use the real formula)."""
        num_days = len(next(iter(prices.values()))) - 1
        return Market(stocks, etfs, seed=0, num_days=num_days, stock_prices=prices)

    def add_event(self, event: MarketEvent) -> None:
        """Attach a news event to its day without changing prices (used by tests)."""
        self._events.setdefault(event.day, []).append(event)

    def _generate_stock_prices(self) -> dict[str, list[float]]:
        """Run the regime + factor model of finance model §3.2 for every day."""
        prices = {symbol: [stock.start_price] for symbol, stock in self.stocks.items()}
        # Each company gets its own "story" for this game: a good year or a bad one.
        stories = {s: self._rng.gauss(0, config.STORY_SPREAD) for s in sorted(self.stocks)}
        nervousness, surprise = 1.0, 0.0
        for day in range(1, self.num_days + 1):
            regime = self.regime_on(day)
            # Volatility memory (GARCH): a big surprise yesterday makes today stormier.
            nervousness = (1 - config.STORM_KICK - config.STORM_MEMORY
                           + config.STORM_KICK * surprise ** 2 + config.STORM_MEMORY * nervousness)
            self._storm[day] = regime.vol_scale * math.sqrt(nervousness)
            surprise = self._rng.gauss(0, 1)
            returns = self._day_returns(day, regime, surprise, stories)
            for symbol, daily_return in returns.items():
                prices[symbol].append(next_price(prices[symbol][-1], daily_return))
        return prices

    def _day_returns(self, day: int, regime: Regime, surprise: float,
                     stories: dict[str, float]) -> dict[str, float]:
        """Every stock's return on `day`: market + sector + own noise + news (§3.2)."""
        storm = self._storm[day]
        market_move = regime.drift + config.MARKET_VOL * storm * surprise
        # Fixed draw order (sorted sectors, then sorted stocks) keeps runs reproducible.
        sector_moves = {name: self._rng.gauss(0, config.SECTOR_VOL * storm)
                        for name in self.sectors()}
        returns = {}
        for symbol in sorted(self.stocks):
            stock = self.stocks[symbol]
            noise = stock.volatility * storm * self._rng.gauss(0, 1)
            shock = sum(e.shock for e in self.events_on(day) if e.affects(stock))
            returns[symbol] = (stock.drift + stories[symbol] + stock.beta * market_move
                               + sector_moves[stock.sector] + noise + shock)
        return returns

    def _etf_history(self, etf: ETF) -> list[float]:
        """Price the ETF on every day from its holdings' prices."""
        return [etf.compute_price(self.stock_prices_on(day), self.stock_prices_on(0))
                for day in range(self.num_days + 1)]

    def symbols(self) -> list[str]:
        """All tradable symbols: stocks first, then ETFs."""
        return list(self.stocks) + list(self.etfs)

    def index_symbol(self) -> str:
        """The fund that stands for "the whole market" (MKT100), or the first ETF if it's missing."""
        return config.MARKET_INDEX if config.MARKET_INDEX in self.etfs else next(iter(self.etfs))

    def sectors(self) -> list[str]:
        """Every sector name, sorted."""
        return sorted({stock.sector for stock in self.stocks.values()})

    def regime_on(self, day: int) -> Regime:
        """The market's hidden mood on `day` (the player only learns it afterwards)."""
        return self.regime_model.regimes[self.regime_path[day]]

    def fear_index(self, day: int) -> float:
        """A VIX-style fear gauge: the market's expected yearly swing in %, about 13 when calm."""
        self._check_day(day)
        return self._storm[day] * config.MARKET_VOL * math.sqrt(config.TRADING_DAYS_PER_YEAR) * 100

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
        """The price of `symbol` on `day` (a negative day is in the pre-game history)."""
        self._check_symbol(symbol)
        self._check_day(day)
        if day < 0:
            return self._before[symbol][day]
        return self._history[symbol][day]

    def stock_prices_on(self, day: int) -> dict[str, float]:
        """Prices of the stocks only (not ETFs) on `day` (0 or later)."""
        return {symbol: self._history[symbol][day] for symbol in self.stocks}

    def prices_on(self, day: int) -> dict[str, float]:
        """Prices of every symbol on `day`."""
        return {symbol: self.price(symbol, day) for symbol in self.symbols()}

    def history(self, symbol: str, start: int, end: int) -> list[float]:
        """Prices of `symbol` from day `start` to day `end`, inclusive (start may be negative)."""
        self._check_symbol(symbol)
        self._check_day(start)
        self._check_day(end)
        if start >= 0:
            return self._history[symbol][start:end + 1]
        offset = len(self._before[symbol])
        return (self._before[symbol] + self._history[symbol])[start + offset:end + offset + 1]

    def session(self, day: int) -> Session:
        """The tick-by-tick session that ended with `day`'s close (days 1.. or the history)."""
        if not self.first_day < day <= self.num_days:
            raise TradeSimError(f"There is no trading session for day {day}")
        if self._session is None or self._session.day != day:
            self._session = self._build_session(day)
        return self._session

    def _build_session(self, day: int) -> Session:
        """Bridge from yesterday's to today's closes, with a fixed RNG for this day (§3.12)."""
        if day <= 0:
            return self.warmup.session(day - self.first_day).scaled(day, self._scale)
        rng = random.Random(self.seed * config.DAY_SEED_STRIDE + day + config.INTRADAY_SEED_OFFSET)
        jumps = {}
        for event in self.events_on(day):
            for symbol, stock in self.stocks.items():
                if event.affects(stock):
                    jumps[symbol] = jumps.get(symbol, 0.0) + math.log(1 + event.shock)
        return make_session(day, rng, self.stocks, self.etfs, self.stock_prices_on(day - 1),
                            self.stock_prices_on(day), self.stock_prices_on(0), self._storm[day],
                            jumps, self.ticks_per_day)

    def bar(self, symbol: str, day: int) -> Bar:
        """(open, high, low, close, volume) of a finished day, worked out once and remembered."""
        self._check_symbol(symbol)
        if day not in self._bars:
            if day == self.first_day:
                close = self.price(symbol, day)
                return close, close, close, close, 0
            session = self._build_session(day)    # not cached, so the live session stays cached
            self._bars[day] = {s: session.bar(s) for s in session.prices}
        return self._bars[day][symbol]

    def order_books(self, day: int, tick: int) -> dict[str, tuple[list, list]]:
        """Every symbol's bid and ask levels at (`day`, `tick`); the same every time it's asked."""
        session = self.session(day)
        rng = random.Random((self.seed * config.DAY_SEED_STRIDE + day) * 1000 + tick)
        return {symbol: order_book(rng, session.prices[symbol][tick], session.volumes[symbol][tick])
                for symbol in sorted(session.prices)}

    def events_on(self, day: int) -> list[MarketEvent]:
        """News events that happened on `day` (empty list if none)."""
        return self._events.get(day, [])

    def daily_change_pct(self, symbol: str, day: int) -> float:
        """Percentage change from the previous day (0.0 on the first day there is)."""
        if day == self.first_day:
            return 0.0
        return (self.price(symbol, day) / self.price(symbol, day - 1) - 1) * 100

    def _check_symbol(self, symbol: str) -> None:
        """Raise UnknownSymbolError if `symbol` is not traded here."""
        if symbol not in self._history:
            raise UnknownSymbolError(
                f"{symbol} is not a tradable symbol. Try: market")

    def _check_day(self, day: int) -> None:
        """Raise TradeSimError if `day` is outside first_day..num_days."""
        if not self.first_day <= day <= self.num_days:
            raise TradeSimError(f"Day {day} is outside {self.first_day}..{self.num_days}")

    def __str__(self) -> str:
        return f"Market of {len(self.symbols())} symbols over {self.num_days} days (seed {self.seed})"

    def __repr__(self) -> str:
        return f"Market(seed={self.seed}, num_days={self.num_days}, symbols={self.symbols()!r})"


def next_price(previous: float, daily_return: float) -> float:
    """Apply one day's return, clamped to ±MAX_DAILY_MOVE, floored at MIN_PRICE, in cents."""
    clamped = max(-config.MAX_DAILY_MOVE, min(config.MAX_DAILY_MOVE, daily_return))
    return round(max(config.MIN_PRICE, previous * (1 + clamped)), 2)
