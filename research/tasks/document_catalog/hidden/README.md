# Operator-only grading notes

48 equally weighted unittest methods cover discovery and decoding, schema validity, normalized revision winners, link resolution, weighted token search, ordering, CLI behavior, and the supplied archive. Multiple subchecks inside one method still count as one graded case. In particular, count unique failing parent test IDs rather than subtracting each failed subtest from testsRun.

The untouched scaffold scores 1/48: its CLI happens to satisfy the fatal-error behavior. This is a baseline interface check, not a measured solo-agent difficulty estimate. Expected solo time (35 minutes) and target pass rate (60–85%) are uncalibrated design estimates. No model or murmur runs tuned the task.

The scorer copies the delivered tree into a fresh temporary directory, skips git/virtualenv/bytecode artifacts, and runs all cases in a subprocess using only Python's standard library. It sets PYTHONPATH to that copy and disables bytecode writes. Individual CLI calls time out after 10 seconds; the complete worker times out after 180 seconds, returning a clean zero-score JSON if it cannot finish. Normal case failures preserve partial credit. The original tree is never used as an execution directory and is never modified. Diagnostics go to stderr; the last stdout line is the grading JSON.

Independent review: research/notebook/20261017-0743-a3-review-document-catalog.md. Setup, relocated scoring and full input hash preservation can be rechecked before freeze with research/tools/check_screening_tasks.py.
