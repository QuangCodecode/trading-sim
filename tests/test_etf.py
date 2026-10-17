"""ETF pricing: worked examples A and B from docs/03-finance-model.md."""

import math

import pytest

START = {"AAPL": 180.0, "NVDA": 120.0, "XOM": 110.0, "CVX": 150.0, "KO": 60.0, "WMT": 70.0}
DAY_T = {"AAPL": 189.0, "NVDA": 108.0, "XOM": 110.0, "CVX": 157.5, "KO": 63.0, "WMT": 70.0}


@pytest.fixture
def mix6(universe):
    _stocks, etfs = universe
    return etfs["MIX6"]


def test_worked_example_a_price_is_101(mix6):
    assert mix6.compute_price(DAY_T, START) == pytest.approx(101.00)


def test_day_zero_equals_base_value(mix6):
    assert mix6.compute_price(START, START) == mix6.base_value


def test_all_stocks_up_10_percent_moves_etf_10_percent(mix6):
    up = {symbol: price * 1.10 for symbol, price in START.items()}
    assert mix6.compute_price(up, START) == pytest.approx(110.00)


def test_worked_example_b_contributions(mix6):
    after = dict(DAY_T, AAPL=173.88, NVDA=99.36)
    parts = mix6.contributions(DAY_T, after, START)
    assert parts["AAPL"] == pytest.approx(-1.68)
    assert parts["NVDA"] == pytest.approx(-1.08)
    assert sum(parts.values()) == pytest.approx(-2.76)
    assert mix6.compute_price(after, START) == pytest.approx(98.24)


def test_stock_at_price_floor_keeps_etf_finite_and_positive(mix6):
    crashed = dict(START, NVDA=1.0)
    price = mix6.compute_price(crashed, START)
    assert math.isfinite(price) and price > 0
