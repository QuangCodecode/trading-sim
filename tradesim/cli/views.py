"""Build rich Tables/Panels from engine data. Views return renderables; app.py prints them."""

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tradesim import config
from tradesim.cli import charts
from tradesim.education import explainer, headline_lab
from tradesim.education.diversification_lab import LabResult, MonteCarloResult
from tradesim.education.headline_lab import LabScore, Verdict
from tradesim.engine import analytics
from tradesim.engine.events import MarketEvent
from tradesim.engine.game import Game
from tradesim.engine.trade import Trade


def signed(value: float, suffix: str = "", decimals: int = 2) -> Text:
    """A number with +/− sign, green for gains and red for losses."""
    colour = "green" if value > 0 else "red" if value < 0 else "white"
    return Text(f"{value:+,.{decimals}f}{suffix}", style=colour)


def money(value: float) -> str:
    """$1,234.56"""
    return f"${value:,.2f}"


def day_line(game: Game) -> str:
    """'Day 12 / 60' plus a game-over note at the end."""
    end = "  (final day — game over)" if game.is_over() else ""
    return f"[bold]Day {game.day} / {game.market.num_days}[/bold]{end}"


def banner(game: Game) -> Panel:
    """The startup panel with the simulated-prices disclaimer (N-07)."""
    market = game.market
    lines = (f"Learn to invest with [bold]{money(game.portfolio.starting_cash)}[/bold] of virtual cash.\n"
             f"{market.num_days} trading days · {len(market.stocks)} stocks · "
             f"{len(market.etfs)} ETF ({', '.join(market.etfs)})\n"
             f"[yellow]Prices are SIMULATED. Not real data, not financial advice.[/yellow]\n"
             f"Seed {market.seed} — run with --seed {market.seed} to replay this market.")
    return Panel(lines, title="TradeSim", border_style="cyan", expand=False)


def market_table(game: Game) -> Table:
    """Every symbol with price, today's change and a sparkline of recent days."""
    market, day = game.market, game.day
    table = Table(title=day_line(game), title_justify="left")
    for heading in ("Symbol", "Name", "Sector", "Price", "Today", "Last 10 days"):
        table.add_column(heading, justify="right" if heading in ("Price", "Today") else "left")
    start = max(0, day - config.SPARKLINE_DAYS + 1)
    for symbol in market.symbols():
        sector = "ETF" if market.is_etf(symbol) else market.stocks[symbol].sector
        table.add_row(f"[cyan]{symbol}[/cyan]", market.name_of(symbol), sector,
                      f"{market.price(symbol, day):,.2f}",
                      signed(market.daily_change_pct(symbol, day), "%"),
                      charts.sparkline(market.history(symbol, start, day)))
    return table


def quote_panel(game: Game, symbol: str) -> Panel:
    """One symbol: price, day change, high/low so far and the player's holding."""
    market, day = game.market, game.day
    prices = market.history(symbol, 0, day)
    body = Text.assemble(
        f"Price      {money(prices[-1])}   Today ", signed(market.daily_change_pct(symbol, day), "%"),
        f"\nHigh/low   {money(max(prices))} / {money(min(prices))} since day 0",
        f"\nYou hold   {game.portfolio.qty_held(symbol)} shares")
    return Panel(body, title=f"{symbol} — {market.name_of(symbol)}", expand=False)


def chart_panel(game: Game, symbols: list[str]) -> Panel:
    """Price chart from day 0 to today; two symbols are scaled to 'value of $100'."""
    histories = {s: game.market.history(s, 0, game.day) for s in symbols}
    if len(symbols) > 1:
        histories = {s: analytics.value_of(100, h) for s, h in histories.items()}
        title = " vs ".join(f"{s} ({m})" for s, m in zip(symbols, charts.MARKERS))
        title += " — value of $100 invested on day 0"
    else:
        title = f"{symbols[0]} price"
    return Panel("\n".join(charts.line_chart(histories)), title=title, expand=False)


