"""ai/sentiment.py with a fake model: cache, fallbacks and the AI-never-moves-prices guard."""

import sqlite3
from contextlib import closing

import pytest

from tradesim.ai.sentiment import SentimentClassifier, read_labels
from tradesim.database import SENTIMENT_TABLE
from tradesim.education import headline_lab
from tradesim.engine.market import Market
from tradesim.loader import load_events


class FakeModel:
    """Stands in for Laya: answers 'positive 0.9' and counts how often it was asked."""

    def __init__(self):
        self.calls = 0

    def predict(self, headline, questions):
        self.calls += 1
        return {"answers": {"sentiment": {"choice": "positive",
                                          "probabilities": {"positive": 0.9, "negative": 0.1}}}}


@pytest.fixture
def paths(tmp_path):
    model_dir = tmp_path / "laya"
    model_dir.mkdir()
    return tmp_path / "cache.db", model_dir


def make(paths, model, seed_path=None):
    """A classifier with a temp cache and, unless asked, no shipped answers to find."""
    cache_path, model_dir = paths
    return SentimentClassifier(cache_path, model_dir, load_model=lambda folder: model, seed_path=seed_path)


def put(path, headline, label, confidence):
    """Write one answer into a sentiment table, the way a previous game would have."""
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(SENTIMENT_TABLE)
        db.execute("INSERT INTO sentiment VALUES (?, ?, ?)", (headline, label, confidence))


def test_cache_hit_never_touches_the_model(paths):
    cache_path, _model_dir = paths
    put(cache_path, "Hello", "negative", 0.8)
    model = FakeModel()
    verdict = make(paths, model).classify("Hello")
    assert (verdict.label, verdict.confidence, model.calls) == ("negative", 0.8, 0)


def test_miss_asks_model_once_then_saves_cache(paths):
    model = FakeModel()
    classifier = make(paths, model)
    assert classifier.classify("News").label == "positive"
    assert classifier.classify("News").confidence == 0.9
    assert model.calls == 1
    assert read_labels(paths[0])["News"]["label"] == "positive"


def test_missing_model_folder_means_offline(tmp_path):
    classifier = SentimentClassifier(tmp_path / "c.db", tmp_path / "nope",
                                     load_model=lambda folder: FakeModel(), seed_path=None)
    assert classifier.classify("News") is None
    assert classifier.offline


def test_model_that_crashes_or_answers_oddly_gives_none(paths):
    class Broken:
        def predict(self, headline, questions):
            return {"answers": {}}
    classifier = make(paths, Broken())
    assert classifier.classify("News") is None
    assert classifier.classify("More news") is None  # stays offline, no retry storm


def test_loader_raising_gives_none(paths):
    def explode(folder):
        raise ImportError("No module named 'laya'")
    cache_path, model_dir = paths
    assert SentimentClassifier(cache_path, model_dir, load_model=explode, seed_path=None).classify("x") is None


def test_corrupt_cache_is_treated_as_empty_and_the_answer_still_comes(paths):
    paths[0].write_bytes(b"not a database " * 20)
    classifier = make(paths, FakeModel())
    assert classifier.cache == {}
    assert classifier.classify("News").label == "positive"   # the cache just can't be saved


def test_shipped_answers_are_read_but_new_ones_never_written_to_them(paths, tmp_path):
    shipped = tmp_path / "reference.db"
    put(shipped, "Old news", "negative", 0.7)
    model = FakeModel()
    classifier = make(paths, model, seed_path=shipped)
    assert classifier.classify("Old news").label == "negative" and model.calls == 0
    classifier.classify("New news")
    assert "New news" in read_labels(paths[0]) and "New news" not in read_labels(shipped)


def test_ai_never_changes_prices(universe, paths):
    stocks, etfs = universe
    catalogue = load_events(stocks)
    market = Market(stocks, etfs, 42, 60, catalogue.templates)
    before = {s: market.history(s, 0, 60) for s in market.symbols()}
    events = [e for day in range(1, 61) for e in market.events_on(day)]
    headline_lab.score(events, make(paths, FakeModel()).classify,
                       catalogue.positive_words, catalogue.negative_words)
    assert {s: market.history(s, 0, 60) for s in market.symbols()} == before


def test_shipped_cache_covers_every_event_headline(universe):
    stocks, _etfs = universe
    catalogue = load_events(stocks)
    classifier = SentimentClassifier(load_model=lambda folder: None)   # reads the real reference.db
    missing = [t["headline"] for t in catalogue.templates if classifier.cached(t["headline"]) is None]
    assert missing == [], "run: python3 tools/warm_cache.py"
