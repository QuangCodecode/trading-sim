"""cli/agent.py (X-06): one command per call, game kept in a JSON file. Never loads Laya."""

import json

import pytest

import main
from tradesim.cli import agent, app
from tradesim.engine.errors import CommandError, TradeSimError


@pytest.fixture
def path(tmp_path):
    """Where this test's game file lives (deleted after the test)."""
    return tmp_path / "saves" / "agent.json"


def run(path, line, seed=None, days=10):
    """One agent call, like `uv run main.py --game PATH LINE`."""
    return agent.run_once(path, seed, days, line)


def test_first_call_creates_the_file_with_the_seed(path):
    assert run(path, "market", seed=42) == 0
    state = json.loads(path.read_text())
    assert (state["seed"], state["days"], state["commands"]) == (42, 10, [])


def test_looking_without_a_seed_creates_no_file(path):
    assert run(path, "help") == 0
    assert not path.exists()
    assert run(path, "market", seed=42) == 0  # so the seed chosen next still applies
    assert json.loads(path.read_text())["seed"] == 42


def test_only_successful_state_changes_are_recorded(path):
    run(path, "buy NVDA 2", seed=42)
    run(path, "market")
    assert run(path, "buy XYZ 1") == 1
    run(path, "next 3")
    assert json.loads(path.read_text())["commands"] == ["buy NVDA 2", "next 3"]


def test_state_carries_over_between_calls(path):
    run(path, "buy NVDA 2", seed=42)
    run(path, "next 3")
    game, _ = agent.load_game(path)
    assert game.day == 3
    assert game.portfolio.qty_held("NVDA") == 2
    assert game.portfolio.cash < 10_000


def test_replay_matches_playing_in_one_session(path):
    for line in ["buy NVDA 5", "next 4", "sell NVDA all", "buy MIX6 max", "next 2"]:
        run(path, line, seed=7)
    live = app.new_game(7, 10)
    for line in ["buy NVDA 5", "next 4", "sell NVDA all", "buy MIX6 max", "next 2"]:
        app.execute(live, line)
    replayed, _ = agent.load_game(path)
    assert replayed.equity() == pytest.approx(live.equity())


@pytest.mark.parametrize("content", [
    "{not json",
    '{"version": 99, "seed": 1, "days": 10, "commands": []}',
    '{"version": 1, "seed": "x", "days": 10, "commands": []}',
    '{"version": 1, "seed": 1, "days": 10, "commands": ["buy NVDA 999999"]}',
    "[]",
])
def test_damaged_file_is_a_friendly_error_and_left_alone(path, capsys, content):
    path.parent.mkdir(parents=True)
    path.write_text(content)
    assert run(path, "market") == 1
    assert "damaged" in capsys.readouterr().out
    assert path.read_text() == content


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


def test_no_command_words_means_the_repl():
    assert main.parse_args(["--seed", "42"]).command == []
    args = main.parse_args(["--seed", "42", "buy", "NVDA", "20"])
    assert " ".join(args.command) == "buy NVDA 20"


def test_challenge_rewrites_the_file_and_replays_after_it(path):
    assert run(path, "challenge tech", seed=42) == 0
    state = json.loads(path.read_text())
    assert state["challenge"] == "tech" and state["seed"] == 506 and state["commands"] == []
    assert run(path, "next 3") == 0
    game, _ = agent.load_game(path)
    assert game.challenge.id == "tech" and game.day == 3 and game.portfolio.qty_held("TECH3") > 0


def test_new_starts_a_fresh_file(path):
    run(path, "buy NVDA 2", seed=42)
    assert run(path, "new 9") == 0
    state = json.loads(path.read_text())
    assert state["seed"] == 9 and state["commands"] == [] and state["challenge"] is None


def test_quiz_answers_are_remembered(path):
    run(path, "market", seed=42)
    assert run(path, "quiz b") == 0
    game, _ = agent.load_game(path)
    assert len(game.quiz_results) == 1
