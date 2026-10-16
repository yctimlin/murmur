# Round two: implemented mechanisms and evidence

Round two builds **new executable collaboration mechanisms**, rather than treating changed
prompts/defaults as the intervention. The shipped round-one baseline is `658d82a`. All roles
remain claimable by any peer, the root only spawns and waits, and the public command surface
stays `murmur setup` / `murmur run`. Prototypes are isolated, disabled by default, and make no
model/effort/context/compaction choice.

**Current evidence boundary:** all attempted live-peer screens reported the same child-shell
infrastructure error before peers could read their instructions: `app-server socket directory
must be a user-owned directory with mode 0700`. Mechanism owners preserved those attempts and
stopped only their own processes. No sandbox/permission/credential workaround was attempted.
A successful launcher exit in such an attempt is not a successful screen. Scripted real-Git
screens and tests establish the new machinery fires; they establish neither live adoption nor
quality/speed/token improvement. No prototype currently qualifies as a live-screen survivor.

The required next comparison is [eval-plan.md](../eval-plan.md), prepared without access to the
operator's sealed tasks. It requires re-screening in a functioning environment before at most
three candidates enter the controlled comparison. There is no vote-selected winner.

## Observed problem and prior work

The immutable round-one [report](REPORT.md), surveys and [experiment log](evidence/LOG.md) were
read, not recreated. The local evidence is descriptive: every L1/L2 swarm P0 was in a file
written by one peer; one failure crossed a UI/API boundary; all seven observed swarms ended
within 0.5–3 minutes of one another; and two to six commits arrived in the final 20% with little
review of the final state. Prompt-only review missed its preregistered quality/time/token rule.
Shell calls accounted for 77–82% of input in the cited analysis. These findings motivate explicit
state and executable gates but do not prove any proposed mechanism will improve task outcomes.

The existing surveys cover persistent task ledgers, claim locks, integration queues, structured
intermediate artifacts and executable candidate validation. They are design precedents with
different topologies/workloads. We do not borrow their benchmark numbers as murmur results.

## Proposals and ownership

| Mechanism | Owner / branch | Failure targeted | New code behavior | Cost hypothesis |
| --- | --- | --- | --- | --- |
| Final-revision integration duty | a1 / `proto/a1-integration-barrier` | Final merged state lacks a late check | Any peer claims an expiring duty, executes a check on clean accepted main and records revision-bound evidence; a later main update invalidates completion | One claimed late check and bounded status/receipt calls; no extra model thread |
| Independent changed-path review | a2 / `proto/a2-cross-review` | Single-author logic receives no independent inspection | Derive changed-path author obligations from Git, reject self/stale/dirty attestations and gate final completion on another peer's content-bound receipt | Claimed estimate <=15% incremental screen input; unverified |
| Leased work stealing | a4 / `proto/a4-work-stealing` | Unstarted/abandoned units and synchronized finishes | Atomic ready-task claims, dependencies, lease expiry, fencing tokens and a completion barrier on declared work | Roughly add/claim/finish per unit; predicts >=10% lower imbalanced-task time at <=1.2x base input; unverified |
| Frozen executable interface contracts | a5 / `proto/a5-contracts` | Independent changes silently break an agreed interface | Freeze peer-authored probe bytes; run them on incoming main under Git ref locking; reject violating updates before acceptance | Bounded local checks per push; no new inference call, but extra check latency |
| Two-candidate executable alternatives | a6 / `proto/a6-alternatives` | Risky logic has one implementation and correlated review misses it | Two peers submit different candidate commits; frozen argv checks execute in disposable clones and the first passing candidate is promoted with old-head compare-and-swap | Two bounded implementations plus trial calls; may exceed the token budget |
| Frozen interface acknowledgment variant | a3; merged into a5, discarded separate prototype | Interface changes land without another peer noticing | Proposed exact old/new content acknowledgment by a different peer before push | Two or three helper replies per interface change; unverified |

A3 first proposed work stealing independently; that overlapping proposal was merged under a4.
A3 then proposed interface acknowledgment concurrently with a5's earlier contract claim. The
uncommitted duplicate was discarded and its design merged into a5's direction. See
[proposal-a3.md](proposal-a3.md) for the chronology, failed path-validation check and explicit
reason there is no surviving `proto/a3-*` branch. Avoiding duplicate prototypes follows the
specific round-two requirement; the generic draft/vote footer does not override it.

## Prior art and falsifiable predictions

