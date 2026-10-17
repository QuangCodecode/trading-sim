"""E-01 Diversification Lab: one stock vs an ETF over the same days, with a plain-English verdict."""

from tradesim import config
from tradesim.engine import analytics
from tradesim.engine.errors import TradeSimError, UnknownSymbolError
from tradesim.engine.etf import ETF
from tradesim.engine.market import Market
from tradesim.engine.stock import Stock


class SeriesStats:
    """The Lab's numbers for one symbol: what `amount` invested at the start became."""

    def __init__(self, symbol: str, values: list[float]) -> None:
        """Compute every metric from the value-of-$X series."""
        self.symbol = symbol
        self.values = values
        self.final_value = values[-1]
        self.total_return = analytics.total_return(values)
        self.volatility = analytics.volatility(values)
        self.worst_day, self.worst_day_index = analytics.worst_day(values)
        self.max_drawdown = analytics.max_drawdown(values)

    def __repr__(self) -> str:
        return (f"SeriesStats({self.symbol!r}, final={self.final_value:.2f}, "
                f"vol={self.volatility:.4f}, dd={self.max_drawdown:.4f})")


class LabResult:
    """Everything the CLI needs to show one Lab comparison."""

    def __init__(self, stock: SeriesStats, etf: SeriesStats, start_day: int,
                 end_day: int, amount: float, verdict: list[str]) -> None:
        """Bundle both sides, the window and the verdict sentences."""
        self.stock = stock
        self.etf = etf
        self.start_day = start_day
        self.end_day = end_day
        self.amount = amount
        self.verdict = verdict

    def __repr__(self) -> str:
        return f"LabResult({self.stock.symbol} vs {self.etf.symbol}, days {self.start_day}-{self.end_day})"


def compare(market: Market, stock_symbol: str, etf_symbol: str, start_day: int,
            end_day: int, amount: float = config.LAB_DEFAULT_AMOUNT) -> LabResult:
    """Compare `amount` in a stock vs the same in an ETF from `start_day` to `end_day`."""
    check_lab_symbols(market, stock_symbol, etf_symbol)
    if end_day - start_day < config.LAB_MIN_DAYS:
        raise TradeSimError(f"Play at least {config.LAB_MIN_DAYS} days first "
                            f"— or try: lab mc for a simulated preview.")
    stock = SeriesStats(stock_symbol, analytics.value_of(
        amount, market.history(stock_symbol, start_day, end_day)))
    etf = SeriesStats(etf_symbol, analytics.value_of(
        amount, market.history(etf_symbol, start_day, end_day)))
    return LabResult(stock, etf, start_day, end_day, amount, build_verdict(stock, etf, market))


def check_lab_symbols(market: Market, stock_symbol: str, etf_symbol: str) -> None:
    """Raise unless the first symbol is a stock and the second an ETF."""
    for symbol in (stock_symbol, etf_symbol):
        if symbol not in market.symbols():
            raise UnknownSymbolError(f"{symbol} is not a tradable symbol. Try: market")
    if market.is_etf(stock_symbol):
        raise TradeSimError(f"{stock_symbol} is already an ETF. Compare a stock, e.g. lab NVDA")
    if not market.is_etf(etf_symbol):
        raise TradeSimError(f"{etf_symbol} is not an ETF. Try: lab NVDA MIX6")


def build_verdict(stock: SeriesStats, etf: SeriesStats, market: Market) -> list[str]:
    """Pick the verdict sentences from the rules table in docs/04 §4.3."""
    s, e = stock.symbol, etf.symbol
    lines = []
    if etf.volatility > 0 and stock.volatility >= config.LAB_VOL_RATIO * etf.volatility:
        lines.append(f"{s} swung {stock.volatility / etf.volatility:.1f}× harder day to day than {e}.")
    if stock.max_drawdown > etf.max_drawdown:
        lines.append(f"At its worst, {s} was {stock.max_drawdown:.1%} below its peak; "
                     f"{e} only {etf.max_drawdown:.1%}.")
    if stock.total_return > etf.total_return and stock.volatility <= etf.volatility:
        # A calm stock can beat the ETF over a short window; don't call that "more risk".
        lines.append(f"{s} beat {e} this time with smaller swings — one stock can get lucky "
                     f"over a few days. Try: lab mc {s} to see the odds over 200 markets.")
    elif stock.total_return > etf.total_return:
        lines.append(f"{s} earned more this time — but you took much more risk to get it. "
                     f"Would you have held through the {stock.max_drawdown:.0%} drop?")
    else:
        lines.append(f"{e} did better *and* was calmer. That's diversification working.")
    lines.append(describe_etf(market.etfs[e], market.stocks))
    return lines


def describe_etf(etf: ETF, stocks: dict[str, Stock]) -> str:
    """One sentence on why the ETF is diversified, e.g. "MIX6 holds 6 companies in 3 sectors…"."""
    sectors = {stocks[symbol].sector for symbol in etf.weights}
    return (f"{etf.symbol} holds {len(etf.weights)} companies in {len(sectors)} sectors, "
            f"so bad news for one is diluted by the others.")


class MonteCarloResult:
    """Stock vs ETF over many fresh markets: how often did each lose big?"""

    def __init__(self, stock_symbol: str, etf_symbol: str, stock_returns: list[float],
                 etf_returns: list[float], loss_threshold: float) -> None:
        """Store each run's total return and summarise them."""
        self.stock_symbol = stock_symbol
        self.etf_symbol = etf_symbol
        self.runs = len(stock_returns)
        self.loss_threshold = loss_threshold
        self.stock_returns = stock_returns
        self.etf_returns = etf_returns

    def average(self, returns: list[float]) -> float:
        """Mean total return of a list of runs."""
        return sum(returns) / len(returns)

    def big_loss_share(self, returns: list[float]) -> float:
        """Fraction of runs that lost more than the threshold (e.g. worse than −20%)."""
        return sum(1 for r in returns if r < self.loss_threshold) / len(returns)

    def __repr__(self) -> str:
        return f"MonteCarloResult({self.stock_symbol} vs {self.etf_symbol}, runs={self.runs})"


def monte_carlo(stocks: dict[str, Stock], etfs: dict[str, ETF], stock_symbol: str,
                etf_symbol: str, base_seed: int, runs: int = config.MONTE_CARLO_RUNS,
                days: int = config.GAME_DAYS,
                loss_threshold: float = config.MC_LOSS_THRESHOLD) -> MonteCarloResult:
    """Build `runs` fresh markets (seeds base_seed+1…) and record both total returns."""
    stock_returns, etf_returns = [], []
    for run in range(1, runs + 1):
        market = Market(stocks, etfs, base_seed + run, days)
        if run == 1:
            check_lab_symbols(market, stock_symbol, etf_symbol)
        stock_returns.append(analytics.total_return(market.history(stock_symbol, 0, days)))
        etf_returns.append(analytics.total_return(market.history(etf_symbol, 0, days)))
    return MonteCarloResult(stock_symbol, etf_symbol, stock_returns, etf_returns, loss_threshold)