def etf_panel(game: Game, symbol: str) -> Panel:
    """ETF holdings: launch weight, sector and each holding's share of the fund today."""
    market, etf = game.market, game.market.etfs[symbol]
    today, start = market.stock_prices_on(game.day), market.stock_prices_on(0)
    grown = {s: w * today[s] / start[s] for s, w in etf.weights.items()}
    table = Table()
    for heading in ("Holding", "Sector", "Launch weight", "Share today"):
        table.add_column(heading, justify="left" if heading in ("Holding", "Sector") else "right")
    for s, weight in etf.weights.items():
        table.add_row(f"[cyan]{s}[/cyan]", market.stocks[s].sector, f"{weight:.0%}",
                      f"{grown[s] / sum(grown.values()):.1%}")
    explain = (f"An ETF is one share that holds a basket of companies. {symbol} = "
               f"{config.ETF_BASE_VALUE:.0f} × the weighted average of each holding's price "
               f"relative to day 0, so a 10% drop in one stock with a 15% weight moves "
               f"{symbol} only about 1.5%.")
    return Panel(Group(table, Text(explain, style="italic")),
                 title=f"{symbol} — {etf.name} · {money(market.price(symbol, game.day))}",
                 expand=False)


def trade_message(trade: Trade, cash: float) -> str:
    """One-line confirmation after a buy or sell."""
    verb = "Bought" if trade.side == "BUY" else "Sold"
    text = (f"[green]✓ {verb} {trade.qty} [cyan]{trade.symbol}[/cyan] @ {money(trade.price)} "
            f"= {money(trade.value())} + {money(trade.fee)} fee.[/green]  Cash: {money(cash)}")
    if trade.side == "SELL":
        text += f"  Realised P&L: {trade.realised_pnl:+,.2f}"
    return text


def portfolio_view(game: Game) -> Group:
    """Holdings table plus the cash/equity/P&L summary (C-07, C-08)."""
    account, prices = game.portfolio, game.current_prices()
    weights = account.weights(prices)
    table = Table(title=day_line(game), title_justify="left")
    for heading in ("Symbol", "Qty", "Avg cost", "Price", "Value", "Unrealised", "Weight"):
        table.add_column(heading, justify="left" if heading == "Symbol" else "right")
    for symbol, pos in account.positions.items():
        pnl = pos.unrealised_pnl(prices[symbol])
        pct = pnl / (pos.avg_cost * pos.qty) * 100
        table.add_row(f"[cyan]{symbol}[/cyan]", str(pos.qty), f"{pos.avg_cost:,.2f}",
                      f"{prices[symbol]:,.2f}", f"{pos.market_value(prices[symbol]):,.2f}",
                      Text.assemble(signed(pnl), " (", signed(pct, "%", 1), ")"),
                      f"{weights[symbol]:.1%}")
    table.add_row("Cash", "", "", "", f"{account.cash:,.2f}", "", f"{weights['CASH']:.1%}",
                  end_section=True)
    return Group(table, pnl_summary(game))


def pnl_summary(game: Game) -> Text:
    """Equity and the three P&L parts that always add up to the total."""
    account, prices = game.portfolio, game.current_prices()
    return Text.assemble(
        f"Equity {money(account.equity(prices))}   Total P&L ", signed(account.total_pnl(prices)),
        " (", signed(account.total_return_pct(prices), "%"), ")\n",
        "Realised ", signed(account.realised_pnl), "   Unrealised ",
        signed(account.unrealised_pnl(prices)), "   Fees ", signed(-account.fees_paid))


def history_table(trades: list[Trade]) -> Table | str:
    """The trade log (C-09)."""
    if not trades:
        return "No trades yet. Try: buy MIX6 10"
    table = Table(title="Trade history", title_justify="left")
    for heading in ("#", "Day", "Side", "Symbol", "Qty", "Price", "Fee", "Realised"):
        table.add_column(heading, justify="right")
    for t in trades:
        realised = signed(t.realised_pnl) if t.side == "SELL" else Text("")
        table.add_row(str(t.trade_id), str(t.day), t.side, f"[cyan]{t.symbol}[/cyan]", str(t.qty),
                      f"{t.price:,.2f}", f"{t.fee:,.2f}", realised)
    return table


