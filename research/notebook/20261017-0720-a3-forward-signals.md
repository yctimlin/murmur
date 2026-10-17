# Follow-up: preserve the interruption signal

- Question: Does an external SIGINT reach the Codex child as SIGINT rather than being converted to a generic termination?
- Method: Preserve the signal number in the launcher interrupt handler, pass it to `stop_process_group`, and exercise both the existing SIGTERM interruption test and the SIGINT regression. Targeted run/process tests passed (`12 passed`).
- Result: Commit `aff72ad` forwards SIGINT to the Codex process group while retaining SIGTERM behavior and cleanup grace periods.
- Decision: Keep the original signal type through cleanup so callers and child processes observe the interruption they sent.
