"""E-05 Headline Lab logic, with a fake classifier (never the real model)."""

import pytest

from tradesim import config
from tradesim.education import headline_lab as hl
from tradesim.engine.events import MarketEvent
from tradesim.loader import load_events


@pytest.fixture
def words(universe):
    stocks, _etfs = universe
    catalogue = load_events(config.EVENTS_PATH, stocks)
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


def test_score_with_fake_classifier_counts_hits(words):
    events = [event("Walmart sales not as bad as feared", 0.05),
              event("Chip export curbs hit tech stocks", -0.08)]
    answers = {"Walmart sales not as bad as feared": hl.Verdict(hl.POSITIVE, 0.61, "laya"),
               "Chip export curbs hit tech stocks": hl.Verdict(hl.POSITIVE, 0.55, "laya")}
    result = hl.score(events, answers.get, *words)
    assert (result.keyword_hits, result.ai_hits) == (1, 1)
    assert result.lessons() == ["Simple headlines are easy. Watch the tricky ones."]
    assert result.rows[1].ai.is_unsure()


def test_ai_beating_counter_gives_whole_sentence_lesson(words):
    events = [event("Walmart sales not as bad as feared", 0.05)]
    result = hl.score(events, lambda text: hl.Verdict(hl.POSITIVE, 0.9, "laya"), *words)
    assert "whole sentence" in result.lessons()[0]


def test_offline_classifier_gives_keyword_only_result(words):
    events = [event("Chip export curbs hit tech stocks", -0.08)]
    result = hl.score(events, lambda text: None, *words)
    assert result.ai_hits == 0 and not result.ai_online
    assert result.lessons() == ["AI offline: keyword counter only."]
