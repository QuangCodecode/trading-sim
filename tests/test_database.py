"""database.py: the reference database round trip, read-only access and the player database."""

import sqlite3
from contextlib import closing

import pytest

from tradesim import config
from tradesim.database import (open_player, open_reference, read_games, read_section, write_reference)
from tradesim.engine.errors import DataFileError, TradeSimError

SECTIONS = {
    "universe": {"stocks": [{"symbol": "ZZZ", "name": "Z", "sector": "X", "start_price": 5.0, "drift": 0.0,
                             "volatility": 0.02, "beta": 1.2, "description": "d"},
                            {"symbol": "AAA", "name": "A", "sector": "Y", "start_price": 9.0, "drift": 0.0,
                             "volatility": 0.01, "beta": 1.0, "description": ""}],
                 "etfs": [{"symbol": "FND", "name": "F", "base_value": 100.0, "description": "",
                           "weights": {"ZZZ": 0.25, "AAA": 0.75}}]},
    "events": {"templates": [{"id": "t", "scope": "market", "target": "all", "shock_min": 0.01,
                              "shock_max": 0.02, "headline": "Up", "explanation": "e"}],
               "positive_words": ["up", "gain"], "negative_words": ["down"]},
    "regimes": {"start": {"bull": 0.7, "bear": 0.3},
                "regimes": [{"name": "bull", "label": "Bull", "emoji": "b", "drift": 0.001, "vol_scale": 1.0,
                             "about": "a", "next": {"bull": 0.9, "bear": 0.1}},
                            {"name": "bear", "label": "Bear", "emoji": "r", "drift": -0.001, "vol_scale": 1.5,
                             "about": "", "next": {"bear": 0.8, "bull": 0.2}}]},
    "challenges": {"challenges": [{"id": "c1", "title": "T", "emoji": "e", "seed": 1, "days": 30, "intro": "i",
                                   "goals": [{"type": "min_equity", "value": 9000}], "lesson": "l",
                                   "story": {"regime": "bull"}, "start": ["buy AAA 1"]},
                                  {"id": "c2", "title": "U", "emoji": "e", "seed": 2, "days": 60, "intro": "i",
                                   "goals": [], "lesson": "l", "story": {}}]},
    "glossary": {"terms": [{"term": "ETF", "emoji": "e", "short": "s", "long": "l", "try": "t"}]},
    "quiz": {"questions": [{"question": "q?", "options": ["a", "b"], "answer": 1, "explain": "x"}]},
}


@pytest.fixture
def reference(tmp_path):
    path = tmp_path / "reference.db"
    write_reference(path, SECTIONS)
    return path


@pytest.mark.parametrize("name", list(SECTIONS))
def test_every_section_round_trips(reference, name):
    assert read_section(reference, name) == SECTIONS[name]


def test_row_and_weight_order_survive_because_they_feed_the_seeded_random_numbers(reference):
    universe = read_section(reference, "universe")
    assert [s["symbol"] for s in universe["stocks"]] == ["ZZZ", "AAA"]        # not alphabetical
    assert list(universe["etfs"][0]["weights"]) == ["ZZZ", "AAA"]
    assert list(read_section(reference, "regimes")["regimes"][1]["next"]) == ["bear", "bull"]


def test_the_game_can_not_write_to_the_reference_database(reference):
    with closing(open_reference(reference)) as db:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            db.execute("DELETE FROM stocks")


def test_missing_and_damaged_reference_files_name_the_path(tmp_path):
    with pytest.raises(DataFileError, match="nope.db"):
        read_section(tmp_path / "nope.db", "quiz")
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"garbage " * 50)
    with pytest.raises(DataFileError, match="bad.db"):
        read_section(bad, "quiz")


def test_the_real_reference_database_has_all_the_game_data():
    assert len(read_section(config.REFERENCE_DB_PATH, "universe")["stocks"]) == 100
    assert len(read_section(config.REFERENCE_DB_PATH, "events")["templates"]) == 84
    assert len(read_section(config.REFERENCE_DB_PATH, "quiz")["questions"]) == 21


def test_player_database_is_created_with_its_tables_and_foreign_keys(tmp_path):
    path = tmp_path / "deep" / "folder" / "player.db"
    with closing(open_player(path)) as db:
        names = {row["name"] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {"games", "commands", "badges", "sentiment"} <= names
        with pytest.raises(sqlite3.IntegrityError):                       # no such game
            db.execute("INSERT INTO commands VALUES (99, 0, 'next')")


def test_player_database_from_another_version_is_refused(tmp_path):
    path = tmp_path / "player.db"
    with closing(open_player(path)) as db:
        db.execute(f"PRAGMA user_version = {config.DB_VERSION + 1}")
    with pytest.raises(TradeSimError, match="delete it"):
        open_player(path)


def test_history_is_newest_first_with_badges(tmp_path):
    path = tmp_path / "player.db"
    with closing(open_player(path)) as db, db:
        db.execute("INSERT INTO games (id, seed, days, started_at) VALUES (1, 10, 5, 'a'), (2, 20, 5, 'b')")
        db.execute("INSERT INTO badges VALUES (1, 'first_trade'), (1, 'diversified')")
    history = read_games(path)
    assert [g["seed"] for g in history] == [20, 10]
    assert history[0]["badges"] == [] and history[1]["badges"] == ["first_trade", "diversified"]
