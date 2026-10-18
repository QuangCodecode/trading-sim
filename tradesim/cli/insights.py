"""Rich screens for the 'understand the market' features: Robo-analyst, market story,
sectors, Trade Coach, What-if Replay, the live session and leverage.
Like views.py, these only build renderables."""

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tradesim import config
from tradesim.cli import charts
from tradesim.cli.views import (REGIME_STYLES, money, sector_text, signed)
from tradesim.education import leverage_lab, robo_analyst
from tradesim.education.coach import PRAISE, WARN, Tip
from tradesim.education.leverage_lab import LeverageRun
from tradesim.education.robo_analyst import RoboAnalyst, Scorecard
from tradesim.education.whatif import YOURS, ReplayResult
from tradesim.engine import analytics, margin
from tradesim.engine.events import MarketEvent
from tradesim.engine.game import Game
from tradesim.engine.intraday import clock_text
from tradesim.engine.regime import spells
from tradesim.engine.trade import Trade

BAR_WIDTH = 12


def bar(value: float, biggest: float, colour: str) -> Text:
    """A text bar whose length shows `value` relative to `biggest`."""
    length = round(abs(value) / biggest * BAR_WIDTH) if biggest else 0
    return Text("█" * length, style=colour)


def chance_text(chance: float, good_when_high: bool) -> Text:
    """'72%' coloured green when it's good news, red when it's bad news."""
    good = chance >= 0.5 if good_when_high else chance < 0.5
    return Text(f"{chance:.0%}", style="green" if good else "red")


def outlook_text(analyst: RoboAnalyst, game: Game, symbol: str) -> Text:
    """'Leaning up — 58% chance higher in 5 days' for the quote screen."""
    if not analyst.ready(game.day, game.market.first_day):
        return Text(f"needs {config.ROBO_LOOKBACK} days of history (try again on day "
                    f"{config.ROBO_LOOKBACK})", style="dim")
    chance = analyst.up_chance(game.market, symbol, game.day)
    return Text.assemble((robo_analyst.price_call(chance), "bold"), " — ",
                         chance_text(chance, True), f" chance higher in {config.ROBO_HORIZON} days",
                         (" (type robo to see why)", "dim"))


def reasons_table(reasons: dict[str, float], up_is: str) -> Table:
    """Each feature's push on the score as a bar; `up_is` names what a push up means."""
    table = Table(box=None, show_header=False, padding=(0, 1))
    biggest = max(abs(v) for v in reasons.values())
    for name, push in reasons.items():
        colour = "red" if (push > 0) == (up_is == "danger") else "green"
        arrow = "▲" if push > 0 else "▼"
        table.add_row(name, Text(f"{arrow} {push:+.2f}", style=colour), bar(push, biggest, colour))
    return table


def mood_section(game: Game, analyst: RoboAnalyst) -> Group:
    """Today's downturn chance, the reasons, and how the detector has done this game."""
    chance = analyst.downturn_chance(game.market, game.day)
    headline = Text.assemble("Market mood check: ", chance_text(chance, False),
                             " chance the market is in a downturn → ",
                             (robo_analyst.mood_call(chance), "bold"))
    record = analyst.mood_track_record(game.market, game.day)
    caption = Text("Why (pushes towards ▲ danger / ▼ calm):", style="dim")
    return Group(headline, caption,
                 reasons_table(analyst.mood.reasons(robo_analyst.market_features(game.market, game.day)), "danger"),
                 Text(track_line("This game so far", record, "downturn days"), style="dim"))


def track_line(label: str, record: Scorecard, yes_name: str) -> str:
    """'This game so far: right 31/40 days (78%); always-no would score 75%; caught 2/8 …'."""
    if not record.total:
        return f"{label}: no results to check yet."
    caught = (f"caught {record.caught}/{record.yes_cases} {yes_name}" if record.yes_cases
              else f"no {yes_name} so far to catch")
    return (f"{label}: right {record.hits}/{record.total} ({record.accuracy():.0%}); the lazy "
            f"guess scores {record.lazy_accuracy():.0%}; {caught}.")


def outlook_table(game: Game, analyst: RoboAnalyst) -> Table:
    """Every symbol's chance of being higher in ROBO_HORIZON days, plus its track record."""
    table = Table(title=f"Price forecaster — chance each price is higher in {config.ROBO_HORIZON} days",
                  title_justify="left", box=box.SIMPLE)
    for heading in ("Symbol", "Sector", "Chance up", "Call", "Right so far"):
        table.add_column(heading, justify="right" if heading in ("Chance up", "Right so far") else "left")
    for symbol in game.market.symbols():
        chance = analyst.up_chance(game.market, symbol, game.day)
        record = analyst.price_track_record(game.market, symbol, game.day)
        sector = "ETF" if game.market.is_etf(symbol) else game.market.stocks[symbol].sector
        so_far = f"{record.accuracy():.0%} of {record.total}" if record.total else "—"
        table.add_row(f"[bold cyan]{symbol}[/bold cyan]", sector_text(sector),
                      chance_text(chance, True), robo_analyst.price_call(chance), so_far)
    return table


