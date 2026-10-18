"""Performance metrics: worked examples D and E."""

import pytest

from tradesim.engine import analytics

JUMPY = [100, 102, 99, 101, 104]
CALM = [100, 100.5, 100.2, 100.6, 101.0]


def test_worked_example_d_volatility():
    assert analytics.volatility(JUMPY) == pytest.approx(0.02674, abs=5e-6)
    assert analytics.volatility(CALM) == pytest.approx(0.00369, abs=5e-6)


def test_worked_example_d_total_return():
    assert analytics.total_return(JUMPY) == pytest.approx(0.04)
    assert analytics.total_return(CALM) == pytest.approx(0.01)


def test_worked_example_e_max_drawdown():
    equity = [10000, 10400, 9800, 10100, 9500, 10300]
    assert analytics.max_drawdown(equity) == pytest.approx(900 / 10400)


def test_rising_series_has_no_drawdown():
    assert analytics.max_drawdown([1, 2, 3, 4]) == 0.0


def test_volatility_of_short_series_is_zero():
    assert analytics.volatility([100, 101]) == 0.0


def test_worst_day_reports_return_and_day():
    worst, day = analytics.worst_day(JUMPY)
    assert worst == pytest.approx(99 / 102 - 1)
    assert day == 2


def test_value_of_scales_to_amount():
    assert analytics.value_of(5000, [50, 55, 45]) == pytest.approx([5000, 5500, 4500])


def test_moving_average_uses_what_exists_at_the_start():
    assert analytics.moving_average([2, 4, 6, 8], 2) == [2, 3, 5, 7]
    assert analytics.moving_average([1, 2, 3], 5) == [1, 1.5, 2]


def test_change_over_the_last_days():
    assert analytics.change([100, 110, 121], 1) == pytest.approx(0.10)
    assert analytics.change([100, 110, 121], 9) == pytest.approx(0.21)
