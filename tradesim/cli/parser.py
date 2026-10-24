"""Turn a line of user input into a Command, checking only its shape (docs/04 §4.1)."""

import difflib

from tradesim import config
from tradesim.engine.errors import CommandError

MAX = "max"   # buy SYMBOL max
ALL = "all"   # sell SYMBOL all

# name → (usage line, one-line description). The commands the web page sends (and a saved game
# replays), plus a few "visit" commands that only record that a page was opened (for badges).
COMMANDS = {
    "buy": ("buy SYMBOL QTY", "Buy shares, e.g. buy AAPL 10 or buy MIX6 max"),
    "sell": ("sell SYMBOL QTY", "Sell shares, e.g. sell AAPL 5 or sell AAPL all"),
    "next": ("next [N]", "Advance 1 or N trading days, e.g. next 5"),
    "tick": ("tick [N]", "Let today's session run N five-minute ticks (the day closes after 78)"),
    "leverage": ("leverage [N]", "Set how much you may borrow, e.g. leverage 2"),
    "levlab": ("levlab", "Visit the Leverage Lab"),
    "news": ("news", "Visit the News page"),
    "lab": ("lab [mc [STOCK]]", "Visit the Diversification Lab, or run 200 markets (lab mc NVDA)"),
    "headlines": ('hl "TEXT"', "Headline Lab: what does the word counter say about your headline?"),
    "robo": ("robo", "Visit the Robo-analyst"),
    "whatif": ("whatif", "Visit the What-if Replay"),
    "challenge": ("challenge NAME", "Start a challenge, e.g. challenge crash"),
    "quiz": ("quiz [A-D]", "Answer the current quiz question, e.g. quiz B"),
    "new": ("new [SEED]", "Start a new free-play game (optionally a seed)"),
}
# Short names that older saved games may hold (savegame replays the lines it stored).
ALIASES = {"b": "buy", "s": "sell", "n": "next", "hl": "headlines", "bot": "robo",
           "replay": "whatif", "wi": "whatif", "ch": "challenge", "challenges": "challenge",
           "wait": "tick", "t": "tick", "lev": "leverage", "margin": "leverage", "ll": "levlab"}


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
    # isdecimal, not isdigit: "²".isdigit() is True but int("²") fails
    if not word.isdecimal() or int(word) == 0:
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
    """next [N] / tick [N] / new [SEED] / leverage [N]: zero or one whole number."""
    if len(args) > 1:
        raise usage_error(name)
    if args and not args[0].isdecimal():
        raise CommandError(f"{args[0]} is not a whole number. {usage_error(name)}")
    return [int(word) for word in args]


def lab_args(name: str, args: list[str]) -> list:
    """lab, or lab MC [STOCK]."""
    if len(args) > 2:
        raise usage_error(name)
    return args


def optional_word(name: str, args: list[str]) -> list:
    """challenge [NAME] / quiz [LETTER]: zero or one word, lower-case."""
    if len(args) > 1:
        raise usage_error(name)
    return [word.lower() for word in args]


def parse_headline_text(line: str) -> list[str]:
    """hl "TEXT" → [TEXT] with quotes removed and original case kept."""
    if len(line.split()) == 1:
        raise usage_error("headlines")
    text = line.strip().split(maxsplit=1)[1].strip('"').strip("'").strip()
    if not text:
        raise usage_error("headlines")
    if len(text) > config.MAX_HEADLINE_LENGTH:
        raise CommandError(f"Headlines must be {config.MAX_HEADLINE_LENGTH} characters or fewer.")
    return [text]


ARG_CHECKERS = {
    "buy": symbol_and_qty,
    "sell": symbol_and_qty,
    "next": optional_number,
    "tick": optional_number,
    "leverage": optional_number,
    "lab": lab_args,
    "challenge": optional_word,
    "quiz": optional_word,
    "new": optional_number,
}
