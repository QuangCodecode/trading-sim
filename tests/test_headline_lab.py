"""E-05 Headline Lab logic: the keyword counter and the real outcome of a headline."""

import pytest

from tradesim.education import headline_lab as hl
from tradesim.engine.events import MarketEvent
from tradesim.loader import load_events


@pytest.fixture
def words(universe):
    stocks, _etfs = universe
    catalogue = load_events(stocks)
    return catalogue.positive_words, catalogue.negative_words


def event(headline, shock):
    return MarketEvent(1, headline, "", "market", "ALL", shock)


def test_plain_negative_headline(words):
    assert hl.keyword_verdict("Chip export curbs hit tech stocks", *words).label == hl.NEGATIVE


def test_tricky_headlines_fool_the_counter_on_purpose(words):
    # These document the counter's weakness — they are the Lab's teaching moments.
    assert hl.keyword_verdict("Walmart sales not as bad as feared", *words).label == hl.NEGATIVE
    assert hl.keyword_verdict("Oil glut fears ease as demand recovers", *words).label == hl.NEGATIVE
    assert hl.keyword_verdict("Record highs fail to hold as chip rally fizzles", *words).label == hl.POSITIVE


def test_counter_shows_which_words_it_counted(words):
    verdict = hl.keyword_verdict("Walmart sales not as bad as feared!", *words)
    assert verdict.reason == "bad −, feared −"
    assert hl.keyword_verdict("Walmart opens a store", *words).label == hl.NEUTRAL


def test_truth_is_sign_of_shock():
    assert hl.truth(event("x", 0.04)) == hl.POSITIVE
    assert hl.truth(event("x", -0.01)) == hl.NEGATIVE
