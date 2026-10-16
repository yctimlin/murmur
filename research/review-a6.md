# a6 independent mechanism review

All archives were made from published prototype branches under a6's own `.work/`.
No peer clone or sealed evaluation input was inspected or changed. These are
credential-free regression/runtime checks, not model-performance experiments.

| Prototype | Independent initial full suite | Extra finding and disposition |
| --- | --- | --- |
| a1 integration barrier | 63 passed, 14.59s | Inspected exclusive claims, lease expiry, clean/current-head guards, late-update invalidation and final exit. No additional blocker found. |
| a2 independent review | 62 passed, 13.10s | A no-conflict merge by a second peer counted as content authorship and waived the sole-author obligation. Reproduced with independent real-Git regression (failed in 0.48s); owner corrected merge attribution in `99773f3`; regression then passed in 0.33s. |
| a4 work stealing | 63 passed, 12.41s | Inspected atomic claims, dependency readiness, expired-owner fencing and handoff notes. No additional blocker found. Completion covers declared work only. |
| a5 executable contracts | 58 passed, 13.29s | A probe could repair its temporary tracked file before asserting, then admit the original broken revision. Reproduced (failed in 0.49s); owner corrected tracked-tree validation in `22ed84c`; independent regression passed in 0.45s. a3 independently identified the same gap. |
| a6 alternatives | Owner initially 60 passed, 13.40s | a3 found failed-trial recovery contradicted retry guidance. Owner added one audited retry, preserving checks and prior evidence, and later added missing-ledger/interrupted-child cleanup coverage. See mechanism-a6.md for final suite. |

The merge reproduction creates a1's `logic.py` on a draft, creates unrelated work
by a2, merges a1's draft with `--no-ff`, and checks that `logic.py` still requires
independent review. The contract reproduction freezes a probe that rewrites a
tracked file to the baseline value before asserting; a changed incoming revision
must be rejected despite the probe's zero exit.

Conditional re-screen priority is integration duty, independent review, and
executable contracts. This follows the measured final-head, single-author, and
interface failures directly; it is not a vote for a performance winner or a
preference for small diffs. Work stealing addresses potentially stranded work
without direct evidence of that bottleneck in the supplied failures. Alternatives
incur an additional implementation context for the same risky unit. Keep both
branches/evidence so operator results can overturn these expectations.

The shared integration branch at `406c428` passed 56 tests in 10.71s. Six launcher
captures produced the expected exits 0/1/1/124/130/0 for success, failure, partial
result, cap, interruption, and a resistant descendant. Subsequent changes inspected
through `caec075` were documentation/evidence updates. No live-agent adoption or
quality, speed, or token-ratio gain is established by this review.
