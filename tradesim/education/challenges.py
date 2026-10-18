"""X-01 Challenges: a fixed market (seed) plus goals to reach by the final day.

Each challenge's seed was picked because its hidden story fits (a crash, a bear market,
a tech slump…), so everyone who plays it faces the same market.
"""

from tradesim.engine import analytics
from tradesim.engine.game import Game


class Challenge:
    """One scenario: which market, what you start with, and what counts as winning."""

    def __init__(self, data: dict) -> None:
        """Copy the fields of one entry in data/challenges.json."""
        self.id = data["id"]
        self.title = data["title"]
        self.emoji = data["emoji"]
        self.seed = data["seed"]
        self.days = data["days"]
        self.intro = data["intro"]
        self.goals = data["goals"]
        self.start = data.get("start", [])
        self.lesson = data["lesson"]
        self.story = data.get("story", {})

    def __str__(self) -> str:
        return f"{self.emoji} {self.title}"

    def __repr__(self) -> str:
        return f"Challenge({self.id!r}, seed={self.seed})"


class GoalCheck:
    """One goal: what it asks, where the player is now, and whether that passes."""

    def __init__(self, text: str, now: str, passed: bool) -> None:
        """`now` is the player's current value, e.g. "$9,812.00"."""
        self.text = text
        self.now = now
        self.passed = passed

    def __repr__(self) -> str:
        return f"GoalCheck({self.text!r}, passed={self.passed})"


def symbol_return(game: Game, symbol: str) -> float:
    """What buying `symbol` on day 0 and holding it would have returned by today."""
    return analytics.total_return(game.market.history(symbol, 0, game.day))


def check_goal(game: Game, goal: dict) -> GoalCheck:
    """Measure one goal from data/challenges.json against the game right now."""
    prices, account = game.current_prices(), game.portfolio
    kind, value = goal["type"], goal.get("value")
    equity = account.equity(prices)
    if kind == "min_equity":
        return GoalCheck(f"Finish with at least ${value:,.0f}", f"${equity:,.2f}", equity >= value)
    if kind == "min_return":
        mine = account.total_return_pct(prices) / 100
        return GoalCheck(f"Finish up at least {value:+.0%}", f"{mine:+.1%}", mine >= value)
    if kind == "beat":
        mine, theirs = account.total_return_pct(prices) / 100, symbol_return(game, goal["symbol"])
        return GoalCheck(f"Beat buy-and-hold {goal['symbol']} ({theirs:+.1%})", f"{mine:+.1%}",
                         mine > theirs)
    if kind == "max_fees":
        return GoalCheck(f"Pay no more than ${value:,.0f} in fees", f"${account.fees_paid:,.0f}",
                         account.fees_paid <= value)
    if kind == "max_drawdown":
        worst = analytics.max_drawdown(game.equity_history)
        return GoalCheck(f"Never fall more than {value:.0%} from your peak", f"{worst:.1%}",
                         worst <= value)
    if kind == "no_margin_call":
        calls = len(game.margin_calls)
        return GoalCheck("Never get margin-called", f"{calls} margin call(s)", calls == 0)
    invested = 1 - account.weights(prices)["CASH"]
    return GoalCheck(f"Have at least {value:.0%} invested", f"{invested:.0%}", invested >= value)


def progress(game: Game) -> list[GoalCheck]:
    """Every goal of the current challenge (empty in free play)."""
    if game.challenge is None:
        return []
    return [check_goal(game, goal) for goal in game.challenge.goals]


def is_won(game: Game) -> bool:
    """True once the challenge is over and every goal passed."""
    checks = progress(game)
    return game.is_over() and bool(checks) and all(check.passed for check in checks)