def lab_view(result: LabResult) -> Group:
    """Diversification Lab: comparison table, chart and verdict (E-01)."""
    s, e = result.stock, result.etf
    table = Table(title=(f"Diversification Lab — {money(result.amount)} in {s.symbol} vs "
                         f"{money(result.amount)} in {e.symbol}, day {result.start_day} → {result.end_day}"),
                  title_justify="left")
    table.add_column("")
    table.add_column(s.symbol, justify="right")
    table.add_column(e.symbol, justify="right")
    table.add_row("Final value", money(s.final_value), money(e.final_value))
    table.add_row("Total return", signed(s.total_return * 100, "%", 1), signed(e.total_return * 100, "%", 1))
    table.add_row("Daily swing (volatility)", f"{s.volatility:.1%}", f"{e.volatility:.1%}")
    table.add_row("Worst day", signed(s.worst_day * 100, "%", 1), signed(e.worst_day * 100, "%", 1))
    table.add_row("Max drawdown", f"{s.max_drawdown:.1%}", f"{e.max_drawdown:.1%}")
    chart = "\n".join(charts.line_chart({s.symbol: s.values, e.symbol: e.values}))
    legend = f"{s.symbol} (*)  vs  {e.symbol} (o) — value of {money(result.amount)}"
    verdict = Text("\n".join(f"▸ {line}" for line in result.verdict), style="yellow")
    note = Text("Thought experiment: fractional shares, no fees.", style="dim")
    return Group(table, Text(legend, style="bold"), chart, verdict, note)


def monte_carlo_view(result: MonteCarloResult) -> Panel:
    """Monte Carlo lab: average return and big-loss odds over many simulated markets."""
    table = Table()
    table.add_column("")
    for symbol in (result.stock_symbol, result.etf_symbol):
        table.add_column(symbol, justify="right")
    rows = [result.stock_returns, result.etf_returns]
    table.add_row("Average return", *[signed(result.average(r) * 100, "%", 1) for r in rows])
    table.add_row(f"Lost more than {-result.loss_threshold:.0%}",
                  *[f"{result.big_loss_share(r):.0%} of runs" for r in rows])
    table.add_row("Best run", *[signed(max(r) * 100, "%", 1) for r in rows])
    table.add_row("Worst run", *[signed(min(r) * 100, "%", 1) for r in rows])
    stock_odds = result.big_loss_share(result.stock_returns)
    lesson = (f"▸ In {result.runs} simulated markets, {result.stock_symbol} lost more than "
              f"{-result.loss_threshold:.0%} in {stock_odds:.0%} of them; {result.etf_symbol} in "
              f"{result.big_loss_share(result.etf_returns):.0%}. Diversification is about odds, not luck.")
    return Panel(Group(table, Text(lesson, style="yellow")),
                 title=f"Monte Carlo Lab — {result.runs} markets", expand=False)


def report_panel(game: Game) -> Panel:
    """End-of-game report (also `report` mid-game) (C-09)."""
    account, prices = game.portfolio, game.current_prices()
    title = "Final report" if game.is_over() else "Report so far"
    body = Text.assemble(
        f"Starting cash   {money(account.starting_cash)}\n",
        f"Equity          {money(account.equity(prices))}  (",
        signed(account.total_return_pct(prices), "%"), ")\n",
        "Realised ", signed(account.realised_pnl), " · Unrealised ",
        signed(account.unrealised_pnl(prices)), " · Fees ", signed(-account.fees_paid), "\n",
        best_and_worst(game),
        f"Max drawdown    {analytics.max_drawdown(game.equity_history):.1%}   "
        f"Trades {len(account.trades)}")
    return Panel(body, title=f"{title} — Day {game.day}", expand=False)


