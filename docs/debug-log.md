# Debug log

Evidence for LO10 (debugging). Add an entry for every real bug worth remembering —
symptom, what the traceback / failing test said, root cause, fix, and the test that now
guards it. Aim for at least 5 entries by the final submission.

## Bug 1 — Lab called a calmer stock "riskier" than the ETF
Symptom:  `--seed 42`, `next 5`, `lab KO` said "KO earned more this time — but you took
          much more risk", yet the table showed KO's daily swing 0.9% < MIX6's 1.1%.
Traceback / failing assert: `assert not any("more risk" in line ...)` → `assert not True`
Cause:    the verdict rule only compared returns (stock > ETF ⇒ "more risk"); it never
          checked whether the stock was actually more volatile.
Fix:      new rule first: stock return > ETF **and** stock vol ≤ ETF vol ⇒ "beat MIX6 this
          time with smaller swings … Try: lab mc KO" (diversification_lab.build_verdict).
Test:     test_calm_stock_that_beat_etf_is_not_called_riskier

## Bug 2 — torch/Laya warnings printed over the game screen
Symptom:  first `hl "…"` printed `W1018 … NOTE: Redirects are currently not supported in
          MacOs.` and a `RuntimeWarning: laya: this checkpoint ships invalid temperatures …`
          between the prompt and the answer.
Traceback / failing assert: none — found by running `main.py` and reading stderr.
Cause:    torch's logging and Laya's `warnings.warn` write to stderr when the model loads.
Fix:      `load_laya` wraps import + load in `warnings.catch_warnings()` and
          `contextlib.redirect_stderr(io.StringIO())`.
Test:     manual (stderr of `printf 'hl "x"' | python3 main.py` is empty). Note: the warning
          says some confidences are *uncalibrated* — call them "Laya's probability", not "accuracy".

## Bug 3 — `hl ""` ran the whole Headline Lab instead of showing usage
Symptom:  `hl ""` printed the full table, but docs/04 §4.3 says it should show `Usage: hl "TEXT"`.
Traceback / failing assert: `test_empty_quoted_headline_shows_usage` → DID NOT RAISE CommandError
Cause:    `parse_headline_text` treated "nothing left after stripping quotes" the same as
          "no text typed" and returned `[]`; my first test had encoded that wrong behaviour.
Fix:      only a bare `hl` returns `[]`; empty quoted text raises the usage error.
Test:     test_empty_quoted_headline_shows_usage

## Bug 4 — `uv run main.py` crashed with ModuleNotFoundError: rich
Symptom:  `uv run main.py --seed 42` printed "Removed virtual environment … Creating virtual
          environment" and then crashed with `ModuleNotFoundError: No module named 'rich'`.
Traceback / failing assert: `tradesim/cli/app.py`, line 5, `from rich.console import Console`
Cause:    the dependencies were only in requirements.txt. uv reads `pyproject.toml`
          (`dependencies = []`) and `.python-version` (3.11), so it replaced the pip-built
          3.14 venv with an empty 3.11 one.
Fix:      list rich/textual/laya in `pyproject.toml` (+ a `dev` group for pytest) and commit `uv.lock`.
Test:     manual: `uv run main.py --seed 42` plays and `uv run pytest` → 144 passed on Python 3.11.

## Bug 5 — Web "Start new game" ignored the seed just typed
Symptom:  typing seed 42 and clicking Start new game gave a random seed (e.g. 636378).
Traceback / failing assert: `test_page_runs_without_errors` → `assert 636378 == 42`
Cause:    the button was `st.button(..., on_click=start_game, args=(seed, days))`. Streamlit
          builds `args` while drawing the page, so they held the inputs from the *previous*
          run (blank seed); the click's callback runs before the page is redrawn.
Fix:      give the inputs keys and read `st.session_state.seed` inside the callback
          (`start_from_sidebar`), the same way the Buy/Sell callbacks already read theirs.
Test:     test_page_runs_without_errors (the Streamlit UI and its tests were deleted in D-45; kept as evidence)

## Bug 6 — Final report praised a 10% loss as "Grade A+ … Superb"
Symptom:  "Survive the Crash", held MKT100 all game: equity −9.98%, market −10.07% →
          `Grade A+  You beat the whole market AND took less risk. Superb.`
