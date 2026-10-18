"""Turn the game into plain dicts for the web page's JSON API (D-37).

Pure functions: they read the game and return data, never change it (only session.run
does that), and they never show the page anything the player couldn't see yet: a
running session is only read up to the current tick.
"""

import datetime
import io
import math
import statistics

from rich.console import Console
from rich.terminal_theme import MONOKAI

from tradesim import config
from tradesim.cli import app, progress, views
from tradesim.education import (academy, challenges, coach, diversification_lab, explainer,
                                headline_lab, leverage_lab, robo_analyst, whatif)
from tradesim.education.achievements import BADGES
from tradesim.engine import analytics, margin
from tradesim.engine.errors import TradeSimError
from tradesim.engine.game import Game
from tradesim.engine.intraday import Session, clock_text
from tradesim.loader import load_challenges, load_list
from tradesim.webapp.session import WebSession

START_DATE = datetime.date.fromisoformat(config.GAME_START_DATE)


def trading_date(day: int) -> datetime.date:
    """The calendar date of a trading day: day 0 is a Monday and weekends are skipped."""
    weeks, weekday = divmod(day, 5)
    return START_DATE + datetime.timedelta(days=weeks * 7 + weekday)


def date_label(day: int) -> str:
    """'Mon 05 Jan' for a trading day."""
    return trading_date(day).strftime("%a %d %b")


def finite(value: float) -> float | None:
    """JSON has no infinity: send None instead."""
    return value if math.isfinite(value) else None


def to_html(output: list) -> str:
    """Draw the terminal's rich screens as HTML (used by the Terminal page and the report)."""
    console = Console(record=True, width=config.WEB_WIDTH, file=io.StringIO(),
                      color_system="truecolor", force_terminal=True)
    for renderable in output:
        console.print(renderable)
    # MONOKAI: the terminal colours that read well on the page's dark background
    return console.export_html(theme=MONOKAI, inline_styles=True, code_format='<pre class="rich">{code}</pre>')


def report_html(game: Game) -> str:
    """The terminal's report (grade, goals, coach, the market's story) as HTML."""
    return to_html(app.report_bundle(game))


def universe(game: Game) -> dict:
    """What never changes during a game: names, sectors, ETF holdings, the settings."""
    market = game.market
    rows = [{"symbol": s, "name": stock.name, "sector": stock.sector, "etf": False, "beta": stock.beta,
             "about": stock.description} for s, stock in market.stocks.items()]
    rows += [{"symbol": s, "name": etf.name, "sector": "ETF", "etf": True, "about": etf.description,
              "holdings": sorted(etf.weights.items(), key=lambda pair: -pair[1])}
             for s, etf in market.etfs.items()]
    return {"symbols": rows, "sectors": market.sectors(), "index": market.index_symbol(),
            "cards": [s for s in config.WEB_INDEX_CARDS if s in market.etfs],
            "ticks": market.ticks_per_day, "max_leverage": config.MAX_LEVERAGE,
            "leverage_levels": list(config.LEVERAGE_LAB_LEVELS), "margin_rate": config.MARGIN_RATE,
            "fee": config.FEE_PER_TRADE, "seed": market.seed, "days": market.num_days}


def board_session(game: Game) -> tuple[Session | None, int]:
    """The session the board shows and how far into it: the running one, else the last one."""
    market = game.market
    if game.is_open():
        return market.session(game.day + 1), game.tick
    if game.day > market.first_day:
        session = market.session(game.day)
        return session, session.ticks()
    return None, 0


def clock(game: Game) -> dict:
    """Where the game is: day, time of day and whether the market is open."""
    market = game.market
    phase = "over" if game.is_over() else "open" if game.is_open() else "closed"
    shown = game.day + 1 if game.is_open() else game.day
    fear = market.fear_index(game.day)
    challenge = game.challenge
    return {"day": game.day, "tick": game.tick, "days": market.num_days, "phase": phase,
            "shown_day": shown, "date": date_label(shown),
            "time": clock_text(game.tick) if game.is_open() else "16:00",
            "next_date": date_label(game.day + 1), "ticks": market.ticks_per_day,
            "fear": round(fear, 1), "fear_word": views.fear_label(fear)[0], "seed": market.seed,
            "challenge": None if challenge is None else
            {"id": challenge.id, "title": challenge.title, "emoji": challenge.emoji,
             "goals": [{"text": c.text, "now": c.now, "passed": c.passed} for c in challenges.progress(game)]}}


