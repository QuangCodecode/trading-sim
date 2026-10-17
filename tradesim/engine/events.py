"""Market events (E-02): news that shocks one stock, one sector or the whole market."""

import random

from tradesim import config
from tradesim.engine.stock import Stock

SCOPES = ("stock", "sector", "market")


class MarketEvent:
    """One piece of news on one day, with the extra return it adds to affected stocks."""

    def __init__(self, day: int, headline: str, explanation: str, scope: str,
                 target: str, shock: float) -> None:
        """`scope` is "stock" (target = symbol), "sector" (target = sector) or "market"."""
        self.day = day
        self.headline = headline
        self.explanation = explanation
        self.scope = scope
        self.target = target
        self.shock = shock

    def affects(self, stock: Stock) -> bool:
        """True if this event moves `stock`."""
        if self.scope == "market":
            return True
        if self.scope == "sector":
            return stock.sector == self.target
        return stock.symbol == self.target

    def __str__(self) -> str:
        return f"Day {self.day}: {self.headline}"

    def __repr__(self) -> str:
        return (f"MarketEvent(day={self.day}, headline={self.headline!r}, scope={self.scope!r}, "
                f"target={self.target!r}, shock={self.shock:.4f})")


def generate_events(templates: list[dict], seed: int, num_days: int) -> dict[int, list[MarketEvent]]:
    """Roll for news on each day 1..num_days using its own RNG (so prices' RNG is untouched)."""
    rng = random.Random(seed + config.EVENT_SEED_OFFSET)
    events = {}
    for day in range(1, num_days + 1):
        if templates and rng.random() < config.EVENT_PROBABILITY:
            template = rng.choice(templates)
            shock = rng.uniform(template["shock_min"], template["shock_max"])
            events[day] = [MarketEvent(day, template["headline"], template["explanation"],
                                       template["scope"], template["target"], shock)]
    return events
