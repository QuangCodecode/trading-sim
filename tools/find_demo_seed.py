"""Find a dramatic, reliable market for the 3-minute demo (roadmap Phase 7).

    uv run tools/find_demo_seed.py

Wanted: an early news shock that hits NVDA hard but MIX6 only a little (the Explainer's
lesson), then a mood change later (a bear market or crash for the market story), enough news,
and a scary NVDA drawdown. Prints the first seed that fits and why.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # let `tradesim` import from tools/

from tradesim.cli.app import new_game
from tradesim.engine import analytics
from tradesim.engine.market import Market
from tradesim.engine.regime import spells

SEARCH_SEEDS = 3000


def early_tech_shock(market: Market) -> int | None:
    """The first day 4-15 when bad tech/NVDA news drops NVDA ≥ 6% but MIX6 < 3%."""
    for day in range(4, 16):
        for event in market.events_on(day):
            bad_tech = event.shock < 0 and event.target in ("Tech", "NVDA")
            if (bad_tech and market.daily_change_pct("NVDA", day) <= -6
                    and market.daily_change_pct("MIX6", day) > -3):
                return day
    return None


def fits(market: Market) -> bool:
    """Starts calm, turns bad later, plenty of news, NVDA falls hard at some point."""
    moods = [name for name, _, _ in spells(market.regime_path)]
    news_days = [d for d in range(1, market.num_days + 1) if market.events_on(d)]
    return (moods[0] in ("bull", "sideways") and ("bear" in moods or "crash" in moods)
            and len(news_days) >= 8
            and analytics.max_drawdown(market.history("NVDA", 0, market.num_days)) > 0.18)


def main() -> None:
    """Print the first seed that makes a good demo."""
    for seed in range(1, SEARCH_SEEDS):
        market = new_game(seed, 60).market
        day = early_tech_shock(market)
        if day and fits(market):
            print(f"Seed {seed}: day {day} {market.events_on(day)[0].headline} — NVDA "
                  f"{market.daily_change_pct('NVDA', day):+.1f}%, MIX6 {market.daily_change_pct('MIX6', day):+.2f}%")
            print("Moods:", spells(market.regime_path))
            return
    print("No seed found — loosen the rules in fits().")


if __name__ == "__main__":
    main()