def training_note(analyst: RoboAnalyst) -> Text:
    """What the models learned from, and their honest scores on markets they never saw."""
    mood, price = analyst.mood.report, analyst.price.report
    if not mood:
        return Text("")
    return Text(
        f"Trained by gradient descent on {mood['examples']:,} market days and {price['examples']:,} "
        f"price charts from simulated markets you never see. Tested on fresh markets: the mood "
        f"detector was right {mood['test_accuracy']:.0%} (lazy guess {mood['lazy_accuracy']:.0%}, "
        f"caught {mood['catch_rate']:.0%} of downturn days); the price forecaster "
        f"{price['test_accuracy']:.0%} (lazy guess {price['lazy_accuracy']:.0%}).", style="dim")


def robo_view(game: Game, analyst: RoboAnalyst) -> Panel:
    """The whole Robo-analyst screen."""
    lesson = Text("▸ Spotting a stormy market is possible. Predicting next week's price is close "
                  "to a coin flip — even for a model trained on thousands of examples.", style="yellow")
    if not analyst.ready(game.day, game.market.first_day):
        body = Group(Text(f"The Robo-analyst needs {config.ROBO_LOOKBACK} days of price history "
                          f"before it can read the charts. Today is day {game.day} — try "
                          f"next {config.ROBO_LOOKBACK - game.day}."), training_note(analyst), lesson)
    else:
        body = Group(mood_section(game, analyst), Text(""), outlook_table(game, analyst),
                     training_note(analyst), lesson)
    return Panel(body, title="🤖 Robo-analyst — a tiny machine-learning model (logistic regression)",
                 title_align="left", border_style="magenta", expand=False, width=100)


def symbol_robo_view(game: Game, analyst: RoboAnalyst, symbol: str) -> Panel:
    """One symbol: the forecast, why, and how often it has been right on this symbol."""
    if not analyst.ready(game.day, game.market.first_day):
        return robo_view(game, analyst)
    market = game.market
    chance = analyst.up_chance(market, symbol, game.day)
    record = analyst.price_track_record(market, symbol, game.day)
    reasons = analyst.price.reasons(robo_analyst.symbol_features(market, symbol, game.day))
    body = Group(
        Text.assemble(f"{symbol}: ", chance_text(chance, True),
                      f" chance higher in {config.ROBO_HORIZON} days → ", (robo_analyst.price_call(chance), "bold")),
        Text("Why (pushes towards ▲ up / ▼ down):", style="dim"),
        reasons_table(reasons, "up"),
        Text(track_line(f"Its calls on {symbol} this game", record, "up weeks"), style="dim"),
        Text("▸ The weights are tiny: chart patterns barely predict next week. Real investors "
             "find the same thing.", style="yellow"))
    return Panel(body, title=f"🤖 Robo-analyst on {symbol}", title_align="left",
                 border_style="magenta", expand=False, width=100)


def revealed_until(game: Game) -> int:
    """Last day whose mood is public: STORY_REVEAL_LAG days ago, or every day once the game ends."""
    return game.day if game.is_over() else game.day - config.STORY_REVEAL_LAG


def timeline(game: Game, last_known: int) -> Text:
    """One coloured block per day: the mood, or ░ where it isn't known yet."""
    text = Text()
    for day in range(game.day + 1):
        name = game.market.regime_path[day]
        text.append("█" if day <= last_known else "░",
                    style=REGIME_STYLES[name] if day <= last_known else "dim")
    return text


