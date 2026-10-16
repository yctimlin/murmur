# murmur eval plan (fixed 2026-10-13 23:4x Taipei, before any prompt change)

Purpose: validate batch 1 (full-suite regression check, risk-directed review, PR.md evidence,
early environment probe) on tasks never used before. This file is not edited after results.

## Tasks
- A (existing repo, real suite, risky path = data loss + concurrency): msiemens/tinydb @ 6d7c4fc,
  brief A/brief.md (crash-safe writes + multi-process safety).
- B (greenfield, risky path = money + deletion): splitledger, brief B/brief.md, empty repo.

## Arms (gpt-6-astra, effort high, same relay)
- swarm-new: murmur on feat/verification-batch1, 3 peers, cap 40m.
- solo: plain `codex exec` (no murmur) in a fresh clone, same model/effort, brief + "commit your
  work to main, write PR.md", cap 40m.
- swarm-old (optional, budget permitting): murmur on main before batch 1, task A only.

## Rubric (each 0-10, judge sees code + brief, not which arm produced it)
1. Correctness: the brief's outcome works (judge runs it and writes own checks).
2. Regressions: full suite (A: repo suite; B: its own suite + judge checks) vs base. A failure that
   also fails on base is not a regression. Score 10 = none, -3 per regression.
3. Risk-path bugs: a separate adversarial judge pass attacks the highest-risk paths (A: crash
   mid-write, concurrent writers, lock/rename edge cases; B: rounding/sum invariants, delete/edit,
   interrupted write, member removal). Score 10 - 2 per P0, -1 per P1 found.
4. PR.md accuracy: each claim checked against evidence; overstatement or uncited "verified" lowers.
5. Design quality: API/CLI clarity, simplicity, fit with codebase, docs.
Overall = mean of 1-5.

## Metrics
Wall time (launch to exit), murmur active minutes, exit code; tokens input / uncached / output
summed over all sessions (root separately for swarms); commits.
