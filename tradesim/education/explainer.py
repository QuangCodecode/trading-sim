"""E-02 Explainer: how much of a news shock reached the ETF, and why (finance model §3.4)."""

from tradesim.engine.events import MarketEvent
from tradesim.engine.market import Market
from tradesim.engine.portfolio import Portfolio


class ContributionRow:
    """One holding's part in the ETF's move on one day."""

    def __init__(self, symbol: str, move_pct: float, share: float, points: float) -> None:
        """`share` is the holding's effective weight going into the day; `points` its contribution."""
        self.symbol = symbol
        self.move_pct = move_pct
        self.share = share
        self.points = points

    def __repr__(self) -> str:
        return f"ContributionRow({self.symbol!r}, move={self.move_pct:.2f}%, points={self.points:.2f})"


def etf_move_breakdown(market: Market, etf_symbol: str, day: int) -> list[ContributionRow]:
    """Split the ETF's change from day−1 to `day` into each holding's points."""
    etf = market.etfs[etf_symbol]
    prev, today = market.stock_prices_on(day - 1), market.stock_prices_on(day)
    start = market.stock_prices_on(0)
    points = etf.contributions(prev, today, start)
    shares = effective_shares(market, etf_symbol, day - 1)
    return [ContributionRow(s, (today[s] / prev[s] - 1) * 100, shares[s], points[s])
            for s in etf.weights]


def effective_shares(market: Market, etf_symbol: str, day: int) -> dict[str, float]:
    """Each holding's share of the fund on `day`: launch weight × how much it has grown."""
    etf = market.etfs[etf_symbol]
    today, start = market.stock_prices_on(day), market.stock_prices_on(0)
    grown = {s: w * today[s] / start[s] for s, w in etf.weights.items()}
    total = sum(grown.values())
    return {s: value / total for s, value in grown.items()}


def affected_symbols(market: Market, event: MarketEvent) -> list[str]:
    """Stocks this event moved, in the market's order."""
    return [s for s, stock in market.stocks.items() if event.affects(stock)]


def explain_event(market: Market, event: MarketEvent, etf_symbol: str) -> str:
    """The explainer sentence built from the real numbers (docs/04 §4.3, E-02)."""
    rows = etf_move_breakdown(market, etf_symbol, event.day)
    hit = set(affected_symbols(market, event))
    inside = [row for row in rows if row.symbol in hit]
    etf_move = market.daily_change_pct(etf_symbol, event.day)
    if not inside:
        return (f"{etf_symbol} doesn't hold {', '.join(sorted(hit))}, so this news didn't reach it "
                f"directly. Net: {etf_symbol} {etf_move:+.2f}%.")
    moves = " and ".join(f"{row.symbol} {row.move_pct:+.1f}%" for row in inside)
    share = sum(row.share for row in inside) * 100
    affected_points = sum(row.points for row in inside)
    other_points = sum(row.points for row in rows) - affected_points
    if share > 99.5:
        return (f"Everything in {etf_symbol} was hit ({moves}). Market-wide news can't be "
                f"diversified away. Net: {etf_symbol} {etf_move:+.2f}%.")
    return (f"{moves}. They make up about {share:.0f}% of {etf_symbol} today, so they moved the "
            f"ETF {affected_points:+.2f} points. Everything else moved it {other_points:+.2f} "
            f"points. Net: {etf_symbol} {etf_move:+.2f}%.")


def position_impacts(market: Market, portfolio: Portfolio, event: MarketEvent) -> dict[str, float]:
    """$ change on `event.day` of each held position the event hit directly."""
    impacts = {}
    for symbol in affected_symbols(market, event):
        qty = portfolio.qty_held(symbol)
        if qty:
            move = market.price(symbol, event.day) - market.price(symbol, event.day - 1)
            impacts[symbol] = qty * move
    return impacts
