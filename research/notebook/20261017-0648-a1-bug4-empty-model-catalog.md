# Bug 4: reject an empty Codex model catalog

- **Question:** Does `murmur setup` avoid creating a broken `models.json` when `codex debug models` returns no models?
- **Method:** Stub `codex debug models` to return `{"models": []}` and call `write_model_catalog` in `tests/test_bug4_empty_model_catalog.py`.
- **Prediction:** Before the fix, setup exits later or writes an empty catalog; after the fix, it exits with a clear launcher error and leaves no destination file.
- **Raw-data path:** `tests/test_bug4_empty_model_catalog.py` (deterministic reproducer; no lab run needed).
- **Result:** `write_model_catalog` now validates the catalog before mutating the destination and reports `codex debug models returned an empty model catalog; refusing to write models.json`.
- **Decision:** Keep the guard as the setup boundary check; an empty model catalog cannot produce a runnable workspace.
