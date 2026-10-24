"""TradeSim entry point: parse command-line options, then start the web app.

    python3 main.py                  play at http://127.0.0.1:8000 (a random market, or your last game)
    python3 main.py --seed 42        start a fresh game with a reproducible market
"""

import argparse
from pathlib import Path

from tradesim import config
from tradesim.cli import app
from tradesim.webapp import server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Read --seed, --days, --port, --no-browser and --db from the command line."""
    parser = argparse.ArgumentParser(description="TradeSim — a trading simulator that teaches diversification.")
    parser.add_argument("--seed", type=int, default=None, help="start a new game with the same market every time (e.g. --seed 42)")
    parser.add_argument("--days", type=int, default=config.GAME_DAYS, help="game length in trading days")
    parser.add_argument("--port", type=int, default=config.WEB_PORT, help="web app port (default 8000)")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    parser.add_argument("--db", type=Path, default=config.PLAYER_DB_PATH,
                        help="the player database holding saved games (default saves/player.db)")
    args = parser.parse_args(argv)
    if args.days < 1:
        parser.error("--days must be at least 1")
    if args.seed is not None and not 0 <= args.seed < app.MAX_SEED:
        parser.error(f"--seed must be from 0 to {app.MAX_SEED - 1}")
    return args


def main() -> None:
    """Start the web app."""
    args = parse_args()
    server.serve(args.seed, args.days, args.port, not args.no_browser, args.db)


if __name__ == "__main__":
    main()
