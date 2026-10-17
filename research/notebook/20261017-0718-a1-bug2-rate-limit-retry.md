# Bug 2: survive a transient Codex 429

- **Question:** Does a transient HTTP 429 terminate the run, or does murmur retry the Codex child and preserve delivery?
- **Method:** Added fake Codex mode `429-first`, which emits `HTTP 429` once and then commits on the next invocation. `run` now recognizes 429/rate-limit stderr, retries within the run cap using exponential backoff with ±10% jitter, and records the attempt count. Regression: `tests/test_bug2_rate_limit_retry.py`.
- **Prediction:** Baseline exits zero without work after the first transient failure; fixed code makes a second attempt and delivers one commit.
- **Raw-data path:** `/tmp/murmur-review-bug2-base-1792221097` (baseline reproducer); fixed targeted run in this worktree.
- **Result:** Fixed targeted suite passes (`9 passed` including `tests/test_run.py`); clean `eec78f8` baseline with the regression test fails because `run.json` has no retry attempt record. The fixed run records `attempts: 2` and `delivered: true`.
- **Codex source:** `/workspace/codex-src-0.162.1/codex-rs/model-provider-info/src/lib.rs:454-460` configures 200ms base delay, retries 5xx and transport errors, but explicitly sets `retry_429: false`. Generic policy `/workspace/codex-src-0.162.1/codex-rs/codex-client/src/retry.rs:22-52` supports 429 when enabled and uses exponential backoff with random 0.9–1.1 jitter.
- **Decision:** Keep a bounded launcher retry for transient 429s because the Codex provider default does not retry them; preserve the original cap and signal forwarding while retrying.