Traceback / failing assert: none — found by reading the smoke-test transcript.
Cause:    `grade()` compared `mine > market` with no margin, so beating the market by
          0.09 points (the cash left over after buying) counted as a win, even at a loss.
Fix:      beating the market needs `BEAT_MARGIN` (1 point); a loss that beats the market
          is a B ("you lost clearly less"), never an A. Same margin for the Market Beater badge.
Test:     test_grade_never_praises_a_loss_that_only_matched_the_market, test_grade_b_for_losing_clearly_less_than_the_market

## Bug 7 — Crashes looked harmless in the market story
Symptom:  `story` showed `💥 Market crash day 23 → 30  MKT100 -0.8%` while the fear gauge read 36 (panic).
Cause:    two things. (1) The spell's move was measured from its *first* close, so the crash's
          biggest day was left out. (2) A crash drift of −0.9%/day drowned in 3× volatility.
Fix:      measure from the close *before* the spell; crash drift −2%/day (≈ −12% per crash).
Test:     manual: `uv run python /tmp/moods.py`-style check — crash spells now fall in 100% of
          69 crashes over 300 markets (median −12%).

## Bug 8 — `learn bear` explained "Beta"
Symptom:  `learn bear` showed the Beta card instead of "Bear market".
Cause:    `difflib.get_close_matches("bear", …)` scores "beta" (3 of 4 letters) above
          "bear market" (a much longer string).
Fix:      exact match first, then a whole-word match inside a term, then difflib.
Test:     test_glossary_lookup_forgives_case_typos_and_partial_words

## Bug 9 — The market story printed its explanations in a different order each run
Symptom:  two runs of the same seed printed the bull/bear explanations in a different order.
Cause:    the moods seen were collected in a `set`; string hashes change every Python run
          (hash randomisation), so set order isn't stable. This breaks N-03 (same seed ⇒ same output).
Fix:      collect them in a list in order of appearance.
Test:     manual: `PYTHONHASHSEED=1` and `=2` give the same `story` text.

## Bug 10 — Every command failed on the tests' hand-made market
Symptom:  `test_badges_are_announced_once` → `UnknownSymbolError: MKT100 is not a tradable symbol`.
Cause:    the "Market Beater" badge (checked after *every* command) asked for MKT100's prices,
          but `tiny_market` only has the FUND ETF. In the game this would hit any custom universe.
Fix:      `Market.index_symbol()` — MKT100 if present, otherwise the first ETF — used by badges,
          views and what-if instead of the hard-coded symbol.
Test:     test_badges_are_announced_once, test_command_badges_come_from_commands_used

## Bug 11 — Web order ticket showed a green maths formula instead of the cost
Symptom:  "Cost ≈ $1,252.20 incl. $1 fee" rendered as `Cost ≈ ** 1,252.20** incl.  1 fee`
          with the middle in green monospace.
Cause:    Streamlit's markdown treats text between two `$` signs as a LaTeX formula.
Fix:      `no_math()` escapes `$` in every dynamic markdown/toast text (coach tips, goals, quiz…).
Test:     test_dollars_are_escaped_for_markdown (the Streamlit UI and its tests were deleted in D-45; kept as evidence)

## Bug 12 — Improving the news silently changed two challenges
Symptom:  after stopping a headline repeating within 40 days, `test_every_challenge_market_still_tells_its_story[bull]`
          and `[sideways]` failed.
Cause:    the news generator draws differently, so prices in those seeds changed and the
          "bull" seed no longer rose 8%.
Fix:      re-picked seeds with a scan script; the story test is exactly what caught it.
Test:     test_every_challenge_market_still_tells_its_story (7 cases)

## Bug 13 — "Bear market" spells that went up
Symptom:  verify transcript: `🐻 Bear market day 4 → 53  MKT100 +9.3%`.
Cause:    the bear drift (−0.14%/day) was small next to the daily noise: only 62% of bear
          spells actually fell (measured over 300 markets).
Fix:      bear −0.30%/day, bull +0.16%/day, and bulls last longer than bears (as in real
          markets) so the long-run return stays ≈ +10%/yr. Now 82% of bear spells fall and 86% of bull spells rise.
