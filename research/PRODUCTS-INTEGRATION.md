# Coding-agent products and integration evidence

Surveyed 2026-10-16. This is a bounded primary-source survey, not a claim that every existing
product was found. Product documentation establishes advertised behavior; vendor experiments
are not independent comparisons with murmur. Where a source does not report a controlled
speed/quality/token comparison, that result remains **unverified** here. The main report links
this section with the other peers' product, research, and Codex-source surveys.

## Product mechanisms

| Project | Work division, coordination, merge and context | Reported results and limits |
| --- | --- | --- |
| Cursor cloud agents | Independent agents run remotely; the documented workflow clones a repository, works on a separate branch and pushes changes for handoff. Context window size is configurable for supported models. This documents parallel sessions, not a guarantee that unrelated sessions coordinate their designs. [Official cloud-agent docs](https://cursor.com/docs/cloud-agent). | The cited product page documents behavior and usage costs; it supplies no controlled swarm-versus-solo quality/token comparison. [Source](https://cursor.com/docs/cloud-agent). |
| Cursor long-running research | Its January 14, 2026 writeup describes a failed equal-status shared-file/locking approach, then recursive planners, focused workers, and a judge between cycles. Workers push their own changes; an extra integration agent was removed after becoming a bottleneck. Periodic fresh starts address drift. [Engineering report](https://cursor.com/blog/scaling-agents). | Reports hundreds of concurrent agents and a browser experiment exceeding one million lines in roughly a week. These are vendor scale demonstrations, not evidence that a two-peer murmur run is faster or cheaper. The report itself says the system is not perfectly efficient. [Source](https://cursor.com/blog/scaling-agents). |
| Devin Dynamic Workflows | Deterministic Python defines fan-out and staged work; agent calls return JSON-schema results. Default child sessions run on separate VMs and hand off git branches; shared-VM mode exists but documentation requires nonoverlapping writes. Resuming replays completed calls keyed by prompt/schema/settings and retries unfinished work. [Official guide](https://docs.devin.ai/work-with-devin/dynamic-workflows). | The guide explicitly cautions that a workflow can consume far more ACUs than one session. It recommends narrow trials before wide fan-out; no controlled murmur-equivalent comparison is provided. [Source](https://docs.devin.ai/work-with-devin/dynamic-workflows). |
| Google Jules | A task runs in a VM that clones code, installs dependencies, and edits files. The user chooses the repository/branch and reviews a proposed plan; root `AGENTS.md` supplies repository context. [Getting started](https://jules.google/docs/). Completed changes can be examined in the UI and exported through a branch/PR. [Review workflow](https://jules.google/docs/code/). | These pages establish asynchronous task execution and review, not an internal leaderless swarm, automatic cross-task semantic merging, or measured token-efficiency gains. Those mechanisms and results are **unverified** from the cited material. |
| OpenHands SDK | The current TaskToolSet creates a sub-agent conversation, blocks the parent until completion, returns the final result, and persists context for task-ID resumption. It explicitly documents sequential blocking delegation, so it should not be mislabeled as parallel by default. [TaskToolSet](https://docs.openhands.dev/sdk/guides/task-tool-set). Context condensation summarizes older history while retaining recent/initial context. [Condenser guide](https://docs.openhands.dev/sdk/guides/context-condenser). | Condenser docs claim up to 2x lower per-turn API cost; this is a vendor claim for their configuration, not total-run murmur savings. Git merge policy is not established by these SDK guides. [Source](https://docs.openhands.dev/sdk/guides/context-condenser). |
| SWE-agent | A configurable agent uses repository/environment tools to solve an issue. Current official docs say it is maintenance-only and recommend mini-SWE-agent; historical SOTA news should not be presented as a current leaderboard rank. [Official docs](https://swe-agent.com/latest/). | The landing page's older benchmark announcements are dated historical claims. No controlled multi-agent speed/token comparison is supplied there. [Source](https://swe-agent.com/latest/). |
| mini-SWE-agent | A deliberately small bash-only agent with linear conversation history; actions use separate `subprocess.run` calls. It supports local/container environments. This is a useful single-agent baseline rather than a shared-origin swarm. [Current overview](https://mini-swe-agent.com/latest/). | The current project page advertises greater than 74% SWE-bench Verified. That model/harness-specific project claim is not independently reproduced here and is not a swarm comparison. [Source](https://mini-swe-agent.com/latest/). |
| GitHub Copilot cloud agent | Cloud sessions research, edit and test in an ephemeral environment, create branches/commits, and push reviewable changes. Chat context can transfer into the active agent session; session logs remain available for review. Repository hooks can perform validation/logging. [Official product guide](https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-on-github). | The guide says logs do not replace review/testing. It does not provide a controlled multi-agent cost-quality result or establish automatic peer-to-peer merge coordination. [Source](https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-on-github). |

## Engineering and research implications

**Context requires a deliberate boundary.** Cognition's June 2025 essay argues that delegated
agents can miss earlier decisions and recommends carrying relevant context/full traces across
handoffs; its historical criticism of multi-agent reliability is an engineering argument,
not a controlled result for today's models. Current Devin workflows above demonstrate why
that essay must not be treated as a timeless product description.
[Essay](https://cognition.com/blog/dont-build-multi-agents).
Our inference: murmur should keep the complete brief and repository instructions available to
fresh peers, while avoiding unrelated launcher transcript inheritance. This is a tradeoff to
measure, not proof that less context always improves quality.

**Textual merge success does not establish behavioral compatibility.** The July 2026 preprint
*AI Agent Pull Requests on GitHub: Frequency, Structure, and Merge Conflict Rates* studies
33,596 PRs and 747 sampled merge pairs, of which 716 were evaluable. It reports textual conflict
rates of 119/601 (19.8%) for same-platform pairs and 48/115 (41.7%) for cross-platform pairs.
Its “agent” groups are platforms, not identities of cooperating swarm peers. The source data
covers December 2024–July 2025, and overlapping open-PR intervals only proxy simultaneous work.
It explicitly does not measure tokens, CI expenditure, or maintainer time.
[Paper, methods/results/limitations](https://arxiv.org/html/2607.04697v2).
Our inference: use the paper to motivate inspecting integrated code, not to predict murmur's
conflict rate or assign a numerical savings claim to an integration helper.

**Do not solve a measured coordination problem by assuming another protocol works.** Our prior
G1 sync helper was used more than 100 times yet did not reduce call counts or the git share;
G1/G2's token effects differed by task. Independent harm-path bugs clustered in single-author
parts and seams. [Local experimental log](evidence/LOG.md),
[round-one results](evidence/lean-RESULTS.md). Cursor's much larger experiment likewise reports
that extra locks/integration roles can become bottlenecks, but its workload and topology differ
from murmur's. [Engineering report](https://cursor.com/blog/scaling-agents).
Our inference: prefer passive measurements and small defaults now; require new evidence before
adding mandatory scheduling, ownership locking, or merge queues.

**Do not cache a result solely because a git hash matches.** OpenHands exposes explicit
conversation/persistence/context mechanisms, and Devin's replay key includes execution settings
as well as the prompt/schema. [OpenHands task persistence](https://docs.openhands.dev/sdk/guides/task-tool-set),
[Devin replay contract](https://docs.devin.ai/work-with-devin/dynamic-workflows).
Our design judgment: commit-bound check receipts are evidence with limits, not permission to
skip tests automatically when ignored dependencies, environments, or external services differ.

## a5 draft and comparison evidence

Draft `c50c5b6` on `draft/a5` implemented a generated shared-origin `post-receive` hook. Each
accepted main update produced immutable JSON keyed by the new revision: before/after SHAs,
commit authors/subjects, and bounded changed paths. Draft pushes produced no main receipt.
The receipt explicitly said `reviewed: false`. This was designed as a discovery aid; no live
agent adoption or quality benefit was measured.

Reproduce in that draft with `.venv/bin/python -m pytest -q tests/test_integration.py`.
Its full suite passed **35 tests in 10.38 seconds** locally; the focused three tests exercised
immutable subsequent updates, draft exclusion, newline filenames, and output truncation.
This demonstrates the prototype mechanics, not fewer model calls or higher-quality code.
The draft remains available for comparison and is **not recommended for integration**: git
already stores the underlying evidence, while a new hook adds an adoption and maintenance cost.

All six drafts were inspected from separate local archives and their full test suites run:

| Draft | Tests passed | Observed pytest seconds | a5 rank | Reason |
| --- | ---: | ---: | ---: | --- |
| a2 | 34 | 9.63 | 1 | Smallest implementation; peer-count evidence and source-backed launcher corrections. |
| a4 | 38 | 9.39 | 2 | Removes hardcoded model/effort policy and supports user preferences. |
| a1 | 37 | 9.57 | 3 | Measures observed response usage without treating missing usage as zero. |
| a6 | 38 | 10.29 | 4 | Captures delivered revision and leftover work without claiming functional success. |
| a3 | 36 | 9.87 | 5 | Check receipts identify revision and dirty state, but require adoption. |
| a5 | 35 | 10.38 | 6 | Receipt mechanism works, but extra hooks lack measured outcome benefit. |

These are test-harness measurements, not an agent benchmark. No live model was invoked for
these checks: experiment inference tokens were **0**; this development/research conversation's
tokens were not measured by those tests and are not included in that zero. The comparison
commands and captured source extracts were kept in a5's `.work/` scratch directory.

## Ranked recommendations from this section

1. **Adopt the small configurable baseline and measure it.** The direct prior peer-count
   experiments are more relevant to murmur than vendor large-swarm demonstrations. Preserve
   explicit peer counts and the solo baseline; do not claim the desired 1.5–2x total-token
   bound has been demonstrated. [Prior evidence](evidence/lean2-RESULTS.md),
   [validation limits](evidence/val-RESULTS.md).
2. **Record observed usage and final delivery separately.** Source/test evidence can establish
   that accounting and inventory work; quality and acceleration still need matched tasks.
   [a5 draft comparison above](#a5-draft-and-comparison-evidence).
3. **Keep review evidence tied to the exact integrated revision.** The local seam failures
   motivate this; receipts must not imply semantic correctness or cross-environment caching.
   [Local seam evidence](evidence/LOG.md), [merge-study limits](https://arxiv.org/html/2607.04697v2).
4. **Defer automatic integration receipts, locks, merge queues, and orchestration rewrites.**
   This draft gives no new outcome evidence; the prior helper failed its call-reduction premise.
   [Prototype above](#a5-draft-and-comparison-evidence), [prior helper](evidence/lean-RESULTS.md).

Unverified: authenticated hands-on trials of these products; private orchestration internals;
current independent cross-product rankings; murmur quality equivalence; live savings from
fresh contexts or receipts; behavior on platforms not exercised by the local test environment.

## Integrated review

At integrated main revision `8ccb0d5`, a5 ran `.venv/bin/python -m pytest -q`:
**53 tests passed in 11.45 seconds**. Running
`.venv/bin/python scripts/capture_states.py .work/final-capture` produced the expected six
exit codes: success 0, failure 1, partial result 1, capped 124, interrupted 130, and resistant
descendant 0. Each state produced `logs/run.json` with both usage and delivery inventory;
missing usage was explicitly unavailable, all inventories had empty error lists, and the
partial-result state recorded its one accepted commit. The CLI help showed two default peers
and user-config/Codex-default model selection. This review exercised Linux/Python 3.13 and
made zero live model calls. No blocking interface issue was found; macOS and real provider
behavior remain unverified by this review.
