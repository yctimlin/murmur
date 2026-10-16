# a2: independent review receipts

## Mechanism and prediction

Round-one `research/evidence/LOG.md` (C1, lines 83–91) reports every L1/L2 swarm P0
in a file written by one peer. `large-RESULTS.md` rejects prompt-only independent
review under its aggregate keep rule. This prototype makes the missing review
observable and mechanically prevents an enabled run from reporting exit 0 when
delivered changed paths have no independent receipt.

Any peer runs `.murmur/review status`, reviews another peer's accepted changes in
a clean checkout, and runs `.murmur/review attest --revision FULL_SHA --note 'what
was checked' -- PATH...`. A shared SQLite ledger records attributed receipts.
The helper rejects self-review, a stale checkout, a dirty tracked checkout, unknown
peers, and empty notes. The receipt binds baseline, path, content/object type/mode,
and latest change author identity. Editing that content invalidates it; unrelated changes keep
it valid. Deletions require review too. The final launcher checks accepted main
again and changes an otherwise successful exit into 1 if coverage is incomplete.
No leader, additional model thread, public command, model setting, or language
assumption is introduced. The root still only spawns and waits.

Prior art is already surveyed: Claude Code teams' task/lifecycle hooks and shared
claims (`research/products-other.md`, https://code.claude.com/docs/en/agent-teams),
and revision-bound evidence (`research/survey-a3.md`). These are structural
analogies, not performance evidence for this implementation.

Preregistered mechanical prediction: every successful enabled run has independent
receipts for 100% of its changed paths; injected self/stale receipts
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
The gate assigns each changed path to its latest change author since baseline,
using Git path-history simplification; it is not line-level blame or proof of semantic
independence. A reviewer may have contributed earlier code but cannot sign their
own latest change. Multi-author paths are reported and also require review; a
second historical writer cannot waive review of a later rewrite. Ordinary merges follow a parent
with identical path content; importing another peer's work does not become new
authorship. Merge resolutions that change every parent count as authored changes.
The diagnostic historical-author list conservatively includes merge touchers. This stronger policy replaced an
initial historical-single-author exemption after a3 identified its rewrite gap. Ignored/untracked runtime dependencies
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
ledger failing closed. Live paired small-task screen results are recorded below; screen evidence does not substitute for sealed operator evaluation.

## Screen results (October 16, 2026)

The tiny invented task implements a greeting utility with whitespace and blank
input handling. No evaluation task was read or guessed. Two live attempts used
two peers, unchanged model/effort configuration, and a 25-minute cap each. Both
were blocked before implementation: child shells reported `error building
bubblewrap command: app-server socket directory must be a user-owned directory
with mode 0700`. Both returned process exit 0 with **zero commits and zero changed
paths**. That vacuous gate pass is not task success. No sandbox setting or shared
infrastructure was modified to bypass the failure.

| Live arm | Wall seconds | Input | Cached input | Uncached input | Output |
|---|---:|---:|---:|---:|---:|
| Base | 206.4 | 665,139 | 642,560 | 22,579 | 1,266 |
| Review enabled | 203.8 | 641,571 | 581,248 | 60,323 | 1,267 |

These observed records describe blocked attempts; their ratio is not a meaningful
cost test. Live screen/quality/token-overhead hypotheses remain **unverified**.
The prototype is mechanically screened and provisionally available for operator
screening; it is **not a live-screen survivor or an evaluation winner**.

The reproducible credential-free screen uses scripted peers, real Git, the actual
helper, and the actual launcher. It deliberately detects a blank-input bug, lands
a repair, rejects self-review and stale-review attempts, and signs corrected
content from the other peer. A separate missing-review arm verifies final exit 1.
Run `.venv/bin/python scripts/screen_review.py /tmp/NEW_DIRECTORY`.

| Scripted arm | Wall seconds | Exit | Inference tokens |
|---|---:|---:|---:|
| Base | 0.237 | 0 | 0 |
| Review enabled | 0.560 | 0 | 0 |
| Missing review | 0.403 | 1 | 0 |

Durable summaries and mechanism events are in
[`../screens/a2-review.json`](../screens/a2-review.json). Each generated workspace
also retains `logs/run.json`, `logs/screen-events.json`, and the SQLite receipts.
The zero-token count applies only to scripted inference; development-agent tokens
are unavailable and not included. A3's independent review found the historical
multi-author waiver; the final policy and regression test close it.

Final review hardening adds regressions for missing ledgers, malformed config, and
ordinary merges. Runtime ledger opens never recreate lost state. A6 identified
merge-attribution risk; Git path-history simplification preserves the imported
content's actual author, and a normal no-conflict merge regression rejects that
author's self-review. Final full suite: **65 passed in 14.24 seconds**, including 12 review-specific tests.
