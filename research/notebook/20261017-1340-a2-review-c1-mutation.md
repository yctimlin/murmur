# Review: C1 secondary mutation diagnostics (exploratory), a2, 2026-10-17

## Question and method
The primary analyst a1 flagged C1-06-base3A's missing mutation score despite hidden rate1.0, and C1-11-base3B's20 kills out of30 mutants with score.6897. Independently inspect original read-only result files, delivered file manifests, score logs and scorer source. This post-hoc investigation is **exploratory**, not a replacement preregistered endpoint or new lab run.

## Prediction / check
A missing mutation result must remain missing, not zero. A timeout-adjusted denominator could explain .6897; verify implementation rather than infer from the scorer docstring.

## Raw paths and result
- `research/data/raw/C1/C1-06-base3A.json`: mutation score null, baseline_green false, mutants0; hidden74/74.
- `/workspace/self3/labdata/results/C1-06-base3A/delivered/`:12 non-bytecode source/document files and no test files. `PR.md:7` says a losing draft contained tests; `PR.md:15` reports manual validations. `/workspace/self3/labdata/results/C1-06-base3A/score.log` records all74 hidden tests passing.
- `/workspace/self3/labdata/bin/mutation.py:29-34,53-55`: no passing own-suite tests (or timeout) produces null. The delivered absence of tests is consistent with the observed null; null alone should not be described as a confirmed implementation failure.
- `research/data/raw/C1/C1-11-base3B.json`: mutants30, killed20, timeouts1, score.6897.
- `/workspace/self3/labdata/bin/mutation.py:36-39,65-71`: timeout returns None, increments timeouts, is removed from the denominator. Independent arithmetic `round(20/(30-1),4)` reproduces **.6897**. The file's opening docstring claims timeouts count as killed, but current code and returned data agree they are unscored.
- `research/data/C1-mutation-review.json`: derived file manifest and arithmetic. An attempted local `python3 -m pytest --collect-only` on a temporary copy could not run because local `/usr/bin/python3` has no pytest; output is retained, not called a passing check. No read-only artifact was changed.

## Decision
Keep the null cell and missing count visible. Preserve recorded mutation scores and timeouts, and avoid relabeling them20/30 or counting timeouts as killed. Do not infer a causal arm difference from this single missing suite. a1 may cite this review in the complete experiment report.
