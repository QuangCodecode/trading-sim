"""One browser player's game, and the notices the page pops up as toasts (D-37).

Every action is an ordinary command line ("buy NVDA 20", "tick 1", "next 5") run by
cli.app.execute, exactly as a terminal player would type it, so the web app, the REPL
and agent mode share one set of rules and error messages. After each command we compare
the game with a snapshot taken just before and queue a Notice for every change:
trades, coach tips, breaking news, margin calls, the closing bell and badges.
"""

from tradesim import config
from tradesim.ai.sentiment import SentimentClassifier
from tradesim.cli import app
from tradesim.education import achievements, coach
from tradesim.education.robo_analyst import RoboAnalyst
from tradesim.engine import intraday
from tradesim.engine.game import Game
from tradesim.loader import load_events


class Notice:
    """One toast: `kind` picks its look (trade, tip, news, margin, close, badge, game)."""

    def __init__(self, notice_id: int, kind: str, title: str, text: str, data: dict | None = None) -> None:
        """`data` carries extra numbers for the page (e.g. the closing-bell summary)."""
        self.notice_id = notice_id
        self.kind = kind
        self.title = title
        self.text = text
        self.data = data or {}

    def to_dict(self) -> dict:
        """Plain data for the JSON API."""
        return {"id": self.notice_id, "kind": self.kind, "title": self.title, "text": self.text,
                "data": self.data}

    def __repr__(self) -> str:
        return f"Notice({self.notice_id}, {self.kind!r}, {self.title!r})"


class Snapshot:
    """The bits of a game we compare before and after a command."""

    def __init__(self, game: Game) -> None:
        """Copy the counters (not the objects) so later changes show up as differences."""
        self.portfolio = game.portfolio
        self.trades = len(game.portfolio.trades)
        self.margin_calls = len(game.margin_calls)
        self.day = game.day
        self.badges = list(game.badges)
        self.over = game.is_over()
        self.leverage = game.portfolio.max_leverage


class WebSession:
    """The game shown in the browser, the AI helpers and the queue of notices."""

    def __init__(self, seed: int | None = None, days: int = config.GAME_DAYS,
                 ai: SentimentClassifier | None = None, robo: RoboAnalyst | None = None) -> None:
        """Start a game; tests pass a fake `ai` so the model is never loaded."""
        self.ai = ai or SentimentClassifier()
        self.robo = robo or app.robo_model()
        self.game = app.new_game(seed, days)
        self.words = load_events(config.EVENTS_PATH, self.game.market.stocks)   # keyword lists
        self.notices: list[Notice] = []
        self.last_output: list = []
        self._next_id = 1
        self.news_seen: set[int] = set()
        self._forget_old_news()

    def run(self, line: str) -> list:
        """Run one command line and queue notices for what changed. Raises TradeSimError."""
        before = Snapshot(self.game)
        self.last_output = app.execute(self.game, line, self.ai)
        if self.game.portfolio is not before.portfolio:      # `new` or `challenge` restarted
            self._forget_old_news()
            name = self.game.challenge or f"seed {self.game.market.seed}"
            self.notify("game", "New game", f"{name} — the market opens when you press Start.")
        else:
            self._announce(before)
        return self.last_output

    def notify(self, kind: str, title: str, text: str, data: dict | None = None) -> None:
        """Queue one notice (only the newest WEB_MAX_NOTICES are kept)."""
        self.notices.append(Notice(self._next_id, kind, title, text, data))
        self._next_id += 1
        del self.notices[:-config.WEB_MAX_NOTICES]

    def notices_since(self, last_id: int) -> list[dict]:
        """Notices the page hasn't shown yet."""
        return [n.to_dict() for n in self.notices if n.notice_id > last_id]

    def visible_news_days(self) -> list[int]:
        """Days whose headline the player has seen: every closed day, plus today once it broke."""
        game, market = self.game, self.game.market
        days = [d for d in range(1, game.day + 1) if market.events_on(d)]
        if game.is_open() and market.events_on(game.day + 1) and \
                game.tick >= market.session(game.day + 1).news_tick:
            days.append(game.day + 1)
        return days

    def _forget_old_news(self) -> None:
        """A fresh game: everything already visible counts as seen (no flood of toasts)."""
        self.news_seen = set(self.visible_news_days())

    def _announce(self, before: Snapshot) -> None:
        """Queue a notice for each change since `before`."""
        game = self.game
        if game.portfolio.max_leverage != before.leverage:
            borrow = game.portfolio.max_leverage - 1
            self.notify("info", f"Leverage limit: {game.portfolio.max_leverage:.0f}×",
                        f"You may borrow up to ${borrow:.0f} for every $1 of yours." if borrow else "Cash only: no borrowing.")
        for trade in game.portfolio.trades[before.trades:]:
            if trade.note:
                continue                                       # forced sales get the margin notice
            verb = "Bought" if trade.side == "BUY" else "Sold"
            self.notify("trade", f"{verb} {trade.qty} {trade.symbol}", f"@ ${trade.price:,.2f} + ${trade.fee:,.2f} fee",
                        {"side": trade.side, "symbol": trade.symbol})
            for tip in coach.review_trade(game, trade):
                self.notify("tip", "Coach", tip.message, {"severity": tip.severity})
        for trades in game.margin_calls[before.margin_calls:]:
            sold = ", ".join(f"{t.qty} {t.symbol} @ ${t.price:,.2f}" for t in trades)
            self.notify("margin", "Margin call!", f"Your money fell below the broker's minimum, so it sold {sold}.")
        self._announce_news()
        if game.day > before.day:
            self.notify("close", "Closing bell", f"Day {game.day} is done.", self.day_summary(before.day))
        for badge in achievements.BADGES:
            if badge.badge_id in game.badges and badge.badge_id not in before.badges:
                self.notify("badge", f"Badge: {badge.title}", badge.how, {"emoji": badge.emoji})
        if game.is_over() and not before.over:
            self.notify("game", "Game over", "The final report is ready.")

    def _announce_news(self) -> None:
        """A notice per headline that became visible (at most the last 3 when days are skipped)."""
        market = self.game.market
        fresh = [d for d in self.visible_news_days() if d not in self.news_seen]
        for day in fresh[-3:]:
            for event in market.events_on(day):
                when = intraday.clock_text(market.session(day).news_tick)
                verdict = self.ai.cached(event.headline)
                self.notify("news", f"Breaking · Day {day} {when}", event.headline,
                            {"day": day, "explanation": event.explanation,
                             "ai": verdict.label if verdict else None})
        self.news_seen.update(fresh)

    def day_summary(self, start: int) -> dict:
        """Numbers for the closing-bell card: you vs the market since `start`, and the movers."""
        game, market = self.game, self.game.market
        index = market.index_symbol()
        moves = sorted(((s, market.price(s, game.day) / market.price(s, start) - 1) for s in market.stocks),
                       key=lambda pair: pair[1])
        mine = game.equity_history[-1] / game.equity_history[start] - 1
        return {"from": start, "to": game.day, "you": mine, "equity": game.equity_history[-1],
                "market": market.price(index, game.day) / market.price(index, start) - 1, "index": index,
                "best": moves[-3:][::-1], "worst": moves[:3], "over": game.is_over()}
