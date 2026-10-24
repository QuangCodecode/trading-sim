"""The web app (D-37): the session's notices, the JSON builders and the HTTP server."""

import json
import re
import threading
import urllib.error
import urllib.request
from contextlib import closing
from http.server import HTTPServer

import pytest

from tradesim import config
from tradesim.database import open_player
from tradesim.engine.errors import TradeSimError
from tradesim.webapp import api, server
from tradesim.webapp.session import WebSession


class FakeAI:
    """Never loads Laya: no cached answers, no classifier."""

    def cached(self, headline):
        return None

    def classify(self, headline):
        return None


@pytest.fixture
def session():
    return WebSession(42, 60, ai=FakeAI())


def kinds(session, since=0):
    return [n["kind"] for n in session.notices_since(since)]


def test_trading_dates_skip_weekends():
    assert api.date_label(0) == "Mon 05 Jan" and api.date_label(4) == "Fri 09 Jan"
    assert api.date_label(5) == "Mon 12 Jan" and api.date_label(-1) == "Fri 02 Jan"


def test_state_before_the_bell_shows_the_last_close(session):
    state = api.state(session, 0)
    assert state["clock"]["phase"] == "closed" and state["clock"]["day"] == 0
    nvda = next(q for q in state["quotes"] if q["s"] == "NVDA")
    assert nvda["c"] == session.game.market.price("NVDA", 0) and len(nvda["bid"]) == 3
    assert len(state["quotes"]) == len(session.game.market.symbols())
    json.dumps(state)                                  # everything is JSON-ready


def test_board_never_peeks_past_the_current_tick(session):
    session.run("tick 10")
    nvda = next(q for q in api.state(session, 0)["quotes"] if q["s"] == "NVDA")
    path = session.game.market.session(1).prices["NVDA"]
    assert nvda["c"] == path[10] and nvda["h"] == max(path[1:11]) and nvda["ref"] == path[0]


def test_trade_tip_and_badge_notices(session):
    session.run("buy NVDA 60")
    assert kinds(session)[:1] == ["trade"] and "badge" in kinds(session)


def test_closing_bell_notice_carries_the_day_summary(session):
    session.run(f"tick {config.TICKS_PER_DAY}")
    close = next(n for n in session.notices_since(0) if n["kind"] == "close")
    assert close["data"]["to"] == 1 and close["data"]["index"] == "MKT100" and len(close["data"]["best"]) == 3


def test_news_is_announced_when_it_breaks_not_before(session):
    market = session.game.market
    day = next(d for d in range(1, 61) if market.events_on(d))
    session.run(f"next {day - 1}") if day > 1 else None
    seen = session.notices[-1].notice_id if session.notices else 0
    news_tick = market.session(day).news_tick
    if news_tick > 1:
        session.run(f"tick {news_tick - 1}")
        assert "news" not in kinds(session, seen)
    session.run("tick 1")
    assert "news" in kinds(session, seen)


def test_margin_call_and_leverage_notices(session):
    session.run("challenge margin")                     # 3× all-in, a bear market
    first = session.notices[-1].notice_id
    session.run("next 60")
    assert "margin" in kinds(session, first)
    session.run("new 5")
    session.run("leverage 2")
    assert kinds(session)[-1] == "info"


def test_new_game_forgets_old_news(session):
    session.run("next 30")
    session.run("new 7")
    assert session.news_seen == set(session.visible_news_days()) and kinds(session)[-1] == "game"


def test_charts(session):
    session.run("tick 7")
    intraday = api.chart(session.game, "NVDA", "1D")
    assert len(intraday["candles"]) == 3 and intraday["ref"] == session.game.market.price("NVDA", 0)
    daily = api.chart(session.game, "MKT100", "1M")
    assert daily["candles"][-1]["live"] and len(daily["candles"]) == 21 + 1   # 21 closed days + today
    with pytest.raises(TradeSimError):
        api.chart(session.game, "NVDA", "5Y")


def test_trade_markers_land_on_their_candle(session):
    session.run("tick 4")
    session.run("buy AAPL 1")
    session.run("tick 2")
    assert api.chart(session.game, "AAPL", "1D")["markers"][0]["k"] == 4
    session.run(f"tick {config.TICKS_PER_DAY}")
    assert api.chart(session.game, "AAPL", "1M")["markers"][0]["k"] == 1


def test_pages_build(session):
    session.run("buy MKT100 10")
    session.run("next 25")
    assert api.quote(session, "NVDA")["robo"]["call"]
    assert api.quote(session, "MIX6")["holdings"][0]["w"] == 0.20
    assert api.portfolio(session.game)["you"][0] == config.STARTING_CASH
    assert len(api.leverage(session.game, "MKT100")["runs"]) == 5
    assert api.diversification(session.game, "NVDA", "MIX6")["verdict"]
    assert api.what_if(session)["results"]
    assert api.robo(session)["ready"]
    assert api.learn(session.game)["quiz"]["options"]
    assert any(c["id"] == "margin" for c in api.challenge_list(session.game))
    assert all(n["truth"] for n in api.news(session))   # every headline so far has closed
    assert "Final report" in api.report_html(session.game) or "report" in api.report_html(session.game).lower()


def test_what_if_needs_a_day(session):
    with pytest.raises(TradeSimError):
        api.what_if(session)


# ---------------------------------------------------------------- the HTTP server

