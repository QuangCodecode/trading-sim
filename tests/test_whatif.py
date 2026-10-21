"""E-04 What-if Replay: strategies and the replay engine."""

import pytest

from tradesim import config
from tradesim.cli import app
from tradesim.education import strategies, whatif
from tradesim.loader import load_robo


@pytest.fixture
def played():
    """A real seed-42 game with a few trades, 40 days in."""
    game = app.new_game(42, 60)
    for line in ["buy nvda 20", "buy mix6 30", "next 15", "sell nvda 10", "buy ko 10", "next 25"]:
        app.execute(game, line)
    return game


def test_your_trades_replay_matches_the_real_game(played):
    """Replay fidelity: if this fails, the replay engine has a bug (docs/04 E-04)."""
    trades = played.portfolio.trades
    def copy_trades(day, market, portfolio):
        return [(t.side, t.symbol, t.qty) for t in trades if t.day == day]
    mine = whatif.replay(played.market, whatif.YOURS, "", copy_trades, played.day)
    assert mine.final == pytest.approx(played.equity())
    assert mine.trades == len(played.portfolio.trades)


def test_cash_only_keeps_starting_cash(played):
    result = whatif.replay(played.market, "Cash", "", strategies.cash_only, played.day)
    assert result.final == config.STARTING_CASH and result.trades == 0


def test_hold_spends_almost_everything_once(played):
    result = whatif.replay(played.market, "Hold", "", strategies.buy_and_hold("MKT100"), played.day)
    expected_qty = int((config.STARTING_CASH - config.FEE_PER_TRADE) // played.market.price("MKT100", 0))
    leftover = config.STARTING_CASH - config.FEE_PER_TRADE - expected_qty * played.market.price("MKT100", 0)
    assert result.trades == 1
    assert result.final == pytest.approx(leftover + expected_qty * played.market.price("MKT100", played.day))


def test_compare_ranks_every_strategy_best_first(played):
    results = whatif.compare_strategies(played, load_robo(config.ROBO_MODEL_PATH))
    assert len(results) == 11
    finals = [r.final for r in results]
    assert finals == sorted(finals, reverse=True)
    assert whatif.YOURS in [r.name for r in results]
    assert whatif.lessons(results, "MKT100")


def test_chase_the_winner_reinvests_the_sale_proceeds(played):
    result = whatif.replay(played.market, "Chase", "", strategies.chase_the_winner, played.day)
    assert result.trades > 2
    assert result.curve[-1] > 0.5 * config.STARTING_CASH   # it was invested, not stuck in cash


def test_strategies_never_peek_beyond_today(played):
    """Strategies only see prices up to `day`: a market cut short must give the same orders."""
    short = app.new_game(42, 20).market
    for day in range(0, 21):
        assert strategies.chase_the_winner(day, short, whatif.Portfolio(10_000, 1)) == \
            strategies.chase_the_winner(day, played.market, whatif.Portfolio(10_000, 1))


def test_favourite_stock_is_the_one_you_spent_most_on(played):
    assert whatif.favourite_stock(played) == "NVDA"


def test_your_trades_row_is_what_really_happened_with_leverage_and_ticks():
    """Bug 21: mid-session trades on margin used to be replayed at closes in a cash account."""
    game = app.new_game(42, 60)
    app.execute(game, "leverage 2")
    app.execute(game, "tick 30")
    app.execute(game, "buy MKT100 max")
    app.execute(game, "next 10")
    yours = next(r for r in whatif.compare_strategies(game, app.robo_model()) if r.name == whatif.YOURS)
    assert yours.curve == game.equity_history and yours.final == pytest.approx(game.equity())