- **Integration duty:** the local late-commit observations and the integration mechanisms in
  [PRODUCTS-INTEGRATION.md](PRODUCTS-INTEGRATION.md) motivate a claimable final check, without
  adopting a fixed integration leader. Prediction: accepted main changes make earlier evidence
  stale, and a successful enabled run has executed evidence for the final delivered revision.
- **Independent review:** [products-other.md](products-other.md) documents Claude Code teams'
  shared state/lifecycle hooks; [survey-a3.md](survey-a3.md) discusses revision/content evidence.
  Prediction: every delivered changed path has another peer's current-content
  attestation, with self/stale/dirty attempts rejected. Attestations do not prove review quality.
- **Work stealing:** Claude Code task claims and Gas Town tracking in
  [products-other.md](products-other.md), compiler task locks in [evaluation.md](evaluation.md),
  and Magentic-One's ledgers in [ORCHESTRATORS.md](ORCHESTRATORS.md). Prediction: simultaneous
  claims yield one owner; expired/released work is claimable by another; old tokens cannot finish.
- **Executable contracts / acknowledgment variant:** MetaGPT intermediate verification already
  surveyed in [survey-a3.md](survey-a3.md), plus Git's native reference-transaction hook. Prediction:
  activate a passing interface probe, reject a violating main update, accept a repair, and resist
  a registration/publication race. This covers only declared executable invariants.
