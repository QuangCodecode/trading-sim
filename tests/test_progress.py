"""Achievements (X-05), challenges (X-01) and the academy (glossary + quiz)."""

import pytest

from tradesim import config
from tradesim.cli import app
from tradesim.education import academy, achievements, challenges
from tradesim.engine import analytics
from tradesim.engine.errors import TradeSimError
from tradesim.loader import load_challenges, load_glossary, load_quiz


def test_badges_are_announced_once(game):
    game.buy("FUND", 5)
    first = [b.badge_id for b in achievements.newly_unlocked(game)]
    assert "first_trade" in first and "basket" in first
    assert achievements.newly_unlocked(game) == []


def test_command_badges_come_from_commands_used(game):
    app.execute(game, "next 5")
    assert "scientist" not in game.badges
    app.execute(game, "lab")
    assert "scientist" in game.badges


@pytest.fixture
def catalogue():
    return load_challenges()


@pytest.mark.parametrize("challenge_id", ["bull", "crash", "bear", "tech", "sideways", "index", "rollercoaster",
                                          "margin", "borrowed_bull"])
def test_every_challenge_market_still_tells_its_story(catalogue, challenge_id):
    """If the price model changes, a challenge seed may stop fitting its story: re-pick it."""
    challenge = catalogue[challenge_id]
    market = app.new_game(None, 0, challenge).market
    story = challenge.story
    if "regime" in story:
        assert story["regime"] in market.regime_path
    if "symbol" in story:
        result = analytics.total_return(market.history(story["symbol"], 0, challenge.days))
        low, high = story.get("return_between", [story.get("return_above", -1), story.get("return_below", 9)])
        assert low < result < high


def test_challenge_start_trades_are_made(catalogue):
    game = app.new_game(None, 0, catalogue["tech"])
    assert game.portfolio.qty_held("TECH3") > 0 and game.challenge.id == "tech"


def test_goals_pass_and_fail(catalogue):
    game = app.new_game(None, 0, catalogue["sideways"])
    checks = challenges.progress(game)
    assert [c.passed for c in checks] == [True, True]     # day 0: no loss, no fees
    assert not challenges.is_won(game)                    # only judged on the final day
    app.execute(game, "next 99")
    assert challenges.is_won(game)                        # did nothing: 0% return, $0 fees


def test_challenge_command_restarts_the_same_game_object():
    game = app.new_game(1, 60)
    app.execute(game, "next 3")
    app.execute(game, "challenge bull")
    assert game.day == 0 and game.market.seed == 47 and game.challenge.id == "bull"
    with pytest.raises(TradeSimError, match='Did you mean "challenge bull"'):
        app.execute(game, "challenge bul")


def test_new_command_starts_fresh():
    game = app.new_game(1, 60)
    app.execute(game, "buy nvda 1")
    app.execute(game, "new 7")
    assert game.market.seed == 7 and game.portfolio.trades == [] and game.challenge is None


def test_glossary_lookup_forgives_case_typos_and_partial_words():
    terms = load_glossary()
    assert academy.find_term(terms, "ETF")["term"] == "ETF"
    assert academy.find_term(terms, "bear")["term"] == "Bear market"
    assert academy.find_term(terms, "volatilty")["term"] == "Volatility"
    with pytest.raises(TradeSimError):
        academy.find_term(terms, "spaceship")


def test_quiz_marks_answers_and_rejects_bad_letters():
    questions = load_quiz()
    question = questions[0]
    right = academy.LETTERS[question["answer"]]
    assert academy.mark(question, right.lower())
    assert not academy.mark(question, "A" if right != "A" else "B")
    with pytest.raises(TradeSimError):
        academy.mark(question, "Z")


def test_quiz_answers_are_not_all_the_same_letter():
    answers = {q["answer"] for q in load_quiz()}
    assert len(answers) == 4


def test_quiz_command_counts_the_score():
    game = app.new_game(1, 60)
    question = load_quiz()[0]
    app.execute(game, f"quiz {academy.LETTERS[question['answer']]}")
    assert game.quiz_results == [True]


@pytest.mark.parametrize("goal, passes_in_cash", [
    ({"type": "min_equity", "value": 9_000}, True),
    ({"type": "min_return", "value": 0.05}, False),
    ({"type": "max_fees", "value": 0}, True),
    ({"type": "max_drawdown", "value": 0.10}, True),
    ({"type": "min_invested", "value": 0.5}, False),
])
def test_each_goal_type_on_an_all_cash_game(goal, passes_in_cash):
    game = app.new_game(42, 60)
    app.execute(game, "next 10")
    check = challenges.check_goal(game, goal)
    assert check.passed == passes_in_cash and check.text and check.now


def test_beat_goal_compares_with_buy_and_hold():
    game = app.new_game(15, 60)                     # a rising market: cash can't beat it
    app.execute(game, "next 30")
    assert not challenges.check_goal(game, {"type": "beat", "symbol": "MKT100"}).passed
    assert challenges.symbol_return(game, "MKT100") > 0
