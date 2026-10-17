# murmur research program — advisor memo

Status: complete. Date: 2026-10-17.
- Sources: files under /workspace, read-only.
- New analyses: scripts in /workspace/advisor/analysis/, all re-runnable with `python3 -I <script>`.
- Every number cites its file. Inferences and external literature (not verified on this box) are marked as such.

## 0. Executive summary
1. **Rounds 1–2 failed for structural reasons, not effort.**
   - The peers could not run murmur experiments at all (sandbox socket masking).
   - murmur's peer protocol is a product-building protocol: draft → rank by looking → "finish when nothing is worth fixing". It ends research runs after ~26–29 min and rewards small, safe diffs.
   - Round 2 was built on a broken base (658d82a: nothing merged on W2).
   - Round 2's evaluation could not accept anything: n = 1, judge sd ≈ 0.63, saturated hidden tests, and a token gate the baseline itself fails 2.5–7.5×.
2. **The box data does not support "1.6–1.8× faster at near-solo quality" for the tasks being used.**
   - Across 16 swarm-vs-solo pairs: quality **−0.65** (90% CI −0.95…−0.35; worse in 12/16), speed **1.18×** (geometric mean), input **5.3×**.
   - The premise comes from 2 n = 1 trials on PR #1 with 57–67 min solo runs. Speedup grows with task length (r = 0.53).
   - The quality gap is mainly the risk dimension (P0/P1, 44%) and PR.md honesty (24%).
3. **Round-3 design: the right direction, but it will almost surely end in "no KEEP" whatever the truth is.**
   - Simulated power: P(KEEP | true +0.5 quality) ≈ 0.19–0.49. The efficiency path gives ≈ 0.06–0.14 for a true −25% tokens. An identical base3 fails the per-task speed gate about half the time.
   - The bootstrap with 3 runs per stratum is anti-conservative.
   - Sealed tasks planned under /workspace/self3 are readable by the peers: the Codex sandbox reads the whole disk, and that path is whitelisted in the lab runner.
   - Nothing keeps the peers working for 10–15 h.
4. **Priorities:**
   - (i) Leakage fix, phase driver, deterministic instruments (graded hidden tests, reproducer-confirmed P0, mutation score), pooled and paired decision rules.
   - (ii) Round 3 as a *measurement* round: A/A calibration, protocol-vs-parallelism, peer-count dose-response on long tasks.
   - (iii) Mechanisms that use parallelism for **independent verification** rather than dividing up the typing: M1 clean-room verifier with a mechanically enforced oracle; M2 test-arbitrated speculation with differential testing; M3 elastic peer activation for tokens; M4 claims-checked PR.md.
5. **Open decisions:**
   - Round 3 is the foundation round, plus ≤ 2 mechanism rounds, with an evidence-of-absence stop rule.
   - About 0.75B input per round, ≈ 2.3B program cap.
   - Write sealed tasks *after* the candidate is frozen, from a specification and seeded selection procedure registered now.
   - Yes to an efficiency path, but redesigned (pooled, CI-based, sized n), and open to parameter findings.

## (a) Why rounds 1-2 failed — root causes

The round-3 brief says rounds 1–2 failed because "research effort was shallow" (/workspace/self3/brief.md §0). That's true, but it's the symptom. I see five structural causes. Fixing effort alone won't fix any of them.

**RC1. The peers could not run an experiment, even if they had wanted to.** Nested `murmur run` inside a Codex sandbox fails ("app-server socket directory must be a user-owned directory with mode 0700"; /workspace/self2/REPORT.md, bug 6). The Codex Linux sandbox masks `/tmp/codex-daemon-$UID` on purpose (/workspace/self3/brief.md §5, citing codex-rs/uds/src/daemon_directory.rs and linux-sandbox/src/bwrap.rs). In round 2, "Live screens all failed" and the shortlist a1/a2/a5 was chosen without any run (/workspace/self2/LOG.md 12:21). Round 1's PR says plainly: "No paid/live performance experiment was run" (/workspace/self/ws/self6p/work/peers/a1/PR.md:146). Under that constraint, "no experimental evidence" was the only possible outcome. The round-3 lab runner (/workspace/self3/lab/runner.py) is the right fix, and it's the single most important change since round 2.

**RC2. The murmur peer protocol is a product-building protocol, and it was used to run research.** /workspace/murmur/src/murmur/prompts/peer.md prescribes: explore, then draft for about $draft minutes, then "choose by looking" and rank drafts, then integrate, then review, then "Finish only when a review of the latest `main` finds nothing worth fixing." Three consequences:
- *Termination.* Both research runs ended within half an hour of a 24 h cap. Round 1 ran 10:40→11:06 (/workspace/explore/LOG.md, last two lines; /workspace/self/mon.log). Round-2 phase 1 took 28.6 min (/workspace/self2/LOG.md 12:21). The protocol's stopping rule ("nothing worth fixing on main") is met as soon as a coherent diff exists. It has no notion of "the hypothesis is still untested".
- *Selection pressure toward small, safe diffs.* Ranking drafts by inspection rewards the lowest-risk, easiest-to-verify diff. Round 1 deferred every collaboration mechanism ("receipts: defer … gains remain unmeasured", PR.md:38–40), and the round-2 brief notes that "the draft vote favoured the smallest, lowest-risk diff" (/workspace/self2/brief.md, "Why round 2 exists").
- *Cost without depth.* Round 1 used 6 peers for ~26 min and ~24.5M input tokens (/workspace/advisor/CONTEXT.md) on work that was mostly surveying.

