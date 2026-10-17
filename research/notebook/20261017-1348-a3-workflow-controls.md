# New workflow task local controls (a3, 2026-10-17)

Question: can the new task's grader distinguish an absent implementation and specific important defects from a contract-following control before task freeze?

Method: `python3 research/tasks/workflow_store/controls/check.py --output research/data/workflow_store-controls`. The script regenerates only the public input in a temporary directory, builds an operator reference package, and scores fresh copies of each. Eight one-defect transformations are defined by explicit string anchors; no model is called. Raw summaries and per-case failure logs are in [workflow_store-controls](../data/workflow_store-controls/summary.json). Independent a1 review reproduced0/129,129/129 and expiry122/129 at4ff4051, plus input isolation in [review](20261017-1345-a1-review-workflow-store.md).

Prediction: absent input0/129, positive129/129, each defect loses at least one case. Result: baseline0, positive129, expiry-strict122, retry-from-observation128, no-attempt-fencing128, weak-type-equality124, reversed-priority127, linear-backoff128, partial-batch-commit113, load-without-state-check120 (all denominators129). All predicted control directions held. This is an authored negative-control check, not runner mutation coverage or empirical task quality.

Public tracked files are exactly `.gitignore`, `README.md`, `SPEC.md`, `examples/batch.json`; hidden tests and reference are absent. The scorer checks behavior only; packaging installation, docs, PR.md and own tests are specified but not scored. Equal case weights include schema and CLI cases as well as concurrency/transaction semantics. The public task may still be too easy; no local control can answer duration/difficulty.

Following a2 review, clarify load failure wording from 'leaves target empty' to 'leaves target unchanged (an initially empty target remains empty)'. This corrects a contradiction for nonempty targets before any freeze/run. It changes no API intention/test; controls rerun and hashes updated. No previously frozen task or C1 prereg changed. The new C2 prereg and notebook carry the stopping/admission decision; this local check does not authorize swarm runs.
