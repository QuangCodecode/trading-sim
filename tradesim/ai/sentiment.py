"""E-05 AI sentiment with Laya, an open-source decision model running locally on the CPU (D-21).

The only module that touches the model or the `sentiment` tables (D-46). Every failure
(no model downloaded, laya not installed, bad answer) returns None so the game falls back
to the keyword counter and never crashes (N-08). AI output is display-only (D-20).
"""

import contextlib
import io
import os
import sqlite3
import warnings
from contextlib import closing
from pathlib import Path

from tradesim import config
from tradesim.database import SENTIMENT_TABLE
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


def read_labels(path: Path | None) -> dict:
    """{headline: {"label", "confidence"}} from the `sentiment` table at `path`.

    A missing file, a corrupt file or a missing table counts as no answers (the game just asks again).
    """
    if path is None or not path.exists():
        return {}
    try:
        with closing(sqlite3.connect(path)) as db:
            rows = db.execute("SELECT headline, label, confidence FROM sentiment").fetchall()
    except sqlite3.Error:
        return {}
    return {headline: {"label": label, "confidence": confidence} for headline, label, confidence in rows}


class SentimentClassifier:
    """Labels headlines with Laya, remembering every answer in a SQLite table.

    Answers shipped with the game (reference.db) are read first; new ones are saved to `cache_path`
    (the player database, or reference.db itself when tools/warm_cache.py runs).
    """

    def __init__(self, cache_path: Path = config.PLAYER_DB_PATH, model_dir: Path = config.MODEL_DIR,
                 load_model=load_laya, seed_path: Path | None = config.REFERENCE_DB_PATH) -> None:
        """Nothing heavy happens here; the cache and model load on first use."""
        self.cache_path = cache_path
        self.model_dir = model_dir
        self.load_model = load_model
        self.model = None
        self.offline = False   # set once loading fails, so we don't retry every headline
        self.cache = {**read_labels(seed_path), **read_labels(cache_path)}

    def _save_answer(self, headline: str, entry: dict) -> None:
        """Add one answer to the table, creating the file and table the first time."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.cache_path)) as db, db:     # `with db` = one transaction
            db.execute(SENTIMENT_TABLE)
            db.execute("INSERT OR REPLACE INTO sentiment VALUES (?, ?, ?)",
                       (headline, entry["label"], entry["confidence"]))

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
                self._save_answer(headline, self.cache[headline])
            except (OSError, sqlite3.Error):
                pass  # a read-only folder or a damaged file only costs us the cache, not the answer
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
