"""Shared pytest fixtures: the real universe, a tiny hand-made market, a fresh portfolio."""

import pytest

from tradesim import config
from tradesim.engine.etf import ETF
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.engine.stock import Stock
from tradesim.loader import load_universe


@pytest.fixture
def universe():
    """(stocks, etfs) loaded from the real data/universe.json."""
    return load_universe(config.UNIVERSE_PATH)


@pytest.fixture
def tiny_market():
    """3 stocks + 1 ETF over 6 days of known prices. JUMP is wild, the other two are calm."""
    stocks = {
        "JUMP": Stock("JUMP", "Jumpy Co", "Tech", 100.0, 0.0, 0.05),
        "CALM": Stock("CALM", "Calm Co", "Consumer", 50.0, 0.0, 0.01),
        "OIL": Stock("OIL", "Oil Co", "Energy", 20.0, 0.0, 0.01),
    }
    etfs = {"FUND": ETF("FUND", "Tiny Fund", {"JUMP": 0.2, "CALM": 0.4, "OIL": 0.4}, 100.0)}
    prices = {
        "JUMP": [100.0, 110.0, 90.0, 105.0, 80.0, 100.0],
        "CALM": [50.0, 50.5, 50.2, 50.6, 50.4, 51.0],
        "OIL": [20.0, 20.1, 20.0, 20.2, 20.1, 20.3],
    }
    return Market.from_prices(stocks, etfs, prices)


@pytest.fixture
def portfolio():
    """A fresh $10,000 account with a $1 fee."""
    return Portfolio(starting_cash=10_000.0, fee_per_trade=1.0)


@pytest.fixture
def game(tiny_market, portfolio):
    """A game on the tiny market, starting at day 0."""
    return Game(tiny_market, portfolio)
