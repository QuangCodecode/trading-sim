"""cli/app.py: no input line may ever raise (N-02)."""

import pytest

from tradesim.cli import app

BAD_OR_ODD_LINES = [
    "", "   ", "buy", "buy XYZ 1", "buy JUMP 999999", "buy JUMP ten", "buy JUMP 1.5",
    "sell JUMP all", "sell JUMP 3", "next 0", "next -2", "next abc", "lab", "lab FUND",
    "lab JUMP CALM", "lab NOPE", "chart", "chart NOPE", "quote", "etf JUMP", "etf NOPE",
    "help nope", "hl", "x" * 500, "ünïcødé 🚀", "quit", "news", "next 999", "buy JUMP 1",
]


@pytest.mark.parametrize("line", BAD_OR_ODD_LINES)
def test_any_line_returns_output_without_raising(game, line):
    output = app.run_command(game, line)
    assert isinstance(output, list)


def test_buy_max_spends_almost_all_cash(game):
    app.run_command(game, "buy fund max")
    assert 0 <= game.portfolio.cash < game.market.price("FUND", 0) + 1


def test_full_scripted_game_ends_with_report(game):
    for line in ["buy jump 10", "next 2", "sell jump all", "next 99", "lab"]:
        app.run_command(game, line)
    assert game.is_over()
    assert len(game.portfolio.trades) == 2
