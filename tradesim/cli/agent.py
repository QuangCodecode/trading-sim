"""Agent mode (X-06): run ONE command, print plain text, exit. Lets an AI agent play from a shell.

The game file stores only the seed, the length and the commands that changed the game.
Loading rebuilds the market from the seed and replays those commands, which gives back the
exact same game because the same seed always makes the same market (D-08, D-26).
"""

import json
from pathlib import Path

from rich.console import Console

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
from tradesim.cli import app, parser, views
from tradesim.engine.errors import TradeSimError
from tradesim.engine.game import Game
from tradesim.loader import load_challenges

# Only these change the game, so only these are replayed (market, lab, ... just look).
STATE_COMMANDS = {"buy", "sell", "next", "quiz", "tick", "leverage"}
# These throw the old game away: the file is rewritten for the new one.
RESTART_COMMANDS = {"new", "challenge"}


def damaged(path: Path) -> TradeSimError:
    """The one error shown for any unreadable game file."""
    return TradeSimError(f"Game file {path} is damaged — delete it to start a new game.")


def read_state(path: Path) -> dict:
    """The saved {version, seed, days, commands} dict, checked key by key."""
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        ok = (state["version"] == config.AGENT_GAME_VERSION
              and isinstance(state["seed"], int) and isinstance(state["days"], int)
              and state["days"] >= 1 and isinstance(state["commands"], list)
              and all(isinstance(line, str) for line in state["commands"])
              and isinstance(state.get("challenge"), (str, type(None))))
    except (OSError, ValueError, KeyError, TypeError):
        ok = False
    if not ok:
        raise damaged(path)
    return state


def load_game(path: Path) -> tuple[Game, dict] | None:
    """Rebuild the saved game by replaying its commands; None if there is no file yet."""
    if not path.exists():
        return None
    state = read_state(path)
    try:
        challenge = None
        if state.get("challenge"):
            challenge = load_challenges(config.CHALLENGES_PATH)[state["challenge"]]
        game = app.new_game(state["seed"], state["days"], challenge)
        for line in state["commands"]:
            app.execute(game, line)
    except (TradeSimError, KeyError):
        raise damaged(path)  # a stored command that fails now means the file was edited
    return game, state


def fresh_state(game: Game) -> dict:
    """The game file for a game that has just started."""
    challenge = game.challenge.id if game.challenge else None
    return {"version": config.AGENT_GAME_VERSION, "seed": game.market.seed,
            "days": game.market.num_days, "challenge": challenge, "commands": []}


def save_game(path: Path, state: dict) -> None:
    """Write the game file, creating its folder the first time."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def open_game(path: Path, seed: int | None, days: int) -> tuple[Game, dict]:
    """The saved game, or a new one with `seed`/`days` if the file doesn't exist yet."""
    loaded = load_game(path)
    if loaded is None:
        game = app.new_game(seed, days)
        return game, fresh_state(game)
    game, state = loaded
    if seed is not None and seed != state["seed"]:
        raise TradeSimError(f"{path} is a seed {state['seed']} game. "
                            "Delete it to start a new game with another seed.")
    return game, state


def status_line(game: Game) -> str:
    """Day, cash and seed, printed first so the agent always knows where it is."""
    return (f"{views.day_line(game)} · Cash {views.money(game.portfolio.cash)} · "
            f"Equity {views.money(game.equity())} · Seed {game.market.seed}")


def run_once(path: Path, seed: int | None, days: int, line: str,
             ai: SentimentClassifier | None = None) -> int:
    """Run one command on the saved game and print the result. Returns the exit code (0 ok, 1 error)."""
    console = Console(color_system=None, width=config.AGENT_WIDTH)
    try:
        game, state = open_game(path, seed, days)
        output = app.execute(game, line, ai)
    except TradeSimError as error:
        console.print(f"✗ {error}", markup=False)
        return 1  # nothing is saved, so a failed command never changes the game
    command = parser.parse(line)
    changed = command is not None and command.name in STATE_COMMANDS
    if changed:
        state["commands"].append(line)
    if command is not None and command.name in RESTART_COMMANDS and (command.args or command.name == "new"):
        state, changed = fresh_state(game), True
    if changed or seed is not None:
        save_game(path, state)  # so `help` before `--seed 42 market` doesn't lock in a random seed
    console.print(status_line(game))
    for renderable in output:
        console.print(renderable)
    return 0
