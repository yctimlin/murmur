# Bug 4: reject an empty Codex model catalog

- Question: What should `murmur setup` do when `codex debug models` succeeds but returns no models?
- Method: Stub `codex debug models` to return `{\"models\": []}` and call `write_model_catalog` directly. Verify setup exits nonzero with a clear diagnostic and does not create `models.json`.
- Prediction: The existing code would write an unusable empty catalog; the fix should fail before writing it.
- Raw-data path: `tests/test_bug4_empty_models.py`
- Result: Before the fix, iterating the empty list completed successfully and wrote a broken catalog. Commit `f1ec600` validates that `models` is a non-empty list, reports `codex model catalog is empty`, and leaves the destination absent. Regression tests pass (`4 passed`).
- Decision: Keep the setup failure early and explicit so later setup steps cannot run with a broken model catalog.
