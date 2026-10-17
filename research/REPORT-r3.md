# Murmur round 3: measurement and foundation report

2026-10-17. **Freeze decision: no candidate mechanism or parameter finding.** The four fixes remain on the bug-fix base, but this round does not establish performance noninferiority. The experiments measure substantial time/token variation on short, saturated tasks. They do not identify a protocol penalty, a peer-count optimum, or quality noise on difficult work. `CANDIDATE.json` is the machine-readable decision; [NEXT.md](NEXT.md) ranks the remaining work.

## Evidence, scope and admission failure

The protected original is `eec78f8`; the scheduler-pinned bug-fix base is `f95eaa169f1cd1741d1fbf02d7d939f8e77ba156` (base3). All C1 murmur arms use one of those revisions. [C1](prereg/C1.json) scheduled 18 runs: three separate exec task calibrations, six base3 A/A repeats each on ledger_replay and reserveplan, and three original-baseline ledger runs. [C2](prereg/C2.json) scheduled three exec repeats of workflow_store in one concurrent block. No researcher submitted additional lab jobs.

Every one of the 21 runs delivered, scored 1.0, exited zero, and recorded zero leak hits and zero rate-limit lines. This is observed coverage, not evidence of population reliability. C1's first exec calibration exceeded its preregistered .95 saturation threshold on all three tasks; **zero confirmatory eligible pairs remain**. C2 additionally required every calibration to score ≤.85 and take ≥30 active minutes. Its three runs all failed both thresholds. None of the four frozen tasks qualified as the requested 45–90 solo-minute long task. The C2 ineligible branch therefore ended experimentation in [C-DONE.md](C-DONE.md), with no C3 and no favorable subset or replacement runs.

| Task / exec calibration | n | Scores | Active minutes, every run | Admission |
|---|---:|---|---|---|
| document_catalog | 1 | 1.0 | 8.20 | C1 saturated; also below 30 min |
| ledger_replay | 1 | 1.0 | 10.78 | C1 saturated; also below 30 min |
| reserveplan | 1 | 1.0 | 15.03 | C1 saturated; also below 30 min |
| workflow_store | 3 | 1.0, 1.0, 1.0 | 19.81, 14.31, 15.46 | All fail C2 score and time gates |

The inputs, decisions and independent reviews are preserved in [EXPERIMENTS.md](EXPERIMENTS.md), the [C1 complete analysis](data/C1-analysis.md), the [C2 notebook](notebook/20261017-1415-a1-c2-analysis.md), and their linked raw results. C1 numerical review reproduced 255 values ([initial review](notebook/20261017-1342-a2-review-c1-analysis.md), [accepted correction](notebook/20261017-1343-a2-review-c1-analysis-accepted.md)); [C2 review](notebook/20261017-1425-a2-review-a1-c2-analysis.md) reproduced its active mean, SD, run validity and gate. No frozen preregistration, raw result or hidden task was changed in phase D.

## 1. Same-condition noise: measurable costs, unmeasured unsaturated quality

The table pools only identical treatments within each task. Sample SD uses n−1. The six base3 repeats occupy three concurrent A/B blocks per task; C2 has three exec runs in one block. Input means total input, including cached input; uncached is a subset. Output remains separately recorded rather than being conflated with input. Active minutes are the runner's capped union of event time; wall time is a different endpoint.

| Task / treatment | Runs / blocks | Active min, mean ± SD | Wall min, mean ± SD | Input, mean ± SD | Uncached, mean ± SD | Score / delivery |
|---|---:|---:|---:|---:|---:|---|
| ledger / base3, 3 peers | 6 / 3 | 12.8083 ± 1.9905 | 18.7867 ± 2.9691 | 4,796,086 ± 773,150 | 195,382 ± 31,187 | 1 ± 0 / 6 of 6 |
| reserve / base3, 3 peers | 6 / 3 | 16.6533 ± 3.9555 | 20.1000 ± 4.7886 | 7,932,951 ± 2,783,804 | 238,337 ± 36,195 | 1 ± 0 / 6 of 6 |
| workflow / plain exec | 3 / 1 | 16.5267 ± 2.9010 | 17.2067 ± 2.8069 | 1,025,845 ± 177,806 | 67,893 ± 8,905 | 1 ± 0 / 3 of 3 |

Active/input/uncached CVs were **.1554/.1612/.1596** on ledger, **.2375/.3509/.1519** on reserve, and **.1755/.1733/.1312** on workflow exec. On the same base3 revision and same reserve task, a single paired active ratio ranged .6759–1.7829 and input ratio .5262–2.1523. Thus a near-unit average A/A ratio does not imply stable individual runs. These are descriptive small-sample observations; no noise is pooled across tasks or wrappers.

