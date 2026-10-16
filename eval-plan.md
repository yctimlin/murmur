# Round-two preregistered operator evaluation

This plan is prepared before access to the operator's sealed tasks. No evaluation task, private
fixture, hidden test, or expected solution was inspected or guessed. The operator must freeze
the task IDs/content hashes, exact code revisions, model/provider settings, resource limits,
run order and judge rubric before executing the first evaluation arm. The local screening
examples are development fixtures and must not become evaluation tasks.

## Eligibility before comparison

A candidate must pass the full repository suite and a fresh, small **live-peer** screen that
shows its required state transition in durable mechanism evidence. The screen uses at most
three peers and the existing `--cap 25m`. Preserve all attempts, including infrastructure
failures and cases where the helper is never used. An unused or crashing mechanism is not a
survivor. Fake-Codex/real-Git fixtures demonstrate mechanics only; they cannot satisfy a
predeclared live-adoption requirement or substitute for missing inference measurements.

The round-two environment currently prevents child shells from reading their instruction
files (`app-server socket directory must be a user-owned directory with mode 0700`). No
permission, sandbox, credential or shared-host workaround is authorized by this plan. A
blocked live screen remains blocked. Any shortlist is conditional until the operator can
re-screen in a functioning environment. Do not combine mechanisms until each has passed.

At most three surviving mechanisms advance. If more survive, prioritize expected effect on
the measured failure modes: missing late integration checks, unreviewed sole-author logic,
and unprotected interfaces. Published peer rankings may narrow the candidate set but cannot
select a performance winner. Diff size, implementation conservatism and majority vote are
not selection criteria. Record the final candidate IDs and rationale before evaluations.

## Arms and controls

For every sealed task, run three replicates of each eligible arm. Each prototype is its own
branch build: compare its enabled arm with the same branch build disabled. Do not pool base
runs across different builds without first verifying identical disabled behavior:

- **Solo:** the same model/provider configuration, task, dependencies, tools and time budget,
  using the existing solo mode.
- **Base:** two equal peers from the candidate-capable build with every mechanism disabled.
- **Each candidate:** the identical build and two equal peers, with exactly that one internal
  mechanism setting enabled. Do not enable an untested combination.

Use fresh workspaces from the same input revision or folder snapshot. Preserve model/effort
preferences through existing user configuration; this plan specifies no model name, context
size, compaction threshold or default reasoning level. Keep CPU/RAM/tool/network limits,
setup commands, backend, cap and peer count constant across swarm arms. Freeze an order that
counterbalances arms within tasks and replicates. Record provider/configuration changes;
do not silently substitute a different model when an arm fails.

## Outcomes collected from every attempt

Keep `murmur.json`, `logs/run.json`, per-response Codex rollouts, final delivered revision,
mechanism ledger/events, test output, and all partial artifacts. Use
`scripts/audit_screen.py WORKSPACE --kind live --section KEY` to export existing reports;
this is a read-only accounting aid, not a quality judge or proof of activation.

Record separately:

1. Launch-to-exit wall seconds, cap/interruption/provider/mechanism exit, and any externally
   measured machine pause interval. Raw wall time is primary; report adjusted time only when
   the same independently measured adjustment exists for all arms.
2. Observed **input**, cached input, derived uncached input, output, and input-plus-output
   tokens, with response count, coverage gaps and malformed records. Do not add reasoning
   tokens to output a second time. A missing total cannot pass the budget gate.
3. Mechanism activation and coverage: claims/reclaims or trials/checks/reviews as appropriate,
   stale/invalid attempts rejected, final evidence state, and work left unfinished. Count
   actual triggering events; a directory or zero exit is insufficient.
4. Blind task quality: independent executable requirements, regression checks, severity-tagged
   behavioral defects, and a frozen 0–10 overall rubric combining correctness, regressions,
   high-impact risks, requirement fidelity and interface/design clarity. Judges see the task
   and final artifact, not branch/arm/peer metadata or coordination claims.
5. Defect location/provenance: single-author delivered logic, cross-part interface, or other.
   Have judges locate and demonstrate the defect before an unblinded provenance audit.

All arms receive the same independent checks and judge budget. Receipt existence, check exit
zero and helper coverage are intermediate mechanism outcomes, not evidence of no defects.
Inspect high-impact failure behavior explicitly when the task has it; do not introduce
language-specific or task-specific requirements into the mechanism itself.

## Fixed keep rule and ranking

Report per-task/per-replicate values, paired differences, medians and uncertainty; never report
only the most favorable run. The primary budget ratio is total observed **input tokens**;
input-plus-output is a co-reported cost metric, and cached/uncached ratios are diagnostics.
A candidate is eligible for adoption only if all of these hold across the frozen suite:

- Mean blind quality is at least solo and at least base; no increase over either comparison
  in the total count of independently demonstrated highest-severity defects.
- Median paired wall-time ratio is below 1.0 versus solo, and no task's median exceeds 1.25
  times base. Capped runs count at their full cap and retain their partial-artifact quality.
- Median paired total-input ratio is at most 2.0 versus solo, with no task's median exceeding
  2.0. Also disclose input-plus-output and uncached ratios; they cannot replace this gate.
- The candidate has the intended mechanism activation on every successful enabled run, and
  improves mean blind quality by at least 0.5/10 **or** reduces highest-severity defects versus
  base. Mechanical activation alone is insufficient.

If none meets all gates, retain base and publish the failed hypotheses. If multiple qualify,
rank by highest mean blind quality, then fewer highest-severity defects, then lower median
paired wall time, then lower total input. Do not use peer votes. This bounded experiment is
not proof of universal superiority; retain per-task failures and confidence limits.

## Missing data and infrastructure failures

A process failure remains in the outcome table. A reproducible infrastructure failure may
justify one replacement attempt for the whole affected matched block after the operator
repairs it, but retain both attempts and a sensitivity analysis including the originals.
Do not repair permissions or another run's resources from a peer to make an arm succeed.
Incomplete token coverage means the cost criterion is unverified. Do not impute missing
usage as zero or infer missing requests from cumulative counters. Do not call the resulting
comparison preregistered if task/arm choices or keep thresholds change after outcomes are seen;
record amendments with timestamps and label subsequent results exploratory.
