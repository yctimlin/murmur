# Operator-only grading notes

50 equally weighted unittest methods cover exact money, account/event validity, transfer rules, event deduplication, sequence ordering, detached state, atomic iterable batches, canonical snapshot restoration, and CLI replay/output behavior. A method containing multiple invalid examples counts as one graded case; failed unittest subtests are deduplicated by parent test ID. No score depends on a particular module implementation.

The untouched float-based package scores 12/50 = 0.24. This establishes a baseline below the gate's 0.30 ceiling, not a measured solo-agent result. Expected solo time (40 minutes) and target score (60–85%) are uncalibrated design estimates. No model or murmur runs tuned the task.

The scorer copies the delivered tree to a fresh temporary directory before importing or executing candidate code. It locates hidden cases relative to score.sh, uses the standard library only, disables bytecode writes, and does not modify the original delivery. CLI calls have a 10-second timeout; the whole worker has a 180-second timeout and clean zero-score fallback. Ordinary case failures preserve partial credit. Successful output replacement is checked by changed file inode on the Linux scoring box; failed output preservation is checked byte-for-byte. Diagnostics go to stderr and the final stdout line is the score JSON.

Independent review: research/notebook/20261017-0743-a3-review-ledger-replay.md plus its atomic-output followup. Pre-freeze setup/determinism/scoring controls: research/tools/check_screening_tasks.py.
