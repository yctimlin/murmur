# A prior model of murmur scaling (phase B, frozen before C1)

This is a hypothesis-generating model, not a fitted causal explanation. Phase A has heterogeneous task/arm cells with one run each. C1 is the first out-of-sample test of the forecasts below; its calibration results must not be used to revise these forecasts before scoring them. No mechanism or default peer-count change is proposed in this phase.

## Evidence and scope

`research/DIAGNOSIS.md`, derived from `research/data/index.csv` with definitions in `research/data/METHODS.md`, reconstructs 16 historical baseline swarm/solo pairs: mean judge-score difference −0.6521 points, geometric input ratio 5.260, and geometric active-time speedup 1.145. Their changing tasks, rubrics, engine revisions and single repetitions prevent estimation of within-task noise or separation of protocol, parallelism and selection. **Judge points are not hidden-test pass-rate points.** The independent reproduction is `research/notebook/20261017-0816-a3-c1-design-review.md`.

Of the 668,357,819 observed input tokens across all indexed evidence, 646,147,840 were cached (96.68%). This is accounting evidence about repeated context, not a causal estimate of removable cost. Tool-category input counters charge entire contexts; board-output characters are not input tokens. The 2/54 task-swarm nondeliveries, 18 judge-labeled seam observations with multi-author line evidence, and 65.81% same-path textual non-retention of draft additions motivate delivery, coupling and duplication terms. None estimates their coefficients. Some failures and telemetry are missing; counts are not independent Bernoulli trials across one population.

The forecast domain is 1–3 peers on the three frozen screening tasks at the runner's unchanged model/effort. A peer count excludes the launcher root. `exec` and murmur `solo` have one task-solving agent but different wrappers; protocol with one peer has a launcher plus one peer. No model, reasoning-effort, context-window or compaction setting is changed.

## Literature: mechanisms to consider, not transferable coefficients

1. **Amdahl (1967), “Validity of the single processor approach to achieving large scale computing capabilities.”** Serial work bounds parallel speedup. The serial-fraction term below is its limiting case, not an assertion that agent work is a fixed parallel program. DOI: https://doi.org/10.1145/1465482.1465560 .
2. **Gunther (2008), “A General Theory of Computational Scalability Based on Rational Functions.”** The universal scalability law adds contention and coherency terms, permitting retrograde scaling. We use its rational form as a low-dimensional descriptive model. It was not validated there for LLM coding agents. https://arxiv.org/abs/0808.1431 .
3. **Brooks, The Mythical Man-Month, anniversary edition (1995), chapter 2.** Training, repartitioning and communication can defeat added staffing on coupled work. This supports considering startup and integration overhead; it does not imply an immutable law that more agents are worse. Publisher: https://www.pearson.com/en-us/subject-catalog/p/mythical-man-month-the-essays-on-software-engineering-anniversary-edition/P200000009637/9780201835953 .
4. **Wang et al. (2022/ICLR 2023), “Self-Consistency Improves Chain of Thought Reasoning in Language Models.”** Diverse sampled reasoning paths with answer aggregation can improve benchmark accuracy. A merged software artifact is not majority voting over independent answers; correlated drafts and imperfect selection can erase this advantage. https://arxiv.org/abs/2203.11171 .
5. **Wu et al. (2023), “AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation.”** Agent conversations and tool participation are programmable design variables. Framework demonstrations are not evidence that any particular peer protocol beats a matched single agent. https://arxiv.org/abs/2308.08155 .
6. **Cemri et al. (2025), “Why Do Multi-Agent LLM Systems Fail?”** The authors' failure taxonomy includes system specification, inter-agent alignment, and verification/termination. These motivate separate delivery, integration and verification endpoints; taxonomy frequencies are not priors for murmur's task population. https://arxiv.org/abs/2503.13657 .
7. **Anthropic engineering, “How we built our multi-agent research system” (2025).** A deployed lead-agent/subagent research product reports benefits on breadth-first research together with substantial token use. This is a useful product comparator with different topology, tasks, evaluation and resources, not a controlled murmur benchmark. https://www.anthropic.com/engineering/multi-agent-research-system .
8. **OpenAI multi-agent documentation**, retrieved 2026-10-17, describes task decomposition, orchestration and cross-agent review as distinct patterns. The public API documentation is a product comparator; the exact Codex snapshot below is authoritative for this experiment. https://developers.openai.com/api/docs/guides/agents-api/multi-agent .

These sources support candidate mechanisms and competing explanations. All numeric parameters below are explicitly elicited working priors, lightly anchored by historical scale; no literature coefficient is imported as a measured murmur effect.

## Codex and murmur implementation grounding

