"""cli/agent.py (X-06): one command per call, game kept in the player database. Never loads Laya."""

from contextlib import closing

import pytest

import main
from tradesim import config
from tradesim.cli import agent, app, savegame
from tradesim.database import open_player, read_games
from tradesim.engine.errors import CommandError, TradeSimError


@pytest.fixture
def path(tmp_path):
    """Where this test's player database lives (deleted after the test)."""
    return tmp_path / "saves" / "player.db"


def run(path, line, seed=None, days=10):
    """One agent call, like `uv run main.py --db PATH LINE`."""
    return agent.run_once(path, config.AGENT_SLOT, seed, days, line)


def commands(path, game_id=None):
    """The stored command lines of one game (the current game if no id is given)."""
    with closing(open_player(path)) as db:
        game_id = game_id or db.execute("SELECT id FROM games WHERE slot = ?", (config.AGENT_SLOT,)).fetchone()[0]
        rows = db.execute("SELECT line FROM commands WHERE game_id = ? ORDER BY position", (game_id,))
        return [row["line"] for row in rows]


def test_first_call_saves_the_game_with_its_seed(path):
    assert run(path, "market", seed=42) == 0
    (game,) = read_games(path)
    assert (game["seed"], game["days"], game["slot"], commands(path)) == (42, 10, "agent", [])


def test_looking_without_a_seed_saves_no_game(path):
    assert run(path, "help") == 0
    assert read_games(path) == []
    assert run(path, "market", seed=42) == 0  # so the seed chosen next still applies
    assert read_games(path)[0]["seed"] == 42


def test_only_successful_state_changes_are_recorded(path):
    run(path, "buy NVDA 2", seed=42)
    run(path, "market")
    assert run(path, "buy XYZ 1") == 1
    run(path, "next 3")
    assert commands(path) == ["buy NVDA 2", "next 3"]


def test_state_carries_over_between_calls(path):
    run(path, "buy NVDA 2", seed=42)
    run(path, "next 3")
    game, _ = savegame.load_game(path, config.AGENT_SLOT)
    assert game.day == 3
    assert game.portfolio.qty_held("NVDA") == 2
    assert game.portfolio.cash < 10_000


def test_replay_matches_playing_in_one_session(path):
    for line in ["buy NVDA 5", "next 4", "sell NVDA all", "buy MIX6 max", "next 2"]:
        run(path, line, seed=7)
    live = app.new_game(7, 10)
    for line in ["buy NVDA 5", "next 4", "sell NVDA all", "buy MIX6 max", "next 2"]:
        app.execute(live, line)
    replayed, _ = savegame.load_game(path, config.AGENT_SLOT)
    assert replayed.equity() == pytest.approx(live.equity())


def damage_garbage(path):
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not a database " * 20)


def damage_version(path):
    with closing(open_player(path)) as db:
        db.execute("PRAGMA user_version = 99")


def damage_command(path):
    run(path, "market", seed=1)
    with closing(open_player(path)) as db, db:
        db.execute("INSERT INTO commands VALUES (1, 0, 'buy NVDA 999999')")   # can't be afforded


def damage_challenge(path):
    run(path, "market", seed=1)
    with closing(open_player(path)) as db, db:
        db.execute("UPDATE games SET challenge = 'nope'")


@pytest.mark.parametrize("damage", [damage_garbage, damage_version, damage_command, damage_challenge])
def test_damaged_database_is_a_friendly_error(path, capsys, damage):
    damage(path)
    capsys.readouterr()
    assert run(path, "market") == 1
    assert "damaged" in capsys.readouterr().out


def test_other_seed_than_the_saved_game_is_refused(path, capsys):
    run(path, "market", seed=42)
    assert run(path, "market", seed=7) == 1
    assert "seed 42" in capsys.readouterr().out


def test_output_is_plain_text_with_the_status_line(path, capsys):
    run(path, "portfolio", seed=42)
    out = capsys.readouterr().out
    assert "\x1b[" not in out  # no colour codes for the agent to wade through
    assert out.startswith("Day 0 / 10 · Cash $10,000.00")


def test_execute_raises_but_run_command_does_not(game):
    with pytest.raises(CommandError):
        app.execute(game, "buy")
    assert "✗" in app.run_command(game, "buy")[0]
    assert isinstance(CommandError("x"), TradeSimError)


def test_a_seed_too_big_to_save_is_refused():
    with pytest.raises(SystemExit):
        main.parse_args(["--seed", "99999999999999999999"])


def test_no_command_words_means_the_repl():
    assert main.parse_args(["--seed", "42"]).command == []
    args = main.parse_args(["--seed", "42", "buy", "NVDA", "20"])
    assert " ".join(args.command) == "buy NVDA 20"


def test_challenge_starts_a_new_game_and_replays_after_it(path):
    assert run(path, "challenge tech", seed=42) == 0
    (saved,) = read_games(path)
    assert saved["challenge"] == "tech" and saved["seed"] == 506 and commands(path) == []
    assert run(path, "next 3") == 0
    game, _ = savegame.load_game(path, config.AGENT_SLOT)
    assert game.challenge.id == "tech" and game.day == 3 and game.portfolio.qty_held("TECH3") > 0


def test_new_starts_a_fresh_game_and_keeps_the_old_one_in_history(path):
    run(path, "buy NVDA 2", seed=42)
    assert run(path, "new 9") == 0
    newest, older = read_games(path)
    assert (newest["seed"], newest["slot"], commands(path)) == (9, "agent", [])
    assert (older["seed"], older["slot"], commands(path, older["id"])) == (42, None, ["buy NVDA 2"])


def test_two_slots_are_two_games(path):
    agent.run_once(path, "alice", 1, 10, "buy NVDA 1")
    agent.run_once(path, "bob", 2, 10, "market")
    assert {g["slot"]: g["seed"] for g in read_games(path)} == {"alice": 1, "bob": 2}


def test_quiz_answers_are_remembered(path):
    run(path, "market", seed=42)
    assert run(path, "quiz b") == 0
    game, _ = savegame.load_game(path, config.AGENT_SLOT)
    assert len(game.quiz_results) == 1
    assert read_games(path)[0]["quiz_answered"] == 1
