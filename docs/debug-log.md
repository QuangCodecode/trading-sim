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
