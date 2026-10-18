"""E-06 Robo-analyst: two tiny machine-learning models that read price charts.

Both are logistic regressions written in plain Python (no numpy):

    score = bias + w1·z1 + w2·z2 + … + w5·z5        (z = a feature, standardised)
    P     = 1 / (1 + e^(−score))                      (the "sigmoid" squashes score into 0..1)

* The **mood detector** looks at the whole market (MKT100) and estimates the chance that
  the market's hidden mood is a downturn (bear market or crash). It "maps the trend".
* The **price forecaster** looks at one symbol and estimates the chance its price is
  higher ROBO_HORIZON days from now.

Training = gradient descent: start with every weight at 0, measure how wrong the
predictions are (log loss), nudge each weight a little in the direction that shrinks
the loss, repeat. Both learn from simulated markets the player never sees
(tools/train_robo.py → data/robo_model.json). Display-only: they never move prices.
The lesson: spotting the mood is possible; predicting next week's price barely is.
"""

import math
import statistics

from tradesim import config
from tradesim.engine import analytics
from tradesim.engine.market import Market

PRICE_FEATURES = ["5-day trend", "20-day trend", "gap to 20-day average", "10-day swing",
                  "market 20-day trend"]
MOOD_FEATURES = ["market 20-day trend", "gap to 20-day average", "fall from 20-day high",
                 "10-day swing", "20-day swing"]
DOWNTURNS = ("bear", "crash")


def price_features(prices: list[float], index: list[float]) -> list[float]:
    """Five chart features from the last ROBO_LOOKBACK+1 prices of a symbol and the market:
    short and long trend, how stretched the price is, how jumpy it has been, market trend.
    """
    return [prices[-1] / prices[-6] - 1,
            prices[-1] / prices[-21] - 1,
            prices[-1] / statistics.mean(prices[-20:]) - 1,
            analytics.volatility(prices[-11:]),
            index[-1] / index[-21] - 1]


def mood_features(index: list[float]) -> list[float]:
    """Five features of the whole market: trend, stretch, fall from its high, storminess."""
    return [index[-1] / index[-21] - 1,
            index[-1] / statistics.mean(index[-20:]) - 1,
            1 - index[-1] / max(index),
            analytics.volatility(index[-11:]),
            analytics.volatility(index)]


def symbol_features(market: Market, symbol: str, day: int) -> list[float]:
    """Price features for `symbol` as seen on `day` (only days up to `day`: no peeking)."""
    start = day - config.ROBO_LOOKBACK
    return price_features(market.history(symbol, start, day),
                          market.history(config.MARKET_INDEX, start, day))


def market_features(market: Market, day: int) -> list[float]:
    """Mood features as seen on `day`."""
    return mood_features(market.history(config.MARKET_INDEX, day - config.ROBO_LOOKBACK, day))


def went_up(market: Market, symbol: str, day: int) -> int:
    """1 if the price was higher ROBO_HORIZON days after `day`, else 0."""
    return int(market.price(symbol, day + config.ROBO_HORIZON) > market.price(symbol, day))


def in_downturn(market: Market, day: int) -> int:
    """1 if the market's hidden mood on `day` was a bear market or a crash, else 0."""
    return int(market.regime_path[day] in DOWNTURNS)


def sigmoid(score: float) -> float:
    """Squash any number into a probability between 0 and 1."""
    score = max(-30.0, min(30.0, score))  # stop math.exp overflowing on extreme scores
    return 1 / (1 + math.exp(-score))


