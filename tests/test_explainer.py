"""E-02 Explainer and event scopes: worked example B from docs/03 §3.4."""

import pytest

from tradesim.education import explainer
from tradesim.engine.events import MarketEvent
from tradesim.engine.market import Market

START = {"AAPL": 180.0, "NVDA": 120.0, "XOM": 110.0, "CVX": 150.0, "KO": 60.0, "WMT": 70.0}
DAY_1 = {"AAPL": 189.0, "NVDA": 108.0, "XOM": 110.0, "CVX": 157.5, "KO": 63.0, "WMT": 70.0}
DAY_2 = dict(DAY_1, AAPL=173.88, NVDA=99.36)
CHIP_CURBS = MarketEvent(2, "Chip export curbs hit tech stocks", "", "sector", "Tech", -0.08)


@pytest.fixture
def example_b(universe):
    stocks, etfs = universe
    prices = {s: [START[s], DAY_1[s], DAY_2[s]] for s in START}
    market = Market.from_prices(stocks, etfs, prices)
    market.add_event(CHIP_CURBS)
    return market


def test_breakdown_matches_worked_example_b(example_b):
    rows = {row.symbol: row for row in explainer.etf_move_breakdown(example_b, "MIX6", 2)}
    assert rows["AAPL"].points == pytest.approx(-1.68)
    assert rows["NVDA"].points == pytest.approx(-1.08)
    assert rows["KO"].points == pytest.approx(0.0)
    assert sum(r.points for r in rows.values()) == pytest.approx(-2.76)


def test_tech_share_going_into_the_day_is_34_percent(example_b):
    shares = explainer.effective_shares(example_b, "MIX6", 1)
    assert shares["AAPL"] + shares["NVDA"] == pytest.approx((0.21 + 0.135) / 1.01)


def test_explainer_sentence_uses_the_real_numbers(example_b):
    sentence = explainer.explain_event(example_b, CHIP_CURBS, "MIX6")
    assert "34%" in sentence
    assert "-2.73%" in sentence
    assert "AAPL -8.0% and NVDA -8.0%" in sentence


def test_market_wide_event_says_it_cannot_be_diversified(example_b):
    crash = MarketEvent(2, "Recession fears rattle markets", "", "market", "ALL", -0.03)
    assert "can't be diversified away" in explainer.explain_event(example_b, crash, "MIX6")


def test_position_impact_only_for_held_affected_stocks(example_b, portfolio):
    portfolio.buy("NVDA", 10, 108.0, day=1)
    portfolio.buy("KO", 10, 63.0, day=1)
    impacts = explainer.position_impacts(example_b, portfolio, CHIP_CURBS)
    assert impacts == {"NVDA": pytest.approx(10 * (99.36 - 108.0))}


def test_scopes_affect_only_their_targets(universe):
    stocks, _etfs = universe
    stock_event = MarketEvent(1, "", "", "stock", "NVDA", 0.1)
    sector_event = MarketEvent(1, "", "", "sector", "Energy", 0.1)
    market_event = MarketEvent(1, "", "", "market", "ALL", 0.1)
    assert [s for s in stocks if stock_event.affects(stocks[s])] == ["NVDA"]
    assert [s for s in stocks if sector_event.affects(stocks[s])] == ["XOM", "CVX"]
    assert all(market_event.affects(stock) for stock in stocks.values())
