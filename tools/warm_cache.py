"""Label every events.json headline with Laya once and save data/sentiment_cache.json.

Run before committing or demoing: python3 tools/warm_cache.py
Then the game shows Laya's answers instantly, even on a machine without the model.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # let `tradesim` import from tools/

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
from tradesim.loader import load_events, load_universe


def main() -> None:
    """Classify each template headline (cached ones are skipped) and print the results."""
    stocks, _etfs = load_universe(config.UNIVERSE_PATH)
    catalogue = load_events(config.EVENTS_PATH, stocks)
    classifier = SentimentClassifier()
    for template in catalogue.templates:
        verdict = classifier.classify(template["headline"])
        if verdict is None:
            sys.exit("Laya is unavailable — run python3 tools/download_model.py first.")
        truth = "positive" if template["shock_min"] > 0 else "negative"
        mark = "✔" if verdict.label == truth else "✗"
        print(f"{mark} {template['headline']:50} {verdict}")
    print(f"Saved {len(classifier.cache)} answers to {config.SENTIMENT_CACHE_PATH}")


if __name__ == "__main__":
    main()