| A minus B, three independent blocks per task | Active difference mean ± SD, min | Input difference mean ± SD | Uncached difference mean ± SD | SD of log A/B: active / input / uncached |
|---|---:|---:|---:|---|
| ledger | −.3967 ± 3.9736 | −689,595 ± 1,323,224 | −35,771 ± 44,453 | .3121 / .2870 / .2139 |
| reserve | +.6533 ± 8.4649 | +619,290 ± 5,783,905 | −23,654 ± 36,373 | .4974 / .7091 / .1471 |

Every A/A score and delivery difference was zero. This reports ceiling saturation and all-success observations; it cannot supply an informative quality-noise estimate or rare-delivery-failure bound for future long tasks. C2's three pairwise active differences (+5.50, +4.35, −1.15 minutes) share runs and are **dependent**, not three replicated blocks. The one-block sample cannot estimate between-block variability.

Median base3 uncached/input fractions were .0397066 on ledger and .0366745 on reserve, near the frozen .04 forecast. The high cached shares are accounting results, not estimates of removable overhead. C1 output means ± SD were 43,576.5 ± 8,147.1 on ledger base3 and 56,136.5 ± 4,494.9 on reserve base3; C2 output was 36,533.7 ± 6,272.0. Full precision and all other endpoints appear in the linked analysis artifacts.

## 2. Protocol versus parallelism: historical gap verified, cause unresolved

[DIAGNOSIS.md](DIAGNOSIS.md) independently reconstructs the advisor's **16 historical swarm/solo task pairs**: mean judge-score difference swarm minus solo **−.6521 points**, sample SD **.7647**, better/tied/worse **2/2/12**; geometric input ratio **5.260×**, geometric active-time speedup **1.145×**. Each historical task/arm has one run; changing revisions, tasks and rubrics prevent causal attribution. Judge points are not hidden-test pass-rate points. Evidence and per-pair values are in that document and [the model/design review](notebook/20261017-0816-a3-c1-design-review.md).

Round 3 has **six exec runs, zero murmur-solo runs, zero protocol-one runs, zero protocol-two runs, and fifteen protocol-three runs** (including the original-baseline arm). It therefore supplies no matched four-arm experiment. C1's single exec observation per task and C2's different task cannot be combined with the swarms into a controlled protocol contrast. The −.65 historical gap remains unexplained. Neither parallel work nor board traffic has been isolated as its cause.

The test-covered `MURMUR_ONE_PEER_PROTOCOL=1` instrumentation enables the missing protocol-one arm while retaining the root/peer workflow. It is an experimental switch, default off, not a validated improvement. A future solo-to-protocol-one contrast measures the whole protocol bundle; exec-to-solo also includes wrapper/delivery differences. [MODEL.md](MODEL.md) gives the source-path grounding and the frozen predictions.

## 3. Peer-count curve: no fit is identifiable; third-peer value unknown

The preregistered working time model was

```
T(n,p,S,k) = h[p] + S * (1/n + alpha*(n−1)/n + beta*k*(n−1)).
```

This separates a fixed wrapper term from serial and coordination terms as a hypothesis, not as measured partitions. With no protocol-one or protocol-two observations, the design does not identify its coefficients. **A fitted peer-count curve cannot honestly be reported.** Neither the time saved by a third peer nor its marginal token cost is measured on a qualifying long task.

The frozen reserveplan prior predicted protocol-one/two/three active times **70 / 57 / 59.1667 minutes** and input **4.200 / 8.892 / 17.040M**; that implies a third peer taking 3.8% longer and 91.6% more input than two. These remain untested predictions. They are not findings and do not justify changing the default peer count.

The measured three-peer reserve mean was 16.6533 minutes and 7.9330M input, while its single exec calibration took 15.03 minutes. This task-size forecast failed: all 18 C1 active measurements fell below their frozen per-run bands; C2's redesigned task averaged 16.5267 minutes against its 45-minute point forecast. A short-task three-peer/exec ratio is not a substitute for the required paired count experiment. The frozen model and all forecast errors remain in [MODEL.md](MODEL.md) and [C1 forecast data](data/C1-forecast-runs.csv); no coefficients were refitted after seeing the failure.

## 4. Bug-fix safety: reproducible fixes, inconclusive performance noninferiority

The only registered safety contrast is base3_A versus original on ledger, in three concurrent blocks. Base3_B is not an additional independent baseline comparison.

| Treatment, n=3 each | Active min, mean ± SD | Input, mean ± SD | Uncached, mean ± SD | Score / delivery |
|---|---:|---:|---:|---|
| base3_A | 12.6100 ± 2.5429 | 4,451,289 ± 1,019,960 | 177,497 ± 19,495 | 1 ± 0 / 3 of 3 |
| original | 13.0100 ± 2.2791 | 4,921,682 ± 933,968 | 213,074 ± 11,190 | 1 ± 0 / 3 of 3 |

