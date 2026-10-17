"""Loading and validating data/universe.json."""

import json

import pytest

from tradesim.engine.errors import DataFileError
from tradesim.loader import load_universe

GOOD = {
    "stocks": [
        {"symbol": "AAA", "name": "A", "sector": "X", "start_price": 10, "drift": 0, "volatility": 0.01},
        {"symbol": "BBB", "name": "B", "sector": "Y", "start_price": 20, "drift": 0, "volatility": 0.01},
    ],
    "etfs": [{"symbol": "FND", "name": "F", "base_value": 100, "weights": {"AAA": 0.5, "BBB": 0.5}}],
}


def write(tmp_path, data):
    path = tmp_path / "universe.json"
    path.write_text(json.dumps(data))
    return path


def test_real_universe_loads(universe):
    stocks, etfs = universe
    assert len(stocks) == 6
    assert sum(etfs["MIX6"].weights.values()) == pytest.approx(1.0)


def test_weights_summing_to_099_rejected(tmp_path):
    data = json.loads(json.dumps(GOOD))
    data["etfs"][0]["weights"] = {"AAA": 0.5, "BBB": 0.49}
    with pytest.raises(DataFileError, match="sum"):
        load_universe(write(tmp_path, data))


def test_unknown_symbol_in_weights_rejected(tmp_path):
    data = json.loads(json.dumps(GOOD))
    data["etfs"][0]["weights"] = {"AAA": 0.5, "ZZZ": 0.5}
    with pytest.raises(DataFileError, match="ZZZ"):
        load_universe(write(tmp_path, data))


def test_duplicate_symbol_rejected(tmp_path):
    data = json.loads(json.dumps(GOOD))
    data["stocks"][1]["symbol"] = "AAA"
    with pytest.raises(DataFileError, match="Duplicate"):
        load_universe(write(tmp_path, data))


def test_missing_file_names_the_path(tmp_path):
    missing = tmp_path / "nope.json"
    with pytest.raises(DataFileError, match="nope.json"):
        load_universe(missing)


def test_bad_json_rejected(tmp_path):
    path = tmp_path / "universe.json"
    path.write_text("{not json")
    with pytest.raises(DataFileError):
        load_universe(path)
