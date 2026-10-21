"""Rich screens for the player's progress: badges, challenges, glossary and quiz."""

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tradesim import config
from tradesim.cli.views import signed
from tradesim.education import academy, challenges
from tradesim.education.achievements import BADGES, Badge
from tradesim.education.challenges import Challenge
from tradesim.engine.game import Game


def badge_line(badge: Badge) -> Text:
    """The announcement printed when a badge is won."""
    return Text(f"🏅 Badge unlocked: {badge.emoji} {badge.title} — {badge.how}", style="bold magenta")


def badges_view(game: Game) -> Panel:
    """Every badge: won ones in colour, locked ones dimmed with how to earn them."""
    table = Table(box=None, show_header=False, padding=(0, 1))
    for badge in BADGES:
        won = badge.badge_id in game.badges
        table.add_row(badge.emoji if won else "🔒", Text(badge.title, style="bold" if won else "dim"),
                      Text(badge.how, style="" if won else "dim"))
    title = f"🏅 Achievements — {len(game.badges)} / {len(BADGES)}"
    return Panel(table, title=title, title_align="left", border_style="magenta", expand=False)


def challenges_view(catalogue: dict[str, Challenge]) -> Table:
    """Every challenge with its goals and the command that starts it."""
    table = Table(title="🎯 Challenges — same market for everyone, can you hit the goals?",
                  title_justify="left", box=box.SIMPLE_HEAVY)
    for heading in ("Start with", "Challenge", "Goals", "The setup"):
        table.add_column(heading)
    for challenge in catalogue.values():
        goals = "\n".join(goal_text(goal) for goal in challenge.goals)
        table.add_row(f"[cyan]challenge {challenge.id}[/cyan]", str(challenge), goals,
                      Text(challenge.intro, style="dim"))
    return table


def goal_text(goal: dict) -> str:
    """A goal's wording without needing a game (used in the list)."""
    kind, value = goal["type"], goal.get("value")
    words = {"min_equity": f"Finish ≥ ${value:,.0f}" if value is not None else "",
             "min_return": f"Return ≥ {value:+.0%}" if value is not None else "",
             "beat": f"Beat {goal.get('symbol')}",
             "max_fees": f"Fees ≤ ${value:,.0f}" if value is not None else "",
             "max_drawdown": f"Max drop ≤ {value:.0%}" if value is not None else "",
             "min_invested": f"≥ {value:.0%} invested" if value is not None else "",
             "no_margin_call": "No margin call"}
    return words.get(kind, kind)


def goals_panel(game: Game) -> Panel | None:
    """Live goal progress for the current challenge (None in free play)."""
    checks = challenges.progress(game)
    if not checks:
        return None
    table = Table(box=None, show_header=False, padding=(0, 1))
    for check in checks:
        table.add_row("✅" if check.passed else "⬜", check.text, Text(f"now {check.now}", style="dim"))
    if game.is_over():
        won = challenges.is_won(game)
        verdict = Text("🏆 CHALLENGE COMPLETE!" if won else "✗ Not this time — try again: "
                       f"challenge {game.challenge.id}", style="bold green" if won else "bold red")
        body = Group(table, verdict, Text(f"Lesson: {game.challenge.lesson}", style="yellow"))
    else:
        body = Group(table, Text(f"Goals are checked on the final day (day {game.market.num_days}).",
                                 style="dim"))
    return Panel(body, title=f"🎯 {game.challenge}", title_align="left", border_style="yellow",
                 expand=False)


def challenge_intro(game: Game) -> Panel:
    """Shown when a challenge starts."""
    challenge = game.challenge
    goals = "\n".join(f"  ⬜ {goal_text(goal)}" for goal in challenge.goals)
    start = f"\nYou start with: {', '.join(challenge.start)}" if challenge.start else ""
    body = Text(f"{challenge.intro}\n\nGoals by day {challenge.days}:\n{goals}{start}\n\n"
                "Tip: the market's mood is hidden. Check story, robo and news as you go.")
    return Panel(body, title=f"🎯 Challenge started: {challenge}", title_align="left",
                 border_style="yellow", expand=False, width=90)


