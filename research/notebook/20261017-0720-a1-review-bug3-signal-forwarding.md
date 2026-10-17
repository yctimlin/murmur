# Independent review: preserve interruption signals

- **Reviewer:** a1
- **Change reviewed:** `aff72ad` / `12521f0`, which extends bug 3's empty-wait fix.
- **Method:** Pulled the integrated origin branch and ran `tests/test_bug3_empty_wait_signals.py tests/test_run.py` (`10 passed`). Inspected the signal path: `procutil._interrupt` now raises `KeyboardInterrupt(signum)`, `run` captures SIGINT/SIGTERM/SIGHUP, and `stop_process_group` sends that exact signal to the Codex process group before escalation.
- **Result:** The launcher preserves the initiating signal instead of always converting it to SIGTERM, while existing child cleanup tests remain green.
- **Decision:** Reviewed and accepted the follow-up signal-forwarding fix.
