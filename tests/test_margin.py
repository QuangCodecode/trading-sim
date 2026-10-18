"""Margin trading / leverage (finance model §3.13) with the worked numbers from the doc."""

import pytest

from tradesim import config
from tradesim.engine import margin
from tradesim.engine.errors import InsufficientCashError, TradeSimError
from tradesim.engine.etf import ETF
from tradesim.engine.game import Game
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio
from tradesim.engine.stock import Stock


@pytest.fixture
def account():
    """$10,000 margin account allowed 2× leverage, $1 fee."""
    return Portfolio(10_000.0, 1.0, max_leverage=2)


def test_cash_account_cannot_borrow(portfolio):
    assert margin.credit(portfolio, {}) == 0
    with pytest.raises(InsufficientCashError, match="Not enough cash"):
        portfolio.buy("X", 101, 100.0, 0, margin.credit(portfolio, {}))


def test_2x_lets_you_borrow_your_own_money_again(account):
    assert margin.credit(account, {}) == 9_999.0
    account.buy("X", 199, 100.0, 0, margin.credit(account, {}))       # $19,901 with the fee
    assert account.cash == pytest.approx(-9_901.0) and account.loan() == pytest.approx(9_901.0)
    prices = {"X": 100.0}
    assert margin.leverage_used(account, prices) == pytest.approx(19_900 / 9_999)
    with pytest.raises(InsufficientCashError, match="buying power"):
        account.buy("X", 2, 100.0, 0, margin.credit(account, prices))


def test_maintenance_and_moves():
    assert margin.maintenance(2) == 0.25 and margin.maintenance(5) == pytest.approx(0.10)
    assert margin.call_move(2) == pytest.approx(1 / 3) and margin.call_move(5) == pytest.approx(1 / 9)
    assert margin.wipeout_move(2) == 0.5 and margin.call_move(1) == 1.0


@pytest.mark.parametrize("price, called", [(70.0, False), (65.0, True)])
def test_margin_call_needs_equity_below_maintenance(account, price, called):
    account.buy("X", 199, 100.0, 0, 9_999.0)
    # −30%: equity 4,029 is 28.9% of 13,930 → fine. −35%: 3,034 is 23.5% of 12,935 → call.
    assert margin.is_margin_call(account, {"X": price}) == called


def test_liquidation_sells_back_to_the_leverage_limit(account):
    account.buy("X", 199, 100.0, 0, 9_999.0)
    trades = margin.liquidate(account, {"X": 65.0}, day=3, tick=12)
    assert [(t.qty, t.note, t.tick) for t in trades] == [(106, "margin call", 12)]
    assert account.qty_held("X") == 93 and account.cash == pytest.approx(-3_012.0)
    assert margin.leverage_used(account, {"X": 65.0}) <= 2


def test_wipeout_sells_everything_and_leaves_a_debt(account):
    account.buy("X", 199, 100.0, 0, 9_999.0)
    margin.liquidate(account, {"X": 40.0}, day=3, tick=0)
    assert account.positions == {} and account.cash == pytest.approx(-9_901 + 7_960 - 1)


def test_interest_is_charged_on_the_loan_only(account, portfolio):
    account.buy("X", 199, 100.0, 0, 9_999.0)
    assert account.charge_interest(0.08, 252) == pytest.approx(9_901 * 0.08 / 252)
    assert portfolio.charge_interest(0.08, 252) == 0 and portfolio.interest_paid == 0


def test_changing_leverage(account):
    account.buy("X", 199, 100.0, 0, 9_999.0)
    with pytest.raises(TradeSimError, match="Sell some"):
        margin.check_new_leverage(account, {"X": 100.0}, 1)
    with pytest.raises(TradeSimError, match="between 1 and"):
        margin.check_new_leverage(account, {"X": 100.0}, config.MAX_LEVERAGE + 1)
    margin.check_new_leverage(account, {"X": 100.0}, 3)


@pytest.fixture
def crash_game():
    """One stock that halves on day 1, played on a 2× account."""
    stocks = {"DROP": Stock("DROP", "Drop Co", "Tech", 100.0, 0.0, 0.01)}
    etfs = {"F": ETF("F", "Fund", {"DROP": 1.0}, 100.0)}
    market = Market.from_prices(stocks, etfs, {"DROP": [100.0, 50.0, 50.0]})
    return Game(market, Portfolio(10_000.0, 1.0, max_leverage=2))


def test_game_margin_call_during_the_session(crash_game):
    crash_game.buy("DROP", crash_game.max_buy("DROP"))
    crash_game.step(config.TICKS_PER_DAY)
    forced = [t for t in crash_game.portfolio.trades if t.note == "margin call"]
    assert crash_game.margin_calls and forced and forced[0].tick > 0


def test_next_checks_margin_on_every_tick_when_borrowing(crash_game):
    crash_game.buy("DROP", crash_game.max_buy("DROP"))
    crash_game.advance(1)
    assert crash_game.margin_calls and crash_game.portfolio.interest_paid > 0


def test_set_leverage_through_the_game(crash_game):
    crash_game.set_leverage(3)
    assert crash_game.portfolio.max_leverage == 3
    assert crash_game.max_buy("DROP") == 299
