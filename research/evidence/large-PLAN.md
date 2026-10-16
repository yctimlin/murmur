# Large-task integration-quality experiment (fixed 2026-10-14 ~09:40 Taipei, before results)

## Verified causes (from L1/L2/A/B/trials logs; see LOG.md "Why quality drops")
C1 single-author logic: each P0 sat in a file only one peer wrote (L1 compare logic: a1 only;
   L2 static/app.js: a2 only); other peers tested from the spec, not the author's code.
C2 end-together: peers end within 1-3 min of each other; the final main was tested by at most
   one peer (0 in L1); late commits land with no second pair of eyes.
C3 harm-path review under-applied: L2 had one harm-path claim (backend); none on the UI/API seam.

## Arms (gpt-6-astra high, 3 peers, cap 50m)
- base: branch research/large-base (batch-1 prompts + folder input + R1; no E3).
- new: feat/integration-quality = base + M1 independent reviewer per logic part, M2 re-check main
  before ending / no change reaches final main un-run by a non-author, M3 distinct harm-path
  claims with posted reports.
- solo: plain codex exec, repo as subdir.
## Tasks (new, unseen)
- T1 huey @ c5afa05: dead-letter store + operator CLI (existing repo, real suite; base has 1
  pre-existing error; risky: duplicate execution, purge, lost dead tasks).
- T2 plain folder: customer research synthesis + dashboard + reproducible analysis
  (truth T2/truth.json; risky: wrong numbers, invented quotes).
- T3 greenfield git: moneyfold bank-transaction importer/budgeting (risky: duplicates vs genuine
  repeats, undo, interrupted import, exact money).
## Rubric (0-10, blind judges; QA judge separate)
correctness (judge's own checks; T2 vs truth: NPS overall+per plan, theme counts, churn by
category, R017 issue flagged, quotes verbatim) | regressions (full suite vs base) | risk-path
bugs (QA judge, 10-2*P0-P1) | PR.md accuracy | design/usability. Mean of 5.
Hypotheses: H-q new mean >= base mean + 0.5 and fewer P0s; H-t new time <= base time * 1.15 and
uncached <= base * 1.25. Keep M1-M3 if H-q holds and H-t holds.
Also measured: seam metrics (who tested final main, cross-author review count).