class LogisticModel:
    """Weights for one logistic regression plus the feature scaling learnt in training."""

    def __init__(self, names: list[str], weights: list[float], bias: float,
                 means: list[float], scales: list[float], report: dict | None = None) -> None:
        """`means`/`scales` turn raw features into z-scores; `report` holds test results."""
        self.names = names
        self.weights = weights
        self.bias = bias
        self.means = means
        self.scales = scales
        self.report = report or {}

    def standardise(self, features: list[float]) -> list[float]:
        """z = (x − mean) / scale, so every feature is on the same footing."""
        return [(x - m) / s for x, m, s in zip(features, self.means, self.scales)]

    def reasons(self, features: list[float]) -> dict[str, float]:
        """How much each feature pushed the score up (+) or down (−): weight × z."""
        z = self.standardise(features)
        return {name: w * value for name, w, value in zip(self.names, self.weights, z)}

    def probability(self, features: list[float]) -> float:
        """The model's answer: a probability between 0 and 1."""
        return sigmoid(self.bias + sum(self.reasons(features).values()))

    def to_dict(self) -> dict:
        """Plain data for data/robo_model.json."""
        return {"features": self.names, "weights": self.weights, "bias": self.bias,
                "means": self.means, "scales": self.scales, "report": self.report}

    @staticmethod
    def from_dict(data: dict) -> "LogisticModel":
        """Rebuild a saved model."""
        return LogisticModel(data["features"], data["weights"], data["bias"],
                             data["means"], data["scales"], data.get("report"))

    def __repr__(self) -> str:
        weights = ", ".join(f"{w:+.2f}" for w in self.weights)
        return f"LogisticModel(bias={self.bias:+.2f}, weights=[{weights}])"


def train(rows: list[list[float]], labels: list[int], names: list[str],
          epochs: int = config.ROBO_EPOCHS,
          rate: float = config.ROBO_LEARNING_RATE) -> tuple[LogisticModel, list[float]]:
    """Fit the weights by gradient descent; returns the model and the loss before each epoch."""
    columns = list(zip(*rows))
    means = [statistics.mean(column) for column in columns]
    scales = [statistics.pstdev(column) or 1.0 for column in columns]
    model = LogisticModel(names, [0.0] * len(names), 0.0, means, scales)
    examples = [model.standardise(row) for row in rows]
    losses = [gradient_step(model, examples, labels, rate) for _ in range(epochs)]
    return model, losses


def gradient_step(model: LogisticModel, examples: list[list[float]], labels: list[int],
                  rate: float) -> float:
    """One pass over all examples: average the errors, move every weight against them.

    Returns the average log loss before the step (lower = better predictions).
    """
    grad_w = [0.0] * len(model.weights)
    grad_b, loss = 0.0, 0.0
    for z, label in zip(examples, labels):
        p = sigmoid(model.bias + sum(w * x for w, x in zip(model.weights, z)))
        error = p - label  # the gradient of log loss for logistic regression
        grad_b += error
        for i, x in enumerate(z):
            grad_w[i] += error * x
        chance_of_truth = p if label else 1 - p
        loss -= math.log(max(chance_of_truth, 1e-12))
    n = len(examples)
    model.bias -= rate * grad_b / n
    model.weights = [w - rate * g / n for w, g in zip(model.weights, grad_w)]
    return loss / n


def price_dataset(markets: list[Market]) -> tuple[list[list[float]], list[int]]:
    """(features, went_up) for every stock on every ROBO_SAMPLE_EVERY-th usable day."""
    rows, labels = [], []
    for market in markets:
        for symbol in market.stocks:
            for day in range(config.ROBO_LOOKBACK, market.num_days - config.ROBO_HORIZON + 1,
                             config.ROBO_SAMPLE_EVERY):
                rows.append(symbol_features(market, symbol, day))
                labels.append(went_up(market, symbol, day))
    return rows, labels


def mood_dataset(markets: list[Market]) -> tuple[list[list[float]], list[int]]:
    """(features, in_downturn) for every day with enough history."""
    rows, labels = [], []
    for market in markets:
        for day in range(config.ROBO_LOOKBACK, market.num_days + 1):
            rows.append(market_features(market, day))
            labels.append(in_downturn(market, day))
    return rows, labels


