"""The web app's HTTP server (D-37), built only from the standard library.

    uv run main.py --web            then open http://127.0.0.1:8000

GET  /                  the page (static/index.html, which loads static/css + static/js)
GET  /api/<name>?…      read-only JSON built by webapp/api.py (/api/games lists the saved games)
POST /api/command       {"line": "buy NVDA 10"} → runs it like a terminal player would
POST /api/tick          {"ticks": 1} → lets the live session run (the page's clock)

One player, one game, one thread: requests are answered one at a time, so the game is
never changed by two requests at once. It only listens on 127.0.0.1 (this computer).
"""

import json
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tradesim import config
from tradesim.engine.errors import TradeSimError
from tradesim.webapp import api
from tradesim.webapp.session import WebSession

STATIC_DIR = (Path(__file__).parent / "static").resolve()
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml",
                 ".png": "image/png", ".ico": "image/x-icon", ".json": "application/json"}
MAX_LINE = 300          # longest command line accepted


def symbol_arg(params: dict, name: str = "symbol", default: str = "") -> str:
    """An upper-case symbol from the query string (validated later by the market)."""
    return params.get(name, [default])[0].strip().upper()[:12]


def number(params: dict, name: str) -> int:
    """A whole number from the query string (0 if missing)."""
    return int(params.get(name, ["0"])[0] or 0)


# Each read-only path → a function of (session, query parameters) that returns a dict.
GET_ROUTES = {
    "/api/universe": lambda s, p: api.universe(s.game),
    "/api/state": lambda s, p: api.state(s, number(p, "since")),
    "/api/chart": lambda s, p: api.chart(s.game, symbol_arg(p), p.get("span", ["1D"])[0].upper()),
    "/api/quote": lambda s, p: api.quote(s, symbol_arg(p)),
    "/api/portfolio": lambda s, p: api.portfolio(s.game),
    "/api/news": lambda s, p: {"news": api.news(s)},
    "/api/leverage": lambda s, p: api.leverage(s.game, symbol_arg(p, default=s.game.market.index_symbol())),
    "/api/diversification": lambda s, p: api.diversification(s.game, symbol_arg(p, "stock", "NVDA"),
                                                             symbol_arg(p, "etf", config.LAB_DEFAULT_ETF)),
    "/api/whatif": lambda s, p: api.what_if(s),
    "/api/robo": lambda s, p: api.robo(s),
    "/api/learn": lambda s, p: api.learn(s.game),
    "/api/challenges": lambda s, p: {"challenges": api.challenge_list(s.game)},
    "/api/games": lambda s, p: api.games(s),
    "/api/report": lambda s, p: {"html": api.report_html(s.game)},
}


def post_command(session: WebSession, body: dict) -> dict:
    """Run one command line; the reply carries its terminal output as HTML."""
    line = str(body.get("line", "")).strip()[:MAX_LINE]
    output = session.run(line)
    return {"ok": True, "html": api.to_html(output) if body.get("html") else ""}


def post_tick(session: WebSession, body: dict) -> dict:
    """Let the session run a few ticks (the page's clock calls this every second or so)."""
    ticks = body.get("ticks", 1)
    if not isinstance(ticks, int) or not 1 <= ticks <= config.TICKS_PER_DAY:
        raise TradeSimError(f"ticks must be a whole number from 1 to {config.TICKS_PER_DAY}")
    session.run(f"tick {ticks}")
    return {"ok": True}


POST_ROUTES = {"/api/command": post_command, "/api/tick": post_tick}


class Handler(BaseHTTPRequestHandler):
    """Answers one request. `session` is set once by `serve` (one player per server)."""

    session: WebSession = None

    def do_GET(self) -> None:
        """Static files, or a JSON API path."""
        url = urlparse(self.path)
        if not url.path.startswith("/api/"):
            self.send_static(url.path)
            return
        route = GET_ROUTES.get(url.path)
        if route is None:
            self.send_json({"error": "Not found"}, 404)
            return
        self.answer(lambda: route(self.session, parse_qs(url.query)))

    def do_POST(self) -> None:
        """A command or a clock tick, with a small JSON body."""
        path = urlparse(self.path).path
        if path not in POST_ROUTES:
            self.send_json({"error": "Not found"}, 404)
            return
        body = self.read_body()
        if body is None:
            self.send_json({"error": "The request body must be a small JSON object."}, 400)
            return
        # The reply also carries the new state, so the page updates without a second request.
        self.answer(lambda: POST_ROUTES[path](self.session, body) | api.state(self.session, int(body.get("since", 0))))

    def answer(self, make_reply) -> None:
        """Send `make_reply()` as JSON: rule breaks become a friendly 400, crashes a 500."""
        try:
            self.send_json(make_reply())
        except TradeSimError as error:
            self.send_json({"error": str(error)}, 400)
        except (ValueError, KeyError, TypeError) as error:
            self.send_json({"error": f"Bad request: {error}"}, 400)
        except Exception:                      # never let one bug kill the server mid-game
            traceback.print_exc()
            self.send_json({"error": "Something went wrong on the server (see the terminal)."}, 500)

    def read_body(self) -> dict | None:
        """The request's JSON object, or None if it is missing, too big or not an object."""
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= config.WEB_MAX_BODY:
            return None
        try:
            body = json.loads(self.rfile.read(length))
        except ValueError:
            return None
        return body if isinstance(body, dict) else None

    def send_json(self, data: dict, status: int = 200) -> None:
        """Reply with `data` as JSON."""
        payload = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_bytes(payload, "application/json", status)

    def send_static(self, path: str) -> None:
        """A file under static/ (index.html for "/"); nothing outside that folder."""
        target = (STATIC_DIR / (path.lstrip("/") or "index.html")).resolve()
        if not target.is_relative_to(STATIC_DIR) or not target.is_file() or target.suffix not in CONTENT_TYPES:
            self.send_json({"error": "Not found"}, 404)
            return
        self.send_bytes(target.read_bytes(), CONTENT_TYPES[target.suffix])

    def send_bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        """Write the status line, headers and body."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args) -> None:
        """Stay quiet: the clock polls every second, which would flood the terminal."""


def serve(seed: int | None, days: int, port: int = config.WEB_PORT, open_browser: bool = True,
          db_path: Path = config.PLAYER_DB_PATH) -> None:
    """Start (or resume) one game, saved in `db_path`, and answer the browser until Ctrl+C."""
    Handler.session = WebSession(seed, days, db_path=db_path)
    server = HTTPServer((config.WEB_HOST, port), Handler)
    url = f"http://{config.WEB_HOST}:{port}"
    game = Handler.session.game
    print(f"TradeSim is running at {url}  (seed {game.market.seed}, day {game.day}) — Ctrl+C to stop", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        server.server_close()
        sys.stdout.flush()
