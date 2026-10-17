# Independent red-team of the Phase-B hypotheses

- Question: Which alternative explanations could produce each proposed H1–H6 result, and what would distinguish prediction failure from mechanism evidence?
- Method: a3 independently critiqued a1's H1–H6 before C1 execution, inspected the frozen-task metadata, historical index and run-accounting implementation, and reviewed the actual solo/peer setup and prompts. Numerical anchors were separately reproduced in `20261017-0816-a3-c1-design-review.md`. This is adversarial review of priors, not new experimental data.
- Prediction: C1 should be able to reject badly centered forecasts and expose saturation or large variability. It will not identify a unique coordination mechanism, establish rare-failure safety, or precisely estimate all scaling parameters.
- Raw-data paths: `research/data/index.csv`, `research/GATES.md`, `research/tasks/*/TASK.json`, `src/murmur/cli.py`, `src/murmur/prompts/peer.md`; read-only `/workspace/self3/lab/runner2.py`, `/workspace/self3/sched/scheduler.py`, `/workspace/codex-src-0.162.1`.

## H1: Repeated-run variability

**Alternative explanation.** Large observed CV or score SD can reflect provider congestion, different rate-limit exposure, shared block contention, ceiling/floor effects, or task-specific implementation cliffs. It need not show intrinsic model randomness or instability of the peer protocol. Conversely, concurrent A/A arms share shocks and can yield small paired differences despite substantial variation across blocks. Two base3 runs in a block are not independent draws of the environment.

**Discriminator and requested limit.** Report each task's six observations, pooled SD/CV, three within-block A-minus-B differences, block means, and rate-limit/cap indicators. Compare paired and across-block variability descriptively, without claiming variance components are precisely identified. Six per-task replicates do not turn the historical n=1 cells into replicates. A statistic outside the preregistered working range challenges the prior; sampling uncertainty still limits conclusions about the population parameter. Across several metrics/tasks, at least one range miss is not a corrected omnibus rejection.

## H2: Bug-fix base does not materially regress

**Alternative explanation.** Base3 may change delivery because its integration receipt prompt changes behavior, while retry/wait/catalog fixes act on rare operational conditions. A better run can therefore result from different strategy, common block load, or luck; a null comparison can occur simply because no relevant failure was triggered. The base3-versus-orig contrast evaluates a bundle, not attribution to each patch.

**Discriminator and requested limit.** Use only the three predesignated base3-A/orig pairs and retain every delivery failure and timeout. A/B runs may describe noise but must not double the treatment-comparison sample size. Record score differences and resource log ratios, with gross-regression and inconclusive categories. Three pairs provide only eight sign assignments: the minimum two-sided exact sign-flip p-value is 0.25. Even zero failures among three runs has probability `(1-p)^3`, which remains 0.729 if the true failure probability is 0.10; it cannot establish rare-failure safety. Existing runnable bug reproducers are distinct evidence and do not replace this practical comparison. No significant difference is not equivalence.

## H3: Absolute C1 forecast validation

**Alternative explanation.** A forecast miss can result from incorrect task-size or coupling elicitation, graders with correlated cases, a cap truncating difficult runs, or a ceiling task—not the chosen scalability functional form. An apparent hit within very broad bands can be uninformative. One exec calibration cannot estimate task difficulty precisely, and its realized time is not an independent repeated estimate of latent solo work.

**Discriminator and requested limit.** Freeze all point forecasts and bands before calibration; retain their original values even after observing the exec run. Report absolute errors and interval coverage per endpoint/task as well as the preregistered failure screen. Call the nominal 80% bands elicited and uncalibrated. Comparing a six-run task mean with a per-run band is a conservative screen, not an 80% confidence test for the mean. Drop a task from the prescribed score inference only when its calibration score exceeds 0.95; retain its raw data and diagnostic resource results. Do not replace it post hoc or tune hidden tests. If both A/A tasks saturate, acknowledge that the quality test is unavailable and select a future design under a new registration.