class Scorecard:
    """How often a model's yes/no calls came true, against the lazy "always no" guess."""

    def __init__(self, hits: int, total: int, yes_cases: int, caught: int = 0) -> None:
        """`yes_cases` = cases that were really "yes" (up / downturn); `caught` = of those, called yes."""
        self.hits = hits
        self.total = total
        self.yes_cases = yes_cases
        self.caught = caught

    def catch_rate(self) -> float:
        """Share of real "yes" cases the model spotted (a lazy "always no" catches none)."""
        return self.caught / self.yes_cases if self.yes_cases else 0.0

    def accuracy(self) -> float:
        """Share of correct calls (0.5 = coin flip)."""
        return self.hits / self.total if self.total else 0.0

    def lazy_accuracy(self) -> float:
        """Score of always giving the more common answer: the bar a model must beat."""
        if not self.total:
            return 0.0
        return max(self.yes_cases, self.total - self.yes_cases) / self.total

    def __repr__(self) -> str:
        return f"Scorecard({self.hits}/{self.total}, yes {self.yes_cases})"


def score(model: LogisticModel, rows: list[list[float]], labels: list[int]) -> Scorecard:
    """Count the model's correct calls (probability > 0.5 means "yes")."""
    calls = [int(model.probability(row) > 0.5) for row in rows]
    hits = sum(call == label for call, label in zip(calls, labels))
    caught = sum(call and label for call, label in zip(calls, labels))
    return Scorecard(hits, len(labels), sum(labels), caught)


class RoboAnalyst:
    """Both trained models, ready to read today's charts."""

    def __init__(self, mood: LogisticModel, price: LogisticModel) -> None:
        """`mood` spots downturns; `price` forecasts one symbol ROBO_HORIZON days ahead."""
        self.mood = mood
        self.price = price

    def ready(self, day: int, first_day: int = 0) -> bool:
        """The models need ROBO_LOOKBACK days of history (since `first_day`) to say anything."""
        return day - config.ROBO_LOOKBACK >= first_day

    def downturn_chance(self, market: Market, day: int) -> float:
        """Chance the market is in a bear market or crash on `day`."""
        return self.mood.probability(market_features(market, day))

    def up_chance(self, market: Market, symbol: str, day: int) -> float:
        """Chance `symbol` is higher ROBO_HORIZON days after `day`."""
        return self.price.probability(symbol_features(market, symbol, day))

    def mood_track_record(self, market: Market, today: int) -> Scorecard:
        """The mood detector's daily calls so far vs the market's real (hidden) mood."""
        days = range(config.ROBO_LOOKBACK, today + 1)
        return score(self.mood, [market_features(market, d) for d in days],
                     [in_downturn(market, d) for d in days])

    def price_track_record(self, market: Market, symbol: str, today: int) -> Scorecard:
        """The forecaster's calls for `symbol` whose outcome is already known by `today`."""
        days = range(config.ROBO_LOOKBACK, today - config.ROBO_HORIZON + 1)
        return score(self.price, [symbol_features(market, symbol, d) for d in days],
                     [went_up(market, symbol, d) for d in days])

    def to_dict(self) -> dict:
        """Plain data for data/robo_model.json."""
        return {"mood": self.mood.to_dict(), "price": self.price.to_dict()}

    @staticmethod
    def from_dict(data: dict) -> "RoboAnalyst":
        """Rebuild both saved models."""
        return RoboAnalyst(LogisticModel.from_dict(data["mood"]),
                           LogisticModel.from_dict(data["price"]))

    def __repr__(self) -> str:
        return f"RoboAnalyst(mood={self.mood!r}, price={self.price!r})"


def mood_call(chance: float) -> str:
    """Turn a downturn probability into a plain-English call."""
    if chance >= config.ROBO_DANGER:
        return "Downturn likely"
    if chance <= config.ROBO_SAFE:
        return "Looks healthy"
    return "Unclear"


def price_call(chance: float) -> str:
    """Turn an up-probability into a plain-English call."""
    if chance >= config.ROBO_STRONG:
        return "Leaning up"
    if chance <= 1 - config.ROBO_STRONG:
        return "Leaning down"
    return "Coin flip"
