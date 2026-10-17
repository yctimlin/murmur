# Independent task review: workflow_store — a1 — 2026-10-17 13:45 UTC

## Question, method, and prediction

Review a3's new unfrozen task at 4ff4051 for a coherent public contract, observable hidden oracles, genuine process/durability checks, grading isolation, and non-leaking starter construction. This is task validation, not a real murmur run, a calibration observation, or a mechanism experiment. Predicted control outcomes: empty input zero, reference full score, strict-less-than lease-expiry mutant below full score.

Read the full SPEC, brief, TASK metadata, make_input/score scripts, all hidden cases, and reference/CLI source. Created a temporary copy of the task and ran its `make_input.sh`. Built two separate temporary deliverables by copying `controls/reference.py` to `workflow_store/__init__.py` and `reference_cli.py` to `workflow_store/__main__.py`; one used the source unchanged, and one replaced `t['expires']<=self.clock` with `t['expires']<self.clock`. Invoked the real task `score.sh <temporary-deliverable>` on each and on the empty starter. All temporary directories were cleaned; no frozen task or external evidence was changed.

## Raw/derived evidence and result

`research/data/workflow-store-a1-review.json` records exact scores, execution statuses, diagnostics, elapsed time, and the public manifest:

- Empty starter: **0/129**. This is absence of implementation, not an empirical coding-agent calibration.
- Positive control: **129/129**, 1.371 seconds including scorer process overhead on this machine.
- Expiry-boundary negative control: **122/129**, five assertion failures and two errors. The seven detected failures include renewal at exact expiry, expired-state propagation, and stale completion.
- Public input contains exactly `.gitignore`, `README.md`, `SPEC.md`, and `examples/batch.json` outside Git internals. No reference, controls, or hidden grader files are copied. Public SPEC is byte-identical to reviewed SPEC.

The suite checks observable results, schema errors and rollback, duplicate-command typing, dependency/retry/expiry interactions, durable reopen, cross-process competing claims, batch rollback after iterator failure, tampered replay, long chains, large integers, and CLI behavior. Oracles do not import the reference implementation. Package layout support covers flat and src paths. The grader copies the deliverable before executing and emits a final JSON rate. Positive score plus a detected boundary defect is evidence that these checks execute; it does not prove complete contract coverage.

## Limits and decision

The hidden score does not independently check pip-installability, documentation quality, or usefulness of the deliverable's own automated tests, although the public brief requests them. These remain outside the hidden-rate measurement; mutation and artifact inspection are separate. Current tests and reference are not an empirical difficulty or time study. Reference code is compact enough that saturation remains plausible despite more interacting requirements; therefore no swarm use is justified before a valid exec calibration meets the operator gate.

Accept this task's public contract/scoring construction for exec-only calibration, subject to final frozen-file review if the author changes it before C2 registration. No oracle/spec mismatch was found in reviewed cases. A2 separately reviews C2 admission, budget, and decision rules. No murmur implementation is changed.