| Paired endpoint | Mean difference ± SD | Geometric ratio | Descriptive two-sided 95% ratio interval | One-sided 95% upper ratio |
|---|---:|---:|---|---:|
| Active minutes | −.4000 ± 3.9491 | .96633 | [.44117, 2.11663] | 1.64520 |
| Input | −470,393 ± 1,405,027 | .90053 | [.41251, 1.96593] | 1.52970 |
| Uncached | −35,577 ± 22,928 | .83057 | [.61620, 1.11950] | 1.01710 |

Score differences were 0/0/0 and delivery pairs 1/1 in all three blocks. No registered gross-regression trigger fired, but this is **not noninferiority**: all pairs are excluded by saturation, and even nominal active/input upper bounds fail the 1.25 margin. The degenerate score interval is not informative quality evidence. Intervals assume approximately normal paired log ratios at n=3 (df=2); the smallest exact two-sided sign-flip p-value with three nonzero pairs is .25. No .05 significance claim is available.

The retained fixes have deterministic regression coverage and independent reviews:

| Fix | Reproducer / behavior | Evidence and review |
|---|---|---|
| No-work success | `tests/test_bug1_no_work_delivered.py`: no main advance produces a nonzero result and delivery diagnostic; peer instructions require integration | [implementation](notebook/20261017-0710-a2-bug1-no-work-delivered.md), [baseline-failing review](notebook/20261017-0703-a1-review-bug1-no-work-delivered.md) |
| Transient 429 | `tests/test_bug2_rate_limit_retry.py`: bounded retry within cap, records attempts and delivery | [implementation/reproducer](notebook/20261017-0718-a1-bug2-rate-limit-retry.md), [review](notebook/20261017-0725-a3-review-bug2.md) |
| Empty wait / signals | `tests/test_bug3_empty_wait_signals.py`: empty wait result leads to list-agents; SIGINT reaches child process group and exits promptly | [implementation](notebook/20261017-0700-a3-bug3-empty-wait-signals.md), [signal follow-up](notebook/20261017-0720-a3-forward-signals.md), [review](notebook/20261017-0720-a1-review-bug3-signal-forwarding.md) |
| Empty model catalog | `tests/test_bug4_empty_model_catalog.py`: fail before writing an unusable catalog | [implementation](notebook/20261017-0648-a1-bug4-empty-model-catalog.md), [review](notebook/20261017-0655-a2-review-bug4-empty-model-catalog.md) |

The CLI remains `murmur setup` and `murmur run`, the root remains a launcher/waiter, and no phase-D production behavior is changed. Code-level regression tests address these specific failures; the easy-task lab results cannot establish their rare-failure prevention rate or ordinary-case safety on difficult work.

## Every round-3 run and data completeness

The compact table reports all runs; full wall/output/commits/mutation records and paired values are in [C1](data/C1-analysis.md) and [C2](notebook/20261017-1415-a1-c2-analysis.md). All rows have score 1.0, delivery true, run_exit 0, leaks 0 and 429 lines 0. Exec rows omit setup_exit; every available swarm setup_exit is zero. No primary endpoint is missing or censored.

| Raw run (C1 or C2 directory) | Task / arm | Active min | Input | Uncached |
|---|---|---:|---:|---:|
| C1-00-execcalibration | document / exec | 8.20 | 296,783 | 33,999 |
| C1-01-execcalibration | ledger / exec | 10.78 | 432,487 | 61,287 |
| C1-02-execcalibration | reserve / exec | 15.03 | 761,257 | 53,801 |
| C1-03-base3A | ledger / A | 12.47 | 4,292,640 | 167,456 |
| C1-04-orig | ledger / original | 10.58 | 3,858,303 | 224,895 |
| C1-05-base3B | ledger / B | 11.47 | 5,091,418 | 251,354 |
| C1-06-base3A | reserve / A | 22.75 | 11,186,514 | 184,146 |
| C1-07-base3B | reserve / B | 12.76 | 5,197,542 | 216,038 |
| C1-08-orig | ledger / original | 15.10 | 5,608,982 | 202,646 |
| C1-09-base3B | ledger / B | 15.02 | 5,474,794 | 192,234 |
| C1-10-base3A | ledger / A | 10.14 | 3,519,949 | 165,069 |
| C1-11-base3B | reserve / B | 20.12 | 11,618,548 | 285,172 |
| C1-12-base3A | reserve / A | 13.60 | 6,113,746 | 229,970 |
| C1-13-base3B | ledger / B | 12.53 | 4,856,440 | 196,216 |
| C1-14-base3A | ledger / A | 15.22 | 5,541,277 | 199,965 |
| C1-15-orig | ledger / original | 13.35 | 5,297,760 | 211,680 |
| C1-16-base3A | reserve / A | 14.59 | 7,427,526 | 265,414 |
| C1-17-base3B | reserve / B | 16.10 | 6,053,827 | 249,283 |
| C2-00-execcalibrationr | workflow / exec | 19.81 | 1,231,152 | 78,128 |
| C2-01-execcalibrationr | workflow / exec | 14.31 | 924,556 | 63,628 |
| C2-02-execcalibrationr | workflow / exec | 15.46 | 921,827 | 61,923 |

