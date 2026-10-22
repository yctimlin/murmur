# AMENDMENT-4 — auxiliary scoring + judge robustness (tooling only, no design change). 2026-10-20 18:43 Asia/Taipei,
# per supervisor directive 2026-10-20 18:06; before any held-out use (evallab does not exist), before the candidate is chosen.
Diagnosis. (1) "cp: cannot stat /srv/murmur-lab-hidden/<task>": T1b/T2/T3b/T4b are OPEN tasks with no hidden tests by
design (RUBRIC.md: "Hidden tests: none (open tasks)"; r3's evallab showed the same error on every open run). The dirs in
/srv/murmur-lab-hidden belong to r2/self3 closed-class tasks. tools/runner.py (copied from runner2.py) set _scorer
unconditionally. Fix: scoring only if the task dir has score.sh; otherwise result.json gets score_na. No hidden scoring
exists or is added for the dev or held-out tasks; the sealed held-out dir was not touched. (2) mutation IndexError: the
runner called LAB/bin/mutation.py, which does not exist in the r4 lab -> empty stdout -> IndexError. Fix: the r3 sealed
scorer is now tools/mutation.py (byte-identical copy of /workspace/self3/evallab/bin/mutation.py, sha256 4797fc2f...),
called relative to runner.py, and empty output raises an explicit error. tools/backfill_mutation.py (sha256 20eab66e...)
backfills the mutation score of finished runs (nice 19, sequential). Mutation stays a SECONDARY sanity metric only
(RUBRIC.md); it enters no decision rule. (3) Judge: an empty claude stdout raised IndexError; now an explicit
"no verdict JSON" error with exit code/stderr logged, a fresh anonymized copy per attempt, backoff 120 s x attempt
(600 s on usage limits). Judge prompt, rubric, scoring, number of judgments unchanged.
New sha256: tools/runner.py 41ab4069a65bd0ea...; tools/r4eval.py d48f661a837e0acd... (FINAL.md froze 15c75549; this
amendment supersedes that hash, judge prompt/aggregation code unchanged).
