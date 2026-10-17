"""Read and validate data/*.json files into engine objects."""

import json
from pathlib import Path

from tradesim.engine.errors import DataFileError
from tradesim.engine.etf import ETF
from tradesim.engine.events import SCOPES
from tradesim.engine.stock import Stock

WEIGHT_TOLERANCE = 1e-9


def read_json(path: Path) -> dict:
    """Return the parsed JSON object at `path`, or raise DataFileError naming the file."""
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise DataFileError(f"Data file not found: {path}")
    except json.JSONDecodeError as error:
        raise DataFileError(f"{path} is not valid JSON: {error}")


def load_universe(path: Path) -> tuple[dict[str, Stock], dict[str, ETF]]:
    """Load stocks and ETFs from `path`, checking every rule in finance model §3.1."""
    data = read_json(path)
    try:
        stocks = {}
        for row in data["stocks"]:
            stock = Stock(row["symbol"], row["name"], row["sector"],
                          float(row["start_price"]), float(row["drift"]),
                          float(row["volatility"]))
            _check_stock(stock, stocks)
            stocks[stock.symbol] = stock
        etfs = {}
        for row in data["etfs"]:
            etf = ETF(row["symbol"], row["name"], dict(row["weights"]),
                      float(row["base_value"]))
            _check_etf(etf, stocks, etfs)
            etfs[etf.symbol] = etf
    except (KeyError, TypeError, ValueError) as error:
        raise DataFileError(f"{path} has a missing or bad field: {error}")
    return stocks, etfs


def _check_stock(stock: Stock, seen: dict[str, Stock]) -> None:
    """Raise DataFileError if this stock breaks a universe rule."""
    if stock.symbol in seen:
        raise DataFileError(f"Duplicate symbol {stock.symbol}")
    if stock.symbol != stock.symbol.upper():
        raise DataFileError(f"Symbol {stock.symbol} must be upper-case")
    if stock.start_price <= 0:
        raise DataFileError(f"{stock.symbol} start_price must be > 0")
    if stock.volatility < 0:
        raise DataFileError(f"{stock.symbol} volatility must be >= 0")


def _check_etf(etf: ETF, stocks: dict[str, Stock], seen: dict[str, ETF]) -> None:
    """Raise DataFileError if this ETF's symbol or weights break a universe rule."""
    if etf.symbol in stocks or etf.symbol in seen:
        raise DataFileError(f"Duplicate symbol {etf.symbol}")
    for symbol, weight in etf.weights.items():
        if symbol not in stocks:
            raise DataFileError(f"{etf.symbol} holds unknown symbol {symbol}")
        if weight <= 0:
            raise DataFileError(f"{etf.symbol} weight for {symbol} must be > 0")
    total = sum(etf.weights.values())
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise DataFileError(f"{etf.symbol} weights sum to {total}, not 1")


class EventCatalogue:
    """Everything in data/events.json: headline templates and the keyword counter's word lists."""

    def __init__(self, templates: list[dict], positive_words: list[str],
                 negative_words: list[str]) -> None:
        """Store the validated templates and lower-cased word lists."""
        self.templates = templates
        self.positive_words = [word.lower() for word in positive_words]
        self.negative_words = [word.lower() for word in negative_words]

    def __repr__(self) -> str:
        return f"EventCatalogue({len(self.templates)} templates)"


def load_events(path: Path, stocks: dict[str, Stock]) -> EventCatalogue:
    """Load event templates, checking each target exists and its shock has one sign (§3.7)."""
    data = read_json(path)
    try:
        for template in data["templates"]:
            _check_template(template, stocks)
        return EventCatalogue(data["templates"], data["positive_words"], data["negative_words"])
    except (KeyError, TypeError) as error:
        raise DataFileError(f"{path} has a missing or bad field: {error}")


def _check_template(template: dict, stocks: dict[str, Stock]) -> None:
    """Raise DataFileError if one event template breaks a rule."""
    name, scope, target = template["id"], template["scope"], template["target"]
    sectors = {stock.sector for stock in stocks.values()}
    if scope not in SCOPES:
        raise DataFileError(f"Event {name}: unknown scope {scope}")
    if (scope == "stock" and target not in stocks) or (scope == "sector" and target not in sectors):
        raise DataFileError(f"Event {name}: unknown {scope} {target}")
    low, high = template["shock_min"], template["shock_max"]
    if low > high:
        raise DataFileError(f"Event {name}: shock_min is above shock_max")
    # The Headline Lab's "truth" is the shock's sign, so a range must not cross zero.
    if low < 0 < high or low == high == 0:
        raise DataFileError(f"Event {name}: shock range must be all positive or all negative")
    if not template["headline"]:
        raise DataFileError(f"Event {name}: empty headline")
