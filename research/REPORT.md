# Murmur: evidence-led improvements

Research date: **October 16, 2026**. The target is faster large-task execution, quality no worse
than a strong solo run, and roughly 1.5–2 times solo tokens. **The available evidence does not
establish that murmur meets all three goals.** The held-out validation rejected both tested
lean variants; implementing plausible mechanisms must not be presented as a successful
performance experiment. [Validation plan](evidence/val-PLAN.md),
[validation results](evidence/val-RESULTS.md).

## Scope and method

This is a bounded survey of official documentation, original repositories, author papers,
engineering accounts, the provided immutable experiment summaries, and the installed Codex
source. It is not an exhaustive enumeration of every internet project, an independent
replication of vendor benchmarks, or a prediction that historical scores apply to current
models. Each external mechanism or result below has a source URL; linked survey appendices
carry the detailed per-project citations. Inferences and proposals are labelled as such.

Read the report together with:

- [Additional products and projects](products-other.md): Claude Code subagents/teams, Amp,
  Aider, MetaGPT, ChatDev, gpt-engineer, Sweep, mini-SWE-agent, Claude Squad, Conductor, Warp,
  Gas Town, Ruflo/Claude Flow, Swarms, smolagents, OpenCode and Goose.
- [Codex source verification](CODEX-SOURCE.md): installed CLI 0.162.1 thread creation, waits,
  context inheritance, reasoning defaults, compaction, cache keys and sandbox.
- [Usage source verification](usage.md): durable per-response records, cumulative-counter
  hazards and incomplete telemetry.
- [Orchestration frameworks](ORCHESTRATORS.md): AutoGen, Magentic-One, Microsoft Agent
  Framework, CrewAI, LangGraph and Anthropic research engineering.
- [Coding products and integration](PRODUCTS-INTEGRATION.md): Cursor, Devin, Jules, OpenHands,
  SWE-agent and their coordination/merge mechanisms.
- [Evaluation and research](evaluation.md): closest leaderless-swarm study, multi-agent failure
  taxonomy, architecture scaling, compiler case study, Agentless and evaluation validity.
- [Supplemental coordination and source survey](survey-a3.md): additional coding-system
  context mechanisms and Git/sandbox evidence.

These source families use different definitions of an agent and different evaluation tasks.
A parallel workspace manager, sequential specialist pipeline, centralized planner/worker team,
and equal-authority shared-origin swarm should not be treated as interchangeable mechanisms.
The project-specific rows in the linked appendices describe which model applies, including
unverified merge/context behavior rather than filling gaps from memory.

## What our own experiments actually support

The supplied files are summaries and preregistrations, not full raw trajectories or the
judge harness. We read them without editing `evidence/`. Their arithmetic can be checked;
the original runs, judge identities and environment effects cannot be independently rerun
from these files alone. [Evidence inventory](README.md), [experiment log](evidence/LOG.md).

