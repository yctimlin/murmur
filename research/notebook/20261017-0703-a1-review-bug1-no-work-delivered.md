# Independent review: bug 1 no work delivered

- **Reviewer:** a1
- **Change reviewed:** commit `0a59222` (`src/murmur/cli.py`, `src/murmur/prompts/peer.md`, `tests/test_bug1_no_work_delivered.py`)
- **Method:** Ran the targeted regression and existing run tests on the fixed commit (`9 passed`). Copied `test_bug1_no_work_delivered.py` into a clean `eec78f8` worktree and reran it; the baseline returned zero from a successful no-commit run, failing the expected launcher error.
- **Evidence:** `/tmp/murmur-review-bug1-1792220454` (fixed) and `/tmp/murmur-review-bug1-base-1792220484` (baseline); command `.venv/bin/python -m pytest -q tests/test_bug1_no_work_delivered.py tests/test_run.py`.
- **Decision:** Reviewed and accepted. `run` compares `main` against the recorded base, logs `commits`, `delivered`, and `diagnostic`, and exits nonzero with `no work delivered`; the peer prompt requires the winning draft to be integrated and acknowledged before ranking can finish.
