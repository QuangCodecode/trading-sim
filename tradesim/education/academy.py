"""E-07 Academy: a glossary of investing words and a quiz that checks understanding.

Plain data from the glossary and quiz_questions tables (data/reference.db); these functions only look
things up and mark answers, so the CLI and the web app show the same lessons.
"""

import difflib

from tradesim.engine.errors import TradeSimError

LETTERS = "ABCD"


def find_term(terms: list[dict], word: str) -> dict:
    """The glossary entry for `word` (case-insensitive, typos forgiven)."""
    names = {entry["term"].lower(): entry for entry in terms}
    if word.lower() in names:
        return names[word.lower()]
    for name, entry in names.items():
        if word.lower() in name.split():  # "bear" → "Bear market"
            return entry
    close = difflib.get_close_matches(word.lower(), list(names), n=1, cutoff=0.6)
    if close:
        return names[close[0]]
    raise TradeSimError(f'"{word}" isn\'t in the glossary yet. Type learn to see every term.')


def current_question(questions: list[dict], answered: int) -> tuple[int, dict]:
    """(number, question) of the next question; it cycles after the last one."""
    number = answered % len(questions)
    return number, questions[number]


def mark(question: dict, letter: str) -> bool:
    """True if `letter` (A-D) is the right answer; raise on a letter that isn't an option."""
    letter = letter.upper()
    if letter not in LETTERS[:len(question["options"])]:
        raise TradeSimError(f"Answer with a letter A-{LETTERS[len(question['options']) - 1]}, "
                            "e.g. quiz B")
    return LETTERS.index(letter) == question["answer"]
