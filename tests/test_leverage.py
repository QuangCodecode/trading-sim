"""E-08 Leverage Lab, the leverage/tick/levlab/market commands, and leverage coaching."""

import pytest

from tradesim import config
from tradesim.cli import app
from tradesim.education import achievements, challenges, coach, leverage_lab
from tradesim.engine.errors import TradeSimError
from tradesim.loader import load_challenges


def test_no_borrowing_run_is_plain_buy_and_hold(tiny_market):
    run = leverage_lab.margin_run(tiny_market, "JUMP", 0, 5, 1, 5_000.0)
    # 49 shares at $100 (+$1 fee), $99 left over; JUMP ends at $100 again.
    assert run.values[-1] == pytest.approx(99 + 49 * 100) and run.interest == 0 and run.called_on is None


def test_2x_run_pays_interest_and_doubles_the_swings(tiny_market):
    one = leverage_lab.margin_run(tiny_market, "JUMP", 0, 1, 1, 5_000.0)
    two = leverage_lab.margin_run(tiny_market, "JUMP", 0, 1, 2, 5_000.0)
    assert two.total_return() == pytest.approx(2 * one.total_return(), rel=0.05)
    assert two.interest > 0


def test_5x_run_is_margin_called_and_wiped_out(tiny_market):
    run = leverage_lab.margin_run(tiny_market, "JUMP", 0, 5, 5, 5_000.0)
    # 249 shares, $19,901 borrowed. Day 2 at $90: equity $2,509 is 11.2% of $22,410 (above 10%).
    # Day 4 at $80: equity is about $19, so the broker sells everything and a small debt remains.
    assert run.called_on == 4 and run.values[-1] < 0


def test_daily_fund_shows_volatility_decay(tiny_market):
    run = leverage_lab.daily_fund_run(tiny_market, "JUMP", 0, 5, 2, 100.0)
    # JUMP ends where it started, but the 2× daily fund doesn't: 1.2 × 0.636 × 1.333 × 0.524 × 1.5
    assert tiny_market.price("JUMP", 5) == tiny_market.price("JUMP", 0)
    assert run.values[-1] < 100 and run.values[1] == pytest.approx(120)


def test_compare_and_lessons(tiny_market):
    runs = leverage_lab.compare(tiny_market, "JUMP", 0, 5)
    assert [r.label for r in runs] == ["No borrowing", "2× on margin", "3× on margin", "5× on margin",
                                       "2× daily fund"]
    lessons = leverage_lab.lessons(runs, "JUMP")
    assert len(lessons) == 3 and "margin-called on day 4" in lessons[1]


def test_risk_table():
    table = leverage_lab.risk_table()
    assert len(table) == config.MAX_LEVERAGE
    assert table[1] == (2, 0.25, pytest.approx(1 / 3), 0.5)


def test_leverage_command_shows_and_sets():
    game = app.new_game(42, 60)
    assert app.execute(game, "leverage")
    app.execute(game, "leverage 2")
    assert game.portfolio.max_leverage == 2
    with pytest.raises(TradeSimError, match="between 1 and"):
        app.execute(game, "leverage 9")


def test_leveraged_buy_borrows_and_the_coach_warns():
    game = app.new_game(42, 60)
    app.execute(game, "leverage 2")
    output = app.execute(game, "buy MKT100 max")
    assert game.portfolio.loan() > 0
    assert any("borrowing" in str(getattr(line, "plain", line)) for line in output)
    assert "borrower" in game.badges


def test_tick_command_runs_the_session():
    game = app.new_game(42, 60)
    app.execute(game, "tick 6")
    assert (game.day, game.tick) == (0, 6)
    app.execute(game, "buy NVDA 1")
    assert "day_trader" in game.badges
    app.execute(game, "tick 100")
    assert (game.day, game.tick) == (1, 0)


def test_levlab_works_from_day_0_thanks_to_the_history():
    game = app.new_game(42, 60)
    assert app.execute(game, "levlab")
    assert app.execute(game, "levlab NVDA") and "lev_lab" in game.badges


def test_levlab_needs_days_without_history(game):
    with pytest.raises(TradeSimError, match="Play a few days"):
        app.execute(game, "levlab FUND")


def test_market_filters_by_sector():
    game = app.new_game(42, 60)
    assert app.pick_symbols(game, "real") == [s for s, st in game.market.stocks.items()
                                              if st.sector == "Real Estate"]
    assert app.pick_symbols(game, "etf") == list(game.market.etfs)
    with pytest.raises(TradeSimError, match="No sector"):
        app.execute(game, "market spaceships")


def test_margin_madness_punishes_doing_nothing():
    challenge = load_challenges(config.CHALLENGES_PATH)["margin"]
    game = app.new_game(None, 0, challenge)
    assert game.portfolio.max_leverage == 3 and game.portfolio.loan() > 0
    app.execute(game, "next 60")
    assert game.margin_calls and not challenges.is_won(game)
    assert "margin_called" in game.badges
    assert any(tip.rule_id == "CALL" for tip in coach.review_session(game))


def test_new_badges_exist():
    ids = [badge.badge_id for badge in achievements.BADGES]
    assert {"day_trader", "borrower", "margin_called", "lev_lab"} <= set(ids)
