"""TradeSim entry point: parse command-line options, then start the game."""

import argparse

from tradesim import config
from tradesim.cli import app


def parse_args() -> argparse.Namespace:
    """Read --seed and --days from the command line."""
    parser = argparse.ArgumentParser(description="TradeSim — a trading simulator that teaches diversification.")
    parser.add_argument("--seed", type=int, default=None, help="replay the same market (e.g. --seed 42)")
    parser.add_argument("--days", type=int, default=config.GAME_DAYS, help="game length in trading days")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days must be at least 1")
    return args


def main() -> None:
    """Start the game."""
    args = parse_args()
    app.run(args.seed, args.days)


if __name__ == "__main__":
    main()