## H4: Repeated context dominates input cost

**Alternative explanation.** A low uncached/input ratio can arise from efficient provider prefix caching, long useful code context, repeated whole-history billing, or accounting across forked sessions. It need not imply avoidable board overhead. A higher ratio can reflect cache eviction, compaction boundaries, cold sessions or provider reporting, without worse collaboration. The byte size of board output is not a token attribution measure.

**Discriminator and requested limit.** Report total input, uncached input and output separately; retain U/I only when input is positive and usage is observed. State whether final cumulative counters reset or are missing and audit suspicious values from retained sessions before interpreting them. The runner reads the last token-count totals from each session and sums them (`/workspace/self3/lab/runner2.py:78–90`); it does not isolate coordination-generated tokens. Model failure at the ratio endpoint challenges a cost prior, not a causal waste claim. Attribution needs a future controlled intervention and cannot be inferred from this descriptive ratio.

## H5: One-peer protocol versus solo isolates a protocol penalty

**Alternative explanation.** The contrast changes an entire workflow: root/fork history, tool availability, prompt length, board access, draft/self-ranking instructions and integration requirements. A one-peer draft/rank protocol may be an unusual corner case. A difference does not specifically prove that the message board, independent exploration or any individual prompt rule is harmful.

**Discriminator and requested limit.** Treat base3 murmur-solo versus base3 one-peer protocol as the practical bundled protocol effect. The source switches IDs and root creation at `src/murmur/cli.py:625–642,684–704`, and solo disables multi-agent tools at `:162–167`; the peer draft/rank requirement is `src/murmur/prompts/peer.md:22–37`. Plain exec differs further: the runner auto-commits its uncommitted work (`/workspace/self3/lab/runner2.py:118–120`), starts its wall timer after setup (`:111–117`), and enforces a strict cap (`:115`), while murmur wall includes setup and allows an outer cap+10 timeout (`:139–148`). Use active time as the declared primary time endpoint and report these practical bundle differences. Do not rewrite the runner or introduce another mechanism in response to this review. C1 lacks the repeated arms to test H5; C2 must preregister the exact contrasts.

## H6: Two peers are faster and cheaper than three on the long task

**Alternative explanation.** A third peer can change the selected draft and the algorithmic approach, yielding a discrete quality/time jump unrelated to a smooth coordination penalty. Apparent superlinear cost can instead reflect longer retained contexts, duplicated exploration, or shared backend contention. Coupling and serial fraction chosen from a task description are not independently measured variables. Many parameter sets can interpolate a three-count curve.

**Discriminator and requested limit.** Keep all murmur arms on base3 and compare n=1,2,3 at matched caps in prospective blocks. Report delivered score alongside time and both cost counters; faster low-quality termination is not a speed win. Record draft, merge, waiting and rate-limit indicators as explanatory observations, not validated mediators. With one long task and three repetitions per arm, fit only an explicitly constrained simple curve, show all run values and uncertainty, and resist claiming a universal optimal count. A default change requires acceptable delivery/quality plus a reproducible useful time/token tradeoff, not merely that the prior predicts n=2 fastest. Any mechanism proposal still needs its own controlled evidence.

## Cross-cutting assessment and decision

The historical mean judge gap of -0.652083375 points is not a hidden-test percentage-point effect. Task cases are correlated; the run, not the test case or judge pass, is the experimental unit. Capped work is retained, and missing telemetry or scoring failures are not zero-cost successes. Mutation score is secondary and can be missing when a deliverable's suite is not green, so conditionally observed mutation scores must not silently replace unconditional delivered quality.

This red-team supports the noise-first C1 allocation and deferral of H5/H6 to C2. Its requested changes are limitations, explicit analysis branches and narrower interpretations, not untested product changes. Final MODEL/C1 consistency checks will be recorded in a separate append-only review entry once the artifacts are available.
