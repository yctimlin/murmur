# Run usage accounting: source verification and limits

Inspected installed Codex 0.162.1 checkout at commit
`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` on 2026-10-16. Links below identify that
source revision; public availability of this commit was not verified.

- `TokenUsageRecord` has response/thread IDs, per-response `usage`, and cumulative
  turn/thread counters. Summing per-response `usage` avoids summing cumulative counters.
  [Protocol definition](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/protocol/src/protocol.rs#L2293).
- `record_observed_response_completed` only persists a usage record when the provider
  returns usage. These are observations, not a guarantee of all attempted requests or
  billing completeness. [Persistence](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/session/mod.rs#L4717).
- The rollout persistence policy retains these records in both history modes.
  [Policy](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/rollout/src/policy.rs#L40).
- `codex exec --json` emits its last observed thread total at `turn.completed`, so that
  stream is not an independently verified complete swarm total. The implementation reads
  isolated-home rollouts instead. [JSONL adapter](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/exec/src/event_processor_with_jsonl_output.rs#L118).
- Codex's source tests exercise three usage-bearing responses plus one without usage:
  only three durable records result. [Source test](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/tests/suite/token_usage_rollout.rs#L33).

Murmur design: stream only this run's `sessions` and `archived_sessions`, deduplicate
`(thread_id, response_id)`, sum input/cached input/output, and derive uncached input as
input minus cached input. Report observed responses, per-thread usage, malformed-record
counts, and threads with no usage. Never replace unknown usage with zero. Reasoning output
is reported as a subset, not added again. No price/model table or active-time heuristic is
introduced. See [implementation](../src/murmur/usage.py) and [tests](../tests/test_usage.py).

Validation: draft `tests/test_usage.py` and `tests/test_run.py` passed (13 tests, 4.01s);
full draft suite passed (37 tests, 9.76s). The six-state fake capture took ~3s, uses no
credentials, and spends zero model tokens. This verifies parsing/lifecycle integration,
not live provider coverage, token savings, or agent output quality. No live model
experiment was run for this draft. The report deliberately calls the figures “observed”
even when all parsed records are valid: missing provider usage is not inferable.