All Codex paths in this section are relative to the read-only snapshot `/workspace/codex-src-0.162.1/`; line numbers refer to that snapshot, not a moving online branch.

| Observed implementation | Source path:line | Model implication, distinguished from measurement |
|---|---|---|
| The v2 handler routes spawn, message, followup, wait and list operations. | `codex-rs/core/src/tools/handlers/multi_agents_v2.rs:28` | Independent conversations incur calls and context; a peer is not a zero-cost worker. |
| `fork_turns` defaults to `all`; the spawn handler determines full-history fork and passes it to agent control. | `codex-rs/core/src/tools/handlers/multi_agents_spec.rs:665`; `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs:123`; `codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs:185` | Shared prefixes and correlated initial reasoning are plausible; inherited history is not proof of independent samples. |
| Full-history fork preserves cached prompt prefixes; fork snapshots the parent's stored model history. | `codex-rs/core/src/agent/control/spawn.rs:125`; `codex-rs/core/src/agent/control/spawn.rs:1067` | Track input and uncached input separately. Prefix reuse does not remove all billed input. |
| V2 wait accepts only a timeout, subscribes to input-queue activity, and wakes for mailbox, steer, or timeout. Completed event receiver IDs are empty. | `codex-rs/core/src/tools/handlers/multi_agents_spec.rs:917`; `codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs:67`; `codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs:113`; `codex-rs/core/src/tools/handlers/multi_agents_v2/wait.rs:202` | Empty receiver IDs do not establish completion. A wait tool's elapsed time is not continuously sampled model inference. Repeated wake/list cycles add model turns, but not one token charge per waiting second. |
| Board notification delivery never starts/restores idle recipients; `trigger_turn` is false. | `codex-rs/core/src/agent_message_board.rs:1`; `codex-rs/core/src/agent_message_board.rs:204`; `codex-rs/core/src/agent_message_board.rs:232` | Durable knowledge and active notifications differ; rereads and missed handoffs can add overhead. |
| Board reads have preview/output budgets; `read_post` caps the requested character count. | `codex-rs/ext/agent-message-board/src/tools.rs:130`; `codex-rs/ext/agent-message-board/src/tools.rs:288` | Message count and visible bytes alone cannot reconstruct repeatedly processed context. |
| Context accounting distinguishes full active usage from compaction scope; thresholds depend on configuration/model information. | `codex-rs/core/src/session/context_window.rs:8`; `codex-rs/core/src/session/context_window.rs:60`; `codex-rs/core/src/session/context_window.rs:83` | Context limits are variables, not a hardcoded shared constant. |
| The local compaction path replaces history with a summary/user-message representation, recomputes usage, and emits a caution about repeated compactions. | `codex-rs/core/src/compact.rs:370`; `codex-rs/core/src/compact.rs:401`; `codex-rs/core/src/compact.rs:416` | Compaction can reset context growth and introduce recovery work. This local path does not prove every run uses it or quantify information loss; the snapshot also has remote compaction paths. |

Murmur source paths are repository-relative: `src/murmur/prompts/root.md:1` makes the root a launcher/waiter; `src/murmur/prompts/peer.md:22`–`:43` requests distinct drafts, ranking and integration before division of work. These supply potential duplicated exploration and synchronization barriers. `src/murmur/cli.py:625` selects solo versus the one-peer protocol switch; `src/murmur/cli.py:752`–`:765` disables agent tools in solo or enables v2/board with root capacity in swarm. Thus `solo` versus protocol-1 identifies a **bundle** (prompts, root/fork, tools, draft/self-ranking and delivery workflow), not a board-only effect.

Runner boundaries also matter: `/workspace/self3/lab/runner2.py:111`–`:117` starts exec timing after setup with a strict outer cap; `:139`–`:148` includes murmur setup and allows a larger outer timeout. Its exec auto-commit differs from murmur push delivery. Active minutes are primary; wall, setup and capped status are diagnostics. Equal `cap` text does not guarantee identical opportunity or wall accounting across wrappers.

## Quantitative model

Let task size `S` be expected plain-exec active minutes; `n` the number of solving peers; `k` a dimensionless coupling index; `p` the wrapper/protocol. Time is measured with the runner's gap-capped union of event timestamps, not CPU utilization or summed peer effort. The working mean is

```
T(n,p,S,k) = h[p] + S * (1/n + alpha*(n-1)/n + beta*k*(n-1)).
```

