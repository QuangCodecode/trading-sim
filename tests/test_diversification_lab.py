"""E-01 Diversification Lab."""

import pytest

from tradesim.education import diversification_lab as lab
from tradesim.engine.errors import TradeSimError, UnknownSymbolError


def test_jumpy_stock_swings_harder_than_calm_etf(tiny_market):
    result = lab.compare(tiny_market, "JUMP", "FUND", 0, 5, amount=5000)
    assert result.stock.volatility > result.etf.volatility
    assert any("swung" in line and "harder" in line for line in result.verdict)
    assert result.verdict[-1].startswith("FUND holds 3 companies in 3 sectors")


def test_value_series_starts_at_amount(tiny_market):
    result = lab.compare(tiny_market, "JUMP", "FUND", 0, 5, amount=5000)
    assert result.stock.values[0] == pytest.approx(5000)
    assert result.stock.final_value == pytest.approx(5000)  # JUMP ends where it started


def test_etf_doing_better_gives_diversification_line(tiny_market):
    result = lab.compare(tiny_market, "JUMP", "FUND", 0, 5)
    assert any("did better" in line for line in result.verdict)


def test_lab_needs_five_days(tiny_market):
    with pytest.raises(TradeSimError, match="at least 5 days"):
        lab.compare(tiny_market, "JUMP", "FUND", 0, 4)


def test_unknown_symbol_rejected(tiny_market):
    with pytest.raises(UnknownSymbolError):
        lab.compare(tiny_market, "NOPE", "FUND", 0, 5)


def test_etf_as_stock_and_stock_as_etf_rejected(tiny_market):
    with pytest.raises(TradeSimError, match="already an ETF"):
        lab.compare(tiny_market, "FUND", "FUND", 0, 5)
    with pytest.raises(TradeSimError, match="not an ETF"):
        lab.compare(tiny_market, "JUMP", "CALM", 0, 5)


def test_monte_carlo_is_deterministic_and_etf_loses_big_less_often(universe):
    stocks, etfs = universe
    a = lab.monte_carlo(stocks, etfs, "NVDA", "MIX6", base_seed=42, runs=20)
    b = lab.monte_carlo(stocks, etfs, "NVDA", "MIX6", base_seed=42, runs=20)
    assert a.stock_returns == b.stock_returns
    assert a.big_loss_share(a.etf_returns) <= a.big_loss_share(a.stock_returns)


def test_calm_stock_that_beat_etf_is_not_called_riskier(tiny_market):
    # CALM: smaller daily swings than FUND and a higher return over days 0→5.
    result = lab.compare(tiny_market, "CALM", "FUND", 0, 5)
    assert result.stock.volatility < result.etf.volatility
    assert not any("more risk" in line for line in result.verdict)
    assert any("lab mc CALM" in line for line in result.verdict)
