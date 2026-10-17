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
                                  "buy AAPL ten", "buy AAPL", "sell AAPL max"])
def test_bad_buy_sell_shapes_rejected(line):
    with pytest.raises(CommandError):
        parse(line)


def test_typo_suggests_command():
    with pytest.raises(CommandError, match='Did you mean "buy"'):
        parse("biy AAPL 1")


def test_blank_line_ignored():
    assert parse("   ") is None


def test_aliases():
    assert parse("pf") == Command("portfolio", [])
    assert parse("n 5") == Command("next", [5])
    assert parse("? buy") == Command("help", ["buy"])


@pytest.mark.parametrize("line", ["next abc", "next -2", "next 1 2", "market now"])
def test_bad_next_and_extra_args_rejected(line):
    with pytest.raises(CommandError):
        parse(line)


def test_lab_variants():
    assert parse("lab") == Command("lab", [])
    assert parse("lab ko") == Command("lab", ["KO"])
    assert parse("lab mc nvda") == Command("lab", ["MC", "NVDA"])


def test_headline_text_keeps_case_and_drops_quotes():
    assert parse('hl "Walmart sales not as bad as feared"') == \
        Command("headlines", ["Walmart sales not as bad as feared"])
    assert parse("headlines") == Command("headlines", [])
    assert parse('hl ""') == Command("headlines", [])


def test_headline_too_long_rejected():
    with pytest.raises(CommandError, match="200"):
        parse("hl " + "x" * 201)
