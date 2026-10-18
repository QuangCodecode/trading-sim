"""Intraday sessions (finance model §3.12), pre-game history and the tick clock."""

import random

import pytest

from tradesim import config
from tradesim.engine import intraday
from tradesim.engine.errors import InvalidQuantityError, TradeSimError
from tradesim.engine.events import MarketEvent
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio


@pytest.fixture
def real_market(universe):
    stocks, etfs = universe
    return Market(stocks, etfs, 42, 10, prehistory_days=30)


def test_variance_clock_starts_at_0_ends_at_1_and_only_grows():
    clock = intraday.variance_clock(78)
    assert clock[0] == 0 and clock[1] == config.OPEN_GAP_SHARE and clock[-1] == pytest.approx(1)
    assert len(clock) == 79 and all(a < b for a, b in zip(clock, clock[1:]))


def test_bridge_starts_and_ends_at_zero():
    path = intraday.bridge(random.Random(1), intraday.variance_clock(10))
    assert path[0] == 0 and path[-1] == pytest.approx(0, abs=1e-12) and len(path) == 11


def test_session_runs_from_yesterdays_close_to_todays_close(real_market):
    session = real_market.session(3)
    assert session.ticks() == config.TICKS_PER_DAY
    for symbol in ("NVDA", "KO", "MIX6", "MKT100"):
        assert session.prices[symbol][0] == real_market.price(symbol, 2)
        assert session.prices[symbol][-1] == real_market.price(symbol, 3)


def test_etf_ticks_follow_the_etf_formula(real_market):
    session = real_market.session(2)
    etf = real_market.etfs["MIX6"]
    for tick in (1, 30, 77):
        expected = etf.compute_price(session.prices_at(tick), real_market.stock_prices_on(0))
        assert session.prices["MIX6"][tick] == expected


def test_same_seed_same_session_and_days_differ(universe):
    stocks, etfs = universe
    one, two = Market(stocks, etfs, 7, 5), Market(stocks, etfs, 7, 5)
    assert one.session(4).prices["AAPL"] == two.session(4).prices["AAPL"]
    assert one.session(3).prices["AAPL"][1:-1] != one.session(4).prices["AAPL"][1:-1]


def test_bar_is_open_high_low_close_volume(real_market):
    open_, high, low, close, volume = real_market.bar("NVDA", 4)
    assert low <= min(open_, close) <= max(open_, close) <= high
    assert close == real_market.price("NVDA", 4) and volume > 0


def test_news_jumps_at_its_tick(tiny_market):
    tiny_market.add_event(MarketEvent(2, "Jumpy Co wins big contract", "", "stock", "JUMP", 0.2))
    session = tiny_market.session(2)
    k = session.news_tick
    jump = session.prices["JUMP"][k] / session.prices["JUMP"][k - 1] - 1
    calm = session.prices["CALM"][k] / session.prices["CALM"][k - 1] - 1
    assert jump > 0.1 and abs(calm) < 0.05


def test_prehistory_joins_day_0_without_a_jump(real_market):
    history = real_market.history("NVDA", -30, 0)
    assert len(history) == 31 and history[-1] == 120.0
    assert real_market.price("NVDA", -1) == history[-2]
    assert real_market.history("NVDA", -5, -3) == history[25:28]
    assert real_market.session(0).prices["NVDA"][-1] == 120.0   # day 0 has a session too
    with pytest.raises(TradeSimError):
        real_market.price("NVDA", -31)


def test_market_without_prehistory_starts_at_day_0(tiny_market):
    with pytest.raises(TradeSimError):
        tiny_market.price("JUMP", -1)
    with pytest.raises(TradeSimError):
        tiny_market.session(0)
    assert tiny_market.bar("JUMP", 0) == (100.0, 100.0, 100.0, 100.0, 0)


def test_order_book_brackets_the_last_price(real_market):
    books = real_market.order_books(2, 10)
    bids, asks = books["NVDA"]
    last = real_market.session(2).prices["NVDA"][10]
    assert [p for p, _ in bids] == sorted((p for p, _ in bids), reverse=True)
    assert bids[0][0] < last < asks[0][0] and all(size > 0 for _, size in bids + asks)
    assert real_market.order_books(2, 10) == books                     # same every time
    assert books["KO"][0][0][1] != books["NVDA"][0][0][1] or books["KO"][0][1][1] != books["NVDA"][0][1][1]


def test_step_moves_the_clock_and_prices(game, tiny_market):
    news = game.step(10)
    assert (game.day, game.tick) == (0, 10) and game.is_open() and news == []
    assert game.current_prices()["JUMP"] == tiny_market.session(1).prices["JUMP"][10]


def test_step_stops_at_the_closing_bell(game, tiny_market):
    game.step(5)
    game.step(500)
    assert (game.day, game.tick) == (1, 0)
    assert game.current_prices()["JUMP"] == 110.0 and len(game.equity_history) == 2


def test_step_reports_news_when_it_breaks(game, tiny_market):
    event = MarketEvent(1, "Oil Co strikes oil", "", "stock", "OIL", 0.05)
    tiny_market.add_event(event)
    news_tick = tiny_market.session(1).news_tick
    assert game.step(news_tick - 1) == []
    assert game.step(1) == [event]


def test_step_rejects_zero_ticks(game):
    with pytest.raises(InvalidQuantityError):
        game.step(0)


def test_trade_mid_session_uses_the_tick_price(game, tiny_market):
    game.step(20)
    trade = game.buy("JUMP", 3)
    assert trade.price == tiny_market.session(1).prices["JUMP"][20]
    assert (trade.day, trade.tick) == (0, 20)


def test_next_mid_session_finishes_that_day(game):
    game.step(30)
    game.advance(1)
    assert (game.day, game.tick) == (1, 0)


def test_time_of_tick():
    assert intraday.clock_text(0) == "09:30" and intraday.clock_text(1) == "09:35"
    assert intraday.clock_text(config.TICKS_PER_DAY) == "16:00"


def test_new_game_has_prehistory():
    from tradesim.cli.app import new_game
    game = new_game(3, 20)
    assert game.market.first_day == -config.PREHISTORY_DAYS
    assert isinstance(game.portfolio, Portfolio) and isinstance(game, Game)
