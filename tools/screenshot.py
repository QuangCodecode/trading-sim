"""Screenshot the web app with headless Google Chrome.

    uv run tools/verify.py web                       # in another terminal (port 8599)
    uv run tools/screenshot.py verify-out/shots "goto http://127.0.0.1:8599/" \\
        "eval localStorage.setItem('tradesim.tutorial','done')" "goto http://127.0.0.1:8599/" "click Open day 1" \\
        "wait 3" "shot board" "nav trade/NVDA" "wait 1" "shot trade"

A fresh Chrome profile shows the required tutorial (D-49): set its flag first, as above.
Steps: goto URL · nav PAGE (the #hash route, e.g. leverage or trade/NVDA) · click BUTTON TEXT ·
clickcss SELECTOR · focus SELECTOR · type TEXT · enter · scroll PIXELS · top · wait SECONDS ·
eval JS · shot NAME

It talks to Chrome over the DevTools protocol with `websockets` (a dev dependency).
Dev tool only: the game never imports it.
"""

import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT = 9333
WIDTH, HEIGHT = 1500, 1000
PAUSE_S = 0.8          # let the page react to a click before the next step

CLICK_JS = """(() => {
  const want = %s, norm = t => (t || '').replace(/\\s+/g, ' ').trim();
  const els = [...document.querySelectorAll('button, a, [role=tab], label, summary')];
  const el = els.find(e => norm(e.innerText) === want) || els.find(e => norm(e.innerText).startsWith(want))
          || els.find(e => norm(e.innerText).endsWith(want));
  if (!el) return false; el.scrollIntoView({block: 'center'}); el.click(); return true; })()"""
NAV_JS = "(() => { location.hash = %s; return true; })()"
MAIN = "document.getElementById('main')"


class Browser:
    """One headless Chrome tab driven over the DevTools protocol."""

    def __init__(self, socket, out: Path) -> None:
        """`socket` is the tab's DevTools websocket; screenshots go to `out`."""
        self.socket = socket
        self.out = out
        self.next_id = 0

    async def call(self, method: str, **params) -> dict:
        """Send one DevTools command and wait for its answer."""
        self.next_id += 1
        await self.socket.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            message = json.loads(await self.socket.recv())
            if message.get("id") == self.next_id:
                return message.get("result", {})

    async def js(self, code: str) -> object:
        """Run JavaScript in the page and return its value."""
        result = await self.call("Runtime.evaluate", expression=code, returnByValue=True, awaitPromise=True)
        return result.get("result", {}).get("value")

    async def report(self, found: object, step: str) -> None:
        """Print what happened, then give the page a moment to react."""
        print(("ok    " if found else "MISSING ") + step)
        await asyncio.sleep(PAUSE_S)


async def run_step(browser: Browser, step: str) -> None:
    """Carry out one step such as "click Buy" or "shot trade"."""
    command, _, arg = step.partition(" ")
    if command == "goto":
        await browser.call("Page.navigate", url=arg)
        await asyncio.sleep(3)
    elif command in ("click", "nav", "clickcss"):
        code = {"click": CLICK_JS % json.dumps(arg), "nav": NAV_JS % json.dumps(arg),
                "clickcss": f"(() => {{const e = document.querySelector({json.dumps(arg)}); e && e.click(); return !!e;}})()"}
        await browser.report(await browser.js(code[command]), step)
    elif command == "focus":
        print("ok    " + step if await browser.js(f"(() => {{const e = document.querySelector({json.dumps(arg)}); e && e.focus(); return !!e;}})()") else "MISSING " + step)
    elif command == "type":
        await browser.call("Input.insertText", text=arg)
    elif command == "enter":
        for kind in ("keyDown", "keyUp"):
            await browser.call("Input.dispatchKeyEvent", type=kind, key="Enter", code="Enter", text="\r",
                               windowsVirtualKeyCode=13, nativeVirtualKeyCode=13)
        await browser.report(True, step)
    else:
        await other_step(browser, command, arg)


async def other_step(browser: Browser, command: str, arg: str) -> None:
    """Scrolling, waiting, JavaScript and screenshots."""
    if command == "scroll":
        await browser.js(f"{MAIN}.scrollBy(0, {int(arg)})")
    elif command == "top":
        await browser.js(f"{MAIN}.scrollTo(0, 0)")
    elif command == "wait":
        await asyncio.sleep(float(arg))
    elif command == "eval":
        print("eval:", await browser.js(arg))
    elif command == "shot":
        image = await browser.call("Page.captureScreenshot", format="png")
        path = browser.out / f"{arg}.png"
        path.write_bytes(base64.b64decode(image["data"]))
        print("saved", path)
    await asyncio.sleep(0.5)


def tab_socket_url() -> str:
    """The DevTools websocket of Chrome's first tab (Chrome takes a moment to start)."""
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://localhost:{PORT}/json"))
            return next(tab["webSocketDebuggerUrl"] for tab in tabs if tab["type"] == "page")
        except (OSError, StopIteration):
            time.sleep(0.2)
    raise SystemExit("Chrome did not start — is Google Chrome installed?")


async def main(out: Path, steps: list[str]) -> None:
    """Start headless Chrome, run every step, then close Chrome."""
    chrome = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}",
                               f"--user-data-dir={out / '.chrome-profile'}", f"--window-size={WIDTH},{HEIGHT}",
                               "--hide-scrollbars", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        async with websockets.connect(tab_socket_url(), max_size=50_000_000) as socket:
            browser = Browser(socket, out)
            await browser.call("Page.enable")
            await browser.call("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT,
                               deviceScaleFactor=1, mobile=False)
            for step in steps:
                await run_step(browser, step)
    finally:
        chrome.terminate()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    folder = Path(sys.argv[1])
    folder.mkdir(parents=True, exist_ok=True)
    asyncio.run(main(folder, sys.argv[2:]))
