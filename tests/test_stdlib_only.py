"""D-50: playing TradeSim needs only Python itself (and a web browser): no third-party packages."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# tools/screenshot.py talks to Chrome with `websockets` (a dev tool, not part of the game).
DEV_ONLY = {ROOT / "tools" / "screenshot.py"}


def imported_modules(path: Path) -> set[str]:
    """The top-level package name of every import in one file."""
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_the_game_imports_only_the_standard_library_and_itself():
    files = [ROOT / "main.py", *(ROOT / "tradesim").rglob("*.py"), *(ROOT / "tools").glob("*.py")]
    allowed = set(sys.stdlib_module_names) | {"tradesim"}
    outside = {f.relative_to(ROOT).as_posix(): sorted(imported_modules(f) - allowed)
               for f in files if f not in DEV_ONLY and imported_modules(f) - allowed}
    assert outside == {}, "third-party imports found (D-50)"
