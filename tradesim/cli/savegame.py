"""Saved games in the player database (D-46): a game is its seed plus the commands that changed it.

Loading rebuilds the market from the seed and replays those commands through app.execute, which
gives back the exact same game because the same seed always makes the same market (D-08, D-26).
Prices and cash are never stored, so they can't be edited. The web app saves here.
"""

from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3

from tradesim.cli import app, parser
from tradesim.database import open_player
from tradesim.education import challenges
from tradesim.engine import analytics
from tradesim.engine.errors import TradeSimError
from tradesim.engine.game import Game
from tradesim.loader import load_challenges

# Only these change the game, so only these are replayed (market, lab, ... just look).
STATE_COMMANDS = {"buy", "sell", "next", "quiz", "tick", "leverage"}
# These throw the old game away: the next game starts a new row (the old one stays in `history`).
RESTART_COMMANDS = {"new", "challenge"}


def damaged(slot: str) -> TradeSimError:
    """The one error shown for a saved game that can't be rebuilt."""
    return TradeSimError(f"Saved game '{slot}' is damaged. Start with --seed N for a new game, "
                         "or delete saves/player.db.")


def load_game(db_path: Path, slot: str) -> tuple[Game, int] | None:
    """Rebuild the current game of `slot` by replaying its commands; None if there isn't one."""
    with closing(open_player(db_path)) as db:
        row = db.execute("SELECT id, seed, days, challenge FROM games WHERE slot = ?", (slot,)).fetchone()
        if row is None:
            return None
        lines = [r["line"] for r in db.execute(
            "SELECT line FROM commands WHERE game_id = ? ORDER BY position", (row["id"],))]
        badges = [r["badge_id"] for r in db.execute(
            "SELECT badge_id FROM badges WHERE game_id = ? ORDER BY rowid", (row["id"],))]
    try:
        challenge = load_challenges()[row["challenge"]] if row["challenge"] else None
        game = app.new_game(row["seed"], row["days"], challenge)
        for line in lines:
            app.execute(game, line)
    except (TradeSimError, KeyError):
        raise damaged(slot)   # a stored command that fails now means the database was edited
    # Badges for looking (lab, robo, news…) aren't replayed, because only state commands are stored.
    game.badges += [badge for badge in badges if badge not in game.badges]
    return game, row["id"]


def start_game(db_path: Path, slot: str, game: Game) -> int:
    """Make `game` the current game of `slot` and return its id. The game it replaces is kept."""
    challenge = game.challenge.id if game.challenge else None
    with closing(open_player(db_path)) as db, db:          # `with db` = one transaction
        db.execute("UPDATE games SET slot = NULL WHERE slot = ?", (slot,))
        cursor = db.execute(
            "INSERT INTO games (slot, seed, days, challenge, started_at) VALUES (?, ?, ?, ?, ?)",
            (slot, game.market.seed, game.market.num_days, challenge,
             datetime.now().isoformat(timespec="seconds")))
        write_summary(db, cursor.lastrowid, game)
    return cursor.lastrowid


def record(db_path: Path, game_id: int, game: Game, line: str | None = None) -> None:
    """Save the command `line` that just changed `game` (if any) and refresh the game's summary."""
    with closing(open_player(db_path)) as db, db:
        if line is not None:
            count = db.execute("SELECT COUNT(*) FROM commands WHERE game_id = ?", (game_id,)).fetchone()[0]
            db.execute("INSERT INTO commands VALUES (?, ?, ?)", (game_id, count, line))
        write_summary(db, game_id, game)


def save_after(db_path: Path, slot: str, game: Game, game_id: int | None, line: str) -> int | None:
    """Save what the command `line` just did to `game` and return the game's id.

    `game_id` is None for a game that has never been saved; it is saved once a command changes it.
    """
    command = parser.parse(line)
    name = command.name if command else None
    restarted = name in RESTART_COMMANDS and bool(command.args or name == "new")
    changed = name in STATE_COMMANDS
    if restarted or (game_id is None and changed):
        game_id = start_game(db_path, slot, game)
    if changed:
        record(db_path, game_id, game, line)
    return game_id


def write_summary(db: sqlite3.Connection, game_id: int, game: Game) -> None:
    """Update the numbers `history` shows, and remember every badge the game has won so far."""
    index = game.market.index_symbol()
    market_return = analytics.total_return(game.market.history(index, 0, game.day))
    right, answered = sum(game.quiz_results), len(game.quiz_results)
    won = challenges.is_won(game) if game.challenge and game.is_over() else None   # None = not decided yet
    db.execute("UPDATE games SET day = ?, equity = ?, market_return = ?, fees = ?, over = ?, passed = ?, "
               "quiz_right = ?, quiz_answered = ? WHERE id = ?",
               (game.day, game.equity(), market_return, game.portfolio.fees_paid, game.is_over(), won,
                right, answered, game_id))
    db.executemany("INSERT OR IGNORE INTO badges VALUES (?, ?)", [(game_id, badge) for badge in game.badges])
