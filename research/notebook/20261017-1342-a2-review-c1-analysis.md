# Independent review: C1 primary analysis, a2, 2026-10-17

## Question
Does a1's primary analysis at commit8b84cbf reproduce raw C1 data and follow the immutable decision rules, and does the prose agree with those numbers?

## Method and expected result
Independently implemented `research/tools/review_c1_model.py` before reading a1's calculation (first committed2a5a831). It imports only standard-library modules, reads raw JSON and the immutable preregistration, and does not call/import the primary script. Compared its serialized results to `research/data/C1-analysis.json`: each task/arm score/time/input/uncached mean and sample SD, coverage, mean error, mean-band failure; each paired geometric ratio, log mean/SD, nominal upper bound and two-sided interval; exact total input. Tolerance1e-12 relative. Expected identical numbers and zero eligible tasks under the saturation rule.

## Reproduced numbers and raw paths
Ledger six base3 active values in run order are12.47,11.47,15.02,10.14,12.53,15.22 from `research/data/raw/C1/C1-03-base3A.json`, `C1-05-base3B.json`, `C1-09-base3B.json`, `C1-10-base3A.json`, `C1-13-base3B.json`, `C1-14-base3A.json`. Their sum76.85 divided by6 gives **12.808333333333334**, sample SD **1.9905116595153785**, CV **.15540754661148043**. This reproduces a1's table.

For bug-fix active cost, the only allowed A/orig paired ratios are12.47/10.58,10.14/15.10,15.22/13.35. Their geometric mean is **.9663291044672464**; exponentiating mean(log ratio)+2.919986*sampleSD(log ratio)/sqrt(3) gives **1.6451995142038698**, failing the<1.25 nominal noninferiority margin. All score deltas are0 but calibration excludes the task from confirmatory inference. a1 correctly did not count B as a second comparator.

All **255** compared numerical fields/checks agree (see `research/data/C1-analysis-independent-review.json`). Input totals **92,629,793**, leaving357,370,207. Single-observation SD is null. Missing C1-06 mutation stays missing; timeout denominator review is in `20261017-1340-a2-review-c1-mutation.md`.

## Review finding and decision
Arithmetic and registered estimators pass. One material prose inconsistency was found and sent to a1: EXPERIMENTS.md incorrectly states most swarm input means fall below frozen bands. In fact **only the three exec input means** fall below; all five swarm arm means and both pooled base3 means are inside. Ledger input lower band is4,139,520 and A/B/orig means are4,451,288.6667/5,140,884/4,921,681.6667. Reserve lower band6,816,000 and A/B means8,242,595.3333/7,623,305.6667. The generated primary table and MODEL already report this correctly. Require the prose correction before calling the complete report accepted; preserve this finding rather than silently overwrite it.

The analysis correctly reports ceiling scores descriptively, no confirmatory eligible tasks, no gross-regression trigger, inconclusive bug-fix noninferiority, H5/H6 untested, and no mechanism promotion. No real murmur experiment was run during this review.