| Observation | Evidence and strength | Consequence |
|---|---|---|
| Four-to-six times the model calls and similar context per call accompanied high total input; shell Git coordination accounted for 41–45% of swarm input in the analyzed runs. | Logged analysis of T1–T3; scripts/raw traces are referenced but not supplied. Descriptive, not causal. [Log](evidence/LOG.md#token-lean-phase-user-decision-1107-baseline--original-main-target-15-2x-solo-tokens), [lean plan](evidence/lean-PLAN.md). | Inference: lower unnecessary agent/call count is more promising than merely shortening tool output. |
| Two peers reduced input relative to three peers using the same lean build on V1/V2; uncached usage was 1.8×/1.7× solo in that round. | Matched lean2/lean3 arms, one run and judge per task; quality scoring is noisy. [Plan](evidence/lean2-PLAN.md), [results](evidence/lean2-RESULTS.md). | Supports a conservative two-peer default; does not prove quality equivalence or the target ratio generally. |
| The same lean2 approach failed later: 4.4×/4.6× uncached solo input, and W2 quality below its keep threshold. | Held-out preregistered tasks, but still one run/judge per arm. Stronger local counterevidence than the favorable exploratory result. [Validation plan](evidence/val-PLAN.md), [results](evidence/val-RESULTS.md). | Do not advertise “2× solo tokens,” infer success from one favorable task, or confuse uncached with total input. |
| Prompt-based independent review improved some risk outcomes but missed its aggregate quality/time/token rule. | Mean quality gain +0.2 versus required +0.5; T1 time +37%, uncached +44%. [Large-task plan](evidence/large-PLAN.md), [results](evidence/large-RESULTS.md). | More review instructions alone are not the selected primary mechanism. |
| A one-call sync helper was used over 100 times without cutting call counts or Git coordination share. | Reported U1/U2 behavior; no raw replay here. [Lean results](evidence/lean-RESULTS.md). | Do not reintroduce command batching as a demonstrated token-saving fix. |
| Small-task swarms often matched or lost solo speed; larger tasks sometimes benefited. | Mixed workloads and varying timing adjustments; correlation, not controlled task-size intervention. [Experiment log](evidence/LOG.md). | Keep explicit `--solo` and peer-count choice; automatic task-size routing remains unvalidated. |
| The final plain-folder comparison had 14.43M versus 3.01M total input and 397k versus 88k uncached input; quality favored swarm on that task. | One task, imperfect blinding, different wall/active timing. [Big3 plan](evidence/big3-PLAN.md), [results](evidence/big3-RESULTS.md). | Speed, quality and cost must all be reported; a favorable quality score is not budget compliance. |
| Cache hits and machine pauses vary, and review coverage of late commits is weak in the summaries. | Explicit measurement and seam analysis in the log; underlying trace audit not independently repeated. [Log](evidence/LOG.md#large-tasks-only-user-decision-0921--why-swarm-quality-drops-verified-from-logs). | Record observed usage and exact delivered revision; avoid guessed “active time” or clean-exit success claims. |

The user requested **total tokens** around 1.5–2× solo; earlier keep rules sometimes tested
**uncached input** instead. Those are different metrics. Our reporting preserves input,
cached input, derived uncached input, and output separately; the sum of input and output is
also available. Reasoning output is a subset of output and is not added again.
[Accounting implementation](../src/murmur/usage.py), [accounting tests](../tests/test_usage.py).

## Cross-source synthesis

**Context separation is broadly available; its value depends on what gets passed.** Claude
subagents have separate contexts; Amp handoff extracts relevant information; Aider selects
repository structure; Anthropic's research system delegates independent questions with
summarized returns. This supports focused worker inputs and explicit artifacts, not blind
transcript duplication or a universal claim that subagents save tokens.
[Claude](https://code.claude.com/docs/en/sub-agents),
[Amp](https://ampcode.com/guides/context-management),
[Aider](https://aider.chat/docs/repomap.html),
[Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system).

**Isolation is different from integration correctness.** Claude Squad and Conductor expose
separate Git workspaces; Git's fast-forward checks reject incompatible reference updates.
These mechanisms prevent some overwrite races but cannot decide whether independently
correct features interact correctly. The local seam findings and multi-agent failure taxonomy
therefore justify inspecting the delivered revision and testing behavior across interfaces.
[Claude Squad](https://github.com/smtg-ai/claude-squad),
[Conductor](https://www.conductor.build/docs),
[Git receive configuration](https://git-scm.com/docs/git-config#Documentation/git-config.txt-receivedenyNonFastForwards),
[MAST](https://arxiv.org/html/2503.13657v3), [local seam evidence](evidence/LOG.md).

**More agents are not a universal scaling law.** The closest identified external swarm study
uses equal-prompt agents with shared repository/forum coordination and reports correlated
choices and integration/product problems. Architecture comparisons find task-dependent
benefits, including degradation on sequential planning. These results are evidence against a
universal agent count, not a controlled estimate for murmur's selected model and repository.
[Anthropic swarm study](https://www.anthropic.com/research/multiagent-systems),
[Scaling Agent Systems](https://arxiv.org/html/2512.08296v1).

**Vendor benchmark results are evidence about their stated workloads.** Anthropic's research
system's token denominator is chat, not solo coding; its compiler project is a feasibility
case study with a substantial harness. Coding repair benchmarks and short synthetic software
builds do not directly measure a long shared-origin project with subjective requirements.
Infrastructure allocation and benchmark defects can change scores without a better model.
[Research system](https://www.anthropic.com/engineering/multi-agent-research-system),
[compiler](https://www.anthropic.com/engineering/building-c-compiler),
[infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise),
[evaluation appendix](evaluation.md).

## Installed source, not remembered behavior

The source audit uses the read-only checkout `/workspace/codex-src-0.162.1`, commit
`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`. The exact findings and source line links are in
[CODEX-SOURCE.md](CODEX-SOURCE.md) and [usage.md](usage.md). Public availability of that
commit's GitHub links was not verified; the files were read locally.

The implemented decisions are narrowly grounded in that audit: the V2 wait argument schema,
fresh versus inherited child history, selected settings rather than a model-name constant,
and per-response usage rather than repeated cumulative counters. Source inspection establishes
what this implementation does. It does not establish provider billing completeness, cache-hit
rates, model quality or identical behavior in future CLI versions.

## Ranked improvements and disposition

Ranking balances direct evidence, implementation footprint, user constraints and uncertainty.
It is a design recommendation, not a measured ordering of performance gains.

1. **Smaller default swarm and explicit fresh peer context — implemented.** Two peers remain
   equal-authority, users can request more, and complete peer briefs already live in local
   files. Fix the invalid V2 wait wording at the same time. Peer-count evidence is directionally
   useful but held-out quality/budget targets remain unproven; fresh-context savings are not
   measured here. [Source audit](CODEX-SOURCE.md), [lean2](evidence/lean2-RESULTS.md),
   [validation](evidence/val-RESULTS.md), [setup tests](../tests/test_setup_git.py).
2. **Preserve user-selected model/effort, impose no model or compaction constant — implemented.**
   This directly satisfies the task's portability constraint. Omitted preferences let Codex
   resolve defaults; explicit flags still override configuration. Supported scope and profile
   limitations must remain documented. [Configuration tests](../tests/test_config.py),
   [catalog tests](../tests/test_catalog.py), [source audit](CODEX-SOURCE.md).
3. **Observed run usage and exact delivered-state inventory — implemented.** Offline accounting
   and read-only Git inspection add no peer model calls. Unknown telemetry remains unknown;
   a successful process or presence of PR.md never proves correctness. This enables later
   falsification of cost/completion claims. It is observability, not an established optimization.
   [Usage](usage.md), [usage tests](../tests/test_usage.py), [result tests](../tests/test_result.py).
4. **Revision-bound check evidence — draft retained as research, implementation deferred.**
   Correct receipts can prevent ambiguous “tests passed” messages, but matching a commit and
   command cannot establish equal dependencies, ignored files or services. Optional helper
   adoption and performance benefit were not measured. [Supplemental survey](survey-a3.md),
   [prior failed shared-check rules](evidence/lean-PLAN.md).
5. **Automatic integration receipts/queues — draft receipts deferred; queues remain future work.**
   Accepted-ref receipts are deterministic, but Git already exposes revision/diff data; another
   hook needs evidence that agents use it to prevent seam failures or save calls. A mandatory
   queue/check gate would require repository-specific test configuration and more lifecycle
   machinery. [Local seam evidence](evidence/LOG.md),
   [Gas Town](https://github.com/gastownhall/gastown).
6. **Automatic task routing, hard token budgets, automatic context reset or role hierarchies —
   deferred.** Available studies show task dependence, and prior prompt experiments failed
   their keep rules. No trustworthy general complexity detector, safe budget cut point or
   model-independent reset policy was validated in this run. [Scaling study](https://arxiv.org/html/2512.08296v1),
   [swarm study](https://www.anthropic.com/research/multiagent-systems),
   [local validation](evidence/val-RESULTS.md).

## Verification and future evaluation

We used credential-free subprocess and real-Git fixtures, not paid performance runs. The shared
[capture script](../scripts/capture_states.py) records success, failure, partial result, time cap,
interruption and stubborn descendants in about three seconds on this machine. It makes **zero
model calls**. Six independent draft suites passed in a1's isolated archive review (37/34/36/38/35/38
tests; roughly 9–10 seconds each). This verifies mechanics only; definitive integrated validation
and draft selection are recorded in [PR.md](../PR.md). Development-agent tokens are not exposed
to this peer and are **unverified**; zero model calls applies to these fake validation experiments,
not to the agents performing this research and implementation.

A future performance experiment should preregister held-out long tasks, compare solo against
old and new murmur with identical model/effort/resource/dependency/time budgets, repeat each
arm, and judge anonymized final artifacts with independent behavioral checks. Report wall time
and disclosed pause handling, total input/output and cached input, missing-usage coverage,
quality/bugs, and unsuccessful/interrupted runs. Separate peer-count, fresh-context and any
future integration mechanism arms before attributing causality. This proposed design follows
local reversals and infrastructure-noise research; **it was not run here**.
[Local validation](evidence/val-PLAN.md),
[infrastructure noise](https://www.anthropic.com/engineering/infrastructure-noise).
