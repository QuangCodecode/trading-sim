"""cli/parser.py: shape checks only."""

import pytest

from tradesim.cli.parser import ALL, MAX, Command, parse
from tradesim.engine.errors import CommandError


def test_case_insensitive_buy():
    assert parse("Buy aapl 10") == Command("buy", ["AAPL", 10])


def test_max_and_all_keywords():
    assert parse("buy AAPL max") == Command("buy", ["AAPL", MAX])
    assert parse("sell AAPL ALL") == Command("sell", ["AAPL", ALL])


@pytest.mark.parametrize("line", ["buy AAPL 10.5", "buy AAPL -1", "buy AAPL 0",
                                  "buy AAPL ten", "buy AAPL", "sell AAPL max",
                                  "buy AAPL ²"])        # Bug 24: "²".isdigit() is True
def test_bad_buy_sell_shapes_rejected(line):
    with pytest.raises(CommandError):
        parse(line)


def test_typo_suggests_command():
    with pytest.raises(CommandError, match='Did you mean "buy"'):
        parse("biy AAPL 1")


def test_blank_line_ignored():
    assert parse("   ") is None


def test_aliases():
    assert parse("n 5") == Command("next", [5])
    assert parse("b nvda 10") == Command("buy", ["NVDA", 10])
    assert parse("lev 2") == Command("leverage", [2])


@pytest.mark.parametrize("line", ["next abc", "next -2", "next 1 2", "robo now", "next ³"])
def test_bad_next_and_extra_args_rejected(line):
    with pytest.raises(CommandError):
        parse(line)


def test_lab_variants():
    assert parse("lab") == Command("lab", [])
    assert parse("lab mc nvda") == Command("lab", ["MC", "NVDA"])
    with pytest.raises(CommandError):
        parse("lab mc nvda mix6")


def test_headline_text_keeps_case_and_drops_quotes():
    assert parse('hl "Walmart sales not as bad as feared"') == \
        Command("headlines", ["Walmart sales not as bad as feared"])
    with pytest.raises(CommandError, match="Usage: hl"):
        parse("headlines")


def test_empty_quoted_headline_shows_usage():
    with pytest.raises(CommandError, match="Usage: hl"):
        parse('hl ""')


def test_headline_too_long_rejected():
    with pytest.raises(CommandError, match="200"):
        parse("hl " + "x" * 201)