For `h=0`, speedup is `n / [1 + alpha*(n−1) + beta*k*n*(n−1)]`, the USL form. With `beta=0` it is Amdahl's model. `h` is fixed protocol/setup burden visible in the chosen time metric, `alpha` summarizes serial/contended work, and `beta*k` summarizes reconciliation/coordination growing with peer count. These are effective quantities, not identifiable semantic partitions. There is no fixed-work assumption about real agents hidden behind the notation: duplicated work and changed strategies can make this approximation fail.

For fixed positive `beta*k`, the unconstrained minimum occurs at `n*=sqrt((1−alpha)/(beta*k))`, then integer counts must be compared. Larger `S` amortizes `h`; larger coupling can move the optimum down. Because C1 has only n=3 plus unreplicated exec, it cannot fit this curve. C2 must test its **pre-existing predictions**, then fit a descriptive curve with uncertainty, without treating a three-point interpolation as validation.

Token accounting starts from per-response context:

```
I = sum_over_agents_and_calls(context_tokens_at_call)
U = sum_over_agents_and_calls(context_tokens_at_call - cached_tokens_at_call)
O = sum_over_agents_and_calls(output_tokens_at_call)
```

Within a context segment with `m` calls and mean added context `g`, an approximation is `I_segment=m*c0 + g*m*(m−1)/2`. Compaction creates new segments and may add summary/recovery calls. This explains how token growth can outpace elapsed time without calling all repeated context waste. `g` includes newly retained instructions, tool results and model messages, not only board text.

For batch planning, use the simpler aggregate approximation

```
I_exec = 60,000*S
r_context(n) = 1 + 0.30*(n−1)
I(n,p) = I_exec * n*T(n,p)/S * r_context(n)
U(n,p) = 0.04*I(n,p).
```

Here `n*T` is an exposure proxy, **not observed summed peer active time**; uneven worker activity, root turns, duplicated exploration, long contexts and compaction are absorbed in `r_context`. The exact accounting identity above has priority. There is no monetary forecast; prices/cache discounts are not assumed. Output is retained as a separate measured endpoint, without an invented historical source partition.

Quality needs both successful behavior and delivery. Let `q0[t]` be exec graded-test score, `pi[p]` the protocol penalty, `rho` error correlation, `gq` a possible ensemble benefit, and `lambda` the coupling penalty. An intentionally small bounded model is

```
e(n) = gq*(1-rho)*(n-1)/(1+rho*(n-1))
q(n,p,t) = clip(q0[t] - pi[p] + e(n) - lambda*k[t]*(n-1), 0, 1)
D ~ Bernoulli(d[p,t]); record D separately from q.
```

`q` forecasts the **unconditional scored deliverable**, including scorer results for baseline/partial outputs after failure; do not multiply it by `D` or drop nondeliveries. A nondelivery may leave inherited code with a nonzero score. The mixture interpretation is `E[q]=d*E[q|D=1]+(1−d)*E[q|D=0]`; C1 cannot estimate its components precisely. `rho` is a conceptual draft-error correlation, not estimated from line overlap. A perfectly correlated ensemble yields no modeled ensemble gain. `pi`, `lambda`, `rho` and `gq` are not separately identified here.

## Explicit priors and assumptions (not posterior estimates)

| Parameter | Working point | Elicited sensitivity range / basis |
|---|---:|---|
| `S`: document_catalog / ledger_replay / reserveplan | 35 / 40 / 65 min | Task-author design estimates from each `TASK.json`; actual runtime uncalibrated. Use 0.5–1.5 times these in sensitivity work. |
| Coupling `k`: document / ledger / reserve | 0.5 / 1 / 1.25 | Subjective design ordering (migration, transactional repair, shared-capacity DAG); vary each by factor 0.5–2. No hidden outcomes used. |
| `h`: exec / solo / protocol | 0 / 2 / 5 min | Elicited fixed-overhead hypothesis; protocol range 0–10. |
| `alpha`, `beta` | .30, .12 | Sensitivity .10–.60 and .03–.25. Historical near-unit speedup makes large overhead plausible but cannot estimate either. |
| Input rate, context slope | 60k/min, .30 | Sensitivity 30k–120k/min, .0–.7; cost anchors are heterogeneous. |
| Uncached fraction | .04 | Working range .02–.12, lightly informed by historical .0332. |
| `q0`: document / ledger / reserve | .75 / .75 / .70 | Task designers targeted non-saturation; these are uncalibrated test-rate beliefs, not converted judge scores. |
| `pi`: exec / solo / protocol | 0 / 0 / .03 | Protocol range −.03 to .10; a negative penalty permits benefit. |
| `rho`, `gq`, `lambda` | .75, .04, .014 | Sensitivity rho .25–1, gq 0–.15, lambda 0–.05; no separate inference in C1. |
| Delivery probability base3 / orig | .97 / .97 | Cautious equal-arm working prior, not extrapolation of 2/54 as a binomial estimate. Three original runs cannot establish rare-failure safety. |
| Repeat CV: active / input / uncached | .20 / .35 / .40 | Ranges .10–.40 / .15–.70 / .15–.80. No Phase-A estimate of same-cell noise exists. |
| Repeat score SD | .10 | Range .03–.20 on 0–1 scale. Independent task runs, not individual hidden tests, are the experimental units. |

