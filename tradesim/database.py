"""SQLite storage (D-46): the reference data the game reads and the player data it writes.

Two database files, both opened with the standard library's sqlite3:

    data/reference.db   committed to git, read-only while playing: stocks, ETFs, news
                        templates, market moods, glossary, quiz, challenges, AI labels
    saves/player.db     git-ignored: games, the commands that rebuild them, badges won

The readers hand back plain dicts in the same shape the old data/*.json files had, so the
checks in loader.py did not need to change. Rows come back in insertion order (`ORDER BY
rowid`) because the order of stocks and of an ETF's weights feeds the seeded random numbers.
"""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

from tradesim import config
from tradesim.engine.errors import DataFileError, TradeSimError


# No PRIMARY KEY / FOREIGN KEY / CHECK on these tables on purpose: loader.py already checks
# every rule (duplicate symbols, weights adding up to 1, ...) and raises a friendly DataFileError.
REFERENCE_SCHEMA = """
CREATE TABLE stocks (symbol TEXT, name TEXT, sector TEXT, start_price REAL, drift REAL,
                     volatility REAL, beta REAL, description TEXT);
CREATE TABLE etfs (symbol TEXT, name TEXT, base_value REAL, description TEXT);
CREATE TABLE etf_weights (etf TEXT, stock TEXT, weight REAL);
CREATE TABLE event_templates (id TEXT, scope TEXT, target TEXT, shock_min REAL, shock_max REAL,
                              headline TEXT, "explanation" TEXT);
CREATE TABLE event_words (word TEXT, polarity TEXT);          -- polarity: positive / negative
CREATE TABLE regimes (name TEXT, label TEXT, emoji TEXT, drift REAL, vol_scale REAL, about TEXT);
CREATE TABLE regime_next (name TEXT, next_name TEXT, chance REAL);   -- one row per arrow
CREATE TABLE regime_start (name TEXT, chance REAL);
CREATE TABLE glossary (term TEXT, emoji TEXT, short TEXT, long TEXT, "try" TEXT);
CREATE TABLE quiz_questions (question TEXT, options TEXT, answer INTEGER, "explain" TEXT);
CREATE TABLE challenges (id TEXT, title TEXT, emoji TEXT, seed INTEGER, days INTEGER, intro TEXT,
                         goals TEXT, lesson TEXT, story TEXT, start TEXT);
-- the "sentence reader" labels of the Headline Lab: worked out once, stored as plain data (D-50)
CREATE TABLE sentiment (headline TEXT PRIMARY KEY, label TEXT NOT NULL, confidence REAL NOT NULL);
"""

# A game is a seed plus the commands that changed it (D-08, D-26): prices are never stored.
PLAYER_SCHEMA = f"""
CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    slot TEXT UNIQUE,            -- 'agent' / 'web' while it is the current game, NULL once replaced
    seed INTEGER NOT NULL, days INTEGER NOT NULL, challenge TEXT,
    started_at TEXT NOT NULL,
    day INTEGER NOT NULL DEFAULT 0, equity REAL, market_return REAL, fees REAL,
    over INTEGER NOT NULL DEFAULT 0, passed INTEGER,
    quiz_right INTEGER NOT NULL DEFAULT 0, quiz_answered INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE commands (
    game_id INTEGER NOT NULL REFERENCES games(id), position INTEGER NOT NULL, line TEXT NOT NULL,
    PRIMARY KEY (game_id, position)
);
CREATE TABLE badges (
    game_id INTEGER NOT NULL REFERENCES games(id), badge_id TEXT NOT NULL,
    PRIMARY KEY (game_id, badge_id)
);
PRAGMA user_version = {config.DB_VERSION};
"""


def connect(target: str, uri: bool = False) -> sqlite3.Connection:
    """A connection whose rows can be read by column name (row["symbol"])."""
    db = sqlite3.connect(target, uri=uri)
    db.row_factory = sqlite3.Row
    return db


