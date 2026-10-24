"""Loading and validating the reference database (stocks, ETFs, news templates, market moods)."""

import json

import pytest

from tradesim.database import write_reference
from tradesim.engine.errors import DataFileError
from tradesim.loader import load_events, load_readings, load_regimes, load_universe

GOOD = {
    "stocks": [
        {"symbol": "AAA", "name": "A", "sector": "X", "start_price": 10, "drift": 0, "volatility": 0.01},
        {"symbol": "BBB", "name": "B", "sector": "Y", "start_price": 20, "drift": 0, "volatility": 0.01},
    ],
    "etfs": [{"symbol": "FND", "name": "F", "base_value": 100, "weights": {"AAA": 0.5, "BBB": 0.5}}],
}


def write(tmp_path, data):
    """A reference database holding only this universe."""
    path = tmp_path / "reference.db"
    write_reference(path, {"universe": data})
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
    missing = tmp_path / "nope.db"
    with pytest.raises(DataFileError, match="nope.db"):
        load_universe(missing)


@pytest.mark.parametrize("content", [b"{not a database " * 20, b""])
def test_damaged_database_rejected(tmp_path, content):
    path = tmp_path / "reference.db"
    path.write_bytes(content)              # garbage, or an empty file with no tables
    with pytest.raises(DataFileError, match="reference.db"):
        load_universe(path)


def test_real_events_load_with_balanced_good_and_bad_news(universe):
    stocks, _etfs = universe
    catalogue = load_events(stocks)
    good = [t for t in catalogue.templates if t["shock_min"] > 0]
    assert len(catalogue.templates) >= 12
    assert len(good) == len(catalogue.templates) / 2
    assert "bad" in catalogue.negative_words


def event_file(tmp_path, **changes):
    template = {"id": "t", "scope": "sector", "target": "Tech", "shock_min": -0.1,
                "shock_max": -0.05, "headline": "h", "explanation": "e"}
    template.update(changes)
    path = tmp_path / "reference.db"
    write_reference(path, {"events": {"templates": [template], "positive_words": [],
                                      "negative_words": []}})
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
        load_events(stocks, event_file(tmp_path, **changes))


def test_real_regimes_load_and_every_table_sums_to_one():
    model = load_regimes()
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
    path = tmp_path / "reference.db"
    write_reference(path, {"regimes": data})
    with pytest.raises(DataFileError, match=message):
        load_regimes(path)


def test_every_shipped_headline_has_a_stored_reading(universe):
    stocks, _etfs = universe
    readings = load_readings()
    missing = [t["headline"] for t in load_events(stocks).templates if t["headline"] not in readings]
    assert missing == [], "add a row to the sentiment table of data/reference.db for each"
    assert {v.label for v in readings.values()} <= {"positive", "negative"}
    assert all(0.5 <= v.confidence <= 1 for v in readings.values())


def test_stored_readings_never_change_prices(universe):
    """The Headline Lab only displays them: a market is identical with or without reading them."""
    from tradesim.engine.market import Market
    stocks, etfs = universe
    templates = load_events(stocks).templates
    before = Market(stocks, etfs, 42, 30, templates)
    load_readings()
    after = Market(stocks, etfs, 42, 30, templates)
    assert all(before.history(s, 0, 30) == after.history(s, 0, 30) for s in before.symbols())
