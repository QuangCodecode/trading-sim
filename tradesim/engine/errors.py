"""Custom exceptions. The CLI catches TradeSimError and shows the message in red."""


class TradeSimError(Exception):
    """Base class for every rule violation the player can trigger."""


class UnknownSymbolError(TradeSimError):
    """A symbol that is not in the market."""


class InvalidQuantityError(TradeSimError):
    """A trade quantity that is not a whole number above 0."""


class InsufficientCashError(TradeSimError):
    """A buy that costs more than the cash available."""


class InsufficientSharesError(TradeSimError):
    """A sell of more shares than the player holds."""


class GameOverError(TradeSimError):
    """Trading or advancing after the final day."""


class CommandError(TradeSimError):
    """Raised by cli/parser.py when a command has the wrong shape."""


class DataFileError(TradeSimError):
    """A missing or invalid data/*.json file."""
