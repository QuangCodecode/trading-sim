"""Agent mode (X-06): run ONE command, print plain text, exit. Lets an AI agent play from a shell.

The game lives in the player database (cli/savegame.py): the seed, the length and the commands
that changed it. Each call rebuilds the game by replaying them, runs one more command and saves.
"""

from pathlib import Path

from rich.console import Console

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
from tradesim.cli import app, savegame, views
from tradesim.engine.errors import TradeSimError
from tradesim.engine.game import Game


def open_game(db_path: Path, slot: str, seed: int | None, days: int) -> tuple[Game, int | None]:
    """The saved game and its id, or a new unsaved game (id None) with `seed`/`days`."""
    loaded = savegame.load_game(db_path, slot)
    if loaded is None:
        return app.new_game(seed, days), None
    game, game_id = loaded
    if seed is not None and seed != game.market.seed:
        raise TradeSimError(f"The '{slot}' game is a seed {game.market.seed} game. Start another with "
                            f"`new {seed}`, or use --game NAME for a second game.")
    return game, game_id


def status_line(game: Game) -> str:
    """Day, cash and seed, printed first so the agent always knows where it is."""
    return (f"{views.day_line(game)} · Cash {views.money(game.portfolio.cash)} · "
            f"Equity {views.money(game.equity())} · Seed {game.market.seed}")


def run_once(db_path: Path, slot: str, seed: int | None, days: int, line: str,
             ai: SentimentClassifier | None = None) -> int:
    """Run one command on the saved game and print the result. Returns the exit code (0 ok, 1 error)."""
    console = Console(color_system=None, width=config.AGENT_WIDTH)
    try:
        game, game_id = open_game(db_path, slot, seed, days)
        output = app.execute(game, line, ai, db_path)   # a failed command raises before anything is saved
        # `help` before `--seed 42 market` must not lock in a random seed, so a new game is only
        # saved once something changed it or the seed was chosen on purpose.
        savegame.save_after(db_path, slot, game, game_id, line, save_new=seed is not None)
    except TradeSimError as error:
        console.print(f"✗ {error}", markup=False)
        return 1
    console.print(status_line(game))
    for renderable in output:
        console.print(renderable)
    return 0
