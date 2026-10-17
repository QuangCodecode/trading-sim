"""Turn a line of user input into a Command, checking only its shape (docs/04 §4.1)."""

import difflib

from tradesim import config
from tradesim.engine.errors import CommandError

MAX = "max"   # buy SYMBOL max
ALL = "all"   # sell SYMBOL all

# name → (usage line, one-line description). Order here is the order `help` shows.
COMMANDS = {
    "market": ("market", "Price table for every stock and the ETF"),
    "quote": ("quote SYMBOL", "Details for one symbol, e.g. quote NVDA"),
    "chart": ("chart SYMBOL [SYMBOL2]", "Price chart from day 0, e.g. chart NVDA MIX6"),
    "etf": ("etf [SYMBOL]", "What's inside the ETF and why that matters"),
    "buy": ("buy SYMBOL QTY", "Buy shares, e.g. buy AAPL 10 or buy MIX6 max"),
    "sell": ("sell SYMBOL QTY", "Sell shares, e.g. sell AAPL 5 or sell AAPL all"),
    "portfolio": ("portfolio", "Your holdings, cash and profit/loss"),
    "history": ("history", "Every trade you've made"),
    "next": ("next [N]", "Advance 1 or N trading days, e.g. next 5"),
    "news": ("news [DAY]", "Today's (or a past day's) news and how it moved the ETF"),
    "lab": ("lab [STOCK] [ETF]", "Diversification Lab: one stock vs the ETF (lab mc = 200 markets)"),
    "headlines": ('headlines  or  hl "TEXT"', "Headline Lab: can AI read the news better than word counting?"),
    "report": ("report", "Your results so far"),
    "help": ("help [COMMAND]", "List commands or explain one"),
    "quit": ("quit", "End the game and show the final report"),
}
ALIASES = {"?": "help", "h": "help", "m": "market", "q": "quote", "c": "chart",
           "b": "buy", "s": "sell", "pf": "portfolio", "p": "portfolio",
           "hist": "history", "n": "next", "hl": "headlines", "exit": "quit"}


class Command:
    """A parsed command: its canonical name and cleaned-up arguments."""

    def __init__(self, name: str, args: list) -> None:
        """Store the command name (e.g. "buy") and its arguments (e.g. ["AAPL", 10])."""
        self.name = name
        self.args = args

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Command) and (self.name, self.args) == (other.name, other.args)

    def __repr__(self) -> str:
        return f"Command({self.name!r}, {self.args!r})"


def parse(line: str) -> Command | None:
    """Parse one input line; return None for a blank line, raise CommandError if malformed."""
    words = line.split()
    if not words:
        return None
    name = resolve_name(words[0].lower())
    if name == "headlines":
        return Command(name, parse_headline_text(line))
    args = [word.upper() for word in words[1:]]
    checker = ARG_CHECKERS.get(name, no_args)
    return Command(name, checker(name, args))


def resolve_name(word: str) -> str:
    """Map a typed command or alias to its canonical name, suggesting one on a typo."""
    if word in COMMANDS:
        return word
    if word in ALIASES:
        return ALIASES[word]
    close = difflib.get_close_matches(word, list(COMMANDS) + list(ALIASES), n=1)
    hint = f' Did you mean "{resolve_name(close[0])}"?' if close else " Type help."
    raise CommandError(f'Unknown command "{word}".{hint}')


def usage_error(name: str) -> CommandError:
    """A CommandError showing the correct usage of `name`."""
    usage, description = COMMANDS[name]
    return CommandError(f"Usage: {usage}  — {description}")


def parse_quantity(word: str, keyword: str) -> int | str:
    """A positive whole number, or the keyword ("max"/"all") itself."""
    if word.lower() == keyword:
        return keyword
    if not word.isdigit() or int(word) == 0:
        raise CommandError("Quantity must be a whole number greater than 0.")
    return int(word)


def no_args(name: str, args: list[str]) -> list:
    """Commands that take nothing (extra words are a mistake)."""
    if args:
        raise usage_error(name)
    return []


def symbol_and_qty(name: str, args: list[str]) -> list:
    """buy/sell: exactly a symbol and a quantity."""
    if len(args) != 2:
        raise usage_error(name)
    keyword = MAX if name == "buy" else ALL
    return [args[0], parse_quantity(args[1], keyword)]


def optional_number(name: str, args: list[str]) -> list:
    """next [N] / news [DAY]: zero or one whole number."""
    if len(args) > 1:
        raise usage_error(name)
    if args and not args[0].isdigit():
        raise CommandError(f"{args[0]} is not a whole number. {usage_error(name)}")
    return [int(word) for word in args]


# How many symbols each symbol-only command accepts: (minimum, maximum).
SYMBOL_COUNTS = {"quote": (1, 1), "chart": (1, 2), "etf": (0, 1), "lab": (0, 2)}


def symbol_args(name: str, args: list[str]) -> list:
    """quote/chart/etf/lab: a number of symbols within SYMBOL_COUNTS[name]."""
    minimum, maximum = SYMBOL_COUNTS[name]
    if not minimum <= len(args) <= maximum:
        raise usage_error(name)
    return args


def optional_command(name: str, args: list[str]) -> list:
    """help [COMMAND]: the topic is resolved like a typed command."""
    if len(args) > 1:
        raise usage_error(name)
    return [resolve_name(word.lower()) for word in args]


def parse_headline_text(line: str) -> list[str]:
    """hl alone → []; hl "TEXT" → [TEXT] with quotes removed and original case kept."""
    text = line.strip().split(maxsplit=1)[1] if len(line.split()) > 1 else ""
    text = text.strip().strip('"').strip("'").strip()
    if not text:
        return []
    if len(text) > config.MAX_HEADLINE_LENGTH:
        raise CommandError(f"Headlines must be {config.MAX_HEADLINE_LENGTH} characters or fewer.")
    return [text]


ARG_CHECKERS = {
    "buy": symbol_and_qty,
    "sell": symbol_and_qty,
    "next": optional_number,
    "news": optional_number,
    "quote": symbol_args,
    "chart": symbol_args,
    "etf": symbol_args,
    "lab": symbol_args,
    "help": optional_command,
}
