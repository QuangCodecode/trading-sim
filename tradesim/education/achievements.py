"""X-05 Achievements: badges for good investing habits and for exploring the game.

Each badge is a small rule function, like the Coach's rules. `newly_unlocked` checks the
ones not yet won after every command and remembers winners in `game.badges`.
"""

from collections.abc import Callable

from tradesim import config
from tradesim.education import challenges, coach
from tradesim.engine import analytics
from tradesim.engine.game import Game


class Badge:
    """One achievement and the rule that unlocks it."""

    def __init__(self, badge_id: str, emoji: str, title: str, how: str, rule) -> None:
        """`rule(game)` returns True once the badge is earned; `how` says how to earn it."""
        self.badge_id = badge_id
        self.emoji = emoji
        self.title = title
        self.how = how
        self.rule = rule

    def __str__(self) -> str:
        return f"{self.emoji} {self.title}"

    def __repr__(self) -> str:
        return f"Badge({self.badge_id!r})"


def return_now(game: Game) -> float:
    """The player's total return so far as a fraction."""
    return game.portfolio.total_return_pct(game.current_prices()) / 100


def invested_share(game: Game) -> float:
    """Share of equity not sitting in cash."""
    return 1 - game.portfolio.weights(game.current_prices())["CASH"]


def diversified(game: Game) -> bool:
    """3+ sectors, no single stock above 30%, at least half invested."""
    biggest = max(coach.stock_weights(game).values(), default=0.0)
    return (len(coach.sectors_held(game)) >= config.GOOD_MIN_SECTORS
            and biggest <= config.GOOD_MAX_WEIGHT and invested_share(game) >= 0.5)


def held_through_downturn(game: Game) -> bool:
    """A bear market or crash has come and gone while you stayed mostly invested and in profit."""
    seen = any(game.market.regime_path[d] in ("bear", "crash") for d in range(game.day + 1))
    return seen and game.is_over() and invested_share(game) >= 0.5 and return_now(game) > 0


def beat_market(game: Game) -> bool:
    """After 20+ days, your return beats buying the whole market on day 0."""
    index = analytics.total_return(game.market.history(game.market.index_symbol(), 0, game.day))
    return game.day >= 20 and invested_share(game) > 0 and return_now(game) > index + config.BEAT_MARGIN


def used(command: str) -> Callable[[Game], bool]:
    """Make a rule: True once the player has used `command`."""
    return lambda game: command in game.commands_used


BADGES = [
    Badge("first_trade", "🎬", "First Trade", "Make your first trade", lambda g: bool(g.portfolio.trades)),
    Badge("basket", "🧺", "Basket Holder", "Own an ETF", lambda g: any(g.market.is_etf(s) for s in g.portfolio.positions)),
    Badge("diversified", "🌈", "Diversified", "Own 3+ sectors, no stock above 30%, half invested", diversified),
    Badge("green", "📈", "In the Green", "Be up 5% or more", lambda g: return_now(g) >= 0.05),
    Badge("market_beater", "🚀", "Market Beater", "Beat MKT100 after day 20", beat_market),
    Badge("patient", "🧘", "Patient Investor", "Reach day 30 with 5 trades or fewer, mostly invested",
          lambda g: g.day >= 30 and 0 < len(g.portfolio.trades) <= 5 and invested_share(g) >= 0.5),
    Badge("survivor", "🛡️", "Storm Survivor", "Finish in profit after living through a downturn", held_through_downturn),
    Badge("fee_miser", "🪙", "Fee Miser", "Finish a game paying less than $5 in fees",
          lambda g: g.is_over() and len(g.portfolio.trades) > 0 and g.portfolio.fees_paid < 5),
    Badge("finisher", "🏁", "Finisher", "Reach the final day", lambda g: g.is_over()),
    Badge("champion", "🏆", "Challenge Champion", "Win a challenge", challenges.is_won),
    Badge("scientist", "🔬", "Scientist", "Run the Diversification Lab", used("lab")),
    Badge("news_hound", "📰", "News Hound", "Read a news breakdown", used("news")),
    Badge("ai_skeptic", "🗞️", "Headline Detective", "Try the Headline Lab", used("headlines")),
    Badge("robo", "🤖", "Robo Curious", "Ask the Robo-analyst", used("robo")),
    Badge("time_traveller", "⏪", "Time Traveller", "Run a What-if Replay", used("whatif")),
    Badge("scholar", "🎓", "Scholar", "Answer 5 quiz questions correctly", lambda g: sum(g.quiz_results) >= 5),
    Badge("day_trader", "⏱️", "Day Trader", "Trade while the market is open",
          lambda g: any(t.tick > 0 and not t.note for t in g.portfolio.trades)),   # not forced sales
    Badge("borrower", "🏦", "On Margin", "Buy with borrowed money", lambda g: g.portfolio.loan() > 0),
    Badge("margin_called", "📞", "Learned the Hard Way", "Get margin-called (it happens to pros too)",
          lambda g: bool(g.margin_calls)),
    Badge("lev_lab", "🧪", "Leverage Scientist", "Run the Leverage Lab", used("levlab")),
]


def newly_unlocked(game: Game) -> list[Badge]:
    """Badges earned since the last check (each is only ever announced once)."""
    fresh = [b for b in BADGES if b.badge_id not in game.badges and b.rule(game)]
    game.badges.extend(b.badge_id for b in fresh)
    return fresh
