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
