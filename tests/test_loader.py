"""Loading and validating data/universe.json and data/events.json."""

import json

import pytest

from tradesim import config
from tradesim.engine.errors import DataFileError
from tradesim.loader import load_events, load_regimes, load_universe

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
    assert len(stocks) == 100
    assert len({stock.sector for stock in stocks.values()}) == 10
    assert set(etfs["MKT100"].weights) == set(stocks)
    assert sum(etfs["MIX6"].weights.values()) == pytest.approx(1.0)
    assert set(etfs["MIX6"].weights) == {"AAPL", "NVDA", "XOM", "CVX", "KO", "WMT"}
    assert all(stock.description and stock.beta > 0 for stock in stocks.values())


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


def test_real_events_load_with_balanced_good_and_bad_news(universe):
    stocks, _etfs = universe
    catalogue = load_events(config.EVENTS_PATH, stocks)
    good = [t for t in catalogue.templates if t["shock_min"] > 0]
    assert len(catalogue.templates) >= 12
    assert len(good) == len(catalogue.templates) / 2
    assert "bad" in catalogue.negative_words


def event_file(tmp_path, **changes):
    template = {"id": "t", "scope": "sector", "target": "Tech", "shock_min": -0.1,
                "shock_max": -0.05, "headline": "h", "explanation": "e"}
    template.update(changes)
    path = tmp_path / "events.json"
    path.write_text(json.dumps({"templates": [template], "positive_words": [],
                                "negative_words": []}))
    return path


@pytest.mark.parametrize("changes, message", [
    ({"shock_min": -0.05, "shock_max": 0.05}, "all positive or all negative"),
    ({"target": "Mining"}, "unknown sector"),
    ({"scope": "stock", "target": "ZZZ"}, "unknown stock"),
    ({"scope": "planet"}, "unknown scope"),
    ({"shock_min": -0.01, "shock_max": -0.05}, "above"),
])
def test_bad_event_templates_rejected(universe, tmp_path, changes, message):
    stocks, _etfs = universe
    with pytest.raises(DataFileError, match=message):
        load_events(event_file(tmp_path, **changes), stocks)


def test_real_regimes_load_and_every_table_sums_to_one():
    model = load_regimes(config.REGIMES_PATH)
    assert set(model.regimes) == {"bull", "sideways", "bear", "crash"}
    for regime in model.regimes.values():
        assert sum(regime.transitions.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("change, message", [
    ({"start": {"bull": 0.5}}, "sum"),
    ({"start": {"moon": 1.0}}, "unknown regime"),
])
def test_bad_regime_tables_rejected(tmp_path, change, message):
    data = {"start": {"bull": 1.0},
            "regimes": [{"name": "bull", "label": "Bull", "emoji": "b", "drift": 0.001,
                         "vol_scale": 1.0, "next": {"bull": 1.0}}]}
    data.update(change)
    path = tmp_path / "regimes.json"
    path.write_text(json.dumps(data))
    with pytest.raises(DataFileError, match=message):
        load_regimes(path)