**RC3. Round 2 was evaluated on a contaminated base.** The prototypes were built on round-1's 658d82a, not on the protected eec78f8. 658d82a delivered nothing on W2 (quality 1.1, 0 commits), and so did a2 (1.4). a1 and a5 on the same base did integrate (/workspace/self2/REPORT.md "W2 zero-commit"). 658d82a changed the root prompt (`fork_turns: "none"`, `wait_agent` with no ids) and also removed the catalog `multi_agent_reasoning_effort` pin (diff of /workspace/self2/arms/{eec78f8,658d82a}/src/src/murmur). I checked the effort pin: in Codex 0.162.1 it only changes how `Ultra` resolves (codex-rs/protocol/src/openai_models/reasoning_effort.rs:10–35). It's therefore probably *not* a confound at `--effort high`. The root-prompt change remains an untested suspect, as REPORT.md says. Separately, the gates in eval-plan.md compared prototypes to this broken base (mean 5.73), so "beat base" and "beat the user's baseline" were different questions.

**RC4. The round-2 evaluation could not detect any plausible effect, and one gate was infeasible before the first run.**
- *n = 1 per arm.* Judge noise alone is large. Recomputed from the final judge outputs (/workspace/advisor/analysis/judge_noise2.py, which supersedes judge_noise.py; that script reads a stale `scores.json` in which W1|orig, W2|orig, W2|a2 and W2|a5 lack passes): over 18 artifacts the two blind passes differ by mean |A−B| = 1.09 points (sd 1.26, max 2.4). That implies a two-pass-mean judge sd of about **0.63** quality points, before any run-to-run variance. The decision rule was a +0.3 margin.
- *Most of the judge noise sits in one dimension.* The adversarial "risk" score (10 − 2·P0 − P1) has a between-pass sd of 4.07 on a 0–10 scale (design: 0.58). The same W3-a5 artifact got P0 = 5 from one pass and 0 from the other.
- *Hidden tests are saturated.* Every delivered arm passed 100% (W1 14/14, W2 16/16, W3 38/38; REPORT.md table). The only deterministic signal therefore carried zero information between delivered arms.
- *The "≤ 2× solo input" gate was infeasible.* Every 3-peer arm, orig included, was 2.5–7.5× solo (REPORT.md), and that was already known: val base3 6.5×/4.7× (/workspace/val/RESULTS.md), big3 4.8× (/workspace/explore/LOG.md 20:18). A pre-registered gate that the protected baseline fails by more than 2× guarantees REJECT.
- *Infrastructure noise.* Six arms ran concurrently and hit HTTP 429s (W1-a1 and W1-a5 died, W2-a2 logged 6–16 retries per session). Three harness bugs were fixed mid-eval (/workspace/self2/LOG.md 13:29, 15:46, 17:24). These were handled honestly, but each is a source of arm-specific noise.

**RC5. The mechanisms aimed at a minority failure mode, using prompt-shaped levers.** The brief steered peers toward seam mechanisms (/workspace/self2/brief.md §1). From REPORT.md:
- Seam-attributed P0s are about 31% of swarm P0s: 5.5 of 18.0 summed over the 13 delivered swarm runs.
- Swarm P0 per run is 1.38 vs solo's 0.5.
- The non-seam excess (≈0.96 − 0.5 = 0.46 per run) is about as large as the seam share (0.42 per run).

The prototypes a1 (integration barrier), a2 (cross-review) and a5 (contracts) are close relatives of interventions that had already failed as prompt rules (M1–M3 on T1–T3, /workspace/explore/LOG.md "Large-task integration-quality results": mean +0.2, FAIL). Their round-2 means of 7.30 / 5.53 / 7.47 vs orig 7.33 are within one judge-sd of null.

**Bottom line for (a).** Round 1 failed because its brief did not require evidence and the environment could not produce any. Round 2 failed because (i) it still could not run experiments, (ii) it was built on a broken base, and (iii) its evaluation could not have accepted anything. None of this shows that the peers are bad researchers. It shows that the *system around them* made research impossible and acceptance unreachable.



## (b) Is a swarm of peers the right lever? What the data supports

### b1. The pooled data (all large-task swarm vs solo pairs on the box)
/workspace/advisor/analysis/swarm_vs_solo.py pools 16 pairs: tinydb A, L1, L2, T1–T3, U1, U2, V1, V2, val W1/W2, big3, and round-2 W1–W3. In each pair the swarm is the *then-current main or orig* with 3 peers, so these are not prototypes. Sources are cited per row in the script.

| quantity | value |
|---|---|
| quality, swarm − solo | mean **−0.65**, 90% bootstrap CI **[−0.95, −0.35]**; swarm better in 2, tied in 2, worse in 12; sign test p = 0.013 |
| speedup (solo min / swarm min) | geometric mean **1.18×**, median 1.12×, range 0.93–1.54× |
| input tokens, swarm / solo | geometric mean **5.3×**, range 3.7–10.0× |
| corr(solo duration, speedup) | r = 0.53; solo < 30 min: 1.13×, 30–40 min: 1.22×, > 40 min: 1.37× (n = 8 / 6 / 2) |

Caveats:
- murmur main changed across these evals: batch-1 main, pre-PR#4 main, big3 = feat/folder-input@90d8501, round 2 = eec78f8.
- Rubrics and judge counts differ; the earlier evals used 1 judge pass.
- Some solo times are wall time, not active time (marked "~" in /workspace/explore/LOG.md and /workspace/val/RESULTS.md). That biases speedup *upward* for the swarm.
- Judges are the same model family as the agents (/workspace/self2/tasks/SCORING.md: gpt-6-astra high).
- Swarm vs solo is probably *not* truly blind. peer.md requires PR.md to "Record the drafts, the rankings…", and the git authors are a1..a3. Judges can tell a swarm artifact from a solo one.

Even with these caveats, the direction is consistent across 12 of 16 tasks.