def story_view(game: Game) -> Panel:
    """The market's hidden moods so far, revealed late — like economists declaring a recession."""
    market, last_known = game.market, revealed_until(game)
    lines = [timeline(game, last_known), Text("")]
    if last_known < 0:
        lines.append(Text(f"Too early: moods are only confirmed {config.STORY_REVEAL_LAG} days "
                          f"after they happen. Come back on day {config.STORY_REVEAL_LAG}."))
    for name, first, last in spells(market.regime_path[:max(0, last_known + 1)]):
        regime = market.regime_model.regimes[name]
        # Measure from the close before the spell, so its first day's move counts too.
        before = max(0, first - 1)
        index = market.index_symbol()
        move = (market.price(index, last) / market.price(index, before) - 1) * 100
        lines.append(Text.assemble((f"{regime.emoji} {regime.label:16}", REGIME_STYLES[name]),
                                   f" day {first:>3} → {last:<3}  {index} ",
                                   signed(move, "%", 1)))
    if not game.is_over() and last_known >= 0:
        lines.append(Text(f"Days {last_known + 1}–{game.day}: not confirmed yet (░). "
                          "Ask the Robo-analyst for a guess: robo", style="dim"))
    seen = []  # a list, not a set, so the explanations always come out in the same order
    for name, _, _ in spells(market.regime_path[:max(0, last_known + 1)]):
        if name not in seen:
            seen.append(name)
    for name in seen:
        regime = market.regime_model.regimes[name]
        lines.append(Text(f"{regime.emoji} {regime.about}", style="italic dim"))
    return Panel(Group(*lines), title="📖 The market's story — hidden moods, revealed late",
                 title_align="left", border_style="blue", expand=False, width=100)


def sectors_view(game: Game) -> Table:
    """Each sector: today, last 5 days and since day 0 (equal-weight average of its stocks)."""
    market, day = game.market, game.day
    table = Table(title=f"Sectors — day {day}", title_justify="left", box=box.SIMPLE_HEAVY)
    for heading in ("Sector", "Companies", "Today", "5 days", "Since day 0", "", "Best since day 0"):
        table.add_column(heading, justify="right" if heading in ("Today", "5 days", "Since day 0") else "left")
    rows = []
    for sector in market.sectors():
        members = [s for s, stock in market.stocks.items() if stock.sector == sector]
        averages = [sum(analytics.change(market.history(s, 0, day), n) for s in members) / len(members) * 100
                    for n in (1, 5, day)]
        best = max(members, key=lambda s: market.price(s, day) / market.price(s, 0))
        rows.append((sector, members, averages, best))
    biggest = max(abs(r[2][2]) for r in rows) or 1
    for sector, members, (today, week, total), best in sorted(rows, key=lambda r: r[2][2], reverse=True):
        table.add_row(sector_text(sector), " ".join(members), signed(today, "%"), signed(week, "%", 1),
                      signed(total, "%", 1), bar(total, biggest, "green" if total >= 0 else "red"),
                      Text.assemble(f"{best} ", signed((market.price(best, day) / market.price(best, 0) - 1) * 100, "%", 1)))
    return table


TIP_STYLES = {WARN: ("⚠ ", "yellow"), PRAISE: ("✔ ", "green")}


def tip_line(tip: Tip) -> Text:
    """One coach tip with its icon and colour."""
    icon, colour = TIP_STYLES.get(tip.severity, ("💡 ", "cyan"))
    return Text(f"{icon}Coach: {tip.message}", style=colour)


def coach_view(tips: list[Tip]) -> Panel:
    """All session tips, or a word of encouragement."""
    lines = [tip_line(tip) for tip in tips] or [Text("No tips right now — your habits look fine. "
                                                     "Keep going!", style="green")]
    return Panel(Group(*lines), title="🧑‍🏫 Trade Coach", title_align="left",
                 border_style="yellow", expand=False, width=100)


def whatif_view(results: list[ReplayResult], lessons: list[str], end_day: int, index: str) -> Group:
    """Ranked strategy table, a chart of the key curves and the lessons (E-04)."""
    table = Table(title=f"What-if Replay — the same market, day 0 → {end_day}, $10,000 each",
                  title_justify="left", box=box.SIMPLE_HEAVY)
    for heading in ("#", "Strategy", "Final", "Return", "Max drop", "Trades", "Fees"):
        table.add_column(heading, justify="left" if heading == "Strategy" else "right")
    for rank, r in enumerate(results, start=1):
        style = "bold reverse" if r.name == YOURS else ""
        table.add_row(str(rank), r.name, money(r.final), signed(r.total_return * 100, "%", 1),
                      f"{r.max_drawdown:.1%}", str(r.trades), f"{r.fees:,.0f}", style=style)
    shown = chart_picks(results, index)
    curves = {r.name: r.curve for r in shown}
    legend = "   ".join(f"{m} {r.name}" for m, r in zip(charts.MARKERS, shown))
    chart = "\n".join(charts.line_chart(curves)) if end_day >= 1 else ""
    advice = Text("\n".join(f"▸ {line}" for line in lessons), style="yellow")
    return Group(table, Text(legend, style="bold"), chart, advice)


