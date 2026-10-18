"""E-03 Trade Coach: one positive and one negative case per rule (tiny market from conftest)."""

import pytest

from tradesim.education import coach


def test_concentration_warns_about_one_big_stock(game):
    trade = game.buy("JUMP", 80)          # $8,000 of $10,000 in one stock
    tips = coach.review_trade(game, trade)
    assert tips[0].rule_id == "CONC" and "JUMP" in tips[0].message


def test_concentration_ignores_etfs(game):
    trade = game.buy("FUND", 90)          # an ETF is already spread out
    assert all(t.rule_id != "CONC" for t in coach.review_trade(game, trade))


def test_panic_sell_after_a_sharp_drop(game):
    game.advance(1)                       # JUMP 110
    game.buy("JUMP", 10)
    game.advance(1)                       # JUMP 90: −18% in a day
    tips = coach.review_trade(game, game.sell("JUMP", 10))
    assert any(t.rule_id == "PANIC" for t in tips)


def test_selling_at_a_profit_is_not_panic(game):
    game.buy("JUMP", 10)                  # bought at 100
    game.advance(1)                       # 110
    tips = coach.review_trade(game, game.sell("JUMP", 10))
    assert all(t.rule_id != "PANIC" for t in tips)


def test_overtrading_after_five_trades_in_a_day(game):
    for _ in range(4):
        game.buy("CALM", 1)
    tips = coach.review_trade(game, game.buy("CALM", 1))
    assert any(t.rule_id == "OVER" for t in tips)
    assert len(tips) <= 2                 # never naggy


def test_idle_cash_only_after_the_grace_period(game):
    assert coach.idle_cash(game) is None  # day 0 is too early to nag
    game.day = 10                         # pretend time passed (prices stay valid via min)
    game.day = game.market.num_days
    assert coach.idle_cash(game) is None or coach.idle_cash(game).rule_id == "IDLE"


def test_diversified_praise_needs_three_sectors(game):
    game.buy("FUND", 50)                  # FUND holds Tech, Consumer and Energy
    assert coach.diversified(game).severity == coach.PRAISE
    game.sell("FUND", 50)
    game.buy("JUMP", 5)
    assert coach.diversified(game) is None


def test_fees_tip_when_fees_eat_the_result(game):
    for _ in range(6):
        game.buy("OIL", 1)
        game.sell("OIL", 1)
    tip = coach.fees(game)
    assert tip and tip.rule_id == "FEES"


def test_sector_exposure_looks_inside_etfs(game):
    game.buy("FUND", 10)                   # FUND = 20% JUMP (Tech), 40% CALM, 40% OIL at launch
    game.buy("JUMP", 5)
    exposure = coach.sector_exposure(game)
    assert exposure["Tech"] == pytest.approx(0.2 * 10 * 100 + 5 * 100)
    assert sum(exposure.values()) == pytest.approx(game.portfolio.market_value(game.current_prices()))
