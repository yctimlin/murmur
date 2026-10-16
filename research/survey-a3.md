# Additional projects, coordination, and sandbox audit

Sources retrieved on October 16, 2026. This is a bounded primary-source survey, not a claim
that every similar project has been found. “Unverified” means the inspected material did
not establish the detail; no missing detail is filled in from product reputation.

## Project mechanisms

| Project | Split, coordination, and context | Merge behavior and reported results | Relevance to murmur |
|---|---|---|---|
| Aider | Architect mode makes an architect request followed by an editor request that translates the proposal into file edits. Repository maps expose definitions/signatures; a dependency graph ranks the relevant parts to fit a token budget. [Modes](https://aider.chat/docs/usage/modes.html), [repo map](https://aider.chat/docs/repomap.html). | These pages describe staged editing, not independent concurrent Git branches. Conflict merging and a controlled swarm-versus-solo result are unverified in these sources. [Modes](https://aider.chat/docs/usage/modes.html). | Inference: concise structural context can help file discovery, but adding a second model call for every edit is not evidence of lower total cost. |
| MetaGPT | Assigns software-company roles, including product manager, architect, project manager and engineer. Its paper describes SOP prompt sequences, intermediate verification and assembly-line task decomposition. [Repository](https://github.com/FoundationAgents/MetaGPT), [paper](https://arxiv.org/abs/2308.00352). | The paper abstract reports more coherent solutions than previous chat-based systems on collaborative software-engineering benchmarks. Exact effect size, current frontier-model comparison, independent Git integration and long-running repository maintenance performance are unverified here. [Paper](https://arxiv.org/abs/2308.00352). | Inference: intermediate artifacts and explicit interfaces are relevant; imposing fixed job titles would violate murmur's flexible peer design without evidence that those roles fit every task. |
| ChatDev / DevAll | The current repository calls its configurable orchestration platform ChatDev 2.0 / DevAll and links the original software-company implementation on `chatdev1.0`. Workflows configure nodes and edges; memory attachments control retrieval stages and read/write access. [Repository](https://github.com/OpenBMB/ChatDev), [workflow guide](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/workflow_authoring.md), [memory guide](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/modules/memory.md). | Python nodes share a code workspace; the legacy README entry describes opt-in Git version management. These sources do not establish an automatic conflict-free merge guarantee. The original paper reports a language-mediated design/coding/testing paradigm, not a comparable token target for modern long tasks. [Workflow guide](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/workflow_authoring.md), [README](https://github.com/OpenBMB/ChatDev), [paper](https://arxiv.org/abs/2307.07924). | Inference: a bounded append-only blackboard, one documented memory option, resembles the lightweight artifact sharing murmur needs more closely than a new vector-memory dependency. [Memory guide](https://github.com/OpenBMB/ChatDev/blob/main/docs/user_guide/en/modules/memory.md). |
| Amp | Specialist subagents have their own context windows and start with context supplied by the main agent; the docs say those subagents cannot communicate with each other or be guided mid-task. Separately, agent-to-agent orb threads get their own conversation, context, working copy and orb and can report back. [Subagents](https://ampcode.com/docs/models-and-subagents), [agent-to-agent](https://ampcode.com/docs/orbs/agent-to-agent). | Amp's orb guide recommends keeping constantly coordinating or same-file work in the current thread. The inspected pages do not provide a standardized swarm-versus-solo speed/token/quality result or a merge guarantee. [Agent-to-agent](https://ampcode.com/docs/orbs/agent-to-agent). | Inference: separate context is useful for independent work, but independent context and shared mutable files require different safeguards. Do not conflate subagents with independent working copies. |
| gpt-engineer | The CLI accepts a natural-language prompt, generates and executes code, and supports improving an existing directory. Its README points users seeking a maintained hackable CLI to Aider. [Repository](https://github.com/gpt-engineer-org/gpt-engineer). | The README documents a `bench` tool and APPS/MBPP benchmarking support. It does not establish leaderless coordination, context isolation, concurrent Git merging, or a relevant current multi-agent cost result. [Repository](https://github.com/gpt-engineer-org/gpt-engineer). | Inference: it belongs in the coding-agent comparison set, but should not be mislabeled a coding swarm. |
| Sweep | The currently fetched public README is a short notice that the team is building a JetBrains coding assistant. [Current README](https://github.com/sweepai/sweep/blob/main/README.md). | Historical issue-to-PR implementation, present merge mechanics, context policy, and performance numbers are unverified from that notice. [Current README](https://github.com/sweepai/sweep/blob/main/README.md). | Decision: retain an explicit evidence gap instead of repeating stale claims about today's product. |

## Installed Codex sandbox: source, not assumptions

The supplied `/workspace/codex-src-0.162.1` checkout resolves to commit
`092d3acd6bec3e3a14bdc7e7a2810ab628ab759d` (`git rev-parse HEAD`, local observation).
The source URLs below identify that exact revision. Local source was inspected read-only;
remote availability of every commit URL was not independently verified.

- `SandboxPolicy::WorkspaceWrite` includes configured writable roots, cwd, and normally `/tmp`
  and `TMPDIR`. Network permission is a separate Boolean. Source:
  [protocol.rs, WorkspaceWrite and get_writable_roots_with_cwd](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/protocol/src/protocol.rs#L1111).
- The default protected-subpath function examines root-level `.git`, `.agents`, `.codex`, and
  `.aws`; it resolves worktree Git pointers and protects a missing `.codex` for cwd. Source:
  [permissions.rs, default_read_only_subpaths_for_writable_root](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/protocol/src/permissions.rs#L2347).
- Multi-agent handler documentation says children inherit runtime provider, approval policy,
  sandbox and cwd. Source:
  [multi_agents.rs](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/core/src/tools/handlers/multi_agents.rs#L1).
- Murmur launches the session with cwd `work/`, workspace-write, network enabled, approvals
  never, and a shell environment with Git configuration overrides. Source:
  [codex_command and shell_env](../src/murmur/cli.py). **Inference:** the separate peer clones
  isolate ordinary Git working state by convention; this configuration does not create one
  OS sandbox per peer that denies writes to sibling clones. The helper must not describe
  its shared receipts as tamper-proof or a trust boundary.

The official security landing page was also fetched, but the version-specific conclusions
above rely on the supplied source rather than current documentation behavior:
<https://developers.openai.com/codex/security>.

## Ranked improvement implications

1. **Preserve configuration and narrow peer context mechanically.** These avoid coupling the
   launcher to guessed defaults and shared conversational baggage; the source audit and a2/a4
   drafts establish the implementation details. This is an engineering recommendation, not a
   measured end-to-end speed claim. Amp's documented separate-context pattern is supporting
   design precedent, not causal evidence for murmur. [Amp context](https://ampcode.com/docs/models-and-subagents).
2. **Record exactly what was checked.** Prior evidence identifies final-integration review gaps,
   and prior G2 was a prompt rule asking peers to share check results. A receipt can contain the
   actual command/commit/dirty state and exit status without interpreting agent prose.
   [Prior log](evidence/LOG.md), [G2 plan](evidence/lean-PLAN.md),
   [receipt draft and tests](draft-a3.md). This supports provenance, not an automatic correctness
   verdict or a demonstrated token saving.
3. **Do not repeat the sync-helper experiment as a cost claim.** The prior log says the helper
   was used more than 100 times without reducing model-call counts or git-coordination share.
   [Prior log](evidence/LOG.md). A new helper could have operational value, but its token benefit
   remains unverified.
4. **Avoid automatic cross-clone test caching.** A commit identifies tracked content, while
   dependencies, environment and remote state may differ; this is a conservative design
   inference, not a benchmark finding. The draft always executes requested checks and labels
   changed/dirty work trees explicitly. [Archived draft and exact commit](draft-a3.md).

## Draft validation and cost

On this machine, `.venv/bin/python -m pytest -q` on draft `b6d4d15` passed 36 tests in
10.01 seconds. Four new tests exercise clean receipts, dirty/mutating checks, failure/missing
commands, repeat execution, and actual generated wrappers in two temporary clones.
[Archived draft test source at commit b6d4d15](draft-a3.md), [existing fixture isolation](../tests/conftest.py).
The tests use fake Codex, local git and child Python commands; model API calls and model tokens
for this validation were zero. Agent development/research tokens are not measured here.
No live-model swarm experiment, macOS run, or end-to-end quality/token improvement was verified.

Peer selection deferred the receipt implementation; this research and the archived draft note
remain, while main gains automatic run accounting and delivered-state evidence from other
drafts. The receipt implementation is not a main-branch dependency. [Archived decision](draft-a3.md).
