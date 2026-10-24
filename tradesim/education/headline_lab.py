"""E-05 Headline Lab: can a reader of whole sentences beat counting good and bad words?

Pure logic only. The "sentence reader" is a stored good/bad label per shipped headline
(loader.load_readings); the word counter and the real outcome are worked out here (D-50).
"""

from tradesim.engine.events import MarketEvent

POSITIVE = "positive"
NEGATIVE = "negative"
NEUTRAL = "neutral"


class Verdict:
    """One method's reading of a headline."""

    def __init__(self, label: str, confidence: float | None, source: str, reason: str = "") -> None:
        """`label` is positive/negative/neutral; `confidence` is 0..1 (None for keywords)."""
        self.label = label
        self.confidence = confidence
        self.source = source
        self.reason = reason

    def __str__(self) -> str:
        if self.confidence is None:
            return self.label
        return f"{self.label} {self.confidence:.0%}"

    def __repr__(self) -> str:
        return f"Verdict({self.label!r}, {self.confidence!r}, {self.source!r})"


def words_in(headline: str) -> list[str]:
    """Lower-case words with punctuation removed: "Walmart's sales!" → ["walmart", "s", "sales"]."""
    letters = "".join(char if char.isalpha() else " " for char in headline.lower())
    return letters.split()


def keyword_verdict(headline: str, positive_words: list[str], negative_words: list[str]) -> Verdict:
    """Count good words minus bad words: above 0 positive, below 0 negative, 0 neutral."""
    found = []
    score = 0
    for word in words_in(headline):
        if word in positive_words:
            score += 1
            found.append(f"{word} +")
        elif word in negative_words:
            score -= 1
            found.append(f"{word} −")
    label = POSITIVE if score > 0 else NEGATIVE if score < 0 else NEUTRAL
    return Verdict(label, None, "keywords", ", ".join(found) or "no listed words")


def truth(event: MarketEvent) -> str:
    """What really happened: the sign of the event's shock."""
    return POSITIVE if event.shock > 0 else NEGATIVE
