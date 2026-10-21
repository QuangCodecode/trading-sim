"""cli/savegame.py: a game is its seed plus the commands that changed it, kept in player.db."""

from contextlib import closing

import pytest

from tradesim.cli import app, savegame
from tradesim.database import open_player, read_games
from tradesim.education import challenges
from tradesim.engine.errors import TradeSimError
from tradesim.loader import load_challenges


@pytest.fixture
def path(tmp_path):
    return tmp_path / "player.db"


def play(game, *lines):
    for line in lines:
        app.execute(game, line)


def test_no_saved_game_means_none(path):
    assert savegame.load_game(path, "web") is None


def test_start_then_record_then_load_gives_the_same_game(path):
    game = app.new_game(42, 10)
    game_id = savegame.start_game(path, "web", game)
    for line in ["buy NVDA 3", "next 2", "buy MIX6 max"]:
        app.execute(game, line)
        savegame.record(path, game_id, game, line)
    loaded, loaded_id = savegame.load_game(path, "web")
    assert loaded_id == game_id
    assert (loaded.day, loaded.portfolio.cash, loaded.equity()) == pytest.approx((game.day, game.portfolio.cash, game.equity()))
    assert loaded.portfolio.qty_held("NVDA") == 3


def test_the_summary_row_follows_the_game(path):
    game = app.new_game(42, 10)
    game_id = savegame.start_game(path, "web", game)
    play(game, "buy NVDA 3", "next 2", "quiz b")
    savegame.record(path, game_id, game, "next 2")
    row = read_games(path)[0]
    assert row["day"] == 2 and row["over"] == 0 and row["passed"] is None
    assert row["equity"] == pytest.approx(game.equity())
    assert row["fees"] == pytest.approx(game.portfolio.fees_paid)
    assert (row["quiz_right"], row["quiz_answered"]) == app.quiz_score(game)


def test_badges_are_kept_once_each(path):
    game = app.new_game(42, 10)
    game_id = savegame.start_game(path, "web", game)
    play(game, "buy NVDA 3")
    savegame.record(path, game_id, game, "buy NVDA 3")
    savegame.record(path, game_id, game)                  # a second save must not duplicate them
    assert game.badges and read_games(path)[0]["badges"] == game.badges


def test_a_finished_challenge_records_whether_it_was_passed(path):
    challenge = load_challenges()["bull"]
    game = app.new_game(None, 60, challenge)
    game_id = savegame.start_game(path, "web", game)
    assert read_games(path)[0]["passed"] is None        # not decided while it is still running
    play(game, "next 60")
    savegame.record(path, game_id, game, "next 60")
    row = read_games(path)[0]
    assert row["over"] == 1 and row["passed"] == int(challenges.is_won(game)) and row["challenge"] == "bull"


def test_starting_again_in_a_slot_keeps_the_old_game_but_frees_the_slot(path):
    first = savegame.start_game(path, "web", app.new_game(1, 10))
    second = savegame.start_game(path, "web", app.new_game(2, 10))
    by_id = {g["id"]: g for g in read_games(path)}
    assert by_id[first]["slot"] is None and by_id[second]["slot"] == "web"
    loaded, loaded_id = savegame.load_game(path, "web")
    assert loaded_id == second and loaded.market.seed == 2


def test_a_command_that_no_longer_works_means_damaged(path):
    game_id = savegame.start_game(path, "web", app.new_game(1, 10))
    with closing(open_player(path)) as db, db:
        db.execute("INSERT INTO commands VALUES (?, 0, 'sell NVDA 5')", (game_id,))   # nothing to sell
    with pytest.raises(TradeSimError, match="damaged"):
        savegame.load_game(path, "web")
