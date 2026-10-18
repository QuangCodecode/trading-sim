"""Intraday sessions (finance model §3.12): how prices move tick by tick inside one day.

The daily model (§3.2) has already fixed every closing price. A session fills in the path
from yesterday's close to today's close with a *Brownian bridge*: a random walk that is
pulled back so it ends exactly at today's close. Every stock shares one market-wide
bridge (scaled by its beta), so the whole board rises and falls together during the day,
and a news story makes the stocks it affects jump at the tick it breaks.

    x[k] = t[k]·(R − J) + J·(k ≥ news) + β·σm·M[k] + σs·E[k]       price[k] = P0·e^x[k]

R = log(P1/P0) is the whole day's move, J the news jump, t[k] the share of the day's
variance used up by tick k, and M, E are bridges that start and end at 0.
"""

import math
import random

from tradesim import config
from tradesim.engine.etf import ETF
from tradesim.engine.stock import Stock

Bar = tuple[float, float, float, float, int]   # (open, high, low, close, volume)


class Session:
    """One trading day: each symbol's price and traded volume at every tick.

    Tick 0 is yesterday's close (the "reference" price); the last tick is today's close.
    """

    def __init__(self, day: int, prices: dict[str, list[float]], volumes: dict[str, list[int]],
                 news_tick: int) -> None:
        """Store the paths; `news_tick` is when the day's news (if any) broke."""
        self.day = day
        self.prices = prices
        self.volumes = volumes
        self.news_tick = news_tick

    def ticks(self) -> int:
        """Number of ticks after the reference price (78 five-minute bars by default)."""
        return len(next(iter(self.prices.values()))) - 1

    def prices_at(self, tick: int) -> dict[str, float]:
        """Every symbol's price at `tick`."""
        return {symbol: path[tick] for symbol, path in self.prices.items()}

    def bar(self, symbol: str, tick: int | None = None) -> Bar:
        """Open, high, low, last price and volume from the opening bell up to `tick`."""
        end = self.ticks() if tick is None else max(1, tick)
        traded = self.prices[symbol][1:end + 1]
        return (traded[0], max(traded), min(traded), traded[-1], sum(self.volumes[symbol][1:end + 1]))

    def scaled(self, day: int, factors: dict[str, float]) -> "Session":
        """This session renamed to `day`, each symbol's prices times its factor (pre-history)."""
        prices = {s: [round(p * factors[s], 2) for p in path] for s, path in self.prices.items()}
        return Session(day, prices, self.volumes, self.news_tick)

    def __repr__(self) -> str:
        return f"Session(day={self.day}, ticks={self.ticks()}, symbols={len(self.prices)})"


def clock_text(tick: int) -> str:
    """The time of day at `tick`: "09:30" at the opening bell, "16:00" at the close."""
    minutes = config.OPENING_BELL + tick * config.MINUTES_PER_TICK
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def variance_clock(ticks: int) -> list[float]:
    """t[k]: share of the day's variance used up by tick k. Tick 1 (the open) gets the
    overnight gap's share, and the rest is spread evenly over the trading day."""
    gap = config.OPEN_GAP_SHARE
    return [0.0, gap] + [gap + (1 - gap) * k / (ticks - 1) for k in range(1, ticks)]


def bridge(rng: random.Random, clock: list[float]) -> list[float]:
    """A random walk whose variance at tick k is clock[k], pulled back so it ends at 0."""
    walk = [0.0]
    for k in range(1, len(clock)):
        walk.append(walk[-1] + rng.gauss(0, 1) * math.sqrt(clock[k] - clock[k - 1]))
    return [w - t * walk[-1] for w, t in zip(walk, clock)]


def activity(k: int, ticks: int, step: float, usual_step: float) -> float:
    """How busy tick k is: more trading near the open and close, and on big moves."""
    middle = 2 * k / ticks - 1          # −1 at the open, 0 at lunch, +1 at the close
    return (1 + config.VOLUME_SMILE * middle ** 2) * (0.5 + abs(step) / usual_step)


def stock_path(stock: Stock, p0: float, p1: float, clock: list[float], market: list[float],
               own: list[float], jump: float, news_tick: int, storm: float) -> list[float]:
    """One stock's prices for the day (tick 0 = p0, last tick = p1 exactly)."""
    move = math.log(p1 / p0)
    beta_sd = stock.beta * config.MARKET_VOL * storm
    own_sd = stock.volatility * storm
    path = [p0]
    for k in range(1, len(clock)):
        news = jump if k >= news_tick else 0.0
        x = clock[k] * (move - jump) + news + beta_sd * market[k] + own_sd * own[k]
        path.append(round(max(config.MIN_PRICE, p0 * math.exp(x)), 2))
    path[-1] = p1
    return path


def volume_path(path: list[float], dollars: float, usual_step: float) -> list[int]:
    """Shares traded at each tick: about `dollars` worth, busier on big moves (tick 0 = 0)."""
    ticks = len(path) - 1
    return [0] + [round(dollars / path[k] * activity(k, ticks, math.log(path[k] / path[k - 1]), usual_step))
                  for k in range(1, len(path))]


def make_session(day: int, rng: random.Random, stocks: dict[str, Stock], etfs: dict[str, ETF],
                 before: dict[str, float], after: dict[str, float], start_prices: dict[str, float],
                 storm: float, jumps: dict[str, float], ticks: int) -> Session:
    """Build every symbol's path for `day` from yesterday's (`before`) to today's (`after`) closes.

    `jumps` maps a stock to the log-size of the news shock it gets at the news tick.
    Draw order is fixed (news tick, market bridge, then stocks sorted) so a seed always
    gives the same session.
    """
    clock = variance_clock(ticks)
    news_tick = rng.randint(1, ticks - 1)
    market = bridge(rng, clock)
    usual = math.sqrt(1 / ticks)        # a typical tick's share of a 1-σ daily move
    dollars = config.TICK_DOLLAR_VOLUME * config.TICKS_PER_DAY / ticks   # same daily volume at any tick size
    prices, volumes = {}, {}
    for symbol in sorted(stocks):
        stock = stocks[symbol]
        own = bridge(rng, clock)
        prices[symbol] = stock_path(stock, before[symbol], after[symbol], clock, market, own,
                                    jumps.get(symbol, 0.0), news_tick, storm)
        day_sd = math.hypot(stock.beta * config.MARKET_VOL, stock.volatility) * storm
        volumes[symbol] = volume_path(prices[symbol], dollars, day_sd * usual)
    for symbol, etf in etfs.items():
        prices[symbol] = [etf.compute_price({s: prices[s][k] for s in etf.weights}, start_prices)
                          for k in range(ticks + 1)]
        volumes[symbol] = volume_path(prices[symbol], dollars * config.ETF_VOLUME_SHARE,
                                      config.MARKET_VOL * storm * usual)
    return Session(day, prices, volumes, news_tick)


def order_book(rng: random.Random, last: float, tick_volume: int) -> tuple[list, list]:
    """Three bid and three ask levels around `last`: ([(price, shares)…], […]).

    Cosmetic, like the depth on a real price board: trades always fill at the last price.
    """
    step = max(0.01, round(last * config.BOOK_STEP, 2))
    size = max(100, tick_volume)
    bids = [(round(last - step * (i + 1), 2), int(size * rng.uniform(0.3, 1.6))) for i in range(3)]
    asks = [(round(last + step * (i + 1), 2), int(size * rng.uniform(0.3, 1.6))) for i in range(3)]
    return bids, asks
