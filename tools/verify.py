"""Let a coding agent SEE what it built (D-28): start the real web app on a throwaway database.

    python3 tools/verify.py    start the web app (seed 42) on WEB_PORT and wait until it answers

Then drive it in the browser (tools/screenshot.py) and read the screenshots.
"""

import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_PORT = 8599
WEB_START_TIMEOUT_S = 30


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
    server = subprocess.Popen([sys.executable, "main.py", "--seed", "42", "--no-browser",
                               "--port", str(WEB_PORT), "--db", str(db_file)], cwd=ROOT)
    deadline = time.monotonic() + WEB_START_TIMEOUT_S
    while not web_is_up():
        if server.poll() is not None or time.monotonic() > deadline:
            print("FAIL web app did not start — run `python3 main.py` to see why")
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
    sys.exit(verify_web())
