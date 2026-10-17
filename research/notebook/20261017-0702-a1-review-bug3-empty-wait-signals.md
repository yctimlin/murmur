# Independent review: bug 3 empty waits and SIGINT

- **Reviewer:** a1
- **Change reviewed:** commit `2464fab` (`src/murmur/prompts/root.md`, `src/murmur/procutil.py`, `tests/test_bug3_empty_wait_signals.py`)
- **Method:** Ran the targeted regression and existing run tests on the fixed commit (`10 passed`). Copied the regression test into a clean `eec78f8` worktree and reran it; the baseline failed at `receiver_thread_ids=[]` assertion while the remaining nine tests passed.
- **Evidence:** `/tmp/murmur-review-bug3-1792220321` (fixed) and `/tmp/murmur-review-bug3-base-1792220349` (baseline); command `.venv/bin/python -m pytest -q tests/test_bug3_empty_wait_signals.py tests/test_run.py`.
- **Decision:** Reviewed and accepted. The prompt assertion is a runnable reproducer that distinguishes the baseline; the fixed root instruction handles an empty wait result and terminates after `list_agents` finds no peers. The SIGINT path also passed the targeted child cleanup test.
