# Batch-1 baseline results (rubric per PLAN.md, fixed before changes; judges blind)

| Arm | Wall min | Input | Uncached | Output | Correct | Regress | Risk (P0/P1) | PR.md | Design | Mean |
|---|---|---|---|---|---|---|---|---|---|---|
| A swarm-new (batch 1) | 26.9 | 12.80M | 340k | 80k | 8 | 10 | 8 (0/2) | 9 | 9 | 8.8 |
| A swarm-old (main)    | 21.0 | 9.31M | 294k | 58k | 10 | 10 | 7 (1/1) | 8 | 9 | 8.8 |
| A solo codex          | 23.8 | 2.23M | 108k | 36k | 9 | 10 | 8 (0/2) | 9 | 9 | 9.0 |
| B swarm-new (batch 1) | 21.0 | 6.60M | 233k | 65k | 10 | 10 | 7 (1/1) | 9 | 9 | 9.0 |
| B solo codex          | 21.7 | 1.12M | 86k | 35k | 8 | 10 | 7 (1/1) | 9 | 8 | 8.4 |

Wall = launch to exit, wall clock. Swarm root input: 0.18-0.22M (PR #2 fix holds).
Harness note: plain `codex exec --sandbox workspace-write` leaves .git read-only, so solo work
was committed by the harness afterwards (content unchanged). The first adversarial pass was
refused by the provider's cyber-safety filter ("attack" wording); re-run worded as QA review.
P0s: A-old lock-closing on failed stream construction; B-new interrupted write via hard-link
alias; B-solo lock replaced by another ledger with a colliding filename.