Sensitivity ranges are not independent probability distributions. The simple model does not produce a fitted Bayesian posterior. Block shocks and possible arm interaction from concurrent provider load should be represented in later analysis as `log(Y_run)=log(mu_arm,task)+b_block+epsilon_run`; pairing removes only a shared additive log shock. No particular block correlation is assumed known. Report `lines_429` and capped statuses, with no outcome-based removal.

## Frozen C1 forecasts

Score forecasts are the quality model rounded to the nearest .05; ledger's modeled .70 stays .70 and reserve's .643 becomes .65. Orig and base3 have identical mean forecasts: the safety fixes have a null ordinary-case performance prior. Ranges below are **elicited nominal 80% per-run prediction bands**, not calibrated confidence intervals.

| Task / arm | Score | Active min | Input M | Uncached M |
|---|---:|---:|---:|---:|
| document_catalog / exec calibration | .75 | 35 | 2.1000 | .084000 |
| ledger_replay / exec calibration | .75 | 40 | 2.4000 | .096000 |
| reserveplan / exec calibration | .70 | 65 | 3.9000 | .156000 |
| ledger_replay / base3 or orig, 3 peers | .70 | 35.933333 | 10.3488 | .413952 |
| reserveplan / base3, 3 peers | .65 | 59.166667 | 17.0400 | .681600 |

For any row with point `mu`, score band is `[max(0,mu−.25),min(1,mu+.25)]`; active band `[.5*mu,min(1.45*mu,configured cap)]`; input `[.4*mu,2.2*mu]`; uncached `[.25*mu,3*mu]`. Administrative caps can censor completion and compress measured variability; do not impute a capped run as an uncensored completion at the cap. Model point expected C1 input is 203.7792M for the proposed 18 jobs; the scheduler's separate heuristic is 189M. Neither authorizes exceeding 450M total.

C1 uses one exec calibration per screening task first, six base3 repetitions on each of ledger and reserve (three true A/A blocks per task), and three ledger original runs paired only with the predesignated A member. The second base3 member is not another independent original comparison. See `research/prereg/C1.json` for exact immutable jobs and decision rules.

**Evaluation before any refitting:** report every run, arm/task mean and SD, score MAE, log-ratio error for positive time/token endpoints, and prediction-band coverage numerator/denominator. Undefined ratios remain missing with reasons. A task/arm mean outside its per-run band is a conservative forecast failure screen, not a calibrated mean test. Report all failures rather than choosing the best endpoint. Scores from a task whose first exec rate is strictly greater than .95 are excluded from confirmatory task comparisons under the preregistered saturation rule; show all-run descriptive forecasts as a separate table. Do not silently replace that task or add jobs. At exactly .95 it remains eligible. Calibration is n=1 and cannot establish either difficulty or a causal exec contrast.

H1–H6, mechanisms, sizes, falsifiers and decision limits are in `research/HYPOTHESES.md`. The required independent red-team entry has `redteam` in its filename. Raw C1 data will be `/workspace/self3/labdata/results/<name>/` and `research/data/raw/C1/`; no C1 result exists at this registration.

## Deferred C2 predictions and identification

With reserveplan's frozen `S=65,k=1.25`, protocol n=1/2/3 gives `T=70/57/59.166667` minutes and `I=4.2/8.892/17.04M`. Thus a third peer is predicted 3.8% slower and costs 91.6% more input than two; three is still 15.5% faster than one. These are prospective **weak priors**, not a peer-count finding. Quality model values are .6700/.6582/.6430, so even a faster count needs a score/delivery check. Solo predicts `T=67` and `I=4.02M`, versus protocol-1 `70` and `4.2M`: +4.5% time/input and −.03 score from the protocol bundle. Exec-to-solo differences include wrapper and delivery semantics.

C2 will preregister after C1's noise/saturation review, preserving these original predictions for an honest comparison if the task remains eligible. Every murmur arm must use base3; protocol-1 requires `MURMUR_ONE_PEER_PROTOCOL=1`. Eighteen jobs remain under the count budget, but actual C1 tokens govern feasibility. No protocol-vs-parallelism or peer-count causal claim comes from C1. No mechanism is selected without the round's own controlled signal; a null result or failed prior is a valid research outcome.
