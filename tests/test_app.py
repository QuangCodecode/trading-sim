"""cli/app.py: no input line may ever raise (N-02)."""

import io

import pytest
from rich.console import Console

from tradesim.cli import app, savegame
from tradesim.education.headline_lab import Verdict
from tradesim.engine.errors import TradeSimError

BAD_OR_ODD_LINES = [
    "robo NOPE", "robo a b", "challenge nope", "challenge a b", "learn spaceship", "quiz z",
    "quiz a b", "new abc", "whatif", "story", "coach", "badges", "sectors", "learn",
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
              "robo", "story", "buy nvda 40", "buy mix6 max", "next 25", "news 21", "news 3", "portfolio",
              "history", "lab", "lab ko", "lab mc", "hl", 'hl "Shares soar"', "sell nvda all",
              "robo", "robo nvda", "story", "sectors", "coach", "whatif", "badges", "learn",
              "learn beta", "quiz", "quiz a", "challenge", "etf mkt100", "quote mkt100",
              "report", "next 99", "story", "whatif", "challenge crash", "next 99", "new 5"]
    errors = []
    for line in script:
        output = app.run_command(game, line, FakeAI())
        errors += [(line, r) for r in output if isinstance(r, str) and r.startswith("[red]✗")]
        for renderable in output:
            console.print(renderable)
    text = console.file.getvalue()
    assert errors == []
    assert "Laya: negative 55% (unsure)" in text
    assert "Score: keywords" in text and "Final report" in text
    assert "Robo-analyst" in text and "What-if Replay" in text and "Survive the Crash" in text


def test_grade_never_praises_a_loss_that_only_matched_the_market():
    """Bug 6: holding MKT100 through a crash (−10% vs the market's −10.07%) got 'A+ Superb'."""
    from tradesim.cli import views
    game = app.new_game(106, 60)
    app.execute(game, "buy MKT100 max")
    app.execute(game, "next 60")
    letter, _ = views.grade(game)
    assert letter in ("C", "D")             # a loss level with the market is not an A


def test_grade_b_for_losing_clearly_less_than_the_market():
    from tradesim.cli import views
    game = app.new_game(104, 60)             # a falling market (re-picked for the 100-stock universe)
    app.execute(game, "buy DEF4 40")         # mostly cash, a little defensive fund
    app.execute(game, "next 60")
    market = game.market.price("MKT100", 60) / 100 - 1
    mine = game.portfolio.total_return_pct(game.current_prices()) / 100
    assert mine < 0 and mine > market + 0.01
    assert views.grade(game)[0] == "B"


def test_final_report_counts_the_last_day_badges():
    game = app.new_game(42, 60)
    app.execute(game, "buy mkt100 10")
    output = app.execute(game, "next 99")
    finisher = next(i for i, r in enumerate(output) if "Finisher" in str(getattr(r, "plain", r)))
    report = next(i for i, r in enumerate(output) if "Final report" in str(getattr(r, "title", "")))
    assert finisher < report and "finisher" in game.badges


# ---------------------------------------------------------------- games (saved games, D-46)

def test_games_with_nothing_saved_says_how_to_start(game, tmp_path):
    (text,) = app.execute(game, "games", None, tmp_path / "player.db")
    assert "No saved games" in text


def test_games_lists_saved_games_with_results_and_badges(game, tmp_path):
    db = tmp_path / "player.db"
    savegame.start_game(db, "agent", app.new_game(5, 10))              # still being played
    finished = app.new_game(6, 5)
    finished_id = savegame.start_game(db, "web", finished)
    app.execute(finished, "buy NVDA 1")
    app.execute(finished, "next 5")
    savegame.record(db, finished_id, finished)
    console = Console(file=io.StringIO(), width=120, color_system=None)
    console.print(*app.execute(game, "games", None, db))
    text = console.file.getvalue()
    assert "Free play, seed 5" in text and "▶ playing now" in text
    assert "Free play, seed 6" in text and "🏁 finished" in text
    assert f"Badges won across games: {len(finished.badges)} /" in text


def test_games_needs_a_database(game):
    with pytest.raises(TradeSimError, match="Saved games"):
        app.execute(game, "games", None, None)
