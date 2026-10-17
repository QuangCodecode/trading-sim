"""ai/sentiment.py with a fake model: cache, fallbacks and the AI-never-moves-prices guard."""

import json

import pytest

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
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
    return tmp_path / "cache.json", model_dir


def make(paths, model):
    cache_path, model_dir = paths
    return SentimentClassifier(cache_path, model_dir, load_model=lambda folder: model)


def test_cache_hit_never_touches_the_model(paths):
    cache_path, _model_dir = paths
    cache_path.write_text(json.dumps({"Hello": {"label": "negative", "confidence": 0.8}}))
    model = FakeModel()
    verdict = make(paths, model).classify("Hello")
    assert (verdict.label, verdict.confidence, model.calls) == ("negative", 0.8, 0)


def test_miss_asks_model_once_then_saves_cache(paths):
    model = FakeModel()
    classifier = make(paths, model)
    assert classifier.classify("News").label == "positive"
    assert classifier.classify("News").confidence == 0.9
    assert model.calls == 1
    assert json.loads(paths[0].read_text())["News"]["label"] == "positive"


def test_missing_model_folder_means_offline(tmp_path):
    classifier = SentimentClassifier(tmp_path / "c.json", tmp_path / "nope",
                                     load_model=lambda folder: FakeModel())
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
    assert SentimentClassifier(cache_path, model_dir, load_model=explode).classify("x") is None


def test_corrupt_cache_is_treated_as_empty_and_rewritten(paths):
    paths[0].write_text("{not json")
    classifier = make(paths, FakeModel())
    assert classifier.cache == {}
    classifier.classify("News")
    assert "News" in json.loads(paths[0].read_text())


def test_ai_never_changes_prices(universe, paths):
    stocks, etfs = universe
    catalogue = load_events(config.EVENTS_PATH, stocks)
    market = Market(stocks, etfs, 42, 60, catalogue.templates)
    before = {s: market.history(s, 0, 60) for s in market.symbols()}
    events = [e for day in range(1, 61) for e in market.events_on(day)]
    headline_lab.score(events, make(paths, FakeModel()).classify,
                       catalogue.positive_words, catalogue.negative_words)
    assert {s: market.history(s, 0, 60) for s in market.symbols()} == before


def test_shipped_cache_covers_every_event_headline(universe):
    stocks, _etfs = universe
    catalogue = load_events(config.EVENTS_PATH, stocks)
    classifier = SentimentClassifier(load_model=lambda folder: None)
    missing = [t["headline"] for t in catalogue.templates if classifier.cached(t["headline"]) is None]
    assert missing == [], "run: python3 tools/warm_cache.py"
