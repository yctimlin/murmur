# AMENDMENT-9 — provider retry exhaustion (429) is infra too (extends AMENDMENT-6; tooling)

Written 2026-10-22 ~05:15 Asia/Taipei, during E4, before any E4 result is unblinded or analysed against a rule.

## Trigger (disclosed)
In E4-T1b-K1-r1, peer a3 was ended by codex at 19:38 (budget minute ~35) with task_complete error
"exceeded retry limit, last status: 429 Too Many Requests": the relay rejected requests until codex gave up. This is a
provider/relay failure in the sense of FAIRNESS.md F5, the same class as AMENDMENT-6's "stream disconnected" (codex
exhausted its retries on a provider error), but AMENDMENT-6's pattern does not match its wording. murmur does not and
must not handle 429 (BRIEF); the run is therefore an infrastructure failure, not a property of the arm.

What the PI saw before writing this: the run's descriptive logs (run ended at murmur budget minute 62/120, 27 of 84
ledger rows not closed, peers a1/a2 ended their turns, no END posts). Two blind judgments of the run had just been
written by the judge loop; the PI has NOT read the score file or the judgments. They are moved unread to
judge/E4-infra/ and will never be used.

## Rule
r4eval.provider_killed() now also matches a task_complete error message beginning with "exceeded retry limit". Same
scope as AMENDMENT-6: mechanical, arm-blind, every past and future run (dev and FINAL, swarm and solo).

## Effect at writing time (scan of all lab results)
Flagged: E1-T1b-C2-r3, E1-T2-C1-r3, E1-T2-C2-r2, E1-T3b-C1-r2, E1-T3b-C2-r3, E1-T4b-base4-r3 (all already infra under
AMENDMENT-6) and E4-T1b-K1-r1 (new). No other run changes class.

## Rerun
E4-T1b-K1-r1 is rerun under the same name (same spec, placed first in the queue) so that E4.md's (task, rep) pairing
is unchanged. The infra copy is moved to lab/results-infra/ and lab/ws-infra/ (outside the E4 globs).
