# Bug 3: empty peer waits and launcher signals

- Question: Does the swarm root stop promptly when `wait_agent` returns an empty `receiver_thread_ids=[]`, and does interruption reach the Codex child?
- Method: Make the generated root prompt explicitly treat an empty receiver list as a wait return and immediately call `list_agents`, finishing when no peer remains. Add SIGINT handling alongside SIGTERM/SIGHUP in the launcher process handler. Exercise a hanging fake Codex and send SIGINT to the launcher process group; render the root prompt and check the empty-result instruction.
- Prediction: An empty wait result can cause another indefinite wait, and SIGINT currently bypasses the launcher handler, leaving the child running until the cap.
- Raw-data path: `tests/test_bug3_empty_wait_signals.py`; targeted suite `tests/test_bug3_empty_wait_signals.py tests/test_run.py`.
- Result: Commit `2464fab` adds the explicit empty-result prompt branch and registers SIGINT. The regression and existing run tests pass (`10 passed`); a SIGINT to the launcher returns exit 130 promptly while the fake Codex is stopped.
- Decision: Preserve the one-wait/list-agents protocol while making the empty-result termination condition explicit and ensuring SIGINT follows the same child cleanup path as SIGTERM.
