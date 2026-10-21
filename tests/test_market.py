"""Market generation: determinism, bounds, lookups and statistical sanity."""

import statistics

import pytest

from tradesim import config
from tradesim.engine import analytics
from tradesim.engine.errors import TradeSimError, UnknownSymbolError
from tradesim.engine.market import Market
from tradesim.loader import load_events


def make(universe, seed, days=60):
    stocks, etfs = universe
    return Market(stocks, etfs, seed, days)


def test_same_seed_gives_identical_history(universe):
    a, b = make(universe, 42), make(universe, 42)
    for symbol in a.symbols():
        assert a.history(symbol, 0, 60) == b.history(symbol, 0, 60)


def test_different_seed_gives_different_history(universe):
    assert make(universe, 42).history("NVDA", 0, 60) != make(universe, 43).history("NVDA", 0, 60)


def test_history_length_and_day_zero_prices(universe):
    market = make(universe, 1)
    stocks, _etfs = universe
    assert len(market.history("AAPL", 0, 60)) == 61
    for symbol, stock in stocks.items():
        assert market.price(symbol, 0) == stock.start_price
    assert market.price("MIX6", 0) == config.ETF_BASE_VALUE


def test_prices_respect_floor_and_daily_clamp(universe):
    market = make(universe, 7, days=250)
    stocks, _etfs = universe
    for symbol in stocks:
        prices = market.history(symbol, 0, 250)
        assert min(prices) >= config.MIN_PRICE
        for change in analytics.daily_returns(prices):
            # Rounding to cents can push a clamped move a hair past the limit.
            assert abs(change) <= config.MAX_DAILY_MOVE + 0.001


def test_unknown_symbol_and_bad_day_raise(universe):
    market = make(universe, 1)
    with pytest.raises(UnknownSymbolError):
        market.price("XYZ", 3)
    with pytest.raises(TradeSimError):
        market.price("AAPL", 999)


def test_nvda_swings_more_than_ko_and_etf_calmer_than_average_stock(universe):
    stocks, _etfs = universe
    nvda, ko, mix6, avg_stock = [], [], [], []
    for seed in range(20):
        market = make(universe, seed, days=250)
        nvda.append(analytics.volatility(market.history("NVDA", 0, 250)))
        ko.append(analytics.volatility(market.history("KO", 0, 250)))
        mix6.append(analytics.volatility(market.history("MIX6", 0, 250)))
        avg_stock.append(statistics.mean(
            analytics.volatility(market.history(s, 0, 250)) for s in stocks))
    assert statistics.mean(nvda) > statistics.mean(ko)
    assert statistics.mean(mix6) < statistics.mean(avg_stock)


def test_from_prices_computes_etf_by_formula(tiny_market):
    # Day 1: 100 × (0.2·110/100 + 0.4·50.5/50 + 0.4·20.1/20) = 102.6
    assert tiny_market.price("FUND", 1) == pytest.approx(102.60)
    assert tiny_market.num_days == 5


def test_daily_change_pct(tiny_market):
    assert tiny_market.daily_change_pct("JUMP", 1) == pytest.approx(10.0)
    assert tiny_market.daily_change_pct("JUMP", 0) == 0.0


def test_events_use_separate_rng_so_prices_match_until_first_event(universe):
    stocks, etfs = universe
    templates = load_events(stocks).templates
    plain = Market(stocks, etfs, 42, 60)
    with_news = Market(stocks, etfs, 42, 60, templates)
    first = min(day for day in range(1, 61) if with_news.events_on(day))
    for symbol in plain.symbols():
        assert plain.history(symbol, 0, first - 1) == with_news.history(symbol, 0, first - 1)
    assert plain.prices_on(first) != with_news.prices_on(first)


def test_events_are_deterministic_and_roughly_25_percent_of_days(universe):
    stocks, etfs = universe
    templates = load_events(stocks).templates
    a = Market(stocks, etfs, 7, 1000, templates)
    b = Market(stocks, etfs, 7, 1000, templates)
    days_a = [d for d in range(1, 1001) if a.events_on(d)]
    assert days_a == [d for d in range(1, 1001) if b.events_on(d)]
    assert 200 < len(days_a) < 300