def best_and_worst(game: Game) -> Text:
    """'Best holding AAPL +14.2%  Worst XOM −6.1%' over currently held positions."""
    prices = game.current_prices()
    returns = {s: (prices[s] / p.avg_cost - 1) * 100 for s, p in game.portfolio.positions.items()}
    if not returns:
        return Text("No open holdings\n")
    best = max(returns, key=returns.get)
    worst = min(returns, key=returns.get)
    if best == worst:
        return Text.assemble(f"Holding         {best} ", signed(returns[best], "%", 1), "\n")
    return Text.assemble(f"Best holding    {best} ", signed(returns[best], "%", 1),
                         f"   Worst {worst} ", signed(returns[worst], "%", 1), "\n")


def move_list(game: Game, event: MarketEvent) -> Text:
    """'NVDA -8.1%, AAPL -7.9% · MIX6 -2.6%' for the stocks an event hit and the ETF."""
    market, day = game.market, event.day
    parts = [Text.assemble(f"{s} ", signed(market.daily_change_pct(s, day), "%", 1))
             for s in explainer.affected_symbols(market, event)]
    parts.append(Text.assemble(f"{config.LAB_DEFAULT_ETF} ",
                               signed(market.daily_change_pct(config.LAB_DEFAULT_ETF, day), "%", 1)))
    return Text(", ").join(parts[:-1]) + Text(" · ") + parts[-1]


def news_lines(game: Game, events: list[MarketEvent], ai_lookup) -> list:
    """Short NEWS lines shown after `next`, plus how each one hit the player's holdings.

    `ai_lookup(headline)` returns a saved AI Verdict or None (it never loads the model).
    """
    lines = []
    for event in events:
        lines.append(Text.assemble((f"NEWS day {event.day}: {event.headline}", "bold yellow"),
                                   "  ", move_list(game, event), ai_tag(ai_lookup(event.headline))))
        for symbol, change in explainer.position_impacts(game.market, game.portfolio, event).items():
            lines.append(Text.assemble(f"   Your {symbol} position changed by ", signed(change),
                                       " that day."))
    if events:
        lines.append(Text("Type news DAY for the full breakdown.", style="dim"))
    return lines


def news_view(game: Game, day: int) -> Group:
    """Every event on `day`, its explanation and how MIX6 moved, holding by holding (E-02)."""
    etf = config.LAB_DEFAULT_ETF
    events = game.market.events_on(day)
    parts = []
    for event in events:
        body = Text.assemble((event.explanation, "italic"), "\n", move_list(game, event), "\n\n",
                             (explainer.explain_event(game.market, event, etf), "yellow"))
        parts.append(Panel(body, title=f"Day {day}: {event.headline}", expand=False))
    if not events:
        parts.append(f"No news on day {day}. {etf} moved "
                     f"{game.market.daily_change_pct(etf, day):+.2f}% on ordinary day-to-day noise.")
    parts.append(breakdown_table(game, day))
    return Group(*parts)


def breakdown_table(game: Game, day: int) -> Table:
    """Each holding's move, share of the fund and contribution in points (§3.4)."""
    etf = config.LAB_DEFAULT_ETF
    rows = explainer.etf_move_breakdown(game.market, etf, day)
    table = Table(title=f"How {etf} moved on day {day}", title_justify="left")
    for heading in ("Holding", "Move", "Share of fund", "Points"):
        table.add_column(heading, justify="left" if heading == "Holding" else "right")
    for row in rows:
        table.add_row(f"[cyan]{row.symbol}[/cyan]", signed(row.move_pct, "%"),
                      f"{row.share:.1%}", signed(row.points))
    total = sum(row.points for row in rows)
    table.add_row(f"[bold]{etf}[/bold]", signed(game.market.daily_change_pct(etf, day), "%"),
                  "100%", signed(total), end_section=True)
    return table


def ai_tag(verdict: Verdict | None) -> Text:
    """'  · Laya: negative 91%' after a news line, or nothing if the AI has no answer."""
    if verdict is None:
        return Text("")
    return Text.assemble("  · Laya: ", ai_text(verdict))


