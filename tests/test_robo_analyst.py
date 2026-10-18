"""E-06 Robo-analyst: the tiny logistic-regression models (pure Python, no network)."""

import math

import pytest

from tradesim import config
from tradesim.cli.app import new_game
from tradesim.education import robo_analyst as robo
from tradesim.loader import load_robo


def test_sigmoid_is_a_probability_and_never_overflows():
    assert robo.sigmoid(0) == 0.5
    assert robo.sigmoid(2) == pytest.approx(1 / (1 + math.exp(-2)))
    assert robo.sigmoid(10_000) <= 1.0 and robo.sigmoid(-10_000) >= 0.0


def test_price_features_on_a_known_series():
    prices = [100.0] * 15 + [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]   # 21 prices
    index = [100.0] * 20 + [105.0]
    five_day, twenty_day, gap, swing, market = robo.price_features(prices, index)
    assert five_day == pytest.approx(110 / 100 - 1)
    assert twenty_day == pytest.approx(0.10)
    assert gap == pytest.approx(110 / (sum(prices[-20:]) / 20) - 1)
    assert swing > 0
    assert market == pytest.approx(0.05)


def test_mood_features_measure_the_fall_from_the_high():
    index = [100.0] * 10 + [120.0] + [90.0] * 10
    features = robo.mood_features(index)
    assert features[2] == pytest.approx(1 - 90 / 120)


def test_training_learns_an_easy_rule_and_the_loss_falls():
    """Label = 1 when the first feature is positive: the model must find that rule."""
    rows = [[x / 10, (x * 7 % 5) / 5] for x in range(-50, 51) if x]
    labels = [int(row[0] > 0) for row in rows]
    model, losses = robo.train(rows, labels, ["signal", "noise"], epochs=100, rate=1.0)
    assert losses[-1] < losses[0] < 0.7
    assert model.weights[0] > abs(model.weights[1])
    assert robo.score(model, rows, labels).accuracy() > 0.95


def test_reasons_add_up_to_the_score():
    model = robo.LogisticModel(["a", "b"], [2.0, -1.0], 0.5, [0.0, 0.0], [1.0, 2.0])
    reasons = model.reasons([1.0, 4.0])
    assert reasons == {"a": 2.0, "b": -2.0}
    assert model.probability([1.0, 4.0]) == pytest.approx(robo.sigmoid(0.5))


def test_save_and_load_round_trip(tmp_path):
    model = robo.LogisticModel(["a"], [0.3], -0.1, [1.0], [2.0], {"test_accuracy": 0.6})
    analyst = robo.RoboAnalyst(model, model)
    again = robo.RoboAnalyst.from_dict(analyst.to_dict())
    assert again.mood.weights == [0.3] and again.price.report["test_accuracy"] == 0.6


def test_scorecard_compares_with_the_lazy_guess():
    card = robo.Scorecard(hits=7, total=10, yes_cases=3, caught=2)
    assert card.accuracy() == 0.7
    assert card.lazy_accuracy() == 0.7      # always "no" is right 7 times out of 10
    assert card.catch_rate() == pytest.approx(2 / 3)


@pytest.fixture
def analyst():
    """The shipped, trained models."""
    return load_robo(config.ROBO_MODEL_PATH)


def test_shipped_model_learnt_that_storms_mean_danger(analyst):
    """Higher volatility must raise the downturn chance (a sanity check on the weights)."""
    swing = analyst.mood.names.index("10-day swing")
    assert analyst.mood.weights[swing] > 0
    assert analyst.mood.report["test_accuracy"] >= analyst.mood.report["lazy_accuracy"]


def test_models_never_peek_at_future_prices(analyst):
    """Changing prices after `day` must not change what the model says on `day`."""
    game = new_game(42, 60)
    market = game.market
    before = analyst.downturn_chance(market, 30), analyst.up_chance(market, "NVDA", 30)
    for symbol in market.symbols():
        history = market._history[symbol]
        history[31:] = [price * 3 for price in history[31:]]
    assert (analyst.downturn_chance(market, 30), analyst.up_chance(market, "NVDA", 30)) == before


def test_track_records_only_use_known_outcomes(analyst):
    market = new_game(42, 60).market
    assert not analyst.ready(config.ROBO_LOOKBACK - 1) and analyst.ready(config.ROBO_LOOKBACK)
    assert analyst.price_track_record(market, "NVDA", 30).total == 30 - config.ROBO_HORIZON - config.ROBO_LOOKBACK + 1
    assert analyst.mood_track_record(market, 30).total == 30 - config.ROBO_LOOKBACK + 1


@pytest.mark.parametrize("chance, call", [(0.7, "Downturn likely"), (0.2, "Looks healthy"), (0.45, "Unclear")])
def test_mood_calls(chance, call):
    assert robo.mood_call(chance) == call


@pytest.mark.parametrize("chance, call", [(0.6, "Leaning up"), (0.4, "Leaning down"), (0.5, "Coin flip")])
def test_price_calls(chance, call):
    assert robo.price_call(chance) == call
