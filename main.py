"""TradeSim entry point: parse command-line options, then start the game.

    uv run main.py --seed 42          play in the terminal (REPL)
    uv run main.py --web              play in the browser: http://127.0.0.1:8000
    uv run main.py --seed 42 market   agent mode: run one command on the saved 'agent' game and exit
"""

import argparse
import sys
from pathlib import Path

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
from tradesim.cli import agent, app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Read --seed, --days, --game and the optional one-shot command from the command line."""
    parser = argparse.ArgumentParser(description="TradeSim — a trading simulator that teaches diversification.")
    parser.add_argument("--seed", type=int, default=None, help="replay the same market (e.g. --seed 42)")
    parser.add_argument("--days", type=int, default=config.GAME_DAYS, help="game length in trading days")
    parser.add_argument("--game", default=config.AGENT_SLOT,
                        help="agent mode: the name of the saved game to continue (default agent)")
    parser.add_argument("--db", type=Path, default=config.PLAYER_DB_PATH,
                        help="the player database holding saved games (default saves/player.db)")
    parser.add_argument("--web", action="store_true", help="start the web app (price board, live trading)")
    parser.add_argument("--port", type=int, default=config.WEB_PORT, help="web app port (default 8000)")
    parser.add_argument("--no-browser", action="store_true", help="web app: don't open a browser tab")
    parser.add_argument("command", nargs="*",
                        help="agent mode: run one command and exit, e.g. buy NVDA 20")
    args = parser.parse_args(argv)
    if args.days < 1:
        parser.error("--days must be at least 1")
    return args


def main() -> None:
    """Run one agent command if one was given, otherwise start the interactive game."""
    args = parse_args()
    if args.web:
        from tradesim.webapp import server   # imported here so the terminal game starts fast
        server.serve(args.seed, args.days, args.port, not args.no_browser, args.db)
        return
    if args.command:
        sys.exit(agent.run_once(args.db, args.game, args.seed, args.days, " ".join(args.command),
                                SentimentClassifier()))
    app.run(args.seed, args.days)


if __name__ == "__main__":
    main()
