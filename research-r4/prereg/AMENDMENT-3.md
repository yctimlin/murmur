# AMENDMENT-3 — tooling fix in tools/final_eval.py (no design change). 2026-10-20 14:46 Asia/Taipei,
# before any held-out use (no task copied, evallab does not exist), before the candidate is chosen.
The "dev runner stopped" precondition ran `pgrep -f 'runner.py r4-lab-runner'` through a shell whose own command line
contains the pattern, so it always matched and `start` could never run. Now an anchored pgrep without a shell.
Also: tools/runner.py gained restart-safe concurrency (in-flight children of an earlier parent count toward PAR);
it applies to both labs and does not affect arms, tasks, metrics or the decision rule.
final_eval.py sha256 now 2df5208d08f339a9...; runner.py bf8f7872287da7fb...