- **Alternatives:** Agentless localization/repair/validation in [evaluation.md](evaluation.md)
  ([original paper](https://arxiv.org/abs/2407.01489)). Prediction: a seeded bad candidate fails,
  the correct candidate passes and lands, and stale main is never overwritten. Two candidate
  authors and executable selection do not imply unbiased independence or sufficient checks.

These are prospective mechanism predictions, not retrospective claims of superior quality.

## Screening and independent review

Screen examples were invented for this run, separately from the sealed evaluation tasks. Live
runs use two peers and a 25-minute cap. The authoritative attempt reports are linked below. Every live attempt was blocked before
activation; recorded exits and token totals describe those failed attempts only.

| Prototype / evidence | Independent a3 full suite | Scripted firing screen | Live-peer screen recorded elapsed |
| --- | --- | --- | --- |
| [a1 integration duty](screens/a1-integration.json) | 64 passed / 15.32s at `cd4aea1` | Mismatch fails, repaired result passes, late commit invalidates receipt; 0.378s base / 0.877s enabled | 188.7s recorded elapsed / 319s UTC span; exit 2; no ready peers/check |
| [a2 changed-path review](screens/a2-review.json) | Initial draft: 62 passed / 13.64s; final 13 review tests / 3.98s | Self/stale receipts rejected, independent receipt accepted; 0.237s base / 0.560s enabled / 0.403s missing-review; missing-review exits 1 | 203.8s enabled / 206.4s base; zero delivered changes or attestations |
| [a4 work stealing](screens/a4-scripted.json) | 63 passed / 12.57s | Two tasks, three claims, handoff to another peer, old owner rejected; 0.668s | [192.1s](screens/a4-live.json); exit 1, unused queue |
| [a5 executable contracts](screens/a5-contracts-scripted.json) | Initial draft: 58 passed / 12.87s; final 10 contract tests / 4.06s | Frozen activation, rejected violation, accepted repair; 0.6238s | [155.5s recorded elapsed](screens/a5-contracts-live.json); UTC timestamps span 285s; no activations or commits |
| [a6 alternatives](screens/a6-alternatives.json) | Initial draft: 60 passed / 12.70s; final 10 alternative tests / 3.10s | Bad candidate fails, good candidate promoted; 0.6435s including setup | No run.json survived interruption; rollout timestamp span 303.979s, no trial |

Every scripted row makes **zero model calls**; its run accounting correctly reports usage
unavailable. Scripted behavior is programmed, so these examples do not demonstrate that live
peers will adopt the helper. A3 independently reproduced the a5 screen in 0.6885s and the a1
screen from archived branches, in addition to running each published draft's full suite. Detailed independent snapshots
and commands are summarized in [a3 review evidence](screens/a3-independent-review.json);
[a6 review notes](review-a6.md) record additional independent findings and fixes.

| Blocked live attempt | Input | Cached input | Uncached input | Output |
| --- | ---: | ---: | ---: | ---: |
| a1 enabled | 652,824 | 586,752 | 66,072 | 1,126 |
| a2 base | 665,139 | 642,560 | 22,579 | 1,266 |
| a2 enabled | 641,571 | 581,248 | 60,323 | 1,267 |
| a4 enabled | 597,695 | 514,688 | 83,007 | 1,065 |
| a5 enabled | 587,855 | 529,152 | 58,703 | 1,082 |
| a6 enabled | 602,795 | 540,800 | 61,995 | 1,043 |

These totals are provider-observed response usage, not complete billing guarantees. There is
no task-outcome comparison to infer from them. Recorded monotonic elapsed, UTC timestamp span
and rollout span are kept distinct; no machine-pause adjustment is guessed.

Independent review found and prompted substantive corrections:

- A2's initial all-history author count let an old second author exempt later sole-author
  rewrites. The prototype now requires a different peer from the **latest effective change author
  for every changed path**, including historical multi-author paths. Ordinary merges preserve
  the underlying content author (`99773f3`). Literal-path handling and a colliding-filename regression now protect
  names containing wildcard syntax (`a19c01c`, 66 full-suite tests reported by owner). Content-bound receipts deliberately survive unrelated commits; they do not certify dependency behavior.
- A6's initial retry wording could never restore final completion after a failed trial.
  An explicit, at-most-once retry now records the prior outcome, retains acceptance settings,
  and resets candidates against current main. Final `bd3e0e2` also preserves run evidence when
  the ledger is missing and cleans up interrupted check process groups; the owner reports
  63 full-suite tests. The original attempt remains evidence.
- A5 fixed the finding that a probe could repair the temporary input before checking it;
  tracked-input immutability and interrupted-probe cleanup now have real-subprocess tests
  (`22ed84c`, 63 full-suite tests reported by owner, 10 focused tests independently passed).

The read-only [screen auditor](../scripts/audit_screen.py) recomputes observed usage from rollout
records, preserves unknown values, fingerprints the source report files and exports mechanism
sections. A caller-declared fixture label is never interpreted as measured zero inference.
Scripted screens explicitly make zero model calls; the agents writing/reviewing these mechanisms
consume separate inference that these fixture counts do not measure.

## Eligibility, conditional shortlist and dropped work

**Zero candidates are eligible for the live performance comparison yet.** All five substantive
code prototypes remain on their branches. Re-screen in a functioning environment first; do not
combine mechanisms before both pass. For that re-screen, the conditional shortlist is:

1. **a2 independent changed-path review:** directly targets every observed L1/L2 swarm P0's
   single-author exposure. The corrected policy also covers multi-author files. Receipt
   quality and peer adherence remain the central uncertainty.
2. **a1 final-revision integration duty:** directly targets the measured absence of checks
   after late commits and requires executed final-head evidence. Check relevance remains
   a peer judgment that the mechanism cannot establish.
3. **a5 frozen executable contracts:** targets the demonstrated UI/API seam before a bad
   update is accepted. Benefit depends on peers declaring useful invariants early enough;
   fresh-tree dependency setup and local check latency are costs to measure.

This ordering is based on expected effect on the measured failures, not votes, diff size, or
screen timings. It is **not a winner selection or claim of efficacy**. A4 work stealing is
retained as a reserve because the log establishes synchronized finish but not a measured
backlog of abandoned runnable units. A6 alternatives is retained as a reserve because it adds
duplicate implementation work and needs a sufficient executable oracle; its causal relevance
and budget cost remain less directly supported. These reserves are not dropped for code size.
A3's duplicate code was discarded and its two proposals merged as described above.

## Enable each prototype

Check out the corresponding branch first. Aggregate `experiment/self-improve-r2` retains
baseline runtime plus the reports/auditor; it does not silently combine unvalidated candidates.
For TOML settings, put the shown one-line entry in the file passed through the **existing**
`murmur setup --config CONFIG` option. Omit it or set false for base from the same build.

| Branch / final pinned revision | Internal enable line | Detailed mechanism / reproduction |
| --- | --- | --- |
| `proto/a1-integration-barrier` @ `b585ab5` | `integration_barrier = true` | [Integration duty](integration-barrier.md) |
| `proto/a2-cross-review` @ `a19c01c` | `independent_review = true` | [Changed-path review](proposals/a2-cross-review.md) |
| `proto/a4-work-stealing` @ `3305f42` | `work_stealing = true` | [Leased work stealing](work-stealing.md) |
| `proto/a5-contracts` @ `22ed84c` | `MURMUR_CONTRACTS=1 murmur setup BRIEF [existing options]` | [Executable contracts](mechanism-a5.md) |
| `proto/a6-alternatives` @ `bd3e0e2` | `MURMUR_ALTERNATIVES=1 murmur setup BRIEF [existing options]` | [Executable alternatives](mechanism-a6.md) |

Environment switches are frozen at setup; omit them or set `0` for the branch's base arm.
No new public flags or model constants are needed. The final operator decision is governed
by [eval-plan.md](../eval-plan.md), not by this conditional ranking.
