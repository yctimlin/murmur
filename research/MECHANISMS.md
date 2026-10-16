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
| Independent sole-author review | a2 / `proto/a2-cross-review` | Single-author logic receives no independent inspection | Derive changed-path author obligations from Git, reject self/stale/dirty attestations and gate final completion on another peer's content-bound receipt | Claimed estimate <=15% incremental screen input; unverified |
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
  Prediction: every eligible delivered sole-author path has another peer's current-content
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
runs use two peers and a 25-minute cap. The authoritative attempt reports and per-owner notes
are being collected below; pending entries are not passing results.

| Prototype | Full suite at initial published revision | Scripted firing screen | Live-peer screen |
| --- | --- | --- | --- |
| a1 integration duty | Owner: 63 passed / 14.88s | Pending report | Infrastructure-blocked; report pending |
| a2 independent review | Independent a3 archive: 62 passed / 13.64s | Pending report | Infrastructure-blocked; report pending |
| a4 work stealing | Owner: 63 passed / 12.19s | Pending report | Infrastructure-blocked; report pending |
| a5 executable contracts | Owner: 58 passed / 13.52s | Frozen activation, rejected violation, accepted repair; 0.6277s, zero model calls | Blocked before prompt read; 155.5s, 587,855 input / 529,152 cached / 58,703 uncached / 1,082 output; no activations or commits |
| a6 alternatives | Owner: 60 passed / 13.40s | Pending report | Infrastructure-blocked; report pending |

A3 independently inspected published code and identified two meaningful limits: historical
path-touch authors can exempt subsequently rewritten sole-author logic in a2, and a stale trial
in a6 cannot currently be erased by a later successful retry despite suggested retry wording.
A3 also requested immutable-input checking for a5's temporary probe tree. Owners are reviewing
these findings; final disposition and exact final tests will be recorded before delivery.

The read-only [screen auditor](../scripts/audit_screen.py) recomputes observed usage from rollout
records, preserves unknown values, fingerprints the source report files and exports mechanism
sections. A caller-declared fixture label is never interpreted as measured zero inference.
Scripted screens explicitly make zero model calls; the agents writing/reviewing these mechanisms
consume separate inference that these fixture counts do not measure.

## Eligibility and dropped work

No live-screen winner or performance recommendation is made. All substantive prototype code
is retained on its branch for review/re-screening. A3's duplicate implementation was dropped
before publication; merged proposal ideas remain documented. No prototype may be combined
before both have passed the required screen. The operator may later advance at most three
live-screen survivors based on expected effect on the measured defects, followed by the fixed
quality/time/token evaluation. Candidate ranking and exact enable lines will be finalized with
the remaining screen reports; missing live evidence will remain visibly missing.
