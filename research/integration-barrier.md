# a1: claimable integration barrier

Status: code prototype; deterministic screen passed; live adoption unverified because the
host blocked both nested peers before reading their brief. Branch `proto/a1-integration-barrier`.
Enable with `integration_barrier = true` in the TOML passed to existing `murmur setup --config`.
The default is false and solo runs omit the mechanism. No new public command or flag.

## Failure, prior art and prediction

Our supplied [LOG.md](evidence/LOG.md), C2, reports peers stopping within 0.5–3 minutes
of one another across seven runs, with zero or one peer checking final main and 2–6 commits
arriving in the final fifth. C1 also identifies bugs at UI/API seams. Prior prompt-based
review failed its aggregate keep rule ([large results](evidence/large-RESULTS.md)).

The design borrows claimable duties and executable integration checks from the compiler
case study already surveyed in [evaluation.md](evaluation.md):
https://www.anthropic.com/engineering/building-c-compiler . Its revision binding resembles
Git-based CI rather than a prose "tests passed" message. The installed Codex source
`/workspace/codex-src-0.162.1/codex-rs/core/src/agent_message_board.rs:1` explicitly says board
notifications never start or restore an idle agent. Accordingly this design keeps a duty
visible before peers finish and does not depend on a last-minute notice waking them.
These are design precedents, not evidence of murmur performance.

Prediction registered before the screen: enabled successful runs have a passing command
receipt for exactly delivered main, never a stale receipt; a later blinded evaluation
should test fewer seam P0s at no more than 2x solo total input. Expected coordination cost
is one bounded readiness result per peer, one claim/check result, and status at handoff.
There is no additional model role. Actual model-call/token overhead remains unverified.

## Mechanism and boundaries

Setup freezes a standard-library Python helper and a SQLite ledger in the run workspace.
Each clone receives `.murmur/integration`. Peers call `ready` after pushing/pulling their
implementation; `active` withdraws readiness. Once all are ready, **any** peer may claim and
run `check -- COMMAND ARGS...`. Claim acquisition is transactional and has a finite lease.
The helper runs the real command with a timeout, captures its log and records exit status,
revision, duration and clean-worktree state. It rejects dirty/stale clones and commands
that leave tracked or nonignored untracked changes (documented `.work/` scratch excluded).
Use project ignore rules or tools' normal options for generated non-deliverable output.

The receipt is valid only for that exact shared revision. A subsequent main update,
readiness withdrawal, failure, timeout, mutation or stale concurrent check prevents
completion. The runner reads authoritative main again at finalization. When Codex exits
zero without a complete barrier, murmur returns exit 2 and records the missing evidence in
`logs/run.json`. Existing failures, interruption and cap retain their original exits. Root
instructions and model/effort/context choices are unchanged.

The ledger is cooperative coordination, not a security boundary. A peer can select a weak
command; a successful process does not prove semantic correctness or test coverage. Readiness
is an explicit peer declaration, not automatic task discovery. A crash may leave a claim until
its timeout-plus-30-second lease expires. Finalization detects abandonment but does not revive
peers automatically. Ignored files, dependencies and services are outside revision identity;
checks are executed each time and never reused as a cross-environment cache. Hooks are not
installed, so push throughput and existing repository hooks remain unchanged.

## Screening evidence

[Machine-readable evidence](screens/a1-integration.json) distinguishes two experiments:

- `python scripts/screen_integration.py NEW_DIRECTORY` executes a tiny producer/consumer
  key mismatch through real Git, generated helpers and a scripted fake Codex process. Base
  finishes despite the mismatch; enabled check fails, a peer repairs the producer, another
  checks successfully, a late documentation commit invalidates that receipt, and rechecking
  completes. The observed setup-plus-run wall times were **0.378s base / 0.877s enabled**.
  Both return zero; enabled does so after repair and a final-head check. This fixture makes
  **zero model calls/tokens**; run.json correctly labels usage unavailable. The fake peer
  driver is explicitly programmed to use the mechanism, so this does not establish adoption.
- The live invoice-formatter screen used **2 peers, cap 25m**, ran for **188.7 seconds**, and
  stopped with both peers unable to execute a shell because the app-server socket directory
  failed its ownership/mode-0700 requirement. No environment or sandbox workaround was used.
  Codex exited zero; the barrier correctly returned **2**, with both peers pending. Observed
  usage: **652,824 input**, **586,752 cached**, **66,072 uncached input**, **1,126 output**;
  **653,950 total**, 29 observed responses. No implementation or integration check fired in
  that live run. This is a blocked adoption screen, not a quality or cost comparison.

An initial scripted attempt created Python bytecode as untracked files and was correctly
rejected by the clean-worktree guard. The fixture now uses Python's `-B` switch; no mechanism
exception for Python was added. An initial live setup accidentally pointed inside this Git
checkout; it was never run. The actual live screen used a distinct plain folder under `/tmp`.

## Verification and disposition

The full suite passed **63 tests** after implementation. New tests cover off/solo behavior,
missing evidence exit, frozen helper execution, readiness/current-main checks, failed and
mutating commands, stale receipts, simultaneous claim exclusion, expired-lease recovery,
main moving during a running check, readiness withdrawal, timeout and missing ledger.

This candidate survives the **deterministic firing screen only**. Live adoption remains
blocked and must be rerun in a functioning environment before interpreting performance.
It is eligible for a conditional operator shortlist because it directly targets measured C2;
no claim of better quality, speed or tokens is made, and no winner is selected by vote.
