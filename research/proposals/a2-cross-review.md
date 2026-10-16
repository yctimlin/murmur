# a2: independent review receipts

## Mechanism and prediction

Round-one `research/evidence/LOG.md` (C1, lines 83–91) reports every L1/L2 swarm P0
in a file written by one peer. `large-RESULTS.md` rejects prompt-only independent
review under its aggregate keep rule. This prototype makes the missing review
observable and mechanically prevents an enabled run from reporting exit 0 when
sole-author delivered paths have no independent receipt.

Any peer runs `.murmur/review status`, reviews another peer's accepted changes in
a clean checkout, and runs `.murmur/review attest --revision FULL_SHA --note 'what
was checked' -- PATH...`. A shared SQLite ledger records attributed receipts.
The helper rejects self-review, a stale checkout, a dirty tracked checkout, unknown
peers, and empty notes. The receipt binds baseline, path, content/object type/mode,
and writer identity. Editing that content invalidates it; unrelated changes keep
it valid. Deletions require review too. The final launcher checks accepted main
again and changes an otherwise successful exit into 1 if coverage is incomplete.
No leader, additional model thread, public command, model setting, or language
assumption is introduced. The root still only spawns and waits.

Prior art is already surveyed: Claude Code teams' task/lifecycle hooks and shared
claims (`research/products-other.md`, https://code.claude.com/docs/en/agent-teams),
and revision-bound evidence (`research/survey-a3.md`). These are structural
analogies, not performance evidence for this implementation.

Preregistered mechanical prediction: every successful enabled run has independent
receipts for 100% of its sole-author changed paths; injected self/stale receipts
are rejected. Cost hypothesis: one status call and a bounded independent review
per peer adds no more than 15% observed input tokens on the small paired screen.
That exploratory hypothesis is not a quality or general token-budget claim.
Operator-held-out evaluation must decide whether fewer P0s justify the cost.

## Enable and inspect

Put `independent_review = true` in the existing TOML supplied through
`murmur setup --config CONFIG`; omit it or set false for base in the same build.
At least two peers are required. The helper and ledger live under workspace
`work/.murmur-review`; peers get `.murmur/review`. `logs/run.json` includes the
final `independent_review` coverage. SQL tables `receipts` and `events` preserve
review notes and exact inspected revisions.

## Limits and decisions

This is an accidental-omission guard, not a security boundary: peers can edit
shared workspace state, impersonate Git authors, or claim reviews they did not
perform. The signature proves attributed acknowledgment, not correct reasoning.
The gate counts commit-author emails touching each changed path since baseline;
it is not a line-level blame or semantic independence proof. Multi-author paths
are reported and currently do not require another receipt. Merge commits count
as authors of differences to each parent. Ignored/untracked runtime dependencies
are not bound into a code-review receipt, and this is not a check-result cache.
A missing receipt fails a completed run; it does not automatically restart peers.
The peer prompt asks peers to wake a reviewer before finishing.

This round's specific no-vote/proto-branch instructions override its generic
footer's draft vote. `origin/main` here is the isolated shared transport; the
operator-facing destination remains `experiment/self-improve-r2`, not the real
repository's main branch. No external repository main is pushed.

## Verification

Initial full suite: **62 passed in 13.51 seconds**, including nine new real-Git
review tests. All tests are credential-free and make zero model calls. They cover
self/stale/dirty rejection, successful independent receipt, final exit enforcement,
content invalidation, unrelated commits, deletion/mode changes, multi-author
scope, helper invocation with spaces, default-off/solo validation, and a corrupt
ledger failing closed. Live paired small-task screen results are recorded below
when complete; screen evidence does not substitute for sealed operator evaluation.