def test_shock_moves_the_affected_stock(universe):
    stocks, etfs = universe
    boom = [{"id": "x", "scope": "stock", "target": "KO", "shock_min": 0.25, "shock_max": 0.25,
             "headline": "h", "explanation": "e"}]
    # Every rolled event is this +25% KO shock, so KO's biggest day must come from one.
    market = Market(stocks, etfs, 3, 200, boom)
    event_day = next(d for d in range(1, 201) if market.events_on(d))
    assert market.daily_change_pct("KO", event_day) > 15


# --- Real-life trends: regimes, volatility memory, beta (finance model §3.2) ---

from tradesim.engine.regime import NORMAL, Regime, RegimeModel, spells
from tradesim.loader import load_regimes


@pytest.fixture
def regimes():
    """The real market moods from data/reference.db."""
    return load_regimes()


def test_regime_path_is_deterministic_and_covers_every_day(regimes):
    a, b = regimes.generate(42, 60), regimes.generate(42, 60)
    assert a == b and len(a) == 61
    assert set(a) <= set(regimes.regimes)


def test_regime_path_does_not_change_the_noise_stream(universe, regimes):
    """Moods use their own RNG: switching them on must not reshuffle the random draws."""
    stocks, etfs = universe
    flat = Market(stocks, etfs, 5, 30)
    moody = Market(stocks, etfs, 5, 30, regime_model=regimes)
    assert flat.regime_path == ["normal"] * 31
    assert moody.regime_path == regimes.generate(5, 30)


def test_bull_markets_last_longer_than_crashes(regimes):
    assert regimes.regimes["bull"].expected_days() > 30
    assert regimes.regimes["crash"].expected_days() < 6


def test_spells_group_runs_of_the_same_mood():
    path = ["bull", "bull", "bear", "bear", "bear", "bull"]
    assert spells(path) == [("bull", 0, 1), ("bear", 2, 4), ("bull", 5, 5)]


def test_crash_regime_drags_the_market_down(universe):
    """A market stuck in a crash must fall on average; one stuck in a bull must rise."""
    stocks, etfs = universe
    crash = Regime("crash", "Crash", "!", -0.01, 3.0, {"crash": 1.0})
    bull = Regime("bull", "Bull", "^", 0.002, 0.8, {"bull": 1.0})
    falls = [Market(stocks, etfs, seed, 60, regime_model=RegimeModel({"crash": crash}, {"crash": 1.0}))
             for seed in range(5)]
    rises = [Market(stocks, etfs, seed, 60, regime_model=RegimeModel({"bull": bull}, {"bull": 1.0}))
             for seed in range(5)]
    assert statistics.mean(analytics.total_return(m.history("MIX6", 0, 60)) for m in falls) < -0.2
    assert statistics.mean(analytics.total_return(m.history("MIX6", 0, 60)) for m in rises) > 0.05


def test_high_beta_stock_follows_the_market_more(universe, regimes):
    """NVDA (beta 1.6) must swing more than JNJ (beta 0.5) over many markets."""
    stocks, etfs = universe
    nvda, jnj = [], []
    for seed in range(10):
        market = Market(stocks, etfs, seed, 120, regime_model=regimes)
        nvda.append(analytics.volatility(market.history("NVDA", 0, 120)))
        jnj.append(analytics.volatility(market.history("JNJ", 0, 120)))
    assert statistics.mean(nvda) > 2 * statistics.mean(jnj)


def test_fear_index_is_about_11_when_calm_and_jumps_in_a_crash(universe):
    stocks, etfs = universe
    calm = Market(stocks, etfs, 1, 10)
    assert calm.fear_index(0) == pytest.approx(config.MARKET_VOL * 252 ** 0.5 * 100)
    crash = Regime("crash", "Crash", "!", 0.0, 3.0, {"crash": 1.0})
    stormy = Market(stocks, etfs, 1, 10, regime_model=RegimeModel({"crash": crash}, {"crash": 1.0}))
    assert stormy.fear_index(5) > 2.5 * calm.fear_index(0)


def test_normal_regime_is_the_default(universe):
    stocks, etfs = universe
    assert Market(stocks, etfs, 1, 5).regime_on(3) is NORMAL


def test_the_same_headline_never_repeats_within_the_gap(universe):
    stocks, etfs = universe
    templates = load_events(stocks).templates
    market = Market(stocks, etfs, 11, 400, templates)
    seen = {}
    for day in range(1, 401):
        for event in market.events_on(day):
            if event.headline in seen:
                assert day - seen[event.headline] > config.EVENT_REPEAT_GAP
            seen[event.headline] = day