@pytest.fixture
def base_url(session):
    """A real server on a free port, answered by a background thread for this test."""
    server.Handler.session = session
    httpd = HTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def call(url, body=None, raw=None, content_type="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    request = urllib.request.Request(url, data=data, headers={"Content-Type": content_type})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_server_serves_the_page_and_state(base_url):
    status, page = call(base_url + "/")
    assert status == 200 and b"TradeSim" in page
    status, body = call(base_url + "/api/state?since=0")
    assert status == 200 and json.loads(body)["clock"]["day"] == 0


def test_every_javascript_import_exists():
    """The page is plain ES modules: one wrong import path blanks the whole app, and no other test would notice."""
    for path in (server.STATIC_DIR / "js").glob("*.js"):
        for name in re.findall(r"from '\./([\w-]+\.js)'", path.read_text()):
            assert (server.STATIC_DIR / "js" / name).is_file(), f"{path.name} imports the missing {name}"


def test_every_id_the_app_shell_looks_up_is_in_the_page():
    """app.js and tutorial.js wire buttons by id at start-up; a missing one would stop the page from loading."""
    page = (server.STATIC_DIR / "index.html").read_text()
    for name in ("app.js", "tutorial.js"):
        for element_id in re.findall(r"getElementById\('([\w-]+)'\)", (server.STATIC_DIR / "js" / name).read_text()):
            assert f'id="{element_id}"' in page, f"{name} looks up #{element_id}, which index.html lacks"


def test_server_runs_commands_and_ticks(base_url, session):
    status, body = call(base_url + "/api/command", {"line": "buy NVDA 2", "html": True})
    reply = json.loads(body)
    assert status == 200 and reply["ok"] and "Bought" in reply["html"] and reply["positions"]
    status, body = call(base_url + "/api/tick", {"ticks": 3})
    assert status == 200 and json.loads(body)["clock"]["tick"] == 3


@pytest.mark.parametrize("path, body, raw", [
    ("/api/command", {"line": "buy NOPE 1"}, None),          # a rule break: friendly message
    ("/api/tick", {"ticks": 0}, None),                        # out of range
    ("/api/tick", {"ticks": "lots"}, None),
    ("/api/command", None, b"not json"),
    ("/api/command", None, b"[1, 2]"),
])
def test_server_rejects_bad_requests_politely(base_url, path, body, raw):
    status, reply = call(base_url + path, body, raw)
    assert status == 400 and json.loads(reply)["error"]


def test_server_refuses_commands_that_are_not_json(base_url, session):
    """Another website can POST text/plain to localhost without asking, so that type is refused."""
    status, _ = call(base_url + "/api/command", {"line": "buy NVDA 2"}, content_type="text/plain")
    assert status == 400 and session.game.portfolio.trades == []


def test_a_bad_since_is_refused_before_the_command_runs(base_url, session):
    status, _ = call(base_url + "/api/command", {"line": "buy NVDA 2", "since": "x"})
    assert status == 400 and session.game.portfolio.trades == []


def test_server_hides_everything_outside_static(base_url):
    for path in ("/api/nope", "/../config.py", "/%2e%2e/server.py", "/js/../../server.py"):
        assert call(base_url + path)[0] == 404


# ---------------------------------------------------------------- saved games (D-46)

def saved_session(db, seed=None, days=60):
    return WebSession(seed, days, ai=FakeAI(), db_path=db)


def test_game_is_resumed_after_a_restart(tmp_path):
    db = tmp_path / "player.db"
    first = saved_session(db, 42)
    for line in ["buy NVDA 5", "tick 10", "next 2", "tick 3"]:
        first.run(line)
    again = saved_session(db)                                      # no seed: continue
    assert (again.game.market.seed, again.game.day, again.game.tick) == (42, first.game.day, 3)
    assert again.game.portfolio.qty_held("NVDA") == 5
    assert again.game.equity() == pytest.approx(first.game.equity())
    assert again.notices == []                                     # no flood of old toasts


def test_a_seed_starts_a_fresh_game_and_keeps_the_old_one(tmp_path):
    db = tmp_path / "player.db"
    saved_session(db, 42).run("buy NVDA 5")
    fresh = saved_session(db, 7)
    assert fresh.game.market.seed == 7 and not fresh.game.portfolio.trades
    assert [g["seed"] for g in api.games(fresh)["games"]] == [7, 42]
    assert saved_session(db).game.market.seed == 7                 # the new one is what resumes now


def test_a_finished_game_is_not_resumed(tmp_path):
    db = tmp_path / "player.db"
    saved_session(db, 42, 5).run("next 5")
    assert saved_session(db).game.day == 0


def test_new_and_challenge_replace_the_saved_game(tmp_path):
    db = tmp_path / "player.db"
    first = saved_session(db, 42)
    first.run("buy NVDA 5")
    first.run("new 9")
    first.run("challenge crash")
    games = api.games(first)["games"]
    assert [g["challenge"] for g in games] == ["crash", None, None]
    assert [g["slot"] for g in games] == ["web", None, None]
    assert saved_session(db).game.challenge.id == "crash"


def test_a_damaged_save_starts_a_new_game_with_a_message(tmp_path, capsys):
    db = tmp_path / "player.db"
    saved_session(db, 42)
    with closing(open_player(db)) as raw, raw:
        raw.execute("INSERT INTO commands VALUES (1, 0, 'sell NVDA 5')")   # nothing to sell
    again = saved_session(db)
    assert "damaged" in capsys.readouterr().out and again.game.day == 0
    assert [g["slot"] for g in api.games(again)["games"]] == ["web", None]   # the bad one is archived


def test_without_a_database_nothing_is_saved(session):
    session.run("buy NVDA 2")
    assert session.game_id is None and api.games(session) == {"games": []}


def test_games_route(base_url):
    status, body = call(base_url + "/api/games")
    assert status == 200 and json.loads(body) == {"games": []}
