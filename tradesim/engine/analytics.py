"""Pure performance metrics on a list of values (finance model §3.6)."""

import statistics


def daily_returns(values: list[float]) -> list[float]:
    """Return r_t = v_t / v_(t-1) − 1 for each day after the first."""
    return [values[i] / values[i - 1] - 1 for i in range(1, len(values))]


def total_return(values: list[float]) -> float:
    """Return the change from first to last value as a fraction (0.04 = +4%)."""
    return values[-1] / values[0] - 1


def volatility(values: list[float]) -> float:
    """Return the sample standard deviation of daily returns ("typical daily swing").

    Needs at least 2 returns (3 values); with fewer it returns 0.0 instead of raising.
    """
    returns = daily_returns(values)
    if len(returns) < 2:
        return 0.0
    return statistics.stdev(returns)


def worst_day(values: list[float]) -> tuple[float, int]:
    """Return (worst daily return, day it happened); (0.0, 0) if there are no returns."""
    returns = daily_returns(values)
    if not returns:
        return 0.0, 0
    worst = min(returns)
    return worst, returns.index(worst) + 1


def max_drawdown(values: list[float]) -> float:
    """Return the largest fall from a running peak, as a fraction (0.0865 = 8.65%)."""
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak)
    return worst


def value_of(amount: float, values: list[float]) -> list[float]:
    """Return what `amount` invested at values[0] would be worth on each day."""
    return [amount * value / values[0] for value in values]


def moving_average(values: list[float], window: int) -> list[float]:
    """The average of the last `window` values at each point (fewer at the very start)."""
    return [sum(values[max(0, i - window + 1):i + 1]) / (i - max(0, i - window + 1) + 1)
            for i in range(len(values))]


def change(values: list[float], days: int) -> float:
    """Return over the last `days` values as a fraction (or since the start if shorter)."""
    start = values[max(0, len(values) - 1 - days)]
    return values[-1] / start - 1
