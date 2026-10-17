"""Portfolio accounting: worked example C, the P&L invariant and every rejection rule."""

import random

import pytest

from tradesim.engine.errors import (InsufficientCashError, InsufficientSharesError,
                                    InvalidQuantityError)
from tradesim.engine.portfolio import Portfolio


def test_worked_example_c_step_by_step(portfolio):
    portfolio.buy("AAPL", 10, 180.0, day=0)
    assert portfolio.cash == pytest.approx(8_199.00)
    portfolio.buy("AAPL", 5, 190.0, day=1)
    assert portfolio.cash == pytest.approx(7_248.00)
    assert portfolio.positions["AAPL"].avg_cost == pytest.approx(183.3333, abs=1e-4)
    portfolio.sell("AAPL", 6, 200.0, day=2)
    assert portfolio.cash == pytest.approx(8_447.00)
    assert portfolio.realised_pnl == pytest.approx(100.00)
    prices = {"AAPL": 195.0}
    assert portfolio.unrealised_pnl(prices) == pytest.approx(105.00)
    assert portfolio.equity(prices) == pytest.approx(10_202.00)
    assert portfolio.total_pnl(prices) == pytest.approx(202.00)
    assert portfolio.fees_paid == pytest.approx(3.00)


def test_invariant_holds_after_100_random_trades():
    rng = random.Random(9001)
    account = Portfolio(10_000.0, 1.0)
    prices = {"A": 50.0, "B": 120.0, "C": 8.0}
    for day in range(100):
        prices = {s: round(p * (1 + rng.uniform(-0.05, 0.05)), 2) for s, p in prices.items()}
        symbol = rng.choice(list(prices))
        held = account.qty_held(symbol)
        if held and rng.random() < 0.5:
            account.sell(symbol, rng.randint(1, held), prices[symbol], day)
        elif account.max_affordable(prices[symbol]) > 0:
            account.buy(symbol, rng.randint(1, account.max_affordable(prices[symbol])),
                        prices[symbol], day)
        parts = account.realised_pnl + account.unrealised_pnl(prices) - account.fees_paid
        assert account.total_pnl(prices) == pytest.approx(parts, abs=1e-6)
        assert account.cash >= 0


def test_buy_with_exactly_enough_cash_leaves_zero(portfolio):
    portfolio.buy("X", 1, 9_999.0, day=0)
    assert portfolio.cash == pytest.approx(0.0)


def test_buy_rejects_when_cash_short_by_one_cent(portfolio):
    with pytest.raises(InsufficientCashError, match="Max you can buy: 0"):
        portfolio.buy("X", 1, 9_999.01, day=0)
    assert portfolio.cash == 10_000.0 and portfolio.trades == []


@pytest.mark.parametrize("qty", [0, -3, 2.5, True])
def test_bad_quantity_rejected(portfolio, qty):
    with pytest.raises(InvalidQuantityError):
        portfolio.buy("X", qty, 10.0, day=0)


def test_sell_more_than_held_rejected(portfolio):
    portfolio.buy("X", 5, 10.0, day=0)
    with pytest.raises(InsufficientSharesError, match="hold 5"):
        portfolio.sell("X", 10, 10.0, day=0)


def test_sell_unheld_rejected(portfolio):
    with pytest.raises(InsufficientSharesError):
        portfolio.sell("X", 1, 10.0, day=0)


def test_sell_worth_less_than_fee_rejected(portfolio):
    portfolio.buy("X", 1, 0.5, day=0)
    with pytest.raises(InsufficientCashError):
        portfolio.sell("X", 1, 0.5, day=0)


def test_selling_all_removes_position(portfolio):
    portfolio.buy("X", 5, 10.0, day=0)
    portfolio.sell("X", 5, 12.0, day=1)
    assert "X" not in portfolio.positions


def test_each_trade_logs_one_entry_with_correct_fields(portfolio):
    buy = portfolio.buy("X", 5, 10.0, day=3)
    sell = portfolio.sell("X", 2, 12.0, day=4)
    assert portfolio.trades == [buy, sell]
    assert (sell.day, sell.side, sell.symbol, sell.qty, sell.price, sell.fee) == \
        (4, "SELL", "X", 2, 12.0, 1.0)
    assert sell.realised_pnl == pytest.approx(4.0)
    assert sell.trade_id == buy.trade_id + 1


def test_weights_sum_to_one_including_cash(portfolio):
    portfolio.buy("X", 10, 100.0, day=0)
    portfolio.buy("Y", 20, 50.0, day=0)
    weights = portfolio.weights({"X": 110.0, "Y": 45.0})
    assert sum(weights.values()) == pytest.approx(1.0)
    assert "CASH" in weights
