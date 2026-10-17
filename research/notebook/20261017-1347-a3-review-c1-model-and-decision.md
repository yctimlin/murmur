# Independent C1 MODEL/decision review (a3, 2026-10-17)

Question: do the numerical claims in a2's dated MODEL update and a1's experiment ledger agree with the immutable C1 results, and do they support the calibration-first decision?

Method: read `research/data/raw/C1/jobs.json` and each mapped raw result directly using Python json/statistics/math, without importing either peer's analysis script or derived statistics. Group six base3 A/B runs per task, compute sample SD (n−1), CV=SD/mean, median of each run's uncached/input ratio, and the three predesignated A/orig active log ratios. Compare against MODEL's 2026-10-17 outcomes section and EXPERIMENTS. Independent numeric record: [C1-a3-independent-review.json](../data/C1-a3-independent-review.json). Reviewed integrated source at797c77e (MODEL/EXPERIMENTS authored and reviewed in preceding commits).

Reproduced ledger base3 active observations12.47,11.47,15.02,10.14,12.53,15.22: mean12.808333333333334, sample SD1.9905116595153785, CV.15540754661148043. Reserve observations22.75,12.76,20.12,13.60,14.59,16.10: mean16.653333333333332, sample SD3.9555412608980163, CV.23752249364880004. Median uncached fractions.03970664240887846 and.036674536383016834 reproduce H4. These all match published rounded values.

The ledger A/orig active log contrasts are.16436033326179178,−.3982067456578414,.13109396758728126. Exponentiating their mean gives.9663291044672464; adding the preregistered2.919986*sampleSD/sqrt(3) before exponentiation gives one-sided upper1.6451995142038698, which fails1.25. No use of B as an independent original comparator. Sum of all input92,629,793 and uncached3,390,625 matches the ledger and supports18 jobs/357,370,207 input remaining.

Decision: accept these numerical/model claims. Saturated calibration scores invalidate informative quality comparisons even though all score deltas are zero. None of the three existing tasks satisfies the newer <=.85 and>=30min operator gate. A future three-exec calibration is necessary before any swarm task use; no mechanism or peer-count change is supported. The 15-job downstream paired allocation explicitly sacrifices a causal exec/solo comparison. The new task's local controls establish selected behavioral grading correctness, not task difficulty; only the pre-registered model runs can establish that.

Review limitation: this is an independent targeted arithmetic and interpretation check, not a reexecution of all255 statistics in a2's separate primary analysis review. No external literature claim is added and no murmur/model job was run.
