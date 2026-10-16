# Work stealing with expiring, fenced task claims (a4)

## Proposal

The supplied [experiment log](evidence/LOG.md) reports peers ending within 0.5–3 minutes,
without late integration coverage. A board message that claims work has no atomic ownership,
recovery deadline, or reliable completion count. This prototype adds those properties to a
shared queue. It does not discover missing work or independently validate completed work.

Any peer can publish bounded task descriptions, declare dependencies on existing tasks,
claim a ready task, renew a claim, release it with a handoff, or finish it with evidence.
SQLite transactions grant one task to one peer at a time. Claims expire after 15 minutes;
a new owner gets a new random fencing token, so an old owner cannot finish or renew the
reclaimed task. Dependencies must already exist, preventing cycles by construction.
Recovery requires inspecting earlier work: fencing protects ledger updates, not Git writes.
The queue does not lock files or appoint a leader. The root prompt remains unchanged.

Prior art: [the round-one product survey](products-other.md) records Claude Code teams'
shared task lists and lock-protected claims, and Gas Town's persistent work tracking.
[The evaluation survey](evaluation.md) records task locks in Anthropic's compiler experiment.
[The orchestrator survey](ORCHESTRATORS.md) describes Magentic-One's task/progress ledgers;
its centralized scheduler differs from the leaderless queue here. These prior mechanisms
motivate explicit state; none proves this prototype improves murmur's quality or cost.

## Interface and prediction

Enable with `work_stealing = true` in an existing `murmur setup --config CONFIG` TOML file.
Default is false. No additional user CLI command or flag is introduced; solo rejects the
setting because stealing requires multiple peers. Setup copies a standalone helper into
`work/.murmur/work_queue.py`, with a sibling SQLite ledger. Generated peer instructions
contain the exact command. Every peer uses the same operations:

- `add ID TITLE DETAIL [--after ID]`: bounded task publication, with idempotent same-author retry.
- `next`: acquire the oldest ready task, or return readiness/running/dependency counts.
- `renew ID TOKEN`: extend a current claim.
- `release ID TOKEN HANDOFF`: make unfinished work immediately available.
- `finish ID TOKEN RESULT`: record completion of a current claim.
- `status [--offset N]`: summaries in pages of 20, without other peers' fencing tokens.

The run's `logs/run.json.work_queue` contains final queue state and event counts. Enabled
runs cannot exit successfully with an empty, unfinished, missing or unreadable queue.
Cap/interruption/provider failure retain their existing exit precedence. This is a declared-work
barrier, not a correctness verdict. Agents can still omit necessary work when decomposing.

Cost hypothesis: add/claim/finish costs roughly three shell calls per work unit; no background
model calls or extra peers. Descriptions are capped at 1,800 characters and result/handoff
notes at 1,000; status is paginated. Repeated polls and overly fine units can increase cost.
On held-out imbalanced tasks, predict at least 10% lower active wall time, with total input
at most 1.2 times baseline, fewer stranded ready units, and no quality regression. This is a
falsifiable hypothesis; no such benefit is established by unit tests or a mechanics screen.

## Verification

Initial full suite: **63 passed in 12.19 seconds**, using fake Codex and real SQLite/Git.
New cases exercise simultaneous claims, idempotent retry, lease expiry and stale-owner
fencing, dependencies, release/handoff, bounded status, standalone helper invocation,
unused/unfinished/missing queue rejection, and unchanged disabled behavior. Test-model
calls/tokens: zero; development-agent inference is separate and unmeasured here.

## Screens and disposition

The live screen used two peers and a 25-minute cap to implement an invented lowercase word
counter and a dependent summary utility. Both children were blocked before reading their
prompts by the host error `app-server socket directory must be a user-owned directory with
mode 0700`. The queue remained unused; the enabled completion barrier returned exit 1 despite
Codex returning 0. No environment-limit workaround was attempted. The run took **192.1 seconds**
and observed **597,695 input**, **514,688 cached input**, **83,007 uncached input** and
**1,065 output** tokens (**598,760 total**). These are wasted/blocked-run observations,
not mechanism overhead or a baseline comparison. [Live evidence](screens/a4-live.json).

A separate scripted screen uses fake Codex with real helper subprocesses, SQLite and Git.
It creates a payload task and a dependent byte-manifest task, releases the first peer's claim,
lets the second peer steal it, rejects a stale completion, integrates the payload, unlocks
the dependent task and validates the integrated byte count. Both units finish; the runner
exits 0. Observed time including setup/operations: **0.668 seconds**, three claims, one
release, two completions. Model calls/tokens: **zero**; fake rollouts correctly report usage
unavailable. [Scripted evidence](screens/a4-scripted.json).

Reproduce from `proto/a4-work-stealing`: `python scripts/screen_work_queue.py .work/new-screen`
(the output path must not already exist), or `python -m pytest -q tests/test_work_queue.py`.
These fixtures are unrelated to the operator's sealed evaluation tasks. The live attempt
cannot establish agent adoption. The scripted attempt proves the mechanism fires and
survives the invented handoff; it cannot substitute for held-out model evaluation.

Recommendation: retain the prototype branch but defer it from the three operator candidate
slots if integration-barrier, independent-review and interface-contract prototypes pass their
mechanics screens. Those target the observed single-author and seam failures more directly.
Synchronized finishing alone is not evidence of idle-peer imbalance or abandoned task claims.
No performance winner is selected by voting.
