"""Game clock, equity snapshots and game-over rules."""

import pytest

from tradesim.engine.errors import GameOverError, InvalidQuantityError, UnknownSymbolError


def test_advance_one_day_appends_one_snapshot(game):
    game.advance(1)
    assert game.day == 1
    assert len(game.equity_history) == 2


def test_advance_caps_at_final_day_then_game_over(game):
    game.advance(999)
    assert game.day == 5 and game.is_over()
    with pytest.raises(GameOverError):
        game.buy("JUMP", 1)
    with pytest.raises(GameOverError):
        game.advance(1)


def test_advance_rejects_zero_days(game):
    with pytest.raises(InvalidQuantityError):
        game.advance(0)


def test_current_prices_are_todays_only(game, tiny_market):
    game.advance(2)
    assert game.current_prices() == tiny_market.prices_on(2)


def test_trades_use_todays_price_and_track_equity(game):
    game.advance(1)
    trade = game.buy("JUMP", 10)
    assert trade.price == 110.0 and trade.day == 1
    game.advance(1)
    # 10 shares fell from 110 to 90; minus the $1 fee.
    assert game.equity_history[-1] == pytest.approx(10_000 - 200 - 1)


def test_unknown_symbol_rejected(game):
    with pytest.raises(UnknownSymbolError):
        game.buy("NOPE", 1)