def ai_text(verdict: Verdict | None) -> Text:
    """'positive 91%', dimmed with '(unsure)' below NEUTRAL_BAND; '—' when offline."""
    if verdict is None:
        return Text("—", style="dim")
    colour = "green" if verdict.label == headline_lab.POSITIVE else "red"
    if verdict.is_unsure():
        return Text(f"{verdict} (unsure)", style=f"dim {colour}")
    return Text(str(verdict), style=colour)


def mark(hit: bool) -> Text:
    """✔ for a correct call, ✗ for a wrong one."""
    return Text(" ✔", style="green") if hit else Text(" ✗", style="red")


def biggest_move(game: Game, event: MarketEvent) -> tuple[str, float]:
    """The affected stock that moved most on the event's day, and its % move."""
    moves = {s: game.market.daily_change_pct(s, event.day)
             for s in explainer.affected_symbols(game.market, event)}
    symbol = max(moves, key=lambda s: abs(moves[s]))
    return symbol, moves[symbol]


def headline_lab_view(game: Game, result: LabScore) -> Group:
    """Every headline so far: keyword counter vs Laya vs what really happened (E-05)."""
    etf = config.LAB_DEFAULT_ETF
    table = Table(title=f"Headline Lab — day 1 → {game.day}", title_justify="left")
    for heading in ("Day", "Headline", "Keywords", "Laya (AI)", "Real move", etf):
        table.add_column(heading, justify="right" if heading in ("Day", "Real move", etf) else "left")
    for row in result.rows:
        symbol, move = biggest_move(game, row.event)
        ai_cell = ai_text(row.ai) + (mark(row.ai_hit()) if row.ai else Text(""))
        table.add_row(str(row.event.day), row.event.headline,
                      Text(row.keywords.label) + mark(row.keyword_hit()), ai_cell,
                      Text.assemble(f"{symbol} ", signed(move, "%", 1)),
                      signed(game.market.daily_change_pct(etf, row.event.day), "%", 1))
    total = len(result.rows)
    ai_score = f"{result.ai_hits}/{total}" if result.ai_online else "offline"
    score_line = Text(f"Score: keywords {result.keyword_hits}/{total} · Laya {ai_score}", style="bold")
    lessons = [f"▸ {line}" for line in result.lessons()] + [f"▸ {price_lesson(game, result)}"]
    tip = Text('Try your own: hl "Walmart sales not as bad as feared"', style="dim")
    return Group(table, score_line, Text("\n".join(lessons), style="yellow"), tip)


def price_lesson(game: Game, result: LabScore) -> str:
    """'Sentiment isn't price…' using the headline with the biggest stock move."""
    etf = config.LAB_DEFAULT_ETF
    event = max((row.event for row in result.rows), key=lambda e: abs(biggest_move(game, e)[1]))
    symbol, move = biggest_move(game, event)
    etf_move = game.market.daily_change_pct(etf, event.day)
    return (f"Sentiment isn't price: even a correct call doesn't say how much. On day {event.day} "
            f"{symbol} moved {move:+.1f}%, but {etf} only {etf_move:+.1f}%.")


def own_headline_view(text: str, keywords: Verdict, ai: Verdict | None) -> Panel:
    """Both verdicts for a headline the player typed (no truth: it never happened)."""
    ai_line = ai_text(ai) if ai else Text("— AI offline (run: python3 tools/download_model.py)", style="dim")
    body = Text.assemble(
        "Keyword counter  ", keywords.label, (f"   counted: {keywords.reason}", "dim"), "\n",
        "Laya (AI)        ", ai_line, "\n\n",
        ("The counter only adds up listed words. Laya reads the whole sentence — "
         "watch for 'not', 'less than feared', 'fail to'.", "italic"))
    return Panel(body, title=f'"{text}"', expand=False)


def help_view(commands: dict[str, tuple[str, str]], topic: str | None) -> Table | str:
    """All commands, or the usage of one."""
    if topic:
        usage, description = commands[topic]
        return f"[bold]{usage}[/bold] — {description}"
    table = Table(title="Commands (case doesn't matter)", title_justify="left")
    table.add_column("Command", style="cyan")
    table.add_column("What it does")
    for usage, description in commands.values():
        table.add_row(usage, description)
    return table