def quotes(game: Game) -> list[dict]:
    """Every row of the price board: reference, open/high/low/last, volume and the book."""
    market = game.market
    session, tick = board_session(game)
    books = market.order_books(session.day, tick) if session else {}
    rows = []
    for symbol in market.symbols():
        if session is None:
            last = market.price(symbol, game.day)
            ref, bar = last, (last, last, last, last, 0)
        else:
            ref, bar = session.prices[symbol][0], session.bar(symbol, tick)
        bids, asks = books.get(symbol, ([], []))
        rows.append({"s": symbol, "ref": ref, "o": bar[0], "h": bar[1], "l": bar[2], "c": bar[3],
                     "v": bar[4], "bid": bids, "ask": asks})
    return rows


def sparks(game: Game) -> dict[str, list[float]]:
    """Today's path so far for the index cards at the top."""
    session, tick = board_session(game)
    if session is None:
        return {}
    return {s: session.prices[s][:tick + 1] for s in config.WEB_INDEX_CARDS if s in session.prices}


def account(game: Game) -> dict:
    """Cash, loan, equity, profit and the margin numbers."""
    p, prices = game.portfolio, game.current_prices()
    equity = p.equity(prices)
    previous = game.equity_history[-1] if game.is_open() else game.equity_history[max(0, len(game.equity_history) - 2)]
    return {"cash": p.cash, "equity": equity, "loan": p.loan(), "start": p.starting_cash,
            "pnl": equity - p.starting_cash, "pnl_pct": p.total_return_pct(prices) / 100,
            "day_pnl": equity - previous, "day_pct": equity / previous - 1 if previous else 0.0,
            "invested": p.market_value(prices), "buying_power": margin.buying_power(p, prices),
            "leverage": p.max_leverage, "used": finite(margin.leverage_used(p, prices)),
            "maintenance": margin.maintenance(p.max_leverage), "room": margin.fall_to_call(p, prices),
            "interest": p.interest_paid, "fees": p.fees_paid, "realised": p.realised_pnl,
            "unrealised": p.unrealised_pnl(prices), "margin_calls": len(game.margin_calls)}


def positions(game: Game) -> list[dict]:
    """Every holding with its profit."""
    p, prices = game.portfolio, game.current_prices()
    weights = p.weights(prices)
    return [{"s": s, "qty": pos.qty, "avg": pos.avg_cost, "last": prices[s], "value": pos.market_value(prices[s]),
             "pnl": pos.unrealised_pnl(prices[s]), "pnl_pct": prices[s] / pos.avg_cost - 1, "weight": weights[s]}
            for s, pos in p.positions.items()]


def state(session: WebSession, since: int) -> dict:
    """Everything that changes tick by tick, plus the notices the page hasn't shown."""
    game = session.game
    return {"clock": clock(game), "account": account(game), "positions": positions(game),
            "quotes": quotes(game), "sparks": sparks(game), "notices": session.notices_since(since)}


def candle(label: str, prices: list[float], volumes: list[int], key: int) -> dict:
    """One candle from a run of prices (first = the previous close)."""
    return {"t": label, "k": key, "o": prices[0], "h": max(prices), "l": min(prices), "c": prices[-1],
            "v": sum(volumes)}


def chart(game: Game, symbol: str, span: str) -> dict:
    """Candles for `symbol`: 15-minute ones for "1D", daily ones for the longer spans."""
    game.market.name_of(symbol)      # raises UnknownSymbolError
    if span == "1D":
        return intraday_chart(game, symbol)
    if span not in config.WEB_CHART_RANGES:
        raise TradeSimError(f"Unknown chart range {span}")
    market = game.market
    first = max(market.first_day + 1, game.day - config.WEB_CHART_RANGES[span] + 1)
    candles = []
    for day in range(first, game.day + 1):
        o, h, l, c, v = market.bar(symbol, day)
        candles.append({"t": date_label(day), "k": day, "o": o, "h": h, "l": l, "c": c, "v": v})
    if game.is_open():
        o, h, l, c, v = market.session(game.day + 1).bar(symbol, game.tick)
        candles.append({"t": date_label(game.day + 1), "k": game.day + 1, "o": o, "h": h, "l": l, "c": c,
                        "v": v, "live": True})
    markers = [{"k": t.day + (1 if t.tick else 0), "side": t.side, "qty": t.qty, "price": t.price,
                "forced": bool(t.note)} for t in game.portfolio.trades if t.symbol == symbol]
    return {"symbol": symbol, "span": span, "interval": "1 day", "candles": candles, "markers": markers,
            "ref": None}


