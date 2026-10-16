# Shared plan and user experience

Round two targets the observed collaboration failures with executable mechanisms: missing
independent review, absent checks of late integration, unclaimed work, interface drift, and
single-candidate risky logic. Every peer has the same authority; root remains spawn/wait-only.
The public interface stays `murmur setup` and `murmur run`, with no required new flags and no
hardcoded model, effort, context or compaction settings. Each prototype is default-disabled,
uses the existing private Git origin plus small durable state, and can compare enabled versus
base from the same build. Mechanisms apply to repositories, snapshotted folders and greenfield
work; their code prescribes no task filename or language.

Five code prototypes are delivered on separate `proto/*` branches. The aggregate
`experiment/self-improve-r2` branch contains research, screen evidence, the operator evaluation
plan and a read-only screen auditor. It preserves baseline runtime because **none completed a
live adoption screen in this environment**. This separation follows the explicit requirement
not to combine mechanisms before screening; it is not a claim that a docs-only intervention
solves the objective. The substantive new mechanism implementations and tests are on the
published prototype branches, ready for independent review and re-screening.

Shared contracts are existing setup metadata and `logs/run.json`, with prototype-specific
state under `work/` and generated peer helpers. Owners: a1 integration duty, a2 independent
review, a4 leased queue, a5 executable interface contracts, a6 measured alternatives; a3
merged duplicate proposals, independently reviewed drafts, provided accounting support and
assembled this report. Every prototype received independent archived-suite review. Findings
were returned to their authors and corrected rather than selecting the smallest diff.

## What changed and evidence strength

| Prototype | Concrete behavior | Evidence and limits |
| --- | --- | --- |
| `proto/a1-integration-barrier` | Any peer claims and executes a final-main check; stale/missing evidence prevents a successful run | [Real-Git tests and mismatch/repair/late-commit screen](research/integration-barrier.md). Proves mechanics, not check quality or live adoption. |
| `proto/a2-cross-review` | Every changed path requires an attestation from a peer other than its latest change author; self/stale/dirty receipts are rejected | [Author/revision tests and independent-review screen](research/proposals/a2-cross-review.md). Historical-author waiver was closed after review. Receipt quality remains human/model judgment. |
| `proto/a4-work-stealing` | Atomic ready-task claims, dependency ordering, lease recovery and fencing protect a durable shared work queue | [Concurrent-claim tests and two-unit handoff screen](research/work-stealing.md). Completion covers declared tasks, not the whole objective automatically. |
| `proto/a5-contracts` | Frozen executable probes reject violating main updates under Git's ref lock | [Activation/rejection/repair screen and race tests](research/mechanism-a5.md). Coverage is limited to declared invariants and available dependencies. |
| `proto/a6-alternatives` | Two peer candidates execute the same registered checks; only a passing candidate can advance unchanged main | [Candidate-selection/stale-head tests and screen](research/mechanism-a6.md). Duplicate coding costs tokens; executable checks must actually distinguish quality. |

The proposal inventory, prior art, cost hypotheses, exact screening measurements and conditional
shortlist are in [research/MECHANISMS.md](research/MECHANISMS.md). Sources are the supplied
round-one evidence and already-completed surveys; no sealed task or hidden test was inspected.
Every stronger claim about quality, speed, token targets or live adherence remains unverified.

The shared [audit script](scripts/audit_screen.py) recomputes provider-observed per-response
usage, detects disagreement with the persisted run record, preserves missing usage as unknown,
exports requested mechanism sections, and fingerprints the source files. It distinguishes
recorded elapsed seconds from UTC timestamp span. This is accounting/review support, not a
new optimization claim. Tests cover missing/malformed data, copied response deduplication,
stale totals, caller-declared fixture limits and differing clocks.

## Decisions and uncompleted work

- **Specific round-two instructions override generic draft voting.** There is no majority-vote
  winner. A3's overlapping work-stealing and contract proposals merged into a4/a5; the duplicate
  uncommitted implementation was discarded. [Proposal/disposition](research/proposal-a3.md).
