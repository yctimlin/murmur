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

Live screen results will be attached after the invented two-peer text-utilities task ends.
The screening fixture is unrelated to the operator's sealed evaluation tasks.