### b2. The "1.6–1.8× faster at near-solo quality" premise
That claim comes from trials 2 and 3 (/workspace/murmur-trial3/COMPARISON.md "Cross-experiment"):
- 1.6× (41.4 vs 67.3 min; quality 7.5/7.5) and 1.76× (32.1 vs 56.6 min; 8.4/8.5).
- Both used murmur **PR #1 @94a733e, not eec78f8**, n = 1 each, single judge.
- In trial 2 the solo hit the 60-min cap with 6 relay stream timeouts and had to be resumed (/workspace/murmur-trial2/COMPARISON.md). That solo run was handicapped.

The README pilot shows 2.6× with "solo slightly better", also n = 1. So the premise holds only for **long tasks (solo ≥ 55 min)**, with n = 2–3, on an older version. On the 20–60 min tasks the program has used since, eec78f8-era swarms are about 1.2× faster and about 0.65 points worse. **The user should know that the baseline they are protecting is weaker on box data than the premise states.** This matters because round 3's sealed tasks are specified at "expected solo duration 25–45 min" (/workspace/self3/eval-rules.md, "Tasks"). That is precisely the regime where the swarm's speed advantage is smallest (~1.1–1.2×) and where any mechanism's overhead turns into a "slower" verdict.

### b3. Where the quality gap comes from
From /workspace/advisor/analysis/dims.py (12 tasks with per-dimension scores):

| dimension | swarm − solo | share of gap | swarm worse in |
|---|---|---|---|
| risk (adversarial P0/P1) | **−2.04** | **44%** | 8/12 |
| PR.md honesty | **−1.12** (round 2 alone: −2.50) | 24% | 8/12 |
| correctness | −0.79 | 17% | 6/12 |
| regressions | −0.38 | 8% | 2/12 |
| design | −0.29 | 6% | 4/12 |

So the gap is mostly **(i) more serious defects on the main path and (ii) a less accurate PR.md**. It is not design or feature completeness. The risk dimension is also the noisiest one (a1), so this attribution is less certain than its pooled consistency suggests. Note also that ~31% of swarm P0s are seam-attributed (a, RC5). The other ~69% sit in single-author code, which matches the earlier blame finding that "every swarm P0 on L1/L2 sits in a file written by one peer only" (/workspace/explore/LOG.md, "why swarm quality drops", C1).

### b4. Is the swarm the right lever?
**For wall-clock speed on long, decomposable tasks: plausibly yes. For quality: no evidence, as currently built. For tokens: it is the main cost driver.**
- **Speed.** Speedup grows with task length (r = 0.53 here; also the LOG.md "Side question"). It is real but small below 40 solo-minutes.
- **Quality.** No eval on the box shows swarm quality above solo by more than judge noise; the two wins are +0.40 (val W1) and +0.66 (big3), both n = 1. Peers are the *same model with the same brief* (peer.md says so itself), so their errors are correlated. Splitting work fragments the context each author holds. Neither ingredient for an ensemble quality gain (independent errors plus a reliable selector) is present. The protocol's only selector is "rank drafts by looking", which is an LLM-judged vote and not an executable oracle.
- **Tokens.** These scale with peer count × calls. The swarm makes 4–6× the model calls at a similar context per call; shell output is 77–82% of input; git coordination is 41–45% of swarm input (/workspace/explore/LOG.md "Token-lean phase"). Peer count was the only lever that moved tokens a lot: lean2 (2 peers) reached 1.1–2.5× solo input on V1/V2. It failed validation on quality and uncached tokens (/workspace/val/RESULTS.md: lean2 W2 −1.0, uncached 4.4–4.6×).

**What is untested and should be tested first** (cheap, high-information experiments):
1. **Is the quality loss caused by parallelism or by murmur's protocol?** Every "solo" arm was plain `codex exec` with a different prompt (/workspace/self2/eval/run_task.sh). No eval on the box separates the two:
- *Plain solo vs murmur `--solo`.* `murmur --solo` gives the agent brief + closing.md + solo.md, with the same PR.md and "aim for the best result" framing as swarm peers but without peer.md (/workspace/murmur/src/murmur/cli.py:666–681). This arm separates "harness/closing prompt" from "plain codex exec". The lab runner already supports `"peers":"solo"` (/workspace/self3/lab/runner.py:68).
- *Peer protocol with no parallelism.* This needs an internal switch (e.g. `MURMUR_*`) that renders peer.md with n = 1 (draft, rank-by-looking and PR-bookkeeping steps intact). If it also loses ~0.65, the protocol is the culprit, not parallelism.
2. **Peer-count dose-response at 1/2/3 peers on long tasks.** This fits a Universal Scalability Law curve and says whether a third peer buys any speed. The existing hints are inconclusive and confounded with G1–G3: lean3 vs lean2 shows similar time at 3 vs 2 peers (V1 15.4 vs 16.9; V2 22.0 vs 22.1).
3. **Task length as a design variable.** Run eval tasks of 45–90 solo-minutes, where the swarm can actually show value.

My recommendation: keep the swarm as the *speed* lever. Stop expecting more peers or more coordination rules to buy *quality*. Use parallel capacity explicitly for **independent verification and test-arbitrated alternatives** (d, M1–M2), because those are the mechanisms with a theoretical route to quality above solo.



## (c) Critique of the round-3 design

What the draft gets right, and should keep:
- the restart from eec78f8;
- bug fixes with failing-first regression tests before any measurement;
- the lab runner, which respects the sandbox instead of bypassing it;
- an append-only notebook, predictions written before data, null results logged;
- one candidate per round;
- a token gate relative to the reference instead of the infeasible "≤ 2× solo".

These are real improvements over round 2. The problems below are ordered by severity.

### c1. Research protocol

