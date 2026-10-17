"""E-05 Headline Lab: can AI read the news better than counting good and bad words?

Pure logic only. The AI arrives as a `classify` function argument, so this module never
imports the model and tests can pass in a fake (docs/02 §2.3).
"""

from tradesim import config
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

    def is_unsure(self) -> bool:
        """True when the AI's probability is below NEUTRAL_BAND (shown dimmed, still scored)."""
        return self.confidence is not None and self.confidence < config.NEUTRAL_BAND

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


class HeadlineRow:
    """One headline with both verdicts and the truth."""

    def __init__(self, event: MarketEvent, keywords: Verdict, ai: Verdict | None) -> None:
        """`ai` is None when the AI was unavailable."""
        self.event = event
        self.keywords = keywords
        self.ai = ai
        self.truth = truth(event)

    def keyword_hit(self) -> bool:
        """Did the word counter get it right?"""
        return self.keywords.label == self.truth

    def ai_hit(self) -> bool:
        """Did the AI get it right? (False if the AI was offline.)"""
        return self.ai is not None and self.ai.label == self.truth

    def __repr__(self) -> str:
        return f"HeadlineRow({self.event.headline!r}, truth={self.truth})"


class LabScore:
    """All rows plus each method's hit count."""

    def __init__(self, rows: list[HeadlineRow]) -> None:
        """Count hits for both methods."""
        self.rows = rows
        self.keyword_hits = sum(1 for row in rows if row.keyword_hit())
        self.ai_hits = sum(1 for row in rows if row.ai_hit())
        self.ai_online = any(row.ai is not None for row in rows)

    def lessons(self) -> list[str]:
        """Closing lesson lines chosen by rule (docs/04 §4.3, E-05)."""
        if not self.ai_online:
            lines = ["AI offline: keyword counter only."]
        elif self.ai_hits > self.keyword_hits:
            lines = ["Words like 'bad' or 'record' can point the wrong way. "
                     "Reading the whole sentence matters."]
        elif self.ai_hits == self.keyword_hits:
            lines = ["Simple headlines are easy. Watch the tricky ones."]
        else:
            lines = ["The AI missed more than the word counter this time — it reads language "
                     "well, but it isn't magic."]
        return lines

    def __repr__(self) -> str:
        return f"LabScore(keywords {self.keyword_hits}/{len(self.rows)}, ai {self.ai_hits}/{len(self.rows)})"


def score(events: list[MarketEvent], classify, positive_words: list[str],
          negative_words: list[str]) -> LabScore:
    """Label every headline both ways and score them against what really happened.

    `classify(headline)` returns a Verdict, or None if the AI is unavailable.
    """
    rows = [HeadlineRow(event, keyword_verdict(event.headline, positive_words, negative_words),
                        classify(event.headline))
            for event in events]
    return LabScore(rows)
