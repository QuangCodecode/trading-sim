"""The end-of-game report: a letter grade against the market, and who is in the spotlight.

Pure logic only. The web page draws it (webapp/api.py hands over the numbers).
"""

from tradesim import config
from tradesim.engine import analytics
from tradesim.engine.game import Game


def grade(game: Game) -> tuple[str, str]:
    """A letter grade comparing the player with simply holding the whole market."""
    account, prices = game.portfolio, game.current_prices()
    if not account.trades:
        return "–", "You haven't invested yet. Cash is safe, but it never grows."
    mine = account.total_return_pct(prices) / 100
    history = game.market.history(game.market.index_symbol(), 0, game.day)
    calmer = analytics.max_drawdown(game.equity_history) <= analytics.max_drawdown(history)
    if mine > analytics.total_return(history) + config.BEAT_MARGIN:
        if mine <= 0:
            return "B", "You lost money, but clearly less than the market. That's skill in a falling market."
        if calmer:
            return "A+", "You beat the whole market AND took less risk. Superb."
        return "A", "You beat the whole market. Check the drawdown to see the risk you took."
    if mine > 0:
        return "B", "In profit, but simply holding the whole market would have done better."
    if mine > config.GRADE_SMALL_LOSS:
        return "C", "A small loss. Markets go down too; what matters is not panicking."
    return "D", "A big loss. Look at the Coach tips and the What-if Replay to see other strategies."


def best_and_worst(game: Game) -> tuple[tuple[str, float], tuple[str, float]] | None:
    """((symbol, % return), (symbol, % return)) of the best and worst open holding, or None."""
    prices = game.current_prices()
    returns = {s: (prices[s] / p.avg_cost - 1) * 100 for s, p in game.portfolio.positions.items()}
    if not returns:
        return None
    best = max(returns, key=returns.get)
    worst = min(returns, key=returns.get)
    return (best, returns[best]), (worst, returns[worst])
