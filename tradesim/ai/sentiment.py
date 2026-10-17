"""E-05 AI sentiment with Laya, an open-source decision model running locally on the CPU (D-21).

The only module that touches the model or data/sentiment_cache.json. Every failure
(no model downloaded, laya not installed, bad answer) returns None so the game falls back
to the keyword counter and never crashes (N-08). AI output is display-only (D-20).
"""

import contextlib
import io
import json
import os
import warnings
from pathlib import Path

from tradesim import config
from tradesim.education.headline_lab import NEGATIVE, POSITIVE, Verdict

SOURCE = "laya"

# One "choice" question with two labels (D-22): every event is truly good or bad news.
QUESTION = {
    "sentiment": {
        "type": "choice",
        "instructions": "Is this news headline good or bad for the stock price of the "
                        "company or sector it mentions?",
        "criteria": {
            POSITIVE: "good news: the price is likely to rise",
            NEGATIVE: "bad news: the price is likely to fall",
        },
    }
}


def load_laya(model_dir: Path):
    """Load Laya from a local folder on the CPU (slow: ~10 s, so it's done once, lazily)."""
    # The weights are already on disk, so forbid any network call to Hugging Face.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    # torch and laya print set-up notes to stderr that would mess up the game screen.
    with warnings.catch_warnings(), contextlib.redirect_stderr(io.StringIO()):
        warnings.simplefilter("ignore")
        import laya  # imported here so the game starts fast and tests never load torch
        return laya.load(str(model_dir), device="cpu")


class SentimentClassifier:
    """Labels headlines with Laya, remembering every answer in a JSON cache."""

    def __init__(self, cache_path: Path = config.SENTIMENT_CACHE_PATH,
                 model_dir: Path = config.MODEL_DIR, load_model=load_laya) -> None:
        """Nothing heavy happens here; the cache and model load on first use."""
        self.cache_path = cache_path
        self.model_dir = model_dir
        self.load_model = load_model
        self.model = None
        self.offline = False   # set once loading fails, so we don't retry every headline
        self.cache = self._read_cache()

    def _read_cache(self) -> dict:
        """The saved answers; a missing or corrupt file counts as empty."""
        try:
            with open(self.cache_path, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_cache(self) -> None:
        """Write every answer back to disk (sorted, so git diffs stay small)."""
        with open(self.cache_path, "w", encoding="utf-8") as file:
            json.dump(self.cache, file, indent=2, sort_keys=True)

    def cached(self, headline: str) -> Verdict | None:
        """The saved answer for `headline`, without ever loading the model."""
        entry = self.cache.get(headline)
        if not isinstance(entry, dict) or entry.get("label") not in (POSITIVE, NEGATIVE):
            return None
        return Verdict(entry["label"], float(entry.get("confidence", 0.0)), SOURCE)

    def classify(self, headline: str) -> Verdict | None:
        """Cache → Laya → None. Never raises."""
        verdict = self.cached(headline)
        if verdict is not None:
            return verdict
        verdict = self._ask_model(headline)
        if verdict is not None:
            self.cache[headline] = {"label": verdict.label, "confidence": round(verdict.confidence, 4)}
            try:
                self._save_cache()
            except OSError:
                pass  # a read-only folder only costs us the cache, not the answer
        return verdict

    def _ask_model(self, headline: str) -> Verdict | None:
        """Run Laya once; any failure switches the AI off for the rest of the game."""
        if self.offline:
            return None
        try:
            if self.model is None:
                if not self.model_dir.exists():
                    raise FileNotFoundError(self.model_dir)
                self.model = self.load_model(self.model_dir)
            answer = self.model.predict(headline, QUESTION)["answers"]["sentiment"]
            return Verdict(answer["choice"], answer["probabilities"][answer["choice"]], SOURCE)
        except Exception:
            # Deliberately broad: a missing package, missing weights or an odd answer must
            # never crash the game (N-08) — we fall back to the keyword counter instead.
            self.offline = True
            return None

    def __repr__(self) -> str:
        return f"SentimentClassifier(cached={len(self.cache)}, loaded={self.model is not None})"
