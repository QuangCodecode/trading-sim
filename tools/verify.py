"""Let a coding agent SEE what it built (D-28): play a fixed game and save every screen.

    uv run tools/verify.py cli    play seed 42 through agent mode → verify-out/cli.txt
    uv run tools/verify.py web    start the web app (seed 42) on WEB_PORT and wait until it answers

Each step runs the real `main.py` in a new process, exactly as an AI player would, and
checks its exit code. The transcript is the evidence: read it, don't just trust the ✓.
"""

import shlex
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "verify-out"
WEB_PORT = 8599
WEB_START_TIMEOUT_S = 30

# (command line, expected exit code). Touches every command and the main error paths.
CLI_SCRIPT = [
    ("help", 0),
    ("--seed 42 market", 0),
    ("market tech", 0),
    ("market etf", 0),
    ("market spaceships", 1),
    ("quote nvda", 0),
    ("etf", 0),
    ("buy nvda 20", 0),
    ("buy XYZ 1", 1),
    ("buy nvda ten", 1),
    ("buy mix6 max", 0),
    ("tick 6", 0),
    ("leverage", 0),
    ("leverage 9", 1),
    ("leverage 2", 0),
    ("buy mkt100 max", 0),
    ("portfolio", 0),
    ("levlab", 0),
    ("levlab nvda", 0),
    ("next 5", 0),
    ("news", 0),
    ("lab", 0),
    ("chart nvda mix6", 0),
    ('hl "Walmart sales not as bad as feared"', 0),
    ("--seed 7 market", 1),
    ("next 20", 0),
    ("robo", 0),
    ("robo nvda", 0),
    ("story", 0),
    ("sectors", 0),
    ("coach", 0),
    ("whatif", 0),
    ("learn beta", 0),
    ("quiz", 0),
    ("quiz b", 0),
    ("quiz z", 1),
    ("badges", 0),
    ("next 100", 0),
    ("buy aapl 1", 1),
    ("history", 0),
    ("report", 0),
    ("challenge", 0),
    ("challenge nope", 1),
    ("challenge tech", 0),
    ("next 60", 0),
    ("games", 0),
]


def run_step(db_file: Path, line: str) -> subprocess.CompletedProcess:
    """One agent-mode call: python main.py --db FILE <line> (a throwaway player database)."""
    command = [sys.executable, "main.py", "--db", str(db_file)] + shlex.split(line)
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)


def verify_cli() -> int:
    """Play CLI_SCRIPT, write the transcript, print one line per step. Exit 1 on any surprise."""
    OUT_DIR.mkdir(exist_ok=True)
    transcript, failures = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        db_file = Path(tmp) / "verify.db"
        for line, expected in CLI_SCRIPT:
            result = run_step(db_file, line)
            ok = result.returncode == expected and "Traceback" not in result.stderr
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} exit {result.returncode} (want {expected})  {line}")
            transcript.append(f"$ main.py {line}\n[exit {result.returncode}]\n{result.stdout}{result.stderr}")
    out = OUT_DIR / "cli.txt"
    out.write_text("\n".join(transcript), encoding="utf-8")
    print(f"\n{len(CLI_SCRIPT) - failures}/{len(CLI_SCRIPT)} steps as expected. Read the evidence: {out}")
    return 1 if failures else 0


def web_is_up() -> bool:
    """True once the web app's API answers."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{WEB_PORT}/api/universe", timeout=1) as reply:
            return reply.status == 200
    except OSError:
        return False


def verify_web() -> int:
    """Start the web app (seed 42, throwaway player database), wait until it answers, keep it running."""
    with tempfile.TemporaryDirectory() as tmp:
        return run_web(Path(tmp) / "verify-web.db")


def run_web(db_file: Path) -> int:
    """The body of verify_web, so the temporary database lives as long as the server."""
    server = subprocess.Popen([sys.executable, "main.py", "--web", "--seed", "42", "--no-browser",
                               "--port", str(WEB_PORT), "--db", str(db_file)], cwd=ROOT)
    deadline = time.monotonic() + WEB_START_TIMEOUT_S
    while not web_is_up():
        if server.poll() is not None or time.monotonic() > deadline:
            print("FAIL web app did not start — run `uv run main.py --web` to see why")
            server.kill()
            return 1
        time.sleep(0.5)
    print(f"READY http://127.0.0.1:{WEB_PORT}  (Ctrl+C or kill this process to stop)", flush=True)
    try:
        return server.wait()
    except KeyboardInterrupt:
        server.terminate()
        return 0


if __name__ == "__main__":
    modes = {"cli": verify_cli, "web": verify_web}
    if len(sys.argv) != 2 or sys.argv[1] not in modes:
        sys.exit("Usage: uv run tools/verify.py cli|web")
    sys.exit(modes[sys.argv[1]]())