Test:     manual calibration run (docs/03 §3.2 table); challenge story tests re-picked seeds.

## Bug 14 — 100 stocks quietly changed every market a test relied on
Symptom:  after D-38, `test_grade_b_for_losing_clearly_less_than_the_market` failed (seed 106 no
          longer a falling market) and so did `…story[tech]` until the new headlines were added.
Cause:    more stocks = more random draws per day (sorted symbols), and more news templates =
          different events, so every seed's prices changed. Only the mood path (own RNG) stayed.
Fix:      re-picked seeds with a scan script (grade test → seed 104, demo seed 180 → 39) and
          retrained the Robo-analyst; the story tests caught exactly the seeds that drifted.
Test:     test_grade_b_for_losing_clearly_less_than_the_market, test_every_challenge_market_still_tells_its_story

## Bug 15 — Clicking "Trade" changed the address but the board stayed on screen
Symptom:  Chrome: URL `#trade`, page still the price board; console clean.
Cause:    `.page-board { display: flex }` beats the browser's `[hidden] { display: none }`, so the
          board section ignored `hidden`.
Fix:      `.page[hidden] { display: none !important; }` in app.css.
Test:     manual (Chrome, every page in turn); JS check of each section's computed display.

## Bug 16 — Reloading the page replayed old toasts and the closing bell
Symptom:  after F5, every toast since the start popped up again and the day-1 closing-bell dialog reopened.
Cause:    the page asked for notices `since=0` on boot and treated them all as new.
Fix:      on boot, remember the newest notice id from the first state and only show newer ones.
Test:     manual reload in Chrome; session side covered by test_new_game_forgets_old_news.

## Bug 17 — The "Skip 20 days" click did nothing
Symptom:  clicked the menu item, the day didn't change; a toast was sitting on top of it.
Cause:    toasts were stacked top-right, over the header's Skip-days menu, and catch clicks.
Fix:      toasts stack bottom-right above the status bar.
Test:     manual (Chrome): menu clickable while toasts are showing.

## Bug 18 — Margin-call sales won the "Day Trader" badge (and the coach praised a 5× account)
Symptom:  Margin Madness report: "🏅 Day Trader" and "✔ Nicely diversified" for a player who never
          traded and was 5× leveraged into a −80% loss.
Cause:    the badge counted any trade with `tick > 0`, including the broker's forced sales; the
          diversification praise only looked at sectors, not at borrowing.
Fix:      the badge ignores trades with a `note`; `coach.diversified` returns None while there is a loan.
Test:     test_margin_madness_punishes_doing_nothing (badges), manual report check.

## Bug 19 — History candles had a third of the volume of live ones
Symptom:  on the All-range chart the day-1 volume bar towered over 120 days of history.
Cause:    pre-history sessions use 26 ticks instead of 78 (for speed) but the dollars per tick were
          the same, so a history day traded ~1/3 as much.
Fix:      dollars per tick = TICK_DOLLAR_VOLUME × 78 / ticks, so a day's volume doesn't depend on tick size.
Test:     manual (Chrome chart); volumes visible in test_bar_is_open_high_low_close_volume.

## Bug 20 — "Cash $-9,933.00" and a lab chart labelled day 0 → 60 for days −60 → 0
Symptom:  agent-mode status line and `levlab` output in verify-out/cli.txt.
Cause:    `money()` put the minus after the $; `line_chart` always labelled the axis from day 0.
Fix:      `money(-x)` → "−$x"; `line_chart(..., first_day=start)`.
Test:     verify-out/cli.txt (tools/verify.py cli, 45 steps).

## Bug 21 — What-if said holding the market beat "your trades" when you were actually ahead
Symptom:  Chrome, Labs → What-if: the "Your trades" curve ended near $10,000 while the account showed
          $10,373; the lesson said "Simply holding MKT100 would have beaten your trades".
Cause:    "Your trades" was a *replay* of the trade log at each day's close in a cash account. A
          margin buy failed (not enough cash) and mid-session trades got the close price instead.
Fix:      `whatif.your_result` uses the game's real equity curve (ticks, borrowing, interest and
          margin calls included); only the preset strategies are replayed.
Test:     test_your_trades_row_is_what_really_happened_with_leverage_and_ticks