def intraday_chart(game: Game, symbol: str) -> dict:
    """15-minute candles of the running (or last) session up to now."""
    session, tick = board_session(game)
    if session is None:
        return {"symbol": symbol, "span": "1D", "interval": "15 min", "candles": [], "markers": [], "ref": None}
    prices, volumes, step = session.prices[symbol], session.volumes[symbol], config.WEB_CANDLE_TICKS
    candles = [candle(clock_text(k - 1), prices[k - 1:min(k + step, tick + 1)],
                      volumes[k:min(k + step, tick + 1)], k) for k in range(1, tick + 1, step)]
    live_day = session.day
    markers = [{"k": 1 + (t.tick - 1) // step * step, "side": t.side, "qty": t.qty, "price": t.price,
                "forced": bool(t.note)}
               for t in game.portfolio.trades if t.symbol == symbol and t.tick and t.day + 1 == live_day]
    return {"symbol": symbol, "span": "1D", "interval": "15 min", "candles": candles, "markers": markers,
            "ref": prices[0], "date": date_label(live_day)}


def quote(session: WebSession, symbol: str) -> dict:
    """A symbol's profile: what it is, how it has behaved, the robo's view and your position."""
    game, market = session.game, session.game.market
    name = market.name_of(symbol)
    history = market.history(symbol, market.first_day, game.day)
    recent = history[-61:]
    yearly_vol = statistics.stdev(analytics.daily_returns(recent)) * math.sqrt(config.TRADING_DAYS_PER_YEAR)
    result = {"symbol": symbol, "name": name, "etf": market.is_etf(symbol),
              "high": max(history[-126:]), "low": min(history[-126:]), "vol": yearly_vol,
              "m1": analytics.change(history, 21), "m3": analytics.change(history, 63),
              "since_start": market.price(symbol, game.day) / market.price(symbol, 0) - 1}
    if session.robo.ready(game.day, market.first_day):
        chance = session.robo.up_chance(market, symbol, game.day)
        result["robo"] = {"chance": chance, "call": robo_analyst.price_call(chance)}
    if market.is_etf(symbol):
        etf = market.etfs[symbol]
        result["holdings"] = [{"s": s, "w": w, "sector": market.stocks[s].sector}
                              for s, w in sorted(etf.weights.items(), key=lambda pair: -pair[1])]
    else:
        stock = market.stocks[symbol]
        result.update(sector=stock.sector, beta=stock.beta, about=stock.description)
    held = game.portfolio.positions.get(symbol)
    result["position"] = None if held is None else {"qty": held.qty, "avg": held.avg_cost}
    result["max_buy"] = 0 if game.is_over() else game.max_buy(symbol)
    result["news"] = [n for n in news(session) if symbol in n["hit"]][:5]
    return result


def news(session: WebSession) -> list[dict]:
    """Every headline the player has seen, newest first, with how it moved prices once known."""
    game, market = session.game, session.game.market
    rows = []
    for day in reversed(session.visible_news_days()):
        for event in market.events_on(day):
            verdict = session.ai.cached(event.headline)
            words = headline_lab.keyword_verdict(event.headline, session.words.positive_words,
                                                 session.words.negative_words)
            hit = explainer.affected_symbols(market, event)
            closed = day <= game.day
            rows.append({"day": day, "date": date_label(day), "time": clock_text(market.session(day).news_tick),
                         "headline": event.headline, "explanation": event.explanation, "scope": event.scope,
                         "target": event.target, "hit": hit,
                         "ai": None if verdict is None else {"label": verdict.label, "confidence": verdict.confidence},
                         "words": words.label,
                         "truth": headline_lab.truth(event) if closed else None,
                         "moves": [[s, market.daily_change_pct(s, day)] for s in hit[:6]] if closed else []})
    return rows


def portfolio(game: Game) -> dict:
    """Your money vs the whole market each day, where it sits, every trade and coach tips."""
    market, index = game.market, game.market.index_symbol()
    curve = list(game.equity_history)
    index_path = market.history(index, 0, game.day)
    if game.is_open():
        curve.append(game.equity())
        index_path.append(game.current_prices()[index])
    start_cash = game.portfolio.starting_cash
    exposure = coach.sector_exposure(game)
    trades = [{"when": f"{date_label(t.day + (1 if t.tick else 0))} {clock_text(t.tick) if t.tick else 'close'}",
               "side": t.side, "s": t.symbol, "qty": t.qty, "price": t.price, "fee": t.fee,
               "pnl": t.realised_pnl if t.side == "SELL" else None, "note": t.note}
              for t in reversed(game.portfolio.trades)]
    return {"labels": [date_label(d) for d in range(len(curve))], "you": curve,
            "market": [start_cash * v / index_path[0] for v in index_path], "index": index,
            "sectors": sorted(exposure.items(), key=lambda pair: -pair[1]), "trades": trades,
            "tips": [{"severity": t.severity, "text": t.message} for t in coach.review_session(game)]}


