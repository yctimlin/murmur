# Independent review: C2 calibration registration and fixture, a2, 2026-10-17

## Question
Does a3's C2 registration at797c77e implement the new task-admission gate, preserve the round budget, and provide a reviewable next step without implying unmeasured difficulty or promoting a mechanism?

## Method and predictions under review
Read `research/prereg/C2.json`, its referenced pre-run notebook, final workflow_store SPEC/TASK/setup/scorer contract, operator GATES, and all recorded control outcomes. Independently validate registration/known budget using `research/tools/validate_c2.py`. Regenerate the public input twice in isolated temporary copies, compare all file hashes and git seed commits, and verify no hidden/reference files enter solver input. Compare all old task files, C1 prereg, and C1 raw data against phase-start963ae66. No real model or murmur run is launched.

Frozen C2 forecasts are score.80, active45min, input2.7M, uncached.162M, successful delivery with broad explicit run bands; task-author expected_solo_min60 is separately labeled. They are prospective elicited forecasts, not measured properties. The 129-case positive control shows feasibility only.

## Results / reproduced numbers
`research/data/C2-design-independent-review.json` records passing checks: exactly3 exec jobs, zero swarm jobs, one concurrent block of3, equal100m caps, no env/config switches, correct base3 revision f95eaa169f1cd1741d1fbf02d7d939f8e77ba156 verified in runner git. Exact raw C1 input sum92,629,793 leaves357,370,207 before C2;3*3M scheduler estimate leaves **348,370,207 input and15 jobs**. Frozen old task/prereg/raw contents are unchanged.

The final task's generated seed is **a91d3bbe52ec4e7bd08002b85b8d23a0d6171085**, identical in both independent regenerations. Only SPEC.md, README.md, examples/batch.json and .gitignore are delivered. Final SPEC SHA256 is **adfc9d869d49a7cf5e88c71726224b07161d4427695578f15c18a90b19e0978c**. The earlier ambiguity “Every failure leaves the target empty” was corrected before freeze to unchanged state (already-empty targets remain empty); this preserves nonempty-load rejection semantics. Final manifest matches a3's control report. a1 independently reviewed reference129/129, empty0/129 and an expiry defect122/129; a3 additionally reports eight detected negative controls. These checks do not guarantee complete coverage or >=30min model runtime.

## Decision
**Accept C2 for scheduler execution.** It requires each of all3 runs to be valid, delivered, leak-free and uncensored, with score<=.85 and active>=30; equality boundaries are explicit. It retains invalid/failed runs and forbids favorable-subset selection or unregistered replacement. All jobs have identical treatment; three within-block pairwise differences are explicitly dependent, not three experimental comparisons. C1 and later arms cannot be turned into causal exec comparisons by cross-batch subtraction.

The conditional15-job downstream allocation [solo,protocol1]x3 plus [protocol1,2,3]x3 can measure the protocol bundle and peer curve with true paired blocks; its forecasts/decisions require a future preregistration after calibration. The missing concurrent exec comparison is acknowledged. If any calibration fails the conservative rule, the registered decision is C-DONE next phase with unresolved questions and unspent budget. No mechanism/default change or new murmur implementation is proposed. Current task qualification remains unknown until actual calibration; accepting a registration is not accepting the task for swarm use.
