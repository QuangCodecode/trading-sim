"""cli/app.py: no input line may ever raise (N-02)."""

import io

import pytest
from rich.console import Console

from tradesim.cli import app
from tradesim.education.headline_lab import Verdict

BAD_OR_ODD_LINES = [
    "", "   ", "buy", "buy XYZ 1", "buy JUMP 999999", "buy JUMP ten", "buy JUMP 1.5",
    "sell JUMP all", "sell JUMP 3", "next 0", "next -2", "next abc", "lab", "lab FUND",
    "lab JUMP CALM", "lab NOPE", "chart", "chart NOPE", "quote", "etf JUMP", "etf NOPE",
    "help nope", "hl", "x" * 500, "ünïcødé 🚀", "quit", "news", "news 0", "news 99", "news 3", "next 999", "buy JUMP 1",
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


class FakeAI:
    """Answers every headline 'negative 55%' without loading a model."""

    def cached(self, headline):
        return self.classify(headline)

    def classify(self, headline):
        return Verdict("negative", 0.55, "laya")


def test_every_screen_renders_on_a_real_market():
    game = app.new_game(42, 60)
    console = Console(file=io.StringIO(), width=100)
    script = ["help", "help buy", "market", "quote nvda", "chart nvda", "chart nvda mix6", "etf",
              "buy nvda 40", "buy mix6 max", "next 25", "news 21", "news 3", "portfolio",
              "history", "lab", "lab ko", "lab mc", "hl", 'hl "Shares soar"', "sell nvda all",
              "report", "next 99"]
    for line in script:
        for renderable in app.run_command(game, line, FakeAI()):
            console.print(renderable)
    text = console.file.getvalue()
    assert "Laya: negative 55% (unsure)" in text
    assert "Score: keywords" in text and "Final report" in text