1. **Nothing in the design keeps the round alive for 10–15 h. (Critical.)** The brief is appended to the *same* peer.md/closing.md, whose stopping rule is "Finish only when a review of the latest `main` finds nothing worth fixing" (peer.md, last paragraph). The root ends when `list_agents` shows nothing running (root.md step 3). Both previous research runs stopped after ~26–29 min (a, RC2). Phases A→D with ~40 lab runs at 15–45 min each cannot fit in one convergence cycle of peer.md. The draft also brings back peer.md's draft/rank step, which caused RC2's bias toward small diffs. **Fix:** run each phase (A, B, C-batch k, D) as its *own* bounded `murmur run` with a phase-specific brief. A deterministic gate script then checks the artifacts (index.csv exists and reproduces; each notebook entry has a prediction timestamped before its lab job's start; and so on) and launches the next phase. This is a scheduler, not an outer researcher, so it respects the user's rule that the peers do the research. For research runs, also disable or replace peer.md's draft/rank step (research claims are ranked by data, not by "looking").
2. **The lab budget cannot support the protocol as written.** "≤ ~40 lab runs", "≥ 3 reps per arm", "≥ 2 screening tasks", "one variable at a time" (brief §2C), plus the base3-vs-eec78f8 non-inferiority check with ≥ 3 reps (brief §3). That check alone takes ≥ 6 runs, and 12 if done on both tasks. What's left is about 28 runs ≈ 4 two-arm experiments on one task, or 2 on two tasks. At n = 3 and the noise levels in c3, each of these can only detect effects of about 1 sd or more. **Fix:** use process metrics with low noise and a clear mechanistic link as the *screening* endpoints, not LLM-judged quality. Examples: deterministic graded-test pass rate, a mutation score for the produced tests, idle-time fraction, time to first green main, P0s confirmed by an executable reproducer. Use sequential designs (stop early when the effect is obvious) and pair arms within concurrent blocks.
3. **There is no quality instrument inside the round.** The lab returns time and tokens (/workspace/self3/lab/runner.py `tokens(ws)`) but no quality. If peers judge their own experiments, the round is self-grading. **Fix:** ship a judge-free scorer with the lab: a hidden graded acceptance suite per screening task, written in Phase A *before* any mechanism is designed and frozen by hash, plus a mutation-testing pass over the produced tests. Optionally add an operator-side judge job type, with the judge model held fixed.
4. **Self-made screening tasks invite designer bias.** Peers who already have a favorite mechanism can write tasks that favor it. **Fix:** freeze the screening tasks and their tests at the end of Phase A, with a second peer's review, before Phase B produces any hypothesis.
5. **"Parameter-only changes don't count" conflicts with the data.** The one lever with a large measured token effect is peer count (b4). The brief allows it only as a "controlled variable". **Fix:** let parameter findings reach the base through the efficiency path (e5), recorded as *findings*. They then don't consume the round's "one mechanism" slot.
6. **Phase B's "fit the model, report fit error" gate is too strong for the data.** Phase-A data is n = 1 per heterogeneous condition, from evolving murmur versions and different rubrics (b1 caveats). A USL/Amdahl fit will be underdetermined. Treat Phase B as hypothesis generation with explicit priors; don't gate on fit quality. Require *out-of-sample* prediction of the first Phase-C result instead. That is the honest test of a model.
7. **Lab concurrency vs rate limits.** 3 concurrent lab jobs × (3 peers + root), plus the 6 research peers themselves, is ~18 sessions. Round 2's 429 deaths happened at a similar scale (/workspace/self2/LOG.md 13:15, 13:43). Rate-limit retries inflate time unevenly across arms. **Fix:** pair arms inside each concurrent block (as eval-rules does) and log the 429 count per run as a covariate. The runner should requeue (not count) runs that die of infrastructure errors in *both* arms of a block.
8. **The lab's own smoke test shows the hang bug.** /workspace/self3/lab/nested-test.out reports `run_exit: 124`, `wall_min: 10.06`, `active_min: 4.43` for a 10-min cap. The run likely sat idle until the cap after the peers finished, consistent with root-hang bug #3 (inference, not verified from the ws logs). Until bug #3 is fixed, every lab run wastes wall time up to its cap and caps lab throughput. That's one more reason to fix bugs first.

### c2. Eval rules (/workspace/self3/eval-rules.md)

1. **The gates are a conjunction of about 10 noisy per-task tests, so power is poor.** /workspace/advisor/analysis/power_r3.py simulates the rules as written: 3 tasks × 3 reps, stratified bootstrap, noise taken from round 2.

   | true effect | quality sd 0.6, time CV 0.08 | quality sd 0.8, time CV 0.16 |
   |---|---|---|
   | none (A/A) — P(KEEP) | 0.08 | 0.05 |
   | +0.5 quality — P(KEEP) | 0.49 | 0.19 |
   | +1.0 quality — P(KEEP) | 0.75 | 0.35 |
   | +0.5 quality with +5% time and +15% tokens | 0.16 | 0.06 |
   | −25% tokens, no other change — P(efficiency KEEP) | **0.14** | **0.06** |
   | A/A: fails the "≤ 1.10× time on every task" gate | 0.22 | 0.53 |
   | A/A: fails the "no task < −0.5 quality" gate | 0.41 | 0.55 |

   Round 2's between-arm spreads put time CV at 0.08 (W3) to 0.32 (W2). The right column is therefore probably the realistic one, or even optimistic.
   - A **truly identical** base3 fails Step 1 (non-inferiority to orig) on speed alone about half the time.
   - A mechanism with a +0.5 quality gain is larger than anything the program has measured, and it still gets kept only 1 time in 5.
   - The efficiency path is nearly unreachable. A true −25% token saving yields an expected observed ratio of 0.75, so "≤ 0.80× on *every* task" fails about a third of the time per task, *and* the per-task quality and speed guards each fail roughly half the time under the null.
   - The model omits task × arm interaction and non-delivery, so real power is lower still.
2. **A stratified bootstrap with 3 runs per stratum is anti-conservative.** The resampled variance is biased by (n−1)/n = 2/3, so the CIs come out roughly 18% too narrow, and with only 3 values the bootstrap distribution is lumpy. Use a t-interval on block-paired differences, or an exact permutation test over the 3 blocks × 3 tasks. Better still, a pre-registered mixed model (task fixed, block random).
3. **Scoring non-delivery as quality 0 mixes reliability into the quality mean.** One zero among 9 runs moves the arm mean by about 0.8. A single 429 death or root hang in orig (still unfixed in orig) can decide Step 1 on its own. **Fix:** make delivery rate a separate primary reliability endpoint (as Step 2 item 4 partly does). Compute quality on delivered runs, and keep a pre-registered joint rule.
4. **Judging is the weakest link.**
   - The two-pass-mean judge sd is ≈ 0.63 (a, RC4). The risk dimension alone has a between-pass sd of 4.07.
   - Judges are the same model family as the agents.
   - Swarm artifacts carry identifying features: peer ids in git authors, draft/ranking sections in PR.md.
   - A candidate's artifacts (receipts, board notes) can unblind cand vs base3.

   **Fix:**
   - (i) Count a P0 only if the judge supplies an executable reproducer that the harness runs on the artifact. That turns the noisiest dimension into a deterministic one.
   - (ii) Use graded hidden tests designed *not* to saturate; round 2's were 100% for every delivered arm. Target a solo pass rate of ~60–85% on a held-out reference build.
   - (iii) Scrub artifacts before judging: normalize git authors; strip `.work/`, draft branches and murmur-specific PR.md sections; give solo and swarm the same PR.md template.
   - (iv) Use ≥ 3 passes, ideally from 2 model families, and pre-register their aggregation.
5. **Three tasks is too few to generalize.** Variance of the mean effect = σ²_run/(T·n) + σ²_task×arm/T. When the task × arm interaction is non-trivial (round 2: a5 vs orig was +1.0 on W1, −0.4 on W2 and −0.2 on W3, n = 1), more tasks with fewer reps beat 3 × 3. Same 27 swarm runs: **5–6 tasks × 2 reps** (or 9 × 1 with blocking) gives a better estimate of the effect *across tasks* and makes "no task worse than −0.5" meaningful. Per-task gates then become catastrophe guards (e.g. no task worse than −1.0 quality or slower than 1.25×), not tests.
6. **The task-length mismatch.** "Expected solo duration 25–45 min" is the regime where the swarm's measured speedup is 1.1–1.2× (b1). Any mechanism that adds coordination work will look "slower". If the user's target is large tasks, specify **45–90 solo-minutes** and raise the cap accordingly. That's also where the baseline premise (1.6–1.8×) was observed.
7. **The token gate is fine** (≤ 1.25× the reference), and so is reporting the solo ratio. Pre-register *uncached* input as a co-primary token metric. It is what costs money and it has behaved differently from total input (val: lean2 cut total input to 3.5× but uncached was 4.4×; /workspace/val/RESULTS.md).

### c3. Statistics: noise and the minimum detectable effect
- **Quality.** Judge-only noise ≈ 0.63 (two-pass mean). Run-to-run noise is *unmeasured*: no on-box condition has ever been replicated. The upper bound from between-arm spread is 0.22–0.66 by task (power_r3.py header).
- **MDE** (two-sided α = 0.10, power 0.8) for an overall difference over 9 vs 9 runs is ≈ 2.49·σ·√(2/9). That's ≈ 0.70 at σ = 0.6 and ≈ 0.94 at σ = 0.8. The largest non-catastrophic between-arm difference ever seen on one task is 1.8 (W1 base vs orig, n = 1). Typical mechanism effects have been ±0.1–0.5. **So n = 3 cannot resolve the effect sizes this program is chasing.**
- **The first thing round 3 should buy is an A/A calibration:** eec78f8 vs eec78f8, 3–4 reps on 2 lab tasks. It measures σ_run for quality, time, input and uncached; sets honest margins and n for the sealed eval; and costs ~6–8 lab runs. The brief's own "bug-fix base not worse than eec78f8" check (§3) can double as this if it is designed as a paired A/A-plus-delta experiment.

### c4. Hidden-task leakage
- Codex's workspace-write sandbox **can read the entire disk**. `SandboxPolicy::has_full_disk_read_access` returns `true` for every policy (/workspace/codex-src-0.162.1/codex-rs/protocol/src/protocol.rs:1225–1240; the comment reads "a policy that can read the entire disk, but can only write to the current working directory"). Anything the peers' uid can read, they can read.
- eval-rules.md plans to store sealed tasks at **/workspace/self3/sealed/**. That path is (i) readable by the peers and (ii) under the lab runner's default `ALLOWED_ROOTS = /tmp/murmur-lab:/workspace/self3` (runner.py:21). A peer could even submit a sealed brief as a lab job's `brief`. eval-rules.md itself currently sits at /workspace/self3/eval-rules.md, inside that same whitelisted root. The brief also points peers at /workspace/self3 as a place to push repos for the runner (brief §5).
- Phase A directs peers to read /workspace/self2 in full, which includes /workspace/self2/tasks/rubric.txt and adversarial.txt, the judge prompts. If round 3 reuses those prompts, peers can optimize to the judge (Goodhart). This matters most for the PR.md-honesty and design dimensions.
- **Fix:** see (e) "When to write sealed tasks". In short: write them *after* the candidate is frozen, with the task specification and selection procedure pre-registered now. Also change the round-3 judge prompts from round 2's, or accept, and say openly, that the rubric is public.

### c5. Cost
- **Research run.** The estimate is "~10–15 h, 500–650M input" (/workspace/advisor/CONTEXT.md). The lab dominates: 40 runs × ~12M ≈ 480M (round-2 swarm runs were 7–18M each, /workspace/self2/REPORT.md). The research peers' own sessions come on top: round 1 used 24.5M for 26 min of 6 peers, so 10–15 h of 6 peers is plausibly another 100–300M if they stay active (an extrapolation, uncertain).
- **Sealed eval.** ~350M input plus ~10M for judges, 7–9 h (eval-rules.md "Cost estimate").
- **Per round:** ≈ **0.85–1.0B input tokens (≈ 95% cached), ~20–24 h wall.** With the power numbers in c2, the expected yield of one round as designed is low: P(KEEP | a real +0.5 effect) ≈ 0.2–0.5, and no mechanism so far has shown a real +0.5. **The cost-effective move is to spend the first round mainly on measurement (A/A, dose-response, protocol-vs-parallelism) rather than on a candidate.**



## (d) Prioritized changes and innovative mechanism directions

### d1. Before launching round 3 (blocking; operator-side, cheap)
1. **Close the leakage paths** (c4). Don't put sealed material on the box until the candidate is frozen. Remove /workspace/self3 from the runner's `ALLOWED_ROOTS` (keep a dedicated /tmp/murmur-lab/repos). Decide openly whether judge prompts are public.
2. **Add a phase driver** (c1.1). Each phase is a separate bounded `murmur run` with its own brief. A deterministic gate script checks the artifacts between phases. For research runs, disable peer.md's draft/rank step via an internal setting.
3. **Upgrade measurement** (c2.4):
   - graded, non-saturating hidden tests;
   - P0 counted only with a harness-executed reproducer;
   - artifact scrubbing before judging;
   - ≥ 3 judge passes, with the aggregation pre-registered;
   - a mutation score of the delivered test suite as a deterministic quality covariate.
4. **Rewrite the decision rules** (c2):
   - Primary endpoints are pooled across tasks: quality on delivered runs, delivery rate, geometric-mean active-time ratio, uncached and total input ratio.
   - Analysis is paired by concurrent block (t-interval or permutation, not a 3-sample bootstrap).
   - Per-task rules become catastrophe guards only.
   - n and margins are set from the A/A calibration (d2.1) and written into the sealed rules before the eval runs. Writing them after calibration but before any candidate eval is still pre-registration.
5. **Bug fixes as planned** (/workspace/self3/brief.md §3). Add one more: the lab smoke test's `run_exit 124` at 4.4 active min (c1.8) suggests bug #3 also hits the lab, so verify the fix there.

### d2. What round 3's research should test first (ordered by information per run)
These are *measurement* experiments, which the brief allows as controlled variables. Each one decides where the program's effort should go.

1. **A/A calibration.** eec78f8 vs eec78f8, ≥ 3 reps each, on 2 lab tasks.
   - Output: σ_run for quality (graded tests and reproducer-P0), active time, input, uncached.
   - Prediction to register: time CV 0.1–0.3, input CV 0.1–0.25. Basis: the round-2 between-arm spreads of 0.08–0.32 and 0.14–0.27 (power_r3.py).
2. **Protocol vs parallelism.** On one long task (≥ 45 solo-min), run four arms:
   - plain `codex exec`;
   - `murmur --solo`;
   - peer protocol with n = 1 (internal switch);
   - eec78f8 with 3 peers.

   This decomposes the −0.65 quality gap (b1) into "harness/prompt" vs "parallelism". If most of it comes from the protocol, the cheapest quality win is a protocol fix. If it comes from parallelism, invest in d3 M1/M2.
3. **Peer-count dose-response** (1/2/3 peers, the same long task), fitted with USL: T(N) = T₁·(1 + α(N−1) + βN(N−1))/N.
   - Prediction to register: the contention term α is large enough that 3 peers ≈ 2 peers on time.
   - Basis: lean2/lean3 times of 16.9/15.4 and 22.1/22.0 min (/workspace/explore/LOG.md lean round 2), noting that those runs are confounded by G1–G3.
   - If confirmed, the token-optimal default is 2, and that becomes a *finding* for the efficiency path.
4. **Only then, one mechanism experiment** (M1 recommended), against the bug-fixed base, n set by (1).

### d3. Mechanism directions (innovative, with theory and a test for each)
Design principle, derived from (b): **use parallel capacity for things a single agent cannot do for itself (independent verification, diversity checked by tests), not only for dividing up the typing.** External citations below are from my own knowledge and were *not* verified on this box; the peers should verify them (URL or paper) in Phase B.

**M1. Clean-room verifier (an independent oracle, enforced mechanically).** Highest priority.
- *Targets:* the risk dimension (44% of the gap, b3) and the ~69% of swarm P0s in single-author code (a, RC5).
- *Mechanism:*
  - A claimable role (any peer; no leader). The verifier's clone is built by murmur with only the brief, the repo's public interfaces, and the *spec sections* of PR.md. murmur doesn't stop it from pulling main, but its tests are written to a separate ref, `verify/*`, before it reads the implementation. The board records the ordering: test commit timestamps precede the verifier's first read of the implementation files, which can be checked from session logs.
  - A `post-receive` hook in origin.git (murmur already owns origin.git) runs the `verify/*` suite against every new main and posts each failure to the board as a `FAIL` task with the reproducer attached. This is executable, not a prompt rule.
- *Theory:*
  - When an author writes both the code and its tests, both come from the same mental model, so they share blind spots.
  - An oracle built from the spec alone reduces that correlation. The N-version-programming results (Knight & Leveson, IEEE TSE 1986) show that independence is only partial even across separate teams. So the claim is *reduced*, not eliminated, correlation, and the forced information asymmetry (spec-only) is what buys it.
  - CodeT (Chen et al., 2022, arXiv:2207.10397) shows that independently generated tests are a useful selector for generated code.
- *How it differs from a2 (cross-review, rejected):* a2 reviewed code after reading it, which anchors the reviewer on the implementation. It produced receipts, not executable checks, and its findings had no enforcement.
- *Predictions to register:*
  - reproducer-confirmed P0 per run ↓ ≥ 40% vs base (swarm ~1.38 → ≤ 0.8; solo ~0.5; /workspace/self2/REPORT.md);
  - graded hidden-test pass rate ↑;
  - active time ≤ +10% (the verifier works in parallel during the build);
  - input ≤ +10% (one of 3 peers changes role; no extra peer).
- *Falsifier:* confirmed P0 not reduced, or the verifier's suite has a mutation score no higher than the authors' own tests.
- *Cheap first test (deterministic, small n):* on a frozen lab task, compare the *mutation score* and *seeded-defect detection rate* of the verifier's suite vs the implementers' suite in the same runs. The comparison is within-run, so it is paired and needs few runs.

**M2. Test-arbitrated speculation on the riskiest component.** This replaces "draft and rank by looking".
- *Mechanism:* during planning, peers mark the single highest-risk/most-coupled component (claim table field). Two peers implement it independently with *forced diversity*: claims must differ in algorithm or data structure, and the board checks this. The M1 oracle plus **differential testing** between the two versions selects the winner (or merges the two). Inputs on which the versions disagree become test cases. murmur provides the harness: a helper that runs both versions on generated inputs and reports where they disagree.
- *Theory:*
  - Best-of-n improves expected quality when (i) errors are partly independent and (ii) the selector is accurate.
  - Today's selector (an LLM vote "by looking") is weak for non-visual code. Executable agreement is a stronger one.
  - Differential testing (McKeeman, 1998, "Differential Testing for Software") finds bugs without a full oracle.
- *Cost bound:* drafts were only 4–11% of input (/workspace/explore/LOG.md "Token-lean phase"). Restricting speculation to one component keeps the cost within the 1.25× token gate. That is a prediction to check, not a fact.
- *Predictions:* correctness/hidden-test pass rate on that component ↑. Falsifier: the versions rarely disagree (errors are fully correlated) or the oracle can't tell them apart.

**M3. Elastic, demand-driven peer activation.** Token lever.
- *Mechanism:* N peers are spawned, but only one is active at the start. It explores, writes the plan and fills the claim table. Dormant peers get a minimal start message and are activated only when the claim table holds ≥ 2 independent unclaimed tasks. Activation is done by murmur, through a board trigger plus `followup_task`, not by prompt discretion. A newly activated peer gets a compact handoff (its claimed task, FACT posts, the plan section), not the full exploration context.
- *Theory:*
  - Amdahl/USL: the serial fraction (exploration, planning, final integration) gets no faster with N, while contention (git coordination is 41–45% of swarm input; 50–67% of files are read by ≥ 2 peers; /workspace/explore/LOG.md) grows with N.
  - A static N = 3 over-provisions most of the run.
- *Known risk from our own data:* E4 found that waking peers who had *ended* cost +89% uncached, because they rebuild context (/workspace/explore/LOG.md E4/E5). M3 differs because dormant peers have no context to rebuild, but this must be tested.
- *Predictions:* input −25% to −40% vs static 3; active time within +10%. Test after d2.3 has established the static dose-response.

**M4. Claims-checked PR.md.** A cheap win, not a headline innovation.
- *Targets:* the PR.md-honesty gap (24% of the pooled gap; −2.5 in round 2, b3).
- *Mechanism:* murmur requires PR.md to contain a machine-readable "verification" block (command → expected outcome). At the end of the run, murmur executes those commands on the final main and appends the actual results. Any claim that fails is flagged inside PR.md itself.
- *Theory:* multi-author documentation drifts from the final state. Executing the claims makes them self-correcting.
- *Prediction:* the pr-dimension gap vs solo closes to within judge noise. A deterministic secondary metric is the number of PR.md claims contradicted by the harness.

**Not recommended for now:** more seam and integration prompt rules (they failed 3 times: M1–M3 on T1–T3; a1, a2 and a5 in round 2); shared scouting maps (E5, null); waking ended peers (E4, +89% uncached).

### d4. Pre-registration template for each mechanism experiment
For every M-experiment the notebook entry must state:
- the endpoint (deterministic, from d1.3);
- the predicted effect and direction, with a mechanism-specific *process* signature (e.g. M1: ≥ 1 `verify/*` failure posted and fixed per run);
- n, justified by the A/A σ;
- the decision rule;
- the falsifier.

The process signature matters: if the outcome improves but the signature didn't fire, the improvement is noise.



## (e) Open decisions

### e1. Number of rounds
- **Commit to round 3 as a measurement-and-foundation round:** bug-fixed base, A/A calibration, protocol-vs-parallelism, dose-response (d2), plus at most one mechanism experiment (M1). Its sealed eval should compare **base3 vs orig**, plus the M1 candidate only if Phase C gave it a clear signal.
- **Pre-authorize at most 2 further mechanism rounds (4 and 5).** Re-decide after each sealed eval.
- **Replace the stop rule** "two consecutive rounds with no KEEP" (brief §4) with: *stop when the best candidate's upper CI bound on the primary endpoint lies below the minimum effect the user cares about, in two consecutive rounds.* That way a round stops because of evidence of no effect, not because an underpowered test failed to see one.
- Rationale: with the current power, "no KEEP" is the expected outcome even for a real +0.5 effect (c2.1). Under the old rule the program would stop after rounds 3–4 without having learned whether anything works.

### e2. Budget
These are estimates. I have no price per token, so input-token counts are the unit; the extrapolations are marked.

| item | proposal | basis |
|---|---|---|
| round-3 research run | ≤ 30 lab runs, ≤ 350M input, ≤ 10 h | 30 × ~12M per swarm run ≈ 360M (REPORT.md run sizes 7–18M); lab-task runs may be shorter |
| round-3 sealed eval | base3 vs orig (± cand), **5–6 tasks × 2 reps**, + 1 solo per task: ≈ 30 runs, ≤ 400M, ~8–10 h | eval-rules.md cost model (~12M per swarm run) |
| per round total | **≈ 0.75B input (~96–98% cached → ~20–35M uncached), ~20 h wall** | sum of the above; uncached share from REPORT.md (swarm uncached/input ≈ 2–4%, e.g. W1 orig 450k/12.46M) |
| program cap (rounds 3–5) | **≈ 2.3B input**; stop early if e1 triggers | 3 × 0.75B |

On n: with today's judge-based quality (σ ≈ 0.8), a −0.5 non-inferiority margin at 80% power needs ≈ (2.49·0.8·√2/0.5)² ≈ **32 runs per arm**, which is unaffordable. With deterministic graded tests at an assumed σ ≈ 0.5 it needs ≈ **12 per arm**, which is feasible. This is the strongest argument for d1.3: **better instruments are cheaper than more runs.** Set the final n from the A/A calibration.

### e3. When to write the sealed tasks
**Write them after the candidate is frozen, and pre-register *how* they will be written now.**
1. **Now** (before round 3 starts), hash and keep in an operator-only location:
   - the task *specification*: task classes X1/X2/X3 (+ extras, if moving to 5–6 tasks), solo duration **45–90 min**, a non-git folder of ≥ 1,000 files for X2, and a graded hidden-test target of 60–85% solo pass on a reference build;
   - the *selection procedure*, e.g. a list of candidate source repos/datasets chosen by a seed derived from a value that doesn't exist yet, such as the frozen candidate's commit sha;
   - the scoring scripts and judge prompts.
2. **At freeze:** the research peers' run has ended, the lab queue is closed, and the candidate sha is recorded. Then the operator, or a fresh agent never exposed to round-3 materials, writes the briefs and hidden tests. They are validated with one solo reference build each, used only to check coherence and non-saturation, not to tune tests to that build's failures (round 2 did this validation at /workspace/self2/LOG.md 11:53). Hash into SEALED.md, then run the eval.
3. **Why not "write first, hide"?** The sandbox reads the whole disk (c4), so "hidden" on the box requires encryption with a key that never touches the box. That is workable but fragile. Writing after freeze makes leakage *impossible*, and the pre-registered specification plus seeded selection removes the operator's freedom to pick tasks that favor the candidate.

### e4. Should efficiency-only proposals pass?
**Yes, but with a redesigned rule.** As written (≤ 0.80× tokens on every task, plus per-task quality and speed guards) it has ≈ 6–14% power for a true 25% saving (c2.1). That makes it nominal, not a real path. The user said tokens of "~1.5–2× solo acceptable … optimize" (/workspace/advisor/CONTEXT.md), and the swarm currently sits at ~5.3× solo (b1). An efficiency gain that leaves quality and speed unchanged is exactly what they asked for. Proposed rule:
- **Primary:** pooled uncached *and* total input ratio vs reference ≤ 0.85, with the 90% CI upper bound < 1.0.
- **Quality non-inferiority (pooled, delivered runs, deterministic-weighted score):** CI lower bound ≥ −0.5. Size n so this is achievable (e2).
- **Delivery rate** ≥ reference.
- **Speed:** pooled geometric-mean active-time ratio ≤ 1.10.
- **Per-task catastrophe guards:** no task worse than −1.0 quality or 1.25× time.
- **Allowed for parameter findings** (e.g. a peer-count default from d2.3), labelled as findings so they don't count as the round's mechanism. This keeps the "no parameter tweaks as innovation" rule without throwing away the most data-supported lever.



## Appendix: analyses run (all in /workspace/advisor/analysis, read-only over /workspace)
- `judge_noise.py` (pre-existing): **superseded.** It reads /workspace/self2/eval/judge/scores.json, which is stale. W1|orig shows 1 pass and W2|orig/a2/a5 show 0 passes, but REPORT.md shows 2 passes for every arm.
- `judge_noise2.py`: recomputes the pass-A vs pass-B disagreement from the final judge outputs, using the regexes in /workspace/self2/eval/judge/score.py. Result: n = 18, mean |A−B| 1.09, sd 1.26, two-pass-mean judge sd ≈ 0.63; per-dimension sd of differences: risk 4.07, r 3.38, pr 1.22, c 0.97, d 0.58.
- `swarm_vs_solo.py`: the pooled 16-pair comparison in (b1). Values are transcribed from the cited results files.
- `dims.py`: the per-dimension gap decomposition in (b3), over 12 tasks.
- `power_r3.py`: simulates eval-rules.md under noise estimated from round 2. It is a model with assumed Gaussian noise and no task × arm interaction, so treat its numbers as optimistic upper bounds on power.

**Things I could not verify** (flagged):
- Whether the W2 non-integration was caused by 658d82a's root-prompt change.
- Whether `run_exit 124` in the lab smoke test is the root-hang bug.
- Run-to-run noise: no condition has ever been replicated on the box.
- The external literature in d3, cited from memory.
- Exact dollar costs.

I did not inspect the research branches (feat/token-lean etc.): git commands in the repos required approval in this environment, so diffs came from the installed arm trees under /workspace/self2/arms.