def glossary_view(terms: list[dict]) -> Table:
    """Every glossary term with its one-line meaning."""
    table = Table(title="📚 Glossary — type learn TERM for more, e.g. learn beta",
                  title_justify="left", box=box.SIMPLE)
    table.add_column("")
    table.add_column("Term", style="bold cyan")
    table.add_column("In one line")
    for entry in terms:
        table.add_row(entry["emoji"], entry["term"], entry["short"])
    return table


def term_view(entry: dict) -> Panel:
    """One glossary entry, with a command to see it in the game."""
    body = Text.assemble((entry["short"], "bold"), "\n\n", entry["long"], "\n\n",
                         ("See it in the game: ", "dim"), (entry["try"], "cyan"))
    return Panel(body, title=f"{entry['emoji']} {entry['term']}", title_align="left",
                 border_style="cyan", expand=False, width=80)


def question_view(number: int, question: dict, total: int, score: tuple[int, int]) -> Panel:
    """One quiz question with lettered options."""
    options = "\n".join(f"  [bold cyan]{letter}[/bold cyan]  {option}"
                        for letter, option in zip(academy.LETTERS, question["options"]))
    body = Text.from_markup(f"[bold]{question['question']}[/bold]\n\n{options}\n\n"
                            "[dim]Answer with: quiz A (or B, C, D)[/dim]")
    right, asked = score
    return Panel(body, title=f"🧠 Quiz — question {number + 1} of {total} · score {right}/{asked}",
                 title_align="left", border_style="cyan", expand=False, width=86)


def answer_view(question: dict, correct: bool, score: tuple[int, int]) -> Panel:
    """Right or wrong, the explanation, and the running score."""
    letter = academy.LETTERS[question["answer"]]
    verdict = ("✔ Correct!", "bold green") if correct else (f"✗ Not quite — the answer is {letter}.", "bold red")
    right, asked = score
    body = Text.assemble(verdict, "\n\n", question["explain"], "\n\n",
                         (f"Score {right}/{asked}. Type quiz for the next question.", "dim"))
    return Panel(body, title="🧠 Quiz", title_align="left",
                 border_style="green" if correct else "red", expand=False, width=86)


def games_view(rows: list[dict], catalogue: dict[str, Challenge]) -> Group | str:
    """Every saved game (newest first) and the badges won across all of them."""
    if not rows:
        return ("No saved games yet. They are saved when you play in the web app "
                "(uv run main.py --web) or in agent mode (uv run main.py --seed 42 market).")
    table = Table(box=box.SIMPLE_HEAVY, title="📜 Your saved games", title_justify="left")
    for heading in ("Started", "Game", "Day", "Return", "Market", "Result"):
        table.add_column(heading)
    for row in rows:
        challenge = catalogue.get(row["challenge"]) if row["challenge"] else None
        name = str(challenge) if challenge else f"Free play, seed {row['seed']}"
        table.add_row(row["started_at"].replace("T", " "), name, f"{row['day']} / {row['days']}",
                      signed((row["equity"] / config.STARTING_CASH - 1) * 100, "%", 1),
                      signed(row["market_return"] * 100, "%", 1), game_result(row))
    won = {badge for row in rows for badge in row["badges"]}
    emojis = " ".join(badge.emoji for badge in BADGES if badge.badge_id in won)
    footer = Text(f"🏅 Badges won across games: {len(won)} / {len(BADGES)}  {emojis}", style="magenta")
    return Group(table, footer)


def game_result(row: dict) -> Text:
    """'passed' / 'failed' for a finished challenge, 'finished' for free play, else how it stands."""
    if row["passed"] is not None:
        return Text("✅ passed", style="green") if row["passed"] else Text("❌ failed", style="red")
    if row["over"]:
        return Text("🏁 finished")
    return Text("▶ playing now" if row["slot"] else "left unfinished", style="dim")