def open_reference(path: Path) -> sqlite3.Connection:
    """The reference database, opened read-only so the game can never change it."""
    if not path.exists():
        raise DataFileError(f"Data file not found: {path}")
    return connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def open_player(path: Path) -> sqlite3.Connection:
    """The player database, created with its tables the first time it is needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = connect(str(path))
    try:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:                       # a brand-new (empty) file
            db.executescript(PLAYER_SCHEMA)
        elif version != config.DB_VERSION:
            raise sqlite3.DatabaseError(f"version {version}, expected {config.DB_VERSION}")
        db.execute("PRAGMA foreign_keys = ON")
    except sqlite3.DatabaseError:
        db.close()
        raise TradeSimError(f"Player database {path} is damaged or from another version — "
                            "delete it to start fresh.")
    return db


# ----- reading: rows → the dicts the old JSON files held -----

def read_universe(db: sqlite3.Connection) -> dict:
    """{"stocks": [...], "etfs": [... each with a "weights" dict]}."""
    weights: dict[str, dict[str, float]] = {}
    for row in db.execute("SELECT etf, stock, weight FROM etf_weights ORDER BY rowid"):
        weights.setdefault(row["etf"], {})[row["stock"]] = row["weight"]
    stocks = [dict(row) for row in db.execute("SELECT * FROM stocks ORDER BY rowid")]
    etfs = [dict(row, weights=weights.get(row["symbol"], {}))
            for row in db.execute("SELECT * FROM etfs ORDER BY rowid")]
    return {"stocks": stocks, "etfs": etfs}


def read_events(db: sqlite3.Connection) -> dict:
    """{"templates": [...], "positive_words": [...], "negative_words": [...]}."""
    def words(polarity: str) -> list[str]:
        rows = db.execute("SELECT word FROM event_words WHERE polarity = ? ORDER BY rowid", (polarity,))
        return [row["word"] for row in rows]
    templates = [dict(row) for row in db.execute("SELECT * FROM event_templates ORDER BY rowid")]
    return {"templates": templates, "positive_words": words("positive"), "negative_words": words("negative")}


def read_regimes(db: sqlite3.Connection) -> dict:
    """{"start": {mood: chance}, "regimes": [... each with a "next" dict]}."""
    arrows: dict[str, dict[str, float]] = {}
    for row in db.execute("SELECT name, next_name, chance FROM regime_next ORDER BY rowid"):
        arrows.setdefault(row["name"], {})[row["next_name"]] = row["chance"]
    start = {row["name"]: row["chance"] for row in db.execute("SELECT * FROM regime_start ORDER BY rowid")}
    regimes = [dict(row, next=arrows.get(row["name"], {}))
               for row in db.execute("SELECT * FROM regimes ORDER BY rowid")]
    return {"start": start, "regimes": regimes}


def read_challenges(db: sqlite3.Connection) -> dict:
    """{"challenges": [...]}; goals/story/start are stored as JSON text."""
    challenges = []
    for row in db.execute("SELECT * FROM challenges ORDER BY rowid"):
        challenge = dict(row, goals=json.loads(row["goals"]), story=json.loads(row["story"]))
        if row["start"] is None:
            del challenge["start"]              # most challenges have no starting trades
        else:
            challenge["start"] = json.loads(row["start"])
        challenges.append(challenge)
    return {"challenges": challenges}


def read_glossary(db: sqlite3.Connection) -> dict:
    """{"terms": [...]}."""
    return {"terms": [dict(row) for row in db.execute("SELECT * FROM glossary ORDER BY rowid")]}


def read_quiz(db: sqlite3.Connection) -> dict:
    """{"questions": [... each with its "options" list]}."""
    questions = [dict(row, options=json.loads(row["options"]))
                 for row in db.execute("SELECT * FROM quiz_questions ORDER BY rowid")]
    return {"questions": questions}


def read_sentiment(db: sqlite3.Connection) -> dict:
    """{headline: {"label", "confidence"}}: the stored reading of each news headline."""
    rows = db.execute("SELECT headline, label, confidence FROM sentiment ORDER BY rowid")
    return {row["headline"]: {"label": row["label"], "confidence": row["confidence"]} for row in rows}


SECTION_READERS = {"universe": read_universe, "events": read_events, "regimes": read_regimes,
                   "challenges": read_challenges, "glossary": read_glossary, "quiz": read_quiz,
                   "sentiment": read_sentiment}


def read_section(path: Path, name: str) -> dict:
    """One part of the reference data (a SECTION_READERS key). Raises DataFileError if unreadable."""
    with closing(open_reference(path)) as db:
        try:
            return SECTION_READERS[name](db)
        except sqlite3.DatabaseError as error:       # not a database, or a table is missing
            raise DataFileError(f"{path} is not a valid reference database: {error}")


# ----- writing: used by tests and by tools that build or update reference.db -----

def write_reference(path: Path, sections: dict) -> None:
    """Create a fresh reference database from dicts shaped like the old JSON files.

    `sections` may hold any of the SECTION_READERS names ("sentiment" is
    {headline: {"label", "confidence"}}). A missing part is simply left empty.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    with closing(sqlite3.connect(path)) as db:
        db.executescript(REFERENCE_SCHEMA)
        with db:                                     # one transaction: all or nothing
            _write_universe(db, sections.get("universe", {}))
            _write_events(db, sections.get("events", {}))
            _write_regimes(db, sections.get("regimes", {}))
            _write_lists(db, sections)
            db.executemany("INSERT INTO sentiment VALUES (?, ?, ?)",
                           [(text, entry["label"], entry["confidence"])
                            for text, entry in sections.get("sentiment", {}).items()])