def chart_picks(results: list[ReplayResult], index: str) -> list[ReplayResult]:
    """The curves worth drawing: yours, the whole market, the best and the worst."""
    by_name = {r.name: r for r in results}
    picks = [by_name[YOURS], by_name[f"Hold {index}"], results[0], results[-1]]
    unique = []
    for r in picks:
        if r not in unique:
            unique.append(r)
    return unique[:config.WHATIF_CHART_LINES]


def tick_line(game: Game) -> Text:
    """'⏱ Day 4 · 11:35 — 50 ticks to the close' (or the closing bell)."""
    if game.is_open():
        left = game.market.ticks_per_day - game.tick
        return Text(f"⏱ Day {game.day + 1} · {clock_text(game.tick)} — {left} ticks to the close", style="bold")
    return Text(f"🔔 Closing bell: day {game.day} is done.", style="bold")


def breaking_line(event: MarketEvent, tick: int) -> Text:
    """A headline as it breaks during the session (its full effect is only known at the close)."""
    return Text.assemble((f"BREAKING {clock_text(tick)}: {event.headline}", "bold yellow"),
                         ("  " + event.explanation, "italic dim"))


def margin_call_line(trades: list[Trade]) -> Text:
    """'📞 MARGIN CALL — the broker sold 106 X @ $65.00 …' for one forced sale."""
    sold = ", ".join(f"{t.qty} {t.symbol} @ {money(t.price)}" for t in trades)
    return Text(f"📞 MARGIN CALL — your money fell below the broker's minimum, so it sold {sold} "
                "to cover your loan.", style="bold red")


def leverage_view(game: Game) -> Panel:
    """The margin account right now, plus how small a fall hurts at each leverage."""
    account, prices = game.portfolio, game.current_prices()
    used, room = margin.leverage_used(account, prices), margin.fall_to_call(account, prices)
    status = Text.assemble(
        ("Allowed leverage ", "bold"), f"{account.max_leverage:.0f}×   ",
        ("Using ", "bold"), f"{used:.2f}×   ", ("Loan ", "bold"), money(account.loan()),
        f" at {config.MARGIN_RATE:.0%}/yr   ", ("Interest paid ", "bold"), money(account.interest_paid), "\n",
        ("Buying power ", "bold"), money(margin.buying_power(account, prices)), "   ",
        ("Margin call if your holdings fall ", "bold"),
        Text(f"{room:.1%}", style="red" if room < config.MARGIN_DANGER else "green") if account.loan() else "— (no loan)")
    table = Table(title="What leverage does to a fall", title_justify="left", box=box.SIMPLE_HEAVY)
    for heading in ("Leverage", "$10,000 of yours buys", "Margin call after a fall of", "Wiped out after"):
        table.add_column(heading, justify="right")
    for level, _maintenance, call, wipe in leverage_lab.risk_table():
        table.add_row(f"{level}×", money(config.STARTING_CASH * level), "never (no loan)" if level == 1 else f"{call:.1%}",
                      f"{wipe:.0%}", style="bold" if level == account.max_leverage else "")
    hint = Text(f"Change it: leverage 2 (1 = cash only, up to {config.MAX_LEVERAGE}). Replay the market "
                "with borrowed money: levlab", style="dim")
    return Panel(Group(status, table, hint), title="🏦 Margin account", title_align="left",
                 border_style="magenta", expand=False, width=100)


def leverage_lab_view(symbol: str, runs: list[LeverageRun], lessons: list[str], start: int, end: int) -> Group:
    """Each way of holding `symbol` with leverage, a chart of the curves and the lessons (E-08)."""
    table = Table(title=f"Leverage Lab — {money(config.LAB_DEFAULT_AMOUNT)} of your own money in {symbol}, "
                        f"day {start} → {end}", title_justify="left", box=box.SIMPLE_HEAVY)
    for heading in ("Way", "Final", "Return", "Max drop", "Margin call", "Interest"):
        table.add_column(heading, justify="left" if heading == "Way" else "right")
    for run in runs:
        table.add_row(run.label, money(run.values[-1]), signed(run.total_return() * 100, "%", 1),
                      f"{analytics.max_drawdown([max(v, 0.01) for v in run.values]):.1%}",
                      f"day {run.called_on}" if run.called_on else "—", money(run.interest))
    shown = [runs[0], runs[1], runs[-2], runs[-1]]
    legend = "   ".join(f"{m} {r.label}" for m, r in zip(charts.MARKERS, shown))
    chart = "\n".join(charts.line_chart({r.label: r.values for r in shown}, first_day=start))
    advice = Text("\n".join(f"▸ {line}" for line in lessons), style="yellow")
    return Group(table, Text(legend, style="bold"), chart, advice)
