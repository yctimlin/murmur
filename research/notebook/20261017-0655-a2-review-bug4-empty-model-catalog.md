# Review: bug 4 empty model catalog fix

- Question: Does the bug 4 implementation on `origin/main` prevent setup from publishing an empty or malformed model catalog while preserving existing catalog behavior?
- Reviewer/method: a2 reviewed commits `f1ec600`, `3c74365`, and `6d18cee`. The guard in `src/murmur/cli.py` checks that the decoded response is a mapping with a non-empty list at `models` before modifying or writing the destination. The regression test stubs `codex debug models`, asserts a non-zero launcher exit, checks the diagnostic, and verifies no `models.json` is created. Existing `tests/test_catalog.py` covers swarm pinning and solo behavior.
- Prediction: The regression test fails on protected baseline `eec78f8` because it writes the empty catalog, and passes on `origin/main`; the existing catalog tests remain green.
- Raw-data path: `tests/test_bug4_empty_model_catalog.py`, `tests/test_catalog.py`; implementation `src/murmur/cli.py`.
- Result: `.venv/bin/python -m pytest -q tests/test_bug4_empty_model_catalog.py tests/test_catalog.py` passed (4 tests). The guard runs before `path.write_text`, and `setup` removes its unpublished workspace in the existing `finally` path after `SystemExit`, so no broken catalog is left behind.
- Decision: Approve the bug 4 fix for the phase base. No changes requested.
