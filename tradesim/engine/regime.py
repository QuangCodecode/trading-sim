"""Market regimes: the hidden "mood" of the market that makes real-life trends.

Real markets don't wander randomly every day: they spend weeks or months in a bull run,
a sideways chop or a bear market, and once in a while they crash. We copy that with a
Markov chain: each day the market keeps its mood with a high probability or switches to
another one, using the transition table in data/reference.db (finance model §3.2).
"""

import random

from tradesim import config


class Regime:
    """One market mood: how the whole market drifts and how stormy it is."""

    def __init__(self, name: str, label: str, emoji: str, drift: float, vol_scale: float,
                 transitions: dict[str, float], about: str = "") -> None:
        """`transitions` maps each regime name to the chance of being in it tomorrow."""
        self.name = name
        self.label = label
        self.emoji = emoji
        self.drift = drift
        self.vol_scale = vol_scale
        self.transitions = transitions
        self.about = about

    def expected_days(self) -> float:
        """Average length of a spell in this mood: 1 / (chance of leaving each day)."""
        leave = 1 - self.transitions.get(self.name, 0.0)
        return 1 / leave if leave > 0 else float("inf")

    def __str__(self) -> str:
        return f"{self.emoji} {self.label}"

    def __repr__(self) -> str:
        return f"Regime({self.name!r}, drift={self.drift}, vol_scale={self.vol_scale})"


class RegimeModel:
    """All the moods plus the chance of starting the game in each one."""

    def __init__(self, regimes: dict[str, Regime], start: dict[str, float]) -> None:
        """`start` maps regime name → probability of being the day-0 mood (sums to 1)."""
        self.regimes = regimes
        self.start = start

    def generate(self, seed: int, num_days: int) -> list[str]:
        """Walk the Markov chain for days 0..num_days and return each day's regime name.

        Uses its own RNG (like events), so the market's "story" is drawn separately from
        the day-to-day noise (D-09).
        """
        rng = random.Random(seed + config.REGIME_SEED_OFFSET)
        path = [pick(rng, self.start)]
        for _ in range(num_days):
            path.append(pick(rng, self.regimes[path[-1]].transitions))
        return path

    def __repr__(self) -> str:
        return f"RegimeModel({list(self.regimes)})"


def pick(rng: random.Random, chances: dict[str, float]) -> str:
    """Choose one key of `chances` at random, each with its own probability."""
    names = list(chances)
    return rng.choices(names, weights=[chances[name] for name in names])[0]


# Used when a market is built without regime data (tests, hand-made markets): no trend.
NORMAL = Regime("normal", "Normal market", "·", 0.0, 1.0, {"normal": 1.0})
FLAT_MODEL = RegimeModel({"normal": NORMAL}, {"normal": 1.0})


def spells(path: list[str]) -> list[tuple[str, int, int]]:
    """Group a regime path into (name, first day, last day) runs, e.g. bull 0-17, bear 18-30."""
    result = []
    start = 0
    for day in range(1, len(path) + 1):
        if day == len(path) or path[day] != path[start]:
            result.append((path[start], start, day - 1))
            start = day
    return result
