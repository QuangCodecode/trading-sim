"""Train the Robo-analyst's two tiny models and save them to data/robo_model.json.

    uv run tools/train_robo.py

Markets come from seeds far away from any player's game, so the models are tested on
markets they have never seen (the honest score shown in the game).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # let `tradesim` import from tools/

from tradesim import config
from tradesim.cli.app import new_game
from tradesim.education import robo_analyst as robo


def markets(first_seed: int, count: int) -> list:
    """`count` full markets (regimes + news) with consecutive seeds."""
    return [new_game(first_seed + i, config.ROBO_TRAIN_DAYS).market for i in range(count)]


def fit(name: str, dataset, names: list[str], train_set: list, test_set: list) -> robo.LogisticModel:
    """Train one model, test it on unseen markets and store the scores in its report."""
    rows, labels = dataset(train_set)
    model, losses = robo.train(rows, labels, names)
    test = robo.score(model, *dataset(test_set))
    model.report = {"examples": len(rows), "test_examples": test.total,
                    "test_accuracy": round(test.accuracy(), 4),
                    "lazy_accuracy": round(test.lazy_accuracy(), 4),
                    "catch_rate": round(test.catch_rate(), 4),
                    "loss_start": round(losses[0], 4), "loss_end": round(losses[-1], 4)}
    print(f"{name:5} {model}  test {test.accuracy():.1%} vs lazy guess "
          f"{test.lazy_accuracy():.1%}, caught {test.catch_rate():.0%} of 'yes' cases")
    return model


def main() -> None:
    """Build the training and test markets, fit both models, save the weights."""
    train_set = markets(config.ROBO_TRAIN_SEED, config.ROBO_TRAIN_MARKETS)
    test_set = markets(config.ROBO_TRAIN_SEED + 1_000_000, config.ROBO_TEST_MARKETS)
    analyst = robo.RoboAnalyst(
        fit("mood", robo.mood_dataset, robo.MOOD_FEATURES, train_set, test_set),
        fit("price", robo.price_dataset, robo.PRICE_FEATURES, train_set, test_set))
    config.ROBO_MODEL_PATH.write_text(json.dumps(analyst.to_dict(), indent=2), encoding="utf-8")
    print(f"Saved {config.ROBO_MODEL_PATH}")


if __name__ == "__main__":
    main()