def leverage(game: Game, symbol: str) -> dict:
    """The Leverage page: risk table and the Leverage Lab replay of the last days."""
    market = game.market
    market.name_of(symbol)
    start = max(market.first_day, game.day - config.LEVERAGE_LAB_DAYS)
    runs = leverage_lab.compare(market, symbol, start, game.day)
    return {"symbol": symbol, "labels": [date_label(d) for d in range(start, game.day + 1)],
            "runs": [{"label": r.label, "leverage": r.leverage, "values": r.values, "called_on": r.called_on,
                      "called_label": date_label(r.called_on) if r.called_on is not None else None,
                      "called_index": r.called_on - start if r.called_on is not None else None,
                      "interest": r.interest, "return": r.total_return(),
                      "drop": analytics.max_drawdown([max(v, 0.01) for v in r.values])} for r in runs],
            "lessons": leverage_lab.lessons(runs, symbol, date_label),
            "risk": [{"leverage": lv, "maintenance": m, "call": c, "wipe": w} for lv, m, c, w in leverage_lab.risk_table()]}


def diversification(game: Game, stock: str, etf: str) -> dict:
    """Diversification Lab: the same money in one stock vs an ETF over the last days."""
    market = game.market
    start = max(market.first_day, game.day - config.LEVERAGE_LAB_DAYS)
    result = diversification_lab.compare(market, stock, etf, start, game.day)
    sides = [{"symbol": side.symbol, "values": side.values, "return": side.total_return,
              "vol": side.volatility, "worst": side.worst_day, "drop": side.max_drawdown}
             for side in (result.stock, result.etf)]
    return {"labels": [date_label(d) for d in range(start, game.day + 1)], "sides": sides,
            "verdict": result.verdict, "amount": result.amount}


def what_if(session: WebSession) -> dict:
    """What-if Replay: every strategy on this market from day 0 to today, best first."""
    game = session.game
    if game.day == 0:
        raise TradeSimError("Nothing to replay on day 0. Play a few days first.")
    results = whatif.compare_strategies(game, session.robo)
    return {"labels": [date_label(d) for d in range(game.day + 1)],
            "results": [{"name": r.name, "about": r.about, "final": r.final, "return": r.total_return,
                         "drop": r.max_drawdown, "trades": r.trades, "fees": r.fees, "curve": r.curve}
                        for r in results],
            "lessons": whatif.lessons(results, game.market.index_symbol()), "yours": whatif.YOURS}


def robo(session: WebSession) -> dict:
    """The Robo-analyst's market-mood call and its most confident symbol forecasts."""
    game, analyst, market = session.game, session.robo, session.game.market
    if not analyst.ready(game.day, market.first_day):
        return {"ready": False}
    chance = analyst.downturn_chance(market, game.day)
    calls = sorted(((s, analyst.up_chance(market, s, game.day)) for s in market.symbols()), key=lambda p: -p[1])
    shown = config.WEB_OUTLOOKS_SHOWN
    reasons = analyst.mood.reasons(robo_analyst.market_features(market, game.day))
    return {"ready": True, "downturn": chance, "mood_call": robo_analyst.mood_call(chance),
            "reasons": sorted(reasons.items(), key=lambda pair: -abs(pair[1])),
            "up": [{"s": s, "chance": c} for s, c in calls[:shown]],
            "down": [{"s": s, "chance": c} for s, c in calls[-shown:][::-1]],
            "mood_report": analyst.mood.report, "price_report": analyst.price.report}


def learn(game: Game) -> dict:
    """Glossary, the next quiz question and the badge wall."""
    questions = load_list(config.QUIZ_PATH, "questions")
    number, question = academy.current_question(questions, len(game.quiz_results))
    return {"terms": load_list(config.GLOSSARY_PATH, "terms"),
            "quiz": {"number": number, "total": len(questions), "question": question["question"],
                     "options": question["options"], "right": sum(game.quiz_results),
                     "answered": len(game.quiz_results)},
            "badges": [{"id": b.badge_id, "emoji": b.emoji, "title": b.title, "how": b.how,
                        "won": b.badge_id in game.badges} for b in BADGES]}


def challenge_list(game: Game) -> list[dict]:
    """Every challenge with its goals in words."""
    return [{"id": c.id, "title": c.title, "emoji": c.emoji, "intro": c.intro, "lesson": c.lesson,
             "goals": [progress.goal_text(goal) for goal in c.goals], "start": c.start,
             "playing": game.challenge is not None and game.challenge.id == c.id}
            for c in load_challenges(config.CHALLENGES_PATH).values()]
