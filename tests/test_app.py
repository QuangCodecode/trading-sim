"""cli/app.py: the commands every front end sends. A bad line raises a TradeSimError, never anything else (N-02)."""

import pytest

from tradesim.cli import app
from tradesim.engine.errors import TradeSimError

# Lines a player (or an old saved game) might send. Each either works or raises a TradeSimError.
BAD_OR_ODD_LINES = [
    "robo NOPE", "robo a b", "challenge", "challenge nope", "challenge a b", "quiz z", "quiz a b", "quiz",
    "new abc", "whatif", "", "   ", "buy", "buy XYZ 1", "buy JUMP 999999", "buy JUMP ten",
    "buy JUMP 1.5", "sell JUMP all", "sell JUMP 3", "next 0", "next -2", "next abc", "lab",
    "lab FUND", "lab MC NOPE", "lab MC JUMP CALM", "levlab", "hl", 'hl "[/x] beats"', "x" * 500,
    "buy JUMP ²", "next ³", "new 99999999999999999999", "ünïcødé 🚀", "quit", "market", "news",
    "next 999", "buy JUMP 1", "leverage", "leverage 9", "leverage two",
]


@pytest.mark.parametrize("line", BAD_OR_ODD_LINES)
def test_any_line_returns_a_result_or_a_friendly_error(game, line):
    try:
        result = app.execute(game, line)
    except TradeSimError:
        return
    assert result is None or isinstance(result, dict)


def test_new_refuses_a_seed_too_big_to_save(game):
    """Bug 25: SQLite can't store it, so the save failed after the game had already changed."""
    with pytest.raises(TradeSimError, match="seed must be below"):
        app.execute(game, "new 99999999999999999999")


def test_buy_max_spends_almost_all_cash(game):
    app.execute(game, "buy fund max")
    assert 0 <= game.portfolio.cash < game.market.price("FUND", 0) + 1


def test_full_scripted_game_ends(game):
    for line in ["buy jump 10", "next 2", "sell jump all", "next 99", "lab"]:
        app.execute(game, line)
    assert game.is_over()
    assert len(game.portfolio.trades) == 2


def test_quiz_marks_the_answer_and_keeps_the_score():
    game = app.new_game(42, 60)
    first = app.execute(game, "quiz a")
    assert set(first) == {"correct", "answer", "explain", "right", "asked"}
    assert first["asked"] == 1 and first["right"] == int(first["correct"])
    assert app.execute(game, "quiz") is None and len(game.quiz_results) == 1   # a bare quiz does nothing


def test_headline_test_reports_what_the_word_counter_found():
    game = app.new_game(42, 60)
    result = app.execute(game, 'hl "Record profits and strong growth"')
    assert result["label"] == "positive" and "profits" in result["found"]
    assert app.execute(game, 'hl "Quarterly meeting held"')["label"] == "neutral"


def test_monte_carlo_returns_both_columns():
    game = app.new_game(42, 60)
    result = app.execute(game, "lab mc nvda")
    assert [side["symbol"] for side in result["sides"]] == ["NVDA", "MIX6"]
    assert result["runs"] == 200 and all(0 <= side["big_loss"] <= 1 for side in result["sides"])


def test_a_whole_game_with_every_command_runs_clean():
    game = app.new_game(42, 60)
    for line in ["leverage 2", "buy nvda 40", "buy mix6 max", "tick 30", "next 25", "sell nvda all",
                 "quiz a", "news", "robo", "levlab", "lab", "whatif", "next 99", "challenge crash",
                 "next 99", "new 5"]:
        app.execute(game, line)
    assert game.day == 0 and game.market.seed == 5            # `new 5` started over


def test_the_looking_commands_unlock_their_badges():
    game = app.new_game(42, 60)
    for line in ["robo", "news", "whatif", "levlab", "lab"]:
        app.execute(game, line)
    assert {"robo", "news_hound", "time_traveller", "lev_lab", "scientist"} <= set(game.badges)