C1-06 mutation is missing because the runner's own-test baseline was not green; it is not imputed as zero. C1-11 reports 20/29 after one mutant timeout, not 20/30. C2 mutation scores were .7667/.9000/.9333, all with green baselines. These secondary diagnostics do not rescue a saturated primary endpoint or establish a new P0 ([mutation review](notebook/20261017-1340-a2-review-c1-mutation.md)).

## Sizing the sealed evaluation: sensitivity inputs, not a promised sample size

The independent [raw-data audit](data/final-noise-audit.json) and [methods notebook](notebook/20261017-1430-a3-final-noise-and-suite.md) supply a reproducible planning calculation. For a two-arm paired log-cost contrast with two-sided alpha=.05 and power=.80, the normal approximation is `N=ceil((2.801585*s/abs(log(1−r)))²)`, where s is the paired log SD and r is the target fractional cost reduction. N is **independent pairs/blocks**, requiring 2N run slots. These targets are planning examples chosen after the experiment, not preregistered effect tests.

| Pilot task | Endpoint | Paired log SD (3 blocks) | Pairs for 10% lower cost | Pairs for 20% lower cost |
|---|---|---:|---:|---:|
| ledger | active | .312076 | 69 | 16 |
| ledger | input | .286958 | 59 | 13 |
| ledger | uncached | .213865 | 33 | 8 |
| reserve | active | .497428 | 175 | 40 |
| reserve | input | .709067 | 356 | 80 |
| reserve | uncached | .147051 | 16 | 4 |

The calculation substitutes an n=3 sample SD into a known-variance normal formula: it is not exact small-sample t-test power, a guaranteed minimum, or a validated transfer to long tasks. No multiplicity correction is included. Under independent normal contrasts, an illustrative one-sided 95% upper SD bound is **4.4154 times** the estimated SD; using that bound multiplies unrounded N by **19.4957**. The 20% reduction stress counts become ledger **300/254/141** and reserve **761/1546/67** pairs for active/input/uncached. These are a sensitivity to uncertainty, not a proposed required budget.

The practical implication is to calibrate difficulty first, collect repeated blocks on admitted long tasks, select a minimum effect worth acting on and primary endpoint, and preregister a feasible sample-size rule with variance uncertainty and task heterogeneity. Three pairs cannot be assumed sufficient for the frozen 3.8–4.5% time predictions. C2's dependent within-block pairs cannot increase the independent pilot n. Score SD0 cannot size an unsaturated quality endpoint. For delivery, even an independent Bernoulli model gives a one-sided 95% failure-rate upper bound of .3930 after 0/6 failures and .6316 after 0/3; concurrent dependence makes that optimistic. Do not pool heterogeneous tasks to claim reliability.

## Validation

At phase-D starting revision `8f77689`, a different peer ran `.venv/bin/python -m pytest -q`: **39 passed in 11.29s**. The [validation notebook](notebook/20261017-1430-a3-final-noise-and-suite.md) records the command, result, and empty source/test diff from base3. Phase D changes research documents and analysis tooling; the tested runtime and regressions are unchanged. Independent artifact reviews accept the [final report](notebook/20261017-1438-a3-review-final-report.md), [NEXT priorities](notebook/20261017-1436-a2-review-next.md), [candidate/base pin/PR](notebook/20261017-1438-a1-review-candidate-pr.md), and [sizing arithmetic](notebook/20261017-1433-a2-review-final-sizing.md). The report review matched all 21 run rows and 63 cost/time cells to raw data; the sizing review reproduced 162 numeric checks. The [audit correction](notebook/20261017-1431-a3-noise-transcription-correction.md) fixes a notebook-only C2 input-SD transcription; this report uses the correct rounded 177,806.

## Budget and frozen outcome

Raw C1+C2 spending was **21 jobs, 95,707,328 total input, 3,594,304 uncached input, and 895,861 output tokens**. Input plus output was 96,603,189 tokens; the budget is defined on input only. The exact unused budget is **15 jobs and 354,292,672 input tokens**, consistent with the scheduler's rounded 95.7M used. Earlier C-DONE prose also retains a prospective estimate of 348,370,207 remaining; that estimate is not actual spending and does not override raw arithmetic.

The null candidate freezes this round's decision, with no mechanism trial or default peer-count change. The unspent budget does not make the missing measurements positive or negative findings. Further experimentation belongs to a separately registered round after tasks actually meet the duration and score admission gates.