def _write_universe(db: sqlite3.Connection, data: dict) -> None:
    """Stocks, ETFs and one etf_weights row per holding."""
    db.executemany("INSERT INTO stocks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   [(s["symbol"], s["name"], s["sector"], s["start_price"], s["drift"], s["volatility"],
                     s.get("beta", 1.0), s.get("description", "")) for s in data.get("stocks", [])])
    for etf in data.get("etfs", []):
        db.execute("INSERT INTO etfs VALUES (?, ?, ?, ?)",
                   (etf["symbol"], etf["name"], etf["base_value"], etf.get("description", "")))
        db.executemany("INSERT INTO etf_weights VALUES (?, ?, ?)",
                       [(etf["symbol"], stock, weight) for stock, weight in etf["weights"].items()])


def _write_events(db: sqlite3.Connection, data: dict) -> None:
    """News templates and the keyword counter's word lists."""
    db.executemany("INSERT INTO event_templates VALUES (?, ?, ?, ?, ?, ?, ?)",
                   [(t["id"], t["scope"], t["target"], t["shock_min"], t["shock_max"], t["headline"],
                     t["explanation"]) for t in data.get("templates", [])])
    for polarity in ("positive", "negative"):
        db.executemany("INSERT INTO event_words VALUES (?, ?)",
                       [(word, polarity) for word in data.get(f"{polarity}_words", [])])


def _write_regimes(db: sqlite3.Connection, data: dict) -> None:
    """Market moods, the chance of each mood on day 0, and every mood-to-mood arrow."""
    db.executemany("INSERT INTO regime_start VALUES (?, ?)", list(data.get("start", {}).items()))
    for mood in data.get("regimes", []):
        db.execute("INSERT INTO regimes VALUES (?, ?, ?, ?, ?, ?)",
                   (mood["name"], mood["label"], mood["emoji"], mood["drift"], mood["vol_scale"],
                    mood.get("about", "")))
        db.executemany("INSERT INTO regime_next VALUES (?, ?, ?)",
                       [(mood["name"], target, chance) for target, chance in mood["next"].items()])


def _write_lists(db: sqlite3.Connection, sections: dict) -> None:
    """Glossary terms, quiz questions and challenges (their nested parts become JSON text)."""
    db.executemany("INSERT INTO glossary VALUES (?, ?, ?, ?, ?)",
                   [(t["term"], t["emoji"], t["short"], t["long"], t["try"])
                    for t in sections.get("glossary", {}).get("terms", [])])
    db.executemany("INSERT INTO quiz_questions VALUES (?, ?, ?, ?)",
                   [(q["question"], json.dumps(q["options"]), q["answer"], q["explain"])
                    for q in sections.get("quiz", {}).get("questions", [])])
    for c in sections.get("challenges", {}).get("challenges", []):
        start = json.dumps(c["start"]) if "start" in c else None
        db.execute("INSERT INTO challenges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (c["id"], c["title"], c["emoji"], c["seed"], c["days"], c["intro"],
                    json.dumps(c["goals"]), c["lesson"], json.dumps(c["story"]), start))


def read_games(path: Path) -> list[dict]:
    """Every game ever saved (for the `games` command), newest first. Each dict is a `games` row plus a "badges" list."""
    with closing(open_player(path)) as db:
        games = [dict(row) for row in db.execute("SELECT * FROM games ORDER BY id DESC")]
        for game in games:
            rows = db.execute("SELECT badge_id FROM badges WHERE game_id = ? ORDER BY rowid", (game["id"],))
            game["badges"] = [row["badge_id"] for row in rows]
    return games