- **No live survivor is claimed.** Every live attempt failed before children could read their
  briefs with `app-server socket directory must be a user-owned directory with mode 0700`.
  No sandbox, ownership, authentication or shared-host workaround was attempted. Some launchers
  returned zero because no scoped work was registered; those attempts still delivered no work
  and are explicitly failed adoption screens. [Attempt evidence](research/MECHANISMS.md#screening-and-independent-review).
- **Scripted screens are separate evidence.** They invoke real Git/SQLite/helpers but scripted
  fake peers. They prove firing and lifecycle behavior with zero model calls; they do not prove
  natural helper adoption. Development-agent inference is separate and unmeasured in those zeros.
- **No premature combination.** All prototype code stays isolated. The conditional re-screen
  shortlist is a2 review, a1 integration duty and a5 contracts because they directly address
  measured C1/C2/seam failures. A4/a6 remain reserves. This is effect-based triage, not an efficacy
  ranking or a result of screen timings. [Rationale](research/MECHANISMS.md#eligibility-conditional-shortlist-and-dropped-work).
- **Performance selection remains with the operator.** [eval-plan.md](eval-plan.md) requires
  functioning live screens, sealed-task/configuration freeze, matched off/enabled builds,
  repeated solo/base/candidate arms, blind checks, and fixed quality/time/total-input gates.
  Missing telemetry cannot pass a budget gate. No performance experiment was completed here.
- **Branch destination:** this environment's `origin` is the private local bare repository at
  `/workspace/self2/ws/r2/work/origin.git`. Its `main` is integration transport required by the
  peer workflow, not the real project's main branch. Final aggregate output is also published
  as `experiment/self-improve-r2`; prototype refs are preserved. No PR is opened, no force push
  is used, and no real upstream main is modified.

## How to see it

On the aggregate branch:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/capture_states.py /tmp/murmur-r2-states-new
.venv/bin/python scripts/audit_screen.py /path/to/completed/workspace --kind live --section KEY
```

The capture destination must not exist. Replace `KEY` with the prototype's actual run-report
section (`integration`, `independent_review`, `work_queue`, or `alternatives`); omit it for base
runs or use the contract prototype's separate event ledger. The audit command does not run a
model and does not treat a populated section as proof of mechanism activation.

For a prototype, check out its branch first and use its documented screen script and full suite.
The enable lines are:

| Branch | Internal setting at setup |
| --- | --- |
| `proto/a1-integration-barrier` | TOML `integration_barrier = true` via existing `--config` |
| `proto/a2-cross-review` | TOML `independent_review = true` via existing `--config` |
| `proto/a4-work-stealing` | TOML `work_stealing = true` via existing `--config` |
| `proto/a5-contracts` | `MURMUR_CONTRACTS=1 murmur setup BRIEF [existing options]` |
| `proto/a6-alternatives` | `MURMUR_ALTERNATIVES=1 murmur setup BRIEF [existing options]` |

Omit/disable the setting for base from that same branch build. Re-screen before enabling more
than one mechanism in a future combined build. No prototype configuration is silently active
on this aggregate branch.

## Verification

All five initially published prototype suites passed independent a3 archive review: a1 **64**,
a2 **62**, a4 **63**, a5 **58**, a6 **60** tests. Subsequent focused fixes and final branch revisions
are recorded in [MECHANISMS.md](research/MECHANISMS.md); aggregate validation passes **57 tests in 10.54 seconds**. The six-state capture retains
expected exits **0 / 1 / 1 / 124 / 130 / 0**; both original launcher behavior and additive
audit export were checked. Current focused follow-up suites also pass: a2 12, a5 10, a6 8. The original [research/evidence/](research/evidence/) files are
unchanged. Environment-blocked live attempts retain observed token totals and explicit lack
of activation. No macOS/Windows behavior, live quality improvement, speedup or token-ratio
success is claimed.
